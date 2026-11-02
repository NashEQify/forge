#!/usr/bin/env python3
"""Install Forge: into one project (the default), or for every session of this machine.

`forge_install.py PROJECT` installs the `project` profile: Buddy and the roles in
that project only (scripts/project_install.py); nothing outside the project
changes, and `--remove PROJECT` takes it out again. `--profile
full-ai-integration` installs the big installation: Buddy in every session, with
knowledge and continuity across projects (the user scope), the project
discipline included, as one recoverable generation of the chosen Codex, Claude
Code and OpenCode host plans: --host, else the hosts recorded by the existing
installation, else the assistants found installed on PATH. Maintainers use
--maintenance prepare before changing sources, status/retry/rollback after
interruption, and validate with an exact operation ID and fresh-session evidence.
--check observes pending changes without writing. Source and integration state
remain stopped at validation_pending until evidence is explicitly accepted.
Unknown local edits are conflicts; rollback never resets a repository or rewrites
consumer workflow state. Machine settings and ownership checks remain preserved.
"""

from __future__ import annotations

import argparse
import base64
import contextlib
import io
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
from pathlib import Path

sys.dont_write_bytecode = True

try:
    from . import install_activation, project_install
except ImportError:
    import install_activation
    import project_install

import yaml  # noqa: E402 - disable bytecode before third-party/project imports

try:
    from .generate_codex_agents import END as CODEX_END
    from .generate_codex_agents import START as CODEX_START
    from .generate_codex_agents import plan_codex, plan_hook_cleanup
    from .generate_skill_wrappers import build_desired, render_entry
    from .managed_install import (
        InstallConflict,
        InstallPlan,
        digest,
        managed_files,
        owned_part,
        json_bytes,
        plan_block_removal,
        plan_text_block_removal,
        prune_empty_dirs,
        read_file,
        read_manifest,
        safe_path,
        unmanage_root,
    )
    from .user_scope import (
        MACHINE_PROFILE,
        PROFILES,
        PROJECT_PROFILE,
        UserScope,
        config_path,
        forge_soul,
        from_config,
        load_config,
        normalize_profile,
        unusable_setting,
    )
except ImportError:
    from generate_codex_agents import END as CODEX_END
    from generate_codex_agents import START as CODEX_START
    from generate_codex_agents import plan_codex, plan_hook_cleanup
    from generate_skill_wrappers import build_desired, render_entry
    from managed_install import (
        InstallConflict,
        InstallPlan,
        digest,
        managed_files,
        owned_part,
        json_bytes,
        plan_block_removal,
        plan_text_block_removal,
        prune_empty_dirs,
        read_file,
        read_manifest,
        safe_path,
        unmanage_root,
    )
    from user_scope import (
        MACHINE_PROFILE,
        PROFILES,
        PROJECT_PROFILE,
        UserScope,
        config_path,
        forge_soul,
        from_config,
        load_config,
        normalize_profile,
        unusable_setting,
    )

FRAMEWORK = Path(__file__).resolve().parents[1]
CLAUDE_START = "<!-- FORGE-CLAUDE-BOOT:START -->"
CLAUDE_END = "<!-- FORGE-CLAUDE-BOOT:END -->"
FORGE_HOOK_DIR = "/orchestrators/claude-code/hooks/"
CODEX_LABELS = {"tool_label": "Codex", "discovery_label": "Codex"}
CLAUDE_LABELS = {"tool_label": "Claude Code", "discovery_label": "Claude-Code"}
# Host choice -> the executable that shows the assistant is installed.
HOSTS = {"claude-code": "claude", "codex": "codex", "opencode": "opencode"}
# Profile placement (framework/install-profiles.yaml) -> the hosts it has entries for.
PLACEMENT_HOSTS = {"machine": tuple(HOSTS), "project": project_install.PROJECT_HOSTS}


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
    if profile.get("placement") not in PLACEMENT_HOSTS:
        raise ValueError(f"{path}: placement of {name!r} must be one of {', '.join(PLACEMENT_HOSTS)}")
    return profile


def resolve_hosts(chosen: list[str], selection: dict, existing: bool, env) -> tuple[list[str], str]:
    """The hosts to plan and where the choice came from.

    An installation recorded before host choice existed planned every host and
    keeps doing so. Detection reads PATH only: a leftover configuration
    directory is not an installed assistant.
    """
    if chosen:
        names = [name.strip() for value in chosen for name in value.split(",") if name.strip()]
        if not names:
            raise ValueError(f"--host needs a value: {'|'.join(HOSTS)}")
        unknown = sorted(set(names) - set(HOSTS))
        if unknown:
            raise ValueError(f"unknown host: {', '.join(unknown)} (choose from {', '.join(HOSTS)})")
        return [host for host in HOSTS if host in names], "chosen"
    if "hosts" in selection:
        recorded = selection["hosts"]
        if not isinstance(recorded, list) or not recorded or not set(recorded) <= set(HOSTS):
            raise ValueError(f"invalid recorded hosts: {recorded!r}")
        return [host for host in HOSTS if host in recorded], "recorded"
    if existing:
        return list(HOSTS), "existing installation"
    found = [host for host, command in HOSTS.items() if shutil.which(command, path=env.get("PATH", ""))]
    if not found:
        raise InstallConflict(
            "no supported assistant found on PATH ("
            + ", ".join(HOSTS.values())
            + "); choose one or several with --host "
            + "|".join(HOSTS)
        )
    return found, "detected"


# --- the user scope of the big installation (AC-10; framework/user-scope.md) -------------------------

USER_SCOPE_NEEDED = (
    "full-ai-integration keeps your personal context (who you are, how you want to work) in a folder of "
    "your own, and no machine setting names one yet; name it with --user-repo PATH: an existing folder, "
    "or a new one with --create-user-repo (for example --user-repo ~/forge-context --create-user-repo)"
)
# The user-scope convention's scaffold: headings only, nothing personal filled in.
USER_SCOPE_SCAFFOLD = {
    "profile.md": "# Profile\n\n## Who\n\n## Values and priorities\n\n## Constraint defaults\n",
    "navigation.md": "# Navigation\n\n- profile.md\n",
}


def _interactive() -> bool:
    try:
        return sys.stdin.isatty()
    except (AttributeError, ValueError):
        return False


def _ask(prompt: str) -> str:
    sys.stderr.write(prompt)
    sys.stderr.flush()
    line = sys.stdin.readline()
    if not line:
        raise InstallConflict("no answer; " + USER_SCOPE_NEEDED)
    return line.strip()


def ask_user_scope() -> tuple[Path, bool]:
    """The one question of AC-10: an existing folder or a new one, then its path."""
    answer = _ask("Use an existing folder for your personal context, or create a new one? [existing/new] ")
    if answer.lower() not in {"existing", "e", "new", "n"}:
        raise InstallConflict(f"answer existing or new, not {answer!r}")
    create = answer.lower().startswith("n")
    path = _ask("Path of that folder (for example ~/forge-context): ")
    if not path:
        raise InstallConflict("no path given; " + USER_SCOPE_NEEDED)
    return Path(path), create


