---
name: sectional-deep-review
description: Deep review for large foundation specs (>1000 lines, many subsections). Splits the spec into pattern groups, reviews each with cross-reference context, fixes per group, then runs a full-spec review for composition and gaps. Triggers when reviewing a large foundation spec (>1000 lines, many subsections) that needs pattern-group splitting (review execute, type=sectional); NOT for small specs (use spec_board).
---

# Skill: sectional-deep-review (Wrapper)

<!-- generated-by: scripts/generate_skill_wrappers.py (do not hand-edit) -->

This is the Claude-Code-discoverable wrapper. The full
orchestrator-neutral protocol — methodology, contract, modes,
red flags — lives in the SoT:

**SoT:** `skills/sectional_deep_review/SKILL.md`

Read the SoT and follow it. This wrapper is a generated derived
artifact (`scripts/generate_skill_wrappers.py`); it exists only so
Claude Code can inject the skill into the available-skills
system-reminder for proactive discovery. Do not hand-edit — edits
are reverted on the next generator run and flagged by
`consistency_check`.
