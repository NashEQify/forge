# Task status update — graph closure, archive and persist gate

Step-loaded unit of `skills/task_status_update/SKILL.md`. Read it after Step 2 (and Step 3, when it applies) has
written the task YAML, on every status change: Step 4 closes the cross-task graph on terminal status and checks the
critical path on every change, Step 5 moves the task to or from the archive, Step 5.5 runs the persist gate on
`done`. Step numbers are skill-wide: Input, Steps 1–3, Step 6 and the anti-patterns in `SKILL.md`, Steps 4–5.5 in
`closure.md`.

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
`consistency_check/REFERENCE.md` §Frozen-zone integrity check).

### Step 5.5: persist gate (when new_status == done)

On flip to `done` the agent MUST:

1. Patch `context/overview.md`.
2. Add `context/history/<entry>.md` close-out.
2a. Remove the task from the handoff (running, next, held-back entries) where this
   actor owns the handoff; otherwise name the removal in the return for its owner.
   The handoff keeps no closed work (`workflows/runbooks/save/WORKFLOW.md` §2).
3. If `workflow_engine.py --find --task {task_id}` shows an active
   workflow not yet at `commit-deploy` → drive it (`--complete
   commit-deploy`). No auto-abort.
4. **Doc-currency backstop (when the project declares an architecture
   reading-map per its `intent.md`):** run `consistency_check` check-12
   (doc-currency) over the project's doc-set + reading-map. On a finding
   (a banner naming a task as pending while its YAML is terminal; a
   `last_updated` a banner date has overtaken; a reading-map SoT pointer
   that no longer resolves or a doc-of-record the map omits), reconcile
   the specific flagged item in this close — targeted, non-blocking. This
   is the **universal** doc-currency point: every route (incl. DIRECT /
   SUB-BUILD / fix) reaches a terminal status through this skill, so
   neither a stale banner nor an un-indexed born-here spec can survive its
   own close — the rot a diff-scoped Verify step structurally cannot see.
   Generic: the map + path live in the consumer's `intent.md`; this names
   the duty, not a path. No reading-map declared → skip.
