---
name: consistency-check
description: Checks the structural integrity of the repo. Dead references, orphan files, adapter SoT drift, navigation desync, doc-currency drift (stale banners + reading-map index-omission). Triggers when structural repo integrity must be validated after structural changes or before commit (dead refs, orphans, adapter drift, stale "Task N pending" banners, reading-map gone stale); NOT for content/logic review.
---

# Skill: consistency-check (Wrapper)

<!-- generated-by: scripts/generate_skill_wrappers.py (do not hand-edit) -->

This is the Claude-Code-discoverable wrapper. The full
orchestrator-neutral protocol — methodology, contract, modes,
red flags — lives in the SoT:

**SoT:** `skills/consistency_check/SKILL.md`

Read the SoT and follow it. This wrapper is a generated derived
artifact (`scripts/generate_skill_wrappers.py`); it exists only so
Claude Code can inject the skill into the available-skills
system-reminder for proactive discovery. Do not hand-edit — edits
are reverted on the next generator run and flagged by
`consistency_check`.
