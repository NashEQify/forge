#!/usr/bin/env python3
"""validate_evidence_pointers.py — Standalone Evidence-Pointer-Validator.

Schicht 1+2 Backstop. Orchestrator-neutral.

Validation-Mechanik fuer Pointer-Schema (`skills/_protocols/evidence-pointer-
schema.md`). 4 kinds: file_range, grep_match, dir_listing, file_exists.

Re-Use:
- Engine-Check (`workflow_engine.py` `pointer_check`): Library-Import.
- Pre-commit Check 5 SOURCE-VERIFICATION (`pre-commit.sh`): CLI-Aufruf
  pro staged File-Batch (nargs="+" Multi-File-Mode).

Quote-Length-Cap-Metrik: Codepoints (`len(quote)` in Python). Nicht Bytes,
nicht Grapheme-Cluster. Documented decision.

Exit-Codes (CLI):
  0 — alle pointers valid (oder schema_version: 0 = legacy)
  1 — schema_version: 1 + mindestens ein pointer invalid
  2 — parse-error im evidence-block

Usage:
  python3 scripts/validate_evidence_pointers.py <file> [<file>...] \\
      [--strict] [--layout per_finding|top_level|auto] [--repo-root <path>]

Layer-Hinweis (Pointer-Note): dieses Modul lebt aktuell
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
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Literal, overload

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


class PointerFault(Enum):
    """Why a pointer did not pass.

    CONTENT: the pointer was well-formed and the cited content did not hold.
    FORM: the pointer cannot be evaluated as written (missing field, unknown
    kind, bad regex, path outside the repository, quote over the cap).
    """

    CONTENT = "content"
    FORM = "form"


# ---------------------------------------------------------------------------
# Quote-Length-Cap (§1.3, §6.4)
# ---------------------------------------------------------------------------


def quote_length_cap_ok(quote: str) -> tuple[bool, str]:
    """Enforce <=3 lines AND <=200 codepoints (Spec §1.3).

    Metrik-Decision: Python-Codepoints via `len(quote)`. Nicht
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
# Path-Resolution mit Repo-Boundary
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


@overload
def validate_pointer(
    pointer: dict[str, Any],
    repo_root: str,
    _file_cache: dict[str, str] | None = None,
    *,
    check_cap: bool = True,
    with_fault: Literal[False] = False,
) -> tuple[bool, str]: ...


@overload
def validate_pointer(
    pointer: dict[str, Any],
    repo_root: str,
    _file_cache: dict[str, str] | None = None,
    *,
    check_cap: bool = True,
    with_fault: Literal[True],
) -> tuple[bool, str, PointerFault | None]: ...


def validate_pointer(
    pointer: dict[str, Any],
    repo_root: str,
    _file_cache: dict[str, str] | None = None,
    *,
    check_cap: bool = True,
    with_fault: bool = False,
) -> tuple[bool, str] | tuple[bool, str, PointerFault | None]:
    """Single-pointer validation.

    Returns (ok, reason); reason is "" when ok=True. ``with_fault=True``
    returns (ok, reason, fault): fault is None when ok=True,
    PointerFault.CONTENT when the pointer was well-formed and the
    cited content did not hold (file or directory not found, expected file
    missing, quote no match, lines outside the file, expected_count not met,
    path not found, file read or grep failed); PointerFault.FORM for every
    other reason (missing or malformed field, unknown kind, bad regex, path
    outside the repository, quote over the cap).

    ``check_cap=False`` skips the quote-length cap so a long or multi-line
    quote is still matched (the review reader resolves every quote).

    optional `_file_cache`-Dict reduziert N-fache
    `read_text()`-Calls auf dieselbe target-source. AC-8 verlangt <10%
    Mehrkosten + <5s Worst-Case fuer 50 staged-Files; multi-pointer-Outputs
    auf grosse source-files (z.B. workflow_engine.py ~70k chars) wuerden
    pre-fix linear in N skalieren.
    """
    ok, reason, fault = _pointer_verdict(
        pointer, repo_root, _file_cache, check_cap=check_cap
    )
    return (ok, reason, fault) if with_fault else (ok, reason)


