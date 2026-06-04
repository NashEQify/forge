---
name: task-creation
description: >
  Create a new, self-contained task (acceptance criteria + duplicate /
  dependency check). Use when actionable work needs tracking as a new
  task — at intake, as a fix-task, or from spec decomposition;
  reach for it instead of free-flow-adding a task by hand. NOT for editing
  an existing task (use task_status_update) or a fix you can just do now.
status: active
invocation:
  primary: user-facing
  secondary: [workflow-step]
disable-model-invocation: false
uses: []
---

# Skill: task-creation

Structured, high-quality task creation. Self-contained tasks with
clear ACs, a derived `intent_chain`, and no duplicates. Task quality
sets the upper bound on downstream work quality.

Triggers: intake gate ACTIONABLE, root-cause-fix step 4, user
"create a task for X", spec decomposition.

## Input

- **problem:** what is broken / missing / wanted? (raw)
- **context** (optional): defect info, incident, conversation.
- **source** (optional): `intake` | `root-cause-fix` | `user` |
  `decomposition`.

## The 5 steps

### 1. Duplicate + dependency check (MUST)

Single scan over `docs/tasks/`, two dimensions:

**(a) Duplicate check** — same goal (semantic, not title match),
subset of existing, or makes existing obsolete?
- Duplicate → no new task, reference the existing one.
- Subset → fold the problem into the existing task as an AC /
  comment.
- Obsolescence-maker → supersede the existing one (via
  `task_status_update`), the new task is the successor.
- No duplicate → continue.

**(b) Cross-task dependency check (required, not optional)** — for
every pending / in_progress task, is there a logical dependency in
**either** direction?

- New task needs result of existing → new task gets
  `blocked_by: [NNN]`.
- Existing task needs result of new → **edit the existing YAML**
  and add the new task ID to its `blocked_by`. Mandatory.

Yes on any → record; document rationale in the MD body as a
`## Dependency: blocked_by N` block (why, direction, order). No on
all → `blocked_by: []`.

Trigger questions + worked example: `REFERENCE.md`.

**Lifecycle symmetry:** this step **builds** the `blocked_by`
graph; closure on terminal status (replace on superseded/absorbed,
remove on wontfix, keep on done) is `task_status_update` Step 4.

### 1.5. Value floor (MUST)

What operational impact does NOT doing this have?

- **Nothing breaks** — no contract violation, no one blocked, no
  behaviour change → `accept`, no task. Optional record where
  natural (forge-feed for lessons, ADR for decision-drivers).
- **Cosmetic only** — SoT-link tidiness, placeholder fills, "nice
  to have" docs → `accept`.
- **Real impact** — defect, blocker, contract gap, user-visible
  bug, measurable downstream cost → continue to step 2.

Applies regardless of trigger. Symmetric with `code_review_board`
LOW-hard-floor.

**User-override:** if trigger=user AND the floor says `accept`,
surface the outcome before proceeding —
*"Value-floor says accept (Grund X) — really file?"*. Explicit
yes overrides; otherwise: no task.

### 1.6. Claim verification (MUST when trigger formulations present)

If the task body uses any of: `supersedes`, `reuses existing`,
`already implemented`, `wraps existing`, `delivered in Task`,
`existing-code verifications confirm` — each claim MUST be paired
with a `C-VERIFY` block (claim text + verbatim `grep -rn` command
+ verbatim output + `CONFIRMED|FALSIFIED` disposition). The canonical
trigger set — incl. the spec-citation and cross-producer
dedup/collision/reconcile classes — lives in
`agents/code-architect-lens.md` §Claim-Verifications; a task that
locks a reconcile/dedup premise triggers the cross-producer class
(verify producer key-assignment co-location, not mere existence).
`[DISCIPLINE]` — this is an authoring rule applied by the agent, NOT
a hook. (Historical note: a `BRIEF-CLAIMS` PreToolUse hook was
described here but never existed as a runnable artifact, and
PreToolUse hooks were purged in ADR-004; per ADR-005 enforcement-
honesty, no doc claims a `BLOCK` for a non-existent mechanism. The
real safeguard is this C-VERIFY discipline + the optional
pre-commit WARN anti-phantom check.)

### 1.7. Critical-path placement (MUST)

`milestone` + `priority` encode **path-position**, not topic-fit.
Before writing (§4), read `plan_engine.py --boot` (critical path +
milestone gates + next-actions) and place the task against the path,
not by subject-matter resemblance:

- **Milestone by dependency, not topic.** Pick the `milestone` where
  the task's dependencies actually sit, not the topically-nearest
  one. `--critical-path` shows where the target runs and which
  milestone gates it.
- **On-path vs off-path.** If the task is NOT on the critical path to
  the target, say so in the MD body. Off-path work defaults
  `priority` **away from `high`** unless a *named active consumer*
  demands it (same L→G→C floor as §1.5, applied to placement, not
  filing).
- **Priority semantics.** Name which the `priority:` field means:
  critical-path-priority (gates the path) vs user-value-priority
  (valuable but off-path). A high-user-value off-path task is not
  `priority: high`.
- **Forward blast radius.** When the new task blocks or unblocks
  existing work, `plan_engine.py --after <id>` shows what unblocks
  downstream — set `blocked_by` edges deliberately from that, not
  pairwise guesses alone.

