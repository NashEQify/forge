---
name: adversary-test-plan
description: >
  Adversary-driven test-plan extension BEFORE implementation.
  Code-adversary reviews the tester design output and adds
  edge-case TCs the implementer's cognitive bias systematically
  misses. RED tests are a required pre-fix gate (mechanical
  definition of done). Pattern lesson 388 NEW-V-001 5x replay.
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

The tester writes tests from the spec fragment — the
implementer's cognitive bias systematically misses the same
edge cases (compensation-action shares-bug-class,
cycle-entry-point sensitivity, cleanup-tx silent-ack). A
soft-prompt mitigation in the MCA brief is not enough: the
pattern replicates in follow-up iterations.

Adversary-driven test plan BEFORE implementation: the
code-adversary persona extends the tester design output with
edge-case TCs targeting exactly the pattern classes the
spec-derivative tester would miss. RED tests are a mechanical
pre-fix gate — MCA's definition of done requires every
adversary test green.

discipline-as-mechanism: an adversary perspective up front
(tuned differently to the tester) catches edge cases that
slip through coverage heuristics.

## When to call

**Trigger condition (analogous to impl_plan_review):**

- Task has ≥3 acceptance criteria, **OR**
- Task contains a schema change (DB / API / event schema),
  **OR**
- Task has cross-module impact (>1 subsystem), **OR**
- Workflow is sub-build (parent has remaining scope, edge
  cases compound).

Below threshold (≤2 ACs, single-file, no schema): the skill is
skip-eligible with rationale. on_fail: warn — the hook adds
nothing mechanically; Buddy discipline.

**Position in the workflow:** between `test-design` (the
tester writes a spec-derivative test plan) and
`delegation-artefact` (Buddy writes the MCA brief). The
extended test plan is input for `test-skeleton-writer` +
`delegation-artefact`.

## Who runs it

Buddy (orchestrator). Spawns the code-adversary persona with:
- Spec (`spec_ref` from the task YAML).
- Tester test plan (from the test-design step output).
- Pattern-lessons list (`skills/testing/REFERENCE.md`
  §Adversary patterns).

The adversary returns the extended test plan v2 + the coverage
rationale.

## Process

### 1. Prepare input

- `spec_ref`: path to the spec.
- `test_plan_ref`: path to the test-design output
  (`docs/tasks/<id>.md` test-plan section).
- `pattern_refs`: list of pattern lessons
  (`skills/testing/REFERENCE.md` §Adversary patterns + 388
  dogfooding pattern lessons).

### 2. Adversary persona spawn (per dispatch-template.md)

```
Review test plan: {test_plan_ref}
Spec context: {spec_ref}
Pattern-lessons cross-ref: {pattern_refs}
Output: extended test plan in {output_path}
Pass: {Standard|Deep}, code-adversary persona
```

The dispatch is context-isolated (per
`_protocols/context-isolation.md`) — the adversary sees ONLY
the spec + the test plan + the pattern lessons, NO
implementation code.

### 3. Augenmaß discipline (core behaviour rule)

