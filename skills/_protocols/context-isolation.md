# Protocol: Context Isolation

Prevents anchoring bias in multi-pass reviews.
Referenced by: spec_board (incl. mode=ux), code_review_board,
sectional_deep_review.

## Rule

Fresh-investigation reviewers receive no prior findings. Each such pass
is a new look at the current artifact. This controls the supplied context;
a shared filesystem does not enforce access isolation. Do not consult other
review outputs during fresh investigation.

Targeted fix verification is a separate, explicitly named assignment. It may
receive the prior finding and regression evidence needed to test that fix;
do not present it as a fresh independent search for new defects.

## Fresh-investigation dispatch: MUST NOT contain

- Previous findings (from earlier passes or runs).
- Finding counts or severity distributions.
- Hints about which areas changed.
- Phrases like "check whether fix X resolves the problem".
- Any information that steers the agent toward specific areas.

## Buddy dispatch: MUST contain only

1. Artifact path (spec, code, etc.).
2. Output destination (Buddy persists the returned inline artifact).
3. Agent definition (implicit via agent type).

Identical for EVERY pass — pass 1 and pass N receive the same
prompt.

## Finding tracking

Tracking is the consolidating agent's job (chief), not the
individual reviewer's. The chief maps findings from pass N against
pass N-1.

## Rationale

Empirically demonstrated: tainted passes found 0C/0H on a spec
that, on a fresh look, had 0C/5H. Anchoring on previous findings
turns reviewers into fix-verifiers instead of independent
analysts.
