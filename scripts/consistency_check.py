#!/usr/bin/env python3
"""consistency_check.py — Strukturelle Repo-Integritaet.

Library + CLI entry. Spec 299 Phase D extension: tier1-drift Check
(Spec §3.2). Pro `verification_tier: 1`-Skill prueft ob mindestens ein
workflow.yaml-Step Skill referenziert mit `completion.compound`-Sub-Check
`pointer_check`. Fehlt → WARN.

Other check-types in this module are placeholder for future migration of
`skills/consistency_check/REFERENCE.md` checks into Python.

Usage:
  python3 -m scripts.consistency_check --check tier1-drift
  python3 -m scripts.consistency_check --check tier1-drift \\
      --workflows-root <dir>
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    print("ERROR: PyYAML required.", file=sys.stderr)
    sys.exit(2)


_FRAMEWORK_ROOT = Path(__file__).resolve().parent.parent


def _read_skill_frontmatter(skill_md: Path) -> dict | None:
    try:
        text = skill_md.read_text(encoding="utf-8")
    except OSError:
        return None
    if not text.startswith("---"):
        return None
    parts = text.split("---", 2)
    if len(parts) < 3:
        return None
    try:
        data = yaml.safe_load(parts[1])
    except yaml.YAMLError:
        return None
    if not isinstance(data, dict):
        return None
    return data


def collect_tier1_skills(skills_roots: list[Path]) -> dict[str, Path]:
    """Find all Skills with verification_tier: 1.

    Returns dict mapping skill-dir-name → SKILL.md path.
    """
    found: dict[str, Path] = {}
    for root in skills_roots:
        if not root.is_dir():
            continue
        for skill_md in root.glob("*/SKILL.md"):
            fm = _read_skill_frontmatter(skill_md)
            if fm and fm.get("verification_tier") == 1:
                found[skill_md.parent.name] = skill_md
    return found


def collect_workflow_steps(workflows_root: Path) -> list[tuple[Path, dict, dict]]:
    """Yield (workflow_path, workflow_data, step_data) for each step in each
    workflow.yaml under workflows_root.
    """
    out: list[tuple[Path, dict, dict]] = []
    if not workflows_root.is_dir():
        return out
    for wf_yaml in workflows_root.rglob("workflow.yaml"):
        try:
            data = yaml.safe_load(wf_yaml.read_text(encoding="utf-8"))
        except (OSError, yaml.YAMLError):
            continue
        if not isinstance(data, dict):
            continue
        steps = data.get("steps", [])
        if not isinstance(steps, list):
            continue
        for step in steps:
            if isinstance(step, dict):
                out.append((wf_yaml, data, step))
    return out


def _step_has_pointer_check(step: dict) -> bool:
    """True wenn step.completion Spec §2.2 Convention erfuellt:
    `compound` mit `pointer_check` UND `manual` als sub-checks.

    CC-011 (F-CA-007) Pass-1-Fix: pre-fix akzeptierte top-level pointer_check
    auch als "protected", obwohl Spec §2.2 explizit sagt "Convention bleibt
    aber `compound` mit `pointer_check VOR manual` fuer alle Tier-1-Reviewer-
    Steps damit Reviewer-Persona explizit manuell abschliessen muss."
    Pre-fix war damit Compensation-Bug — Drift-Check faengt Konvention-
    Verletzung NICHT mehr.
    """
    comp = step.get("completion", {})
    if not isinstance(comp, dict):
        return False
    ctype = comp.get("type")
    # Spec §2.2 enforces compound[pointer_check, manual] for Tier-1.
    if ctype != "compound":
        return False
    checks = comp.get("checks", [])
    if not isinstance(checks, list):
        return False
    sub_types = [s.get("type") for s in checks if isinstance(s, dict)]
    return "pointer_check" in sub_types and "manual" in sub_types


def _step_has_top_level_pointer_check(step: dict) -> bool:
    """True wenn step.completion direkt pointer_check ohne compound-wrapper
    ist. Spec §2.2 erlaubt das schema-permissiv (auto-complete-on-pass), aber
    Convention prefer compound. CC-011 separater WARN-Pfad fuer Drift-Check."""
    comp = step.get("completion", {})
    if not isinstance(comp, dict):
        return False
    return comp.get("type") == "pointer_check"


def _ref_points_at(ref: str, skill_dir_name: str) -> bool:
    if not isinstance(ref, str):
        return False
    return f"/{skill_dir_name}/" in ref or ref.endswith(f"/{skill_dir_name}/SKILL.md")


def _step_skill_ref_matches(step: dict, skill_dir_name: str) -> bool:
    """True wenn step.skill_ref ODER ein Eintrag in step.alternative_skill_refs
    auf skill_dir_name zeigt. alternative_skill_refs deklariert die weiteren
    Skills, die ein Routing-/Dispatch-Step fahren kann (z.B. review board-dispatch
    routet spec_board / sectional_deep_review / architecture_coherence_review) —
    sie teilen das pointer_check-completion dieses Steps, also zaehlen sie als
    Tier-1-backed."""
    if _ref_points_at(step.get("skill_ref", ""), skill_dir_name):
        return True
    alts = step.get("alternative_skill_refs") or []
    if isinstance(alts, list):
        return any(_ref_points_at(a, skill_dir_name) for a in alts)
    return False


def check_tier1_drift(
    skills_roots: list[Path] | None = None,
    workflows_root: Path | None = None,
) -> tuple[int, list[str]]:
    """Tier-1-Drift-Check (Spec 299 §3.2).

    Pro Tier-1-Skill: mindestens 1 workflow.yaml-Step muss skill referenzieren
    UND completion.compound mit pointer_check enthalten. Fehlt → WARN.

    Returns (exit_code, warnings). exit_code 0 wenn keine Drift, 1 sonst.
    """
    skills_roots = skills_roots or [
        _FRAMEWORK_ROOT / "skills",
        _FRAMEWORK_ROOT / "framework" / "skills",
    ]
    workflows_root = workflows_root or (_FRAMEWORK_ROOT / "workflows" / "runbooks")

    tier1 = collect_tier1_skills(skills_roots)
    if not tier1:
        return 0, ["INFO: no tier-1 skills found"]

    steps = collect_workflow_steps(workflows_root)

    warnings: list[str] = []
    for skill_name in sorted(tier1):
        # Find any step that refs this skill AND has pointer_check
        protected = False
        any_ref = False
        # Track top-level pointer_check refs separately (CC-011 soft-WARN)
        top_level_only_steps: list[str] = []
        for _wf_path, _wf_data, step in steps:
            if _step_skill_ref_matches(step, skill_name):
                any_ref = True
                if _step_has_pointer_check(step):
                    protected = True
                    break
                if _step_has_top_level_pointer_check(step):
                    top_level_only_steps.append(step.get("id", "<no-id>"))
        if not any_ref:
            warnings.append(
                f"WARN tier1-drift: skill {skill_name!r} verification_tier: 1 "
                f"aber kein workflow.yaml-Step referenziert es."
            )
        elif not protected:
            warnings.append(
                f"WARN tier1-drift: skill {skill_name!r} verification_tier: 1 "
                f"aber kein referenzierender workflow.yaml-Step hat "
                f"completion.compound mit pointer_check + manual (Spec §2.2 "
                f"Convention)."
            )
        elif top_level_only_steps:
            # protected=True but ALSO has top-level-only refs — soft-WARN.
            warnings.append(
                f"INFO tier1-drift soft: skill {skill_name!r} hat top-level "
                f"pointer_check (steps: {', '.join(top_level_only_steps)}) — "
                f"schema-permissiv, aber Spec §2.2 prefer compound[pointer_check, manual]."
            )

    if warnings:
        return 1, warnings
    return 0, ["OK: alle tier-1 skills durch pointer_check-Steps geschuetzt"]


def check_tier1_multi_workflow_drift(
    skills_roots: list[Path] | None = None,
    workflows_root: Path | None = None,
) -> tuple[int, list[str]]:
    """ADV-TC-018 multi-workflow drift: pro Tier-1-Skill alle Workflows pruefen
    die ihn referenzieren. Wenn IRGENDEIN referenzierender Workflow KEIN
    pointer_check hat → WARN (nicht nur 'min 1 Workflow OK')."""
    skills_roots = skills_roots or [
        _FRAMEWORK_ROOT / "skills",
        _FRAMEWORK_ROOT / "framework" / "skills",
    ]
    workflows_root = workflows_root or (_FRAMEWORK_ROOT / "workflows" / "runbooks")

    tier1 = collect_tier1_skills(skills_roots)
    steps = collect_workflow_steps(workflows_root)

    warnings: list[str] = []
    for skill_name in sorted(tier1):
        # Per-workflow-file: hat dieser Workflow den Skill referenziert? Wenn
        # ja, hat min. einer dieser Refs pointer_check (compound + manual,
        # CC-011 strikter)?
        per_wf: dict[Path, dict[str, bool]] = {}
        for wf_path, _wf, step in steps:
            if _step_skill_ref_matches(step, skill_name):
                d = per_wf.setdefault(wf_path, {"any": False, "protected": False})
                d["any"] = True
                if _step_has_pointer_check(step):
                    d["protected"] = True
        for wf_path, d in per_wf.items():
            if d["any"] and not d["protected"]:
                warnings.append(
                    f"WARN tier1-drift (multi-workflow): skill {skill_name!r} "
                    f"in workflow {wf_path.parent.name!r} referenziert ohne "
                    f"compound[pointer_check, manual] (Spec §2.2 Convention)."
                )

    if warnings:
        return 1, warnings
    return 0, ["OK: kein multi-workflow tier1-drift"]


_VALID_CLASSES = {"STRUCTURAL", "GATE", "WORKFLOW", "DISCIPLINE"}


def check_enforcement_registry(
    registry_path: Path | None = None,
) -> tuple[int, list[str]]:
    """Check 11: validate framework/enforcement-registry.md integrity.

    Every row of the Live table must (a) carry exactly one valid class
    tag and (b) name an artifact pointer that resolves on disk. A stale
    pointer is the phantom-enforcement failure class the registry exists
    to prevent → ERROR.
    """
    registry_path = registry_path or (
        _FRAMEWORK_ROOT / "framework" / "enforcement-registry.md"
    )
    if not registry_path.is_file():
        return 1, [f"ERROR enforcement-registry: not found at {registry_path}"]

    text = registry_path.read_text(encoding="utf-8")
    lines = text.splitlines()

    # Slice the Live-mechanisms section (## Live ... until next ## ).
    in_live = False
    table_rows: list[str] = []
    for ln in lines:
        if ln.startswith("## "):
            in_live = ln.startswith("## Live")
            continue
        if in_live and ln.lstrip().startswith("|"):
            table_rows.append(ln.strip())

    if not table_rows:
        return 1, ["ERROR enforcement-registry: no Live table found"]

    errors: list[str] = []
    checked = 0
    for row in table_rows:
        cells = [c.strip() for c in row.strip("|").split("|")]
        if len(cells) < 5:
            continue
        mechanism, cls_raw, _sev, artifact_raw = cells[0], cells[1], cells[2], cells[3]
        # Skip header + separator rows.
        if mechanism.lower() == "mechanism" or set(mechanism) <= {"-", ":", " "}:
            continue
        checked += 1

        cls = cls_raw.strip("`[] ")
        if cls not in _VALID_CLASSES:
            errors.append(
                f"ERROR enforcement-registry: row {mechanism!r} has invalid "
                f"class {cls_raw!r} (must be one of {sorted(_VALID_CLASSES)})"
            )

        # Extract the first backticked token as the artifact path; strip a
        # trailing '§...' section suffix.
        m = re.search(r"`([^`]+)`", artifact_raw)
        if not m:
            errors.append(
                f"ERROR enforcement-registry: row {mechanism!r} has no "
                f"backticked artifact pointer (got {artifact_raw!r})"
            )
            continue
        path_token = m.group(1).split("§", 1)[0].strip()
        if not (_FRAMEWORK_ROOT / path_token).exists():
            errors.append(
                f"ERROR enforcement-registry: row {mechanism!r} artifact "
                f"{path_token!r} does not resolve on disk"
            )

    if errors:
        return 1, errors
    return 0, [f"OK: enforcement-registry — {checked} live rows resolve + tagged"]


def _main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="consistency_check — Repo-Integritaet (Spec 299 Phase D).",
    )
    parser.add_argument(
        "--check",
        choices=("tier1-drift", "tier1-multi-workflow-drift", "enforcement-registry"),
        required=True,
        help="Welcher Check ausgefuehrt werden soll.",
    )
    parser.add_argument(
        "--workflows-root", default=None,
        help="Override workflows-runbooks-root (default framework workflows/runbooks).",
    )

    args = parser.parse_args(argv)

    workflows_root = Path(args.workflows_root) if args.workflows_root else None

    if args.check == "tier1-drift":
        exit_code, warnings = check_tier1_drift(workflows_root=workflows_root)
    elif args.check == "tier1-multi-workflow-drift":
        exit_code, warnings = check_tier1_multi_workflow_drift(
            workflows_root=workflows_root,
        )
    elif args.check == "enforcement-registry":
        exit_code, warnings = check_enforcement_registry()
    else:
        print(f"ERROR: unknown check {args.check!r}", file=sys.stderr)
        return 2

    out = sys.stderr if exit_code != 0 else sys.stdout
    for w in warnings:
        print(w, file=out)

    return exit_code


if __name__ == "__main__":
    sys.exit(_main())
