#!/usr/bin/env python3
"""consistency_check.py — Strukturelle Repo-Integritaet.

Library + CLI entry. Tier1-drift Check
(Spec §3.2). Pro `verification_tier: 1`-Skill prueft ob mindestens ein
workflow.yaml-Step Skill referenziert mit `completion.compound`-Sub-Check
`pointer_check`. Fehlt → WARN.

Other check-types in this module are placeholder for future migration of
`skills/consistency_check/REFERENCE.md` checks into Python.

Usage:
  python3 -m scripts.consistency_check --check tier1-drift
  python3 -m scripts.consistency_check --check tier1-drift \\
      --workflows-root <dir>
  python3 $FRAMEWORK_DIR/scripts/consistency_check.py --check brief-acceptance --brief <path>
      (run from the project root; compares the brief's approved-acceptance block
      with docs/tasks/<id>.yaml)
  python3 $FRAMEWORK_DIR/scripts/consistency_check.py --check spine --spine <path>
      (run from the project root; checks an architecture spine's form, parent paths
      resolved from that root)
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    print("ERROR: PyYAML required.", file=sys.stderr)
    sys.exit(2)


_FRAMEWORK_ROOT = Path(__file__).resolve().parent.parent

# Make the sibling _plan_engine package importable whether this module is run
# as `python3 -m scripts.consistency_check` (framework root on sys.path) or
# imported by plan_engine's shim (scripts/ already on sys.path). The autonomy
# consistency check (relocated here from plan_engine) returns ValidationIssue
# objects so the --validate pre-commit BLOCK keeps rendering them unchanged.
_SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
if _SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, _SCRIPTS_DIR)

from _plan_engine.core import ValidationIssue  # noqa: E402
from user_scope import ENTRY_UNITS  # noqa: E402


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

    pre-fix akzeptierte top-level pointer_check
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
    Convention prefer compound. Separater WARN-Pfad fuer Drift-Check."""
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


def _step_tier1_exempt(step: dict) -> bool:
    """True when the step declares `tier1_pointer_exempt: <reason>`: its
    artifact has no engine-resolvable path (e.g. a <date>-<topic> council
    output, a conditional spec patch), so a pointer_check would create a
    stale-pointer class. The reason must be a non-empty string; a bare
    `true` does not count."""
    reason = step.get("tier1_pointer_exempt")
    return isinstance(reason, str) and bool(reason.strip())


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
        # Track top-level pointer_check refs separately (soft-WARN)
        top_level_only_steps: list[str] = []
        for _wf_path, _wf_data, step in steps:
            if _step_skill_ref_matches(step, skill_name):
                any_ref = True
                if _step_has_pointer_check(step) or _step_tier1_exempt(step):
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
        # strikter)?
        per_wf: dict[Path, dict[str, bool]] = {}
        for wf_path, _wf, step in steps:
            if _step_skill_ref_matches(step, skill_name):
                d = per_wf.setdefault(wf_path, {"any": False, "protected": False})
                d["any"] = True
                if _step_has_pointer_check(step) or _step_tier1_exempt(step):
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


# ---------------------------------------------------------------------------
# Autonomy Consistency (framework/agent-autonomy.md SoT)
# ---------------------------------------------------------------------------

# SoT-Datei der Autonomy-Regeln. Mirror-Check, Existenz-Check und Referenz-
# Integritaet werden gegen dieses Dokument gefahren.
# Framework-intern → _FRAMEWORK_ROOT.
AUTONOMY_SOT_PATH = _FRAMEWORK_ROOT / "framework" / "agent-autonomy.md"

# Dateien, in denen der Verweis auf framework/agent-autonomy.md existieren
# MUSS (Check 3, Referenz-Integritaet). Relativ zu _FRAMEWORK_ROOT.
AUTONOMY_REFERENCE_FILES = [
    "framework/invariants.md",
    "agents/buddy/operational.md",
    "agents/buddy/delegation.md",
    "workflows/runbooks/solve/WORKFLOW.md",
]


