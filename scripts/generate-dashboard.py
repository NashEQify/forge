#!/usr/bin/env python3
"""
Dev-Flow Dashboard Generator — Multi-Repo, plan.yaml SoT.

Loads task + milestone data via plan_engine.py (library import) for one or
more project repos. Each repo must expose docs/plan.yaml + docs/tasks/*.yaml.

Key design:
- plan_engine.load_plan(project_root=...) / load_tasks(...) are the ONLY
  data inputs. Legacy parsers (backlog.md, phases.yaml, current-hook.md,
  implementation-plan.md, feature-registry.md, prebuild-status) are retired.
- Multi-repo first-class: --projects <slug1>,<slug2>,... builds a unified
  Gantt. Task-IDs are namespaced as "<repo>#<id:03d>".
- --host-repo selects which repo drives the Top-Panel (Target, Bottleneck,
  Next Action, Critical Path, Warnings). Independent of UI repo-toggles.
- --title sets the HTML <title>. Default: "<host-repo> Dev Dashboard".

Usage:
    python3 scripts/generate-dashboard.py \\
        --host-repo <primary-slug> \\
        --projects <slug1>,<slug2>,<slug3> \\
        --output /path/to/index.html

Each <slug> resolves to $PROJECTS_DIR/<slug> by default (overridable via
$PROJECTS_DIR env var). Missing repos are skipped with a warning.
"""

import argparse
import json
import os
import re
import sys
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    import yaml  # type: ignore[import-untyped]
except ImportError:
    print("ERROR: PyYAML not installed. Install with: pip install pyyaml", file=sys.stderr)
    sys.exit(1)


# ---------------------------------------------------------------------------
# Path resolution
# ---------------------------------------------------------------------------
#
# REPO_ROOT is this script's containing framework repo. We do NOT assume it is
# a data-holding repo — the dashboard sources data from each --projects entry
# via plan_engine.load_plan(project_root=...).

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = REPO_ROOT / "scripts"

# Import plan_engine as a library. plan_engine lives alongside this script.
sys.path.insert(0, str(SCRIPTS_DIR))
try:
    import plan_engine  # noqa: E402
except Exception as exc:  # pragma: no cover
    print(f"ERROR: failed to import plan_engine from {SCRIPTS_DIR}: {exc}", file=sys.stderr)
    sys.exit(1)

DEFAULT_OUTPUT = REPO_ROOT / "_site" / "dashboard" / "index.html"

# Known repo name → filesystem path mappings. Checked first during repo
# resolution; falls back to $PROJECTS_DIR / <slug> (default ~/projects/<slug>).
DEFAULT_REPO_PATHS: dict[str, Path] = {
    # All first-class repos live under ~/projects/<slug>/ today.
}

# Legacy constants referenced by dead-code parsers (kept to avoid NameErrors
# in unused functions; safe because the functions themselves are unreachable).
BACKLOG_PATH = REPO_ROOT / "docs" / "backlog.md"
IMPL_PLAN_PATH = REPO_ROOT / "docs" / "implementation-plan.md"
CURRENT_HOOK_PATH = REPO_ROOT / "docs" / "current-hook.md"
FEATURE_REGISTRY_PATH = REPO_ROOT / "docs" / "feature-registry.md"
PHASES_PATH = REPO_ROOT / "docs" / "phases.yaml"
TASKS_DIR = REPO_ROOT / "docs" / "tasks"
SPECS_DIR = REPO_ROOT / "docs" / "specs"


# ---------------------------------------------------------------------------
# Readiness pipeline labels & tooltips
# ---------------------------------------------------------------------------

READINESS_LABELS = {
    "raw": "Idea",
    "specced": "Spec",
    "reviewed": "Board \u2713",
    "implementing": "Building",
    "done": "Done",
}

READINESS_TOOLTIPS = {
    "raw": "Idee, kein Spec (raw)",
    "specced": "Spec geschrieben, kein Board (specced)",
    "reviewed": "Board-reviewed (reviewed)",
    "implementing": "In Implementierung (implementing)",
    "done": "Abgeschlossen (done)",
}

READINESS_ORDER = ["raw", "specced", "reviewed", "implementing", "done"]


# Phases NOT counted as implementation (exclude-list for is_implementation heuristic).
# Everything else is treated as an implementation phase in the Gantt chart.
NON_IMPLEMENTATION_PHASES = {
    "Prozess", "Parallel", "Deferred", "Exploration", "Uncategorized",
}


# ---------------------------------------------------------------------------
# Parsing helpers
# ---------------------------------------------------------------------------

def warn(msg: str) -> None:
    print(f"  WARNING: {msg}", file=sys.stderr)


def _parse_dep_ids(deps_str: str) -> list:
    """Extract numeric task IDs from a deps string."""
    if not deps_str or deps_str.strip() in ("—", "-", ""):
        return []
    deps_str = deps_str.split("|")[0].strip()
    deps_str = re.sub(r'\([^)]*\)', '', deps_str)
    return [d.strip().zfill(3) for d in deps_str.split(",")
            if d.strip() and d.strip().isdigit()]


def parse_current_hook(path: Path) -> dict:
    """Parse current-hook.md key-value pairs."""
    result = {"status": "unknown", "task": "-", "step": "-", "context_note": "", "task_id": ""}
    if not path.exists():
        warn(f"current-hook.md not found at {path}")
        return result
    text = path.read_text(encoding="utf-8")
    text = re.sub(r"^#[^\n]*\n", "", text)
    for key in ("status", "since", "project", "task", "step"):
        m = re.search(rf"^{key}:\s*(.+)$", text, re.MULTILINE)
        if m:
            result[key] = m.group(1).strip().strip('"').strip("'")
    m = re.search(r"^context_note:\s*\|?\s*\n((?:[ \t]+.+\n?)+)", text, re.MULTILINE)
    if m:
        lines = m.group(1).split("\n")
        result["context_note"] = "\n".join(line.strip() for line in lines if line.strip())
    # Extract task ID from task string (e.g. "Task 192" or "[192]" or "Dashboard 192")
    task_str = result.get("task", "")
    tid_m = re.search(r"(\d{3})", task_str)
    if tid_m:
        result["task_id"] = tid_m.group(1)
    return result


def parse_phases(path: Path) -> tuple[list[str], dict[str, dict[str, str]], dict[str, str]]:
    """Parse phases.yaml — SoT for phase ordering and metadata.

    Returns (phase_order, phase_info, phase_types) or ([], {}, {}) on error.
      - phase_order: list of phase keys in canonical order
      - phase_info: dict {key: {"title": str, "desc": str, "status": str, "type": str}}
      - phase_types: dict {key: "implementation"|"support"}
    """
    phase_order: list[str] = []
    phase_info: dict[str, dict[str, str]] = {}
    phase_types: dict[str, str] = {}

    if not path.exists():
        warn(f"phases.yaml not found at {path} — falling back to backlog.md ordering")
        return phase_order, phase_info, phase_types

    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except Exception as e:
        warn(f"Failed to parse phases.yaml: {e} — falling back to backlog.md ordering")
        return phase_order, phase_info, phase_types

    if not data or "phases" not in data:
        warn("phases.yaml has no 'phases' key — falling back to backlog.md ordering")
        return phase_order, phase_info, phase_types

    for entry in data["phases"]:
        key = entry.get("key", "")
        if not key:
            continue
        phase_order.append(key)
        phase_info[key] = {
            "title": key,
            "desc": entry.get("desc", ""),
            "status": entry.get("status", ""),
            "type": entry.get("type", ""),
        }
        phase_types[key] = entry.get("type", "implementation")

    # Ensure "Uncategorized" always exists as fallback
    if "Uncategorized" not in phase_info:
        phase_order.append("Uncategorized")
        phase_info["Uncategorized"] = {"title": "Uncategorized", "desc": "", "status": "", "type": "support"}
        phase_types["Uncategorized"] = "support"

    return phase_order, phase_info, phase_types


def parse_backlog(path: Path) -> tuple[dict[str, dict[str, Any]], dict[str, str], str, list[str], dict[str, dict[str, str]]]:
    """Parse backlog.md.

    Returns (tasks_by_id, phase_map, north_star, phase_order, phase_info).
      - phase_order: list of canonical phase names in backlog appearance order
      - phase_info: dict {canonical_name: {"title": str, "desc": str}}
    """
    tasks: dict[str, dict[str, Any]] = {}
    phase_map: dict[str, str] = {}
    north_star = ""
    phase_order: list[str] = []
    phase_info: dict[str, dict[str, str]] = {}

    if not path.exists():
        warn(f"backlog.md not found at {path}")
        return tasks, phase_map, north_star, phase_order, phase_info

    text = path.read_text(encoding="utf-8")

    m = re.search(r"\*\*north_star:\*\*\s*(.+)", text)
    if m:
        north_star = m.group(1).strip()

    # Dynamic phase detection: every `## ` header that is NOT "Current Operational Intent"
    # is treated as a phase section.
    phase_pattern = re.compile(r"^##\s+(.+)$", re.MULTILINE)
    raw_phase_starts = []
    for pm in phase_pattern.finditer(text):
        raw_header = pm.group(1).strip()
        # Skip non-phase headers
        if raw_header.lower().startswith("current operational intent"):
            continue
        raw_phase_starts.append((pm.start(), raw_header))

    # Build phase_order and phase_info from raw headers
    for _start, raw_header in raw_phase_starts:
        canonical = _normalize_phase(raw_header)
        if canonical not in phase_info:
            phase_order.append(canonical)
            # Extract description: text between "## Header" and first "###" or next "## " or "---"
            # The title is the canonical name, desc is the first non-empty paragraph after the header.
            phase_info[canonical] = {"title": canonical, "desc": ""}

    # Extract descriptions: for each phase section, grab the first non-empty paragraph
    for idx, (start, raw_header) in enumerate(raw_phase_starts):
        canonical = _normalize_phase(raw_header)
        end = raw_phase_starts[idx + 1][0] if idx + 1 < len(raw_phase_starts) else len(text)
        section = text[start:end]

        # Find lines between the ## header and first ### or ---
        desc_lines = []
        past_header = False
        for line in section.split("\n"):
            stripped = line.strip()
            if not past_header:
                if stripped.startswith("## "):
                    past_header = True
                continue
            # Stop at first task header, horizontal rule, or another ## header
            if stripped.startswith("### ") or stripped.startswith("---") or stripped.startswith("## "):
                break
            if stripped:
                desc_lines.append(stripped)
            elif desc_lines:
                break  # empty line after content = end of description paragraph
        if desc_lines and not phase_info[canonical]["desc"]:
            phase_info[canonical]["desc"] = " ".join(desc_lines)[:200]

    # Ensure "Uncategorized" always exists as fallback
    if "Uncategorized" not in phase_info:
        phase_order.append("Uncategorized")
        phase_info["Uncategorized"] = {"title": "Uncategorized", "desc": ""}

    # Parse tasks per phase section
    for idx, (start, raw_header) in enumerate(raw_phase_starts):
        end = raw_phase_starts[idx + 1][0] if idx + 1 < len(raw_phase_starts) else len(text)
        section = text[start:end]

        phase_label = _normalize_phase(raw_header)

        task_pattern = re.compile(
            r"^###\s+\[(\d{3})\]\s+(.+?)(?:\s*—\s*(.+?))?$",
            re.MULTILINE
        )

        for tm in task_pattern.finditer(section):
            task_id = tm.group(1)
            title = tm.group(2).strip()
            title = re.sub(r"\s*—\s*(DONE|SUPERSEDED|DEFERRED)\s*$", "", title, flags=re.IGNORECASE)
            phase_map[task_id] = phase_label

            block_start = tm.end()
            block_end_m = re.search(r"^###?\s", section[block_start:], re.MULTILINE)
            block = section[block_start:block_start + block_end_m.start() if block_end_m else len(section)]

            meta_line = ""
            for line in block.split("\n"):
                if "Prio:" in line or "Area:" in line or "Status:" in line:
                    meta_line = line
                    break

            prio = ""
            area = ""
            status = ""
            deps_str = ""

            prio_m = re.search(r"Prio:\s*(\w+)", meta_line)
            if prio_m:
                prio = prio_m.group(1)
            area_m = re.search(r"Area:\s*([^|]+)", meta_line)
            if area_m:
                area = area_m.group(1).strip()
            status_m = re.search(r"Status:\s*(\w+)", meta_line)
            if status_m:
                status = status_m.group(1)

            dm = re.search(r"^Deps:\s*(.+)$", block, re.MULTILINE)
            if dm:
                deps_str = dm.group(1).split("|")[0].strip()

            desc_lines = []
            past_meta = False
            for line in block.split("\n"):
                stripped = line.strip()
                if not stripped:
                    if past_meta and desc_lines:
                        break
                    continue
                if "Prio:" in stripped or "Deps:" in stripped or "Erstellt:" in stripped:
                    past_meta = True
                    continue
                if stripped.startswith("\u2192") or stripped.startswith(">"):
                    continue
                if past_meta or (not any(k in stripped for k in ["Prio:", "Deps:", "Erstellt:"])):
                    past_meta = True
                    desc_lines.append(stripped)

            tasks[task_id] = {
                "id": task_id,
                "title": title,
                "prio": prio,
                "area": area,
                "status": status,
                "deps": _parse_dep_ids(deps_str),
                "description": " ".join(desc_lines)[:200],
                "phase": phase_label,
                "_raw_block": meta_line,
            }

    # Second pass for phase assignment (references outside task headers)
    for idx, (start, raw_header) in enumerate(raw_phase_starts):
        end = raw_phase_starts[idx + 1][0] if idx + 1 < len(raw_phase_starts) else len(text)
        section = text[start:end]
        phase_label = _normalize_phase(raw_header)

        for ref_id in re.findall(r"\[(\d{3})\]", section):
            if ref_id not in phase_map:
                phase_map[ref_id] = phase_label
        for ref_id in re.findall(r"(?<=[\s,(])(\d{3})(?=[\s,)])", section):
            if ref_id not in phase_map:
                phase_map[ref_id] = phase_label

    return tasks, phase_map, north_star, phase_order, phase_info


def _normalize_phase(raw_header: str) -> str:
    """Normalize a raw backlog ## header to a canonical phase label.

    Strips status suffixes (DONE, IN PROGRESS, PENDING, FUTURE) and
    trailing descriptions after em-dashes.  E.g.:
      "Phase 2: Spec Readiness — IN PROGRESS"  ->  "Phase 2: Spec Readiness"
      "CC Source Analysis — Research (von ...)"  ->  "CC Source Analysis"
      "Prozess / Framework"  ->  "Prozess"
      "Parallel / Opportunistisch"  ->  "Parallel"
      "Exploration / Someday"  ->  "Exploration"
    """
    # Strip everything after " — " (em-dash with spaces) or " -- "
    name = re.split(r"\s+[\u2014—]\s+|\s+--\s+", raw_header, maxsplit=1)[0].strip()

    # Collapse known "X / Y" patterns to their short canonical form
    _slash_map = {
        "Prozess / Framework": "Prozess",
        "Parallel / Opportunistisch": "Parallel",
        "Exploration / Someday": "Exploration",
    }
    if name in _slash_map:
        return _slash_map[name]

    return name


def parse_yaml_tasks(tasks_dir: Path) -> dict[str, dict[str, Any]]:
    """Parse all docs/tasks/NNN.yaml files. Returns {id_str: yaml_data}."""
    result: dict[str, dict[str, Any]] = {}
    if not tasks_dir.exists():
        warn(f"Tasks directory not found: {tasks_dir}")
        return result

    for yf in sorted(tasks_dir.glob("*.yaml")):
        if "-gates" in yf.stem:
            continue
        if not yf.stem.isdigit():
            continue
        try:
            data = yaml.safe_load(yf.read_text(encoding="utf-8"))
            if data and isinstance(data, dict):
                tid = yf.stem.zfill(3)
                raw = yf.read_text(encoding="utf-8")
                blocked_raw = re.search(r"^blocked_by:\s*\[([^\]]*)\]", raw, re.MULTILINE)
                if blocked_raw:
                    raw_deps = blocked_raw.group(1).strip()
                    if raw_deps:
                        data["blocked_by"] = [d.strip().zfill(3) for d in raw_deps.split(",") if d.strip()]
                    else:
                        data["blocked_by"] = []
                elif "blocked_by:" in raw:
                    blocked_lines = re.findall(r"^\s*-\s*(\S+)", raw[raw.index("blocked_by:"):], re.MULTILINE)
                    data["blocked_by"] = [d.strip().zfill(3) for d in blocked_lines if d.strip()]
                result[tid] = data
        except Exception as e:
            warn(f"Failed to parse {yf.name}: {e}")

    return result


def parse_md_task(path: Path) -> dict[str, Any]:
    """Parse a single task markdown file for detail content."""
    result: dict[str, Any] = {
        "intent": "", "problem": "", "description": "",
        "acs": [], "workflow_steps": [], "constraints": "",
        "kommentare": [], "sections": {},
        "prio": "", "area": "", "status": "", "deps": [], "title": "",
    }

    if not path.exists():
        return result

    text = path.read_text(encoding="utf-8")

    if text.startswith("---"):
        end_fm = text.find("---", 3)
        if end_fm > 0:
            try:
                fm = yaml.safe_load(text[3:end_fm])
                if isinstance(fm, dict):
                    for k in ("prio", "area", "status", "title"):
                        if k in fm:
                            result[k] = str(fm[k])
                    if "deps" in fm and fm["deps"]:
                        result["deps"] = [str(d).zfill(3) for d in fm["deps"]] if isinstance(fm["deps"], list) else [str(fm["deps"]).zfill(3)]
            except Exception:
                pass
            text = text[end_fm + 3:]

    hm = re.search(r"^#\s+(?:Task\s+)?(\d+):\s*(.+)$", text, re.MULTILINE)
    if hm and not result["title"]:
        result["title"] = hm.group(2).strip()

    meta_m = re.search(r"^Prio:\s*(\w+)\s*\|\s*Area:\s*([^|]+)\|\s*Status:\s*(\S+)", text, re.MULTILINE)
    if meta_m:
        if not result["prio"]:
            result["prio"] = meta_m.group(1)
        if not result["area"]:
            result["area"] = meta_m.group(2).strip()
        if not result["status"]:
            result["status"] = meta_m.group(3)

    if not result["deps"]:
        dm = re.search(r"^Deps:\s*(.+)$", text, re.MULTILINE)
        if dm:
            raw = dm.group(1).strip()
            if raw and raw != "—":
                result["deps"] = [d.strip().zfill(3) for d in raw.split(",") if d.strip().isdigit()]

    sections = {}
    sec_pattern = re.compile(r"^##\s+(.+)$", re.MULTILINE)
    sec_matches = list(sec_pattern.finditer(text))
    for idx, sm in enumerate(sec_matches):
        sec_name = sm.group(1).strip()
        start = sm.end()
        end = sec_matches[idx + 1].start() if idx + 1 < len(sec_matches) else len(text)
        sections[sec_name] = text[start:end].strip()
    result["sections"] = sections

    for key in sections:
        lower = key.lower()
        if lower == "intent":
            result["intent"] = sections[key]
        elif lower == "problem":
            result["problem"] = sections[key]
        elif lower.startswith("beschreibung") or lower == "description":
            result["description"] = sections[key]
        elif "constraint" in lower:
            result["constraints"] = sections[key]

    for key in sections:
        if "acceptance" in key.lower():
            result["acs"] = _parse_ac_table(sections[key])
            break

    step_pattern = re.compile(r"^###\s+(Step|Stufe)\s+(\S+):\s*(.+)$", re.MULTILINE)
    step_matches = list(step_pattern.finditer(text))
    for idx, stm in enumerate(step_matches):
        step_num = stm.group(2)
        step_title = stm.group(3).strip()
        start = stm.end()
        end = step_matches[idx + 1].start() if idx + 1 < len(step_matches) else len(text)
        next_sec = re.search(r"^##\s", text[start:end], re.MULTILINE)
        if next_sec:
            end = start + next_sec.start()
        content = text[start:end].strip()
        gate = ""
        gm = re.search(r"\*\*(?:Gate|Decision Gate):\*\*\s*(.+?)(?:\n\n|\n###|\n##|$)", content, re.DOTALL)
        if gm:
            gate = gm.group(1).strip()
        result["workflow_steps"].append({
            "num": step_num, "title": step_title,
            "content": content[:500], "gate": gate[:300],
        })

    if not result["workflow_steps"]:
        for key in sections:
            if "workflow" in key.lower() and "step" in key.lower():
                ws_text = sections[key]
                list_pattern = re.compile(
                    r"^\s*(\d+)\.\s+(?:\*\*(.+?)\*\*\s*(?:—|--|-|:)\s*(.+)|(.+))$",
                    re.MULTILINE
                )
                for lm in list_pattern.finditer(ws_text):
                    num = lm.group(1)
                    title = (lm.group(2) or lm.group(4) or "").strip()
                    content = (lm.group(3) or "").strip()
                    result["workflow_steps"].append({
                        "num": num, "title": title,
                        "content": content[:500], "gate": "",
                    })
                break

    for key in sections:
        if "kommentar" in key.lower() or "comment" in key.lower():
            komm_text = sections[key]
            date_pattern = re.compile(r"^(\d{4}-\d{2}-\d{2}):\s*(.+?)(?=\n\d{4}-\d{2}-\d{2}:|\Z)", re.MULTILINE | re.DOTALL)
            for km in date_pattern.finditer(komm_text):
                result["kommentare"].append({
                    "date": km.group(1), "text": km.group(2).strip()[:500],
                })
            break

    return result


def _parse_ac_table(text: str) -> list:
    """Parse markdown AC table rows."""
    acs = []
    lines = text.split("\n")
    in_table = False
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("|") and ("AC" in stripped or "Beschreibung" in stripped or "Verifikation" in stripped):
            in_table = True
            continue
        if stripped.startswith("|") and re.match(r"^\|[\s\-:]+\|", stripped):
            continue
        if in_table and stripped.startswith("|"):
            cells = [c.strip() for c in stripped.split("|")[1:-1]]
            if len(cells) >= 2:
                acs.append({
                    "code": cells[0], "desc": cells[1],
                    "verif": cells[2] if len(cells) > 2 else "",
                })
    return acs


