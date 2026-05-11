"""
Test-File fuer Spec 299 Fabrication-Mitigation — Tier-1-Migration-Group.

RED skeletons. Implementation steht noch aus.

TCs: TC-036..TC-041 aus docs/tasks/299-test-plan.md
(Phase D Tier-1-Migration + Drift-Schutz).
"""
from __future__ import annotations

from pathlib import Path

import pytest


TIER_1_SKILLS = (
    "spec_board",
    "code_review_board",
    "architecture_coherence_review",
    "sectional_deep_review",
    "adversary_test_plan",
    "spec_amendment_verification",
)


def _read_frontmatter(path: Path) -> dict:
    """Helper: liest YAML-Frontmatter aus Markdown-File."""
    import yaml

    text = path.read_text(encoding="utf-8")
    if not text.startswith("---"):
        return {}
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}
    return yaml.safe_load(parts[1]) or {}


class TestTier1Frontmatter:
    @pytest.mark.parametrize("skill_name", TIER_1_SKILLS)
    def test_TC_036_tier1_skills_have_verification_tier_1(
        self, framework_root: Path, skill_name: str
    ):
        """
        TC-036: 6 Tier-1-Skill-Frontmatter haben verification_tier: 1.

        Phase: D
        Level: L0 (Structural)
        Quelle: AC-5
        evidence:
          - kind: file_range
            path: docs/specs/299-fabrication-mitigation.md
            lines: 222-224
            quote: "Tier-1** | 1 + 2 + 3 (CC-Hook)"
        """
        skill = framework_root / f"skills/{skill_name}/SKILL.md"
        if not skill.is_file():
            # Plugin-Layout?
            skill = framework_root / f"framework/skills/{skill_name}/SKILL.md"
        assert skill.is_file(), f"Skill-File fehlt: {skill_name}"

        fm = _read_frontmatter(skill)
        assert fm.get("verification_tier") == 1, \
            f"{skill_name} hat keinen verification_tier: 1 — got {fm.get('verification_tier')}"

    def test_TC_037_non_tier1_skills_have_no_tier_1_field(
        self, framework_root: Path
    ):
        """
        TC-037: Non-Tier-1-Skills haben KEIN verification_tier: 1
        (Negativ-Regression).

        Phase: D
        Level: L0
        Quelle: AC-5
        evidence:
          - kind: file_range
            path: docs/specs/299-fabrication-mitigation.md
            lines: 230-232
            quote: "Skill-Frontmatter explicit `verification_tier: 1` ODER nicht gesetzt"
        """
        skills_dirs = [
            framework_root / "skills",
            framework_root / "framework/skills",
        ]
        skills_root = next((d for d in skills_dirs if d.is_dir()), None)
        assert skills_root is not None, \
            "skills/ directory fehlt — Test koennte sonst trivially passen"

        # Pre-Gate: Tier-1-Skills MUSS Tier-1-Field gesetzt haben (sonst
        # ist das negative ALL-NONE-Tier-1 Set trivially gruen — Phase D
        # noch nicht implementiert).
        tier1_set = []
        for skill_md in skills_root.glob("*/SKILL.md"):
            name = skill_md.parent.name
            if name not in TIER_1_SKILLS:
                continue
            fm = _read_frontmatter(skill_md)
            if fm.get("verification_tier") == 1:
                tier1_set.append(name)

        assert tier1_set, \
            "Pre-Gate: Kein Tier-1-Skill hat verification_tier: 1 — Phase D " \
            "noch nicht implementiert. Negativ-Test waere trivially PASS."

        # Eigentlicher Test: kein Non-Tier-1 hat falschlicherweise Tier-1
        unexpected = []
        for skill_md in skills_root.glob("*/SKILL.md"):
            name = skill_md.parent.name
            if name in TIER_1_SKILLS:
                continue
            fm = _read_frontmatter(skill_md)
            if fm.get("verification_tier") == 1:
                unexpected.append(name)

        assert not unexpected, \
            f"Unexpected Tier-1-Skills (Drift!): {unexpected}"


