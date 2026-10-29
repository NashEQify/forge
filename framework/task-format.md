# Task Format

Purpose: unified format for all tasks.
Applies to: all files in `docs/tasks/` (forge_dev + every consumer repo).
SoT (human): this file — prose, semantics, and rationale.
SoT (machine): `framework/task-schema.yaml` — the single authoritative
field set (names, required-set, value vocab) the validator parses. The
schema wins on which fields exist; this prose documents their semantics
and must be hand-synced when a field is blessed (there is no automated
guard — keep both edits in the same change).
Validation: `plan_engine --validate` (post-hoc, SoT) + the task skills
(`task_creation`, `task_status_update`) validate the touched task
inline against the same schema.

## File structure

Each task consists of two files:

- `NNN.yaml` � metadata, machine-readable, SoT for status/assignment/routing
- `NNN.md` � prose + workflow checklist, for execution context

NNN (the file basename) is **pure-numeric** (`^[0-9]+$`). Zero-padding
is a per-repo cosmetic convention, NOT validated (forge_dev uses `327`,
some repos use `020` — both valid). Gate/auxiliary files are
`NNN-<suffix>.{md,yaml}` (non-pure-numeric basename) and are never
tasks — every reader (`show_open_tasks`, `plan_engine`, workflow-engine
state files) keys on the pure-numeric rule, so gate-file naming never
collides with task discovery.
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
                               # REQUIRED on open (non-terminal) tasks.
                               # Strict vocab: exactly S|M|L|XL (no S-M, no aliases).
                               # S=1, M=3, L=8, XL=20 (engine weights).
                               # XL tasks: plan_engine warns (DECOMPOSE � split into subtasks).
  priority: [enum]             # high | medium | low � REQUIRED on open
                               # (non-terminal) tasks. Write-strict (only the
                               # 3 values). Tolerant READ-aliases (mid|med|
                               # normal->medium, hi->high, lo->low) live in
                               # exactly one place (task-schema.yaml), never
                               # duplicated in a reader. Terminal/archived
                               # tasks: not required (no history rewrite).
  area: [string]               # thematic area (optional, for dashboard filters).
  assignee: [string]           # buddy | main-code-agent | human | null
  spec_ref: [string|null]      # path to design spec (e.g. "personal-chat-backend.md").
  board_result: [string|null]  # pass | pass_with_risks | needs_work | null
  readiness: [enum|null]       # raw | specced | reviewed | ready | implementing | done
  summary: [string|null]       # one-liner: current state for boot output and dashboard.
  intent_chain: [object|list]  # context for agents/humans (domain, objective, action).
  sub_tasks: [int[]]           # empty: []
  parent_task: [int|null]      # subtask hierarchy (this task has parent NNN).
                               # Scope: docs/tasks/<NNN>.yaml ONLY. NOT to be used
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

Task-content fields (presence-only, not vocab-enforced — the generic
authoring vocabulary; `task-schema.yaml` is the authoritative set):

  acceptance_criteria: [list]  # ACs (also fine as a `## Acceptance` block in the .md).
  out_of_scope: [list]         # explicit scope boundary (mirrors the `## Not yet` block).
  objective: [string|null]     # top-level objective (cf. intent_chain.objective).
  notes: [list]                # free-form authoring notes / provenance.
  discoveries: [list]          # findings surfaced during the work.
  status_notes: [string|null]  # short status annotation.
  blocks: [int[]]              # task IDs this task blocks (inverse of blocked_by).
  context_manifest: [object]   # required/available context + skills (see task_creation).
  ephemeral: [bool]            # subtask without a permanent artifact (see Lifecycle below).

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
`skills/task_status_update/closure.md` step 5.

### Cross-reference fields (terminal-status closure)

When a task reaches a terminal status: read and follow `framework/task-format-lifecycle.md` (§Cross-reference fields:
`superseded_by`, `supersedes`, `absorbed_by`).

### Cross-reference MD blocks

| Block | Written by | Purpose |
|---|---|---|
| `## Dependency: blocked_by N` | `task_creation` Step 1b | Free-text justification for the `blocked_by` entry — why this dependency, which direction, what order. |

The MD block is rationale, the YAML field is the graph SoT. `plan_engine`
reads only the YAML.

Readiness levels (dashboard):
- raw: idea, no spec
- specced: spec written, no board
- reviewed: board-reviewed
- ready: reviewed + queued for implementation
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
2. `## Not yet` is required — empty block is invalid (scope must be explicitly bounded).
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

When a task is set to `done`, archived or reopened, and when a cross-reference to an archived task is written or
resolved: read and follow `framework/task-format-lifecycle.md` (§Lifecycle and archiving: archive location, frozen
zone, auto-move, cross-refs, reverse move, ephemeral tasks).

## Subtask creation by main-code-agent

main-code-agent can create subtasks:
1. Create new `NNN.yaml` + `NNN.md` (next free ID)
2. Set `parent_task` to the parent task ID
3. Extend `sub_tasks` in the parent YAML
4. Set `ephemeral: true` if no permanent artifact is created

## Example

docs/tasks/<NNN>.yaml:

  id: NNN
  title: Add session-handoff persistence
  status: in_progress
  milestone: cross-session-continuity
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
      - docs/specs/<name>.md
    skills: [task_status_update, knowledge_processor]
  created: YYYY-MM-DD
  updated: YYYY-MM-DD
  parent_task: null
  sub_tasks: []
  blocked_by: []

docs/tasks/<NNN>.md:

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

## Task-graph reconciliation

The `blocked_by` graph and `docs/plan.yaml` refs are kept consistent
at mutation time by the two task skills, not batched later:
`task_creation` **builds** the graph (§1b pairwise dependency check +
§1.7 critical-path placement); `task_status_update` **closes** it on
terminal status (§4 cross-task + plan.yaml sweep) and surfaces
critical-path blast radius on every status change. `plan_engine
--validate` is the integrity gate after either.