def _extract_sections_containing(text: str, needle: str) -> dict[str, str]:
    """Extrahiere alle `###`-Sektionen, deren Inhalt `needle` enthaelt.

    Rueckgabe: dict mapping `title_key → section_text` (inkl. Header-Zeile bis
    zum naechsten gleich- oder hoeherrangigen Header). Der `title_key` ist der
    Header-Text ohne Prefix-`### ` und ohne fuehrende Sektions-Nummer
    (`5. `, `5.1 `, etc.) — das erlaubt robustes Matching zwischen zwei
    Dateien, auch wenn die Nummerierung auseinanderlaeuft.

    Hintergrund: Der Mirror-Check darf nicht mehr an die feste
    Header-Nummer `### 5. Code-Delegation` gebunden sein. Stattdessen werden
    alle Sektionen gespiegelt, die den SoT-Pfad `framework/agent-autonomy.md`
    erwaehnen.
    """
    import re
    lines = text.split("\n")
    # Indizes der `###`-Header (und Ende bei `##` oder `#`).
    header_indices: list[int] = []
    for i, line in enumerate(lines):
        if line.startswith("### "):
            header_indices.append(i)
        elif line.startswith(("## ", "# ")):
            header_indices.append(i)  # Sentinel als Grenze
    # Fuer jeden `###`-Header die Sektion bis zum naechsten Header extrahieren.
    num_prefix_re = re.compile(r"^\d+(?:\.\d+)*\.?\s+")
    result: dict[str, str] = {}
    for idx, start in enumerate(header_indices):
        if not lines[start].startswith("### "):
            continue
        # Ende = naechster Header-Index (egal welche Ebene)
        end = len(lines)
        if idx + 1 < len(header_indices):
            end = header_indices[idx + 1]
        section = "\n".join(lines[start:end])
        if needle not in section:
            continue
        # Title-Key normalisieren: `### 5. Code-Delegation / Autonomy` →
        # `code-delegation / autonomy`
        header_line = lines[start][4:].strip()  # strip "### "
        title_key = num_prefix_re.sub("", header_line).strip().lower()
        # Kollisionen: bei Duplicate-Headern vermeiden wir Overwrite indem
        # wir nur den ersten behalten — Duplicate-Warnung ist out-of-scope.
        if title_key not in result:
            result[title_key] = section
    return result


def validate_autonomy_consistency() -> list[ValidationIssue]:
    """Autonomy-Consistency-Checks.

    Prueffaelle:
      Check 1 — single home: framework/invariants.md carries the autonomy anchor,
                no adapter repeats it (ERROR otherwise)
      Check 2 — Existenz-Check framework/agent-autonomy.md (ERROR bei Fehlern)
      Check 3 — Referenz-Integritaet in Konsumenten-Dateien (ERROR pro fehlendem Verweis)
    """
    import re
    issues: list[ValidationIssue] = []

    # Check 1: single home of the autonomy anchor. The framework-wide
    # invariants live once, in framework/invariants.md; its `###` sections that
    # name the SoT path are the Tier-0 anchor. CLAUDE.md and AGENTS.md keep the
    # forge repository's own rules and carry no second copy of such a section.
    unit_path = _FRAMEWORK_ROOT / "framework" / "invariants.md"
    if not unit_path.exists():
        issues.append(ValidationIssue(
            "AUTONOMY_MIRROR", "ERROR",
            detail="framework/invariants.md missing — no Tier-0 autonomy anchor"))
    elif not _extract_sections_containing(
            unit_path.read_text(encoding="utf-8"), "framework/agent-autonomy.md"):
        issues.append(ValidationIssue(
            "AUTONOMY_MIRROR", "ERROR",
            detail=("framework/invariants.md: no '###' section names "
                    "'framework/agent-autonomy.md' — Tier-0 anchor missing")))
    for adapter in ("CLAUDE.md", "AGENTS.md"):
        adapter_path = _FRAMEWORK_ROOT / adapter
        if not adapter_path.exists():
            continue
        copies = _extract_sections_containing(
            adapter_path.read_text(encoding="utf-8"), "framework/agent-autonomy.md")
        for title_key in copies:
            issues.append(ValidationIssue(
                "AUTONOMY_MIRROR", "ERROR",
                detail=(f"{adapter}: section '{title_key}' repeats the autonomy "
                        "anchor that lives in framework/invariants.md — keep one home")))

    # Check 2: Existenz-Check framework/agent-autonomy.md
    autonomy_text = ""
    if not AUTONOMY_SOT_PATH.exists():
        issues.append(ValidationIssue(
            "AUTONOMY_EXISTS", "ERROR",
            detail=f"{AUTONOMY_SOT_PATH.relative_to(_FRAMEWORK_ROOT)} fehlt — "
                   "SoT fuer Permission/Gate/Routing nicht vorhanden"))
    else:
        autonomy_text = AUTONOMY_SOT_PATH.read_text(encoding="utf-8")
        # Header "# Agent Autonomy"
        if not re.search(r"^# Agent Autonomy\s*$", autonomy_text, re.MULTILINE):
            issues.append(ValidationIssue(
                "AUTONOMY_EXISTS", "ERROR",
                detail=f"{AUTONOMY_SOT_PATH.relative_to(_FRAMEWORK_ROOT)}: "
                       "Header '# Agent Autonomy' fehlt"))
        # Section "## Tabelle — Artefakt-Typ → Autonomy" (DE) or
        # "## Table — artifact type -> autonomy" (EN).
        # Match either German or English header form.
        table_header_found = False
        for line in autonomy_text.split("\n"):
            if not line.startswith("## "):
                continue
            line_lower = line.lower()
            de_match = ("tabelle" in line_lower and "artefakt-typ" in line_lower)
            en_match = ("table" in line_lower and "artifact" in line_lower
                        and "type" in line_lower)
            if de_match or en_match:
                table_header_found = True
                break
        if not table_header_found:
            issues.append(ValidationIssue(
                "AUTONOMY_EXISTS", "ERROR",
                detail=f"{AUTONOMY_SOT_PATH.relative_to(_FRAMEWORK_ROOT)}: "
                       "section header with 'Tabelle'+'Artefakt-Typ' (DE) or "
                       "'Table'+'artifact'+'type' (EN) missing"))

    # Check 3: Referenz-Integritaet in Konsumenten-Dateien
    for rel_path in AUTONOMY_REFERENCE_FILES:
        file_path = _FRAMEWORK_ROOT / rel_path
        if not file_path.exists():
            issues.append(ValidationIssue(
                "AUTONOMY_REF", "ERROR",
                detail=f"{rel_path}: Datei fehlt, Referenz-Check nicht moeglich"))
            continue
        content = file_path.read_text(encoding="utf-8")
        # Als Pfad-String oder Markdown-Link. Suche nach dem Pfad-Fragment.
        if "framework/agent-autonomy.md" not in content:
            issues.append(ValidationIssue(
                "AUTONOMY_REF", "ERROR",
                detail=f"{rel_path}: kein Verweis auf "
                       "'framework/agent-autonomy.md' gefunden — Konsument "
                       "muss auf SoT verweisen"))

    return issues


