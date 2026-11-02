#!/usr/bin/env python3
"""The project install: Forge in one named project only (Task467, design note §1 shape B).

It writes into PROJECT only, never into HOME, /tmp or the Forge checkout:
- `.claude/agents/<role>.md`: one wrapper per active role, naming the canonical role in this checkout
  (owned through `.claude/agents/.forge-managed.json`);
- `.claude/settings.local.json`: `agent: buddy` and one SessionStart group running this checkout's boot
  hook in project mode (an owned fragment: keys and hooks the host or the user add stay);
- `AGENTS.override.md`: the Codex boot block (when Codex is chosen);
- `.git/info/exclude`: one block listing every owned path, so Git never tracks them (rule S1);
- `.claude/.forge-project.json`: the record of what it owns, with the hash of each owned fragment.

The record comes first: an install writes it with a pending marker (the wrapper hashes and the earlier
fragment hashes), then the exclude block, then the owned parts, then the final record, so an owned part
never exists without a record naming it. Removal (`--remove PROJECT`) deletes exactly the recorded parts
whose bytes still match (rule S4), a pending record's included; a part a user changed stops it before
anything is deleted. The project install never reads, asks for or writes a user scope, never installs into
HOME, an ancestor of it or a host's user configuration folder, and refuses a host the machine-wide
installation already serves.

The state vocabulary is the design note's §Mechanism-Lifecycle: project entry (absent-clear,
absent-blocked, installed-current, installed-stale, partial, diverged).
"""

from __future__ import annotations

import json
import os
import shlex
import subprocess
import sys
from pathlib import Path

sys.dont_write_bytecode = True

import yaml  # noqa: E402 - disable bytecode before third-party/project imports

try:
    from .generate_codex_agents import END as CODEX_END
    from .generate_codex_agents import START as CODEX_START
    from .generate_codex_agents import Role, active_roles, boot_instructions
    from .managed_install import (
        InstallConflict,
        InstallPlan,
        digest,
        json_bytes,
        managed_files,
        plan_json_fragment,
        plan_json_fragment_removal,
        plan_text_block,
        plan_text_block_removal,
        prune_empty_dirs,
        read_file,
        read_manifest,
        unmanage_root,
    )
    from .user_scope import PROJECT_PROFILE
except ImportError:
    from generate_codex_agents import END as CODEX_END
    from generate_codex_agents import START as CODEX_START
    from generate_codex_agents import Role, active_roles, boot_instructions
    from managed_install import (
        InstallConflict,
        InstallPlan,
        digest,
        json_bytes,
        managed_files,
        plan_json_fragment,
        plan_json_fragment_removal,
        plan_text_block,
        plan_text_block_removal,
        prune_empty_dirs,
        read_file,
        read_manifest,
        unmanage_root,
    )
    from user_scope import PROJECT_PROFILE

RECORD = ".claude/.forge-project.json"
# The record's pending marker: present while an install writes its owned parts.
PENDING = "pending"
SETTINGS = ".claude/settings.local.json"
SHARED_SETTINGS = ".claude/settings.json"
AGENTS_DIR = ".claude/agents"
OVERRIDE = "AGENTS.override.md"
EXCLUDE_START = "# FORGE-PROJECT:START"
EXCLUDE_END = "# FORGE-PROJECT:END"
HOOK = "orchestrators/claude-code/hooks/buddy-boot-inject.sh"
HOOK_TIMEOUT = 3
# Listed before the boot hook, with its own timeout: `git pull` in the checkout is the update (AC-13).
REFRESH_HOOK = "orchestrators/claude-code/hooks/forge-refresh.sh"
REFRESH_TIMEOUT = 60
MAIN_AGENT = "buddy"
SESSION_START = "hooks.SessionStart"
# Codex reads AGENTS.override.md in place of the folder's AGENTS.md (unverified until the Codex half of
# the AC-P probe), so the block names the project's own rules file.
CODEX_PROJECT_RULES = (
    "Codex does not load this project's AGENTS.md while this file exists; read it as the project rules."
)
# The frontmatter keys a wrapper carries over from its canonical role, in this order.
WRAPPER_KEYS = ("name", "description", "tools", "disallowedTools", "model")
# Hosts a project-placed profile has entries for (forge_install.PLACEMENT_HOSTS reads it from here).
PROJECT_HOSTS = ("claude-code", "codex")
_GIT_ENV_DROP = ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_COMMON_DIR", "GIT_OBJECT_DIRECTORY",
                 "GIT_NAMESPACE", "GIT_PREFIX")


