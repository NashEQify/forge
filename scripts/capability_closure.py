"""Selected source closure, independent of active workflow selection.

The existing profile manifest owns mandatory read/invocation dependencies.
Historical citations and conditional development callers are not runtime imports.
Missing required sources fail before integration changes, including sparse trees.
"""

from __future__ import annotations

import ast
import json
import os
from copy import deepcopy
from pathlib import Path
import re

import yaml

METHODS = {"bedrock", "council", "frame"}
BARE_PROTOCOL = re.compile(r"(?<![\w/])(_protocols/[\w.-]+\.md)")
REFERENCE = re.compile(
    r"(?<![\w/-])((?:skills|agents|framework|scripts|workflows|docs)/[\w./-]+\.(?:md|py|sh|yaml))"
)


def compose_profile(framework: Path, profile: dict, methods: list[str]) -> dict:
    data = yaml.safe_load((framework / "framework/install-profiles.yaml").read_text())
    result = deepcopy(profile)
    selected = list(result.get("capabilities", []))
    for method in methods:
        method = "bedrock" if method == "bedrock-drill" else method
        if method not in METHODS:
            raise ValueError(f"unknown method: {method}")
        if method not in selected:
            selected.append(method)
    definitions = data.get("capability_sets", {})
    # Compatibility for fixtures/old manifests with no capability declarations.
    if not definitions and not selected:
        return result
    required = list(result.get("required_paths", [])) + list(
        data.get("installation_required_paths", [])
    )
    skills = result.get("skills", "all")
    roles = []
    visited = set()
    instruction_roots = []

    def include(name: str) -> None:
        if name in visited:
            return
        if name not in definitions:
            raise ValueError(f"unknown capability: {name}")
        visited.add(name)
        definition = definitions[name]
        for dependency in definition.get("depends_on", []):
            include(dependency)
        required.extend(definition.get("required_paths", []))
        if name != "development":
            instruction_roots.extend(
                p for p in definition.get("required_paths", []) if p.endswith(".md")
            )
        roles.extend(definition.get("roles", []))
        if isinstance(skills, list):
            skills.extend(definition.get("skills", []))

    for name in selected:
        include(name)
    result["capabilities"] = sorted(visited)
    result["required_paths"] = sorted(set(required))
    result["instruction_roots"] = sorted(set(instruction_roots))
    result["method_roles"] = sorted(set(roles))
    result["skills"] = sorted(set(skills)) if isinstance(skills, list) else skills
    result["reference_classification"] = data.get("reference_classification", {})
    return result


def _contained(framework: Path, relative: str) -> Path:
    path = framework / relative
    if (
        Path(relative).is_absolute()
        or ".." in Path(relative).parts
        or not path.resolve().is_relative_to(framework.resolve())
    ):
        raise ValueError(f"source closure path escapes framework: {relative}")
    if not path.exists():
        raise ValueError(
            f"required source closure missing: {relative}; restore source closure and retry ordinary installation (integration unchanged)"
        )
    return path


SHARED_SKILLS_ROOT = Path(".claude/skills")


def foreign_skill_path(framework: Path, path: Path) -> bool:
    """True for a path the shared `.claude/skills/` host root holds for others.

    `~/.claude/skills` links to this directory, so host sync, Pinokio and users
    write here too. Only a child proven by the generated-wrapper marker is a
    Forge source. Deciding that reads the child's `SKILL.md` marker; nothing
    else of a foreign child is read, walked (see `owned_tree`), baselined or
    changed. A child whose marker cannot be read is not proven, so foreign.
    """
    try:
        from .generate_skill_wrappers import is_generated_wrapper
    except ImportError:
        from generate_skill_wrappers import is_generated_wrapper
    try:
        parts = path.relative_to(framework).parts
    except ValueError:
        return False
    root = SHARED_SKILLS_ROOT.parts
    if len(parts) <= len(root) or parts[: len(root)] != root:
        return False
    try:
        return not is_generated_wrapper(framework.joinpath(*root, parts[len(root)]))
    except OSError:  # e.g. a mode-000 host child: ownership not proven
        return True


