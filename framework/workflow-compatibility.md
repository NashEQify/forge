# Reviewed workflow compatibility

The exact fingerprint pairs in `workflow-compatibility.yaml` permit only the
reviewed save/context-housekeeping transitions to shared continuity and the
forward development transitions below. They are
not a general older-version support promise. Unlisted changes fail closed.

When a workflow definition changes its semantic fingerprint, include its reviewed compatibility pair in the same
change so retained runs can continue after an update.

The ordered checkpoints and engine completion, dependency, routing and commit
conditions are retained. Dependent writes publish coherently instead of using the
old parallel-write grouping. The following records the substantive obligations.

| Retained checkpoint | Substantive obligation and approved implementation change |
|---|---|
| save/orient | Active owner, permission and prior-state orientation remains; coherent scope/pending checks strengthen retrieval. |
| save/dispatcher-final | Existing buffer triage and optional framework-feedback handling retained verbatim in parsed instruction. Shared authorization/privacy still binds. |
| save/validate-reconciliation | Session knowledge gap closure remains. Already selected task-status and plan obligations forward to development adapter; ambiguous legacy selection blocks, never silently drops checks. File presence no longer selects unrelated new work. |
| save/knowledge-process | Actual useful deltas, scoped user/project knowledge and navigability remain. Canonical KP replaces duplicated algorithm; protected publication supplies concurrency/recovery. |
| save/workflow-handoff-context | Required continuation information for selected work remains; full authoritative references and checked state replace truncated all-active display. Unknown selection is a blocker; unrelated workflows are preserved unmodified. |
| save/handoff-write | Full prior handoff, merge of untouched/open topics, goals, decisions, failed attempts, approvals, leading results, next steps and jobs remain. Fixed nine-heading layout and unprotected reread/copy mechanics are deliberately replaced under spec by semantic merge and durable recovery. |
| save/history-entry | Task closeout and meaningful durable outcomes retain history/audit duties through selected development contribution. Interim saves do not manufacture history; immutable evidence and owner conventions remain. |
| save/buffer-cleanup | Only reconciled PROCESSED entries may be removed; unresolved entries remain. Protected publication replaces direct mutation. |
| save/commit-push | Parsed instruction and mechanical completion unchanged. Authorization, no foreign staged work, no destructive Git recovery, and explicit partial-save reporting remain. |
| save/verify-report | Actual files/routes, commit/push verification and partial outcome reporting remain. Pending reconciliation and domain blockers explicitly prevent false completion. |
| housekeeping/phase-analysis | Read-only inventory of structure, validity and discovery remains. Size is explicitly a review signal rather than a deletion rule, as the user requested. |
| housekeeping/phase-curation | Retained area checklist and completed/remaining work resume against actual files. Each meaningful change is reconciled; existing implementation authorization replaces repeated routine permission. No automatic bulk discard. |
| housekeeping/phase-close | Only fully resolved progress can clear; commit remains authorization-bound. Unresolved recovery survives and prevents completion. |

This permits reviewed changes in procedure/shape, not loss of source meaning or old
open obligations. Completed step evidence and workflow state files are not rewritten.
State schema/status/reference validation remains independently mandatory. A mapping
cannot authorize unknown state vocabulary or a missing selected run.

Implementation requirement: exact old/new semantic fingerprint pairs, scoped to these
two workflows, with explicit forward/reverse allowance. Do not authorize by name,
matching step count, or shared IDs alone. Any further instruction/gate/dependency/
completion change creates a new fingerprint and must fail until separately reviewed.
Cosmetic metadata may normalize only where the engine's contract defines it as such.


## Forward build and solve interpretation; mandatory review definition transitions

When a retained build, solve, fix, review or spec-board run is interpreted, installed or rolled back under these
pairs, and when a change to those definitions is reviewed: read and follow
`framework/workflow-compatibility-review-gates.md` (§Forward build and solve interpretation, §Mandatory review
definition transitions, §Review-round and architect-lens transition).

## Taskless Solve progression and close

The exact pair allows upgrade observation. Both routes retain all step IDs,
order, applicable validation, task readiness and historical evidence. Refine
keeps dialogue and notes on either entry, with the Council decision inside
the step. Close checks the original Frame state file, fresh invocation
evidence and the attached task's done record when bound. An unfinished run
with the preceding creation fingerprint still refuses progression. Preserve
its state and history pending explicit disposition.

## Solve refinement intent transition

The Refine instruction requires the selected approach's rationale to compare the governing project
and original local intent, with the dependent artifact held on unresolved authority. A still-governing
Frame suffices for an unchanged choice. Dialogue, the optional Council route, step IDs, predicates,
order and original Frame-history contract are preserved.

Two exact upgrade edges cover the immediate prior definition and its retained taskless predecessor.
They permit observing those retained runs with their evidence and revisions intact. Unfinished
creation-bound Refine or close checks still require matching interpretation before progression.
Neither edge permits rollback or implies a transitive transition.

## Solve state and review ownership transition