class ProjectRefusal(InstallConflict):
    """Installing would collide (absent-blocked) or a part changed (diverged); nothing was written."""


def say(message: str) -> None:
    print(f"forge install: {message}", file=sys.stderr)


# --- what the entry consists of ---------------------------------------------------------------------


class _WrapperDumper(yaml.SafeDumper):
    """Wrapper frontmatter: a block mapping whose list values stay in flow style."""


_WrapperDumper.add_representer(
    list, lambda dumper, data: dumper.represent_sequence("tag:yaml.org,2002:seq", data, flow_style=True))


def role_wrapper(role: Role, framework: Path) -> str:
    """A Claude Code role wrapper: the canonical role's name, description and tool or model limits, then a
    pointer to the canonical role in this checkout. No instruction text is copied."""
    header = {key: role.metadata[key] for key in WRAPPER_KEYS if key in role.metadata}
    header["name"], header["description"] = role.name, " ".join(role.description.split())
    # Block style for the mapping, as every canonical role writes it; a list stays inline ([Agent, Edit]).
    text = yaml.dump(header, Dumper=_WrapperDumper, sort_keys=False, allow_unicode=True,
                     default_flow_style=False, width=10**6)
    return (
        "---\n" + text.strip() + "\n---\n\n"
        "<!-- generated-by: scripts/project_install.py -->\n"
        f"Read and follow the canonical role at `{role.source}`.\n"
        f"Resolve framework references against `{framework}` and bare `_protocols/` references against "
        f"`{framework / 'agents'}`.\n"
        "Use the caller's execution and output context as specified by the canonical role.\n"
    )


def session_start_group(framework: Path) -> dict:
    refresh = "bash " + shlex.quote(str(framework / REFRESH_HOOK)) + " --project"
    command = "bash " + shlex.quote(str(framework / HOOK)) + " --project"
    return {"hooks": [{"type": "command", "command": refresh, "timeout": REFRESH_TIMEOUT},
                      {"type": "command", "command": command, "timeout": HOOK_TIMEOUT}]}


def codex_block(framework: Path) -> str:
    return boot_instructions(str(framework), None, refresh=".") + CODEX_PROJECT_RULES + "\n"


# --- reading the project --------------------------------------------------------------------------


def _git(project: Path, *args: str) -> subprocess.CompletedProcess:
    env = {key: value for key, value in os.environ.items() if key not in _GIT_ENV_DROP}
    env["GIT_OPTIONAL_LOCKS"] = "0"
    return subprocess.run(["git", "-C", str(project), *args], text=True, capture_output=True,
                          timeout=10, env=env)


def git_exclude(project: Path) -> Path | None:
    """The project's info/exclude when PROJECT is the top level of its own Git work tree, None outside Git.

    Refuses when PROJECT lies inside a work tree without being its top level, or when info/exclude
    resolves outside PROJECT (a linked worktree or a submodule shares another repository's)."""
    try:
        top = _git(project, "rev-parse", "--show-toplevel")
    except (OSError, subprocess.SubprocessError) as exc:
        if (project / ".git").exists():
            raise ProjectRefusal(f"cannot read the Git repository of {project}: {exc}") from exc
        return None
    if top.returncode != 0:
        if (project / ".git").exists():
            raise ProjectRefusal(f"cannot read the Git repository of {project}: {top.stderr.strip()}")
        return None
    if os.path.realpath(top.stdout.strip()) != str(project):
        raise ProjectRefusal(
            f"{project} is inside the Git work tree {top.stdout.strip()}; install into its top level")
    found = _git(project, "rev-parse", "--git-path", "info/exclude")
    if found.returncode != 0:
        raise ProjectRefusal(f"cannot resolve info/exclude of {project}: {found.stderr.strip()}")
    exclude = Path(os.path.realpath(project / found.stdout.strip()))
    if not exclude.is_relative_to(project):
        raise ProjectRefusal(
            f"{project} shares another repository's Git directory ({exclude.parent.parent}), as a linked "
            "worktree or a submodule does; install into the main work tree")
    return exclude


