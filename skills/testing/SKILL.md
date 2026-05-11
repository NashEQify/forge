---
name: testing
description: >
  Methodology and formats for test-case design and execution
  across the entire SSDLC. Code tests, logic, processes, specs,
  constraints. Domain-specific eval patterns: testing/eval_patterns/.
status: active
relevant_for: ["tester"]
invocation:
  primary: workflow-step
  secondary: [user-facing, sub-skill]
disable-model-invocation: false
modes: [design, execution]
uses: [convergence_loop]
---

# Skill: testing

Methodology and formats for test-case design and execution across
the entire SSDLC. Not just code tests — also logic, processes,
specs, constraints.
Agent: `agents/tester.md`. Infrastructure:
`skills/test_infrastructure/SKILL.md`.

Detail mechanics (format details, skeleton templates, eval
methodology, retest gate): `REFERENCE.md`.

## 6-level test pyramid

| Level | What | Trigger |
|-------|------|---------|
| L0 Structural | Dead refs, schema, invariants | Every commit |
| L1 Logic / Semantic | Process gaps, spec consistency, DRY, simulation | Spec / process change |
| L2 Unit | Function / module level | Code change |
| L3 Integration | Agent handoffs, API contracts, event schemas | Interface change |
| L4 E2E | Full workflows (boot, delegation, save) | Workflow change, periodic |
| L5 Adversarial | Stale context, drift, chaos, properties | Milestone, periodic |

**Regression rule:** L4 / L5 check STRUCTURE / TYPE. L3 checks
CONTRACTS. L2 checks BEHAVIOUR / VALUES. Lower levels must never
break when higher ones are added — on a break: abstract the
assertion, do not delete the test.

## Test-case design (core task)

Test cases are designed BEFORE implementation. No delegation
without a test plan.

### Derivation from specs

| Spec element | Test-case type | Level |
|---|---|---|
| Every AC | Positive test | L2 / L3 |
| Every MUST NOT | Negative test | L2 / L3 |
| Every ESCALATE | Boundary test | L3 / L4 |
| Edge cases (interview) | Regression test | L2 |
| Failure modes (constraint architecture) | Smart-but-wrong caught? | L2 / L3 |
| Process definitions | Simulation of concrete cases | L1 |
| Verifiable assumptions | Eval test (hypothesis with code) | Eval (3e) |
| Architecture invariants | Structural test | L0 |

### L1 Logic / semantic

For process definitions, workflow specs, agent behaviour:
simulation (concrete case against the definition) · completeness
(does every step have a successor?) · consistency (does it
contradict another definition?) · DRY check (canonical or
duplicate?) · constraint satisfaction (are all constraints
satisfiable?).

Role split: `tester` (design mode) defines L1 checks. Buddy runs
L1 scenarios (the L1-SIM step in
`workflows/runbooks/build/WORKFLOW.md` Specify phase).
`main-code-agent` calls `tester` (execution mode) after
implementation.

### Iteration protocol

Test-case design runs inside the convergence loop
(`skills/convergence_loop/SKILL.md`). Pass 1: full derivation
with varied patterns (happy / error / boundary / concurrent /
stale state). Passes 2-3: coverage gaps, rising threshold. Gate
type: self-service (the tester adjusts its own test plan).

## Coverage matrix (MUST output)

ACs without TC = GAP. An empty row = invalid state.

| Spec element | TC IDs | Level | AC quality | Eval status |
|---|---|---|---|---|

**AC quality** (required): **clear** / **vague** (annotate what's
missing) / **contradictory** (which contradiction). Vague /
contradictory → spec review BEFORE execution. No opt-out.

Persistence: section in `docs/tasks/NNN.md`. Update on a spec
change, do not recreate.

## Contract

### INPUT
- **Required:** spec with ACs (or process definition for L1).
- **Required:** `spec_ref` from the task YAML — for the
  spec-freshness check.
- **Optional:** existing test plan — for delta updates instead
  of starting from scratch.
- **Context:** `skills/testing/REFERENCE.md` (format details,
  skeleton templates, eval methodology).

### OUTPUT
**DELIVERS:**
- Test plan: test cases per spec element (AC → positive TC,
  MUST NOT → negative TC, etc.).