def _pointer_verdict(
    pointer: dict[str, Any],
    repo_root: str,
    _file_cache: dict[str, str] | None,
    *,
    check_cap: bool,
) -> tuple[bool, str, PointerFault | None]:
    """validate_pointer with its fault class (see there)."""
    def form(reason: str) -> tuple[bool, str, PointerFault]:
        return False, reason, PointerFault.FORM

    def content(reason: str) -> tuple[bool, str, PointerFault]:
        return False, reason, PointerFault.CONTENT

    if not isinstance(pointer, dict):
        return form(f"pointer is not a mapping: {pointer!r}")

    kind = pointer.get("kind")
    if kind not in VALID_KINDS:
        return form(f"unknown kind {kind!r}; valid: {VALID_KINDS}")

    raw_path = pointer.get("path")
    if not raw_path:
        return form(f"kind={kind} requires 'path' field")

    resolved, err = _resolve_within_repo(str(raw_path), repo_root)
    if resolved is None:
        return form(err)

    if kind == "file_exists":
        if not resolved.is_file():
            return content(f"file not found: {raw_path}")
        return True, "", None

    if kind == "dir_listing":
        if not resolved.is_dir():
            return content(f"directory not found: {raw_path}")
        expected_files = pointer.get("expected_files")
        if not isinstance(expected_files, list) or not expected_files:
            return form("dir_listing requires non-empty 'expected_files' list")
        for ef in expected_files:
            child = resolved / str(ef)
            if not child.exists():
                return content(f"dir_listing: expected file missing: {ef}")
        return True, "", None

    if kind == "file_range":
        if not resolved.is_file():
            return content(f"file not found: {raw_path}")
        lines_spec = pointer.get("lines")
        if not lines_spec:
            return form("file_range requires 'lines'")
        m = re.match(r"^\s*(\d+)\s*-\s*(\d+)\s*$", str(lines_spec))
        if not m:
            return form(
                f"file_range 'lines' must be '<start>-<end>': {lines_spec!r}"
            )
        start, end = int(m.group(1)), int(m.group(2))
        if start < 1 or end < start:
            return form(
                f"file_range 'lines' invalid range: {start}-{end}"
            )
        # cache-aware read
        cache_key = str(resolved)
        if _file_cache is not None and cache_key in _file_cache:
            text = _file_cache[cache_key]
        else:
            try:
                text = resolved.read_text(encoding="utf-8", errors="replace")
            except OSError as exc:
                return content(f"file read failed: {exc}")
            if _file_cache is not None:
                _file_cache[cache_key] = text
        total_lines = len(text.splitlines())
        if start > total_lines or end > total_lines:
            return content(
                f"file_range out of range: lines {start}-{end} exceed "
                f"file linecount {total_lines}"
            )

        quote = pointer.get("quote")
        if quote is None:
            return form("file_range requires 'quote'")
        if check_cap:
            cap_ok, cap_msg = quote_length_cap_ok(str(quote))
            if not cap_ok:
                return form(cap_msg)

        # grep -F (fixed-string) Quote-Match — beschraenkt auf den Line-Range
        # [start..end] damit `lines:` ein verbindlicher Anker ist und nicht
        # zur Spec-Affirmation degeneriert (Self-Reference im selben File).
        # Pre-Quote-Cap (max 3 Zeilen) macht das tractable.
        all_lines = text.splitlines()
        # 1-indexed range [start..end] inclusive
        target_text = "\n".join(all_lines[start - 1:end])
        quote_str = str(quote)
        if quote_str in target_text:
            return True, "", None
        return content(
            f"quote no match in {raw_path} lines {start}-{end}: "
            f"{quote_str[:60]!r}"
        )

    if kind == "grep_match":
        pattern = pointer.get("pattern")
        if pattern is None:
            return form("grep_match requires 'pattern'")
        # file-targets via in-process re.findall —
        # subprocess `grep` cold-start ~5-10ms pro Aufruf, ratio ~10x vs
        # in-process re-Match. dir-recursive bleibt subprocess (rekursive
        # Datei-Iteration in Python ist hier mehr Aufwand als nutzen, und
        # `grep -r` ist hochoptimiert).
        if resolved.is_file():
            try:
                cache_key = str(resolved)
                if _file_cache is not None and cache_key in _file_cache:
                    text = _file_cache[cache_key]
                else:
                    text = resolved.read_text(
                        encoding="utf-8", errors="replace",
                    )
                    if _file_cache is not None:
                        _file_cache[cache_key] = text
                actual = len(re.findall(str(pattern), text, re.MULTILINE))
            except re.error as exc:
                return form(f"invalid regex pattern: {exc}")
            except OSError as exc:
                return content(f"file read failed: {exc}")
        elif resolved.is_dir():
            cmd = ["grep", "-rcE", "--", str(pattern), str(resolved)]
            try:
                result = subprocess.run(  # noqa: S603, S607
                    cmd, capture_output=True, text=True, timeout=10,
                )
            except (OSError, subprocess.TimeoutExpired) as exc:
                return content(f"grep failed: {exc}")
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
            return content(f"grep_match: path not found: {raw_path}")
        expr = pointer.get("expected_count")
        if expr is not None and not isinstance(expr, int) and not _DSL_RE.match(str(expr)):
            return form(f"invalid expected_count DSL: {expr!r}")
        ok, reason = _eval_expected_count(actual, expr)
        return (True, "", None) if ok else content(reason)

    return form(f"unsupported kind: {kind}")


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

    `_normalize_fm_indent` wurde entfernt. Pre-fix hat
    der Helper mixed-indent silent gefixt — das maskierte kaputtes YAML als
    valides. Real-World mixed-indent Frontmatter ist ein Authoring-Bug und
    sollte als parse-error sichtbar sein, nicht silent normalisiert werden.
    Conftest `_write_top_level_pointer_file` wurde bereits
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

    pre-fix had two bugs.
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
    # block-header form `evidence:`. Indent-tolerant.
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

    optional pre-loaded `content` Argument konsolidiert
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
        # Match BOTH forms (Spec §1.5 + reviewer-protocols):
        #   1. `<indent>evidence:` (block-header form)
        #   2. `<indent>- evidence:` (markdown-list-item form, prescribed by
        #      spec/code/ux-reviewer-protocol.md "Output-Format" sections)
        # Real-formatted reviewer-outputs use form (2). Pre-fix the regex
        # rejected form (2) silently which made per_finding-defense
        # structurally ineffective.
        #
        # Empty-evidence detection: also match
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

            # Inline-empty per-finding evidence: treat as parse-error
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


