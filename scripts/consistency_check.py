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
        # strikter)?
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


# ---------------------------------------------------------------------------
# Autonomy Consistency (framework/agent-autonomy.md SoT)
# ---------------------------------------------------------------------------

# SoT-Datei der Autonomy-Regeln. Mirror-Check, Existenz-Check, Referenz-
# Integritaet und Drift-Warnung werden gegen dieses Dokument gefahren.
# Framework-intern → _FRAMEWORK_ROOT.
AUTONOMY_SOT_PATH = _FRAMEWORK_ROOT / "framework" / "agent-autonomy.md"

# Dateien, in denen der Verweis auf framework/agent-autonomy.md existieren
# MUSS (Check 3, Referenz-Integritaet). Relativ zu _FRAMEWORK_ROOT.
AUTONOMY_REFERENCE_FILES = [
    "CLAUDE.md",
    "AGENTS.md",
    "agents/buddy/operational.md",
    "workflows/runbooks/solve/WORKFLOW.md",
]


def _extract_section(text: str, header_pattern: str) -> str | None:
    """Extrahiere Inhalt einer Markdown-Sektion.

    header_pattern: Regex, der auf den Sektions-Header matched (inkl. ### Prefix).
    Gibt den Block inkl. Header bis zum naechsten Header gleicher oder
    hoeherer Ebene (###) zurueck. None wenn nicht gefunden.
    """
    import re
    lines = text.split("\n")
    start = None
    for i, line in enumerate(lines):
        if re.match(header_pattern, line):
            start = i
            break
    if start is None:
        return None
    end = len(lines)
    for j in range(start + 1, len(lines)):
        # Naechster Header gleicher Ebene (###) oder hoeher (##, #)
        if lines[j].startswith("### ") or lines[j].startswith("## ") or lines[j].startswith("# "):
            end = j
            break
    return "\n".join(lines[start:end])


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


def _extract_autonomy_table_routing(text: str) -> list[str]:
    """Extrahiere die Routing-Spalte der Haupttabelle aus agent-autonomy.md.

    Die Tabelle hat Spalten: # | Artefakt-Typ | Pfad-Muster | Permission | Gate | Routing
    Routing ist Spalte 6 (Index 5). Wir sammeln alle rohen Routing-Zellen.
    """
    import re
    lines = text.split("\n")
    in_table = False
    routing_values = []
    for line in lines:
        stripped = line.strip()
        if not stripped.startswith("|"):
            if in_table:
                # Tabelle zu Ende
                break
            continue
        # Tabellen-Zeile
        cells = [c.strip() for c in stripped.strip("|").split("|")]
        if not in_table:
            # Header-Zeile? Pruefe auf "Routing" in Zellen
            if any("Routing" in c for c in cells) and any("Permission" in c for c in cells):
                in_table = True
            continue
        # Separator-Zeile (---|---|...) ueberspringen
        if all(re.match(r"^-+$", c) for c in cells if c):
            continue
        # Daten-Zeile — Routing ist die letzte Spalte (bei 6 Spalten Index 5)
        if len(cells) >= 6:
            routing_values.append(cells[5])
    return routing_values


def _extract_autonomy_table_gate_peers(text: str) -> list[str]:
    """Extrahiere `peer:<agent>` Targets aus der Gate-Spalte der Haupttabelle.

    Hintergrund: Die Gate-Polymorphie in agent-autonomy.md erlaubt
    Merger-Faelle, bei denen ein Peer-Konsultations-Gate gleichzeitig die
    Routing-Antwort traegt (z.B. `peer:council`, `peer:solution-expert`).
    Ein Drift-Check, der nur die Routing-Spalte liest, meldet diese Agenten
    faelschlich als "in operational.md aber nicht in agent-autonomy.md".

    Diese Funktion scannt die Gate-Spalte (Index 4) und gibt alle Tokens
    nach einem `peer:`-Prefix zurueck. `review:*` Gates werden bewusst
    ignoriert (das sind Skill-Gates, keine Agenten).
    """
    import re
    lines = text.split("\n")
    in_table = False
    peers: list[str] = []
    peer_re = re.compile(r"peer:([A-Za-z0-9_-]+)")
    for line in lines:
        stripped = line.strip()
        if not stripped.startswith("|"):
            if in_table:
                break
            continue
        cells = [c.strip() for c in stripped.strip("|").split("|")]
        if not in_table:
            if any("Routing" in c for c in cells) and any("Permission" in c for c in cells):
                in_table = True
            continue
        if all(re.match(r"^-+$", c) for c in cells if c):
            continue
        # Daten-Zeile — Gate ist Index 4 (bei 6 Spalten: 0=#, 1=Typ, 2=Pfad,
        # 3=Permission, 4=Gate, 5=Routing).
        if len(cells) >= 6:
            gate_cell = cells[4]
            for match in peer_re.finditer(gate_cell):
                peers.append(match.group(1))
    return peers


