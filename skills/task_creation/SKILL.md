---
name: task-creation
description: >
  Structured task creation. Self-contained tasks with ACs,
  intent_chain, and a duplicate check. Task quality determines
  downstream quality.
status: active
invocation:
  primary: user-facing
  secondary: [workflow-step]
disable-model-invocation: false
uses: []
---

# Skill: task-creation

## Purpose

Structured, high-quality task creation. Ensures that every new
task is self-contained, has clear ACs, carries an `intent_chain`,
and does not produce duplicates. Task quality sets the upper bound
on the quality of all downstream work.

## Who and when

Buddy. Calls this skill on:

| Trigger | Context |
|---------|---------|
| Intake gate ACTIONABLE — future work identified | Buddy creates a task instead of an ad-hoc note |
| Root-cause-fix primitive step 4 — the fix is a task | Defect task with root-cause info |
| User says "create a task for X" | Explicit instruction |
| Spec process produces a new task | Result of decomposition |

## Input

- **problem:** what is broken / missing / wanted? (raw input)
- **context** (optional): additional context (defect info,
  incident, conversation)
- **source** (optional): `intake` | `root-cause-fix` | `user` |
  `decomposition`

## The 5 steps

### 1. Duplicate + dependency check (MUST)

Two checks in the same scan of `docs/tasks/`:

**(a) Duplicate check:** is there a task with the same goal
(semantic, not just title match)? A subset of an existing one? An
existing one becoming obsolete? Action: duplicate → no new task,
reference the existing one. Subset → fold into the existing task as
an AC / comment. Obsolescence-maker → supersede the existing one.
No duplicate → continue.

**(b) Cross-task dependency check (required, not optional):** for
every pending / in_progress task, check — is there a logical
dependency to the new task in **either** direction?

- **The new task needs the result of an existing task** → the new
  task gets `blocked_by: [NNN]` for the predecessor(s). Example:
  the new task documents a framework state. An existing pending
  task is changing that framework state. → the new task gets
  `blocked_by: [<existing>]`.
- **An existing task needs the result of the new task** → the
  existing task gets the new task added to its `blocked_by`.
  Editing the existing YAML is required, not optional.

Trigger questions for the dependency check (substantive, not
regex):
- Does either task change framework artifacts that the other
  documents / uses / extends?
- Does either task produce specs / decisions that the other
  needs?
- Is A's scope a precondition for B's scope?
- Would running them in parallel produce rework (B documents the
  state, A changes the state → B repeats work)?

Yes on any → record the dependency. No on all → `blocked_by: []`.
Document the dependency rationale in the MD body as a
`## Dependency: blocked_by N` block (why, which direction, order).

Detail + examples: `REFERENCE.md`.

### 2. Triage (MUST)

Fix immediately or create a task? Criteria: effort, reversibility,
dependencies, context, interruption. All "fix immediately"
criteria met → light plan, no task; **steps 3-5 are skipped**.
Otherwise → continue. Triage table: `REFERENCE.md`.

### 3. Derive the intent_chain (MUST)

Derive from the active context. Required field on delegation;
optional in direct user conversation. Format and rules (build +
life variants): `framework/intent-tree.md` §intent_chain.

### 4. Write the task file (MUST)

Format: `docs/tasks/NNN.yaml` + `NNN.md` (see
`framework/task-format.md`).

**Required YAML fields:** `id`, `title`, `status`, `milestone`,
`blocked_by`, `created`, `updated`, `effort` (S/M/L/XL, required
when status=pending or in_progress).

**`milestone` MUST** be a key from `docs/plan.yaml` milestones.

**`spec_ref` required check:** when the task implements an
existing spec → `spec_ref` MUST point at the spec. `null` only
when no spec exists.

**Dependency-spike check:** new external dependency with >1
integration point? → place a spike task (PoC / eval) ahead of it
as `blocked_by`. Detail: `REFERENCE.md`.

**MD content quality** (required check before commit, not YAML
fields): problem (is the why understandable?), intent (goal
without prescribing the path?), description (self-contained?),
priority (plausible?), area (does it fit?). FAIL criteria:
`REFERENCE.md`.

**Optional but always check:** `context_manifest` (when context
is clear) and `workflow_template` (decision / research —
`standard-build` deprecated, build via the runbook). Detail +
YAML signature: `REFERENCE.md`.

The "Not yet" block is required — an empty block is invalid
(DR-10). **No exclusion from the user → ask actively.** Optional
fields (ACs, constraints, deps) when known.

