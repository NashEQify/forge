# Code Review Board — Reference

Detail mechanics. Buddy loads SKILL.md for dispatch. This file is
reference material.

## L2 phases (detail)

1. SCOPE + REVIEW BRIEF (Buddy).
2. L0 static analysis (MCA already ran it; Buddy checks the
   return).
3. PARALLEL agent reviews (context-isolated).
4. CHIEF-1 consolidation (L2 only) — dedup, severity ranking,
   noise filtering.
5. DISCOURSE (L2 only, optional).
6. CHIEF-2 synthesis (L2 only) — confidence adjustment.
7. VERDICT.

## Content preservation on fixes

→ `skills/_protocols/content-preservation.md` (SoT).
Defensive code (timeout guards, fallback paths) is not removed
just because the happy path doesn't exercise it.

## Extended output paths

| Artifact | Path |
|----------|------|
| Agent reviews | `docs/reviews/code/{task-id}-{role}.md` |
| Consolidated | `docs/reviews/code/{task-id}-consolidated.md` |
| Discourse | `docs/reviews/code/{task-id}-discourse-{role}.md` |
| Verdict | `docs/reviews/code/{task-id}-verdict.md` |

## Agent overview

| Agent | Focus | L1 | L2 |
|-------|-------|----|-----|
| code-review | Correctness + architecture + performance (3 axes) | ✓ | ✓ |
| code-adversary | Smart-but-wrong, race conditions | ✓ | ✓ |
| code-security | Auth, injection, validation | — | ✓ |
| code-domain-logic | State machines, business rules | — | ✓ |
| code-reliability | Observability, failure recovery | — | ✓ |
| code-data | Schema, queries, migrations | — | ✓ |
| code-api-contract | REST, schema pipeline, SSE | — | ✓ |
| code-ai-llm | Prompt, model, token budget | — | ✓ |
| code-docs-consumer | Code docs + spec readability | — | ✓ |
| code-chief | Consolidation, discourse synthesis | — | ✓ |
| code-spec-fit | Spec conformance | — | ✓ + spec_ref |
| code-spec-drift | Retroactive spec drift | — | ✓ + retroactive |

**Multi-axis persona:** code-quality + code-architecture +
code-performance were absorbed into code-review as a 3-axis
persona. Axis marker in findings:
`Axis: Correctness | Architecture | Performance`. Drill+Trace per
axis is required.
