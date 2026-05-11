#!/usr/bin/env python3
"""
board-depth.py — Mechanischer Tiefenmodus-Check für Spec Board Reviews.

Bestimmt ob eine Spec Quick oder Deep reviewed werden muss.
4 Checks — mindestens 1 JA → Deep.

Usage:
  python3 scripts/board-depth.py brain-search-v2
  python3 scripts/board-depth.py docs/specs/brain-search-v2.md
  python3 scripts/board-depth.py --project-root /path/to/project brain-search-v2

Exit-Codes:
  0 = QUICK
  1 = DEEP
  2 = Error
"""

import argparse
import os
import re
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    print("ERROR: PyYAML not installed", file=sys.stderr)
    sys.exit(2)

# Path resolution (Task 010 Part L0b — Pre-Split Refactor)
#
# board-depth.py reads exclusively from project data (docs/specs/,
# docs/tasks/, SPEC-MAP.md), so it only needs PROJECT_ROOT. Derived from
# --project-root flag, BUDDY_PROJECT_ROOT env-var, or Path.cwd(). Post
# repo-split the script lives in the framework repo but must still target
# the active project for spec analysis.
#
# Pre-Split Invariant: when invoked from the BuddyAI monolith root without
# BUDDY_PROJECT_ROOT set, PROJECT_ROOT == BuddyAI root, so existing
# behaviour is preserved.
PROJECT_ROOT = Path(os.environ.get("BUDDY_PROJECT_ROOT", Path.cwd())).resolve()
SPECS_DIR = PROJECT_ROOT / "docs" / "specs"
TASKS_DIR = PROJECT_ROOT / "docs" / "tasks"
SPEC_MAP = SPECS_DIR / "SPEC-MAP.md"


def parse_spec_map_layers() -> dict[str, str]:
    """Parse SPEC-MAP to get layer per spec."""
    layers = {}
    if not SPEC_MAP.exists():
        return layers
    current_layer = ""
    for line in SPEC_MAP.read_text(encoding="utf-8").splitlines():
        if line.startswith("## "):
            current_layer = line.strip("# ").strip()
        if line.startswith("| ") and not line.startswith("| Spec") and not line.startswith("|---"):
            cells = [c.strip() for c in line.split("|")[1:-1]]
            if len(cells) >= 1:
                spec_name = cells[0].strip()
                if spec_name and spec_name not in ("Spec",):
                    layers[spec_name] = current_layer
    return layers


def parse_spec_map_consumers(spec_name: str) -> list[str]:
    """Get consumers of a spec from SPEC-MAP."""
    if not SPEC_MAP.exists():
        return []
    for line in SPEC_MAP.read_text(encoding="utf-8").splitlines():
        if line.startswith("| ") and spec_name in line:
            cells = [c.strip() for c in line.split("|")[1:-1]]
            if len(cells) >= 1 and cells[0].strip() == spec_name:
                # Consumers is the last column (4th or 6th depending on table)
                consumers_col = cells[-1] if len(cells) >= 4 else ""
                if consumers_col and consumers_col != "—" and consumers_col != "--":
                    return [c.strip() for c in consumers_col.split(",")]
    return []


def check_cross_layer(spec_name: str) -> tuple[bool, str]:
    """Check 1: Consumers in different layer than spec?"""
    layers = parse_spec_map_layers()
    spec_layer = layers.get(spec_name, "")
    if not spec_layer:
        return False, f"spec not found in SPEC-MAP"

    consumers = parse_spec_map_consumers(spec_name)
    cross = []
    for c in consumers:
        c_layer = layers.get(c, "")
        if c_layer and c_layer != spec_layer:
            cross.append(f"{c} ({c_layer})")

    if cross:
        return True, f"spec={spec_layer}, cross-layer consumers: {', '.join(cross)}"
    return False, f"all consumers in same layer ({spec_layer})"


