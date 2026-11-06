# 04 — Core Concepts

These terms and approaches explain how Forge chooses work, carries knowledge and
evaluates results. They apply at different scopes; using one does not imply using
them all.

## Capability, profile and workflow

A **capability** is an independently usable responsibility: knowledge and
continuity, general reasoning, or software development.

Where Forge is active is a switch, not an installation: one line in a project's
`AGENTS.md` starts Buddy in that project, and a user setting starts it in every
session of the machine, with a personal context folder (the user scope). Both supply
the same capabilities. Neither defines the purpose of the current conversation.

A **workflow selection** comes from project intent or explicit development
invocation. On-demand projects use their own working rules and explicitly requested
Forge methods. Software projects can use the automatic development processes.
[Workflow selection](../framework/workflow-selection.md) owns this choice.

## How Forge works

These approaches shape every Forge workflow. Each names how Forge implements it and
where its rule lives.

### Intent-driven work

**Intent** names the outcome the work should serve. A consumer's `intent.md` states
the goal as facts an agent can check against, and may select `software` or
`on-demand` workflows. Each task derives its intent from that goal in one sentence.
Scope, defer and effort decisions reason from it, so a locally sensible change
does not work against the larger goal. The agent may help sharpen an incomplete
intent; it does not invent one. Rule: [intent tree](../framework/intent-tree.md).

### Spec-driven design

The spec defines the product; code is produced from it. When a defect shows the spec
was wrong or silent, the spec changes first and the code follows. When the spec
already states the right behaviour, a reproducing test pins it and the code adapts.
Forge implements this with:

- **Three carriers.** A change's working spec (acceptance, brief, plan) binds while
  the change runs and then stays with its records. Tests hold the behaviour case by
  case. The durable spec holds what tests cannot: contracts between separately built
  units, invariants, limits and the rationale of non-obvious choices. Before close,
  what the change decided durably moves into the durable spec.
  [Spec carriers](../framework/spec-engineering-implementation-specs.md#convention-spec-carriers)
- **A test matrix from the spec.** The behaviour spec gives one row per promised
  behaviour, including edge rows for stated limits, and that matrix is the test plan
  before any code. [Test design](../skills/testing/SKILL.md)
- **A need for every addition.** A new layer, abstraction, dependency, configuration
  option or guard carries a row that states its need and the simpler alternative it
  rejected. A fix adds no public surface and guards no state that was never shown to
  occur, unless such a row names why.
  [Complexity tracking](../framework/spec-engineering-implementation-specs.md#convention-complexity-tracking-for-specs-and-briefs)
- **Specs written by interview and reviewed for rebuild-readiness.** New specs come
  from an interview that explores the solution space; a spec board asks whether an
  implementer could rebuild the behaviour from the spec alone.
  [Spec authoring](../skills/spec_authoring/SKILL.md) · [Spec board](../skills/spec_board/SKILL.md)
- **A UX drawn out, not imposed.** When a change adds or changes a screen, page, flow or terminal
  interaction a person operates, two contracts are written from that person's answers and the
  existing sources: how it looks (tokens, components) and how it behaves (surfaces, states,
  journeys of a named person, wording). Every stated need has a screen that delivers it and
  every screen a journey that reaches it; a gap is asked about, never filled in. The UX board
  reviews the contracts, and the UI is built from them.
  [UX authoring](../skills/ux_authoring/SKILL.md)
- **An architecture spine for parts built apart.** When a change defines a contract that
  another task or implementer builds against, Forge writes down only the decisions that
  two separately built parts could otherwise get incompatibly wrong, each with what it binds,
  what it prevents and its rule, and names everything else as deferred with its reason.
  A lower level inherits the higher spine read-only. Inside one part, the mechanism model
  stays the tool. A script checks the spine's form; the architect reviewers check its substance.
  [Architecture spine](../skills/_protocols/architecture-spine.md)
- **Drift kept visible.** Amendments to a locked spec are checked against the code
  before they are written. A spec that fell behind the code is brought up to date
  from the code, never extended with wishes. When a fix decides an outcome no spec
  item states, that outcome goes into the spec in the same change.
  [Amendments](../skills/_protocols/spec-amendment-discipline.md) ·
  [Retroactive update](../skills/retroactive_spec_update/SKILL.md) ·
  [Spec gaps a fix reveals](../skills/convergence_loop/cause-before-answer.md#spec-gaps-a-fix-reveals)

The method as a whole: [spec engineering](../framework/spec-engineering.md).

### Proportional effort

Effort follows consequences, reversibility and uncertainty. Safety floors are
checked first: authorization, secrets, data migrations, public contracts and live
infrastructure keep their safeguards however small the change. A bounded,
reversible change that follows an existing pattern can take the short complete path,
which still includes verification. File counts are a warning signal, not the
decision. The route decision records three facts first: the open points the user
would notice, what cannot be undone, and the footprint. A change works toward one
goal; a second goal is offered as its own task, and a long change spec prompts a
split the user may decline. Conditional stages such as UX and architecture run only on their trigger.
Before each further fix round or review, total effort is weighed against the
remaining risk. [Process map](../framework/process-map.md) ·
[Short-path eligibility](../framework/direct-eligibility.md) ·
[Sizing facts](../workflows/runbooks/build/lifecycle.md#sizing-facts) ·
[One goal per change](../framework/spec-engineering-implementation-specs.md#convention-one-goal-per-change)

### Evidence before claims

A completion claim carries the evidence it requires beside it: the test command with
its counts from a run after the last edit, the retest that reproduces the original
symptom, the commit and the state after the push. Without that evidence, the record
says what holds ("not run", "push pending"). The approved acceptance is checked line
by line, verbatim. [Completion claims](../skills/_protocols/evidence-author-claims.md)

The same rule applies to a session looked at afterwards. Session diagnosis reads a
transcript and its subagents' transcripts where they lie, read-only. It checks first
whether Forge loaded, then reports seven dimensions: the process timeline, plan
adherence, repeated work, stumbles, quality evidence, request conflicts, and cost and
time. Every finding cites its transcript line, and the report asks whether the problem
occurs without Forge. [Session diagnosis](../skills/session_diagnosis/SKILL.md)

### Independent review, one decider

Reviewers investigate separately and read one package of exactly the change under
review. Every kept finding is verified at the location it cites, and that check sets
its grade. Its cause is classified before it is answered. The implementer may push
back with technical reasons. Buddy, the orchestrator, rules on the push-back, checks
the load-bearing claims and owns the decision. Agreement among reviewers is evidence
to examine, not proof.
[Finding verification](../skills/_protocols/finding-verification.md) ·
[Cause before answer](../skills/convergence_loop/cause-before-answer.md)

### Who builds and who checks

In software work, product code goes to the coding agent at any size; "it is only
one line" is no exception, except on the quick path below. On the full paths the
review board checks a change. On the short path Buddy chooses per change how much
check it gets, from what a defect would cost, how easily the change is undone and
how sure the record is:

- **quick:** the change alters no behaviour (a typo, formatting, wording), or it is a
  trivially reversible local change its existing test shows directly. Buddy makes it
  himself and runs the test; nothing else checks it.
- **checked:** a local behaviour change along an existing pattern that an executable
  test covers. The coding agent builds it; Buddy reads the diff and reruns the tests.
- **reviewed:** uncertainty remains, or the effect reaches beyond the changed unit.
  The coding agent builds it, and a separate, fresh agent run that never built it
  gets the record, the builder's report and the diff and re-runs the reproduction
  and the tests itself.

In doubt between two paths Buddy asks in one sentence; when you told him to run the
work through, he takes the heavier one and says so. Your word ("quick", "reviewed")
or a standing preference in your profile sets the path; none of this lifts a safety
floor. Every short path has four steps: record the goal, path, scope and checks; build;
check; report. Without a task record and when the check passes, they close within
one turn. The final reply says what the change now does, which checks ran with their
results, the path and who changed the code, and on reviewed the agent run that
checked it. A check Buddy or the builder ran is reported as their own, never as
independent; when no separate run can be started for reviewed, the reply says the
change has no independent check. A role the
host has no agent type for runs as a general agent told to read its role file first.
[The DIRECT run](../framework/direct-eligibility.md#the-direct-run) ·
[Invariants](../framework/invariants.md#4-code-delegation)

### Instruction-first mechanisms

Forge's methods are plain instruction text that any capable agent host can load.
A rule's form follows the failure it must prevent: a missing step gets a required
slot, output of the wrong shape gets a recipe, behaviour that must differ by case
gets a condition the agent can check, and a rule that is skipped gets firmer wording
only where a reproduction shows the skip. Scripts, validators and Git hooks
make specific mechanical checks where they are invoked; they do not make the methods
enforced. [Instruction form](../skills/_protocols/instruction-form.md)

The rules that hold in every project, whatever its workflow, sit in one short unit
that every installation reads before the first answer: workflow selection, the
goal as the input to every decision, review responsibility, authorization,
delegation, cleanup of retired artifacts, deployment verification, proportional
effort, checked claims, and a one-line record of each state-changing action. The rules of one repository
stay in that repository's own instruction files. Before a rule, structure or
decision is changed, the intent it serves and the failure it prevents are named,
and the changed version is checked end to end against both.
[Framework invariants](../framework/invariants.md) ·
[Work principle](../framework/work-principle.md)

### Explicit authorization boundaries

**Authorization** names what may actually happen. A clear implementation request
authorizes the work in its scope, and that authorization survives ordinary phase
changes. A request to investigate authorizes a diagnosis, not a fix. Publication,
live operations and destructive steps keep their own explicit boundary; a clean-up
or fix order covers deleting what is provably useless within its scope. Bookkeeping
never widens a boundary. A saved proposal remains a proposal until the user
accepts it. [Authorization](../framework/process-map.md#authorization)

### Decisions taken for you, made visible

Within an approved scope, agents settle many points without asking. Those the request
did not decide, and where a wrong choice would cost you more than redoing the point,
are listed in the final message, each with that cost and how to undo it. A point
that needs your judgment stays a question asked before acting.
[Decisions I took for you](../skills/return_summary/SKILL.md#decisions-i-took-for-you)

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
where the selected mode requires one; Buddy owns the resulting decision, as
[above](#independent-review-one-decider). Independent agreement can still share an error.

**Context isolation** is a protocol unless the host supplies stronger separation.
Read-only role instructions and effective filesystem permissions are also distinct.
Verify the runtime boundary before claiming it is mechanically enforced.

## Development state

A **task** records tracked software work. A **plan** relates work to goals. A
**workflow instance** records exact selected execution state. A handoff summarizes
continuation and carries explicit bindings; it does not replace any of these owners.

A new task is checked against open ones before it is written: a duplicate is not
filed, and work that serves the same deliverable as an open task (one decides the
other's shape, is its acceptance, changes the same files or needs the same install
window) is folded into it as steps or acceptance criteria. Such parts stay separate
tasks only when they differ in owner, timing, authorization or safety floor, and that
reason is written down.
[Task creation](../skills/task_creation/SKILL.md)

[Development continuation](../framework/development-continuation.md) restores only
bound work without advancing or unpausing it. Local gitignored engine state does not
travel with a Git push. Missing state is a continuation blocker, not an invitation
to reconstruct progress from prose.

Next: [Installation](05-installation.md) · [Usage and methods](06-usage-workflows.md).