def plan_user_scope_scaffold(repo: Path) -> InstallPlan | None:
    """A new user repository: the user-scope layout, planned on its own. None for a folder that already
    holds a user scope (a re-run): it is used as it is.

    The scaffold is the person's content from its first write on, so it stays out of the activation
    journal: a journaled file the person then fills in would read as integration drift, and readiness
    (--maintenance status) would stop every session start. Written after the installation applied; an
    interruption leaves at most the folder, which the next run uses as it is."""
    if (repo / "context/user").is_dir():
        print(f"forge install: {repo} already holds context/user/; using it as it is", file=sys.stderr)
        return None
    if repo.exists() and (not repo.is_dir() or any(repo.iterdir())):
        raise InstallConflict(f"--create-user-repo needs a missing or empty folder: {repo}")
    plan = InstallPlan()
    for name, text in USER_SCOPE_SCAFFOLD.items():
        plan.add(repo / "context/user" / name, text.encode(), expected=None)
    return plan


def scaffold_scope(framework: Path, repo: Path, config: Path, skill_links: list[str]) -> UserScope:
    """The scope a new user repository will have once the plan is applied (from_config reads files that
    do not exist yet)."""
    user_dir = repo / "context/user"
    return UserScope(
        configured=True, config_path=str(config), user_repo=str(repo), user_dir=str(user_dir),
        profile=MACHINE_PROFILE, soul=str(forge_soul(framework)), soul_source="forge",
        boot=[str(user_dir / "profile.md")], navigation=str(user_dir / "navigation.md"),
        skill_links=list(skill_links),
    )


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


# The machine setting's keys the installer itself sets: a change to them alone is no difference that needs
# --force-user-config (`profile` moves from a retired name, `maintenance` comes from --coordinated).
INSTALLER_KEYS = ("profile", "maintenance")
COORDINATED = "coordinated"


def rewrite_setting(raw: bytes, current: dict, wanted: dict) -> bytes:
    """The machine setting with only the installer's keys changed: each changed top-level `key: value` line
    is replaced in place (a missing key appended); every other line stays byte for byte. Falls back to a
    whole rewrite when the file's form does not allow that (a key over several lines, flow style)."""
    text = raw.decode("utf-8")
    for key in INSTALLER_KEYS:
        if key not in wanted or current.get(key) == wanted[key]:
            continue
        line = yaml.safe_dump({key: wanted[key]}, sort_keys=False, allow_unicode=True).strip()
        pattern = re.compile(rf"^{re.escape(key)}:[^\n]*$", re.M)
        if key in current:
            text = pattern.sub(lambda _: line, text, count=1)
        else:
            text = (text if text.endswith("\n") or not text else text + "\n") + line + "\n"
    result = text.encode("utf-8")
    try:
        if yaml.safe_load(result) == wanted:
            return result
    except yaml.YAMLError:
        pass
    return yaml.safe_dump(wanted, sort_keys=False, allow_unicode=True).encode()


def plan_user_config(
    plan: InstallPlan, path: Path, data: dict, *, force: bool
) -> None:
    raw = read_file(path)
    if raw is not None:
        try:
            current = yaml.safe_load(raw)
        except yaml.YAMLError:
            current = None
        if isinstance(current, dict):
            # A retired profile name is the profile it moved to, and maintenance follows --coordinated:
            # rewritten in place, no --force-user-config.
            def others(mapping: dict) -> dict:
                return {key: value for key, value in mapping.items() if key not in INSTALLER_KEYS}

            moved = normalize_profile(current.get("profile")) == data.get("profile")
            if moved and others(current) == others(data):
                wanted = dict(current, **{key: data[key] for key in INSTALLER_KEYS if key in data})
                if wanted != current:
                    plan.add(path, rewrite_setting(raw, current, wanted), expected=raw)
                return
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


def coordinated_setting(data: dict | None) -> bool:
    """The machine setting chooses the coordinated maintenance path (`maintenance: coordinated`)."""
    value = data.get("maintenance") if data else None
    if value is not None and value != COORDINATED:
        print(f"forge install: machine setting: maintenance must be {COORDINATED}, ignored: {value!r}",
              file=sys.stderr)
    return value == COORDINATED


def choose_authority(framework: Path, coordinated: bool, head: str | None = None):
    """The machine setting's source authority: the byte snapshot on the coordinated path, the Git commit
    otherwise; a checkout without a commit has nothing to follow and keeps the snapshot. It is the authority
    of an implicit prepare and of a journal without the key (D3). head: the HEAD already read (read here when
    None)."""
    if coordinated or (head or install_activation.source_head(framework)) is None:
        return install_activation.SNAPSHOT
    return install_activation.COMMIT


def _forge_checkout_link(link: Path, name: str) -> bool:
    """A symlink to <some forge checkout>/.claude/<name>."""
    if not link.is_symlink():
        return False
    lexical = Path(os.path.normpath(link.parent / os.readlink(link)))
    return any(
        target.name == name and (target.parent.parent / "agents/buddy/boot.md").is_file()
        for target in (lexical, Path(os.path.realpath(link)))
    )


def plan_daily_claude_removal(
    plan: InstallPlan, claude_root: Path, skill_links: list[str], forge_names: frozenset[str] = frozenset()
) -> list[Path]:
    """daily → full-ai-integration: remove what a daily install owns in ~/.claude.

    Returns forge-created skill links to unlink after apply. Only a Forge-named entry (`forge_names`, the
    manifest, the skill links) changed or of the wrong kind is a conflict; others (the host's synced/) are foreign.
    """
    state = claude_root / ".forge-claude-boot.json"
    _, raw, owned = read_manifest(claude_root)
    if read_file(state) is None and raw is None:
        return []

    def changed(path: Path) -> InstallConflict:
        return InstallConflict(f"a Forge entry was changed outside Forge: {path}; restore it or move it away, then run the install again")

    for name, hashed in sorted(owned.items()):
        current = read_file(claude_root / name)
        if current is not None and digest(current) != hashed:
            raise changed(claude_root / name)
    unmanage_root(plan, claude_root)
    plan_block_removal(plan, claude_root / "CLAUDE.md", state, CLAUDE_START, CLAUDE_END)
    skills_dir = claude_root / "skills"
    if not skills_dir.is_dir() or skills_dir.is_symlink():
        return []
    targets = {os.path.basename(os.path.normpath(t)): t for t in skill_links}
    forge = set(forge_names) | {Path(name).parts[1] for name in owned if Path(name).parts[0] == "skills"}
    links = []
    for entry in sorted(skills_dir.iterdir()):
        if entry.name in targets:
            if not entry.is_symlink() or os.path.realpath(entry) != os.path.realpath(targets[entry.name]):
                raise changed(entry)
            links.append(entry)
        elif entry.name in forge:
            if entry.is_symlink() or not entry.is_dir():
                raise changed(entry)
            for path in sorted(entry.rglob("*")):
                if not path.is_dir() and str(path.relative_to(claude_root)) not in owned:
                    raise changed(path)
    return links


def source_inventory(framework: Path, closure: list[str]) -> list[Path]:
    """Actual bytes, including local edits and old routes, not Git HEAD.

    Foreign-owned children of the shared `.claude/skills/` root are not Forge
    source and stay out of the recoverable baseline.
    """
    try:
        from .capability_closure import owned_tree
    except ImportError:
        from capability_closure import owned_tree
    paths = set()
    roots = [framework / rel for rel in closure]
    roots += [framework / name for name in ("scripts", "framework", "workflows", "agents", "skills", "orchestrators", ".claude")]
    roots += [framework / name for name in ("AGENTS.md", "CLAUDE.md", "intent.md")]
    for root in roots:
        if root.is_file() or root.is_symlink():
            paths.add(root)
        elif root.is_dir():
            paths.update(p for p in owned_tree(framework, root) if (p.is_file() or p.is_symlink()) and "__pycache__" not in p.parts and ".git" not in p.parts)
    return sorted(paths)


