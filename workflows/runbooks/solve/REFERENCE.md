# solve Workflow — REFERENCE

Detail mechanics. Reference for state-file format, slug convention,
first-run, problem decomposition, variant details. The Buddy-facing WORKFLOW.md is
the checklist.

## State file — detail format

One file per solve invocation: `docs/solve/YYYY-MM-DD-<slug>.md`.

**Frontmatter (mandatory):**
```yaml
---
workflow: solve
problem: short problem description (1 line)
started: YYYY-MM-DD
phase: frame | refine | artifact | validate | execute | done
status: active | paused | done | aborted
task_ref: NNN | null
artefacts: [list of produced files]
---
```

`workflow` identifies the workflow type (for workflow-agnostic tooling).
`task_ref` links to the task YAML (null if no task exists).
Both fields are mandatory. Existing state files are
not migrated — on resume, Buddy adds the fields inline.
Set the exact `state_file` at taskless start. The first ordinary accepted Frame identifies the canonical file. Use it for
the rest of the run, including retries and close. Restore the original path
on a mismatch without replacing historical evidence. Hold if the original
checked path cannot be established.

**Body structure:** one `## Phase N: <name>` block per phase, append-only.
- Phase 1: frame report (8 sub-steps from frame)
- Phase 2: refinement notes (dialogue results, chosen approach)
- Phase 3: artefact refs + registration plan
- Phase 4: board result (consolidated with tracking table)
- Phase 5: execute result (applied actions, deploy, handoff)

**After every phase:** extend the body, update frontmatter `phase`, and persist
the result. Phase and final commits follow `framework/process-map.md` section
Authorization: commit only under an applicable request or standing repository
policy. Continue already authorized actions for the unchanged scope and target
without routine reapproval. Local work or a docs change grants no push/deployment
authority. Retain the validated artefact even when no commit is authorized.
An authorized failed or missing publication remains an unresolved obligation;
local solve closure does not satisfy it or establish publication success.

## Slug convention

- `<kebab-case-short-topic>`
- At most 40 characters, lowercase, no special characters
- Derivation: first 3-5 significant words of the problem description
- Examples: `YYYY-MM-DD-solve-bootstrap.md`, `YYYY-MM-DD-dashboard-perf.md`
- On naming collision: counter suffix (`-2`, `-3`) or timestamp
  (`YYYY-MM-DD-HHMM-<slug>.md`)

## First run (new project)

`mkdir -p docs/solve` before the first state-file write (idempotent). For
clones/forks without prior solve invocations.

## Problem decomposition (exception)

If the problem is recognised as too large in Phase 1: **decompose inline in the
same state file**. The body then contains multiple Phase-1 sub-blocks:

```
## Phase 1: Frame (Sub-Problem A)
{8 sub-steps for A}

## Phase 1: Frame (Sub-Problem B)
{8 sub-steps for B}

## Phase 2: Refine
{operates on the combined understanding of all sub-problems}
```

**No scoping handoff** — scoping is for objectives with a known done,
not for unframed problem decomposition. See
`skills/frame/REFERENCE.md` §Edge Cases.

**Iteration-bound mechanics:** "Frame max 1" refers to one frame
pass per problem OR sub-problem. On decomposition: N sub-problems = N
frames, but each sub-frame runs only once. User feedback after frame =
Phase 2 Refine, not a new frame.

## Planning and plan maintenance

For an agreed outcome spanning separately commissioned work, record this plan
in Solve Phase 2 or in the existing Scoping handoff for approved outcomes:

1. The original agreement and authority for scope and order.
2. Each promised outcome, its covering work and observable acceptance.
3. Known prerequisites and uncertainties, including who will resolve them and
   what evidence or decision is needed before dependent work.
4. The first executable slice with prerequisites, scope and acceptance, then
   later outcomes with their constraints, order and dependencies.
5. The integration, activation and outcome checks, with responsible owners and
   the evidence that will establish each required result.

Check coverage before completing Refine. Recheck before dependent artifact
work or commission, Validate, Apply or Scoping handoff.
Trace every outcome to work and evidence, including any promised result after
restart or retry. Check readiness and authority for the next slice. If a
plan or evidence due now is missing, unreachable or incomplete, hold the step
until repaired and checked. Keep the decision in the existing
record. Validate the selected artifact separately using its applicable method.

**Handoff and commission.** At Apply, compare the current plan and evidence
with the agreement. Repair changed coverage or resolve authority before
release. Changed artifact proof needs current Validate evidence as well.
Transfer the agreement, current record links, outstanding acceptance duties
and next authorized action. Record the receiver's acknowledgment and duties.
The handoff directs the receiver to repeat the plan, evidence and authority
check at their owners immediately before filing or releasing work, even after
acknowledgment. Hold while these checks expose a gap. File an authorized work
unit through `task_creation` with its own approved acceptance and constraints,
check placement and dependencies and validate the plan. Before dispatch, link
the current plan and evidence from the task. Give the worker the plan-derived
purpose, accepted prerequisites, permitted action and approved acceptance.
Instruct the worker to stop affected work and return source evidence when a
premise is contradicted.

