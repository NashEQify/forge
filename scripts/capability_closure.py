"""Selected source closure, independent of active workflow selection.

The existing profile manifest owns mandatory read/invocation dependencies.
Historical citations and conditional development callers are not runtime imports.
Missing required sources fail before integration changes, including sparse trees.
"""

from __future__ import annotations

import ast
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


def validate_closure(framework: Path, profile: dict) -> list[str]:
    pending = list(profile.get("required_paths", []))
    files: set[str] = set()
    instruction_roots = set(profile.get("instruction_roots", []))
    while pending:
        relative = pending.pop()
        path = _contained(framework, relative)
        if path.is_dir():
            pending.extend(
                p.relative_to(framework).as_posix()
                for p in path.rglob("*")
                if p.is_file()
                and "__pycache__" not in p.parts
                and not p.name.endswith(".pyc")
            )
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
