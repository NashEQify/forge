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

## Parallel workflows (instance resolution + agent scope)

`.workflow-state/` is per-checkout, so two `cc` sessions (or a build + a fix) on
the same repo share it. The engine is instance-aware so a parallel workflow's
files never bleed into the wrong place:

- **Resolution refuses, never guesses.** With >=2 workflows live and no
  `--id`/`--task`, `--next` / `--complete` / `--skip` / `--retry` / `--pause`
  exit `5` (`EXIT_AMBIGUOUS`) with a copy-paste `--id` candidate list, instead of
  silently picking first-match / most-recent-leaf (the solve-593-vs-594 silent
  wrong-instance bug). Pass `--id <wf>` (the `ID:` line `--next` prints) or
  `--task <id>`. A single live workflow resolves with no key (fast-path).
- **Agent scope rides `--next`.** When a sibling workflow is live, `--next` adds
  a `SCOPE:` line (this instance's own files) + a `NOT-YOURS:` line (the sibling
  files to ignore). When Buddy dispatches an agent inside a workflow step, that
  block goes into the brief (`mca-brief-template.md` / `fix-brief-template.md`
  §Workflow scope) so the agent never reconstructs "which files are mine" by
  browsing `docs/<workflow>/` — the failure that let solve-593's agent trip over
  solve-594's files.
- **Stale workflows are reapable.** Abandoned workflows (left `in_progress` for
  days) pollute `list_active_states()` and the agent's perception, and force an
  ambiguity refusal next to a genuinely-live one. `--reap` archives any active
  workflow idle past the threshold (default 7d, floor 1h; `--dry-run` to preview;
  paused never reaped). It re-reads + re-checks each candidate immediately before
  acting — a workflow advanced since the scan is left alone — and only ARCHIVES
  (reversible from `.workflow-state/archive/`), never deletes. Idleness is a
  heuristic on step transitions, not a liveness heartbeat; fit for
  `context_housekeeping`.

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
Command checks use exit `0` for pass and `1` for a valid negative; other exits,
timeouts and I/O failures are evaluation errors. Unreadable glob directories
also fail evaluation instead of being treated as empty results.
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

## Completion provenance

Manual completion remains an explicit agent confirmation. `--complete` accepts
it, retains `status: complete`, and records `completion_method: agent-confirmed`.
The completion response and `--status` say `agent-confirmed (not verified)`.
The same applies to an omitted completion check or a compound containing a
manual check. Evidence text is retained, but does not itself prove verification.

Successful mechanical checks record `completion_method: verified`, including
deterministic steps automatically completed by `--next`. This means the defined
check passed, not that every property of the work was verified. Legacy pointer
checks accepted without a current evidence schema record `legacy-unverified`.

The existing bounded `--force` override remains available for completion checks;
it records `forced (not verified)` alongside the existing force counter and
`force_completed` flag. It cannot override guard errors. Retry clears the prior
completion method. State schema version `2` and existing statuses are unchanged;
older states without this additive field still load and are not retroactively
labeled verified.

## Recovery

`--recover` evaluates guards before recovering active steps. A guard error exits
`6`; a valid nonapplicable guard leaves the step alone for `--next` to handle.
Manual checks, including compounds containing a manual check, remain active
until explicit `--complete` confirmation.

Successful mechanical recovery records the completion method and the actual
check result in evidence and displays the method in the recovery response.
Completion evaluation errors exit `1` without completing the step. Legacy
pointer checks retain their `legacy-unverified` provenance.

## `--complete` idempotence

Repeated `--complete <id>` on an already complete step → exit 1.
When in doubt: read `--status` or check `--next`.

## Boot integration

Boot step `WORKFLOW-RESUME` reads active workflows automatically
(`--boot-context`). Buddy reads workflow state on demand via `--next` /
`--status` / `--boot-context` when relevant, rather than every turn. Session-handoff
carries continuity across sessions; the engine state-file is read when
Buddy actively returns to an in-flight workflow.

## Extension API — `--guard` / `--handoff-context`

`--start` / `--next` / `--complete` / `--skip` / `--retry` are the generic
cycle every workflow uses. Two **named, stable extension commands** sit
alongside them — a sanctioned contract (ADR-007 O-4), not per-workflow
ad-hoc special-casing:

**`--guard <name> [<task_id>]`** — a named guard predicate referenced from a
step's `guard:` block (`type: script`, `command: "… --guard <name> {task_id}"`).
Exit `0` means applicable; exit `1` is a successfully evaluated, legitimate
negative and skips the step. Every other exit code, a missing program, timeout,
I/O failure, unresolved input, or unknown guard type/name is an evaluation error.
It leaves the required step incomplete and does not advance to later steps.
Named guard errors return exit `6`; `--start` and `--next` report guard errors
with exit `6`, while rejected `--complete` and `--skip` return exit `1`.
Correct the error and retry; required steps cannot use `--skip` to bypass it.

For Python callers, `evaluate_guard` retains its two-item result:
`(True, reason)` means applicable, `(False, reason)` means nonapplicable, and
`(None, reason)` means error. Consumers must distinguish `is False` from
`is None`. `find_next_step` raises `GuardEvaluationError` on evaluation errors.
File guards support repo-relative globs (including `**`) and report unreadable
directories as errors. Missing files remain valid negative results.

