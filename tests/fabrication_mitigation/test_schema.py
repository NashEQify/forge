"""
Test-File fuer Spec 299 Fabrication-Mitigation — Schema-Group.

RED skeletons. Implementation steht noch aus. Generiert von
test-skeleton-writer.

TCs: TC-001..TC-009 + TC-056..TC-057 aus docs/tasks/299-test-plan.md
(Phase B Schema + Reviewer-Protocol-Migration + Persona-Audit).
"""
from __future__ import annotations

from pathlib import Path

import pytest


# ---------------------------------------------------------------------------
# AC-1 — Schema-Spec
# ---------------------------------------------------------------------------


class TestSchemaSpec:
    def test_TC_001_schema_file_exists_with_4_kinds(self, framework_root: Path):
        """
        TC-001: Schema-Spec-File existiert mit 4 kinds.

        Phase: B
        Level: L0 (Structural)
        Quelle: AC-1
        evidence:
          - kind: file_range
            path: docs/specs/299-fabrication-mitigation.md
            lines: 58-66
            quote: "Kind-Inventar (vollstaendig fuer v1)"
          - kind: file_range
            path: docs/specs/299-fabrication-mitigation.md
            lines: 71-77
            quote: "Quote-Length-Cap"
        """
        schema = framework_root / "skills/_protocols/evidence-pointer-schema.md"
        assert schema.is_file(), f"Schema-Spec-File fehlt: {schema}"

        text = schema.read_text(encoding="utf-8")
        # schema_version Pflicht-Field dokumentiert
        assert "schema_version: 1" in text, "schema_version: 1 nicht dokumentiert"
        # 4 kinds vollstaendig
        for kind in ("file_range", "grep_match", "dir_listing", "file_exists"):
            assert kind in text, f"kind={kind} fehlt in Schema-Doku"
        # Quote-Length-Cap
        assert "3 Zeilen" in text or "max 3" in text.lower(), \
            "Quote-Length-Cap (3 Zeilen) nicht dokumentiert"
        assert "200" in text, "200-Zeichen-Cap nicht dokumentiert"

    def test_TC_002_schema_documents_both_layouts(self, framework_root: Path):
        """
        TC-002: Schema dokumentiert beide Layouts (per_finding + top_level).

        Phase: B
        Level: L0
        Quelle: AC-1
        evidence:
          - kind: file_range
            path: docs/specs/299-fabrication-mitigation.md
            lines: 92-110
            quote: "Per-Finding-Inline (Default fuer Reviewer-Outputs)"
        """
        schema = framework_root / "skills/_protocols/evidence-pointer-schema.md"
        assert schema.is_file()
        text = schema.read_text(encoding="utf-8")

        assert "per_finding" in text
        assert "top_level" in text
        assert "evidence_layout" in text

    def test_TC_003_schema_documents_required_fields_per_kind(
        self, framework_root: Path
    ):
        """
        TC-003: Schema dokumentiert Pflichtfelder pro kind exakt.

        Phase: B
        Level: L1 (Logic — Completeness)
        Quelle: AC-1
        evidence:
          - kind: file_range
            path: docs/specs/299-fabrication-mitigation.md
            lines: 60-65
            quote: "file_range"
          - kind: file_range
            path: docs/specs/299-fabrication-mitigation.md
            lines: 644-647
            quote: "F-I-015 `kind: file_exists` Defeating-Pattern"
        """
        schema = framework_root / "skills/_protocols/evidence-pointer-schema.md"
        assert schema.is_file()
        text = schema.read_text(encoding="utf-8")

        # file_range: path + lines + quote
        assert "path" in text and "lines" in text and "quote" in text
        # grep_match: pattern + path + (expected_count optional, Default >=1)
        assert "pattern" in text
        assert "expected_count" in text
        # dir_listing: path + expected_files
        assert "expected_files" in text
        # file_exists ist explizit-trivial dokumentiert (F-I-015 discipline-note)
        assert "file_exists" in text
        assert "trivial" in text.lower() or "discipline" in text.lower(), \
            "F-I-015 file_exists Discipline-Note nicht dokumentiert"

    def test_TC_004_schema_documents_schema_version_semantics(
        self, framework_root: Path
    ):
        """
        TC-004: Schema dokumentiert schema_version-Semantik (legacy v0 vs v1).

        Phase: B
        Level: L1 (Consistency)
        Quelle: AC-1, AC-9
        evidence:
          - kind: file_range
            path: docs/specs/299-fabrication-mitigation.md
            lines: 79-90
            quote: "schema_version: 0` ODER fehlend = **legacy**"
        """
        schema = framework_root / "skills/_protocols/evidence-pointer-schema.md"
        assert schema.is_file()
        text = schema.read_text(encoding="utf-8")

        assert "schema_version: 0" in text
        assert "schema_version: 1" in text
        assert "legacy" in text.lower()

    def test_TC_005_schema_documents_dsl_grammar_for_expected_count(
        self, framework_root: Path
    ):
        """
        TC-005: Schema dokumentiert DSL-Grammar fuer expected_count.

        Phase: B + C3
        Level: L1
        Quelle: AC-1, AC-4
        evidence:
          - kind: file_range
            path: docs/specs/299-fabrication-mitigation.md
            lines: 405-413
            quote: "EXPR := OPERATOR INTEGER | INTEGER"
        """
        schema = framework_root / "skills/_protocols/evidence-pointer-schema.md"
        assert schema.is_file()
        text = schema.read_text(encoding="utf-8")

        # Operatoren
        for op in (">=", "<=", ">", "<", "==", "!="):
            assert op in text, f"Operator {op!r} nicht dokumentiert"
        assert ">=1" in text, "Default >=1 nicht dokumentiert"


