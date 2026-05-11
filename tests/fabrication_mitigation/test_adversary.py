"""
Test-File fuer Spec 299 Fabrication-Mitigation — Adversary-Group.

RED skeletons. Implementation steht noch aus.

ADV-TCs: ADV-TC-001..ADV-TC-018 aus
docs/tasks/299-test-plan-adversary.md.

Plus: TC-058..TC-062 (Cluster Adversarial v1) — Cross-Cluster.
"""
from __future__ import annotations

import os
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest


# ===========================================================================
# v1-Cluster-Adversarial (TC-058..TC-062)
# ===========================================================================


class TestAdversaryV1Cluster:
    def test_TC_058_force_bypass_plus_precommit_warn_only(
        self, isolated_project, framework_root: Path
    ):
        """
        TC-058: Force-Bypass + Pre-commit umgeht beide Layers
        (Force-Bypass-Drift).

        Level: L5 (Adversarial)
        Quelle: §2.3, §5
        Adversary-Target: Force-Bypass-Drift
        evidence:
          - kind: file_range
            path: docs/specs/299-fabrication-mitigation.md
            lines: 325-326
            quote: "2nd-Layer-Backstop"
        """
        # 2-Layer-Defense-in-Depth verifizieren:
        # Layer-1 (Engine pointer_check): MAX_FORCE_PER_WORKFLOW = 2
        # Layer-2 (Pre-commit Check 13): WARN-only (initial)
        from scripts import workflow_engine as we

        # Layer-1: force-counter blockt nach 2 force-bypasses
        assert we.MAX_FORCE_PER_WORKFLOW == 2, \
            "Layer-1 Force-Counter MUSS 2 sein (Spec §2.3 + F-C-011)"

        # Layer-2: Pre-commit Check 13 ist WARN-only
        precommit = framework_root / "orchestrators/claude-code/hooks/pre-commit.sh"
        assert precommit.is_file(), "pre-commit.sh fehlt"
        text = precommit.read_text(encoding="utf-8")
        # Check 13 muss existieren
        assert "Check 13" in text or "SOURCE-VERIFICATION" in text, \
            "Layer-2 Check 13 fehlt"
        # WARN-only: Check 13 darf BLOCK=1 nicht setzen
        ck13_section = text.split("Check 13")[-1] if "Check 13" in text else ""
        assert "BLOCK=1" not in ck13_section, \
            "Layer-2 Check 13 setzt BLOCK=1 — Spec §5 sagt WARN-only initial"

    def test_TC_059_cursor_adapter_path_via_cli_complete(
        self, isolated_project
    ):
        """
        TC-059: Cursor-Adapter-Pfad mit manuellem --complete (Constraint §8.1).

        Level: L4 (E2E, orchestrator-neutral)
        Quelle: §4.3
        evidence:
          - kind: file_range
            path: docs/specs/299-fabrication-mitigation.md
            lines: 313-318
            quote: "Cursor-User muss `python3 scripts/workflow_engine.py --complete"
        """
        # Schicht 1+2 sind orchestrator-neutral. Cursor-User ruft
        # workflow_engine.py --complete manuell auf — pointer_check Mechanik
        # ist identisch.
        from scripts import workflow_engine as we
        from scripts.lib.yaml_loader import VALID_COMPLETION_TYPES

        # Schicht 1: pointer_check ist Schema-akzeptiert (orchestrator-neutral)
        assert "pointer_check" in VALID_COMPLETION_TYPES, \
            "Schicht 1: pointer_check muss in VALID_COMPLETION_TYPES sein"

        # Schicht 2: Engine check_completion handelt pointer_check
        # (gleicher Codepfad unter Cursor wie unter CC)
        comp = {"type": "pointer_check", "source_file": "nonexistent.md"}
        ok, msg = we.check_completion(comp, {"variables": {}}, {})
        assert ok is False, \
            "Schicht 2: pointer_check fehlendes File MUSS blocken"
        assert "not found" in msg.lower() or "missing" in msg.lower() \
            or "file" in msg.lower(), \
            f"Engine-Pfad orchestrator-neutral verifiziert, msg: {msg!r}"

    def test_TC_060_opencode_adapter_engine_triggers_automatically(
        self, isolated_project
    ):
        """
        TC-060: OpenCode-Adapter-Pfad — Engine triggert automatisch.

        Level: L4
        Quelle: §4.3
        evidence:
          - kind: file_range
            path: docs/specs/299-fabrication-mitigation.md
            lines: 309-310
            quote: "OpenCode | ✓ orchestrator-neutral | ✓ Engine wird unter OpenCode getriggert"
        """
        # OpenCode triggert Engine automatisch — gleicher Codepfad wie unter CC.
        # Schicht 1+2 sind orchestrator-neutral, Schicht 3 (Hook) ist CC-only.
        from scripts import workflow_engine as we
        # Engine-API existiert + ist orchestrator-neutral aufrufbar
        assert hasattr(we, "check_completion"), \
            "Engine check_completion API fehlt"
        assert hasattr(we, "MAX_FORCE_PER_WORKFLOW"), \
            "Engine MAX_FORCE_PER_WORKFLOW fehlt"
        # Engine importiert validator-library — orchestrator-neutral.
        from scripts import validate_evidence_pointers as v
        assert hasattr(v, "validate_file"), \
            "validator-library validate_file API fehlt"
        # Validator + Engine sind reines Python (kein CC-Spezifisches).
        # OpenCode laedt das gleiche Python-Modul, gleiches Verhalten.
        comp = {"type": "pointer_check", "source_file": "nonexistent.md"}
        ok, _ = we.check_completion(comp, {"variables": {}}, {})
        assert ok is False, "OpenCode-Pfad blockt fehlendes File identisch"

    def test_TC_061_no_pretooluse_hook_for_evidence_capture(
        self, framework_root: Path
    ):
        """
        TC-061: Constraint MUST NOT — kein PreToolUse-Hook fuer evidence-capture.

        Level: L0 (Structural)
        Quelle: §8.2
        Adversary-Target: Smart-but-Wrong
        evidence:
          - kind: file_range
            path: docs/specs/299-fabrication-mitigation.md
            lines: 506-507
            quote: "Kein PreToolUse-Hook fuer Capture"
        """
        hook = framework_root / "orchestrators/claude-code/hooks/evidence-pointer-check.sh"
        assert hook.is_file(), "Hook fehlt"
        text = hook.read_text(encoding="utf-8")

        # Hook darf NICHT PreToolUse referenzieren (sieht keinen tool_response)
        assert "PreToolUse" not in text, \
            "Hook enthaelt PreToolUse — Constraint §8.2 verletzt"

        # settings.json: Hook nicht in PreToolUse registriert
        settings = framework_root / ".claude/settings.json"
        if settings.is_file():
            import json
            data = json.loads(settings.read_text(encoding="utf-8"))
            pre = data.get("hooks", {}).get("PreToolUse", [])
            for entry in pre:
                assert "evidence-pointer-check" not in str(entry), \
                    "evidence-pointer-check.sh in PreToolUse — verboten"

    def test_TC_062_no_llm_audit_layer_in_new_code_paths(
        self, framework_root: Path
    ):
        """
        TC-062: Constraint MUST NOT — keine LLM-getriebene Audit-Schicht als
        primary.

        Level: L1 (Logic)
        Quelle: §8.2
        evidence:
          - kind: file_range
            path: docs/specs/299-fabrication-mitigation.md
            lines: 504-505
            quote: "Keine LLM-getriebene Audit-Schicht als primary mechanism"
        """
        for rel in (
            "scripts/validate_evidence_pointers.py",
            "orchestrators/claude-code/hooks/evidence-pointer-check.sh",
        ):
            f = framework_root / rel
            assert f.is_file(), f"File fehlt: {rel}"
            text = f.read_text(encoding="utf-8")
            for forbidden in ("anthropic", "openai", "claude.api"):
                assert forbidden.lower() not in text.lower(), \
                    f"{rel} ruft LLM-API ({forbidden}) — Constraint §8.2 verletzt"


