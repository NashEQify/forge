# Agentic Design Principles

13 design rules (DR-1 to DR-13) derived from research on agentic systems
(2025/2026). Required reference for every design.
Checked via design_review skill.

**See also:** [arch-doc/04 §26 Agentic Design Principles](../architecture-documentation/04-core-concepts.md) (concept context, use case) ·
solution-expert §entry check step 5 (mechanical checkpoint)

---

## Design rules

**DR-1 Proof Output:** every primitive needs an enforced output block
that proves compliance, not signals it. Not "I did X" —
but "X applies, because: [proof]".

**DR-2 Independent Gates:** every agent checks its own stage independently.
No agent assumes the previous agent worked correctly.

**DR-3 Delta-Check:** no additive write without read-before-write + delta check.
What is already there? What is truly new? What contradicts what?

**DR-4 Freshness:** state-describing elements need a freshness date
or verification trigger. State information without a date is unreliable.

**DR-5 Intent Understood:** every receiving agent must interpret
intent_chain task-specifically (paraphrase), not just copy it.

**DR-6 Plan-Intent Alignment:** every delegation artifact includes an
explicit alignment point between planned approach and intent_chain.

**DR-7 Absorption:** new primitives absorb existing primitives; they do
not merely add to them. DRY applies to agent rules the same way it
applies to code. If two rules govern the same behavior: remove one.

**DR-8 External Memory:** context window is working memory, not storage.
Everything relevant across sessions must be written to external memory.

**DR-9 Checkpoints:** tasks with estimated runtime > 1 session require
mandatory checkpoints. Long operation without checkpoints degrades reasoning.

**DR-10 Scope Boundaries:** no task is delegated without explicit scope
boundaries ("Not yet"). An empty "Not yet" block is not a valid state.

**DR-11 Intent-Driven Naming:** skill names describe intent (what is
achieved), not mechanism (how/on what). No artifact name in skill name.

**DR-12 Source Grounding:** when an agent states the state of an artifact
(spec, code, config, task status), it must verify against the current
artifact, not against derived context (summaries, materializations,
context from previous turns). Derived context is heuristic, not ground truth.
Mandatory source read before: str_replace on spec/code files, consistency
assertions across 2+ artifacts.
Staleness threshold: >5 turns since last read (tier 1), time-based in
harness (Day-N).

**DR-13 No Autonomous Deletion:** no agent may delete tasks, specs,
context files, or other persistent artifacts without explicit user OK.
"Scope creep" or "not authorized" is not a valid reason — the user
decides what stays and what goes. Applies also to artifacts created in
other sessions or by other agents.
Pre-harness: prompt rule in soul.md ("you decide nothing alone") + this DR.
Post-harness: pre-delete hook enforcing user confirmation.

---

## Pre-harness vs. post-harness

| DR | Pre-harness (now) | Post-harness |
|----|---------------------|--------------|
| DR-1 | enforced output block in prompt | mechanical runtime check |
| DR-2 | independent gate checks per stage | middleware gates, schema validation |
| DR-3 | read-before-write + delta check (manual) | conflict detection on DB write |
| DR-4 | boot entropy audit + freshness date | APScheduler + temporal queries |
| DR-5 | transparency header as paraphrase proof | intent_chain schema with validation |
| DR-6 | plan-intent check in delegation artifact | runtime check on agent behavior |
| DR-7 | meta-primitives absorb single rules | harness takes over mechanical rules |
| DR-8 | 3-level loading + flush before discard | FastAPI context assembler |
| DR-9 | session checkpoints for long tasks | session tracing, behavioral metrics |
| DR-10 | explicit scope boundaries always | agent handoff with schema validation |
| DR-11 | intent-driven naming in skills/workflows | naming-convention lint |
| DR-12 | mandatory source read before str_replace + assertions (turn-based) | harness Pattern 3.20: source-grounding gate (tool call blocked without fresh read) |
| DR-13 | prompt rule: no delete without user OK | pre-delete hook enforces user confirmation |