def check_interface(spec_path: Path) -> tuple[bool, str]:
    """Check 2: Defines API, Pydantic Model, Schema?"""
    if not spec_path.exists():
        return False, "spec file not found"
    text = spec_path.read_text(encoding="utf-8")
    markers = []
    if re.search(r'class \w+.*(?:BaseModel|Protocol|TypedDict)', text):
        markers.append("Pydantic/Protocol")
    if re.search(r'async def \w+\(', text):
        markers.append("async API")
    if re.search(r'CREATE TABLE|CREATE INDEX|ALTER TABLE', text, re.IGNORECASE):
        markers.append("DDL")
    if re.search(r'SearchResult|BrainFacade|DelegationSpec', text):
        markers.append("Interface type")

    if markers:
        return True, f"defines: {', '.join(markers)}"
    return False, "no interface markers found"


def check_full_path(spec_name: str) -> tuple[bool, str]:
    """Check 3: Any task with dev_path: full referencing this spec?"""
    spec_ref = f"{spec_name}.md"
    for yaml_path in TASKS_DIR.glob("*.yaml"):
        if yaml_path.name.endswith("-gates.yaml"):
            continue
        try:
            data = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if not isinstance(data, dict):
            continue
        sr = data.get("spec_ref") or ""
        if sr.replace(".md", "") == spec_name:
            if data.get("dev_path") == "full":
                return True, f"task {data.get('id')} has dev_path: full"
    return False, "no full-path task"


def check_security(spec_path: Path) -> tuple[bool, str]:
    """Check 4: Security-relevant content?"""
    if not spec_path.exists():
        return False, "spec file not found"
    text = spec_path.read_text(encoding="utf-8").lower()
    markers = []
    if "auth" in text and ("user_id" in text or "token" in text):
        markers.append("auth")
    if "consent" in text:
        markers.append("consent")
    if "encrypt" in text or "crypto" in text:
        markers.append("crypto")
    if "user_id" in text and ("filter" in text or "isolat" in text):
        markers.append("user-isolation")

    if markers:
        return True, f"security markers: {', '.join(markers)}"
    return False, "no security markers"


def main():
    parser = argparse.ArgumentParser(
        description="Mechanischer Tiefenmodus-Check für Spec Board Reviews.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "spec",
        help="Spec name (e.g. brain-search-v2) or path (docs/specs/brain-search-v2.md)",
    )
    parser.add_argument(
        "--project-root",
        type=str,
        default=None,
        help="Override PROJECT_ROOT (where docs/specs + docs/tasks live). "
             "Takes precedence over BUDDY_PROJECT_ROOT env-var.",
    )
    args = parser.parse_args()

    # Task 010 Part L0b: explicit --project-root override rebinds the
    # module-level data dirs so every check resolves against the new root.
    if args.project_root:
        global PROJECT_ROOT, SPECS_DIR, TASKS_DIR, SPEC_MAP
        PROJECT_ROOT = Path(args.project_root).resolve()
        SPECS_DIR = PROJECT_ROOT / "docs" / "specs"
        TASKS_DIR = PROJECT_ROOT / "docs" / "tasks"
        SPEC_MAP = SPECS_DIR / "SPEC-MAP.md"

    spec_input = args.spec
    # Normalize: accept "brain-search-v2" or "docs/specs/brain-search-v2.md"
    spec_name = Path(spec_input).stem.replace(".md", "")
    spec_path = SPECS_DIR / f"{spec_name}.md"

    checks = [
        ("Cross-Layer", check_cross_layer(spec_name)),
        ("Interface", check_interface(spec_path)),
        ("Full-Path", check_full_path(spec_name)),
        ("Security", check_security(spec_path)),
    ]

    deep = False
    for name, (triggered, detail) in checks:
        mark = "→ DEEP" if triggered else "  ok"
        print(f"  {mark}  {name}: {detail}")
        if triggered:
            deep = True

    mode = "DEEP" if deep else "QUICK"
    print(f"\n  Result: {mode}")
    sys.exit(1 if deep else 0)


if __name__ == "__main__":
    main()