# Per-Finding-Counter — `### F-<TAG>-<NNN>` Heading-Pattern
# matched zu Findings die einen evidence-Block haben sollten (Spec §2.1 Schritt 4).
# Pattern: `### F-<TAG>-<NNN>` mit optionalen Trailing-Tokens (Severity-Tag,
# Doppelpunkt-Description). Beispiele:
#   ### F-CR2-001
#   ### F-CA-PASS3-001: Validator-Asymmetrie
#   ### F-CF-008 [LOW]
_FINDING_HEADING_RE = re.compile(r"(?m)^###\s+F-[A-Z][A-Z0-9]*-\d+\b")


def count_finding_headings(content: str) -> int:
    """Count `### F-<TAG>-<NNN>` finding-headings in body.

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
    """walk up from file_path looking for .git/ or pyproject.toml.

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


@dataclass(frozen=True)
class ValidationResult:
    """Schema and validation outcome from one supplied report view."""

    schema_version: int | None
    exit_code: int
    messages: list[str]


@dataclass
class _Finding:
    identifier: str
    line: int
    depth: int
    pointers: list[dict[str, Any]] = field(default_factory=list)

    @property
    def location(self) -> str:
        return f"{self.identifier} (heading line {self.line})"


_ATX_RE = re.compile(r"^ {0,3}(#{1,6})(?:[ \t]+|$)(.*)$")
_IDENTIFIER_RE = re.compile(r"(?:F|UX)-[A-Z][A-Z0-9]*(?:-[A-Z][A-Z0-9]*)*-[0-9]+\b")
_FINDING_LIKE_RE = re.compile(r"(?:F-|UX-|C[0-9]+-[0-9]+)")
_FENCE_RE = re.compile(r"^ {0,3}(`{3,}|~{3,})(.*)$")
_EVIDENCE_RE = re.compile(r"^([ \t]*)(-[ \t]+)?evidence[ \t]*:(.*)$")