def commit_observation(transaction, framework: Path, inventory=None, data=None) -> dict:
    """Installed sources Git reports as not committed in HEAD (status key).

    Covers the journal's recorded sources and the current source inventory;
    callers pass what they already loaded. Observation only: never changes
    phase, reason or readiness; any failure becomes
    ``uncommitted_sources_unavailable``.
    """
    try:
        recorded = (data if data is not None else transaction._load())["sources"]
        if inventory is None:
            inventory = source_inventory(framework, [])
        paths = sorted(set(recorded) | {str(Path(p).absolute()) for p in inventory})
        _, uncommitted, reason = install_activation.uncommitted_sources(transaction.root, paths)
    except Exception as exc:
        reason = f"{type(exc).__name__}: {exc}"
    if reason is not None:
        return {"uncommitted_sources_unavailable": reason}
    return {"uncommitted_sources": uncommitted}


# Exact source bytes from the immediately preceding installed generation. Only
# the installation root substitution is normalized; user edits remain conflicts.
PREDECESSOR_LAUNCHER_HASHES = {
    "cc": "ca12a48770763ff66aa5ce99615924de790223d0b9bf6aeed02dace4bf4da7ca",
    "oc": "58587bfd8a3715907e54711ad4c2967e62a90b0ad12cd7facd801f537f896cdf",
}


# ~/.local/bin/cc and oc: the same bytes for every commit of one checkout (design note §4, references instead
# of copies).
LAUNCHER_STUB = (
    "#!/usr/bin/env bash\n"
    "# Forge's {} launcher: runs the checkout's own (written by scripts/forge_install.py).\n"
    'exec {} "$@"\n'
)
CC_STUB = LAUNCHER_STUB.replace("{}", "Claude Code", 1)


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
    for name in ('pre-commit', 'commit-msg', 'pre-merge-commit'):
        target = hookdir / name
        effective = git('rev-parse', '--path-format=absolute', '--git-path', 'hooks/' + name)
        if effective.returncode or Path(effective.stdout.strip()).resolve() != target.resolve():
            raise ValueError('framework Git hook routing conflict: ' + name)
        paths.append(target)
    return paths


def existing_installation(selection_raw, home: Path, codex_home: Path, agents_home: Path) -> bool:
    """Forge entries are on this machine. A rolled-back first install leaves none
    (its journal remains); one from before the state record has its manifests."""
    markers = (
        codex_home / ".forge-codex-boot.json",
        home / ".claude/.forge-claude-boot.json",
        home / ".claude/.forge-managed.json",
        home / ".local/bin/.forge-managed.json",
        agents_home / "skills/.forge-managed.json",
    )
    return selection_raw is not None or any(marker.exists() for marker in markers)


def machine_forge_hosts(home: Path, codex_home: Path, agents_home: Path) -> set[str]:
    """The hosts the machine-wide installation serves on this machine (read only, nothing written).

    Claude Code: its boot hook in ~/.claude/settings.json, its links, or a daily installation's state;
    Codex: ~/.codex/.forge-codex-boot.json or its skill manifest; OpenCode: its launcher. selection.json adds
    its recorded hosts, or every host when it records none (an installation from before host choice)."""
    hosts: set[str] = set()
    raw = read_file(home / ".local/state/forge/selection.json")
    if raw is not None:
        try:
            recorded = json.loads(raw).get("hosts")
        except (ValueError, AttributeError):
            recorded = None
        hosts |= set(recorded) & set(HOSTS) if isinstance(recorded, list) else set(HOSTS)
    try:
        settings = json.loads(read_file(home / ".claude/settings.json") or b"{}")
        groups = settings.get("hooks", {}).get("SessionStart", []) if isinstance(settings, dict) else []
        commands = [hook.get("command", "") for group in groups for hook in group.get("hooks", [])]
    except (ValueError, AttributeError, TypeError):
        commands = []
    if any(FORGE_HOOK_DIR + "buddy-boot-inject.sh" in command and "--project" not in command
           for command in commands) or any(
            _forge_checkout_link(home / ".claude" / name, name) for name in ("skills", "agents")) or any(
            (home / ".claude" / name).exists() for name in (".forge-claude-boot.json", ".forge-managed.json")):
        hosts.add("claude-code")
    if (codex_home / ".forge-codex-boot.json").exists() or (agents_home / "skills/.forge-managed.json").exists():
        hosts.add("codex")
    if (home / ".local/bin/.forge-managed.json").exists():
        try:
            launchers = read_manifest(home / ".local/bin")[2]
            hosts |= {host for host, name in (("claude-code", "cc"), ("opencode", "oc")) if name in launchers}
        except InstallConflict:
            hosts |= set(HOSTS)  # an unreadable manifest: assume every host
    return hosts


def served_hosts(profile: dict) -> set[str]:
    """Hosts the profile has entries for, by its placement."""
    return set(PLACEMENT_HOSTS[profile["placement"]])


def claude_settings_template(framework: Path) -> dict:
    """The machine install's part of ~/.claude/settings.json: the template with the checkout path in each
    hook command shell-quoted (a path with a space or a quote stays one word), then JSON-escaped."""
    quoted = json.dumps(shlex.quote(str(framework)))[1:-1]
    text = (framework / "orchestrators/claude-code/settings.json.template").read_text()
    return json.loads(text.replace("__FRAMEWORK_DIR__", quoted))


def plan_full_hosts(plan, framework, home, scope, modes, hosts):
    """Host planning uses read-only Git resolution; mutation belongs to activation."""
    if isinstance(hosts, str):
        raise TypeError("hosts is a collection of host names, not a string")
    links = []
    launchers = {}
    for name, adapter, label in (("cc", "claude-code", "Claude Code"), ("oc", "opencode", "OpenCode")):
        if adapter not in hosts:
            continue
        # A fixed stub: the checkout's launcher runs, so a pull reaches it without a re-render.
        launchers[name] = LAUNCHER_STUB.format(label, shlex.quote(str(framework / f"orchestrators/{adapter}/bin/{name}")))
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
    if "claude-code" in hosts:
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
        template = claude_settings_template(framework)
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
                    cause = ""
                    if (root / ".forge-project.json").exists():
                        cause = (f"; a project install in {home} owns it (~/.claude/.forge-project.json): "
                                 f"remove it with forge_install.py --remove {home}, then run this again")
                    raise ValueError(f"unowned Claude host directory: {link}{cause}")
            else:
                links.append((link, str(target)))
    if "opencode" in hosts:
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
    # An explicit prepare is the coordinated path's: snapshot by argument, whatever the setting says.
    transaction.prepare(source_inventory(framework, []), sorted(targets), authority=install_activation.SNAPSHOT,
                        consumer_roots=consumer_roots)
    data = transaction._load()
    data["compatibility"] = install_activation.workflow_compatibility(data)
    transaction._save(data)
    return transaction.status()


# Flags that only the machine-wide installation (--profile full-ai-integration) knows.
MACHINE_ONLY = ("--user-repo", "--skill-link", "--force-user-config", "--create-user-repo", "--coordinated",
                "--method", "--methods", "--migrate-legacy", "--consumer-root", "--maintenance")