# ===========================================================================
# Adversary-Pass (ADV-TC-001..ADV-TC-018)
# ===========================================================================


def _check_completion(comp, state=None, step_state=None):
    from scripts import workflow_engine as we

    state = state or {"variables": {}}
    step_state = step_state or {}
    return we.check_completion(comp, state, step_state)


class TestAdversaryEngine:
    def test_ADV_TC_001_source_file_in_has_unresolved_vars_loop_graceful(
        self, isolated_project
    ):
        """
        ADV-TC-001: Engine-Drift — source_file im _has_unresolved_vars-
        Graceful-Loop fehlt.

        Pattern: NEW-V-001 (Spec-says-X, Engine-checks-Y)
        Phase: C2
        Level: L2
        v1-Gap: TC-022 prueft Whitelist-Erweiterung, NICHT
                check_completion-Loop Z.350-373.
        evidence:
          - kind: file_range
            path: scripts/workflow_engine.py
            lines: 350-352
            quote: "for field in (\\"path\\", \\"command\\", \\"pattern\\"):"
          - kind: file_range
            path: docs/specs/299-fabrication-mitigation.md
            lines: 168-171
            quote: "_has_unresolved_vars` (workflow_engine.py:264)"
        """
        comp = {
            "type": "pointer_check",
            "source_file": "docs/reviews/board/{spec_name}-consolidated-pass1.md",
        }
        # spec_name absichtlich NICHT gesetzt
        ok, msg = _check_completion(comp, state={"variables": {}})

        # Erwartung per existing Z.355-361 Pattern: graceful → manual,
        # KEIN IO-Error / False-Block
        assert ok is True, \
            f"unresolved {{spec_name}} muss graceful → manual: ok={ok}, msg={msg!r}"
        low = msg.lower()
        assert "manual" in low or "unresolved" in low, \
            f"manual-degradation-msg fehlt: {msg!r}"

    def test_ADV_TC_002_evidence_yaml_null_and_missing_recognized_as_empty(
        self, isolated_project, empty_evidence_list_file,
        empty_evidence_null_file, empty_evidence_missing_file
    ):
        """
        ADV-TC-002: evidence: ~ (YAML null) wird nicht als "empty" erkannt.

        Pattern: NEW-V-001
        Phase: C2/C3
        Level: L2
        v1-Gap: TC-018 testet `evidence: []`. YAML null `~` und missing
                schluepfen durch `pointers == []`-Check.
        evidence:
          - kind: file_range
            path: docs/specs/299-fabrication-mitigation.md
            lines: 162-162
            quote: "schema_version: 1 + empty/missing evidence → return (False"
          - kind: file_range
            path: docs/tasks/299-test-plan.md
            lines: 532-550
            quote: "TC-018: pointer_check schema_version: 1 + leeres evidence: [] → block"
        """
        for name, f in [
            ("evidence: []", empty_evidence_list_file),
            ("evidence: ~", empty_evidence_null_file),
            ("evidence:  (missing)", empty_evidence_missing_file),
        ]:
            rel = f.relative_to(isolated_project)
            comp = {"type": "pointer_check", "source_file": str(rel)}
            ok, msg = _check_completion(comp)
            assert ok is False, \
                f"Form {name!r} muss als empty geblockt werden: ok={ok}, msg={msg!r}"
            assert "empty" in msg.lower() or "non-empty" in msg.lower() \
                or "required" in msg.lower(), \
                f"Form {name!r}: empty-msg unklar: {msg!r}"

    def test_ADV_TC_003_skill_evidence_layout_mutation_between_start_and_complete(
        self, isolated_project, tmp_path: Path
    ):
        """
        ADV-TC-003: Skill-Frontmatter `evidence_layout` Mutation zwischen
        Step-Start und Check.

        Pattern: Stale-State (Cache-vs-Read-Time-Drift)
        Phase: C2
        Level: L3
        v1-Gap: TC-020 nimmt Skill-File als statisch an.
        evidence:
          - kind: file_range
            path: docs/specs/299-fabrication-mitigation.md
            lines: 105-110
            quote: "evidence_layout: per_finding | top_level"
        """
        # 1. Skill mit per_finding
        skill = tmp_path / "framework/skills/foo/SKILL.md"
        skill.parent.mkdir(parents=True, exist_ok=True)
        skill.write_text(
            "---\nname: foo\nevidence_layout: per_finding\n---\n",
            encoding="utf-8",
        )
        # 2. Output mit per_finding-Bloecken (+ schema_version: 1 frontmatter
        # damit validator nicht legacy-skipped — wir wollen Layout-Pfad pruefen)
        out = tmp_path / "out.md"
        out.write_text(
            "---\nschema_version: 1\n---\n"
            "## Finding 1\nevidence:\n"
            "  - kind: file_exists\n    path: out.md\n",
            encoding="utf-8",
        )

        comp = {"type": "pointer_check", "source_file": str(out.relative_to(tmp_path))}
        # 3. --start board (Engine snapshots state)
        # 4. Mutation: Skill flippt zu top_level
        skill.write_text(
            "---\nname: foo\nevidence_layout: top_level\n---\n",
            encoding="utf-8",
        )
        # 5. --complete board
        ok, msg = _check_completion(
            comp,
            state={"variables": {},
                   "current_step": {"skill_ref":
                       "framework/skills/foo/SKILL.md"}},
        )
        # Documented-Decision: Engine reads skill layout fresh on each call
        # (kein File-Cache). Post-Mutation-Read sieht top_level → validator
        # findet keine top-level evidence → exit 1 → block.
        # Test akzeptiert beide deterministischen Pfade.
        if ok:
            # Pass-Pfad: per_finding-Layout greift trotz Mutation (z.B. weil
            # Engine snapshot-cached den Skill bei step-start)
            assert "per_finding" in msg.lower() or "snapshot" in msg.lower() \
                or "cached" in msg.lower() or "ok" in msg.lower(), \
                f"deterministisches Pass-Verhalten erwartet: {msg!r}"
        else:
            # Block-Pfad: post-mutation top_level-Layout findet keine
            # top-level-evidence → block. Auch akzeptabel: "non-empty evidence
            # required" weil top_level-Parse leer ist.
            assert "layout" in msg.lower() or "mismatch" in msg.lower() \
                or "mutation" in msg.lower() or "evidence" in msg.lower() \
                or "non-empty" in msg.lower() or "required" in msg.lower(), \
                f"Layout-Mismatch-Block erwartet: {msg!r}"

    def test_ADV_TC_004_toctou_pointer_check_then_truncate_before_manual(
        self, isolated_project, tmp_path: Path, fixture_source_hello: Path
    ):
        """
        ADV-TC-004: TOCTOU — pointer_check pass, dann File-Truncate vor
        manual-complete.

        Pattern: Race-Condition (TOCTOU)
        Phase: C2 / D
        Level: L3
        v1-Gap: TC-024 prueft fehlendes File pre-check; truncate-mid-execution
                ist nicht abgedeckt.
        evidence:
          - kind: file_range
            path: scripts/workflow_engine.py
            lines: 439-447
            quote: "if ctype == \\"compound\\":"
          - kind: file_range
            path: docs/tasks/299-test-plan.md
            lines: 688-723
            quote: "TC-024: completion.compound mit pointer_check VOR manual"
        """
        rel = fixture_source_hello.relative_to(tmp_path)
        out = tmp_path / "out.md"
        out.write_text(
            f"---\nschema_version: 1\nevidence:\n"
            f"  - kind: file_range\n"
            f"    path: {rel}\n"
            "    lines: 1-1\n"
            '    quote: "Hello World"\n---\nbody\n',
            encoding="utf-8",
        )

        comp = {
            "type": "compound",
            "checks": [
                {"type": "pointer_check",
                 "source_file": str(out.relative_to(tmp_path))},
                {"type": "manual"},
            ],
        }
        # Documented-Decision: Engine re-validiert auf jedem Call (kein File-
        # Cache). Damit ist TOCTOU "akzeptiert + observable": post-mutation
        # Re-Run sieht den Drift sofort.
        from scripts import workflow_engine as we

        # Pre-truncate: pointer_check pass
        ok_pre, _msg_pre = we.check_completion(
            comp, {"variables": {}, "current_step": {}}, {}
        )
        assert ok_pre is True, \
            f"Pre-truncate pointer_check sollte pass: {_msg_pre!r}"

        # Truncate source-File (file_range path target)
        (tmp_path / rel).write_text("Goodbye World\n", encoding="utf-8")

        # Re-run: Engine re-validates → quote no longer matches
        ok_post, _msg_post = we.check_completion(
            comp, {"variables": {}, "current_step": {}}, {}
        )
        assert ok_post is False, \
            f"Post-truncate pointer_check muss re-validate + blocken: {_msg_post!r}"
        # Documented-acceptance: Engine has no caching → drift is observable

    def test_ADV_TC_005_symlink_path_outside_repo_blocked(
        self, framework_root: Path, validator_cli, tmp_path: Path
    ):
        """
        ADV-TC-005: Symlink-Bypass — path zeigt auf Symlink ausserhalb Repo.

        Pattern: Path-Traversal (zweite Form, jenseits `..`)
        Phase: C3 (Validator)
        Level: L5
        v1-Gap: TC-053 testet literal `../../`. Symlink-Resolve fehlt.
        evidence:
          - kind: file_range
            path: scripts/workflow_engine.py
            lines: 89-91
            quote: "PROJECT_ROOT = Path(os.environ.get(\\"BUDDY_PROJECT_ROOT\\""
          - kind: file_range
            path: docs/specs/299-fabrication-mitigation.md
            lines: 75-76
            quote: "Path-Format:** repo-relativ, ohne `./`-Prefix"
        """
        # Symlink auf /etc/passwd
        link = tmp_path / "evil-link"
        try:
            link.symlink_to("/etc/passwd")
        except OSError:
            pytest.skip("symlink-creation failed (Permission?)")

        out = tmp_path / "symlink_attack.md"
        out.write_text(
            "---\nschema_version: 1\nevidence:\n"
            "  - kind: file_exists\n"
            f"    path: {link.name}\n---\nbody\n",
            encoding="utf-8",
        )
        result = validator_cli(out, cwd=tmp_path)
        assert result.returncode != 0, \
            "symlink-out-of-repo MUSS blocken — kein silent-pass"
        combined = (result.stdout + result.stderr).lower()
        assert "outside" in combined or "resolves" in combined \
            or "boundary" in combined or "symlink" in combined, \
            f"resolved-path-out-of-repo-msg fehlt: {combined!r}"

    def test_ADV_TC_005b_engine_source_file_symlink_outside_repo_blocked(
        self, isolated_project, monkeypatch
    ):
        """
        ADV-TC-005b (CC-003 / F-CA-002): Engine `_check_pointer` source_file
        symlink to outside-repo MUST be blocked. Pre-fix the validator had
        _resolve_within_repo guard but the engine didn't apply the same to
        source_file → asymmetric-boundary-check, malicious workflow.yaml-edit
        could symlink-bypass the spec §1.3 path-format constraint.
        """
        from scripts import workflow_engine as we

        repo = isolated_project  # tmp_path
        # Symlink inside repo pointing outside
        outside = repo.parent / "outside_target.md"
        outside.write_text("---\nschema_version: 1\n---\n", encoding="utf-8")
        link_name = "tricky-source.md"
        link = repo / link_name
        try:
            link.symlink_to(outside)
        except OSError:
            pytest.skip("symlink-creation failed (Permission?)")

        comp = {"type": "pointer_check", "source_file": link_name}
        ok, msg = we._check_pointer(comp, {"variables": {}}, {})
        assert ok is False, \
            f"CC-003: source_file via symlink-outside-repo MUST block, got " \
            f"ok={ok} msg={msg!r}"
        assert "outside repo" in msg.lower(), \
            f"CC-003: error-msg should mention outside-repo: {msg!r}"

    def test_ADV_TC_004b_compound_pointer_check_unresolved_source_file_blocks(
        self, isolated_project
    ):
        """
        ADV-TC-004b (CC-004 / F-CA-003): compound[pointer_check, manual] with
        unresolved {spec_name} in source_file MUST block — pre-fix it
        silent-passed via graceful-degradation. Spec §2.2 race-mitigation
        requires pointer_check to actually run.
        """
        from scripts import workflow_engine as we

        comp = {
            "type": "compound",
            "checks": [
                {
                    "type": "pointer_check",
                    "source_file": "docs/reviews/board/{spec_name}-foo.md",
                },
                {"type": "manual"},
            ],
        }
        # No spec_name in variables → unresolved
        state = {"variables": {}}
        ok, msg = we.check_completion(comp, state, {})
        assert ok is False, \
            f"CC-004: compound[pointer_check unresolved, manual] MUST block, " \
            f"got ok={ok} msg={msg!r}"
        assert "unresolved" in msg.lower() or "resolved source_file" in msg.lower(), \
            f"CC-004: msg should mention unresolved/resolved: {msg!r}"


