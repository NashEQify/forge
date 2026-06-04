---
name: spec-board
description: Multi-perspective review of whether an EXISTING spec is rebuild-ready — could an implementer rebuild it 1:1 from the spec alone? Use when a spec needs a quality check after writing and before build (completeness / consistency / contract / dependency gaps); reach for it instead of eyeballing a spec yourself. NOT for authoring a new spec (use spec_authoring) or syncing a spec to code (use retroactive_spec_update).
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
