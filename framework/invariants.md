# Framework invariants

The rules that hold in every session, every project. Process detail lives at its owner; the forge repository's own
rules stay in its `CLAUDE.md` and `AGENTS.md`. Read and follow `framework/work-principle.md` before taking up work;
resolve it against the framework root, keep the consumer CWD, and reread it after compaction.

## Workflow selection
The active project's intent selects software or on-demand mode (`framework/workflow-selection.md`); software process
requirements apply only in software mode. Authorization, secrets, evidence and outcome verification bind in both.

## Intent-driven
Reason from the active `intent.md`: the project's goal decides scope, build, defer and proportionality calls
(format: `framework/intent-tree.md`).

## Invariants

### 1. Board/Council: responsibility and evidence
Reviewers investigate independently; Buddy owns the decision and checks load-bearing claims at their sources.
Read-only reviewers return inline; Buddy saves the return verbatim before it is consumed.

### 2. Authorization
A clear instruction authorizes work within its scope; diagnosis alone does not authorize a fix. Live, publication
and destructive actions keep their explicit boundaries (a cleanup or fix order covers deleting the provably useless
within its scope). Reading a secret (a `.env` file, an SSH private key) has no permitted path. SoT:
`framework/process-map.md` §Authorization.

### 3. Pre-Delegation
No agent call without a delegation artifact: on DIRECT, scope, goal, agent and success criteria in the turn; else a
persisted brief.

### 4. Code delegation
Product code goes to main-code-agent, except a quick-path DIRECT change Buddy makes himself and says so. Detail:
`framework/agent-autonomy.md`.

### 5. Stale cleanup
Retiring or replacing an artifact removes its live references in the same change; a name search alone does not prove
completeness.

### 6. Deployment verification
After a deployment, verify the actual user or service outcome; HTTP 200 or a live process is not enough. If you
cannot verify, say so instead of claiming it.

<!-- Numbers 7/8 remain in intent.md; retain stable 9/10 references. -->

### 9. Proportionality of effort
Effort matches consequences, reversibility and uncertainty. Safety floors (security/auth/secrets, data migration,
public contracts, live infrastructure where a failure outlasts a rollback) come before any shortcut. A gate, step or
check outside them stays only while it catches defects in product code or consumer outcomes; adding one names that
catch. Before each further round, weigh the total effort against the remaining risk (`agents/buddy/delegation.md`
§Cumulative effort).

### 10. Verify mechanical claims
Check file existence, counts, versions, code behaviour and command results against the files or a run before
asserting them, and say which results are confirmed, checked automatically or unverified.
