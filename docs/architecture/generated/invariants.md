# Invariants (auto-generated)

> Extracted from CLAUDE.md. Do not edit manually.

### 1. Board/Council: Buddy = Dispatcher
On Board/Council, Buddy doesn't read review files, analyze findings,
write consolidations, or verify fixes. Spawn → read the Chief signal
→ SAVE → escalate. That's the whole job.

### 2. Default: discuss, don't implement
Implement only on a clear imperative. Unclear → ask. Self-triggered →
always discuss first. Context writes and bookkeeping skip the gate.

### 3. Pre-Delegation
No agent call without a delegation artifact. Direct path: plan block,
or scope/goal/agent stated in the turn. Standard/Full path: gate file.
Routing rules in `framework/process-map.md`; path detail in
`workflows/runbooks/build/WORKFLOW.md`.

### 4. Code delegation
Product code goes to main-code-agent. Buddy writes within intent-scope
by discipline. Orchestrator work (agents/, framework/,
skills/, context/, docs/) Buddy writes directly. Detail:
`framework/agent-autonomy.md`.

### 5. Stale cleanup
When an artifact is retired/replaced/sunset, clean up every live
reference in non-frozen files in the same commit. `grep -rn <artifact>`,
filter frozen zones, fix the rest. Discipline-only.

### 6. Deployment verification
After a deploy, look at it. HTTP 200 isn't proof. If you can't see it,
say so and ask the user to check.

### 9. Proportionality of effort
Effort matches stakes. Every decision boundary that creates followup
work (task, gate, test, route, lens-binding) needs a value-floor
judgment: *what named operational cost would NOT doing this incur,
for which named consumer?* Concrete cost + concrete consumer = justified
(a non-blocking fix for performance, stability, security, observability,
maintainability still passes when the cost is named). Hand-wavy
"future-edit safety" / "should be cleaner" / "follows convention" =
re-route. CRITICAL / security / schema / public-API / full-path hard
floors stay in scope regardless.

### 10. Verify mechanical claims with the shell
Before stating a mechanical fact (file exists, grep count, line
numbers, version, byte-identity, command output), run the check (`ls`,
`grep`, `wc`, `read`, `stat`). Don't infer from the model — confident
plausible specifics that turn out wrong are a recurrent silent failure
class. Reviewers carry an evidence-pointer mandate
(`_protocols/evidence-pointer-schema.md`); this is the Buddy-side
equivalent — every load-bearing fact costs one verifying command, not
"sounds right".

*Status: 2026-06-02. Source: CLAUDE.md*
