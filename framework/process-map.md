# Process Map

Central entry point: which workflow for which kind of work.
Consumer: Buddy (orchestrator). Agents do not read this document.

Skills, composition, maturity -> `framework/skill-map.md`.

**Path convention:** all runbook and skill paths in the tables below are
from the **repository root** (not relative to `framework/`).

---

## Workflow routing

### Workflows (6)

| I want to... | Workflow | Runbook |
|-------------|---------|---------|
| Solve a problem — solution shape still unclear | **Solve** | `workflows/runbooks/solve/WORKFLOW.md` |
| Break down an objective into a spec hierarchy | **Solve** (scoping mode) | `skills/scoping/SKILL.md` |
| Implement a feature/task | **Build** | `workflows/runbooks/build/WORKFLOW.md` |
| Write/design a spec | **Build** (Specify) | `workflows/runbooks/build/WORKFLOW.md` |
| Review/validate spec(s) | **Review** | `workflows/runbooks/review/WORKFLOW.md` |
| Fix a bug / handle an incident | **Fix** | `workflows/runbooks/fix/WORKFLOW.md` |
| Research / evaluate / spike | **Research** | `workflows/runbooks/research/WORKFLOW.md` |
| Rewrite documentation (reader-journey-first) | **Docs-Rewrite** | `workflows/runbooks/docs-rewrite/WORKFLOW.md` |

### Housekeeping (1)

| I want to... | Workflow | Runbook |
|-------------|---------|---------|
| End a session | **Save** | `workflows/runbooks/save/WORKFLOW.md` |

**Autonomy decision** (who writes which artifact, with which gate, via which routing):
SoT is `framework/agent-autonomy.md`. Workflow assignment above answers
"which workflow"; `agent-autonomy.md` answers the orthogonal sub-questions
permission and gate per artifact type.

**Solve vs. other workflows — entry-point matrix:**
- **Solve**: the problem is known, but solution shape (feature? spec? code? process?) is unclear. Typical for meta-problems, structural questions, new processes.
- **Build**: feature is clear (already decided to build), solution lives in code-space.
- **Fix**: bug reproducible, cause still to be found. ONLY when investigation is needed — known bug with defined fix -> Build-DIRECT.
- **Review**: artifact exists and needs validation.
- **Research**: knowledge gap, answer needs to be found.
- **Solve (scoping mode)**: large objective to split into spec hierarchy. Done criterion foreseeable, solution shape = spec hierarchy. Uses `skills/scoping/SKILL.md` as capability.

If unclear: derive routing from intent (what is the desired result?).
Hybrid tasks: choose a primary workflow and embed other workflows as sub-steps.

---

## Milestone execution

Above single-task workflows. Describes how MULTIPLE tasks are orchestrated
inside one milestone. Details: `framework/milestone-execution.md` (SoT for
milestone-level orchestration).

```
1. PRE-CHECK:   plan_engine --check <milestone>
2. PRE-GATE:    Per task: board_result pass, gates.yaml, test design, delegation
3. BUILD:       Per task in blocked_by order -> Build workflow
4. INTEGRATION: L3 component + L4 integration + L5 E2E smoke
5. DONE:        plan_engine --check PASS, deploy, milestone done
```
