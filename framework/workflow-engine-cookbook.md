# Workflow Engine — CLI Cookbook

Tier-2 reference for `scripts/workflow_engine.py`. Operational invariants
live in `agents/buddy/operational.md` §Workflow engine; the CLI surface,
path routing, step patterns, and multi-machine warnings live here.

## Step-loop

```bash
# 1. Start (default route is "standard" if workflow.yaml has top-level routes)
python3 $FRAMEWORK_DIR/scripts/workflow_engine.py --start <name> --task <id>

# 1a. With explicit path-route (build/sub-build, build/full):
python3 $FRAMEWORK_DIR/scripts/workflow_engine.py --start <name> --task <id> --route <path>

# 2. Step-loop until everything is done. With >=2 workflows live in the checkout
#    the engine REFUSES a keyless --next/--complete/--skip/--retry/--pause
#    (exit 5 EXIT_AMBIGUOUS) + prints a copy-paste --id list. Pass --id <wf>
#    (the `ID:` line from --next) or --task <id>. Single workflow: key optional.
while WF_HAS_PENDING; do
  python3 $FRAMEWORK_DIR/scripts/workflow_engine.py --next [--id <wf>]   # current step + instruction (+ SCOPE/NOT-YOURS when siblings live)
  # → Buddy executes the instruction (call skill_ref, write content, etc.)
  python3 $FRAMEWORK_DIR/scripts/workflow_engine.py --complete <step-id> [--id <wf>] --evidence "<short>"
  # For classification steps (mid-flow): --complete --route <key>
  # For skip-eligible: --skip <step-id> [--id <wf>] --reason "<why>"
  # For re-iteration (step has to run again): --retry <step-id> [--id <wf>] --reason "<why>"
  # Iteration cap defaults to 3, override via --reason "override: <rationale>"
done

# Status / recovery / debug:
python3 $FRAMEWORK_DIR/scripts/workflow_engine.py --status            # all active workflows
python3 $FRAMEWORK_DIR/scripts/workflow_engine.py --recover           # after a crash
python3 $FRAMEWORK_DIR/scripts/workflow_engine.py --pause / --resume
python3 $FRAMEWORK_DIR/scripts/workflow_engine.py --abort <wf-id> --reason "..."
python3 $FRAMEWORK_DIR/scripts/workflow_engine.py --reap [--max-age-hours N] [--dry-run]
#   --reap archives long-idle stale workflows (default > 168h / 7d; paused never reaped)
```

## Review capture and brief binding

When a workflow step runs or adopts a mandatory software review, and when a build brief is bound or legacy work is
adopted: read and follow `framework/workflow-engine-review-and-brief.md` (§Mandatory software-review capture and
adoption, §Build brief binding and legacy adoption).

## Parallel workflows, extension API and concurrency

When more than one workflow instance is active, when `--guard` or `--handoff-context` is used, and when another
session, machine or repository may touch the same state: read and follow `framework/workflow-engine-parallel.md`
(§Parallel workflows, §Extension API, §Concurrency, §Multi-machine constraint, §Cross-repo scope).

## Path routing

If the workflow has a top-level `routes:` block, the route is picked at
`--start` (eager). Steps in OTHER routes but NOT in the selected one
are eagerly marked `STATUS_ROUTE_SKIPPED`. Default without `--route`:
`"standard"`.

**Limit — top-level routes are NOT re-routable mid-flow.** A top-level
route is fixed at `--start` (it IS stored at state-root as
`selected_route`, but there is no `--complete --route` re-selection and
no re-pristine for it). If a top-level route turns out wrong after
`--start` (e.g. `build --route authority-only` but the work needs
code), the path is `--abort` + re-`--start` with the right route — not
an in-flight switch. Only **classification routes** (`--complete <step>
--route <key>`) re-route mid-flow and re-pristine prior-route children
on retry. This asymmetry is accepted (no live trigger needs in-flight
top-level re-routing); absorbing top-level routes into the
classification primitive is a deferred option, not done.

| Workflow | Routes | Default | Use-case |
|---|---|---|---|
| `build` | standard, full, sub-build | standard | sub-build = nested on an existing locked spec (skips interview/spec-write/board + task-status-done) |
| `fix` | standard, full, sub-fix | standard | sub-fix = nested in a parent build (skips task-status-done — the parent owns task-level status) |
| `solve` / `research` / `docs-rewrite` | (no top-level routes) | n/a | nested-iteration use-case not yet confirmed |
| `spec_board` | classification-step routes (standard/deep) | mid-flow | choose mid-workflow via `--complete classify --route deep` |

## Workflow step patterns

- `phase-done` step (deterministic, on_fail: block) — marks ONLY this
  workflow iteration as done via `task_status_update workflow_phase=done`.
  Universal step (in no route — runs in all paths).
- `task-status-done` step (deterministic, required: false, on_fail:
  warn) — sets task-level `status=done`. ONLY in standard/full
  routes; sub-build/sub-fix routes skip mechanically.
