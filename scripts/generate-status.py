#!/usr/bin/env python3
"""
Component Status Generator for BuddyAI Architecture Documentation.

Data-driven: uses spec_ref from task YAMLs as the ONLY source for
spec↔task linking. No hardcoded maps.

Categorizes specs: implementation | reference | superseded.

Sources:
    - docs/specs/*.md (Layer, Status, Category from header)
    - docs/tasks/*.yaml (spec_ref, status, blocked_by)
    - docs/backlog.md (task metadata fallback)

Output:
    - docs/architecture/generated/component-status.md
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SPECS_DIR = ROOT / "docs" / "specs"
TASKS_DIR = ROOT / "docs" / "tasks"
BACKLOG_PATH = ROOT / "docs" / "backlog.md"
OUTPUT_PATH = ROOT / "docs" / "architecture" / "generated" / "component-status.md"

# Specs that are reference/theoretical docs — no implementation task expected
REFERENCE_SPECS = {
    "knowledge-architecture",   # High-level architecture, no direct code
    "cognitive-architecture",   # Theoretical model
    "graph-ontology",           # Reference catalog, implemented via brain-foundation
    "harness-runtime-patterns", # Day-N patterns, cross-cutting reference
    "architecture-overview",    # Gesamtbild, no direct code
}

SUPERSEDED_SPECS = {
    "dev-flow",  # Superseded by framework/process-map.md + workflows/runbooks/
}

SKIP_FILES = {"SPEC-MAP.md", "README.md", "Spec header.md"}


@dataclass
class SpecInfo:
    name: str
    layer: str = ""
    status: str = ""
    category: str = "implementation"  # implementation | reference | superseded


@dataclass
class TaskInfo:
    id: str
    title: str = ""
    status: str = ""
    deps: list[str] = field(default_factory=list)
    spec_ref: str = ""


def parse_specs(specs_dir: Path) -> list[SpecInfo]:
    """Extract Layer and Status from spec headers."""
    specs = []
    for md_file in sorted(specs_dir.glob("*.md")):
        if md_file.name in SKIP_FILES or md_file.name.startswith("archive"):
            continue

        text = md_file.read_text(encoding="utf-8")
        name = md_file.stem
        layer = ""
        status = ""

        for line in text.splitlines()[:40]:
            m = re.match(r'\|\s*\*\*Layer\*\*\s*\|\s*(.+?)\s*\|', line)
            if m:
                layer = m.group(1).strip()
            m = re.match(r'\|\s*\*\*Status\*\*\s*\|\s*(.+?)\s*\|', line)
            if m:
                status = m.group(1).strip()

        # Categorize
        cat = "implementation"
        if name in SUPERSEDED_SPECS:
            cat = "superseded"
        elif name in REFERENCE_SPECS:
            cat = "reference"

        specs.append(SpecInfo(name=name, layer=layer, status=status, category=cat))
    return specs


def parse_task_yamls(tasks_dir: Path) -> list[TaskInfo]:
    """Parse ALL task YAMLs — spec_ref is the primary linking mechanism."""
    try:
        import yaml
    except ImportError:
        print("  WARNING: PyYAML not available, task linking will be incomplete", file=sys.stderr)
        return []

    tasks = []
    for yf in sorted(tasks_dir.glob("*.yaml")):
        try:
            data = yaml.safe_load(yf.read_text(encoding="utf-8"))
            if not data or not isinstance(data, dict):
                continue
            tid = str(data.get("id", ""))
            if not tid:
                continue

            spec_ref = data.get("spec_ref") or ""
            if isinstance(spec_ref, str):
                # Normalize: "brain-foundation.md" → "brain-foundation"
                # Also handle "docs/specs/architecture-portal.md"
                spec_ref = spec_ref.strip().strip('"').strip("'")
                spec_ref = spec_ref.replace("docs/specs/", "")
                if spec_ref.endswith(".md"):
                    spec_ref = spec_ref[:-3]
                if spec_ref == "null":
                    spec_ref = ""

            tasks.append(TaskInfo(
                id=tid,
                title=data.get("title", ""),
                status=data.get("status", ""),
                deps=[str(d) for d in (data.get("blocked_by") or [])],
                spec_ref=spec_ref,
            ))
        except Exception:
            pass
    return tasks


def parse_backlog_tasks(backlog_path: Path) -> dict[str, str]:
    """Fallback: get task titles from backlog for tasks without YAML."""
    titles = {}
    if not backlog_path.exists():
        return titles
    text = backlog_path.read_text(encoding="utf-8")
    for m in re.finditer(r'###\s*\[(\d+)\]\s*(.+?)$', text, re.MULTILINE):
        titles[m.group(1)] = m.group(2).strip()
    return titles


def build_spec_task_map(specs: list[SpecInfo], tasks: list[TaskInfo]) -> dict[str, list[TaskInfo]]:
    """Build spec→tasks mapping using spec_ref from YAMLs (data-driven, no hardcoded map)."""
    mapping: dict[str, list[TaskInfo]] = {s.name: [] for s in specs}

    for task in tasks:
        if task.spec_ref and task.spec_ref in mapping:
            mapping[task.spec_ref].append(task)

    return mapping


def status_label(raw: str) -> str:
    s = raw.lower()
    if "implementiert" in s or s == "aktuell (implementiert)":
        return "IMPL"
    if "aktuell" in s:
        return "SPEC"
    if "proposed" in s:
        return "PROP"
    if "spec-ready" in s:
        return "READY"
    if "board-approved" in s:
        return "APPR"
    if "conditionally" in s:
        return "COND"
    if "superseded" in s:
        return "SUPER"
    if "stale" in s:
        return "STALE"
    if "implemented" in s:
        return "IMPL"
    return raw[:8] if raw else "?"


def task_label(status: str) -> str:
    s = status.lower()
    if s == "done":
        return "DONE"
    if s in ("in_progress", "in-progress"):
        return "WIP"
    if s in ("pending", "open"):
        return "PEND"
    if s == "blocked":
        return "BLCK"
    return status[:6] if status else "—"


def normalize_layer(raw: str) -> str:
    s = raw.lower()
    if "cross-cutting" in s or "cross cutting" in s:
        return "Cross-Cutting"
    if "tooling" in s or "ux" in s:
        return "Tooling / UX"
    if "interface" in s:
        return "Interface"
    if "knowledge" in s and ("runtime" in s or "harness" in s):
        return "Knowledge + Runtime"
    if "knowledge" in s and "intelligence" in s:
        return "Knowledge + Intelligence"
    if "knowledge" in s:
        return "Knowledge"
    if ("runtime" in s or "harness" in s) and "intelligence" in s:
        return "Runtime + Intelligence"
    if "runtime" in s or "harness" in s:
        return "Runtime / Harness"
    if "intelligence" in s:
        return "Intelligence"
    return raw or "Uncategorized"


def generate(specs: list[SpecInfo], spec_tasks: dict[str, list[TaskInfo]]) -> str:
    """Generate the markdown status page."""
    lines = [
        "# Component Status Overview",
        "",
        "Auto-generated by `scripts/generate-status.py`.",
        "Re-run: `python3 scripts/generate-status.py`",
        "",
        "**Linking mechanism:** `spec_ref` in task YAMLs → spec name. Data-driven, no hardcoded maps.",
        "",
        "**Spec Status:** IMPL = implemented | SPEC = spec current | READY = spec-ready |"
        " APPR = board-approved | PROP = proposed | COND = conditional | SUPER = superseded | STALE = stale",
        "",
        "**Task Status:** DONE | WIP | PEND | BLCK",
        "",
        "**Spec Category:** impl = implementation spec (needs tasks) |"
        " ref = reference spec (no task expected) | super = superseded",
        "",
        "---",
        "",
    ]

    # Group by layer
    layer_groups: dict[str, list[SpecInfo]] = {}
    for spec in specs:
        layer = normalize_layer(spec.layer)
        layer_groups.setdefault(layer, []).append(spec)

    # Preferred order
    order = [
        "Knowledge", "Knowledge + Runtime", "Knowledge + Intelligence",
        "Runtime / Harness", "Runtime + Intelligence", "Intelligence",
        "Interface", "Cross-Cutting", "Tooling / UX", "Uncategorized",
    ]

    total = 0
    impl_count = 0
    spec_count = 0
    prop_count = 0
    other_count = 0
    no_task_impl_specs = []

    for layer in order:
        group = layer_groups.get(layer, [])
        if not group:
            continue

        lines.append(f"## {layer}")
        lines.append("")
        lines.append("| Spec | Cat | Spec-Status | Tasks | Task-Status | Deps |")
        lines.append("|------|-----|------------|-------|-------------|------|")

        for spec in sorted(group, key=lambda s: s.name):
            total += 1
            sl = status_label(spec.status)

            if sl == "IMPL":
                impl_count += 1
            elif sl in ("SPEC",):
                spec_count += 1
            elif sl in ("PROP",):
                prop_count += 1
            else:
                other_count += 1

            cat = spec.category[:5]
            tasks = spec_tasks.get(spec.name, [])

            if tasks:
                task_ids = ", ".join(f"[{t.id}]" for t in tasks)
                task_statuses = ", ".join(task_label(t.status) for t in tasks)
                all_deps = set()
                for t in tasks:
                    all_deps.update(t.deps)
                deps_str = ", ".join(sorted(all_deps)) if all_deps else "—"
            else:
                task_ids = "—"
                task_statuses = "—"
                deps_str = "—"

                # Flag implementation specs without tasks
                if spec.category == "implementation" and sl not in ("SUPER", "STALE"):
                    no_task_impl_specs.append(spec.name)

            lines.append(f"| {spec.name} | {cat} | {sl} | {task_ids} | {task_statuses} | {deps_str} |")

        lines.append("")

    # Summary
    lines.append("---")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append("| Metric | Count |")
    lines.append("|--------|-------|")
    lines.append(f"| Total Specs | {total} |")
    lines.append(f"| Implemented | {impl_count} |")
    lines.append(f"| Spec Current (no code yet) | {spec_count} |")
    lines.append(f"| Proposed | {prop_count} |")
    lines.append(f"| Other (ready, approved, cond.) | {other_count} |")
    lines.append("")

    if no_task_impl_specs:
        lines.append("## Gaps: Implementation Specs Without Tasks")
        lines.append("")
        lines.append("These specs are categorized as implementation specs but have **no task with `spec_ref`** pointing to them.")
        lines.append("Either create a task with `spec_ref: <spec-name>.md` or recategorize as reference spec.")
        lines.append("")
        for name in sorted(no_task_impl_specs):
            lines.append(f"- **{name}** — needs a task or reclassification")
        lines.append("")

    return "\n".join(lines)


def main():
    print(f"Parsing specs from {SPECS_DIR} ...")
    specs = parse_specs(SPECS_DIR)
    print(f"  Found {len(specs)} specs")

    print(f"Parsing task YAMLs from {TASKS_DIR} ...")
    tasks = parse_task_yamls(TASKS_DIR)
    print(f"  Found {len(tasks)} task YAML files")

    spec_tasks = build_spec_task_map(specs, tasks)

    # Stats
    linked = sum(1 for v in spec_tasks.values() if v)
    print(f"  Linked: {linked} specs have tasks via spec_ref")
    print(f"  Unlinked: {len(specs) - linked} specs have no tasks")

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    content = generate(specs, spec_tasks)
    OUTPUT_PATH.write_text(content, encoding="utf-8")
    print(f"Written to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
