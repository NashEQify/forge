#!/usr/bin/env python3
"""Install forge for one machine with an install profile (full | daily).

Usage: forge_install.py [--profile full|daily] [--check]
                        [--user-repo PATH [--skill-link PATH ...] [--force-user-config]]

Profiles: framework/install-profiles.yaml. User scope: framework/user-scope.md
(machine setting ${XDG_CONFIG_HOME:-~/.config}/forge/user.yaml, override
FORGE_USER_CONFIG). Destinations follow HOME, CODEX_HOME, AGENTS_HOME.

- daily: Codex skills (~/.agents/skills) + Codex home boot block; Claude Code
  skills (~/.claude, names skills/<n>/SKILL.md) + managed block in
  ~/.claude/CLAUDE.md; skill_links as symlinks; no roles, hooks or launcher.
  Previously owned Codex roles are removed; full-profile Claude Code surfaces
  (forge hooks in settings.json, ~/.claude/{agents,skills} symlinks, the cc
  launcher) are a conflict naming the manual steps.
- full: Codex roles + all skills + home boot block + hook cleanup; Claude Code
  surfaces are checked read-only and applied by the unchanged setup-cc.sh
  (never under --check and never against a staged HOME, because setup-cc.sh
  also installs git hooks into the framework checkout). What a daily install
  owns in ~/.claude (block, state, skills, manifest) is removed first.

Hash ownership as in managed_install.py: any conflict aborts before the first
write. Text outside the managed blocks is never edited; legacy person-specific
text there is a conflict for a manual rollout step. --check never writes,
prints one pending path per line and exits 1 when anything is pending.
Exit 2: conflict or error, nothing written. Exit 3: changes were applied and a
later step failed (the message names the step); a re-run converges.
"""

from __future__ import annotations

import argparse
import json
import os
import pwd
import re
import subprocess
import sys
from pathlib import Path

sys.dont_write_bytecode = True

import yaml  # noqa: E402 - disable bytecode before third-party/project imports

try:
    from .generate_codex_agents import (
        check_legacy_text,
        plan_block,
        plan_block_removal,
        plan_codex,
    )
    from .generate_skill_wrappers import build_desired, render_entry
    from .managed_install import (
        InstallConflict,
        InstallPlan,
        digest,
        managed_files,
        read_file,
        read_manifest,
        safe_path,
        unmanage_root,
    )
    from .user_scope import (
        PROFILE_BOOT_FILES,
        PROFILES,
        UserScope,
        boot_text,
        config_path,
        daily_rules,
        from_config,
        load_config,
        unusable_setting,
    )
except ImportError:
    from generate_codex_agents import (
        check_legacy_text,
        plan_block,
        plan_block_removal,
        plan_codex,
    )
    from generate_skill_wrappers import build_desired, render_entry
    from managed_install import (
        InstallConflict,
        InstallPlan,
        digest,
        managed_files,
        read_file,
        read_manifest,
        safe_path,
        unmanage_root,
    )
    from user_scope import (
        PROFILE_BOOT_FILES,
        PROFILES,
        UserScope,
        boot_text,
        config_path,
        daily_rules,
        from_config,
        load_config,
        unusable_setting,
    )

FRAMEWORK = Path(__file__).resolve().parents[1]
CLAUDE_START = "<!-- FORGE-CLAUDE-BOOT:START -->"
CLAUDE_END = "<!-- FORGE-CLAUDE-BOOT:END -->"
CC_SUBSTITUTION = "SUBSTITUTED-BY-SETUP-CC"
CC_MARKER = re.compile(
    r'^FRAMEWORK_DIR_INSTALLED=""  # SUBSTITUTED-BY-SETUP-CC$', re.MULTILINE
)
FORGE_HOOK_DIR = "/orchestrators/claude-code/hooks/"
CODEX_LABELS = {"tool_label": "Codex", "discovery_label": "Codex"}
CLAUDE_LABELS = {"tool_label": "Claude Code", "discovery_label": "Claude-Code"}


class ApplyFailure(Exception):
    """Changes were written, then a later step failed."""

    def __init__(self, applied: int, step: str, error: BaseException) -> None:
        super().__init__(f"applied {applied} changes; {step} failed: {error}")


