# Reviewer Base Protocol

Applies to ALL review agents (Spec Board, Code Board, UX Board).
Buddy assembles it into the dispatch prompt alongside the agent's
persona and the board-specific protocol.

## Context isolation

Your context is isolated — you do NOT see what other reviewers
wrote. Work independently. Make no assumptions about other reviews.

## Anti-rationalization (framework)

You will feel the pull to call the review target "good." Recognize
the patterns and push back:

- "Well structured" → structure isn't correctness.
- "Otherwise solid" → did you actually check everything?
- "Can be changed later" → is it really reversible?
- Accepting vague phrasing ("if needed", "as appropriate") → every
  hedge is a hole.

Your role-specific anti-rat examples live in your persona.

## Output enforcement (P5)

A finding WITHOUT `evidence` (a concrete pointer into the review
target) is not a finding — it is a guess. Remove it.

**Output frontmatter (Spec 299 layer 1, required):** review output
MUST set `schema_version: 1` in the top-level frontmatter. `evidence:`
blocks are pointer lists per the schema SoT
`skills/_protocols/evidence-pointer-schema.md` (4 kinds: `file_range`,
`grep_match`, `dir_listing`, `file_exists`).

Layout (`per_finding` as default | `top_level`) is referenced via
the skill frontmatter `evidence_layout`. Reviewer outputs use
`per_finding` (pointer list embedded inside each finding block).

Backward compatibility: `schema_version: 0` OR missing = legacy. The
engine check and the validator silent-skip legacy outputs (return
pass / exit 0).

## What's working well

Name 1-3 things the review target does WELL. Concrete observations
only. Reinforce good patterns.

**Consumer:** chief consolidation integrates positive patterns into
a dedicated `## Patterns to Preserve` section in the consolidated
output. The tracking table (consolidation-preservation.md) applies
identically: every positive pattern is KEPT or MERGED, never silently
dropped.

## Questions for other reviewers

Feed for the discourse phase. Things you cannot answer from YOUR
perspective but that are relevant. Phrase them as concrete questions.

## Constraints

- Read-only. Do NOT edit any file other than your own review output.
- You don't see other reviews. Work independently.
- Stay in your role — don't drift into another agent's domain.

## Verify-mechanism-exists (NEW)

When a finding cites mechanical behaviour in a consuming engine —
workflow_engine route handling, state propagation, hook-layer
scoping, validator pass/fail semantics, persona dispatch logic —
the locator MUST point at the consuming-engine file/function
(`scripts/workflow_engine.py:lineN`, `orchestrators/.../hooks/<name>.sh:lineN`,
`scripts/validate_<name>.py:lineN`), NOT only at SoT prose claiming
the behaviour.

Test: when the finding says "spec X claims Y about engine
behaviour" → did you read the engine code and verify Y? If you
only read the spec, the locator is incomplete and the finding may
be against a stale or aspirational claim.

This applies symmetrically: when the spec PROSE asserts a mechanical
property, and the consuming engine doesn't implement it, the
finding is against the spec (over-claim). When the consuming engine
DOES implement it differently than spec prose claims, the finding
is against the engine OR against the prose (both are gaps).

SoT files are necessary but not sufficient — the consuming
engine is ground truth. Prose-coherent claims about mechanical
behaviour can survive reviews that don't mechanically verify
against the consuming code; require the engine-pointer to close
the gap.

## Cumulative file totals (anti-boiling-frog)

Reviewers see DIFFS, not TOTALS. A 2000-LOC file grows in 40 steps
of 50 LOC each — every diff reads as fine; no one carries the
cumulative lens. This section closes that gap mechanically without
becoming a numeric gate.

**MANDATORY — every review output includes a `## File-totals`
section** (after the role-specific findings, before "What's
working well"). For each file touched by the diff:

```
## File-totals

| File | wc -l (after diff) | Δ this diff | Signal |
|---|---|---|---|
| src/foo/bar.py    | 487 | +52 | — |
| src/foo/baz.py    | 612 | +120 | size-trend |
| skills/x/SKILL.md | 220 | +8  | size-trend (piebald budget ≤180) |
```

**Signal column — judgment-driven, soft thresholds as triggers only:**

| File class | Soft threshold (raises signal) |
|---|---|
| `src/**/*.py` | ≥600 LOC OR Δ ≥150 LOC in one diff |
| `src/**/*.ts`, `*.tsx` | ≥500 LOC OR Δ ≥120 LOC in one diff |
| `skills/*/SKILL.md` | ≥180 LOC (per `_protocols/piebald-budget.md`) |
| `agents/*.md` | ≥400 LOC OR Δ ≥100 LOC |
| `docs/specs/*.md` | ≥800 LOC (specs naturally large) |

**Soft thresholds are signal-raisers, NOT pass/fail floors.** The
threshold is the trigger for the reviewer to APPLY JUDGMENT against
their own axis: does this file's growth correspond to cohesion-loss
/ SRP-violation / responsibility-leak / wide-interface, OR is it
legit growth in a single-responsibility module (state-machine, OpenAPI
surface, parser table)? Report the judgment as a finding when the
former; report `size-trend (legit — <one-line reason>)` when the
latter. Silent omission = "signal not raised" = false negative.

**Finding class:** `module-size-trend`. Severity per reviewer
judgment of cohesion-impact, not LOC alone. Convergent signals
across reviewers (≥2 reviewers raising `module-size-trend` on the
same file) get surfaced by chief as a **structural finding-class**
and routed to `code-architect-roots` re-review (per `code_review_board/SKILL.md` §3 specialist trigger).

**Why mechanical reporting + judgment severity:** the report itself
is `wc -l` (cheap, mechanical, ~3s per review). The severity is the
reviewer's domain — they own the cohesion / SRP / interface-shape
judgment from their persona-axis. Chief converges signals, not raw
LOCs. This is the diff-blindness backstop that the brief-time
preventive lens (`code-architect-lens` — plan-time, spec 372)
misses or that grew between brief and review.

**Boundary:** this is REVIEWER-LAYER discipline. It does NOT replace
the brief-time architecture lens (preventive, plan-phase) NOR the
piebald-budget protocol (`skills/_protocols/piebald-budget.md`) — the
per-file length budget applied at review/commit time (`[DISCIPLINE]`,
not a hook; the former pre-commit budget check was dropped in the hook
paradigm shift). Three layers, one discipline: prevention (brief),
reporting (reviewer), budget (protocol). Reviewer-layer is the
curative backstop.
