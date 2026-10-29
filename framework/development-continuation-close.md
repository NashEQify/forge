# Development continuation — checks, envelope and close

Step-loaded unit of `framework/development-continuation.md`. Read it when the adapter's task or plan checks run, when
an export changes the envelope or its owned handoff region, and when selected obligations are reconciled or closed.
It applies only to software work selected as that file defines.

## Check receipts

The adapter's required task and plan checks leave a run receipt on the binding they decide, in the shape of the
engine's [Run receipts](workflow-engine-receipts.md#run-receipts). It does not infer results from workflow
status, a completion method, truncated handoff text or the existence of a report; engine receipts reach it only
through exact selected-state export.

`bind` (including rebind), `reconcile`, `export` and `close` evaluate each distinct required check once per
invocation, shared by every binding that requires the identical definition. An accepted binding stores one
receipt for its required checks, in order:

```yaml
check_receipt:
  operation: bind
  at: "<UTC timestamp>"
  checks:
    - check: "task:<NNN>"
      type: task
      result: passed               # passed | failed | unknown
      producer: checker
      input: [{kind: file, path: "docs/tasks/archive/<NNN>.yaml", identity: {sha256: "<digest of the bytes read>"}}]
      detail: "passed"
```

A plan check also records its `command` and `exit_code` and is `partial: true`, because the validator reads more
than `docs/plan.yaml`. The adapter publishes the handoff once, at the end. A failed check leaves accepted expectations, compatibility baselines and closure
unchanged and is reported in the command's output; nothing is published for a rejected `bind`, `reconcile` or
`close`. An interrupted run publishes nothing. With no required check, no receipt is created; empty close stays
refused. Bindings closed under the earlier contract stay readable and untouched, without rerunning their checks.
`restore` is read-only and
returns its fresh results with `retention: not_persisted`; a caller that relies on them keeps the output at its
own evidence owner, and a prior exported success cannot substitute for a failed restore.

`close` uses the results of the same inspection that decides it: every required task/plan check must pass and
every selected workflow must be terminal. A verified close removes the binding from the envelope; its output returns
the `closed` record (reason, evidence, `verified_states`, `verified_checks` with their receipts), which the caller keeps
at its evidence owner, such as the commit that closes the work. The
receipt establishes the checked status/validation propositions on the recorded inputs; it does not establish
that every delivered behaviour was verified. Task-status reconciliation stays with the task owner.

Older envelopes may carry a top-level `check_observations` block, binding `check_observation_refs` and
`observation_ref` entries in closure receipts. The adapter reads and preserves them unchanged but neither
validates nor interprets them; a binding that is accepted again gets `check_receipt` and drops its
`check_observation_refs`.

## Legacy compatibility obligations

Old save and housekeeping definitions keep workflow/step IDs, routes, completion
checks, variables and evidence interpretation. For `validate-reconciliation`, retain
its unfinished task-status/plan checks when the legacy session selected development;
for `workflow-handoff-context`, restore/export exactly the selected authoritative
runs through this adapter. Missing legacy selection is an explicit blocker, never a
silent no-op. Existing checked evidence is not reset or reinterpreted by a new label.
Housekeeping area progress remains readable, while the shared publication journal
protects actual multi-file mutation.

Installation validates explicitly supplied project runs before activation and before
rollback, including state created/advanced after upgrade. Incompatible state keeps
sessions stopped until repair or validated mapping; no blanket state rewrite.

## Owned envelope region

