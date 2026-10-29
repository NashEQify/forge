# Documentation and ADRs — independent verify-pass

Step-loaded unit of `skills/documentation_and_adrs/SKILL.md`. Read it when an artifact you author names or cites code
mechanics, before the artifact is treated as authoritative, and before changing the verify-pass trigger or tiers.

## Independent verify-pass (code-mechanics claims)

The author is the worst checker of their own mechanical claims:
evidence-pointer-at-write (`framework/invariants.md` Inv 10) makes a claim auditable
but does NOT catch a MISREAD — the author can cite the right line and
still conclude wrong. The only thing that catches a misread is an
independent reader. So for the artifact class most prone to it, the
verify-pass is a **default, not a user-initiated "send it to council"**.

Design rationale + the rejected alternatives: **ADR-008**
(`docs/decisions/ADR-008-independent-verify-pass-semantics.md`). Read it
before changing the trigger or the tiers — the semantics below are a
deliberate hard-to-reverse call, not a default.

### Trigger — observable signal, NOT author self-assessment

The firing condition must NOT rest on the author judging "is my claim
consequential?" — that re-imports the exact author-lens the discipline
distrusts, and lets a misreading author self-declare out of the check
(the under-coverage failure). Fire on an OBSERVABLE property instead:

> **The artifact NAMES or CITES code mechanics** — a code symbol, a
> `file:line`, a hook / check / engine-field / step name, or a sentence
> asserting what a subsystem *does* ("the engine reads X", "the hook
> blocks Y", "A publishes to B"). If it does → the verify-pass fires by
> DEFAULT.

Skip is allowed only on a SHORT, explicit, RECORDED exception — never a
silent self-waiver:

- the artifact is throwaway scratch (not propagated, not authoritative);
- the claim is trivially self-evident at the cited line (a one-token
  read, no interpretation);
- the claim is reversible within the session and nothing downstream acts
  on it yet.

A skip costs a one-line reason next to the claim (`verify-pass skipped:
<which exception>`), so the skip is itself auditable. Default = fire;
the burden is on skipping, not on firing. (Contrast the ADR-triple in `SKILL.md`,
which gates AGAINST inflation — here under-coverage is the enemy, so the
bias is reversed: fire broadly.)

### Two tiers — breadth by default, depth by stakes (Hybrid, ADR-008)

A single same-model cold-start reader does NOT reliably catch a misread
— empirically the historical misreads were caught by a human + a
multi-perspective council, not one cold reader. So the floor is honest
about its ceiling, and stakes escalate depth:

- **Floor (default, broad):** dispatch ONE context-isolated cold-start
  reviewer that reads the cited code and returns a verdict. It RAISES
  the odds of catching a misread; it does NOT guarantee it. Cheap, fires
  on the whole observable-signal class — this is the breadth that closes
  the under-coverage gap.
- **Stakes-escalation (depth):** when the code-claim is
  consequential/hard-to-reverse (a downstream consumer will act on it as
  authority — schema, contract, public surface, a claim that gates other
  work), escalate to MULTI-perspective: ≥2 different lenses / an
  adversary / a council. One reader is structurally insufficient for the
  misread at this stakes level; the diversity is the catch.

Stakes here gate DEPTH (floor vs multi-perspective), never WHETHER the
pass fires — that is the §Trigger's observable signal. This is the
correction of the original single-tier design (see ADR-008).

### Reviewer contract + Invariant-1 boundary

The verify-pass is a DISPATCHED reviewer, never Buddy self-verifying —
Buddy dispatches + reads the verdict signal (Invariant 1: Buddy is the
dispatcher, not the verifier). The reviewer is context-isolated per
`skills/_protocols/dispatch-template.md` and returns:

- a verdict label — `CLAIMS-HOLD` / `CLAIMS-HOLD-WITH-NITS` /
  `CLAIMS-BROKEN`;
- per claim checked: an evidence pointer
  (`skills/_protocols/evidence-pointer-schema.md`) to the line it read;
- the lens it used (so "different lens" is shown, not asserted).

`CLAIMS-BROKEN` blocks the artifact from being treated as authoritative
until re-authored + re-passed.

### Enforcement class (honest)

This is **[WORKFLOW] / [DISCIPLINE]**, not **[STRUCTURAL]**: there is no
pre-commit hook and no script that fires it. It is wired as a contract of
THIS skill — when `documentation_and_adrs` is invoked (the close-bookkeeping
ADR sub-step in build / solve, see `SKILL.md` §When to use) AND the
§Trigger's observable signal is present, running the verify-pass is part
of the skill's DONE. That is as mechanical as it gets without a hook; do
not over-state it as automatic enforcement. The pre-commit
SOURCE-VERIFICATION check governs *reviewer* outputs (machine-checked
pointers); this governs *authored* artifacts (a dispatched reader
verifies the claims).