# ---------------------------------------------------------------------------
# Instruction-unit size guard
# ---------------------------------------------------------------------------

# Strictest host budget: Claude Code restores a file after compaction only up to 5,000 tokens
# (about 13,900 bytes at the measured ratio); 12,000 leaves headroom, far below Codex's 10,000-token tool output.
INSTRUCTION_UNIT_BUDGET = 12_000

# Codex cuts tool output at 10,000 tokens: 28,000 bytes at the conservative 2.8 B/token; the largest lookup measured
# 6,503 o200k_base tokens (about 7,350 Codex tokens).
LOOKUP_READ_CEILING = 28_000

# Framework-relative globs whose files are read as instruction text at a step.
# Not enumerated: top-level agents/*.md (sub-agent personas, injected by the host as a system prompt) and every
# workflow.yaml (engine data; the workflow engine prints one step's instruction).
INSTRUCTION_UNIT_GLOBS = (
    "agents/buddy/*.md",
    "agents/_protocols/*.md",
    "framework/**/*.md",
    "skills/**/*.md",
    "workflows/runbooks/**/*.md",
    "workflows/templates/*.yaml",
    "orchestrators/*/rules/*.md",
)
INSTRUCTION_UNIT_FILES = ("CLAUDE.md", "AGENTS.md")

# Lookup references: read for one entry at the step, so the binding limit is whole arrival at that read.
LOOKUP_REFERENCES: tuple[tuple[str, str], ...] = (
    ("framework/adopted-methods.md", "one adopted method's row"),
    ("framework/adopted-methods-superpowers.md", "one adopted method's row"),
    ("framework/enforcement-registry.md", "one rule's row"),
    ("skills/code_review_board/REFERENCE.md", "one row or schema per question"),
    ("skills/consistency_check/REFERENCE-drift.md", "one check's detail at that check"),
    ("skills/consistency_check/REFERENCE.md", "one check's detail at that check"),
    ("skills/navigation.md", "route index"),
    ("skills/testing/eval_patterns/fastapi.md", "one stack's patterns"),
    ("skills/testing/eval_patterns/postgres.md", "one stack's patterns"),
    ("workflows/templates/spec-board-convergence.yaml", "board mechanics by key"),
    ("workflows/templates/spec-board.yaml", "board mechanics by key"),
)


def required_units() -> list[str]:
    """Files that must exist: the boot entry list and the forge soul."""
    units = {unit.path for unit in ENTRY_UNITS}
    units.add("agents/buddy/soul.md")
    return sorted(units)


def instruction_units(root: Path | None = None) -> list[str]:
    """Framework-relative paths of every enumerated file that is not a listed lookup, sorted."""
    root = root or _FRAMEWORK_ROOT
    lookups = {rel for rel, _ in LOOKUP_REFERENCES}
    found = {
        path.relative_to(root).as_posix()
        for pattern in INSTRUCTION_UNIT_GLOBS
        for path in root.glob(pattern)
        if path.is_file()
    }
    found.update(rel for rel in INSTRUCTION_UNIT_FILES if (root / rel).is_file())
    return sorted(found - lookups)


