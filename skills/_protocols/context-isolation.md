# Protocol: Context Isolation

Prevents anchoring bias in multi-pass reviews.
Referenced by: spec_board (incl. mode=ux), code_review_board,
sectional_deep_review.

## Rule

Reviewer agents in pass N receive NO information from pass N-1.
Every pass is a fresh look at the current artifact.

## Buddy dispatch: MUST NOT contain

- Previous findings (from earlier passes or runs).
- Finding counts or severity distributions.
- Hints about which areas changed.
- Phrases like "check whether fix X resolves the problem".
- Any information that steers the agent toward specific areas.

## Buddy dispatch: MUST contain only

1. Artifact path (spec, code, etc.).
2. Output path.
3. Agent definition (implicit via agent type).

Identical for EVERY pass — pass 1 and pass N receive the same
prompt.

## Finding tracking

Tracking is the consolidating agent's job (chief), not the
individual reviewer's. The chief maps findings from pass N against
pass N-1.

## Rationale

Empirically demonstrated (2026-03-25): tainted passes found 0C/0H
on a spec that, on a fresh look, had 0C/5H. Anchoring on previous
findings turns reviewers into fix-verifiers instead of independent
analysts.
