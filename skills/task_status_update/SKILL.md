---
name: task-status-update
description: >
  Coherent task-status change — the ONLY allowed way to change a task's
  `status` (it also closes the cross-task graph + plan refs on terminal
  status). Use whenever a task's status must change; always route status
  changes here instead of editing the YAML field directly. NOT for content
  edits to an OPEN task's body (manual) — though the terminal-status sweep
  of `blocked_by` / cross-refs on OTHER tasks IS in scope.
status: active
relevant_for: ["main-code-agent"]
invocation:
  primary: cross-cutting
  secondary: [user-facing, workflow-step]
disable-model-invocation: false
uses: []
---

# Skill: task-status-update

The only allowed way to change `status` in a task YAML. Direct
edits to that field are forbidden. On terminal status (done,
superseded, wontfix, absorbed) it also closes the task-graph
(cross-task `blocked_by`) and aligns `docs/plan.yaml` inline refs —
all in one invocation, so the graph never sees a half-closed
terminal.

## Input

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| task_id | int | yes | Task ID (NNN). |
| new_status | enum | yes | pending, in_progress, done, blocked, superseded, wontfix, absorbed. |
| board_result | string | no | APPROVED, APPROVED_WITH_RISKS, REJECTED, PASS_WITH_RISKS, null. |
| readiness | enum | no | raw, specced, reviewed, ready, implementing, done. |
| reason | string | no | Free text for traceability; not stored. |
| workflow_phase | string | no | Current workflow phase. Soft-validated. |
| spec_phase_update | object | no | Spec-phase transition (see Step 3). |
| closure_ref | int | conditional | Successor / absorbing task ID. Required when `new_status` ∈ {superseded, absorbed}. |

**Vocab SoT:** the `new_status` and `readiness` value sets mirror
`framework/task-schema.yaml` (the authoritative vocab). When the schema
changes a value set, update this table in the same change — there is no
automated guard (the same hand-sync discipline as `task-format.md`).

## Flow

### Step 1: read YAML

Lookup `docs/tasks/{task_id}.yaml`, else
`docs/tasks/archive/{task_id}.yaml`. Missing → error. Remember the
source path (Step 5 uses it).

### Step 2: write YAML

Write to the source path. Always:
- `status: {new_status}`
- `updated: {today YYYY-MM-DD}`

Optional fields when given: `board_result`, `readiness`,
`workflow_phase`. Don't touch others. Unknown `workflow_phase`
value → WARN, still write (new workflows define new phases).

Validate the touched task against `framework/task-schema.yaml` via
`plan_engine --validate <id>`; on schema FAIL, fix before
reporting.

### Step 3: spec_phase_update (conditional)

Only when `spec_phase_update` is in the input. Writes to the task's
`spec_states` map. Valid transitions (each may fire a counter):

- `raw → reviewing` (`increment_review=true`)
- `reviewing → fixing`
- `fixing → reviewing` (`increment_review=true`,
  `increment_fix=true`)
- `reviewing → ready`

`spec_name` is created at `raw` if absent. Invalid transition or
unknown `current_phase` → abort.

### Step 4: cross-task graph closure + critical-path blast radius

Two parts: **(A)** graph closure on terminal status (MUST), **(B)**
critical-path blast-radius visibility on every status change.

#### (A) Graph closure — MUST on terminal status

Lifecycle-symmetric with `task_creation` Step 1b — that step
**builds** the `blocked_by` graph, this step **closes** it.

Runs BEFORE Step 5 archive so the focal task stays at top level
until the graph is consistent. On sweep failure, the focal task is
re-readable; the archive move only happens after the sweep returns.

**`closure_ref` existence guard (superseded / absorbed):** verify
`closure_ref` resolves to an existing task whose status is NOT in
`terminal_status`. Fail → abort with `closure_ref={id} does not
point at an open task — ask the user, then re-run`.

**Focal-task closure write:**

- `superseded` → focal: `superseded_by: {closure_ref}`; successor
  (`{closure_ref}`): `supersedes: {task_id}`.
- `absorbed` → focal: `absorbed_by: {closure_ref}` (one-way —
  no `absorbs:` on the absorbing task; its body documents what was
  folded in).
- `done` / `wontfix` → no closure-field write.

Missing `closure_ref` on superseded / absorbed → abort with
`closure_ref required for status={status} — ask the user, then
re-run`.

**`blocked_by` sweep on open tasks** (open = status NOT in
`terminal_status`):

- `done` → **keep** the entry (historical record; `plan_engine`
  evaluates via status).
- `superseded` / `absorbed` → **replace** `{task_id}` with
  `{closure_ref}`.
- `wontfix` → **remove** `{task_id}`; emit `wontfix on {task_id}
  orphans N blocked-by entries — review each`.

