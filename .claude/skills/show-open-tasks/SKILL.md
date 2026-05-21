---
name: show-open-tasks
description: 'Render a fast terminal overview of the OPEN tasks in a docs/tasks/ tree (status not in a terminal set), grouped by priority and sorted by created date descending (newest first). Columns: ID, title, dep (blocked_by IDs), status, created, touched. Script-less: the methodology below is run directly. Triggers when the user wants a task list/overview/status table ("liste aller tasks", "zeig offene tasks", "task overview"); NOT for changing task status (use task-status-update) or creating a task (use task-creation).'
---

# Skill: show-open-tasks (Wrapper)

<!-- generated-by: scripts/generate_skill_wrappers.py (do not hand-edit) -->

This is the Claude-Code-discoverable wrapper. The full
orchestrator-neutral protocol — methodology, contract, modes,
red flags — lives in the SoT:

**SoT:** `skills/show_open_tasks/SKILL.md`

Read the SoT and follow it. This wrapper is a generated derived
artifact (`scripts/generate_skill_wrappers.py`); it exists only so
Claude Code can inject the skill into the available-skills
system-reminder for proactive discovery. Do not hand-edit — edits
are reverted on the next generator run and flagged by
`consistency_check`.
