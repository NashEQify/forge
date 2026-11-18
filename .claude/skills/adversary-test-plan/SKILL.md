---
name: adversary-test-plan
description: Adversary extension of a test plan BEFORE implementation — a code-adversary adds the edge-case tests the implementer's bias systematically misses (RED tests as a required pre-fix gate). Triggers when the change touches a safety floor (security/auth/secrets, schema/state-format/data migration, public contract, live infrastructure) and a tester design output exists (build prepare); NOT for post-implementation review (use code_review_board).
---

# Skill: adversary-test-plan (Wrapper)

<!-- generated-by: scripts/generate_skill_wrappers.py (do not hand-edit) -->

Read and follow `framework/work-principle.md` before taking up work.
Resolve it against the same framework root as the SoT; retain the consumer CWD.

This is the Claude-Code-discoverable wrapper. The full
orchestrator-neutral protocol — methodology, contract, modes,
red flags — lives in the SoT:

**SoT:** `skills/adversary_test_plan/SKILL.md`

Read the SoT and follow it. This wrapper is a generated derived
artifact (`scripts/generate_skill_wrappers.py`); it exists only so
Claude Code can inject the skill into the available-skills
system-reminder for proactive discovery. Do not hand-edit — edits
are reverted on the next generator run and flagged by
`consistency_check`.
