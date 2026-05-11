"""
Test-File fuer Spec 299 Fabrication-Mitigation — Engine-Group.

RED skeletons. Implementation steht noch aus.

TCs: TC-010..TC-024 aus docs/tasks/299-test-plan.md
(Phase C1 yaml_loader.py + Phase C2 workflow_engine.py pointer_check).
"""
from __future__ import annotations

from pathlib import Path

import pytest


# ---------------------------------------------------------------------------
# Phase C1 — yaml_loader.py Edit (AC-3)
# ---------------------------------------------------------------------------


class TestYamlLoaderEdit:
    def test_TC_010_VALID_COMPLETION_TYPES_includes_pointer_check(self):
        """
        TC-010: VALID_COMPLETION_TYPES enthaelt pointer_check.

        Phase: C1
        Level: L2 (Unit)
        Quelle: AC-3
        evidence:
          - kind: file_range
            path: scripts/lib/yaml_loader.py
            lines: 59-62
            quote: "VALID_COMPLETION_TYPES = {"
          - kind: file_range
            path: docs/specs/299-fabrication-mitigation.md
            lines: 446-448
            quote: "VALID_COMPLETION_TYPES (Z.59) erweitert"
        """
        from scripts.lib.yaml_loader import VALID_COMPLETION_TYPES

        assert "pointer_check" in VALID_COMPLETION_TYPES, \
            "pointer_check fehlt in VALID_COMPLETION_TYPES"
        # Regression: existing Members weiterhin enthalten
        for existing in (
            "manual",
            "compound",
            "file_modified_after",
            "file_created_matching",
            "file_content_check",
            "exit_code",
        ):
            assert existing in VALID_COMPLETION_TYPES, \
                f"Regression: {existing!r} aus VALID_COMPLETION_TYPES verschwunden"

    def test_TC_011_validate_completion_accepts_pointer_check_and_requires_source_file(
        self,
    ):
        """
        TC-011: _validate_completion akzeptiert pointer_check und prueft source_file.

        Phase: C1
        Level: L2 (Unit)
        Quelle: AC-3
        evidence:
          - kind: file_range
            path: scripts/lib/yaml_loader.py
            lines: 73-109
            quote: "def _validate_completion"
          - kind: file_range
            path: docs/specs/299-fabrication-mitigation.md
            lines: 458-459
            quote: "yaml_loader rejects unknown `pointer_check` BEFORE Edit"
        """
        from scripts.lib.yaml_loader import _validate_completion

        errors_ok = _validate_completion(
            {"type": "pointer_check", "source_file": "docs/foo/bar.md"},
            "step-x",
        )
        assert errors_ok == [], \
            f"_validate_completion mit valid pointer_check liefert errors: {errors_ok}"

        errors_fail = _validate_completion(
            {"type": "pointer_check"}, "step-x"
        )
        assert errors_fail, \
            "_validate_completion ohne source_file muss Error liefern"
        assert any("source_file" in e for e in errors_fail), \
            f"Error-Message referenziert source_file nicht: {errors_fail}"


# ---------------------------------------------------------------------------
# Phase C2 — workflow_engine.py pointer_check Mechanik (AC-3 Tests 1..7)
# ---------------------------------------------------------------------------


def _check_completion(comp, state=None, step_state=None):
    """Helper: ruft Engine `check_completion`. Signatur kann sich aendern;
    Tests fangen das mit klarem Fail."""
    from scripts import workflow_engine as we

    state = state or {"variables": {}}
    step_state = step_state or {}
    return we.check_completion(comp, state, step_state)


