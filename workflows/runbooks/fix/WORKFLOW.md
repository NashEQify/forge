# Workflow: fix

Fix a bug or handle an incident. Root-cause-first, no symptom patching.

## Trigger

- User reports a defect (directly or via Buddy's intake-gate INCIDENT).
- Sub-agent ESCALATED or AUTO-FIXED.
- Test failure in the verify phase of a build workflow.
- Monitoring / health-check alert.

## NOT for

Known feature gap → **build**. Spec error → **review**. Unclear
problem → **solve**. Research → **research** (sub-workflow).

## Path determination

```
Nested in a parent build (parent task has open ACs / sub-builds)? → SUB-FIX
Otherwise                                                          → STANDARD (default)
FULL = reserved for future-extension (L2 board on schema-impact fixes).
```

`workflow_engine.py --start fix --task <id> --route <path>`. SUB-FIX
mechanically excludes `close-bookkeeping` and `commit-deploy` — the
parent owns task-level status.

## Named gates

The fix workflow has **9 named gates**. Phase-status transitions
are engine-internal.

| # | Gate | Skill | Conditional |
|---|------|-------|-------------|
| 1 | root-cause | `root_cause_fix/SKILL.md` (Phase A) | — |
| 2 | test-plan | — (write failing test) | RED before fix |
| 3 | fix-brief | `agents/brief-architect.md` (architect-authored on substantial; Buddy-inline on DIRECT) | mirrors build's brief-author at fix scope |
| 4 | brief-signoff | gate (user approval) per spec 306 §4.4 | DIRECT path skips; sub-fix route omits (parent already approved at parent-scope brief-signoff) |
| 5 | fix-execute | `root_cause_fix/SKILL.md` (Phase B); MCA inline OR Buddy direct per architect-authored fix-brief | retest as inline sub-step (regression suite green) |
| 6 | code-review | `code_review_board/SKILL.md` (light / L1 / L2 per §1) | level: light on ≤2 files mechanical-trigger; L1 default for fixes effort S-M; L2 on schema/cross-spec or larger scope |
| 7 | spec-drift-check | `spec_amendment_verification/SKILL.md` | when fix changes spec-defined behaviour OR authority log exists with new spec edits |
| 8 | close-bookkeeping | `knowledge_processor/SKILL.md` + `task_creation/SKILL.md` + `risk_followup_routing/SKILL.md` (per spec 306 §4.7) | each sub-check skip-eligible |
| 9 | commit-deploy | git pre-commit hooks | sub-fix route skips this gate |

## Detail per gate

**1. root-cause** — `root_cause_fix/SKILL.md` Phase A. Symptoms →
hypotheses → drill. Output: hypothesis + test plan that reproduces
the bug. Do NOT patch symptoms.

**2. test-plan** — write a failing test that triggers the bug
symptom. MUST be RED before the fix.

**3. fix-brief** — architect-authored fix-brief on substantial
fixes per spec 306 §4.5. Brief covers: root-cause hypothesis (from
gate 1), fix-implementation plan, scope-focused test/verification,
RETURN-SUMMARY structure, sign-off field per spec 306 §5.2. DIRECT
path: Buddy authors inline as today. **On external library API
references in the fix scope: invoke `get_api_docs` BEFORE writing
the fix plan** (DR-12 source-grounding, mirrors build's spec-write hook).

**4. brief-signoff** — Mirrors build's brief-signoff (same step
ID, path-agnostic — single signoff shared across DIRECT/STANDARD/
FULL paths). User approves the fix-brief before fix-execute.
DIRECT path skips. Sub-fix route omits per parent-owns-approval
pattern.

**5. fix-execute** — MCA inline OR Buddy direct (orchestrator
path). Fix-diff makes the RED test green per the architect-authored
fix-brief. Add regression coverage where it makes sense. Verify
regression suite is green.

**4. code-review** — `code_review_board/SKILL.md`. L1 default
(effort S-M); L2 only on larger fix scope or schema/cross-spec.

**5. spec-drift-check** — spec-body drift: did the fix change behaviour
defined in a spec? Yes → spec patch in the SAME block-commit. No
spec-defined behaviour touched: skip with rationale.

**6. close-bookkeeping** — two skip-eligible sub-checks:
(a) lessons-learned via `knowledge_processor` (root cause + pattern
lesson into context);
(b) risk follow-up — file ONE follow-up task per non-empty
`remaining_findings:` block in the verdict.

**7. commit-deploy** — `git commit + push`. Deploy conditional on
docs/ changes. Engine auto-advances `workflow_phase=done`; task-level
`status=done` is conditional (sub-fix route skips — parent owns
task status).

## Iteration bounds

| Gate | Max | On overshoot |
|------|-----|--------------|
| root-cause | 3 drill rounds | escalate to user (root cause unclear) |
| fix-execute | 3 attempts to make test green | escalate (architecture problem, not a fix) |
| code-review | 2 review-fix rounds | escalate (review NEEDS-WORK persistent) |

## References

| Topic | Detail SoT |
|-------|------------|
| Root cause fix | `skills/root_cause_fix/SKILL.md` |
| Code review | `skills/code_review_board/SKILL.md` |
| Spec amendment | `skills/spec_amendment_verification/SKILL.md` |
| API docs lookup | `skills/get_api_docs/SKILL.md` |
| Knowledge processor | `skills/knowledge_processor/SKILL.md` |
| Workflow engine CLI | `framework/workflow-engine-cookbook.md` |
