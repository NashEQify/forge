---
name: show-open-tasks
description: Render an overview table of the OPEN tasks in a docs/tasks/ tree (status not in a terminal set). Each row shows the task intent (title + summary first sentence), status, the YAML updated date, and the last git change (date + commit subject) that touched the task files. Triggers when the user wants a task list/overview/status table ("liste aller tasks", "zeig offene tasks", "task overview"); NOT for changing task status (use task-status-update) or creating a task (use task-creation).
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
