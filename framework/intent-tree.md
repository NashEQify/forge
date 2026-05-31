# Intent Tree & Constraint Inheritance

How intent flows in a forge-consuming project. Meta-framework —
describes the structure, not a concrete intent.

## Intent tree

```
intent.md (in folder)              <- vision intent
  -> docs/plan.yaml operational_intent  <- operational intent (build target)
    -> docs/tasks/NNN.md           <- action intent (per task)
      -> agent reasoning           <- action intent (per action, in-head)
```

Every level must be derivable in one sentence from the level above.
If not -> the action has no intent -> STOP.

## Parallel intent trees

A project may carry **more than one** intent tree in parallel —
e.g. a code build-tree (this project's roadmap) and an out-of-band
domain-tree (longer-term concerns the project also tracks). Forge
does not prescribe a specific parallel-tree shape; that is a
consumer-side concern.

When parallel trees exist, each one independently follows the same
"derivable in one sentence from above" rule. Trees are sibling, not
nested — an action under one tree never derives from another tree's
vision.

## intent_chain

Required field for planned work on a build tree:

```
intent_chain:
  vision: <1 sentence — from active intent.md>
  operational: <1 sentence — from plan.yaml operational_intent>
  action: <1 sentence — why this specific task exists>
  trace_id: null   # pre-harness. post-harness: Langfuse/OTel.
```

A consumer with parallel non-build trees declares its own
intent_chain shape for those trees; the rules below apply
identically.

Rules:
- Required on delegation (pre-delegation checklist). No delegation
  without intent_chain.
- Optional in direct conversation. Backfilled when task enters the log.
- Every agent inherits intent_chain from delegation and passes it to subtasks.
- intent_chain is filled by the delegator (typically Buddy).

## Constraint inheritance

Trade-off and constraint hierarchies in
`~/projects/personal/context/user/values.md` are the defaults.
They inherit downward:

```
~/projects/personal/context/user/values.md            <- overarching intent + personal defaults
  +- CLAUDE.md                                        <- global technical constraints (always active)
      ?
        project/workspace intent.md                   <- project-level constraints (can add)
          -> task constraints                         <- task-specific (can add)
            -> agent reasoning                        <- per action
```

`values.md` and `CLAUDE.md` are parallel axes that merge at project
level. A personal-default constraint cannot override a technical
invariant, and vice versa.

Lower levels can **ADD** constraints, never **REMOVE** constraints.
Soft constraints can be REWEIGHTED at lower levels (different priority),
but not deleted. On real conflict, higher level wins.
HARD constraints (marked in values.md) are never overridable and never
reweightable.

## intent.md format

Every intent.md — root, workspace, objective, external project — uses
this format:

```
# Intent — [Name]

## Vision
[Why does this folder exist? What should exist at the end? 1-3 sentences.]

## Done
[How do I know the goal is reached?]

## Non-Goals
[What is explicitly out.]

## Constraint Overrides (optional)
[Which defaults from values.md are different here?
 If no differences: omit section.]

## Context
[Mode signal. Then Boot/On-demand/Not-relevant split.
 Boot = what loads at startup (small, curated).
 On-demand = belongs to scope, loaded when needed.
 Not relevant = what should not be loaded.]
```

## Intent freshness

Before every substantial action (agent check step 0):
Can I write a derivation chain from this action to the active intent?
If not -> STOP. Either wrong task, or stale intent.

Do not continue with stale intent.
Intent tree must reflect reality, not an outdated plan.

## Intent update

When an intent update is needed at any level:

1. Describe the drift — what intent says vs what we actually do
2. Propose updated intent — concrete, in that level's format
3. User confirms (or corrects)
4. Update file — plan.yaml operational_intent, intent.md, etc.
5. Create missing tasks retroactively when needed

Triggered by: save (session review), agent check step 0 (freshness),
obligation 7d.