def owned_tree(framework: Path, root: Path):
    """`root.rglob("*")`, pruning foreign shared-skill children before descent."""
    skills = framework / SHARED_SKILLS_ROOT
    for directory, dirnames, filenames in os.walk(root):
        here = Path(directory)
        if here == skills:
            dirnames[:] = [n for n in dirnames if not foreign_skill_path(framework, here / n)]
            filenames = [n for n in filenames if not foreign_skill_path(framework, here / n)]
        yield from (here / name for name in dirnames + filenames)


def _python_imports(framework: Path, path: Path) -> list[str]:
    """Follow actual local Python imports; external libraries stay environment prerequisites."""
    found = []
    for node in ast.walk(ast.parse(path.read_text())):
        modules = []
        if isinstance(node, ast.ImportFrom):
            prefix = (node.module or "").replace(".", "/")
            if node.level:
                base = path.parent
                for _ in range(node.level - 1):
                    base = base.parent
                modules.append(base / prefix)
                modules.extend(
                    base / prefix / alias.name
                    for alias in node.names
                    if alias.name != "*"
                )
            else:
                modules.extend((framework / prefix, path.parent / prefix))
        elif isinstance(node, ast.Import):
            for name in node.names:
                modules.extend(
                    (
                        framework / name.name.replace(".", "/"),
                        path.parent / name.name.replace(".", "/"),
                    )
                )
        for module in modules:
            for candidate in (module.with_suffix(".py"), module / "__init__.py"):
                if candidate.is_file() and candidate.resolve().is_relative_to(
                    framework.resolve()
                ):
                    found.append(candidate.relative_to(framework).as_posix())
    # Explicit relative imports are mandatory even in a sparse tree where the
    # dependency is absent; existence-only import discovery would miss this.
    for node in ast.walk(ast.parse(path.read_text())):
        if isinstance(node, ast.ImportFrom) and node.level:
            base = path.parent
            for _ in range(node.level - 1):
                base = base.parent
            targets = (
                [base / node.module.replace(".", "/")]
                if node.module
                else [base / a.name for a in node.names]
            )
            for target in targets:
                candidate = (
                    target / "__init__.py"
                    if target.is_dir()
                    else target.with_suffix(".py")
                )
                found.append(candidate.relative_to(framework).as_posix())
    return found


def _document_references(path: Path, relative: str) -> set[str]:
    text = path.read_text()
    references = set(REFERENCE.findall(text))
    prefix = "agents/" if relative.startswith("agents/") else "skills/"
    references.update(prefix + ref for ref in BARE_PROTOCOL.findall(text))
    if (
        "REFERENCE.md" in text
        and path.name != "REFERENCE.md"
        and (path.parent / "REFERENCE.md").is_file()
    ):
        references.add(str(Path(relative).parent / "REFERENCE.md"))
    return references


def _classification(reference: str, required: set[str], policy: dict) -> str:
    if reference in required:
        return "required"
    if any(
        reference.startswith(prefix) for prefix in policy.get("historical_prefixes", [])
    ):
        return "historical"
    if reference in policy.get("optional_development", []):
        return "optional-development"
    if reference in policy.get("optional_methods", []):
        return "optional-method"
    return "required"


def _opencode_instructions(text: str) -> list[object]:
    """Read the template's active JSONC array, preserving quoted comment markers."""
    quoted = r'("(?:\\.|[^"\\])*")'
    uncommented = re.sub(
        quoted + r"|//[^\n]*|/\*.*?\*/",
        lambda match: match.group(1) or "", text, flags=re.S,
    )
    # Template arrays/objects permit trailing commas; leave string contents intact.
    clean = re.sub(
        quoted + r"|,(?=\s*[}\]])",
        lambda match: match.group(1) or "", uncommented,
    )
    document = json.loads(clean)
    instructions = document.get("instructions", []) if isinstance(document, dict) else []
    return instructions if isinstance(instructions, list) else []