EPILOG = """examples:
  forge_install.py ~/my-app                 install Forge into ~/my-app only (the default)
  forge_install.py --check ~/my-app         show what that would write, write nothing
  forge_install.py --remove ~/my-app        take the project install out of ~/my-app again
  forge_install.py --profile full-ai-integration --user-repo ~/forge-context --create-user-repo
                                            Buddy in every session; your context in a new ~/forge-context
  forge_install.py --profile full-ai-integration --user-repo ~/notes
                                            the same with an existing folder for your context
  forge_install.py --profile full-ai-integration --remove
                                            take the machine-wide installation out again
"""


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="forge_install.py", description=__doc__.splitlines()[0], epilog=EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--profile", metavar="|".join(PROFILES),
        help="project (the default): Forge in the named project only, nothing else on the machine "
             "changes; full-ai-integration: Buddy in every session of this machine, with knowledge "
             "and continuity across projects")
    parser.add_argument("--host", action="append", default=[], metavar="|".join(HOSTS),
                        help="assistant to install for; repeat or comma-separate for several "
                             "(default: the ones found on PATH)")
    parser.add_argument("--check", action="store_true", help="list the paths an install would change; write nothing")
    parser.add_argument("--remove", nargs="?", const="", default=None, metavar="PROJECT",
                        help="--remove PROJECT: remove the project install from PROJECT; --profile "
                             "full-ai-integration --remove: remove the machine-wide installation. Either takes "
                             "out only what it wrote and you did not change")
    parser.add_argument("--refresh", nargs="?", const="", default=None, metavar="PROJECT",
                        help="bring the installed entries up to the checkout's commit after a git pull (the "
                             "session start runs it); with PROJECT, that project's install. It skips with one "
                             "line when there is nothing it may do and exits 2 on a conflict; a session start "
                             "never fails on it (the hooks, cc and oc ignore its exit code)")
    machine = parser.add_argument_group("full-ai-integration only")
    machine.add_argument("--user-repo", type=Path, metavar="PATH",
                         help="the folder that holds your personal context (context/user/), e.g. ~/forge-context")
    machine.add_argument("--create-user-repo", action="store_true",
                         help="create --user-repo PATH with the user-scope layout when it is missing or empty")
    machine.add_argument("--skill-link", type=Path, action="append", default=None, metavar="PATH",
                         help="link one of your own skill folders next to Forge's; repeatable")
    machine.add_argument("--force-user-config", action="store_true",
                         help="replace a differing machine setting")
    machine.add_argument("--coordinated", action="store_true",
                         help="record maintenance: coordinated in the machine setting (a developer checkout: "
                              "changes go through --maintenance prepare and validate); kept on later installs")
    machine.add_argument("--maintenance", choices=["prepare", "status", "retry", "rollback", "validate"],
                         help="coordinated maintenance of the machine installation")
    machine.add_argument("--operation-id")
    machine.add_argument("--require-ready", action="store_true")
    machine.add_argument("--validation-operation")
    machine.add_argument("--validation-evidence", type=Path)
    machine.add_argument("--consumer-root", type=Path, action="append", default=[])
    machine.add_argument("--method", action="append", default=[])
    machine.add_argument("--methods", default="")
    machine.add_argument("--migrate-legacy", action="store_true")
    parser.add_argument(
        "projects", nargs="*", type=Path, metavar="PROJECT",
        help="the project to install into; with --profile full-ai-integration, projects that get a "
             "Codex AGENTS.md boot block")
    return parser


def _given(args: argparse.Namespace, flag: str) -> bool:
    value = getattr(args, flag[2:].replace("-", "_"))
    return value not in (None, False, [], "")


def _finish(result: dict, scaffold: InstallPlan | None) -> int:
    """Print the installation's state; write a new user repository's scaffold after it applied."""
    if scaffold is not None and scaffold.changes():
        scaffold.apply()
        created = sorted({path.parent for path in scaffold.files})
        print(f"forge install: created {', '.join(map(str, created))} (profile.md, navigation.md)", file=sys.stderr)
    print(json.dumps(result, sort_keys=True))
    return 0


