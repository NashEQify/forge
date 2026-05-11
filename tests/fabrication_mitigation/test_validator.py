"""
Test-File fuer Spec 299 Fabrication-Mitigation — Validator-Group.

RED skeletons. Implementation steht noch aus.

TCs: TC-025..TC-035 aus docs/tasks/299-test-plan.md
(Phase C3 Standalone-Validator scripts/validate_evidence_pointers.py).
"""
from __future__ import annotations

from pathlib import Path

import pytest


# ---------------------------------------------------------------------------
# AC-4 — Standalone-Validator CLI
# ---------------------------------------------------------------------------


class TestValidatorCLI:
    def test_TC_025_cli_exit_0_for_valid_pointer(
        self, validator_cli, valid_pointer_file
    ):
        """
        TC-025: validate_evidence_pointers.py CLI Exit 0 fuer valid pointer (Eval 3).

        Phase: C3
        Level: L2 (Unit, CLI)
        Quelle: AC-4, Eval 3
        evidence:
          - kind: file_range
            path: docs/specs/299-fabrication-mitigation.md
            lines: 568-573
            quote: "Eval 3 — Valid Pointer"
        """
        result = validator_cli(valid_pointer_file, cwd=valid_pointer_file.parent)
        assert result.returncode == 0, \
            f"valid pointer CLI exit != 0: code={result.returncode}, " \
            f"stdout={result.stdout!r}, stderr={result.stderr!r}"

    def test_TC_026_cli_exit_1_for_quote_mismatch(
        self, validator_cli, fabricated_quote_file
    ):
        """
        TC-026: validate_evidence_pointers.py Exit 1 fuer Quote-Mismatch (Eval 1).

        Phase: C3
        Level: L2
        Quelle: AC-4, Eval 1
        evidence:
          - kind: file_range
            path: docs/specs/299-fabrication-mitigation.md
            lines: 555-562
            quote: "Eval 1 — Quote-Mismatch"
        """
        result = validator_cli(
            fabricated_quote_file, cwd=fabricated_quote_file.parent
        )
        assert result.returncode == 1, \
            f"fabricated quote MUST exit 1: got {result.returncode}"
        combined = (result.stderr + result.stdout).lower()
        assert "fail" in combined or "no match" in combined or "match" in combined, \
            f"fail-reason fehlt im Output: {combined!r}"

    def test_TC_027_cli_exit_1_for_range_overflow(
        self, validator_cli, out_of_range_file
    ):
        """
        TC-027: validate_evidence_pointers.py Exit 1 fuer Range-Overflow (Eval 2).

        Phase: C3
        Level: L2
        Quelle: AC-4, Eval 2
        evidence:
          - kind: file_range
            path: docs/specs/299-fabrication-mitigation.md
            lines: 564-568
            quote: "Eval 2 — Range-Overflow"
        """
        result = validator_cli(out_of_range_file, cwd=out_of_range_file.parent)
        assert result.returncode == 1
        combined = (result.stderr + result.stdout).lower()
        assert "range" in combined or "out of" in combined, \
            f"range-error fehlt: {combined!r}"

    def test_TC_028_cli_exit_1_for_pattern_match_count(
        self, validator_cli, tmp_path
    ):
        """
        TC-028: validate_evidence_pointers.py Exit 1 fuer Pattern-Match Count (Eval 4).

        Phase: C3
        Level: L2
        Quelle: AC-4, Eval 4
        evidence:
          - kind: file_range
            path: docs/specs/299-fabrication-mitigation.md
            lines: 575-581
            quote: "Eval 4 — Pattern-Match Count"
        """
        src = tmp_path / "patterns.txt"
        src.write_text("foo\nbar\nfoo\n", encoding="utf-8")  # 2 matches
        out = tmp_path / "grep.md"
        out.write_text(
            "---\nschema_version: 1\nevidence:\n"
            "  - kind: grep_match\n"
            f'    pattern: "foo"\n'
            f"    path: {src.name}\n"
            '    expected_count: ">=5"\n---\nbody\n',
            encoding="utf-8",
        )
        result = validator_cli(out, cwd=tmp_path)
        assert result.returncode == 1, \
            f"expected_count >=5 with 2 matches MUST exit 1: {result.returncode}"

    def test_TC_029_cli_exit_0_for_legacy_schema_version_0(
        self, validator_cli, legacy_v0_file
    ):
        """
        TC-029: validate_evidence_pointers.py Exit 0 fuer Legacy schema_version: 0
        (Eval 5).

        Phase: C3
        Level: L2 (Backward-Compat)
        Quelle: AC-4, AC-9, Eval 5
        evidence:
          - kind: file_range
            path: docs/specs/299-fabrication-mitigation.md
            lines: 583-589
            quote: "Eval 5 — Legacy Backward-Compat"
        """
        result = validator_cli(legacy_v0_file, cwd=legacy_v0_file.parent)
        assert result.returncode == 0, \
            f"legacy schema_version: 0 MUST exit 0 (silent skip): " \
            f"{result.returncode}, {result.stderr!r}"

    def test_TC_030_cli_exit_2_for_parse_error(
        self, framework_root: Path, validator_cli, tmp_path
    ):
        """
        TC-030: validate_evidence_pointers.py Exit 2 fuer parse-error.

        Phase: C3
        Level: L2 (Negativ — Edge)
        Quelle: AC-4, §6.1
        evidence:
          - kind: file_range
            path: docs/specs/299-fabrication-mitigation.md
            lines: 380-383
            quote: "exit 2: parse-error im evidence-block"
        """
        # Pre-Gate: validator-CLI muss existieren. Sonst trivially PASS
        # (Python returnt 2 bei FileNotFoundError beim Modul-Laden).
        validator_path = framework_root / "scripts/validate_evidence_pointers.py"
        assert validator_path.is_file(), \
            "Pre-Gate: scripts/validate_evidence_pointers.py fehlt — Test " \
            "wuerde trivially PASS via Python-FileNotFound exit 2"

        broken = tmp_path / "broken.md"
        broken.write_text(
            "---\nschema_version: 1\nevidence:\n"
            "  - kind: file_range\n"
            "    path: foo\n"
            "    lines: [unclosed\n"  # broken YAML
            "---\nbody\n",
            encoding="utf-8",
        )
        result = validator_cli(broken, cwd=tmp_path)
        assert result.returncode == 2, \
            f"parse-error MUST exit 2: got {result.returncode}"
        # Strenger: parse-error-Reason im stderr/stdout (validator-spezifisch)
        combined = (result.stdout + result.stderr).lower()
        assert "parse" in combined or "yaml" in combined or "syntax" in combined, \
            f"parse-error-msg fehlt (Trivial-PASS-Pfad): {combined!r}"

    def test_TC_031_cli_exit_0_for_valid_pointer_with_misinterpretation(
        self, validator_cli, valid_pointer_file
    ):
        """
        TC-031: validate_evidence_pointers.py Exit 0 fuer valid pointer +
        falsche semantische Schlussfolgerung (Eval 6, Compensation-Bug).

        Phase: C3
        Level: L2 (Trade-off-Negativ — akzeptiertes Trade-off)
        Quelle: AC-4, Eval 6
        Adversary-Target: Compensation-Bug (Schema-Limitation, akzeptiert)
        evidence:
          - kind: file_range
            path: docs/specs/299-fabrication-mitigation.md
            lines: 591-598
            quote: "Eval 6 — Misinterpretation"
        """
        # Schema faengt FABRICATION, nicht MISINTERPRETATION.
        # Test verifiziert akzeptiertes Trade-off: Pointer mechanisch valid →
        # exit 0 EGAL ob Reviewer-Schluss semantisch korrekt ist.
        result = validator_cli(valid_pointer_file, cwd=valid_pointer_file.parent)
        assert result.returncode == 0, \
            "Trade-off: valid pointer mit falschem semantischem Schluss bleibt " \
            f"mechanisch valid. exit 0 erwartet, got {result.returncode}"


