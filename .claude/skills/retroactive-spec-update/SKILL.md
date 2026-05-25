---
name: retroactive-spec-update
description: Retroactively update existing specs to match the as-is code state. Git commits give SCOPE, source code is the EVIDENCE. Walk through the spec section by section, read the relevant source files completely, compare, update. Prevents feature creep by never asking "what could be added" — only "what does the code already do that the spec does not describe". Triggers when an existing spec must be synced to the as-is code state (code = evidence); NOT for authoring new specs (use spec_authoring) or amending locked specs by intent (use spec-amendment-discipline).
---

# Skill: retroactive-spec-update (Wrapper)

<!-- generated-by: scripts/generate_skill_wrappers.py (do not hand-edit) -->

This is the Claude-Code-discoverable wrapper. The full
orchestrator-neutral protocol — methodology, contract, modes,
red flags — lives in the SoT:

**SoT:** `skills/retroactive_spec_update/SKILL.md`

Read the SoT and follow it. This wrapper is a generated derived
artifact (`scripts/generate_skill_wrappers.py`); it exists only so
Claude Code can inject the skill into the available-skills
system-reminder for proactive discovery. Do not hand-edit — edits
are reverted on the next generator run and flagged by
`consistency_check`.
