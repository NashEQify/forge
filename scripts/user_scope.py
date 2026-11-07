#!/usr/bin/env python3
"""Resolve the machine's user scope (framework/user-scope.md is the SoT).

Machine setting `${XDG_CONFIG_HOME:-~/.config}/forge/user.yaml` (override:
env FORGE_USER_CONFIG) names the person's user repository; inside it the
fixed convention `context/user/{soul,profile,navigation}.md` applies.

The resolver never raises on user data: every defect degrades to "no user
scope" (forge soul) or a skipped file, with a warning. Consumers: the Claude
Code plugin hook (`--hook-json`, `--plugin`), the boot skill (`--boot-entry`),
forge_setup.py, the boot probe (`--json`), the generators and eval runners.

CLI: user_scope.py [--framework-root P] [--profile project|full-ai-integration | --project | --plugin]
                   (--json | --soul | --boot-text | --hook-json | --boot-entry)
--project renders the project install's entry: no user scope, the machine
setting is not read (the project hook passes it).
--plugin (with --hook-json) renders the plugin hook's entry: it reads the
SessionStart payload from stdin and prints nothing unless Buddy is active
(the project's activation line or the user switch, is_active()).
--boot-entry prints the plugin entry as plain text (the boot skill; no
activation check).
Exit 0 whenever a scope (possibly empty) was produced; exit 2 on internal error.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shlex
import stat
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Callable, Mapping, NamedTuple

sys.dont_write_bytecode = True

# The two profile names a boot entry carries: project: Forge in one named project only, no user scope;
# full-ai-integration: Buddy in every session of the machine, with the user scope.
PROJECT_PROFILE = "project"
MACHINE_PROFILE = "full-ai-integration"
PROFILES = (PROJECT_PROFILE, MACHINE_PROFILE)
# Retired profile names an existing installation may still record (selection.json, user.yaml), with the profile
# each moved to. Read only through normalize_profile().
_RETIRED_PROFILES = {"full": MACHINE_PROFILE, "daily": MACHINE_PROFILE}
# The plugin is a third way Forge is placed (the host's plugin manager, not the installer). It is a render value
# of the entry's profile line only, never a user.yaml profile: normalize_profile() keeps rejecting it.
PLUGIN_RENDER = "plugin"


def normalize_profile(name: object) -> str | None:
    """The profile `name` stands for: a profile name as is, a retired name as the profile it moved to
    (full, daily -> full-ai-integration), anything else None. The one owner of the alias rule: every read of a
    recorded or given profile name goes through here."""
    if not isinstance(name, str):
        return None
    if name in PROFILES:
        return name
    return _RETIRED_PROFILES.get(name)


class EntryUnit(NamedTuple):
    """One framework unit a boot entry names (framework-relative)."""

    path: str
    qualifier: str | None  # None: always; else the reread qualifier that limits when it is read
    read_first: bool = False  # also in the entry's read list before the first answer


INVARIANTS_UNIT = "framework/invariants.md"
# The one boot entry list, the same for both profiles (Task467 design note §3, AC-1c): the soul named first, then
# boot.md, framework/work-principle.md and framework/invariants.md; operational.md (software) and
# boot-on-demand.md (on-demand) only after workflow selection, as reread qualifiers. Why both profiles load the
# invariants whole: authorization, evidence and outcome verification bind in every session, also outside software
# work, and they live in invariants.md, whose own "Workflow selection" section limits the software-process
# invariants to software work. The user scope is the only difference between the profiles.
# The read list before the first answer names the soul, boot.md and the invariants (boot.md carries the
# work-principle directive); reread_line() renders the whole list; consistency_check.py --check
# instruction-units guards the same files.
ENTRY_UNITS: tuple[EntryUnit, ...] = (
    EntryUnit("agents/buddy/boot.md", None, read_first=True),
    EntryUnit("framework/work-principle.md", None),
    EntryUnit(INVARIANTS_UNIT, None, read_first=True),
    EntryUnit("agents/buddy/operational.md", "software"),
    EntryUnit("agents/buddy/boot-software.md", "software"),
    EntryUnit("agents/buddy/boot-on-demand.md", "on-demand"),
    EntryUnit("agents/buddy/codex-execution.md", "codex"),
)
KNOWN_KEYS = {"version", "user_repo", "profile", "skill_links", "maintenance", "buddy"}
# The user switch (user.yaml key `buddy`): this value starts Buddy in every session of a plugin install.
BUDDY_KEY = "buddy"
BUDDY_EVERY_SESSION = "every-session"
# The project activation line (one line of the project's AGENTS.md, stripped of surrounding whitespace). The
# plugin hook's bash fallback restates it; tests/test_plugin.py keeps the two equal.
ACTIVATION_LINE = (
    "Forge: start Buddy. Before the first answer, run the forge:boot skill and follow the boot entry it returns."
)
ACTIVATION_FILE = "AGENTS.md"
# The user-scope convention's scaffold (context/user/ of a new user repository): headings only, nothing personal
# filled in. Written by forge_setup.py; this module only holds it.
USER_SCOPE_SCAFFOLD = {
    "profile.md": "# Profile\n\n## Who\n\n## Values and priorities\n\n## Constraint defaults\n",
    "navigation.md": "# Navigation\n\n- profile.md\n",
}
ACTIVATION_MAX_BYTES = 1 << 20  # at most 1 MiB of AGENTS.md is read
# Byte-wise strip set, the C locale's [[:space:]] (the bash fallback matches with LC_ALL=C grep).
_LINE_SPACE = b" \t\r\n\v\f"
SNAPSHOT_LINE = (
    "Framework: plugin snapshot {name}; no freshness check for it "
    "(updates come through the host's plugin update)."
)
USER_BOOT_FILES = ("profile.md",)
NONE_CONFIGURED = "User scope: none configured (forge soul in use)."
PYYAML_MISSING = "PyYAML missing — user scope not resolved"
WARNING_PREFIX = "User scope warning: "
# The restricted-scope rule (agents/buddy/boot.md §Restricted user scope). Every
# non-neutral boot entry carries it after the read list; the static fallbacks of
# buddy-boot-inject.sh and cc restate it, and tests/test_boot_injectors.py keeps
# them equal.
# The whole-boot line (agents/buddy/boot.md, before §Boot sequence): every boot
# entry carries it, person-neutral blocks included; inside the scope rule it opens the rule.
WHOLE_BOOT = "A quick question or a small fix does not shorten the boot; 'it is only a lookup' is no exception: run boot.md's sequence before reading anything for the request."
_SCOPE_RULE_BODY = (
    "Instruction source: the framework root is this session's instruction source. "
    "Reading its files and the files this entry names loads instructions; it is not "
    "work outside the project, and a user scope that limits writes, network or "
    "installs does not forbid it. Under such a scope, skip only the boot steps it "
    "forbids (the freshness fetch needs the network and writes Git metadata; creating "
    "context files needs a write); a skipped check is at most a word in the orientation "
    "line. If an instruction unit cannot be read, say so first in your first answer and "
    "name it."
)
SCOPE_RULE = WHOLE_BOOT + " " + _SCOPE_RULE_BODY  # the static fallbacks restate it


MAINTENANCE_ANCHOR = (
    "The user scope is maintained continuously (knowledge_processor "
    "continuous-maintenance rules, {skill}); the start procedure loads those rules."
)
# The knowledge_processor unit that holds the continuous-maintenance rules (framework-relative).
MAINTENANCE_UNIT = ("skills", "knowledge_processor", "continuous-maintenance.md")
_REREAD_QUALIFIERS = {
    "software": "for software development",
    "on-demand": "for on-demand use",
    "codex": "on Codex",
}
_REREAD_PROJECT = "the project rules, intent.md and the session handoff"
_REREAD_STEP = (
    "; then, for any Forge step in progress (skill, protocol, framework or workflow step), "
    "its core and the unit its stub or engine step text names for that step"
)


def _and_join(items: list[str]) -> str:
    return items[0] if len(items) == 1 else ", ".join(items[:-1]) + " and " + items[-1]


# The boot's first tool round (agents/buddy/boot.md): one batch of reads plus the boot probe as its own call,
# before the freshness gate. Framework-relative; round_one_line() names their root first.
# Rendered into the hook tail (hook_tail), the Codex boot block (generate_codex_agents.boot_instructions) and
# boot_text(round_one=True); the hook's static fallback restates the line.
ROUND_ONE = (
    "agents/buddy/boot.md",
    "agents/buddy/boot-status.md",
    "agents/buddy/boot-routing.md",
    "framework/workflow-selection.md",
    INVARIANTS_UNIT,
    "framework/work-principle.md",
)


def round_one_line(framework_root: Path | str) -> str:
    """The Round-1 line of an entry: the root named before the framework-relative reads (as the reread
    line names it) and again in the probe call."""
    return (
        f"Round 1, one batch before the gate: under the framework root {framework_root} (paths relative to it), "
        "read " + _and_join(list(ROUND_ONE))
        + f", and run `bash {shlex.quote(f'{framework_root}/scripts/git-status-check.sh')} --boot` as its own call."
    )


def reread_line(framework_root: Path | str) -> str:
    """The post-compaction reread line, naming the framework root once.

    framework_root is named as given (callers pass an absolute root, or a
    placeholder such as <FRAMEWORK_ROOT> for portable role templates).
    The root is named once, absolute, as the base of the framework files that
    follow; they are relative to it, never to the project (the CWD). Naming it
    once keeps the entry within the hook budget on long framework paths.
    """
    groups: dict[str | None, list[str]] = {}
    for unit in ENTRY_UNITS:
        groups.setdefault(unit.qualifier, []).append(unit.path)
    parts = [", ".join(groups.pop(None, []))]
    parts += [f"{_REREAD_QUALIFIERS[q]} {_and_join(files)}" for q, files in groups.items() if q is not None]
    maintenance = "/".join(MAINTENANCE_UNIT)
    return (
        "After compaction, reread before continuing: "
        + "the soul named above; "
        + f"under the framework root {framework_root} (every framework path in this line is "
        "relative to it, not to the project): " + "; ".join(p for p in parts if p)
        + "; then the user profile (when a user scope is configured), the "
        f"knowledge_processor continuous-maintenance rules ({maintenance}, under that root), "
        + _REREAD_PROJECT + _REREAD_STEP + "."
    )


# Whole-file inclusion budgets per session-start carrier (agents/buddy/boot.md
# §User scope). Every other entry (--boot-text, --json, the Codex and Claude
# home blocks, OpenCode, neutral/role blocks, the static fallbacks) includes
# nothing. Install-time blocks never include: framework Markdown changes on the
# light path without a reinstall, and a baked copy would go stale while telling
# the session no read is needed.
#
# Claude Code 2.1.302 cuts a settings hook's additionalContext silently at
# 8,000 characters / 200 lines, measured as a JavaScript string length (UTF-16
# code units); stay under it, measured the same way, with room for longer paths.
HOOK_CONTEXT_MAX_CHARS = 7_600
HOOK_CONTEXT_MAX_LINES = 190
# Bound system-prompt growth to the core set; guard against an oversized user soul.
SHELL_INCLUDED_MAX_CHARS = 32_000
INCLUDED_SUFFIX = " (included in full below)"
INCLUDED_LINE = "Included in full below and already loaded (no read needed at boot): "


@dataclass(frozen=True)
class Inclusion:
    """Whole-file inclusion policy of one session-start carrier.

    max_included_chars: bound on the included file texts together.
    entry_fits: bound on the rendered carrier, given the rendered entry.
    """

    max_included_chars: int | None = None
    entry_fits: Callable[[str], bool] | None = None


SHELL_INCLUSION = Inclusion(max_included_chars=SHELL_INCLUDED_MAX_CHARS)


def whole_file(path: str | Path) -> str | None:
    """A regular file's UTF-8 text with its final newline stripped, else None.

    Never raises: an unreadable candidate is simply not included.
    """
    candidate = Path(path)
    if _kind(candidate) != "file":  # also keeps a FIFO from blocking the read
        return None
    try:
        text = candidate.read_bytes().decode("utf-8")
    except (OSError, UnicodeError, ValueError):
        return None
    return text[:-1] if text.endswith("\n") else text


def _render_entry(
    lines: list[str], soul_at: int | None, soul: str, included: list[tuple[str, str]]
) -> str:
    out = list(lines)
    if included:
        paths = [path for path, _ in included]
        if soul_at is not None and soul in paths:
            out[soul_at] += INCLUDED_SUFFIX
        out.append(INCLUDED_LINE + ", ".join(paths) + ".")
        for path, text in included:
            out += [f"===== BEGIN {path} =====", text, f"===== END {path} ====="]
    return "\n".join(out) + "\n"


def _include(
    lines: list[str], soul_at: int | None, soul: str, candidates: list[str],
    policy: Inclusion,
) -> str:
    """Include candidates whole, in priority order, while the policy's budget allows."""
    included: list[tuple[str, str]] = []
    for path in candidates:
        text = whole_file(path)
        if text is None:
            continue
        trial = included + [(path, text)]
        if (
            policy.max_included_chars is not None
            and sum(len(t) for _, t in trial) > policy.max_included_chars
        ):
            continue
        if policy.entry_fits is not None and not policy.entry_fits(
            _render_entry(lines, soul_at, soul, trial)
        ):
            continue
        included = trial
    return _render_entry(lines, soul_at, soul, included)


