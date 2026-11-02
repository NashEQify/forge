# 06 — Usage and workflows

Describe the desired result, relevant context and boundaries. Buddy uses the active
workspace's intent to choose ordinary work or selected development, then applies
the needed capabilities. Installation availability does not choose that mode.

## Quickstart

After [installation and activation](05-installation.md), open your working folder
and tell Buddy what you want to achieve. If work is already underway, ask Buddy to
pick up from the latest draft and the constraints you agreed on.

For a standalone question, supply the context directly. You do not need to create
an intent file, repository or task simply to use a reasoning method.

## Start with an idea

Tell Buddy **“Forge my idea”** when you know what you want to improve and the
form of the solution is open. This starts the Solve workflow.

> Forge my idea. Our volunteers keep turning up for the wrong shift. How could we help
> everyone find the current rota?

Buddy asks where the rota changes hands and what the volunteers actually see.
Together you might choose one shared schedule and retire the printouts, or decide
that a reminder app would help. Solve gives you something you can use and a way
to check it. For the shared schedule, that might mean trying the new procedure
for a week and checking whether volunteers found their shifts.

**Use Build when you've chosen a software feature.** “Add a shift reminder to
our existing app and test what happens when a shift changes” can go straight to
Build. Solve can hand that same work to Build if you reach the decision together.
Build scales its implementation and checks to the work, whether you enter it
directly or through Solve. [Solve runbook](../workflows/runbooks/solve/WORKFLOW.md)
and [Build runbook](../workflows/runbooks/build/WORKFLOW.md).

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
alone do not select development. See [workflow selection](../framework/workflow-selection.md).

| Desired result | Selected development workflow | Canonical guide |
|---|---|---|
| Find a workable solution when its form is open | Solve | [Solve runbook](../workflows/runbooks/solve/WORKFLOW.md) |
| Implement a defined feature | Build | [Build runbook](../workflows/runbooks/build/WORKFLOW.md) |
| Investigate and repair a defect | Fix | [Fix runbook](../workflows/runbooks/fix/WORKFLOW.md) |
| Validate an existing specification | Review | [Review runbook](../workflows/runbooks/review/WORKFLOW.md) |
| Close a knowledge gap or evaluate an approach | Research | [Research runbook](../workflows/runbooks/research/WORKFLOW.md) |
| Rewrite documentation for its readers | Docs-Rewrite | [Docs-Rewrite runbook](../workflows/runbooks/docs-rewrite/WORKFLOW.md) |

“Implement this feature” authorizes work within its clear scope. “Investigate why
this fails” authorizes diagnosis; it does not by itself authorize a fix. New live,
destructive or publication actions retain their explicit authorization boundaries.

Build chooses a path appropriate to uncertainty and consequences. DIRECT is a
short, complete lifecycle for eligible bounded reversible work; it is not selected
from file count alone. It runs in four steps and, without a task record and when the
check passes, closes within the same turn: Buddy records the goal, the path, scope and
checks; the change is built; it is checked; the reply reports what changed, the checks
with their results, the path and who checked. Buddy chooses the path per change:
quick (a change that alters no behaviour, or a trivially reversible one its test
shows: Buddy makes it and runs the test), checked (a tested local change: the coding
agent builds, Buddy reads the diff and reruns the tests) or reviewed (remaining
uncertainty or a wider effect: the coding agent builds and a separate agent run
checks and re-runs the tests). Your word sets the path either way; what each path
costs on Claude Code and Codex, against a bare session, is in the
[README](../README.md#what-it-costs-and-how-you-choose). Existing approved
specifications can support implementation without repeating the specification
interview. Exact route criteria live in
[DIRECT eligibility](../framework/direct-eligibility.md) and Build runbook.

### What a build goes through

A build runs the stages in the [overview](01-overview.md#software-development-from-intent-to-verified-result):
intent and sizing, the spec with its test matrix (a UX design drawn from your answers and
an architecture spine of the decisions separately built parts must share, each on its trigger), a plan whose tasks are checked against each other, dispatches with a fixed
contract, review, fixes and an evidenced close. What you see along the way:

- **Before code:** the acceptance criteria you approve travel word for word into
  every implementer's brief ([approved acceptance](../skills/_protocols/approved-acceptance.md)).
  When the acceptance admits two readings that would give you different results, and
  neither the spec nor the code settles which, the question comes back to you;
  smaller points are settled and listed for you at the end.
- **During review:** each finding is checked at the location it cites before it is
  graded. A finding that does not hold is recorded as false, with its evidence,
  rather than fixed ([finding verification](../skills/_protocols/finding-verification.md)).
- **During fixes:** each finding gets its cause first. A spec-caused finding changes
  the spec and the code follows; an intent question comes back to you
  ([cause before answer](../skills/convergence_loop/cause-before-answer.md)). At the
  re-review limit, every open finding gets a class and a ruling instead of another
  round ([at the cap](../skills/convergence_loop/at-the-cap.md)).
- **For a defect:** Fix compares the broken path with a working one, tests one written
  hypothesis before changing code, and after three failed fixes looks for the cause
  outside the code
  ([root-cause fix](../skills/root_cause_fix/SKILL.md)).
- **At the end:** the final message lists the claims with their evidence and the
  decisions taken for you, each with its cost and undo
  ([completion claims](../skills/_protocols/evidence-author-claims.md),
  [decisions](../skills/return_summary/SKILL.md#decisions-i-took-for-you)).

Which stages a route runs and which reviewers it calls depend on the change's risk;
a short path skips the separate spec and signoff cycle, keeps the check its path
names (quick, checked, reviewed), and the reply says what did not run.
The route decision shows why: three facts written before the route (the open points
you would notice, what cannot be undone, the footprint). Open points that need you
come to you before work starts, and a request with two independent goals is offered
to you as a split ([sizing facts](../workflows/runbooks/build/lifecycle.md#sizing-facts)).

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
