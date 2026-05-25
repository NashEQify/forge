---
name: spec-board
description: 'Multi-perspective spec quality review. Checks whether an existing spec is rebuild-ready: can an implementer rebuild it 1:1 from the spec alone? 5 dimensions: completeness, consistency, implementability, interface contracts, dependencies. NOT for spec authoring (new specs) and NOT for retroactive code sync — those are spec_authoring and retroactive_spec_update. The board is the quality check AFTER writing. Triggers when an existing spec must be checked for rebuild-readiness AFTER writing; NOT for spec authoring (use spec_authoring) or retroactive code sync (use retroactive_spec_update).'
---

# Skill: spec-board (Wrapper)

<!-- generated-by: scripts/generate_skill_wrappers.py (do not hand-edit) -->

This is the Claude-Code-discoverable wrapper. The full
orchestrator-neutral protocol — methodology, contract, modes,
red flags — lives in the SoT:

**SoT:** `skills/spec_board/SKILL.md`

Read the SoT and follow it. This wrapper is a generated derived
artifact (`scripts/generate_skill_wrappers.py`); it exists only so
Claude Code can inject the skill into the available-skills
system-reminder for proactive discovery. Do not hand-edit — edits
are reverted on the next generator run and flagged by
`consistency_check`.