**Discovery and continuation.** Verify the returned finding against its source.
Persist the finding and its scope immediately at the evidence owner, preserve
still-valid evidence, and link the hold from the task and plan before reconciling
the graph. Track each affected brief's actual disposition. A requested stop
remains pending until acknowledged. File a separately justified prerequisite through
`task_creation` when authorized. Reconcile both dependency directions, plan
and brief at their owners, and validate the graph. Obtain the applicable order
decision before placing work outside the agreed order. A fresh actor follows
the current links from normal task entry before dependent action. An unresolved
hold takes precedence over apparent readiness in the old graph. After graph
repair, compare actual predecessor evidence with its approved acceptance and
check current order and replacement brief before release. Persist each change
as it occurs so either interruption can be recovered from the task.

**Integrated acceptance.** The receiving initiative owner holds acceptance
until activation and verification in the actual operating context are observed
against the promised outcomes, even with every local task closed. Keep the
open duty and its owner in the plan. Solve closes against its original Frame.

**Definition transition.** Exact forward pairs permit observation only.
Preserve state bytes, pauses, receipts and history. Old unfinished progression
still requires creation-bound proof. Current artifact review, Apply freshness
and the original Frame close checks still apply.

## Validation decision

Complete Write artifact with `--set artifact_path PATH --evidence TEXT`
to record the chosen nonempty project-relative file. Keep that path distinct
from review outputs. For code, spec and UX use the selected artifact in the
exact Solve `validate` review capture and adopt the current applicable
decision before `--complete validate --id WORKFLOW --set artifact_class CLASS
--evidence TEXT`. Retry Validate and establish new current evidence if the
artifact or decision changes before Apply.

For a Council decision on an architecture artifact or an eligible MCA
implementation-plan review, retain a Markdown decision and supply
`--set validation_decision PATH` at the same explicit completion. The
frontmatter fields are `workflow_id`, `artifact_path`, `artifact_sha256`,
`method`, and `outcome`. Use `council` with `ACCEPTED` or
`impl_plan_review` with `APPROVED` respectively. An implementation-plan
decision also records project-relative `mca_plan`, `spec` and `delegation`
paths from the actual commissioned inputs. The plan is the selected artifact.
Record the authorized decision maker and original reports in the body.
The operator owns the decision and prerequisite judgment. The engine
observes file identity and records the method as agent-confirmed.

## Phase 5 Execute — variant details

### Variant 1: Direct (skill/runbook/protocol)
1. Retain the artefact validated in Phase 4; commit only under the authorization rule above
2. Extend process-map.md (routing + skill taxonomy + composition map + maturity)
3. Stale cleanup: grep for replaced artefacts, fix all references
4. Only when deployment is authorized for the intended target: deploy via `$FRAMEWORK_DIR/scripts/deploy-docs.sh`; a docs/ edit alone does not authorize it
5. After authorized deployment, verify the actual intended outcome visually per `framework/invariants.md` §Deployment verification; if unavailable, request user inspection and retain the unverified boundary
6. knowledge_processor wrap-up -> history entry
7. Persist state file `status: done`; final commit only when authorized under the rule above; retain any authorized missing publication separately

### Variant 2: Handoff Build
1. Artefact is a spec/plan for feature implementation
2. Record the artefact as input for Build intake; start task-bound execution
   when an applicable task exists
3. solve Phase 5 = document handover + status: done
4. The build workflow continues independently
5. knowledge_processor wrap-up in solve close
6. Persist state file `status: done`; final commit only when authorized under the rule above; retain any authorized missing publication separately

### Variant 3: Handoff docs-rewrite
1. Artefact is a docs plan
2. docs-rewrite/WORKFLOW.md takes over
3. Analogous to Variant 2 (handover + solve close)

### Variant 4: Self-apply
1. Artefact is directly executable (e.g. a fix script, a configuration update)
2. Buddy executes it in the solve Phase 5 step
3. Verification + knowledge_processor wrap-up
4. Persist state file `status: done`; final commit only when authorized under the rule above; retain any authorized missing publication separately

## Status transitions

- `active` -> `paused`: user request or session end mid-phase
- `active` -> `done`: Phase 5 and close bookkeeping complete, the Solve
  record is terminal, and any attached task is done
- `active` -> `aborted`: user abort or unrecoverable failure
- `paused` -> `active`: resume on a new session (boot finds via `ls docs/solve/`)

## ADR check (close-bookkeeping)

Sub-step (a) of `close-bookkeeping`, fed by close-retro's §Stale-Decisions.
Triggers `skills/documentation_and_adrs/SKILL.md` when the ADR-discipline triple
is satisfied:

- **Hard-to-reverse** — meaningful cost to switch later
- **Surprising-without-context** — future reader asks "why like this?"
- **Result-of-real-trade-off** — genuine alternatives with justification

Solve is by definition for **open solution shape** — the skip rate is lower
than for build. The frame report (Phase 1) has already documented trade-offs,
Phase 2 Refine has sharpened them, Phase 5 Apply has activated them. If the chosen
approach satisfies the triple: ADR with cross-reference to the frame report.

One-line skip, no block. Anti-pattern: ADR inflation.

## Trigger validation (Phase 0 — at intake)

Before Phase 1 starts: trigger validation against the NOT-FOR list in
WORKFLOW.md. If the problem actually belongs to another workflow
(bug, knowledge question, clear feature): redispatch immediately, do not force it
through Phase 1. Document the redispatch decision in the state file
and close it with `status: aborted` (reason: "redispatched to <workflow>").
