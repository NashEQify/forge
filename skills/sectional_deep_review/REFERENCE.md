# Sectional Deep Review — Reference

Detail mechanics. Buddy loads SKILL.md for the flow. This file is
reference material for agent-dispatch details, artifacts, and
constraints.

## Boundary

| | spec-board | **sectional-deep** | corpus-review |
|---|---|---|---|
| Specs | 1 | 1 (large) | All |
| Sectional | No | Yes (pattern groups) | By cluster |
| Passes | 1+ (convergence) | Sectional + full + convergence | 2 |
| Cross-ref | No | Yes (in the agent context) | Yes (complete) |
| Agent count | 4-7 | 20-35 | 20-40+ |

## Cross-reference map dimensions

| Dimension | Source | Question |
|-----------|--------|----------|
| Consumed-by | SPEC-MAP | Which specs consume this section? |
| HC / neighbour refs | grep + read | Which places reference this pattern? |
| Code impl | `src/` | Does code exist? Gaps? |
| Consumer specs | SPEC-MAP + read | What assumptions do consumers make? |

## Agent dispatch (overall)

| Phase | Mode | Team | Discourse |
|-------|------|------|-----------|
| Sectional (standard) | Standard | 4 + specialists | Buddy decision |
| Sectional (deep) | Deep | 7 + specialists | ALWAYS |
| Full review | Deep | 7 + specialists | ALWAYS |
| Convergence 2+ | Deep | 4 | ALWAYS |
| Verification | Deep | 2 | No |

Specialists per group (IN ADDITION to the base team):

| Group content | Agent |
|---------------|-------|
| API, Pydantic, schema | code-api-contract |
| Token budget, readability | board-consumer |
| Security, auth | board-adversary-2 |
| Cross-spec interfaces | board-impact |

Typical: ~26-32 agents + discourse + convergence.

## Architecture

```
sectional-deep-review    → WHAT (scoping, grouping, cross-ref, order)
  └── spec_board         → HOW (agents, discourse, convergence)
       └── Board agents  → reviews, findings
```

## Artifact paths

| Artifact | Path |
|----------|------|
| Sectional review | `docs/reviews/board/{spec}-{group}-{role}-pass{N}.md` |
| Sectional verdict | `docs/reviews/board/{spec}-{group}-verdict-pass{N}.md` |
| Sectional discourse | `docs/reviews/board/{spec}-{group}-discourse-{role}.md` |
| Full review | `docs/reviews/board/{spec}-full-{role}-pass{N}.md` |
| Full verdict | `docs/reviews/board/{spec}-full-verdict-pass{N}.md` |

## Session planning

Does not fit in one session. Realistic pacing per spec:

- Session A: phase 0 (prep) + groups 1-2.
- Session B: groups 3-4 + fixes.
- Session C: full review + convergence.

## Constraints

- Dispatch neutral (GAP-03). No Buddy analysis in the prompt.
- Focus points from cross-ref YES, solution hypotheses NO.
- Full review: context-isolated (does not know the sectional
  findings).
- Content preservation on fixes: →
  `_protocols/content-preservation.md`.

## Pre-conditions

- `docs/specs/SPEC-MAP.md` is up to date.
- Target spec exists in `docs/specs/`.
- Neighbour specs exist.
- No uncommitted WIP on the relevant files.
