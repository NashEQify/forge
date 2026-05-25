---
name: source-spec-reduce
description: 'Post-authoring source-spec reduction: cut each absorbed section + leave a pointer stub. Required output: drift-items.yaml with 3-way triage (existing-task / new-task / die). When the source is fully dissolved: archive it. Triggers when a source spec''s sections have been absorbed post-authoring and need pointer-stub reduction (build specify); NOT for greenfield specs with no source predecessor.'
---

# Skill: source-spec-reduce (Wrapper)

<!-- generated-by: scripts/generate_skill_wrappers.py (do not hand-edit) -->

This is the Claude-Code-discoverable wrapper. The full
orchestrator-neutral protocol — methodology, contract, modes,
red flags — lives in the SoT:

**SoT:** `skills/source_spec_reduce/SKILL.md`

Read the SoT and follow it. This wrapper is a generated derived
artifact (`scripts/generate_skill_wrappers.py`); it exists only so
Claude Code can inject the skill into the available-skills
system-reminder for proactive discovery. Do not hand-edit — edits
are reverted on the next generator run and flagged by
`consistency_check`.