# Warnings about a missing boot file depend on the current file set; baked
# (install-time) text omits them: the start procedure reads the profile.
_MISSING_BOOT_FILE = "boot file missing: "


@dataclass
class UserScope:
    configured: bool = False
    config_path: str | None = None
    user_repo: str | None = None
    user_dir: str | None = None
    profile: str = MACHINE_PROFILE
    soul: str = ""
    soul_source: str = "forge"
    boot: list[str] = field(default_factory=list)
    navigation: str | None = None
    skill_links: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def forge_soul(framework_root: Path) -> Path:
    return Path(os.path.abspath(framework_root)) / "agents" / "buddy" / "soul.md"


def config_path(env: Mapping[str, str]) -> Path | None:
    """FORGE_USER_CONFIG, else $XDG_CONFIG_HOME/forge/user.yaml, else ~/.config/…"""
    override = env.get("FORGE_USER_CONFIG")
    if override:
        return Path(os.path.abspath(os.path.expanduser(override)))
    xdg = env.get("XDG_CONFIG_HOME")
    if xdg and os.path.isabs(xdg):  # XDG spec: relative values are ignored
        return Path(xdg) / "forge" / "user.yaml"
    home = env.get("HOME")
    if not home:
        return None
    return Path(home) / ".config" / "forge" / "user.yaml"