#: Reader mode only: an evidence block that exists but was not read as YAML
#: (a parse failure, or evidence inside a fence that is not ``yaml``/``yml``).
_UNPARSED = object()
_YAML_INFO = frozenset({"yaml", "yml"})


def _scan_findings(
    content: str,
    *,
    reader: bool = False,
) -> tuple[list[_Finding], list[tuple[_Finding | None, int, Any]], list[str]]:
    """Scan body boundaries, owners and examples together; retain every block.

    ``reader`` (``review_evidence`` only) keeps the heading, fence and ownership
    rules with two differences: a block that fails to parse is reported in
    ``errors`` and retained as ``_UNPARSED`` while the scan continues, and an
    ``evidence:`` block inside a ``yaml``/``yml`` fence is a body block of the
    enclosing finding. Evidence inside any other fence is retained as
    ``_UNPARSED`` so its finding still counts as carrying an evidence block.
    """
    lines = content.splitlines()
    frontmatter = _FRONTMATTER_RE.match(content)
    i = content[: frontmatter.end()].count("\n") + 1 if frontmatter else 0
    findings: list[_Finding] = []
    stack: list[_Finding] = []
    blocks: list[tuple[_Finding | None, int, Any]] = []
    errors: list[str] = []
    identifiers: set[str] = set()
    fence_char = ""
    fence_length = 0
    fence_yaml = False
    while i < len(lines):
        line = lines[i]
        fence = _FENCE_RE.match(line)
        if fence_char:
            if (
                fence
                and fence.group(1)[0] == fence_char
                and len(fence.group(1)) >= fence_length
                and not fence.group(2).strip()
            ):
                fence_char = ""
                i += 1
                continue
            if not (reader and _EVIDENCE_RE.match(line)):
                i += 1
                continue
            if not fence_yaml:
                blocks.append((stack[-1] if stack else None, i + 1, _UNPARSED))
                i += 1
                continue
            # A yaml-fenced evidence block is read like a body block below.
        elif fence:
            fence_char, fence_length = fence.group(1)[0], len(fence.group(1))
            info = fence.group(2).split()
            fence_yaml = reader and bool(info) and info[0].lower() in _YAML_INFO
            i += 1
            continue
        else:
            heading = _ATX_RE.match(line)
            if heading:
                depth = len(heading.group(1))
                title = heading.group(2).strip()
                while stack and stack[-1].depth >= depth:
                    stack.pop()
                identifier = _IDENTIFIER_RE.match(title)
                if identifier and 2 <= depth <= 4:
                    finding = _Finding(identifier.group(), i + 1, depth)
                    if finding.identifier in identifiers:
                        errors.append(f"{finding.location}: duplicate finding identifier")
                    identifiers.add(finding.identifier)
                    findings.append(finding)
                    stack.append(finding)
                elif _FINDING_LIKE_RE.match(title):
                    errors.append(
                        f"line {i + 1}: unsupported finding heading {title!r}; use an F/UX identifier at ATX depth 2–4"
                    )
                i += 1
                continue
        evidence = _EVIDENCE_RE.match(line)
        if not evidence:
            i += 1
            continue
        owner = stack[-1] if stack else None
        block_line = i + 1
        base_indent = len(evidence.group(1)) + (2 if evidence.group(2) else 0)
        snippet = ["evidence:" + evidence.group(3)]
        i += 1
        while i < len(lines):
            following = lines[i]
            # Indented '#' lines are YAML comments. Report headings stop at
            # the indentation boundary below; fenced examples remain separate.
            if _FENCE_RE.match(following):
                break
            if (
                following.strip()
                and len(following) - len(following.lstrip(" ")) <= base_indent
            ):
                break
            heading = _ATX_RE.match(following)
            if heading and _FINDING_LIKE_RE.match(heading.group(2).strip()):
                errors.append(
                    f"line {i + 1}: ambiguous finding-like heading {heading.group(2).strip()!r} "
                    "inside evidence; move the report heading outside the YAML indentation, "
                    "or rewrite the comment so it does not resemble a finding heading"
                )
            snippet.append(following[base_indent:] if following.strip() else "")
            i += 1
        location = owner.location if owner else f"line {block_line} (no finding owner)"
        try:
            parsed = yaml.safe_load("\n".join(snippet))
        except yaml.YAMLError as exc:
            if not reader:
                raise EvidenceParseError(
                    f"{location}, evidence line {block_line}: malformed YAML: {exc}"
                ) from exc
            parsed = exc
        except ValueError as exc:  # e.g. an impossible date; strict mode keeps raising
            if not reader:
                raise
            parsed = exc
        if reader and not (isinstance(parsed, dict) and "evidence" in parsed):
            detail = f"malformed YAML: {parsed}" if isinstance(parsed, Exception) else "unreadable block"
            errors.append(f"{location}, evidence line {block_line}: {detail}")
            blocks.append((owner, block_line, _UNPARSED))
            continue
        blocks.append((owner, block_line, parsed["evidence"]))
    return findings, blocks, errors