class TestValidatorLibraryAPI:
    def test_TC_032_validate_pointer_library_api_single_pointer(
        self, framework_root, fixture_source_hello, tmp_path
    ):
        """
        TC-032: validate_pointer Library-API single-pointer (kind=file_range).

        Phase: C3
        Level: L2 (Unit, Library)
        Quelle: AC-4, §6.2
        evidence:
          - kind: file_range
            path: docs/specs/299-fabrication-mitigation.md
            lines: 393-396
            quote: "def validate_pointer(pointer: dict"
        """
        from scripts.validate_evidence_pointers import validate_pointer

        rel = fixture_source_hello.relative_to(tmp_path)
        ok_pos, _ = validate_pointer(
            {"kind": "file_range", "path": str(rel),
             "lines": "1-1", "quote": "Hello World"},
            str(tmp_path),
        )
        assert ok_pos is True, "valid pointer MUST return ok=True"

        ok_neg, _ = validate_pointer(
            {"kind": "file_range", "path": str(rel),
             "lines": "1-1", "quote": "Goodbye"},
            str(tmp_path),
        )
        assert ok_neg is False, "fabricated pointer MUST return ok=False"

    def test_TC_033_parse_evidence_block_both_layouts(
        self, framework_root, valid_pointer_file, tmp_path
    ):
        """
        TC-033: parse_evidence_block Library-API beide Layouts.

        Phase: C3
        Level: L2 (Unit)
        Quelle: AC-4, §6.2
        evidence:
          - kind: file_range
            path: docs/specs/299-fabrication-mitigation.md
            lines: 397-399
            quote: "def parse_evidence_block"
        """
        from scripts.validate_evidence_pointers import parse_evidence_block

        # top_level → bereits im valid_pointer_file fixture
        pointers_tl = parse_evidence_block(str(valid_pointer_file), "top_level")
        assert isinstance(pointers_tl, list)
        assert len(pointers_tl) >= 1

        # per_finding-Layout: Output mit Finding-Bloecken
        pf = tmp_path / "per_finding.md"
        pf.write_text(
            "## Finding 1\n"
            "evidence:\n"
            "  - kind: file_exists\n"
            "    path: per_finding.md\n"
            "## Finding 2\n"
            "evidence:\n"
            "  - kind: file_exists\n"
            "    path: per_finding.md\n",
            encoding="utf-8",
        )
        pointers_pf = parse_evidence_block(str(pf), "per_finding")
        assert len(pointers_pf) >= 1

        # auto-detect
        pointers_auto = parse_evidence_block(str(pf), "auto")
        assert len(pointers_auto) >= 1

    def test_TC_034_dsl_grammar_for_expected_count_all_operators(
        self, framework_root, tmp_path
    ):
        """
        TC-034: DSL-Grammar fuer expected_count alle Operatoren.

        Phase: C3
        Level: L2 (Unit)
        Quelle: AC-4, §6.3
        evidence:
          - kind: file_range
            path: docs/specs/299-fabrication-mitigation.md
            lines: 405-413
            quote: "OPERATOR := \\">=\\""
        """
        from scripts.validate_evidence_pointers import validate_pointer

        src = tmp_path / "src.txt"
        src.write_text("foo\nfoo\nfoo\n", encoding="utf-8")  # 3 matches
        rel = str(src.relative_to(tmp_path))

        # Positive Cases
        for expr, expected_ok in [
            (">=1", True),
            ("<=5", True),
            (">2", True),
            ("<10", True),
            ("==3", True),
            ("!=0", True),
            (">=5", False),  # 3 < 5
            ("==5", False),  # 3 != 5
        ]:
            ok, _ = validate_pointer(
                {"kind": "grep_match", "pattern": "foo",
                 "path": rel, "expected_count": expr},
                str(tmp_path),
            )
            assert ok is expected_ok, \
                f"expected_count={expr!r} → expected {expected_ok}, got {ok}"

    def test_TC_035_validate_file_with_auto_layout(
        self, framework_root, valid_pointer_file
    ):
        """
        TC-035: validate_file Library-API mit auto-layout-Detect.

        Phase: C3
        Level: L2 (Unit)
        Quelle: AC-4
        evidence:
          - kind: file_range
            path: docs/specs/299-fabrication-mitigation.md
            lines: 391-393
            quote: "def validate_file(file_path: str"
        """
        from scripts.validate_evidence_pointers import validate_file

        exit_code, errors = validate_file(str(valid_pointer_file), "auto")
        assert exit_code in (0, 1, 2), \
            f"exit_code muss 0/1/2 sein: {exit_code}"
        assert isinstance(errors, list)