def _extract_operational_routing_agents(text: str) -> list[str]:
    """Extrahiere die Agent-Spalte aus der Delegation-Routing-Tabelle in operational.md.

    Die Tabelle hat Spalten: | Thema | Agent |
    """
    import re
    lines = text.split("\n")
    in_table = False
    agents = []
    for line in lines:
        stripped = line.strip()
        if not stripped.startswith("|"):
            if in_table:
                break
            continue
        cells = [c.strip() for c in stripped.strip("|").split("|")]
        if not in_table:
            if any("Agent" in c for c in cells) and any("Thema" in c for c in cells):
                in_table = True
            continue
        if all(re.match(r"^-+$", c) for c in cells if c):
            continue
        if len(cells) >= 2:
            agents.append(cells[1])
    return agents


def validate_autonomy_consistency() -> list[ValidationIssue]:
    """Autonomy-Consistency-Checks.

    Prueffaelle:
      Check 1 — Mirror-Check CLAUDE.md §5 ↔ AGENTS.md §5 (ERROR bei Abweichung)
      Check 2 — Existenz-Check framework/agent-autonomy.md (ERROR bei Fehlern)
      Check 3 — Referenz-Integritaet in Konsumenten-Dateien (ERROR pro fehlendem Verweis)
      Check 4 — Cross-Reference Drift-Warnung operational.md ↔ agent-autonomy.md (WARN)
    """
    import re
    issues: list[ValidationIssue] = []

    # Check 1: Mirror-Check CLAUDE.md ↔ AGENTS.md
    # Scope ist nicht mehr die feste Sektion "### 5. Code-Delegation",
    # sondern alle `###`-Sektionen, die den SoT-Pfad `framework/agent-autonomy.md`
    # erwaehnen. Matching der korrespondierenden Sektionen erfolgt ueber den
    # normalisierten Header-Text (Nummer entfernt), damit Nummer-Aenderungen
    # nicht still den Check umgehen koennen.
    claude_path = _FRAMEWORK_ROOT / "CLAUDE.md"
    agents_path = _FRAMEWORK_ROOT / "AGENTS.md"

    if not claude_path.exists():
        issues.append(ValidationIssue(
            "AUTONOMY_MIRROR", "ERROR",
            detail="CLAUDE.md fehlt — Mirror-Check nicht moeglich"))
    elif not agents_path.exists():
        issues.append(ValidationIssue(
            "AUTONOMY_MIRROR", "ERROR",
            detail="AGENTS.md fehlt — Mirror-Check nicht moeglich"))
    else:
        claude_text = claude_path.read_text(encoding="utf-8")
        agents_text = agents_path.read_text(encoding="utf-8")
        claude_sections = _extract_sections_containing(
            claude_text, "framework/agent-autonomy.md")
        agents_sections = _extract_sections_containing(
            agents_text, "framework/agent-autonomy.md")

        if not claude_sections:
            issues.append(ValidationIssue(
                "AUTONOMY_MIRROR", "ERROR",
                detail=("CLAUDE.md: keine '###'-Sektion gefunden, die "
                        "'framework/agent-autonomy.md' erwaehnt — Mirror-"
                        "Anker fehlt")))
        if not agents_sections:
            issues.append(ValidationIssue(
                "AUTONOMY_MIRROR", "ERROR",
                detail=("AGENTS.md: keine '###'-Sektion gefunden, die "
                        "'framework/agent-autonomy.md' erwaehnt — Mirror-"
                        "Anker fehlt")))

        if claude_sections and agents_sections:
            # Symmetrischer Satz-Vergleich: jeder Title-Key muss in beiden
            # Dateien existieren.
            only_in_claude = set(claude_sections) - set(agents_sections)
            only_in_agents = set(agents_sections) - set(claude_sections)
            for tk in sorted(only_in_claude):
                issues.append(ValidationIssue(
                    "AUTONOMY_MIRROR", "ERROR",
                    detail=(f"CLAUDE.md hat Sektion '{tk}' (erwaehnt "
                            f"agent-autonomy.md), die in AGENTS.md fehlt — "
                            f"Sync noetig")))
            for tk in sorted(only_in_agents):
                issues.append(ValidationIssue(
                    "AUTONOMY_MIRROR", "ERROR",
                    detail=(f"AGENTS.md hat Sektion '{tk}' (erwaehnt "
                            f"agent-autonomy.md), die in CLAUDE.md fehlt — "
                            f"Sync noetig")))

            # Fuer Sektionen die in beiden Dateien existieren: Text-Gleichheit.
            # Body ohne die erste Zeile (Header) vergleichen, damit eine
            # unterschiedliche Sektions-Nummer im Header die Sektion nicht
            # faelschlich als "Mismatch" meldet. Der Title-Key-Match oben
            # stellt bereits sicher, dass die Header textlich identisch sind
            # (modulo Nummer-Prefix).
            common = set(claude_sections) & set(agents_sections)
            for tk in sorted(common):
                claude_body = "\n".join(
                    claude_sections[tk].rstrip().split("\n")[1:])
                agents_body = "\n".join(
                    agents_sections[tk].rstrip().split("\n")[1:])
                if claude_body.rstrip() == agents_body.rstrip():
                    continue
                # Diff-Darstellung: erste abweichende Zeile. Zeilennummer
                # ist sektion-relativ (Header = Zeile 1, erste Body-Zeile = 2).
                claude_lines = claude_body.rstrip().split("\n")
                agents_lines = agents_body.rstrip().split("\n")
                diff_line = None
                max_len = max(len(claude_lines), len(agents_lines))
                for i in range(max_len):
                    cl = claude_lines[i] if i < len(claude_lines) else "<EOF>"
                    al = agents_lines[i] if i < len(agents_lines) else "<EOF>"
                    if cl != al:
                        diff_line = (i + 2, cl, al)
                        break
                if diff_line:
                    ln, cl, al = diff_line
                    issues.append(ValidationIssue(
                        "AUTONOMY_MIRROR", "ERROR",
                        detail=(f"CLAUDE.md Sektion '{tk}' != AGENTS.md "
                                f"ab Zeile {ln}: CLAUDE='{cl[:60]}' vs "
                                f"AGENTS='{al[:60]}' — Sync via Edit "
                                f"beider Dateien noetig")))
                else:
                    issues.append(ValidationIssue(
                        "AUTONOMY_MIRROR", "ERROR",
                        detail=(f"CLAUDE.md Sektion '{tk}' != AGENTS.md "
                                f"(Laengenunterschied)")))

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

    # Check 4: Cross-Reference Drift-Warnung (operational.md ↔ agent-autonomy.md)
    # Weicher Check: wenn Agenten in einer Tabelle stehen aber nicht in der
    # anderen, Warning mit Drift-Hinweis. Kein Blocker (unterschiedlicher Scope
    # ist legitim moeglich).
    operational_path = _FRAMEWORK_ROOT / "agents" / "buddy" / "operational.md"
    if operational_path.exists() and autonomy_text:
        operational_text = operational_path.read_text(encoding="utf-8")
        op_section = _extract_section(operational_text, r"^### Delegation-Routing")
        if op_section is not None:
            op_agents_raw = _extract_operational_routing_agents(op_section)
            autonomy_routing_raw = _extract_autonomy_table_routing(autonomy_text)
            # Merger-Faelle mitzaehlen — Agenten, die in der
            # Gate-Spalte als `peer:X` auftauchen, sind ebenfalls "bekannt".
            autonomy_gate_peers = _extract_autonomy_table_gate_peers(autonomy_text)

            # Bekannte Rollen-Tokens. Wenn die normalisierte Form eines davon
            # als Wort enthaelt, nehmen wir den Token (grobe Matching-Heuristik).
            known_roles = (
                "main-code-agent", "solution-expert", "buddy", "security",
                # council: Merger-Fall (peer:council in Gate-Spalte = Routing,
                # intentionally NOT in operational.md Delegation-Routing).
                # review-agent: entfernt (existiert nicht, war Phantom).
            )

            def _normalize_agent(s: str) -> str:
                s = s.strip().lower()
                s = s.replace("`", "").replace("*", "")
                # Prefix-Strip fuer agent-autonomy.md Routing-Zellen
                for prefix in ("handoff:", "peer:", "review:"):
                    if s.startswith(prefix):
                        s = s[len(prefix):]
                # Klammer-Suffixe droppen
                if "(" in s:
                    s = s.split("(", 1)[0]
                # Phrase-Tails droppen (" weil ...", " mit ...", " direkt" ...)
                for sep in (" weil ", " mit ", " via ", " direkt",
                            " dispatcht", " schreibt"):
                    if sep in s:
                        s = s.split(sep, 1)[0]
                s = s.strip().strip(",;.:")
                # Wenn ein bekannter Rollen-Token als Wort enthalten ist,
                # nehmen wir den als normalisierte Form (robuster gegen Prosa).
                tokens = re.split(r"\s+", s)
                for role in known_roles:
                    if role in tokens:
                        return role
                return s

            # Agent-Filter: nur Token, die plausibel ein Agent-Name sind
            # (in known_roles oder hyphen-basiert). Alles andere (z.B.
            # "mirror", "plan_engine") ist Mechanismus-Beiwerk und wird
            # als Rauschen verworfen.
            def _looks_like_agent(token: str) -> bool:
                if not token:
                    return False
                if token in known_roles:
                    return True
                # Workflow/Runbook/Skill-Suffixe sind keine Agenten
                # Zellen wie `handoff:build-workflow oder
                # fix-workflow` koennen `fix-workflow` als hyphen-Token
                # produzieren, das faelschlich als Agent durchrutscht.
                for suffix in ("-workflow", "-runbook", "-skill"):
                    if token.endswith(suffix):
                        return False
                # hyphen-basierte Agent-Namen (z.B. "foo-agent", "bar-expert")
                return bool(re.match(r"^[a-z]+(-[a-z]+)+$", token))

            op_agents_norm = {
                _normalize_agent(a) for a in op_agents_raw if a.strip()
            }
            op_agents_norm = {a for a in op_agents_norm if _looks_like_agent(a)}

            # Aus agent-autonomy.md nehmen wir nur Zellen ohne Workflow-Handoff
            # (diese routen per Workflow, nicht an einen Agent), und zerlegen
            # an "oder"/"/" sowie Kommas fuer multi-agent-Zellen.
            autonomy_agents_norm = set()
            for cell in autonomy_routing_raw:
                cell_l = cell.lower()
                if "handoff:" in cell_l:
                    continue
                parts = re.split(r"\bor\b|\boder\b|/|,", cell, flags=re.IGNORECASE)
                for p in parts:
                    norm = _normalize_agent(p)
                    if norm:
                        autonomy_agents_norm.add(norm)

            # Gate-Peer-Targets als bekannte Agenten mitfuehren
            # (Merger-Fall Gate = Routing). Peers durchlaufen dieselbe
            # Normalisierung wie Routing-Zellen.
            for peer in autonomy_gate_peers:
                norm = _normalize_agent(peer)
                if norm:
                    autonomy_agents_norm.add(norm)

            autonomy_agents_norm = {
                a for a in autonomy_agents_norm if _looks_like_agent(a)
            }

            # Leere Strings aussortieren
            op_agents_norm.discard("")
            autonomy_agents_norm.discard("")

            only_in_op = op_agents_norm - autonomy_agents_norm
            only_in_autonomy = autonomy_agents_norm - op_agents_norm

            if only_in_op:
                issues.append(ValidationIssue(
                    "AUTONOMY_DRIFT", "WARN",
                    detail=(f"operational.md Delegation-Routing listet Agenten, "
                            f"die in agent-autonomy.md Routing-Spalte fehlen: "
                            f"{sorted(only_in_op)} — Drift-Risiko, ggf. "
                            f"agent-autonomy.md erweitern")))
            if only_in_autonomy:
                issues.append(ValidationIssue(
                    "AUTONOMY_DRIFT", "WARN",
                    detail=(f"agent-autonomy.md Routing-Spalte nennt Agenten, "
                            f"die in operational.md Delegation-Routing fehlen: "
                            f"{sorted(only_in_autonomy)} — Drift-Risiko, ggf. "
                            f"operational.md-Tabelle ergaenzen")))

    return issues


def _main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="consistency_check — Repo-Integritaet.",
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