def check_instruction_units(root: Path | None = None) -> tuple[int, list[str]]:
    """Every enumerated unit is at most INSTRUCTION_UNIT_BUDGET bytes, every listed lookup exists and is at most
    LOOKUP_READ_CEILING bytes, and every required unit exists."""
    root = root or _FRAMEWORK_ROOT
    units = instruction_units(root)
    errors = [f"{rel}: missing" for rel in required_units() if not (root / rel).is_file()]
    for rel in units:
        size = (root / rel).stat().st_size
        if size > INSTRUCTION_UNIT_BUDGET:
            errors.append(f"{rel}: {size} bytes > {INSTRUCTION_UNIT_BUDGET} (unit)")
    for rel, _ in LOOKUP_REFERENCES:
        path = root / rel
        if not path.is_file():
            errors.append(f"{rel}: missing")
            continue
        size = path.stat().st_size
        if size > LOOKUP_READ_CEILING:
            errors.append(f"{rel}: {size} bytes > {LOOKUP_READ_CEILING} (lookup)")
    if errors:
        return 1, errors
    return 0, [
        f"OK: instruction-units — {len(units)} units within {INSTRUCTION_UNIT_BUDGET} bytes, "
        f"{len(LOOKUP_REFERENCES)} lookups within {LOOKUP_READ_CEILING} bytes"
    ]


# ---------------------------------------------------------------------------
# Brief acceptance copy (contract: skills/_protocols/approved-acceptance.md §The check)
# ---------------------------------------------------------------------------

BRIEF_ACCEPTANCE_TITLE = "Approved acceptance (read-only)"
BRIEF_ACCEPTANCE_KEYS = ("task", "acceptance_criteria", "out_of_scope", "approved_by")
_FENCE_OPEN_RE = re.compile(r"^ {0,3}(`{3,}|~{3,})(.*)$")
_HEADING_RE = re.compile(r"^ {0,3}(#{1,6})\s+(.+?)\s*#*\s*$")


class _BriefAcceptanceError(Exception):
    """One reason the brief's copy cannot be established as an exact match."""


class _UniqueKeyLoader(yaml.SafeLoader):
    """SafeLoader that rejects a mapping key given twice or a key that cannot be a mapping key."""

    def construct_mapping(self, node, deep=False):
        self.flatten_mapping(node)
        result = {}
        for key_node, value_node in node.value:
            key = self.construct_object(key_node, deep=deep)
            try:
                hash(key)
            except TypeError:
                raise _BriefAcceptanceError(
                    f"unhashable YAML mapping key {key!r} (line {key_node.start_mark.line + 1})"
                ) from None
            if key in result:
                raise _BriefAcceptanceError(f"duplicate YAML key {key!r} (line {key_node.start_mark.line + 1})")
            result[key] = self.construct_object(value_node, deep=deep)
        return result


def _load_unique_yaml(text: str, where: str):
    try:
        return yaml.load(text, Loader=_UniqueKeyLoader)  # noqa: S506 - SafeLoader subclass
    except _BriefAcceptanceError as exc:
        raise _BriefAcceptanceError(f"{where}: {exc}") from None
    except yaml.YAMLError as exc:
        detail = " ".join(str(exc).split())
        raise _BriefAcceptanceError(f"{where}: invalid YAML ({detail})") from None
    except RecursionError:
        raise _BriefAcceptanceError(f"{where}: YAML nested too deeply to parse") from None


def _fence_closes(line: str, fence: tuple[str, int]) -> bool:
    return re.fullmatch(rf" {{0,3}}{re.escape(fence[0])}{{{fence[1]},}}\s*", line) is not None


def _acceptance_section(lines: list[str]) -> list[tuple[int, str]]:
    """Body lines (1-based number, text) of the one level-2 acceptance section, headings inside fences ignored."""
    sections: list[list[tuple[int, str]]] = []
    current: list[tuple[int, str]] | None = None
    fence: tuple[str, int] | None = None
    fence_line = 0
    for number, line in enumerate(lines, start=1):
        if fence:
            if current is not None:
                current.append((number, line))
            if _fence_closes(line, fence):
                fence = None
            continue
        marker = _FENCE_OPEN_RE.match(line)
        if marker:
            fence = (marker[1][0], len(marker[1]))
            fence_line = number
        else:
            heading = _HEADING_RE.match(line)
            if heading and len(heading[1]) <= 2:
                current = None
                if len(heading[1]) == 2 and heading[2].removeprefix("§").strip() == BRIEF_ACCEPTANCE_TITLE:
                    current = []
                    sections.append(current)
                continue
        if current is not None:
            current.append((number, line))
    if fence:
        raise _BriefAcceptanceError(f"unterminated code fence opened at line {fence_line}")
    if not sections:
        raise _BriefAcceptanceError(f"missing block: no '## {BRIEF_ACCEPTANCE_TITLE}' section")
    if len(sections) > 1:
        raise _BriefAcceptanceError(f"{len(sections)} '## {BRIEF_ACCEPTANCE_TITLE}' sections; exactly one allowed")
    return sections[0]


