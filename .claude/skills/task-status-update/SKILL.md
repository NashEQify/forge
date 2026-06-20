---
name: task-status-update
description: 'Closing or completing a task (status→done), or any other task-status change — start (→in_progress), block, supersede, wontfix, absorbed. The ONLY allowed way to change a task''s `status`: it also runs the cross-task graph closure, plan.yaml ref sweep, atomic archive move + integrity guard, and the persist-gate — all silently lost on a raw YAML edit. Use when a task reaches `done` or any status must change; never hand-edit the `status:` field. NOT for creating a task (use task-creation) and NOT for content edits to an OPEN task''s body (manual) — though the terminal sweep of `blocked_by` / cross-refs on OTHER tasks IS in scope.'
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
