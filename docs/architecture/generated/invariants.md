# Invariants (auto-generated)

> Extracted from framework/invariants.md. Do not edit manually.

### 1. Board/Council: responsibility and evidence
Reviewers investigate independently; a Chief consolidates where the
selected review mode calls for one. Buddy owns the decision and verifies
load-bearing claims against their sources. Buddy may inspect relevant
findings to resolve contradictions, but does not routinely repeat every
review. Read-only reviewers return complete artifacts inline; Buddy
persists them verbatim with provenance before Chief consumption.
Platform instructions and effective permissions are never overridden.

### 2. Authorization
Discuss when the requested outcome or a consequential decision is unclear.
A clear implementation instruction authorizes work within its stated scope.
Existing authorization survives phase transitions; ask again only for a
material scope/risk change or a genuinely unresolved user decision.
Diagnosis-only does not authorize a fix. Live and publication actions
retain their explicit boundaries. Destructive actions do too, except that
the user's cleanup or fix order covers deleting the provably useless
within its scope. When a boundary lifts (commit,
push, publication), first reconcile the work it held back, then take up new
work. Bookkeeping does not authorize new substantive decisions.
SoT: `framework/process-map.md` section Authorization.

### 3. Pre-Delegation
No agent call without a delegation artifact. DIRECT: scope, goal, agent
and success criteria in the turn suffice. Other paths use a persisted
brief. Do not request another routine signoff for an already approved
scope. Routing: `framework/process-map.md` and the selected runbook.

### 4. Code delegation
Product code goes to main-code-agent. A role not installed as an agent type
runs as a general agent run told to read its role file (`agents/<role>.md`
under the framework root); a missing agent type is no reason to build inline. Buddy writes orchestrator artifacts
(`agents/`, `framework/`, `skills/`, `workflows/`, `context/`, `docs/`)
within the approved intent-scope. Detail: `framework/agent-autonomy.md`.

### 5. Stale cleanup
Retiring or replacing an artifact includes its live references in the same
change. Search names and enumerate the relevant live inventory; neither a
name search nor a confident summary alone proves completeness. Preserve
frozen history. Detail: `skills/_protocols/evidence-author-claims.md`
section 8.2 and `skills/deprecation_and_migration/migration.md`.

### 6. Deployment verification
Verify the actual user/service outcome after deployment; HTTP 200 or
process liveness alone is insufficient. If verification is unavailable,
report the unverified boundary instead of claiming verified deployment.
Incident recovery follows `workflows/runbooks/fix/WORKFLOW.md` section
Incident recovery before final RCA; authorization is not relaxed.

<!-- Numbers 7/8 remain in intent.md; retain stable 9/10 references. -->

### 9. Proportionality of effort
Effort matches consequences, reversibility and uncertainty. Name the
consumer and concrete cost a gate, task or test addresses. Vision-named
product deliverables count even before deployment. Safety floors for
security/auth/secrets, schema/data migration, public contracts and live
infrastructure are evaluated before any small-change shortcut.
DIRECT eligibility has one source: `framework/direct-eligibility.md`.
File counts are signals, not substitutes for risk assessment.
Weigh effort cumulatively: before each further round (fix pass, added
review, new review owner, extension) compare total effort and remaining
risk with the stated expectation, then close with a recorded limit, narrow,
or escalate (`agents/buddy/delegation.md` §Delegation hygiene).

### 10. Verify mechanical claims
Verify file existence, counts, versions, code behavior and command results
against actual files or executed checks before asserting them. Consequential
artifacts carry evidence pointers or commands beside the claim. Distinguish
agent-confirmed, automatically checked and unverified results. A correct
pointer can still be misread; independent review checks interpretation.
Detail: `skills/_protocols/evidence-author-claims.md`.

*Status: 2026-10-29. Source: framework/invariants.md*