The adapter owns exactly one LF-delimited ```` ```forge-development ```` fence in the
handoff; everything outside it belongs to the handoff's other writers. Observed
guarantees (`scripts/development_continuation.py` `_envelope`;
`tests/capabilities/test_owned_regions.py`):

- Create appends the fence after the existing text; replace swaps only the fence.
  Prose before and after it, including Unicode and CRLF line endings, is kept
  byte-for-byte. `restore` never writes; an unchanged envelope is a no-op.
- A second envelope, an unterminated or CRLF fence, any other line that opens a
  `forge-development` fence (backticks or tildes, indented or after `>`, a space
  before the info string, a variant name), an unsupported schema version or a
  binding of another project refuses before any write. The adapter never picks one
  region. A mention of the marker inside a line of prose is not a fence.
- Publication goes through `continuity.publish` against the whole handoff baseline.
  A concurrent correction anywhere in the file, inside or outside the fence, fails
  with `stale_baseline` (exit 3); the caller recaptures and reconciles semantically.
  A pending reconciliation naming the handoff blocks the adapter.

Limits: a verified close removes its binding. The last one removes the fence and leaves the text around it
byte-identical; when the envelope ends the file, it also takes back the one separator newline the adapter adds when
it creates the envelope (an envelope created before that rule may leave one newline). A removed binding ID can be
bound again as a new binding; a binding still carrying an earlier `closed` record cannot reopen.
Trailing spaces after the closing fence and a missing newline after it are
normalized, since they are part of the owned region. Advisory locking does not bind
nonparticipating writers. What an interrupted multi-file publication retains for
recovery, and its rollback limit: `framework/continuity.md` §Recovery without
stale replay.

## Reconcile and close selected obligations

A required task check has the stable identity `task:<numeric task ID>`; a plan
check has `plan:docs/plan.yaml`. Task archive relocation retains its identity and
must agree with the authoritative task file's `id`. Task statuses come from the
plan/task owner. Rebinding adds obligations; changing an existing expectation
requires explicit `reconcile`, which replaces that identity's expectation while
retaining every other obligation and records its prior value, reason and evidence.
It cannot remove an obligation or invent a successful task transition. Run the
owner's task-status process first, then submit the observed authoritative status:

```json
{"binding_id":"selected-work","reason":"Task owner completed and archived work",
 "evidence":"docs/tasks/archive/<NNN>.yaml",
 "required_checks":[{"kind":"task","path":"docs/tasks/archive/<NNN>.yaml",
                     "expected_status":"done"}]}
```

Use the same project/handoff CLI arguments with `reconcile`. Failed target checks
leave accepted expectations, compatibility baselines and closure unchanged; the
command output names the failing check. Other bindings retain their independent
status and work.

Task-only work remains unfinished until explicit `close` with `binding_id`,
`reason`, and `evidence`. Close evaluates every selected obligation once for its decision: workflows must
be terminal according to the engine; tasks must have an owner-recognized terminal
status; every required task/plan check must pass its supported predicate. Use that
same qualified result in the closure receipt. Failed or unknown required results
cannot pass merely because workflow/task terminality passed. Plan validity alone and an empty selection cannot prove completion.
Failed close preserves all obligations. A successful close removes the binding and returns its verified
receipt for the caller to keep at its evidence owner; if publication is interrupted, the error output still
carries that record. A binding closed under the earlier contract stays historical, and export/restore preserve
its receipt without reopening completed checks.

The engine exports `lifecycle: {status, terminal}` for each selected workflow
according to `workflow-engine-closure.md` §Mechanism-Lifecycle: local workflow
closure. Successful completion requires eligible terminal steps and authoritative
archived placement; an active completion record awaiting archival remains
nonterminal. Unresolved escalation is not successful completion and remains
nonterminal.

An authoritative abort is terminal even when untouched steps remain pending or a
prior pause flag remains set. It represents aborted work, not successful delivery,
and does not discharge task/plan checks. Archived identity must be unique across
active and archive storage even after a retained reference has relocated. Loading
and inspection never change pause, progress or archive placement. Explicit engine
`--next --id <workflow-id>` performs eligible local reconciliation; adapter
restore/export/close does not repair engine state.

## Definition compatibility

The engine fingerprints all loaded definition fields conservatively, including
manual instructions, completion checks, required flags, dependencies, commit gates,
iteration limits, skill/context references and unknown future fields. Only display
step names and top-level discovery/provenance metadata (`description`, `need_phrase`,
`trigger`, `derived_from`) are excluded; engine defaults normalize omitted values.
Schema and status validation remain independent of definition compatibility.

`continuation_compatible(workflow, observed_fingerprint, current_fingerprint,
direction=None)` accepts identical fingerprints or an exact reviewed transition in
`framework/workflow-compatibility.yaml`. Explicit `upgrade`/`rollback` restricts the
permitted direction; omitted direction infers it from the exact pair. The manifest
records workflow, prior/current hashes, allowed directions, acceptance and the
preserved-obligation review pointer. That pointer is review provenance, not a runtime
requirement to install private review documents. There is no name/step-count bypass.
The reviewed save/housekeeping pairs cover only their exact definitions;
any further instruction or execution change requires another reviewed transition.


## Creation-bound observational checks

Selected-work exports describe installed interpretation at observation time; they
do not establish an old run's creation definition. New workflows record the
semantic fingerprint of their actual supplied definition. Affected unfinished
save/solve/spec-board checks with absent/mismatched identity stop before progress:
preserve the run/history and reconcile unfinished obligations explicitly. There
is no automatic adoption or new import path. Existing unrelated compatibility
mappings and historical records retain their behavior. Manual action completion
requires newly supplied evidence and remains agent-confirmed; the engine does not
validate free-text outcome truth, freshness, completeness or remote reality.
