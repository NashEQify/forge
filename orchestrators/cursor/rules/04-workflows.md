---
description: Workflow runbooks + commands under Cursor
---

# Workflows

8 active workflows under `workflows/runbooks/<name>/WORKFLOW.md`.
Routing-table: `framework/process-map.md`.

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
| "save" / "quicksave" | save-Workflow |
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

12 checks at git-commit time. Even under Cursor (no PreToolUse-Hook), this
runs at every commit and is the primary quality gate:
- BLOCK: PLAN-VALIDATE, CG-CONV, SKILL-FM-VALIDATE
- WARN: TASK-SYNC, OBLIGATIONS, STALE-CLEANUP, PERSIST-GATE

Install:
```bash
ln -sf "$FRAMEWORK_DIR/orchestrators/claude-code/hooks/pre-commit.sh" \
       .git/hooks/pre-commit
```

(The hook lives under `claude-code/` historically, but it's harness-agnostic
— pure bash + git, no Claude-Code specifics. Same hook for all adapters.)
