---
name: adversary-test-plan
description: Adversary-driven test-plan extension BEFORE implementation. Code-adversary reviews the tester design output and adds edge-case TCs the implementer's cognitive bias systematically misses. RED tests are a required pre-fix gate (mechanical definition of done). Pattern lesson 388 NEW-V-001 5x replay. Triggers when a tester design output exists and RED edge-case TCs are needed before implementation (build prepare); NOT for post-implementation review (use code_review_board).
---

# Skill: adversary-test-plan (Wrapper)

<!-- generated-by: scripts/generate_skill_wrappers.py (do not hand-edit) -->

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
