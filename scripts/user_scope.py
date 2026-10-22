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
from typing import Mapping

sys.dont_write_bytecode = True

PROFILES = ("full", "daily")
# Framework boot files per install profile (mirrors boot_files in
# framework/install-profiles.yaml; a test keeps both in sync).
PROFILE_BOOT_FILES = {"full": ("soul", "boot"), "daily": ("soul", "boot-on-demand")}
KNOWN_KEYS = {"version", "user_repo", "profile", "skill_links"}
USER_BOOT_FILES = ("profile.md",)
NONE_CONFIGURED = "User scope: none configured (forge soul in use)."
PYYAML_MISSING = "PyYAML missing — user scope not resolved"
WARNING_PREFIX = "User scope warning: "
MAINTENANCE_ANCHOR = (
    "The user scope is maintained continuously (knowledge_processor §Continuous "
    "maintenance, {skill}); the start procedure loads those rules. After "
    "compaction re-read them, the project rules and the handoff."
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
        f"User scope: not resolved (PyYAML missing); read {config} per "
        "framework/user-scope.md",
    ]
    lines += [WARNING_PREFIX + w for w in scope.warnings if w != PYYAML_MISSING]
    return "\n".join(lines) + "\n"


def boot_text(
    scope: UserScope, framework_root: Path, profile: str | None = None, *,
    install_time: bool = False, neutral: bool = False,
) -> str:
    """Person-specific boot lines.

    install_time=True renders text baked into a home-level block: the soul
    is named conditionally so adding or removing soul.md needs no re-install;
    the start procedure reads the profile itself. neutral=True renders only the profile's framework
    boot files (no user-scope section) for person-neutral blocks.
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
    for part in PROFILE_BOOT_FILES[profile]:
        lines.append(f"- soul: {soul}" if part == "soul" else f"- {buddy / (part + '.md')}")
    if profile == "daily":
        lines.append(f"This install is on-demand: {DAILY_OPERATIONAL}.")
    if neutral:
        return "\n".join(lines) + "\n"
    if scope.configured:
        lines.append(
            f"User repo: {scope.user_repo} (the start procedure reads "
            f"{scope.user_dir}/profile.md after its freshness check)"
        )
        skill = framework / "skills" / "knowledge_processor" / "SKILL.md"
        lines.append(MAINTENANCE_ANCHOR.format(skill=skill))
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
    return "\n".join(lines) + "\n"


HOOK_HEAD = "BUDDY-BOOT REQUIRED before answering."


def hook_tail(framework: str) -> str:
    return (
        "Follow boot.md in order: orientation, freshness gate, intent and workflow "
        "selection, then the selected mode's boot procedure and greeting. Resolve any "
        "remote-update decision before loading intent or context. Do not run "
        "plan/workflow probes or load the full skill index ahead of workflow selection. "
        "For on-demand use, follow the project's local boot and working rules.\n\n"
        "Keep the consumer CWD active. CLAUDE.md and local authorization rules apply. "
        f"FRAMEWORK_DIR={framework}."
    )


def hook_json(scope: UserScope, framework_root: Path) -> str:
    framework = os.path.abspath(framework_root)
    context = (
        HOOK_HEAD + "\n\n" + boot_text(scope, framework_root) + "\n" + hook_tail(framework)
    )
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
            text = boot_text(scope, args.framework_root, args.profile).rstrip("\n")
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
