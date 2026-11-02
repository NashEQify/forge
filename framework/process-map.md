# Process Map

Central entry point: which workflow for which kind of work.
Consumer: Buddy (orchestrator). Agents do not read this document.

Skills, composition, maturity -> `framework/skill-map.md`.

**Discovery entry point:** the `workflow_router` skill
(`skills/workflow_router/SKILL.md`, generated) is the injected sign-post
into this map — its need-phrased catalog is pushed into the
available-skills reminder, so a workflow is reached for at the moment of
need; the router then points back here for routing.

**Path convention:** all runbook and skill paths in the tables below are
from the **repository root** (not relative to `framework/`).

---

## Workflow routing

### Workflow selection

At boot step 2, and whenever the mode of the work is in question: read and follow
`framework/workflow-selection.md` (software or on-demand).
The workflow tables and automatic gates below apply to software development;
the Authorization section applies to both modes.

### Workflows (8)

| I want to... | Workflow | Runbook |
|-------------|---------|---------|
| “Forge my idea” — work out what would solve an open problem | **Solve** | `workflows/runbooks/solve/WORKFLOW.md` |
| Break down an objective into a spec hierarchy | **Solve** (scoping mode) | `skills/scoping/SKILL.md` |
| Implement a feature/task | **Build** | `workflows/runbooks/build/WORKFLOW.md` |
| Write/design a spec | **Build** (Specify) | `workflows/runbooks/build/WORKFLOW.md` |
| Review/validate spec(s) | **Review** | `workflows/runbooks/review/WORKFLOW.md` |
| Restore service during ongoing harm | **Fix: Incident recovery first** | `workflows/runbooks/fix/WORKFLOW.md` |
| Diagnose and permanently fix a defect | **Fix** | `workflows/runbooks/fix/WORKFLOW.md` |
| Research / evaluate / spike | **Research** | `workflows/runbooks/research/WORKFLOW.md` |
| Rewrite reader-facing docs / README / positioning (reader-journey-first) | **Docs-Rewrite** | `workflows/runbooks/docs-rewrite/WORKFLOW.md` |

### Common continuity and generic reasoning

Save (`workflows/runbooks/save/WORKFLOW.md`), housekeeping
(`workflows/runbooks/context_housekeeping/WORKFLOW.md`), Council, Frame and Bedrock
have direct entries without an engine prerequisite; `framework/capabilities.md`
defines ownership. Software intent or an explicit development invocation binds
`framework/development-continuation.md` before progressing selected work. Preserve
unfinished bindings across ordinary saves; task/plan/state-file presence does not
create them. Restore exact selected state without advancing or unpausing.

### Common save

| I want to... | Workflow | Runbook |
|-------------|---------|---------|
| End a session | **Save** | `workflows/runbooks/save/WORKFLOW.md` |

**Autonomy decision** (who writes which artifact, with which gate, via which routing):
SoT is `framework/agent-autonomy.md`. Workflow assignment above answers
"which workflow"; `agent-autonomy.md` answers the orthogonal sub-questions
permission and gate per artifact type.

**Solve vs. other workflows — entry-point matrix:**
- **Solve**: the problem is known, but solution shape (feature? spec? code? process?) is unclear. Typical for meta-problems, structural questions, new processes.
- **Build**: feature is clear (already decided to build), solution lives in code-space.
- **Fix**: a defect needs investigation; capacity and hygiene problems are defects. A known cause and defined fix may use Build-DIRECT only if all DIRECT criteria below hold. A fix on any path, DIRECT included, covers the cause class (`skills/root_cause_fix/SKILL.md` Step 3). An active outage or ongoing harm takes Incident recovery first, even when final RCA is incomplete.
- **Review**: artifact exists and needs validation.
- **Research**: knowledge gap, answer needs to be found.
- **Solve (scoping mode)**: large objective to split into spec hierarchy. Done criterion foreseeable, solution shape = spec hierarchy. Uses `skills/scoping/SKILL.md` as capability.

If unclear: derive routing from intent (what is the desired result?).
Hybrid tasks: choose one primary workflow and apply the relevant existing
primitives to each work item according to its uncertainty, consequences and
known solution shape. Frame unresolved solution choices; carry known mechanical
work directly into the implementation and verification scope without inventing
alternatives. A defect embedded in broader work retains root-cause
investigation, a failure witness and outcome verification through the existing
fix primitives; it does not automatically require another workflow instance.
Record these obligations in the existing work artifact. Counts of acceptance
criteria, files or sub-problems are inspection signals, not route decisions.
Authorization and safety floors continue to apply to every item.

## Authorization

