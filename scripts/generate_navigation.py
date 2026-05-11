#!/usr/bin/env python3
"""
Regenerate AUTO blocks in navigation.md files across the repo.

Phase 366-D.5 (Navigation-Layer-Re-Introduction): per-Directory navigation.md
with AUTO-Block (file-listing from frontmatter) + manual Reader-Journey content.

Markers (analog skill-map.md):
  <!-- NAV-AUTO-START -->
  ...
  <!-- NAV-AUTO-END -->

Per-Directory navigation.md targets (top-level-3 cap):
  framework/                — Level 1, all framework sub-areas
  skills/         — Level 2, all active skills
  skills/_protocols/ — Level 3, all protocols
  workflows/runbooks/ — Level 2, all workflows
  references/     — Level 2, all references
  agents/                   — Level 1, all personas
  agents/buddy/             — Level 2, Buddy sub-files
  agents/_protocols/        — Level 2, agent protocols
  docs/                     — Level 1, docs structure

Idempotent: second run with no input change yields no diff.

Drift-Detection: complementary to consistency_check (validates that manual
content outside AUTO-Block points to existing files).
"""
from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Optional

try:
    import yaml
except ImportError:
    yaml = None  # type: ignore

AUTO_START = "<!-- NAV-AUTO-START -->"
AUTO_END = "<!-- NAV-AUTO-END -->"

# Per-target configuration: target_path -> (scan_dir, label, exclude_patterns)
TARGETS: list[tuple[str, str, str, list[str]]] = [
    # (target_navigation_path, scan_dir, scan_label, excluded_dir_patterns)
    (
        "framework/navigation.md",
        "framework",
        "Framework Sub-Areas",
        ["_archived", "audits", "skills/_archived"],
    ),
    (
        "skills/navigation.md",
        "skills",
        "Active Skills",
        ["_archived", "_protocols"],
    ),
    (
        "skills/_protocols/navigation.md",
        "skills/_protocols",
        "Skill Protocols",
        [],
    ),
    (
        "workflows/runbooks/navigation.md",
        "workflows/runbooks",
        "Workflows",
        [],
    ),
    (
        "references/navigation.md",
        "references",
        "References",
        [],
    ),
    (
        "agents/navigation.md",
        "agents",
        "Personas",
        ["_protocols", "buddy", "companions", "templates"],
    ),
    (
        "agents/buddy/navigation.md",
        "agents/buddy",
        "Buddy Sub-Files",
        [],
    ),
    (
        "agents/_protocols/navigation.md",
        "agents/_protocols",
        "Agent Protocols",
        [],
    ),
]


def repo_root(start: Path) -> Path:
    cur = start.resolve()
    for parent in [cur] + list(cur.parents):
        if (parent / "framework").is_dir() and (parent / "agents").is_dir():
            return parent
    return start.resolve()


def extract_frontmatter(text: str) -> Optional[dict]:
    text = text.lstrip("﻿")
    if not text.startswith("---"):
        return None
    parts = text.split("---", 2)
    if len(parts) < 3:
        return None
    if yaml is None:
        return None
    try:
        data = yaml.safe_load(parts[1])
        return data if isinstance(data, dict) else None
    except yaml.YAMLError:
        return None


def first_paragraph(text: str, max_chars: int = 200) -> str:
    """Extract first non-empty paragraph after frontmatter, no headers."""
    # Strip frontmatter
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) >= 3:
            text = parts[2]
    text = text.lstrip("﻿").strip()
    # Find first paragraph that's not a heading
    for para in re.split(r"\n\s*\n", text):
        para = para.strip()
        if not para:
            continue
        # Skip pure headings or code-blocks
        if para.startswith("#") or para.startswith("```"):
            continue
        # First non-heading paragraph found
        single = re.sub(r"\s+", " ", para)
        if len(single) > max_chars:
            single = single[: max_chars - 1].rsplit(" ", 1)[0] + "…"
        return single
    return ""


def describe_md_file(path: Path) -> str:
    """One-line description for an MD file: prefer description from frontmatter."""
    try:
        text = path.read_text(encoding="utf-8")
    except Exception:
        return ""
    fm = extract_frontmatter(text)
    if fm:
        desc = fm.get("description")
        if isinstance(desc, str):
            single = re.sub(r"\s+", " ", desc).strip()
            if len(single) > 200:
                single = single[:199].rsplit(" ", 1)[0] + "…"
            return single
    return first_paragraph(text)


def describe_dir(dir_path: Path) -> str:
    """One-line description for a sub-directory.

    Note: navigation.md is intentionally NOT in the candidates list. Its
    manual sections are placeholder-bait until filled and would pollute
    parent navigation.md's AUTO-Block. README.md / SKILL.md / WORKFLOW.md /
    soul.md are SoT for the directory's identity.
    """
    for candidate in ("SKILL.md", "WORKFLOW.md", "soul.md", "README.md"):
        f = dir_path / candidate
        if f.exists():
            return describe_md_file(f)
    # Fallback: if directory has EXACTLY ONE meaningful sub-directory with a
    # canonical SoT file, use that (e.g. <name>/<sub>/WORKFLOW.md).
    # Multi-child container dirs (e.g. skills/, references/) have no single
    # representative sub — leave empty and rely on parent navigation.md manual.
    if dir_path.exists():
        subs = [s for s in sorted(dir_path.iterdir()) if s.is_dir() and not s.name.startswith((".", "_"))]
        if len(subs) == 1:
            for candidate in ("WORKFLOW.md", "SKILL.md", "soul.md", "README.md"):
                f = subs[0] / candidate
                if f.exists():
                    return describe_md_file(f)
    return ""


