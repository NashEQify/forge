---
name: convergence-loop
description: >
  Intra-gate iteration protocol. Bounded convergence with a rising
  severity threshold and narrowing scope. Max 3 passes.
status: active
relevant_for: ["main-code-agent", "tester"]
invocation:
  primary: sub-skill
  secondary: [workflow-step]
disable-model-invocation: false
uses: []
---

# Skill: convergence-loop

## Purpose

Intra-gate iteration protocol: how a gate step iterates internally
instead of running single-pass. Bounded convergence — max 3 passes
with a rising severity threshold and narrowing scope. Not a new
gate; a mechanic inside existing gates (cascade:
`workflows/runbooks/build/WORKFLOW.md` phase Specify / Verify,
`workflows/runbooks/review/WORKFLOW.md` phase Verify).

Detail mechanics (override, fix responsibility, scope narrowing,
analysis patterns, DR coverage): `REFERENCE.md`.

## Who and when

Every agent with a gate step that produces findings: board agents
(every `board-*`), Buddy (L1 simulation), `tester` (design / eval
mode). The agent loads this skill in addition to the gate-specific
skill. Full path and standard path alike.

Not applicable: `tester` execution mode (the fix loop in
`main-code-agent`) · pure execution steps (writing code, running
tests).

## The protocol

### Step 0: entry (before pass 1)

1. **Intent paraphrase:** the agent formulates the artifact's
   purpose in one sentence. If paraphrase isn't possible → P1
   problem (self-containedness), immediately a BLOCKER.
2. **Scope declaration:** "full scope" on pass 1. Pass 2-3:
   `affected_scope` from the predecessor.

### Three passes, three rules

| Pass | Scope | Severity threshold | Purpose |
|------|-------|--------------------|---------|
| 1 | Full artifact scope | All (BLOCKER + MAJOR + MINOR) | Broad analysis, varied patterns |
| 2 | `affected_scope` from pass 1 + direct dependencies | BLOCKER + MAJOR | Second-order effects |
| 3 | `affected_scope` from pass 2 | BLOCKER only | Verification: any new problems caused by pass-2 fixes? |

**Mechanical stop after pass 3.** No exceptions — unless the
calling sub-workflow has its own limits (e.g. `spec-board.yaml`
safety valve at pass 5, → `REFERENCE.md`).

### Severity definitions (L2 constrained judgment)

| Severity | Definition |
|----------|------------|
| BLOCKER | Artifact unusable as written. The next step cannot start. |
| MAJOR | Usable but with a known defect. Predictably leads to problems / follow-up questions in the next step. |
| MINOR | Improvement, not a defect. The next step's outcome doesn't change. |

Definitions anchored at the next step — mechanically checkable.
Guidance questions: `REFERENCE.md`.

### Fix scope (NON-NEGOTIABLE)

Between passes, **ALL findings** are fixed — not just those above
the current threshold. The threshold determines when CONVERGENCE
is reached, not what gets FIXED. Rationale (Task 191): high-only
fixes led to stagnating accumulation of M/L findings.

Scope narrowing (pass 2+) refers to the ANALYSIS scope of the next
pass, not to the FIX scope.

### Test scope between passes (NON-NEGOTIABLE)

Between passes, MCA fixes findings (per `Fix scope` above). The
**test scope per fix is narrow, not full-suite** — each finding has
a known `file:line` documented in the verdict; re-testing modules
that weren't touched produces zero new signal at 2-3× wallclock
+ token cost.

| Fix touches | Run |
|-------------|-----|
| One module | unit-test file for that module — explicit path, not `tests/` glob |
| Cross-pass-binding test (RED skeleton) | that specific test file |
| Public-API / spec-defined contract | + 0-1 integration smoke |
| L0 (ruff + mypy) | only on touched files |

**ONE full-suite sweep at the END** — after the last
convergence-loop pass converges, ONE full repo run confirms no
cross-cutting regression. Not per fix-phase. Same for pre-deploy
and cross-cutting refactors (dependency-injection rewiring, schema
migration) — those are cross-cutting by definition.

This is the test-side analog of the fix-scope rule above: fix all
findings, but verify each fix at its narrow scope.

### Termination

| Situation | Decision |
|-----------|----------|
| Pass N has 0 findings above the threshold | **CONVERGED** — proceed to the next gate |
| Pass 3 finished, 0 BLOCKERs | **CONVERGED** — MINORs carried as an annex |
| Pass 3 finished, BLOCKERs remain | **ESCALATE** — concrete question to Buddy / user |
| Finding requires an architecture decision | **ESCALATE immediately** — not an iteration problem |

Early termination allowed: pass 1 zero findings → CONVERGED after
pass 1.

## State format between passes

```
## Convergence Pass {N} — {gate name}
### Scope: {pass 1: full scope; pass 2+: affected_scope from N-1}
### Findings
- F{N}.{X}: [{BLOCKER|MAJOR|MINOR}] {description}
  Root cause: {...} | Affected scope: {...}
### Below-threshold: {findings under the threshold — annex}
### Termination: CONTINUE → pass {N+1} | CONVERGED | ESCALATE
```

CONVERGED: annex with below-threshold findings from every pass.
ESCALATE: concrete reason + question ("BLOCKER F3.1 needs a
decision: {...}"), not "there are problems".

## Integration into gate steps

The gate skill = **lens** (what is being checked). The convergence
loop = **iteration** (how often, which scope, when to stop).
Agents load it in addition to their gate skill: step 0 → pass 1
with varied patterns → fixes → pass 2 `affected_scope` → fixes →
pass 3 → CONVERGED / ESCALATE. Varied patterns per gate type +
fix responsibility: `REFERENCE.md`.

## Boundary

- **Not** the fix loop in `main-code-agent` · **not** the gate
  cascade itself (the cascade decides which gates run).
- **Not** the review protocol (superseded 2026-03-24, Task-182
  F-2 — replaced by Spec Board).
- **Not** alternatives evaluation — divergent thinking belongs in
  council / solution-expert.
- **Not** execution steps (writing code, running tests) — only
  analytical / validating gates.

## Anti-patterns

- **NOT** fix only findings above the threshold between passes.
  **INSTEAD** fix ALL findings — the threshold determines
  convergence, not fix scope. Because: MINOR accumulation
  (Task 191, empirical).
- **NOT** treat pass 2 / 3 as fix verification. **INSTEAD** every
  pass is a fresh analysis. Because: anchoring bias — tainted
  passes miss high findings a fresh look catches.
- **NOT** iterate over architecture findings. **INSTEAD**
  ESCALATE immediately. Because: architecture is not an
  iteration problem.
- **NOT** set severity abstractly. **INSTEAD** anchor it at the
  next step ("can the next step proceed?"). Because: only that
  is mechanically checkable.
- **NOT** run `pytest tests/` (full suite) after every fix-phase
  between passes. **INSTEAD** scope-focused tests on the modules
  touched by the fix. Because: re-running untouched modules
  produces zero new signal at 2-3× wallclock + token cost.
- **NOT** run L0 (ruff + mypy) on the full repo between passes.
  **INSTEAD** only on touched files. Because: pre-existing errors
  elsewhere are not a fix-pass concern; treating them as one
  inflates the pass.
