"""
Test-File fuer Spec 299 Fabrication-Mitigation — Eval-Cases-Group + Performance.

RED skeletons. Implementation steht noch aus.

TCs: TC-050 (Performance Engine), TC-052..TC-055 (synth Eval-Set AC-9)
aus docs/tasks/299-test-plan.md.

Eval-Mapping (Spec §10):
- Eval 1 (Quote-Mismatch) → TC-026 (in test_validator.py)
- Eval 2 (Range-Overflow) → TC-027 (in test_validator.py)
- Eval 3 (Valid Pointer) → TC-025 (in test_validator.py)
- Eval 4 (Pattern-Match Count) → TC-028 (in test_validator.py)
- Eval 5 (Legacy Backward-Compat) → TC-029 (in test_validator.py)
- Eval 6 (Misinterpretation) → TC-031 (in test_validator.py)

Hier: AC-9 synth Eval-Set (5 Cases) + Adversarial Variants + Performance.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest


class TestPerformance:
    @pytest.mark.skip(reason="Perf-Test braucht Engine-Bench-Setup — "
                              "Skeleton bleibt RED; Implementer aktiviert.")
    def test_TC_050_engine_check_under_10pct_overhead(self, framework_root: Path):
        """
        TC-050: Engine-Check + Hook-Latency unter 10% Mehrkosten (AC-8).

        Phase: G
        Level: L5 (Performance, periodisch)
        Quelle: AC-8
        evidence:
          - kind: file_range
            path: docs/specs/299-fabrication-mitigation.md
            lines: 477-479
            quote: "Engine-Check + Hook-Latency unter 10% Mehrkosten"
        """
        # baseline = time_step_run_without_pointer_check()
        # with_check = time_step_run_with_pointer_check()
        # ratio = (with_check - baseline) / baseline
        # assert ratio < 0.10
        assert False, "RED skeleton — perf-bench braucht Engine-Setup"


class TestSynthEvalSet:
    def test_TC_052_synth_legacy_only_file_exists_passes_with_discipline_note(
        self, framework_root: Path, validator_cli, tmp_path: Path
    ):
        """
        TC-052: Synthetic-Legacy-Output durchlaeuft ohne BLOCK
        (Defeating-Pattern fuer file_exists, F-I-015).

        Phase: G
        Level: L3 (Integration, Synthetic)
        Quelle: AC-9, F-I-015
        Adversary-Target: Smart-but-Wrong (F-I-015)
        evidence:
          - kind: file_range
            path: docs/specs/299-fabrication-mitigation.md
            lines: 644-645
            quote: "Discipline-Note in Schema-Doku"
        """
        # Output mit nur file_exists Pointers (mechanisch valid, disziplinarisch
        # anti-pattern).
        target = tmp_path / "real_file.md"
        target.write_text("body\n", encoding="utf-8")

        out = tmp_path / "only_file_exists.md"
        out.write_text(
            "---\nschema_version: 1\nevidence:\n"
            "  - kind: file_exists\n"
            f"    path: {target.name}\n---\nbody\n",
            encoding="utf-8",
        )
        result = validator_cli(out, cwd=tmp_path)
        # Mechanisch pass
        assert result.returncode == 0, \
            f"file_exists-only sollte mechanisch pass: {result.returncode}"

        # Discipline-Note in Schema-Doku dokumentiert
        schema = framework_root / "skills/_protocols/evidence-pointer-schema.md"
        assert schema.is_file()
        text = schema.read_text(encoding="utf-8")
        assert "trivial" in text.lower() or "discipline" in text.lower() \
            or "F-I-015" in text, \
            "F-I-015 Discipline-Note fehlt in Schema-Doku"

    def test_TC_053_path_traversal_dotdot_blocked(
        self, framework_root: Path, validator_cli, tmp_path: Path
    ):
        """
        TC-053: Path-Traversal-Adversary path: "../../etc/passwd" → block ODER
        sandboxed.

        Phase: G
        Level: L5 (Adversarial)
        Quelle: Adversary, §1.3
        Adversary-Target: Path-Traversal
        evidence:
          - kind: file_range
            path: docs/specs/299-fabrication-mitigation.md
            lines: 75-76
            quote: "Path-Format:** repo-relativ, ohne `./`-Prefix"
        """
        # Pre-Gate: validator-CLI muss existieren. Sonst PASSiert Test trivial
        # via subprocess-FileNotFound (returncode != 0).
        validator_path = framework_root / "scripts/validate_evidence_pointers.py"
        assert validator_path.is_file(), \
            "Pre-Gate: scripts/validate_evidence_pointers.py muss existieren " \
            "(sonst returnt subprocess-Aufruf trivial != 0 — Test ist " \
            "trivially PASS)"

        out = tmp_path / "traversal.md"
        out.write_text(
            "---\nschema_version: 1\nevidence:\n"
            "  - kind: file_exists\n"
            '    path: "../../etc/passwd"\n---\nbody\n',
            encoding="utf-8",
        )
        result = validator_cli(out, cwd=tmp_path)
        # Strenger: Validator-Aufruf muss tatsaechlich gestartet sein
        # (nicht subprocess-spawn-Error). Pruefen via stderr-Inhalt:
        # Trivial-Fail: "No such file or directory: 'validate_evidence...'"
        # Echter Fail: validator-output ueber path-traversal.
        combined = (result.stdout + result.stderr).lower()
        assert "no such file or directory" not in combined or \
               "evidence" in combined or "pointer" in combined, \
            f"Validator-CLI nicht gestartet — Trivial-Pass: {combined!r}"
        assert result.returncode != 0, \
            f"path-traversal MUSS blocken (exit != 0): got {result.returncode}"
        assert "outside" in combined or "repo" in combined \
            or "traversal" in combined or "boundary" in combined \
            or "path" in combined, \
            f"path-traversal fail-reason unklar: {combined!r}"

    def test_TC_054_multiline_quote_just_over_cap_blocks(
        self, framework_root: Path, validator_cli, fixture_source_hello: Path,
        tmp_path: Path
    ):
        """
        TC-054: Multi-Line-Quote knapp ueber Cap (3 Zeilen + 1 Char ODER 4 Zeilen)
        → block.

        Phase: G
        Level: L5 (Boundary, Adversarial)
        Quelle: §1.3, AC-4
        Adversary-Target: Quote-Cap-Bypass
        evidence:
          - kind: file_range
            path: docs/specs/299-fabrication-mitigation.md
            lines: 72-72
            quote: "<= 3 Zeilen UND <= 200 Zeichen"
        """
        rel = fixture_source_hello.relative_to(tmp_path)
        # 4-zeilig (1 ueber Cap)
        out = tmp_path / "cap_violation.md"
        out.write_text(
            "---\nschema_version: 1\nevidence:\n"
            "  - kind: file_range\n"
            f"    path: {rel}\n"
            "    lines: 1-1\n"
            '    quote: "l1\\nl2\\nl3\\nl4"\n---\nbody\n',
            encoding="utf-8",
        )
        result = validator_cli(out, cwd=tmp_path)
        assert result.returncode == 1, \
            f"4-line quote MUSS blocken: got {result.returncode}"

        # 201 Zeichen (1 ueber Cap)
        out2 = tmp_path / "cap_chars.md"
        out2.write_text(
            "---\nschema_version: 1\nevidence:\n"
            "  - kind: file_range\n"
            f"    path: {rel}\n"
            "    lines: 1-1\n"
            f'    quote: "{"x" * 201}"\n---\nbody\n',
            encoding="utf-8",
        )
        result2 = validator_cli(out2, cwd=tmp_path)
        assert result2.returncode == 1, \
            f"201-char quote MUSS blocken: got {result2.returncode}"

    def test_TC_055_synth_eval_set_5_legacy_cases_all_pass(
        self, framework_root: Path, validator_cli, tmp_path: Path
    ):
        """
        TC-055: Synthetic Eval-Set 5 Cases parallel (AC-9 Pflicht).

        Phase: G
        Level: L3
        Quelle: AC-9
        evidence:
          - kind: file_range
            path: docs/specs/299-fabrication-mitigation.md
            lines: 482-485
            quote: "mindest 5 konstruierte Legacy"
        """
        cases = []

        # Case 1: schema_version: 0
        c1 = tmp_path / "c1.md"
        c1.write_text("---\nschema_version: 0\nevidence: []\n---\n", encoding="utf-8")
        cases.append(c1)

        # Case 2: kein schema_version-Field
        c2 = tmp_path / "c2.md"
        c2.write_text("---\n# nichts\n---\nbody\n", encoding="utf-8")
        cases.append(c2)

        # Case 3: schema_version: 0 + leeres evidence
        c3 = tmp_path / "c3.md"
        c3.write_text("---\nschema_version: 0\nevidence: []\n---\n", encoding="utf-8")
        cases.append(c3)

        # Case 4: schema_version: 0 + fabricated evidence
        c4 = tmp_path / "c4.md"
        c4.write_text(
            "---\nschema_version: 0\nevidence:\n"
            "  - kind: file_range\n"
            "    path: nonexistent.md\n"
            "    lines: 1-1\n"
            '    quote: "fabricated"\n---\nbody\n',
            encoding="utf-8",
        )
        cases.append(c4)

        # Case 5: Pre-Spec-299-Format ohne evidence-Block
        c5 = tmp_path / "c5.md"
        c5.write_text("---\ntitle: pre-spec-299\n---\nbody\n", encoding="utf-8")
        cases.append(c5)

        for case in cases:
            result = validator_cli(case, cwd=tmp_path)
            assert result.returncode == 0, \
                f"Legacy-Case {case.name} MUSS exit 0: got {result.returncode}, " \
                f"stderr={result.stderr!r}"
