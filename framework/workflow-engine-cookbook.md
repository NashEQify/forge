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

## `on_fail` policy reaction

| `on_fail` | Buddy reaction |
|---|---|
| `block` | Step stays `in_progress`; Buddy MUST fix and retry `--complete` |
| `warn` | Step stays `in_progress`; Buddy may `--complete --force` with a reason |
| `skip` | Step automatically `warn_skipped`, engine advances |
| `escalate` | Step → `escalated`, workflow pauses, user decision required |

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
Exit `0` → the step proceeds; exit `≠0` → the step is skipped (see
`evaluate_guard`). Named guards today:

| Guard | Returns 0 (proceed) when |
|---|---|
| `council-needed` | the **solve** state file (`docs/solve/*.md`) carries the opt-in marker `council-required: true` (Buddy writes it when frame's >1-path + hard-to-reverse criteria fire). NOTE: greps `docs/solve/` only — solve-scoped today |
| `task-yaml-ok` | `docs/tasks/<id>.yaml` exists |

**Retired:** `delta-needed` — removed (its trigger was a judgment the engine
cannot compute; see the design rule below). It has no `cmd_guard` branch now,
so referencing `--guard delta-needed` falls to "Unknown guard" → exit ≠0 (the
step is skipped, fail-safe). No `workflow.yaml` references it.

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

- `build` DIRECT path (≤3 files, no spec, no new behavior)
- `save` / `checkpoint` / `wakeup` / `sleep`
  (lifecycle commands without long continuity)
- `context_housekeeping` (ad hoc, no multi-session state)
- `frame` / `bedrock_drill` standalone (sub-skills, not standalone
  workflows)
- `think!` (stance change, not a workflow)

## Concurrency

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
