# task-creation — REFERENCE

Detail mechanics. The Buddy-facing `SKILL.md` has the 5 steps in short form. This file
is the reference for quality checks, optional fields, dependency spike,
context manifest and workflow templates.

## Duplicate, bundling + dependency check (Step 1) — details

A single scan over `docs/tasks/` and the sibling tasks the same request would file, with three check dimensions
(duplicate + bundling, dependency, split-gap).

### 1a — Duplicate + bundling check

Check:
1. **Does a task with the same goal already exist** (semantically, not just title match)?
2. **Does a task exist that contains this problem as a sub-problem**?
3. **Does a task exist that this problem makes obsolete**?

Result:
- **Duplicate found** -> no new task. Reference the existing one, optionally extend with a comment
- **Sub-problem of an existing task** -> add the problem as a comment/AC into the existing task
- **Obsolescence-maker** -> set the existing task to `status: superseded`, the new task becomes the successor
- **No duplicate** -> the bundling check (`SKILL.md` step 1a), then 1b for the tasks that stay separate

Bundling details:
- **Timing differs** when one part can or must run at a time the other cannot for a reason outside the two parts: it is
  due now while the other waits for a third result, or it needs a maintenance or install window the other does not.
  Waiting for the other part's own result is the fold case (a shape-deciding step), not a timing difference.
- **Stop point:** the shape-deciding part is a `## Workflow` step (`framework/task-format.md`) whose failure criterion
  is written in the step: when it fails, the task stops and reports before the next step.
- **After a fold**, run 1b for the task that received the part, in both directions, against the tasks that stay
  separate: a new part brings dependencies that no `blocked_by` edge carries yet.

### 1b — Cross-task dependency check

**Scope of the scan:** all tasks with `status: pending` or `status: in_progress` that stay separate
after the bundling check, checked against the new task or the task that received it.

**Lifecycle symmetry:** this step **builds** the `blocked_by` graph; closure on terminal status (replace on
superseded/absorbed, remove on wontfix, keep on done) is `task_status_update` Step 4.
Skip `done`/`superseded`/`wontfix`/`absorbed` (no dependency
possible).

**Check questions per task (substantive, not regex):**

| Question | Implication |
|---|---|
| Does one of the tasks change framework artefacts (skills/workflows/agents/specs) that the other documents/uses/extends? | Doc task `blocked_by` refactoring task |
| Does one of the tasks produce specs/decisions/ADRs that the other needs? | Consumer `blocked_by` producer |
| Is the scope of A a logical prerequisite for B's scope? | B `blocked_by` A |
| Would parallel execution produce extra work (B documents a state that A is changing in the meantime)? | B `blocked_by` A |
| Does one of the tasks use artefacts that the other is currently building or removing? | User `blocked_by` builder |

**Determine the direction of the dependency:**

- **New task depends on an existing one:** enter `blocked_by: [existing_NNN]` in the
  new YAML. Documentation: `## Dependency: blocked_by N` block
  in the new MD with justification.
