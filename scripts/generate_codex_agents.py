#!/usr/bin/env python3
"""Generate Codex roles from neutral agents/*.md; install only managed surfaces.

Use --output-root /tmp/roles for portable templates. Add --framework-root for
concrete installed paths. setup-codex.sh invokes --install for home/project setup.
--check is read-only. --migrate-legacy adopts only exact known legacy files;
modified or unknown legacy content is a conflict requiring manual review.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shlex
import sys
from dataclasses import dataclass
from pathlib import Path

sys.dont_write_bytecode = True

import yaml  # noqa: E402 - disable bytecode before third-party/project imports

try:
    from .managed_install import (
        InstallConflict,
        InstallPlan,
        check_legacy_text,
        json_bytes,
        managed_files,
        plan_block,
        read_file,
        safe_path,
    )
    from .user_scope import (
        INVARIANTS_UNIT, MACHINE_PROFILE, WHOLE_BOOT, UserScope, boot_text, reread_line, round_one_line,
    )
except ImportError:
    from managed_install import (
        InstallConflict,
        InstallPlan,
        check_legacy_text,
        json_bytes,
        managed_files,
        plan_block,
        read_file,
        safe_path,
    )
    from user_scope import (
        INVARIANTS_UNIT, MACHINE_PROFILE, WHOLE_BOOT, UserScope, boot_text, reread_line, round_one_line,
    )


# These roles execute or author files; the others produce reports.
# spec-text-drift-batch is a writer despite its "spec" name.
WRITER_ROLES = {
    "buddy",
    "main-code-agent",
    "tester",
    "test-skeleton-writer",
    "spec-text-drift-batch",
    "security",
}
START = "<!-- FORGE-CODEX-BOOT:START -->"
END = "<!-- FORGE-CODEX-BOOT:END -->"


_TAIL = (
    "Keep the consumer CWD as the active project. Resolve framework paths\n"
    "against the framework root above; resolve project intent.md, AGENTS.md,\n"
    "docs/ and context/ against the active project. Follow the consumer's\n"
    "AGENTS.md instructions as project rules. Delegated roles follow their\n"
    "own canonical role and do not repeat primary-session boot/bookkeeping.\n"
)


def refresh_line(framework: str, target: str) -> str:
    """The installed entry's own refresh, as the first call of the Codex boot (AC-13: `git pull` in the
    checkout is the update). target "" refreshes the machine installation, "." the project."""
    command = f"python3 -B {shlex.quote(framework + '/scripts/forge_install.py')} --refresh" + (f" {target}" if target else "")
    return (
        f"First call, on its own and before the boot reads: run `{command}`. It brings the installed\n"
        "Forge entries up to the checkout's commit; its result does not change the boot.\n\n"
    )


def boot_instructions(
    framework: str, scope: UserScope | None = None, *, profile: str = MACHINE_PROFILE,
    refresh: str | None = None,
) -> str:
    """Codex boot entry. scope=None stays person-neutral (roles, project blocks);
    only home-level blocks receive a scope (framework/user-scope.md), and only
    they name the profile. refresh names the installed entry's refresh call
    (refresh_line): "" in the home block, "." in a project install's override
    block; None (roles, positional project blocks) adds none."""
    head = "Forge framework root: " + framework + "\n\n"
    if refresh is not None:
        head += refresh_line(framework, refresh)
    if scope is None:
        return (
            head
            + "For the primary Buddy session, read these files before responding, even\n"
            "when no Buddy role was explicitly selected:\n\n"
            + "\n".join(
                f"- {framework}/agents/buddy/{part}.md"
                for part in ("codex-execution", "soul", "boot")
            )
            + f"\n- {framework}/{INVARIANTS_UNIT}"
            + "\n" + WHOLE_BOOT
            + "\n" + reread_line(framework)
            + "\n" + round_one_line(framework) + "\n\n" + _TAIL
        )
    entry = boot_text(scope, Path(framework), profile, install_time=True)
    return (
        head
        + "For the primary Buddy session, follow this boot entry before responding,\n"
        "even when no Buddy role was explicitly selected:\n\n"
        + f"First read {framework}/agents/buddy/codex-execution.md.\n\n"
        + entry + round_one_line(framework) + "\n\n" + _TAIL
    )


@dataclass(frozen=True)
class Role:
    """One active neutral role: its frontmatter and the text after it."""

    name: str
    description: str
    source: Path
    metadata: dict
    body: str


def active_roles(repo: Path) -> list[Role]:
    """The role inventory: every active neutral role under `repo`/agents, by file name.

    Navigation documents (no frontmatter) and archived, deprecated or inactive
    roles are not roles. One owner for the Codex TOML renderer, the project
    install's Claude role wrappers and the capability closure.
    """
    roles = []
    seen = set()
    for source in sorted((repo / "agents").glob("*.md")):
        text = source.read_text(encoding="utf-8")
        if not text.startswith("---\n"):
            continue  # navigation documents are not roles
        sections = re.split(r"(?m)^---[ \t]*$", text, maxsplit=2)
        if len(sections) != 3:
            raise ValueError(f"unclosed role frontmatter: {source}")
        metadata = yaml.safe_load(sections[1])
        if not isinstance(metadata, dict):
            raise ValueError(f"invalid role frontmatter: {source}")
        if metadata.get("status") in {"archived", "deprecated", "inactive"}:
            continue
        name, description = metadata.get("name"), metadata.get("description")
        if not isinstance(name, str) or not re.fullmatch(r"[a-z][a-z0-9-]*", name):
            raise ValueError(f"invalid role name: {source}")
        if not isinstance(description, str) or not description.strip():
            raise ValueError(f"missing role description: {source}")
        if name in seen:
            raise ValueError(f"duplicate role name: {name}")
        seen.add(name)
        roles.append(Role(name, description, source, metadata, sections[2]))
    if not roles:
        raise ValueError(f"no active neutral roles in {repo / 'agents'}")
    return roles


def generate_roles(repo: Path, framework_root: Path | None = None) -> dict[str, str]:
    desired = {}
    framework = str(framework_root.resolve()) if framework_root else "<FRAMEWORK_ROOT>"
    for role in active_roles(repo):
        name, description, source = role.name, role.description, role.source
        root_resolution = ""
        if framework_root is None:
            root_resolution = (
                "Resolve <FRAMEWORK_ROOT> before reading framework files: use the\n"
                "active repository when it contains agents/buddy/boot.md and\n"
                "framework/boot-navigation.md. In a consumer checkout, use the\n"
                "concrete Forge root from the managed AGENTS boot entry. Report\n"
                "a missing root instead of guessing.\n\n"
            )
        execution_guide = (
            f"Before executing commands, read {framework}/agents/buddy/codex-execution.md.\n\n"
            if name in WRITER_ROLES else ""
        )
        instructions = root_resolution + execution_guide + (
            f"Canonical role: {framework}/agents/{source.name}\n"
            f"Resolve framework references against {framework}; resolve bare\n"
            f"_protocols/ references against {framework}/agents/. Keep project\n"
            "paths relative to the active consumer CWD.\n\n" + role.body.lstrip("\n")
        )
        settings = {"name": name, "description": " ".join(description.split())}
        if name == "buddy":
            instructions += "\n## Codex boot entry\n\n" + boot_instructions(framework)
        if name not in WRITER_ROLES:
            settings.update(sandbox_mode="read-only", approval_policy="never")
            instructions += (
                "\n## Codex report handoff\n\n"
                "This role defaults to read-only with approval_policy=never.\n"
                "Do not write files, including through shell commands or /tmp.\n"
                "Return the complete report inline, including intended artifact\n"
                "paths, evidence, and provenance. The parent persists it verbatim.\n"
                "Apply this handoff when a neutral protocol requests file output.\n"
                "Parent runtime overrides can override these defaults; they are\n"
                "not a guarantee of effective sandbox enforcement. Report any\n"
                "observed mismatch and retain the report-only behavior.\n"
            )
        settings["developer_instructions"] = instructions
        # JSON basic strings are TOML-compatible, without triple-quote interpolation.
        desired[f"{name}.toml"] = (
            "# Generated by scripts/generate_codex_agents.py; canonical source: agents/\n"
            + "\n".join(
                f"{key} = {json.dumps(value, ensure_ascii=False)}"
                for key, value in settings.items()
            )
            + "\n"
        )
    return desired


def plan_boot(
    plan: InstallPlan,
    root: Path,
    framework: Path,
    *,
    scope: UserScope | None = None,
    profile: str = MACHINE_PROFILE,
    filename: str = "AGENTS.md",
    refresh: str | None = None,
) -> None:
    """Codex wrapper: `<root>/<filename>` block. Pass a scope only for ~/.codex."""
    path = safe_path(root) / filename
    plan_block(
        plan,
        path,
        path.with_name(".forge-codex-boot.json"),
        START,
        END,
        boot_instructions(str(framework), scope, profile=profile, refresh=refresh),
    )


def plan_codex(
    plan: InstallPlan,
    codex_home: Path,
    agents_home: Path,
    framework: Path,
    *,
    skills: dict[str, str],
    scope: UserScope | None,
    profile: str = MACHINE_PROFILE,
    roles: bool | list[str] = True,
    legacy_roles: dict[str, set[str]] | None = None,
    legacy_skills: dict[str, str] | None = None,
    legacy_skill_hashes: dict[str, set[str]] | None = None,
) -> None:
    """The one planner for the Codex home surfaces (setup-codex.sh, forge_install.py).

    roles=False removes previously owned roles instead of installing them.
    `skills` maps kebab name -> wrapper content.
    """
    agents = codex_home / "agents"
    if roles:
        desired_roles = generate_roles(framework, framework)
        if isinstance(roles, list):
            missing = set(roles) - {Path(name).stem for name in desired_roles}
            if missing:
                raise ValueError(f"selected method roles unavailable: {sorted(missing)}")
            desired_roles = {name: text for name, text in desired_roles.items() if Path(name).stem in roles}
        managed_files(
            plan, agents, desired_roles, legacy_hashes=legacy_roles
        )
    elif read_file(agents / ".forge-managed.json") is not None:
        managed_files(plan, agents, {})
    managed_files(
        plan,
        agents_home / "skills",
        {f"{name}/SKILL.md": content for name, content in skills.items()},
        legacy=legacy_skills,
        legacy_hashes=legacy_skill_hashes,
    )
    check_legacy_text(codex_home / "AGENTS.md", START, END)
    # Only the home-level block is person-specific; project blocks stay neutral.
    plan_boot(plan, codex_home, framework, scope=scope, profile=profile, refresh="")
    if roles:
        plan_hook_cleanup(plan, codex_home, framework)


def obsolete_hook(hook: object, framework: Path) -> bool:
    if not isinstance(hook, dict) or hook.get("type") != "command":
        return False
    command = hook.get("command")
    if not isinstance(command, str):
        return False
    for script in ("session-start-remote.sh", "buddy-boot-inject.sh"):
        legacy = "bash ${CLAUDE_PROJECT_DIR}/orchestrators/claude-code/hooks/" + script
        if command == legacy:
            return True
        target = str(framework / "orchestrators/claude-code/hooks" / script)
        # The former installer emitted unquoted paths, including spaces.
        if command == f"bash {target}":
            return True
        try:
            if shlex.split(command) == ["bash", target]:
                return True
        except ValueError:
            return False
    return False


def plan_hook_cleanup(plan: InstallPlan, root: Path, framework: Path) -> None:
    path = safe_path(root) / "hooks.json"
    original = read_file(path)
    if original is None:
        return
    data = json.loads(original)
    if not isinstance(data, dict) or not isinstance(data.get("hooks", {}), dict):
        raise InstallConflict(f"invalid hooks structure: {path}")
    changed = False
    for event, groups in data.get("hooks", {}).items():
        if not isinstance(groups, list):
            raise InstallConflict(f"invalid hook event: {path}: {event}")
        remaining = []
        for group in groups:
            if not isinstance(group, dict) or not isinstance(group.get("hooks"), list):
                raise InstallConflict(f"invalid hook group: {path}: {event}")
            hooks = group["hooks"]
            filtered = [hook for hook in hooks if not obsolete_hook(hook, framework)]
            if filtered != hooks:
                changed = True
                group["hooks"] = filtered
            remaining.append(group)
        data["hooks"][event] = remaining
    if changed:
        plan.add(path, json_bytes(data), expected=original)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repo", type=Path, default=Path(__file__).resolve().parents[1]
    )
    parser.add_argument("--output-root", type=Path)
    parser.add_argument("--framework-root", type=Path)
    parser.add_argument("--install", action="store_true")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--migrate-legacy", action="store_true")
    parser.add_argument(
        "--codex-home",
        type=Path,
        default=Path(os.environ.get("CODEX_HOME", "~/.codex")),
    )
    parser.add_argument(
        "--agents-home",
        type=Path,
        default=Path(os.environ.get("AGENTS_HOME", "~/.agents")),
    )
    parser.add_argument("projects", type=Path, nargs="*")
    args = parser.parse_args(argv)
    repo = args.repo.resolve()
    plan = InstallPlan()
    try:
        if args.install:
            if args.output_root or args.framework_root:
                raise ValueError("--install derives framework paths from --repo")
            # Every host installation uses the coordinated activation boundary.
            # This legacy entry preserves argument spelling and exit-code family.
            try:
                from . import forge_install
            except ImportError:
                import forge_install
            forwarded = ["--profile", MACHINE_PROFILE] + (["--check"] if args.check else [])
            forwarded += ["--migrate-legacy"] if args.migrate_legacy else []
            forwarded.extend(str(project) for project in args.projects)
            previous = {key: os.environ.get(key) for key in ("CODEX_HOME", "AGENTS_HOME")}
            try:
                os.environ["CODEX_HOME"] = str(safe_path(args.codex_home))
                os.environ["AGENTS_HOME"] = str(safe_path(args.agents_home))
                return int(forge_install.main(forwarded, framework=repo) != 0)
            finally:
                for key, value in previous.items():
                    if value is None:
                        os.environ.pop(key, None)
                    else:
                        os.environ[key] = value

        else:
            if args.output_root is None or args.projects:
                raise ValueError(
                    "generation requires --output-root and accepts no projects"
                )
            managed_files(
                plan, args.output_root, generate_roles(repo, args.framework_root)
            )
        changes = plan.changes()
        if not args.check:
            plan.apply()
        print(
            f"codex adapter: {len(changes)} {'pending' if args.check else 'applied'} file changes"
        )
        if args.check:
            for path in changes:
                print(f"  drift: {path}")
        return int(args.check and bool(changes))
    except (OSError, ValueError, yaml.YAMLError) as exc:
        print(f"codex adapter: conflict: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
