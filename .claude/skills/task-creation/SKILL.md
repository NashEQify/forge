---
name: task-creation
description: Structured task creation. Self-contained tasks with ACs, intent_chain, and a duplicate + dependency check. Task quality determines downstream quality. Triggers when actionable work needs tracking as a new task (intake ACTIONABLE, root-cause fix-task, spec decomposition); NOT for direct YAML edits or sofort-fixes.
---

# Skill: task-creation (Wrapper)

<!-- generated-by: scripts/generate_skill_wrappers.py (do not hand-edit) -->

This is the Claude-Code-discoverable wrapper. The full
orchestrator-neutral protocol — methodology, contract, modes,
red flags — lives in the SoT:

**SoT:** `skills/task_creation/SKILL.md`

Read the SoT and follow it. This wrapper is a generated derived
artifact (`scripts/generate_skill_wrappers.py`); it exists only so
Claude Code can inject the skill into the available-skills
system-reminder for proactive discovery. Do not hand-edit — edits
are reverted on the next generator run and flagged by
`consistency_check`.