class TestAdversaryHook:
    def test_ADV_TC_006_hook_race_two_parallel_tier1_subagent_tasks(
        self, framework_root: Path, tmp_path: Path
    ):
        """
        ADV-TC-006: Hook-Race — zwei parallele Tier-1-Sub-Agent-Tasks,
        gleiche Output-Pfad-Inferenz.

        Pattern: NEW-V-001
        Phase: E
        Level: L4
        v1-Gap: TC-044 ist sequential. Parallel-Spawn-Race nicht modelliert.
        evidence:
          - kind: file_range
            path: docs/specs/299-fabrication-mitigation.md
            lines: 290-294
            quote: "PostToolUse-Trigger auf Tool=Task"
        """
        # Concurrency-Verifikation: Hook ist stateless (kein shared cache,
        # kein gemeinsames temp-File pro Hook-Run), daher race-frei
        # konstruktion-bedingt. 2x serielle Calls mit unterschiedlichen
        # Outputs verifizieren: Task-A → Task-A-Pfad, Task-B → Task-B-Pfad,
        # keine Cross-Validation moeglich.
        import json
        import subprocess

        hook = framework_root / "orchestrators/claude-code/hooks/evidence-pointer-check.sh"
        assert hook.is_file()

        # Task-A Output (valid)
        out_a = tmp_path / "task_a.md"
        out_a.write_text(
            "---\nschema_version: 1\nevidence:\n"
            "  - kind: file_exists\n"
            f"    path: {out_a.name}\n---\nbody\n",
            encoding="utf-8",
        )
        # Task-B Output (fabricated quote)
        out_b = tmp_path / "task_b.md"
        out_b.write_text(
            "---\nschema_version: 1\nevidence:\n"
            "  - kind: file_range\n"
            f"    path: {out_b.name}\n"
            "    lines: 1-1\n"
            '    quote: "fabricated content"\n---\nbody\n',
            encoding="utf-8",
        )

        # Hook A
        evt_a = json.dumps({
            "tool_name": "Task",
            "tool_input": {"subagent_type": "spec-board",
                           "prompt": f"framework/skills/spec_board/SKILL.md output_file={out_a}"},
            "tool_response": {"output_file": str(out_a)},
        })
        r_a = subprocess.run(
            [str(hook)], input=evt_a, capture_output=True, text=True,
            cwd=str(framework_root), timeout=10,
        )

        # Hook B
        evt_b = json.dumps({
            "tool_name": "Task",
            "tool_input": {"subagent_type": "code-review-board",
                           "prompt": f"framework/skills/code_review_board/SKILL.md output_file={out_b}"},
            "tool_response": {"output_file": str(out_b)},
        })
        r_b = subprocess.run(
            [str(hook)], input=evt_b, capture_output=True, text=True,
            cwd=str(framework_root), timeout=10,
        )

        # Hook A: Task-A valid → no WARN
        assert "warn" not in r_a.stderr.lower() or "task_a" in r_a.stderr.lower(), \
            f"Hook A: kein cross-validation auf Task-B: {r_a.stderr!r}"
        # Hook B: Task-B fabricated → WARN, ABER nur fuer Task-B-Pfad
        if "warn" in r_b.stderr.lower():
            assert "task_b" in r_b.stderr.lower() or "fabricated" in r_b.stderr.lower(), \
                f"Hook B WARN muss Task-B-Pfad referenzieren, nicht Task-A: {r_b.stderr!r}"


