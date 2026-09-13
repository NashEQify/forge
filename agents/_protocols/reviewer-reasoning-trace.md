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
- **Impact:** {concrete consequence of the strongest finding; if
  none, what the checked scenario establishes and what remains unverified.}
```

## Bind rule (trace ↔ findings)

Connect findings to the checked scenario or its concrete impact.
When findings exist, at least one refers back to the trace. When none
exist, the conclusion links the checked scenario, supporting evidence
and limits to that result. Apply this separately to each reviewed axis.

Chief verifies the trace section and this substantive connection.
A keyword match alone does not establish it; zero findings alone does
not violate it. Missing trace or connection → F-C-TRACE-MISSING,
analogous to F-C-DRILL-MISSING.

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