- **Existing task depends on the new one:** edit the existing YAML — add the new
  task ID to its `blocked_by` list. **Mandatory, not optional.**
  Documentation: short note in the existing MD ("blocked_by updated: waiting
  for Task NNN — [reason]").

**After the decision:**
- `blocked_by: []` set only if all tasks have passed the scan
- Dependency justification ALWAYS documented in the MD body, never only in the YAML field
- plan_engine --validate (Step 5) checks cycles — dependency errors are
  caught there

**Example:**
- A "framework rationalisation" task was created before a "/dev doc review"
  task, but the doc-review changes documentation about a framework state that
  the rationalisation alters. Without the dependency check, the doc-review would
  have started in parallel -> duplicate work (docs against a stale state, then
  again after the rationalisation).
- Correction: the doc-review task gets `blocked_by: [<rationalisation-task>]` +
  a `## Dependency` block in its MD body.
  with justification. The user had to flag the missing dependency manually —
  the skill did not have the check as a mandatory step. Fix: this REFERENCE.md
  section + Step 1b in SKILL.md.

**Non-goal of the check:** no automatic graph reading of all specs. The
check is substantive — Buddy reads the titles + summaries of pending/in_progress
tasks and decides with their head, not with grep.

## Claim verification (Step 1.6)

C-VERIFY is an authoring discipline applied by the agent; no hook enforces it, so no doc claims a `BLOCK` for it. The
safeguard is the C-VERIFY block itself.

## Triage table (Step 2)

| Criterion | Fix immediately | Create a task |
|-----------|-----------------|--------------|
| Effort | < 5 minutes, clearly scoped | > 5 minutes or unclear |
| Reversibility | Easy to undo | Hard to undo or unclear |
| Dependencies | None | Has deps or is a dep for others |
| Context | Available now, gone later | Can be done later without context loss |
| Interruption | Does not significantly interrupt | Would substantially interrupt work |

If ALL "fix immediately" criteria apply -> fix immediately (Light Plan). Otherwise -> create a task.

## MD content quality checks

| Field | Check question | FAIL when |
|-------|----------------|-----------|
| **Problem** | Does an outsider understand why this matters? | Too short ("fix XY"), no context, no impact |
| **Intent** | Is the goal clear without describing the path? | Describes solution instead of goal, or identical to problem |
| **Description** | Can the task be picked up later without information loss? | Refers to "current conversation" or "described above" |
| **Prio** | Plausible relative to existing tasks? | Everything is "highest" |
| **Area** | Fits existing areas in the backlog? | New area without justification |

## Optional fields

| Field | When to fill |
|------|--------------|
| **Acceptance Criteria** | When the done criterion is clear. Check question: "Can an outsider unambiguously say whether it is met?" |
| **Constraints** | When MUST/MUST NOT/PREFER/ESCALATE are known |
| **Deps** | When dependencies are recognisable. Check against the backlog |
| **Scope / Not yet** | When the scope boundaries are clear. An empty "Not yet" block is invalid (scope must be explicitly bounded) |

## Dependency-spike check

Does the task introduce a new external dependency with >1 integration point? -> It gets a spike (PoC/eval). The spike validates integration assumptions that are not derivable from documentation (undocumented config behaviour, implicit constraints, API deviations) before the build relies on them.

**Where the spike sits:** when it needs its own decision or authorization (its result goes to someone to decide whether to adopt the dependency at all, or it needs a permission the build does not), it is a separate spike task, `blocked_by` ahead of the build ("Cognee eval" -> "Cognee integration" when the eval decides whether Cognee is adopted). Otherwise it is the task's first step, with a stop point before the build: a failed spike stops the task and reports instead of building.

**Not needed** for well-documented, stable libraries (requests, click, pydantic).

## No milestone fits

Surface to the user before continuing: *"No existing milestone fits — propose a new one (key + title + desc) or pick
the closest existing one?"* (See `docs/plan.yaml` `milestones:` for the schema — new entries follow the existing
`key + title + desc + phases + requires` shape.) Plan.yaml milestone-writes belong outside this skill; if the user
approves, Buddy edits `docs/plan.yaml` directly before the skill resumes at step 5.

## Field vocabulary

The canonical task-field set is `framework/task-schema.yaml`; draw field names from it rather than inventing them. A
`SCHEMA_UNKNOWN_FIELD` WARN is not noise — it means one of three things, each with a defined response:
- **typo / alias** (e.g. `ac`, `note`) → fix the name.
- **genuine repo-domain field** (meaningful only in this consumer) → declare it in
  `<project>/docs/task-schema-extensions.yaml` (`extension_fields:`), never leave it ad-hoc.
- **genuinely universal new field** → add it to `task-schema.yaml` (+ sync `task-format.md`) as a framework change,
  not a per-task improvisation.

This is the producer half of the shaping-contract: the schema shapes what gets written; it is not a trailing log of
whatever was improvised.

## "Not yet" check

Every task MD MUST have a non-empty `## Not yet` block (mandatory per task-format.md — scope must be explicitly bounded). At creation, formulate at least one scope exclusion. If the user names none, ask actively: "What explicitly does NOT belong in the scope of this task?"

## Context manifest (for Step 4: writing the task file)

If the required context is clear at task creation: fill `context_manifest` in the task file.

```yaml
context_manifest:
  required:
    - path: docs/specs/<name>.md                    # long form with sections
      sections: ["## Entity-Schema", "## Relations"]
  available:
    - framework/spec-engineering.md
  skills:
    - skills/impl_plan_review/SKILL.md
```

**Rules:**
- Max 5 required entries. More -> narrow `required` to what the first steps need (the rest goes to `available`), or
  split only for a step-1a reason (owner, timing, authorization, safety floor)
- No manifest -> warning in the task output: "No context manifest. Buddy uses manifest inference (degraded)."
- The manifest can be added later when the context becomes clearer — better late than never

## Workflow-template assignment (for Step 4)

Does a standard template fit?
- **Build task** (code, docs with spec process) -> no template, build via `workflows/runbooks/build/WORKFLOW.md` (standard-build deprecated)
- **Decision task** (evaluate options) -> `workflow_template: decision`
- **Research task** (gather information + incorporate) -> `workflow_template: research`
- **None fits** -> no template, Buddy writes the workflow manually at execution

The template is set in the YAML. Buddy instantiates the `## Workflow` section from the template when the task comes up for execution.