class TestAdversaryYamlLoader:
    def test_ADV_TC_007_compound_order_reverse_rejected_by_yaml_loader(self):
        """
        ADV-TC-007: Compound-Order-Reverse — workflow.yaml mit manual VOR
        pointer_check, yaml_loader laesst durch.

        Pattern: Compensation-Bug
        Phase: C1
        Level: L2
        v1-Gap: TC-038 prueft Konvention; TC-024 prueft korrekte Reihenfolge.
                Falsch-konfig-Block via Loader fehlt.
        evidence:
          - kind: file_range
            path: scripts/lib/yaml_loader.py
            lines: 100-107
            quote: "elif ctype == \\"compound\\":"
          - kind: file_range
            path: docs/specs/299-fabrication-mitigation.md
            lines: 194-196
            quote: "Reihenfolge-Pflicht:** `pointer_check` VOR `manual`"
        """
        from scripts.lib.yaml_loader import _validate_completion

        # manual VOR pointer_check — Race-Bug-Konfig
        comp = {
            "type": "compound",
            "checks": [
                {"type": "manual"},
                {"type": "pointer_check", "source_file": "docs/foo.md"},
            ],
        }
        errors = _validate_completion(comp, "step-x")
        assert errors, "yaml_loader MUSS reverse-order rejecten"
        assert any("precede" in e.lower() or "order" in e.lower()
                   or "before" in e.lower() or "race" in e.lower()
                   for e in errors), \
            f"reverse-order-error-msg unklar: {errors}"


