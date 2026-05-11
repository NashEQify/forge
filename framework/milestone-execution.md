# Milestone Execution

Multi-task orchestration: how multiple tasks combine into a verifiable
milestone-done state. Per-task flows (Direct/Standard/Full) are in
`workflows/runbooks/build/WORKFLOW.md`.

**SoT note:** in practice this orchestration is implemented by
`scripts/plan_engine.py` (critical path, requires chain, gate conditions)
plus the build runbook. This file is prose for human understanding and
onboarding — not an active runbook Buddy reads every turn.

---

## Input

- `docs/plan.yaml` defines milestones with gate conditions and requires chain.
- `scripts/plan_engine.py` computes everything (status, critical path, next actions).

## Readiness check

Before milestone start:

```bash
python3 $FRAMEWORK_DIR/scripts/plan_engine.py --check <milestone>
```

Checks: required milestones done? gate scripts present? gate conditions met?

## Engine

Buddy reads `plan_engine --next` and drives tasks through the per-task flow
(build runbook, Direct/Standard/Full).

## Flow

```
For milestone M:

  1. PRE-CHECK
     plan_engine --check M: required milestones done? gate scripts present?
     Amendments: all amendment tasks (blocked_by chain) resolved?

  2. PRE-GATE (per spec task, dependency order from blocked_by)
     Checks before MCA starts:
     - [ ] board_result: pass (task YAML)
     - [ ] gates.yaml exists and is current
     - [ ] test design exists
     - [ ] delegation artifact exists
     - [ ] schema: pipeline regeneration required?

  3. BUILD (per spec task, blocked_by order)
     Build workflow Execute phase from MCA PLAN.

  4. INTEGRATION (after last task in milestone)
     - L3 component tests
     - L4 integration tests: container composition
     - L5 E2E smoke

  5. MILESTONE-DONE
     plan_engine --check M: PASS.
     Deploy + health checks. Verify milestone as completed.
```

## Dependency order

`plan_engine --critical-path` + blocked_by chains.
A spec without consumed entries in the milestone goes first.
Multiple tasks without deps can run in parallel.

## First slice = learning phase

After the first milestone run, evaluate whether the process fits.
Document adjustments. No overengineering before real experience.

---

## References

| Topic | SoT |
|---|---|
| Per-task flow (Direct/Standard/Full) | `workflows/runbooks/build/WORKFLOW.md` |
| Plan engine | `scripts/plan_engine.py` |
| Plan SoT (milestones, gates, requires chain) | `docs/plan.yaml` |
| Task format (YAML + MD) | `framework/task-format.md` |
| Workflow routing | `framework/process-map.md` |
| Gate template | `workflows/templates/gates-template.yaml` |
| Workflow template (compliance) | `workflows/workflow-template.md` |