@dataclass
class ReviewEvidence:
    """What a review report's evidence established at adoption.

    ``failures`` refuse adoption (a well-formed pointer whose cited content did
    not hold, a form-faulted pointer whose quote is absent from the file it
    cites, or a recognized finding without any evidence block);
    ``diagnostics`` are retained for Buddy's decision; ``verified`` counts the
    pointers that passed, including a form-faulted one whose quote was found.
    """

    failures: list[str] = field(default_factory=list)
    diagnostics: list[str] = field(default_factory=list)
    verified: int = 0


def review_evidence(content: str, *, repo_root: str) -> ReviewEvidence:
    """Resolve every parseable evidence pointer of one review report.

    Never raises for malformed report content: form problems are diagnostics.
    Quotes are matched without the length cap; behind a form problem, a
    string quote is matched against the whole cited file.
    """
    result = ReviewEvidence()
    try:
        fm = _parse_frontmatter(content)
    except (EvidenceParseError, ValueError) as exc:
        result.diagnostics.append(f"frontmatter unreadable: {exc}")
        fm = {}
    else:
        sv = fm.get("schema_version")
        if "schema_version" not in fm:
            result.diagnostics.append("schema_version missing")
        elif not ((type(sv) is int and sv == 1) or sv == "1"):
            result.diagnostics.append(f"unsupported schema_version: {sv!r}")

    pointers: list[tuple[Any, str]] = []

    def collect(value: Any, location: str) -> list[dict[str, Any]]:
        if not isinstance(value, list):
            result.diagnostics.append(f"{location}: evidence holds no pointer list")
            return []
        entries = []
        for index, entry in enumerate(value, start=1):
            if isinstance(entry, dict):
                entries.append(entry)
                pointers.append((entry, location))
            else:
                result.diagnostics.append(
                    f"{location}: entry {index} is not a pointer mapping"
                )
        return entries

    if "evidence" in fm:
        collect(fm["evidence"], "frontmatter evidence")
    findings, blocks, errors = _scan_findings(content, reader=True)
    result.diagnostics.extend(errors)
    with_blocks: set[int] = set()
    for owner, line, value in blocks:
        if owner is not None:
            with_blocks.add(id(owner))
        if value is _UNPARSED:
            continue
        location = (
            f"{owner.location}, evidence line {line}"
            if owner is not None
            else f"line {line} (no finding owner)"
        )
        entries = collect(value, location)
        if owner is not None:
            owner.pointers.extend(entries)
    for finding in findings:
        if id(finding) not in with_blocks:
            result.failures.append(f"{finding.location}: finding has no evidence")
        elif not finding.pointers:
            result.diagnostics.append(f"{finding.location}: no parseable evidence")
    if not findings and not pointers:
        result.diagnostics.append("no findings or evidence recognized")

    cache: dict[str, str] = {}
    for pointer, location in pointers:
        ok, reason, fault = validate_pointer(
            pointer, repo_root, _file_cache=cache, check_cap=False, with_fault=True
        )
        if ok:
            result.verified += 1
        elif fault is PointerFault.CONTENT:
            result.failures.append(f"{location}: {reason}")
        else:
            result.diagnostics.append(f"{location}: {reason}")
            # A form slip must not hide a fabricated quote: match it in the whole cited file.
            unconfirmed = _quote_in_cited_file(pointer, repo_root, cache)
            if unconfirmed == "":
                result.verified += 1
            elif unconfirmed is not None:
                result.failures.append(f"{location}: {unconfirmed} (pointer form: {reason})")
    return result