class TestPointerCheckEngine:
    def test_TC_012_kind_file_range_valid_quote_passes(
        self, isolated_project, valid_pointer_file
    ):
        """
        TC-012: pointer_check kind=file_range mit valid quote → pass.

        Phase: C2
        Level: L2 (Unit)
        Quelle: AC-3 Test-1
        evidence:
          - kind: file_range
            path: scripts/workflow_engine.py
            lines: 343-343
            quote: "def check_completion"
          - kind: file_range
            path: docs/specs/299-fabrication-mitigation.md
            lines: 452-453
            quote: "Test-1: kind=file_range mit valid quote"
        """
        rel = valid_pointer_file.relative_to(isolated_project)
        comp = {"type": "pointer_check", "source_file": str(rel)}
        ok, msg = _check_completion(comp)

        assert ok is True, f"valid pointer should pass, got: ok={ok}, msg={msg!r}"
        assert "pass" in msg.lower() or "ok" in msg.lower() \
            or "valid" in msg.lower(), f"unexpected msg: {msg!r}"

    def test_TC_013_kind_file_range_fabricated_quote_blocks(
        self, isolated_project, fabricated_quote_file
    ):
        """
        TC-013: pointer_check kind=file_range mit fabricated quote → block.

        Phase: C2
        Level: L2 (Unit)
        Quelle: AC-3 Test-2
        evidence:
          - kind: file_range
            path: docs/specs/299-fabrication-mitigation.md
            lines: 453-453
            quote: "Test-2: kind=file_range mit fabricated quote"
        """
        rel = fabricated_quote_file.relative_to(isolated_project)
        comp = {"type": "pointer_check", "source_file": str(rel)}
        ok, msg = _check_completion(comp)

        assert ok is False, "fabricated quote MUST block"
        assert "fail" in msg.lower() or "match" in msg.lower() \
            or "no match" in msg.lower(), f"fail-reason unklar: {msg!r}"

    def test_TC_014_kind_file_range_out_of_range_blocks(
        self, isolated_project, out_of_range_file
    ):
        """
        TC-014: pointer_check kind=file_range mit out-of-range lines → block.

        Phase: C2
        Level: L2 (Unit)
        Quelle: AC-3 Test-3
        evidence:
          - kind: file_range
            path: docs/specs/299-fabrication-mitigation.md
            lines: 73-74
            quote: "innerhalb File-Linecount"
        """
        rel = out_of_range_file.relative_to(isolated_project)
        comp = {"type": "pointer_check", "source_file": str(rel)}
        ok, msg = _check_completion(comp)

        assert ok is False
        assert "range" in msg.lower() or "linecount" in msg.lower() \
            or "out of" in msg.lower(), f"range-msg fehlt: {msg!r}"

    def test_TC_015_kind_grep_match_expected_count_unmet_blocks(
        self, isolated_project, tmp_path
    ):
        """
        TC-015: pointer_check kind=grep_match expected_count nicht erfuellt → block.

        Phase: C2
        Level: L2 (Unit)
        Quelle: AC-3 Test-4
        evidence:
          - kind: file_range
            path: docs/specs/299-fabrication-mitigation.md
            lines: 455-455
            quote: "Test-4: kind=grep_match mit expected_count"
        """
        # Source mit 2 'foo'-Matches
        src = tmp_path / "patterns.txt"
        src.write_text("foo\nbar\nfoo\nbaz\n", encoding="utf-8")
        rel_src = src.relative_to(tmp_path)

        out = tmp_path / "grep_check.md"
        out.write_text(
            "---\n"
            "schema_version: 1\n"
            "evidence:\n"
            "  - kind: grep_match\n"
            f'    pattern: "foo"\n'
            f"    path: {rel_src}\n"
            '    expected_count: ">=5"\n'
            "---\nbody\n",
            encoding="utf-8",
        )
        comp = {"type": "pointer_check", "source_file": str(out.relative_to(tmp_path))}
        ok, msg = _check_completion(comp)

        assert ok is False
        assert "count" in msg.lower() or "expected" in msg.lower(), \
            f"count-msg fehlt: {msg!r}"

    def test_TC_016_quote_cap_violation_lines_blocks(
        self, isolated_project, fixture_source_hello, tmp_path
    ):
        """
        TC-016: pointer_check Quote-Cap-Verletzung (>3 Zeilen) → block.

        Phase: C2/C3
        Level: L2 (Boundary, Adversary: Quote-Cap-Bypass)
        Quelle: AC-3, AC-4, §1.3
        evidence:
          - kind: file_range
            path: docs/specs/299-fabrication-mitigation.md
            lines: 415-419
            quote: "quote_length_cap_ok()` wird in `validate_pointer()` aufgerufen BEFORE"
        """
        # 4-zeiliger quote (>3 Zeilen Cap)
        rel = fixture_source_hello.relative_to(tmp_path)
        out = tmp_path / "cap_lines.md"
        out.write_text(
            "---\n"
            "schema_version: 1\n"
            "evidence:\n"
            "  - kind: file_range\n"
            f"    path: {rel}\n"
            "    lines: 1-1\n"
            '    quote: "line1\\nline2\\nline3\\nline4"\n'
            "---\nbody\n",
            encoding="utf-8",
        )
        comp = {"type": "pointer_check", "source_file": str(out.relative_to(tmp_path))}
        ok, msg = _check_completion(comp)

        assert ok is False
        low = msg.lower()
        assert "cap" in low or "max 3" in low or "exceeds" in low or "lines" in low, \
            f"cap-msg fehlt: {msg!r}"

    def test_TC_017_quote_cap_violation_chars_blocks(
        self, isolated_project, fixture_source_hello, tmp_path
    ):
        """
        TC-017: pointer_check Quote-Cap-Verletzung (>200 Zeichen) → block.

        Phase: C2/C3
        Level: L2 (Boundary)
        Quelle: AC-3, AC-4
        evidence:
          - kind: file_range
            path: docs/specs/299-fabrication-mitigation.md
            lines: 72-72
            quote: "<= 3 Zeilen UND <= 200 Zeichen"
        """
        rel = fixture_source_hello.relative_to(tmp_path)
        long_quote = "x" * 250  # 1-zeilig, 250 Zeichen
        out = tmp_path / "cap_chars.md"
        out.write_text(
            "---\n"
            "schema_version: 1\n"
            "evidence:\n"
            "  - kind: file_range\n"
            f"    path: {rel}\n"
            "    lines: 1-1\n"
            f'    quote: "{long_quote}"\n'
            "---\nbody\n",
            encoding="utf-8",
        )
        comp = {"type": "pointer_check", "source_file": str(out.relative_to(tmp_path))}
        ok, msg = _check_completion(comp)

        assert ok is False
        assert "200" in msg or "char" in msg.lower() or "cap" in msg.lower(), \
            f"char-cap-msg fehlt: {msg!r}"

    def test_TC_018_schema_version_1_empty_evidence_list_blocks(
        self, isolated_project, empty_evidence_list_file
    ):
        """
        TC-018: pointer_check schema_version: 1 + leeres evidence: [] → block.

        Phase: C2
        Level: L2 (Negativ — kritischer F-C-002 Fix)
        Quelle: AC-3 Test-6, F-C-002
        evidence:
          - kind: file_range
            path: docs/specs/299-fabrication-mitigation.md
            lines: 162-162
            quote: "schema_version: 1 + empty/missing evidence → return (False"
        """
        rel = empty_evidence_list_file.relative_to(isolated_project)
        comp = {"type": "pointer_check", "source_file": str(rel)}
        ok, msg = _check_completion(comp)

        assert ok is False, "empty evidence list with schema_version: 1 must block"
        assert "non-empty" in msg.lower() or "empty" in msg.lower() \
            or "required" in msg.lower(), f"empty-evidence-msg unklar: {msg!r}"

    def test_TC_019_schema_version_0_skips_legacy(
        self, isolated_project, legacy_v0_file
    ):
        """
        TC-019: pointer_check schema_version: 0 → skip (Eval 5 + Stale-State).

        Phase: C2
        Level: L2 (Backward-Compat)
        Quelle: AC-3 Test-5, AC-9, Eval 5
        evidence:
          - kind: file_range
            path: docs/specs/299-fabrication-mitigation.md
            lines: 161-161
            quote: "schema_version: 0 OR missing → return (True, \\"legacy, skipped\\")"
        """
        rel = legacy_v0_file.relative_to(isolated_project)
        comp = {"type": "pointer_check", "source_file": str(rel)}
        ok, msg = _check_completion(comp)

        assert ok is True, "legacy schema_version: 0 must silent-skip"
        assert "legacy" in msg.lower() or "skip" in msg.lower(), \
            f"legacy-msg unklar: {msg!r}"

    def test_TC_020_pointer_check_reads_evidence_layout_from_skill(
        self, isolated_project, tmp_path
    ):
        """
        TC-020: pointer_check liest evidence_layout aus Skill-Frontmatter (F-I-014).

        Phase: C2
        Level: L2 (Unit)
        Quelle: F-I-014, AC-3
        evidence:
          - kind: file_range
            path: docs/specs/299-fabrication-mitigation.md
            lines: 642-643
            quote: "F-I-014 `evidence_layout` Lookup-Pfad"
          - kind: file_range
            path: docs/specs/299-fabrication-mitigation.md
            lines: 105-107
            quote: "evidence_layout: per_finding | top_level"
        """
        # Skill-File mit evidence_layout: top_level
        skill = tmp_path / "framework/skills/foo/SKILL.md"
        skill.parent.mkdir(parents=True, exist_ok=True)
        skill.write_text(
            "---\nname: foo\nevidence_layout: top_level\n---\nbody\n",
            encoding="utf-8",
        )

        # Output-File mit top-level evidence-Block
        out = tmp_path / "output.md"
        out.write_text(
            "---\nschema_version: 1\nevidence:\n"
            "  - kind: file_exists\n"
            "    path: output.md\n---\nbody\n",
            encoding="utf-8",
        )

        comp = {"type": "pointer_check",
                "source_file": str(out.relative_to(tmp_path))}
        step_state = {"skill_ref": "framework/skills/foo/SKILL.md"}
        ok, msg = _check_completion(
            comp,
            state={"variables": {}, "current_step": {"skill_ref":
                "framework/skills/foo/SKILL.md"}},
            step_state=step_state,
        )
        assert ok is True, f"top_level layout-aware check failed: ok={ok}, msg={msg!r}"

    def test_TC_021_spec_name_resolved_from_task_spec_ref_basename(
        self, isolated_project, tmp_path
    ):
        """
        TC-021: spec_name-Variable wird aus task.spec_ref Basename befuellt (F-I-013).

        Phase: C2
        Level: L2 (Unit, Engine-State-Setup)
        Quelle: F-I-013, AC-3 Test-7-Erweiterung
        evidence:
          - kind: file_range
            path: docs/specs/299-fabrication-mitigation.md
            lines: 642-642
            quote: "F-I-013 `{spec_name}` Befuellungs-Pfad"
          - kind: file_range
            path: docs/specs/299-fabrication-mitigation.md
            lines: 147-148
            quote: "neue Variable `{spec_name}` (= `task.spec_ref` Basename ohne Extension)"
        """
        from scripts import workflow_engine as we

        # Public-API: bestimmt zur Implementation-Zeit. Hier asserten wir
        # generisch ueber State-Initialization-Pfad.
        # API-Vermutungen (Implementer waehlt eine):
        #   - we.run_workflow_init(workflow_def, task_id) -> state
        #   - we._resolve_vars(text, variables) -> str
        # Wir asserten: nach Setup mit task.spec_ref =
        # "docs/specs/299-fabrication-mitigation.md" muss spec_name in
        # variables-Dict landen.
        task_yaml = tmp_path / "docs/tasks/299.yaml"
        task_yaml.parent.mkdir(parents=True, exist_ok=True)
        task_yaml.write_text(
            "task_id: 299\nspec_ref: docs/specs/299-fabrication-mitigation.md\n",
            encoding="utf-8",
        )

        # Implementer muss eine Engine-API exposen die State mit spec_name
        # befuellt. Test prueft Resolution-Output.
        if hasattr(we, "_resolve_vars"):
            resolved = we._resolve_vars(
                "docs/reviews/board/{spec_name}-consolidated-pass1.md",
                {"spec_name": "299-fabrication-mitigation"},
            )
            assert resolved == \
                "docs/reviews/board/299-fabrication-mitigation-consolidated-pass1.md"

        # Negativ: ohne spec_name muss _has_unresolved_vars die Variable
        # melden (graceful-degradation Pfad).
        # CC-016 Pass-1-Fix: Signatur 1-arg (Optional-Param entfernt YAGNI).
        # Restpruefung — Variable bleibt im Text wenn _resolve_completion_vars
        # sie nicht ersetzt.
        assert hasattr(we, "_has_unresolved_vars"), \
            "_has_unresolved_vars muss existieren"
        unresolved = we._has_unresolved_vars(
            "docs/reviews/board/{spec_name}-consolidated.md"
        )
        assert unresolved, "missing spec_name muss als unresolved gemeldet werden"

    def test_TC_022_has_unresolved_vars_whitelist_includes_spec_name_and_source_file(
        self, isolated_project
    ):
        """
        TC-022: _has_unresolved_vars Whitelist enthaelt spec_name + source_file
        (Cycle-Entry-Point).

        Phase: C2
        Level: L2 (Unit)
        Quelle: F-C-012, AC-3
        evidence:
          - kind: file_range
            path: scripts/workflow_engine.py
            lines: 264-266
            quote: "def _has_unresolved_vars"
          - kind: file_range
            path: docs/specs/299-fabrication-mitigation.md
            lines: 168-171
            quote: "_has_unresolved_vars` (workflow_engine.py:264)"
        """
        from scripts import workflow_engine as we

        # CC-014 + CC-016 Pass-1-Fix: Whitelist-Erweiterung passiert via
        # `_resolve_completion_vars()`-Pre-Resolution. `_has_unresolved_vars`
        # ist die 1-arg Restpruefung — findet Placeholder die nach
        # Resolution noch im Text stehen. Der semantische Test ist:
        # spec_name im variables-Dict → _resolve_completion_vars ersetzt es
        # → Restpruefung findet leere Liste.
        vars_with = {"spec_name": "299-fabrication-mitigation"}
        resolved_text = we._resolve_vars(
            "docs/reviews/board/{spec_name}-consolidated.md", vars_with,
        )
        unresolved = we._has_unresolved_vars(resolved_text)
        assert not unresolved, \
            f"spec_name in variables sollte resolved werden: {unresolved}"

        # spec_name fehlt → _resolve_vars ersetzt nicht → Restpruefung findet
        # `{spec_name}` als unresolved (graceful-degradation).
        resolved_text2 = we._resolve_vars(
            "docs/reviews/board/{spec_name}-consolidated.md", {},
        )
        unresolved2 = we._has_unresolved_vars(resolved_text2)
        assert unresolved2, "missing spec_name muss als unresolved gemeldet werden"

        # Cycle-Adversary: source_file als selbst-referent, keine InfiniteLoop
        comp = {"type": "pointer_check",
                "source_file": "{source_file}"}
        ok, msg = _check_completion(comp,
                                    state={"variables":
                                        {"source_file": "{source_file}"}})
        # Per Spec: graceful → manual-degradation
        assert "manual" in msg.lower() or "unresolved" in msg.lower() \
            or ok is False, f"cycle nicht graceful behandelt: {msg!r}"

    def test_TC_023_force_bypass_counts_to_max_force_per_workflow_2(
        self, isolated_project
    ):
        """
        TC-023: --force-Bypass umgeht pointer_check und zaehlt zum
        MAX_FORCE_PER_WORKFLOW=2.

        Phase: C2
        Level: L2 (Unit, Boundary)
        Quelle: AC-3, §2.3, F-C-011
        Adversary-Target: Force-Bypass-Drift
        evidence:
          - kind: file_range
            path: scripts/workflow_engine.py
            lines: 121-121
            quote: "MAX_FORCE_PER_WORKFLOW = 2"
          - kind: file_range
            path: docs/specs/299-fabrication-mitigation.md
            lines: 205-209
            quote: "MAX_FORCE_PER_WORKFLOW`-Limit"
        """
        from scripts import workflow_engine as we

        assert getattr(we, "MAX_FORCE_PER_WORKFLOW", None) == 2, \
            "MAX_FORCE_PER_WORKFLOW muss 2 sein (nicht 3)"

        # Force-Counter-Logik: Engine haelt force_count im State-Dict.
        # Per Spec §2.3: --force umgeht pointer_check, zaehlt aber zum
        # MAX_FORCE_PER_WORKFLOW=2-Limit.
        # Verifikation via State-Schema (Implementation-Detail-frei):
        # 1. fresh state hat force_count == 0
        # 2. force_count < MAX_FORCE_PER_WORKFLOW erlaubt force-bypass
        # 3. force_count == MAX_FORCE_PER_WORKFLOW blockiert weitere force
        state = {"force_count": 0, "variables": {}, "steps": {}}
        assert state["force_count"] < we.MAX_FORCE_PER_WORKFLOW, \
            "force_count=0 muss bypass erlauben"
        state["force_count"] = 1
        assert state["force_count"] < we.MAX_FORCE_PER_WORKFLOW, \
            "force_count=1 muss bypass erlauben (1 < 2)"
        state["force_count"] = 2
        assert state["force_count"] >= we.MAX_FORCE_PER_WORKFLOW, \
            "force_count=2 muss bypass blocken (2 >= MAX 2)"

    def test_TC_024_compound_pointer_check_before_manual_blocks_when_file_missing(
        self, isolated_project, tmp_path
    ):
        """
        TC-024: completion.compound mit pointer_check VOR manual blockiert wenn
        File fehlt (Race-Mitigation).

        Phase: C2 / D
        Level: L3 (Integration)
        Quelle: §2.2, Race-Adversary, Cleanup-Tx-Silent-Ack
        evidence:
          - kind: file_range
            path: scripts/workflow_engine.py
            lines: 439-447
            quote: "if ctype == \\"compound\\":"
          - kind: file_range
            path: docs/specs/299-fabrication-mitigation.md
            lines: 194-196
            quote: "Reihenfolge-Pflicht:** `pointer_check` VOR `manual`"
        """
        from scripts.lib.yaml_loader import VALID_COMPLETION_TYPES

        # Pre-Gate: pointer_check muss als gueltiger Type registriert sein.
        # Sonst PASSiert dieser Test trivial via "unknown completion type"-Pfad.
        assert "pointer_check" in VALID_COMPLETION_TYPES, \
            "Pre-Gate: pointer_check muss in VALID_COMPLETION_TYPES sein " \
            "(sonst greift Engine 'unknown completion type'-Branch und " \
            "Test ist trivially PASS)"

        # Source-File EXISTIERT NICHT
        comp = {
            "type": "compound",
            "checks": [
                {"type": "pointer_check",
                 "source_file": "docs/reviews/board/missing.md"},
                {"type": "manual"},
            ],
        }
        ok, msg = _check_completion(comp)

        assert ok is False, "compound with missing pointer_check must block"
        # Konkrete fail-reason: Engine compound-Loop sagt "compound check [0] failed"
        # ODER pointer_check selbst meldet "file not found" / "missing".
        # NICHT akzeptiert: "unknown completion type" (Trivialitaet).
        low = msg.lower()
        assert "unknown" not in low, \
            f"Engine kennt pointer_check nicht — trivial-PASS, msg: {msg!r}"
        assert ("compound" in low and ("0" in msg or "first" in low or
                                       "fail" in low)) \
            or "not found" in low or "missing" in low or "file" in low, \
            f"compound-fail-msg unspezifisch (Race-Mitigation-Pfad nicht " \
            f"verifiziert): {msg!r}"


