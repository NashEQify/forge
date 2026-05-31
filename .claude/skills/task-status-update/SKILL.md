---
name: task-status-update
description: Coherent task-status change. The only allowed way to change `status` in task YAMLs. On terminal status (done, superseded, wontfix, absorbed) it also sweeps cross-task `blocked_by` and `docs/plan.yaml` inline refs so the task-graph and plan stay consistent. Triggers when a task's status must change (the only allowed path); NOT for content edits to task bodies of OPEN tasks — the terminal-status sweep of `blocked_by` / cross-refs on OTHER tasks IS in scope.
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