**`docs/plan.yaml` inline refs:** run
`grep -nE 'Task {task_id}\b' docs/plan.yaml` (`\b` portable across
ugrep / GNU / BSD — the project shell's `grep` is a ugrep wrapper).
Inspect each hit in `operational_intent.goal`,
`operational_intent.done`, each milestone's `desc`. Rewrite stale
descs substantively. No hit → skip.

After the sweep: `plan_engine --validate` (whole tree, no `<id>`
arg) must PASS — dangling `blocked_by` is a graph error.

#### (B) Critical-path blast radius — every status change

A status change on a task that gates the critical path shifts what
`plan_engine` computes downstream. On `in_progress` / `blocked` /
terminal of a path-gating task, run `plan_engine.py --after
{task_id}` and read what it un/blocks; a `blocked` on a path-gating
task surfaces the stalled downstream set rather than passing
silently. Non-terminal transitions change no `blocked_by` edges —
this is visibility (path-position seen now), not a YAML write, and
not deferred to `save`.

### Step 5: auto-archive / reverse move

Lifecycle move between `docs/tasks/` (active) and
`docs/tasks/archive/` (history, WORM frozen zone). Move pair (yaml
+ md) via two `git mv`; if the second fails, roll back the first.

- `new_status == done` from top level → forward move to archive/.
- `new_status != done` from archive/ → reverse move back.
- Otherwise → no-op.

**Terminal-close integrity guard (atomicity, forward move only).** The
split-failure mode: writing `status` at the OLD path and THEN `git mv`
stages the rename from the *original* blob — the status edit is stranded as
an unstaged working-tree modification (`RM` in `git status`) and never
reaches the commit, so the task is archived at a non-terminal status
(silent corruption; the archive is WORM, so it then sits wrong
indefinitely). A working-tree read does NOT catch this — the working file
shows the new status while the index still holds the old. Guard: after the
forward move, `git add` the archived YAML, then assert the **staged** blob
carries the terminal status —
`git show :docs/tasks/archive/{id}.yaml | grep -q '^status: {new_status}'`
(the index is the layer the commit reads). Mismatch → re-write
`status: {new_status}` + `git add` + re-verify; emit a LOUD warning. The
close is thus self-correcting at the index level, so a split can never
reach a commit.

Aux files (`{id}-gates.md`, `{id}-delegation.md`,
`{id}-test-plan.md`) stay at the source path — gitignored,
operational state.

Other terminal statuses (`superseded`, `wontfix`, `absorbed`) do
NOT auto-move — their cross-refs would break under the move.

Step 5 is the only legitimate write operation in
`docs/tasks/archive/`; subsequent calls on already-archived files
keep writing there per contract (see
`consistency_check/REFERENCE.md` §Frozen Zone).

### Step 5.5: persist gate (when new_status == done)

On flip to `done` the agent MUST:

1. Patch `context/overview.md`.
2. Add `context/history/<entry>.md` close-out.
3. If `workflow_engine.py --find --task {task_id}` shows an active
   workflow not yet at `commit-deploy` → drive it (`--complete
   commit-deploy`). No auto-abort.

### Step 6: output

```
Status update: [{task_id}] {title}
  status: {old} -> {new}
  updated: {today}
  board_result | readiness | workflow_phase | spec_states: ... | unchanged
  cross-task sweep: N blocked_by + M closure entries | n/a (non-terminal)
  plan.yaml sweep: K descs rewritten | n/a
  critical-path: on-path | off-path | gates {ids} via --after | n/a
  archive: forward | reverse | no-op
```

## Anti-patterns

- **NOT** edit `status` directly in the YAML — call this skill.
  Reason: cross-task graph + plan.yaml refs must stay consistent in
  the same operation.
- **NOT** create new tasks via this skill (`status: pending` on a
  non-existent task) — `task_creation`. Reason: new tasks need
  duplicate check + triage.
- **NOT** edit `docs/tasks/archive/` directly or `git mv` files
  yourself — Step 5 is the only legitimate write. Reason: frozen
  zone (WORM); `consistency_check` reports hand edits as INCIDENT.
- **NOT** sequence `workflow_phase=done` AFTER `status=done` on the
  same task — phase first, status last. Reason: `status=done`
  archives the YAML; subsequent writes look like frozen-zone
  modifies.
- **NOT** skip the cross-task sweep on superseded/absorbed because
  *"there are probably no dependents"* — run the scan; cold-graph
  assumptions break silently.
- **NOT** change a task's scope or dependencies via a raw body edit
  and skip the graph. Open-body content edits go through neither
  task skill; if a scope edit adds or drops a real dependency, run
  the `task_creation` §1b-style pairwise check by hand plus
  `plan_engine --validate`. The skills fire on create + status —
  content-edit reconciliation is manual.