def _quote_in_cited_file(
    pointer: Any, repo_root: str, cache: dict[str, str]
) -> str | None:
    """Whole-file quote check behind a FORM-faulted pointer.

    None when the pointer has no string ``path`` resolving to a regular file
    inside the repository or no string ``quote`` (nothing to check); "" when
    the quote occurs in that file's text (exact substring, multi-line
    allowed); otherwise the content failure.
    """
    if not isinstance(pointer, dict):
        return None
    raw_path, quote = pointer.get("path"), pointer.get("quote")
    if not isinstance(raw_path, str) or not raw_path or not isinstance(quote, str):
        return None
    resolved, _ = _resolve_within_repo(raw_path, repo_root)
    if resolved is None or not resolved.is_file():
        return None
    key = str(resolved)
    if key not in cache:
        try:
            cache[key] = resolved.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            return f"file read failed: {exc}"
    if quote in cache[key]:
        return ""
    return f"quote no match in {raw_path} (whole file): {quote[:60]!r}"


def validate_content(
    content: str,
    *,
    layout: str = "auto",
    repo_root: str,
    strict: bool = False,
) -> ValidationResult:
    """Validate supplied report bytes decoded as text, without reading the report."""
    try:
        fm = _parse_frontmatter(content)
    except EvidenceParseError as exc:
        return ValidationResult(
            None, EXIT_PARSE_ERROR, [f"parse-error: yaml frontmatter: {exc}"]
        )
    # Validator-Acceptor schmaeler — nur exakt
    # int(1) oder string `"1"`. Pre-fix akzeptierte `isdigit()` (also "01" als
    # sv=1) was Pre-Filter-Strictness-Drift produziert (Filter rejected "01",
    # Validator akzeptiert). Plus float (z.B. `schema_version: 1.0`) wurde
    # silent-skipped als legacy ohne Author-Signal — schlimmer als rejected.
    # Fix: schmal akzeptieren + explizit ablehnen mit Author-Signal.
    sv_raw = fm.get("schema_version")
    if isinstance(sv_raw, bool):
        # bool ist isinstance(int) True in Python — explizit ausschliessen
        return ValidationResult(
            None,
            EXIT_INVALID,
            [
                f"unsupported schema_version form: {sv_raw!r} "
                f"(expect int 1 or string '1', not bool)"
            ],
        )
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
            return ValidationResult(
                None,
                EXIT_INVALID,
                [
                    f"unsupported schema_version form: {sv_raw!r} "
                    f"(expect int 1 or string '1', got string)"
                ],
            )
    elif sv_raw is None:
        sv = None
    else:
        # Float (z.B. 1.0), list, dict, etc. — pre-fix silent-skip (sv=None).
        # Author-Signal: explicit reject damit Reviewer sieht dass `1.0` nicht
        # als v1 interpretiert wird (Versionsschema-Drift).
        return ValidationResult(
            None,
            EXIT_INVALID,
            [
                f"unsupported schema_version form: {sv_raw!r} "
                f"(expect int 1 or string '1', got {type(sv_raw).__name__})"
            ],
        )

    if sv is None or sv == 0:
        # Legacy: silent skip
        return (
            ValidationResult(
                sv,
                EXIT_INVALID,
                ["current schema_version: 1 required (strict validation)"],
            )
            if strict
            else ValidationResult(sv, EXIT_VALID, [])
        )

    if sv != 1:
        return ValidationResult(
            sv,
            EXIT_INVALID,
            [f"unsupported schema_version: {sv} (only 0 + 1 known in v1)"],
        )

    if layout not in ("auto", "per_finding", "top_level"):
        return ValidationResult(sv, EXIT_PARSE_ERROR, [f"unknown layout: {layout}"])
    selected = (
        ("top_level" if "evidence" in fm else "per_finding")
        if layout == "auto"
        else layout
    )
    try:
        findings, blocks, errors = _scan_findings(content)
    except EvidenceParseError as exc:
        return ValidationResult(sv, EXIT_PARSE_ERROR, [f"parse-error: {exc}"])

    def checked_list(value: Any, location: str) -> list[dict[str, Any]]:
        if not isinstance(value, list) or not value:
            errors.append(
                f"{location}: non-empty evidence list of pointer mappings required"
            )
            return []
        if any(not isinstance(pointer, dict) for pointer in value):
            errors.append(f"{location}: evidence entries must all be pointer mappings")
            return []
        return value

    owned_pointers: list[tuple[dict[str, Any], str]] = []
    if selected == "top_level":
        if findings or blocks:
            errors.append(
                "layout conflict: top_level evidence cannot contain finding structure or body evidence"
            )
        owned_pointers.extend(
            (p, "frontmatter evidence")
            for p in checked_list(fm.get("evidence"), "frontmatter")
        )
    else:
        if "evidence" in fm:
            errors.append(
                "layout conflict: per_finding evidence cannot contain frontmatter evidence"
            )
        if not findings:
            errors.append(
                "per_finding requires supported findings with non-empty evidence"
            )
        for owner, line, value in blocks:
            if owner is None:
                errors.append(f"line {line}: orphan evidence has no finding owner")
            else:
                owner.pointers.extend(
                    checked_list(value, f"{owner.location}, evidence line {line}")
                )
        for finding in findings:
            if not finding.pointers:
                errors.append(
                    f"{finding.location}: non-empty evidence required for this finding"
                )
            owned_pointers.extend((p, finding.location) for p in finding.pointers)
    if errors:
        return ValidationResult(sv, EXIT_INVALID, errors)

    messages: list[str] = []
    file_cache: dict[str, str] = {}
    failed = False
    for idx, (pointer, location) in enumerate(owned_pointers, start=1):
        ok, reason = validate_pointer(pointer, repo_root, _file_cache=file_cache)
        failed = failed or not ok
        messages.append(
            f"pointer {idx}: ok"
            if ok
            else f"pointer {idx}: fail — {location}: {reason}"
        )
    if failed:
        return ValidationResult(sv, EXIT_INVALID, messages)
    if owned_pointers and all(
        p.get("kind") == "file_exists" for p, _ in owned_pointers
    ):
        messages.append(
            "WARN discipline F-I-015: all pointers are kind=file_exists "
            "(trivial). Tier-1-Reviewer should include at least one "
            "non-trivial pointer (file_range or grep_match) per finding."
        )
    return ValidationResult(sv, EXIT_VALID, messages)