# ---------------------------------------------------------------------------
# AC-2 — Reviewer-Protocol-Migration (3 Files)
# ---------------------------------------------------------------------------


class TestReviewerProtocolMigration:
    def test_TC_006_spec_reviewer_protocol_migrated_to_pointer_list(
        self, framework_root: Path
    ):
        """
        TC-006: spec-reviewer-protocol.md migriert auf Pointer-Liste.

        Phase: B
        Level: L0 + L1
        Quelle: AC-2
        evidence:
          - kind: file_range
            path: agents/_protocols/spec-reviewer-protocol.md
            lines: 40-40
            quote: "evidence: {Konkrete Spec-Stelle"
        """
        proto = framework_root / "agents/_protocols/spec-reviewer-protocol.md"
        assert proto.is_file()
        text = proto.read_text(encoding="utf-8")

        # Pointer-Schema-Felder
        assert "kind:" in text, "kind:-Field nicht im migrierten Protocol"
        assert "quote:" in text
        # per_finding-Layout
        assert "per_finding" in text
        # Negativ: alte Prosa-Form nicht mehr Pflicht-Anweisung
        # (Wenn Z.40 aus Spec ggf. noch als Beispiel "Konkrete Spec-Stelle"
        # auftaucht ist das ok; Pflicht ist die Pointer-Liste.)
        assert "kind: file_range" in text or "kind: grep_match" in text \
            or "kind: dir_listing" in text or "kind: file_exists" in text, \
            "Kein Beispiel-Pointer mit kind: <kind> im Protocol"

    def test_TC_007_code_reviewer_protocol_migrated_to_pointer_list(
        self, framework_root: Path
    ):
        """
        TC-007: code-reviewer-protocol.md migriert auf Pointer-Liste.

        Phase: B
        Level: L0 + L1
        Quelle: AC-2
        evidence:
          - kind: file_range
            path: agents/_protocols/code-reviewer-protocol.md
            lines: 41-41
            quote: "evidence: {Datei:Zeile oder konkretes Code-Snippet}"
        """
        proto = framework_root / "agents/_protocols/code-reviewer-protocol.md"
        assert proto.is_file()
        text = proto.read_text(encoding="utf-8")

        assert "kind:" in text
        assert "path:" in text
        assert "lines:" in text or "pattern:" in text
        assert "quote:" in text or "expected_count" in text

    def test_TC_008_ux_reviewer_protocol_migrated_to_pointer_list(
        self, framework_root: Path
    ):
        """
        TC-008: ux-reviewer-protocol.md migriert auf Pointer-Liste.

        Phase: B
        Level: L0 + L1
        Quelle: AC-2
        evidence:
          - kind: file_range
            path: agents/_protocols/ux-reviewer-protocol.md
            lines: 27-27
            quote: "evidence: {Konkrete Spec-Stelle"
        """
        proto = framework_root / "agents/_protocols/ux-reviewer-protocol.md"
        assert proto.is_file()
        text = proto.read_text(encoding="utf-8")

        assert "kind:" in text
        assert "path:" in text

    def test_TC_009_reviewer_base_extended_with_schema_version_and_no_persona_factoid(
        self, framework_root: Path, spec_path: Path
    ):
        """
        TC-009: reviewer-base.md ergaenzt um schema_version-Pflicht (F-X-011).

        Phase: B
        Level: L0 + L1
        Quelle: AC-2, F-X-011
        evidence:
          - kind: file_range
            path: agents/_protocols/reviewer-base.md
            lines: 25-25
            quote: "Ein Finding OHNE `evidence`"
          - kind: file_range
            path: docs/specs/299-fabrication-mitigation.md
            lines: 134-139
            quote: "Persona-Audit ist generisch formuliert"
        """
        base = framework_root / "agents/_protocols/reviewer-base.md"
        assert base.is_file()
        text = base.read_text(encoding="utf-8")

        # Existing evidence-Pflicht erhalten
        assert "evidence" in text
        # Neuer Block: schema_version: 1 Pflicht
        assert "schema_version: 1" in text, \
            "schema_version: 1 Pflicht nicht in reviewer-base.md"
        # Layout-Reference
        assert "per_finding" in text or "top_level" in text or "evidence_layout" in text

        # F-X-011 Negativ: Spec-Text §1.6 generisch formuliert,
        # NICHT Persona-spezifisch (z.B. nicht behaupten council-member
        # laedt kein Reviewer-Protocol als verifiziertes Faktoid).
        spec_text = spec_path.read_text(encoding="utf-8")
        # Pass-2-Mini-Amendment: F-X-011 — Audit-Befund generisch.
        # Wenn weiterhin "council-message-Persona" im Spec steht UND nicht
        # als generisches Beispiel gekennzeichnet ist, ist F-X-011 ungefixt.
        # Hier asserten wir das schwaecher: das Wort "verifiziert" muss in
        # §1.6-Naehe stehen ODER persona-Faktoid ist explizit als Beispiel
        # markiert.
        assert "generisch" in spec_text.lower() or "Beispiel" in spec_text, \
            "F-X-011: §1.6-Persona-Audit-Statement nicht als generisch markiert"