### 5. Validation (MUST)

`python3 $FRAMEWORK_DIR/scripts/plan_engine.py --validate`. The
new task must appear without an ERROR. Checks: milestone exists in
plan.yaml, blocked_by references existing tasks, no cycle.
**FAIL →** correct the task file (milestone vs `docs/plan.yaml`,
blocked_by IDs vs `docs/tasks/`) and re-validate. Repeated FAIL →
delete the task files; escalate to the user (NNN is reused).

## SoT boundary

The task YAML is the SoT for metadata (status, deps, effort,
assignee). `docs/plan.yaml` is the SoT for milestone assignment.
There is no separate backlog index — `plan_engine` computes the
overviews.

## Output format

```
Task creation: [NNN] [title]
Duplicate check: no duplicate / duplicate of [NNN] / subset of [NNN]
Triage: fix immediately / create task — [rationale]
milestone: [key from plan.yaml]
File: docs/tasks/NNN.yaml + NNN.md
Validate: plan_engine --validate PASS
```

## Contract

### INPUT
- **Required:** problem — what is broken / missing / wanted?
  (raw input)
- **Optional:** context — additional context (defect info,
  incident, conversation)
- **Optional:** source — `intake` | `root-cause-fix` | `user` |
  `decomposition`
- **Context:** `docs/tasks/` (for duplicate check),
  `docs/plan.yaml` (for milestone assignment),
  `framework/task-format.md` (format SoT).

### OUTPUT
**DELIVERS:**
- Task YAML (`docs/tasks/NNN.yaml`) + task MD
  (`docs/tasks/NNN.md`).
- Duplicate check result (no duplicate / duplicate of / subset of).
- Triage decision (fix immediately / create task + rationale).
- `plan_engine --validate` PASS.

**DOES NOT DELIVER:**
- No spec process — task creation, not spec maturation.
- No status update — that is `task_status_update`.
- No index management — overviews come from `plan_engine`.
- No backlog grooming — no bulk reorganization.

**ENABLES:**
- Build workflow: task as the delegation artifact.
- Spec process: task with `spec_ref` as a tracking anchor.
- Plan engine: task in milestone calculation and the critical
  path.

### DONE
- Duplicate check executed.
- Triage decision taken (fix immediately or create task).
- For a task: YAML + MD written, `intent_chain` derived.
- "Not yet" block filled (not empty).
- `plan_engine --validate` PASS (0 errors).

### FAIL
- **Retry:** `plan_engine --validate` FAIL → correct the task
  file, re-validate.
- **Escalate:** repeated FAIL → delete the task files, escalate
  to the user (NNN is reused).
- **Abort:** duplicate found → no new task, reference the existing
  one.

## Boundary

- **No spec process.** This skill creates tasks. Spec maturation →
  spec process (interview → spec → review → test design)
  separately.
- **No status update.** Status changes → `task_status_update`
  skill.
- **No index management.** Overviews come from
  `plan_engine --boot`, not from this skill.
- **No backlog grooming.** Task merging, re-sorting, or bulk
  reorganization do not belong here.

## Anti-patterns

- **NOT** skipping the duplicate check because "my task is
  certainly new". **INSTEAD** always scan. Because: duplicates
  arise from slightly different wording — a semantic match is
  required.
- **NOT** setting `blocked_by: []` without actively checking
  pending / in_progress tasks. **INSTEAD** run the cross-task
  dependency check (step 1b) substantively: "does either task
  change artifacts the other documents / uses?" Because: parallel
  tasks with implicit dependency produce rework (A changes
  framework while B documents it → B has to redo). Task 365 ↔ 366
  was the proven case (2026-04-09).
- **NOT** skipping triage and always creating a task. **INSTEAD**
  check the immediate-fix criteria. Because: backlog bloat from
  5-minute tasks that could be done directly.
- **NOT** accepting an empty "Not yet" block. **INSTEAD** ask the
  user actively "what is explicitly out of scope?". Because:
  scope drift across the task lifecycle, DR-10 violation.
- **NOT** `spec_ref=null` on implementing tasks. **INSTEAD**
  assign a spec, or hold the task until the spec exists. Because:
  the spec ↔ task link is missing — breaks consistency_check spec
  coverage (exception: REFERENCE_SPECS).
- **NOT** filling required fields with "see above" or "current
  conversation". **INSTEAD** make them self-contained. Because:
  tasks are picked up later without the session context.
