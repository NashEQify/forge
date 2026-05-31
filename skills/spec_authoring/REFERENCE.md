# Spec-Authoring — Reference

Detail mechanics. Buddy loads SKILL.md for the contract + checklist.
This file holds long-form detail moved out to keep SKILL attention
on the rules.

## Grilling mode (alternative interview shape)

For complex / controversial / high-stakes specs, an alternative
interview mode "grilling":

- **One question at a time** (matches the user TRAIT in `profile.md`
  "max one question per turn").
- **Recommended answer per question** (agent offers its own proposal,
  not just asks).
- **Walk down the decision tree systematically** — don't jump between
  topics.
- **Codebase exploration before the question** when the question is
  answerable from code (agent greps / reads instead of asking).
- **Conflict surfacing:** when user uses a term / concept that
  conflicts with existing CONTEXT.md / spec / ADR → flag immediately
  ("the glossary defines X as Y, but you mean Z — which?").

Triggers for grilling instead of standard:
- Foundation spec (cascading constraints).
- Spec with high user uncertainty.
- Spec with existing-system conflict risk.
- User request ("grill me", "stress-test the design").

Standard vs grilling: standard is multi-aspect, high frequency.
Grilling is single-aspect-deep, recommended-answer-first,
walk-the-tree systematic.

Cross-ref: `skills/improve_codebase_architecture/SKILL.md` phase 3
for the grilling loop on architecture refactor (same pattern,
different domain).

## Solution-space exploration (full sub-step detail)

Mechanic: `skills/frame/SKILL.md` (SoT). 8 sub-steps run as part of
the interview. Especially:

- Sub-step 1: reformulate the problem.
- Sub-step 2: first-principles drill — on foundation specs, run the
  full `bedrock_drill` skill with bedrock map.
- Sub-step 7: ≥3 fundamentally different approaches; null option
  allowed.
- Sub-step 8: happy path / edge case / effort / reversibility +
  recommendation with anti-rationalization.

**Bedrock map as constraint input:** when the drill (step 2)
produced a bedrock map, it flows into the spec as a constraint
source. Physics / logic axioms → hard constraints. "YOUR CHOICE"
axioms → soft constraints with explicit rationale. The bedrock map
is referenced in the frame report and available as context for board
reviewers.

When a council trigger fires after exploration: the council gets the
approaches from the frame report as input (no fresh start).

## Mediator pass-through audit (full detail)

When the spec captures state downstream of a proxy / aggregator /
broker / wrapper SDK, run the 3-question audit BEFORE locking the
capture contract:

1. What does the mediator forward, on what conditions?
2. What does the mediator compute vs pass through?
3. At what timing does each forwarded element arrive?

Document answers in the §-section that defines the capture contract.

**Unverified state:** mark the §-section with `[mediator-audit-pending]`.
The marker MUST be resolved before requesting `spec_board` review;
the board chief checks for the marker during consolidation and raises
a finding if present (no mechanical enforcer yet — see
`docs/tasks/321.{yaml,md}` for the workflow.yaml grep check /
pre-commit hook follow-up).

**DONE for this audit:** either the 3 questions are answered in the
§-section AND no `[mediator-audit-pending]` marker remains, OR the
marker is present AND linked to an open verification task.

The mediator forwards what it forwards, not what you assume —
invisible state stays invisible until production. Recurrence shape:
two adjacent capture contracts (response-cost during streaming +
upstream rate-limit headers) sharing one upstream-pass-through
assumption — both ship as production bugs until the mediator is
bypassed at the relevant capture point.

## Intent alignment validation (format)

```
Intent alignment:
  Received: [distilled intent_chain in 1 sentence]
  Plan: [your own plan in 1 sentence]
  Consistent: yes — [rationale] / no — [deviation, STOP]
```

## Extended anti-patterns (with rationale)

- **NOT** write a spec without solution-space exploration.
  INSTEAD `frame` sub-steps 1-8 as required interview part.
  **Because:** the first solution is almost never the best, and
  without explicit exploration the user falls back on the first one.

- **NOT** treat failure modes as "I'll add later". INSTEAD required
  Phase 2 output. **Because:** P3 FAIL on board review, and the
  author at authoring time is best placed to answer "what can go
  wrong" — later the intuition is gone.

- **NOT** treat `intent_chain` as checkbox. INSTEAD actively derive
  vision → operational → action. **Because:** intent_chain without
  derivation is prose that disambiguates nothing.

- **NOT** author multiple new specs in parallel. INSTEAD sequential,
  with full interview per spec. **Because:** context switching
  between specs leads to shallow interviews and missed edge cases.

- **NOT** ask the user "does the spec look complete?" as meta-question.
  INSTEAD identify specific uncertainties; ask sharp questions with
  agent's own recommendation attached. **Because:** whole-spec
  validation outsources the spec author's job — uncovering gaps the
  user did not see — back to the user.

