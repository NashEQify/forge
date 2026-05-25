---
name: cross-spec-consistency-check
description: 'Pre-authoring conflict detection between specs in the source-grounding set of the current build run. Four pattern classes (API naming drift, concept double authority, schema drift, authority overlap). Output: drift-list- cross.md with severity triage. Block on high severity. Triggers when a build run has a source-grounding set of 2+ specs to check pre-authoring (build specify); NOT for greenfield specs with no source set.'
---

# Skill: cross-spec-consistency-check (Wrapper)

<!-- generated-by: scripts/generate_skill_wrappers.py (do not hand-edit) -->

This is the Claude-Code-discoverable wrapper. The full
orchestrator-neutral protocol — methodology, contract, modes,
red flags — lives in the SoT:

**SoT:** `skills/cross_spec_consistency_check/SKILL.md`

Read the SoT and follow it. This wrapper is a generated derived
artifact (`scripts/generate_skill_wrappers.py`); it exists only so
Claude Code can inject the skill into the available-skills
system-reminder for proactive discovery. Do not hand-edit — edits
are reverted on the next generator run and flagged by
`consistency_check`.