def _kind(path: Path) -> str | OSError:
    """'dir' | 'file' | 'missing' | 'other', or the OSError (e.g. EACCES).

    Path.exists()/is_dir() re-raise PermissionError; user data must never
    raise, so every probe of user data goes through here.
    """
    try:
        mode = os.stat(path).st_mode
    except (FileNotFoundError, NotADirectoryError):
        return "missing"
    except OSError as exc:
        return exc
    if stat.S_ISDIR(mode):
        return "dir"
    return "file" if stat.S_ISREG(mode) else "other"


def _denied(path: Path, exc: OSError) -> str:
    return f"not accessible: {path} ({exc.__class__.__name__})"


def load_config(path: Path) -> tuple[dict | None, list[str]]:
    """Return (mapping, warnings); mapping is None when no usable setting exists."""
    kind = _kind(path)
    if isinstance(kind, OSError):
        return None, ["machine setting " + _denied(path, kind)]
    if kind == "missing":
        return None, [f"no machine setting at {path}"]
    if kind != "file":
        return None, [f"machine setting is not a file: {path}"]
    try:
        import yaml  # lazy: the hook must work without PyYAML
    except ImportError:
        return None, [PYYAML_MISSING]
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError) as exc:
        return None, [f"machine setting unreadable: {path}: {exc.__class__.__name__}"]
    except yaml.YAMLError as exc:
        return None, [f"machine setting is not valid YAML: {path}: {exc.__class__.__name__}"]
    if not isinstance(data, dict):
        return None, [f"machine setting is not a mapping: {path}"]
    if data.get("version") != 1:
        return None, [f"machine setting version must be 1: {path}"]
    return data, []


