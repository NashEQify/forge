"""YAML loading + schema validation for workflow definitions."""

from __future__ import annotations

import sys
from pathlib import Path  # noqa: TC003 — used at runtime
from typing import Any

try:
    import yaml
except ImportError:
    print("ERROR: PyYAML required. pip install pyyaml", file=sys.stderr)
    sys.exit(1)

from scripts.lib import FRAMEWORK_ROOT

# ---------------------------------------------------------------------------
# YAML Discovery (Task 010 Part L0b)
# ---------------------------------------------------------------------------
#
# Workflow YAML definitions live inside the framework tree, so discovery is
# always rooted at FRAMEWORK_ROOT regardless of which project is currently
# active. Post repo-split this resolves to the framework repo checkout.

WORKFLOW_SEARCH_PATHS = [
    FRAMEWORK_ROOT / "workflows" / "runbooks",
    FRAMEWORK_ROOT / "skills",
]


def discover_workflow_yaml(name: str) -> Path | None:
    """Find workflow.yaml for a given workflow name."""
    for base in WORKFLOW_SEARCH_PATHS:
        candidate = base / name / "workflow.yaml"
        if candidate.exists():
            return candidate
    return None


def list_available_workflows() -> list[str]:
    """Return names of all available workflow definitions."""
    names: list[str] = []
    for base in WORKFLOW_SEARCH_PATHS:
        if not base.exists():
            continue
        for child in sorted(base.iterdir()):
            if child.is_dir() and (child / "workflow.yaml").exists():
                names.append(child.name)
    return names


# ---------------------------------------------------------------------------
# Schema Validation
# ---------------------------------------------------------------------------

REQUIRED_WORKFLOW_FIELDS = {"name", "steps"}
REQUIRED_STEP_FIELDS = {"id", "name", "category", "instruction"}
VALID_CATEGORIES = {"deterministic", "classification", "content", "gate"}
# "gate" — hold step waiting for an external decision (user approval,
# external review). Distinct from "content" because no LLM content is
# produced; distinct from "deterministic" because it never auto-completes
# (completion: manual only). The engine does not special-case "gate" —
# it falls through the standard manual-completion path.
VALID_COMPLETION_TYPES = {
    "file_modified_after", "file_created_matching", "file_content_check",
    "exit_code", "compound", "manual",
    # Spec 299 Phase C1: pointer_check sub-Check fuer Source-Verifikation.
    # Pflichtfeld: source_file. Validation-Mechanik im Engine-Check
    # (workflow_engine.py check_completion) gegen Schema-SoT
    # skills/_protocols/evidence-pointer-schema.md.
    "pointer_check",
}
VALID_GUARD_TYPES = {
    "file_exists", "step_status", "route_active", "script", "always_skip",
}
VALID_ON_FAIL = {"block", "warn", "skip", "escalate"}


class SchemaError(Exception):
    """Raised when a workflow YAML fails schema validation."""