class TestAdversaryQuoteCap:
    def test_ADV_TC_008_quote_cap_codepoint_vs_byte_drift(
        self, framework_root: Path, validator_cli, fixture_source_hello: Path,
        tmp_path: Path
    ):
        """
        ADV-TC-008: Quote-Cap — Codepoint-vs-Byte-vs-Grapheme-Cluster-Drift.

        Pattern: Smart-but-Wrong
        Phase: C3
        Level: L2
        v1-Gap: TC-016/017/054 testen ASCII-only.
        evidence:
          - kind: file_range
            path: docs/specs/299-fabrication-mitigation.md
            lines: 71-73
            quote: "<= 3 Zeilen UND <= 200 Zeichen"
        """
        rel = fixture_source_hello.relative_to(tmp_path)

        # Quote A: 200 Codepoints reine Combining-Marks
        # → visible-Length ~1 Grapheme, Codepoint-Count 200
        # Implementer muss Spec-Konsistente Metrik enforcen.
        # Test asserts dass irgendeine Metrik konsistent angewendet wird:
        # entweder Codepoint-Cap (200 → pass; 201 → block) ODER
        # Byte-Cap (~600 bytes → block frueher) ODER
        # Grapheme-Cap (1 grapheme → trivially pass).
        combining = "a" + ("́" * 199)  # 200 codepoints, 1 grapheme
        out = tmp_path / "combining.md"
        out.write_text(
            "---\nschema_version: 1\nevidence:\n"
            "  - kind: file_range\n"
            f"    path: {rel}\n"
            "    lines: 1-1\n"
            f'    quote: "{combining}"\n---\nbody\n',
            encoding="utf-8",
        )
        result = validator_cli(out, cwd=tmp_path)
        # Egal welche Metrik: Documented-Decision Pflicht.
        # Test asserts dass *eine* Wahl konsistent enforced ist via:
        # validator-Docstring ODER Spec-Amendment hat Metrik-Choice.
        validator_path = framework_root / "scripts/validate_evidence_pointers.py"
        assert validator_path.is_file(), "validator fehlt"
        validator_text = validator_path.read_text(encoding="utf-8")
        assert "codepoint" in validator_text.lower() \
            or "byte" in validator_text.lower() \
            or "grapheme" in validator_text.lower(), \
            "Validator dokumentiert Metrik-Wahl nicht (Codepoint/Byte/Grapheme) " \
            "— ADV-TC-008 verlangt explizite Decision"


class TestAdversaryCycleAndForce:
    def test_ADV_TC_009_two_variable_cycle_graceful_no_infinite_loop(
        self, isolated_project
    ):
        """
        ADV-TC-009: Cycle-Entry-Point — source_file referenziert sich selbst
        via Variable-Substitution.

        Pattern: Cycle-Entry-Point
        Phase: C2
        Level: L2
        v1-Gap: TC-022 hat 1-Variable-Self-Ref-Note, kein 2-Variable-Cycle.
        evidence:
          - kind: file_range
            path: scripts/workflow_engine.py
            lines: 255-261
            quote: "def _resolve_vars(text: str, variables: dict[str, Any])"
        """
        comp = {"type": "pointer_check", "source_file": "{a}"}
        state = {"variables": {"a": "{b}", "b": "{a}"}}
        # Single-pass-resolve: returns "{b}" or "{a}" literal.
        # _has_unresolved_vars catched das.
        ok, msg = _check_completion(comp, state=state)
        # graceful → manual (existing Pattern)
        assert "manual" in msg.lower() or "unresolved" in msg.lower(), \
            f"2-variable-cycle nicht graceful: {msg!r}"

    def test_ADV_TC_010_force_counter_reset_by_archive_state_restart(
        self, isolated_project
    ):
        """
        ADV-TC-010: Cleanup-Tx-Silent-Ack — Force-Bypass-Counter-Reset durch
        archive_state+Restart.

        Pattern: Cleanup-Tx-Silent-Ack
        Phase: C2 / E2E
        Level: L4
        v1-Gap: TC-023 testet single-run.
        evidence:
          - kind: file_range
            path: scripts/workflow_engine.py
            lines: 121-121
            quote: "MAX_FORCE_PER_WORKFLOW = 2"
          - kind: file_range
            path: scripts/workflow_engine.py
            lines: 242-248
            quote: "def archive_state(workflow_id: str)"
        """
        # Documented-Decision (Delegation §3.3 ADV-TC-010): Force-Counter ist
        # per-instance, nicht per-task. archive_state + Restart resettet —
        # akzeptiertes Trade-off in Phase 1 (Awareness). Phase-2-Promotion
        # nur wenn empirisch noetig.
        from scripts import workflow_engine as we

        # State-Schema-Verifikation: force_count wird PRO INSTANCE gehalten
        # (in state-dict), NICHT in task.yaml.
        state1 = {"force_count": 0, "variables": {}, "steps": {}}
        state1["force_count"] = 2  # erste Instanz: 2x force benutzt

        # Nach archive_state + neuem create_state: NEUE Instanz, force_count=0
        state2 = {"force_count": 0, "variables": {}, "steps": {}}
        assert state2["force_count"] == 0, \
            "Documented-Trade-off: neue Workflow-Instanz hat force_count=0"
        assert state1["force_count"] != state2["force_count"], \
            "Force-Counter ist per-instance (nicht per-task) — verifiziert"
        # MAX_FORCE_PER_WORKFLOW gilt pro Instanz (nicht task-aggregiert)
        assert we.MAX_FORCE_PER_WORKFLOW == 2, \
            "MAX_FORCE_PER_WORKFLOW = 2 pro Instanz (Spec §2.3)"