# ---------------------------------------------------------------------------
# CC-001 Snapshot-Tests — per_finding format with `- evidence:` markdown
# bullet-list-item form, copy-pasted EXACTLY from prescribed reviewer-
# protocols. Pre-fix the parser regex `^(\s*)evidence:\s*$` did NOT match
# this form → defense was structurally ineffective.
# ---------------------------------------------------------------------------


class TestPerFindingPrescribedFormatSnapshot:
    """Snapshot-Tests für CC-001: per_finding parser MUSS das prescribed
    Reviewer-Protocol-Format `- evidence:` (markdown-list-item-form) matchen.

    evidence:
      - kind: file_range
        path: agents/_protocols/code-reviewer-protocol.md
        lines: 47-52
        quote: "- evidence:"
    """

    def test_TC_058_parser_matches_dash_evidence_bullet_list_item_form(
        self, tmp_path
    ):
        """CC-001 (F-CR-002+F-CA-001): parser muss `- evidence:` als Markdown-
        Bullet-Item matchen (prescribed form per reviewer-protocols)."""
        from scripts.validate_evidence_pointers import parse_evidence_block

        # Source-File mit echten Bytes fuer Pointer-Validierung
        src = tmp_path / "src.py"
        src.write_text("def hello():\n    return 'world'\n", encoding="utf-8")

        # Prescribed format: copy-paste aus code-reviewer-protocol.md
        pf = tmp_path / "review.md"
        pf.write_text(
            "---\n"
            "schema_version: 1\n"
            "evidence_layout: per_finding\n"
            "---\n"
            "\n"
            "### F-TEST-001: Beispiel-Finding\n"
            "- severity: critical\n"
            "- scope: local\n"
            "- evidence:\n"
            "    - kind: file_range\n"
            "      path: src.py\n"
            "      lines: 1-2\n"
            '      quote: "def hello"\n'
            "- description: Beispiel\n"
            "- suggested_fix: Beispiel\n",
            encoding="utf-8",
        )
        pointers = parse_evidence_block(str(pf), "per_finding")
        assert len(pointers) == 1, \
            f"per_finding parser MUST match `- evidence:` bullet-list-item " \
            f"form (CC-001). Got {len(pointers)} pointers from prescribed " \
            f"reviewer-protocol format."
        assert pointers[0]["kind"] == "file_range"
        assert pointers[0]["path"] == "src.py"

    def test_TC_059_parser_matches_block_form_evidence_no_dash(
        self, tmp_path
    ):
        """CC-001 backward-compat: parser MUSS auch `evidence:` (ohne `- `)
        matchen — beide Forms sind erlaubt (CC-001 Fix).
        """
        from scripts.validate_evidence_pointers import parse_evidence_block

        pf = tmp_path / "review.md"
        pf.write_text(
            "---\n"
            "schema_version: 1\n"
            "evidence_layout: per_finding\n"
            "---\n"
            "\n"
            "## Finding 1\n"
            "evidence:\n"
            "  - kind: file_exists\n"
            "    path: review.md\n",
            encoding="utf-8",
        )
        pointers = parse_evidence_block(str(pf), "per_finding")
        assert len(pointers) == 1, \
            f"per_finding parser MUST also match block-form `evidence:` " \
            f"(no dash). Got {len(pointers)} pointers."

    def test_TC_060_parser_real_world_reviewer_output(
        self, framework_root, tmp_path
    ):
        """CC-001 Real-World-Test: reviewer-output File aus docs/reviews/code/
        muss parsable sein (ergo: > 0 pointers extrahiert)."""
        from scripts.validate_evidence_pointers import parse_evidence_block

        target = framework_root / "docs/reviews/code/299-fabrication-mitigation-code-review.md"
        if not target.is_file():
            import pytest
            pytest.skip("real-world reviewer-output not present (OSS-clean repo)")

        pointers = parse_evidence_block(str(target), "per_finding")
        # Pre-fix: 0 pointers (parser ineffective). Post-fix: should find > 0.
        assert len(pointers) > 0, \
            f"CC-001 dogfooding: real reviewer-output {target.name} produces " \
            f"{len(pointers)} pointers. Pre-fix this was 0 (parser defense " \
            f"structurally ineffective for prescribed format)."

    def test_TC_061_per_finding_null_evidence_raises_parse_error(
        self, tmp_path
    ):
        """CC-009: `evidence: ~` and `evidence: []` in per_finding context
        MUST raise EvidenceParseError so AC-3 Test-6 semantics extend to
        per-finding granularity (not just file-level top_level)."""
        from scripts.validate_evidence_pointers import (
            EvidenceParseError, parse_evidence_block,
        )
        import pytest

        pf = tmp_path / "review.md"
        pf.write_text(
            "---\n"
            "schema_version: 1\n"
            "evidence_layout: per_finding\n"
            "---\n"
            "\n"
            "### F-NULL-001: Finding mit null-evidence\n"
            "- evidence: ~\n"
            "- description: missing pointers\n",
            encoding="utf-8",
        )
        with pytest.raises(EvidenceParseError, match="null/empty"):
            parse_evidence_block(str(pf), "per_finding")

    def test_TC_062_per_finding_empty_list_evidence_raises_parse_error(
        self, tmp_path
    ):
        """CC-009: `evidence: []` per finding MUST raise parse-error too."""
        from scripts.validate_evidence_pointers import (
            EvidenceParseError, parse_evidence_block,
        )
        import pytest

        pf = tmp_path / "review.md"
        pf.write_text(
            "---\n"
            "schema_version: 1\n"
            "evidence_layout: per_finding\n"
            "---\n"
            "\n"
            "### F-EMPTY-001: Finding mit leerer evidence-Liste\n"
            "- evidence: []\n"
            "- description: missing pointers\n",
            encoding="utf-8",
        )
        with pytest.raises(EvidenceParseError, match="null/empty"):
            parse_evidence_block(str(pf), "per_finding")

    def test_TC_063_layout_detect_does_not_confuse_evidence_layout_key(
        self, tmp_path
    ):
        """CC-010: `evidence_layout: per_finding` in frontmatter MUST NOT
        be misdetected as `evidence:` top-level key.

        Pre-fix the regex `^evidence:` matched `evidence_layout:` because
        it matched the prefix → file got treated as top_level instead of
        per_finding.
        """
        from scripts.validate_evidence_pointers import _detect_layout

        content = (
            "---\n"
            "schema_version: 1\n"
            "evidence_layout: per_finding\n"
            "---\n"
            "\n"
            "### F-X-001: Finding\n"
            "- evidence:\n"
            "    - kind: file_exists\n"
            "      path: x.md\n"
        )
        layout = _detect_layout(content)
        assert layout == "per_finding", \
            f"CC-010: `evidence_layout:` key MUST NOT confuse detect. " \
            f"Got layout={layout!r} for per_finding-content."


