# Convoy format

Purpose: objective progress tracking. Single SoT for the state of one objective.
Location: `workspaces/<objective>/convoy.md`
Exists: only when an objective has >=2 tasks.

---

## Why convoy.md

"How many tasks in objective X are done?" requires opening all task files
without convoy.md. With 10+ tasks, that's context overhead with no value.

convoy.md solves:
- progress overview in one file
- cross-domain impact check (LIFE-004) without scanning the task corpus
- context-tier-2 loading: one file instead of N files on objective wakeup
- main-code-agent knows which tasks belong to the objective without searching

---

## Format

  # Convoy: [objective-slug]

  status: [pending|in_progress|done|blocked]
  started: [YYYY-MM-DD]
  updated: [YYYY-MM-DD]

  ## Tasks

  | ID  | Title              | Status      | Assignee   | Notes            |
  |-----|--------------------|-------------|------------|------------------|
  | NNN | [short title]      | [status]    | [assignee] | [short note]     |

  ## Blocked by
  - [task-id: blocker description]

  ## Done check (from intent.md)
  - [x] [done criterion] ([task reference])
  - [ ] [remaining done criterion]

---

## SoT boundary

convoy.md is SoT for: objective status, task list, task status (overview), notes.
Task file is SoT for: task detail, workflow steps, blocker detail, prose.

Redundancy is minimal and deliberate: convoy.md mirrors task status.
That redundancy is accepted for context-budget gains.

---

## When to update

SoT for update obligations: `framework/task-format.md`
(section convoy-update-required).

- On task status changes in this objective
- On `save` when a task from this objective was active
- When main-code-agent creates subtasks (new row in tasks table)
- When a new task is added to this objective

---

## Context loading

convoy.md loads at objective wakeup as part of tier 2:
after `plan_engine --boot`, before individual task files.

---

## Objective status

Field `status` in convoy.md mirrors the overall state:
- `pending`: no task started yet
- `in_progress`: at least one task in_progress
- `done`: all done-check criteria from intent.md fulfilled
- `blocked`: no task in_progress, at least one blocked

---

## Lifecycle

Created when the second task for an objective is created.
Stays after objective completion (historical record).
Status is set to `done`; no further updates.

---

## Example

  # Convoy: cross-session-continuity

  status: in_progress
  started: 2026-05-01
  updated: 2026-05-09

  ## Tasks

  | ID  | Title                          | Status      | Assignee         | Notes      |
  |-----|--------------------------------|-------------|------------------|------------|
  | 101 | Spec the handoff format        | done        | buddy            |            |
  | 102 | Implement save-side write      | done        | main-code-agent  |            |
  | 103 | Implement boot-side read       | in_progress | main-code-agent  | Step 3/4   |
  | 104 | Cross-session smoke test       | pending     | tester           | after 103  |

  ## Blocked by
  - none

  ## Done check (from intent.md)
  - [x] Handoff format specified (101)
  - [x] Save writes the handoff (102)
  - [ ] Boot reads the handoff (103)
  - [ ] Round-trip verified (104)
