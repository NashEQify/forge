# Reviewed workflow compatibility — forward and review-gate transitions

Step-loaded unit of `framework/workflow-compatibility.md`. Read it when a retained build, solve, fix, review or
spec-board run is interpreted, installed or rolled back under the forward build/solve pairs, the mandatory review
definition pairs or the review-round and architect-lens pair, and when a change to those definitions is reviewed.

## Forward build and solve interpretation

The additional exact build and solve pairs allow upgrade only. Existing terminal
step evidence remains historical; installation never replays or recertifies it.

| Retained obligation | Preserved interpretation |
|---|---|
| Build authority-only route | Brief gates remain route-skipped; open publication work remains open. |
| Paused standard build before test design | Pause, route, variables, step evidence and pending implementation remain unchanged. Future brief-author/signoff must bind one artifact to the exact run and meet the current brief contract. Old evidence cannot stand in for the new check. |
| All-terminal active solve without completion marker | The workflow remains unfinished. Earlier terminal checks retain their evidence without replay; future retry of affected checks requires matching creation-bound interpretation. |

These are observational compatibility decisions, not authorizations to progress,
unpause, publish or close retained runs. The predecessor's weaker brief/evidence
and executable-check rules do not preserve the current guarantees in reverse, so
no reciprocal rollback pair is permitted. New or advanced runs are revalidated
before rollback. Unrelated pairs, one-field definition mutations, and the later
save/spec-board definitions remain unsupported until separately reviewed.

Maintenance separately validates supported retained carrier structure before
recognizing acknowledged archived completion or abort. Its deterministic private
history projection includes the exact retained state, independent of current
step/route vocabulary. It cannot authorize ordinary continuation. Missing markers,
active completion awaiting archival, paused completion and unresolved escalation
retain strict current-definition interpretation. Abort remains distinct from success
and may retain pending steps or a pause. No state or journal schema changes.

## Mandatory review definition transitions

The additional exact build, fix, review and spec-board pairs are upgrade-only
policy for the matched generation. Activating this policy requires independent
review of the exact definition changes and these preserved obligations; manifest
presence alone is not evidence of review adoption or installation. Older accepted
pairs remain frozen. There is no transitive older-to-latest allowance and no
reverse mapping: the predecessor cannot preserve the stronger current gate.

| Definition and boundary | Preserved obligation and particular change |
|---|---|
| Build board-spec | Existing spec review, source-grounded Buddy decision, severity/team rules and manual completion remain. Exact owner/iteration/run/subject/current reports now qualify the decision at spec_success with minimum schema1. Relevant fixes use retry and fresh applicable review; old PASS is historical. |
| Build code-review-board | Existing light/L1/L2 selection, pivotal-source checks, dispositions and commit gate remain. Complete current light/scoped/board producers and Buddy decision qualify code_success with minimum schema1. Code PARTIAL/FAIL cannot advance; risk acceptance rules remain separate. |
| Fix code-review | Existing risk-based selection and applicable scoped reproduction/adversary verification remain. The exact retained decision must qualify code_success; canonical locators do not confer identity. No full-board rerun is added. |
| Review board-dispatch | Same routed skills and required step vocabulary. Current evidence policy deliberately accepts supported NEEDS-WORK so repair is reachable; it does not grant readiness. Exact captured owner is retained after dispatch completes while the workflow is live. |
| Review convergence and phase-close | Optional convergence skip remains optional. Relevant repair retries board-dispatch and fresh-captures before the existing applicable verification. Required phase-close now checks spec_success before manual completion and review-derived writes; a negative or missing adoption blocks forward readiness. |
| Spec-board dispatch and readiness | Standalone owner remains agent-dispatch; nested calls carry the exact caller pair and existing parent identity without competing capture. Matching-file completion remains transport evidence. Readiness checks the explicit retained owner before task existence and before task-status writes. New PASS writes APPROVED; historical pass stays readable. |
| Spec-board discourse/delta | Earlier selected payloads remain unchanged. Register contingent slots through append-only same-subject capture, preserve discourse and subsequent Chief as separate reports, and use creation transport instead of modifying an earlier consolidated payload. Relevant changes require retry/fresh capture; the existing triggering delta team and reduced final teams remain. |

All four retain routes, dependencies, status meaning, evidence-required publication
boundaries, authorization and unrelated unfinished obligations. No mapping rewrites
state, advances a pointer, unpauses a workflow, supplies missing qualification or
recertifies completed evidence. Legacy current reports cannot fill new current
slots. Historical capture/adoption is never backfilled. A terminal step's evidence
remains history even if its definition has gained a stronger completion condition.

