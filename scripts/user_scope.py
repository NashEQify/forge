#!/usr/bin/env python3
"""Resolve the machine's user scope (framework/user-scope.md is the SoT).

Machine setting `${XDG_CONFIG_HOME:-~/.config}/forge/user.yaml` (override:
env FORGE_USER_CONFIG) names the person's user repository; inside it the
fixed convention `context/user/{soul,profile,navigation}.md` applies.

The resolver never raises on user data: every defect degrades to "no user
scope" (forge soul) or a skipped file, with a warning. Consumers: the Claude
Code hook (`--hook-json`), `cc` (`--boot-text`, `--json`), the Codex/CC home
boot blocks (`boot_text(..., install_time=True)`), forge_install.py and
setup-oc.sh.

CLI: user_scope.py [--framework-root P] [--profile full|daily]
                   (--json | --soul | --boot-text | --hook-json | --shell)
--shell prints USER_REPO=… and BOOT_TEXT=… as shell-quoted assignments (cc).
Exit 0 whenever a scope (possibly empty) was produced; exit 2 on internal error.
"""

from __future__ import annotations

import argparse
import json
import os
import shlex
import stat
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Callable, Mapping

sys.dont_write_bytecode = True

PROFILES = ("full", "daily")
# Framework boot files per install profile (mirrors boot_files in
# framework/install-profiles.yaml; a test keeps both in sync).
PROFILE_BOOT_FILES = {"full": ("soul", "boot"), "daily": ("soul", "boot-on-demand")}
# The framework-wide invariants (framework-relative): every boot of these profiles reads them before the first
# answer, in every project. A host loads no framework file in a consumer project by itself, so the entry names it.
# The daily profile's on-demand start carries its own rules (agents/buddy/boot-on-demand.md).
INVARIANTS_UNIT = "framework/invariants.md"
INVARIANTS_PROFILES = ("full",)
KNOWN_KEYS = {"version", "user_repo", "profile", "skill_links"}
USER_BOOT_FILES = ("profile.md",)
NONE_CONFIGURED = "User scope: none configured (forge soul in use)."
PYYAML_MISSING = "PyYAML missing — user scope not resolved"
WARNING_PREFIX = "User scope warning: "
# The restricted-scope rule (agents/buddy/boot.md §Restricted user scope). Every
# non-neutral boot entry carries it after the read list; the static fallbacks of
# buddy-boot-inject.sh and cc restate it, and tests/test_boot_injectors.py keeps
# them equal.
# The whole-boot line (agents/buddy/boot.md, before §Boot sequence): every boot
# entry carries it, person-neutral blocks included; inside SCOPE_RULE it opens the rule.
WHOLE_BOOT = "A quick question or a small fix does not shorten the boot; 'it is only a lookup' is no exception: run boot.md's sequence before reading anything for the request."
SCOPE_RULE = (
    WHOLE_BOOT + " "
    "Instruction source: the framework root is this session's instruction source. "
    "Reading its files and the files this entry names loads instructions; it is not "
    "work outside the project, and a user scope that limits writes, network or "
    "installs does not forbid it. Under such a scope, skip only the boot steps it "
    "forbids (the freshness fetch needs the network and writes Git metadata; creating "
    "context files needs a write) and report each as an unavailable check. If the boot "
    "is skipped or cut "
    "short for any reason, say so at the start of your first answer and name what "
    "did not load."
)
MAINTENANCE_ANCHOR = (
    "The user scope is maintained continuously (knowledge_processor "
    "continuous-maintenance rules, {skill}); the start procedure loads those rules."
)
# The knowledge_processor unit that holds the continuous-maintenance rules (framework-relative).
MAINTENANCE_UNIT = ("skills", "knowledge_processor", "continuous-maintenance.md")
# Framework-owned always-loaded files per install profile (framework-relative),
# each with the qualifier that limits when it is loaded (None: always). The soul
# is not listed: it is the resolved soul the entry already names. reread_line()
# renders this table into every boot entry; consistency_check.py
# --check instruction-units guards the same files.
REREAD_FILES: dict[str, tuple[tuple[str, str | None], ...]] = {
    "full": (
        ("agents/buddy/boot.md", None),
        ("framework/work-principle.md", None),
        ("framework/invariants.md", None),
        ("agents/buddy/operational.md", "software"),
        ("framework/boot-navigation.md", "software"),
        ("agents/buddy/boot-software.md", "software"),
        ("agents/buddy/boot-on-demand.md", "on-demand"),
        ("agents/buddy/codex-execution.md", "codex"),
    ),
    "daily": (
        ("agents/buddy/boot-on-demand.md", None),
        ("framework/work-principle.md", None),
        ("agents/buddy/codex-execution.md", "codex"),
    ),
}
_REREAD_QUALIFIERS = {
    "software": "for software development",
    "on-demand": "for on-demand use",
    "codex": "on Codex",
}
_REREAD_PROJECT = {
    "full": "the project rules, intent.md and the session handoff",
    "daily": "the project rules, intent.md and the session handoff",
}
_REREAD_STEP = (
    "; then, for any Forge step in progress (skill, protocol, framework or workflow step), "
    "its core and the unit its stub or engine step text names for that step"
)
DAILY_OPERATIONAL = "load development instructions only for explicitly selected software development"
_RULES_COMMON = (
    "This install is on-demand: no automatic boards,\n"
    "role delegation, plan/workflow engine or development test chains. Installed\n"
    "skills may be used when they fit; other Forge methods only on explicit\n"
    "request. The active project stays the CWD.\n"
)
_PROJECT_RULES = {
    "claude": (
        "Project rules: the project's CLAUDE.md, else its AGENTS.md (Claude Code does\n"
        "not load AGENTS.md by itself). "
    ),
    "codex": "Project rules: the project's AGENTS.md. ",
}