def source_commit(framework: Path) -> str | None:
    """The checkout's HEAD commit (what the entry was rendered from), or None outside Git."""
    try:
        result = _git(framework, "rev-parse", "--verify", "-q", "HEAD")
    except (OSError, subprocess.SubprocessError):
        return None
    head = result.stdout.strip()
    return head if result.returncode == 0 and head else None


def tracked(project: Path, relatives: list[str]) -> list[str]:
    result = _git(project, "ls-files", "--", *relatives)
    if result.returncode != 0:
        raise ProjectRefusal(f"cannot list the tracked files of {project}: {result.stderr.strip()}")
    return result.stdout.splitlines()


def read_record(project: Path) -> tuple[bytes | None, dict | None]:
    path = project / RECORD
    raw = read_file(path)
    if raw is None:
        return None, None
    try:
        record = json.loads(raw)
    except ValueError as exc:
        raise ProjectRefusal(f"invalid project install record: {path}") from exc
    if (
        not isinstance(record, dict)
        or record.get("version") != 1
        or not isinstance(record.get("fragments"), dict)
        or not isinstance(record.get("hosts"), list)
    ):
        raise ProjectRefusal(f"invalid project install record: {path}")
    return raw, record


def _settings_agent(path: Path) -> object:
    raw = read_file(path)
    if raw is None:
        return None
    try:
        data = json.loads(raw)
    except ValueError as exc:
        raise ProjectRefusal(f"not valid JSON: {path}") from exc
    return data.get("agent") if isinstance(data, dict) else None


def _resolve(path: Path) -> Path:
    return Path(os.path.realpath(os.path.abspath(os.path.expanduser(path))))


def refuse_user_scope(project: Path) -> None:
    """Refuse HOME, an ancestor of HOME, and a folder whose `.claude` is the host's user configuration
    folder (~/.claude, or CLAUDE_CONFIG_DIR): a project install there would reach every session."""
    project = _resolve(project)
    home = os.environ.get("HOME")
    if home and os.path.isabs(home) and _resolve(Path(home)).is_relative_to(project):
        raise ProjectRefusal(
            f"{project} is your home folder or contains it; a project install there would reach every "
            "session on this machine. Name the project's own folder")
    claude = os.path.realpath(project / ".claude")
    for folder in filter(None, (home and os.path.join(home, ".claude"), os.environ.get("CLAUDE_CONFIG_DIR"))):
        if claude == os.path.realpath(os.path.expanduser(folder)):
            raise ProjectRefusal(
                f"{project / '.claude'} is Claude Code's user configuration folder ({folder}); a project "
                "install there would reach every session. Name another folder")


def _candidates(record: dict | None, key: str) -> list[str]:
    """The recorded hashes of a fragment: the record's, then the one before a pending write."""
    if not record:
        return []
    values = [record["fragments"].get(key), (record.get(PENDING) or {}).get("previous", {}).get(key)]
    return list(dict.fromkeys(value for value in values if value))


def _held(record: dict | None, key: str, attempt) -> str | None:
    """The recorded hash of fragment `key` that the file holds now (`attempt(plan, hash)` raises
    InstallConflict for one it does not hold); the last candidate when none does, so the real call names
    the conflict."""
    candidates = _candidates(record, key)
    for value in candidates[:-1]:
        try:
            attempt(InstallPlan(), value)
            return value
        except InstallConflict:
            continue
    return candidates[-1] if candidates else None


# --- install --------------------------------------------------------------------------------------


class Entry:
    """A planned project entry: the owned parts (`plan`), the record written around them, and the exclude
    block written before them."""

    def __init__(self, plan: InstallPlan, record: Path, raw: bytes | None, final: dict, pending: dict,
                 exclude: Path | None) -> None:
        self.plan, self.record, self.raw, self.final, self.pending, self.exclude = (
            plan, record, raw, final, pending, exclude)

    def changes(self) -> list[Path]:
        record = [self.record] if json_bytes(self.final) != self.raw else []
        return self.plan.changes() + record

    def apply(self) -> None:
        """Record (pending) first, then the exclude block, the owned parts and the final record: an owned
        part never exists without a record naming it."""
        final = json_bytes(self.final)
        if not self.plan.changes():
            if final != self.raw:
                done = InstallPlan()
                done.add(self.record, final, expected=self.raw)
                done.apply()
            return
        pending = json_bytes(dict(self.final, **{PENDING: self.pending}))
        first = InstallPlan()
        first.add(self.record, pending, expected=self.raw)
        created = not self.record.parent.exists()
        try:
            first.apply()
        except BaseException:
            if created:  # nothing was written: leave no empty .claude/ behind
                prune_empty_dirs([self.record], [self.record.parent.parent])
            raise
        self.plan.apply(first=(self.exclude,) if self.exclude else ())
        last = InstallPlan()
        last.add(self.record, final, expected=pending)
        last.apply()


