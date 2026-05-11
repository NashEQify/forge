---
name: task-status-update
description: >
  Atomic task-status change. The only allowed way to change
  `status` in task YAMLs. Writes YAML + backlog in one operation.
status: active
relevant_for: ["main-code-agent"]
invocation:
  primary: cross-cutting
  secondary: [user-facing, workflow-step]
disable-model-invocation: false
uses: []
---

# Skill: task-status-update

## Purpose

Atomic status changes for tasks. Ensures that `status`, `updated`,
the backlog entry, and (when applicable) the convoy are updated
consistently in one operation.

This skill is the ONLY allowed way to change `status` in task
YAMLs. Direct edits to that field are forbidden.

## Who runs it

Buddy (as orchestrator). Other agents report status changes to
Buddy, who runs this skill. Post-harness: NATS event handler.

## Input

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| task_id | int | yes | Task ID (NNN) |
| new_status | enum | yes | Target status: pending, in_progress, done, blocked, superseded, wontfix, absorbed |
| board_result | string | no | Board result: APPROVED, APPROVED_WITH_RISKS, REJECTED, PASS_WITH_RISKS, null. Written to YAML when given. |
| readiness | enum | no | Spec readiness: raw, reviewed, ready, impl_ready. Written to YAML when given. |
| reason | string | no | Free text; not stored — kept for traceability in chat. |
| workflow_phase | string (soft-validated) | no | Current workflow phase. Written to YAML when given. Values: workflow-specific (e.g. specify, prepare, execute, verify, close, done; solve: frame, refine, artifact, validate, execute, done). |
| spec_phase_update | object | no | Spec-phase update (see below). |

## Flow

### Step 1: read the YAML

Lookup order:
1. `docs/tasks/{task_id}.yaml` (top level — active tasks).
2. If absent: `docs/tasks/archive/{task_id}.yaml` (archived done
   tasks).

The task must exist in one of these paths — otherwise an error.
Remember the source path (used in step 5 for the auto-move
decision).

### Step 2: write the YAML

Writes to the source path discovered in step 1 (top level or
archive/). The move happens only in step 5.

Required fields (always):
- `status: {new_status}`
- `updated: {today, YYYY-MM-DD}`

Optional fields (only when set in the input):
- `board_result: {board_result}` — board review result.
- `readiness: {readiness}` — spec readiness level.
- `workflow_phase: {workflow_phase}` — current workflow phase.

**`workflow_phase` validation:** known values: frame, refine,
artifact, validate, specify, prepare, execute, verify, close,
done. Unknown value → emit a warning ("workflow_phase '{value}'
not in the known list — typo?"), still write (no hard block —
future workflows can define new phases).

Do not change other fields.

### Step 3: convoy update (conditional)

If `objective` is in the YAML and not null →
`workspaces/{objective}/convoy.md` is updated. Field absent →
skip.

### Step 4: spec_phase_update (conditional)

Only when `spec_phase_update` is set in the input. Writes to the
`spec_states` map of the task.

**Input format:**

```yaml
spec_phase_update:
  spec_name: harness-runtime-patterns
  current_phase: reviewing        # target phase
  increment_review: true          # review_passes += 1
  increment_fix: false            # fix_passes += 1
```

**Transition matrix (SoT: docs/tasks/328.md):**

- `raw -> reviewing` — board started. `increment_review=true`.
- `reviewing -> fixing` — board NEEDS-WORK. `increment_fix` not
  incremented.
- `fixing -> reviewing` — fix pass done, re-review.
  `increment_review=true`, `increment_fix=true`.
- `reviewing -> ready` — board PASS. `increment_review` not
  incremented again (already counted).

Invalid transitions (e.g. raw→ready, fixing→raw) are errors.
Buddy aborts and reports the error.

**Validation:**

1. `spec_name` must exist in `spec_states` OR is created (raw as
   the starting point).
2. `current_phase` must be in {raw, reviewing, fixing, ready}.
3. The transition must be valid (old_phase → new_phase per
   matrix).
4. On `increment_review=true`: `review_passes += 1`.
5. On `increment_fix=true`: `fix_passes += 1`.

### Step 5: auto-archive / reverse move

Lifecycle move mechanic between `docs/tasks/` (active) and
`docs/tasks/archive/` (history). Happens AFTER all YAML writes
(steps 2-4).

**Forward move (top level → archive/):** when `new_status == done`
AND the source path from step 1 was the top level → atomic move:

1. `git mv docs/tasks/{task_id}.yaml docs/tasks/archive/{task_id}.yaml`
2. `git mv docs/tasks/{task_id}.md   docs/tasks/archive/{task_id}.md`

If an error occurs after (1) but before (2): roll (1) back via
`git mv`, then raise the error.

**Reverse move (archive/ → top level):** when `new_status != done`
AND the source path from step 1 was archive/ (reopen pattern, e.g.
done → in_progress) → analogous move, both files back to the top
level.

**No-op cases:**
- `new_status == done` AND source is already in archive/ → no
  move (already there).
- `new_status != done` AND source is already at top level → no
  move.

**What gets moved:**
- `{task_id}.yaml`
- `{task_id}.md`

**What stays at the source path (do NOT take along):**
- Auxiliary files: `{task_id}-gates.md`,
  `{task_id}-delegation.md`, `{task_id}-test-plan.md`.
- These are gitignored per the docs-folder-taxonomy decision
  (internal operational state, not part of the historical work
  record).

**Other terminal statuses (`superseded`, `wontfix`, `absorbed`):**
trigger NO auto-move. The lifecycle semantic is different —
`superseded` often has cross-refs to the original
(`supersedes: <id>`, `superseded_by: <id>`) that would break on
move. Such tasks stay at the top level with their terminal status.

