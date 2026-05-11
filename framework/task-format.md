# Task Format

Purpose: unified format for all tasks in BuddyAI.
Applies to: all files in `docs/tasks/`.
SoT: this file.

## File structure

Each task consists of two files:

- `NNN.yaml` � metadata, machine-readable, SoT for status/assignment/routing
- `NNN.md` � prose + workflow checklist, for execution context

NNN is a three-digit number with leading zeros (001, 042, 100+).
Next free ID: look up the highest existing ID in `docs/tasks/`.

## YAML format

Required fields:

  id: [int]
  title: [string]              # max ~60 chars
  status: [enum]               # pending | in_progress | done | blocked | superseded | wontfix | absorbed
  milestone: [string]          # reference to docs/plan.yaml key.
                               # Determines execution order and dashboard grouping.
                               # MUST be a key in plan.yaml milestones.
  blocked_by: [int[]]          # empty: []
  created: [YYYY-MM-DD]
  updated: [YYYY-MM-DD]        # update on every status change

Optional fields:

  effort: [enum]               # S | M | L | XL � t-shirt size for critical-path weighting.
                               # Required for pending/in_progress tasks.
                               # S=1, M=3, L=8, XL=20 (engine weights).
                               # XL tasks: plan_engine warns (DECOMPOSE � split into subtasks).
  area: [string]               # thematic area (optional, for dashboard filters).
  assignee: [string]           # buddy | main-code-agent | human | null
  spec_ref: [string|null]      # path to design spec (e.g. "personal-chat-backend.md").
  board_result: [string|null]  # pass | pass_with_risks | needs_work | null
  readiness: [enum|null]       # raw | specced | reviewed | implementing | done
  summary: [string|null]       # one-liner: current state for boot output and dashboard.
  intent_chain: [object|list]  # context for agents/humans (domain, objective, action).
  sub_tasks: [int[]]           # empty: []
  parent_task: [int|null]      # subtask hierarchy (this task has parent NNN).
                               # Scope: docs/tasks/NNN.yaml ONLY. NOT to be used
                               # as state-file frontmatter — there `task_ref:` is
                               # the canonical form (see
                               # workflows/workflow-template.md §Frontmatter
                               # schema). workflow_engine `_discover_state_file`
                               # matches `task_ref` primarily; `parent_task` in
                               # state files is only a legacy fallback.
  blocked_by_external: [list]  # cross-project dependencies. Engine treats as NOT ready.
  spec_version: [string]       # start value v1, increment on semantic spec changes.
  workflow_template: [string]  # templates from workflows/templates/
  test_plan_spec_ref: [string] # which spec_version the test plan covers.

Status enum:
- pending: not started yet
- in_progress: actively being worked on
- done: completed, acceptance criteria met
- blocked: waiting for external input
- superseded: replaced by another task/spec
- wontfix: intentionally not implemented
- absorbed: folded into another task

Terminal statuses (task is closed): done, superseded, wontfix, absorbed.
plan_engine DEAD_DEP warns if blocked_by points at terminal status other than done.

**Auto-archive on `done`:** when `task_status_update` sets a task to
`status: done`, `<id>.yaml` + `<id>.md` are automatically moved to
`docs/tasks/archive/`. Other terminal statuses (`superseded`, `wontfix`,
`absorbed`) do NOT trigger auto-move � they often have cross-refs
(e.g. `superseded_by: <id>`) that would break on move. See
`skills/task_status_update/SKILL.md` step 5.

Readiness levels (dashboard):
- raw: idea, no spec
- specced: spec written, no board
- reviewed: board-reviewed
- implementing: implementation in progress
- done: completed

## MD format

  # Task NNN: [Title]

  [prose: context, background, why this task exists]

  ## Workflow
  - [x] Step 1: [description] � done YYYY-MM-DD
  - [ ] Step 2: [description] � in_progress, Assignee: [name]
  - [ ] Step 3: [description]

  ## Blockers
  - [description, since when]

  ## Not yet (scope boundary)
  - [what is explicitly out of scope]

Required rules:
1. `## Workflow` is required when the task has more than one step.
2. `## Not yet` is required � empty block is invalid (DR-10).
3. Workflow steps are always checkboxes, never prose.
4. Last `in_progress` step = entry point for the next session (NDI principle).
5. `## Blockers` only when a blocker currently exists.

## Workflow templates

When `workflow_template` is set, Buddy instantiates the `## Workflow`
section from `workflows/templates/<n>.yaml` when creating the task.

Available templates: `decision`, `research`.
(The former `standard-build` template is retired; build now goes via
`workflows/runbooks/build/WORKFLOW.md`.)
If no template is set, Buddy writes the workflow manually.

## Lifecycle and archiving

**Archive location:** `docs/tasks/archive/NNN.yaml` + `docs/tasks/archive/NNN.md`.

**Status `tracked`:** archive/ is committed in the OSS repo (historical
work record). Decision: 2026-05-03, see
`docs/solve/2026-05-03-doc-folder-taxonomy.md`.

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

## Subtask creation by main-code-agent

main-code-agent can create subtasks:
1. Create new `NNN.yaml` + `NNN.md` (next free ID)
2. Set `parent_task` to the parent task ID
3. Extend `sub_tasks` in the parent YAML
4. Add subtask to objective `convoy.md`
5. Set `ephemeral: true` if no permanent artifact is created

## Example

docs/tasks/NNN.yaml:

  id: NNN
  title: Add session-handoff persistence
  status: in_progress
  objective: cross-session-continuity
  assignee: main-code-agent
  ephemeral: false
  workflow_template: build
  intent_chain:
    domain: framework/persistence
    objective: cross-session-continuity
    action: Persist session handoff so the next session can resume.
  context_manifest:
    required:
      - context/framework/persistence.md
    available:
      - docs/specs/session-handoff.md
    skills: [task_status_update, knowledge_processor]
  created: 2026-05-01
  updated: 2026-05-09
  parent_task: null
  sub_tasks: []
  blocked_by: []

docs/tasks/NNN.md:

  # Add session-handoff persistence

  Sessions currently restart from zero. Add a handoff file written on
  `save` and read at boot.

  ## Workflow
  - [x] Step 1: Spec the handoff format
  - [x] Step 2: Implement save-side write
  - [ ] Step 3: Implement boot-side read — in_progress
  - [ ] Step 4: Smoke test the cross-session round-trip

  ## Blockers
  - none

  ## Not yet
  - Multi-machine sync (separate task)

## Convoy update requirement

On EVERY task status change: if the task is mapped to an objective
(`objective` in YAML is not null), `workspaces/<objective>/convoy.md`
MUST be updated.

This applies to:
- status transitions (pending -> in_progress, in_progress -> done, etc.)
- new task assigned to an objective
- subtask creation (new row in convoy.md tasks table)

Owner: whoever changes the status (Buddy, main-code-agent via
`task_status_update` skill).
Post-harness: NATS event `task.status.changed` triggers automatic convoy updates.

No separate skill � convoy update is a required side effect of every
status mutation.