def _acceptance_yaml(body: list[tuple[int, str]]) -> str:
    """Text of the one yaml/yml fenced block directly in the section body."""
    payloads: list[list[str]] = []
    block: list[str] | None = None
    fence: tuple[str, int] | None = None
    for _number, line in body:
        if fence:
            if _fence_closes(line, fence):
                if block is not None:
                    payloads.append(block)
                fence, block = None, None
            elif block is not None:
                block.append(line)
            continue
        marker = _FENCE_OPEN_RE.match(line)
        if marker:
            fence = (marker[1][0], len(marker[1]))
            block = [] if marker[2].strip().lower() in {"yaml", "yml"} else None
    if len(payloads) != 1:
        raise _BriefAcceptanceError(
            f"the '{BRIEF_ACCEPTANCE_TITLE}' section needs exactly one ```yaml block, found {len(payloads)}"
        )
    return "\n".join(payloads[0])


def _string_list(value, where: str) -> list[str]:
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise _BriefAcceptanceError(f"{where} must be a list of strings")
    return value


def _task_id(value, where: str) -> int:
    if isinstance(value, int) and not isinstance(value, bool) and value >= 0:
        return value
    if isinstance(value, str) and value.isascii() and value.isdigit():
        return int(value)
    raise _BriefAcceptanceError(f"{where} must be a task number (got {value!r})")


def _read_block(brief: Path) -> dict:
    try:
        text = brief.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise _BriefAcceptanceError(f"cannot read brief {brief}: {exc}") from None
    payload = _load_unique_yaml(_acceptance_yaml(_acceptance_section(text.splitlines())), "block")
    if not isinstance(payload, dict):
        raise _BriefAcceptanceError("block: the YAML must be a mapping")
    keys = set(payload)
    if keys != set(BRIEF_ACCEPTANCE_KEYS):
        missing = sorted(set(BRIEF_ACCEPTANCE_KEYS) - keys)
        unknown = sorted(str(k) for k in keys - set(BRIEF_ACCEPTANCE_KEYS))
        raise _BriefAcceptanceError(
            f"block: keys must be exactly {', '.join(BRIEF_ACCEPTANCE_KEYS)} "
            f"(missing: {missing or 'none'}; unknown: {unknown or 'none'})"
        )
    approved_by = payload["approved_by"]
    if not isinstance(approved_by, str) or not approved_by.strip():
        raise _BriefAcceptanceError("block: approved_by must be a nonblank string")
    return {
        "task": _task_id(payload["task"], "block: task"),
        "acceptance_criteria": _string_list(payload["acceptance_criteria"], "block: acceptance_criteria"),
        "out_of_scope": _string_list(payload["out_of_scope"], "block: out_of_scope"),
    }


def _find_task_file(task: int, project_root: Path) -> Path:
    tasks = project_root / "docs" / "tasks"
    names = dict.fromkeys((f"{task}.yaml", f"{task:03d}.yaml"))
    for directory in (tasks, tasks / "archive"):
        for name in names:
            candidate = directory / name
            if candidate.is_file():
                return candidate
    raise _BriefAcceptanceError(f"task file not found for task {task} under {tasks} (archive included)")


def _list_differences(name: str, task_items: list[str], brief_items: list[str], task_label: str) -> list[str]:
    out: list[str] = []
    if len(task_items) != len(brief_items):
        out.append(f"{name}: {task_label} has {len(task_items)} items, the brief has {len(brief_items)}")
    for index in range(max(len(task_items), len(brief_items))):
        in_task = task_items[index] if index < len(task_items) else None
        in_brief = brief_items[index] if index < len(brief_items) else None
        if in_task == in_brief:
            continue
        if in_brief is None:
            out.append(f"{name}[{index}] missing from the brief; {task_label}: {in_task!r}")
        elif in_task is None:
            out.append(f"{name}[{index}] extra in the brief: {in_brief!r}; {task_label} has no item {index}")
        else:
            out.append(f"{name}[{index}] differs; {task_label}: {in_task!r}; brief: {in_brief!r}")
    return out


