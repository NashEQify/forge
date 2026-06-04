---
name: transparency-header
description: >
  Header formats for delegation, execution, and direct action — the
  user's at-a-glance scan of what was done and why across parallel
  sessions. Triggers when a turn delegates, executes, or takes a
  state-changing / decision-bearing direct action; pure discussion and
  acknowledgements are exempt (the prose is the record).
status: active
relevant_for: ["*"]
invocation:
  primary: cross-cutting
  secondary: [hook, workflow-step]
disable-model-invocation: false
uses: []
---

# Skill: transparency-header

Header formats for delegation, execution, and direct action — printed
before the work, on the turns that *do* or *decide* something.

## Why this exists (read before treating it as ceremony)

The user runs many sessions in parallel and loses track of which
threads are open across them. This header is his at-a-glance scan —
*what was done this turn and why* — so he can reconstruct the open
threads without re-reading the full transcript or a diff.

It serves the **user's observability, not the agent's task.** That
asymmetry is the whole point: a step with no task-local payoff is the
first thing an agent drops under cognitive load — which is exactly how
this convention frayed before (high-frequency, thin in-the-moment why,
dropped silently across a long session). The fix is not more rigidity;
it is keeping the why present at the trigger and firing only where the
header carries signal. When it's gone, the user is flying blind across
his parallel work.

## When it fires (action / decision bound)

Fire the header on a turn that **delegates, executes, or takes a
state-changing / decision-bearing direct action** — the turns where
the work is opaque to the reader (an agent ran, a file changed, a
decision was locked) and the what/why isn't already visible in the
response prose.

Do **not** fire it on pure discussion, questions, analysis, or
acknowledgements ("ok", a yes/no answer, a greeting): there the prose
*is* the record, and an empty `Intent: ad-hoc` header is noise that
dilutes the signal. This is the same frequency as
`CLAUDE.md §Observability` (action-bound — "skip it for analysis or
discussion"): the header is the structured turn-level form of that
discipline, not a competing every-turn rule.

Judgment cost is trivial: *did this turn do or decide something?* Yes
→ header; just talk → none.

## Format on delegation

```
→ DELEGATED
  From:    <who delegates — e.g. Buddy>
  To:      <target agent — e.g. main-code-agent / solution-expert>
  Task:    <task ID + title, or short description if there is no task entry>
  Intent:  <one sentence — why this task exists>
  Intent tree:
    vision (intent.md):       <derivation from the vision level>
    operational (plan.yaml):  <derivation from the operational intent>
    action (task NNN):        <concrete task / direct instruction>
```

## Format on task execution

```
→ EXECUTING
  Agent:   <who is executing>
  Task:    <task ID + title, or short description>
  Intent:  <one sentence>
  Intent tree:
    vision (intent.md):       <derivation from the vision level>
    operational (plan.yaml):  <derivation from the operational intent>
    action (task NNN):        <concrete task / direct instruction>
```

## Format on a direct action (no active ORIENT block)

Trigger: a turn where Buddy himself does or decides something on the
orchestrator path (edits a file, runs a state-changing op, locks a
decision) without a formal ORIENT switch.

Single-line format (inline, before the response):

```
→ DIRECT | Task: <short description of what is being done> | Intent: <one sentence>
```

Once a context switch (ORIENT block) has happened, DIRECT drops out
for the rest of the active task — ORIENT takes over the role. On a
task switch without a formal switch: print DIRECT again.

Examples:

```
→ DIRECT | Task: adapt boot.md — generalize cross-repo context-path resolution | Intent: keep boot behaviour consistent across consumer repos

→ DIRECT | Task: lock the verdict on the store_fact placement decision | Intent: adopt the council outcome before authoring the brief

→ DIRECT | Task: file a backlog entry for OBS-001 | Intent: prepare observability for when the harness is up
```

## Rules

- Print on action / delegation / decision turns — before the work,
  not after. Pure discussion and acknowledgements: no header.
- Once per delegation / start / action — not on every intermediate
  step. The inline `CLAUDE.md §Observability` one-liner
  (`{action} → {target} ({reason})`) covers intermediate
  state-changing steps within a turn.
- Compact — each line as long as needed for clarity. Don't artificially
  shorten when the derivation needs more, but no prose overhead either.
- The source file in parentheses shows where the level is defined.
  No fixed format — it should show what is actually active. Examples:
  `intent.md`, `workspaces/insurance/intent.md`,
  `docs/tasks/042-brain-schema.md`, `direct instruction`.
- The intent tree comes from the active context — don't invent it. If
  the tree is broken: STOP instead of printing the header. That is then
  an intent problem, not a transparency problem.
- Life tasks: `domain (context/life/<domain>.md)` instead of `vision`,
  `objective (workspaces/.../intent.md)` instead of `operational` —
  analogous to `framework/spec-authoring.md`.
- DIRECT does NOT replace ORIENT — it is the fallback when no switch
  happened. After a context switch (ORIENT printed): DIRECT pauses
  until the next task switch.

## Boundary

- No delegation artifact → framework/spec-authoring.md §Delegation-Ready.
- No intent check → operational.md §Advisory Gate (the header is
  output, not a check).
- Intermediate state-changing steps → `CLAUDE.md §Observability`
  one-liner (`{action} → {target} ({reason})`): same action-bound
  frequency, inline rather than structured. The header is the
  turn-level form; the one-liner is for sub-steps.

## Anti-patterns

- **NOT** withholding the header on an opaque action turn (a
  delegation, a file edit, a locked decision) just because the turn is
  short. INSTEAD: header whenever the work isn't visible in the prose.
  Because: the reader cannot see what an agent did or what changed; the
  header is his only window onto it.
- **NOT** firing the header on a pure-discussion or ack turn to be
  "safe". INSTEAD: no header — the prose is the record. Because: an
  empty `Intent: ad-hoc` header is the rote, high-frequency, thin-why
  ritual that made this convention fray and read as ignorable; volume
  without signal is what kills it.
- **NOT** inventing the intent tree when boot context is unclear.
  INSTEAD: STOP + ask the user. Because: a wrong tree = wrong
  delegation.
- **NOT** printing DIRECT and ORIENT in parallel. INSTEAD: ORIENT
  after a switch, DIRECT as fallback. Because: double output = noise.