def plan_install(
    project: Path, framework: Path, hosts: list[str], *, machine_hosts: set[str], refresh: bool = False
) -> Entry:
    """Plan the project entry for `hosts`.

    Raises ProjectRefusal for every absent-blocked and diverged state; nothing is written then. A refresh
    leaves the parts of a host the machine installation serves, and a diverged or colliding wrapper, as
    they are (one stderr line each) and brings every other part to the checkout's HEAD."""
    project, framework = _resolve(project), _resolve(framework)
    if not project.is_dir():
        raise ProjectRefusal(f"project directory missing: {project}")
    if project == framework or project.is_relative_to(framework):
        raise ProjectRefusal(f"{project} is the Forge checkout or lies inside it; name a project outside it")
    refuse_user_scope(project)
    served = [host for host in PROJECT_HOSTS if host in hosts]
    if not served:
        raise ProjectRefusal(
            f"the project install has no entry for {', '.join(hosts)}; choose with --host "
            + "|".join(PROJECT_HOSTS))
    blocked = [host for host in served if host in machine_hosts]
    if blocked and (not refresh or blocked == served):
        raise ProjectRefusal(
            f"Buddy already runs in every session on this machine for {', '.join(blocked)} (the "
            "full-ai-integration installation); a project install would start it a second time")
    for host in blocked:
        say(f"refresh: the {host} parts are left as they are (the machine installation serves {host})")
    head = source_commit(framework)  # read once, before rendering: the record names what was rendered
    raw_record, record = read_record(project)
    fragments = dict(record["fragments"]) if record else {}
    pending_files = (record.get(PENDING) or {}).get("files", {}) if record else {}
    exclude = git_exclude(project)
    plan = InstallPlan()
    owned: list[str] = []
    before: dict[str, str | None] = {}  # the fragment hash each file holds now

    agents = project / AGENTS_DIR
    wrapper_hashes: dict[str, str] = {}
    if "claude-code" in blocked:
        owned += [f"{AGENTS_DIR}/{name}" for name in sorted(read_manifest(agents)[2])]
        owned += [f"{AGENTS_DIR}/.forge-managed.json", SETTINGS]
    elif "claude-code" in served:
        # Installed, settings.local.json's owned keys are checked against their hash (diverged) instead.
        checked = [SHARED_SETTINGS] + ([] if fragments.get("settings") else [SETTINGS])
        for path in (project / rel for rel in checked):
            agent = _settings_agent(path)
            if agent not in (None, MAIN_AGENT):
                raise ProjectRefusal(f"{path} sets agent to {agent!r}; the project install sets it to "
                                     f"{MAIN_AGENT!r} (remove the key or keep Forge out of this project)")
        wrappers = {f"{role.name}.md": role_wrapper(role, framework) for role in active_roles(framework)}
        hold = _diverged_wrappers(agents, wrappers, pending_files) if refresh else frozenset()
        managed_files(plan, agents, wrappers, pending=pending_files, hold=hold)
        wrapper_hashes = {name: digest(text.encode()) for name, text in wrappers.items() if name not in hold}
        owned += [f"{AGENTS_DIR}/{name}" for name in sorted(set(wrappers) - hold)]
        owned += [f"{AGENTS_DIR}/.forge-managed.json"]

        def settings_fragment(target: InstallPlan, old: str | None) -> str:
            return plan_json_fragment(target, project / SETTINGS, {"agent": MAIN_AGENT},
                                      {SESSION_START: session_start_group(framework)}, old_hash=old)

        before["settings"] = _held(record, "settings", settings_fragment)
        fragments["settings"] = settings_fragment(plan, before["settings"])
        owned.append(SETTINGS)
    else:
        if read_manifest(agents)[1] is not None:
            unmanage_root(plan, agents, pending=pending_files)
        held = _held(record, "settings", lambda target, old: plan_json_fragment_removal(
            target, project / SETTINGS, ["agent"], [SESSION_START], old))
        if held:
            plan_json_fragment_removal(plan, project / SETTINGS, ["agent"], [SESSION_START], held)
        fragments["settings"] = None

    override = project / OVERRIDE
    if "codex" in blocked:
        owned.append(OVERRIDE)
    elif "codex" in served:
        raw = read_file(override)
        if raw is not None and CODEX_START.encode() not in raw and not fragments.get("agents_override"):
            raise ProjectRefusal(f"{override} exists without the Forge block; Forge does not take it over")

        def override_block(target: InstallPlan, old: str | None) -> str:
            return plan_text_block(target, override, CODEX_START, CODEX_END, codex_block(framework),
                                   old_hash=old, adopt_absent=True)

        before["agents_override"] = _held(record, "agents_override", override_block)
        fragments["agents_override"] = override_block(plan, before["agents_override"])
        owned.append(OVERRIDE)
    else:
        held = _held(record, "agents_override", lambda target, old: plan_text_block_removal(
            target, override, CODEX_START, CODEX_END, old))
        if held:
            plan_text_block_removal(plan, override, CODEX_START, CODEX_END, held)
        fragments["agents_override"] = None

    owned.append(RECORD)
    if exclude is not None:
        hits = tracked(project, owned)
        if hits:
            paths = " ".join(shlex.quote(hit) for hit in hits)
            raise ProjectRefusal("Git tracks paths the project install writes (an exclude line does not "
                                 f"untrack them): {', '.join(hits)}; untrack them with: git -C "
                                 f"{shlex.quote(str(project))} rm -r --cached {paths}")
        body = "".join(f"/{path}\n" for path in owned)

        def exclude_block(target: InstallPlan, old: str | None) -> str:
            return plan_text_block(target, exclude, EXCLUDE_START, EXCLUDE_END, body, old_hash=old,
                                   adopt_absent=True)

        before["exclude"] = _held(record, "exclude", exclude_block)
        fragments["exclude"] = exclude_block(plan, before["exclude"])
    elif fragments.get("exclude"):
        say(f"{project} is no longer a Git work tree; its recorded exclude block is left as it is")
    final = {
        "version": 1,
        "profile": PROJECT_PROFILE,
        "framework": str(framework),
        "hosts": served,
        "fragments": {key: fragments.get(key) for key in ("settings", "exclude", "agents_override")},
        "source_commit": head,
    }
    # The pending marker: the wrappers about to be written, and each fragment's hash before this write
    # (remove and the next install accept either while the record is pending).
    pending = {"files": {**pending_files, **wrapper_hashes},
               "previous": {key: value for key, value in before.items() if value and value != fragments[key]}}
    return Entry(plan, project / RECORD, raw_record, final, pending, exclude)


