# 06 — Usage and workflows

Describe the desired result, relevant context and boundaries. Buddy uses the active
workspace's intent to choose ordinary work or selected development, then applies
the needed capabilities. Installation availability does not choose that mode.

## Quickstart

After [installation and activation](05-installation.md), open your working folder
and make a concrete request:

> Continue the application from the latest draft. Reuse the constraints we already
> recorded, and identify what still needs my input.

For a standalone question, supply the context directly. You do not need to create
an intent file, repository or task simply to use a reasoning method.

## Knowledge and continuity

| Situation | Example request | Expected behavior |
|---|---|---|
| Resume a topic | “Where did we leave the application?” | Read its current owner and handoff; identify the leading draft and next step |
| Correct context | “That deadline changed; use the new date.” | Reconcile the correction and affected current references |
| Reuse prior decisions | “Use our earlier criteria for this comparison.” | Retrieve and apply the relevant criteria; qualify stale or missing evidence |
| Finish a session | “Save.” | Reconcile useful knowledge, handoff and authorized Git persistence |
| Repair accumulated context drift | “Housekeeping for this project's context.” | Inspect ownership, routes and freshness, then reconcile within scope |

Continuous maintenance captures useful changes during the conversation. `save` is
also a checkpoint for unfinished work and its next steps. It is not the only time
knowledge can be maintained, nor a promise that all prior chats are available.

An explicit `save` requests commit and push to the active project's tracked
upstream unless local rules restrict it. Separate user-repository changes follow
that repository's rules. Ordinary maintenance alone grants no commit/push authority.
Without Git, local continuity still works. See the [save contract](../workflows/runbooks/save/WORKFLOW.md).

## General reasoning

Choose a method by what is uncertain:

| Method | Use when | Example | Output |
|---|---|---|---|
| [Frame](../skills/frame/SKILL.md) | The problem or solution space is unclear | “Frame why this plan keeps slipping.” | Reformulated problem, constraints, distinct approaches and a recommendation |
| [Bedrock](../skills/bedrock_drill/SKILL.md) | An assumption needs deeper examination | “Use Bedrock to examine why we think this deadline is fixed.” | Assumption tree, underlying constraints/values, blind spots and implications |
| [Council](../skills/council/SKILL.md) | A consequential choice needs multiple perspectives | “Compare these options with a Council, including the option to wait.” | Consolidated positions, trade-offs, uncertainty and a recommendation |

Supply the goal, alternatives already considered, constraints and available evidence.
Distinguish hard limits from preferences. Methods must keep missing evidence and
user-owned values visible rather than filling them with invented certainty.

Frame offers quick, standard and deep analysis. Bedrock offers focused, broad and
exhaustive depth. Council offers light, standard, full and interactive modes.
The selected skill defines proportionality and its required steps; a deeper mode
costs more time and model work.

Independent Council modes use separate member investigations and a Chief's
consolidation; Buddy checks the load-bearing claims. Interactive Council is a
moderated dialogue, not a claim of independent-agent execution. Different role
names do not prove model diversity or independent runtime isolation.

Methods can finish inline without durable files. They do not automatically start
a development workflow, write an ADR or turn a recommendation into an accepted
decision. Saving useful results follows the caller's authority.

## Software development

Software workflows apply when the active project's intent establishes software
development, or when development is explicitly invoked for the scope. An optional
line under `## Context` in `intent.md` makes project selection explicit:

```text
Forge workflows: software
```

Use `Forge workflows: on-demand` when project-local rules should govern work and
Forge methods should be invoked as needed. If intent does not establish software
development, on-demand is the default. Scripts, configuration or old workflow files
alone do not select development. See [workflow selection](../framework/process-map.md#workflow-selection).

| Desired result | Selected development workflow | Canonical guide |
|---|---|---|
| Implement a defined feature | Build | [Build runbook](../workflows/runbooks/build/WORKFLOW.md) |
| Investigate and repair a defect | Fix | [Fix runbook](../workflows/runbooks/fix/WORKFLOW.md) |
| Validate an existing specification | Review | [Review runbook](../workflows/runbooks/review/WORKFLOW.md) |
| Close a knowledge gap or evaluate an approach | Research | [Research runbook](../workflows/runbooks/research/WORKFLOW.md) |
| Resolve an open problem shape | Solve | [Solve runbook](../workflows/runbooks/solve/WORKFLOW.md) |
| Rewrite documentation for its readers | Docs-Rewrite | [Docs-Rewrite runbook](../workflows/runbooks/docs-rewrite/WORKFLOW.md) |

“Implement this feature” authorizes work within its clear scope. “Investigate why
this fails” authorizes diagnosis; it does not by itself authorize a fix. New live,
destructive or publication actions retain their explicit authorization boundaries.

Build chooses a path appropriate to uncertainty and consequences. DIRECT is a
short, complete lifecycle for eligible bounded reversible work, with verification;
it is not selected from file count alone. Existing approved specifications can
support implementation without repeating the specification interview. Exact route
criteria live in the [process map](../framework/process-map.md#direct-eligibility)
and Build runbook.

For an active outage, Fix puts authorized recovery and actual service verification
before final root-cause repair. “Restored” and “resolved” are distinct outcomes.

## Continue across sessions

Common save preserves open topics and carries the contribution of explicitly
selected development. The development adapter exports and validates exact bound
workflow state. Restore checks it without advancing, completing or unpausing it.

A missing required contribution makes save partial; unrelated ordinary work can
continue with that blocker visible. Merely finding workflow files is not permission
to resume all of them. See [development continuation](../framework/development-continuation.md).

## Next step

[Daily handbook](13-operational-handbook.md) · [Human guide](10-human-guide.md) ·
[Visual guide](workflow-diagrams.md) · [Documentation hub](README.md)
