"""
Test-File fuer Spec 299 Fabrication-Mitigation — Pre-commit-Group.

RED skeletons. Implementation steht noch aus.

TCs: TC-046..TC-049 + TC-051 (Performance) aus docs/tasks/299-test-plan.md
(Phase F Pre-commit Check 13 SOURCE-VERIFICATION).
"""
from __future__ import annotations

import subprocess
from pathlib import Path

import pytest


PRECOMMIT_REL = "orchestrators/claude-code/hooks/pre-commit.sh"


class TestPrecommitCheck13:
    def test_TC_046_precommit_contains_check_13_after_check_12(
        self, framework_root: Path
    ):
        """
        TC-046: pre-commit.sh enthaelt Check 13 SOURCE-VERIFICATION nach Check 12.

        Phase: F
        Level: L0 (Structural)
        Quelle: AC-7, §5
        evidence:
          - kind: file_range
            path: docs/specs/299-fabrication-mitigation.md
            lines: 354-356
            quote: "Reihenfolge-Hinweis:** Check 13 NACH Check 12 SECRET-SCAN"
        """
        hook = framework_root / PRECOMMIT_REL
        assert hook.is_file(), f"pre-commit.sh fehlt: {hook}"

        text = hook.read_text(encoding="utf-8")
        # Check 13 existiert
        assert "Check 13" in text or "SOURCE-VERIFICATION" in text, \
            "Check 13 SOURCE-VERIFICATION fehlt in pre-commit.sh"

        # Reihenfolge: Check 13 NACH Check 12
        idx_12 = text.find("Check 12")
        idx_13 = text.find("Check 13")
        if idx_12 == -1:
            idx_12 = text.find("SECRET-SCAN")
        if idx_13 == -1:
            idx_13 = text.find("SOURCE-VERIFICATION")
        assert idx_12 != -1, "Check 12 fehlt"
        assert idx_13 != -1, "Check 13 fehlt"
        assert idx_12 < idx_13, \
            f"Check 13 ({idx_13}) muss NACH Check 12 ({idx_12}) stehen"

        # Filter-grep
        assert "docs/reviews/board" in text or "docs/reviews/(board|council)" in text, \
            "Filter-grep matched nicht docs/reviews/board"
        assert "docs/specs" in text

    def test_TC_047_precommit_calls_validator_per_staged_file(
        self, framework_root: Path, tmp_path: Path
    ):
        """
        TC-047: Pre-commit Check 13 ruft validate_evidence_pointers.py pro
        staged File.

        Phase: F
        Level: L4 (E2E pre-commit)
        Quelle: AC-7
        evidence:
          - kind: file_range
            path: docs/specs/299-fabrication-mitigation.md
            lines: 339-340
            quote: "Pro File: scripts/validate_evidence_pointers.py"
        """
        hook = framework_root / PRECOMMIT_REL
        assert hook.is_file()

        text = hook.read_text(encoding="utf-8")
        # Check 13 ruft validator-Skript
        assert "validate_evidence_pointers.py" in text, \
            "validator-Aufruf fehlt in pre-commit.sh Check 13"

    def test_TC_048_precommit_silent_skip_for_legacy(
        self, framework_root: Path, tmp_path: Path
    ):
        """
        TC-048: Pre-commit Check 13 silent skip fuer schema_version: 0 / fehlend.

        Phase: F
        Level: L4
        Quelle: AC-7, AC-9
        evidence:
          - kind: file_range
            path: docs/specs/299-fabrication-mitigation.md
            lines: 343-343
            quote: "Legacy (schema_version: 0 oder fehlend) → silent skip"
        """
        hook = framework_root / PRECOMMIT_REL
        assert hook.is_file()
        text = hook.read_text(encoding="utf-8")

        # Filter-grep: nur File mit schema_version: 1 ODER evidence:-Block
        # triggert validator. Legacy ohne schema_version → grep-filter fail
        # → kein validator-call.
        assert "schema_version: 1" in text or "schema_version:" in text, \
            "Pre-commit-Filter prueft schema_version nicht"

    def test_TC_049_precommit_does_not_call_for_non_tracked_paths(
        self, framework_root: Path
    ):
        """
        TC-049: Pre-commit Check 13 filtert NICHT auf nicht-tracked-Pfade.

        Phase: F
        Level: L4
        Quelle: AC-7
        evidence:
          - kind: file_range
            path: docs/specs/299-fabrication-mitigation.md
            lines: 332-336
            quote: "docs/reviews/board/*.md"
        """
        hook = framework_root / PRECOMMIT_REL
        assert hook.is_file()
        text = hook.read_text(encoding="utf-8")

        # Filter-grep enthaelt nur die 3 Tracked-Path-Familien
        # (docs/reviews/board, docs/reviews/council, docs/specs).
        # agents/, scripts/ etc. sind NICHT in Filter-grep.
        assert "agents/" not in text.split("Check 13")[-1].split("Check 14")[0] \
            if "Check 14" in text else "agents/" not in text.split("Check 13")[-1], \
            "Pre-commit Check 13 filtert agents/ — sollte NICHT"