def unusable_setting(env: Mapping[str, str] = os.environ) -> str | None:
    """Warning when a machine setting exists but cannot be used, else None.

    forge_setup.py refuses on it instead of defaulting; a missing setting is not
    unusable (no user scope).
    """
    path = config_path(env)
    if path is None or _kind(path) == "missing":
        return None
    data, warnings = load_config(path)
    return None if data is not None else (warnings[0] if warnings else str(path))


def _inside(path: Path, root: Path) -> bool:
    real, real_root = os.path.realpath(path), os.path.realpath(root)
    return real == real_root or real.startswith(real_root.rstrip(os.sep) + os.sep)


def from_config(
    framework_root: Path, data: Mapping | None, *, config: Path | None = None,
    warnings: list[str] | None = None,
) -> UserScope:
    """Build the effective scope from an already-loaded machine setting."""
    scope = UserScope(
        config_path=(
            str(config) if config is not None and _kind(config) in ("file", "dir", "other")
            else None
        ),
        soul=str(forge_soul(framework_root)),
        warnings=list(warnings or []),
    )
    if data is None:
        return scope
    warn = scope.warnings.append
    for key in sorted(set(map(str, data)) - KNOWN_KEYS):
        warn(f"unknown key ignored: {key}")
    if BUDDY_KEY in data and data[BUDDY_KEY] != BUDDY_EVERY_SESSION:
        warn(f"{BUDDY_KEY} must be {BUDDY_EVERY_SESSION}, Buddy switch off: {data[BUDDY_KEY]!r}")

    recorded = data.get("profile", MACHINE_PROFILE)
    profile = normalize_profile(recorded)
    if profile is None:
        warn(f"profile must be {' or '.join(PROFILES)}, using {MACHINE_PROFILE}: {recorded!r}")
        profile = MACHINE_PROFILE
    scope.profile = profile

    links = data.get("skill_links", []) or []
    if not isinstance(links, list):
        warn("skill_links must be a list, ignored")
        links = []
    names: set[str] = set()
    for link in links:
        if not isinstance(link, str) or not os.path.isabs(link):
            warn(f"skill link must be an absolute path, dropped: {link!r}")
        elif _kind(Path(link)) != "dir" or _kind(Path(link) / "SKILL.md") != "file":
            warn(f"skill link is not a directory with SKILL.md, dropped: {link}")
        elif os.path.basename(os.path.normpath(link)) in names:
            warn(f"skill link name already used, dropped: {link}")
        else:
            names.add(os.path.basename(os.path.normpath(link)))
            scope.skill_links.append(os.path.normpath(link))

    repo = data.get("user_repo")
    if repo is None:
        warn("user_repo missing in machine setting")
        return scope
    if not isinstance(repo, str) or not os.path.isabs(repo):
        warn(f"user_repo must be an absolute path: {repo!r}")
        return scope
    repo_path = Path(os.path.normpath(repo))
    kind = _kind(repo_path)
    if isinstance(kind, OSError):
        warn("user_repo " + _denied(repo_path, kind))
        return scope
    if kind != "dir":
        warn(f"user_repo is not a directory: {repo_path}")
        return scope
    user_dir = repo_path / "context" / "user"
    kind = _kind(user_dir)
    if isinstance(kind, OSError):
        warn("user context directory " + _denied(user_dir, kind))
        return scope
    if kind != "dir" or not _inside(user_dir, repo_path):
        warn(f"user context directory missing: {user_dir}")
        return scope

    scope.configured = True
    scope.user_repo = str(repo_path)
    scope.user_dir = str(user_dir)

    def contained(name: str) -> Path | None:
        path = user_dir / name
        kind = _kind(path)
        if isinstance(kind, OSError):
            warn(f"user file {_denied(path, kind)}, skipped")
            return None
        if kind == "missing":
            return None
        if kind != "file" or not _inside(path, repo_path):
            warn(f"not a file inside user_repo, ignored: {path}")
            return None
        return path

    soul = contained("soul.md")
    if soul is not None:
        scope.soul, scope.soul_source = str(soul), "user"
    for name in USER_BOOT_FILES:
        path = contained(name)
        if path is not None:
            scope.boot.append(str(path))
        elif _kind(user_dir / name) == "missing":
            warn(_MISSING_BOOT_FILE + str(user_dir / name))
        # else: contained() already warned (inaccessible or not a file)
    navigation = contained("navigation.md")
    scope.navigation = str(navigation) if navigation is not None else None
    return scope