# ---------------------------------------------------------------------------
# Task 301 — F-CA-PASS3-001 + C2-006 + C2-005 NEW Tests
# ---------------------------------------------------------------------------


class TestSchemaVersionStrictAcceptor:
    """Task 301 F-CA-PASS3-001: Validator-Acceptor schmaeler — nur exakt
    int(1) oder string `"1"`. Kein `isdigit()`-Pfad mehr (akzeptierte "01"
    silent), kein silent-skip auf float (1.0 → "Reviewer denkt v1 ist aktiv").
    """

    def test_TC_301_schema_version_zero_padded_string_rejected(
        self, tmp_path, validator_cli
    ):
        """Task 301 F-CA-PASS3-001: `schema_version: "01"` muss Author-Signal
        produzieren (exit != 0) statt silent als sv=1 akzeptiert zu werden.

        Phase: 301
        Level: L2 (Unit, CLI)
        Quelle: docs/tasks/301-delegation.md §2 F-CA-PASS3-001
        evidence:
          - kind: file_range
            path: scripts/validate_evidence_pointers.py
            lines: 624-680
            quote: "unsupported schema_version form"
        """
        out = tmp_path / "zero_pad.md"
        out.write_text(
            "---\nschema_version: \"01\"\n---\nBody\n",
            encoding="utf-8",
        )
        result = validator_cli(out, cwd=tmp_path)
        assert result.returncode != 0, (
            f"`schema_version: \"01\"` MUST produce author-signal (rc != 0). "
            f"Got rc={result.returncode}, stdout={result.stdout!r}, "
            f"stderr={result.stderr!r}"
        )
        # Author-Signal: msg sollte form-Hinweis enthalten
        combined = (result.stdout + result.stderr).lower()
        assert "schema_version" in combined and "form" in combined, (
            f"Author-Signal-msg fehlt expected hint. stdout+stderr={combined!r}"
        )

    def test_TC_301_schema_version_float_rejected_not_silent(
        self, tmp_path, validator_cli
    ):
        """Task 301 F-CA-PASS3-001: `schema_version: 1.0` (float) muss
        explizit rejected werden statt silent-skip als legacy. Pre-fix:
        sv=None → silent skip → Reviewer denkt "v1 ist aktiv", Validator
        skippt komplett — schlimmer als rejected weil kein Author-Signal.
        """
        out = tmp_path / "float_form.md"
        out.write_text(
            "---\nschema_version: 1.0\n---\nBody\n",
            encoding="utf-8",
        )
        result = validator_cli(out, cwd=tmp_path)
        assert result.returncode != 0, (
            f"`schema_version: 1.0` MUST NOT silent-skip. "
            f"Got rc={result.returncode}, stdout={result.stdout!r}, "
            f"stderr={result.stderr!r}"
        )

    def test_TC_301_schema_version_plain_int_one_accepted(
        self, tmp_path, fixture_source_hello, validator_cli
    ):
        """Regression: plain `schema_version: 1` (int) bleibt akzeptiert."""
        rel = fixture_source_hello.relative_to(tmp_path)
        body = (
            "---\n"
            "schema_version: 1\n"
            f"evidence:\n"
            f"  - kind: file_range\n"
            f"    path: {rel}\n"
            f"    lines: 1-1\n"
            f"    quote: \"Hello World\"\n"
            "---\n\nBody\n"
        )
        out = tmp_path / "plain.md"
        out.write_text(body, encoding="utf-8")
        result = validator_cli(out, cwd=tmp_path)
        assert result.returncode == 0, (
            f"plain int sv=1 MUST be accepted. rc={result.returncode}, "
            f"stdout={result.stdout!r}, stderr={result.stderr!r}"
        )

    def test_TC_301_schema_version_quoted_string_one_accepted(
        self, tmp_path, fixture_source_hello, validator_cli
    ):
        """Regression: quoted `schema_version: "1"` bleibt akzeptiert
        (Validator-Acceptance-Symmetrie zu Filter `["']?1["']?`).
        """
        rel = fixture_source_hello.relative_to(tmp_path)
        body = (
            "---\n"
            "schema_version: \"1\"\n"
            "evidence:\n"
            f"  - kind: file_range\n"
            f"    path: {rel}\n"
            f"    lines: 1-1\n"
            f"    quote: \"Hello World\"\n"
            "---\n\nBody\n"
        )
        out = tmp_path / "quoted.md"
        out.write_text(body, encoding="utf-8")
        result = validator_cli(out, cwd=tmp_path)
        assert result.returncode == 0, (
            f"quoted sv=\"1\" MUST be accepted. rc={result.returncode}, "
            f"stdout={result.stdout!r}, stderr={result.stderr!r}"
        )