Named guards today (both require a positive task ID):

| Guard | Returns 0 (proceed) when |
|---|---|
| `council-needed` | the task's discovered workflow state file carries `council-required: true` or `council_required: true`; discovery uses the engine's workflow directories and task-reference/legacy filename rules |
| `task-yaml-ok` | `docs/tasks/<id>.yaml` exists |

**Retired:** `delta-needed` — removed (its trigger was a judgment the engine
cannot compute; see the design rule below). It has no `cmd_guard` branch now,
so referencing `--guard delta-needed` reports "Unknown guard" with exit `6`
and blocks advancement. No `workflow.yaml` references it.

Adding a guard: add a branch in `cmd_guard` + reference it from the step's
`guard:` block. **Design rule (the `delta-needed` retirement lesson):** a
guard whose trigger is a *judgment* the engine cannot compute (e.g. "≥1 MAJOR
finding fixed") must NOT be a bare predicate — make it an **opt-in marker**
the guard greps (like `council-needed`), or drop the guard and let Buddy
`--skip` / `--complete` a `required: false` step by judgment. A guard that
always `sys.exit(1)` is a dead surface masquerading as a gate, not enforcement.

**`--handoff-context`** — emits a text block of every active workflow state
(workflow, id, task, current step + instruction, progress) for embedding in
the session-handoff. Consumed by `save`; the boot-side counterpart is
`--boot-context` (cross-session resume, surfaced at session start).

`skip_when` is NOT part of this API: it stays a Buddy-applied `[DISCIPLINE]`
predicate the engine does not evaluate (`framework/enforcement-registry.md`).

## Skip allowed for

- `build` DIRECT path, per [central DIRECT eligibility](process-map.md#direct-eligibility).
  Apply its risk exclusions first. Bounded, reversible new local behavior is
  allowed when all central criteria hold; file and line counts are warning
  signals, not eligibility rules.
- `save` / `checkpoint` / `wakeup` / `sleep`
  (lifecycle commands without long continuity)
- `context_housekeeping` (ad hoc, no multi-session state)
- `frame` / `bedrock_drill` standalone (sub-skills, not standalone
  workflows)
- `think!` (stance change, not a workflow)

## Concurrency

New `workflow_id` values retain their descriptive timestamp prefix and add a
full UUID suffix. Restarting the same workflow/task uses a distinct identity
even when the clock is unchanged, so matching revision numbers cannot let an
old transition modify or archive the replacement run. Existing IDs and state
files remain unchanged; resolution by `--id` or `--task` still works for them.

Publishing a new run rechecks the active `(workflow, task_id)` pair while holding
the same lock used to write its state. Concurrent starts for the same pair
produce one active run; the losing start exits `1` and names the existing run.
This includes workflows without a task ID. Different workflow/task pairs remain
allowed, and archived runs do not block a restart.

State writes compare the snapshot's `revision` with the persisted revision
under the same lock used for replacement, then increment it. Legacy states
without this optional field start at revision `0`; schema version `2` remains
unchanged. Completion, abort and reap also check the revision when archiving,
so a concurrent retry cannot be archived by an older transition.

A stale write or archive raises `StaleStateError` and interactive commands exit
`7` with a reload-and-retry diagnostic. Reload before rerunning the operation;
the engine does not automatically replay checks or overwrite newer evidence.
The maintenance reap sweep reports a conflicting instance and continues with
other candidates.

- **Read-only sub-skills** (research, board reviewers, multi-architect
  brief authoring, source-grounding lookups, code reviewers): dispatch
  in parallel freely. Multiple Agent-tool calls in a single message
  fire concurrently.
- **Write-touching steps** (`mca-implementation`, `fix-execute`,
  spec-text-drift-batch on overlapping files): serialize per file
  scope. Two MCA dispatches on disjoint scopes can run in parallel;
  on overlapping scope they must serialize.
- **Verification** can run alongside implementation when the verifier
  reads disjoint file areas. On the same file area: verify after
  implementation completes.

Pattern is implicit in workflow.yaml step structure — this section
documents the rule so deviation is recognizable.

## Multi-machine constraint (CRITICAL)

`.workflow-state/` is `.gitignored` — per repo checkout, not synced
across the repo. **A workflow belongs to ONE hostname per repo.**

Working on the same repo across two machines:
- DON'T run the same workflow active in parallel on both machines.
- Switching from machine A to B: either `--abort` on A, or wait for
  the workflow to finish. Otherwise state diverges with concurrent
  writes to `docs/<workflow>/<slug>.md` (git-committed) — merge
  conflicts or lost-update.
- On `--start`, Buddy MUST warn the user when `docs/<workflow>/`
  files with a matching `parent_task` exist but there's no local
  `.workflow-state/<id>.json` — that's the classic multi-machine
  symptom.

## Cross-repo scope

The engine works per `BUDDY_PROJECT_ROOT` (default `$CWD`).
`.workflow-state/` is project-relative. When `cc <consumer>` is
invoked, `BUDDY_PROJECT_ROOT=$CWD` must be set so the engine finds
the right state. Workflows in the framework repo and in consumer
repos are separate — there is no cross-repo view.