Exact upgrade observations from the immediate definition and the two
already supported retained predecessors preserve ordered steps, route
membership, revision, receipts, optional Refine Council and both Refine
intent levels and hold. The correction derives the canonical record from
the first ordinary Frame and checks the selected artifact's applicable
decision before handoff. Task-bound readiness and close still use the
actual task. Earlier decisions and file observations remain historical.
Unfinished runs lacking matching creation-bound interpretation stop
before progression. The mappings allow observation, without rollback,
automatic reopening or transformation of retained records.

The next Solve generation (`7820325e…`) requires fresh invocation evidence
for manual, agent-confirmed Apply and restores reader-facing UX review with
IA and heuristic perspectives. The four exact upgrade pairs preserve the
same observational access and creation boundary. Earlier receipts keep
their original assurance.

Solve planning transition in `workflows/runbooks/solve/REFERENCE.md` §Planning and plan maintenance.

## Build test-design challenge, fix verification-scope, test-volume and fix test-count transitions

When a retained build or fix run is interpreted, installed or rolled back under these pairs, and when a change to
those definitions is reviewed: read and follow `framework/workflow-compatibility-test-scope.md` (§Build test-design
challenge transition, §Fix verification-scope transition, §Test-volume transition, §Fix test-count and review-round
transition).

## Instruction-unit pointer transition

The build, fix, review, spec_board and solve definitions changed only in step `instruction:` text that says where a
rule is read: it now names the step-loaded unit that holds a section moved out of its core (for example
`evidence-review-capture.md`, whose header routes to `evidence-review-adoption.md` before any decision, where a
dispatch step named section 9 of the evidence protocol; `skills/testing/run-strategy.md` for the testing skill's
former test-selection section). The rules moved verbatim, so no step gained, lost or changed an
obligation; steps, ids, gates, completion checks and variables are unchanged. The pairs are upgrade-only: a run
started on the earlier definition continues on the new one, and the reverse is not accepted.

## Skeleton-return marking transition

The build definition changed only in the test-design step's `instruction:` text: one sentence now says that a RED
which only shows the interface under test is missing is listed in the skeleton return as `oracle unverified`
(`skills/testing/SKILL.md` §Meaningful pre-fix witness). It adds a marking to the skeleton writer's return;
when test design runs and whether the skeleton writer runs are unchanged, and so are steps, ids, gates, completion
checks and variables. The pair is upgrade-only: a run started on the earlier definition continues on the new one, and
the reverse is not accepted.

## Retirement-inventory pointer transition

The build definition changed only in the interview step's `instruction:` text: one paragraph now says that an owner
answer retiring a capability is carried into the spec with the retirement inventory of
`skills/_protocols/spec-amendment-discipline.md` §Retiring a capability. It adds a part to the spec record
that step leads to; steps, ids, gates, completion checks and variables are unchanged. The pair is upgrade-only: a run
started on the earlier definition continues on the new one, and the reverse is not accepted.

## Verdict-line transition

The build and fix definitions changed in their code review steps (build `code-review-board`, fix `code-review`) and
in the fix `fix-brief` instruction; steps, ids, order, routes, gates, variables and the mandatory adoption check are
unchanged. Each review step's compound gains four `file_content_check` leaves between the adoption check and the
manual leaf. They read `docs/reviews/code/{task_id}-verdict.md` for the lines of the verdict skeleton
(`skills/code_review_board/REFERENCE.md` §Verdict file skeleton): the `Skeleton: verdict <n>` line, a `review:` line
with a level and seats or a waiver, a `re_reviews: <n> of <m> on <mechanism>` line, and a findings table with a
`disposition` column. They check presence only, and `--force` skips them while the adoption check still runs. The
step texts name these lines and their forms, the retry forms of the step and the fix-brief skeleton
(`skills/_protocols/fix-brief-skeleton.md`); the fix-brief text names that skeleton's round and verdict lines.

| Retained obligation | Preserved interpretation |
|---|---|
| Completed review steps | Their evidence stays; the leaves are not replayed on a terminal step. |
| A review step not yet complete | It completes on its current definition: the verdict carries the four lines. A verdict adopted before the lines were added is adopted again after they are written; re-adoption moves the earlier adoption to `adoption_history`. Where the verdict path lies inside the captured subject, the capture becomes noncurrent and a retry with a fresh capture is needed (§Review-round and architect-lens transition, row Review adoption, `workflow-compatibility-review-gates.md`). |
| Review selection, dispositions, re-review limit, at-the-cap ruling, commit gate | Unchanged; the leaves read that the verdict records them, not what they are. |
| Retained runs | Workflow state, completed step evidence and pauses are not rewritten, replayed or recertified. |

The pairs (build `ecf7c645…` to `795fecd6…`, fix `1599a24a…` to `98943eed…`) are upgrade-only. There is no reverse
allowance: the earlier definitions do not refuse a verdict without the lines. There is no transitive allowance: older
pairs do not chain to these, and any further definition change fails closed until separately reviewed.
