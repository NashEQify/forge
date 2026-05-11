---
name: transparency-header
description: >
  Header formats for delegation, execution, and direct
  conversation. Print on every delegation and task start. No opt-in.
status: active
relevant_for: ["*"]
invocation:
  primary: cross-cutting
  secondary: [hook, workflow-step]
disable-model-invocation: false
uses: []
---

# Skill: transparency-header

Header formats for delegation, execution, and direct conversation.
Print on every delegation to an agent and on every task start —
before delegating or executing. No asking, no opt-in, just always.

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

## Format on a direct response (no active ORIENT block)

Trigger: Buddy answers substantively to a task or question, and no
ORIENT block is active (no task switch in this session, no
hook-resume with a manifest).

Applies to: every boot case (2, 3a, 3b, 1+4) as soon as the user
works substantively.
Does NOT apply to: pure greetings, yes/no answers, acknowledgements
without work content.

Single-line format (inline, before the response):

```
→ DIRECT | Task: <short description of what is currently being done> | Intent: <one sentence or "ad-hoc">
```

Once a context switch (ORIENT block) has happened, DIRECT drops
out for the rest of the active task — ORIENT takes over the role.
On a task switch without a formal switch: print DIRECT again.

Examples:

```
→ DIRECT | Task: adapt boot.md — generalize cross-repo context-path resolution | Intent: keep boot behaviour consistent across consumer repos

→ DIRECT | Task: answer a question about context loading | Intent: ad-hoc

→ DIRECT | Task: file a backlog entry for OBS-001 | Intent: prepare observability for when the harness is up
```

## Rules

- Always print — no opt-in, don't wait for consent.
- Once per delegation / start — not on every intermediate step.
- Compact — each line as long as needed for clarity. Don't
  artificially shorten to one sentence when the derivation needs
  more, but no prose overhead either.
- The source file in parentheses shows where the level is defined.
  No fixed format — it should show what is actually active.
  Examples: `intent.md`, `workspaces/insurance/intent.md`,
  `docs/tasks/042-brain-schema.md`, `direct instruction`.
- The intent tree comes from the active context — don't invent it.
  If the tree is broken: STOP instead of printing the header. That
  is then an intent problem, not a transparency problem.
- Life tasks: `domain (context/life/<domain>.md)` instead of
  `vision`, `objective (workspaces/.../intent.md)` instead of
  `operational` — analogous to `framework/spec-authoring.md`.
- The DIRECT header is required on substantive work without an
  active ORIENT block. "Substantive" = more than acknowledgement /
  greeting. No opt-in, no judgment call.
- DIRECT does NOT replace ORIENT — it is the fallback when no
  switch happened.
- After a context switch (ORIENT printed): DIRECT pauses until the
  next task switch.

## Boundary

- No delegation artifact → framework/spec-authoring.md
  §Delegation-Ready.
- No intent check → operational.md §Advisory Gate (the header is
  output, not a check).
- No observability nudge → operational.md §Observability (the
  one-liner note, a separate requirement).

## Anti-patterns

- **NOT** dropping the header on a short acknowledgement.
  INSTEAD: DIRECT on substantive work, even if short. Because:
  transparency is structural, not proportional.
- **NOT** inventing the intent tree when boot context is unclear.
  INSTEAD: STOP + ask the user. Because: a wrong tree = wrong
  delegation.
- **NOT** printing DIRECT and ORIENT in parallel. INSTEAD: ORIENT
  after a switch, DIRECT as fallback. Because: double output =
  noise.
