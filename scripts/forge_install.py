#!/usr/bin/env python3
"""Install the selected Forge capability closure as one recoverable generation.

Ordinary installation composes Codex, Claude and OpenCode host plans. Maintainers
use --maintenance prepare before changing sources, status/retry/rollback after
interruption, and validate with an exact operation ID and fresh-session evidence.
--check observes pending changes without writing. Source and integration state
remain stopped at validation_pending until evidence is explicitly accepted.
Unknown local edits are conflicts; rollback never resets a repository or rewrites
consumer workflow state. Machine settings and ownership checks remain preserved.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

sys.dont_write_bytecode = True

try:
    from . import install_activation
except ImportError:
    import install_activation

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


def source_inventory(framework: Path, closure: list[str]) -> list[Path]:
    """Actual bytes, including local edits and old routes, not Git HEAD."""
    paths = set()
    roots = [framework / rel for rel in closure]
    roots += [framework / name for name in ("scripts", "framework", "workflows", "agents", "skills", "orchestrators", ".claude")]
    roots += [framework / name for name in ("AGENTS.md", "CLAUDE.md", "intent.md")]
    for root in roots:
        if root.is_file() or root.is_symlink():
            paths.add(root)
        elif root.is_dir():
            paths.update(p for p in root.rglob("*") if (p.is_file() or p.is_symlink()) and "__pycache__" not in p.parts and ".git" not in p.parts)
    return sorted(paths)


# Exact source bytes from the immediately preceding installed generation. Only
# the installation root substitution is normalized; user edits remain conflicts.
PREDECESSOR_LAUNCHER_HASHES = {
    "cc": "ca12a48770763ff66aa5ce99615924de790223d0b9bf6aeed02dace4bf4da7ca",
    "oc": "58587bfd8a3715907e54711ad4c2967e62a90b0ad12cd7facd801f537f896cdf",
}


def framework_git_hooks(framework):
    """Resolve only this explicitly selected framework's default Git hooks."""
    if not (framework / '.git').exists():
        return []
    def git(*args):
        return subprocess.run(['git', '-C', str(framework), *args], text=True,
                              capture_output=True, timeout=10)
    configured = git('config', '--get', 'core.hooksPath')
    if configured.returncode != 1:
        raise ValueError('custom or unreadable core.hooksPath; preserve existing hook routing')
    common = git('rev-parse', '--path-format=absolute', '--git-common-dir')
    if common.returncode:
        raise ValueError('cannot resolve framework Git common directory')
    hookdir = Path(common.stdout.strip()) / 'hooks'
    if hookdir.is_symlink():
        raise ValueError('framework Git hooks directory is a symlink')
    paths = []
    for name in ('pre-commit', 'commit-msg'):
        target = hookdir / name
        effective = git('rev-parse', '--path-format=absolute', '--git-path', 'hooks/' + name)
        if effective.returncode or Path(effective.stdout.strip()).resolve() != target.resolve():
            raise ValueError('framework Git hook routing conflict: ' + name)
        paths.append(target)
    return paths


