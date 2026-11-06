#!/usr/bin/env python3
"""Generate Codex roles from neutral agents/*.md (the repository's .codex/agents).

Use --output-root DIR for the generated files. Add --framework-root for concrete
installed paths. --check is read-only and reports drift. Nothing is installed
into a home or project from here: Codex takes Forge as a plugin.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path

sys.dont_write_bytecode = True

import yaml  # noqa: E402 - disable bytecode before third-party/project imports

try:
    from .managed_install import InstallPlan, managed_files
    from .user_scope import (
        INVARIANTS_UNIT, MACHINE_PROFILE, WHOLE_BOOT, UserScope, boot_text, reread_line, round_one_line,
    )
except ImportError:
    from managed_install import InstallPlan, managed_files
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
# Markers of the Codex AGENTS.md boot block the retired installer wrote (managed_install.SHARED_BLOCKS).
START = "<!-- FORGE-CODEX-BOOT:START -->"
END = "<!-- FORGE-CODEX-BOOT:END -->"


_TAIL = (
    "Keep the consumer CWD as the active project. Resolve framework paths\n"
    "against the framework root above; resolve project intent.md, AGENTS.md,\n"
    "docs/ and context/ against the active project. Follow the consumer's\n"
    "AGENTS.md instructions as project rules. Delegated roles follow their\n"
    "own canonical role and do not repeat primary-session boot/bookkeeping.\n"
)


def boot_instructions(
    framework: str, scope: UserScope | None = None, *, profile: str = MACHINE_PROFILE,
) -> str:
    """Codex boot entry. scope=None stays person-neutral (the generated roles);
    a scope (framework/user-scope.md) names the profile (the Codex eval arm)."""
    head = "Forge framework root: " + framework + "\n\n"
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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repo", type=Path, default=Path(__file__).resolve().parents[1]
    )
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--framework-root", type=Path)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)
    repo = args.repo.resolve()
    plan = InstallPlan()
    try:
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
