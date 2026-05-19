---
name: code-review-board
description: 'Multi-perspective code review. 2 levels: L1 (focused) + L2 (full board). Triggers when a code diff needs multi-perspective review before merge (build verify, fix L1); NOT for PR-level checks (use /review) and NOT for spec review (use spec_board).'
---

# Skill: code-review-board (Wrapper)

<!-- generated-by: scripts/generate_skill_wrappers.py (do not hand-edit) -->

This is the Claude-Code-discoverable wrapper. The full
orchestrator-neutral protocol — methodology, contract, modes,
red flags — lives in the SoT:

**SoT:** `skills/code_review_board/SKILL.md`

Read the SoT and follow it. This wrapper is a generated derived
artifact (`scripts/generate_skill_wrappers.py`); it exists only so
Claude Code can inject the skill into the available-skills
system-reminder for proactive discovery. Do not hand-edit — edits
are reverted on the next generator run and flagged by
`consistency_check`.