def parse_implementation_plan(path: Path) -> dict[str, dict[str, Any]]:
    """Parse implementation-plan.md. Returns {slice_name: {tasks: [id_str, ...], title: str}}."""
    slices: dict[str, dict[str, Any]] = {}
    if not path.exists():
        warn(f"implementation-plan.md not found at {path}")
        return slices

    text = path.read_text(encoding="utf-8")

    # Parse S0 and S1 from "## S0 — Title" or "### S0: Title" format
    s_pattern = re.compile(r"^#{2,3}\s+S(\d+)\s*[:\u2014—-]+\s*(.+)$", re.MULTILINE)
    matches = list(s_pattern.finditer(text))

    for idx, m in enumerate(matches):
        slice_num = m.group(1)
        slice_name = m.group(2).strip()
        start = m.end()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(text)
        next_h2 = re.search(r"^##\s", text[start:end], re.MULTILINE)
        if next_h2:
            end = start + next_h2.start()
        section = text[start:end]
        task_ids = re.findall(r"\[(\d{3})\]", section)
        teil_ids = re.findall(r"Teil von (\d{3})", section)
        all_ids = list(dict.fromkeys(task_ids + teil_ids))

        slices[f"S{slice_num}"] = {
            "title": slice_name,
            "tasks": all_ids,
        }

    # Also parse from "Future" or "Naechste Slices" table
    table_m = re.search(r"## (?:Future|Naechste Slices).*?\n(.*?)(?=\n##\s|\Z)", text, re.DOTALL)
    if table_m:
        table_text = table_m.group(1)
        for row in table_text.split("\n"):
            rm = re.match(r"\|\s*S(\d+):", row)
            if rm:
                snum = rm.group(1)
                skey = f"S{snum}"
                if skey not in slices:
                    name_m = re.match(r"\|\s*S\d+:\s*([^|]+)", row)
                    sname = name_m.group(1).strip() if name_m else f"Slice {snum}"
                    tids = re.findall(r"\[(\d{3})\]", row)
                    slices[skey] = {"title": sname, "tasks": tids}
                else:
                    # Add any additional task IDs
                    tids = re.findall(r"\[(\d{3})\]", row)
                    tasks_for_slice = slices[skey].get("tasks", [])
                    if not isinstance(tasks_for_slice, list):
                        tasks_for_slice = []
                        slices[skey]["tasks"] = tasks_for_slice
                    for tid in tids:
                        if tid not in tasks_for_slice:
                            tasks_for_slice.append(tid)

    return slices


def parse_prebuild_status(path: Path) -> dict:
    """Parse Pre-Build Pipeline status from implementation-plan.md."""
    result = {"current_block": "", "total_blocks": 5, "done_blocks": 0, "next_block": "", "status_line": ""}
    if not path.exists():
        return result
    text = path.read_text(encoding="utf-8")

    # Find "**Status:**" line
    m = re.search(r"\*\*Status:\*\*\s*(.+?)(?:\n\n|\n---|\n##)", text, re.DOTALL)
    if not m:
        m = re.search(r"^\*\*Status:\*\*\s*(.+)$", text, re.MULTILINE)
    if m:
        status_line = m.group(1).strip()
        result["status_line"] = status_line

        # Count DONE blocks
        done_count = len(re.findall(r"Block\s+[\d.]+\s+DONE", status_line))
        result["done_blocks"] = done_count

        # Find NEXT block
        next_m = re.search(r"Block\s+([\d.]+)\s+NEXT", status_line)
        if next_m:
            result["next_block"] = next_m.group(1)
            result["current_block"] = next_m.group(1)

        # Count total blocks from table
        table_m = re.search(r"## Pre-Build Pipeline.*?\n(.*?)(?=\n\*\*Status|\n##)", text, re.DOTALL)
        if table_m:
            block_rows = re.findall(r"\*\*[\d.]+:", table_m.group(1))
            if block_rows:
                result["total_blocks"] = len(block_rows)

    return result


def parse_feature_registry(path: Path) -> dict[str, list[dict[str, Any]]]:
    """Parse feature-registry.md for flags, infra toggles, and activation matrix."""
    result: dict[str, list[dict[str, Any]]] = {
        "flags": [],  # [{name, desc, tasks, deps, degraded, slice_group}]
        "infra_toggles": [],  # [{name, component, degraded_when_off, affected_flags}]
        "activation_matrix": [],  # [{flag, S0, S1, S2, S3, S4, Ph4}]
    }
    if not path.exists():
        warn(f"feature-registry.md not found at {path}")
        return result

    text = path.read_text(encoding="utf-8")

    # Parse feature flag tables in section 1
    # Each table has: Flag | Beschreibung | Tasks | Deps | Degraded Mode
    current_group = ""
    for line in text.split("\n"):
        # Detect group headers
        gm = re.match(r"^###\s+(S\d+:.+|Phase\s+\d+:.+)", line)
        if gm:
            current_group = gm.group(1).strip()
            continue

        # Parse table rows (skip header/separator)
        if line.strip().startswith("|") and "`" in line:
            cells = [c.strip() for c in line.split("|")[1:-1]]
            if len(cells) >= 5:
                flag_name = cells[0].strip("`").strip()
                if flag_name and flag_name != "Flag":
                    result["flags"].append({
                        "name": flag_name,
                        "desc": cells[1][:120],
                        "tasks": re.findall(r"\d{3}", cells[2]),
                        "deps": cells[3],
                        "degraded": cells[4][:120],
                        "slice_group": current_group,
                    })

    # Parse infra toggles (section 2)
    infra_section = re.search(r"## 2\. Infrastructure Toggles.*?\n(.*?)(?=\n## \d|\Z)", text, re.DOTALL)
    if infra_section:
        for line in infra_section.group(1).split("\n"):
            if line.strip().startswith("|") and "`infra." in line:
                cells = [c.strip() for c in line.split("|")[1:-1]]
                if len(cells) >= 4:
                    toggle_name = cells[0].strip("`").strip()
                    result["infra_toggles"].append({
                        "name": toggle_name,
                        "component": cells[1],
                        "degraded_when_off": cells[2][:120],
                        "affected_flags": cells[3][:200],
                    })

    # Parse activation matrix (section 7)
    matrix_section = re.search(r"## 7\. Slice-Aktivierungsmatrix.*?\n(.*?)(?=\n## \d|\Z)", text, re.DOTALL)
    if matrix_section:
        lines = matrix_section.group(1).strip().split("\n")
        headers = []
        for line in lines:
            if line.strip().startswith("|"):
                cells = [c.strip() for c in line.split("|")[1:-1]]
                if not cells:
                    continue
                if cells[0].strip() == "Flag":
                    headers = [c.strip() for c in cells]
                    continue
                if re.match(r"^[\s\-:]+$", cells[0]):
                    continue
                if headers and len(cells) >= 7:
                    flag_name = cells[0].strip()
                    entry = {"flag": flag_name}
                    col_map = {"S0": 1, "S1": 2, "S2": 3, "S3": 4, "S4": 5, "Ph4": 6}
                    for col_name, col_idx in col_map.items():
                        if col_idx < len(cells):
                            entry[col_name] = cells[col_idx].strip()
                        else:
                            entry[col_name] = "—"
                    result["activation_matrix"].append(entry)

    return result


def parse_amendments(path: Path) -> list[dict[str, str]]:
    """Parse Amendment Register from implementation-plan.md."""
    amendments: list[dict[str, str]] = []
    if not path.exists():
        return amendments
    text = path.read_text(encoding="utf-8")

    # Find Amendment Register section
    amend_section = re.search(r"## Amendment Register.*?\n(.*?)(?=\n## |\Z)", text, re.DOTALL)
    if not amend_section:
        return amendments

    section_text = amend_section.group(1)
    for line in section_text.split("\n"):
        if line.strip().startswith("|") and "AMEND" in line:
            cells = [c.strip() for c in line.split("|")[1:-1]]
            if len(cells) >= 6:
                amend_id = cells[0].strip("~").strip()
                is_done = "~~" in line or "DONE" in line
                amendments.append({
                    "id": amend_id,
                    "source": cells[1].strip("~").strip(),
                    "target": cells[2].strip("~").strip(),
                    "what": cells[3].strip("~").strip(),
                    "task": cells[4].strip("~").strip(),
                    "slice": cells[5].strip("~").strip(),
                    "status": "DONE" if is_done else "PENDING",
                })

    return amendments


def parse_spec_versions(specs_dir: Path) -> dict[str, str]:
    """Parse spec_version from spec files. Returns {filename: version_str}."""
    versions: dict[str, str] = {}
    if not specs_dir.exists():
        return versions

    for spec_file in specs_dir.glob("*.md"):
        text = spec_file.read_text(encoding="utf-8")

        # Try YAML frontmatter first
        if text.startswith("---"):
            end_fm = text.find("---", 3)
            if end_fm > 0:
                try:
                    fm = yaml.safe_load(text[3:end_fm])
                    if isinstance(fm, dict) and "spec_version" in fm:
                        versions[spec_file.name] = str(fm["spec_version"]).lstrip("v")
                        continue
                except Exception:
                    pass

        # Try table format: | **spec_version** | X.X |
        m = re.search(r"\*\*spec_version\*\*\s*\|\s*([\d.v]+)", text)
        if m:
            versions[spec_file.name] = m.group(1).strip().lstrip("v")
            continue

        # Try inline: spec_version: X
        m = re.search(r"^spec_version:\s*[\"']?([^\s\"']+)", text, re.MULTILINE)
        if m:
            versions[spec_file.name] = m.group(1).strip().lstrip("v")

    return versions


def merge_tasks(backlog_tasks: dict, yaml_tasks: dict, md_dir: Path,
                phase_map: dict, slices: dict) -> list:
    """Merge all data sources into a single task list."""
    all_ids = set(backlog_tasks.keys()) | set(yaml_tasks.keys())

    slice_lookup: dict[str, list[str]] = {}
    for sk, sv in slices.items():
        for tid in sv["tasks"]:
            slice_lookup.setdefault(tid, []).append(sk)

    tasks = []
    for tid in sorted(all_ids):
        bt = backlog_tasks.get(tid, {})
        yt = yaml_tasks.get(tid, {})

        md_path = md_dir / f"{tid}.md"
        if not md_path.exists():
            md_path = md_dir / f"{int(tid)}.md"
        md = parse_md_task(md_path)

        raw_status = (yt.get("status") or md.get("status") or bt.get("status", "pending")).lower()
        raw_status = raw_status.strip("*").strip()
        status_map = {
            "open": "pending", "proposed": "pending", "spec_done": "pending",
            "exploration": "pending", "superseded": "done", "absorbed": "done",
            "deferred": "pending", "blocked": "pending", "": "pending",
        }
        status = status_map.get(raw_status, raw_status)

        title = bt.get("title") or md.get("title") or yt.get("title") or f"Task {tid}"
        prio = md.get("prio") or bt.get("prio", "")
        area = yt.get("area", "") or md.get("area") or bt.get("area", "")

        deps = []
        if yt.get("blocked_by"):
            deps = [str(d).zfill(3) for d in yt["blocked_by"] if d]
        elif md.get("deps"):
            deps = md["deps"]
        elif bt.get("deps"):
            deps = bt["deps"]

        # Phase priority: YAML task `phase` field > backlog section > Uncategorized
        yaml_phase = yt.get("phase", "")
        if yaml_phase and str(yaml_phase) not in ("null", "None", ""):
            phase = str(yaml_phase)
        else:
            phase = phase_map.get(tid, bt.get("phase", "Uncategorized"))

        # Slice: prefer YAML field, fallback to plan-text lookup
        slice_val = yt.get("slice", None)
        if slice_val and str(slice_val) not in ("null", "None", ""):
            task_slices = [str(slice_val)]
        else:
            task_slices = slice_lookup.get(tid, [])

        created = str(yt["created"]) if yt.get("created") else ""
        updated = str(yt["updated"]) if yt.get("updated") else ""
        assignee = yt.get("assignee", "")

        spec_ref = yt.get("spec_ref", "")
        dev_path = yt.get("dev_path", "")
        board_result = yt.get("board_result", "")
        consumed_spec_version = yt.get("consumed_spec_version", "")

        for field_name in ("spec_ref", "dev_path", "board_result", "consumed_spec_version"):
            val = locals()[field_name]
            if val in (None, "null", "None", ""):
                locals()[field_name] = ""
            else:
                locals()[field_name] = str(val)

        # Re-read after normalization
        spec_ref = str(spec_ref) if spec_ref not in (None, "null", "None") else ""
        dev_path = str(dev_path) if dev_path not in (None, "null", "None") else ""
        board_result = str(board_result) if board_result not in (None, "null", "None") else ""
        consumed_spec_version = str(consumed_spec_version) if consumed_spec_version not in (None, "null", "None") else ""

        # Handle board_result with trailing comments
        if board_result and "#" in board_result:
            board_result = board_result.split("#")[0].strip()

        # Derive pipeline_stage from real fields (priority order)
        if status == "done":
            pipeline_stage = "done"
        elif status == "in_progress":
            pipeline_stage = "implementing"
        elif board_result and board_result.startswith("pass"):
            pipeline_stage = "reviewed"
        elif spec_ref:
            pipeline_stage = "specced"
        else:
            pipeline_stage = "raw"

        summary = yt.get("summary", "")
        if summary in (None, "null", "None"):
            summary = ""
        else:
            summary = str(summary)

        spec_progress = yt.get("spec_progress", "")
        if spec_progress in (None, "null", "None"):
            spec_progress = ""
        else:
            spec_progress = str(spec_progress)

        # Parent/sub-task hierarchy
        raw_parent = yt.get("parent_task")
        if raw_parent and raw_parent not in (None, "null", "None"):
            parent_task = str(int(raw_parent)).zfill(3)
        else:
            parent_task = ""
        raw_subs = yt.get("sub_tasks", [])
        if isinstance(raw_subs, list) and raw_subs:
            sub_tasks = [str(int(s)).zfill(3) for s in raw_subs if s]
        else:
            sub_tasks = []

        tasks.append({
            "id": tid,
            "title": title,
            "status": status,
            "_raw_status": raw_status,
            "prio": prio.lower() if prio else "",
            "area": area,
            "phase": phase,
            "deps": deps,
            "slice": str(slice_val) if (slice_val and str(slice_val) not in ("null", "None", "")) else None,
            "slices": task_slices,
            "created": created,
            "updated": updated,
            "assignee": assignee or "",
            "description": bt.get("description", md.get("description", "")),
            "intent": md.get("intent", ""),
            "problem": md.get("problem", ""),
            "acs": md.get("acs", []),
            "workflow_steps": md.get("workflow_steps", []),
            "constraints": md.get("constraints", ""),
            "kommentare": md.get("kommentare", []),
            "pipeline_stage": pipeline_stage,
            "spec_ref": spec_ref,
            "dev_path": dev_path,
            "board_result": board_result,
            "summary": summary,
            "spec_progress": spec_progress,
            "consumed_spec_version": consumed_spec_version,
            "parent_task": parent_task,
            "sub_tasks": sub_tasks,
        })

    return tasks


def build_spec_health(tasks: list, spec_versions: dict) -> list:
    """Build spec health data from task aggregation."""
    spec_groups = {}
    for t in tasks:
        sr = t.get("spec_ref", "")
        if not sr:
            continue
        if sr not in spec_groups:
            spec_groups[sr] = {
                "spec_ref": sr,
                "board_results": set(),
                "consumer_tasks": [],
                "consumed_versions": set(),
            }
        spec_groups[sr]["consumer_tasks"].append(t["id"])
        if t.get("board_result"):
            spec_groups[sr]["board_results"].add(t["board_result"])
        if t.get("consumed_spec_version"):
            spec_groups[sr]["consumed_versions"].add(t["consumed_spec_version"])

    result = []
    for sr, data in sorted(spec_groups.items()):
        current_version = spec_versions.get(sr, "")
        consumed = sorted(data["consumed_versions"])
        # Check mismatch: any consumed version < current version
        mismatch = False
        if current_version and consumed:
            try:
                cv = float(current_version)
                for c in consumed:
                    if float(c) < cv:
                        mismatch = True
                        break
            except (ValueError, TypeError):
                pass

        # Aggregate board result
        board = ""
        if "pass" in data["board_results"]:
            board = "pass"
        if "pass_with_risks" in data["board_results"]:
            board = "pass_with_risks"
        if "needs_work" in data["board_results"]:
            board = "needs_work"

        result.append({
            "spec_ref": sr,
            "current_version": current_version,
            "consumed_versions": list(consumed),
            "board_result": board,
            "consumer_tasks": data["consumer_tasks"],
            "version_mismatch": mismatch,
        })

    return result


# ---------------------------------------------------------------------------
# plan_engine-based data layer (Task-011 Phase 2b-Dashboard, D1-c)
# ---------------------------------------------------------------------------

def resolve_repo_path(slug: str) -> Path | None:
    """Resolve a repo slug to a filesystem path.

    Resolution order:
      1. DEFAULT_REPO_PATHS mapping
      2. $PROJECTS_DIR / <slug>  (default ~/projects/<slug>)
    Returns None when the path does not exist or lacks docs/plan.yaml.
    """
    cand = DEFAULT_REPO_PATHS.get(slug)
    if cand and cand.exists():
        return cand.resolve()
    projects_dir = Path(
        os.environ.get("PROJECTS_DIR") or str(Path.home() / "projects")
    ).expanduser()
    p = projects_dir / slug
    if p.exists():
        return p.resolve()
    return None


def _swap_plan_engine_globals(project_root: Path):
    """Rebind plan_engine's PROJECT_ROOT so gate/file checks resolve per-repo.

    plan_engine has module-level PROJECT_ROOT / TASKS_DIR / PLAN_PATH that a
    handful of internal routines (GateCondition.check script gates, autonomy
    consistency checks) use. When we invoke the library across several repos
    in one process we need to rebind these before each call.
    """
    plan_engine.PROJECT_ROOT = project_root
    plan_engine.TASKS_DIR = project_root / "docs" / "tasks"
    plan_engine.PLAN_PATH = project_root / "docs" / "plan.yaml"
    plan_engine.REPO_ROOT = project_root


def load_repo_data(slug: str, root: Path, error_sink: list[str] | None = None) -> dict | None:
    """Load a single repo via plan_engine and return a RepoData dict.

    Returns None + warns when the repo has no docs/plan.yaml (caller skips).
    """
    plan_path = root / "docs" / "plan.yaml"
    tasks_dir = root / "docs" / "tasks"
    if not plan_path.exists():
        msg = f"[{slug}] no docs/plan.yaml at {root} — skip"
        warn(msg)
        if error_sink is not None:
            error_sink.append(msg)
        return None
    if not tasks_dir.exists():
        msg = f"[{slug}] no docs/tasks/ at {root} — skip"
        warn(msg)
        if error_sink is not None:
            error_sink.append(msg)
        return None

    try:
        _swap_plan_engine_globals(root)

        tasks = plan_engine.load_tasks(project_root=root)
        # 2026-05-07 Fix: archive/-Tasks zusaetzlich laden, damit done-Tasks
        # weiterhin im Dashboard als done-collapsed-Stack rendern (vorher: nach
        # User-Sweep aller done/superseded ins archive war der done-Stack leer).
        # Active-IDs haben Vorrang bei Kollisionen (sollte 0 sein, ID-Drift waere
        # eigenes Daten-Issue).
        try:
            archived = plan_engine.load_archived_tasks(project_root=root)
        except AttributeError:
            # Aelteres plan_engine ohne load_archived_tasks — Fallback: leeres dict.
            archived = {}
        for tid, t in archived.items():
            if tid not in tasks:
                tasks[tid] = t
        plan = plan_engine.load_plan(project_root=root)
        milestones = plan.milestones

        # Task 435 Iteration 2 (CR-003 Fix): plan_data parsen und an
        # compute_critical_path uebergeben damit 4-stufiger Lookup +
        # Greenfield-Authority (`critical_path:` aus plan.yaml) im Dashboard
        # greift. Vorher: 3-arg-Form fiel auf DAG-Topo-Sort zurueck und
        # ignorierte plan.yaml `critical_path:`-Authority (B-4 Lock-Verletzung).
        plan_yaml_path = root / "docs" / "plan.yaml"
        plan_data: dict = {}
        if plan_yaml_path.exists():
            try:
                raw = yaml.safe_load(plan_yaml_path.read_text(encoding="utf-8"))
                if isinstance(raw, dict):
                    plan_data = raw
            except (yaml.YAMLError, OSError):
                plan_data = {}

        plan_engine.assign_tasks_to_milestones(tasks, milestones)
        plan_engine.compute_milestone_dependents(milestones)
        plan_engine.compute_milestone_status(milestones, tasks)

        critical_path = plan_engine.compute_critical_path(
            tasks, milestones, plan.target, plan_data
        )
        blocking_scores = plan_engine.compute_blocking_score(tasks, milestones)
        issues = plan_engine.validate(tasks, milestones)
        next_actions = plan_engine.compute_next_actions(
            tasks, milestones, critical_path, blocking_scores,
            target=plan.target, limit=5,
        )
    except Exception as exc:
        msg = f"[{slug}] load failed at {root}: {exc} — skip"
        warn(msg)
        if error_sink is not None:
            error_sink.append(msg)
        return None

    return {
        "slug": slug,
        "root": root,
        "plan": plan,
        "tasks": tasks,
        "milestones": milestones,
        "critical_path": critical_path,
        "blocking_scores": blocking_scores,
        "issues": issues,
        "next_actions": next_actions,
    }


def _nsid(slug: str, tid: int | str) -> str:
    """Render a namespaced task ID in the form '<repo>#<id:03d>'."""
    try:
        return f"{slug}#{int(tid):03d}"
    except (TypeError, ValueError):
        return f"{slug}#{tid}"


def _nsms(slug: str, key: str) -> str:
    """Render a namespaced milestone key in the form '<repo>#<key>'."""
    return f"{slug}#{key}"


def _dep_str(slug: str, dep) -> str:
    """Normalize a blocked_by entry into a namespaced string.

    Intra-repo int ids → '<slug>#<id>'.
    Already-namespaced strings (contain '#') → unchanged.
    Anything else → str() cast, unchanged.
    """
    if isinstance(dep, int):
        return _nsid(slug, dep)
    s = str(dep).strip()
    if "#" in s:
        return s
    if s.isdigit():
        return _nsid(slug, s)
    return s


def _external_dep_str(entry) -> str:
    """Render a blocked_by_external entry for display.

    Dict form (repo+id) → 'repo#id:03d'.
    Legacy strings → returned as-is (caller may interpret as a URL / path).
    """
    if isinstance(entry, dict) and "repo" in entry and "id" in entry:
        try:
            return f"{entry['repo']}#{int(entry['id']):03d}"
        except (TypeError, ValueError):
            return str(entry)
    return str(entry)


def _pipeline_stage(t) -> str:
    """Derive pipeline_stage from plan_engine Task fields (matches legacy)."""
    if t.status == "done":
        return "done"
    if t.status == "in_progress":
        return "implementing"
    board = (t.board_result or "").strip()
    if board.startswith("pass"):
        return "reviewed"
    if t.spec_ref:
        return "specced"
    return "raw"


def _build_task_md_index(tasks_dir: Path) -> dict[int, Path]:
    """Index docs/tasks/<id>(-<slug>)?.md files by integer task id.

    Files like '010.md' or '010-boundary-map.md' both map to id 10. .yaml
    siblings are ignored. Returns {} when the directory is missing or empty.
    Uses the first 3 digits of the filename as the id key. The first match
    per id wins (sorted lexically — plain '<id>.md' precedes '<id>-slug.md').
    """
    index: dict[int, Path] = {}
    if not tasks_dir or not tasks_dir.exists():
        return index
    for p in sorted(tasks_dir.iterdir()):
        if not p.is_file() or p.suffix != ".md":
            continue
        stem = p.stem  # e.g. '010-boundary-map' or '010'
        # Take leading digit run as id.
        digits = ""
        for ch in stem:
            if ch.isdigit():
                digits += ch
            else:
                break
        if not digits:
            continue
        try:
            tid = int(digits)
        except ValueError:
            continue
        if tid not in index:
            index[tid] = p
    return index


