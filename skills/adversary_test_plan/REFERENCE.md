# adversary_test_plan — REFERENCE

`SKILL.md` is the operational contract. This file holds detail:
full YAML schemas, Augenmaß touchstones, full red-flags list,
common-rationalizations table, discipline rationale.

---

## Adversary TC schema

Per adversary TC in the extended test plan v2:

```yaml
- id: ADV-TC-{N}
  pattern_class: "{NEW-V-001 | Compensation-Bug | Cycle-Entry-Point | Cleanup-Tx-Silent-Ack | Smart-but-Wrong | Stale-State | Race-Condition | ...}"
  scenario: "<concrete scenario, 1-3 sentences>"
  setup: "<minimal test setup>"
  assertion: "<exact assertion — what MUST PASS after the fix>"
  rationale: "<why the implementer's cognitive bias would miss this>"
  level: "L2|L3|L4"
```

## Coverage rationale block schema

Required at the end of the extended test plan v2:

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
                               # an entry with merged set + rationale
  spec_assumption_diff: "<which spec assumptions are non-trivially testable?>"
  implementer_blindspots: "<which edge cases would implementer bias have missed?>"
```

## Augenmaß: 3 stop-and-think questions

Per potential TC, before adding:

1. **"Would the implementer ACTUALLY miss this?"** — when the
   answer is hypothetical or speculative ("could be missed"), the
   TC is weak. The adversary mindset demands concrete pattern-
   replay evidence or a spec-authority gap, not "conceivable
   mistakes".

2. **"Does this pattern class have replay evidence for THIS
   code?"** — race conditions are not universally relevant.
   Compensation bugs need multi-step transactions. When the code
   has no plausible trigger for the pattern class, the class
   doesn't belong in the test plan.

3. **"Is this an honest new probe or a setup variation of an
   existing TC?"** — second answer: consolidate instead of adding
   (see consolidation rule below).

## Consolidation rule

EXTENDS mandates dropped 2026-05-08. The adversary may flag +
consolidate existing tester TCs as redundant variations when a
clean reduction is visible.

Test plan v2 comment:
`# consolidated: TC-X+TC-Y → ADV-TC-N (rationale)`.

Consolidation requires rationale per merged set. Pure deletion
without consolidation is forbidden — only replace-with-rationale.

## Red flags (full)

- Adversary returns only 1-2 TCs ("looks fine") — pattern lessons
  not taken seriously, adversary mindset not active.
- Adversary TCs have no `pattern_class` annotation — no pattern
  discipline, just arbitrary tests.
- Adversary TCs are all happy-path variations — adversary violates
  the mandate ("smart-but-wrong" not active).
- `implementer_blindspots` block empty or "n/a" — pattern-coverage
  rationale missing.
- **TC inflation: ratio >2x deltas / ACs without active rationale**
  — Task-459 pattern (41 TCs / 6 deltas = 6.8). Indicator: the
  adversary uses pattern-class enforcement as boilerplate coverage
  instead of Augenmaß. Re-dispatch with a stop-and-think reminder.
- **`patterns_chosen` contains all ~7 classes with ritualistic
  rationale** ("could-apply" / "defence-in-depth") — pattern-class
  coverage no longer required. Active selection, not blanket cover.
- **`patterns_excluded` empty** — the adversary did not actively
  choose what to leave out. Augenmaß without a visible selection
  act is unverifiable. Audit trail missing.
- **Consolidation without rationale** — the adversary may
  consolidate, but every consolidation needs an entry in
  `consolidations` with rationale. Consolidation without rationale
  = silent deletion.
- Test plan v2 has fewer ADV-TCs than the adversary considered
  internally — **correct** (Augenmaß discipline), NOT a red flag.

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

## Discipline rationale (Task-459 lesson)

Adversary-driven test plan = mechanical pre-fix gate. The adversary
writes tests the implementer cannot think of; the RED phase verifies
the failure mode reproduces. Mechanism > prompt discipline — a soft
mitigation in the MCA brief alone is systematically missed.

**Augenmaß as the central discipline (Task-459, 2026-05-08
correction):** an earlier attempt (severity triage `must / should /
could`) was compliance theatre — the inflation effort was invested;
only the bind label differed. The real problem: writing too many
TCs.

Solution: the adversary writes fewer, with an active selection
discipline. `scope_signal.ratio` is the only audit trail;
`patterns_excluded` is the visible selection act; the consolidation
rule prevents redundancy; the stop-and-think questions are the
internal touchstones.

More mechanism would reproduce the same problem ("yet more rules to
follow"). The right answer is a behaviour rule with a clear
selection audit trail — not yet another tagging layer.