class TestPrecommitFilterSymmetry:
    """C2-004 Pass-2-Fix Coverage: Pre-commit Filter und Validator-Acceptor
    muessen dieselbe Klasse von schema_version: 1 Forms akzeptieren.

    Pre-Pass-2 Filter `^schema_version:\\s*1$` rejected legitime quoted /
    whitespace / comment Forms; Validator akzeptierte sie via isdigit() —
    asymmetrischer Backstop, eine ganze Klasse legitimer YAML-Forms entging
    Schicht-4-Pruefung.

    Diese Tests pruefen pre-commit.sh Filter-Pattern (extrahiert per
    text-scan) gegen 4 v1-Forms + Negativ-Cases, plus Validator-CLI als
    Symmetrie-Check.
    """

    # Test-Cases (form, expected_match) — POSITIVE: alle 4 v1-Forms
    POSITIVE_CASES = [
        ("plain", "schema_version: 1"),
        ("double_quoted", 'schema_version: "1"'),
        ("single_quoted", "schema_version: '1'"),
        ("trailing_whitespace", "schema_version: 1   "),
        ("inline_comment", "schema_version: 1 # comment"),
    ]

    # NEGATIVE: muessen NICHT matchen
    NEGATIVE_CASES = [
        ("legacy_v0", "schema_version: 0"),
        ("future_v2", "schema_version: 2"),
        ("two_digit", "schema_version: 11"),
        ("three_digit", "schema_version: 100"),
        ("commented_out", "# schema_version: 1"),
    ]

    @pytest.fixture
    def filter_pattern(self, framework_root: Path) -> str:
        """Extrahiert Filter-Regex-Pattern aus pre-commit.sh.

        Pflicht: pre-commit.sh enthaelt genau ein `grep -qE` im Check-13-Block
        mit `^schema_version:` als Pattern-Praefix. Das Pattern wird in bash
        als `"..."`-string zitiert; eingebettete `\\"` sind bash-escapes fuer
        ERE-Quote-Klassen `[\\"']`.
        Extraction: Zeile finden die `grep -qE` + `^schema_version` enthaelt,
        dann das doppelt-quoted-Argument extrahieren und bash-escape `\\"`
        wieder zu `"` aufloesen damit das Pattern an `grep` direkt
        weitergegeben werden kann (subprocess kein-shell-Mode).
        """
        hook = framework_root / PRECOMMIT_REL
        text = hook.read_text(encoding="utf-8")

        target_line = None
        for line in text.splitlines():
            if "grep -qE" in line and "^schema_version" in line:
                target_line = line
                break
        assert target_line is not None, (
            "pre-commit.sh enthaelt keine grep -qE-Zeile mit schema_version"
        )

        # Find the first `"` after `grep -qE`; pattern is from there until
        # the matching closing `"` (skip `\"` bash-escapes).
        gpos = target_line.find("grep -qE")
        first_q = target_line.find('"', gpos)
        assert first_q != -1, "Filter-Zeile hat kein doppeltes-Quote"
        i = first_q + 1
        pattern_chars: list[str] = []
        while i < len(target_line):
            ch = target_line[i]
            if ch == "\\" and i + 1 < len(target_line) and target_line[i + 1] == '"':
                # bash-escaped quote inside double-quoted string
                pattern_chars.append('"')
                i += 2
                continue
            if ch == '"':
                break
            pattern_chars.append(ch)
            i += 1
        pattern = "".join(pattern_chars)
        assert pattern.startswith("^schema_version"), (
            f"Extracted Filter-Pattern unerwartet: {pattern!r}"
        )
        return pattern

    def test_TC_C2_004_filter_accepts_plain_v1(
        self, framework_root: Path, tmp_path: Path, filter_pattern: str
    ):
        """C2-004: Plain `schema_version: 1` muss Filter passieren."""
        f = tmp_path / "out.md"
        f.write_text("schema_version: 1\nrest:\n", encoding="utf-8")
        rc = subprocess.run(
            ["grep", "-qE", filter_pattern, str(f)],
        ).returncode
        assert rc == 0, "Filter rejects legitime v1-Form: schema_version: 1"

    def test_TC_C2_004_filter_accepts_quoted_v1(
        self, framework_root: Path, tmp_path: Path, filter_pattern: str
    ):
        """C2-004: Quoted `schema_version: "1"` muss Filter passieren.

        Validator akzeptiert via `sv_raw.isdigit()`. Pre-Pass-2 Filter
        rejected silent — Schicht-4-Backstop entging.
        """
        f = tmp_path / "out.md"
        f.write_text('schema_version: "1"\nrest:\n', encoding="utf-8")
        rc = subprocess.run(
            ["grep", "-qE", filter_pattern, str(f)],
        ).returncode
        assert rc == 0, 'Filter rejects legitime v1-Form: schema_version: "1"'

        # Single-quoted form
        f2 = tmp_path / "out_sq.md"
        f2.write_text("schema_version: '1'\nrest:\n", encoding="utf-8")
        rc2 = subprocess.run(
            ["grep", "-qE", filter_pattern, str(f2)],
        ).returncode
        assert rc2 == 0, "Filter rejects single-quoted v1-Form"

    def test_TC_C2_004_filter_accepts_trailing_whitespace_v1(
        self, framework_root: Path, tmp_path: Path, filter_pattern: str
    ):
        """C2-004: Trailing whitespace nach `schema_version: 1` muss Filter passieren."""
        f = tmp_path / "out.md"
        f.write_text("schema_version: 1   \nrest:\n", encoding="utf-8")
        rc = subprocess.run(
            ["grep", "-qE", filter_pattern, str(f)],
        ).returncode
        assert rc == 0, "Filter rejects v1 mit trailing whitespace"

    def test_TC_C2_004_filter_accepts_inline_comment_v1(
        self, framework_root: Path, tmp_path: Path, filter_pattern: str
    ):
        """C2-004: Inline-comment hinter `schema_version: 1` muss Filter passieren."""
        f = tmp_path / "out.md"
        f.write_text("schema_version: 1 # comment\nrest:\n", encoding="utf-8")
        rc = subprocess.run(
            ["grep", "-qE", filter_pattern, str(f)],
        ).returncode
        assert rc == 0, "Filter rejects v1 mit inline comment"

    def test_TC_C2_004_filter_rejects_negative_cases(
        self, framework_root: Path, tmp_path: Path, filter_pattern: str
    ):
        """C2-004: Filter muss legacy/future/multi-digit/kommentierte Forms rejecten.

        Verhindert dass Fix zu permissiv wird — schmaleres Sicherheitsnetz
        ist auch ein Bug.
        """
        for label, content in self.NEGATIVE_CASES:
            f = tmp_path / f"neg_{label}.md"
            f.write_text(content + "\n", encoding="utf-8")
            rc = subprocess.run(
                ["grep", "-qE", filter_pattern, str(f)],
            ).returncode
            assert rc != 0, (
                f"Filter accepts negative case '{label}': {content!r} — "
                f"Filter zu permissiv geworden"
            )

    def test_TC_C2_004_validator_accepts_all_4_v1_forms(
        self, framework_root: Path, tmp_path: Path
    ):
        """C2-004 Symmetrie: Validator akzeptiert exakt die 4 Filter-Forms.

        Symmetrie-Check: Filter und Validator muessen dieselben Forms als
        sv=1 erkennen. Bei valid file_range pointer auf real source: exit 0.
        """
        # Build real source for evidence pointer
        src = tmp_path / "src.txt"
        src.write_text("Hello World\n", encoding="utf-8")

        validator = framework_root / "scripts/validate_evidence_pointers.py"

        for label, sv_line in self.POSITIVE_CASES:
            out = tmp_path / f"out_{label}.md"
            evidence_block = (
                f"evidence:\n"
                f"  - kind: file_range\n"
                f"    path: {src.name}\n"
                f"    lines: 1-1\n"
                f'    quote: "Hello World"\n'
            )
            body = f"---\n{sv_line}\n{evidence_block}---\n\nBody\n"
            out.write_text(body, encoding="utf-8")

            result = subprocess.run(
                ["python3", str(validator), str(out), "--repo-root", str(tmp_path)],
                capture_output=True, text=True,
            )
            assert result.returncode == 0, (
                f"Validator rejects v1-Form '{label}' ({sv_line!r}): "
                f"rc={result.returncode}\nstdout={result.stdout}\n"
                f"stderr={result.stderr}"
            )


class TestPrecommitPerformance:
    @pytest.mark.skip(reason="Perf-Test braucht echtes Git-Repo + Staging — "
                              "Skeleton bleibt RED; Implementer aktiviert.")
    def test_TC_051_precommit_worst_case_under_5s(self, framework_root: Path):
        """
        TC-051: Pre-commit Check 13 Worst-Case <5s.

        Phase: G
        Level: L5 (Performance)
        Quelle: AC-8
        evidence:
          - kind: file_range
            path: docs/specs/299-fabrication-mitigation.md
            lines: 359-362
            quote: "<5s worst-case"
        """
        # Synthetic 50 staged Files in docs/reviews/board/
        # → time git commit -m "..."
        # → assert total_time < 5.0
        assert False, "RED skeleton — perf-test mit echtem git-staging"
