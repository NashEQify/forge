#!/usr/bin/env python3
"""
board-synthesize-input.py — Generiert Synthesize-Input aus konsolidiertem Review.

Liest consolidated-passN.md, extrahiert ALLE Finding-IDs (C/H/M/L),
gibt einen strukturierten Fix-Auftrag aus. Keine Finding wird ausgelassen.

Usage:
  python3 scripts/board-synthesize-input.py docs/reviews/board/brain-search-v2-consolidated-pass1.md

Output: Strukturierter Text mit allen Findings, gruppiert nach Severity.
"""

import re
import sys
from pathlib import Path


def parse_consolidated(path: Path) -> list[dict]:
    """Parse consolidated review for all findings."""
    text = path.read_text(encoding="utf-8")
    findings = []
    current = None

    for line in text.splitlines():
        # Finding header: ### C-001: Title  or  ### C-001 (severity): Title
        header_match = re.match(r'^###\s+(C-\d+)[\s:]+(.+)', line)
        if header_match:
            if current:
                findings.append(current)
            current = {
                "id": header_match.group(1),
                "title": header_match.group(2).strip(),
                "severity": "",
                "lines": [],
            }
            continue

        if current is None:
            continue

        # Severity line — supports both markdown and table format
        sev_match = re.match(r'^\s*[-*]\s*\*\*Severity[:\s]*\*\*\s*(\w+)', line, re.IGNORECASE)
        if not sev_match:
            sev_match = re.match(r'^\|\s*severity\s*\|\s*(\w+)\s*\|', line, re.IGNORECASE)
        if not sev_match and not current["severity"]:
            # Try extracting from title: [HIGH], [MEDIUM], [LOW], [CRITICAL]
            title_sev = re.search(r'\[(HIGH|MEDIUM|LOW|CRITICAL)\]', current["title"], re.IGNORECASE)
            if title_sev:
                current["severity"] = title_sev.group(1).lower()
        if sev_match:
            current["severity"] = sev_match.group(1).lower()
            continue

        # Collect all content lines for the finding
        if line.startswith("### ") and not line.startswith("### C-"):
            # New non-finding section — save current
            if current:
                findings.append(current)
            current = None
            continue

        if line.startswith("## "):
            if current:
                findings.append(current)
            current = None
            continue

        current["lines"].append(line)

    if current:
        findings.append(current)

    return findings


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 scripts/board-synthesize-input.py <consolidated-file>", file=sys.stderr)
        sys.exit(2)

    path = Path(sys.argv[1])
    if not path.exists():
        # Try relative to repo root
        repo_root = Path(__file__).resolve().parent.parent
        path = repo_root / sys.argv[1]
    if not path.exists():
        print(f"ERROR: {sys.argv[1]} not found", file=sys.stderr)
        sys.exit(2)

    findings = parse_consolidated(path)
    if not findings:
        print("ERROR: No findings parsed", file=sys.stderr)
        sys.exit(2)

    # Group by severity
    by_sev = {"critical": [], "high": [], "medium": [], "low": []}
    unknown = []
    for f in findings:
        sev = f["severity"]
        if sev in by_sev:
            by_sev[sev].append(f)
        else:
            unknown.append(f)

    total = len(findings)
    counts = {s: len(fs) for s, fs in by_sev.items()}

    print(f"# Synthesize Input — {total} Findings")
    print(f"# {counts['critical']}C + {counts['high']}H + {counts['medium']}M + {counts['low']}L")
    print(f"# Source: {path.name}")
    print(f"# ALL findings must be addressed. Fix-Scope: NON-NEGOTIABLE (spec-board v5.3).")
    print()

    for sev in ("critical", "high", "medium", "low"):
        fs = by_sev[sev]
        if not fs:
            continue
        print(f"## {sev.upper()} ({len(fs)})")
        print()
        for f in fs:
            print(f"### {f['id']}: {f['title']}")
            # Print first few content lines (issue + fix)
            content = "\n".join(f["lines"]).strip()
            if content:
                # Extract Issue and Fix lines
                for cline in f["lines"]:
                    stripped = cline.strip()
                    if stripped.startswith("- **Issue") or stripped.startswith("- **Fix") or \
                       stripped.startswith("- **Sources") or stripped.startswith("- **Scope"):
                        print(stripped)
            print()

    if unknown:
        print(f"## UNKNOWN SEVERITY ({len(unknown)})")
        for f in unknown:
            print(f"### {f['id']}: {f['title']} (severity: {f['severity'] or 'MISSING'})")
        print()

    print(f"# Total: {total} findings. ALL must be in synthesize prompt.")
    print(f"# Missing any = NON-NEGOTIABLE violation.")


if __name__ == "__main__":
    main()