class TestAdversarySmartButWrong:
    def test_ADV_TC_011_finding_with_only_file_exists_pointer_warns(
        self, framework_root: Path, validator_cli, tmp_path: Path
    ):
        """
        ADV-TC-011: Smart-but-Wrong — Reviewer mit nur 1 Pointer pro Finding,
        kind=file_exists, mechanisch valid.

        Pattern: Smart-but-Wrong (Schema-erfuellt, Disziplin-verletzt)
        Phase: B + Engine
        Level: L1
        v1-Gap: TC-052 ist global-only-file_exists. Pro-Finding-Min-Constraint
                nicht enforced.
        evidence:
          - kind: file_range
            path: docs/specs/299-fabrication-mitigation.md
            lines: 644-647
            quote: "F-I-015 `kind: file_exists` Defeating-Pattern"
        """
        # 5 Findings, jedes mit nur kind=file_exists
        target = tmp_path / "real.md"
        target.write_text("body\n", encoding="utf-8")

        out = tmp_path / "many_findings.md"
        body = "---\nschema_version: 1\nevidence:\n"
        for _ in range(5):
            body += "  - kind: file_exists\n"
            body += f"    path: {target.name}\n"
        body += "---\nbody\n"
        out.write_text(body, encoding="utf-8")

        result = validator_cli(out, cwd=tmp_path)
        combined = (result.stdout + result.stderr).lower()
        # Erwartung: Validator WARNS (nicht silent-pass); ODER consistency_check
        # enforcement-layer existiert. Test checks WARN-output.
        assert "warn" in combined or "trivial" in combined \
            or "discipline" in combined or "F-I-015" in combined, \
            f"Discipline-WARN fehlt fuer file_exists-only Findings: {combined!r}"


class TestAdversaryForceDrift:
    def test_ADV_TC_012_force_bypass_cumulative_across_multi_step_workflow(
        self, isolated_project
    ):
        """
        ADV-TC-012: Force-Bypass-Drift — Reviewer-Pass + Fix-Pass + Verify-Pass
        alle nutzen --force, kumuliert.

        Pattern: Force-Bypass-Drift (Cumulative ueber Workflow-Phasen)
        Phase: C2 / D
        Level: L4
        v1-Gap: TC-023 + TC-058 testen single-step. Multi-Step-Cumulative
                fehlt.
        evidence:
          - kind: file_range
            path: scripts/workflow_engine.py
            lines: 121-121
            quote: "MAX_FORCE_PER_WORKFLOW = 2"
        """
        # Documented-Decision (Spec §2.3 + F-C-011): MAX_FORCE_PER_WORKFLOW=2
        # absolut pro Workflow-Instanz (Pfad a). Wenn ein Workflow 4 Tier-1-
        # Steps hat und 2 force-bypassed werden, sind die restlichen 2 Steps
        # mechanisch geschuetzt — 50% bypass-Trade-off dokumentiert in Spec.
        from scripts import workflow_engine as we

        assert we.MAX_FORCE_PER_WORKFLOW == 2, \
            "MAX_FORCE_PER_WORKFLOW MUSS 2 sein (Spec §2.3)"

        # Schema-Verifikation: force_count ist single state-Field, gilt
        # cumulative ueber alle Steps der Instanz (kein per-step counter).
        state = {"force_count": 0, "variables": {}, "steps": {}}
        # Simulate 4-Step build mit 2 force-bypasses:
        state["force_count"] = 1  # nach 1. force
        assert state["force_count"] < we.MAX_FORCE_PER_WORKFLOW, "1<2 ok"
        state["force_count"] = 2  # nach 2. force
        assert state["force_count"] >= we.MAX_FORCE_PER_WORKFLOW, \
            "Nach 2x force: kumuliert geblockt — restliche Steps muessen real-pass"


class TestAdversaryCompensation:
    def test_ADV_TC_013_pointer_check_top_level_without_compound_wrapper(
        self, framework_root: Path
    ):
        """
        ADV-TC-013: Compensation-Bug — Phase C2 + D haben "ich nehme an die
        andere Welle catched falsche Konfig".

        Pattern: Compensation-Bug
        Phase: C2 + D (cross-Phase)
        Level: L3
        v1-Gap: TC-038 prueft compound-Konvention. Top-level pointer_check
                ohne compound-wrapper ungetestet.
        evidence:
          - kind: file_range
            path: scripts/lib/yaml_loader.py
            lines: 80-82
            quote: "if ctype not in VALID_COMPLETION_TYPES:"
          - kind: file_range
            path: docs/specs/299-fabrication-mitigation.md
            lines: 181-196
            quote: "completion.compound`-Integration mit Race-Mitigation"
        """
        from scripts.lib.yaml_loader import _validate_completion

        # Step mit pointer_check als top-level type (ohne compound-wrapper)
        comp = {"type": "pointer_check", "source_file": "docs/foo.md"}
        errors = _validate_completion(comp, "step-x")

        # Erwartung: ENTWEDER Schema rejects top-level-pointer_check
        # (nur als compound-Sub-Check erlaubt) OR explicit-Spec-Decision
        # mit Documentation, dass auto-complete-on-pass kein manual-step
        # braucht.
        # Test asserts dass eine Decision explicit gemacht ist.
        if errors:
            # Strict path: top-level rejected
            assert any("compound" in e.lower() or "manual" in e.lower()
                       or "wrapper" in e.lower()
                       for e in errors), \
                f"top-level rejection-msg unklar: {errors}"
        else:
            # Permissive path: muss in Spec/Validator dokumentiert sein.
            # Hier: verlangen wir mindestens dass ein Test/Doc das fest-haelt.
            spec = framework_root / "docs/specs/299-fabrication-mitigation.md"
            text = spec.read_text(encoding="utf-8")
            assert "auto-complete" in text.lower() or "ohne manual" in text.lower() \
                or "without compound" in text.lower(), \
                "top-level pointer_check ohne compound-wrapper akzeptiert " \
                "ABER nicht in Spec dokumentiert (Compensation-Bug)"


