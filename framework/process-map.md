# Process Map

Central entry point: which workflow for which kind of work.
Consumer: Buddy (orchestrator). Agents do not read this document.

Skills, composition, maturity -> `framework/skill-map.md`.

**Discovery entry point:** the `workflow_router` skill
(`skills/workflow_router/SKILL.md`, generated) is the injected sign-post
into this map — its need-phrased catalog is pushed into the
available-skills reminder, so a workflow is reached for at the moment of
need; the router then points back here for routing.

**Path convention:** all runbook and skill paths in the tables below are
from the **repository root** (not relative to `framework/`).

---

## Workflow routing

### Workflows (8)

| I want to... | Workflow | Runbook |
|-------------|---------|---------|
| Solve a problem — solution shape still unclear | **Solve** | `workflows/runbooks/solve/WORKFLOW.md` |
| Break down an objective into a spec hierarchy | **Solve** (scoping mode) | `skills/scoping/SKILL.md` |
| Implement a feature/task | **Build** | `workflows/runbooks/build/WORKFLOW.md` |
| Write/design a spec | **Build** (Specify) | `workflows/runbooks/build/WORKFLOW.md` |
| Review/validate spec(s) | **Review** | `workflows/runbooks/review/WORKFLOW.md` |
| Restore service during ongoing harm | **Fix: Incident recovery first** | `workflows/runbooks/fix/WORKFLOW.md` |
| Diagnose and permanently fix a defect | **Fix** | `workflows/runbooks/fix/WORKFLOW.md` |
| Research / evaluate / spike | **Research** | `workflows/runbooks/research/WORKFLOW.md` |
| Rewrite reader-facing docs / README / positioning (reader-journey-first) | **Docs-Rewrite** | `workflows/runbooks/docs-rewrite/WORKFLOW.md` |

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
- **Fix**: a defect needs investigation. A known cause and defined fix may use Build-DIRECT only if all DIRECT criteria below hold. An active outage or ongoing harm takes Incident recovery first, even when final RCA is incomplete.
- **Review**: artifact exists and needs validation.
- **Research**: knowledge gap, answer needs to be found.
- **Solve (scoping mode)**: large objective to split into spec hierarchy. Done criterion foreseeable, solution shape = spec hierarchy. Uses `skills/scoping/SKILL.md` as capability.

If unclear: derive routing from intent (what is the desired result?).
Hybrid tasks: choose a primary workflow and embed other workflows as sub-steps.

## Authorization

Existing authorization survives phase transitions within the approved scope.
A clear request to implement a bounded change is sufficient; the brief records
that authorization rather than asking for the same decision again. Ask when
the intended result is unclear, a consequential design decision is unresolved,
or the scope, risk, affected host or data impact materially changes.
Diagnosis-only and proposal-only requests do not authorize implementation.
Bookkeeping must not silently change the user's goals or permission boundaries.

Live changes follow the consumer's host/session approvals; destructive actions
require their own explicit confirmation. Recovery does not waive these bounds.
Commit, push and deploy are separate actions: a research or implementation
request does not itself authorize publication. A standing explicit repository
commit policy can authorize local commits; push/deploy require authorization
covering that action and target. No workflow may widen these permissions.

## DIRECT eligibility

Evaluate safety floors first. DIRECT excludes changes to authorization/auth,
secrets, schema/data migration, public or cross-component contracts, live
infrastructure, and changes with hidden/racing/unbounded failure effects.
Size does not cancel a safety floor.

Otherwise DIRECT requires ALL of:
- A clear authorized outcome and concrete success criteria.
- A locally bounded, reversible change following an observed existing pattern.
- No unresolved consequential design decision or new subsystem.
- Relevant implementation/spec context read and an executable verification
  appropriate to the changed behavior; a defect's claimed cause is checked.

New local behavior is allowed. A pre-existing spec is not a reason to repeat
spec authoring; update any affected contract description within scope. File
and line counts are useful warning signals, never the eligibility decision.
If a criterion is unknown, gather targeted evidence; if still unresolved,
use STANDARD/FULL or ask the missing decision, not a ritual authorization.

DIRECT is a short complete lifecycle: outcome + scope + verification plan,
implement, run the relevant tests, independent verification of load-bearing
code, and return evidence. Buddy may author the delegation inline; product
code still goes to main-code-agent. No separate spec/architect/signoff cycle.
Typo/format-only changes require a diff check, not behavioral tests or a board.
An authorization boundary and an independent quality check are different gates.

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
