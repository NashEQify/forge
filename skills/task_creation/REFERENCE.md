# task-creation — REFERENCE

Detail mechanics. The Buddy-facing `SKILL.md` has the 5 steps in short form. This file
is the reference for quality checks, optional fields, dependency spike,
context manifest and workflow templates.

## Duplicate + dependency check (Step 1) — details

A single scan over `docs/tasks/` with **two** check dimensions.

### 1a — Duplicate check

Check:
1. **Does a task with the same goal already exist** (semantically, not just title match)?
2. **Does a task exist that contains this problem as a sub-problem**?
3. **Does a task exist that this problem makes obsolete**?

Result:
- **Duplicate found** -> no new task. Reference the existing one, optionally extend with a comment
- **Sub-problem of an existing task** -> add the problem as a comment/AC into the existing task
- **Obsolescence-maker** -> set the existing task to `status: superseded`, the new task becomes the successor
- **No duplicate** -> continue to 1b

### 1b — Cross-task dependency check

**Scope of the scan:** all tasks with `status: pending` or `status: in_progress`.
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

**Example (Tasks 365/366, 2026-04-09):**
- Task 366 (framework rationalisation) was created before Task 365 (/dev doc review),
  but 365 changes documentation about a framework state that 366
  alters. Without the dependency check, 365 would have started in parallel -> duplicate
  work (docs against a stale state, then again after 366).
- Correction: `365.yaml` -> `blocked_by: [366]`, `365.md` -> `## Dependency` block
  with justification. The user had to flag the missing dependency manually —
  the skill did not have the check as a mandatory step. Fix: this REFERENCE.md
  section + Step 1b in SKILL.md.

**Non-goal of the check:** no automatic graph reading of all specs. The
check is substantive — Buddy reads the titles + summaries of pending/in_progress
tasks and decides with their head, not with grep.

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
| **Scope / Not yet** | When the scope boundaries are clear. An empty "Not yet" block is invalid (DR-10) |

## Dependency-spike check

Does the task introduce a new external dependency with >1 integration point? -> Check whether a spike task (PoC/eval) needs to sit before it as `blocked_by`. The spike validates integration assumptions that are not derivable from documentation (undocumented config behaviour, implicit constraints, API deviations).

**Not needed** for well-documented, stable libraries (requests, click, pydantic). **Examples:** Task 049 (Cognee eval) -> 050 (Cognee integration), Task 110 (rlm eval) -> 111 (rlm integration).

## "Not yet" check

Every task MD MUST have a non-empty `## Not yet` block (mandatory per task-format.md, DR-10). At creation, formulate at least one scope exclusion. If the user names none, ask actively: "What explicitly does NOT belong in the scope of this task?"

## Context manifest (for Step 4: writing the task file)

If the required context is clear at task creation: fill `context_manifest` in the task file.

```yaml
context_manifest:
  required:
    - framework/agentic-design-principles.md        # short form: whole file
    - path: docs/specs/brain-schema.md              # long form with sections
      sections: ["## Entity-Schema", "## Relations"]
  available:
    - framework/spec-engineering.md
  skills:
    - skills/impl_plan_review/SKILL.md
```

**Rules:**
- Max 5 required entries. More -> split the task
- No manifest -> warning in the task output: "No context manifest. Buddy uses manifest inference (degraded)."
- The manifest can be added later when the context becomes clearer — better late than never

## Workflow-template assignment (for Step 4)

Does a standard template fit?
- **Build task** (code, docs with spec process) -> no template, build via `workflows/runbooks/build/WORKFLOW.md` (standard-build deprecated)
- **Decision task** (evaluate options) -> `workflow_template: decision`
- **Research task** (gather information + incorporate) -> `workflow_template: research`
- **None fits** -> no template, Buddy writes the workflow manually at execution

The template is set in the YAML. Buddy instantiates the `## Workflow` section from the template when the task comes up for execution.