def check_brief_acceptance(brief: Path, project_root: Path | None = None) -> tuple[int, list[str]]:
    """The brief's `## Approved acceptance (read-only)` block equals the task file's acceptance_criteria and
    out_of_scope item by item. The task file is read, never written. Fails closed on any input it cannot read."""
    project_root = Path.cwd() if project_root is None else project_root
    brief = Path(brief)
    prefix = "ERROR brief-acceptance:"
    try:
        block = _read_block(brief)
        task_file = _find_task_file(block["task"], project_root)
        try:
            task_text = task_file.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as exc:
            raise _BriefAcceptanceError(f"cannot read task file {task_file}: {exc}") from None
        task_label = (Path("docs/tasks") / task_file.relative_to(project_root / "docs" / "tasks")).as_posix()
        task_data = _load_unique_yaml(task_text, task_label)
        if not isinstance(task_data, dict):
            raise _BriefAcceptanceError(f"{task_label}: not a mapping")
        if "id" not in task_data or _task_id(task_data["id"], f"{task_label}: id") != block["task"]:
            raise _BriefAcceptanceError(
                f"{task_label}: id {task_data.get('id')!r} does not match the block's task {block['task']}"
            )
        task_criteria = _string_list(task_data.get("acceptance_criteria"), f"{task_label}: acceptance_criteria")
        exclusions = task_data.get("out_of_scope")
        task_exclusions = [] if exclusions is None else _string_list(exclusions, f"{task_label}: out_of_scope")
    except _BriefAcceptanceError as exc:
        return 1, [f"{prefix} {brief}: {exc}"]

    errors = _list_differences("acceptance_criteria", task_criteria, block["acceptance_criteria"], task_label)
    errors += _list_differences("out_of_scope", task_exclusions, block["out_of_scope"], task_label)
    if errors:
        return 1, [f"{prefix} {brief}: the block differs from {task_label}"] + [f"{prefix} {e}" for e in errors]
    return 0, [
        f"OK: brief-acceptance — {brief} matches {task_label} "
        f"({len(task_criteria)} criteria, {len(task_exclusions)} exclusions)"
    ]


# ---------------------------------------------------------------------------
# Architecture spine form (contract: skills/_protocols/architecture-spine.md §Format)
# ---------------------------------------------------------------------------

SPINE_ALTITUDES = ("initiative", "feature", "unit")
SPINE_REQUIRED_FIELDS = ("Binds", "Prevents", "Rule", "Settled")
SPINE_DEFERRED_REASONS = ("one unit", "readable", "no trade-off", "can wait")
_SPINE_AD_RE = re.compile(r"AD-(\d+)\b")
_SPINE_FIELD_RE = re.compile(r"^\s*-\s+\*\*([A-Za-z]+):\*\*\s*(.*)$")
_SPINE_DEFERRED_RE = re.compile(
    r"^-\s+\S.*?\s+—\s+(" + "|".join(re.escape(r) for r in SPINE_DEFERRED_REASONS) + r"):\s*\S"
)
_SPINE_INHERITED_RE = re.compile(r"^AD-(\d+)\s+\(([^()]+)\)$")
_SPINE_PLACEHOLDER_RE = re.compile(r"(?<![\w-])(?:TBD|TODO|FIXME)(?![\w-])|(?<!\w)<[a-z][^<>]*>")


def _spine_lines(text: str) -> list[tuple[int, str]]:
    """(1-based number, text) of every line outside code fences; an unterminated fence is an error."""
    out: list[tuple[int, str]] = []
    fence: tuple[str, int] | None = None
    fence_line = 0
    for number, line in enumerate(text.splitlines(), start=1):
        if fence:
            if _fence_closes(line, fence):
                fence = None
            continue
        marker = _FENCE_OPEN_RE.match(line)
        if marker:
            fence = (marker[1][0], len(marker[1]))
            fence_line = number
            continue
        out.append((number, line))
    if fence:
        raise _BriefAcceptanceError(f"unterminated code fence opened at line {fence_line}")
    return out


def _spine_sections(lines: list[tuple[int, str]]) -> tuple[list[tuple[int, str]], dict, list[str]]:
    """The lines before the first level-2 heading, the body of each level-2 section, and errors."""
    head: list[tuple[int, str]] = []
    sections: dict[str, list[tuple[int, str]]] = {}
    errors: list[str] = []
    current = head
    for number, line in lines:
        heading = _HEADING_RE.match(line)
        if heading and len(heading[1]) == 2:
            name = heading[2].strip()
            if name in sections:
                errors.append(f"line {number}: second '## {name}' section")
            current = sections.setdefault(name, [])
            continue
        current.append((number, line))
    return head, sections, errors


def _spine_ad_ids(path: Path) -> set[int]:
    """AD numbers declared as level-3 headings in another spine (fails closed when unreadable)."""
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise _BriefAcceptanceError(f"cannot read parent spine {path}: {exc}") from None
    _head, sections, _errors = _spine_sections(_spine_lines(text))
    ids = set()
    for _number, line in sections.get("Decisions", []):
        heading = _HEADING_RE.match(line)
        if heading and len(heading[1]) == 3:
            match = _SPINE_AD_RE.match(heading[2])
            if match:
                ids.add(int(match[1]))
    return ids


