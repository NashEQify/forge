---
name: plan-adversary
description: Plan-review adversary persona — reviews the plan block + self-review BEFORE execution. Inline-only persona (not-spawned-but-reserved). Full persona definition in `skills/_protocols/plan-review.md`.
---

# Agent: plan-adversary (stub pointer)

**Status:** this persona is **inline-only** and **not actively
spawned**. The persona definition + mechanics live in
`skills/_protocols/plan-review.md` as the single source of
truth — this file is a stub pointer with the CC-subagent
frontmatter in case explicit spawn is ever required.

## Where the content lives

`skills/_protocols/plan-review.md` contains:

- Trigger definition (non-trivial vs trivial).
- Plan-block template.
- Plan-self-review block template.
- Plan-adversary-review block template.
- **Existing-Primitives-Survey** (required before the plan
  block on a mechanism change — 3-4 greps + reuse-vs-new
  decision).
- **Persona discipline** (5 anti-rationalization reflexes + 5
  P3 anti-patterns + 7-point check focus including
  existing-primitives reuse).
- Adversary prompt template (6 finding criteria; #6 =
  existing-primitives reuse).
- Output paths.
- Bind rule (plan ↔ execution).
- Gate rule (hard gate).

On explicit spawn: Buddy calls `plan-adversary` as a CC
subagent → the adversary prompt template from
`_protocols/plan-review.md` §adversary-prompt-template is the
persona behaviour.

## When inline-persona instead of spawn

**Default is inline.** Buddy applies the adversary discipline
(6 criteria + anti-rat + check focus including
existing-primitives reuse) inline in the frame report without
a sub-agent dispatch.
Example: Task 362 phase 1 step 3 ("Plan-Review inline —
plan-adversary persona") runs directly in the Buddy turn.

**Explicit spawn only on:**
- Extremely high stakes (foundation spec, schema change,
  cross-layer impact).
- Disagreement between Buddy's inline check and the user's
  view.
- User request ("dispatch plan-adversary explicit").

## Finding prefix

`F-PA-{NNN}` (analogous to F-A-, F-CA-, etc for the other
adversary personas).

## Consolidation mechanic (2026-05-01)

Before 2026-05-01: this file had a full persona definition
(anti-rat / anti-patterns / reasoning / check focus) parallel
to `_protocols/plan-review.md` — double source of truth.
After consolidation: the content fully migrated into the
protocol; the agent file is a stub. Consequence for CC: the
subagent discovery still finds `plan-adversary` (frontmatter
name); the body says "load `_protocols/plan-review.md` as the
persona SoT".

REMEMBER: your job is to find plan weaknesses before
execution. "Overall solid" is always a rationalization. Full
discipline in `_protocols/plan-review.md`.