def resolve(framework_root: Path, *, env: Mapping[str, str] = os.environ) -> UserScope:
    """Resolve machine setting → convention → effective scope. Never raises on user data."""
    return _resolve_with_setting(framework_root, env)[0]


def _resolve_with_setting(
    framework_root: Path, env: Mapping[str, str],
) -> tuple[UserScope, dict | None]:
    """resolve(), plus the loaded machine setting (None when there is no usable one)."""
    path = config_path(env)
    if path is None:
        return from_config(framework_root, None, warnings=["HOME not set — no machine setting"]), None
    data, warnings = load_config(path)
    return from_config(framework_root, data, config=path, warnings=warnings), data


def switch_on(data: Mapping | None) -> bool:
    """The user switch: user.yaml `buddy: every-session`. Any other value is off (from_config warns)."""
    return data is not None and data.get(BUDDY_KEY) == BUDDY_EVERY_SESSION


_RAW_SWITCH = re.compile(rb"^buddy:[ \t]*every-session[ \t]*(#.*)?$", re.M)


def raw_switch_on(config: str | Path | None) -> bool:
    """The user switch read without a YAML parser (PyYAML missing): one line `buddy: every-session`, an optional
    comment after it; nothing else of the file is parsed. Unreadable or not a regular file: off."""
    if config is None or _kind(Path(config)) != "file":
        return False
    try:
        with open(config, "rb") as handle:
            text = handle.read(ACTIVATION_MAX_BYTES)
    except OSError:
        return False
    return any(_RAW_SWITCH.match(line.rstrip(b"\r")) for line in text.split(b"\n"))