def _validate_completion(comp: dict[str, Any], step_id: str) -> list[str]:
    """Validate a completion definition. Returns list of errors."""
    errors: list[str] = []
    ctype = comp.get("type")
    if not ctype:
        errors.append(f"step '{step_id}': completion missing 'type'")
        return errors
    if ctype not in VALID_COMPLETION_TYPES:
        errors.append(f"step '{step_id}': unknown completion type '{ctype}'")
        return errors

    if ctype == "file_modified_after":
        if not comp.get("path"):
            errors.append(f"step '{step_id}': file_modified_after requires 'path'")
    elif ctype == "file_created_matching":
        if not comp.get("pattern"):
            errors.append(f"step '{step_id}': file_created_matching requires 'pattern'")
    elif ctype == "file_content_check":
        if not comp.get("path"):
            errors.append(f"step '{step_id}': file_content_check requires 'path'")
        if comp.get("condition") not in ("has_match", "no_match"):
            errors.append(f"step '{step_id}': file_content_check condition must be 'has_match' or 'no_match'")
        if not comp.get("pattern"):
            errors.append(f"step '{step_id}': file_content_check requires 'pattern'")
    elif ctype == "exit_code":
        if not comp.get("command"):
            errors.append(f"step '{step_id}': exit_code requires 'command'")
    elif ctype == "compound":
        checks = comp.get("checks")
        if not checks or not isinstance(checks, list):
            errors.append(f"step '{step_id}': compound requires 'checks' list")
        else:
            for i, sub in enumerate(checks):
                if isinstance(sub, dict):
                    errors.extend(_validate_completion(sub, f"{step_id}.compound[{i}]"))
            # Spec 299 §2.2 ADV-TC-007 — Reihenfolge-Pflicht: pointer_check
            # MUSS vor manual stehen (Race-Mitigation: File muss existieren
            # bevor manual-complete erlaubt). Reverse-order ist Race-Bug-Konfig.
            sub_types = [
                sub.get("type") for sub in checks if isinstance(sub, dict)
            ]
            if "pointer_check" in sub_types and "manual" in sub_types:
                pc_idx = sub_types.index("pointer_check")
                m_idx = sub_types.index("manual")
                if m_idx < pc_idx:
                    errors.append(
                        f"step '{step_id}': compound order violation — "
                        f"pointer_check MUST precede manual (race-mitigation "
                        f"per Spec 299 §2.2). Got manual before pointer_check."
                    )
    elif ctype == "pointer_check":
        # Spec 299 §2.1 — pointer_check braucht source_file Pflichtfeld.
        # Top-level pointer_check ist permissiv akzeptiert (Engine-Check
        # check_completion handelt es als auto-complete-on-pass; siehe
        # Spec §2.2 Note).
        if not comp.get("source_file"):
            errors.append(
                f"step '{step_id}': pointer_check requires 'source_file' "
                f"(Spec 299 §2.1)"
            )
    # manual: no extra fields needed
    return errors


def _validate_guard(guard: dict[str, Any], step_id: str) -> list[str]:
    """Validate a guard definition. Returns list of errors."""
    errors: list[str] = []
    gtype = guard.get("type")
    if not gtype:
        errors.append(f"step '{step_id}': guard missing 'type'")
        return errors
    if gtype not in VALID_GUARD_TYPES:
        errors.append(f"step '{step_id}': unknown guard type '{gtype}'")
        return errors

    if gtype == "file_exists":
        if not guard.get("path"):
            errors.append(f"step '{step_id}': file_exists guard requires 'path'")
    elif gtype == "step_status":
        if not guard.get("step_id"):
            errors.append(f"step '{step_id}': step_status guard requires 'step_id'")
        if not guard.get("expected"):
            errors.append(f"step '{step_id}': step_status guard requires 'expected'")
    elif gtype == "route_active":
        if not guard.get("step_id"):
            errors.append(f"step '{step_id}': route_active guard requires 'step_id'")
        if not guard.get("route"):
            errors.append(f"step '{step_id}': route_active guard requires 'route'")
    elif gtype == "script" and not guard.get("command"):
        errors.append(f"step '{step_id}': script guard requires 'command'")
    # always_skip: no extra fields
    return errors