def _spine_decisions(body: list[tuple[int, str]]) -> tuple[int, list[str]]:
    errors: list[str] = []
    blocks: list[tuple[int, int, dict[str, str]]] = []
    for number, line in body:
        heading = _HEADING_RE.match(line)
        if heading:
            match = _SPINE_AD_RE.match(heading[2]) if len(heading[1]) == 3 else None
            if not match:
                errors.append(f"line {number}: '{line.strip()}' is not an '### AD-<n> — <decision>' heading")
                continue
            blocks.append((number, int(match[1]), {}))
            continue
        field = _SPINE_FIELD_RE.match(line)
        if field and blocks:
            fields = blocks[-1][2]
            if field[1] in fields:
                errors.append(f"line {number}: AD-{blocks[-1][1]} gives {field[1]} twice")
            fields[field[1]] = field[2].strip()
        elif line.strip() and not blocks:
            errors.append(f"line {number}: text in '## Decisions' before the first AD heading")
    previous = 0
    for number, ad, fields in blocks:
        if ad <= previous:
            errors.append(f"line {number}: AD-{ad} does not ascend (follows AD-{previous}); IDs are never reused")
        previous = max(previous, ad)
        for name in SPINE_REQUIRED_FIELDS:
            if not fields.get(name):
                errors.append(f"line {number}: AD-{ad} has no nonblank {name}")
        settled = fields.get("Settled", "")
        if settled and not re.match(r"proposed\b|(asked|adopted):\s*\S", settled):
            errors.append(f"line {number}: AD-{ad} Settled must be 'proposed', 'asked: …' or 'adopted: …'")
    return len(blocks), errors


def _spine_deferred(body: list[tuple[int, str]]) -> tuple[int, list[str]]:
    items: list[tuple[int, str]] = []
    for number, line in body:
        if items and line[:1].isspace() and line.strip():
            items[-1] = (items[-1][0], f"{items[-1][1]} {line.strip()}")
        elif line.strip():
            items.append((number, line.strip()))
    if not items:
        return 0, ["'## Deferred' has no entry; with nothing left write '- none'"]
    if [text for _n, text in items] == ["- none"]:
        return 0, []
    errors = []
    for number, text in items:
        if not _SPINE_DEFERRED_RE.match(text):
            errors.append(
                f"line {number}: Deferred entry needs '- <candidate> — <reason>: <detail>' with a reason of "
                f"{', '.join(SPINE_DEFERRED_REASONS)}: {text!r}"
            )
    return len(items), errors


def _spine_inherited(body: list[tuple[int, str]], project_root: Path, parent: str) -> tuple[int, list[str]]:
    errors: list[str] = []
    rows = 0
    ids: set[int] | None = None
    if [line.strip() for _n, line in body if line.strip()] == ["- none"]:
        return 0, []
    for number, line in body:
        text = line.strip()
        if not text:
            continue
        if not text.startswith("|"):
            errors.append(f"line {number}: '## Inherited' holds only its table")
            continue
        cells = [c.strip() for c in text.strip("|").split("|")]
        if set(text) <= set("|-: ") or cells[0] == "Parent decision":
            continue
        rows += 1
        match = _SPINE_INHERITED_RE.match(cells[0].strip("`"))
        if not match or len(cells) < 2 or not cells[1]:
            errors.append(f"line {number}: inherited row needs 'AD-<n> (<parent spine path>) | <binds here>'")
            continue
        if match[2].strip("`") != parent:
            errors.append(f"line {number}: inherited row cites {match[2]}, not the Parent {parent}")
            continue
        if ids is None:
            try:
                ids = _spine_ad_ids(project_root / parent)
            except _BriefAcceptanceError as exc:
                errors.append(f"line {number}: {exc}")
                ids = set()
                continue
        if int(match[1]) not in ids:
            errors.append(f"line {number}: AD-{match[1]} is not a decision of {match[2]}")
    if not rows:
        errors.append("'## Inherited' has no row; write '- none' when no parent decision binds here")
    return rows, errors