- Coverage matrix: spec element × TC ID × level × AC quality ×
  eval status.
- AC-quality assessment: clear / vague / contradictory per AC.
- Run strategy: which test levels on which trigger.

**DOES NOT DELIVER:**
- No test execution in design mode — plan, not results.
- No spec fixes — reports vague / contradictory ACs, doesn't fix
  them.
- No code skeletons in design mode — skeleton creation is
  execution mode (`tester`).

**ENABLES:**
- Build prepare: test plan as a delegation artifact for MCA.
- Tester execution: plan as binding input for test
  implementation.
- Spec-review feedback: AC-quality findings as a signal to
  `spec_board`.

### DONE
- Coverage matrix complete: every AC has at least 1 TC, no empty
  rows.
- AC quality assessed: clear / vague / contradictory per AC.
- Vague / contradictory ACs → spec-review signal documented.
- Run strategy decided (which levels on which trigger).
- Test plan persisted in `docs/tasks/NNN.md`.

### FAIL
- **Retry:** coverage gaps → convergence-loop pass 2-3 with
  rising threshold.
- **Escalate:** vague / contradictory ACs → spec review BEFORE
  execution (no opt-out).
- **Abort:** spec-freshness check FAIL (`spec_version` ≠
  `test_plan_spec_ref`) → STOP, design first.

## Spec-freshness check (MUST before execution)

`spec_version == test_plan_spec_ref`? Yes → continue. No → STOP,
design first. Fields missing → warning.

## Run strategy

| Trigger | Scope |
|---------|-------|
| Commit | L0 |
| Spec / process | L0 + L1 |
| Code | L0 + L2 + L3 (affected) |
| Workflow | L0 + L1 + L4 |
| Milestone | L0 - L5 |
| Boot | Entropy audit (L5 light) |

Spec-process integration: `Interview → Spec → Review → TEST
DESIGN → PRE-IMPL EVAL → Decomposition → Delegation`.

## Boundary

- **No linting / syntax check** — that is
  `python_code_quality_enforcement` and the pre-commit hooks.
- **No infrastructure details** — fixtures, markers,
  docker-compose → `test_infrastructure`.
- **No structural repo check** — dead refs, orphan files →
  `consistency_check`.
- **No board review** — multi-perspective spec review →
  `spec_board`.

## Anti-patterns

- **NOT** make L4 / L5 assertions too specific. **INSTEAD** at
  L4 / L5 check only STRUCTURE / TYPE. Because: assertions that
  are too specific at higher levels break on every L2 / L3
  refactor — the assertion is wrong, not the code.
- **NOT** write tests after implementation. **INSTEAD**
  skeletons BEFORE implementation as a delegation-ready artifact.
  Because: "green right away" without a red phase is not a test;
  it's a tautology.
- **NOT** write all tests first then all implementation
  ("horizontal slice"). **INSTEAD** vertical slice / tracer
  bullet: one test → one impl → repeat. Pattern lift Phase G
  tier-2 from Pocock TDD. Because: horizontal slicing produces
  tests that test *imagined* behaviour instead of *actual* —
  you end up testing data shape instead of user-facing behaviour
  and tests become insensitive to real changes. Vertical slicing
  responds to what you learned in the previous cycle — you know
  exactly which behaviour matters and how to verify it.
- **NOT** wave through vague / contradictory ACs. **INSTEAD**
  trigger spec review before deriving TCs. Because: TCs on vague
  ACs are guessing, not testing.
- **NOT** treat eval scripts as one-off checks. **INSTEAD** keep
  them persistent in `tests/eval/` — assumption regression
  suite. Because: assumptions remain assumptions; they need
  repeatable verification.
- **NOT** ignore the run strategy and always run everything.
  **INSTEAD** scope per trigger. Because: unnecessary L5 runs
  cost time without signal.

## References

L4 E2E: `tests/TESTCASES.md`. L1 findings:
`docs/tasks/l1-testing-pass-findings.md`. Python tooling
(pytest config, ruff, conventions):
`skills/python_code_quality_enforcement/SKILL.md`. Detail formats
(test plan, skeleton, eval, retest gate): `REFERENCE.md`.
