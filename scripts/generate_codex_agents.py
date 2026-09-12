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
from pathlib import Path

sys.dont_write_bytecode = True

import yaml  # noqa: E402 - disable bytecode before third-party/project imports

try:
    from .codex_legacy import legacy_hashes
    from .generate_skill_wrappers import build_desired
    from .managed_install import (
        InstallConflict,
        InstallPlan,
        digest,
        json_bytes,
        managed_files,
        read_file,
        safe_path,
    )
except ImportError:
    from codex_legacy import legacy_hashes
    from generate_skill_wrappers import build_desired
    from managed_install import (
        InstallConflict,
        InstallPlan,
        digest,
        json_bytes,
        managed_files,
        read_file,
        safe_path,
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


def boot_instructions(framework: str) -> str:
    return (
        "Forge framework root: " + framework + "\n\n"
        "For the primary Buddy session, read these files before responding, even\n"
        "when no Buddy role was explicitly selected:\n\n"
        + "\n".join(
            f"- {framework}/agents/buddy/{part}.md"
            for part in ("soul", "operational", "boot")
        )
        + "\n\nKeep the consumer CWD as the active project. Resolve framework paths\n"
        "against the framework root above; resolve project intent.md, AGENTS.md,\n"
        "docs/ and context/ against the active project. Follow the consumer's\n"
        "AGENTS.md instructions as project rules. Delegated roles follow their\n"
        "own canonical role and do not repeat primary-session boot/bookkeeping.\n"
    )


def generate_roles(repo: Path, framework_root: Path | None = None) -> dict[str, str]:
    desired = {}
    seen = set()
    framework = str(framework_root.resolve()) if framework_root else "<FRAMEWORK_ROOT>"
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
        root_resolution = ""
        if framework_root is None:
            root_resolution = (
                "Resolve <FRAMEWORK_ROOT> before reading framework files: use the\n"
                "active repository when it contains agents/buddy/boot.md and\n"
                "framework/boot-navigation.md. In a consumer checkout, use the\n"
                "concrete Forge root from the managed AGENTS boot entry. Report\n"
                "a missing root instead of guessing.\n\n"
            )
        instructions = root_resolution + (
            f"Canonical role: {framework}/agents/{source.name}\n"
            f"Resolve framework references against {framework}; resolve bare\n"
            f"_protocols/ references against {framework}/agents/. Keep project\n"
            "paths relative to the active consumer CWD.\n\n" + sections[2].lstrip("\n")
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
    if not desired:
        raise ValueError(f"no active neutral roles in {repo / 'agents'}")
    return desired


def plan_boot(plan: InstallPlan, root: Path, framework: Path) -> None:
    path = safe_path(root) / "AGENTS.md"
    state_path = path.with_name(".forge-codex-boot.json")
    original = read_file(path)
    text = original.decode() if original is not None else ""
    raw_state = read_file(state_path)
    old_hash = None
    if raw_state is not None:
        try:
            state = json.loads(raw_state)
            if set(state) != {"version", "sha256"} or state["version"] != 1:
                raise ValueError("unsupported boot state")
            old_hash = state["sha256"]
            if not isinstance(old_hash, str) or not re.fullmatch(
                r"[a-f0-9]{64}", old_hash
            ):
                raise ValueError("invalid boot hash")
        except (ValueError, TypeError) as exc:
            raise InstallConflict(f"invalid boot ownership: {state_path}") from exc
    block = START + "\n" + boot_instructions(str(framework)) + END
    if START in text or END in text:
        if (
            text.count(START) != 1
            or text.count(END) != 1
            or text.index(START) > text.index(END)
        ):
            raise InstallConflict(f"malformed managed boot block: {path}")
        start, end = text.index(START), text.index(END) + len(END)
        current = text[start:end]
        if current != block and digest(current.encode()) != old_hash:
            raise InstallConflict(f"modified or unowned boot block: {path}")
        updated = text[:start] + block + text[end:]
    else:
        if old_hash is not None and original is not None:
            raise InstallConflict(f"managed boot block removed: {path}")
        updated = text + ("\n\n" if text else "") + block + "\n"
    plan.add(path, updated.encode(), expected=original)
    plan.add(
        state_path,
        json_bytes({"version": 1, "sha256": digest(block.encode())}),
        expected=raw_state,
    )


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
            codex_home = safe_path(args.codex_home)
            agents_home = safe_path(args.agents_home)
            # Mandatory inputs must validate before any ownership/cleanup planning.
            skills = build_desired(
                repo / "skills",
                tool_label="Codex",
                discovery_label="Codex",
                framework_root=repo,
            )
            legacy_roles = None
            legacy_skills = None
            legacy_skill_hashes = None
            if args.migrate_legacy:
                legacy_roles = legacy_hashes("roles", repo)
                legacy_skill_hashes = legacy_hashes("skills")
                legacy_skills = {
                    f"{name}/SKILL.md": content
                    for name, content in build_desired(
                        repo / "skills", tool_label="Codex", discovery_label="Codex"
                    ).items()
                }
            managed_files(
                plan,
                codex_home / "agents",
                generate_roles(repo, repo),
                legacy_hashes=legacy_roles,
            )
            managed_files(
                plan,
                agents_home / "skills",
                {f"{name}/SKILL.md": content for name, content in skills.items()},
                legacy=legacy_skills,
                legacy_hashes=legacy_skill_hashes,
            )
            plan_boot(plan, codex_home, repo)
            plan_hook_cleanup(plan, codex_home, repo)
            for project in args.projects:
                project = safe_path(project)
                if not project.is_dir():
                    raise ValueError(f"project directory missing: {project}")
                plan_boot(plan, project, repo)
                plan_hook_cleanup(plan, project / ".codex", repo)
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
