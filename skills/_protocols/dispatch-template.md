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

- Neutral commissioning bounds: the intended user outcome, assignment and edit
  boundaries, the unresolved question, necessary independent
  perspective, model/effort rationale, relevant source/revision paths, requested
  return shape and stopping/escalation condition. These bounds must not reveal
  expected findings, another reviewer’s judgments or a preferred solution. Use
  the applicable delta-review protocol for corrective passes rather than
  importing prior findings into a cold initial review.

- Focus points from the risk assessment (in `code_review_board`
  review brief).
- Reference-material paths (in `sectional_deep_review` cross-ref
  briefs).
- Scope narrowing (in `sectional_deep_review`: "Sections in scope:
  {list}").

The caller retains integration responsibility. Supply the applicable commissioning
requirements and relevant unresolved obligations as neutral outcome and assignment
bounds, so an isolated actor can identify necessary unchecked connections and return
them without expanding its role or edit authority. Apply the agreement comparison
in `framework/work-principle.md` to the actual return against those bounds and the
original parent obligation; retain unmet parent requirements. These bounds must
preserve review isolation and must not convey expected findings, preferred
conclusions or prior reviewer judgments.

## Pre-dispatch check (Buddy, before the agent call)

`Anchoring-free? [Yes — only artifact path + output path + scope]`

`Model: [<model> (<role row>), passed in the call — framework/models.md]`

Buddy checks the assembled dispatch text against the MUST-NOT list
below. If violated: shorten the text — don't post-rationalize.

## What MUST NOT go into the dispatch

- Buddy's own analysis or summary of the artifact.
- Solution preferences or opinions.
- Previous findings or results.
- Hints at known problems or expected findings.

## Captured mandatory software review

Before dispatch intended to satisfy a mandatory result/readiness/completion gate,
load `skills/_protocols/evidence-pointer-schema.md` §9. Resolve the exact owner
first: standalone spec-board owns `agent-dispatch`; nested callers supply their
exact parent owner and retain the existing explicit parent workflow identity.
Capture before current production. For code capture, declare owner-state and all
intended report/decision outputs or dedicated prefixes before enumeration; review
input changes must remain inside the product subject, outside those exclusions.

Consume only successful `--review-capture STEP --id WORKFLOW` stdout as JSON.
Retain its owner and iteration; pass its `review_run_id` and
`review_subject_digest` verbatim, plus the assigned captured `review_slot`, role,
focus and historical references, as neutral commissioning metadata. No private
state-path parsing, status-text derivation or fabricated success envelope.
Require reviewer-base/domain or light-verification §9 loading in the assembled
prompt. The producer echoes the three identity fields with schema version 1.

Before downstream consumption, persist each complete returned payload verbatim,
frontmatter at byte zero. Record actual returned actor identity, selected path and
raw-byte SHA-256 in Buddy's selected references. Preserve prior reports before
canonical replacement. Scope qualifications and dissent are part of the payload;
a summary is not a replacement. Keep historical context separate from current slots.

## Output transport

For standalone reasoning the caller may supply a private temporary execution root
instead of a repository. Output paths and evidence ranges resolve within that root;
Git, task files, durable repository paths and development bookkeeping are not required.
Keep the brief, supplied evidence, attributed complete member returns, consolidation
and decision available through final result assembly. Persist returns verbatim before
Chief consumption even in this temporary mode. The caller owns cleanup under the
host's temporary-storage policy; disclose lack of cross-session recovery unless
retention was explicitly authorized. Missing temporary storage/agent capability is
an execution limit, never permission to fabricate independent review. Development
callers retain their separately selected evidence-placement obligations.

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

Preserve each complete original return once at its owner with provenance. Later
consumers receive the relevant originals or their accessible paths and the
decision context; do not recreate unchanged reports or substitute a summary for
required evidence. A host-supported faithful extraction may avoid manual
re-authoring only when the complete payload and its preservation are verified.
Otherwise retain the complete inline fallback. Concise requested output must
still contain every required finding, evidence pointer, qualification and
meaningful dissent.

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
(`evidence-author-claims.md` §8.3, dispatch-authoring layer).
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
- **Persistent sessions** return through a return artifact (plus the
  host's notification where it has one), not a tool result. Don't peek applies to their transcripts too;
  ownership and integration: `agents/buddy/coordinating-sessions.md`.

SoT: spec 306 §7.2.