def _main(args: argparse.Namespace, parser: argparse.ArgumentParser, *, framework: Path = FRAMEWORK) -> int:
    """The machine-wide installation (full-ai-integration) and its maintenance."""
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
        coordinated = args.coordinated or coordinated_setting(data)
        # HEAD, read once before planning: the commit an implicit prepare records is the one planned from.
        head = install_activation.source_head(framework)
        authority = choose_authority(framework, coordinated, head)
        transaction = install_activation.Activation(framework, install_activation.journal_path(home),
                                                    default_authority=authority)
        if _removal_interrupted(home) and args.maintenance != "status":
            raise ValueError(REMOVAL_INTERRUPTED)
        if args.maintenance in {"status", "retry", "rollback", "validate"}:
            if args.check and args.maintenance != "status":
                raise ValueError("--check cannot mutate maintenance state")
            if args.validation_operation and args.maintenance != "status":
                raise ValueError('--validation-operation requires maintenance status')
            if args.maintenance == "status":
                result = (transaction.validation_status(args.validation_operation, compatibility=install_activation.workflow_compatibility)
                          if args.validation_operation else transaction.status())
                inventory = journal = None
                if not args.validation_operation and result["phase"] in install_activation.TERMINAL:
                    # Readiness also sees new sources the terminal journal never recorded.
                    inventory, journal = source_inventory(framework, []), transaction._load()
                    reason, accepted = transaction.unrecorded(journal, inventory)
                    if reason:
                        result["phase"] = "recovery_required"
                        result["reason"] = reason
                    elif accepted:
                        result["instruction_drift"] = sorted(set(result.get("instruction_drift", [])) | {
                            str(Path(p).relative_to(transaction.root)) for p in accepted})
                if not args.validation_operation and result["phase"] != "unprepared":
                    # Held-back work: installed but not committed (warning, not a block).
                    result.update(commit_observation(transaction, framework, inventory, journal))
                    # After every phase override: is an operation open for its owner?
                    result["operation_open"] = result["phase"] in install_activation.OPERATION_OPEN
                if _removal_interrupted(home):
                    result.update(phase="recovery_required", reason=REMOVAL_INTERRUPTED)
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
            # A new baseline may stack on an uncommitted generation: warn, never refuse.
            # The prepared journal already records the current source inventory.
            result.update(commit_observation(transaction, framework, inventory=()))
            print(json.dumps(result, sort_keys=True))
            return 0

        if not args.check and args.maintenance != "prepare":
            state = transaction.status()
            if state["phase"] in {"applying", "recovery_required"}:
                if state.get("reason") and not state.get("next_start_completes"):
                    raise ValueError(state["reason"])
                result = transaction.retry(compatibility=install_activation.workflow_compatibility)
                if result["phase"] != "prepared":
                    print(json.dumps(result, sort_keys=True))
                    return 0
                state = result
            if state["phase"] == "prepared":
                transaction.seal_updated_sources(source_inventory(framework, []))
        # Recorded names are read through the one alias rule (full, daily -> full-ai-integration).
        file_profile = data.get("profile") if data else None
        recorded_profile = normalize_profile(file_profile) if file_profile is not None else None
        selection = home / ".local/state/forge/selection.json"
        selection_raw = read_file(selection)
        installed_selection = json.loads(selection_raw) if selection_raw else {}
        unusable = unusable_setting(env)
        if unusable and args.user_repo is None:
            raise InstallConflict(
                f"machine setting unusable ({unusable}); fix it, or pass "
                "--user-repo PATH --force-user-config to rewrite it"
            )
        profile_name = MACHINE_PROFILE
        if file_profile is not None and recorded_profile != profile_name and args.user_repo is None:
            raise InstallConflict(
                f"--profile {profile_name} differs from {cfg} (profile: {file_profile}); "
                "pass --user-repo to rewrite the machine setting"
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
        if args.user_repo is None and cfg is not None and not (cfg.exists() or cfg.is_symlink()):
            # AC-10: no machine setting names a user scope yet. Ask once on a terminal; never in --check or
            # in a session-start refresh.
            if args.check or args.refresh is not None or not _interactive():
                raise InstallConflict(USER_SCOPE_NEEDED)
            args.user_repo, args.create_user_repo = ask_user_scope()
        existing = existing_installation(selection_raw, home, codex_home, agents_home)
        hosts, origin = resolve_hosts(args.host, installed_selection, existing, env)
        print(f"forge install: hosts: {', '.join(hosts)} ({origin})", file=sys.stderr)
        if not served_hosts(profile) & set(hosts):
            raise InstallConflict(
                f"profile {profile_name} has no entry for {', '.join(hosts)}; choose with --host "
                + "|".join(host for host in HOSTS if host in served_hosts(profile))
            )
        dropped = [host for host in installed_selection.get("hosts", list(HOSTS) if existing else []) if host not in hosts]
        if dropped:
            print(f"forge install: entries for {', '.join(dropped)} stay in place (no removal)", file=sys.stderr)
        # The Codex projects of every machine install so far plus the ones named now: each refresh re-renders
        # their blocks (C-008). A recorded project that is gone is dropped with one line.
        # Each records whether Forge created its AGENTS.md ("created") or found one ("existing"), for the removal.
        recorded_projects = {}
        for name, origin_of in (installed_selection.get("projects") or {}).items():
            if Path(name).is_dir():
                recorded_projects[name] = origin_of
            else:
                print(f"forge install: recorded Codex project is gone, dropped: {name}", file=sys.stderr)
        for named in args.projects:
            name = os.path.abspath(named)
            if name not in recorded_projects:
                recorded_projects[name] = "existing" if (Path(name) / "AGENTS.md").exists() else "created"
        projects = [Path(name) for name in sorted(recorded_projects)] if "codex" in hosts else []
        if args.projects and not projects:
            print("forge install: project entries are Codex AGENTS.md blocks; skipped without --host codex", file=sys.stderr)

        plan = InstallPlan()
        scaffold: InstallPlan | None = None
        selected = {"profile": profile_name, "methods": selected_methods}
        if origin != "existing installation":
            selected["hosts"] = hosts
        if projects:
            selected["projects"] = recorded_projects
        if "claude-code" in hosts:
            # For the removal: did this install create each Git hook link and ~/.claude/settings.json? A recorded
            # origin never changes; no record (an install before it) counts as "existing", which stays.
            hook_links = dict(installed_selection.get("hooks") or {})
            for target in framework_git_hooks(framework):
                hook_links.setdefault(str(target), "existing" if os.path.lexists(target) else "created")
            if hook_links:
                selected["hooks"] = hook_links
            if installed_selection.get("settings") == "created" or not (claude_root / "settings.json").exists():
                selected["settings"] = "created"
        desired_selection = (json.dumps(selected, sort_keys=True) + "\n").encode()
        plan.add(selection, desired_selection, expected=read_file(selection))
        if args.user_repo is not None:
            if cfg is None:
                raise ValueError("cannot locate the machine setting (HOME unset)")
            repo = Path(os.path.abspath(args.user_repo.expanduser()))
            if args.create_user_repo:
                scaffold = plan_user_scope_scaffold(repo)
            elif not repo.is_dir():
                raise ValueError(f"--user-repo is not a directory: {repo} (create a new one with --create-user-repo)")
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
            if coordinated:
                data["maintenance"] = COORDINATED  # set by --coordinated, else carried over
            cfg_warnings = []
            plan_user_config(plan, cfg, data, force=args.force_user_config)
        elif data and file_profile is not None and file_profile != profile_name and recorded_profile == profile_name:
            # A retired profile name in the machine setting is rewritten, that key only.
            raw = read_file(cfg)
            if raw is not None:
                plan.add(cfg, rewrite_setting(raw, data, dict(data, profile=profile_name)), expected=raw)
        if scaffold is not None:
            scope = scaffold_scope(framework, repo, cfg, data["skill_links"])
        else:
            scope = from_config(framework, data, config=cfg, warnings=cfg_warnings)
        for warning in scope.warnings:
            print(f"forge install: user scope warning: {warning}", file=sys.stderr)

        claude_host = "claude-code" in hosts
        links: list[tuple[Path, str]] = []
        if "codex" in hosts:
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
        if claude_host:
            # A daily installation's ~/.claude surfaces give way to the machine-wide ones.
            per_skill = (claude_root / "skills").is_dir() and not (claude_root / "skills").is_symlink()
            claude = select_skills(framework, profile, CLAUDE_LABELS) if per_skill else {}
            stale_links = plan_daily_claude_removal(plan, claude_root, scope.skill_links, frozenset(claude))
            # Existing managed daily directories remain hash-owned directories.
            # Upgrade their contents without an unsafe directory-to-link swap.
            if per_skill:
                for path in list(plan.files):
                    if path == claude_root / ".forge-managed.json" or path.is_relative_to(claude_root / "skills"):
                        del plan.files[path]
                managed_files(plan, claude_root, {f"skills/{name}/SKILL.md": content for name, content in claude.items()})
        modes = {}
        if claude_host or "opencode" in hosts:
            # Host plans share the same preflight, journal and source generation.
            links += plan_full_hosts(plan, framework, home, scope, modes, hosts)
        if projects:
            try:
                from .generate_codex_agents import plan_boot
            except ImportError:
                from generate_codex_agents import plan_boot
            for project in projects:
                if not project.is_dir():
                    raise ValueError(f"project directory missing: {project}")
                plan_boot(plan, project, framework, scope=None, profile=profile_name)
                plan_hook_cleanup(plan, project / ".codex", framework)

        changes = plan.changes()
        pending = [str(path) for path in changes]
        pending += [str(link) for link, _ in links] + [str(p) for p in stale_links]
        if args.check:
            for path in pending + [str(path) for path in (scaffold.changes() if scaffold else [])]:
                print(path)
            return int(bool(pending or scaffold))

        source_paths = source_inventory(framework, closure)
        targets = [*plan.files, *(p for p, _ in links), *stale_links]
        if claude_host:
            targets.extend(framework_git_hooks(framework))
        state = transaction.status()
        if state["phase"] == "complete" and not pending:
            data = transaction._load()
            # By the journal's source authority (snapshot: instruction Markdown drift between operations is
            # accepted; other source drift and every integration target stay strict).
            recorded = transaction.authority_of(data)
            refusal = recorded.install_drift(transaction, data, source_paths)
            if refusal:
                raise ValueError(refusal)
            if not recorded.behind(transaction, data, head):
                return _finish(state, scaffold)
            # A commit journal behind HEAD: a new operation records the commit the entries now follow.
        if state["phase"] in {"unprepared", "complete", "rolled_back"}:
            # The setting's authority (an implicit prepare), recorded once, with the HEAD planned from.
            transaction.prepare(source_paths, targets, authority=authority, consumer_roots=args.consumer_root,
                                closure=closure, source_commit=head)
        elif state["phase"] == "validation_pending":
            data = transaction._load()
            transaction._check(data, integration=True, source=True)
            if pending:
                raise ValueError("activation awaits validation; validate or rollback before another change")
            return _finish(state, scaffold)
        result = transaction.apply(plan, [*( (p, None) for p in stale_links), *links],
                                   source_paths=source_paths, modes=modes,
                                   compatibility=install_activation.workflow_compatibility, closure=closure)
        return _finish(result, scaffold)
    except ApplyFailure as exc:
        print(f"forge install: {exc}", file=sys.stderr)
        return 3
    except (OSError, ValueError, yaml.YAMLError) as exc:
        print(f"forge install: conflict: {exc}", file=sys.stderr)
        return 2


def _project_preflight(framework: Path, env, *, closure: bool) -> set[str]:
    """The project path's one preflight (install, check, refresh; remove without the closure): the checkout
    holds what the entry names (a sparse checkout fails here, nothing written), HOME is absolute, and the
    hosts the machine-wide installation serves."""
    if closure:
        try:
            from .capability_closure import compose_profile, validate_closure
        except ImportError:
            from capability_closure import compose_profile, validate_closure
        composed = compose_profile(framework, load_profile(framework, PROJECT_PROFILE), [])
        validate_closure(framework, composed)
        check_required_paths(framework, composed)
    home = Path(env.get("HOME") or "")
    if not str(home) or not home.is_absolute():
        raise ValueError("HOME must be an absolute path")
    return machine_forge_hosts(home, Path(env.get("CODEX_HOME") or home / ".codex"),
                               Path(env.get("AGENTS_HOME") or home / ".agents"))


def _project(args: argparse.Namespace, parser: argparse.ArgumentParser, framework: Path) -> int:
    """The project install: dispatched before the machine lock, it reads no machine setting and writes
    only into the project (scripts/project_install.py)."""
    for flag in MACHINE_ONLY:
        if _given(args, flag):
            parser.error(f"{flag} belongs to --profile full-ai-integration, not to the project install")
    if args.remove is not None:
        named = [args.remove] if args.remove else [str(p) for p in args.projects]
        if len(named) != 1:
            parser.error("--remove takes one PROJECT (the machine-wide installation: "
                         "--profile full-ai-integration --remove)")
        project = Path(named[0])
    elif len(args.projects) != 1:
        parser.error(
            "name one PROJECT to install Forge into (forge_install.py PROJECT), "
            "or choose --profile full-ai-integration for Buddy in every session of this machine")
    else:
        project = args.projects[0]
    env = os.environ
    try:
        if args.remove is None:
            project_install.refuse_user_scope(project)
        machine = _project_preflight(framework, env, closure=args.remove is None)
        hosts: list[str] = []
        if args.remove is None:
            _, record = project_install.read_record(Path(os.path.realpath(project)))
            recorded = {"hosts": record["hosts"]} if record and record.get("hosts") else {}
            hosts, origin = resolve_hosts(args.host, recorded, False, env)
            # Only the hosts the project install has entries for (K4); none left: the refusal names them.
            served = [host for host in hosts if host in project_install.PROJECT_HOSTS]
            if served:
                print(f"forge install: hosts: {', '.join(served)} ({origin})", file=sys.stderr)
    except (OSError, ValueError) as exc:
        print(f"forge install: conflict: {exc}", file=sys.stderr)
        return 2
    return project_install.run(project, framework, hosts=hosts, check=args.check,
                               remove=args.remove is not None, machine_hosts=machine)


# The open operation (P, A, V) a machine removal refuses, and the step that finishes or undoes it.
OPEN_STEPS = {
    "prepared": "finish it with forge_install.py --profile full-ai-integration, or roll it back with "
                "--maintenance rollback",
    "applying": "complete it with --maintenance retry, or roll it back with --maintenance rollback",
    "recovery_required": "complete it with --maintenance retry, or roll it back with --maintenance rollback",
    "validation_pending": "validate it (--maintenance validate) or roll it back with --maintenance rollback",
}


def _owned_keys_removal(plan: InstallPlan, path: Path, recorded: dict | None, *, created: bool = False) -> None:
    """Take Forge's part out of a shared file it merged into (~/.claude/settings.json: the hooks key; the
    machine setting: the installer's keys); every other key stays. A Forge part that differs from what the
    install wrote is a conflict, an absent one counts as removed."""
    raw = read_file(path)
    if raw is None or recorded is None:
        return
    current, empty = owned_part(path, raw), owned_part(path, None)
    if current == empty:
        return
    written = base64.b64decode(recorded["bytes"]) if recorded["kind"] == "file" else None
    if current != owned_part(path, written):
        raise InstallConflict(f"a Forge entry was changed outside Forge: {path} (the Forge part of it); restore "
                              "it or remove it by hand, then run the removal again")
    if path.suffix == ".json":
        data = json.loads(raw)
        data.pop("hooks", None)  # a file the install created goes when nothing else is left
        plan.add(path, None if created and not data else (json.dumps(data, indent=2) + "\n").encode(), expected=raw)
        return
    lines, keep = raw.decode("utf-8").splitlines(keepends=True), []
    dropping = False
    for line in lines:
        key = re.match(r"^([A-Za-z_][\w-]*):", line)
        if key or not line[:1].isspace() and not line.startswith("-"):
            dropping = bool(key) and key.group(1) in ("version", "user_repo", "profile", "skill_links")
        if not dropping:
            keep.append(line)
    rest = "".join(keep)
    plan.add(path, rest.encode() if rest.strip() else None, expected=raw)


REMOVAL_INTERRUPTED = ("a removal was interrupted; run forge_install.py --profile full-ai-integration --remove "
                       "again")


def _removal_interrupted(home: Path) -> bool:
    """A machine removal started and has not finished: selection.json carries its marker."""
    try:
        return bool(json.loads(read_file(home / ".local/state/forge/selection.json") or b"{}").get("removing"))
    except (ValueError, AttributeError):
        return False


def _block_removal(plan: InstallPlan, path: Path, state: Path, start: str, end: str, recorded: dict | None,
                   *, keep_file: bool = False) -> None:
    """A boot block's removal by its state file, or, with the state file gone, by the block the journal
    recorded (R-3b)."""
    if read_file(state) is not None or recorded is None or recorded["kind"] != "file":
        plan_block_removal(plan, path, state, start, end, keep_file=keep_file)
        return
    owned = owned_part(path, base64.b64decode(recorded["bytes"])) or ""
    if owned.startswith("block:") and owned != "block:none":
        plan_text_block_removal(plan, path, start, end, owned[len("block:"):], keep_file=keep_file)


def _remove_machine(args: argparse.Namespace, framework: Path) -> int:
    """`--profile full-ai-integration --remove`: take out exactly what the machine installation wrote, read
    from its records (journal, selection.json, the manifests): the owned files and their manifests, the boot
    blocks and their state, the hook entries in ~/.claude/settings.json, the links (Claude, user skill links,
    the checkout's Git hook links the install created), the setting's installer keys, then selection.json and
    the journal, last. Files the journal recorded that no manifest covers go too. The user-scope folder and
    the checkout's tracked content stay. In each recorded Codex project an intact Forge block is taken out
    (the file only when Forge created it); a changed one stays, is named, and the exit is 1. selection.json
    carries a marker while it runs, so an interrupted removal is named and a rerun converges. Under the
    machine lock; --check lists the removal and writes nothing."""
    env = os.environ
    home = Path(env.get("HOME") or "")
    if not str(home) or not home.is_absolute():
        raise ValueError("HOME must be an absolute path")
    codex_home = safe_path(Path(env.get("CODEX_HOME") or home / ".codex"))
    agents_home = safe_path(Path(env.get("AGENTS_HOME") or home / ".agents"))
    cfg = config_path(env)
    setting = load_config(cfg)[0] if cfg is not None else None
    transaction = install_activation.Activation(
        framework, install_activation.journal_path(home),
        default_authority=choose_authority(framework, coordinated_setting(setting)))
    journal = transaction._load()
    if not journal:
        print("forge install: nothing installed (no machine installation journal)", file=sys.stderr)
        return 0
    phase = "applying" if transaction.status().get("journal_transition_pending") else journal["phase"]
    if phase in OPEN_STEPS:
        raise ValueError(f"an installation operation is open ({phase}); {OPEN_STEPS[phase]}, then remove")
    if any(".." in Path(name).parts for name in journal["actions"]):
        raise InstallConflict("the installation journal names a path with '..'; nothing removed")
    direction = "before" if journal["phase"] == "rolled_back" else "after"
    recorded = {os.path.abspath(path): item.get(direction, item["before"])
                for path, item in journal["actions"].items()}
    created = {os.path.abspath(path) for path, item in journal["actions"].items() if item["before"]["kind"] == "absent"}
    manifest_roots = [codex_home / "agents", agents_home / "skills", home / ".claude", home / ".local/bin",
                      *([cfg.parent] if cfg is not None else [])]
    machine_roots = [*manifest_roots, codex_home, agents_home, home / ".local/state/forge"]
    try:
        hooks = set(framework_git_hooks(framework))
    except ValueError:
        hooks = set()

    def under(path: Path, roots) -> bool:
        return any(path.is_relative_to(root) for root in roots)

    selection = home / ".local/state/forge/selection.json"
    origins = json.loads(read_file(selection) or b"{}")
    plan = InstallPlan()
    for root in manifest_roots:
        unmanage_root(plan, root)
    _block_removal(plan, codex_home / "AGENTS.md", codex_home / ".forge-codex-boot.json", CODEX_START, CODEX_END,
                   recorded.get(str(codex_home / "AGENTS.md")))
    _block_removal(plan, home / ".claude/CLAUDE.md", home / ".claude/.forge-claude-boot.json", CLAUDE_START,
                   CLAUDE_END, recorded.get(str(home / ".claude/CLAUDE.md")))
    plan_hook_cleanup(plan, codex_home, framework)
    settings = home / ".claude/settings.json"
    for path in (settings, cfg):
        if path is not None:
            made = str(path) in created or origins.get("settings") == "created"
            _owned_keys_removal(plan, path, recorded.get(str(path)), created=path == settings and made)
    projects = dict(origins.get("projects") or {})
    for name in recorded:
        if Path(name).name == "AGENTS.md" and not under(Path(name), machine_roots):
            projects.setdefault(str(Path(name).parent), "existing")
    # Files the journal recorded that no manifest covered (a manifest or state file deleted by hand).
    for name, wanted in recorded.items():
        path = Path(name)
        walked = under(path, manifest_roots) or path.name.startswith(".forge-") and (
            under(path, machine_roots) or str(path.parent) in projects)
        if wanted["kind"] != "file" or path in plan.files or owned_part(path, None) is not None or not walked \
                or path.name in ("hooks.json", ".forge-project.json"):
            continue
        current = install_activation.identity(path)
        if current["kind"] != "absent" and current != wanted:
            raise InstallConflict(f"changed since the install: {path}; restore it or remove it by hand")
        if current == wanted:
            plan.add(path, None, expected=base64.b64decode(current["bytes"]))
    links = []
    for name, wanted in recorded.items():
        path = Path(name)
        if wanted["kind"] != "link":
            continue
        if not (path in hooks or under(path, machine_roots)):
            raise InstallConflict(f"the installation journal names a link outside Forge's folders: {path}")
        if path in hooks and name not in created and (origins.get("hooks") or {}).get(name) != "created":
            continue  # a hook link that was there before the install (or with no record) stays
        current = install_activation.identity(path)
        if current != wanted and current["kind"] != "absent":
            raise InstallConflict(f"changed since the install: {path}; restore it or remove it by hand")
        if current == wanted:
            links.append(path)
    kept = []
    for name, origin_of in sorted(projects.items()):
        project = Path(name)
        part = InstallPlan()
        try:
            _block_removal(part, project / "AGENTS.md", project / ".forge-codex-boot.json", CODEX_START, CODEX_END,
                           recorded.get(str(project / "AGENTS.md")), keep_file=origin_of != "created")
        except InstallConflict:
            kept.append(project / "AGENTS.md")
            continue
        for path, (old, new) in part.files.items():
            plan.add(path, new, expected=old)
    changes = plan.changes() + links + [selection, transaction.journal]
    if args.check:
        for path in changes:
            print(path)
    for path in kept:
        print(f"forge install: Forge's block in {path} was changed, so it stays: delete the lines from "
              f"{CODEX_START} to {CODEX_END} by hand", file=sys.stderr)
    if args.check:
        return 1
    if selection.exists():  # the marker: an interruption from here on is named, and a rerun converges
        install_activation.replace_identity(selection, install_activation.file_identity(
            json_bytes(dict(origins, removing=True)), 0o644))
    plan.apply()
    for path in links:
        path.unlink()
    selection.unlink(missing_ok=True)
    transaction.journal.unlink(missing_ok=True)
    prune_empty_dirs([path for path in [*changes, *map(Path, recorded)] if under(path, machine_roots)], [home])
    print(f"forge install: removed the machine installation ({len(changes)} paths); the user-scope folder, "
          "projects' own text and the checkout stay", file=sys.stderr)
    return 1 if kept else 0


def _skip(reason: str) -> int:
    """A refresh that may not run: one line on stderr, exit 0 (a refresh never fails a start)."""
    print(f"forge install: refresh skipped: {reason}", file=sys.stderr)
    print(json.dumps({"refresh": "skipped", "reason": reason}, sort_keys=True))
    return 0


def _served_parts(home: Path, env, cfg: Path | None) -> set[str]:
    """The shared targets the recorded selection still renders: its hosts' (every host when none is recorded)
    and its still-existing Codex projects'; a dropped host's file is no absent part (V-2)."""
    selection = json.loads(read_file(home / ".local/state/forge/selection.json") or b"{}")
    hosts = selection.get("hosts") or list(HOSTS)
    served = {str(cfg)} if cfg is not None else set()
    if "claude-code" in hosts:
        served |= {str(home / ".claude/settings.json"), str(home / ".claude/CLAUDE.md")}
    if "codex" in hosts:
        served.add(str(Path(env.get("CODEX_HOME") or home / ".codex") / "AGENTS.md"))
        served |= {str(Path(name) / "AGENTS.md") for name in selection.get("projects") or {} if Path(name).is_dir()}
    return served


def _refresh_machine(parser: argparse.ArgumentParser, framework: Path) -> int:
    """`--refresh`: after a pull, re-plan the recorded machine installation and apply it (design note §4).

    A no-op after one `git rev-parse HEAD` when the journal's source_commit is HEAD. Skips (exit 0) with no
    journal, a journal of another checkout, the snapshot authority or maintenance: coordinated (the
    developer path), a held lock, uncommitted tracked non-Markdown sources, or a Forge entry changed outside
    Forge. Under the commit authority it completes what a pull, a crash or an interrupted start left: a
    prepared operation is sealed and applied, an interrupted one retried (also after further pulls), and a
    journal behind HEAD (one without source_commit included) re-planned. A conflict exits 2."""
    env = os.environ
    home = Path(env.get("HOME") or "")
    if not str(home) or not home.is_absolute():
        return _skip("HOME must be an absolute path")
    try:
        journal = install_activation.journal_path(home)
        if not (journal.exists() or (install_activation.LOCK_ROOT / "active.json").exists()):
            return _skip("no machine installation journal")
        cfg = config_path(env)
        if coordinated_setting(load_config(cfg)[0] if cfg is not None else None):
            return _skip("maintenance: coordinated (the developer path)")
        if _removal_interrupted(home):
            return _skip(REMOVAL_INTERRUPTED)
        head = install_activation.source_head(framework)
        transaction = install_activation.Activation(
            framework, journal, default_authority=choose_authority(framework, False, head))
        data = transaction._load()
        if not data:
            return _skip("no machine installation journal")
        if transaction.authority_of(data) is not install_activation.COMMIT:
            return _skip("the installation follows the byte snapshot (the coordinated maintenance path)")
        served = _served_parts(home, env, cfg)
        if data["phase"] == "complete" and head == data.get("source_commit") and not (
                install_activation.absent_parts(data, served)):
            print(json.dumps({"refresh": "current", "source_commit": head}, sort_keys=True))
            return 0
        with install_activation.machine_lock(blocking=False):
            data = transaction._load()
            transaction._lease(data)
            state = transaction.status()
            if state.get("reason") and not state.get("next_start_completes"):
                return _skip(state["reason"])
            if state["phase"] in {"applying", "recovery_required"}:
                try:
                    state = transaction.retry(compatibility=install_activation.workflow_compatibility)
                except ValueError as exc:
                    print(f"forge install: conflict: {exc}", file=sys.stderr)
                    return 2
            # A prepared operation (the refresh's own, killed before apply) and a journal behind HEAD are
            # both planned and applied by the install; one more round reaches HEAD after a prepared one.
            for _ in range(2):
                if state["phase"] not in {"prepared", "complete"}:
                    return _skip(f"installation phase {state['phase']}")
                data = transaction._load()
                if state["phase"] == "complete" and not transaction.authority_of(data).behind(transaction, data) \
                        and not install_activation.absent_parts(data, served):
                    break  # current, and no Forge part is gone (an absent one is written again)
                args = parser.parse_args(["--profile", MACHINE_PROFILE, "--refresh"] + [
                    f"--consumer-root={root}" for root in data.get("consumer_roots", [])])
                with contextlib.redirect_stdout(io.StringIO()):
                    code = _main(args, parser, framework=framework)
                if code:
                    return code
                state = transaction.status()
            print(json.dumps(state, sort_keys=True))
            return 0
    except BlockingIOError:
        return _skip("another installation run holds the lock")
    except (OSError, ValueError) as exc:
        return _skip(str(exc))


def _refresh_project(project: Path, framework: Path) -> int:
    """`--refresh PROJECT`: bring a project install up to the checkout's commit, as its install would.
    Writes only into the project (no machine lock, no HOME); never fails a start: a refusal of a planned
    write skips with exit 0. A project that is HOME or a host's user configuration folder is refused (2)."""
    env = os.environ
    try:
        project_install.refuse_user_scope(project)
    except ValueError as exc:
        print(f"forge install: conflict: {exc}", file=sys.stderr)
        return 2
    try:
        needed, reason = project_install.refresh_needed(project, framework)
        if not needed:
            if reason:
                return _skip(reason)
            return 0
        machine = _project_preflight(framework, env, closure=True)
        _, record = project_install.read_record(project_install._resolve(project))
        if record and record.get("hosts"):
            hosts = list(record["hosts"])
        else:
            hosts, _ = resolve_hosts([], {}, False, env)
    except (OSError, ValueError) as exc:
        return _skip(str(exc))
    return project_install.run(project, framework, hosts=hosts, check=False, remove=False,
                               machine_hosts=machine, refresh=True)


def main(argv: list[str] | None = None, *, framework: Path = FRAMEWORK) -> int:
    arguments = sys.argv[1:] if argv is None else argv
    parser = build_parser()
    args = parser.parse_args(arguments)
    if args.profile is not None and args.profile not in PROFILES:
        moved = normalize_profile(args.profile)
        if moved is not None:
            print(f"forge install: profile {args.profile} is now {moved}; use --profile {moved}", file=sys.stderr)
            return 2
        parser.error(f"--profile must be {' or '.join(PROFILES)}")
    if args.validation_operation and args.maintenance != "status":
        parser.error("--validation-operation requires --maintenance status")
    if args.require_ready and args.maintenance != "status":
        parser.error("--require-ready requires --maintenance status")
    if (args.skill_link or args.force_user_config or args.create_user_repo or args.coordinated) \
            and args.user_repo is None:
        parser.error("--skill-link, --force-user-config, --create-user-repo and --coordinated require --user-repo")
    if args.refresh is not None:
        others = [flag for flag in ("--profile", "--check", "--remove", "--host", *MACHINE_ONLY,
                                    "--operation-id", "--require-ready", "--validation-operation",
                                    "--validation-evidence") if _given(args, flag)]
        if others or args.projects:
            parser.error("--refresh [PROJECT] takes no other option or project")
        if args.refresh:
            return _refresh_project(Path(args.refresh), framework)
        return _refresh_machine(parser, framework)
    # Without --profile the project install runs; maintenance alone is the machine installation's.
    # The chosen profile's placement (framework/install-profiles.yaml) decides the path.
    if args.remove is not None:
        machine = args.profile == MACHINE_PROFILE
        if args.host or (machine and (args.remove or args.projects)):
            parser.error("--remove takes no --host; the machine removal (--profile full-ai-integration --remove) "
                         "takes no PROJECT, the project removal is --remove PROJECT")
        if not machine:
            return _project(args, parser, framework)
        try:
            with install_activation.machine_lock(shared=args.check):
                return _remove_machine(args, framework)
        except (OSError, ValueError) as exc:
            print(f"forge install: conflict: {exc}", file=sys.stderr)
            return 2
    if args.profile is not None or args.maintenance is None:
        try:
            placement = load_profile(framework, args.profile or PROJECT_PROFILE)["placement"]
        except (OSError, ValueError, yaml.YAMLError) as exc:
            print(f"forge install: conflict: {exc}", file=sys.stderr)
            return 2
        if placement == "project":
            return _project(args, parser, framework)
    shared = args.check or args.maintenance == "status"
    try:
        with install_activation.machine_lock(shared=shared):
            return _main(args, parser, framework=framework)
    except (OSError, ValueError) as exc:
        print(f"forge install: conflict: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