def project_dir(payload: object, env: Mapping[str, str] = os.environ) -> Path:
    """The session's project directory: the SessionStart payload's `cwd`, else CLAUDE_PROJECT_DIR, else the
    process CWD. Canonical (symlinks resolved), as the bash fallback's `pwd -P`."""
    cwd = payload.get("cwd") if isinstance(payload, dict) else None
    for candidate in (cwd, env.get("CLAUDE_PROJECT_DIR")):
        if isinstance(candidate, str) and candidate:
            return Path(os.path.realpath(candidate))
    try:
        return Path(os.path.realpath(os.getcwd()))
    except OSError:
        return Path(os.sep)


def _activation_dirs(start: Path) -> list[Path]:
    """start and its ancestors up to the nearest one holding a `.git` entry; without one, start alone."""
    walked = []
    current = Path(start)
    while True:
        walked.append(current)
        if os.path.exists(current / ".git"):
            return walked
        if current.parent == current:
            return [Path(start)]
        current = current.parent


def has_activation_line(path: Path) -> bool:
    """True when the regular file `path` holds ACTIVATION_LINE as one line (surrounding whitespace stripped).
    Reads at most ACTIVATION_MAX_BYTES; any read error counts as absent. Byte-wise, as the bash fallback."""
    if _kind(path) != "file":
        return False
    try:
        with open(path, "rb") as handle:
            data = handle.read(ACTIVATION_MAX_BYTES)
    except OSError:
        return False
    wanted = ACTIVATION_LINE.encode("utf-8")
    return any(line.strip(_LINE_SPACE) == wanted for line in data.split(b"\n"))


def activation_found(start: Path) -> bool:
    """The project's activation line: in AGENTS.md of start or an ancestor up to the nearest Git root.
    A start that is not an existing directory has none (the bash fallback cannot enter it either)."""
    if _kind(Path(start)) != "dir":
        return False
    return any(has_activation_line(d / ACTIVATION_FILE) for d in _activation_dirs(start))


def is_active(payload: object, data: Mapping | None, env: Mapping[str, str] = os.environ) -> bool:
    """Buddy starts in a plugin session when the project carries the activation line or the switch is on."""
    return switch_on(data) or activation_found(project_dir(payload, env))


def is_snapshot(framework_root: Path) -> bool:
    """True when the framework root itself holds no `.git` entry (a plugin's cache copy), even inside another
    repository (a Git-tracked HOME): that repository is not the framework's checkout."""
    return not os.path.exists(Path(os.path.abspath(framework_root)) / ".git")


def _unresolved_text(scope: UserScope, framework: Path, round_one: bool = False) -> str:
    """PyYAML missing: the setting exists but was not read — state no false facts."""
    buddy = framework / "agents" / "buddy"
    config = scope.config_path or "the machine setting"
    lines = [
        "Install profile: unknown (machine setting not resolved)",
        "Read before the first answer:",
        f"- soul: <user_repo>/context/user/soul.md if {config} names a user repo "
        f"and it exists, else {forge_soul(framework)}",
        f"- {buddy / 'boot.md'}",
        SCOPE_RULE,
        f"User scope: not resolved (PyYAML missing); read {config} per "
        "framework/user-scope.md",
    ]
    lines += [WARNING_PREFIX + w for w in scope.warnings if w != PYYAML_MISSING]
    lines.append(reread_line(framework))
    if round_one:
        lines.append(round_one_line(framework))
    return "\n".join(lines) + "\n"