def load_profile(framework: Path, name: str) -> dict:
    path = framework / "framework" / "install-profiles.yaml"
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or data.get("version") != 1:
        raise ValueError(f"unsupported install profiles file: {path}")
    profile = (data.get("profiles") or {}).get(name)
    if not isinstance(profile, dict):
        raise ValueError(f"profile {name!r} not defined in {path}")
    if tuple(profile.get("boot_files") or ()) != PROFILE_BOOT_FILES[name]:
        raise ValueError(
            f"{path}: boot_files of {name!r} out of sync with scripts/user_scope.py"
        )
    if not profile.get("codex_boot"):
        raise ValueError(f"{path}: profile {name!r} without codex_boot is unsupported")
    return profile


def check_required_paths(framework: Path, profile: dict) -> None:
    for rel in profile.get("required_paths") or []:
        if not (framework / rel).exists():
            raise ValueError(
                f"required framework path missing: {framework / rel} "
                f"(sparse checkout? run: git sparse-checkout add {rel})"
            )


def select_skills(framework: Path, profile: dict, labels: dict) -> dict[str, str]:
    """Kebab name -> wrapper content for the profile's skills and entries."""
    available = build_desired(framework / "skills", framework_root=framework, **labels)
    wanted = profile.get("skills", "all")
    if wanted == "all":
        selected = dict(available)
    elif isinstance(wanted, list):
        missing = [name for name in wanted if name not in available]
        if missing:
            raise ValueError(f"profile skills not available: {', '.join(missing)}")
        selected = {name: available[name] for name in wanted}
    else:
        raise ValueError(f"invalid profile skills: {wanted!r}")
    for name, entry in (profile.get("entries") or {}).items():
        if name in selected:
            raise ValueError(f"entry collides with a skill: {name}")
        if not isinstance(entry, dict) or not entry.get("source") or not entry.get("description"):
            raise ValueError(f"invalid profile entry: {name}")
        source = framework / entry["source"]
        if not source.is_file():
            raise ValueError(f"entry source missing: {source}")
        selected[name] = render_entry(name, entry["description"], source, **labels)
    return selected


def claude_block_body(scope: UserScope, framework: Path, profile: str) -> str:
    """Daily ~/.claude/CLAUDE.md block: the same conditional soul line as the
    Codex block, no install-time soul import."""
    return (
        f"Forge framework root: {framework}\n\n"
        + boot_text(scope, framework, profile, install_time=True)
        + "\n" + daily_rules("claude")
    )


def whole_owned_claude_md(claude_root: Path) -> bool:
    """True when a legacy manifest owns ~/.claude/CLAUDE.md with a matching hash."""
    raw = read_file(claude_root / ".forge-managed.json")
    if raw is None:
        return False
    try:
        owned = json.loads(raw).get("files", {}).get("CLAUDE.md")
    except (ValueError, AttributeError):
        return False  # managed_files reports the invalid manifest
    current = read_file(claude_root / "CLAUDE.md")
    return isinstance(owned, str) and current is not None and digest(current) == owned


def interrupted_migration(claude_root: Path, migrated: bytes) -> bool:
    """True when the manifest still lists CLAUDE.md but the file already holds
    the migrated block-only content (crash between the two writes)."""
    raw = read_file(claude_root / ".forge-managed.json")
    if raw is None:
        return False
    try:
        listed = "CLAUDE.md" in json.loads(raw).get("files", {})
    except (ValueError, AttributeError):
        return False
    return listed and read_file(claude_root / "CLAUDE.md") == migrated


def plan_links(root: Path, links: list[str], managed: set[str]) -> list[tuple[Path, str]]:
    """Return links still to create; same target is fine, anything else conflicts."""
    root = safe_path(root)
    pending = []
    for target in links:
        name = os.path.basename(os.path.normpath(target))
        if name in managed:
            raise InstallConflict(f"skill link collides with a managed skill: {root / name}")
        link = root / name
        if link.is_symlink():
            if os.path.realpath(link) != os.path.realpath(target):
                raise InstallConflict(f"skill link points elsewhere: {link}")
        elif link.exists():
            raise InstallConflict(f"skill link destination exists: {link}")
        else:
            pending.append((link, target))
    return pending


def plan_user_config(
    plan: InstallPlan, path: Path, data: dict, *, force: bool
) -> None:
    raw = read_file(path)
    if raw is not None:
        try:
            current = yaml.safe_load(raw)
        except yaml.YAMLError:
            current = None
        if current == data:
            return
        if not force:
            raise InstallConflict(
                f"machine setting differs: {path} (use --force-user-config to replace it)"
            )
    plan.add(
        path,
        yaml.safe_dump(data, sort_keys=False, allow_unicode=True).encode(),
        expected=raw,
    )