def _diverged_wrappers(agents: Path, wrappers: dict[str, str], pending: dict[str, str]) -> frozenset[str]:
    """Wrappers a refresh leaves as they are: changed by hand since the install, or an unowned file at a new
    wrapper's path (a pulled role whose name the user already uses). One stderr line each."""
    _, _, previous = read_manifest(agents)
    held = set()
    for name in sorted(set(wrappers) | set(previous)):
        current = read_file(agents / name)
        wanted = wrappers[name].encode() if name in wrappers else None
        if current is not None and current != wanted and digest(current) not in {previous.get(name),
                                                                                 pending.get(name)}:
            held.add(name)
            kind = "changed since the install" if name in previous else "not Forge's"
            say(f"refresh: {agents / name} is left as it is ({kind}); restore or move it, and the next start "
                "refreshes it")
    return frozenset(held)


# --- removal --------------------------------------------------------------------------------------


def plan_remove(project: Path) -> tuple[InstallPlan, bool]:
    """Plan the removal of every recorded part whose bytes still match; returns (plan, anything installed).

    A pending record (an interrupted install) counts like a final one: each part it names that is present
    is removed, an absent one counts as removed. A part changed since the install (diverged) raises
    ProjectRefusal: nothing is deleted."""
    project = _resolve(project)
    if not project.is_dir():
        raise ProjectRefusal(f"project directory missing: {project}")
    raw, record = read_record(project)
    agents = project / AGENTS_DIR
    manifest, has_wrappers, previous = read_manifest(agents)
    plan = InstallPlan()
    if record is None and has_wrappers is None:
        return plan, False
    pending_files = (record.get(PENDING) or {}).get("files", {}) if record else {}
    if has_wrappers is not None:
        unmanage_root(plan, agents, pending=pending_files)
    for name, hashed in sorted(pending_files.items()):
        # Written before the manifest named it (an interrupted first install): ours when the bytes match.
        current = read_file(agents / name)
        if name not in previous and current is not None and digest(current) == hashed:
            plan.add(agents / name, None, expected=current)

    def remove_settings(target: InstallPlan, old: str | None) -> None:
        plan_json_fragment_removal(target, project / SETTINGS, ["agent"], [SESSION_START], old)

    def remove_override(target: InstallPlan, old: str | None) -> None:
        plan_text_block_removal(target, project / OVERRIDE, CODEX_START, CODEX_END, old)

    for key, remove in (("settings", remove_settings), ("agents_override", remove_override)):
        held = _held(record, key, remove)
        if held:
            remove(plan, held)
    if _candidates(record, "exclude"):
        exclude = git_exclude(project)
        if exclude is not None:
            def remove_exclude(target: InstallPlan, old: str | None) -> None:
                plan_text_block_removal(target, exclude, EXCLUDE_START, EXCLUDE_END, old)

            remove_exclude(plan, _held(record, "exclude", remove_exclude))
    if raw is not None:
        plan.add(project / RECORD, None, expected=raw)
    return plan, True


