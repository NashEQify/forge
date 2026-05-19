---
name: task-status-update
description: Atomic task-status change. The only allowed way to change `status` in task YAMLs. Writes YAML + backlog in one operation. Triggers when a task's status must change (the only allowed path); NOT for content edits to task bodies.
---

# Skill: task-status-update (Wrapper)

<!-- generated-by: scripts/generate_skill_wrappers.py (do not hand-edit) -->

This is the Claude-Code-discoverable wrapper. The full
orchestrator-neutral protocol — methodology, contract, modes,
red flags — lives in the SoT:

**SoT:** `skills/task_status_update/SKILL.md`

Read the SoT and follow it. This wrapper is a generated derived
artifact (`scripts/generate_skill_wrappers.py`); it exists only so
Claude Code can inject the skill into the available-skills
system-reminder for proactive discovery. Do not hand-edit — edits
are reverted on the next generator run and flagged by
`consistency_check`.
