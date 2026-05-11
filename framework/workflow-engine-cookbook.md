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

# 2. Step-loop until everything is done:
while WF_HAS_PENDING; do
  python3 $FRAMEWORK_DIR/scripts/workflow_engine.py --next     # shows current step + instruction
  # → Buddy executes the instruction (call skill_ref, write content, etc.)
  python3 $FRAMEWORK_DIR/scripts/workflow_engine.py --complete <step-id> --evidence "<short>"
  # For classification steps (mid-flow): --complete --route <key>
  # For skip-eligible: --skip <step-id> --reason "<why>"
  # For re-iteration (step has to run again): --retry <step-id> --reason "<why>"
  # Iteration cap defaults to 3, override via --reason "override: <rationale>"
done

# Status / recovery / debug:
python3 $FRAMEWORK_DIR/scripts/workflow_engine.py --status            # all active workflows
python3 $FRAMEWORK_DIR/scripts/workflow_engine.py --recover           # after a crash
python3 $FRAMEWORK_DIR/scripts/workflow_engine.py --pause / --resume
python3 $FRAMEWORK_DIR/scripts/workflow_engine.py --abort <wf-id> --reason "..."
```

## Path routing

If the workflow has a top-level `routes:` block, the route is picked at
`--start` (eager). Steps in OTHER routes but NOT in the selected one
are eagerly marked `STATUS_ROUTE_SKIPPED`. Default without `--route`:
`"standard"`.

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
(`--boot-context`). UserPromptSubmit hook `workflow-reminder.sh`
injects the current step into every turn context.

## Skip allowed for

- `build` DIRECT path (≤3 files, no spec, no new behavior)
- `save` / `quicksave` / `checkpoint` / `wakeup` / `sleep`
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