Creation-bound interpretation is an independent progress guard. In particular,
an unfinished older spec-board run may be observable under its exact mapping yet
still refuse progression until explicitly reconciled or a new applicable review
is commissioned. The mapping does not bypass that refusal, manufacture creation
provenance or authorize status changes. Installation/rollback must still inspect
the exact retained carriers; unlisted fingerprint changes fail closed.

## Review-round and architect-lens transition

The additional exact build pair (`2e27fd46…` to `ecf7c645…`) allows upgrade only. It spans several
definition changes in one step, for a run started on the earlier definition. Four step instructions and one
flag changed; steps, order, routes, completion predicates and variables did not.
- **`test-design`:** an amendment's `update` entries still dispatch the skeleton writer.
- **`architect-lens`:** `required` becomes false, so the engine accepts `--skip` with a non-blank reason. The
  instruction allows it only for fewer than three touched modules, no new subsystem and effort below L (the unchanged
  `skip_when` also names DIRECT and AUTHORITY-ONLY). That a brief of L2 shape is never skipped is discipline, as the
  lens's applicability was before.
- **`brief-author`:** the brief's test list follows the count rule.
- **`code-review-board`:** the text names the verdict path the unchanged completion check already reads; the check
  passes only when the bytes there equal the adopted decision's. A fix pass and its re-verify run the selected set;
  a due broad run comes once, after the last pass, by the full gate's runner. Each finding gets at most one test (a
  strengthened existing test, one reproduction, or a command only), findings of one class share one, and per-finding
  tests of earlier passes are listed for removal. A finding whose only subject is an existing test opens no fix pass
  or re-review of its own (`skills/code_review_board/test-findings.md`). Before a fix pass or re-review, machinery
  the solution introduced is reassessed against the original outcome, and no task is filed solely because a finding
  exists (`agents/buddy/architecture-comprehension.md` §B). The re-review limit is named with its owner.

| Retained obligation | Preserved interpretation |
|---|---|
| Completed steps | A `test-design`, `architect-lens` or `brief-author` step completed under the earlier definition keeps its evidence; it is not replayed, and the skip allowance does not reopen it. |
| Steps not yet run | A run that reaches one of those steps takes its current instruction; each can be supplied from the run's own inputs. |
| Review adoption | Light / L1 / L2 selection, pivotal-source checks, dispositions and the commit gate remain. A run whose code review is unfinished adopts its current decision at `docs/reviews/code/{task_id}-verdict.md` before completion. Re-adoption there moves the earlier adoption to `adoption_history`; the path must lie outside the captured subject or be excluded, or the capture becomes noncurrent. |
| Regression evidence | A fix still makes the test its fix brief names fail before and pass after, or records a command's output before and after where no test applies, and runs the selected set for its changes; a due broad run (`skills/testing/run-strategy.md` §Test selection) is retained, once, after the last pass. |
| Review findings | Wrong product behaviour, evidence a rule requires and an owner-approved exit criterion still change the verdict; a defect in retained required behaviour still requires correction. A test-only finding is still recorded and routed. |
| Rounds already run | A retained run counts the re-reviews it already ran per mechanism. The limit is the one the earlier definition's owner unit already set (`skills/code_review_board/verdict.md` §Re-review): two, or more under the foundation or user override of `REFERENCE.md` §Re-review limit. Past it the run commissions none and follows `skills/convergence_loop/at-the-cap.md`: each open finding gets a class and a ruling; a critical, safety-floor or blocking finding is never accepted, parked or carried to other work, its smallest change goes to the caller and stays open as the verdict's ESCALATE; no finding leaves without a `remaining_findings` entry or a `blocked_by` edge. |
| Retained runs | Workflow state, completed step evidence and pauses are not rewritten, replayed or recertified. |
| Review currentness | Applicable current capture/adoption remains required; earlier reports do not become current through this mapping. |

Owner units the instructions point to are not fingerprinted: their current text governs retained runs with or without
this pair, and the rows describe that text. There is no reverse allowance: the earlier definition forbids the
`architect-lens` skip a run may have taken on the current one, and its `test-design` text drops the skeleton-writer
dispatch for `update` entries. There is no transitive allowance: the intermediate definitions of those days have no
pair, and older build pairs do not chain to this one. Any further definition change fails closed until separately
reviewed.

## Review basis through adoption

The exact build and fix pairs permit upgrade only. Build `board-spec` and `code-review-board` and fix
`code-review` keep mandatory adoption, their canonical decision paths and completion policies. For unfinished
review, the commissioner keeps captured paths and pinned history write-free through adoption, writes records
outside them or in eligible predeclared exclusions, and observes the retained subject before adoption.
Adoption still checks subject currentness itself. Both close steps require the reviewed pair for a changed
semantic fingerprint. Step IDs, order, routes, completion predicates and variables are unchanged. Terminal
evidence remains historical, and pending obligations use the current instructions. State bytes and pauses stay
intact. Reverse and transitive mappings are unsupported.
