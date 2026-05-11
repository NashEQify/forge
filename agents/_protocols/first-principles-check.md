# Protocol: First-Principles-Check

Required drill for reviewer / council agents before review output.
A visible section in the review file with a bind rule to findings.

Loaded by every Chief persona of the three boards:

- **Spec Board:** `board-chief` loads + enforces on
  `board-adversary`, `-2`, `-3`, `-implementer`, `-impact`. Plus:
  `council-member`, `solution-expert`, `plan-adversary`.
- **Code Board:** `code-chief` loads + enforces on `code-adversary`,
  `code-quality`, `code-security`, `code-architecture`,
  `code-domain-logic`, `code-reliability`, `code-performance`,
  `code-data`, `code-spec-fit`.
- **UX Board:** `board-ux-heuristic` (primus) loads + enforces on
  `board-ux-ia`, `board-ux-interaction`, and itself.

Chief raises `F-{C|UX}-DRILL-MISSING` when the drill is missing,
re-dispatch limited to 1.

**Intentional exception:** `board-consumer` does NOT load this
protocol — the first-reader role would be disrupted by structured
first-principles reasoning.

## Heading (collision protection)

The section in the review file is named
**`## Reviewer-First-Principles-Drill`** — disjoint from
`## First-Principles-Drill` in `problem_framing/SKILL.md` step 2
(problem-analysis side).

## Drill format

```
## Reviewer-First-Principles-Drill

- **Annahme:** {the author's central assumption — explicit,
  attackable}
- **Gegenfrage:** {a concrete question that would refute the
  assumption}
- **1st-Principle-Ebene:** {class / family of problems — more
  abstract than the assumption; test: a second instance of the
  class beyond the current artifact must be nameable}
```

(The German labels `Annahme`, `Gegenfrage`, `1st-Principle-Ebene`
are kept verbatim because the chief mechanically greps for them —
do not translate the bullet labels.)

## Bind rule (drill ↔ findings)

**At least one finding MUST reference the drill section** (the
assumption OR the counter-question OR the 1st-principle level as
motivation). Without the bind: filler. Chief checks via substring
match.

## Chief rejection mechanic

If the drill or the bind is missing → finding F-C-DRILL-MISSING in
the consolidated output + re-dispatch of the same reviewer with a
hint (context-isolated, append only). No full re-review. Max 1
re-dispatch, then ESCALATE.

## Trigger

Every reviewer / council artifact, every pass. Not for:
bookkeeping, mechanical consolidation without a content judgment.

## Anti-patterns

- **NOT:** filler drill. **INSTEAD:** substance + the bind rule.
- **NOT:** drill AFTER findings. **INSTEAD:** BEFORE findings.
- **NOT:** "1st-principle level" = a rephrasing of the problem.
  **INSTEAD:** name the class; a second instance must be testable.

## Gate rule

Hard gate. Mirror of `problem_framing/SKILL.md` step 2 on the review
side. Enforcement via the chief rejection mechanic above.
