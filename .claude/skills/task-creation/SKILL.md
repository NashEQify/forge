---
name: task-creation
description: Use this skill to create a new task with proper YAML+MD structure, duplicate-check against existing pending/in_progress tasks, cross-task dependency-check, and triage (sofort-fix vs task anlegen). Required path for new task creation — direct YAML edits bypass duplicate/dependency checks. Triggers when user explicitly asks to create a task ("leg einen Task an", "task anlegen", "wir brauchen einen Task für X"), when an Intake Gate identifies ACTIONABLE work that needs tracking, when a Root-Cause-Fix produces a fix-task, or when spec-decomposition emits new tasks.
---

# Skill: task-creation (Wrapper)

This is the Claude-Code-discoverable wrapper. The full 5-step protocol
(duplicate-check, dependency-check, triage, intent_chain, YAML+MD write,
plan_engine validate) lives in the orchestrator-neutral SoT:

**SoT:** `skills/task_creation/SKILL.md`

Read the SoT and follow it. This wrapper exists only so Claude Code can
inject the skill into the available-skills system-reminder for proactive
discovery — the methodology is unchanged.