def _read_task_markdown(md_path: Path | None) -> str:
    """Read raw markdown content; return '' on miss/error.

    The frontend renders this via marked.js — we ship the raw source so
    server-side rendering is not required.
    """
    if md_path is None or not md_path.exists():
        return ""
    try:
        return md_path.read_text(encoding="utf-8")
    except OSError:
        return ""


def _lookup_task_map(mapping: dict, task_id, default=None):
    """Lookup helper tolerant to int/str task-id key drift."""
    if task_id in mapping:
        return mapping[task_id]
    sid = str(task_id).strip()
    if sid in mapping:
        return mapping[sid]
    try:
        iid = int(sid)
    except (TypeError, ValueError):
        return default
    return mapping.get(iid, default)


def validate_task_dependency_integrity(tasks: list[dict]) -> list[dict]:
    """Return compact dashboard warnings for malformed IDs and deps."""
    task_ids = {str(t.get("id", "")).strip() for t in tasks if t.get("id")}
    malformed_id_examples: list[str] = []
    orphan_dep_examples: list[str] = []
    self_dep_examples: list[str] = []
    duplicate_dep_examples: list[str] = []
    malformed_id_count = 0
    orphan_dep_count = 0
    self_dep_count = 0
    duplicate_dep_count = 0

    for t in tasks:
        tid = str(t.get("id", "")).strip()
        if not tid:
            continue
        if "#" not in tid:
            malformed_id_count += 1
            if len(malformed_id_examples) < 5:
                malformed_id_examples.append(tid)

        deps = [str(d).strip() for d in (t.get("deps") or []) if str(d).strip()]
        seen: set[str] = set()
        for dep in deps:
            if dep == tid:
                self_dep_count += 1
                if len(self_dep_examples) < 5:
                    self_dep_examples.append(tid)
            if dep in seen:
                duplicate_dep_count += 1
                if len(duplicate_dep_examples) < 5:
                    duplicate_dep_examples.append(f"{tid}->{dep}")
            seen.add(dep)
            if dep not in task_ids:
                orphan_dep_count += 1
                if len(orphan_dep_examples) < 5:
                    orphan_dep_examples.append(f"{tid}->{dep}")

    warnings: list[dict] = []
    if malformed_id_count:
        warnings.append({
            "check": "TASK-ID",
            "location": "task ids",
            "detail": f"{malformed_id_count} malformed id(s), e.g. {', '.join(malformed_id_examples)}",
        })
    if orphan_dep_count:
        warnings.append({
            "check": "DEP-ORPHAN",
            "location": "blocked_by",
            "detail": f"{orphan_dep_count} unresolved dep ref(s), e.g. {', '.join(orphan_dep_examples)}",
        })
    if self_dep_count:
        warnings.append({
            "check": "DEP-SELF",
            "location": "blocked_by",
            "detail": f"{self_dep_count} self-dependency ref(s), e.g. {', '.join(self_dep_examples)}",
        })
    if duplicate_dep_count:
        warnings.append({
            "check": "DEP-DUP",
            "location": "blocked_by",
            "detail": f"{duplicate_dep_count} duplicate dep ref(s), e.g. {', '.join(duplicate_dep_examples)}",
        })
    return warnings


def _normalize_intent_chain(ic) -> dict:
    """Coerce intent_chain to a {domain, objective, action} dict.

    plan_engine accepts both shapes — dict (canonical) and list (legacy 3-tuple
    [vision/domain, operational/objective, action]). Anything else collapses
    to {}.
    """
    if isinstance(ic, dict):
        # Allow either modern (domain/objective/action) or legacy
        # (vision/operational/action) keys; map legacy to modern for the UI.
        return {
            "domain":    ic.get("domain")    or ic.get("vision")      or "",
            "objective": ic.get("objective") or ic.get("operational") or "",
            "action":    ic.get("action")    or "",
        }
    if isinstance(ic, (list, tuple)) and len(ic) >= 1:
        out = {"domain": "", "objective": "", "action": ""}
        keys = ["domain", "objective", "action"]
        for k, v in zip(keys, ic):
            out[k] = str(v) if v is not None else ""
        return out
    return {}


def build_task_dicts(per_repo: dict[str, dict]) -> list:
    """Build dashboard task-dict list from plan_engine data across all repos.

    Every task gets a namespaced id '<slug>#<id:03d>' and a 'phase' derived
    from its milestone.phases[0] (falling back to 'Uncategorized'). deps are
    rewritten to namespaced form. blocked_by_external is rendered into a
    human-readable external_deps list.
    """
    out = []
    # Precompute per-repo done-id sets (normalized task refs) for is_blocked.
    # 2026-05-06 Fix: archived task-ids (docs/tasks/archive/*.yaml) sind faktisch
    # done — sie werden via plan_engine.load_archived_task_ids ergaenzt damit
    # blocked_by zu archived ids korrekt als "resolved" markiert wird.
    # Pre-Fix Bug: 443.blocked_by=[442] blieb "blocked" weil 442 archived war
    # und dadurch nicht in done_refs landete.
    done_by_repo: dict[str, set[str]] = {}
    for slug, data in per_repo.items():
        active_done = {
            _dep_str(slug, tid) for tid, t in data["tasks"].items()
            if (t.status or "").lower() in ("done", "superseded", "absorbed", "wontfix")
        }
        # Archive-Tasks sind alle faktisch done (Frozen Zone WORM-Pattern).
        archive_done = set()
        root = data.get("root")
        if root is not None:
            try:
                archived_ids = plan_engine.load_archived_task_ids(root)
                archive_done = {_dep_str(slug, aid) for aid in archived_ids}
            except (AttributeError, OSError) as e:
                # Fallback: kein archive-loader verfuegbar — leise weiter,
                # alte Verhalten (active-only).
                _ = e
        done_by_repo[slug] = active_done | archive_done
    # Per-repo task-md index. Built once per repo; lookups are O(1).
    md_index_by_repo: dict[str, dict[int, Path]] = {}
    for slug, data in per_repo.items():
        root = data.get("root")
        if root is not None:
            md_index_by_repo[slug] = _build_task_md_index(root / "docs" / "tasks")
        else:
            md_index_by_repo[slug] = {}
    for slug, data in per_repo.items():
        ms = data["milestones"]
        blocking_scores = data.get("blocking_scores") or {}
        done_refs = done_by_repo[slug]
        md_index = md_index_by_repo.get(slug, {})
        def _task_id_sort_key(task) -> tuple[int, int | str]:
            """
            Keep numeric task ids in numeric order; fall back to lexical order
            for non-numeric ids. This avoids int/str comparison TypeError.
            """
            try:
                return (0, int(task.id))
            except (TypeError, ValueError):
                return (1, str(task.id))

        for t in sorted(data["tasks"].values(), key=_task_id_sort_key):
            milestone_obj = ms.get(t.milestone) if t.milestone else None
            phase_key = ""
            if milestone_obj and milestone_obj.phases:
                phase_key = str(milestone_obj.phases[0])
            if not phase_key:
                phase_key = "Uncategorized"
            # Fix 5: task.phase is namespaced `<slug>::<phase_key>` so it
            # matches the phase-registry + gantt grouping.
            phase_key = f"{slug}::{phase_key}"

            # Namespace deps. Single-repo mode keeps ints → string namespaced.
            # Aggregate mode may already contain namespaced strings from
            # load_aggregated, but load_repo_data uses load_tasks (single-repo
            # ints), so this normalizer produces '<slug>#<id>' uniformly.
            deps = [_dep_str(slug, d) for d in (t.blocked_by or [])]

            external_deps = [_external_dep_str(e) for e in (t.blocked_by_external or [])]

            raw_status = (t.status or "pending").lower()
            status_map = {
                "open": "pending", "proposed": "pending", "spec_done": "pending",
                "exploration": "pending", "superseded": "done", "absorbed": "done",
                "deferred": "pending", "blocked": "pending", "wontfix": "done",
                "": "pending",
            }
            status = status_map.get(raw_status, raw_status)

            # is_blocked: any intra-repo blocked_by not done. External deps are
            # out of scope for simple blocked tagging (they may be in another
            # repo; the UI treats them as informational).
            is_blocked = False
            local_prefix = f"{slug}#"
            for dep_ref in deps:
                # External deps are informational in this simple blocked flag.
                if dep_ref.startswith(local_prefix) and dep_ref not in done_refs:
                    is_blocked = True
                    break

            effort_weight = {"S": 1, "M": 3, "L": 8, "XL": 20}.get(t.effort or "M", 3)

            out.append({
                "id": _nsid(slug, t.id),
                "repo": slug,
                "raw_id": t.id,
                "title": t.title or "",
                "status": status,
                "_raw_status": raw_status,
                "prio": "",
                "area": t.area or "",
                "phase": phase_key,
                "deps": deps,
                "external_deps": external_deps,
                "slice": None,
                "slices": [],
                "created": t.created or "",
                "updated": t.updated or "",
                "assignee": t.assignee or "",
                "description": "",
                "intent": "",
                "problem": "",
                "acs": [],
                "workflow_steps": [],
                "constraints": "",
                "kommentare": [],
                "pipeline_stage": _pipeline_stage(t),
                "spec_ref": t.spec_ref or "",
                "dev_path": "",
                "board_result": t.board_result or "",
                "summary": t.summary or "",
                "spec_progress": "",
                "consumed_spec_version": "",
                "parent_task": _nsid(slug, t.parent_task) if t.parent_task else "",
                "sub_tasks": [_nsid(slug, sid) for sid in (t.sub_tasks or []) if sid],
                "intent_chain": _normalize_intent_chain(t.intent_chain),
                "closed": t.closed or "",
                "markdown_body": _read_task_markdown(_lookup_task_map(md_index, t.id)),
                "milestone": _nsms(slug, t.milestone) if t.milestone else "",
                "milestone_title": (milestone_obj.title if milestone_obj else ""),
                "readiness": t.readiness or "",
                "note": t.note or "",
                "blocking_note": t.blocking_note or "",
                "effort": t.effort or "M",
                "effort_weight": effort_weight,
                "blocking_score": int(_lookup_task_map(blocking_scores, t.id, 0) or 0),
                "is_blocked": is_blocked,
                # Task 435 (F-C-014, AC-A.9): Sub-Tags-Propagation in Task-Dict
                "legacy_milestone_key": getattr(t, "legacy_milestone_key", "") or "",
                "migration_note": getattr(t, "migration_note", "") or "",
            })
    return out


def build_phase_data(per_repo: dict[str, dict]) -> tuple[list, dict, set]:
    """Build per-repo-namespaced phase registry.

    Fix 5: phases are now STRICTLY per-repo — keys are `<slug>::<phase_key>`.
    Two repos both declaring 'build' no longer merge into one phase; each
    gets its own Gantt row with a repo badge. Order: each repo's phases in
    declaration order, in --projects order.

    phase_info[<ns_id>] carries `title`, `desc`, `status`, `type`, plus the
    new `repo` (slug) and `phase_key` (plain key) fields — the latter is
    used for CSS color-class lookup (classes can't contain `::`).
    """
    phase_order: list[str] = []
    phase_info: dict[str, dict] = {}
    # Task 435 (B-4 Lock, AC-A.3): Pseudo-Phase 'feature-milestones' als erstes
    # in phase_order pro repo, wenn der repo feature-milestones (M1-M7+M1.5) hat.
    # 2026-05-05: erweitert um M0-cross-cutting + M8 (Decisions-v2 NEU-Slots,
    # INTENT-005 confirmed). POST-MVP bleibt eigene Phase (nicht-Feature-Milestone).
    FEATURE_MILESTONE_KEYS = {"M0-cross-cutting", "M1", "M1.5", "M2", "M3", "M4", "M5", "M6", "M7", "M8"}
    for slug, data in per_repo.items():
        ms = data.get("milestones", {}) or {}
        has_feature_milestones = any(k in FEATURE_MILESTONE_KEYS for k in ms)
        if has_feature_milestones:
            ns_id = f"{slug}::feature-milestones"
            if ns_id not in phase_info:
                phase_info[ns_id] = {
                    "title": "Feature Milestones",
                    "desc": "M1-M7+M1.5 Feature-Milestones (Greenfield-Authority)",
                    "status": "",
                    "type": "implementation",
                    "repo": slug,
                    "phase_key": "feature-milestones",
                }
                phase_order.append(ns_id)
        for p in data["plan"].phases:
            ns_id = f"{slug}::{p.key}"
            if ns_id in phase_info:
                continue
            phase_info[ns_id] = {
                "title": p.title or p.key,
                "desc": p.desc or "",
                "status": "",
                "type": "implementation",
                "repo": slug,
                "phase_key": p.key,
            }
            phase_order.append(ns_id)
    # Every phase is an implementation phase — plan_engine doesn't track a
    # separate type today and no phase belongs to the NON_IMPLEMENTATION
    # exclude-list in multi-repo mode.
    impl_phases = set(phase_order)
    # Tasks whose milestone has no phase fall into "Uncategorized". Emit one
    # Uncategorized bucket PER repo so namespacing stays consistent; only
    # add if/when a milestone actually lands in it (done in build_milestone_data).
    for slug in per_repo.keys():
        ns_id = f"{slug}::Uncategorized"
        if ns_id not in phase_info:
            phase_info[ns_id] = {
                "title": "Uncategorized", "desc": "",
                "status": "", "type": "implementation",
                "repo": slug, "phase_key": "Uncategorized",
            }
            phase_order.append(ns_id)
            impl_phases.add(ns_id)
    return phase_order, phase_info, impl_phases


def build_milestone_data(per_repo: dict[str, dict]) -> list:
    """Per-milestone aggregate list for Gantt/Board rendering.

    Each entry: {key, title, phase, status, repo, tasks[nsid], order, is_target}.
    key is namespaced ('<slug>#<milestone_key>'). Phase defaults to the
    milestone's first listed phase, falling back to 'Uncategorized'.

    Task 435 (B-4 Lock, AC-A.3): Feature-Milestones M1-M7+M1.5 werden in die
    Pseudo-Phase 'feature-milestones' platziert. parallel_to-Visualisierung via
    Lane-Pack — Feature-Milestones bekommen 'parallel_to' Marker im Output.
    """
    # 2026-05-05: erweitert um M0-cross-cutting + M8 (Decisions-v2 NEU-Slots,
    # INTENT-005 confirmed). POST-MVP bleibt eigene Phase (nicht-Feature-Milestone).
    FEATURE_MILESTONE_KEYS = {"M0-cross-cutting", "M1", "M1.5", "M2", "M3", "M4", "M5", "M6", "M7", "M8"}
    out = []
    for slug, data in per_repo.items():
        plan = data["plan"]
        target_key = plan.target or ""
        ms = data["milestones"]
        for i, (mkey, m) in enumerate(ms.items()):
            # Task 435 (B-4): Feature-Milestone -> Pseudo-Phase
            if mkey in FEATURE_MILESTONE_KEYS:
                phase = f"{slug}::feature-milestones"
            else:
                raw_phase = (m.phases[0] if m.phases else "") or "Uncategorized"
                # Fix 5: phases are per-repo — prefix with slug::. This matches
                # build_phase_data's namespaced phase_order/phase_info keys.
                phase = f"{slug}::{raw_phase}"
            # Namespace requires so arrows can resolve across the unified
            # milestones_list (cross-repo dep edges not currently emitted by
            # plan_engine; same-repo deps use raw keys).
            deps_ns = [_nsms(slug, r) for r in (m.requires or [])]
            entry = {
                "key": _nsms(slug, mkey),
                "raw_key": mkey,
                "title": m.title or mkey,
                "phase": phase,
                "status": m.status or "future",
                "repo": slug,
                "tasks": [_nsid(slug, tid) for tid in (m.tasks or [])],
                "deps": deps_ns,
                "order": i,
                "is_target": (mkey == target_key),
            }
            # Task 435 flat-Felder durchschleifen: feature, app_status_post_milestone,
            # parallel_to. Renderer kann diese fuer Display nutzen.
            for fname in ("feature", "app_status_post_milestone", "parallel_to",
                          "fallback_strategy", "capabilities"):
                v = getattr(m, fname, None)
                if v:
                    entry[fname] = v
            out.append(entry)
    return out


def build_top_panel(host_data: dict | None, host_slug: str) -> dict:
    """Build the Top-Panel dict rendered above the Gantt.

    Sources EVERYTHING from the host repo's plan_engine result — independent
    of which repos the user has toggled on in the UI. When host_data is None
    (host repo missing / empty), returns a placeholder with zeros.
    """
    if not host_data:
        return {
            "host_repo": host_slug,
            "target": "",
            "target_title": "(host repo not loaded)",
            "target_status": "",
            "bottleneck": None,
            "next_actions": [],
            "critical_path": [],
            "critical_path_effort": 0,
            "warnings": [],
            "north_star": "",
        }

    plan = host_data["plan"]
    ms = host_data["milestones"]
    tasks = host_data["tasks"]
    next_actions_ids = host_data["next_actions"]
    critical_path = host_data["critical_path"]
    issues = host_data["issues"]

    target_key = plan.target
    target_ms = ms.get(target_key)
    target_title = target_ms.title if target_ms else target_key
    target_status = target_ms.status if target_ms else ""

    # Bottleneck: the highest-blocking-score ready-or-in-progress task on the
    # critical path, else the first critical-path task, else None.
    bottleneck = None
    if critical_path:
        cp_tid = critical_path[0]
        cp_task = tasks.get(cp_tid)
        if cp_task:
            bottleneck = {
                "id": _nsid(host_slug, cp_task.id),
                "title": cp_task.title,
                "status": cp_task.status,
                "milestone": _nsms(host_slug, cp_task.milestone) if cp_task.milestone else "",
                "effort": cp_task.effort,
            }

    na_list = []
    for tid in next_actions_ids[:5]:
        t = tasks.get(tid)
        if not t:
            continue
        na_list.append({
            "id": _nsid(host_slug, t.id),
            "title": t.title,
            "milestone": _nsms(host_slug, t.milestone) if t.milestone else "",
            "effort": t.effort,
        })

    # Iteration 2 (CR-003 Fix Side-Effect): critical_path kann nun Mixed-Items
    # enthalten (int task-id, str milestone-key, list parallel, str post-MVP)
    # weil compute_critical_path 4-stufigen Lookup macht und plan_data
    # `critical_path:` honoriert. Render nur int-Items als Tasks; alles
    # Andere skippen (Top-Panel zeigt nur Task-Items, kein Milestone-Render).
    cp_list = []
    for tid in critical_path:
        if not isinstance(tid, int) or isinstance(tid, bool):
            continue
        t = tasks.get(tid)
        if not t:
            continue
        cp_list.append({
            "id": _nsid(host_slug, t.id),
            "title": t.title,
            "status": t.status,
            "effort": t.effort,
        })
    cp_effort = sum(
        (
            t.effort_weight
            for t in (
                tasks.get(tid)
                for tid in critical_path
                if isinstance(tid, int) and not isinstance(tid, bool)
            )
            if t
        ),
        0,
    )

    warnings_list = []
    for i in issues:
        if i.severity != "WARN":
            continue
        loc = ""
        if i.task_id is not None:
            loc = _nsid(host_slug, i.task_id) if isinstance(i.task_id, int) else str(i.task_id)
        elif i.milestone_key:
            loc = _nsms(host_slug, i.milestone_key)
        warnings_list.append({
            "check": i.check,
            "location": loc,
            "detail": i.detail,
        })
    errors_count = sum(1 for i in issues if i.severity == "ERROR")
    if errors_count:
        warnings_list.insert(0, {
            "check": "ERRORS",
            "location": host_slug,
            "detail": f"{errors_count} validation error(s) — run `plan_engine --validate`",
        })

    return {
        "host_repo": host_slug,
        "target": target_key,
        "target_title": target_title,
        "target_status": target_status,
        "bottleneck": bottleneck,
        "next_actions": na_list,
        "critical_path": cp_list,
        "critical_path_effort": cp_effort,
        "warnings": warnings_list,
        "north_star": plan.north_star or "",
    }


# ---------------------------------------------------------------------------
# Mermaid graph generation
# ---------------------------------------------------------------------------

def _mermaid_id(nsid: str) -> str:
    """Mermaid-safe node id: strip '#' and other non-alnum chars."""
    return re.sub(r'[^A-Za-z0-9_]', '_', nsid)


def generate_mermaid(tasks: list, slices: dict) -> str:
    """Generate Mermaid flowchart code for dependency graph.

    tasks use namespaced string ids ('<slug>#<id>'); deps are namespaced too.
    slices is unused (kept for signature compat — the MVP slice concept is
    retired; every edge is rendered as a plain arrow).
    """
    lines = ["graph LR"]

    task_map = {t["id"]: t for t in tasks}
    has_relations = set()
    for t in tasks:
        for d in t.get("deps", []) or []:
            if d in task_map:
                has_relations.add(t["id"])
                has_relations.add(d)

    if not has_relations:
        lines.append('    EMPTY["No dependency relationships found"]')
        return "\n".join(lines)

    lines.append("    classDef done fill:#2e7d32,stroke:#4caf50,color:#ededed")
    lines.append("    classDef in_progress fill:#3a6a96,stroke:#7ba3cc,color:#ededed")
    lines.append("    classDef pending fill:#2c2c30,stroke:#5c5c64,color:#ededed")

    def _short_title(title: str) -> str:
        s = (title or "")[:25]
        if len(title or "") > 25:
            s += ".."
        return s.replace('"', "'")

    added_nodes: set[str] = set()

    def _ensure_node(tid: str):
        if tid in added_nodes:
            return
        t = task_map.get(tid)
        label = _short_title(t["title"]) if t else "???"
        lines.append(f'    {_mermaid_id(tid)}["{tid} {label}"]')
        added_nodes.add(tid)

    for t in tasks:
        tid = t["id"]
        if tid not in has_relations:
            continue
        _ensure_node(tid)
        for dep in t.get("deps", []) or []:
            if dep not in task_map:
                continue
            _ensure_node(dep)
            lines.append(f"    {_mermaid_id(dep)} --> {_mermaid_id(tid)}")

    for tid in added_nodes:
        t = task_map.get(tid)
        if not t:
            continue
        status = t["status"]
        mid = _mermaid_id(tid)
        if status == "done":
            lines.append(f"    class {mid} done")
        elif status == "in_progress":
            lines.append(f"    class {mid} in_progress")
        else:
            lines.append(f"    class {mid} pending")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Gantt roadmap rendering (Python-side)
# ---------------------------------------------------------------------------