- `spec-co-evolve-check` step (content, required: false, on_fail:
  warn) — post-implementation check: did the commit change
  spec-defined behavior? If yes → spec patch in the SAME block-commit.

## Completion checks and `on_fail`

Unresolved `{variable}` inputs fail completion, including inside compound
checks. Supply the missing value with `--set <key> <value>` or create the
expected artifact before retrying. Empty variable values remain unresolved;
numeric regex quantifiers such as `{3}` are not variables. A missing pointer
validator also fails evaluation. These errors return CLI exit `1`, leave the
step incomplete, and do not invoke `on_fail` or become automatic completion.
Legacy command completions remain unsupported. Supported validators distinguish
a valid negative from unavailable, malformed or erroneous evaluation. The pointer
validator uses exit `0` for its supported passing predicate, `1` for a valid negative
and other exits for evaluation errors. An exit code establishes only that validator's
predicate, not unrelated artifact behavior or command history. Unreadable glob
directories fail evaluation instead of being treated as empty results.

A transition records its components in a [run receipt](workflow-engine-receipts.md#run-receipts); a refused
completion writes nothing and names the failing component in its response. `on_fail`
changes only the permitted step disposition; it never changes a check's recorded result.
Pointer validator exit `2` and raised parse/internal errors likewise fail
evaluation; only exit `1` is a valid negative eligible for `on_fail`.

Compound preflight checks all external inputs before execution, including those
after a check that may return negative. A preceding `file_created_matching`
check can supply `{artifact_path}` to later checks. Each child resolves its
inputs after earlier children execute, so consumers use the producer's current
output. A reference before its producer remains an unresolved-input error.

`on_fail` applies to a check that successfully evaluates to a negative result:

| `on_fail` | Buddy reaction |
|---|---|
| `block` | Step stays `in_progress`; Buddy MUST fix and retry `--complete` |
| `warn` | Step becomes `warn_skipped`; output includes the failed check |
| `skip` | Step becomes `skipped` |
| `escalate` | Step becomes `escalated`; output requests user action |

## Mechanism-Lifecycle: local workflow closure

When a workflow that owns a mechanism lifecycle reaches its close step or a mechanism-lifecycle check fires: read
and follow `framework/workflow-engine-closure.md`.

## Completion provenance, run receipts and observational checks

When a completion check or gate runs or is read back, when its receipt or provenance is written or consumed, and for
observational checks: read and follow `framework/workflow-engine-receipts.md` (§Completion provenance, §Run
receipts, §Observational checks and explicit action completion).

## Recovery

`--recover` evaluates guards before recovering active steps. A guard error exits
`6`; a valid nonapplicable guard leaves the step alone for `--next` to handle.
Manual checks, including compounds containing a manual check, remain active
until explicit `--complete` confirmation.

Successful mechanical recovery records the completion method and the actual
check result in evidence and displays the method in the recovery response.
Completion evaluation errors exit `1` without completing the step. Legacy
pointer checks retain their `legacy-unverified` provenance.

Recovery also applies the local closure contract (`workflow-engine-closure.md`) when permitted mechanical
recovery exhausts the run or the selected active run is already eligible-terminal.
It preserves manual confirmation and fresh-evidence requirements. Paused or aborted
runs are not progressed. Use explicit `--next --id <workflow-id>` to reconcile a
known all-terminal local run or retry interrupted archival.

Each recovered step gets a run receipt (`operation: recover`). Steps that pass
before a later evaluation error stay recovered; the erroring step stays unfinished
and the error is reported. Evidence-required actions retain their existing
explicit-completion requirement. Recovery evaluates afresh and never reconstructs
earlier execution. Eligible local closure or archival reconciliation does not rerun
checks or replace receipt timestamps.

## `--complete` idempotence

Repeated `--complete <id>` on an already complete step → exit 1. Reconciliation
uses `--next --id <workflow-id>` and does not rewrite completed or skipped steps.
Repeating it after successful archival performs no work.
When in doubt: read `--status` or check `--next`.

## Boot integration

Boot runs neither `plan_engine.py --boot` nor `--boot-context`: `plan_engine.py
--boot` runs when a task is taken up (`agents/buddy/operational.md` §Phase 1,
`skills/task_status_update/SKILL.md` Step 1b), and the read-only `restore` runs before selected work progresses
(`framework/development-continuation.md`).
Buddy reads workflow state on demand via `--next` /
`--status` / `--boot-context` when relevant, rather than every turn. Session-handoff
carries continuity across sessions; the engine state-file is read when
Buddy actively returns to an in-flight workflow.

## Skip allowed for

- `build` DIRECT path, per [central DIRECT eligibility](direct-eligibility.md#direct-eligibility).
  Apply its risk exclusions first. Bounded, reversible new local behavior is
  allowed when all central criteria hold; file and line counts are warning
  signals, not eligibility rules.
- `save` / `checkpoint` / `wakeup` / `sleep`
  (lifecycle commands without long continuity)
- `context_housekeeping` (ad hoc, no multi-session state)
- `frame` / `bedrock_drill` standalone (sub-skills, not standalone
  workflows)
- `think!` (stance change, not a workflow)