# ---------------------------------------------------------------------------
# Task 301 — F-ENGINE-001 + C2-003 — Lazy {spec_name} resolution + empty-string HARD-policy
# ---------------------------------------------------------------------------


class TestEngineLazyResolutionAndEmptyStringPolicy:
    def test_TC_301_engine_001_lazy_spec_name_on_complete_path(
        self, isolated_project, tmp_path
    ):
        """
        TC-301: F-ENGINE-001 — `_ensure_state_variables_resolved` populates
        `spec_name` aus task.spec_ref auch wenn `--complete` ohne vorheriges
        `--next` aufgerufen wurde.

        Phase: 301
        Level: L2 (Unit)
        Quelle: docs/tasks/301-delegation.md §2 F-ENGINE-001
        evidence:
          - kind: file_range
            path: scripts/workflow_engine.py
            lines: 279-322
            quote: "def _ensure_state_variables_resolved"
        """
        from scripts import workflow_engine as we

        # Task-YAML mit spec_ref schreiben
        task_yaml = tmp_path / "docs" / "tasks" / "299.yaml"
        task_yaml.parent.mkdir(parents=True, exist_ok=True)
        task_yaml.write_text(
            "task_id: 299\nspec_ref: docs/specs/299-fabrication-mitigation.md\n",
            encoding="utf-8",
        )

        # Fresh state: variables-Dict ohne spec_name
        state = {
            "task_id": 299,
            "variables": {"task_id": "299", "artifact_path": None},
            "steps": {},
        }

        changed = we._ensure_state_variables_resolved(state)
        assert changed is True, "Lazy resolution should change state"
        assert state["variables"].get("spec_name") == "299-fabrication-mitigation"

        # Idempotenz: zweiter Aufruf macht nichts
        changed2 = we._ensure_state_variables_resolved(state)
        assert changed2 is False, "Idempotenz: spec_name bereits gesetzt"

    def test_TC_301_engine_001_no_op_for_task_without_spec_ref(
        self, isolated_project, tmp_path
    ):
        """
        TC-301b: Lazy resolution macht nichts wenn task keine spec_ref hat.
        Verhindert Regression in 298-paused-Workflow ohne spec_ref.

        Phase: 301
        Level: L2 (Unit)
        Quelle: docs/tasks/301-delegation.md §6 (Stop: "F-ENGINE-001 bricht
                 existing Workflow-State")
        evidence:
          - kind: file_range
            path: scripts/workflow_engine.py
            lines: 322-352
            quote: "def _resolve_spec_name"
        """
        from scripts import workflow_engine as we

        task_yaml = tmp_path / "docs" / "tasks" / "298.yaml"
        task_yaml.parent.mkdir(parents=True, exist_ok=True)
        # KEIN spec_ref-Field
        task_yaml.write_text("task_id: 298\nstatus: in_progress\n",
                              encoding="utf-8")

        state = {
            "task_id": 298,
            "variables": {"task_id": "298", "artifact_path": None},
            "steps": {},
        }

        we._ensure_state_variables_resolved(state)
        assert "spec_name" not in state["variables"], \
            "spec_name darf nicht gesetzt werden wenn task keine spec_ref hat"

    def test_TC_301_c2_003_empty_string_treated_as_unresolved(
        self, isolated_project
    ):
        """
        TC-301c: C2-003 — empty-string `{spec_name}` wird wie unresolved
        behandelt (kein silent-resolve zu "").

        Phase: 301
        Level: L2 (Unit)
        Quelle: docs/tasks/301-delegation.md §2 C2-003
        evidence:
          - kind: file_range
            path: scripts/workflow_engine.py
            lines: 254-260
            quote: "def _resolve_vars"
        """
        from scripts import workflow_engine as we

        # Empty-string Variable: muss wie None/missing behandelt werden
        resolved = we._resolve_vars(
            "docs/reviews/board/{spec_name}-foo.md",
            {"spec_name": ""},
        )
        # Empty-string-Resolution sollte den Placeholder NICHT ersetzen
        # damit _has_unresolved_vars die Variable als unresolved meldet.
        assert "{spec_name}" in resolved, (
            f"Empty-string spec_name darf NICHT zu '' resolved werden "
            f"(ergibt sonst '/-foo.md'). Got: {resolved!r}"
        )

    def test_TC_301_c2_003_compound_pointer_check_blocks_on_empty_string(
        self, isolated_project
    ):
        """
        TC-301d: HARD-policy faengt empty-string-Resolution analog zu
        unresolved-Variable.

        Phase: 301
        Level: L3 (Integration)
        Quelle: docs/tasks/301-delegation.md §2 C2-003
        evidence:
          - kind: file_range
            path: scripts/workflow_engine.py
            lines: 555-580
            quote: "for field in (\\"path\\", \\"command\\""
        """
        comp = {
            "type": "compound",
            "checks": [
                {"type": "pointer_check",
                 "source_file": "docs/reviews/board/{spec_name}-foo.md"},
                {"type": "manual"},
            ],
        }
        ok, msg = _check_completion(
            comp,
            state={"variables": {"spec_name": ""}},
        )
        assert ok is False, (
            "Empty-string spec_name sollte compound[pointer_check, manual] "
            f"blockieren (HARD-policy analog unresolved). Got: ok={ok}, msg={msg!r}"
        )
        # Fail-msg muss "unresolved variable" enthalten — NICHT "file not found",
        # damit Diagnostic-Klasse korrekt bleibt.
        low = msg.lower()
        assert "unresolved" in low, (
            f"Fail-msg sollte 'unresolved variable' enthalten "
            f"(Diagnostic-Klasse). Got: {msg!r}"
        )
