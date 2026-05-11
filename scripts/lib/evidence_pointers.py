#!/usr/bin/env python3
"""validate_evidence_pointers.py — Standalone Evidence-Pointer-Validator.

Spec 299 Phase C3 (Schicht 1+2 Backstop). Orchestrator-neutral.

Validation-Mechanik fuer Pointer-Schema (`skills/_protocols/evidence-pointer-
schema.md`). 4 kinds: file_range, grep_match, dir_listing, file_exists.

Re-Use:
- Engine-Check (`workflow_engine.py` `pointer_check`): Library-Import.
- CC-Hook (`evidence-pointer-check.sh`): CLI-Aufruf.
- Pre-commit Check 13 (`pre-commit.sh`): CLI-Aufruf pro staged File-Batch
  (nargs="+" Multi-File-Mode, CC-018 Pass-1-Fix).

Quote-Length-Cap-Metrik: Codepoints (`len(quote)` in Python). Nicht Bytes,
nicht Grapheme-Cluster. Documented decision (ADV-TC-008).

Exit-Codes (CLI):
  0 — alle pointers valid (oder schema_version: 0 = legacy)
  1 — schema_version: 1 + mindestens ein pointer invalid
  2 — parse-error im evidence-block

Usage:
  python3 scripts/validate_evidence_pointers.py <file> [<file>...] \\
      [--strict] [--layout per_finding|top_level|auto] [--repo-root <path>]

Layer-Hinweis (CC-017 Pass-1-Fix Pointer-Note): dieses Modul lebt aktuell
unter `scripts/` (top-level), wird aber von `workflow_engine.py` als Library
importiert (siehe `scripts.lib.yaml_loader`-Pattern). Phase-2-Refactor:
Validator nach `scripts/lib/evidence_pointers.py` schieben, Top-Level-CLI als
duenner Wrapper. Aktueller Status: Pointer-Note, kein Layout-Refactor weil
import-Pfad in Tests + Hook-Skripten an scripts/-Pfad gebunden ist.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:
    print("ERROR: PyYAML required. pip install pyyaml", file=sys.stderr)
    sys.exit(2)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

EXIT_VALID = 0
EXIT_INVALID = 1
EXIT_PARSE_ERROR = 2

QUOTE_MAX_LINES = 3
QUOTE_MAX_CODEPOINTS = 200  # Codepoint metric per ADV-TC-008 decision

VALID_KINDS = ("file_range", "grep_match", "dir_listing", "file_exists")


class EvidenceParseError(Exception):
    """YAML parse-error im evidence-block."""


class EvidenceValidationError(Exception):
    """Validation-Failure (invalid pointer)."""


# ---------------------------------------------------------------------------
# Quote-Length-Cap (§1.3, §6.4)
# ---------------------------------------------------------------------------


def quote_length_cap_ok(quote: str) -> tuple[bool, str]:
    """Enforce <=3 lines AND <=200 codepoints (Spec 299 §1.3).

    Metrik-Decision (ADV-TC-008): Python-Codepoints via `len(quote)`. Nicht
    Bytes, nicht Grapheme-Cluster. Combining-Marks-Bypass (200 Codepoints =
    1 Grapheme) ist akzeptiertes Trade-off.
    """
    lines = quote.splitlines() if quote else [""]
    if len(lines) > QUOTE_MAX_LINES:
        return False, (
            f"quote exceeds cap: {len(lines)} lines (max {QUOTE_MAX_LINES})"
        )
    codepoints = len(quote)
    if codepoints > QUOTE_MAX_CODEPOINTS:
        return False, (
            f"quote exceeds cap: {codepoints} chars (max {QUOTE_MAX_CODEPOINTS})"
        )
    return True, ""


# ---------------------------------------------------------------------------
# expected_count DSL (§6.3)
# ---------------------------------------------------------------------------

_DSL_RE = re.compile(r"^\s*(>=|<=|==|!=|>|<)?\s*(\d+)\s*$")


def _eval_expected_count(actual: int, expr: str | int | None) -> tuple[bool, str]:
    """Evaluate expected_count DSL.

    Grammar:
      EXPR := OPERATOR INTEGER | INTEGER
      OPERATOR := ">=" | "<=" | ">" | "<" | "==" | "!="
    Default ohne expr: ">=1".
    """
    if expr is None:
        op, n = ">=", 1
    elif isinstance(expr, int):
        op, n = "==", expr
    else:
        m = _DSL_RE.match(str(expr))
        if not m:
            return False, f"invalid expected_count DSL: {expr!r}"
        op = m.group(1) or "=="
        n = int(m.group(2))

    if op == ">=":
        ok = actual >= n
    elif op == "<=":
        ok = actual <= n
    elif op == ">":
        ok = actual > n
    elif op == "<":
        ok = actual < n
    elif op == "==":
        ok = actual == n
    elif op == "!=":
        ok = actual != n
    else:
        return False, f"unsupported operator: {op}"

    if not ok:
        return False, f"expected count {op}{n}, got {actual}"
    return True, ""


# ---------------------------------------------------------------------------
# Path-Resolution mit Repo-Boundary (TC-053, ADV-TC-005)
# ---------------------------------------------------------------------------


def _resolve_within_repo(path_str: str, repo_root: str) -> tuple[Path | None, str]:
    """Resolve path repo-relative + assert it stays within repo_root.

    Symlink-aware via Path.resolve(). Out-of-repo (Symlink ODER ../-Traversal)
    → return (None, reason).
    """
    try:
        repo = Path(repo_root).resolve()
        candidate = (repo / path_str).resolve()
    except (OSError, RuntimeError) as exc:
        return None, f"path resolution failed: {exc}"

    try:
        candidate.relative_to(repo)
    except ValueError:
        return None, (
            f"path resolves outside repo boundary: {path_str!r} -> "
            f"{candidate} (repo_root={repo})"
        )
    return candidate, ""


# ---------------------------------------------------------------------------
# Pointer-Validation (Per-Kind Mechanik §1.2)
# ---------------------------------------------------------------------------


def validate_pointer(
    pointer: dict[str, Any],
    repo_root: str,
    _file_cache: dict[str, str] | None = None,
) -> tuple[bool, str]:
    """Single-pointer validation.

    Returns (ok, reason). reason ist leer-string bei ok=True.

    CC-015 (F-CR-006) fix: optional `_file_cache`-Dict reduziert N-fache
    `read_text()`-Calls auf dieselbe target-source. AC-8 verlangt <10%
    Mehrkosten + <5s Worst-Case fuer 50 staged-Files; multi-pointer-Outputs
    auf grosse source-files (z.B. workflow_engine.py ~70k chars) wuerden
    pre-fix linear in N skalieren.
    """
    if not isinstance(pointer, dict):
        return False, f"pointer is not a mapping: {pointer!r}"

    kind = pointer.get("kind")
    if kind not in VALID_KINDS:
        return False, f"unknown kind {kind!r}; valid: {VALID_KINDS}"

    raw_path = pointer.get("path")
    if not raw_path:
        return False, f"kind={kind} requires 'path' field"

    resolved, err = _resolve_within_repo(str(raw_path), repo_root)
    if resolved is None:
        return False, err

    if kind == "file_exists":
        if not resolved.is_file():
            return False, f"file not found: {raw_path}"
        return True, ""

    if kind == "dir_listing":
        if not resolved.is_dir():
            return False, f"directory not found: {raw_path}"
        expected_files = pointer.get("expected_files")
        if not isinstance(expected_files, list) or not expected_files:
            return False, "dir_listing requires non-empty 'expected_files' list"
        for ef in expected_files:
            child = resolved / str(ef)
            if not child.exists():
                return False, f"dir_listing: expected file missing: {ef}"
        return True, ""

    if kind == "file_range":
        if not resolved.is_file():
            return False, f"file not found: {raw_path}"
        lines_spec = pointer.get("lines")
        if not lines_spec:
            return False, "file_range requires 'lines'"
        m = re.match(r"^\s*(\d+)\s*-\s*(\d+)\s*$", str(lines_spec))
        if not m:
            return False, (
                f"file_range 'lines' must be '<start>-<end>': {lines_spec!r}"
            )
        start, end = int(m.group(1)), int(m.group(2))
        if start < 1 or end < start:
            return False, (
                f"file_range 'lines' invalid range: {start}-{end}"
            )
        # CC-015 cache-aware read
        cache_key = str(resolved)
        if _file_cache is not None and cache_key in _file_cache:
            content = _file_cache[cache_key]
        else:
            try:
                content = resolved.read_text(encoding="utf-8", errors="replace")
            except OSError as exc:
                return False, f"file read failed: {exc}"
            if _file_cache is not None:
                _file_cache[cache_key] = content
        total_lines = len(content.splitlines())
        if start > total_lines or end > total_lines:
            return False, (
                f"file_range out of range: lines {start}-{end} exceed "
                f"file linecount {total_lines}"
            )

        quote = pointer.get("quote")
        if quote is None:
            return False, "file_range requires 'quote'"
        cap_ok, cap_msg = quote_length_cap_ok(str(quote))
        if not cap_ok:
            return False, cap_msg

        # grep -F (fixed-string) Quote-Match — beschraenkt auf den Line-Range
        # [start..end] damit `lines:` ein verbindlicher Anker ist und nicht
        # zur Spec-Affirmation degeneriert (Self-Reference im selben File).
        # Pre-Quote-Cap (max 3 Zeilen) macht das tractable.
        all_lines = content.splitlines()
        # 1-indexed range [start..end] inclusive
        target_text = "\n".join(all_lines[start - 1:end])
        quote_str = str(quote)
        if quote_str in target_text:
            return True, ""
        # Multi-line quote via grep -F --null-data fallback ueber den
        # Range-Slice (gleiche Semantik, aber subprocess-Backstop wenn die
        # in-process Substring-Match etwas verfehlt).
        return False, (
            f"quote no match in {raw_path} lines {start}-{end}: "
            f"{quote_str[:60]!r}"
        )

    if kind == "grep_match":
        pattern = pointer.get("pattern")
        if pattern is None:
            return False, "grep_match requires 'pattern'"
        # CC-019 (F-CR-011) fix: file-targets via in-process re.findall —
        # subprocess `grep` cold-start ~5-10ms pro Aufruf, ratio ~10x vs
        # in-process re-Match. dir-recursive bleibt subprocess (rekursive
        # Datei-Iteration in Python ist hier mehr Aufwand als nutzen, und
        # `grep -r` ist hochoptimiert).
        if resolved.is_file():
            try:
                cache_key = str(resolved)
                if _file_cache is not None and cache_key in _file_cache:
                    content = _file_cache[cache_key]
                else:
                    content = resolved.read_text(
                        encoding="utf-8", errors="replace",
                    )
                    if _file_cache is not None:
                        _file_cache[cache_key] = content
                actual = len(re.findall(str(pattern), content, re.MULTILINE))
            except re.error as exc:
                return False, f"invalid regex pattern: {exc}"
            except OSError as exc:
                return False, f"file read failed: {exc}"
        elif resolved.is_dir():
            cmd = ["grep", "-rcE", "--", str(pattern), str(resolved)]
            try:
                result = subprocess.run(  # noqa: S603, S607
                    cmd, capture_output=True, text=True, timeout=10,
                )
            except (OSError, subprocess.TimeoutExpired) as exc:
                return False, f"grep failed: {exc}"
            actual = 0
            for raw_line in result.stdout.splitlines():
                line = raw_line.strip()
                if not line:
                    continue
                if ":" in line:
                    _, _, c = line.rpartition(":")
                    try:
                        actual += int(c)
                    except ValueError:
                        pass
                else:
                    try:
                        actual += int(line)
                    except ValueError:
                        pass
        else:
            return False, f"grep_match: path not found: {raw_path}"
        ok, reason = _eval_expected_count(actual, pointer.get("expected_count"))
        return ok, reason

    return False, f"unsupported kind: {kind}"


# ---------------------------------------------------------------------------
# Frontmatter + Layout-Detection
# ---------------------------------------------------------------------------


# Frontmatter-Marker may have leading whitespace (textwrap.dedent edge-case
# in test-fixtures where embedded YAML has zero indent but surrounding
# `---` markers carry the f-string indent).
_FRONTMATTER_RE = re.compile(r"^[ \t]*---[ \t]*\n(.*?)\n[ \t]*---", re.DOTALL)


def _extract_frontmatter_text(content: str) -> str | None:
    m = _FRONTMATTER_RE.match(content)
    if not m:
        return None
    return m.group(1)


def _parse_frontmatter(content: str) -> dict[str, Any]:
    """Parse YAML-frontmatter; raise EvidenceParseError on YAML-error.

    C2-002 fix (Pass-2): `_normalize_fm_indent` wurde entfernt. Pre-Pass-2 hat
    der Helper mixed-indent silent gefixt — das maskierte kaputtes YAML als
    valides. Real-World mixed-indent Frontmatter ist ein Authoring-Bug und
    sollte als parse-error sichtbar sein, nicht silent normalisiert werden.
    Conftest `_write_top_level_pointer_file` wurde im Pass-1-Fix bereits
    auf explizite 0-indented YAML-Konstruktion umgebaut, Helper war im
    Production-Pfad nicht mehr noetig.
    """
    fm_text = _extract_frontmatter_text(content)
    if fm_text is None:
        return {}
    try:
        data = yaml.safe_load(fm_text)
    except yaml.YAMLError as exc:
        raise EvidenceParseError(f"YAML parse error in frontmatter: {exc}") from exc
    if data is None:
        return {}
    if not isinstance(data, dict):
        raise EvidenceParseError(
            f"frontmatter top-level not a mapping: {type(data).__name__}"
        )
    return data


def _detect_layout(content: str) -> str:
    """Auto-detect: per_finding | top_level.

    CC-010 fix: pre-fix had two bugs.
    1. Frontmatter `^evidence:` regex matched `evidence_layout: per_finding`
       because Python regex `^evidence:` matches the prefix `evidence:` of
       `evidence_layout:`. Fix: anchor on word-boundary or end-of-key by
       requiring optional whitespace + value-or-EOL.
    2. Body offset `len(fm) + 8` is "crude" per the original comment — the
       frontmatter regex matches variable length (leading/trailing whitespace,
       \\r\\n vs \\n). Use the regex match's `.end()` for deterministic offset.
    3. Default fallback was `top_level` which causes per_finding files with
       no detectable evidence-block to error out as "non-empty evidence
       required" instead of the more correct per_finding-style error. Per
       Spec §1.5 per_finding is Default for reviewer-outputs.
    """
    fm_match = _FRONTMATTER_RE.match(content)
    fm_text = fm_match.group(1) if fm_match else ""

    # Frontmatter-EVIDENCE: Match `evidence:` as a STANDALONE YAML KEY,
    # not a prefix of another key. Allow optional value or EOL.
    if re.search(r"(?m)^evidence\s*:(?:\s|$)", fm_text):
        return "top_level"

    # Body: deterministic offset via regex match
    body = content[fm_match.end():] if fm_match else content

    # Per-finding evidence: match BOTH bullet-list-item form `- evidence:` and
    # block-header form `evidence:` per CC-001 fix. Indent-tolerant.
    if re.search(r"(?m)^[ \t]*(?:-\s+)?evidence\s*:(?:\s|$)", body):
        return "per_finding"

    # Default fallback: per_finding (Spec §1.5 — per_finding is the default
    # for reviewer outputs; top_level is the explicit-frontmatter form).
    return "per_finding"


def parse_evidence_block(
    file_path: str,
    layout: str = "auto",
    content: str | None = None,
) -> list[dict[str, Any]]:
    """Extract pointer-list from file. Layout: per_finding | top_level | auto.

    Task 301 C2-005 fix: optional pre-loaded `content` Argument konsolidiert
    den File-Read mit `validate_file`. Pre-fix: validate_file rief get_schema_version
    (1 Read) + parse_evidence_block (2. Read). Mit `content` parameter wird
    parse_evidence_block ohne Disk-IO aufgerufen — single-read-pattern Spec
    §6.5 wirklich erfuellt.

    Raises EvidenceParseError on YAML-error.
    """
    if content is None:
        try:
            content = Path(file_path).read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            raise EvidenceParseError(f"file read failed: {exc}") from exc

    if layout == "auto":
        layout = _detect_layout(content)

    pointers: list[dict[str, Any]] = []

    if layout == "top_level":
        fm = _parse_frontmatter(content)
        ev = fm.get("evidence")
        if isinstance(ev, list):
            pointers.extend([p for p in ev if isinstance(p, dict)])
        return pointers

    if layout == "per_finding":
        # Greedy grep: find each `evidence:` block + parse following YAML-list
        # lines until indent level drops or non-list line found.
        #
        # Match BOTH forms (CC-001 fix, Spec 299 §1.5 + reviewer-protocols):
        #   1. `<indent>evidence:` (block-header form)
        #   2. `<indent>- evidence:` (markdown-list-item form, prescribed by
        #      spec/code/ux-reviewer-protocol.md "Output-Format" sections)
        # Real-formatted reviewer-outputs use form (2). Pre-fix the regex
        # rejected form (2) silently which made per_finding-defense
        # structurally ineffective — see verdict CC-001 / F-CR-002+F-CA-001.
        #
        # Empty-evidence detection (CC-009 fix): also match
        #   `evidence: ~` (YAML null), `evidence: []` (empty list),
        #   `- evidence: ~`, `- evidence: []`
        # and emit a parse-error so per-finding null-evidence is not silent.
        body_lines = content.splitlines()
        # Block-header / list-item header (no value on same line)
        header_re = re.compile(r"^(\s*)(?:-\s+)?evidence:\s*$")
        # Inline-empty form: explicit null/empty-list on same line
        inline_empty_re = re.compile(
            r"^(\s*)(?:-\s+)?evidence:\s*(?:~|\[\s*\])\s*$"
        )
        i = 0
        while i < len(body_lines):
            line = body_lines[i]

            # Inline-empty per-finding evidence (CC-009): treat as parse-error
            # so AC-3 Test-6 semantics (schema_version: 1 + empty evidence
            # → fail) extends from top_level to per_finding granularity.
            ie = inline_empty_re.match(line)
            if ie:
                raise EvidenceParseError(
                    "per_finding evidence is null/empty on a finding "
                    f"(line {i + 1}): {line.strip()!r} — schema_version: 1 "
                    "requires non-empty evidence per finding"
                )

            m = header_re.match(line)
            if m:
                indent_str = m.group(1)
                base_indent = len(indent_str)
                # YAML-Reconstruction-Indent: bei list-item-form `- evidence:`
                # liegen die child-keys 4 Spaces eingerueckt (2 fuer "- "
                # plus 2 fuer YAML-list-item-children). Bei block-form
                # `evidence:` liegen sie 2 Spaces eingerueckt.
                is_list_item = line.lstrip(" ").startswith("- ")
                trim = base_indent + (4 if is_list_item else 2)
                # Collect continuation lines (more indented than base_indent
                # for block-form; more indented than base_indent+2 for
                # list-item-form, since `- ` is its own column).
                continuation_threshold = base_indent + (2 if is_list_item else 0)
                block_lines: list[str] = []
                j = i + 1
                while j < len(body_lines):
                    nxt = body_lines[j]
                    if not nxt.strip():
                        block_lines.append("")
                        j += 1
                        continue
                    leading = len(nxt) - len(nxt.lstrip(" "))
                    if leading <= continuation_threshold:
                        break
                    block_lines.append(nxt)
                    j += 1
                # Re-construct YAML-snippet "evidence:\n<block>"
                # Trim the common indent from block_lines.
                norm = "evidence:\n" + "\n".join(
                    bl[trim:] if len(bl) >= trim else bl.lstrip() for bl in block_lines
                )
                try:
                    parsed = yaml.safe_load(norm)
                except yaml.YAMLError as exc:
                    raise EvidenceParseError(
                        f"YAML parse error in per_finding evidence block: {exc}"
                    ) from exc
                if isinstance(parsed, dict):
                    ev_list = parsed.get("evidence")
                    if isinstance(ev_list, list):
                        pointers.extend(
                            [p for p in ev_list if isinstance(p, dict)]
                        )
                i = j
                continue
            i += 1
        return pointers

    raise EvidenceParseError(f"unknown layout: {layout}")


# Task 301 C2-006 fix: Per-Finding-Counter — `### F-<TAG>-<NNN>` Heading-Pattern
# matched zu Findings die einen evidence-Block haben sollten (Spec §2.1 Schritt 4).
# Pattern: `### F-<TAG>-<NNN>` mit optionalen Trailing-Tokens (Severity-Tag,
# Doppelpunkt-Description). Beispiele:
#   ### F-CR2-001
#   ### F-CA-PASS3-001: Validator-Asymmetrie
#   ### F-CF-008 [LOW]
_FINDING_HEADING_RE = re.compile(r"(?m)^###\s+F-[A-Z][A-Z0-9]*-\d+\b")


def count_finding_headings(content: str) -> int:
    """Task 301 C2-006: Count `### F-<TAG>-<NNN>` finding-headings in body.

    Returns count of finding-headings (Spec §2.1 Schritt 4 — pro Finding ein
    evidence-Block). Caller compares against pointer-count (per_finding-Layout)
    to detect findings WITHOUT evidence-Block (silent-pass pre-fix).
    """
    return len(_FINDING_HEADING_RE.findall(content))


def get_schema_version(file_path: str) -> int | None:
    """Read schema_version from top-level frontmatter. None wenn nicht gesetzt.

    NOTE: propagiert EvidenceParseError nach oben damit validate_file CLI
    exit 2 emit kann. Wenn der Frontmatter selbst kaputt ist, ist das ein
    parse-error, kein "legacy".
    """
    try:
        content = Path(file_path).read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    fm = _parse_frontmatter(content)  # raises EvidenceParseError
    sv = fm.get("schema_version")
    if isinstance(sv, int):
        return sv
    if isinstance(sv, str) and sv.isdigit():
        return int(sv)
    return None


# ---------------------------------------------------------------------------
# File-level Validation API
# ---------------------------------------------------------------------------


def _detect_repo_root(file_path: Path) -> str | None:
    """CC-002 fix: walk up from file_path looking for .git/ or pyproject.toml.

    Pre-fix the CLI default was `parent of file`, which made every
    repo-relative pointer in `docs/reviews/<dir>/foo.md` resolve to
    `<repo>/docs/reviews/<dir>/<pointer-path>` — file-not-found and
    ~100% false-positive WARN-Rate in pre-commit Check 13 + CC-Hook.

    Walk-up looks for .git/ first, then pyproject.toml as fallback.
    Returns absolute path string or None when nothing found (caller falls
    back to file.parent for backwards compat).
    """
    try:
        cur = file_path.resolve().parent
    except (OSError, RuntimeError):
        return None
    last = None
    # Bound the walk by the filesystem root
    while cur != last:
        if (cur / ".git").exists():
            return str(cur)
        if (cur / "pyproject.toml").is_file():
            return str(cur)
        last = cur
        cur = cur.parent
    return None


def validate_file(
    file_path: str,
    layout: str = "auto",
    repo_root: str | None = None,
) -> tuple[int, list[str]]:
    """Returns (exit_code, error_messages). Exit_code per CLI-Spec.

    Pre-condition: file_path muss existieren. Bei OSError → exit 2.

    Legacy-Pfad: wenn schema_version: 0 ODER fehlend → exit 0 (silent skip).

    repo_root resolution (CC-002 fix):
      1. Explicit caller-provided repo_root (Engine-Library-Import path) wins.
      2. CLI default: walk up from file_path for .git/ or pyproject.toml.
      3. Last resort fallback: parent-of-file (preserves pre-fix behaviour
         for tests that explicitly want CWD-as-repo semantics).
    """
    p = Path(file_path)
    if not p.is_file():
        return EXIT_PARSE_ERROR, [f"file not found: {file_path}"]

    if repo_root:
        repo = repo_root
    else:
        detected = _detect_repo_root(p)
        repo = detected if detected else str(p.parent.resolve())

    # CC-020 (F-CA-009) Pass-1-Fix + C2-005 Pass-3-Fix: single-read-pattern.
    # Pre-fix: get_schema_version liest, validate_file liest, parse_evidence_block
    # liest noch einmal — 3 Reads mit Race-Window. Wir lesen einmal und reichen
    # `content` an parse_evidence_block durch (Task 301 C2-005).
    try:
        content = p.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        return EXIT_PARSE_ERROR, [f"file read failed: {exc}"]
    try:
        fm = _parse_frontmatter(content)
    except EvidenceParseError as exc:
        return EXIT_PARSE_ERROR, [f"parse-error: yaml frontmatter: {exc}"]

    # Task 301 F-CA-PASS3-001 fix: Validator-Acceptor schmaeler — nur exakt
    # int(1) oder string `"1"`. Pre-fix akzeptierte `isdigit()` (also "01" als
    # sv=1) was Pre-Filter-Strictness-Drift produziert (Filter rejected "01",
    # Validator akzeptiert). Plus float (z.B. `schema_version: 1.0`) wurde
    # silent-skipped als legacy ohne Author-Signal — schlimmer als rejected.
    # Fix: schmal akzeptieren + explizit ablehnen mit Author-Signal.
    sv_raw = fm.get("schema_version")
    if isinstance(sv_raw, bool):
        # bool ist isinstance(int) True in Python — explizit ausschliessen
        return EXIT_INVALID, [
            f"unsupported schema_version form: {sv_raw!r} "
            f"(expect int 1 or string '1', not bool)"
        ]
    if isinstance(sv_raw, int):
        sv = sv_raw
    elif isinstance(sv_raw, str):
        if sv_raw == "1":
            sv = 1
        elif sv_raw == "0":
            sv = 0
        else:
            # Pre-fix akzeptierte sv_raw.isdigit() — also "01", "001", etc.
            # Filter (pre-commit.sh:498) rejected "01" weil End-Anchor `1` strict.
            # Asymmetrie schmaeler machen statt erweitern: explizit ablehnen
            # damit Author-Signal entsteht ("schreibe `1` statt `01`").
            return EXIT_INVALID, [
                f"unsupported schema_version form: {sv_raw!r} "
                f"(expect int 1 or string '1', got string)"
            ]
    elif sv_raw is None:
        sv = None
    else:
        # Float (z.B. 1.0), list, dict, etc. — pre-fix silent-skip (sv=None).
        # Author-Signal: explicit reject damit Reviewer sieht dass `1.0` nicht
        # als v1 interpretiert wird (Versionsschema-Drift).
        return EXIT_INVALID, [
            f"unsupported schema_version form: {sv_raw!r} "
            f"(expect int 1 or string '1', got {type(sv_raw).__name__})"
        ]

    if sv is None or sv == 0:
        # Legacy: silent skip
        return EXIT_VALID, []

    if sv != 1:
        return EXIT_INVALID, [
            f"unsupported schema_version: {sv} (only 0 + 1 known in v1)"
        ]

    # schema_version: 1 — full validation. C2-005 Pass-3 fix: pass pre-loaded
    # `content` an parse_evidence_block damit kein 2. File-Read passiert
    # (single-read-pattern Spec §6.5 wirklich erfuellt).
    try:
        pointers = parse_evidence_block(file_path, layout, content=content)
    except EvidenceParseError as exc:
        return EXIT_PARSE_ERROR, [f"parse-error: {exc}"]

    if not pointers:
        # schema_version: 1 + leeres/missing evidence → invalid
        return EXIT_INVALID, [
            "non-empty evidence required for schema_version: 1"
        ]

    # Task 301 C2-006 fix: Per-Finding-Counter (CC-009 Option b).
    # Layout per_finding: pro `### F-<TAG>-<NNN>` Heading erwarten wir
    # mindestens ein evidence-Block. Pre-fix: Findings ohne evidence-Block
    # passieren silent (Validator zaehlt Pointer, nicht Findings).
    # Heuristic-Check: wenn finding-Headings > pointer-blocks gefunden wurden,
    # liegt mindestens ein Finding ohne evidence-Block vor.
    detected_layout = layout if layout != "auto" else _detect_layout(content)
    if detected_layout == "per_finding":
        finding_count = count_finding_headings(content)
        # parse_evidence_block produziert pointer-list (jeder Pointer = 1 Eintrag).
        # Per-Finding-Block-Counter: zaehle distinct evidence-Block-Headers im Body
        # (das Aequivalent zu Findings die einen Block haben).
        body = content
        fm_match = _FRONTMATTER_RE.match(content)
        if fm_match:
            body = content[fm_match.end():]
        block_count = len(re.findall(
            r"(?m)^[ \t]*(?:-\s+)?evidence\s*:(?:\s|$)", body,
        ))
        if finding_count > 0 and block_count < finding_count:
            return EXIT_INVALID, [
                f"per_finding evidence-Block-Counter: {finding_count} finding-"
                f"headings (`### F-...`) gefunden, aber nur {block_count} "
                f"evidence-Bloecke. Spec §2.1 Schritt 4 verlangt einen "
                f"evidence-Block PRO Finding."
            ]

    errors: list[str] = []
    file_exists_only = True
    # CC-015 cache: shared dict across pointers in this file
    file_cache: dict[str, str] = {}
    for idx, pointer in enumerate(pointers, start=1):
        if pointer.get("kind") != "file_exists":
            file_exists_only = False
        ok, reason = validate_pointer(pointer, repo, _file_cache=file_cache)
        if not ok:
            errors.append(f"pointer {idx}: fail — {reason}")
        else:
            errors.append(f"pointer {idx}: ok")

    if any("fail" in e for e in errors):
        return EXIT_INVALID, errors

    # All-pointers-pass: emit Discipline-WARN if file_exists-only (F-I-015)
    if file_exists_only and len(pointers) >= 1:
        errors.append(
            "WARN discipline F-I-015: all pointers are kind=file_exists "
            "(trivial). Tier-1-Reviewer should include at least one "
            "non-trivial pointer (file_range or grep_match) per finding."
        )

    return EXIT_VALID, errors


# ---------------------------------------------------------------------------
# CLI Entrypoint
# ---------------------------------------------------------------------------


def _main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Validate evidence pointers per Spec 299 schema.",
    )
    # CC-018 fix: nargs="+" so pre-commit Check 13 can validate N staged
    # files in 1 subprocess instead of N — saves N-1 python cold-starts.
    parser.add_argument(
        "files", nargs="+",
        help="Output-File(s) mit evidence-Block",
    )
    parser.add_argument(
        "--strict", action="store_true",
        help="Reserved for future strict-mode (currently no-op).",
    )
    parser.add_argument(
        "--layout", choices=("per_finding", "top_level", "auto"),
        default="auto",
    )
    parser.add_argument(
        "--repo-root", default=None,
        help="Repo-root for path-boundary check. CC-002: default walks up "
             "from <file> looking for .git or pyproject.toml; falls back to "
             "parent-of-file. Override is the most reliable path.",
    )

    args = parser.parse_args(argv)

    overall_exit = EXIT_VALID
    for file_path in args.files:
        exit_code, messages = validate_file(
            file_path, layout=args.layout, repo_root=args.repo_root,
        )

        # In multi-file mode prefix output with the file path so users can
        # see which file produced which result.
        if len(args.files) > 1:
            header_stream = sys.stderr if exit_code != EXIT_VALID else sys.stdout
            print(f"=== {file_path} (exit {exit_code}) ===", file=header_stream)

        out_stream = sys.stderr if exit_code != EXIT_VALID else sys.stdout
        for msg in messages:
            if msg.startswith("WARN"):
                print(msg, file=sys.stderr)
            else:
                print(msg, file=out_stream)

        # Aggregate exit-code: highest severity wins. 2 (parse) > 1 (invalid)
        # > 0 (valid). This keeps shell-callers' single-rc semantics.
        if exit_code > overall_exit:
            overall_exit = exit_code

    return overall_exit


if __name__ == "__main__":
    sys.exit(_main())