def boot_text(
    scope: UserScope, framework_root: Path, profile: str | None = None, *,
    install_time: bool = False, neutral: bool = False, include: Inclusion | None = None,
    round_one: bool = False,
) -> str:
    """Person-specific boot lines.

    profile names the installation in the entry's first line (default: the
    scope's); both profiles render the same entry list (ENTRY_UNITS).
    install_time=True renders text baked into a home-level block: the soul
    is named conditionally so adding or removing soul.md needs no re-install;
    the start procedure reads the profile itself. neutral=True renders only the framework
    boot files (no user-scope section, no scope rule) for person-neutral blocks.
    include: the carrier's whole-file inclusion policy (None: include nothing).
    Candidates in priority order: the resolved soul, then
    agents/buddy/operational.md. Install-time text includes nothing, whatever
    the policy: a baked copy would go stale on the next light-path edit.
    round_one=True adds the Round-1 line after the reread line (carriers without a hook tail).
    """
    framework = Path(os.path.abspath(framework_root))
    if profile is None and not neutral and PYYAML_MISSING in scope.warnings:
        return _unresolved_text(scope, framework, round_one)
    profile = profile or scope.profile
    if profile not in PROFILES and profile != PLUGIN_RENDER:
        raise ValueError(f"unknown profile: {profile}")
    if install_time and scope.configured:
        soul = (
            f"{scope.user_dir}/soul.md if it exists, else {forge_soul(framework)}"
        )
    elif scope.soul_source == "user":
        soul = scope.soul
    else:  # the forge soul of the framework this text is rendered for
        soul = str(forge_soul(framework))
    lines = [f"Install profile: {profile}"]
    if profile == PLUGIN_RENDER and is_snapshot(framework):
        lines.append(SNAPSHOT_LINE.format(name=framework.name))
    lines.append("Read before the first answer:")
    soul_at = len(lines)
    lines.append(f"- soul: {soul}")
    lines += [f"- {framework / unit.path}" for unit in ENTRY_UNITS if unit.read_first]
    if neutral:
        lines.append(WHOLE_BOOT)
        lines.append(reread_line(framework))
        if round_one:
            lines.append(round_one_line(framework))
        return "\n".join(lines) + "\n"
    lines.append(SCOPE_RULE)
    if scope.configured:
        lines.append(
            f"User repo: {scope.user_repo} (the start procedure reads "
            f"{scope.user_dir}/profile.md after its freshness check)"
        )
        lines.append(MAINTENANCE_ANCHOR.format(skill=framework.joinpath(*MAINTENANCE_UNIT)))
    elif PYYAML_MISSING in scope.warnings:
        config = scope.config_path or "the machine setting"
        lines.append(
            f"User scope: not resolved (PyYAML missing); read {config} per "
            "framework/user-scope.md"
        )
    else:
        lines.append(NONE_CONFIGURED)
    for warning in scope.warnings:
        if install_time and warning.startswith(_MISSING_BOOT_FILE):
            continue
        lines.append(WARNING_PREFIX + warning)
    lines.append(reread_line(framework))
    if round_one:
        lines.append(round_one_line(framework))
    if include is None or install_time:
        return "\n".join(lines) + "\n"
    candidates = [soul, str(framework / "agents" / "buddy" / "operational.md")]
    return _include(lines, soul_at, soul, candidates, include)


HOOK_HEAD = "BUDDY-BOOT REQUIRED before answering."


def hook_tail(framework: str) -> str:
    return (
        "Follow boot.md in order before the first answer: orientation, freshness gate, "
        "intent and workflow selection, then the selected mode's boot procedure and "
        "greeting. Resolve any "
        "remote-update decision before loading intent or context. Do not run "
        "plan/workflow probes or load the full skill index ahead of workflow selection. "
        "For on-demand use, follow the project's local boot and working rules.\n"
        + round_one_line(framework) + "\n\n"
        "Keep the consumer CWD active. The project's CLAUDE.md and local authorization rules apply. "
        f"FRAMEWORK_DIR={framework}."
    )


def hook_context(entry: str, framework: str) -> str:
    """The SessionStart additionalContext around a rendered boot entry."""
    return HOOK_HEAD + "\n\n" + entry + "\n" + hook_tail(framework)


def fits_hook(context: str) -> bool:
    """Within the hook budget, measured as the host measures.

    Characters are UTF-16 code units (the host's JavaScript string length, so a
    character outside the BMP counts twice); lines are newline-separated segments.
    """
    return (
        len(context.encode("utf-16-le")) // 2 <= HOOK_CONTEXT_MAX_CHARS
        and len(context.split("\n")) <= HOOK_CONTEXT_MAX_LINES
    )


def hook_json(scope: UserScope, framework_root: Path, profile: str | None = None) -> str:
    framework = os.path.abspath(framework_root)
    policy = Inclusion(entry_fits=lambda entry: fits_hook(hook_context(entry, framework)))
    context = hook_context(boot_text(scope, framework_root, profile, include=policy), framework)
    return json.dumps(
        {
            "hookSpecificOutput": {
                "hookEventName": "SessionStart",
                "additionalContext": context,
            }
        },
        ensure_ascii=False,
    )


def plugin_boot_entry(scope: UserScope, framework_root: Path) -> str:
    """The plugin entry as plain text (--boot-entry, the boot skill): the hook's context, Round-1 line in
    its tail, the soul and operational core included while the shell budget allows."""
    framework = os.path.abspath(framework_root)
    entry = boot_text(scope, framework_root, PLUGIN_RENDER, include=SHELL_INCLUSION, round_one=False)
    return hook_context(entry, framework)