def plan_full_hosts(plan, framework, home, scope, modes, host):
    """Host planning uses read-only Git resolution; mutation belongs to activation."""
    links = []
    launchers = {}
    for name, adapter, marker in (("cc", "claude-code", "CC"), ("oc", "opencode", "OC")):
        if host not in {"all", name}:
            continue
        source = (framework / f"orchestrators/{adapter}/bin/{name}").read_text()
        needle = f'FRAMEWORK_DIR_INSTALLED=""  # SUBSTITUTED-BY-SETUP-{marker}'
        if source.count(needle) != 1:
            raise ValueError(f"launcher substitution marker invalid: {name}")
        launchers[name] = source.replace(needle, f'FRAMEWORK_DIR_INSTALLED="{framework}"  # SUBSTITUTED-BY-SETUP-{marker}')
        modes[home / ".local/bin" / name] = 0o755
    # Retain other previously owned launchers when an individual public entry runs.
    binroot = home / ".local/bin"
    _, _, owned = read_manifest(binroot)
    for name in owned:
        if name not in launchers:
            launchers[name] = (binroot / name).read_text()
    if launchers:
        legacy_hashes = {}
        for name in launchers:
            current = read_file(binroot / name)
            if current is None or name not in PREDECESSOR_LAUNCHER_HASHES:
                continue
            marker = f'FRAMEWORK_DIR_INSTALLED="{framework}"  # SUBSTITUTED-BY-SETUP-{name.upper()}'
            neutral = f'FRAMEWORK_DIR_INSTALLED=""  # SUBSTITUTED-BY-SETUP-{name.upper()}'
            normalized = current.replace(marker.encode(), neutral.encode())
            if digest(normalized) == PREDECESSOR_LAUNCHER_HASHES[name]:
                legacy_hashes[name] = {digest(current)}
        managed_files(plan, binroot, launchers, legacy=launchers, legacy_hashes=legacy_hashes)
    if host in {"all", "cc"}:
        hook_source = framework / 'orchestrators/claude-code/hooks/pre-commit.sh'
        for target in framework_git_hooks(framework):
            if not hook_source.is_file():
                raise ValueError('missing framework Git hook source')
            current = install_activation.identity(target)
            if current['kind'] == 'absent':
                links.append((target, str(hook_source)))
            elif current['kind'] != 'link' or target.resolve() != hook_source.resolve():
                raise ValueError('unowned framework Git hook: ' + str(target))
        root = home / ".claude"
        settings_path = root / "settings.json"
        old = read_file(settings_path)
        settings = json.loads(old) if old else {}
        if not isinstance(settings, dict):
            raise ValueError("Claude settings must be a JSON object")
        template = json.loads((framework / "orchestrators/claude-code/settings.json.template").read_text().replace("__FRAMEWORK_DIR__", json.dumps(str(framework))[1:-1]))
        hooks = settings.get("hooks")
        if hooks and hooks != template.get("hooks"):
            for groups in hooks.values():
                for group in groups:
                    for hook in group.get("hooks", []):
                        if FORGE_HOOK_DIR not in hook.get("command", ""):
                            raise ValueError("custom Claude hooks conflict with coordinated setup")
        settings.update(template)
        plan.add(settings_path, (json.dumps(settings, indent=2) + "\n").encode(), expected=old)
        for name in ("skills", "agents"):
            link = root / name
            target = framework / ".claude" / name
            if not target.is_dir():
                raise ValueError(f"missing generated host source: {target}")
            if link.is_symlink():
                if not _forge_checkout_link(link, name):
                    raise ValueError(f"unowned Claude link: {link}")
                if os.readlink(link) != str(target):
                    links.append((link, str(target)))
            elif link.exists():
                if name != "skills" or not any(p.is_relative_to(link) and new is not None for p, (_, new) in plan.files.items()):
                    raise ValueError(f"unowned Claude host directory: {link}")
            else:
                links.append((link, str(target)))
    if host in {"all", "oc"}:
        template = framework / "orchestrators/opencode/opencode.jsonc.example"
        text = template.read_text().replace("${FRAMEWORK_DIR}", str(framework)).replace("${HOME}", str(home))
        values = {"FORGE_USER_INSTRUCTIONS": [json.dumps(p) + "," for p in [scope.soul, *scope.boot]],
                  "FORGE_USER_DIR_ALLOW": [json.dumps(scope.user_repo.rstrip("/") + "/**") + ': "allow",'] if scope.configured else []}
        for name, lines in values.items():
            pattern = re.compile(r"^([ \t]*)// \$\{" + name + r"\}[ \t]*$", re.M)
            text = pattern.sub(lambda m: "\n".join(m.group(1) + line for line in lines), text)
        # Runtime configuration is installed in host state, never written into source.
        config = home / ".config/forge/opencode.jsonc"
        managed_files(plan, config.parent, {config.name: text}, legacy={config.name: text})
    return links


def prepare_baseline(transaction, framework, home, codex_home, agents_home, consumer_roots):
    """Bootstrap from a predecessor that does not ship this coordinator.

    Inspect only known installation surfaces and manifest-owned paths, never
    discover consumers or scan host credentials/session stores.
    """
    targets = set(framework_git_hooks(framework))
    for root in (codex_home / "agents", agents_home / "skills", home / ".claude", home / ".claude/agents",
                 home / ".local/bin", home / ".config/forge"):
        if root.is_symlink():
            targets.add(root)
            continue
        if not root.exists():
            continue
        manifest, raw, owned = read_manifest(root)
        targets.add(manifest)
        if raw:
            for name in owned:
                if Path(name).is_absolute() or ".." in Path(name).parts:
                    raise ValueError(f"unsafe previous manifest entry: {name}")
                targets.add(root / name)
    for base, names in ((codex_home, ["AGENTS.md", ".forge-codex-boot.json", "hooks.json"]),
                        (home / ".claude", ["CLAUDE.md", ".forge-claude-boot.json", "settings.json"]),
                        (home / ".local/bin", ["cc", "oc"]),
                        (home / ".config/forge", ["opencode.jsonc"]),
                        (home / ".local/state/forge", ["selection.json"])):
        targets.update(base / name for name in names)
    skills = home / ".claude/skills"
    if skills.is_symlink():
        targets.add(skills)
    # Explicit user skill links are installation identities, not their targets.
    cfg = config_path(os.environ)
    if cfg:
        targets.add(cfg)
        config, _ = load_config(cfg)
        scope = from_config(framework, config, config=cfg)
        for target in scope.skill_links:
            for root in (agents_home / "skills", home / ".claude/skills"):
                if not root.is_symlink():
                    targets.add(root / Path(target).name)
    transaction.prepare(source_inventory(framework, []), sorted(targets), consumer_roots=consumer_roots)
    data = transaction._load()
    data["compatibility"] = install_activation.workflow_compatibility(data)
    transaction._save(data)
    return transaction.status()