def check_spine(spine: Path, project_root: Path | None = None) -> tuple[int, list[str]]:
    """An architecture spine has the form of skills/_protocols/architecture-spine.md §Format: header lines, the
    sections, ascending AD IDs with their fields, Deferred reasons, inherited IDs that exist in the parent, no
    placeholders. Form only; the substance is the architect lenses'. Fails closed on any input it cannot read."""
    project_root = Path.cwd() if project_root is None else project_root
    spine = Path(spine)
    prefix = "ERROR spine:"
    try:
        try:
            text = spine.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as exc:
            raise _BriefAcceptanceError(f"cannot read spine: {exc}") from None
        lines = _spine_lines(text)
    except _BriefAcceptanceError as exc:
        return 1, [f"{prefix} {spine}: {exc}"]

    head, sections, errors = _spine_sections(lines)
    titles = [line for _n, line in head if (h := _HEADING_RE.match(line)) and len(h[1]) == 1]
    if not titles or not _HEADING_RE.match(titles[0])[2].startswith("Architecture spine"):
        errors.append("missing title '# Architecture spine — <scope>'")
    header: dict[str, str] = {}
    for _number, line in head:
        match = re.match(r"^(Altitude|Governs|Parent):\s*(.*)$", line.strip())
        if match:
            header[match[1]] = match[2].strip()
    for name in ("Altitude", "Governs", "Parent"):
        if not header.get(name):
            errors.append(f"missing header line '{name}: …'")
    if header.get("Altitude") and header["Altitude"] not in SPINE_ALTITUDES:
        errors.append(f"Altitude must be one of {', '.join(SPINE_ALTITUDES)} (got {header['Altitude']!r})")
    parent = header.get("Parent", "")
    for name in ("Decisions", "Deferred"):
        if name not in sections:
            errors.append(f"missing section '## {name}'")
    for name in sections:
        if name not in ("Inherited", "Decisions", "Deferred"):
            errors.append(f"unknown section '## {name}'")
    inherited = 0
    if parent and parent != "none":
        if not (project_root / parent.strip("`")).is_file():
            errors.append(f"Parent {parent} is not a file under {project_root}")
        if "Inherited" not in sections:
            errors.append("missing section '## Inherited' (Parent names a spine)")
    elif "Inherited" in sections:
        errors.append("'## Inherited' present but Parent is none")
    if "Inherited" in sections and parent and parent != "none":
        inherited, found = _spine_inherited(sections["Inherited"], project_root, parent.strip("`"))
        errors += found
    decisions, found = _spine_decisions(sections.get("Decisions", []))
    errors += found
    deferred, found = _spine_deferred(sections["Deferred"]) if "Deferred" in sections else (0, [])
    errors += found
    for number, line in lines:
        hit = _SPINE_PLACEHOLDER_RE.search(re.sub(r"`[^`]*`", "", line))
        if hit:
            errors.append(f"line {number}: placeholder {hit[0]!r}")

    if errors:
        return 1, [f"{prefix} {spine}: {e}" for e in errors]
    return 0, [f"OK: spine — {spine} ({decisions} decisions, {inherited} inherited, {deferred} deferred)"]


def _main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="consistency_check — Repo-Integritaet.",
    )
    parser.add_argument(
        "--check",
        choices=(
            "tier1-drift", "tier1-multi-workflow-drift", "enforcement-registry",
            "instruction-units", "brief-acceptance", "spine",
        ),
        required=True,
        help="Welcher Check ausgefuehrt werden soll.",
    )
    parser.add_argument(
        "--workflows-root", default=None,
        help="Override workflows-runbooks-root (default framework workflows/runbooks).",
    )
    parser.add_argument(
        "--brief", default=None,
        help="Brief to check (required for and only used by --check brief-acceptance).",
    )
    parser.add_argument(
        "--spine", default=None,
        help="Architecture spine to check (required for and only used by --check spine).",
    )

    args = parser.parse_args(argv)
    if args.check == "brief-acceptance" and not args.brief:
        parser.error("--check brief-acceptance requires --brief PATH")
    if args.check != "brief-acceptance" and args.brief:
        parser.error("--brief is only used by --check brief-acceptance")
    if args.check == "spine" and not args.spine:
        parser.error("--check spine requires --spine PATH")
    if args.check != "spine" and args.spine:
        parser.error("--spine is only used by --check spine")

    workflows_root = Path(args.workflows_root) if args.workflows_root else None

    if args.check == "tier1-drift":
        exit_code, warnings = check_tier1_drift(workflows_root=workflows_root)
    elif args.check == "tier1-multi-workflow-drift":
        exit_code, warnings = check_tier1_multi_workflow_drift(
            workflows_root=workflows_root,
        )
    elif args.check == "enforcement-registry":
        exit_code, warnings = check_enforcement_registry()
    elif args.check == "instruction-units":
        exit_code, warnings = check_instruction_units()
    elif args.check == "brief-acceptance":
        exit_code, warnings = check_brief_acceptance(Path(args.brief))
    elif args.check == "spine":
        exit_code, warnings = check_spine(Path(args.spine))
    else:
        print(f"ERROR: unknown check {args.check!r}", file=sys.stderr)
        return 2

    out = sys.stderr if exit_code != 0 else sys.stdout
    for w in warnings:
        print(w, file=out)

    return exit_code


if __name__ == "__main__":
    sys.exit(_main())
