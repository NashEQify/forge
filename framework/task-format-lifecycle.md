# Task Format — terminal status and archiving

Step-loaded unit of `framework/task-format.md`. Read it when a task reaches a terminal status, is archived or
reopened, and when a cross-reference to a closed or archived task is written or resolved.

### Cross-reference fields (terminal-status closure)

Optional YAML fields written by `task_status_update` Step 4 when a
task reaches a terminal status. All three are `int_or_null`; declared
in `framework/task-schema.yaml`.

| Field | Status that writes it | Semantics |
|---|---|---|
| `superseded_by: <id>` | `superseded` | This task was replaced by `<id>`. Dependents' `blocked_by` redirects from this task to `<id>`. |
| `supersedes: <id>` | written on the **successor** when the predecessor flips to `superseded` | The successor explicitly carries forward what `<id>` was tracking. |
| `absorbed_by: <id>` | `absorbed` | This task was folded into `<id>`. Dependents' `blocked_by` redirects from this task to `<id>`. |

Examples: task `311` carries `superseded_by: 306`; task `374` carries
`absorbed_by: 372`.

## Lifecycle and archiving

**Archive location:** `docs/tasks/archive/<NNN>.yaml` + `docs/tasks/archive/<NNN>.md`.

**Status `tracked`:** archive/ is committed in the OSS repo as the
project's historical work record.

**Frozen zone (WORM):** consistency_check reports Modify/Rename/Delete in
archive/ as INCIDENT � except task_status_update-driven moves and modifies
(see `skills/consistency_check/REFERENCE.md` �Frozen Zone Integrity Check).

**Auto-move on `status: done`:**
- Trigger: every `task_status_update` call setting `new_status=done`
- Move covers only `<id>.yaml` + `<id>.md` � auxiliary files
  (`<id>-gates.md`, `<id>-delegation.md`, `<id>-test-plan.md`) stay at top level
  (gitignored per docs-folder-taxonomy decision)
- Mechanic: step 5 in `skills/task_status_update/SKILL.md`

**Cross-refs to done tasks:** refs to `docs/tasks/<id>.{yaml,md}`
automatically resolve to `docs/tasks/archive/<id>.{yaml,md}` as fallback
(consistency_check task-ref resolver). Cross-refs do NOT need rewriting
when a task is archived.

**Reverse move (reopen):** `task_status_update` with `new_status != done`
on an archived task moves files back to top level. Edge case for reopened
workflows.

**Ephemeral tasks (wisps):** `ephemeral: true` used to be a separate
pre-harness mechanism for "archive after done". With auto-move this is
obsolete � all done tasks are archived. `ephemeral: true` remains a marker
for "subtask without a permanent artifact" (parent task gets a summary
line in prose).

Post-harness: APScheduler cleanup job can add retention logic
(e.g. archive/ -> cold storage after N months).
