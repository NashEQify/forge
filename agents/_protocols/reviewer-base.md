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