class TestPerFindingCounter:
    """Task 301 C2-006: Per-Finding-Counter (CC-009 Option b). pro
    `### F-<TAG>-<NNN>` Heading mindestens 1 evidence-Block.
    """

    def test_TC_301_finding_without_evidence_block_detected(
        self, tmp_path, fixture_source_hello, validator_cli
    ):
        """Task 301 C2-006: File mit 2 Findings, nur 1 hat evidence-Block →
        Validator MUST exit != 0 mit Finding-Counter-Hinweis.

        Phase: 301
        Level: L2 (Unit, CLI)
        Quelle: docs/tasks/301-delegation.md §2 C2-006
        evidence:
          - kind: file_range
            path: scripts/validate_evidence_pointers.py
            lines: 533-552
            quote: "count_finding_headings"
        """
        rel = fixture_source_hello.relative_to(tmp_path)
        body = (
            "---\n"
            "schema_version: 1\n"
            "evidence_layout: per_finding\n"
            "---\n"
            "\n"
            "### F-X-001: First finding\n"
            "- evidence:\n"
            f"    - kind: file_range\n"
            f"      path: {rel}\n"
            "      lines: 1-1\n"
            "      quote: \"Hello World\"\n"
            "\n"
            "### F-X-002: Second finding (NO evidence-block!)\n"
            "\n"
            "Some text without evidence.\n"
        )
        out = tmp_path / "missing_evidence.md"
        out.write_text(body, encoding="utf-8")
        result = validator_cli(out, cwd=tmp_path)
        assert result.returncode != 0, (
            f"Finding ohne evidence-Block MUST be detected. "
            f"rc={result.returncode}, stdout={result.stdout!r}, "
            f"stderr={result.stderr!r}"
        )
        # Hinweis-Text muss Finding-Counter-Diagnostic enthalten
        combined = (result.stdout + result.stderr).lower()
        assert "finding" in combined and "evidence" in combined, (
            f"Finding-Counter-Diagnostic fehlt. stdout+stderr={combined!r}"
        )

    def test_TC_301_all_findings_have_evidence_blocks_pass(
        self, tmp_path, fixture_source_hello, validator_cli
    ):
        """Regression: File mit 2 Findings + 2 evidence-Blocks passes."""
        rel = fixture_source_hello.relative_to(tmp_path)
        body = (
            "---\n"
            "schema_version: 1\n"
            "evidence_layout: per_finding\n"
            "---\n"
            "\n"
            "### F-X-001: First\n"
            "- evidence:\n"
            f"    - kind: file_range\n"
            f"      path: {rel}\n"
            "      lines: 1-1\n"
            "      quote: \"Hello World\"\n"
            "\n"
            "### F-X-002: Second\n"
            "- evidence:\n"
            f"    - kind: file_range\n"
            f"      path: {rel}\n"
            "      lines: 1-1\n"
            "      quote: \"Hello World\"\n"
        )
        out = tmp_path / "both_findings.md"
        out.write_text(body, encoding="utf-8")
        result = validator_cli(out, cwd=tmp_path)
        assert result.returncode == 0, (
            f"All-findings-with-evidence MUST pass. rc={result.returncode}, "
            f"stdout={result.stdout!r}, stderr={result.stderr!r}"
        )