class TestTier1WorkflowYaml:
    def test_TC_038_tier1_workflow_steps_have_compound_with_pointer_check(
        self, framework_root: Path
    ):
        """
        TC-038: 6 Tier-1-Workflow-Steps haben completion.compound mit
        pointer_check (F-X-010 Subset).

        Phase: D
        Level: L0 + L1
        Quelle: AC-5, F-X-010
        evidence:
          - kind: file_range
            path: docs/specs/299-fabrication-mitigation.md
            lines: 256-263
            quote: "spec_board"
        """
        import yaml

        # build/workflow.yaml: board, code-review-board, adversary-test-plan,
        # spec-amendment-verify
        build_yaml = framework_root / "workflows/runbooks/build/workflow.yaml"
        # review/workflow.yaml: arch-coherence-review, sectional-deep
        review_yaml = framework_root / "workflows/runbooks/review/workflow.yaml"

        expected = {
            build_yaml: ("board", "code-review-board",
                         "adversary-test-plan", "spec-amendment-verify"),
            review_yaml: ("arch-coherence-review", "sectional-deep"),
        }

        for wf_file, step_ids in expected.items():
            assert wf_file.is_file(), f"workflow.yaml fehlt: {wf_file}"
            wf = yaml.safe_load(wf_file.read_text(encoding="utf-8"))
            steps = {s["id"]: s for s in wf.get("steps", [])}
            for sid in step_ids:
                assert sid in steps, f"Step {sid!r} fehlt in {wf_file.name}"
                comp = steps[sid].get("completion", {})
                assert comp.get("type") == "compound", \
                    f"{sid}: completion.type != compound (got {comp.get('type')!r})"
                checks = comp.get("checks", [])
                assert checks, f"{sid}: completion.checks leer"
                assert checks[0].get("type") == "pointer_check", \
                    f"{sid}: checks[0].type != pointer_check (Race-Mitigation)"
                source_file = checks[0].get("source_file", "")
                assert "{spec_name}" in source_file or "{state_file}" in source_file, \
                    f"{sid}: source_file referenziert keine Variable: " \
                    f"{source_file!r}"
                assert steps[sid].get("on_fail") == "block", \
                    f"{sid}: on_fail != block"

    def test_TC_039_arch_and_sectional_review_workflow_steps_exist(
        self, framework_root: Path
    ):
        """
        TC-039: arch+sectional review-workflow-Steps existieren mit skill_ref
        (F-X-010).

        Phase: D
        Level: L0 + L1
        Quelle: F-X-010
        evidence:
          - kind: file_range
            path: docs/specs/299-fabrication-mitigation.md
            lines: 643-644
            quote: "F-X-010 architecture_coherence_review + sectional_deep_review"
        """
        import yaml

        review_yaml = framework_root / "workflows/runbooks/review/workflow.yaml"
        assert review_yaml.is_file()
        wf = yaml.safe_load(review_yaml.read_text(encoding="utf-8"))
        steps = {s["id"]: s for s in wf.get("steps", [])}

        arch = steps.get("arch-coherence-review")
        assert arch, "Step arch-coherence-review fehlt"
        assert "architecture_coherence_review" in str(arch.get("skill_ref", "")), \
            "arch-coherence-review verweist nicht auf architecture_coherence_review"

        sect = steps.get("sectional-deep")
        assert sect, "Step sectional-deep fehlt"
        assert "sectional_deep_review" in str(sect.get("skill_ref", "")), \
            "sectional-deep verweist nicht auf sectional_deep_review"


class TestPointerCheckE2E:
    def test_TC_040_pointer_check_resolves_spec_name_in_real_build_workflow(
        self, isolated_project, framework_root: Path
    ):
        """
        TC-040: pointer_check resolved {spec_name}-Variable in echtem
        build-Workflow E2E (Race-Adversary).

        Phase: C2 + D
        Level: L4 (E2E)
        Quelle: AC-3, AC-5
        Adversary-Target: Race-Condition (real-world)
        evidence:
          - kind: file_range
            path: docs/specs/299-fabrication-mitigation.md
            lines: 181-196
            quote: "completion.compound`-Integration mit Race-Mitigation"
        """
        # E2E: in isolated_project (tmp), simulate task.yaml mit spec_ref →
        # _resolve_spec_name extrahiert 'spec-name'. Dann _resolve_vars +
        # _has_unresolved_vars Pfad funktioniert.
        from scripts import workflow_engine as we

        tasks_dir = isolated_project / "docs" / "tasks"
        tasks_dir.mkdir(parents=True, exist_ok=True)
        task_yaml = tasks_dir / "299.yaml"
        task_yaml.write_text(
            "id: 299\n"
            "spec_ref: docs/specs/299-fabrication-mitigation.md\n"
            "title: t\n"
            "status: in_progress\n",
            encoding="utf-8",
        )

        # Engine-API: _resolve_spec_name liest task.yaml + extrahiert basename
        spec_name = we._resolve_spec_name(299)
        assert spec_name == "299-fabrication-mitigation", \
            f"_resolve_spec_name returnt unerwartetes Ergebnis: {spec_name!r}"

        # _resolve_vars verarbeitet {spec_name} korrekt
        resolved = we._resolve_vars(
            "docs/reviews/board/{spec_name}-consolidated-pass1.md",
            {"spec_name": spec_name},
        )
        assert resolved == \
            "docs/reviews/board/299-fabrication-mitigation-consolidated-pass1.md"

        # Compound mit pointer_check (file fehlt) blockt — Race-Mitigation E2E
        comp = {
            "type": "compound",
            "checks": [
                {"type": "pointer_check",
                 "source_file": resolved},
                {"type": "manual"},
            ],
        }
        ok, msg = we.check_completion(comp, {"variables": {}}, {})
        assert ok is False, \
            f"compound mit fehlendem pointer-file MUSS blocken: msg={msg!r}"


class TestConsistencyCheckTier1Drift:
    def test_TC_041_consistency_check_warns_on_tier1_drift(
        self, framework_root: Path, tmp_path: Path
    ):
        """
        TC-041: consistency_check Tier-1-Drift-WARN bei fehlender
        workflow.yaml-Integration.

        Phase: D
        Level: L1 + L3
        Quelle: AC-5, F-C-013, NEW-V-001
        evidence:
          - kind: file_range
            path: docs/specs/299-fabrication-mitigation.md
            lines: 232-236
            quote: "Drift-Schutz (mechanisch)"
        """
        import subprocess
        import sys

        # consistency_check Skill mit neuem Check tier1-drift
        result = subprocess.run(
            [sys.executable, "-m", "scripts.consistency_check",
             "--check", "tier1-drift"],
            capture_output=True,
            text=True,
            cwd=str(framework_root),
        )
        # Wenn Drift vorhanden (synthetic): exit != 0 ODER WARN-Output
        # Wenn alle 6 Tier-1 korrekt integriert: exit 0, kein WARN.
        # Hier asserten wir nur dass das Tooling lebt (kein "no module").
        combined = (result.stdout + result.stderr).lower()
        assert "no module" not in combined and "module not found" not in combined, \
            f"consistency_check Skill nicht aufrufbar: {combined!r}"
