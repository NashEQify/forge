---
name: adversary-test-plan
description: >
  Adversary-driven test-plan extension BEFORE implementation.
  Code-adversary reviews the tester design output and adds
  edge-case TCs the implementer's cognitive bias systematically
  misses. RED tests are a required pre-fix gate (mechanical
  definition of done). Pattern lesson 388 NEW-V-001 5x replay.
  Triggers when a tester design output exists and RED edge-case TCs are needed before implementation (build prepare); NOT for post-implementation review (use code_review_board).
status: active
verification_tier: 1
evidence_layout: per_finding
relevant_for: ["main-code-agent"]
invocation:
  primary: workflow-step
  secondary: [user-facing]
disable-model-invocation: false
uses: [_protocols/dispatch-template, _protocols/context-isolation, _protocols/evidence-pointer-schema]
---

# Skill: adversary-test-plan

## Purpose

Tester is spec-derivative — implementer's cognitive bias systematically
misses the same edge cases (compensation-action shares-bug-class,
cycle-entry-point sensitivity, cleanup-tx silent-ack). A soft-prompt
mitigation in the MCA brief replicates the failure across iterations.

Adversary-driven test plan BEFORE implementation: the code-adversary
persona extends the tester design output with edge-case TCs targeting
the pattern classes the spec-derivative tester would miss. RED tests
are the mechanical pre-fix gate — MCA's definition of done requires
every adversary test green.

Mechanism > prompt discipline. Detail / pattern lessons / case
studies / full schemas: `REFERENCE.md`.

## When to call

**Trigger condition (analogous to impl_plan_review):**

- Task has ≥3 acceptance criteria, **OR**
- Task contains a schema change (DB / API / event schema), **OR**
- Task has cross-module impact (>1 subsystem), **OR**
- Workflow is sub-build (parent has remaining scope).

Below threshold (≤2 ACs, single-file, no schema): skip-eligible with
rationale. `on_fail: warn` — Buddy discipline.

**Bedrock (why this trigger):** facets per
`agents/buddy/operational.md §Multi-perspective engagement` —
primarily **blind-spot compensation** (implementer cognitive bias
systematically misses what adversary targets) and **reversibility**
(test gaps in shipped code are expensive to recover from). Count is
the fallback when facets are unclear. Facet-question first, count
as net.

**Position in the workflow:** between `test-design` (tester writes
v1) and `delegation-artefact` (Buddy writes MCA brief). Extended
test plan v2 is input for `test-skeleton-writer` +
`delegation-artefact`.

## Who runs it

Buddy (orchestrator). Spawns code-adversary persona with: spec,
tester test plan, pattern-lessons list (`testing/REFERENCE.md`
§Adversary patterns). Returns: extended test plan v2 + coverage
rationale.

## Process

### 1. Prepare input

`spec_ref`, `test_plan_ref`, `output_path`, `pattern_refs`
(defaults: `testing/REFERENCE.md` + 388 dogfooding patterns).

### 2. Spawn persona (per `_protocols/dispatch-template.md`)

Context-isolated — adversary sees ONLY spec + test plan +
pattern-lessons, NO implementation code.

### 3. Augenmaß discipline (core behaviour rule)

**Before adding any TC: stop and think.** Default magnitude: 5-10
high-signal ADV-TCs. Task-459 anti-case: 41 TCs for 6 deltas (6.8
TC/delta) drives MCA into workaround patterns (trivial-green
skeletons, impl-fragments that only serve tests).

When output reflex hits >2x deltas/ACs: pause. **Pattern-class
coverage is NOT required.** Classes without a clear code trigger go
into `patterns_excluded` with rationale.

**Per-TC value-floor (MANDATORY, CLAUDE.md Inv 9).** Before adding
any ADV-TC, name in one sentence on the TC: *what production-
realistic failure-mode does this test catch that the implementer's
tests, the existing scope-suite, and the integration / contract-
pinning tests do NOT catch?* If the answer is "future-edit safety"
/ "convention" / "completeness" / "exports a new contract so it
needs coverage" — the TC fails the value-floor and stays out of v2.
Concrete consumer + concrete failure-mode = TC justified. The
sentence stays inline on the TC as rationale; absence is a
validation fail at MCA-ingest. Hand-curated configuration tuples,
trivially-defaulted Pydantic fields, and topology checks on data
the author edits by hand are typical fail patterns (Task 517 case:
9 proposed TCs → 7 dropped as theater after value-floor pass).

Three stop-and-think questions + consolidation rule (EXTENDS
mandates dropped 2026-05-08): `REFERENCE.md` §Augenmaß +
§Consolidation.

### 4. Output format (required)

Extended test plan v2 = existing TCs (consolidated where applicable)
+ adversary-added TCs with `pattern_class` annotation.

Required coverage rationale block (full YAML schemas in
`REFERENCE.md`): `scope_signal` (ratio + `proportional_check`),
`patterns_chosen` (per class with code-trigger rationale),
`patterns_excluded` (explicit rationale), `consolidations`,
`spec_assumption_diff`, `implementer_blindspots`.