**Frozen zone:** `docs/tasks/archive/` is a consistency_check
frozen zone (WORM). Step 5 is the ONLY legitimate write operation
on that path. Subsequent calls of `task_status_update` on an
already-archived file keep writing to the archive path (step 2
writes at the source path) — that is conceptually a modify, but
legitimate within the skill contract. The frozen-zone check must
tolerate `task_status_update`-driven modifies in archive/ (see
consistency_check/REFERENCE.md §Frozen Zone Integrity Check).

### Step 6: output

```
Status update: [{task_id}] {title}
  status: {old} -> {new}
  updated: {today}
  board_result: {value} | unchanged
  readiness: {value} | unchanged
  workflow_phase: {value} | unchanged
  spec_states: {spec_name} {old_phase} -> {new_phase} | unchanged
  convoy: updated | n/a
  archive: forward | reverse | no-op
```

## Contract

### INPUT
- **Required:** task_id — task ID (NNN), the task must exist.
- **Required:** new_status — target status (pending, in_progress,
  done, blocked, superseded, wontfix, absorbed).
- **Optional:** board_result — board result (APPROVED,
  APPROVED_WITH_RISKS, REJECTED, PASS_WITH_RISKS, null).
- **Optional:** readiness — spec readiness (raw, reviewed,
  ready, impl_ready).
- **Optional:** reason — free text for traceability.
- **Optional:** workflow_phase — current workflow phase.
- **Optional:** spec_phase_update — spec-phase transition
  (spec_name, current_phase, increment_review, increment_fix).
- **Context:** `docs/tasks/{task_id}.yaml` — read in step 1.

### OUTPUT
**DELIVERS:**
- Updated task YAML: status + updated (always) + board_result +
  readiness + workflow_phase + spec_states (optional).
- Convoy update when `objective` is present.
- Status-update output block (old → new for every changed field).

**DOES NOT DELIVER:**
- No new tasks — that is `task_creation`.
- No changes to title, area, prio, spec_ref — only
  status-relevant fields.
- No backlog writes — `plan_engine` computes overviews.

**ENABLES:**
- Commit-guard TASK-SYNC: atomic status updates instead of
  direct YAML edits.
- Plan engine: accurate task statuses for critical path and
  milestone calculation.
- Save workflow: status consistency as part of the save process.

### DONE
- YAML written: status + updated (+ optional fields when set:
  board_result, readiness, workflow_phase, spec_states).
- Convoy updated when `objective` is present.
- Auto-archive move executed (forward on done from top level,
  reverse on != done from archive/) or no-op.
- Status-update output block emitted.

### FAIL
- **Retry:** not foreseen — atomic operation.
- **Escalate:** task does not exist → report the error. Invalid
  spec-phase transition → abort and report the error.
- **Abort:** invalid status value or invalid transition →
  immediate abort with error message.

## Boundary

- **Limited field scope.** Title, area, prio, spec_ref, etc. are
  still edited directly. This skill writes: status, updated
  (always) + board_result, readiness, workflow_phase,
  spec_states (optional, when given).
- **No replacement for task_creation.** New tasks are still
  created via `task_creation`. This skill takes over from the
  first status mutation onwards.

## Anti-patterns

- **NOT** edit status directly in the YAML. INSTEAD call this
  skill. Because: atomic updates + backlog consistency.
- **NOT** commit without an `updated` field. INSTEAD the skill
  sets both atomically. Because: drift between status and the
  updated timestamp.
- **NOT** create new tasks via a status update (status: pending
  on a non-existent task). INSTEAD the `task_creation` skill.
  Because: new tasks need duplicate check + triage.
- **NOT** set `workflow_phase` without updating the state-file
  frontmatter (when the state file exists). INSTEAD do both
  atomically: `task_status_update workflow_phase=X` +
  state-file frontmatter `phase: X` in the same step. Because:
  drift between task YAML and state file produces a contradictory
  state on boot resume.
- **NOT** edit files in `docs/tasks/archive/` directly or move
  them via `git mv` yourself. INSTEAD call this skill — step 5
  is the only legitimate move operation. Because: frozen zone
  (WORM); consistency_check reports hand edits as INCIDENT.
- **NOT** order workflow steps so that `phase-done`
  (workflow_phase=done) runs AFTER `task-status-done`
  (status=done) when both work on the same task. INSTEAD
  `phase-done` first, `task-status-done` as the very last
  content step. Because: after status=done the YAML is in
  archive/, and subsequent writes look like a frozen-zone
  modify — see step 5 §Frozen zone.

## Enforcement

The following points point at this skill as the only allowed way:

- `skills/task_creation/SKILL.md` — creating new tasks.
- `workflows/runbooks/save/WORKFLOW.md` — step 2.5.
- `workflows/runbooks/build/WORKFLOW.md` — `workflow_phase` at
  every phase boundary.
- `workflows/runbooks/fix/WORKFLOW.md` — `workflow_phase` at every
  phase boundary.
- `workflows/runbooks/research/WORKFLOW.md` — `workflow_phase` at
  every phase boundary.
- `workflows/runbooks/solve/WORKFLOW.md` — `workflow_phase` at
  every phase boundary.
- `workflows/runbooks/review/WORKFLOW.md` — `workflow_phase` at
  every phase boundary.
- `workflows/runbooks/docs-rewrite/WORKFLOW.md` — close phase
  step 1 (TASK-UPDATE, when a task exists).
- `CLAUDE.md` — commit-guard TASK-SYNC.