class TestParseEvidenceBlockSingleRead:
    """Task 301 C2-005: parse_evidence_block accepts pre-loaded `content`
    so validate_file does not double-read.
    """

    def test_TC_301_parse_evidence_block_accepts_content_arg(
        self, tmp_path, fixture_source_hello
    ):
        """Task 301 C2-005: `content=` Argument erlaubt single-read-pattern.

        Phase: 301
        Level: L2 (Unit)
        Quelle: docs/tasks/301-delegation.md §2 C2-005
        evidence:
          - kind: file_range
            path: scripts/validate_evidence_pointers.py
            lines: 421-445
            quote: "content: str | None = None"
        """
        from scripts.validate_evidence_pointers import parse_evidence_block

        rel = fixture_source_hello.relative_to(tmp_path)
        content = (
            "---\n"
            "schema_version: 1\n"
            f"evidence:\n"
            f"  - kind: file_range\n"
            f"    path: {rel}\n"
            f"    lines: 1-1\n"
            f"    quote: \"Hello World\"\n"
            "---\n\nBody\n"
        )
        # Without content arg
        out = tmp_path / "ptr.md"
        out.write_text(content, encoding="utf-8")
        pointers_disk = parse_evidence_block(str(out), "auto")

        # With content arg — file_path can even be a non-existent path
        # because read is suppressed by `content` parameter.
        pointers_mem = parse_evidence_block(
            "/non/existent/path.md", "auto", content=content,
        )
        assert pointers_disk == pointers_mem, (
            f"content-arg parsing must equal disk-parsing. "
            f"disk={pointers_disk!r}, mem={pointers_mem!r}"
        )