def _validate_common_delivery(framework: Path, profile: dict, required: set[str]) -> None:
    """Check selected instruction edges at the existing source preflight boundary.

    This verifies delivery, never actor compliance or native host loading. Sparse
    daily trees need only their selected entries; full source also exposes static
    host roots, so check those when present rather than maintaining persona lists.
    """
    if not profile.get("capabilities"):
        return  # Compatibility with older, capability-free installer fixtures.
    common = "framework/work-principle.md"
    _contained(framework, common)
    directive = "Read and follow `" + common + "` before taking up work."
    full = "development" in profile["capabilities"]
    entries = set()
    for part in profile.get("boot_files", []):
        if part != "soul":
            entries.add(f"agents/buddy/{part}.md")
    if profile.get("invariants_unit"):
        entries.add(profile["invariants_unit"])
    entries.update(entry["source"] for entry in profile.get("entries", {}).values())
    try:
        from .generate_codex_agents import generate_roles
        from .generate_skill_wrappers import iter_skills, kebab_normalize
    except ImportError:
        from generate_codex_agents import generate_roles
        from generate_skill_wrappers import iter_skills, kebab_normalize
    roles = profile.get("method_roles", [])
    if full:
        roles = [Path(name).stem for name in generate_roles(framework)]
    entries.update(f"agents/{name}.md" for name in roles)
    wanted = profile.get("skills", "all")
    for dirname, metadata in iter_skills(framework / "skills"):
        if not metadata or metadata.get("status") in {"archived", "deprecated"}:
            continue
        invocation = metadata.get("invocation")
        if not isinstance(invocation, dict) or not invocation.get("primary"):
            continue
        relative = f"skills/{dirname}/SKILL.md"
        # Explicit-only is callable. Discovery restrictions do not retire a source.
        if full or relative in required or kebab_normalize(metadata.get("name", dirname)) in wanted:
            entries.add(relative)
    for relative in ("AGENTS.md", "CLAUDE.md"):
        if full or (framework / relative).exists():
            entries.add(relative)
    rules = framework / "orchestrators/cursor/rules"
    for rule in rules.glob("*.md"):
        if rule.read_text().startswith("---\n"):
            entries.add(rule.relative_to(framework).as_posix())
    for relative in sorted(entries):
        if directive not in _contained(framework, relative).read_text(encoding="utf-8"):
            raise ValueError(f"required common delivery missing: {relative}; read {common} before work (integration unchanged)")
    config = framework / "orchestrators/opencode/opencode.jsonc.example"
    if full or config.exists():
        relative = config.relative_to(framework).as_posix()
        try:
            instructions = _opencode_instructions(_contained(framework, relative).read_text())
        except json.JSONDecodeError as error:
            raise ValueError(f"invalid OpenCode instructions: {relative}: {error.msg}") from error
        if "${FRAMEWORK_DIR}/" + common not in instructions:
            raise ValueError(f"required common delivery missing: {relative}; add {common} to instructions (integration unchanged)")


def validate_closure(framework: Path, profile: dict) -> list[str]:
    pending = list(profile.get("required_paths", []))
    files: set[str] = set()
    instruction_roots = set(profile.get("instruction_roots", []))
    expanded: set[str] = set()  # owned by construction (`owned_tree`)
    while pending:
        relative = pending.pop()
        path = _contained(framework, relative)
        if relative not in expanded and foreign_skill_path(framework, path):
            raise ValueError(
                f"required source closure path is host-owned: {relative}; Forge sources must not depend on foreign .claude/skills content (integration unchanged)"
            )
        if path.is_dir():
            found = [
                p.relative_to(framework).as_posix()
                for p in owned_tree(framework, path)
                if p.is_file()
                and "__pycache__" not in p.parts
                and not p.name.endswith(".pyc")
            ]
            expanded.update(found)
            pending.extend(found)
            continue
        if relative in files:
            continue
        files.add(relative)
        if path.suffix == ".py":
            pending.extend(_python_imports(framework, path))
        elif path.suffix == ".md" and relative in instruction_roots:
            policy = profile.get("reference_classification", {})
            dependencies = {
                ref
                for ref in _document_references(path, relative)
                if _classification(ref, set(), policy) == "required"
            }
            instruction_roots.update(dependencies)
            pending.extend(dependencies)
    _validate_common_delivery(framework, profile, files)
    return sorted(files)


def reference_inventory(framework: Path, profile: dict) -> list[dict[str, str]]:
    """Review aid: distinguish manifested runtime reads from conditional/cited paths."""
    required = set(validate_closure(framework, profile))
    classification = profile.get("reference_classification", {})
    result = []
    for relative in sorted(required):
        if not relative.endswith(".md"):
            continue
        for reference in sorted(_document_references(framework / relative, relative)):
            kind = _classification(reference, required, classification)
            result.append(
                {"source": relative, "target": reference, "classification": kind}
            )
    return result
