# Reviewed workflow compatibility

The exact fingerprint pairs in `workflow-compatibility.yaml` permit only the
reviewed save/context-housekeeping transitions to shared continuity and the
forward development transitions below. They are
not a general older-version support promise. Unlisted changes fail closed.

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
definition transitions).

## Build test-design challenge, fix verification-scope and test-volume transitions

When a retained build or fix run is interpreted, installed or rolled back under these pairs, and when a change to
those definitions is reviewed: read and follow `framework/workflow-compatibility-test-scope.md` (§Build test-design
challenge transition, §Fix verification-scope transition, §Test-volume transition).

## Instruction-unit pointer transition

The build, fix, review, spec_board and solve definitions changed only in step `instruction:` text that says where a
rule is read: it now names the step-loaded unit that holds a section moved out of its core (for example
`evidence-review-capture.md`, whose header routes to `evidence-review-adoption.md` before any decision, where a
dispatch step named section 9 of the evidence protocol; `skills/testing/run-strategy.md` for the testing skill's
former test-selection section). The rules moved verbatim, so no step gained, lost or changed an
obligation; steps, ids, gates, completion checks and variables are unchanged. The pairs are upgrade-only: a run
started on the earlier definition continues on the new one, and the reverse is not accepted.
