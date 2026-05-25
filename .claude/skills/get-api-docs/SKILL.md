---
name: get-api-docs
description: Fetch current API documentation for external libraries before coding against them. Prevents hallucinated parameters and stale interfaces. Triggers when about to write code against an unfamiliar or version-sensitive external API/library; NOT for the stdlib or well-known stable APIs.
---

# Skill: get-api-docs (Wrapper)

<!-- generated-by: scripts/generate_skill_wrappers.py (do not hand-edit) -->

This is the Claude-Code-discoverable wrapper. The full
orchestrator-neutral protocol — methodology, contract, modes,
red flags — lives in the SoT:

**SoT:** `skills/get_api_docs/SKILL.md`

Read the SoT and follow it. This wrapper is a generated derived
artifact (`scripts/generate_skill_wrappers.py`); it exists only so
Claude Code can inject the skill into the available-skills
system-reminder for proactive discovery. Do not hand-edit — edits
are reverted on the next generator run and flagged by
`consistency_check`.