Existing authorization survives phase transitions within the approved scope.
A clear request to implement a bounded change is sufficient; the brief records
that authorization rather than asking for the same decision again. Ask when
the intended result is unclear, a consequential design decision is unresolved,
or the scope, risk, affected host or data impact materially changes.
Diagnosis-only and proposal-only requests do not authorize implementation. A
request that asks for the outcome (fix it, empty it, clean it up) authorizes
its fix even when it also asks for analysis; a question or a report alone is
diagnosis. Bookkeeping must not silently change the user's goals or permission
boundaries. The points the agent settles itself that would cost the user if
wrong are reported in the final message's decisions list
(`skills/return_summary/SKILL.md` §Decisions I took for you).

**Open lists are questions.** A list of open or remaining items put to the
user holds only what needs the user: a reason to ask named above, a cost,
possible data loss, or access the agent lacks. Work the agent can do within
the order is done, not listed. Work that waits on an outside event (an offline
host, a scheduled run) goes to its tracking owner with its trigger. Failures,
partial fixes, limits recorded at a budget close and unverified results are
still reported, as facts rather than questions.

Live changes follow the consumer's host/session approvals. Recovery does not
waive these bounds. Commit, push and deploy are separate actions: a research
or implementation request does not itself authorize publication. A standing
explicit repository commit policy can authorize local commits; push/deploy
require authorization covering that action and target. No workflow may widen
these permissions.

**Deletion under a cleanup or fix order.** The user's order to clean up or
fix, given in the session or quoted in a brief, covers deleting within its
scope what is provably useless, once the agent has checked why:
- regenerable caches and images, when what regenerates them still works (the
  image tag is still pullable, the build context is present);
- rollback copies of a completed change whose outcome is verified (an outcome
  check, not process liveness; `framework/invariants.md` Invariant 6), once the diagnosis has
  cleared that change as unrelated to the problem;
- dumps or backups superseded by a newer one that passed a restore or
  integrity check; never the generations the system's own retention keeps;
- deploy states nothing references (configuration, units, scheduled jobs,
  scripts, links, infrastructure code);
- copies at a backup or sync target of paths the backup now excludes;
- logs and journals beyond the retention the fix sets, once the evidence the
  diagnosis needs is recorded.

Whatever its category, nothing is provably useless that someone deliberately
kept beyond its normal retention, or that is the last copy of user files or
the only one besides the live data, unless the user already gave those files
up (an exclusion or a retention setting is such a decision). Delete these
checked items without a further question, and only them: list or dry-run a
command's targets first; a command that reaches beyond the checked set (a
volume prune, `git clean -x`, a recursive `find`) is not covered. A mechanism
the fix installs that deletes or stops backing up (retention, rotation, prune,
exclusion) passes the same test: its first run's targets are checked like a
manual deletion, its window outlasts the verification of the changes it cleans
up after, and ending backup coverage of user files that may have value is a
question (caches, statistics and a service's duplicates of data the backup
already holds are not such files). Every other destructive action, including
any overwrite, restore or migration, needs its own explicit confirmation, in
particular anything irrecoverable that may have value and anything outside the
order's scope. The report lists every deletion with its reason and the check
behind it; what the agent settled itself, such as a kept item or a window it
chose, goes to the decisions list (`skills/return_summary/SKILL.md`). Platform, harness, host and consumer-project rules that require
confirmation still apply; this rule never relaxes them.

**Held-back work** is accepted or installed work waiting for its commit,
merge, push or publication: uncommitted changes, installed sources not in
`HEAD`, accepted work left in a linked worktree, branch or staging copy, results
awaiting publication. Only a live owner accounts for it: a running task or
session, for the paths its brief or changed paths name (an open installer
operation counts only through the session driving it; one that no running
session drives is a maintenance need: validate or roll it back); or an entry in
the handoff's held-back list (task or paths, reason, owner, releasing event)
whose releasing event is observable — a named authorization lift, a named task
close or a date — and still pending. Anything else is unaccounted: commit, merge
or publish it within the authorization, or give it an entry, before new work
starts. When a boundary lifts, the entries it held are due: reconcile them
first, clear them, then take up new work. The boot status check and installer
status show such work; the save runbook carries the list.

## DIRECT eligibility

Before taking or proposing the DIRECT path, and when a verified known fix is considered for it: read and follow
`framework/direct-eligibility.md` (the single source for DIRECT eligibility).

## Milestone execution

Above single-task workflows. Describes how MULTIPLE tasks are orchestrated
inside one milestone. Details: `framework/milestone-execution.md` (SoT for
milestone-level orchestration).

```
1. PRE-CHECK:   plan_engine --check <milestone>
2. PRE-GATE:    Per task: board_result pass, gates.yaml, test design, delegation
3. BUILD:       Per task in blocked_by order -> Build workflow
4. INTEGRATION: L3 component + L4 integration + L5 E2E smoke
5. DONE:        plan_engine --check PASS, deploy, milestone done
```
