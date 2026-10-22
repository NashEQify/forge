# 09 — Agent Guide

This guide helps an agent enter a Forge workspace without confusing installed
tools with selected work. Canonical contracts and the consumer's rules remain
authoritative; this page is a reading route, not a replacement protocol.

## Start here

1. Establish the active consumer CWD and framework root. Resolve project paths
   against the consumer and framework paths against the framework checkout.
2. Follow the host's primary-session entry and the resolved soul. Delegated roles
   follow their canonical role instead of repeating Buddy boot and bookkeeping.
3. Read the project's intent and rules, then resolve workflow selection through
   the [process map](../framework/process-map.md#workflow-selection).
4. Use the selected boot's scoped recovery and retrieval procedure before relying
   on profile, handoff or topic facts. Follow navigation to the current topic.

`daily` always takes [on-demand boot](../agents/buddy/boot-on-demand.md). A full
install also takes that branch when intent does not select software development.
Do not inspect plans or start engines merely because their files are present.

## Match the work to its owner

| Requested outcome | Entry |
|---|---|
| Maintain or retrieve useful knowledge | [Knowledge Processor](../skills/knowledge_processor/SKILL.md) |
| Save continuity | [Save runbook](../workflows/runbooks/save/WORKFLOW.md) |
| Reconcile context structure and freshness | [Housekeeping](../workflows/runbooks/context_housekeeping/WORKFLOW.md) |
| Clarify a problem | [Frame](../skills/frame/SKILL.md) |
| Examine underlying assumptions | [Bedrock](../skills/bedrock_drill/SKILL.md) |
| Compare independent perspectives | [Council](../skills/council/SKILL.md) |
| Progress selected software work | [Process map](../framework/process-map.md) and its runbook |

Generic reasoning accepts supplied context. Do not create a software task or
persistent repository merely to run a method. On-demand work follows consumer
rules; Forge Councils, boards and workflows require explicit selection there.

## Knowledge handling

Use semantic reconciliation to find the responsible owner before writing. Personal
facts go only to the configured user scope; project facts stay with the project.
If a personal write is blocked, report it as deferred rather than copying it into
a shared project handoff.

[Continuity](../framework/continuity.md) provides snapshot, publish and recover.
Capture required baselines coherently, reason outside locks, and publish conditionally.
A stale result requires recapture and reconciliation. Pending recovery must be
inspected before dependent work; desired text already appearing in one file is
not proof that the whole operation completed.

Maintain useful knowledge during work. Save reconciles owners, navigation and the
handoff. Preserve qualifications and source references, and remeasure changeable
state at resume. Do not write a raw transcript in place of useful continuity.

## Authorization and delegation

A clear bounded implementation request authorizes work in that scope. Diagnosis
and proposals do not authorize implementation. Preserve existing authorization
through ordinary phase transitions and ask only when a real decision or boundary
remains unresolved. Live operations, publication and destructive actions retain
their own consumer-specific boundaries.

Explicit `save` carries the save contract's active-project upstream commit/push
authorization unless local rules restrict it. Continuous knowledge maintenance
alone does not. A separate user repository follows its own Git rules.

When delegating, state the scope, goal, role and success criteria in the required
artifact. Use the selected method's isolation and transport rules. Independent
reviewers receive evidence rather than a desired verdict. Report-only reviewers
return complete artifacts inline; preserve required reports verbatim before
Chief consumption. Verify effective host permissions separately from instructions.

## Development-specific obligations

When software work is selected, follow [agent autonomy](../framework/agent-autonomy.md)
and the chosen runbook for who writes which artifacts. Product code goes to the
implementation role under that discipline; Buddy owns orchestration and decisions.

Bind selected runs and task/plan checks through
[development continuation](../framework/development-continuation.md). Preserve
unfinished bindings across ordinary saves. Restore exact state without invoking a
progression or unpause command. Do not reconstruct state from a handoff excerpt or
select every instance in `.workflow-state/`.

Apply task-status changes through their owner process, then export the current
contribution before common save. Domain blockers may remain visible while unrelated
ordinary work continues; do not hide or silently discharge those obligations.

## Evidence and truthful reporting

Distinguish a protocol requirement, a passing mechanical check and observed behavior.
Check consequential claims against the source and current environment. A file
existing does not establish that a host read it, that a lock excludes external
writers, or that an installed capability works in a fresh session.

For state-changing actions leave the required concise observability line naming
the action, target and reason. Preserve other writers' changes. Keep generated
wrappers and indexes derived from canonical sources, and update live references
when retiring an artifact.

Framework source updates require coordinated stopped-session maintenance. Do not
pull shared runtime sources during boot, bypass managed ownership conflicts or
manufacture validation evidence. Record partial persistence and unverified targets
accurately rather than returning a complete-success claim.

Next: [Human guide](10-human-guide.md) · [Troubleshooting](12-troubleshooting.md).