- **NOT** lock a structural-refactor decision on visible-edge analysis
  only ("single-cycle focus"). INSTEAD trace transitive import graph
  from every entry-point that touches the affected module (per
  `_protocols/mca-brief-template.md` §Structural-refactor pre-lock
  checklist) BEFORE brief locks the decision. **Because:** a brief
  that examines the obvious cycle and misses an adjacent back-edge
  binds MCA to a broken design — implementation correct per spec,
  spec is wrong.

- **NOT** generate two-option questions from handoff / spec
  disagreement without code-grounding first. INSTEAD code-ground
  first, ask only questions that survive grounding. **Because:**
  false dichotomies generated from incomplete grounding send the
  user to choose between two paths neither of which represents reality.

- **NOT** assume mediator pass-through; verify it. INSTEAD run the
  3-question audit (forward-what / compute-vs-pass / timing) before
  locking a capture contract on data downstream of a proxy /
  aggregator / broker. **Because:** the mediator forwards what it
  forwards, not what you assume — invisible state is invisible until
  production.

## Lessons-table

Failure patterns that shaped current discipline. Each entry: the
failure shape + the discipline rule it produced + the SoT for the
rule.

| Anti-pattern | Failure shape | Discipline rule |
|---|---|---|
| **Single-cycle-focus misses transitive cycles** | Brief examines a visible import cycle (A ↔ B), locks decision to break it, MCA implements per spec. Post-implementation a *different* test entry-point fails with ImportError because a back-edge elsewhere in the transitive graph was never inspected. The brief's reasoning was correct for the visible cycle, but the visible cycle was not the whole graph. | Pre-lock checklist for any brief mentioning import / cycle / extraction / move-module: walk transitive imports from every entry-point that touches the affected module, run baseline `pytest --collect-only` on those entry-points, document any prior workarounds with rationale. SoT: `_protocols/mca-brief-template.md` §Structural-refactor pre-lock checklist. |
| **MCA scope-creep on adjacent identical patterns** | Brief locks decision X for field A. MCA implements X for A and "helpfully" applies X to adjacent fields B, C in same file because the pattern looks identical. The brief described the deferral descriptively, not prescriptively. | Briefs MUST forbid adjacent scope-changes by name when migration pattern is reusable. Post-implementation grep: `git diff --name-only` vs brief-named files; anything outside is scope-creep. SoT: `_protocols/mca-brief-template.md` §Anti-patterns + §Structural-refactor pre-lock checklist post-impl grep. |
| **Full-suite tests per fix-pass instead of scope-focused** | Convergence-loop runs `pytest tests/` after every fix-phase, burning 2-3× wallclock without surfacing new signal. The fix touched a documented `file:line` scope; re-testing untouched modules adds noise, not safety. | Brief DoD encodes scope-focused tests + L0 on touched files. ONE full-suite run at convergence-end + pre-deploy + cross-cutting refactor. Re-review on FAIL = single-reviewer pass-1.5 of the finding cluster, not full-board redo. SoT: `convergence_loop/SKILL.md` §Test scope between passes + `code_review_board/SKILL.md` §5 Re-review composition + `_protocols/mca-brief-template.md` §Test/Verification scope. |
| **§-section-amendment without code-grounding** | Amendment drafted from session-handoff text disagreeing with current spec text — both sources stale relative to the code. A two-option question generated from the disagreement became a false dichotomy when code-grounding would have surfaced a third state. Adjacent §-sections (e.g. layout diagrams describing the moved component) also carried drift; the amendment cluster grew to absorb those as stale-cleanup strands. | Pre-edit gate: before amending a §-section that describes code-observable state, grep + read the relevant code. If diverged, reconcile in same commit (CLAUDE.md §Stale cleanup invariant). Architect-dispatched amendments inherit the gate via dispatch contract. SoT: `_protocols/spec-amendment-discipline.md` §Pre-edit code-source-grounding gate. |
| **Implicit mediator pass-through assumption** | Spec captures state at a proxy / aggregator / wrapper-SDK boundary, assumes the mediator forwards upstream state to downstream. The mediator strips / doesn't-compute / doesn't-emit silently. Bug is structurally invisible until production. Concrete recurrence: two adjacent capture contracts (response-cost during streaming + upstream rate-limit headers) sharing one upstream-pass-through assumption — both fixable only by bypassing the mediator at the relevant capture point. | Mediator pass-through audit: 3-question probe (forward-what / compute-vs-pass / timing) on every spec capturing state downstream of proxy / aggregator / broker. Unverified → `[mediator-audit-pending]` marker; resolve before board review (chief checks during consolidation; mechanical pre-lock enforcer is roadmap, not yet implemented). SoT: SKILL.md §Mediator pass-through audit + this REFERENCE §Mediator audit. |
