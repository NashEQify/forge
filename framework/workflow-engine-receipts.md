# Workflow engine — completion provenance, run receipts and observational checks

Step-loaded unit of `framework/workflow-engine-cookbook.md`. Read it when a completion check or gate runs or
is read back, when its receipt or provenance is written or consumed, and for observational checks and explicit
action completion.

## Completion provenance

Manual completion remains explicit agent confirmation. An omitted completion check is an implicit manual component. The existing `status: complete` vocabulary and aggregate `completion_method` remain compatible:

- A completion containing manual confirmation is `agent-confirmed`.
- A permitted forced completion is `forced`.
- A legacy pointer check accepted without current schema qualification remains `legacy-unverified`.
- `verified` means the supported mechanical completion predicates passed. It does not mean every property of the work was verified.

Manual, forced and legacy qualifications are displayed as not verified. Retained evidence text is an assertion or evidence locator; its presence does not prove execution.

The existing bounded `--force` override remains available except for completion
trees containing `brief_check`, which refuse force even for valid artifacts.
Mandatory review checks always run and refuse advancement when unqualified;
force retains the existing force counter and `force_completed` flag. It cannot
override recursive structure, guards, creation-bound interpretation or required
invocation evidence. Retry clears the current aggregate completion method and moves
the step's receipts into its retry history. State schema version `2` and existing
statuses remain unchanged.

The receipt's components determine the qualification. Do not infer component results from message substrings, an aggregate method, a task status or a model-authored JSON object. Historical aggregates remain readable without fabricated components.

## Run receipts

A transition that a completion check decides carries a plain run receipt on its step: what was checked, on
which input bytes, with which result, by which producer. An agent cannot certify its own execution, so the
engine records these exact facts; whether the work is good stays Buddy's judgement. The development adapter
keeps the same receipt per binding (`development-continuation.md`). There is no attempt log, receipt store
or action runner. A receipt does not record which change a review seat saw: the review package's range, named in the
persisted review, does (`skills/code_review_board/review-package.md` §The record).

### Record shape

Each transition (`complete`, `auto_complete`, `recover`, including an `on_fail` disposition) sets the step's
`receipt`; a step transitions at most once per iteration:

```yaml
receipt:
  operation: complete
  at: "<UTC timestamp>"
  iteration: 1
  checks:
    - check: "<step ID>:completion.0"     # step plus completion-tree path; ".input" for an input failure
      type: file_content_check
      result: passed                       # passed | failed | not_evaluated
      producer: checker                    # checker | agent | forced | legacy
      input:
        - {kind: file, path: "<project-relative path>", identity: {sha256: "<digest of the bytes used>"}}
      detail: "<evaluator message, at most 300 characters>"
```

- `checker`: a supported evaluator ran. `agent`: a manual check, an assertion. `forced`: an ordinary leaf skipped
  by permitted force (`not_evaluated`). `legacy`: a pointer check accepted under the legacy schema without the
  current predicate (`not_evaluated`). Children after a failing compound child are `not_evaluated`.
- `input` lists the view the evaluator actually consumed: file digests, timestamp baselines, matched patterns,
  predicate inputs. A digest describes the bytes used, not a later read. A review-backed check records one
  `kind: review` entry with owner, run, subject digest, decision and decision sha256. `partial: true` marks a
  check whose evaluator could not identify all of its input (pointer targets, predicate helpers).
- Mandatory review prechecks add `precheck: true`; under force they still run before the bypassed leaves.

`completion_method` derives from the receipt: `forced` when forced; else `agent-confirmed` if any check is
`agent`; else `legacy-unverified` if any is `legacy`; else `verified`.

### Writing and refusals

The engine evaluates in memory and saves state once, together with the transition and its receipt. A refused
completion (a failed check under `on_fail: block`, an evaluation error, a guard) writes nothing; the response
names each evaluated component and its result, and an evaluation error keeps the `Completion evaluation error:`
prefix. An interrupted process writes nothing, so the step stays where it was. Recovery promotes steps that
pass before a later evaluation error and still reports the error. Retry moves the step's receipt into its
retry-history entry; route children reset by a classification retry lose theirs.

### Reading and limits