def validate_workflow_schema(data: dict[str, Any]) -> list[str]:
    """Validate a workflow definition dict. Returns list of error strings."""
    errors: list[str] = []

    # Top-level required fields
    for f in REQUIRED_WORKFLOW_FIELDS:
        if f not in data:
            errors.append(f"missing required field '{f}'")

    steps = data.get("steps")
    if not isinstance(steps, list):
        errors.append("'steps' must be a list")
        return errors

    step_ids: set[str] = set()
    all_route_step_ids: set[str] = set()  # steps referenced in any route

    for step in steps:
        if not isinstance(step, dict):
            errors.append("each step must be a mapping")
            continue

        sid = step.get("id", "<missing>")

        # Required fields
        for f in REQUIRED_STEP_FIELDS:
            if f not in step:
                errors.append(f"step '{sid}': missing required field '{f}'")

        # Unique ID
        if sid in step_ids:
            errors.append(f"duplicate step id '{sid}'")
        step_ids.add(sid)

        # Category validation
        cat = step.get("category")
        if cat and cat not in VALID_CATEGORIES:
            errors.append(f"step '{sid}': invalid category '{cat}'")

        # Classification + routes consistency
        routes = step.get("routes")
        if cat == "classification":
            if not routes:
                errors.append(f"step '{sid}': classification step must have 'routes'")
            elif isinstance(routes, dict):
                for _route_key, route_steps in routes.items():
                    if isinstance(route_steps, list):
                        all_route_step_ids.update(route_steps)
        elif routes:
            errors.append(f"step '{sid}': only classification steps may have 'routes'")

        # Completion
        comp = step.get("completion")
        if comp and isinstance(comp, dict):
            errors.extend(_validate_completion(comp, sid))

        # Guard
        guard = step.get("guard")
        if guard and isinstance(guard, dict):
            errors.extend(_validate_guard(guard, sid))

        # on_fail
        on_fail = step.get("on_fail")
        if on_fail and on_fail not in VALID_ON_FAIL:
            errors.append(f"step '{sid}': invalid on_fail '{on_fail}'")

    # depends_on: check references exist
    for step in steps:
        if not isinstance(step, dict):
            continue
        sid = step.get("id", "<missing>")
        deps = step.get("depends_on", [])
        if isinstance(deps, list):
            for dep in deps:
                if dep not in step_ids:
                    errors.append(f"step '{sid}': depends_on references unknown step '{dep}'")

    # Route step references: check they exist
    for ref_id in all_route_step_ids:
        if ref_id not in step_ids:
            errors.append(f"route references unknown step '{ref_id}'")

    # Cycle detection in depends_on
    errors.extend(_detect_cycles(steps))

    return errors


def _detect_cycles(steps: list[dict[str, Any]]) -> list[str]:
    """Detect cycles in depends_on graph using DFS."""
    errors: list[str] = []
    adj: dict[str, list[str]] = {}
    for step in steps:
        if not isinstance(step, dict):
            continue
        sid = step.get("id", "")
        deps = step.get("depends_on", [])
        adj[sid] = deps if isinstance(deps, list) else []

    _white, _gray, _black = 0, 1, 2
    color: dict[str, int] = dict.fromkeys(adj, _white)

    def dfs(node: str) -> bool:
        color[node] = _gray
        for nbr in adj.get(node, []):
            if nbr not in color:
                continue
            if color[nbr] == _gray:
                errors.append(f"dependency cycle detected involving '{nbr}'")
                return True
            if color[nbr] == _white and dfs(nbr):
                return True
        color[node] = _black
        return False

    for sid in adj:
        if color[sid] == _white:
            dfs(sid)

    return errors


# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------

def load_workflow_yaml(path: Path) -> dict[str, Any]:
    """Load and validate a workflow YAML file. Raises SchemaError on failure."""
    if not path.exists():
        raise SchemaError(f"File not found: {path}")
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as e:
        raise SchemaError(f"YAML parse error in {path}: {e}") from e

    if not isinstance(data, dict):
        raise SchemaError(f"{path}: expected a mapping at top level")

    errors = validate_workflow_schema(data)
    if errors:
        msg = f"Schema errors in {path.name}:\n" + "\n".join(f"  - {e}" for e in errors)
        raise SchemaError(msg)

    return data


def resolve_task_id(task_arg: str | int | None) -> int | None:
    """Resolve a task ID argument to int, or None."""
    if task_arg is None:
        return None
    try:
        return int(task_arg)
    except (ValueError, TypeError):
        return None