def _stdin_payload() -> object:
    """The SessionStart payload on stdin; anything unreadable or not JSON reads as no payload."""
    try:
        return json.loads(sys.stdin.read() or "null")
    except (OSError, UnicodeError, ValueError):
        return None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--framework-root", type=Path, default=Path(__file__).resolve().parents[1]
    )
    parser.add_argument("--profile", metavar="|".join(PROFILES))
    parser.add_argument("--project", action="store_true",
                        help="the project install's entry: no user scope; the machine setting is not read")
    parser.add_argument("--plugin", action="store_true",
                        help="with --hook-json: the plugin hook's entry, only when Buddy is active (payload on stdin)")
    mode = parser.add_mutually_exclusive_group(required=True)
    for flag in ("--json", "--soul", "--boot-text", "--hook-json", "--boot-entry"):
        mode.add_argument(flag, action="store_true")
    args = parser.parse_args(argv)
    if args.plugin and not args.hook_json:
        parser.error("--plugin renders the plugin hook's entry; use it with --hook-json")
    if (args.plugin or args.boot_entry) and (args.project or args.profile is not None):
        parser.error("the plugin entry takes neither --project nor --profile")
    if args.profile is not None:
        profile = normalize_profile(args.profile)
        if profile is None:
            parser.error(f"--profile must be one of {', '.join(PROFILES)}: {args.profile!r}")
        args.profile = profile
    if args.project:
        if args.profile not in (None, PROJECT_PROFILE):
            parser.error("--project renders the project profile")
        args.profile = PROJECT_PROFILE
    try:
        # The project install never reads a user scope: no machine setting, no warning about one.
        if args.plugin or args.boot_entry:
            # The plugin resolves the user scope whenever user.yaml configures one (line or switch alike).
            scope, data = _resolve_with_setting(args.framework_root, os.environ)
            if args.boot_entry:
                out = plugin_boot_entry(scope, args.framework_root).rstrip("\n")
            else:
                payload = _stdin_payload()
                # Without PyYAML the setting is unread; the switch alone is read by its strict line, and a boot it
                # starts names the unresolved setting (the entry for a missing PyYAML).
                unread_switch = data is None and PYYAML_MISSING in scope.warnings and raw_switch_on(scope.config_path)
                if not unread_switch and not is_active(payload, data):
                    return 0  # not active: the hook stays silent
                out = hook_json(scope, args.framework_root, None if unread_switch else PLUGIN_RENDER)
            sys.stdout.write(out + "\n")
            return 0
        scope = from_config(args.framework_root, None) if args.project else resolve(args.framework_root)
        if args.profile:
            scope.profile = args.profile
        if args.json:
            out = json.dumps(asdict(scope), indent=2, ensure_ascii=False)
        elif args.soul:
            out = scope.soul
        elif args.boot_text:
            out = boot_text(scope, args.framework_root, args.profile).rstrip("\n")
        else:
            out = hook_json(scope, args.framework_root)
        sys.stdout.write(out + "\n")
        return 0
    except Exception as exc:  # internal error only; user data never raises
        print(f"user_scope: internal error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())


@dataclass(frozen=True)
class ContinuityScope:
    """Location and privacy boundary; callers still need write authorization."""

    kind: str
    owner_root: Path
    content_root: Path
    pending_path: Path
    lock_path: Path


def resolve_continuity_scope(
    kind: str, project_root: Path, user_scope: UserScope | None = None,
) -> ContinuityScope:
    """Resolve one scope without consulting the other scope's recovery record."""
    if kind == "project":
        root = Path(project_root).resolve(strict=True)
        content = root
        pending = root / "context" / "maintenance-pending.md"
        lock = root / "context" / ".continuity-project.lock"
    elif kind == "personal":
        if user_scope is None or not user_scope.configured or not user_scope.user_repo:
            raise ValueError("personal scope is unavailable")
        root = Path(user_scope.user_repo).resolve(strict=True)
        content = root / "context" / "user"
        pending = content / "maintenance-pending.md"
        lock = content / ".continuity-personal.lock"
    else:
        raise ValueError("unknown continuity scope")
    if not root.is_dir():
        raise ValueError("scope owner is not a directory")
    for path in (content, pending.parent, pending, lock):
        if not path.resolve().is_relative_to(root):
            raise ValueError("scope path escapes its owner")
        for part in (path, *path.parents):
            if part == root:
                break
            if part.is_symlink():
                raise ValueError("scope paths may not contain symlinks")
    return ContinuityScope(kind, root, content, pending, lock)