**Bind rule (output):** all ADV-TCs are part of definition of done.
Few + binding > many + diluted. On uncertainty: leave out.
Non-included TCs are adversary private notes, not skill output.

### 5. Buddy integration

- v2 written to `docs/tasks/<id>.md` test-plan section (replaces v1
  with consolidations).
- `test-skeleton-writer` consumes v2 + writes RED skeletons for ALL
  TCs (tester + adversary).
- `delegation-artefact` references v2 + RED skeleton path.
- **Post-return check (Augenmaß verification):** ratio plausible,
  `patterns_chosen` with code-trigger rationale, `patterns_excluded`
  filled, consolidations justified. On miss: re-dispatch with
  Augenmaß reminder, max 1 retry.

### 6. MCA definition of done

MCA brief contains: **"All adversary TCs (`ADV-TC-*`) MUST pass
post-implementation."** Adversary TCs are first-class definition of
done. Augenmaß on the adversary side ensures proportional bind
pressure — no severity splitting needed.

Pre-commit check 9 (RUNBOOK-DRIFT) catches when adversary TCs remain
unconfigured.

## Red flags

Skill-violations (full list with detail: `REFERENCE.md`):

- Only 1-2 TCs ("looks fine") — adversary mindset not active.
- No `pattern_class` annotation — no pattern discipline.
- All happy-path variations — "smart-but-wrong" not active.
- TC inflation: ratio >2x without active rationale (Task-459).
- `patterns_chosen` contains all ~7 classes ritualistically.
- `patterns_excluded` empty — selection act invisible.
- Consolidation without rationale — silent deletion.

## Anti-patterns

- **NOT** trigger on a trivial build. INSTEAD respect threshold.
  Because: token overhead without benefit.
- **NOT** TC inflation without Augenmaß. INSTEAD 5-10 high-signal
  default; ratio >2x = stop-and-think + active defence in
  `proportional_check`. Because: many + diluted drives MCA into
  workaround patterns (Task-459 41/6 case).
- **NOT** walk pattern classes ritualistically. INSTEAD per class
  check code trigger; no trigger → `patterns_excluded` with
  rationale. Because: pattern-enforcement drives inflation.
- **NOT** merge adversary output unchecked. INSTEAD Buddy verifies
  coverage rationale + ratio + `patterns_excluded` filled. Because:
  ritualistic TCs without pattern links.
- **NOT** skip `test-skeleton-writer`. INSTEAD RED skeletons for
  ALL adversary TCs as pre-implementation requirement. Because:
  without RED, MCA writes adversary green immediately (NEW-V-001
  reproduces).
- **NOT** treat adversary TCs as optional in the MCA brief. INSTEAD
  first-class definition of done. Because: optional == ignored in
  80% of cases.
- **NOT** silent deletion of tester TCs. INSTEAD consolidate with
  `consolidations` entry + rationale. Because: reduction needs
  audit trail.
- **NOT** "include in case it's needed" default. INSTEAD on
  uncertainty: leave out. Because: default-to-include is the
  TC-inflation root.

## Boundary

- Not code review (= `code_review_board`, post-implementation).
- Not spec review (= `spec_board`, pre-test-design).
- Not test-plan author (= `testing` skill design mode).
- Not RED skeleton author (= `test-skeleton-writer` downstream).
- Not plan review (= `impl_plan_review`, post-MCA-plan).

## Contract

### INPUT
- **Required:** `spec_ref`, `test_plan_ref`, `output_path`.
- **Optional:** `pattern_refs` (default:
  `testing/REFERENCE.md` + 388 dogfooding).

### OUTPUT

**DELIVERS:** test plan v2 (consolidated where applicable +
adversary TCs with `pattern_class`) + coverage rationale block.
Adversary TCs are first-class definition of done for the MCA brief.

**DOES NOT DELIVER:** RED skeletons (downstream
`test-skeleton-writer`), implementation hints (context-isolated),
silent deletion of tester TCs (consolidation with rationale only).

**ENABLES:** `test-skeleton-writer` input; `delegation-artefact`
pattern coverage as MUST constraint; future pre-commit gate for
ADV-TC pass-rate.

### DONE
- Adversary dispatched + returned.
- Test plan v2 written to `output_path`.
- Coverage rationale block filled (all 6 fields).
- Augenmaß visible: 5-10 default, >2x ratio has active defence.

### FAIL
- **Retry:** 0 TCs OR only happy-path → re-dispatch with explicit
  pattern-lessons list (max 2 retries).
- **Escalate:** fundamental spec gap (assumption not testable) →
  STOP, Buddy escalates to user for spec correction.
- **Abort:** trigger fired but no risk (purely declarative) →
  one-sentence rationale, `--skip`.

## Bind rule

- `delegation-artefact`: ADV-TCs as MUST constraints
  (`pattern_class` + count).
- `mca-implementation`: definition of done = ALL ADV-TCs PASS.
- `code-review-board`: reviewers check ADV-TCs PASS + production
  shape (not test shape) covered.