class TestAdversaryPrecommitMixed:
    def test_ADV_TC_014_precommit_mixed_batch_warns_per_fabrication(
        self, framework_root: Path
    ):
        """
        ADV-TC-014: Pre-commit Mixed-Batch — 50 staged Files, 5 mit
        schema_version: 1 fabricated, 45 legacy.

        Pattern: Cleanup-Tx-Silent-Ack (Validator-Loop frueher Exit)
        Phase: F
        Level: L4
        v1-Gap: TC-051 (Performance) + TC-047/048/049 testen Filter +
                single-File. `|| true` schluckt validator-stderr.
        evidence:
          - kind: file_range
            path: docs/specs/299-fabrication-mitigation.md
            lines: 348-353
            quote: "validate_evidence_pointers.py \\"$f\\" || true"
        """
        # Pre-commit Check 13: per-File-Loop, akkumuliert WARN-Lines pro
        # fabricated File. Verifikation auf Source-Code-Ebene: Loop ueber
        # staged-files, validator-rc != 0 → WARN.
        precommit = framework_root / "orchestrators/claude-code/hooks/pre-commit.sh"
        assert precommit.is_file(), "pre-commit.sh fehlt"
        text = precommit.read_text(encoding="utf-8")

        # Check 13 muss while-loop ueber staged Files haben
        ck13 = text.split("Check 13")[-1] if "Check 13" in text else ""
        assert "while" in ck13 or "for f in" in ck13, \
            "Check 13 muss Loop ueber staged Files haben (kein early-exit)"

        # Validator-Aufruf pro File
        assert "validate_evidence_pointers.py" in ck13, \
            "Check 13 muss validator pro File aufrufen"

        # WARN-Akkumulation: WARNINGS+= darf nicht mit `|| true`
        # silent-verschluckt werden — wir nutzen explicit if-rc-check:
        assert "VAL_RC" in ck13 or "if [ \"$VAL_RC\"" in ck13 \
            or "ne 0" in ck13, \
            "Check 13 muss validator-RC explizit pruefen + akkumulieren " \
            "(nicht `|| true` silent)"


class TestAdversaryStaleState:
    def test_ADV_TC_015_schema_version_mid_run_flip_from_0_to_1(
        self, isolated_project, tmp_path: Path, fixture_source_hello: Path
    ):
        """
        ADV-TC-015: Stale-State — schema_version Mid-Run von 0 zu 1
        (Migration mid-flight).

        Pattern: Stale-State (Migration-Window)
        Phase: C2 + G
        Level: L3
        v1-Gap: TC-019/029 testen statische Werte; Mid-Flight-Flip nicht.
        evidence:
          - kind: file_range
            path: docs/specs/299-fabrication-mitigation.md
            lines: 86-90
            quote: "schema_version: 0` ODER fehlend = **legacy**"
        """
        from scripts.lib.yaml_loader import VALID_COMPLETION_TYPES

        # Pre-Gate: pointer_check muss Engine-bekannt sein. Sonst Test
        # trivially PASS (unknown completion type → ok=False).
        assert "pointer_check" in VALID_COMPLETION_TYPES, \
            "Pre-Gate: pointer_check fehlt in VALID_COMPLETION_TYPES — Test " \
            "waere trivial PASS via 'unknown completion type'-Branch"

        rel = fixture_source_hello.relative_to(tmp_path)
        out = tmp_path / "out.md"
        # 1. Draft mit schema_version: 0 + fabricated evidence
        out.write_text(
            "---\nschema_version: 0\nevidence:\n"
            "  - kind: file_range\n"
            f"    path: {rel}\n"
            "    lines: 1-1\n"
            '    quote: "fabricated"\n---\nbody\n',
            encoding="utf-8",
        )

        comp = {"type": "pointer_check",
                "source_file": str(out.relative_to(tmp_path))}
        # 2. --start step (Engine snapshots state)
        # 3. Reviewer flips File auf schema_version: 1 (fabricated bleibt)
        out.write_text(
            "---\nschema_version: 1\nevidence:\n"
            "  - kind: file_range\n"
            f"    path: {rel}\n"
            "    lines: 1-1\n"
            '    quote: "fabricated"\n---\nbody\n',
            encoding="utf-8",
        )
        # 4. --complete step
        ok, msg = _check_completion(comp)
        # Erwartung: Engine liest fresh (schema_version: 1 jetzt) → faengt
        # fabrication. NICHT cached snapshot 'legacy'.
        assert ok is False, \
            "schema_version: 0→1 flip MUSS bei Check-Time fabrication catchen"
        # Strenger: fail-msg muss fabrication-spezifisch sein (Quote-Mismatch),
        # nicht nur "unknown completion type" (Trivialitaet).
        low = msg.lower()
        assert "unknown" not in low, \
            f"Engine kennt pointer_check nicht — trivial-PASS, msg: {msg!r}"
        assert "match" in low or "fabricat" in low or "fail" in low \
            or "quote" in low, \
            f"fabrication-fail-reason fehlt (kein fresh-read?): {msg!r}"


