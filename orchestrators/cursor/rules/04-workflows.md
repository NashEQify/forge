---
description: Workflow runbooks + commands under Cursor
---

Read and follow `framework/work-principle.md` before taking up work.
Resolve this reference against the framework root; retain the consumer CWD.


# Workflows

8 active workflows under `workflows/runbooks/<name>/WORKFLOW.md`.
Routing-table: `framework/process-map.md`.

Resolve the workflow selection first (`framework/workflow-selection.md`). These automatic workflow triggers
apply to `software`; in `on-demand`, use Forge methods on explicit user request.

| Workflow | Trigger |
|---|---|
| `solve` | Problem with open solution-form |
| `build` | Implement feature/task (DIRECT/STANDARD/FULL paths) |
| `fix` | Bug/incident, root-cause-first |
| `review` | Spec(s) review, no code |
| `research` | Spike, SOTA, evaluation |
| `docs-rewrite` | Architecture-doc rewrite, reader-journey-first |
| `save` | End-of-session persistence |
| `context_housekeeping` | Periodic context-system maintenance |

## Invocation

Workflows are followed by Buddy (you). Read the relevant
`workflows/runbooks/<name>/WORKFLOW.md` and execute its phase
sequence. Each phase has Skills, Input, Output, Gate, Failure-Behavior,
Autonomy, Protocols.

For Producer-class workflows (build/fix/review/solve): 5 phases —
Specify → Prepare → Execute → Verify → Close.

## Triggers (natural-language)

| User says | Buddy interprets as |
|---|---|
| "save" | save-Workflow (mid + end of session) |
| "wakeup" | session-continuity boot |
| "checkpoint" | save with deeper drift-check |
| "think!" | THINK-Stance (`agents/buddy/think-operational.md`) |
| "sleep" | forget session |
| "consistency check" | invoke `consistency_check` skill |
| "task <X>" | task-status-update / context-load |

## Workflow-Engine (advanced)

For long-running workflows with explicit state:
```bash
python3 $FRAMEWORK_DIR/scripts/workflow_engine.py --start <wf> --task <id>
python3 $FRAMEWORK_DIR/scripts/workflow_engine.py --next --id <wf-id>
python3 $FRAMEWORK_DIR/scripts/workflow_engine.py --complete <step>
```

Under Cursor, run via terminal-integration. State-file lives under
`docs/<wf>/<date>-<slug>.md`.

## Pre-Commit Hook (mandatory)

Shared Git checks run at applicable commits when installed in that repository.
The current six check families and their BLOCK/WARN behavior are defined in
`framework/enforcement-registry.md` and implemented in
`orchestrators/claude-code/hooks/pre-commit.sh`. Commit-msg owns commit-message
blocking; coverage depends on applicable inputs and available tools. The hook
does not prove that Cursor loaded Forge instructions or intercept each write.

Install:
```bash
bash "$FRAMEWORK_DIR/scripts/install-git-hooks.sh"
```

The shared hook source lives under `claude-code/`; Git invokes it independently
of the editor where installed. Changes to Forge's sources follow `framework/installation-activation.md`.
`scripts/install-git-hooks.sh` links `pre-commit`, `pre-merge-commit` and
`commit-msg` per repository; its checks do not establish host parity.