# --- the command ----------------------------------------------------------------------------------


def refresh_needed(project: Path, framework: Path) -> tuple[bool, str]:
    """Whether a session-start refresh has anything to do in PROJECT: (needed, why not).

    Not needed when nothing is installed and when the entry belongs to another checkout. Needed when the
    record is pending (an interrupted install), names a commit other than the checkout's HEAD, names a part
    that is absent, or has no exclude block while the project is a Git work tree. The no-op path is one
    `git rev-parse`, one `stat` per recorded path and one of `.git`; nothing is planned."""
    project, framework = _resolve(project), _resolve(framework)
    _, record = read_record(project)
    _, manifest, wrappers = read_manifest(project / AGENTS_DIR)
    if record is None:
        if manifest is None:
            return False, f"nothing installed in {project}"
        return True, ""
    if record.get("framework") != str(framework):
        return False, f"{project} is installed from another checkout ({record.get('framework')})"
    if record.get(PENDING):
        return True, ""
    head = source_commit(framework)
    if record.get("source_commit") != head or ("source_commit" not in record and head is None):
        return True, ""
    fragments = record["fragments"]
    parts = [project / AGENTS_DIR / name for name in wrappers]
    parts += [project / rel for key, rel in (("settings", SETTINGS), ("agents_override", OVERRIDE))
              if fragments.get(key)]
    if any(not os.path.lexists(path) for path in parts):
        return True, ""
    if not fragments.get("exclude") and os.path.lexists(project / ".git"):
        return True, ""
    return False, ""


def run(
    project: Path, framework: Path, *, hosts: list[str], check: bool, remove: bool, machine_hosts: set[str],
    refresh: bool = False,
) -> int:
    """Install, check or remove; exit 0 done (or, with check, nothing pending), 1 changes pending (check),
    2 refused (nothing written). A refresh skips a refusal (a changed part, every host served by the machine
    installation) with one line and exit 0: it never fails a session start."""
    try:
        if remove:
            plan, installed = plan_remove(project)
            if not installed:
                say(f"nothing installed in {_resolve(project)}")
                return 0
            changes = plan.changes()
        else:
            entry = plan_install(project, framework, hosts, machine_hosts=machine_hosts, refresh=refresh)
            plan, changes = entry.plan, entry.changes()
        if check:
            for path in changes:
                print(path)
            return int(bool(changes))
        removed = [path for path in changes if path in plan.files and plan.files[path][1] is None]
        if remove:
            plan.apply()
        else:
            entry.apply()
        root = _resolve(project)
        prune_empty_dirs([path for path in removed if path.is_relative_to(root / ".claude")], [root])
        done = "removed from" if remove else ("installed in" if changes else "already current in")
        say(f"project install {'refreshed in' if refresh else done} {root} ({len(changes)} paths)")
        return 0
    except InstallConflict as exc:
        if refresh:
            say(f"refresh skipped: {exc}")
            return 0
        say(f"conflict: {exc}")
        return 2
    except (OSError, ValueError, yaml.YAMLError) as exc:
        say(f"conflict: {exc}")
        return 2
