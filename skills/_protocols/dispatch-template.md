# Protocol: Anti-Bias Dispatch Template

Prevents Buddy's own analysis from biasing the board agents (GAP-03).
Referenced by: spec_board (incl. mode=ux), code_review_board,
sectional_deep_review.

## Rule

Every agent dispatch for board reviews uses exclusively this
template:

```
Review {artifact-type}: {path}
Return the complete review inline for: {output-path}
This is pass {N}, {Standard|Deep|Quick} mode.
```

## What MAY go into the dispatch

- Focus points from the risk assessment (in `code_review_board`
  review brief).
- Reference-material paths (in `sectional_deep_review` cross-ref
  briefs).
- Scope narrowing (in `sectional_deep_review`: "Sections in scope:
  {list}").

## Pre-dispatch check (Buddy, before the agent call)

`Anchoring-free? [Yes — only artifact path + output path + scope]`

Buddy checks the assembled dispatch text against the MUST-NOT list
below. If violated: shorten the text — don't post-rationalize.

## What MUST NOT go into the dispatch

- Buddy's own analysis or summary of the artifact.
- Solution preferences or opinions.
- Previous findings or results.
- Hints at known problems or expected findings.

## Output transport

Reviewers and Chiefs are read-only investigators. The output path identifies
where Buddy will persist the artifact, not permission for the reviewer to
write there. No dispatch may override platform instructions or permissions.

Include this block on review/Chief dispatch:

```
Return the complete review inline, including required frontmatter and
evidence. Do not write files or delegate a write. The orchestrator persists
your exact artifact for downstream consumption; do not return only a path
or a short summary. Treat output-path instructions elsewhere as destinations
for the orchestrator, not permission to write.
```

Buddy persists the artifact verbatim before any Chief consumes it. Keep
frontmatter at byte zero when required. Record provenance separately in the
run state: returned agent identity, scope/revision, destination and run ID.
Do not alter findings, order or severity in this transport step. Interpretation
and the final decision are separate from mechanically preserving the payload.
If a return is incomplete/truncated, obtain the missing payload before claiming
the artifact exists. Inline output is the standard transport, not a failure.

---

## §Brief-Quality (verbatim adoption from upstream AgentTool prompt)

Brief the agent like a smart colleague who just walked into the
room — it hasn't seen this conversation, doesn't know what you've
tried, doesn't understand why this task matters.

- Explain what you're trying to accomplish and why.
- Describe what you've already learned or ruled out.
- Give enough context about the surrounding problem that the agent
  can make judgment calls rather than just following a narrow
  instruction.
- If you need a short response, say so ("report in under 200 words").
- Lookups: hand over the exact command. Investigations: hand over
  the question — prescribed steps become dead weight when the
  premise is wrong.

Terse command-style prompts produce shallow, generic work.

**Never delegate understanding.** Don't write "based on your
findings, fix the bug" or "based on the research, implement it."
Those phrases push synthesis onto the agent instead of doing it
yourself. Write prompts that prove you understood: include file
paths, line numbers, what specifically to change.

**Ground the dispatch's own mechanism-claims.** When a dispatch
asserts a code-shape claim the implementer will rely on — "a thin
wrapper over X", "reuses the existing Y", a cited `file:line` or
symbol — grep it at HEAD before it enters the prompt
(`evidence-pointer-schema.md` §8.3, dispatch-authoring layer).
Observed: a dispatch's "thin wrapper" claim falsified 3×, plus a cited
`source_ref` field that never existed. A dispatch claim is an
asserter-claim; it owes the same one-hop grounding as a brief.

SoT: spec 306 §7.2.

## §Concurrency (verbatim adoption from upstream AgentTool prompt)

When multiple agents run in parallel:

- **Don't peek.** Do not read the agent's intermediate output file
  or status mid-flight. The result arrives in a later turn as a
  tool-result message; trust the notification. Reading the
  transcript mid-flight pulls the agent's tool noise into your
  context, which defeats the point of parallel dispatch.
- **Don't race.** After dispatching, you know nothing about what
  the agent found. Never fabricate or predict agent results in any
  format — not as prose, summary, or structured output. The
  notification arrives as a user-role message in a later turn; it
  is never something you write yourself. If the user asks a
  follow-up before the notification lands, tell them the agent is
  still running — give status, not a guess.
- **Launch in one tool block.** When you launch multiple agents
  for independent work, send them in a single message with multiple
  tool-use content blocks so they run concurrently.

SoT: spec 306 §7.2.