`--status` shows the receipt of each terminal step. Boot and handoff context show steps and methods only. A receipt
establishes its predicate at the time it ran; status does not re-run it, and later progression evaluates
current inputs again. `--status` and the read-only `restore` (`stale_inputs`) mark a recorded file input
` stale` when its bytes changed since the check and ` missing` when it is absent or not a regular file.
`stale` means the input changed, not that the check would now fail; inputs recorded without a content hash
(`file_created_matching`, `file_modified_after`) carry no marker. A predicate can establish a bounded fact beyond exit status (a command that exits zero
without the promised artifact cannot satisfy an artifact check); it cannot establish broader correctness,
remote reality or earlier execution. Read-only evaluators (`--review-check`, adapter `restore`) return their
result with `retention: not_persisted`; a caller that relies on it keeps the output at its own evidence owner.

Older state may contain a top-level `check_observations` block. The engine loads it, never
rewrites it, and `--status` reports it in one line; its attempts are not interpreted. States without receipts
are aggregate-only history: no components are inferred.

### Mechanism-Lifecycle: run receipts

**Owner:** the workflow engine (step receipts) and the development adapter (binding receipts).
**Carrier:** the step's `receipt` and the binding's `check_receipt`, written in the same save as the
transition they describe. **Outside this model:** action execution, crash atomicity between a check and an
external effect, replay.

| Operation | No receipt yet | Receipts present |
|---|---|---|
| Transition decided by checks | Set the receipt with the transition, one save | Not reachable: a terminal step does not transition again before retry |
| Refused completion or interruption | No write | No write |
| Retry or route reset | No receipt | Retry moves the receipt into the retry-history entry; a reset route child drops it |
| Read (`--status`, export) | Aggregate method only | Show the receipt; no rescan |
| Legacy `check_observations` present | Load, report, never rewrite | Same |
| Parent step completed by child-workflow propagation | No check runs, so no receipt; not reachable today (no live definition uses a child workflow) | Same |

Invariants: the producer that ran the check writes its receipt (`ProducerOwnsReceipt`); a receipt never precedes
or outlives its transition (`OneWritePerTransition`); reading never executes (`ReadDoesNotExecute`).

## Observational checks and explicit action completion

Inspection never executes completion/guard commands. Legacy `exit_code`
completions and script guards are unsupported, including nested compounds and
force paths. Recursive structural preflight precedes child evaluation. Unsupported,
malformed or unavailable evaluation is an error, not a negative that `on_fail`
may advance. Plan script gates refuse before the `preliminary` shortcut.

Action steps use `completion: {type: manual}` and a typed step-level
`evidence_required: true`. Such steps never auto-complete during navigation or
recovery. Explicit completion requires nonblank `--evidence` in that invocation,
including `--force`; old retained step evidence is insufficient. Unflagged steps
retain existing behavior. Ordinary completion stays `agent-confirmed (not verified)`;
force stays `forced (not verified)` and still obeys lifecycle/force limits.

```sh
# Use existing authorized tools, then observe the actual intended outcome.
python3 "$FRAMEWORK_DIR/scripts/workflow_engine.py" --complete STEP --id WORKFLOW --evidence "Current observations and retained evidence"
```

Before completing push, observe the intended repository/ref/current revision.
Before completing deployment, observe the intended release and a meaningful
service result. Before completing save, observe current content persistence for
all applicable project/user repositories and required remote persistence; a
no-new-commit save still needs current observations. Failed, timed-out, unknown or
missing outcomes remain open with the concrete blocker. These outcome judgments
are agent obligations: the engine enforces evidence presence and qualification,
not the truth, semantic freshness or completeness of free text. It adds no action
runner, remote verifier, new routine approval or publication authorization.

`named_predicate` observes `council-needed` and `task-yaml-ok` directly, preserving
the explicit council marker and active task-YAML existence meanings. Completion-only
`task-status-done` validates task identity and done status in active/archive YAML;
malformed, conflicting or unavailable data is an error. Predicates never execute
subprocesses or take ownership of task-status writes.

New runs store the semantic fingerprint of their supplied definition in
`definition_fingerprint`. Affected unfinished save/solve/spec-board checks require
exactly matching creation-bound interpretation before progress. Missing/mismatched
identity stops without losing progress/history: preserve the run and reconcile its
unfinished obligations explicitly. An installed definition or old export cannot
establish creation provenance. There is no automatic migration/import path.
Terminal history and unrelated workflows retain existing behavior; unrelated
continuation compatibility mappings remain unchanged.