def _topo_sort_tasks(tasks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Sort tasks by dependency order (Kahn's algorithm)."""
    task_ids = {t["id"] for t in tasks}
    task_map = {t["id"]: t for t in tasks}
    in_deg = {t["id"]: 0 for t in tasks}
    adj: dict[str, list[str]] = {t["id"]: [] for t in tasks}

    for t in tasks:
        for d in t.get("deps", []):
            if d in task_ids:
                adj[d].append(t["id"])
                in_deg[t["id"]] += 1

    queue = sorted([tid for tid, deg in in_deg.items() if deg == 0])
    order = []
    while queue:
        tid = queue.pop(0)
        order.append(tid)
        for nxt in sorted(adj.get(tid, [])):
            in_deg[nxt] -= 1
            if in_deg[nxt] == 0:
                queue.append(nxt)
        queue.sort()

    remaining = sorted(tid for tid in task_ids if tid not in set(order))
    order.extend(remaining)
    return [task_map[tid] for tid in order]


def _esc(text: str) -> str:
    """HTML-escape a string."""
    if not text:
        return ""
    return (str(text)
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;"))


def _render_gantt(tasks: list, milestones: list, phase_order: list,
                  phase_info: dict) -> str:
    """Render v2 Gantt with dependency-topological X-axis layout.

    Each phase section remains a collapsible group (outer structure unchanged).
    WITHIN each phase, milestones are laid out on a 2D grid:
      - X (column/left) = topological depth within the phase sub-DAG
        (roots = 0, deeper chains shift right).
      - Y (row/top)     = greedy lane-packing; parallel milestones at the
        same depth occupy the next free row.
    Bars are absolutely-positioned inside a `.gantt-track` container with an
    explicit width/height so `reflowArrows` sees real coordinates.

    Done milestones (all tasks terminal) default to a compact collapsed strip;
    a click cycles collapsed → bar → expanded (task rows). Non-done milestones
    default to `bar`.
    """
    task_map = {t["id"]: t for t in tasks}

    # Layout constants — interval-based Gantt. Bar width scales with task
    # count; no more fixed-column grid. Kept in sync with CSS.
    ROW_HEIGHT_PX = 48
    PX_PER_TASK = 70
    MIN_BAR_WIDTH_PX = 360
    MAX_BAR_WIDTH_PX = 840
    DONE_CHIP_WIDTH_PX = 100  # Variant B: done-Milestones get narrow chip width
                              # so active milestones reclaim horizontal space
    H_GAP_PX = 12  # horizontal padding after parent end

    # Group milestones by phase (filtering to phases with at least one task).
    by_phase: dict[str, list] = {}
    phase_has_target: dict[str, bool] = {}
    phase_has_active: dict[str, bool] = {}
    for m in milestones:
        if not m["tasks"]:
            continue
        # Fix 5: m["phase"] is already namespaced `<slug>::<phase_key>`.
        # Fallback preserves namespacing when a milestone has no phase.
        phase = m["phase"] or f"{m.get('repo', '')}::Uncategorized"
        by_phase.setdefault(phase, []).append(m)
        if m.get("is_target"):
            phase_has_target[phase] = True
        if m.get("status") == "active":
            phase_has_active[phase] = True

    # Build default-open set (Target-phase + phases with active milestones).
    default_open = {p for p in by_phase if phase_has_target.get(p) or phase_has_active.get(p)}
    if not default_open and by_phase:
        # At least open the first phase so the dashboard isn't empty on load.
        default_open.add(next(iter(by_phase)))

    terminal = {"done", "superseded", "absorbed", "wontfix"}

    def _seg_status(t: dict) -> str:
        raw = (t.get("_raw_status") or t.get("status") or "pending").lower()
        if raw in terminal:
            return "done"
        if raw == "in_progress":
            return "in_progress"
        if raw == "pending":
            # Pending but blocked? tag as blocked for the segment color.
            return "blocked" if t.get("is_blocked") else "pending"
        return raw or "pending"

    def _is_ms_done(m_tasks: list) -> bool:
        """Milestone is 'done' iff every task is in a terminal status."""
        if not m_tasks:
            return False
        return all(t.get("status") in terminal for t in m_tasks)

    def _layout_phase(mlist: list) -> tuple[dict, int, int]:
        """Interval-based Gantt layout.

        Returns (placement, track_width, track_height) where
        placement[m_key] = (left_px, top_px, width_px).

        Bar width scales with task count (clamped). X-position is derived
        from the rightmost parent's end-x within the phase. Lane-packing:
        pick the lowest row >= max(parent rows) where [start, end] does
        not overlap any already-placed milestone in the same row.
        """
        keys_in_phase = {m["key"] for m in mlist}
        in_deps: dict[str, list] = {
            m["key"]: [d for d in (m.get("deps") or []) if d in keys_in_phase]
            for m in mlist
        }

        # Topological depth (memoized DFS) — only used to order iteration
        # so parents are placed before children.
        depth: dict[str, int] = {}
        visiting: set = set()

        def _depth_of(k: str) -> int:
            if k in depth:
                return depth[k]
            if k in visiting:
                return 0
            visiting.add(k)
            ds = in_deps.get(k, [])
            d = 0 if not ds else 1 + max(_depth_of(p) for p in ds)
            visiting.discard(k)
            depth[k] = d
            return d

        for m in mlist:
            _depth_of(m["key"])

        ordered = sorted(
            enumerate(mlist), key=lambda iv: (depth[iv[1]["key"]], iv[0])
        )

        # placement[key] = (left_px, top_px, width_px)
        placement: dict[str, tuple] = {}
        # rows[row_index] = list of (left_px, width_px) already placed.
        rows: dict[int, list] = {}
        max_row = 0
        for _, m in ordered:
            k = m["key"]
            # Variant B Layout: done-Milestones bekommen Chip-Width statt
            # task-count-proportional-Width. Active-Milestones reclaim den
            # freigewordenen Horizontal-Platz. Expand bei Click ist
            # Drop-down-Popup (CSS) — kein Layout-Shift zur Laufzeit noetig.
            m_tasks_data = [task_map[tid] for tid in m["tasks"] if tid in task_map]
            is_done_ms = bool(m_tasks_data) and all(
                t["status"] in terminal for t in m_tasks_data
            )
            if is_done_ms:
                width = DONE_CHIP_WIDTH_PX
            else:
                task_count = len(m["tasks"])
                width = max(
                    MIN_BAR_WIDTH_PX,
                    min(MAX_BAR_WIDTH_PX, task_count * PX_PER_TASK),
                )
            parents = [p for p in in_deps.get(k, []) if p in placement]
            # 2026-05-05 Layout-Patch (User-Lock 'links angeschlagen'): Time-Axis-Versatz
            # entfernt — sequentielles Single-Dev-Plan, parent-end-x-Versatz nicht
            # informativ, kostet nur Horizontal-Scroll. Alle Bars beginnen bei x=0,
            # vertikal gestapelt in topological order (parents sitzen hoeher per row_min).
            start_x = 0
            if parents:
                parent_rows = [placement[p][1] // ROW_HEIGHT_PX for p in parents]
                row_min = max(parent_rows) + 1  # naechste Zeile nach max-parent
            else:
                row_min = 0
            end_x = start_x + width

            row = row_min
            while True:
                occupants = rows.get(row, [])
                collision = any(
                    not (end_x <= ex_l or start_x >= ex_l + ex_w)
                    for (ex_l, ex_w) in occupants
                )
                if not collision:
                    break
                row += 1
            rows.setdefault(row, []).append((start_x, width))
            placement[k] = (start_x, row * ROW_HEIGHT_PX, width)
            if row > max_row:
                max_row = row

        if placement:
            track_width = max(left + w for (left, _t, w) in placement.values())
        else:
            track_width = MIN_BAR_WIDTH_PX
        track_height = (max_row + 1) * ROW_HEIGHT_PX
        return placement, track_width, track_height

    html_parts = ['<div class="gantt" id="gantt-root">']
    html_parts.append('<svg class="gantt-arrows" id="gantt-arrows" aria-hidden="true"></svg>')

    # Iterate phases in declared order, then any leftover (data-driven).
    seen_phases: set = set()
    phase_iter: list = []
    for p in phase_order:
        if p in by_phase and p not in seen_phases:
            phase_iter.append(p)
            seen_phases.add(p)
    for p in by_phase:
        if p not in seen_phases:
            phase_iter.append(p)
            seen_phases.add(p)

    def _is_default_hidden(phase_id: str) -> bool:
        info = phase_info.get(phase_id, {})
        title = (info.get("title") or phase_id).lower()
        pk = (info.get("phase_key") or
              (phase_id.split("::", 1)[1] if "::" in phase_id else phase_id)).lower()
        return title == "foundation" or pk == "foundation"

    # Partition: visible first, default-hidden at the bottom of their repo
    # group. Repo grouping is implicit in phase_order (all of repo A, then
    # repo B, …), so we split per-repo chunks and re-append hidden tails.
    # Simpler approach: split the flat list — since phase_order is already
    # repo-grouped, per-repo order is preserved naturally.
    visible_phases: list = []
    hidden_phases: list = []
    for p in phase_iter:
        if _is_default_hidden(p):
            hidden_phases.append(p)
        else:
            visible_phases.append(p)
    # Group by repo so hidden phases land at the bottom of THEIR repo, not
    # at the global bottom. Preserve original order within each bucket.
    def _repo_of(p: str) -> str:
        return phase_info.get(p, {}).get("repo") or (
            p.split("::", 1)[0] if "::" in p else ""
        )
    repos_seen: list = []
    by_repo_visible: dict = {}
    by_repo_hidden: dict = {}
    for p in phase_iter:
        r = _repo_of(p)
        if r not in by_repo_visible:
            repos_seen.append(r)
            by_repo_visible[r] = []
            by_repo_hidden[r] = []
        if _is_default_hidden(p):
            by_repo_hidden[r].append(p)
        else:
            by_repo_visible[r].append(p)
    phase_iter = []
    for r in repos_seen:
        phase_iter.extend(by_repo_visible[r])
        phase_iter.extend(by_repo_hidden[r])

    for phase in phase_iter:
        mlist = by_phase[phase]
        p_info = phase_info.get(phase, {"title": phase, "desc": ""})
        p_title = p_info.get("title") or phase
        # Fix 5: split namespaced phase id `<slug>::<phase_key>` for CSS color
        # class lookup (classes can't carry `::`) and the repo badge.
        p_repo = p_info.get("repo") or (phase.split("::", 1)[0] if "::" in phase else "")
        p_plain_key = p_info.get("phase_key") or (phase.split("::", 1)[1] if "::" in phase else phase)

        # Phase stats: tasks across all its milestones.
        p_task_ids: list = []
        for m in mlist:
            p_task_ids.extend(m["tasks"])
        p_tasks = [task_map[tid] for tid in p_task_ids if tid in task_map]
        p_total = len(p_tasks)
        p_done = sum(1 for t in p_tasks if t["status"] in terminal)
        is_collapsed = phase not in default_open
        collapsed_attr = ' data-collapsed="true"' if is_collapsed else ''
        chevron = "&#9656;" if is_collapsed else "&#9662;"  # ▸ / ▾

        # data-phase keeps the PLAIN key so existing color CSS rules apply.
        # data-phase-id carries the full namespaced id for JS collapse state.
        # data-default-hidden marks phases that start hidden on first load
        # (currently: any phase titled/keyed "foundation").
        default_hidden = _is_default_hidden(phase)
        default_hidden_attr = ' data-default-hidden="true"' if default_hidden else ''
        html_parts.append(
            f'<div class="gantt-phase" data-phase="{_esc(p_plain_key)}" '
            f'data-phase-id="{_esc(phase)}" data-repo="{_esc(p_repo)}"'
            f'{collapsed_attr}{default_hidden_attr}>'
        )
        repo_badge = (
            f'<span class="phase-repo-badge mono">{_esc(p_repo)}</span>'
            if p_repo else ''
        )
        html_parts.append(
            f'  <div class="phase-header" onclick="togglePhase(\'{_esc(phase)}\')" tabindex="0" role="button" aria-expanded="{str(not is_collapsed).lower()}">'
            f'<span class="phase-chevron">{chevron}</span>'
            f'{repo_badge}'
            f'<span class="phase-title">{_esc(p_title)}</span>'
            f'<span class="phase-count mono">{p_done}/{p_total}</span>'
            f'<span class="phase-hide-btn" role="button" tabindex="0" '
            f'title="Hide phase" '
            f'onclick="event.stopPropagation(); hidePhase(\'{_esc(phase)}\')">&#10005;</span>'
            f'<span class="phase-restore-btn" role="button" tabindex="0" '
            f'title="Restore phase" '
            f'onclick="event.stopPropagation(); restorePhase(\'{_esc(phase)}\')">&#8635;</span>'
            f'</div>'
        )
        html_parts.append('  <div class="phase-milestones">')

        # Compute interval-based placement for this phase.
        placement, track_w, track_h = _layout_phase(mlist)
        html_parts.append(
            f'    <div class="gantt-track" '
            f'style="width:{track_w}px; height:{track_h}px;">'
        )

        for m in mlist:
            m_tasks = [task_map[tid] for tid in m["tasks"] if tid in task_map]
            # Sort: done first (for done-stacking), then in_progress, then
            # remaining tasks in dependency-order (topological). Done +
            # in_progress sorted by ID for stability; rest topo-sorted so the
            # bar-segment order matches actual execution order (Kahn's via
            # _topo_sort_tasks). Resolves "Tasks erscheinen wirr" — the bar now
            # reads left-to-right as the work plan does.
            done_part = sorted(
                [t for t in m_tasks if t["status"] in terminal],
                key=lambda t: t["id"],
            )
            ip_part = sorted(
                [t for t in m_tasks if t["status"] == "in_progress"],
                key=lambda t: t["id"],
            )
            rest_part = _topo_sort_tasks(
                [t for t in m_tasks
                 if t["status"] not in terminal and t["status"] != "in_progress"]
            )
            m_tasks = done_part + ip_part + rest_part
            total_effort = sum(t.get("effort_weight", 3) for t in m_tasks) or 1
            m_done = sum(1 for t in m_tasks if t["status"] in terminal)
            m_total = len(m_tasks)
            pct_done = int(round(100.0 * m_done / m_total)) if m_total else 0
            ms_done = _is_ms_done(m_tasks)

            repo_slug = m.get("repo", "")
            m_key = m["key"]
            m_status = m.get("status") or "future"

            # Partition tasks into done vs non-done (preserving sort order).
            done_tasks_list = [t for t in m_tasks if t["status"] in terminal]
            open_tasks_list = [t for t in m_tasks if t["status"] not in terminal]
            # Done-stack is shown only when we have a mix (≥1 done AND ≥1 open).
            # If ms_done (all done) we render individuals normally and let the
            # existing tri-state collapsed-strip do its thing.
            use_done_stack = (
                not ms_done and len(done_tasks_list) >= 1 and len(open_tasks_list) >= 1
            )

            def _render_seg(t: dict, extra_class: str = "",
                            pct_override: float | None = None) -> str:
                pct_local = (pct_override if pct_override is not None
                             else 100.0 * t.get("effort_weight", 3) / total_effort)
                seg_st = _seg_status(t)
                tid = t["id"]
                repo_slug_t = t.get("repo", "")
                _m_tail = re.search(r'\d+$', str(tid))
                numeric_id = _m_tail.group(0) if _m_tail else str(tid)
                cls = f"bar-segment bar-segment--{seg_st}"
                if extra_class:
                    cls += f" {extra_class}"
                return (
                    f'<div class="{cls}" '
                    f'style="width:{pct_local:.2f}%" '
                    f'data-task-id="{_esc(tid)}" '
                    f'data-repo="{_esc(repo_slug_t)}" '
                    f'title="[{_esc(tid)}] {_esc(t["title"])} — {seg_st}" '
                    f'onclick="event.stopPropagation(); openTaskModal(\'{_esc(tid)}\')">'
                    f'<span class="seg-id mono">{_esc(numeric_id)}</span>'
                    f'</div>'
                )

            seg_html = []
            if use_done_stack:
                # Stack: fixed 42px via CSS flex (no inline width). Non-done
                # segments rescale to fill the remaining bar — that's the
                # space-saving effect of collapsing done-tasks.
                n_done = len(done_tasks_list)
                non_done_weight = sum(
                    t.get("effort_weight", 3) for t in open_tasks_list
                ) or 1
                seg_html.append(
                    f'<div class="bar-segment bar-segment--done-stack" '
                    f'data-milestone="{_esc(m_key)}" '
                    f'data-done-count="{n_done}" '
                    f'onclick="event.stopPropagation(); toggleDoneStack(\'{_esc(m_key)}\', this)" '
                    f'title="{n_done} done tasks — click to expand">'
                    f'<span class="seg-id mono">{n_done}&#10003;</span>'
                    f'</div>'
                )
                # Individual done segments (hidden by default via CSS).
                # Keep original widths so the expanded view retains true
                # proportions relative to the whole milestone.
                for t in done_tasks_list:
                    seg_html.append(_render_seg(t, extra_class="done-individual"))
                # Non-done segments: widths rescaled to sum = 100% of the
                # bar. The fixed-width stack (42px via CSS flex) overlays
                # this naturally; flex-shrink compresses all segments to
                # fit the bar minus 42px.
                for t in open_tasks_list:
                    pct_nd = 100.0 * t.get("effort_weight", 3) / non_done_weight
                    seg_html.append(_render_seg(t, pct_override=pct_nd))
            else:
                for t in m_tasks:
                    seg_html.append(_render_seg(t))

            # Status icon (precedence: ms_done → ✓, blocked → 🔒, active → →, else ○).
            if ms_done:
                ms_icon = "&#10003;"  # ✓
            elif m_status == "blocked":
                ms_icon = "&#128274;"  # 🔒
            elif m_status == "active":
                ms_icon = "&#8594;"  # →
            else:
                ms_icon = "&#9675;"  # ○

            left_px, top_px, width_px = placement[m_key]
            row_index = top_px // ROW_HEIGHT_PX
            # Default display-state: collapsed iff done; else bar.
            init_state = "collapsed" if ms_done else "bar"

            wrap_style = (
                f"left:{left_px}px; top:{top_px}px; "
                f"width:{width_px}px;"
            )
            # Task 435 (B-4 Lock, AC-A.3): parallel_to-Visualisierung via Lane-Pack.
            # data-parallel_to + lane-pack-CSS-Class wenn Milestone parallel_to-Liste hat.
            parallel_to_list = m.get("parallel_to") or []
            parallel_attr = ""
            lane_pack_class = ""
            if parallel_to_list:
                pto = ",".join(str(p) for p in parallel_to_list)
                parallel_attr = f' data-parallel_to="{_esc(pto)}"'
                lane_pack_class = " lane-pack"
            # Feature-Field als data-attribute fuer Display
            feature_attr = ""
            if m.get("feature"):
                feature_attr = f' data-feature="{_esc(str(m.get("feature"))[:120])}"'
            html_parts.append(
                f'    <div class="gantt-milestone-wrap{lane_pack_class}" '
                f'data-milestone="{_esc(m_key)}" '
                f'data-repo="{_esc(repo_slug)}" data-row="{row_index}"'
                f'{parallel_attr}{feature_attr} '
                f'style="{wrap_style}">'
            )
            # Header row (above the bar): icon + key + title + progress%.
            html_parts.append(
                f'      <div class="milestone-header-row">'
                f'<span class="ms-icon mono">{ms_icon}</span>'
                f'<span class="bar-key mono">{_esc(m["raw_key"])}</span>'
                f'<span class="bar-title">{_esc(m["title"])}</span>'
                f'<span class="bar-progress-label mono">{pct_done}%</span>'
                f'</div>'
            )
            # Bar row: pure segment strip.
            html_parts.append(
                f'      <div class="milestone-bar" data-milestone="{_esc(m_key)}" '
                f'data-repo="{_esc(repo_slug)}" '
                f'data-status="{_esc(m_status)}" '
                f'data-ms-done="{"true" if ms_done else "false"}" '
                f'data-display-state="{init_state}" '
                f'data-done-expanded="false" '
                f'tabindex="0" '
                f'onclick="toggleMilestoneDisplay(\'{_esc(m_key)}\')" '
                f'role="button" aria-expanded="false" '
                f'title="{_esc(m["title"])}">'
                f'<div class="bar-segments">{"".join(seg_html)}</div>'
                f'</div>'
            )

            # Expanded task rows.
            row_html = []
            for t in m_tasks:
                t_repo = t.get("repo", "")
                t_status = t.get("status", "pending")
                t_raw = t.get("_raw_status", t_status)
                icon = "&#10003;" if t_status in terminal else (
                    "&#9679;" if t_status == "in_progress" else (
                        "&#128274;" if t.get("is_blocked") else "&#8594;"
                    )
                )
                # Task 435 (F-C-014, AC-A.9): Sub-Tags-Rendering im Dashboard.
                lmk = t.get("legacy_milestone_key") or ""
                mnt = t.get("migration_note") or ""
                sub_tags_attr = ""
                sub_tags_html = ""
                if lmk:
                    sub_tags_attr += f' data-legacy_milestone_key="{_esc(lmk)}"'
                    sub_tags_html += (
                        f'<span class="legacy-milestone-key mono small text-muted" '
                        f'title="legacy_milestone_key">[{_esc(lmk)}]</span>'
                    )
                if mnt:
                    # Multiline-Notes: HTML-escape behaelt newlines via <br> intent
                    short = mnt.replace("\n", " | ")[:80]
                    sub_tags_attr += f' data-migration_note="{_esc(short)}"'
                row_html.append(
                    f'        <div class="gantt-task-row" '
                    f'data-task-id="{_esc(t["id"])}" '
                    f'data-repo="{_esc(t_repo)}"'
                    f'{sub_tags_attr} '
                    f'onclick="event.stopPropagation(); openTaskModal(\'{_esc(t["id"])}\')">'
                    f'<span class="task-status-icon status-{_esc(t_raw)}">{icon}</span>'
                    f'<span class="task-id mono">[{_esc(t["id"])}]</span>'
                    f'<span class="task-title-short">{_esc((t.get("title") or "")[:48])}</span>'
                    f'<span class="effort-badge effort-{_esc(t.get("effort", "M"))}">{_esc(t.get("effort", "M"))}</span>'
                    f'{sub_tags_html}'
                    f'</div>'
                )
            html_parts.append(
                f'      <div class="milestone-tasks-expanded" data-ms-tasks="{_esc(m_key)}">'
                + "".join(row_html) +
                '      </div>'
            )
            html_parts.append('    </div>')

        html_parts.append('    </div>')  # /.gantt-track
        html_parts.append('  </div>')
        html_parts.append('</div>')

    html_parts.append('</div>')
    return "\n".join(html_parts)


# ---------------------------------------------------------------------------
# HTML generation
# ---------------------------------------------------------------------------

def generate_html(tasks, slices, north_star, hook, mermaid_code, gen_time,
                  prebuild, feature_registry, amendments, spec_health,
                  readiness_data=None, phase_order=None, phase_info=None,
                  impl_phases=None, top_panel=None, projects=None,
                  host_repo="", milestones=None, freshness_meta=None,
                  page_title="") -> str:
    """Generate v2 Dashboard HTML.

    v2 views per sub-specs:
    - dev-dashboard.md v4.3 (design system, Zinc palette, Inter/JetBrainsMono)
    - dev-dashboard-roadmap-v2.md v2.1 (compact Gantt, task-segments, expandable rows)
    - dev-dashboard-board-v2.md v2.1 (3-column Kanban, milestone-groups, modal)

    Legacy signature-params (slices/hook/mermaid_code/prebuild/feature_registry/
    amendments/spec_health/readiness_data/impl_phases) kept for caller compat
    but are unused — the v2 dashboard does not render those views.
    """
    top_panel = top_panel or {}
    projects = projects or []
    phase_order = phase_order or []
    phase_info = phase_info or {}
    milestones = milestones or []
    freshness_meta = freshness_meta or {}

    total = len(tasks)
    terminal = {"done", "superseded", "absorbed", "wontfix"}
    done_count = sum(1 for t in tasks if t["status"] in terminal)
    active_count = sum(1 for t in tasks if t["status"] == "in_progress")
    pending_count = total - done_count - active_count

    # ------------------------------------------------------------------
    # Classify tasks v2: open / in_progress / done (per board-v2 spec)
    # ------------------------------------------------------------------
    open_tasks: list = []
    active_tasks: list = []
    done_tasks: list = []
    for t in tasks:
        if t["status"] in terminal:
            done_tasks.append(t)
        elif t["status"] == "in_progress":
            active_tasks.append(t)
        else:
            open_tasks.append(t)

    # Open sort: ready first, blocking_score desc, effort asc.
    open_tasks.sort(key=lambda t: (
        1 if t.get("is_blocked") else 0,
        -int(t.get("blocking_score", 0) or 0),
        int(t.get("effort_weight", 3) or 3),
        t["id"],
    ))
    active_tasks.sort(key=lambda t: (
        -int(t.get("blocking_score", 0) or 0), t["id"]
    ))
    done_tasks.sort(key=lambda t: t["id"], reverse=True)
    done_tasks = done_tasks[:30]

    def _group_by_ms(col_tasks: list) -> list:
        groups: dict = {}
        order: list = []
        for t in col_tasks:
            key = t.get("milestone") or ""
            if key not in groups:
                groups[key] = []
                order.append(key)
            groups[key].append(t)
        return [(k, groups[k]) for k in order]

    open_groups = _group_by_ms(open_tasks)
    active_groups = _group_by_ms(active_tasks)
    done_groups = _group_by_ms(done_tasks)

    ms_map: dict = {m["key"]: m for m in milestones}
    task_status_by_id = {str(t.get("id", "")): str(t.get("status", "")) for t in tasks}

    # ------------------------------------------------------------------
    # Top-panel rendering (preserved from v1)
    # ------------------------------------------------------------------
    tp_target = _esc(top_panel.get("target_title") or top_panel.get("target", ""))
    tp_target_status = _esc(top_panel.get("target_status", ""))
    tp_host = _esc(top_panel.get("host_repo", host_repo))
    tp_bn = top_panel.get("bottleneck")
    if tp_bn:
        bn_html = (f'<span class="tp-task-id">{_esc(tp_bn["id"])}</span>'
                   f' <span class="tp-task-title">{_esc(tp_bn["title"])}</span>'
                   f' <span class="tp-task-meta">[{_esc(tp_bn.get("effort", "M"))}'
                   f' / {_esc(tp_bn.get("status", ""))}]</span>')
    else:
        bn_html = '<span class="tp-empty">&mdash;</span>'

    na = top_panel.get("next_actions") or []
    if na:
        na_html = ''.join(
            f'<div class="tp-na-item">'
            f'<span class="tp-task-id">{_esc(n["id"])}</span> '
            f'<span class="tp-task-title">{_esc(n["title"])}</span> '
            f'<span class="tp-task-meta">[{_esc(n.get("effort", "M"))}]</span>'
            f'</div>'
            for n in na[:3]
        )
    else:
        na_html = '<span class="tp-empty">&mdash;</span>'

    cp = top_panel.get("critical_path") or []
    cp_effort = top_panel.get("critical_path_effort", 0)
    if cp:
        cp_html = (' <span class="tp-cp-sep">&rarr;</span> '.join(
            f'<span class="tp-task-id">{_esc(c["id"])}</span>' for c in cp[:6]
        ))
        if len(cp) > 6:
            cp_html += f' <span class="tp-cp-more">+{len(cp) - 6} more</span>'
        cp_html += f' <span class="tp-cp-effort">&middot; effort {cp_effort}</span>'
    else:
        cp_html = '<span class="tp-empty">&mdash;</span>'

    warnings_list = top_panel.get("warnings") or []
    warn_count = len(warnings_list)
    if warn_count:
        warn_items = ''.join(
            f'<li><span class="tp-warn-check">{_esc(w["check"])}</span>'
            f' <span class="tp-warn-loc">{_esc(w.get("location", ""))}</span>: '
            f' {_esc(w.get("detail", ""))}</li>'
            for w in warnings_list[:20]
        )
        if warn_count > 20:
            warn_items += f'<li class="tp-warn-more">+{warn_count - 20} more</li>'
        warn_html = f'<details class="tp-warnings"><summary>Warnings <span class="tp-warn-badge">{warn_count}</span></summary><ul>{warn_items}</ul></details>'
    else:
        warn_html = '<span class="tp-empty tp-warnings-empty">no warnings</span>'

    top_panel_html = f'''
<section class="top-panel" aria-label="Plan Overview">
  <div class="tp-grid">
    <div class="tp-cell tp-target">
      <div class="tp-label">Target <span class="tp-host-badge">{tp_host}</span></div>
      <div class="tp-value"><strong>{tp_target}</strong>
        {f' <span class="tp-status tp-status-{_esc(tp_target_status)}">{tp_target_status}</span>' if tp_target_status else ''}
      </div>
    </div>
    <div class="tp-cell tp-bottleneck">
      <div class="tp-label">Bottleneck</div>
      <div class="tp-value">{bn_html}</div>
    </div>
    <div class="tp-cell tp-next">
      <div class="tp-label">Next Action</div>
      <div class="tp-value">{na_html}</div>
    </div>
    <div class="tp-cell tp-cp">
      <div class="tp-label">Critical Path</div>
      <div class="tp-value">{cp_html}</div>
    </div>
    <div class="tp-cell tp-warn">
      <div class="tp-label">Warnings</div>
      <div class="tp-value">{warn_html}</div>
    </div>
  </div>
</section>
'''

    generated_at = _esc(freshness_meta.get("generated_at", gen_time))
    git_sha = _esc(freshness_meta.get("git_sha", "unknown"))
    loaded = int(freshness_meta.get("loaded_count", len(projects or [])) or 0)
    requested = int(freshness_meta.get("requested_count", len(projects or [])) or 0)
    skipped = freshness_meta.get("skipped") or []
    partial_cls = " freshness-badge--partial" if skipped else ""
    freshness_rows = "".join(
        f'<li><span class="mono">{_esc(item.get("repo", "?"))}</span>: {_esc(item.get("reason", "skipped"))}</li>'
        for item in skipped[:12]
    )
    if len(skipped) > 12:
        freshness_rows += f'<li class="text-muted">+{len(skipped) - 12} more</li>'
    freshness_detail = (
        f'<details class="freshness-detail"><summary>Partial data ({len(skipped)} skipped)</summary><ul>{freshness_rows}</ul></details>'
        if skipped else ""
    )
    freshness_html = (
        f'<section class="freshness-badge{partial_cls}" aria-label="Freshness">'
        f'<div class="freshness-main"><strong>Freshness:</strong> {generated_at} '
        f'&middot; commit <span class="mono">{git_sha}</span> '
        f'&middot; sources {loaded}/{requested}</div>'
        f'{freshness_detail}'
        f'</section>'
    )

    # ------------------------------------------------------------------
    # Repo-Chips markup
    # ------------------------------------------------------------------
    if projects and len(projects) > 1:
        chips_html = '<div class="repo-chips-row" role="group" aria-label="Repo Filter">'
        chips_html += '<span class="repo-chips-label">Repos:</span>'
        for slug in projects:
            is_host = slug == host_repo
            host_badge = ' <span class="repo-chip-host">host</span>' if is_host else ''
            chips_html += (
                f'<button type="button" class="repo-chip active" '
                f'data-repo="{_esc(slug)}" aria-pressed="true">'
                f'<span class="repo-chip-dot"></span>'
                f'{_esc(slug)}{host_badge}'
                f'</button>'
            )
        chips_html += '</div>'
    else:
        chips_html = ''

    gantt_html = _render_gantt(tasks, milestones, phase_order, phase_info)

    def _phase_color_class(phase: str) -> str:
        # Fix 5: phase may be `<slug>::<phase_key>` — strip prefix for CSS
        # color class (class names can't contain `::`). Two repos sharing a
        # phase key intentionally share the color; repo badge distinguishes.
        if phase and "::" in phase:
            phase = phase.split("::", 1)[1]
        return _esc(phase or "default")

    task_data = {}
    for t in tasks:
        task_data[t["id"]] = {
            "id": t["id"],
            "title": t.get("title", ""),
            "status": t.get("status", ""),
            "raw_status": t.get("_raw_status", ""),
            "effort": t.get("effort", "M"),
            "milestone": t.get("milestone", ""),
            "milestone_title": t.get("milestone_title", ""),
            "phase": t.get("phase", ""),
            "repo": t.get("repo", ""),
            "deps": t.get("deps", []),
            "external_deps": t.get("external_deps", []),
            "blocking_score": t.get("blocking_score", 0),
            "is_blocked": t.get("is_blocked", False),
            "spec_ref": t.get("spec_ref", ""),
            "board_result": t.get("board_result", ""),
            "readiness": t.get("readiness", ""),
            "summary": t.get("summary", ""),
            "note": t.get("note", ""),
            "area": t.get("area", ""),
            "assignee": t.get("assignee", ""),
            "created": t.get("created", ""),
            "updated": t.get("updated", ""),
            "closed": t.get("closed", ""),
            "parent_task": t.get("parent_task", ""),
            "sub_tasks": t.get("sub_tasks", []),
            "intent_chain": t.get("intent_chain", {}),
            "markdown_body": t.get("markdown_body", ""),
        }
    # Escape '</' to '<\/' so markdown bodies containing literal '</script>'
    # don't terminate the surrounding <script> block (HTML parser eats raw
    # ETAGO sequences before the JS parser ever sees them).
    def _safe_dump(obj) -> str:
        return json.dumps(obj, ensure_ascii=False).replace("</", "<\\/")

    task_data_json = _safe_dump(task_data)
    tasks_json = _safe_dump(tasks)
    projects_json = _safe_dump(projects)
    phase_info_json = _safe_dump(phase_info)
    phase_order_json = _safe_dump(phase_order)

    # Fix 3: milestone-dep map for arrow rendering. Shape:
    # {ms_key: [dep_ms_key, ...]} — all keys namespaced `<slug>#<mkey>` so
    # same-repo deps resolve uniquely across the merged milestones_list.
    milestone_deps = {
        m["key"]: list(m.get("deps") or [])
        for m in (milestones or [])
        if m.get("deps")
    }
    milestone_deps_json = _safe_dump(milestone_deps)

    # ------------------------------------------------------------------
    # Board rendering
    # ------------------------------------------------------------------
    def _render_board_group(m_key: str, items: list, default_collapsed: bool = False) -> str:
        m = ms_map.get(m_key) or {}
        phase = (m.get("phase") or (items[0].get("phase") if items else "")) or "default"
        title = m.get("title") or (m_key.split("#", 1)[-1] if m_key else "(no milestone)")
        raw_key = m.get("raw_key") or (m_key.split("#", 1)[-1] if m_key else "none")
        repo_slug = m.get("repo") or (items[0].get("repo") if items else "")
        count = len(items)
        status = m.get("status") or "future"
        cards_html: list = []
        for t in items:
            t_repo = t.get("repo", "")
            tag = ""
            if t.get("is_blocked"):
                tag = '<span class="blocked-tag">&#128274; blocked</span>'
            elif t.get("status") == "pending":
                tag = '<span class="ready-tag">&rarr; ready</span>'
            unresolved = []
            for dep in (t.get("deps") or []):
                dep_s = str(dep)
                dep_status = task_status_by_id.get(dep_s, "")
                if dep_status not in terminal:
                    unresolved.append(dep_s)
            blocked_hint = ""
            if unresolved:
                first = unresolved[0]
                blocked_hint = (
                    f'<span class="blocked-deps" title="Open blocker(s): {len(unresolved)}">'
                    f'<a href="#" onclick="event.stopPropagation(); openTaskModal(\'{_esc(first)}\'); return false;">'
                    f'blocked by {len(unresolved)}</a></span>'
                )
            bs = int(t.get("blocking_score", 0) or 0)
            bscore = f'<span class="blocking-badge mono small" title="Unblocks {bs} tasks">&#8599;{bs}</span>' if bs > 0 else ''
            blocked_cls = " task-blocked" if t.get("is_blocked") else ""
            cards_html.append(
                f'<div class="task-card{blocked_cls}" data-task-id="{_esc(t["id"])}" '
                f'data-repo="{_esc(t_repo)}" '
                f'onclick="openTaskModal(\'{_esc(t["id"])}\')" tabindex="0" role="button" '
                f'aria-label="Task {_esc(t["id"])}: {_esc(t.get("title", ""))}">'
                f'<div class="task-header">'
                f'<span class="task-id mono">[{_esc(t["id"])}]</span>'
                f'<span class="task-title">{_esc((t.get("title") or "")[:48])}</span>'
                f'</div>'
                f'<div class="task-meta">'
                f'<span class="effort-badge effort-{_esc(t.get("effort", "M"))}">{_esc(t.get("effort", "M"))}</span>'
                f'{tag}'
                f'{blocked_hint}'
                f'{bscore}'
                f'</div>'
                f'</div>'
            )
        # Fix 4: Done-column groups default-collapsed. `data-default-collapsed`
        # marks them as such so JS can decide whether a missing localStorage
        # override key means "collapsed" (Done) or "expanded" (Open/In-Progress).
        collapsed_attr = ' data-collapsed="true"' if default_collapsed else ''
        default_attr = ' data-default-collapsed="true"' if default_collapsed else ''
        chevron_char = "&#9656;" if default_collapsed else "&#9662;"  # ▸ / ▾
        aria = "false" if default_collapsed else "true"
        tasks_hidden = ' hidden' if default_collapsed else ''
        return (
            f'<div class="board-milestone-group" data-phase="{_phase_color_class(phase)}" '
            f'data-board-milestone="{_esc(m_key)}" data-repo="{_esc(repo_slug)}"'
            f'{collapsed_attr}{default_attr}>'
            f'<div class="milestone-group-header" tabindex="0" role="button" '
            f'onclick="toggleBoardGroup(\'{_esc(m_key)}\')" aria-expanded="{aria}">'
            f'<span class="group-chevron">{chevron_char}</span>'
            f'<span class="milestone-status-icon status-{_esc(status)}"></span>'
            f'<span class="milestone-name">{_esc(raw_key)}</span>'
            f'<span class="milestone-count mono small text-muted">({count})</span>'
            f'<span class="milestone-title-suffix text-muted">&mdash; {_esc(title)}</span>'
            f'</div>'
            f'<div class="milestone-group-tasks"{tasks_hidden}>'
            + "".join(cards_html) +
            '</div>'
            '</div>'
        )

    def _render_column(label: str, groups: list, col_cls: str, count: int,
                       default_collapsed: bool = False) -> str:
        empty = '<div class="board-col-empty">Keine Tasks</div>' if not groups else ''
        groups_html = "".join(
            _render_board_group(k, v, default_collapsed=default_collapsed)
            for k, v in groups
        )
        return (
            f'<div class="board-col {col_cls}">'
            f'<div class="board-col-header">'
            f'<span class="board-col-title">{label}</span>'
            f'<span class="board-col-count mono">({count})</span>'
            f'</div>'
            f'<div class="board-col-body">{groups_html}{empty}</div>'
            f'</div>'
        )

    board_html = (
        '<div class="board-columns">'
        + _render_column("Open", open_groups, "col-open", len(open_tasks))
        + _render_column("In Progress", active_groups, "col-progress", len(active_tasks))
        + _render_column("Done", done_groups, "col-done", len(done_tasks),
                         default_collapsed=False)
        + '</div>'
    )

    # ------------------------------------------------------------------
    # Repo-toggle CSS (one rule per project) — body-class selector pattern
    # ------------------------------------------------------------------
    # Note: `:not(.repo-chip)` excludes the toggle chip itself — otherwise
    # clicking the chip would hide it (descendant selector matches the button)
    # and the user could never re-toggle.
    repo_toggle_css = "\n".join(
        f"body.hide-repo-{slug} [data-repo=\"{slug}\"]:not(.repo-chip) {{ display: none !important; }}"
        for slug in projects
    )

    html = _build_html_shell(
        total=total, done_count=done_count, active_count=active_count,
        pending_count=pending_count,
        top_panel_html=top_panel_html, freshness_html=freshness_html, chips_html=chips_html,
        gantt_html=gantt_html, board_html=board_html,
        task_data_json=task_data_json, tasks_json=tasks_json,
        projects_json=projects_json, phase_info_json=phase_info_json,
        phase_order_json=phase_order_json,
        milestone_deps_json=milestone_deps_json,
        repo_toggle_css=repo_toggle_css,
        host_repo=host_repo, projects=projects, gen_time=gen_time,
        page_title=page_title,
    )
    return html


def _build_html_shell(
    *, total, done_count, active_count, pending_count,
    top_panel_html, freshness_html, chips_html, gantt_html, board_html,
    task_data_json, tasks_json, projects_json, phase_info_json,
    phase_order_json, milestone_deps_json,
    repo_toggle_css, host_repo, projects, gen_time, page_title="",
) -> str:
    """Assemble the <html>...</html> shell with CSS + JS.

    Separated from generate_html() so that the massive f-string doesn't
    collide with inner Python escaping. All fields are pre-stringified.
    """
    host_repo_json = json.dumps(host_repo)
    repos_label = _esc(', '.join(projects) if projects else host_repo)
    host_esc = _esc(host_repo)
    gen_time_esc = _esc(gen_time)
    # Default page-title from host-repo if not explicitly set.
    title_str = page_title or (f"{host_repo} Dev Dashboard" if host_repo else "Dev Dashboard")
    page_title_esc = _esc(title_str)
    return _HTML_TEMPLATE.format(
        total=total, done_count=done_count, active_count=active_count,
        pending_count=pending_count,
        top_panel_html=top_panel_html, freshness_html=freshness_html, chips_html=chips_html,
        gantt_html=gantt_html, board_html=board_html,
        task_data_json=task_data_json, tasks_json=tasks_json,
        projects_json=projects_json, phase_info_json=phase_info_json,
        phase_order_json=phase_order_json,
        milestone_deps_json=milestone_deps_json,
        repo_toggle_css=repo_toggle_css,
        host_repo=host_esc, repos_label=repos_label, gen_time=gen_time_esc,
        host_repo_json=host_repo_json, page_title=page_title_esc,
    )


# HTML template as a raw module-level constant. All `{` and `}` in CSS/JS
# are escaped as `{{` / `}}` so str.format() leaves them alone; only
# named-placeholders like {gantt_html} are substituted.
_HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="de">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{page_title}</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>
/* ================================================================
   Dev Dashboard v2 — Hub Spec v4.3 Design System (Zinc palette)
   ================================================================ */
:root {{
  --bg-primary:      #0a0a0a;
  --bg-surface:      #141414;
  --bg-elevated:     #1e1e1e;
  --bg-overlay:      rgba(0, 0, 0, 0.5);
  --text-primary:    #fafafa;
  --text-secondary:  #a3a3a3;
  --text-muted:      #737373;
  --accent:          #d4a520;
  --accent-gold:     #d4a520;
  --accent-green:    #4ade80;
  --accent-red:      #f87171;
  --accent-blue:     #93c5fd;
  --accent-cyan:     #67e8f9;
  --status-done:     var(--accent-green);
  --status-active:   var(--accent-blue);
  --status-ready:    var(--accent-cyan);
  --status-blocked:  var(--accent-red);
  --status-future:   var(--text-muted);
  --border:          #2a2a2a;
  --border-active:   #404040;
  --phase-foundation-text: #e2e8f0;
  --phase-mvp-text:        #93c5fd;
  --phase-platform-text:   #86efac;
  --phase-intelligence-text:#c4b5fd;
  --phase-life-text:       #5eead4;
  --phase-production-text: #fdba74;
  --font-body: 'Inter', system-ui, -apple-system, sans-serif;
  --font-mono: 'JetBrains Mono', 'Fira Code', 'Cascadia Code', monospace;
}}
*, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
html {{ font-size: 14px; }}
body {{
  font-family: var(--font-body);
  background: var(--bg-primary);
  color: var(--text-primary);
  line-height: 1.5;
  min-height: 100vh;
}}
a {{ color: var(--accent-cyan); text-decoration: none; }}
a:hover {{ text-decoration: underline; }}
.mono {{ font-family: var(--font-mono); }}
.small {{ font-size: 11px; }}
.text-muted {{ color: var(--text-muted); }}
:focus-visible {{ outline: 2px solid var(--accent-gold); outline-offset: 2px; }}

.sticky-header {{
  position: sticky; top: 0; z-index: 50;
  background: var(--bg-surface);
  border-bottom: 1px solid var(--border);
  padding: 8px 16px;
  display: flex; align-items: center; gap: 16px; flex-wrap: wrap;
  font-size: 13px; color: var(--text-secondary);
}}
.sticky-header .site-title {{ font-size: 16px; font-weight: 600; color: var(--text-primary); }}
.header-item {{ display: flex; align-items: center; gap: 4px; }}
.header-item .label {{ color: var(--text-muted); font-size: 12px; }}
.header-item .value {{ color: var(--text-secondary); font-family: var(--font-mono); }}
.header-timestamp {{ margin-left: auto; font-family: var(--font-mono); font-size: 11px; }}
.freshness-badge {{
  margin: 8px 16px 0;
  padding: 8px 12px;
  border-radius: 6px;
  border: 1px solid var(--border);
  background: var(--bg-elevated);
  color: var(--text-secondary);
  font-size: 12px;
}}
.freshness-badge--partial {{
  border-color: rgba(248, 113, 113, 0.6);
  background: rgba(248, 113, 113, 0.08);
}}
.freshness-main {{ display: flex; flex-wrap: wrap; gap: 6px; align-items: center; }}
.freshness-detail {{ margin-top: 6px; }}
.freshness-detail summary {{ cursor: pointer; color: var(--status-blocked); }}
.freshness-detail ul {{ margin-top: 4px; padding-left: 14px; }}
.freshness-detail li {{ line-height: 1.4; }}

.view-switch {{
  display: flex; gap: 0; padding: 0 16px;
  background: var(--bg-surface);
  border-bottom: 1px solid var(--border);
}}
.view-tab {{
  padding: 10px 20px; cursor: pointer; color: var(--text-muted);
  border: none; border-bottom: 2px solid transparent;
  background: none; font-size: 13px; font-weight: 500;
  font-family: inherit; margin-bottom: -1px;
}}
.view-tab:hover {{ color: var(--text-secondary); }}
.view-tab.active {{ color: var(--text-primary); border-bottom-color: var(--accent-gold); }}
.view-panel {{ display: none; padding: 16px; }}
.view-panel.active {{ display: block; }}

.top-panel {{
  background: var(--bg-elevated);
  border-bottom: 1px solid var(--border);
  padding: 10px 16px; font-size: 13px;
}}
.tp-grid {{
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 8px 16px; align-items: start;
}}
.tp-cell {{ display: flex; flex-direction: column; gap: 2px; min-width: 0; }}
.tp-label {{
  font-size: 11px; text-transform: uppercase; letter-spacing: 0.05em;
  color: var(--text-secondary); font-weight: 600;
}}
.tp-value {{ font-size: 13px; color: var(--text-primary); min-width: 0; }}
.tp-host-badge {{
  display: inline-block; margin-left: 6px; padding: 0 6px;
  background: var(--bg-primary); border: 1px solid var(--border);
  border-radius: 3px; font-family: var(--font-mono); font-size: 10px;
  color: var(--text-secondary);
}}
.tp-task-id {{ font-family: var(--font-mono); font-weight: 500; color: var(--accent-cyan); }}
.tp-task-title {{ color: var(--text-primary); }}
.tp-task-meta {{ color: var(--text-muted); font-size: 11px; font-family: var(--font-mono); }}
.tp-na-item {{ line-height: 1.4; margin-bottom: 2px; }}
.tp-status {{ display: inline-block; margin-left: 6px; padding: 1px 6px; border-radius: 3px; font-size: 10px; text-transform: uppercase; }}
.tp-status-done {{ background: rgba(74, 222, 128, 0.15); color: var(--status-done); }}
.tp-status-active {{ background: rgba(147, 197, 253, 0.15); color: var(--status-active); }}
.tp-status-ready {{ background: rgba(103, 232, 249, 0.15); color: var(--status-ready); }}
.tp-status-blocked,.tp-status-future {{ background: rgba(248, 113, 113, 0.15); color: var(--status-blocked); }}
.tp-cp-sep {{ color: var(--text-muted); }}
.tp-cp-more,.tp-cp-effort {{ color: var(--text-muted); font-size: 11px; margin-left: 6px; }}
.tp-empty {{ color: var(--text-muted); font-style: italic; }}
.tp-warnings summary {{ cursor: pointer; font-weight: 500; color: #fbbf24; list-style: none; display: inline-flex; align-items: center; gap: 6px; }}
.tp-warnings summary::-webkit-details-marker {{ display: none; }}
.tp-warn-badge {{ min-width: 18px; padding: 1px 6px; text-align: center; background: #fbbf24; color: #222; border-radius: 9px; font-size: 10px; font-weight: 600; }}
.tp-warnings ul {{ margin: 6px 0 0; padding-left: 12px; max-height: 160px; overflow-y: auto; }}
.tp-warnings li {{ font-size: 11px; line-height: 1.5; color: var(--text-secondary); margin-bottom: 2px; }}
.tp-warn-check {{ font-family: var(--font-mono); color: #fbbf24; font-weight: 500; }}
.tp-warn-loc {{ font-family: var(--font-mono); color: var(--text-muted); }}
.tp-warn-more {{ font-style: italic; color: var(--text-muted); }}
.tp-warnings-empty {{ font-size: 11px; color: var(--text-muted); }}

.repo-chips-row {{
  display: flex; flex-wrap: wrap; gap: 6px; align-items: center;
  padding: 6px 16px;
  background: var(--bg-primary); border-bottom: 1px solid var(--border);
}}
.repo-chips-label {{ font-size: 11px; text-transform: uppercase; color: var(--text-muted); font-weight: 600; margin-right: 6px; }}
.repo-chip {{
  display: inline-flex; align-items: center; gap: 6px;
  padding: 4px 10px; border: 1px solid var(--border); border-radius: 14px;
  background: var(--bg-elevated); color: var(--text-secondary);
  font-size: 11px; font-family: inherit; cursor: pointer;
}}
.repo-chip.active {{ background: var(--accent-gold); color: #000; border-color: var(--accent-gold); }}
.repo-chip:not(.active) {{ opacity: 0.55; }}
.repo-chip-dot {{ width: 8px; height: 8px; border-radius: 50%; background: currentColor; }}
.repo-chip-host {{ font-size: 9px; text-transform: uppercase; letter-spacing: 0.04em; opacity: 0.75; }}

.stats-bar {{
  display: flex; gap: 24px; padding: 8px 16px;
  font-size: 12px; color: var(--text-secondary);
  background: var(--bg-surface); border-bottom: 1px solid var(--border);
}}
.stats-bar .stat-num {{ font-family: var(--font-mono); font-weight: 600; font-size: 14px; margin-right: 4px; }}
.stat-total {{ color: var(--text-primary); }}
.stat-done {{ color: var(--status-done); }}
.stat-active {{ color: var(--status-active); }}
.stat-open {{ color: var(--text-muted); }}

/* ================================================================
   GANTT v2 — Compact Roadmap
   ================================================================ */
.gantt {{ padding: 16px; position: relative; }}
.gantt-arrows {{
  position: absolute; top: 0; left: 0; width: 100%;
  pointer-events: none; z-index: 5;
  /* Fix 3: currentColor is inherited by <path stroke="currentColor"> and the
     arrow-head marker fill — sets a sensible default; arrows pick it up. */
  color: var(--text-muted);
}}
.phase-repo-badge {{
  display: inline-block; font-size: 10px; padding: 1px 5px;
  border-radius: 3px; background: var(--bg-elevated);
  color: var(--text-secondary);
  border: 1px solid var(--border);
  font-family: 'JetBrains Mono', monospace;
  letter-spacing: 0.2px;
}}
.gantt-phase {{ margin-bottom: 6px; }}
.gantt-phase[data-collapsed="true"] .phase-milestones {{ display: none; }}
.gantt-phase[data-collapsed="true"] .phase-chevron {{ transform: rotate(-90deg); }}
.phase-header {{
  height: 28px; padding: 4px 12px;
  font-size: 13px; font-weight: 600;
  display: flex; align-items: center; gap: 6px;
  background: var(--bg-surface);
  border-left: 3px solid var(--accent-gold);
  border-radius: 3px; cursor: pointer; user-select: none;
  color: var(--text-primary);
}}
.phase-header:hover {{ background: var(--bg-elevated); }}
.phase-chevron {{ display: inline-block; font-size: 11px; color: var(--text-muted); transition: transform 120ms ease-out; }}
.phase-title {{ flex: 1; }}
.phase-count {{ font-size: 11px; color: var(--text-muted); font-weight: 400; }}
.gantt-phase[data-phase="foundation"] .phase-header    {{ border-left-color: var(--phase-foundation-text); }}
.gantt-phase[data-phase="mvp"] .phase-header           {{ border-left-color: var(--phase-mvp-text); }}
.gantt-phase[data-phase="platform"] .phase-header      {{ border-left-color: var(--phase-platform-text); }}
.gantt-phase[data-phase="intelligence"] .phase-header  {{ border-left-color: var(--phase-intelligence-text); }}
.gantt-phase[data-phase="life"] .phase-header          {{ border-left-color: var(--phase-life-text); }}
.gantt-phase[data-phase="production"] .phase-header    {{ border-left-color: var(--phase-production-text); }}
.phase-milestones {{ padding: 4px 0 8px 12px; overflow-x: auto; }}
/* Interval-based Gantt track: absolute-positioned milestone cells. Parent
   defines a natural width/height from Python so reflowArrows sees real
   geometry. `min-width: 100%` lets the track fill the phase container
   even when the natural width is smaller than the viewport. */
.gantt-track {{
  position: relative;
  margin: 6px 0 14px 12px;
  min-height: 44px;
  min-width: calc(100% - 12px);
}}
/* Phase hide/restore controls — small buttons on the right of the header. */
.phase-hide-btn {{
  margin-left: auto; cursor: pointer; opacity: 0.5;
  font-size: 12px; padding: 0 6px; line-height: 1;
  color: var(--text-muted);
}}
.phase-hide-btn:hover {{ opacity: 1; color: var(--text-primary); }}
.phase-restore-btn {{
  display: none; cursor: pointer; opacity: 0.7;
  font-size: 13px; padding: 0 6px; line-height: 1;
  margin-left: auto;
  color: var(--text-muted);
}}
.phase-restore-btn:hover {{ opacity: 1; color: var(--text-primary); }}
.gantt-phase[data-phase-hidden="true"] .phase-milestones {{ display: none; }}
.gantt-phase[data-phase-hidden="true"] .phase-header {{
  height: 20px; min-height: 20px; opacity: 0.55;
  padding-top: 2px; padding-bottom: 2px;
  font-size: 11px;
  cursor: default;
}}
.gantt-phase[data-phase-hidden="true"] .phase-chevron,
.gantt-phase[data-phase-hidden="true"] .phase-count {{ display: none; }}
.gantt-phase[data-phase-hidden="true"] .phase-restore-btn {{ display: inline; }}
.gantt-phase[data-phase-hidden="true"] .phase-hide-btn {{ display: none; }}
.gantt-milestone-wrap {{
  position: absolute;
  margin-bottom: 0;
}}
/* Header row sits above the bar row: icon + key + title + progress%. */
.milestone-header-row {{
  display: flex; align-items: flex-start; gap: 6px;
  min-height: 22px; padding: 2px 8px;
  font-size: 10px;
}}
.ms-icon {{
  font-size: 11px; width: 14px; text-align: center;
  opacity: 0.8; margin-right: 4px;
}}
.milestone-bar {{
  position: relative; height: 22px;
  display: flex; align-items: stretch; padding: 0;
  background: var(--bg-elevated);
  border: 1px solid var(--border); border-radius: 4px;
  font-size: 11px; cursor: pointer; user-select: none;
  overflow: hidden;
  transition: height 120ms ease-out, opacity 120ms ease-out;
}}
/* Variant B: Done-Milestones sind permanent Chips (40px wide, normale
   Bar-Hoehe 22px). Wrap-Container ist 100px (DONE_CHIP_WIDTH_PX) —
   Active-Milestones bekommen den Real-Estate zurueck der frueher von
   done-Wraps belegt war. Hintergrund ist green (status-done) damit
   done-Chips visuell als "fertig" lesbar sind. Header rechts vom Chip
   zeigt: status-icon + key + 100% (title weggelassen). */
.milestone-bar[data-ms-done="true"] {{
  width: 40px;
  background: var(--status-done);
  opacity: 0.85;
}}
.milestone-bar[data-ms-done="true"][data-display-state="expanded"] {{
  opacity: 1.0;
  border-color: var(--border-active);
}}
.milestone-bar[data-ms-done="true"] .bar-segments {{ display: none; }}
.gantt-milestone-wrap:has(.milestone-bar[data-ms-done="true"]) .bar-title {{
  display: none;
}}
.milestone-bar[data-display-state="expanded"]:not([data-ms-done="true"]) {{
  border-color: var(--border-active);
}}
/* Task rows only visible in 'expanded' state. */
.gantt-milestone-wrap .milestone-tasks-expanded {{ display: none; }}
.gantt-milestone-wrap:has(.milestone-bar[data-display-state="expanded"]) .milestone-tasks-expanded {{
  display: block;
}}
/* Expand-Drop-down-Popup: position-absolute unter dem Chip, ueberlagert
   alles darunter. Loest den User-Bug "expanded done-tasks ueberlagern
   Phasen drunter" + verhindert horizontalen Layout-Shift. Click auf
   Chip schliesst Popup wieder. */
.gantt-milestone-wrap:has(.milestone-bar[data-display-state="expanded"]) {{
  z-index: 100;
}}
.gantt-milestone-wrap:has(.milestone-bar[data-display-state="expanded"]) .milestone-tasks-expanded {{
  position: absolute;
  top: 100%;
  left: 0;
  width: 360px;
  max-height: 400px;
  overflow-y: auto;
  z-index: 101;
  background: var(--bg-elevated);
  border: 1px solid var(--border-active);
  border-radius: 4px;
  padding: 6px;
  box-shadow: 0 6px 16px rgba(0,0,0,0.55);
}}
.milestone-bar:hover {{ border-color: var(--border-active); }}
.milestone-bar[data-status="active"]  {{ border-left: 2px solid var(--status-active); }}
.milestone-bar[data-status="done"]    {{ border-left: 2px solid var(--status-done); opacity: 0.85; }}
.milestone-bar[data-status="blocked"] {{ border-left: 2px solid var(--status-blocked); }}
.milestone-bar[data-status="ready"]   {{ border-left: 2px solid var(--status-ready); }}
.bar-segments {{
  position: relative; flex: 1 1 auto; height: 100%; z-index: 1;
  display: flex; border-radius: 3px; overflow: hidden;
  pointer-events: none;
}}
.bar-segment {{
  height: 100%; opacity: 0.4;
  min-width: 4px; flex-shrink: 0;
  pointer-events: auto; cursor: pointer;
  transition: opacity 120ms;
}}
.bar-segment + .bar-segment {{ border-left: 1px solid rgba(0,0,0,0.4); }}
.bar-segment:hover {{ opacity: 0.75; }}
.bar-segment--done        {{ background: var(--status-done); }}
.bar-segment--in_progress {{ background: var(--status-active); }}
.bar-segment--pending     {{ background: var(--text-muted); opacity: 0.55; }}
.bar-segment--blocked     {{ background: var(--status-blocked); opacity: 0.6; }}
/* Min-width fuer non-done Segmente damit Task-IDs lesbar bleiben. Done bleibt
   bei 4px (Default in .bar-segment) — done-Tasks sind Audit-Trail, nicht
   Aufmerksamkeit. */
.bar-segment--in_progress,
.bar-segment--pending,
.bar-segment--blocked {{ min-width: 24px; }}
/* Done-stack aggregated segment (mixed done+open milestones). */
.bar-segment--done-stack {{
  background: var(--status-done); opacity: 0.85;
  display: flex; align-items: center; justify-content: center;
  cursor: pointer;
  /* Fixed narrow width — collapsed done-tasks take ~42px, non-done segments
     flex-shrink to fill the remaining bar. That's the space-saving effect. */
  flex: 0 0 42px; min-width: 42px;
}}
/* Non-done segments in a bar that contains a done-stack: allow shrink so
   the fixed 42px stack doesn't cause horizontal overflow. */
.milestone-bar[data-done-expanded="false"] .bar-segment:not(.bar-segment--done-stack):not(.done-individual) {{
  flex-shrink: 1;
}}
.bar-segment--done-stack:hover {{ opacity: 1.0; }}
.milestone-bar[data-done-expanded="false"] .done-individual {{ display: none; }}
.milestone-bar[data-done-expanded="true"]  .done-individual {{ display: flex; }}
/* Stack segment stays visible in both states so it can act as the toggle
   button (click to collapse). When expanded, both stack + individuals
   are visible — stack label doubles as "click to re-collapse" affordance. */
.seg-id {{
  display: block; font-size: 9px; font-weight: 600;
  color: #fff;
  text-shadow: 0 1px 2px rgba(0, 0, 0, 0.85);
  pointer-events: none; text-align: center;
  overflow: hidden; white-space: nowrap; padding: 0 2px;
  line-height: 20px;
}}
.bar-key {{ position: relative; z-index: 2; font-size: 11px; color: var(--text-primary); font-weight: 500; white-space: nowrap; flex-shrink: 0; }}
.bar-title {{
  position: relative; z-index: 2; font-size: 10px; color: var(--text-secondary);
  white-space: normal; line-height: 1.2; flex: 1 1 auto;
  min-width: 0; overflow: hidden;
  display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical;
}}
.bar-progress-label {{
  position: relative; z-index: 2; margin-left: auto;
  font-size: 10px; color: var(--text-secondary);
}}
.milestone-tasks-expanded {{
  position: absolute; left: 0; right: 0; top: 100%;
  margin-top: 2px; padding: 2px 0 6px 12px;
  background: var(--bg-surface);
  border: 1px solid var(--border); border-radius: 3px;
  z-index: 4; min-width: 100%;
}}
/* `hidden` attr no longer toggled by JS; visibility is driven by
   data-display-state on the parent .milestone-bar via the `:has()` rule above.
   Keep this fallback so the attr still works in older browsers. */
.milestone-tasks-expanded[hidden] {{ display: none; }}
.gantt-task-row {{
  height: 20px; display: flex; align-items: center; gap: 6px;
  font-size: 11px; cursor: pointer;
  color: var(--text-secondary);
  padding-left: 16px;
  border-left: 1px dashed var(--border);
}}
.gantt-task-row:hover {{ color: var(--text-primary); background: var(--bg-elevated); }}
.gantt-task-row .task-status-icon {{ width: 12px; text-align: center; font-family: var(--font-mono); }}
.gantt-task-row .task-status-icon.status-done        {{ color: var(--status-done); }}
.gantt-task-row .task-status-icon.status-in_progress {{ color: var(--status-active); }}
.gantt-task-row .task-status-icon.status-pending     {{ color: var(--text-muted); }}
.gantt-task-row .task-id {{ color: var(--accent-cyan); }}
.gantt-task-row .task-title-short {{ flex: 1; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}
.effort-badge {{
  display: inline-block; padding: 0 5px; border-radius: 3px;
  font-family: var(--font-mono); font-size: 10px; font-weight: 600;
  background: var(--bg-primary); color: var(--text-secondary);
  border: 1px solid var(--border);
}}
.effort-S  {{ color: var(--text-muted); }}
.effort-M  {{ color: var(--accent-cyan); }}
.effort-L  {{ color: var(--accent-gold); }}
.effort-XL {{ color: var(--accent-red); }}

/* ================================================================
   BOARD v2 — 3-Column Kanban
   ================================================================ */
.board-header {{
  display: flex; align-items: center; gap: 12px;
  margin-bottom: 12px; flex-wrap: wrap;
}}
.board-search {{
  flex: 1; min-width: 200px; max-width: 400px;
  background: var(--bg-primary); color: var(--text-primary);
  border: 1px solid var(--border); border-radius: 4px;
  padding: 6px 10px; font-size: 13px; font-family: inherit;
}}
.board-search:focus {{ border-color: var(--border-active); outline: none; }}
.effort-filter {{
  display: flex; gap: 4px; align-items: center;
  font-size: 12px; color: var(--text-muted);
}}
.effort-filter label {{
  padding: 3px 8px; border: 1px solid var(--border);
  border-radius: 3px; cursor: pointer; user-select: none;
  font-family: var(--font-mono);
}}
.effort-filter input {{ display: none; }}
.effort-filter label:has(input:checked) {{
  background: var(--accent-gold); color: #000; border-color: var(--accent-gold);
}}
.board-columns {{
  display: grid;
  grid-template-columns: 1fr 1fr 1fr;
  gap: 16px; align-items: start;
}}
.board-col {{
  background: var(--bg-surface);
  border: 1px solid var(--border);
  border-radius: 8px; padding: 10px;
  min-height: 200px;
}}
.board-col-header {{
  display: flex; justify-content: space-between; align-items: center;
  padding: 4px 4px 8px;
  border-bottom: 1px solid var(--border);
  margin-bottom: 10px;
  font-size: 13px; font-weight: 600;
}}
.col-open .board-col-header     {{ color: var(--text-secondary); }}
.col-progress .board-col-header {{ color: var(--status-active); }}
.col-done .board-col-header     {{ color: var(--status-done); }}
.board-col-count {{ font-size: 11px; color: var(--text-muted); font-weight: 400; }}
.board-col-empty {{
  padding: 24px 12px; text-align: center;
  color: var(--text-muted); font-size: 12px; font-style: italic;
}}
.board-milestone-group {{
  background: var(--bg-elevated);
  border: 1px solid var(--border); border-radius: 8px;
  padding: 8px; margin-bottom: 10px;
  border-left: 3px solid var(--text-muted);
}}
.board-milestone-group[data-phase="foundation"]   {{ border-left-color: var(--phase-foundation-text); }}
.board-milestone-group[data-phase="mvp"]          {{ border-left-color: var(--phase-mvp-text); }}
.board-milestone-group[data-phase="platform"]     {{ border-left-color: var(--phase-platform-text); }}
.board-milestone-group[data-phase="intelligence"] {{ border-left-color: var(--phase-intelligence-text); }}
.board-milestone-group[data-phase="life"]         {{ border-left-color: var(--phase-life-text); }}
.board-milestone-group[data-phase="production"]   {{ border-left-color: var(--phase-production-text); }}
.milestone-group-header {{
  display: flex; align-items: center; gap: 6px;
  padding: 2px 2px 6px; cursor: pointer; user-select: none;
  font-size: 12px; font-weight: 500; color: var(--text-primary);
}}
.milestone-group-header:hover {{ color: var(--accent-cyan); }}
.group-chevron {{
  display: inline-block; font-size: 11px; color: var(--text-muted);
  width: 10px; transition: transform 120ms;
}}
.board-milestone-group[data-collapsed="true"] .group-chevron {{ transform: rotate(-90deg); }}
.board-milestone-group[data-collapsed="true"] .milestone-group-tasks {{ display: none; }}
.milestone-name {{ font-family: var(--font-mono); }}
.milestone-status-icon {{
  display: inline-block; width: 8px; height: 8px; border-radius: 50%;
  background: var(--text-muted);
}}
.milestone-status-icon.status-done    {{ background: var(--status-done); }}
.milestone-status-icon.status-active  {{ background: var(--status-active); }}
.milestone-status-icon.status-ready   {{ background: var(--status-ready); }}
.milestone-status-icon.status-blocked {{ background: var(--status-blocked); }}
.milestone-title-suffix {{
  font-size: 11px; font-weight: 400;
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}}
.milestone-group-tasks {{ display: flex; flex-direction: column; gap: 4px; }}
.task-card {{
  background: var(--bg-surface);
  border: 1px solid var(--border);
  border-radius: 4px; padding: 6px 8px;
  cursor: pointer; transition: background 120ms, border-color 120ms;
}}
.task-card:hover {{ background: var(--bg-elevated); border-color: var(--border-active); }}
.task-card.task-blocked {{ opacity: 0.7; border-left: 3px solid var(--accent-red); }}
.task-header {{
  display: flex; gap: 6px; align-items: baseline;
  margin-bottom: 4px; font-size: 12px;
}}
.task-id {{ color: var(--accent-cyan); font-weight: 500; }}
.task-title {{
  flex: 1; color: var(--text-primary);
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}}
.task-meta {{
  display: flex; gap: 6px; align-items: center; font-size: 11px;
  flex-wrap: wrap;
}}
.blocked-tag {{ color: var(--accent-red); font-size: 11px; }}
.ready-tag {{ color: var(--accent-cyan); font-size: 11px; }}
.blocked-deps {{
  font-size: 10px;
  border: 1px dashed rgba(248, 113, 113, 0.45);
  border-radius: 3px;
  padding: 1px 6px;
  color: var(--status-blocked);
}}
.blocked-deps a {{ color: inherit; text-decoration: none; }}
.blocked-deps a:hover {{ text-decoration: underline; }}
.blocking-badge {{ color: var(--accent-gold); font-family: var(--font-mono); font-size: 10px; font-weight: 600; }}

/* ================================================================
   TASK MODAL v2
   ================================================================ */
.task-modal-backdrop {{
  display: none; position: fixed; inset: 0;
  background: var(--bg-overlay); z-index: 300;
  align-items: flex-start; justify-content: center;
  padding: 60px 20px 20px; overflow-y: auto;
}}
.task-modal-backdrop.active {{ display: flex; }}
.task-modal {{
  background: var(--bg-surface);
  border: 1px solid var(--border);
  border-radius: 12px;
  max-width: 1280px; width: 100%;
  padding: 24px; position: relative;
  box-shadow: 0 16px 48px rgba(0,0,0,0.5);
}}
.task-modal-header {{
  display: flex; align-items: center; gap: 8px;
  margin-bottom: 16px; padding-bottom: 12px;
  border-bottom: 1px solid var(--border);
}}
.task-modal-title {{ flex: 1; font-size: 16px; font-weight: 600; color: var(--text-primary); }}
.task-modal-close {{
  background: none; border: none; cursor: pointer;
  color: var(--text-muted); font-size: 20px; line-height: 1; padding: 4px 8px;
}}
.task-modal-close:hover {{ color: var(--text-primary); }}
.task-modal-meta {{
  display: flex; flex-wrap: wrap; gap: 8px 16px;
  font-size: 12px; color: var(--text-secondary); margin-bottom: 12px;
}}
.task-modal-meta b {{ color: var(--text-primary); font-weight: 500; }}
.task-modal-section {{ margin-bottom: 14px; }}
.task-modal-section h3 {{
  font-size: 11px; color: var(--text-muted);
  text-transform: uppercase; letter-spacing: 0.05em;
  margin-bottom: 6px; font-weight: 600;
}}
.task-modal-section p, .task-modal-section li {{
  font-size: 13px; color: var(--text-secondary); line-height: 1.5;
}}
.task-modal-section ul {{ padding-left: 18px; }}

/* ---- Markdown body (rendered via marked.js into the task modal) ---- */
.task-modal-md {{
  margin-top: 8px;
  padding-top: 12px;
  border-top: 1px solid var(--border);
  max-height: 50vh;
  overflow-y: auto;
  font-size: 13px;
  color: var(--text-secondary);
  line-height: 1.55;
}}
.task-modal-md h1, .task-modal-md h2, .task-modal-md h3, .task-modal-md h4 {{
  color: var(--text-primary);
  margin: 14px 0 6px;
  font-weight: 600;
}}
.task-modal-md h1 {{ font-size: 16px; }}
.task-modal-md h2 {{ font-size: 15px; }}
.task-modal-md h3 {{ font-size: 14px; }}
.task-modal-md h4 {{ font-size: 13px; }}
.task-modal-md p {{ margin: 6px 0; }}
.task-modal-md ul, .task-modal-md ol {{ padding-left: 22px; margin: 6px 0; }}
.task-modal-md li {{ margin: 2px 0; }}
.task-modal-md a {{ color: var(--accent-cyan); }}
.task-modal-md code {{
  font-family: var(--font-mono);
  font-size: 12px;
  background: var(--bg-elevated);
  padding: 1px 5px;
  border-radius: 3px;
  color: var(--accent-cyan);
}}
.task-modal-md pre {{
  background: var(--bg-elevated);
  border: 1px solid var(--border);
  border-radius: 4px;
  padding: 8px 10px;
  overflow-x: auto;
  margin: 8px 0;
}}
.task-modal-md pre code {{
  background: transparent;
  padding: 0;
  color: var(--text-primary);
  font-size: 12px;
}}
.task-modal-md blockquote {{
  border-left: 3px solid var(--border-active);
  padding-left: 10px;
  color: var(--text-muted);
  margin: 6px 0;
}}
.task-modal-md table {{
  border-collapse: collapse;
  font-size: 12px;
  margin: 8px 0;
}}
.task-modal-md th, .task-modal-md td {{
  border: 1px solid var(--border);
  padding: 4px 8px;
  text-align: left;
}}
.task-modal-md hr {{
  border: 0;
  border-top: 1px solid var(--border);
  margin: 12px 0;
}}

/* ---- Repo toggle via body-class (Hub-Spec v4.3 C-003 stretch) ---- */
{repo_toggle_css}

@media (max-width: 1024px) {{
  .board-columns {{ grid-template-columns: 1fr; }}
}}
</style>
</head>
<body>

<header class="sticky-header">
  <span class="site-title">Dev Dashboard</span>
  <div class="header-item"><span class="label">Host:</span><span class="value">{host_repo}</span></div>
  <div class="header-item"><span class="label">Repos:</span><span class="value">{repos_label}</span></div>
  <span class="header-timestamp">{gen_time}</span>
</header>

{freshness_html}

{top_panel_html}

{chips_html}

<section class="stats-bar" aria-label="Totals">
  <div><span class="stat-num stat-total">{total}</span>Tasks</div>
  <div><span class="stat-num stat-done">{done_count}</span>Done</div>
  <div><span class="stat-num stat-active">{active_count}</span>In Progress</div>
  <div><span class="stat-num stat-open">{pending_count}</span>Open</div>
</section>

<nav class="view-switch" role="tablist">
  <button class="view-tab active" role="tab" data-view="roadmap" aria-selected="true">Roadmap</button>
  <button class="view-tab" role="tab" data-view="board" aria-selected="false">Board</button>
</nav>

<section class="view-panel active" id="view-roadmap" role="tabpanel">
  {gantt_html}
</section>

<section class="view-panel" id="view-board" role="tabpanel">
  <div class="board-header">
    <input type="text" class="board-search" id="board-search" placeholder="Task suchen..." aria-label="Task suchen">
    <div class="effort-filter" role="group" aria-label="Effort Filter">
      <span>Effort:</span>
      <label><input type="checkbox" value="S" checked><span>S</span></label>
      <label><input type="checkbox" value="M" checked><span>M</span></label>
      <label><input type="checkbox" value="L" checked><span>L</span></label>
      <label><input type="checkbox" value="XL" checked><span>XL</span></label>
    </div>
  </div>
  {board_html}
</section>

<div class="task-modal-backdrop" id="task-modal-backdrop" aria-hidden="true">
  <div class="task-modal" role="dialog" aria-modal="true" aria-labelledby="task-modal-title">
    <div class="task-modal-header">
      <span class="task-modal-title" id="task-modal-title">Task</span>
      <button class="task-modal-close" id="task-modal-close" aria-label="Schliessen">&times;</button>
    </div>
    <div class="task-modal-body" id="task-modal-body"></div>
  </div>
</div>

<script id="task-data" type="application/json">{task_data_json}</script>
<script src="marked.min.js"></script>

<script>
/* ================================================================
   Dev Dashboard v2 — JS
   ~340 LOC (stretched from 250 baseline per Hub-Spec v4.3 C-003):
   multi-repo toggle via body class + v2 Gantt expand/collapse +
   modal focus-trap + board-group collapse with localStorage +
   board search/effort filters + marked.js task-modal markdown body.
   ================================================================ */
const TASKS = {tasks_json};
const TASK_DATA = JSON.parse(document.getElementById('task-data').textContent);
const PROJECTS = {projects_json};
const PHASE_INFO = {phase_info_json};
const PHASE_ORDER = {phase_order_json};
/* Fix 3: milestone-dep map for Gantt arrow rendering.
   Shape: {{ "<slug>#<to_mkey>": ["<slug>#<from_mkey>", ...], ... }} */
const MILESTONE_DEPS = {milestone_deps_json};
const HOST_REPO = {host_repo_json};
const TASK_MAP = {{}};
TASKS.forEach(t => TASK_MAP[t.id] = t);
const ACTIVE_VIEW_KEY = 'dashboard.activeView.v1';
const BOARD_SEARCH_KEY = 'dashboard.boardSearch.v1';
const BOARD_EFFORT_KEY = 'dashboard.boardEffort.v1';

function $(id) {{ return document.getElementById(id); }}
function esc(s) {{
  if (s === null || s === undefined) return '';
  const d = document.createElement('div');
  d.textContent = String(s);
  return d.innerHTML;
}}
function cssEscape(s) {{
  return String(s).replace(/["\\\\]/g, '\\\\$&');
}}

/* ---- View Switch ---- */
function setActiveView(v, persist = true) {{
  document.querySelectorAll('.view-tab').forEach(t => {{
    const isActive = t.dataset.view === v;
    t.classList.toggle('active', isActive);
    t.setAttribute('aria-selected', isActive ? 'true' : 'false');
  }});
  document.querySelectorAll('.view-panel').forEach(p => p.classList.remove('active'));
  const panel = $('view-' + v);
  if (panel) panel.classList.add('active');
  if (persist) {{
    try {{ localStorage.setItem(ACTIVE_VIEW_KEY, v); }} catch (e) {{ /* noop */ }}
  }}
  if (v === 'roadmap') setTimeout(reflowArrows, 50);
}}
document.querySelectorAll('.view-tab').forEach(tab => {{
  tab.addEventListener('click', () => setActiveView(tab.dataset.view, true));
}});
(function restoreActiveView() {{
  try {{
    const stored = localStorage.getItem(ACTIVE_VIEW_KEY);
    if (stored === 'roadmap' || stored === 'board') setActiveView(stored, false);
  }} catch (e) {{ /* noop */ }}
}})();

/* ---- Gantt: phase collapse ---- */
/* Fix 5: bumped to v2 — old keys were plain phase names; new keys are
   namespaced `<slug>::<phase_key>`. Old LS state would mis-apply. */
const PHASE_COLLAPSE_KEY = 'dashboard-collapsed-phases.v2';
function loadCollapsedPhases() {{
  try {{ return new Set(JSON.parse(localStorage.getItem(PHASE_COLLAPSE_KEY) || '[]')); }}
  catch (e) {{ return new Set(); }}
}}
function saveCollapsedPhases(set) {{
  try {{ localStorage.setItem(PHASE_COLLAPSE_KEY, JSON.stringify(Array.from(set))); }}
  catch (e) {{ /* noop */ }}
}}
function togglePhase(phase) {{
  // Fix 5: phase id is namespaced `<slug>::<phase_key>` — stored in
  // data-phase-id (data-phase keeps the PLAIN key for CSS color).
  const el = document.querySelector('.gantt-phase[data-phase-id="' + cssEscape(phase) + '"]');
  if (!el) return;
  const collapsed = el.getAttribute('data-collapsed') === 'true';
  if (collapsed) el.removeAttribute('data-collapsed');
  else el.setAttribute('data-collapsed', 'true');
  const header = el.querySelector('.phase-header');
  if (header) header.setAttribute('aria-expanded', collapsed ? 'true' : 'false');
  const stored = loadCollapsedPhases();
  if (collapsed) stored.delete(phase); else stored.add(phase);
  saveCollapsedPhases(stored);
  reflowArrows();
}}
(function restorePhaseCollapse() {{
  const stored = loadCollapsedPhases();
  if (!stored.size) return;
  document.querySelectorAll('.gantt-phase').forEach(el => {{
    // Fix 5: collapse state is keyed by the namespaced phase id, not the
    // plain phase key — otherwise two repos sharing `build` would toggle
    // together.
    const id = el.getAttribute('data-phase-id') || el.dataset.phase;
    if (stored.has(id)) el.setAttribute('data-collapsed', 'true');
    else el.removeAttribute('data-collapsed');
  }});
}})();

/* ---- Gantt: phase hide/restore -----------------------------------------
   Separate from collapse. Hidden phases shrink to a 20px strip with only
   a restore button. Default-hidden phases (e.g. Foundation) start hidden
   on first visit; user's explicit restore is persisted so they stay open.
*/
const HIDDEN_PHASES_KEY = 'dashboard.hiddenPhases.v1';
function loadHiddenPhases() {{
  try {{ return new Set(JSON.parse(localStorage.getItem(HIDDEN_PHASES_KEY) || '[]')); }}
  catch (e) {{ return new Set(); }}
}}
function saveHiddenPhases(set) {{
  try {{ localStorage.setItem(HIDDEN_PHASES_KEY, JSON.stringify(Array.from(set))); }}
  catch (e) {{ /* noop */ }}
}}
function _applyHidden(el, hidden) {{
  if (hidden) el.setAttribute('data-phase-hidden', 'true');
  else el.removeAttribute('data-phase-hidden');
}}
function hidePhase(phase) {{
  const el = document.querySelector('.gantt-phase[data-phase-id="' + cssEscape(phase) + '"]');
  if (!el) return;
  _applyHidden(el, true);
  const stored = loadHiddenPhases();
  stored.add(phase);
  saveHiddenPhases(stored);
  reflowArrows();
}}
function restorePhase(phase) {{
  const el = document.querySelector('.gantt-phase[data-phase-id="' + cssEscape(phase) + '"]');
  if (!el) return;
  _applyHidden(el, false);
  const stored = loadHiddenPhases();
  stored.delete(phase);
  // Mark explicit-restore so the default-hidden rule doesn't re-hide on
  // next reload. We stash that in the same LS blob under a sibling key.
  try {{
    const restoredKey = 'dashboard.hiddenPhases.restored.v1';
    const restored = new Set(JSON.parse(localStorage.getItem(restoredKey) || '[]'));
    restored.add(phase);
    localStorage.setItem(restoredKey, JSON.stringify(Array.from(restored)));
  }} catch (e) {{ /* noop */ }}
  saveHiddenPhases(stored);
  reflowArrows();
}}
(function restoreHiddenPhases() {{
  const stored = loadHiddenPhases();
  let explicitlyRestored = new Set();
  try {{
    explicitlyRestored = new Set(JSON.parse(
      localStorage.getItem('dashboard.hiddenPhases.restored.v1') || '[]'
    ));
  }} catch (e) {{ /* noop */ }}
  document.querySelectorAll('.gantt-phase').forEach(el => {{
    const id = el.getAttribute('data-phase-id') || el.dataset.phase;
    const defaultHidden = el.getAttribute('data-default-hidden') === 'true';
    const userHidden = stored.has(id);
    const shouldHide = userHidden || (defaultHidden && !explicitlyRestored.has(id));
    _applyHidden(el, shouldHide);
    if (shouldHide && !userHidden) {{
      // Persist the default-hidden state so it's consistent.
      stored.add(id);
    }}
  }});
  saveHiddenPhases(stored);
}})();

/* ---- Gantt: milestone tri-state display (collapsed / bar / expanded) ----
   Done milestones default to 'collapsed' (compact strip). One click promotes
   to 'bar' (segments visible). Another click promotes to 'expanded' (task
   rows visible). Unified 3-cycle for all milestones. No persistence: every
   reload starts at default state for each milestone (done=collapsed,
   non-done=bar). */
function _defaultMsState(bar) {{
  return bar.getAttribute('data-ms-done') === 'true' ? 'collapsed' : 'bar';
}}
function _applyMsState(bar, state) {{
  bar.setAttribute('data-display-state', state);
  bar.setAttribute('aria-expanded', state === 'expanded' ? 'true' : 'false');
}}
function toggleMilestoneDisplay(key) {{
  const bar = document.querySelector('.milestone-bar[data-milestone="' + cssEscape(key) + '"]');
  if (!bar) return;
  const isDone = bar.getAttribute('data-ms-done') === 'true';
  const cur = bar.getAttribute('data-display-state') || _defaultMsState(bar);
  // 2-state cycle per milestone type:
  //   Done:   collapsed (strip) <-> expanded (task rows)
  //   Active: bar (segments)   <-> expanded (task rows)
  // No intermediate state — done milestones never need to show segments,
  // active milestones never need a "hidden strip" (they ARE the focus).
  let next;
  if (isDone) {{
    next = (cur === 'expanded') ? 'collapsed' : 'expanded';
  }} else {{
    next = (cur === 'expanded') ? 'bar' : 'expanded';
  }}
  _applyMsState(bar, next);
  reflowArrows();
}}
/* Backwards-compat shim: callers (or any cached HTML) referencing the old
   API land on the new tri-state. */
function toggleMilestoneTasks(key) {{ toggleMilestoneDisplay(key); }}
(function initMsDisplay() {{
  document.querySelectorAll('.milestone-bar').forEach(bar => {{
    _applyMsState(bar, _defaultMsState(bar));
  }});
}})();

/* ---- Done-stack: collapse done-tasks into a single aggregated segment.
   Default collapsed; click expands to individual done segments. No
   persistence — every reload starts collapsed. ---- */
function toggleDoneStack(msKey, el) {{
  const bar = (el && el.closest) ? el.closest('.milestone-bar')
    : document.querySelector('.milestone-bar[data-milestone="' + cssEscape(msKey) + '"]');
  if (!bar) return;
  const cur = bar.getAttribute('data-done-expanded') === 'true';
  bar.setAttribute('data-done-expanded', cur ? 'false' : 'true');
  reflowArrows();
}}
(function initDoneStack() {{
  document.querySelectorAll('.milestone-bar').forEach(bar => {{
    bar.setAttribute('data-done-expanded', 'false');
  }});
}})();

/* ---- SVG dep-arrow renderer (Fix 3) ---------------------------------
   Draws cubic-Bezier arrows from source milestone-bars (right edge) to
   target milestone-bars (left edge). Skips arrows where either endpoint
   is display:none (hidden via repo-toggle or collapsed phase). */
const SVG_NS = 'http://www.w3.org/2000/svg';
function _ensureArrowMarker(svg) {{
  let defs = svg.querySelector('defs');
  if (!defs) {{
    defs = document.createElementNS(SVG_NS, 'defs');
    svg.appendChild(defs);
  }}
  if (defs.querySelector('#arrow-head')) return;
  const marker = document.createElementNS(SVG_NS, 'marker');
  marker.setAttribute('id', 'arrow-head');
  marker.setAttribute('viewBox', '0 0 10 10');
  marker.setAttribute('refX', '9');
  marker.setAttribute('refY', '5');
  marker.setAttribute('markerWidth', '8');
  marker.setAttribute('markerHeight', '8');
  marker.setAttribute('orient', 'auto-start-reverse');
  const path = document.createElementNS(SVG_NS, 'path');
  path.setAttribute('d', 'M 0 0 L 10 5 L 0 10 z');
  path.setAttribute('fill', 'currentColor');
  marker.appendChild(path);
  defs.appendChild(marker);
}}
function _barRect(key, rootRect) {{
  const bar = document.querySelector(
    '.milestone-bar[data-milestone="' + cssEscape(key) + '"]'
  );
  if (!bar) return null;
  const cs = window.getComputedStyle(bar);
  if (cs.display === 'none' || cs.visibility === 'hidden') return null;
  // Also skip if any ancestor is collapsed (display:none on phase-milestones)
  let el = bar.parentElement;
  while (el) {{
    const s = window.getComputedStyle(el);
    if (s.display === 'none') return null;
    if (el.id === 'gantt-root') break;
    el = el.parentElement;
  }}
  const r = bar.getBoundingClientRect();
  return {{
    left:   r.left   - rootRect.left,
    right:  r.right  - rootRect.left,
    top:    r.top    - rootRect.top,
    bottom: r.bottom - rootRect.top,
    midY:   (r.top + r.bottom) / 2 - rootRect.top,
  }};
}}
function reflowArrows() {{
  const svg = $('gantt-arrows');
  const root = $('gantt-root');
  if (!svg || !root) return;
  svg.setAttribute('width', root.scrollWidth);
  svg.setAttribute('height', root.scrollHeight);
  // Clear old children except <defs>
  Array.from(svg.childNodes).forEach(n => {{
    if (n.nodeType !== 1 || n.tagName.toLowerCase() !== 'defs') svg.removeChild(n);
  }});
  _ensureArrowMarker(svg);
  if (!MILESTONE_DEPS || typeof MILESTONE_DEPS !== 'object') return;
  const rootRect = root.getBoundingClientRect();
  Object.keys(MILESTONE_DEPS).forEach(toKey => {{
    const to = _barRect(toKey, rootRect);
    if (!to) return;
    (MILESTONE_DEPS[toKey] || []).forEach(fromKey => {{
      const from = _barRect(fromKey, rootRect);
      if (!from) return;
      const x1 = from.right, y1 = from.midY;
      const x2 = to.left,    y2 = to.midY;
      const dx = Math.max(20, Math.abs(x2 - x1) * 0.4);
      const d = 'M ' + x1 + ' ' + y1
              + ' C ' + (x1 + dx) + ' ' + y1
              + ', ' + (x2 - dx) + ' ' + y2
              + ', ' + x2 + ' ' + y2;
      const p = document.createElementNS(SVG_NS, 'path');
      p.setAttribute('d', d);
      p.setAttribute('stroke', 'currentColor');
      p.setAttribute('stroke-width', '1.5');
      p.setAttribute('fill', 'none');
      p.setAttribute('opacity', '0.55');
      p.setAttribute('marker-end', 'url(#arrow-head)');
      svg.appendChild(p);
    }});
  }});
}}
window.addEventListener('resize', reflowArrows);
document.addEventListener('DOMContentLoaded', reflowArrows);
setTimeout(reflowArrows, 100);

/* ================================================================
   TASK MODAL
   ================================================================ */
let _modalPrevFocus = null;
function _taskLink(id) {{
  const dt = TASK_DATA[id];
  const label = dt ? ('[' + id + '] ' + esc(dt.title)) : esc(id);
  return '<a href="#" onclick="openTaskModal(\'' + esc(id) + '\');return false">' + label + '</a>';
}}
function openTaskModal(id) {{
  const t = TASK_DATA[id];
  const backdrop = $('task-modal-backdrop');
  const body = $('task-modal-body');
  const titleEl = $('task-modal-title');
  if (!t) {{
    body.innerHTML = '<p style="color:var(--accent-red)">Task ' + esc(id) + ' nicht gefunden.</p>';
    titleEl.textContent = id;
  }} else {{
    titleEl.innerHTML = '<span class="mono" style="color:var(--accent-cyan)">[' + esc(t.id) + ']</span> ' + esc(t.title);
    let html = '';

    // ---- Meta (compact pill row) ----
    html += '<div class="task-modal-meta">';
    if (t.status)      html += '<span><b>Status:</b> ' + esc(t.status) + '</span>';
    if (t.raw_status && t.raw_status !== t.status)
      html += '<span><b>Raw:</b> ' + esc(t.raw_status) + '</span>';
    if (t.effort)      html += '<span><b>Effort:</b> ' + esc(t.effort) + '</span>';
    if (t.area)        html += '<span><b>Area:</b> ' + esc(t.area) + '</span>';
    if (t.repo)        html += '<span><b>Repo:</b> ' + esc(t.repo) + '</span>';
    if (t.milestone) {{
      let m = esc(t.milestone);
      if (t.milestone_title) m += ' &mdash; ' + esc(t.milestone_title);
      html += '<span><b>Milestone:</b> ' + m + '</span>';
    }}
    if (t.phase)       html += '<span><b>Phase:</b> ' + esc(t.phase) + '</span>';
    if (t.readiness)   html += '<span><b>Readiness:</b> ' + esc(t.readiness) + '</span>';
    if (t.board_result) html += '<span><b>Board:</b> ' + esc(t.board_result) + '</span>';
    if (t.blocking_score) html += '<span><b>Blocking:</b> ' + esc(t.blocking_score) + '</span>';
    if (t.is_blocked)  html += '<span style="color:var(--accent-red)"><b>&#128274; blocked</b></span>';
    html += '</div>';

    // ---- Plan: assignee / created / updated / parent / subs ----
    const planRows = [];
    if (t.assignee) planRows.push(['Assignee', esc(t.assignee)]);
    if (t.created)  planRows.push(['Created',  esc(t.created)]);
    if (t.updated)  planRows.push(['Updated',  esc(t.updated)]);
    if (t.closed)   planRows.push(['Closed',   esc(t.closed)]);
    if (t.parent_task) planRows.push(['Parent', _taskLink(t.parent_task)]);
    if (t.sub_tasks && t.sub_tasks.length) {{
      planRows.push(['Sub-tasks', t.sub_tasks.map(_taskLink).join(', ')]);
    }}
    if (planRows.length) {{
      html += '<div class="task-modal-section"><h3>Plan</h3><ul>';
      planRows.forEach(([k, v]) => {{
        html += '<li><b>' + esc(k) + ':</b> ' + v + '</li>';
      }});
      html += '</ul></div>';
    }}

    // ---- Beziehungen: deps / external / spec ----
    if (t.deps && t.deps.length) {{
      html += '<div class="task-modal-section"><h3>Blocked by</h3><ul>';
      t.deps.forEach(d => {{
        const dt = TASK_DATA[d];
        const label = dt ? ('[' + d + '] ' + esc(dt.title) + ' &mdash; ' + esc(dt.status)) : esc(d);
        html += '<li><a href="#" onclick="openTaskModal(\'' + esc(d) + '\');return false">' + label + '</a></li>';
      }});
      html += '</ul></div>';
    }}
    if (t.external_deps && t.external_deps.length) {{
      html += '<div class="task-modal-section"><h3>External deps</h3><ul>';
      t.external_deps.forEach(d => {{ html += '<li>' + esc(d) + '</li>'; }});
      html += '</ul></div>';
    }}
    if (t.spec_ref) html += '<div class="task-modal-section"><h3>Spec</h3><p>' + esc(t.spec_ref) + '</p></div>';

    // ---- Intent ----
    const ic = t.intent_chain || {{}};
    const icRows = [];
    if (ic.domain)    icRows.push(['Domain',    esc(ic.domain)]);
    if (ic.objective) icRows.push(['Objective', esc(ic.objective)]);
    if (ic.action)    icRows.push(['Action',    esc(ic.action)]);
    if (icRows.length) {{
      html += '<div class="task-modal-section"><h3>Intent</h3><ul>';
      icRows.forEach(([k, v]) => {{
        html += '<li><b>' + esc(k) + ':</b> ' + v + '</li>';
      }});
      html += '</ul></div>';
    }}

    // ---- Inhalt: summary / note ----
    if (t.summary) html += '<div class="task-modal-section"><h3>Summary</h3><p>' + esc(t.summary) + '</p></div>';
    if (t.note)    html += '<div class="task-modal-section"><h3>Note</h3><p>' + esc(t.note) + '</p></div>';

    // ---- Markdown body (rendered via marked.js if available) ----
    if (t.markdown_body && t.markdown_body.length) {{
      let mdHtml;
      try {{
        if (typeof marked !== 'undefined' && typeof marked.parse === 'function') {{
          mdHtml = marked.parse(t.markdown_body);
        }} else {{
          mdHtml = '<pre>' + esc(t.markdown_body) + '</pre>';
        }}
      }} catch (e) {{
        mdHtml = '<pre>' + esc(t.markdown_body) + '</pre>';
      }}
      html += '<div class="task-modal-section"><h3>Details</h3>'
            + '<div class="task-modal-md">' + mdHtml + '</div></div>';
    }}

    body.innerHTML = html;
  }}
  _modalPrevFocus = document.activeElement;
  backdrop.classList.add('active');
  backdrop.setAttribute('aria-hidden', 'false');
  $('task-modal-close').focus();
}}
function closeTaskModal() {{
  const backdrop = $('task-modal-backdrop');
  backdrop.classList.remove('active');
  backdrop.setAttribute('aria-hidden', 'true');
  if (_modalPrevFocus && _modalPrevFocus.focus) _modalPrevFocus.focus();
}}
$('task-modal-close').addEventListener('click', closeTaskModal);
$('task-modal-backdrop').addEventListener('click', (e) => {{
  if (e.target === $('task-modal-backdrop')) closeTaskModal();
}});
document.addEventListener('keydown', (e) => {{
  if (e.key === 'Escape') {{
    if ($('task-modal-backdrop').classList.contains('active')) closeTaskModal();
  }}
}});
$('task-modal-backdrop').addEventListener('keydown', (e) => {{
  if (e.key !== 'Tab') return;
  const modal = document.querySelector('.task-modal');
  const foc = modal.querySelectorAll('button, a, [tabindex]:not([tabindex="-1"])');
  if (!foc.length) return;
  const first = foc[0], last = foc[foc.length - 1];
  if (e.shiftKey && document.activeElement === first) {{ e.preventDefault(); last.focus(); }}
  else if (!e.shiftKey && document.activeElement === last) {{ e.preventDefault(); first.focus(); }}
}});

/* ================================================================
   BOARD: group collapse (localStorage)
   ================================================================ */
/* Fix 4: Done-column groups are server-rendered default-collapsed. LS now
   holds OVERRIDES (keys whose state differs from data-default-collapsed)
   instead of a collapsed-keys set. Key bumped to v2 to discard stale state.
   Fix 5 (post default-switch): Done-default flipped to expanded; old v2
   override-sets would now invert (keys saved as "abweicht von default=collapsed"
   are read as "abweicht von default=expanded"). Bump to v3 to discard. */
const BOARD_COLLAPSE_KEY = 'dashboard-board-group-overrides.v3';
function loadBoardOverrides() {{
  try {{ return new Set(JSON.parse(localStorage.getItem(BOARD_COLLAPSE_KEY) || '[]')); }}
  catch (e) {{ return new Set(); }}
}}
function saveBoardOverrides(set) {{
  try {{ localStorage.setItem(BOARD_COLLAPSE_KEY, JSON.stringify(Array.from(set))); }}
  catch (e) {{ /* noop */ }}
}}
function _groupDefaultCollapsed(g) {{
  return g && g.getAttribute('data-default-collapsed') === 'true';
}}
function _applyGroupState(g, collapsed) {{
  if (collapsed) g.setAttribute('data-collapsed', 'true');
  else g.removeAttribute('data-collapsed');
  const header = g.querySelector('.milestone-group-header');
  if (header) header.setAttribute('aria-expanded', collapsed ? 'false' : 'true');
  const chev = g.querySelector('.group-chevron');
  if (chev) chev.innerHTML = collapsed ? '&#9656;' : '&#9662;';
  const body = g.querySelector('.milestone-group-tasks');
  if (body) {{
    if (collapsed) body.setAttribute('hidden', '');
    else body.removeAttribute('hidden');
  }}
}}
function toggleBoardGroup(key) {{
  const g = document.querySelector('[data-board-milestone="' + cssEscape(key) + '"]');
  if (!g) return;
  const wasCollapsed = g.getAttribute('data-collapsed') === 'true';
  const nextCollapsed = !wasCollapsed;
  _applyGroupState(g, nextCollapsed);
  // Override-set semantics: present iff current state != default
  const stored = loadBoardOverrides();
  const isDefault = _groupDefaultCollapsed(g);
  if (nextCollapsed === isDefault) stored.delete(key);
  else stored.add(key);
  saveBoardOverrides(stored);
}}
(function restoreBoardGroups() {{
  const stored = loadBoardOverrides();
  document.querySelectorAll('.board-milestone-group').forEach(g => {{
    const key = g.getAttribute('data-board-milestone');
    const isDefault = _groupDefaultCollapsed(g);
    const overridden = stored.has(key);
    // Final state = default XOR override
    const collapsed = overridden ? !isDefault : isDefault;
    _applyGroupState(g, collapsed);
  }});
}})();

/* ================================================================
   BOARD: search + effort filter (client-side)
   ================================================================ */
let boardSearch = '';
const boardEffort = new Set(['S', 'M', 'L', 'XL']);
function applyBoardFilters() {{
  document.querySelectorAll('.board-col .task-card').forEach(card => {{
    const id = card.dataset.taskId;
    const t = TASK_MAP[id] || {{}};
    const effortOk = boardEffort.has(t.effort || 'M');
    const hay = ((t.id || '') + ' ' + (t.title || '') + ' ' + (t.summary || '')).toLowerCase();
    const searchOk = !boardSearch || hay.indexOf(boardSearch) !== -1;
    card.style.display = (effortOk && searchOk) ? '' : 'none';
  }});
  document.querySelectorAll('.board-milestone-group').forEach(g => {{
    const visible = Array.from(g.querySelectorAll('.task-card')).some(c => c.style.display !== 'none');
    g.style.display = visible ? '' : 'none';
  }});
}}
$('board-search').addEventListener('input', (e) => {{
  boardSearch = e.target.value.trim().toLowerCase();
  try {{ localStorage.setItem(BOARD_SEARCH_KEY, e.target.value || ''); }} catch (err) {{ /* noop */ }}
  applyBoardFilters();
}});
document.querySelectorAll('.effort-filter input').forEach(chk => {{
  chk.addEventListener('change', () => {{
    if (chk.checked) boardEffort.add(chk.value);
    else boardEffort.delete(chk.value);
    try {{ localStorage.setItem(BOARD_EFFORT_KEY, JSON.stringify(Array.from(boardEffort))); }} catch (err) {{ /* noop */ }}
    applyBoardFilters();
  }});
}});
(function restoreBoardFilters() {{
  try {{
    const q = localStorage.getItem(BOARD_SEARCH_KEY) || '';
    $('board-search').value = q;
    boardSearch = q.trim().toLowerCase();
  }} catch (e) {{ /* noop */ }}
  try {{
    const storedEffort = JSON.parse(localStorage.getItem(BOARD_EFFORT_KEY) || 'null');
    if (Array.isArray(storedEffort) && storedEffort.length) {{
      boardEffort.clear();
      storedEffort.forEach(v => boardEffort.add(v));
      document.querySelectorAll('.effort-filter input').forEach(chk => {{
        chk.checked = boardEffort.has(chk.value);
      }});
    }}
  }} catch (e) {{ /* noop */ }}
}})();

/* ================================================================
   REPO TOGGLE (body-class — survives innerHTML rebuilds)
   Fix 2: key bumped from v1 to 'dashboard.repoToggles.v2'. Old v1 state
   (from the pre-fix buggy build where toggling a chip hid the chip
   itself) is effectively stranded — default on missing key is ALL-ACTIVE.
   ================================================================ */
const REPO_TOGGLE_KEY = 'dashboard.repoToggles.v2';
function applyRepoToggles(active) {{
  PROJECTS.forEach(slug => {{
    document.body.classList.toggle('hide-repo-' + slug, !active.has(slug));
  }});
  document.querySelectorAll('.repo-chip').forEach(btn => {{
    const r = btn.dataset.repo;
    const on = active.has(r);
    btn.classList.toggle('active', on);
    btn.setAttribute('aria-pressed', on ? 'true' : 'false');
  }});
  applyBoardFilters();
  reflowArrows();
}}
(function initRepoChips() {{
  const chips = Array.from(document.querySelectorAll('.repo-chip'));
  if (!chips.length) return;
  const allRepos = chips.map(c => c.dataset.repo);
  let active;
  try {{
    const stored = JSON.parse(localStorage.getItem(REPO_TOGGLE_KEY) || 'null');
    if (Array.isArray(stored)) active = new Set(stored.filter(r => allRepos.includes(r)));
  }} catch (e) {{ /* noop */ }}
  if (!active || !active.size) active = new Set(allRepos);
  applyRepoToggles(active);
  chips.forEach(btn => {{
    btn.addEventListener('click', () => {{
      const r = btn.dataset.repo;
      if (active.has(r)) active.delete(r);
      else active.add(r);
      if (active.size === 0) active.add(r);
      applyRepoToggles(active);
      try {{ localStorage.setItem(REPO_TOGGLE_KEY, JSON.stringify(Array.from(active))); }}
      catch (e) {{ /* ignore quota */ }}
    }});
  }});
}})();

applyBoardFilters();
</script>
</body>
</html>"""




# ---------------------------------------------------------------------------
# Main (Task-011 Phase 2b-Dashboard, D1-c)
# ---------------------------------------------------------------------------
#
# CLI:
#   --host-repo REPO_SLUG   Required when --projects has > 1 entry.
#                           The Top-Panel is sourced exclusively from this
#                           repo. Independent of UI repo-toggles.
#   --projects A,B,C        Comma-separated repo slugs. Single entry → single-
#                           repo mode (no repo-badges). Missing repos warn +
#                           skip (not fail). Empty/omitted → host-repo only,
#                           defaulting to this script's REPO_ROOT parent name
#                           if --host-repo is also omitted.
#   --output PATH           Output HTML path (or directory — index.html is
#                           appended automatically).

def _copy_vendored_mermaid(output_path: Path) -> None:
    """Copy scripts/vendor/mermaid.min.js next to the output HTML so the
    graph view renders when opened as a file:// URL."""
    vendor_mermaid = SCRIPTS_DIR / "vendor" / "mermaid.min.js"
    target_mermaid = output_path.parent / "mermaid.min.js"
    if vendor_mermaid.exists():
        shutil.copy2(vendor_mermaid, target_mermaid)
    else:
        warn(f"Vendored mermaid.min.js not found at {vendor_mermaid} — graph view will not render")


def _load_marked_inline_block() -> str:
    """Read scripts/vendor/marked.min.js and wrap it in a self-contained
    <script> block for inline embedding into the dashboard HTML.

    Inlining avoids the deploy-rsync gap: scripts/deploy-dashboard-lite.sh
    rsyncs only the single index.html — sibling vendor files would 404 on
    the Hetzner host. ETAGO-escape ('</' -> '<\\/') keeps any literal
    '</script>' inside the lib from terminating the surrounding tag
    (same pattern as _safe_dump for JSON blobs)."""
    vendor_marked = SCRIPTS_DIR / "vendor" / "marked.min.js"
    if not vendor_marked.exists():
        print(
            f"ERROR: vendored marked.min.js not found at {vendor_marked} — "
            f"task-modal markdown rendering would silently break. "
            f"Restore the vendor file before regenerating.",
            file=sys.stderr,
        )
        sys.exit(2)
    lib_code = vendor_marked.read_text(encoding="utf-8").replace("</", "<\\/")
    return f"<script>\n{lib_code}\n</script>"


def _current_git_sha(repo_root: Path) -> str:
    """Best-effort short SHA for freshness badge."""
    try:
        out = subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=repo_root,
            stderr=subprocess.DEVNULL,
            text=True,
        ).strip()
        return out or "unknown"
    except Exception:
        return "unknown"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate the Dev-Flow Dashboard (plan.yaml SoT, multi-repo)."
    )
    parser.add_argument(
        "--output", "-o", "--out", type=Path, default=DEFAULT_OUTPUT,
        help="Output HTML file path (or directory — index.html is appended).",
    )
    parser.add_argument(
        "--host-repo", dest="host_repo", type=str, default=None,
        help="Repo slug that drives the Top-Panel. Required when --projects has "
             "more than one entry.",
    )
    parser.add_argument(
        "--projects", type=str, default=None,
        help="Comma-separated list of repo slugs. Each slug resolves to "
             "DEFAULT_REPO_PATHS[slug] then $PROJECTS_DIR/<slug> "
             "(default: ~/projects/<slug>). Missing repos are skipped with a "
             "warning. Empty / omitted → single-repo mode using --host-repo.",
    )
    parser.add_argument(
        "--title", type=str, default=None,
        help="HTML title for the dashboard. Default: '<host-repo> Dev Dashboard'.",
    )
    args = parser.parse_args()

    # Normalize --output: directory-style → <dir>/index.html
    raw_out = str(args.output)
    if raw_out.endswith(("/", os.sep)) or args.output.is_dir() or args.output.suffix == "":
        out_path = args.output / "index.html"
    else:
        out_path = args.output

    # Resolve --projects list
    projects: list[str] = []
    if args.projects:
        projects = [p.strip() for p in args.projects.split(",") if p.strip()]

    # Iteration 2 (CA-003 Fix): Auto-Detect-Override-Map. Wenn der Single-Repo-
    # Auto-Detect-Pfad cwd als project_root benutzt, MUSS der eigentliche cwd-
    # Pfad genommen werden — NICHT slug-resolve gegen ~/projects/<basename>.
    # Sonst lädt ein Worktree/Sandbox/anderer-Mount-Point das homonyme
    # ~/projects/<name>-Repo statt der cwd-Daten (stille Datenkorruption).
    auto_detect_override: dict[str, Path] = {}

    # Validate --host-repo / --projects relationship
    if len(projects) > 1 and not args.host_repo:
        print("ERROR: --host-repo is required when --projects has more than one entry",
              file=sys.stderr)
        return 2
    if not projects:
        # Single-repo mode, fall back to host-repo if given, else derive
        # from cwd / BUDDY_PROJECT_ROOT (Task 435 AC-A.3 cross-repo-test-Pfad).
        if args.host_repo:
            projects = [args.host_repo]
        else:
            # Auto-detect: BUDDY_PROJECT_ROOT or cwd as single-repo project.
            cwd_root = Path(os.environ.get("BUDDY_PROJECT_ROOT", os.getcwd())).resolve()
            if (cwd_root / "docs" / "plan.yaml").exists():
                projects = [cwd_root.name]
                # CA-003 Iteration 2: cwd_root selbst als override speichern,
                # damit der Loader cwd_root benutzt statt slug -> ~/projects/<name>.
                auto_detect_override[cwd_root.name] = cwd_root
            else:
                print("ERROR: must pass --projects (or --host-repo for single-repo mode)",
                      file=sys.stderr)
                return 2
    host_repo = args.host_repo or projects[0]
    if host_repo not in projects:
        print(f"ERROR: --host-repo '{host_repo}' not in --projects {projects}",
              file=sys.stderr)
        return 2

    print("Dev-Flow Dashboard Generator (plan.yaml SoT)")
    print(f"  Host repo: {host_repo}")
    print(f"  Projects:  {', '.join(projects)}")
    print(f"  Output:    {out_path}")
    print()

    # Load per-repo plan_engine data. Missing repos warn + skip gracefully.
    per_repo: dict[str, dict] = {}
    repo_health: list[dict[str, str]] = []
    resolved_slugs: list[str] = []
    for slug in projects:
        # CA-003 Iteration 2: Override-Map wins gegen slug-resolve.
        root: Path | None
        if slug in auto_detect_override:
            root = auto_detect_override[slug]
        else:
            root = resolve_repo_path(slug)
        if root is None:
            msg = f"[{slug}] repo path not found — skip"
            warn(msg)
            repo_health.append({"repo": slug, "status": "skipped", "reason": "path not found"})
            continue
        errors: list[str] = []
        data = load_repo_data(slug, root, error_sink=errors)
        if data is None:
            reason = errors[-1] if errors else "load failed"
            repo_health.append({"repo": slug, "status": "skipped", "reason": reason})
            continue
        per_repo[slug] = data
        resolved_slugs.append(slug)
        repo_health.append({"repo": slug, "status": "loaded", "reason": str(root)})
        print(f"  [{slug}] {len(data['tasks'])} tasks, {len(data['milestones'])} milestones from {root}")

    if not per_repo:
        print("ERROR: no repos loaded — cannot generate dashboard", file=sys.stderr)
        return 1

    # Build dashboard-task-dicts and phase data from the plan_engine output.
    tasks_list = build_task_dicts(per_repo)
    phase_order, phase_info, impl_phases = build_phase_data(per_repo)
    milestones_list = build_milestone_data(per_repo)

    # Top-Panel from host-repo ONLY (unaffected by UI toggles).
    host_data = per_repo.get(host_repo)
    if host_data is None:
        warn(f"host repo '{host_repo}' not loaded — Top-Panel will be empty")
    top_panel = build_top_panel(host_data, host_repo)

    # Global dashboard integrity checks (task ids + dependency refs).
    validation_warnings = validate_task_dependency_integrity(tasks_list)
    if validation_warnings:
        top_panel.setdefault("warnings", []).extend(validation_warnings)

    # North-star from host-repo.
    north_star = host_data["plan"].north_star if host_data else ""

    # Empty containers for retired data sources (kept for HTML/JS compat).
    empty_slices: dict = {}
    empty_hook = {"status": "-", "task": "-", "step": "-", "context_note": "", "task_id": ""}
    empty_prebuild = {"current_block": "-", "total_blocks": "-", "blocks": []}
    empty_feature_registry: dict[str, list[dict[str, Any]]] = {
        "flags": [],
        "infra_toggles": [],
        "activation_matrix": [],
    }
    empty_amendments: list = []
    empty_spec_health: list = []
    empty_readiness: list = []

    mermaid_code = generate_mermaid(tasks_list, empty_slices)
    gen_time = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    html = generate_html(
        tasks=tasks_list,
        slices=empty_slices,
        north_star=north_star,
        hook=empty_hook,
        mermaid_code=mermaid_code,
        gen_time=gen_time,
        prebuild=empty_prebuild,
        feature_registry=empty_feature_registry,
        amendments=empty_amendments,
        spec_health=empty_spec_health,
        readiness_data=empty_readiness,
        phase_order=phase_order,
        phase_info=phase_info,
        impl_phases=impl_phases,
        top_panel=top_panel,
        projects=resolved_slugs,
        host_repo=host_repo,
        milestones=milestones_list,
        freshness_meta={
            "generated_at": gen_time,
            "git_sha": _current_git_sha(REPO_ROOT),
            "requested_count": len(projects),
            "loaded_count": len(resolved_slugs),
            "skipped": [x for x in repo_health if x.get("status") != "loaded"],
        },
        page_title=args.title or "",
    )

    # Inline-embed marked.js so the deploy-rsync (single-HTML) survives:
    # the template ships '<script src="marked.min.js"></script>' as a
    # literal placeholder; we swap it for a <script>…lib…</script> block
    # post-format (placing the lib body in .format() args is unsafe — the
    # JS contains '{'/'}' that would collide with str.format placeholders).
    marked_inline = _load_marked_inline_block()
    html = html.replace(
        '<script src="marked.min.js"></script>',
        marked_inline,
        1,
    )

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html, encoding="utf-8")

    _copy_vendored_mermaid(out_path)

    size_kb = len(html.encode("utf-8")) / 1024
    print()
    print(f"  Dashboard generated: {out_path}")
    print(f"  Size: {size_kb:.1f} KB")
    print(f"  Tasks: {len(tasks_list)} across {len(resolved_slugs)} repo(s)")
    for slug in resolved_slugs:
        n = sum(1 for t in tasks_list if t.get("repo") == slug)
        print(f"    {slug}: {n}")
    return 0


if __name__ == "__main__":
    sys.exit(main() or 0)
