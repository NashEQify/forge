#!/usr/bin/env python3
"""validate_runbook_consistency.py — workflow.yaml ↔ WORKFLOW.md drift check.

Each runbook directory under workflows/runbooks/<name>/ has:
- workflow.yaml — engine-driven state machine (machine-readable)
- WORKFLOW.md  — human-readable guide (canonical SoT for prose)

These two MUST stay in sync (option-a validator from Cross-Session-Workflow F-H).
This script catches drift heuristically:

CHECK 1: paired-existence
  Both workflow.yaml AND WORKFLOW.md exist in the runbook dir.

CHECK 2: derived_from
  workflow.yaml has 'derived_from: WORKFLOW.md@YYYY-MM-DD' frontmatter pointing
  at the canonical version. Missing/malformed → WARN.

CHECK 3: step-name presence
  Each step in workflow.yaml has a 'name' field. The first 2-3 keyword tokens
  (lowercased, stop-word-filtered) of the name must appear somewhere in
  WORKFLOW.md as a substring. Misses → WARN (likely drift: step renamed in
  md but not yaml, or vice versa).

CHECK 4: phase-comment parity
  workflow.yaml uses '# Phase: X' header comments. Each must correspond to a
  '### Phase: X' section in WORKFLOW.md. Phase added/removed in one but not
  the other → WARN.

EXIT CODES
  0 — all clean
  0 — only warnings (heuristic — never blocks; pre-commit hook degrades to WARN)
  2 — hard error (missing files, parse failure)

USAGE
  python3 validate_runbook_consistency.py                     # all runbooks
  python3 validate_runbook_consistency.py --runbook build     # specific one
  python3 validate_runbook_consistency.py --staged            # only staged-in-git

Mechanic: WARN-only per spec — prose-vs-yaml drift is sometimes intentional
(yaml is implementation, md is reference). Pre-commit-hook surfaces; user
decides.
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path

try:
    import yaml  # PyYAML
except ImportError:
    print("WARN: PyYAML missing — install via: pip install pyyaml", file=sys.stderr)
    sys.exit(0)  # Graceful skip — consumer repo without dev deps

FRAMEWORK_ROOT = Path(
    os.environ.get("FRAMEWORK_ROOT", Path(__file__).resolve().parent.parent)
)
RUNBOOKS_DIR = FRAMEWORK_ROOT / "workflows" / "runbooks"

# Stop-words filtered from step-name keyword extraction (German + English mix
# matching the runbook prose conventions).
STOPWORDS = {
    "der", "die", "das", "und", "oder", "mit", "im", "in", "auf", "zur", "zum",
    "fuer", "für", "via", "aus", "bei", "vor", "nach",
    "the", "a", "an", "and", "or", "with", "in", "on", "at", "to", "for", "via",
    "of", "by", "is", "are", "be",
}


def extract_keywords(text: str, n: int = 3) -> list[str]:
    """First N stop-word-filtered alpha tokens from text, lowercased."""
    tokens = re.findall(r"[A-Za-zÄÖÜäöüß_][A-Za-z0-9ÄÖÜäöüß_-]*", text)
    out = []
    for t in tokens:
        tl = t.lower()
        if tl in STOPWORDS:
            continue
        if len(tl) < 3:
            continue
        out.append(tl)
        if len(out) >= n:
            break
    return out


def check_runbook(runbook_dir: Path) -> tuple[list[str], list[str]]:
    """Run all checks on a single runbook dir. Returns (warnings, errors)."""
    warnings: list[str] = []
    errors: list[str] = []
    name = runbook_dir.name
    yaml_path = runbook_dir / "workflow.yaml"
    md_path = runbook_dir / "WORKFLOW.md"

    # CHECK 1: paired-existence
    if not yaml_path.exists() and not md_path.exists():
        return warnings, errors  # not a runbook, skip
    if not yaml_path.exists():
        warnings.append(
            f"[{name}] WORKFLOW.md exists without workflow.yaml — engine-disabled."
        )
        return warnings, errors
    if not md_path.exists():
        errors.append(
            f"[{name}] workflow.yaml exists without WORKFLOW.md — orphan engine config."
        )
        return warnings, errors

    # Parse yaml
    try:
        with yaml_path.open("r", encoding="utf-8") as f:
            yaml_data = yaml.safe_load(f) or {}
    except (yaml.YAMLError, OSError) as e:
        errors.append(f"[{name}] workflow.yaml parse failure: {e}")
        return warnings, errors

    # Read md
    try:
        md_text = md_path.read_text(encoding="utf-8")
    except OSError as e:
        errors.append(f"[{name}] WORKFLOW.md read failure: {e}")
        return warnings, errors

    md_lower = md_text.lower()

    # CHECK 2: derived_from
    derived = yaml_data.get("derived_from", "")
    if not derived:
        warnings.append(
            f"[{name}] workflow.yaml missing 'derived_from: WORKFLOW.md@YYYY-MM-DD'"
        )
    elif not re.match(r"^WORKFLOW\.md@\d{4}-\d{2}-\d{2}$", str(derived)):
        warnings.append(
            f"[{name}] workflow.yaml derived_from='{derived}' — expected "
            f"'WORKFLOW.md@YYYY-MM-DD'"
        )

    # CHECK 3: step-name presence
    steps = yaml_data.get("steps", []) or []
    missing_in_md: list[str] = []
    for step in steps:
        if not isinstance(step, dict):
            continue
        sname = step.get("name", "")
        sid = step.get("id", "")
        if not sname:
            warnings.append(f"[{name}] step '{sid}' has no 'name' field")
            continue
        keywords = extract_keywords(sname, n=2)
        if not keywords:
            continue
        # Heuristic: at least ONE keyword from the step-name should appear in md.
        # Stricter would be ALL — but prose paraphrases. ONE catches obvious drift.
        if not any(kw in md_lower for kw in keywords):
            missing_in_md.append(f"{sid} ({sname[:60]})")
    if missing_in_md:
        warnings.append(
            f"[{name}] {len(missing_in_md)} yaml step(s) have no keyword match "
            f"in WORKFLOW.md (drift?): {'; '.join(missing_in_md[:5])}"
            + (f" +{len(missing_in_md) - 5} more" if len(missing_in_md) > 5 else "")
        )

    # CHECK 4: phase-comment parity
    yaml_phases = set()
    yaml_text = yaml_path.read_text(encoding="utf-8")
    for m in re.finditer(r"^\s*#\s*Phase:\s*(.+?)\s*$", yaml_text, re.MULTILINE):
        yaml_phases.add(m.group(1).strip().lower())
    md_phases = set()
    for m in re.finditer(r"^###\s+Phase:\s*(.+?)\s*$", md_text, re.MULTILINE):
        md_phases.add(m.group(1).strip().lower())
    only_yaml = yaml_phases - md_phases
    only_md = md_phases - yaml_phases
    if only_yaml:
        warnings.append(
            f"[{name}] phase(s) in yaml but not md: {sorted(only_yaml)}"
        )
    if only_md:
        warnings.append(
            f"[{name}] phase(s) in md but not yaml: {sorted(only_md)}"
        )

    # CHECK 5: top-level routes consistency (workflow_engine.py path-routing)
    # Mechanic: per route, all referenced step-ids must exist in steps[].
    # WORKFLOW.md must mention each declared route by name (drift heuristic).
    routes = yaml_data.get("routes")
    if routes is not None:
        if not isinstance(routes, dict) or not routes:
            errors.append(
                f"[{name}] top-level 'routes:' must be non-empty dict, "
                f"got {type(routes).__name__}"
            )
        else:
            step_ids_in_yaml = {
                s.get("id") for s in steps if isinstance(s, dict) and s.get("id")
            }
            for route_name, route_steps in routes.items():
                if not isinstance(route_steps, list):
                    errors.append(
                        f"[{name}] route '{route_name}' must be list of step-ids, "
                        f"got {type(route_steps).__name__}"
                    )
                    continue
                # Each step-id in route must exist in steps[]
                missing_steps = [s for s in route_steps if s not in step_ids_in_yaml]
                if missing_steps:
                    errors.append(
                        f"[{name}] route '{route_name}' references unknown "
                        f"step-id(s): {missing_steps}"
                    )
                # WORKFLOW.md should mention route name (drift heuristic)
                if route_name.lower() not in md_lower:
                    warnings.append(
                        f"[{name}] route '{route_name}' declared in yaml but "
                        f"not mentioned in WORKFLOW.md — drift?"
                    )

    return warnings, errors


def staged_runbook_dirs() -> list[Path]:
    """Return runbook dirs containing staged WORKFLOW.md or workflow.yaml."""
    try:
        out = subprocess.check_output(
            ["git", "diff", "--cached", "--name-only"],
            cwd=FRAMEWORK_ROOT,
            text=True,
        )
    except subprocess.CalledProcessError:
        return []
    dirs = set()
    for line in out.splitlines():
        if not line.strip():
            continue
        p = Path(line)
        if (
            p.name in ("workflow.yaml", "WORKFLOW.md")
            and "workflows/runbooks/" in line
        ):
            dirs.add(FRAMEWORK_ROOT / p.parent)
    return sorted(dirs)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runbook", help="check only this runbook by name")
    parser.add_argument(
        "--staged",
        action="store_true",
        help="check only runbooks with staged yaml/md",
    )
    args = parser.parse_args()

    if not RUNBOOKS_DIR.exists():
        print(f"SKIP: runbooks dir not found at {RUNBOOKS_DIR}")
        return 0

    if args.runbook:
        targets = [RUNBOOKS_DIR / args.runbook]
    elif args.staged:
        targets = staged_runbook_dirs()
        if not targets:
            print("CLEAN: no staged runbook changes")
            return 0
    else:
        targets = sorted(p for p in RUNBOOKS_DIR.iterdir() if p.is_dir())

    all_warns: list[str] = []
    all_errors: list[str] = []
    for t in targets:
        if not t.is_dir():
            all_errors.append(f"Not a directory: {t}")
            continue
        warns, errs = check_runbook(t)
        all_warns.extend(warns)
        all_errors.extend(errs)

    for w in all_warns:
        print(f"WARN: {w}")
    for e in all_errors:
        print(f"ERROR: {e}", file=sys.stderr)

    if all_errors:
        print(f"\nSummary: {len(all_errors)} error(s), {len(all_warns)} warning(s)")
        return 2
    if all_warns:
        print(f"\nSummary: 0 errors, {len(all_warns)} warning(s)")
        return 0
    print(f"CLEAN: {len(targets)} runbook(s) checked, no drift detected")
    return 0


if __name__ == "__main__":
    sys.exit(main())