def _main(argv: list[str] | None = None, *, framework: Path = FRAMEWORK) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--profile", choices=PROFILES)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--user-repo", type=Path)
    parser.add_argument("--skill-link", type=Path, action="append", default=None)
    parser.add_argument("--force-user-config", action="store_true")
    parser.add_argument("--maintenance", choices=["prepare", "status", "retry", "rollback", "validate"])
    parser.add_argument("--operation-id")
    parser.add_argument("--require-ready", action="store_true")
    parser.add_argument("--validation-operation")
    parser.add_argument("--validation-evidence", type=Path)
    parser.add_argument("--consumer-root", type=Path, action="append", default=[])
    parser.add_argument("--method", action="append", default=[])
    parser.add_argument("--methods", default="")
    parser.add_argument("--migrate-legacy", action="store_true")
    parser.add_argument("projects", nargs="*", type=Path)
    args = parser.parse_args(argv)
    if args.validation_operation and args.maintenance != "status":
        parser.error("--validation-operation requires --maintenance status")
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

        transaction = install_activation.Activation(framework, install_activation.journal_path(home))
        if args.maintenance in {"status", "retry", "rollback", "validate"}:
            if args.check and args.maintenance != "status":
                raise ValueError("--check cannot mutate maintenance state")
            if args.validation_operation and args.maintenance != "status":
                raise ValueError('--validation-operation requires maintenance status')
            if args.maintenance == "status":
                result = (transaction.validation_status(args.validation_operation, compatibility=install_activation.workflow_compatibility)
                          if args.validation_operation else transaction.status())
            elif args.maintenance == "retry":
                result = transaction.retry(compatibility=install_activation.workflow_compatibility)
            elif args.maintenance == "rollback":
                result = transaction.rollback(compatibility=install_activation.workflow_compatibility)
            else:
                if not args.operation_id or not args.validation_evidence:
                    raise ValueError("validate requires --operation-id and --validation-evidence")
                result = transaction.validate(args.operation_id, args.validation_evidence)
            print(json.dumps(result, sort_keys=True))
            return int(args.require_ready and not result.get("validation_session") and result["phase"] not in {"complete", "rolled_back"})

        if args.maintenance == "prepare":
            if args.check:
                raise ValueError("--check cannot prepare maintenance")
            result = prepare_baseline(transaction, framework, home, codex_home, agents_home, args.consumer_root)
            print(json.dumps(result, sort_keys=True))
            return 0

        if not args.check and args.maintenance != "prepare":
            state = transaction.status()
            if state["phase"] in {"applying", "recovery_required"}:
                if state.get("reason"):
                    raise ValueError(state["reason"])
                result = transaction.retry(compatibility=install_activation.workflow_compatibility)
                if result["phase"] != "prepared":
                    print(json.dumps(result, sort_keys=True))
                    return 0
                state = result
            if state["phase"] == "prepared":
                transaction.seal_updated_sources(source_inventory(framework, []))
        cfg = config_path(env)
        data, cfg_warnings = load_config(cfg) if cfg is not None else (None, [])
        file_profile = data.get("profile") if data else None
        selection = home / ".local/state/forge/selection.json"
        selection_raw = read_file(selection)
        installed_selection = json.loads(selection_raw) if selection_raw else {}
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
            file_profile if file_profile in PROFILES else installed_selection.get("profile", "full")
        )
        profile = load_profile(framework, profile_name)
        try:
            from .capability_closure import compose_profile, validate_closure
        except ImportError:
            from capability_closure import compose_profile, validate_closure
        selected_methods = args.method + [name for name in args.methods.split(",") if name]
        if not selected_methods:
            selected_methods = installed_selection.get("methods", [])
        profile = compose_profile(framework, profile, selected_methods)
        closure = validate_closure(framework, profile)
        check_required_paths(framework, profile)

        plan = InstallPlan()
        desired_selection = (json.dumps({"profile": profile_name, "methods": selected_methods}, sort_keys=True) + "\n").encode()
        plan.add(selection, desired_selection, expected=read_file(selection))
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
        legacy_roles = legacy_skills = legacy_skill_hashes = None
        if args.migrate_legacy:
            try:
                from .codex_legacy import legacy_hashes
            except ImportError:
                from codex_legacy import legacy_hashes
            legacy_roles = legacy_hashes("roles", framework)
            legacy_skill_hashes = legacy_hashes("skills")
            legacy_skills = {f"{name}/SKILL.md": content for name, content in build_desired(framework / "skills", **CODEX_LABELS).items()}
        plan_codex(
            plan,
            codex_home,
            agents_home,
            framework,
            skills=codex,
            scope=scope,
            profile=profile_name,
            roles=bool(profile.get("codex_roles")) or profile.get("method_roles", []),
            legacy_roles=legacy_roles, legacy_skills=legacy_skills, legacy_skill_hashes=legacy_skill_hashes,
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
            role_wrappers = {}
            for role in profile.get("method_roles", []):
                source = framework / "agents" / f"{role}.md"
                sections = re.split(r"(?m)^---[ \t]*$", source.read_text(), maxsplit=2)
                if len(sections) != 3:
                    raise ValueError(f"invalid selected method role: {source}")
                metadata = yaml.safe_load(sections[1])
                header = yaml.safe_dump({"name": role, "description": metadata["description"]}, sort_keys=False).strip()
                role_wrappers[f"{role}.md"] = (
                    "---\n" + header + "\n---\n\n"
                    "<!-- generated-by: scripts/forge_install.py -->\n"
                    f"Read and follow the canonical role at `{source}`.\n"
                    f"Resolve framework references against `{framework}` and bare `_protocols/` references against `{framework / 'agents'}`.\n"
                    "Use the caller's execution and output context as specified by the canonical role.\n"
                )
            if role_wrappers or (claude_root / "agents/.forge-managed.json").exists():
                managed_files(plan, claude_root / "agents", role_wrappers)

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
            # Existing managed daily directories remain hash-owned directories.
            # Upgrade their contents without an unsafe directory-to-link swap.
            if (claude_root / "skills").is_dir() and not (claude_root / "skills").is_symlink():
                for path in list(plan.files):
                    if path == claude_root / ".forge-managed.json" or path.is_relative_to(claude_root / "skills"):
                        del plan.files[path]
                claude = select_skills(framework, profile, CLAUDE_LABELS)
                managed_files(plan, claude_root, {f"skills/{name}/SKILL.md": content for name, content in claude.items()})
        modes = {}
        if profile.get("claude_setup"):
            # Host plans share the same preflight, journal and source generation.
            links += plan_full_hosts(plan, framework, home, scope, modes, "all")
        if args.projects:
            try:
                from .generate_codex_agents import plan_boot, plan_hook_cleanup
            except ImportError:
                from generate_codex_agents import plan_boot, plan_hook_cleanup
            for project in args.projects:
                if not project.is_dir():
                    raise ValueError(f"project directory missing: {project}")
                plan_boot(plan, project, framework, scope=None, profile=profile_name)
                plan_hook_cleanup(plan, project / ".codex", framework)

        changes = plan.changes()
        pending = [str(path) for path in changes]
        pending += [str(link) for link, _ in links] + [str(p) for p in stale_links]
        if args.check:
            for path in pending + claude_pending:
                print(path)
            return int(bool(pending + claude_pending))

        source_paths = source_inventory(framework, closure)
        targets = [*plan.files, *(p for p, _ in links), *stale_links]
        if profile.get("claude_setup"):
            targets.extend(framework_git_hooks(framework))
        state = transaction.status()
        if state["phase"] == "complete" and not pending:
            data = transaction._load()
            transaction._check(data, integration=True, source=True)
            print(json.dumps(state, sort_keys=True))
            return 0
        if state["phase"] in {"unprepared", "complete", "rolled_back"}:
            transaction.prepare(source_paths, targets, consumer_roots=args.consumer_root, closure=closure)
        elif state["phase"] == "validation_pending":
            data = transaction._load()
            transaction._check(data, integration=True, source=True)
            if pending:
                raise ValueError("activation awaits validation; validate or rollback before another change")
            print(json.dumps(state, sort_keys=True))
            return 0
        result = transaction.apply(plan, [*( (p, None) for p in stale_links), *links],
                                   source_paths=source_paths, modes=modes,
                                   compatibility=install_activation.workflow_compatibility, closure=closure)
        print(json.dumps(result, sort_keys=True))
        return 0
    except ApplyFailure as exc:
        print(f"forge install: {exc}", file=sys.stderr)
        return 3
    except (OSError, ValueError, yaml.YAMLError) as exc:
        print(f"forge install: conflict: {exc}", file=sys.stderr)
        return 2


def main(argv: list[str] | None = None, *, framework: Path = FRAMEWORK) -> int:
    arguments = sys.argv[1:] if argv is None else argv
    shared = "--check" in arguments or ("--maintenance" in arguments and arguments[arguments.index("--maintenance") + 1:][:1] == ["status"])
    try:
        with install_activation.machine_lock(shared=shared):
            return _main(arguments, framework=framework)
    except (OSError, ValueError) as exc:
        print(f"forge install: conflict: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