def daily_rules(runtime: str) -> str:
    """Generic on-demand install rules (S9) for the daily home blocks."""
    if runtime not in _PROJECT_RULES:
        raise ValueError(f"unknown runtime: {runtime}")
    return _PROJECT_RULES[runtime] + _RULES_COMMON


def _and_join(items: list[str]) -> str:
    return items[0] if len(items) == 1 else ", ".join(items[:-1]) + " and " + items[-1]


def reread_line(framework_root: Path | str, profile: str) -> str:
    """The post-compaction reread line for a profile, naming the framework root once.

    framework_root is named as given (callers pass an absolute root, or a
    placeholder such as <FRAMEWORK_ROOT> for portable role templates).
    The root is named once, absolute, as the base of the framework files that
    follow; they are relative to it, never to the project (the CWD). Naming it
    once keeps the entry within the hook budget on long framework paths.
    """
    if profile not in PROFILES:
        raise ValueError(f"unknown profile: {profile}")
    groups: dict[str | None, list[str]] = {}
    for rel, qualifier in REREAD_FILES[profile]:
        groups.setdefault(qualifier, []).append(rel)
    parts = [", ".join(groups.pop(None, []))]
    parts += [f"{_REREAD_QUALIFIERS[q]} {_and_join(files)}" for q, files in groups.items()]
    unit = "/".join(MAINTENANCE_UNIT)
    return (
        "After compaction, reread before continuing: "
        + "the soul named above; "
        + f"under the framework root {framework_root} (every framework path in this line is "
        "relative to it, not to the project): " + "; ".join(p for p in parts if p)
        + "; then the user profile (when a user scope is configured), the "
        f"knowledge_processor continuous-maintenance rules ({unit}, under that root), "
        + _REREAD_PROJECT[profile] + _REREAD_STEP + "."
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
_MISSING_BOOT_FILE = "boot file missing, skipped: "


@dataclass
class UserScope:
    configured: bool = False
    config_path: str | None = None
    user_repo: str | None = None
    user_dir: str | None = None
    profile: str = "full"
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

    Installers refuse on it instead of defaulting to the full profile; a
    missing setting is not unusable (no user scope, profile full).
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

    profile = data.get("profile", "full")
    if profile not in PROFILES:
        warn(f"profile must be full or daily, using full: {profile!r}")
        profile = "full"
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
    path = config_path(env)
    if path is None:
        return from_config(framework_root, None, warnings=["HOME not set — no machine setting"])
    data, warnings = load_config(path)
    return from_config(framework_root, data, config=path, warnings=warnings)


def _unresolved_text(scope: UserScope, framework: Path) -> str:
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
    lines.append(reread_line(framework, scope.profile))
    return "\n".join(lines) + "\n"


def boot_text(
    scope: UserScope, framework_root: Path, profile: str | None = None, *,
    install_time: bool = False, neutral: bool = False, include: Inclusion | None = None,
) -> str:
    """Person-specific boot lines.

    install_time=True renders text baked into a home-level block: the soul
    is named conditionally so adding or removing soul.md needs no re-install;
    the start procedure reads the profile itself. neutral=True renders only the profile's framework
    boot files (no user-scope section, no scope rule) for person-neutral blocks.
    include: the carrier's whole-file inclusion policy (None: include nothing).
    Candidates in priority order: the resolved soul, then in the full profile
    agents/buddy/operational.md. Install-time text includes nothing, whatever
    the policy: a baked copy would go stale on the next light-path edit.
    The full profile's read list ends with the framework-wide invariants (INVARIANTS_UNIT).
    """
    framework = Path(os.path.abspath(framework_root))
    if profile is None and not neutral and PYYAML_MISSING in scope.warnings:
        return _unresolved_text(scope, framework)
    profile = profile or scope.profile
    if profile not in PROFILES:
        raise ValueError(f"unknown profile: {profile}")
    buddy = framework / "agents" / "buddy"
    if install_time and scope.configured:
        soul = (
            f"{scope.user_dir}/soul.md if it exists, else {forge_soul(framework)}"
        )
    elif scope.soul_source == "user":
        soul = scope.soul
    else:  # the forge soul of the framework this text is rendered for
        soul = str(forge_soul(framework))
    lines = [f"Install profile: {profile}", "Read before the first answer:"]
    soul_at: int | None = None
    for part in PROFILE_BOOT_FILES[profile]:
        if part == "soul":
            soul_at = len(lines)
            lines.append(f"- soul: {soul}")
        else:
            lines.append(f"- {buddy / (part + '.md')}")
    if profile in INVARIANTS_PROFILES:
        lines.append(f"- {framework / INVARIANTS_UNIT}")
    if profile == "daily":
        lines.append(f"This install is on-demand: {DAILY_OPERATIONAL}.")
    if neutral:
        lines.append(WHOLE_BOOT)
        lines.append(reread_line(framework, profile))
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
    lines.append(reread_line(framework, profile))
    if include is None or install_time:
        return "\n".join(lines) + "\n"
    candidates = [soul]
    if profile == "full":
        candidates.append(str(buddy / "operational.md"))
    return _include(lines, soul_at, soul, candidates, include)


HOOK_HEAD = "BUDDY-BOOT REQUIRED before answering."


def hook_tail(framework: str) -> str:
    return (
        "Follow boot.md in order before the first answer: orientation, freshness gate, "
        "intent and workflow selection, then the selected mode's boot procedure and "
        "greeting. Resolve any "
        "remote-update decision before loading intent or context. Do not run "
        "plan/workflow probes or load the full skill index ahead of workflow selection. "
        "For on-demand use, follow the project's local boot and working rules.\n\n"
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


def hook_json(scope: UserScope, framework_root: Path) -> str:
    framework = os.path.abspath(framework_root)
    policy = Inclusion(entry_fits=lambda entry: fits_hook(hook_context(entry, framework)))
    context = hook_context(boot_text(scope, framework_root, include=policy), framework)
    return json.dumps(
        {
            "hookSpecificOutput": {
                "hookEventName": "SessionStart",
                "additionalContext": context,
            }
        },
        ensure_ascii=False,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--framework-root", type=Path, default=Path(__file__).resolve().parents[1]
    )
    parser.add_argument("--profile", choices=PROFILES)
    mode = parser.add_mutually_exclusive_group(required=True)
    for flag in ("--json", "--soul", "--boot-text", "--hook-json", "--shell"):
        mode.add_argument(flag, action="store_true")
    args = parser.parse_args(argv)
    try:
        scope = resolve(args.framework_root)
        if args.profile:
            scope.profile = args.profile
        if args.json:
            out = json.dumps(asdict(scope), indent=2, ensure_ascii=False)
        elif args.soul:
            out = scope.soul
        elif args.boot_text:
            out = boot_text(scope, args.framework_root, args.profile).rstrip("\n")
        elif args.shell:
            text = boot_text(
                scope, args.framework_root, args.profile, include=SHELL_INCLUSION,
            ).rstrip("\n")
            out = (
                f"USER_REPO={shlex.quote(scope.user_repo or '')}\n"
                f"BOOT_TEXT={shlex.quote(text)}"
            )
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