The result feeds §4: `milestone` + `priority` justified against
path-position, not topic.

### 2. Triage (MUST)

Fix immediately or create a task? Criteria: effort, reversibility,
dependencies, context, interruption. All "fix immediately" criteria
met → light plan, no task; **steps 3-5 are skipped**. Otherwise →
continue. Triage table: `REFERENCE.md`.

### 3. Derive the intent_chain (MUST)

Derive from the active context. Required on delegation; optional in
direct user conversation. Format + rules (build + life variants):
`framework/intent-tree.md` §intent_chain.

### 4. Write the task file (MUST)

Format: `docs/tasks/NNN.yaml` + `NNN.md`. Schema SoT:
`framework/task-schema.yaml`. Body SoT: `framework/task-format.md`.

**ID selection (MUST):** `NNN` = highest numeric basename across **both**
`docs/tasks/*.yaml` AND `docs/tasks/archive/*.yaml`, + 1. Archived IDs are
retired, never recycled — scanning only the top-level silently collides
with an archived task and breaks the WORM archive move at close. §5
`--validate` flags a live↔archive collision (`ID_REUSED_FROM_ARCHIVE`)
as the safety net.

YAML field names + value vocab live in the schema, not here. New
tasks are open → MUST carry `effort` (`S|M|L|XL`) and `priority`
(`high|medium|low`) alongside the always-required fields (`id`,
`title`, `status`, `milestone`, `blocked_by`, `created`, `updated`).

**`milestone`** MUST be a key from `docs/plan.yaml` milestones.
Pick the milestone that fits the task **inhaltlich** (read the
content, don't default to the last-used one). If no existing
milestone fits, **surface to the user before continuing**:
*"No existing milestone fits — propose a new one (key + title +
desc) or pick the closest existing one?"* (See `docs/plan.yaml`
`milestones:` for the schema — new entries follow the existing
`key + title + desc + phases + requires` shape.) Plan.yaml
milestone-writes belong outside this skill; if the user approves,
Buddy edits `docs/plan.yaml` directly before this skill resumes
at step 5.

**`spec_ref`** required when the task implements an existing spec
(`null` only when no spec exists).

**Dependency-spike check:** new external dependency with >1
integration point → place a spike task (PoC / eval) ahead of it as
`blocked_by`. Detail: `REFERENCE.md`.

**MD content quality** — problem (why understandable?), intent
(goal not path?), description (self-contained?), priority
(plausible?), area (fits?). FAIL criteria: `REFERENCE.md`.

**Optional but always check:** `context_manifest`,
`workflow_template` (decision / research). Detail: `REFERENCE.md`.

**`## Not yet`** block required — empty is invalid. No exclusion
from the user → ask actively.

### 5. Validation (MUST)

`python3 $FRAMEWORK_DIR/scripts/plan_engine.py --validate`. The new
task must appear without an ERROR (milestone exists in plan.yaml,
blocked_by refs existing tasks, no cycle, schema conformance).

**FAIL →** correct the task file (milestone vs `docs/plan.yaml`,
blocked_by IDs vs `docs/tasks/`) and re-validate. Repeated FAIL →
delete the task files; escalate to the user (NNN is reused).

**Field vocabulary (schema-aware — MUST).** The canonical task-field set
is `framework/task-schema.yaml`; draw field names from it rather than
inventing them. A `SCHEMA_UNKNOWN_FIELD` WARN is not noise — it means
one of three things, each with a defined response:
- **typo / alias** (e.g. `ac`, `note`) → fix the name.
- **genuine repo-domain field** (meaningful only in this consumer) →
  declare it in the repo's `docs/task-schema-extensions.yaml`
  (`extension_fields:`), never leave it ad-hoc.
- **genuinely universal new field** → add it to `task-schema.yaml`
  (+ sync `task-format.md`) as a framework change, not a per-task
  improvisation.
This is the producer half of the shaping-contract: the schema shapes
what gets written; it is not a trailing log of whatever was improvised.

## Output

```
Task creation: [NNN] [title]
Duplicate check: no duplicate / duplicate of [NNN] / subset of [NNN]
Triage: fix immediately / create task — [rationale]
milestone: [key from plan.yaml]
File: docs/tasks/NNN.yaml + NNN.md
Validate: plan_engine --validate PASS
```

## Anti-patterns

- **NOT** skip the duplicate check ("my task is certainly new") —
  always scan; duplicates arise from slightly different wording.
- **NOT** set `blocked_by: []` without running step 1b
  substantively — parallel tasks with implicit dependency produce
  rework (B documents while A changes the state, B redoes).
- **NOT** skip triage and always create a task — backlog bloat from
  5-minute tasks that could be done directly.
- **NOT** accept an empty `## Not yet` block — ask actively; scope
  drift across the lifecycle when boundaries are unstated.
- **NOT** `spec_ref: null` on implementing tasks — assign a spec
  or hold the task. Breaks `consistency_check` spec coverage
  (exception: REFERENCE_SPECS).
- **NOT** fill required fields with "see above" / "current
  conversation" — tasks are picked up later without session
  context.
- **NOT** embed build-workflow route decisions in task notes
  (`--route sub-build`) — route-determination at workflow-start
  time per `workflows/runbooks/build/WORKFLOW.md` based on current
  task properties. Stale hints in notes anchor toward outdated
  paths.
