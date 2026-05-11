# Buddy — Context Rules + Operational Details

Two parts: (1) situational rules for context writes, structural
changes, and life-domain work. (2) operational detail extracted out
of operational.md.

Buddy reads this file (Read tool call) before starting any of the
following: context writes, structural changes, life-domain work, or a
mode switch. operational.md points here at the relevant places via
`→ context-rules.md §...`.

## Methodology changes — Buddy's own work, same bar

When Buddy makes methodology changes to the system (processes, gates,
agent behavior, workflows), the same bar applies as for delegated
tasks:
- **Write ACs** — what does the change have to deliver concretely?
- **Test against scenarios** — at least 2-3 realistic scenarios
  simulated (L1 logic / semantic).
- **Don't commit until tests PASS.**
- **Document the eval result** — for prompt changes (agent
  definitions, skills, system prompts): which scenarios were tested,
  before/after results. Either as a comment in the changed file or in
  the commit. Why: prompt phrasing has measurable impact on agent
  behavior — a header rename with the same body can flip the result
  (CC finding: "Trusting what you recall" 0/3 → "Before recommending
  from memory" 3/3, identical body text). Without eval documentation,
  the knowledge of WHY a wording was chosen is lost.

"No delegation without a test plan" applies even when Buddy delegates
to itself. Prose without ACs is not a finished change.

## Consistency cascade on first-principle changes

Any change that affects how agents derive meaning, run processes, or
make decisions — even a small-looking one — triggers a consistency
cascade. The test: "Do other files / agents / processes read this
text and derive behavior from it?" If yes → check immediately.

Buddy runs the cascade with the recursive **IMPACT CHAIN pattern**
(`skills/knowledge_processor/SKILL.md`, step 2): the methodology
change is the initial "information" → LOCATE (every spot that
interprets the concept) → ASSESS (semantically: do logic,
assumptions, and derivations still hold?) → ACT (fix inconsistencies
immediately) → RECURSE (each fix is new information → walk the tree
recursively until exhausted).

This is Buddy's job as orchestrator — Buddy sees the big picture and
recognizes what's affected. A global rule in `CLAUDE.md` →
consistency cascade.

## Consistency-check gate (MUST — after structural changes)

After every structural commit (definition: see
`skills/consistency_check/REFERENCE.md` §Structural commit), the
consistency check is a blocking gate before the next work step. Not
"should run" — same firmness as the History Writing gate.

Flow:
1. Commit contains a structural change → gate active.
2. Run the consistency_check skill.
3. Check reports ERRORS → fix, re-run. Loop until CLEAN.
4. Check reports only WARNINGS or CLEAN → continue.

If the check itself is stale (new paths/patterns it doesn't cover):
update the check first, then run it. That's not a special case — the
check implicitly checks itself, since new paths get reported as
orphaned and dead references to old paths surface.

Post-harness: a pre-commit hook that verifies the path patterns in
consistency_check actually cover the directory structure.
Mechanical, no prompt needed.

## Source-Grounding trigger (DR-12)

When an agent writes an assertion about an artifact AND the last read
of that artifact is more than 5 turns back → **source-read before the
assertion.**

Applies to:
- `str_replace` on spec/code files → reading the target file is
  mandatory.
- Consistency assertions across 2+ artifacts → reading both is
  mandatory.
- Status updates on tasks with a spec reference → reading the spec is
  mandatory.
- Recommendations based on context claims → verify the claim against
  the current state (context names a file path → does the file exist?
  Context names an API endpoint → does it exist? Context names a
  value/status/number → is it still right?). A context claim is any
  statement that comes from a context file, session-handoff, or
  `plan_engine --boot` output and refers to the current state of
  code, infrastructure, or data. "Context says X" is not the same as
  "X is true now".

Does NOT apply to:
- Simple status updates without a spec link (too expensive, low
  risk).
- Reads / greps (those ARE the source check).
- User facts and preferences (rarely change, verification is
  impractical).

Staleness: turn-based (>5 turns). Time-based only in the harness
(Tier 1 has no clock).
Post-harness: Pattern 3.20 Source-Grounding gate (mechanically
enforced).

## Frozen-zone guard

Before every rename, refactor, or batch update:

1. Identify frozen zones: `docs/tasks/archive/`, `docs/specs/archive/`,
   `docs/backlog-archive.md`, `context/history/`, `documents/`.
2. `grep` for the old term in frozen zones — hits are reported, NOT
   replaced.
3. Downstream agents (main-code-agent, sub-agents) get an explicit
   MUST NOT for frozen zones in the delegation prompt.

This applies even when the user prompt doesn't mention frozen-zone
exclusion. Buddy adds it on its own — DR-2 (every agent checks its
own stage).

A reminder: corrections to archived facts go through the corrections
addendum (see STRUCTURE.md), never via mutation.

## Life-domain maintenance

**First-time domain creation:** no objective without a domain file.
When an objective needs a domain that doesn't exist yet:

1. Clarify domain principles with the user ("Are there general rules
   that apply to everything in this area?").
2. Create the domain file (`context/life/<domain>.md`, based on
   TEMPLATE).
3. Update `context/life/overview.md`.
4. Only then: create the workspace + objective.

The domain has to start with substance (principles, constraints),
not as an empty shell.

**overview.md updates:** `context/life/overview.md` does not need to
update on every single status change. Updates can batch — on `save`,
at the end of a work unit, or when Buddy switches the context path.
The information isn't lost (it's in the workspace's backlog.md); the
overview.md is the aggregated view that doesn't have to be
second-precise.

## User-context organization principles

- No rigid categories. The overview structures itself organically.
- From coarse to fine: when the overview gets full, detail moves
  into subfolders.
- Save more rather than less. Detail goes into deeper levels — rarely
  read, costs nothing.
- **Facts** — just store, no clarifying question.
- **Interpretations** — verify briefly before storing.
- Always applies globally (BuddyAI), even inside project contexts.

## History format

`context/history/` is a directory, one file per entry. Frozen zone —
existing entries are never mutated. Applies everywhere, no special
format for external projects.

## Extracted operational details

Detail extracted from operational.md that doesn't need to load on
every boot. operational.md keeps the judgment one-liners; the
context lives here.

### Mode-switch transition matrix

Mode switches are explicit, by the user. Buddy never switches on its
own.

- **Coding → Life:** switch WD to `workspaces/`. Target objective
  unclear → ask.
- **Life → Coding:** flush the context window → switch WD to
  BuddyAI/ root.
- **Life task needs code:** the user switches explicitly. Normal
  coding mode (full delegation, smallest possible context). Life
  context gets flushed.
- **Coding / Life → external project:** start a new `cc <project>`
  call.
- **External project → Coding / Life:** new `cc` or `cc life` call.
- **External project → external project:** new `cc <project>` call.
- **Mid-session switch to external: NOT supported.**
  CC limitation: --add-dir and the project root are startup
  parameters. The project CLAUDE.md isn't auto-enforced and
  .claude/agents isn't updated.

### User facts — explicit, not automatic

User facts (people, places, preferences, hardware, events) are NOT
extracted automatically. When the user wants facts persisted, they
say so explicitly; Buddy then calls
`knowledge_processor (mode=user-signal)` against
`~/projects/personal/context/user/`. No background mechanism, no
per-turn gate, no hook.

Background: an earlier active FACTUAL pipeline (Stop+SessionEnd
hooks, background agent on user transcripts) was retired without
replacement on 2026-05-03 — it worked unreliably, wrote silently
into a user path without per-session authorization, and the outcome
was not verifiable.

### Brain logic during incidents

During an active incident (Phase A Root-Cause-Fix): context writes
(ACT phase) are deferred until the fix is finished.

### SCR — state verification after agent interrupt

**Trigger:** user interrupt or agent cancel during a dispatch.

**Problem:** tool interrupts don't reliably land before agent
completion. An agent can run silently to the end before the
interrupt is processed in the CC harness. The user intent was
"stop", but the state is "completed" — a silent-completion race.

**Rule:** after every tool interrupt or agent cancel, Buddy must
check the actual filesystem / git state BEFORE planning the next
action or doing a rollback. Cancel signal != stable state.

**Proof output:** `git status --porcelain` + relevant file stat.
If file changes are detected: report them explicitly and clarify
with the user whether that was the expected completion or a race.

**Hook coverage (planned):** PostToolUse hook after `ExitPlanMode`
or agent completion that, on interrupt detection, injects
`git status --porcelain` into Buddy's additionalContext for the
next UserPromptSubmit. With the hook: net zero mental load (the
hook handles trigger + content injection).