def scan_dir(scan_path: Path, exclude_patterns: list[str]) -> tuple[list[tuple[str, str]], list[tuple[str, str]]]:
    """Return (files, dirs) lists where each tuple is (name, description)."""
    if not scan_path.exists():
        return [], []
    files: list[tuple[str, str]] = []
    dirs: list[tuple[str, str]] = []
    for entry in sorted(scan_path.iterdir()):
        if entry.name.startswith(".") or entry.name == "navigation.md":
            continue
        if any(pattern in str(entry.relative_to(scan_path)) for pattern in exclude_patterns):
            continue
        if entry.is_dir():
            desc = describe_dir(entry)
            dirs.append((entry.name, desc))
        elif entry.is_file() and entry.suffix == ".md":
            desc = describe_md_file(entry)
            files.append((entry.name, desc))
    return files, dirs


def render_auto_block(label: str, files: list[tuple[str, str]], dirs: list[tuple[str, str]]) -> str:
    """Render the AUTO-Block content (between markers)."""
    lines: list[str] = []
    lines.append("")
    lines.append(f"_Generated by `scripts/generate_navigation.py` — do not edit_")
    lines.append("")
    if dirs:
        lines.append(f"### {label} (Sub-Directories)")
        lines.append("")
        lines.append("| Sub-dir | Description |")
        lines.append("|---|---|")
        for name, desc in dirs:
            desc_short = desc.replace("|", "\\|") if desc else "_(no description)_"
            lines.append(f"| `{name}/` | {desc_short} |")
        lines.append("")
    if files:
        lines.append(f"### {label} (Files)")
        lines.append("")
        lines.append("| File | Description |")
        lines.append("|---|---|")
        for name, desc in files:
            desc_short = desc.replace("|", "\\|") if desc else "_(no description)_"
            lines.append(f"| `{name}` | {desc_short} |")
        lines.append("")
    if not files and not dirs:
        lines.append("_(no entries)_")
        lines.append("")
    return "\n".join(lines)


def update_navigation(target_path: Path, auto_content: str, scan_label: str) -> bool:
    """Update navigation.md, preserving manual content outside AUTO-Block.

    Returns True if file was modified.
    """
    if target_path.exists():
        existing = target_path.read_text(encoding="utf-8")
    else:
        # Create skeleton with manual sections + empty AUTO-Block
        rel = target_path.relative_to(target_path.parents[2 if "skills" in target_path.parts else 1] if target_path.parents else target_path).as_posix() if False else target_path.name
        existing = (
            f"# Navigation: {target_path.parent.name}/\n\n"
            "## What lives here?\n\n"
            "_(manual reader-journey description — what the sub-areas / files\n"
            "of this directory do and when to come here)_\n\n"
            "## Where to look for which question?\n\n"
            "_(manual lookup: typical questions → concrete sub-area / file)_\n\n"
            "## Inventory (auto)\n\n"
            f"{AUTO_START}\n{AUTO_END}\n"
        )

    if AUTO_START in existing and AUTO_END in existing:
        new_text = re.sub(
            re.escape(AUTO_START) + r".*?" + re.escape(AUTO_END),
            f"{AUTO_START}\n{auto_content}\n{AUTO_END}",
            existing,
            count=1,
            flags=re.DOTALL,
        )
    else:
        # Add AUTO-Block at end
        new_text = existing.rstrip() + f"\n\n## Inventar (auto)\n\n{AUTO_START}\n{auto_content}\n{AUTO_END}\n"

    if new_text != existing:
        target_path.parent.mkdir(parents=True, exist_ok=True)
        target_path.write_text(new_text, encoding="utf-8")
        return True
    return False


def main() -> int:
    root = repo_root(Path.cwd())
    if yaml is None:
        print(
            "generate_navigation: PyYAML not installed; will use heuristic descriptions",
            file=sys.stderr,
        )

    changed = 0
    for target_rel, scan_rel, label, excludes in TARGETS:
        target_path = root / target_rel
        scan_path = root / scan_rel
        if not scan_path.exists():
            print(f"generate_navigation: SKIP {scan_rel} (not exists)", file=sys.stderr)
            continue
        files, dirs = scan_dir(scan_path, excludes)
        auto_content = render_auto_block(label, files, dirs)
        if update_navigation(target_path, auto_content, label):
            print(f"generate_navigation: wrote {target_path}")
            changed += 1
        else:
            print(f"generate_navigation: unchanged {target_path}")

    if changed:
        print(f"\ngenerate_navigation: updated {changed} navigation.md file(s)")
    else:
        print("\ngenerate_navigation: all up to date")
    return 0


if __name__ == "__main__":
    sys.exit(main())
