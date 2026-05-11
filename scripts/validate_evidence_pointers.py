#!/usr/bin/env python3
"""validate_evidence_pointers.py — CLI wrapper for scripts.lib.evidence_pointers.

Spec 299 Task 301 C2-007 fix: Validator-Modul ist nach `scripts/lib/`
gewandert (Layer-Discipline analog `scripts.lib.yaml_loader`). Dieses
File bleibt als CLI-Wrapper + Backwards-Compat-Shim (Top-Level-Imports
`from scripts.validate_evidence_pointers import ...` weiter funktional)
damit:
  - Pre-commit + Hook-Skripte (orchestrators/claude-code/hooks/) unverandert
    `python3 scripts/validate_evidence_pointers.py` aufrufen koennen.
  - Tests die `from scripts.validate_evidence_pointers import X` nutzen
    weiter laufen (keine Bulk-Test-Aenderung in Task 301 noetig).
  - Engine-Library-Import-Pfad weiter funktional bleibt.

Phase-3-Refactor (separater Task): Konsumenten direkt auf
`scripts.lib.evidence_pointers` umstellen, Wrapper droppen.

Spec: docs/specs/299-fabrication-mitigation.md §6
"""

from __future__ import annotations

import sys
from pathlib import Path

# Allow running both as `python3 scripts/validate_evidence_pointers.py` (cwd=
# repo root) AND from external cwd (cwd=tmp_dir, e.g. test fixtures invoking
# the CLI from a tempdir). This sys.path insertion targets the framework
# checkout (where scripts/ lives), analog to workflow_engine.py:51-52.
_FRAMEWORK_ROOT = Path(__file__).resolve().parent.parent
if str(_FRAMEWORK_ROOT) not in sys.path:
    sys.path.insert(0, str(_FRAMEWORK_ROOT))

# Re-export full public API from new home so that
# `from scripts.validate_evidence_pointers import X` keeps working.
from scripts.lib.evidence_pointers import (  # noqa: E402, F401
    EXIT_INVALID,
    EXIT_PARSE_ERROR,
    EXIT_VALID,
    QUOTE_MAX_CODEPOINTS,
    QUOTE_MAX_LINES,
    VALID_KINDS,
    EvidenceParseError,
    EvidenceValidationError,
    _detect_layout,
    _detect_repo_root,
    _DSL_RE,
    _eval_expected_count,
    _extract_frontmatter_text,
    _FINDING_HEADING_RE,
    _FRONTMATTER_RE,
    _parse_frontmatter,
    _resolve_within_repo,
    count_finding_headings,
    get_schema_version,
    parse_evidence_block,
    quote_length_cap_ok,
    validate_file,
    validate_pointer,
)
from scripts.lib.evidence_pointers import _main as _delegate_main  # noqa: E402


def _main(argv: list[str] | None = None) -> int:
    return _delegate_main(argv)


if __name__ == "__main__":
    sys.exit(_main())