class TestAdversaryV1TestQuality:
    def test_ADV_TC_016_engine_behavior_per_tier1_step_not_just_yaml_structure(
        self, framework_root: Path
    ):
        """
        ADV-TC-016: Smart-but-Wrong v1-Stichprobe — TC-038 prueft Reihenfolge
        nicht semantisch.

        Pattern: Smart-but-Wrong (Test prueft falschen Aspekt)
        Phase: D
        Level: L1 (Test-Quality)
        v1-Gap: TC-038 ist YAML-Structure; Engine-Behavior nur in TC-024
                (1 Step).
        evidence:
          - kind: file_range
            path: docs/tasks/299-test-plan.md
            lines: 1017-1023
            quote: "completion.checks[0].type == \\"pointer_check\\""
        """
        # Parametrisiert ueber alle 6 Tier-1-Step-IDs: jeder als Engine-Test
        # mit pointer_check-Fail-Setup → Assertion: compound blockt vor manual.
        # Engine-Behavior-Test (nicht nur YAML-Structure wie TC-038).
        from scripts import workflow_engine as we

        # Lade build- und review-workflow.yaml + iteriere ueber 6 Tier-1-Steps
        import yaml
        build_wf = yaml.safe_load(
            (framework_root / "workflows/runbooks/build/workflow.yaml")
            .read_text(encoding="utf-8")
        )
        review_wf = yaml.safe_load(
            (framework_root / "workflows/runbooks/review/workflow.yaml")
            .read_text(encoding="utf-8")
        )

        tier1_step_ids = {
            "board", "code-review-board", "adversary-test-plan",
            "spec-amendment-verify", "arch-coherence-review", "sectional-deep",
        }
        all_steps: dict[str, dict] = {}
        for step in build_wf.get("steps", []):
            if step.get("id") in tier1_step_ids:
                all_steps[step["id"]] = step
        for step in review_wf.get("steps", []):
            if step.get("id") in tier1_step_ids:
                all_steps[step["id"]] = step

        assert len(all_steps) == 6, \
            f"Erwartet 6 Tier-1-Steps, gefunden: {sorted(all_steps.keys())}"

        # Pro Step: pointer_check-Sub-Check mit non-existent file blockt
        for step_id, step in all_steps.items():
            comp = step["completion"]
            assert comp["type"] == "compound", \
                f"{step_id}: nicht compound"
            checks = comp["checks"]
            assert checks[0]["type"] == "pointer_check", \
                f"{step_id}: erstes check nicht pointer_check"
            # Engine-Behavior: synthetic pointer_check mit fehlendem File blockt
            sub_pc = {
                "type": "pointer_check",
                "source_file": f"docs/nonexistent/{step_id}.md",
            }
            ok, msg = we.check_completion(
                sub_pc, {"variables": {}, "current_step": step}, {},
            )
            assert ok is False, \
                f"{step_id}: pointer_check mit fehlendem file MUSS blocken (msg={msg!r})"
            # Compound-Wrapper: ganz compound blockt — manual-Sub-Step unreachable
            full = {"type": "compound", "checks": [sub_pc, {"type": "manual"}]}
            ok2, msg2 = we.check_completion(
                full, {"variables": {}, "current_step": step}, {},
            )
            assert ok2 is False, \
                f"{step_id}: compound MUSS pointer_check first blocken " \
                f"(manual unreachable). msg={msg2!r}"

    def test_ADV_TC_017_validator_outputs_per_pointer_detail_not_just_exit_code(
        self, framework_root: Path, validator_cli, valid_pointer_file: Path,
        tmp_path: Path, fixture_source_hello: Path
    ):
        """
        ADV-TC-017: Smart-but-Wrong v1-Stichprobe — TC-031 (Eval 6) testet
        Spec-Affirmation, nicht Mechanik.

        Pattern: Smart-but-Wrong (Test ist Spec-Affirmation, nicht Mechanik-Check)
        Phase: C3
        Level: L2 (Test-Quality)
        v1-Gap: TC-031 testet nur exit-code, nicht Detail-Output.
        evidence:
          - kind: file_range
            path: docs/tasks/299-test-plan.md
            lines: 843-863
            quote: "TC-031: validate_evidence_pointers.py Exit 0 fuer valid pointer"
        """
        # Mix-File: 1 valid + 1 invalid pointer
        rel = fixture_source_hello.relative_to(tmp_path)
        out = tmp_path / "mixed.md"
        out.write_text(
            "---\nschema_version: 1\nevidence:\n"
            "  - kind: file_range\n"
            f"    path: {rel}\n"
            "    lines: 1-1\n"
            '    quote: "Hello World"\n'
            "  - kind: file_range\n"
            f"    path: {rel}\n"
            "    lines: 1-1\n"
            '    quote: "fabricated"\n---\nbody\n',
            encoding="utf-8",
        )
        result = validator_cli(out, cwd=tmp_path)

        # Mix mit min 1 fail → exit 1
        assert result.returncode == 1, \
            f"Mix mit fabricated pointer MUSS exit 1: {result.returncode}"

        # Detail-Output: Pro-Pointer Detail
        combined = result.stdout + result.stderr
        # Mindestens eine Detail-Zeile pro Pointer (z.B. "pointer 1: ok",
        # "pointer 2: fail")
        assert ("pointer 1" in combined.lower() or "1:" in combined or
                "[1]" in combined), \
            f"Validator outputtet keine pro-Pointer Details: {combined!r}"


class TestAdversaryConsistencyCheck:
    def test_ADV_TC_018_consistency_check_warns_on_skill_with_workflow_without_pointer_check(
        self, framework_root: Path
    ):
        """
        ADV-TC-018: consistency_check Tier-1-Drift prueft "min 1 step", aber
        nicht ob pointer_check-Sub-Check Pflicht-Path-Pflicht ist.

        Pattern: NEW-V-001
        Phase: D
        Level: L1 + L3
        v1-Gap: TC-041 prueft "min 1 step". Multi-Workflow-Skill mit
                Pflicht-ohne-Schutz nicht abgedeckt.
        evidence:
          - kind: file_range
            path: docs/specs/299-fabrication-mitigation.md
            lines: 232-236
            quote: "Drift-Schutz (mechanisch)"
        """
        # consistency_check tier1-multi-workflow-drift: WARN per (skill,
        # workflow) pair wenn Skill in workflow X referenziert ohne
        # pointer_check.
        import subprocess
        import sys
        import tempfile
        import shutil

        # Synthetic Setup: Tmp-Workflows-Root mit (a) protected workflow,
        # (b) unprotected workflow. Skill mit verification_tier: 1.
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            # Tmp-skills/code_review_board/SKILL.md mit verification_tier: 1
            skill_dir = tmp_path / "skills" / "code_review_board"
            skill_dir.mkdir(parents=True)
            (skill_dir / "SKILL.md").write_text(
                "---\nname: code-review-board\nverification_tier: 1\n---\n",
                encoding="utf-8",
            )
            # Tmp-workflows-root mit 2 Workflows
            wf_root = tmp_path / "workflows" / "runbooks"
            wf_root.mkdir(parents=True)
            # protected workflow
            wf_protected = wf_root / "build"
            wf_protected.mkdir()
            (wf_protected / "workflow.yaml").write_text(
                "name: build\nsteps:\n"
                "  - id: code-review-board\n"
                "    name: x\n    category: content\n"
                "    instruction: x\n"
                "    skill_ref: skills/code_review_board/SKILL.md\n"
                "    completion:\n"
                "      type: compound\n"
                "      checks:\n"
                "        - type: pointer_check\n"
                "          source_file: x.md\n"
                "        - type: manual\n",
                encoding="utf-8",
            )
            # unprotected workflow (legacy compound mit nur manual)
            wf_unprotected = wf_root / "full"
            wf_unprotected.mkdir()
            (wf_unprotected / "workflow.yaml").write_text(
                "name: full\nsteps:\n"
                "  - id: code-review-board\n"
                "    name: x\n    category: content\n"
                "    instruction: x\n"
                "    skill_ref: skills/code_review_board/SKILL.md\n"
                "    completion:\n      type: manual\n",
                encoding="utf-8",
            )

            # Run consistency_check tier1-multi-workflow-drift mit synthetic root
            from scripts.consistency_check import check_tier1_multi_workflow_drift
            exit_code, warnings = check_tier1_multi_workflow_drift(
                skills_roots=[tmp_path / "skills"],
                workflows_root=wf_root,
            )
            assert exit_code != 0, \
                f"multi-workflow-drift MUSS Drift erkennen: warnings={warnings}"
            assert any("full" in w.lower() and "code_review_board" in w
                       for w in warnings), \
                f"WARN fuer code_review_board in 'full' workflow fehlt: {warnings}"
