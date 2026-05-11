# Protocol: Reviewer-Reasoning-Trace

Required section for reviewer / council agents before review output.
Covers reasoning steps 1 (Intent), 2 (Plan), 3 (Simulate), 5
(Impact). Step 4 (First Principles) lives in a separate protocol
(`first-principles-check.md`).

Loaded by every agent that loads `first-principles-check.md` — the
two protocols are companions. Chief checks both. See
`first-principles-check.md` §Loaded-by for the full list (Spec
Board, Code Board, UX Board). Exception: `board-consumer` stays
excluded (first-reader role).

## Heading (collision protection)

The section in the review file is named
**`## Reviewer-Reasoning-Trace`** — disjoint from
`## Reviewer-First-Principles-Drill` (first-principles-check.md) and
`## First-Principles-Drill` (problem_framing step 2).

## Trace format

```
## Reviewer-Reasoning-Trace

- **Intent:** {what is this artifact supposed to enable? One
  sentence, your own words.}
- **Plan:** {how do I approach this review? Focus areas, order.}
- **Simulate:** {a concrete scenario played against the artifact.
  Input → expected behaviour → actual behaviour per the artifact.}
- **Impact:** {if my most important finding is NOT fixed — what
  happens concretely? Who is affected, what downstream breaks?}
```

## Bind rule (trace ↔ findings)

**At least one finding MUST refer back to the trace section** —
typically to Simulate (the scenario surfaced the finding) or Impact
(the finding's severity follows from impact). Without that link the
trace is filler and the findings are ungrounded.

**Mechanical check (grep keywords):** Chief verifies that at least
one finding contains one of the keywords `INTENT`, `PLAN`,
`SIMULATE`, or `IMPACT` (uppercase). Analogous to the
first-principles-check keywords (`Annahme`, `Gegenfrage`,
`1st-Principle`).

Chief verifies: (1) `## Reviewer-Reasoning-Trace` heading present,
(2) ≥1 finding contains INTENT|PLAN|SIMULATE|IMPACT. Missing →
F-C-TRACE-MISSING, analogous to F-C-DRILL-MISSING.

## Interaction with first-principles-check

The two protocols are **complementary, not redundant**:

| Protocol | Step | Asks | Checks |
|---|---|---|---|
| reasoning-trace | 1 Intent | What is the artifact for? | Reviewer understood the purpose |
| reasoning-trace | 2 Plan | How do I review it? | Reviewer isn't working at random |
| reasoning-trace | 3 Simulate | Concrete scenario? | Reviewer tested against reality |
| first-principles-check | 4 First Principles | Which assumption is attackable? | Reviewer probed the bias layer |
| reasoning-trace | 5 Impact | What if not fixed? | Severity is grounded |

Order in the review file: `## Reviewer-Reasoning-Trace` BEFORE
`## Reviewer-First-Principles-Drill`. The trace is preparation, the
drill is depth.

## Trigger

Every reviewer / council artifact, every pass. Not for: bookkeeping,
mechanical consolidation without a content judgment.

## Anti-patterns

- **NOT:** copy-pasting the artifact title as "Intent". **INSTEAD:**
  your own words; shows understanding.
- **NOT:** "I'll look at everything" as "Plan". **INSTEAD:**
  concrete focus areas and order.
- **NOT:** a hypothetical scenario without concrete input.
  **INSTEAD:** "When agent X gets prompt Y, then Z happens per the
  artifact."
- **NOT:** "could cause problems" as Impact. **INSTEAD:** concrete
  downstream break with the affected component / person.
