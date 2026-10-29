# Workflow engine — parallel workflows, extension API and concurrency

Step-loaded unit of `framework/workflow-engine-cookbook.md`. Read it when more than one workflow instance is
active, when a guard or handoff context is used, and when another session, machine or repository may touch the same
state.

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

## Extension API — `--guard` / `--handoff-context`

`--start` / `--next` / `--complete` / `--skip` / `--retry` are the generic
cycle every workflow uses. Two **named, stable extension commands** sit
alongside them — a sanctioned contract (ADR-007 O-4), not per-workflow
ad-hoc special-casing:

**`--guard <name> [<task_id>]`** — a named guard predicate referenced from a
step's `guard:` block (`type: named_predicate`, `name: council-needed`,
`task_id: "{task_id}"`). YAML observes the predicate directly without executing
the standalone CLI. Existing standalone named-guard callers remain supported.
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
`--boot-context` (on-demand resume view; boot itself does not run it).

`skip_when` is NOT part of this API: it stays a Buddy-applied `[DISCIPLINE]`
predicate the engine does not evaluate (`framework/enforcement-registry.md`).

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
