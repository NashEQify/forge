---
name: workflow-router
description: 'forge workflow router — Use when you need to: implement a feature or task; do periodic context-system maintenance; rewrite reader-facing docs / README / positioning; fix a bug or handle an incident; research, evaluate or spike; review or validate a spec; persist a session; solve a problem whose solution shape is still open; → open process-map.md and start via workflow_engine.'
status: active
invocation:
  primary: user-facing
disable-model-invocation: false
---

# Skill: workflow-router

<!-- generated-by: scripts/generate_workflow_router.py (do not hand-edit) -->

This is forge's workflow discovery router — one injected sign-post that points to the workflow runbooks. It carries no workflow methodology; the runbooks (`workflows/runbooks/<name>/WORKFLOW.md`) and `framework/process-map.md` are the SoT.

| Workflow | Use case | Runbook |
|---|---|---|
| `build` | implement a feature or task | `workflows/runbooks/build/WORKFLOW.md` |
| `context_housekeeping` | do periodic context-system maintenance | `workflows/runbooks/context_housekeeping/WORKFLOW.md` |
| `docs-rewrite` | rewrite reader-facing docs / README / positioning | `workflows/runbooks/docs-rewrite/WORKFLOW.md` |
| `fix` | fix a bug or handle an incident | `workflows/runbooks/fix/WORKFLOW.md` |
| `research` | research, evaluate or spike | `workflows/runbooks/research/WORKFLOW.md` |
| `review` | review or validate a spec | `workflows/runbooks/review/WORKFLOW.md` |
| `save` | persist a session | `workflows/runbooks/save/WORKFLOW.md` |
| `solve` | solve a problem whose solution shape is still open | `workflows/runbooks/solve/WORKFLOW.md` |

Match a need → open `framework/process-map.md` → start it: `python3 scripts/workflow_engine.py --start <name> --task <id>`
