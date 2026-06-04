---
name: testing
description: >
  Methodology and formats for test-case design and execution
  across the entire SSDLC. Code tests, logic, processes, specs,
  constraints. Domain-specific eval patterns: testing/eval_patterns/.
  Triggers when test cases must be designed or executed (build prepare test-design, fix verify); NOT for ad-hoc manual checks without a test plan.
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
Agent: `agents/tester.md`. Infrastructure discipline
(cross-project): `REFERENCE.md` §Infrastructure.

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

### Derivation from §Test-Strategy catalog (L1+ specs only)

When spec has §Test-Strategy bug-class catalog (per
`framework/spec-engineering.md` §Convention: §Test-Strategy for L1+
specs), the catalog **is the test contract**:

- One TC per `bug_class` row (multi-level verification = one row).
- TC name = `test_<bug_class_slug>`.
- **New bug_class discovered (incl. adversary mode) → inline append
  to §Test-Strategy.** Bookkeeping-tier amendment, no spec_board
  re-spin (per `_protocols/spec-amendment-discipline.md` category f).
  Single commit at adversary-run end (or folded later).
- Legacy specs without catalog: derive per upstream table above.

### Bug-class dedup (at creation time)

Before adding TC for a new `bug_class`, check catalog/plan for
existing coverage. Duplicate or "small variation within a class" →
do not add. **When in doubt, drop.** Real gaps surface later as
real defects (real follow-up tasks), not preemptive imagined edges.

### Proportionality table (plan-size sanity)

| Trigger | TC count | Plan size |
|---|---|---|
| ≤3 ACs, mechanical | 1.5-2× AC | <50 lines |
| 4-7 ACs, new behavior | 2-3× AC | ~100-200 lines |
| New subsystem / schema / cross-module | 3-4× AC | 200-400 lines |

>400 lines without adversary mode = drift signal (likely duplicate /
imagined edges).

### L1 Logic / semantic + Iteration protocol

L1 = simulation, completeness, consistency, DRY check, constraint
satisfaction (for process / workflow / agent-behaviour specs).
`tester` (design) defines L1 checks; Buddy runs L1-SIM in
Specify phase; `main-code-agent` calls `tester` (execution) after
implementation. Design runs inside `convergence_loop` (pass 1 full
derivation; passes 2-3 coverage gaps with rising threshold; tester
self-service gate). Detail: REFERENCE.md.

## Coverage matrix (MUST output)

ACs without TC = GAP. An empty row = invalid state.

| Spec element | TC IDs | bug_class | Level | AC quality | Eval status |
|---|---|---|---|---|---|

**bug_class** (required when spec has §Test-Strategy): noun phrase
naming the defect class this TC guards against. Must be present in
the spec catalog (else: spec amendment first, see "Derivation from
§Test-Strategy catalog"). Duplicate bug_class across rows = drop one.

**AC quality** (required): **clear** / **vague** (annotate what's
missing) / **contradictory** (which contradiction). Vague /
contradictory → spec review BEFORE execution. No opt-out.

Persistence: section in `docs/tasks/NNN.md`. Update on a spec
change, do not recreate.

## Contract

**INPUT:** spec with ACs (or process definition for L1), `spec_ref`
for spec-freshness check. Optional: existing plan (delta updates).
Context: REFERENCE.md.

**OUTPUT:** test plan + coverage matrix (spec element × TC × bug_class
× level × AC quality × eval status) + AC-quality assessment + run
strategy. Persisted in `docs/tasks/NNN.md`.

**DOES NOT:** test execution in design mode (plan only); spec fixes
(reports vague/contradictory ACs); code skeletons in design mode
(execution-mode `tester` does that).

**DONE:** coverage matrix complete (every AC ≥1 TC, no empty rows);
AC quality assessed; vague/contradictory → spec-review signal; run
strategy decided; plan persisted.

**FAIL handling:** coverage gaps → convergence-loop pass 2-3 rising
threshold. Vague/contradictory ACs → ESCALATE to spec review (no
opt-out). Spec-freshness mismatch (`spec_version` ≠ `test_plan_spec_ref`)
→ ABORT, design first.

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
- **No infrastructure details inline** — fixtures, markers,
  docker-compose conventions → `REFERENCE.md` §Infrastructure.
- **No structural repo check** — dead refs, orphan files →
  `consistency_check`.
- **No board review** — multi-perspective spec review →
  `spec_board`.

## Anti-patterns

- **NOT** L4/L5 assertions too specific. INSTEAD STRUCTURE/TYPE only
  at L4/L5 (specific assertions break on every L2/L3 refactor).
- **NOT** tests after implementation. INSTEAD skeletons BEFORE
  (red-phase tautology guard).
- **NOT** horizontal slice (all tests then all impl). INSTEAD vertical
  slice / tracer bullet (one test → one impl → repeat). Horizontal
  produces tests of imagined behaviour, not actual.
- **NOT** wave through vague/contradictory ACs. INSTEAD trigger spec
  review first (TCs on vague ACs = guessing).
- **NOT** assert on the content of a PM/workflow artifact
  (`docs/tasks/*.yaml`, `.workflow-state/*`, test-plan files). INSTEAD
  assert on code behaviour or code structure only. "Is hazard X
  documented / is decision Y recorded" is process-discipline — its home
  is the spec/ADR + `consistency_check`, not `pytest` (a `tests/` file
  that reads `docs/tasks/` breaks CI the moment the artifact is archived).

Extended anti-patterns (eval script persistence, run-strategy scope
discipline): REFERENCE.md.

## References

Python tooling (pytest config, ruff, conventions):
`skills/python_code_quality_enforcement/SKILL.md`. Detail formats
(test plan, skeleton, eval, retest gate): `REFERENCE.md`.
