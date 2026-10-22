# 04 — Core Concepts

These terms explain how Forge chooses work, carries knowledge and evaluates
results. They apply at different scopes; using one does not imply using them all.

## Capability, profile and workflow

A **capability** is an independently usable responsibility: knowledge and
continuity, general reasoning, or software development.

An installation **profile** controls availability. `daily` supplies common
continuity and Bedrock, with optional Council and Frame. `full` also supplies
software tooling. Neither preset defines the purpose of the current conversation.

A **workflow selection** comes from project intent or explicit development
invocation. On-demand projects use their own working rules and explicitly requested
Forge methods. Software projects can use the automatic development processes.
The [process map](../framework/process-map.md#workflow-selection) owns this choice.

## Intent and authorization

**Intent** names the outcome the work should serve. It keeps a locally sensible
change from working against the larger goal. A consumer's `intent.md` records that
purpose and may explicitly select `software` or `on-demand` workflows.

**Authorization** names what may actually happen. Analysis, implementation,
publication and live operations have different boundaries. Existing authorization
survives ordinary phase changes within scope; bookkeeping never widens it.
A saved proposal remains a proposal until the user accepts it.

## Owner, scope and navigation

An **owner** is the responsible location for a fact or decision. Personal facts
belong in the configured user scope; project facts belong in the project. A useful
fact should not become competing copies across unrelated handoffs.

**Navigation** provides routes to detail. A short profile or project entry should
point to topic records rather than preload all history. Before dependent work,
retrieve the relevant owner and its qualifications, not just a remembered summary.

The [Knowledge Processor](../skills/knowledge_processor/SKILL.md) owns semantic
reconciliation. The [user-scope contract](../framework/user-scope.md) determines
location and privacy. Those are separate responsibilities.

## Capture, save and resume

**Capture** maintains useful knowledge during work: corrections, decisions,
constraints and context that will matter again. This is not transcript archiving.

**Save** reconciles owners and routes and leaves a usable handoff. Explicit `save`
also authorizes the active project's upstream commit/push under the save contract,
unless local rules restrict it. Ordinary knowledge maintenance does not authorize
Git publication. A separate user repository follows its own commit/push rules.

**Resume** retrieves the goal, decisions, open points and next step, then rechecks
changeable state. It does not silently start every open topic. See the
[save runbook](../workflows/runbooks/save/WORKFLOW.md) for the full contract.

## Snapshot, publication and recovery

A **snapshot** captures required same-scope files and pending status coherently.
A **conditional publication** compares the current files with that baseline before
replacing them. When another writer has changed the baseline, reconciliation starts
again from current evidence.

A **pending recovery record** preserves intended changes and partial progress for
an interrupted multi-file update. Recovery inspects actual current content; it does
not blindly replay the old text. A completed owner edit with unfinished route
reconciliation is partial persistence, not a completed save.

These protections coordinate participating writers. They neither authorize a write
nor exclude every external editor. [Continuity](../framework/continuity.md) defines
the exact boundary and result states.

## Frame, Bedrock and Council

| Method | Main question | Typical result |
|---|---|---|
| Frame | Are we solving the right problem? | Reformulated problem and solution space |
| Bedrock | Which assumptions does this depend on? | First-principles analysis and synthesis |
| Council | How do viable alternatives compare? | Perspectives, disagreements and a reasoned recommendation |

These methods can operate on supplied context and return useful inline output.
No repository, task or permanent file is inherently necessary. The caller owns
whether and where the result is saved.

## Roles, isolation and evidence

A **role** supplies a perspective or responsibility. A **skill** supplies a method.
A host **wrapper** makes that role or skill discoverable and points to its canonical
instructions. Wrappers should not become a second policy source.

Independent reviewers investigate before consolidation. A Chief organizes findings
where the selected mode requires one; Buddy owns the resulting decision and checks
load-bearing claims against sources. Independent agreement can still share an error.

**Context isolation** is a protocol unless the host supplies stronger separation.
Read-only role instructions and effective filesystem permissions are also distinct.
Verify the runtime boundary before claiming it is mechanically enforced.

## Development state

A **task** records tracked software work. A **plan** relates work to goals. A
**workflow instance** records exact selected execution state. A handoff summarizes
continuation and carries explicit bindings; it does not replace any of these owners.

[Development continuation](../framework/development-continuation.md) restores only
bound work without advancing or unpausing it. Local gitignored engine state does not
travel with a Git push. Missing state is a continuation blocker, not an invitation
to reconstruct progress from prose.

Next: [Installation](05-installation.md) · [Usage and methods](06-usage-workflows.md).