def validate_file(
    file_path: str,
    layout: str = "auto",
    repo_root: str | None = None,
    *,
    strict: bool = False,
) -> tuple[int, list[str]]:
    """Read the report once and preserve the public tuple validation result."""
    path = Path(file_path)
    if not path.is_file():
        return EXIT_PARSE_ERROR, [f"file not found: {file_path}"]
    repo = repo_root or _detect_repo_root(path) or str(path.parent.resolve())
    try:
        content = path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        return EXIT_PARSE_ERROR, [f"file read failed: {exc}"]
    result = validate_content(content, layout=layout, repo_root=repo, strict=strict)
    return result.exit_code, result.messages


# ---------------------------------------------------------------------------
# CLI Entrypoint
# ---------------------------------------------------------------------------


def _main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Validate evidence pointers per Spec 299 schema.",
    )
    # nargs="+" so pre-commit Check 13 can validate N staged
    # files in 1 subprocess instead of N — saves N-1 python cold-starts.
    parser.add_argument(
        "files", nargs="+",
        help="Output-File(s) mit evidence-Block",
    )
    parser.add_argument(
        "--strict", action="store_true",
        help="Require current schema_version: 1; reject missing/legacy schema.",
    )
    parser.add_argument(
        "--layout", choices=("per_finding", "top_level", "auto"),
        default="auto",
    )
    parser.add_argument(
        "--repo-root", default=None,
        help="Repo-root for path-boundary check. Default walks up "
             "from <file> looking for .git or pyproject.toml; falls back to "
             "parent-of-file. Override is the most reliable path.",
    )

    args = parser.parse_args(argv)

    overall_exit = EXIT_VALID
    for file_path in args.files:
        exit_code, messages = validate_file(
            file_path, layout=args.layout, repo_root=args.repo_root, strict=args.strict,
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
