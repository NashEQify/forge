# Protocol: Analysis Mode Gate

Forces the agent into substantive mode before any classification act.
Mechanical gate enforcement via a proof sentence + grep-checkable
binding. Addresses session-99 pattern B (mechanical-as-default) — this
protocol replaces the earlier CLAUDE.md invariant "content before
mechanism": instead of a prompt nudge, here is a checkable gate.

Loaded by: `frame/SKILL.md` step 4, `spec_board/SKILL.md`
§Consolidation, `knowledge_processor/SKILL.md` extract phase.

## The rule — proof sentence with 3 elements

Before every **classification act** (deciding which hits / findings
go into the solution space / the consolidated list / the scope), a
required proof sentence visible in the output:

```
Analysis-mode proof:
- Intent reconstruction: {What does the author / the artifact
  REALLY want here? In your own words, not a paraphrase of the
  text wording.}
- Effect simulation: {What happens when an agent / user reads
  this and acts on it? Concrete scenario, not abstract.}
- Model naming: {Which class / mental model lies underneath?
  Mark instance vs class.}
```

## Bind rule (proof ↔ content coupling)

**Without the bind, the proof is filler.** The subsequent analysis
MUST reference at least one proof element by name or anchor a
decision in it.

**Proof-element keywords (mechanically checkable):** `Intent`,
`Effect`, `Model` (plus aliases `Intent reconstruction`, `Effect
simulation`, `Model naming`). Consumer skills check the bind via
`grep -c` on these keywords in the analysis outside the proof
section itself. Zero count = filler compliance, **rejected**.

Example: "The finding picks up the effect simulation: {scenario}"
— contains the keyword `Effect`, valid bind.

## Granularity — one proof per classification act

**One proof sentence per CLASSIFICATION ACT, not per tool call.**
For 15 grep calls with a shared classification goal, one proof
sentence framing the whole is enough. For 3 separate classification
acts (e.g. repo check + finding merging + cross-phase mapping),
3 proof sentences are required.

## Trigger — when does the gate fire

After every operation that flows into a **scope / solution space /
finding / scope decision** — independent of hit count. Pure file
reading without a decision is exempt. No proof sentences for
bookkeeping, capture, mechanical status updates.

## Output-path matrix (per consumer)

| Consumer | Where the proof sentence goes |
|-----------|-------------------------------|
| Reviewer agents (board-*) | review file as a section before findings |
| Chief agent | consolidated file before the tracking table |
| frame in solve | state-file phase 1 body |
| frame in build/fix | inline in the frame report |
| frame in scoping/council | inline in the elicitation/briefing |
| knowledge_processor | inline in the process output |

The output path is part of gate fulfilment — the proof must appear
in the artifact the consumer checks for gate evidence.

## Quick-mode hardening

In quick mode one-sentence answers per element are enough. Each
sentence must be verifiable (no tautology) and specific enough that
it could not fit any other run.

**Bad (not accepted):** Intent "Goal is clarity" / Effect "It gets
better" / Model "Design decision" — pure tautologies.

**Good (accepted):** Intent "Cross-phase findings from run X must
not be lost" / Effect "Agent Y classifies 18 parked findings into 4
status values" / Model "Finding-based source grounding (vs DR-12)".

## Anti-patterns

- **NOT:** proof paraphrased / abbreviated. **INSTEAD:** substance
  per element, specific.
- **NOT:** proof AFTER the analysis as justification. **INSTEAD:**
  BEFORE the analysis.
- **NOT:** mistaking "model" for "approach". **INSTEAD:** model =
  building blocks + interaction + load-bearing assumption.
- **NOT:** finding list without proof-back-reference. **INSTEAD:**
  at least one finding references a proof element by name (bind
  rule).

## Gate rule

**Hard gate** — proof sentence AND bind are required. Consumer
skills reject analyses without proof or without a visible bind.
Re-dispatch the agent only with a hint at the missing section (no
full re-review).