def _forge_checkout_link(link: Path, name: str) -> bool:
    """A symlink to <some forge checkout>/.claude/<name>."""
    if not link.is_symlink():
        return False
    lexical = Path(os.path.normpath(link.parent / os.readlink(link)))
    return any(
        target.name == name and (target.parent.parent / "agents/buddy/boot.md").is_file()
        for target in (lexical, Path(os.path.realpath(link)))
    )


def full_claude_surfaces(home: Path) -> list[str]:
    """Manual steps for full-profile Claude Code surfaces a daily install must not keep."""
    steps = []
    settings = home / ".claude/settings.json"
    try:
        data = json.loads(settings.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        data = None
    hooks = data.get("hooks") if isinstance(data, dict) else None
    if FORGE_HOOK_DIR in json.dumps(hooks):
        steps.append(
            f"remove the forge SessionStart hooks (buddy-boot-inject.sh, "
            f"session-start-remote.sh) from {settings}"
        )
    agents = home / ".claude/agents"
    if _forge_checkout_link(agents, "agents"):
        steps.append(f"rm {agents}  (symlink to the framework roles)")
    skills = home / ".claude/skills"
    if skills.is_symlink():
        steps.append(f"rm {skills}  (symlink; daily installs real skill files here)")
    launcher = home / ".local/bin/cc"
    try:
        if launcher.is_file() and CC_SUBSTITUTION in launcher.read_text(errors="replace"):
            steps.append(f"rm {launcher}  (forge cc launcher)")
    except OSError:
        pass
    return steps


def plan_daily_claude_removal(
    plan: InstallPlan, claude_root: Path, skill_links: list[str]
) -> list[Path]:
    """daily → full: remove what a daily install owns in ~/.claude.

    Returns forge-created skill links to unlink after apply. Unowned or
    modified leftovers are a conflict with manual steps.
    """
    state = claude_root / ".forge-claude-boot.json"
    _, raw, owned = read_manifest(claude_root)
    if read_file(state) is None and raw is None:
        return []
    unmanage_root(plan, claude_root)
    plan_block_removal(plan, claude_root / "CLAUDE.md", state, CLAUDE_START, CLAUDE_END)
    skills_dir = claude_root / "skills"
    if not skills_dir.is_dir() or skills_dir.is_symlink():
        return []
    targets = {os.path.basename(os.path.normpath(t)): t for t in skill_links}
    links, leftovers = [], []
    for entry in sorted(skills_dir.iterdir()):
        if entry.is_symlink():
            target = targets.get(entry.name)
            if target and os.path.realpath(entry) == os.path.realpath(target):
                links.append(entry)
            else:
                leftovers.append(entry)
        elif entry.is_dir():
            leftovers += [
                path for path in entry.rglob("*")
                if not path.is_dir() and str(path.relative_to(claude_root)) not in owned
            ]
        else:
            leftovers.append(entry)
    if leftovers:
        raise InstallConflict(
            f"unowned entries in {skills_dir} block the switch to full (setup-cc.sh "
            "must replace the directory with the framework symlink); move them "
            "away by hand, then re-run: " + ", ".join(map(str, leftovers))
        )
    return links


def claude_full_drift(framework: Path, home: Path, *, removing: bool) -> list[str]:
    """Read-only check of the surfaces setup-cc.sh owns; returns pending paths."""
    pending = []
    source = (framework / "orchestrators/claude-code/bin/cc").read_text(encoding="utf-8")
    installed = f'FRAMEWORK_DIR_INSTALLED="{framework}"  # {CC_SUBSTITUTION}'
    expected = CC_MARKER.sub(lambda _: installed, source)
    launcher = home / ".local/bin/cc"
    if not launcher.is_file() or launcher.read_text(encoding="utf-8", errors="replace") != expected:
        pending.append(str(launcher))
    template = json.loads(
        (framework / "orchestrators/claude-code/settings.json.template")
        .read_text(encoding="utf-8")
        .replace("__FRAMEWORK_DIR__", json.dumps(str(framework))[1:-1])
    )
    settings_path = home / ".claude/settings.json"
    try:
        settings = json.loads(settings_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        settings = None
    if not isinstance(settings, dict) or any(
        settings.get(key) != value for key, value in template.items()
    ):
        pending.append(str(settings_path))
    for name in ("agents", "skills"):
        link = home / ".claude" / name
        target = framework / ".claude" / name
        if not link.is_symlink() or os.path.realpath(link) != os.path.realpath(target):
            if link.exists() and not link.is_symlink() and not (removing and name == "skills"):
                print(
                    f"forge install: warning: {link} is a real directory; setup-cc.sh "
                    "does not replace it (remove it by hand)",
                    file=sys.stderr,
                )
            pending.append(str(link))
    return pending


def staged_home(home: Path) -> bool:
    try:
        real = pwd.getpwuid(os.getuid()).pw_dir
    except KeyError:
        return True
    return os.path.realpath(home) != os.path.realpath(real)


def prune_empty_dirs(removed: list[Path], roots: list[Path]) -> None:
    """rmdir (non-recursive) directories emptied by owned-file removals."""
    for path in removed:
        directory = path.parent
        while (
            any(directory != root and directory.is_relative_to(root) for root in roots)
            and directory.is_dir()
            and not directory.is_symlink()
            and not any(directory.iterdir())
        ):
            directory.rmdir()
            directory = directory.parent


def prune_empty_skill_dirs(skill_roots: list[Path]) -> None:
    """rmdir skill directories that hold nothing but empty directories.

    Covers removals an interrupted earlier run already finished after its
    manifest no longer lists them; an empty directory holds no user content.
    """
    for root in skill_roots:
        if not root.is_dir() or root.is_symlink():
            continue
        for child in sorted(root.iterdir()):
            if not child.is_dir() or child.is_symlink():
                continue
            nested = sorted(child.rglob("*"), key=lambda q: len(q.parts), reverse=True)
            if all(q.is_dir() and not q.is_symlink() for q in nested):
                for q in nested:
                    q.rmdir()
                child.rmdir()


def main(argv: list[str] | None = None, *, framework: Path = FRAMEWORK) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--profile", choices=PROFILES)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--user-repo", type=Path)
    parser.add_argument("--skill-link", type=Path, action="append", default=None)
    parser.add_argument("--force-user-config", action="store_true")
    args = parser.parse_args(argv)
    if (args.skill_link or args.force_user_config) and args.user_repo is None:
        parser.error("--skill-link and --force-user-config require --user-repo")
    env = os.environ
    try:
        home = Path(env.get("HOME") or "")
        if not str(home) or not home.is_absolute():
            raise ValueError("HOME must be an absolute path")
        codex_home = safe_path(Path(env.get("CODEX_HOME") or home / ".codex"))
        agents_home = safe_path(Path(env.get("AGENTS_HOME") or home / ".agents"))
        claude_root = home / ".claude"

        cfg = config_path(env)
        data, cfg_warnings = load_config(cfg) if cfg is not None else (None, [])
        file_profile = data.get("profile") if data else None
        unusable = unusable_setting(env)
        if unusable and args.profile is None and args.user_repo is None:
            raise InstallConflict(
                f"machine setting unusable ({unusable}); fix it, or pass --profile "
                "(and --user-repo ... --force-user-config to rewrite it)"
            )
        if (
            args.profile
            and file_profile
            and args.profile != file_profile
            and args.user_repo is None
        ):
            raise InstallConflict(
                f"--profile {args.profile} differs from {cfg} (profile: {file_profile}); "
                "pass --user-repo to rewrite the machine setting"
            )
        profile_name = args.profile or (
            file_profile if file_profile in PROFILES else "full"
        )
        profile = load_profile(framework, profile_name)
        check_required_paths(framework, profile)

        plan = InstallPlan()
        if args.user_repo is not None:
            if cfg is None:
                raise ValueError("cannot locate the machine setting (HOME unset)")
            repo = Path(os.path.abspath(args.user_repo.expanduser()))
            if not repo.is_dir():
                raise ValueError(f"--user-repo is not a directory: {repo}")
            if args.skill_link is not None:
                skill_links = [os.path.abspath(p.expanduser()) for p in args.skill_link]
            else:
                # Carry over only links the resolver validated (never list() a scalar).
                previous = from_config(framework, data, config=cfg)
                skill_links = list(previous.skill_links)
                for warning in previous.warnings:
                    if warning.startswith(("skill link", "skill_links")):
                        print(
                            f"forge install: not carried over: {warning}", file=sys.stderr
                        )
            data = {
                "version": 1,
                "user_repo": str(repo),
                "profile": profile_name,
                "skill_links": skill_links,
            }
            cfg_warnings = []
            plan_user_config(plan, cfg, data, force=args.force_user_config)
        scope = from_config(framework, data, config=cfg, warnings=cfg_warnings)
        for warning in scope.warnings:
            print(f"forge install: user scope warning: {warning}", file=sys.stderr)

        daily_claude = bool(profile.get("claude_boot_block"))
        if daily_claude:
            steps = full_claude_surfaces(home)
            if steps:
                raise InstallConflict(
                    "full-profile Claude Code surfaces present; remove them by hand "
                    "before installing daily:\n  - " + "\n  - ".join(steps)
                )

        links: list[tuple[Path, str]] = []
        codex = select_skills(framework, profile, CODEX_LABELS)
        plan_codex(
            plan,
            codex_home,
            agents_home,
            framework,
            skills=codex,
            scope=scope,
            profile=profile_name,
            roles=bool(profile.get("codex_roles")),
        )
        links += plan_links(agents_home / "skills", scope.skill_links, set(codex))

        stale_links: list[Path] = []
        claude_pending: list[str] = []
        if daily_claude:
            claude = select_skills(framework, profile, CLAUDE_LABELS)
            body = claude_block_body(scope, framework, profile_name)
            # Block-only content the legacy migration writes; a file already
            # holding it was written by an interrupted earlier run.
            migrated = (CLAUDE_START + "\n" + body + CLAUDE_END + "\n").encode()
            whole = whole_owned_claude_md(claude_root) or interrupted_migration(
                claude_root, migrated
            )
            managed_files(
                plan,
                claude_root,
                {f"skills/{name}/SKILL.md": content for name, content in claude.items()},
                release=frozenset({"CLAUDE.md"}) if whole else frozenset(),
                release_completed={"CLAUDE.md": migrated},
            )
            links += plan_links(claude_root / "skills", scope.skill_links, set(claude))
            if not whole:
                check_legacy_text(claude_root / "CLAUDE.md", CLAUDE_START, CLAUDE_END)
            plan_block(
                plan,
                claude_root / "CLAUDE.md",
                claude_root / ".forge-claude-boot.json",
                CLAUDE_START,
                CLAUDE_END,
                body,
                replace_whole=whole,
            )
        else:
            stale_links = plan_daily_claude_removal(plan, claude_root, scope.skill_links)
        if profile.get("claude_setup"):
            removing = bool(plan.changes()) and any(
                path.is_relative_to(claude_root) for path in plan.changes()
            )
            claude_pending = claude_full_drift(framework, home, removing=removing)
            if scope.skill_links:
                print(
                    "forge install: skill links not applied to Claude Code: "
                    "~/.claude/skills is the framework symlink",
                    file=sys.stderr,
                )

        changes = plan.changes()
        pending = [str(path) for path in changes]
        pending += [str(link) for link, _ in links] + [str(p) for p in stale_links]
        if args.check:
            for path in pending + claude_pending:
                print(path)
            return int(bool(pending + claude_pending))

        applied = 0
        step = "apply"
        try:
            try:
                plan.apply()
            finally:
                applied = plan.written
            step = "skill links"
            for link in stale_links:
                link.unlink()
                applied += 1
            for link, target in links:
                link.parent.mkdir(parents=True, exist_ok=True)
                link.symlink_to(target, target_is_directory=True)
                applied += 1
            step = "empty directory cleanup"
            # Every planned removal, also ones an interrupted earlier run already did.
            removed = [p for p, (_, new) in plan.files.items() if new is None]
            prune_empty_dirs(removed + stale_links, [agents_home / "skills", claude_root, codex_home / "agents"])
            prune_empty_skill_dirs(
                [agents_home / "skills"] + ([claude_root / "skills"] if daily_claude else [])
            )
            skills_dir = claude_root / "skills"
            if (
                not daily_claude
                and skills_dir.is_dir()
                and not skills_dir.is_symlink()
                and not any(skills_dir.iterdir())
            ):
                skills_dir.rmdir()  # lets setup-cc.sh create the framework symlink
        except (OSError, ValueError) as exc:
            raise ApplyFailure(applied, step, exc) from exc
        print(f"forge install ({profile_name}): {applied} changes applied")
        if profile.get("claude_setup"):
            if staged_home(home):
                print(
                    "forge install: Claude Code full setup skipped for a staged HOME "
                    f"(setup-cc.sh also installs git hooks); pending: {len(claude_pending)}",
                    file=sys.stderr,
                )
            else:
                result = subprocess.run(
                    ["bash", str(framework / profile["claude_setup"])], check=False
                )
                if result.returncode != 0:
                    raise ApplyFailure(
                        applied, profile["claude_setup"], f"exit {result.returncode}"
                    )
        return 0
    except ApplyFailure as exc:
        print(f"forge install: {exc}", file=sys.stderr)
        return 3
    except (OSError, ValueError, yaml.YAMLError) as exc:
        print(f"forge install: conflict: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