**Before adding any TC: stop and think.** This section is the
main mechanism against TC inflation. More tests are not safer
— they are slower, dilute the bind sharpness, and push
implementers into workaround patterns ("make the skeletons
trivially green because 41 is too many").

**Target magnitude:** 5-10 high-signal ADV-TCs > 30+
ritualistic-coverage TCs. Task-459 pattern (41 TCs for 6
deltas, 6.8 TC/delta) is the concrete anti-case. When your
output reflex hits >2x deltas or >1.5x ACs: pause.

**Three stop-and-think questions per potential TC:**

1. *"Would the implementer ACTUALLY miss this?"* — when the
   answer is hypothetical or speculative ("could be missed"),
   that's a weak TC. The adversary mindset demands concrete
   pattern-replay evidence or a spec-authority gap, not
   "conceivable mistakes".
2. *"Does this pattern class have replay evidence for THIS
   code?"* — race conditions are not universally relevant.
   Compensation bugs need multi-step transactions. When the
   code has no plausible trigger for the pattern class, the
   class doesn't belong in the test plan.
3. *"Is this an honest new probe or a setup variation of an
   existing TC?"* — if the second answer: consolidate
   instead of adding (see consolidation rule below).

**Pattern-class coverage is NOT required.** The adversary does
NOT have to cover all ~7 classes. The coverage rationale does
not prove "everything thought of"; it explains "why these 1-3
classes are relevant here". Classes without a clear trigger in
the code: leave out, do NOT write a mandatory variation.

**Consolidation rule (EXTENDS mandates dropped 2026-05-08):**
The adversary may flag and consolidate existing tester TCs as
redundant variations when a clean reduction is visible. Test
plan v2 comment: `# consolidated: TC-X+TC-Y → ADV-TC-N
(rationale)`. Consolidation requires rationale per merged
set. The adversary may NOT delete without consolidation —
only replace-with-rationale.

### 4. Adversary output format (required)

Extended test plan v2 = existing TCs (consolidated where
applicable) + adversary-added TCs. Per adversary TC:

```yaml
- id: ADV-TC-{N}
  pattern_class: "{NEW-V-001 | Compensation-Bug | Cycle-Entry-Point | Cleanup-Tx-Silent-Ack | Smart-but-Wrong | Stale-State | Race-Condition | ...}"
  scenario: "<concrete scenario, 1-3 sentences>"
  setup: "<minimal test setup>"
  assertion: "<exact assertion — what MUST PASS after the fix>"
  rationale: "<why the implementer's cognitive bias would miss this>"
  level: "L2|L3|L4"
```

**Coverage rationale block (required at the end):**

```yaml
adversary_coverage:
  total_advanced_tcs: <N>
  scope_signal:
    deltas_or_acs: <N>          # number of deltas / ACs / schema changes in the task
    ratio: <total_advanced_tcs / deltas_or_acs>
    proportional_check: >
      "<if ratio > 2: active rationale why more TCs are honest here.
       If ratio <= 2: 'Augenmaß within range'.>"
  patterns_chosen:
    - NEW-V-001: "<why this pattern class is relevant for THIS code>"
    - Compensation-Bug: "<why ...>"
    # not every class — only ones with a clear code trigger
  patterns_excluded:
    - Race-Condition: "<why NOT relevant — e.g. 'no concurrency path'>"
    # explicit rationale for what is NOT covered, so it's clear
    # it was deliberately omitted
  consolidations: []           # empty when none; otherwise per consolidation
                               # an entry with the merged set + rationale
  spec_assumption_diff: "<which spec assumptions are non-trivially testable?>"
  implementer_blindspots: "<which edge cases would implementer bias have missed?>"
```

**Bind rule:** all ADV-TCs are part of the definition of done.
Few + binding > many + diluted. When the adversary is unsure
whether a TC belongs in the test plan: leave it out.
Non-included TCs are an adversary private note, not skill
output.

### 5. Buddy integration

- Test plan v2 is written into `docs/tasks/<id>.md` test-plan
  section (replaces the tester's v1, with consolidations
  where applicable).
- The `test-skeleton-writer` agent (downstream step) consumes
  v2 + writes RED skeletons for ALL TCs (tester + adversary).
- `delegation-artefact` (Buddy) references test plan v2 + the
  RED skeleton path.
- **Buddy post-return check (Augenmaß verification):**
  - `total_advanced_tcs / deltas_or_acs` ratio plausible?
    (Soft limit: >2 requires an active `proportional_check`
    rationale. At 41/6 = 6.8: re-dispatch.)
  - `patterns_chosen` only contains classes with code-trigger
    rationale?
  - `patterns_excluded` is filled (shows the active selection
    act)?
  - Consolidations justified?
  - On miss: re-dispatch with an Augenmaß-discipline reminder,
    max 1 retry.

### 6. MCA definition of done

The MCA brief contains explicitly: **"All adversary TCs
(`ADV-TC-*`) MUST pass post-implementation."** Adversary TCs
are first-class definition of done. Augenmaß on the adversary
side (writing fewer TCs) ensures proportional bind pressure —
no severity splitting needed.

Pre-commit check 9 (RUNBOOK-DRIFT) catches when adversary TCs
remain unconfigured.

## Red flags (skill violations)

- The adversary returns only 1-2 TCs ("looks fine") — pattern
  lessons not taken seriously, adversary mindset not active.
- Adversary TCs have no `pattern_class` annotation — no
  pattern discipline, just arbitrary tests.
- Adversary TCs are all happy-path variations — adversary
  violates the mandate ("smart-but-wrong" not active).
- The `implementer_blindspots` block is empty or "n/a" —
  pattern-coverage rationale missing.
- **TC inflation: ratio >2x deltas / ACs without active
  rationale** — Task-459 pattern (41 TCs / 6 deltas = 6.8).
  Indicator: the adversary uses pattern-class enforcement as
  boilerplate coverage instead of Augenmaß. Re-dispatch with
  a stop-and-think reminder.
- **`patterns_chosen` contains all ~7 classes with
  ritualistic rationale** ("could-apply" / "defence-in-depth")
  — pattern-class coverage is no longer required in this skill
  version. The adversary must select actively, not cover all.
- **`patterns_excluded` empty** — the adversary did not
  actively choose what to leave out. Augenmaß without a
  visible selection act is unverifiable. Audit trail missing.
- **Consolidation without rationale** — the adversary may
  consolidate, but every consolidation needs an entry in the
  `consolidations` block with rationale. Consolidation
  without rationale = silent deletion.
- The test plan v2 has fewer ADV-TCs than the adversary
  considered internally — correct (Augenmaß discipline). NOT
  a red flag.

## Common rationalizations (anti-excuse)

| Excuse | Counter |
|---|---|
| "Spec coverage is enough" | NEW-V-001 5x replay in 388. Coverage heuristics don't catch it. The adversary mindset is tuned differently. |
| "Adversary duplicates the code-review-board" | The Code Review Board checks CODE post-implementation. adversary-test-plan checks the TEST PLAN pre-implementation. Different timing, different artifact. |
| "Skill is overhead on a trivial build" | The trigger condition holds — below threshold is skip-eligible. NEW-V-001 5x in substantial builds, not in trivial ones. |
| "The adversary is the LLM, not real bug-finding" | Per dogfooding audit: the adversary persona finds HIGH findings other reviewers miss (4-fold in 388). Empirically supported. |
| "The tester should do this" | The tester is spec-derivative (ACs → TCs). The adversary is critique (what's NOT-in-spec-but-needed). Different reasoning modes — separate skill design. |
| "More TCs are safer" | The other way round: many TCs dilute bind sharpness and push MCA into workaround patterns (trivial-green skeletons, implementation fragments that only serve tests). 5-10 high-signal > 30+ ritualistic. Pattern replay 459 (41/6) is the concrete negative example. |
| "When I have a pattern class, I should test it too" | Pattern-class coverage is no longer required. The class needs a clear code trigger for an adversary TC. Race only on concurrency, compensation only on multi-step transactions. Classes without a trigger belong in `patterns_excluded` with rationale. |
| "I don't know whether the TC is relevant — leave it in to be safe" | Default-to-include is the TC-inflation root. When unsure: leave out. Adversary private note, not skill output. Skill output must have an active defence (pattern-replay evidence / spec-authority gap / security surface). |
| "Adversary TCs are all setup variations of one idea — keep all" | Consolidation rule: variations of one idea belong in one TC with multiple setup branches, not in 5 separate TCs. Consolidation requires a `consolidations` entry with rationale, but it is allowed and desired. |
| "The `proportional_check` rationale is bureaucracy" | The other way round: it is the only audit trail for Augenmaß. Without it Buddy can't verify whether 41 TCs are honest or ritualistic. At ratio ≤2: one sentence is enough. At ratio >2: an active defence per TC cluster. |

## Contract

### INPUT

- **Required:** `spec_ref` (path to the spec).
- **Required:** `test_plan_ref` (path to the tester design
  output).
- **Required:** `output_path` (path for the extended test plan
  v2).
- **Optional:** `pattern_refs` (default:
  `skills/testing/REFERENCE.md` + 388
  `dogfooding-experience.md` pattern lessons).

### OUTPUT

**DELIVERS:**
- Extended test plan v2 (existing TCs consolidated where
  applicable + adversary TCs with `pattern_class` annotation).
- Coverage rationale block (`scope_signal`, `patterns_chosen`,
  `patterns_excluded`, `consolidations`,
  `spec_assumption_diff`, `implementer_blindspots`).
- Adversary TCs are first-class definition of done for the
  MCA brief.

**DOES NOT DELIVER:**
- No test skeletons (`test-skeleton-writer` downstream).
- No implementation hints (the adversary is
  context-isolated, sees only the spec).
- No silent deletion of tester TCs (consolidation allowed
  with rationale; pure deletion forbidden).

**ENABLES:**
- `test-skeleton-writer` input for RED skeletons.
- `delegation-artefact` with pattern coverage as a MUST
  constraint.
- Pre-commit check (future) for adversary TC pass-rate as a
  gate.

### DONE

- The adversary persona dispatched + returned.
- Test plan v2 written to `output_path`.
- Coverage rationale block filled: `scope_signal` (incl.
  ratio + `proportional_check`), `patterns_chosen` with
  code-trigger rationale, `patterns_excluded` with active
  rationale, `consolidations` (may be empty),
  `spec_assumption_diff`, `implementer_blindspots`.
- Augenmaß discipline visible: 5-10 high-signal TCs default,
  >2x ratio has active defence.

### FAIL

- **Retry:** the adversary returns 0 TCs OR only happy-path →
  re-dispatch with an explicit pattern-lessons list (max 2
  retries).
- **Escalate:** the adversary finds a fundamental spec gap
  (spec assumption not testable) → STOP, Buddy escalates to
  the user for a spec correction before implementation.
- **Abort:** the trigger condition fired but the adversary
  identifies no risk (purely declarative change) →
  one-sentence rationale, `--skip` with reason.

## Boundary

- **No code review** (= code_review_board, post-implementation).
- **No spec review** (= spec_board, pre-implementation
  pre-test-design).
- **No test-plan author** (= testing skill design mode,
  spec-derivative).
- **No RED skeleton author** (= `test-skeleton-writer` agent,
  downstream).
- **No plan review** (= impl_plan_review, post-MCA-plan).

## Anti-patterns

- **NOT** trigger `adversary_test_plan` on a trivial build.
  INSTEAD respect the trigger condition (≥3 ACs etc.).
  Because: token overhead without benefit.
- **NOT** TC inflation without Augenmaß. INSTEAD 5-10
  high-signal ADV-TCs as the default magnitude. Ratio >2x
  deltas / ACs = stop-and-think trigger, active defence in
  the `proportional_check` block. Because: the Task-459
  pattern (41 TCs / 6 deltas) drives MCA into workaround
  patterns (trivial-green skeletons, implementation that
  only serves tests). Few + binding > many + diluted.
- **NOT** walk pattern classes ritualistically. INSTEAD per
  class check: does THIS code have a plausible trigger? If
  no: into `patterns_excluded` with rationale. Because: race
  conditions aren't universal, compensation bugs need
  multi-step transactions; pattern-class enforcement drives
  inflation.
- **NOT** merge adversary output into test plan v2
  unchecked. INSTEAD Buddy verifies the coverage-rationale
  block + `pattern_class` annotations + `scope_signal` ratio
  plausibility + `patterns_excluded` filled. Because: the
  adversary can produce ritualistic TCs without pattern
  links.
- **NOT** skip `test-skeleton-writer`. INSTEAD RED skeletons
  for ALL adversary TCs as a pre-implementation requirement.
  Because: without the RED phase, MCA can write adversary TCs
  green immediately (NEW-V-001 reproduces).
- **NOT** treat adversary TCs as optional in the MCA brief.
  INSTEAD first-class definition of done. Because: optional
  == ignored in 80% of cases. Augenmaß on the adversary side
  (fewer TCs written) ensures proportional bind pressure.
- **NOT** silent deletion of tester TCs. INSTEAD consolidate
  with a `consolidations` block entry and rationale. Because:
  the adversary may reduce redundancy (EXTENDS mandates
  dropped 2026-05-08), but not without an audit trail.
- **NOT** "include in case it's needed" default. INSTEAD on
  uncertainty: leave out. Because: default-to-include is the
  TC-inflation root. Skill output must have active defence,
  not "could be relevant".

## Bind rule

Subsequent workflow steps must reference adversary TCs
explicitly:

- `delegation-artefact`: adversary TCs as MUST constraints
  (`pattern_class` + count in the brief). Augenmaß discipline
  on the adversary side ensures a proportional set size.
- `mca-implementation`: definition of done = ALL adversary
  TCs PASS.
- `code-review-board`: reviewers check whether all adversary
  TCs PASS and whether the production shape (not the test
  shape) is covered.

## Discipline rationale

Adversary-driven test plan = mechanical pre-fix gate. The
adversary writes tests the implementer cannot think of; the
RED phase verifies the failure mode reproduces. Mechanism >
prompt discipline — a soft mitigation in the MCA brief alone
is systematically missed.

**Augenmaß as the central discipline (Task-459 lesson,
2026-05-08 correction):** an earlier attempt (severity triage
`must / should / could`) was compliance theatre — the
inflation effort was invested; only the bind label differed.
The real problem: writing too many TCs. Solution: the
adversary writes fewer, with an active selection discipline.
`scope_signal.ratio` is the only audit trail;
`patterns_excluded` is the visible selection act; the
consolidation rule prevents redundancy; the stop-and-think
questions are the internal touchstones.

More mechanism would reproduce the same problem ("yet more
rules to follow"). The right answer is a behaviour rule with
a clear selection audit trail — not yet another tagging
layer.