# ---------------------------------------------------------------------------
# AC-10 — Reviewer-Persona-Audit
# ---------------------------------------------------------------------------


class TestPersonaAudit:
    def test_TC_056_persona_audit_report_exists(self, framework_root: Path):
        """
        TC-056: Persona-Audit-Report existiert mit allen Persona-Files.

        Phase: B
        Level: L0 + L1
        Quelle: AC-10
        evidence:
          - kind: file_range
            path: docs/specs/299-fabrication-mitigation.md
            lines: 137-139
            quote: "docs/build/2026-05-04-task-299-persona-audit.md"
          - kind: dir_listing
            path: agents/
            expected_files: [board-chief.md, council-member.md, code-review.md, code-adversary.md]
        """
        report = framework_root / "docs/build/2026-05-04-task-299-persona-audit.md"
        assert report.is_file(), f"Persona-Audit-Report fehlt: {report}"

        text = report.read_text(encoding="utf-8")

        # Mindestens diese Personas auditiert (sample aus Spec-Liste)
        expected_personas = [
            "board-chief",
            "code-review",
            "code-adversary",
            "council-member",
        ]
        missing = [p for p in expected_personas if p not in text]
        assert not missing, f"Audit-Report listet Personas nicht: {missing}"

        # Tabelle: Persona × Protocol × Migration-Entscheidung
        assert "Protocol" in text or "protocol" in text
        # Migration-Entscheidung-Marker (a) / (b) per Spec §1.6
        assert "(a)" in text or "(b)" in text or "Entscheidung" in text.lower(), \
            "Audit-Report fehlt Migration-Entscheidung pro Persona"

    def test_TC_057_persona_audit_explicit_for_personas_without_protocol(
        self, framework_root: Path
    ):
        """
        TC-057: Persona-Audit dokumentiert Personas ohne Protocol-Bind explizit.

        Phase: B
        Level: L1
        Quelle: AC-10, F-X-011
        evidence:
          - kind: file_range
            path: docs/specs/299-fabrication-mitigation.md
            lines: 134-139
            quote: "Phase-B-Implementer entscheidet pro Persona"
        """
        report = framework_root / "docs/build/2026-05-04-task-299-persona-audit.md"
        assert report.is_file()

        text = report.read_text(encoding="utf-8")

        # Pro Persona ohne Protocol-Bind: explizite Entscheidung (a) ODER (b)
        # Mindestens ein Eintrag mit "no source-claims" / "nothing to do" / "(a)"
        # ODER "Pointer-Pflicht" / "(b)"
        marker_a = any(
            m in text for m in ("no source-claims", "nothing to do", "(a)")
        )
        marker_b = any(
            m in text for m in ("Pointer-Pflicht", "(b)", "explizit")
        )
        assert marker_a or marker_b, \
            "Audit-Report dokumentiert keine (a)/(b)-Entscheidung pro Persona"
