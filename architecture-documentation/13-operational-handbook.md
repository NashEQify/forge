# 13 — Daily handbook

Use your ordinary working folder and describe what you want to accomplish. Buddy
uses the project's rules, relevant knowledge and your authorized user scope to
continue the work. Software workflow machinery is needed only for selected software
work; you can use knowledge and reasoning directly.

For setup or an upgrade, use [installation](05-installation.md). This page starts
with a verified installation and covers the work between sessions.

## Start a session

Open the workspace that owns the work. The current directory identifies the active
project; framework files supply shared methods, while the project's own intent,
navigation and rules supply its goals and boundaries.

The agent should load the applicable boot context, check relevant pending recovery,
and read the current handoff before relying on saved state. With configured user
scope, the short profile provides person-wide context; detailed topics are read
when relevant. Missing user scope does not prevent project-only work.

Give a concrete first request:

> Continue the comparison from the latest draft. Check our earlier constraints,
> then tell me which unresolved question matters most.

## Retrieve and correct context

When a question depends on prior work, expect the agent to read its topic owner
and linked evidence. If navigation is incomplete, a bounded search can locate the
material. “No relevant record found in the searched scope” is different from
“this never happened.”

Useful corrections can be made during the conversation:

> The schedule changed. Keep the earlier date as historical context and use the
> new date for the current plan.

Knowledge maintenance distinguishes new, changed and already-present information.
Repeating the same fact need not create another entry. Corrections should update
the current owner and affected routes or summaries, preserving source meaning and
uncertainty. [Knowledge Processor](../skills/knowledge_processor/SKILL.md) owns these rules.

## Keep personal and project information in scope

| Information | Responsible location |
|---|---|
| How you want to collaborate with Buddy | Configured user `soul.md` |
| Concise person-wide values and defaults | Configured user `profile.md` |
| Personal topic facts and preferences | Responsible user topic file |
| An activity, draft, technical setup or project decision | Its project/topic owner |
| Where to continue open work | Existing session handoff, with leading-file pointers |

The [user-scope contract](../framework/user-scope.md) defines resolution. Configuring
that scope authorizes its maintenance, subject to explicit limits such as “do not
save.” A blocked personal write is reported as deferred; private content is not
parked in another project's context. Maintenance alone does not authorize commits,
pushes or operational changes.

## Use a method during ordinary work

Ask for **Frame** to clarify the problem, **Bedrock** to examine an assumption or
**Council** to compare consequential alternatives. Supply what you know and what
remains uncertain. The result can stay inline; invoking a method does not require
software bookkeeping or change the whole project's mode.

For example: “Use Frame on why this preparation keeps expanding. We have two weeks,
and the outcome is a usable first version.” See [usage and methods](06-usage-workflows.md#general-reasoning).

## Save and finish

Say `save` for a checkpoint or at session end. The common save process:

1. Reconciles useful session changes at their responsible owners.
2. Updates worked-on topics in the handoff while retaining other open work.
3. Carries any explicitly selected development contribution and its blockers.
4. Publishes coherent knowledge, navigation and continuation state.
5. Performs authorized Git persistence and checks the actual outcome.

An explicit `save` requests commit and push to the active project's tracked upstream
unless local rules restrict it. Separate user-repository changes follow that
repository's rules. Say “save locally without committing or pushing” when that is
your intended boundary. Local continuity also works without Git.

The completion report should distinguish knowledge/handoff persistence, Git commit
and push, and any partial outcome. A successful local write is not evidence of a
successful push. The [save runbook](../workflows/runbooks/save/WORKFLOW.md) defines the checks.

## Continue software work

When development is selected, its adapter records the exact workflow identities,
state references and required task/plan checks. Save carries that contribution;
the next session validates it before continuation.

Restoring a session does not advance steps, complete tasks or unpause workflows.
Authoritative state files remain necessary: a short handoff summary cannot replace
them. Gitignored workflow state does not travel automatically with Git. A move to
another machine needs that state handled explicitly, with compatibility verified.

Missing or incompatible state blocks exact development continuation. It does not
require abandoning unrelated everyday work. Keep the blocker visible and use the
[development continuation contract](../framework/development-continuation.md) for recovery.

## Handle interruptions honestly

Protected continuity uses scoped baselines and recovery records. If an interrupted
change leaves owners and navigation inconsistent, inspect and reconcile the actual
files before relying on them. Preserve later corrections; do not blindly replay
an old proposed write or delete recovery records to silence a warning.

“Owner updated; reconciliation pending” is a partial result. A blocked private
write remains unpersisted until its authorized owner can be updated. Separate
repositories have separate publication operations, not a global transaction.
See [troubleshooting](12-troubleshooting.md) and [protected continuity](../framework/continuity.md).

## Housekeeping and updates

Ask for housekeeping when routes, ownership or current views need broader attention.
It uses the same knowledge lifecycle, preserves useful qualifications and history,
and does not delete information simply for age or low mention frequency. It creates
no background schedule by itself.

Framework upgrades use coordinated maintenance with affected sessions stopped
before the source changes. Installation can remain `validation_pending` until a
fresh session supplies real verification. Follow [installation](05-installation.md)
for preparation, validation and recovery instead of updating live integrations.

[Human guide](10-human-guide.md) · [Usage](06-usage-workflows.md) · [Documentation hub](README.md)
