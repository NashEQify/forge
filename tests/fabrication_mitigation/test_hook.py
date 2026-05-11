"""
Test-File fuer Spec 299 Fabrication-Mitigation — CC-Hook-Group.

RED skeletons. Implementation steht noch aus.

TCs: TC-042..TC-045 aus docs/tasks/299-test-plan.md
(Phase E CC-PostToolUse-Hook orchestrators/claude-code/hooks/
evidence-pointer-check.sh).
"""
from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest


HOOK_REL = "orchestrators/claude-code/hooks/evidence-pointer-check.sh"
SETTINGS_REL = ".claude/settings.json"


class TestCCHook:
    def test_TC_042_hook_file_exists_and_executable(self, framework_root: Path):
        """
        TC-042: evidence-pointer-check.sh existiert und nutzt
        board-output-check.sh-Pattern.

        Phase: E
        Level: L0 (Structural)
        Quelle: AC-6
        evidence:
          - kind: file_range
            path: docs/specs/299-fabrication-mitigation.md
            lines: 286-289
            quote: "Pattern:** wiederverwendet `board-output-check.sh"
        """
        hook = framework_root / HOOK_REL
        assert hook.is_file(), f"Hook fehlt: {hook}"
        assert os.access(hook, os.X_OK), f"Hook nicht ausfuehrbar: {hook}"

        text = hook.read_text(encoding="utf-8")
        # Pattern-Re-Use: grep -F + path-resolution
        assert "grep" in text, "Hook nutzt grep nicht (Pattern-Reuse fehlt?)"

    def test_TC_043_settings_json_registers_posttooluse_hook(
        self, framework_root: Path
    ):
        """
        TC-043: .claude/settings.json registriert PostToolUse-Hook.

        Phase: E
        Level: L0
        Quelle: AC-6
        evidence:
          - kind: file_range
            path: docs/specs/299-fabrication-mitigation.md
            lines: 471-472
            quote: "Settings-Registration in `.claude/settings.json` PostToolUse-Hooks"
        """
        settings = framework_root / SETTINGS_REL
        assert settings.is_file(), f"settings.json fehlt: {settings}"

        data = json.loads(settings.read_text(encoding="utf-8"))
        hooks = data.get("hooks", {})
        post = hooks.get("PostToolUse", [])
        assert post, "Keine PostToolUse-Hooks registriert"

        found = any(
            "evidence-pointer-check" in str(entry) for entry in post
        )
        assert found, "evidence-pointer-check.sh nicht in PostToolUse-Hooks"

    def test_TC_044_hook_filters_to_tier1_skill_subagent_outputs(
        self, framework_root: Path, tmp_path: Path
    ):
        """
        TC-044: Hook filtert auf Tier-1-Skill-Sub-Agent-Outputs (F-I-016).

        Phase: E
        Level: L4 (E2E Hook-Trigger)
        Quelle: AC-6, F-I-016
        evidence:
          - kind: file_range
            path: docs/specs/299-fabrication-mitigation.md
            lines: 645-646
            quote: "F-I-016 Hook-Bash-Filter-Mechanik unspezifiziert"
        """
        hook = framework_root / HOOK_REL
        assert hook.is_file()

        # Sub-Agent-Output-File mit Tier-1-skill_ref im Prompt-Pattern
        # (Implementer waehlt Inferenz-Pfad — wir simulieren generisches
        # PostToolUse-Event via stdin/env-Var, je nach Hook-Convention).
        tier1_event = json.dumps({
            "tool_name": "Task",
            "tool_input": {
                "subagent_type": "spec-board",
                "prompt": "framework/skills/spec_board/SKILL.md ...",
            },
            "tool_response": {"output_file": "docs/reviews/board/x.md"},
        })

        result = subprocess.run(
            [str(hook)],
            input=tier1_event,
            capture_output=True,
            text=True,
            cwd=str(framework_root),
            timeout=10,
        )
        # Tier-1: Hook MUST process (kein silent-exit-0 ohne Filter-Match)
        # Erwartung: Hook printet WARN/INFO ueber evidence-Validierung ODER
        # exit-code zeigt Filter-Pass.
        # Schwache Assertion: Hook produziert irgendwelchen Output ODER
        # exit != 0 wenn Output-File fehlt.
        combined = result.stdout + result.stderr
        assert combined or result.returncode != 0, \
            "Hook hat nichts ausgegeben fuer Tier-1-Trigger — Filter falsch?"

        # Non-Tier-1: Hook silent skip
        non_tier1_event = json.dumps({
            "tool_name": "Task",
            "tool_input": {
                "subagent_type": "frame",
                "prompt": "framework/skills/frame/SKILL.md ...",
            },
            "tool_response": {},
        })
        result2 = subprocess.run(
            [str(hook)],
            input=non_tier1_event,
            capture_output=True,
            text=True,
            cwd=str(framework_root),
            timeout=10,
        )
        # Non-Tier-1: silent (no output, exit 0)
        assert result2.returncode == 0, \
            f"Non-Tier-1 muss silent-skip exit 0: {result2.returncode}"

    def test_TC_045_hook_warn_severity_on_match_failure(
        self, framework_root: Path, tmp_path: Path
    ):
        """
        TC-045: Hook WARN-Severity bei Match-Failure (initial).

        Phase: E
        Level: L4
        Quelle: AC-6, §4.1
        evidence:
          - kind: file_range
            path: docs/specs/299-fabrication-mitigation.md
            lines: 295-298
            quote: "Match-Failure → WARN (initial) ODER BLOCK"
        """
        hook = framework_root / HOOK_REL
        assert hook.is_file()

        # Tier-1-Sub-Agent-Output mit fabricated quote
        out = tmp_path / "fab.md"
        out.write_text(
            "---\nschema_version: 1\nevidence:\n"
            "  - kind: file_range\n"
            f"    path: {out.name}\n"
            "    lines: 1-1\n"
            '    quote: "this quote does not match the file"\n---\nbody\n',
            encoding="utf-8",
        )

        event = json.dumps({
            "tool_name": "Task",
            "tool_input": {
                "subagent_type": "spec-board",
                "prompt": f"framework/skills/spec_board/SKILL.md output_file={out}",
            },
            "tool_response": {"output_file": str(out)},
        })
        result = subprocess.run(
            [str(hook)],
            input=event,
            capture_output=True,
            text=True,
            cwd=str(framework_root),
            timeout=10,
        )
        # WARN-only initial: Hook prints WARN aber returncode 0 (kein BLOCK)
        combined = (result.stdout + result.stderr).lower()
        assert "warn" in combined or "fabricat" in combined or "fail" in combined, \
            f"WARN-output fehlt: {combined!r}"
        # Initial WARN-only — Spec sagt WARN nicht BLOCK
        assert result.returncode == 0, \
            f"Hook initial WARN-only, kein BLOCK: returncode={result.returncode}"
