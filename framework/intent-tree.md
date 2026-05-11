# Intent Tree & Constraint Inheritance

How intent flows in the BuddyAI system. Meta-framework — describes the
structure, not a concrete intent.

## Intent tree

```
intent.md (in folder)              <- vision intent
  -> docs/plan.yaml operational_intent  <- operational intent (build target)
    -> docs/tasks/NNN.md           <- action intent (per task)
      -> agent reasoning           <- action intent (per action, in-head)
```

Every level must be derivable in one sentence from the level above.
If not -> the action has no intent -> STOP.

## Life-domain intent (parallel, not below)

Life domains live under `context/life/` and run parallel to the
build-intent tree.
`intent.md` in BuddyAI root describes the system vision (why BuddyAI exists).
Life domains describe the user's life goals (independent of BuddyAI).
Objectives in `workspaces/` derive from domains, not from
BuddyAI/intent.md.

```
context/life/<domain>.md              <- life domain (stable value space)
  -> workspaces/<objective>/intent.md <- objective (concrete initiative)
    -> docs/tasks/NNN.md              <- action
```

## intent_chain

Required field for planned work. Two variants:

**Build tasks** (BuddyAI development, technical projects):
```
intent_chain:
  vision: <1 sentence — from active intent.md>
  operational: <1 sentence — from plan.yaml operational_intent>
  action: <1 sentence — why this specific task exists>
  trace_id: null   # pre-harness. post-harness: Langfuse/OTel.
```

**Life tasks** (objectives under life domains):
```
intent_chain:
  domain: <life domain + core principle>
  objective: <objective intent from workspace intent.md>
  action: <1 sentence — why this specific task exists>
  trace_id: null
```

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
  +- context/life/<domain>.md                         <- domain constraints (for life tasks)
      ?
        project/workspace intent.md                   <- objective/project constraints (can add)
          -> task constraints                         <- task-specific (can add)
            -> agent reasoning                        <- per action
```

CLAUDE.md and domain.md are parallel axes that merge at project level.
A domain constraint cannot override a technical constraint, and vice versa.

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
4. Update file — plan.yaml operational_intent, intent.md, or domain.md
5. Create missing tasks retroactively when needed

Triggered by: save (session review), agent check step 0 (freshness),
obligation 7d.

## Life-domain format

Every domain file under `context/life/<domain>.md`:

```markdown
# Domain — [Name]

## Principles
[What matters in this life area. 3-5 sentences.]

## Constraints
[Hard and soft boundaries. Format like values.md.]

## Health Indicators
[How do I recognize that this domain is going well/poorly?]

## Active Objectives
[Reference to workspaces/<objective>/intent.md. Or: none.]
```

Max 200 lines. Domain is created when the first objective needs it.
Buddy performs first-time domain setup in discussion mode (advisory gate).
