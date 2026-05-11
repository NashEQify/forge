# convergence-loop — REFERENCE

Detail mechanics. The Buddy-facing `SKILL.md` carries the core
mechanic (passes, severity, termination, state format). This file
is reference material for sub-workflow overrides, severity guide
questions, fix responsibility, scope narrowing, varied analysis
patterns, and DR coverage.

## Severity guide questions

A complement to the definitions in SKILL.md. The guide question
makes the classification mechanical:

| Severity | Guide question |
|----------|----------------|
| BLOCKER | "Can the next step proceed with this artifact?" No → BLOCKER |
| MAJOR | "Will the next step fail or trigger follow-up questions?" Yes → MAJOR |
| MINOR | "Does the outcome of the next step change?" No → MINOR |

The severity is set by the executing agent — not by the caller.
The definitions are anchored at the next step (not in the
abstract), which is why they are mechanically checkable.

## Sub-workflow override

Specific sub-workflows may define their own convergence parameters
that override the SKILL defaults (3 passes, BLOCKER / MAJOR /
MINOR). When a sub-workflow has different pass limits, severity
labels, or scope-narrowing rules, the sub-workflow values apply.

**Example `spec-board.yaml`:** safety valve at 5 passes with
critical / high / medium / low.

**Severity mapping:** BLOCKER = critical, MAJOR = high, MINOR =
medium + low.

Without an override, the SKILL defaults apply mechanically.

## Fix responsibility

Between passes, somebody has to fix the findings. Who depends on
the gate type:

| Gate type | Who fixes between passes | Examples |
|-----------|--------------------------|----------|
| Review gate (agent reviews someone else's artifact) | Caller (Buddy / user) | Board review (chief, adversary, implementer, impact, consumer) |
| Self-service gate (agent iterates on its own artifact) | The agent itself | Tester design mode (own test plan), tester eval mode (own hypotheses), L1 simulation (own scenarios) |

Review-gate control flow:

```
Agent: pass 1 → findings to the caller
Caller: applies fixes
Agent: pass 2 on affected_scope → findings
Caller: applies fixes
Agent: pass 3 → CONVERGED / ESCALATE
```

Self-service gate runs entirely inside the agent — no control-flow
hand-off.

**Fix-brief obligation (inter-pass):** the brief Buddy/author
hands to the next-pass reviewer/MCA MUST follow
`skills/_protocols/fix-brief-template.md` whenever pass N reports
≥1 MAJOR/HIGH OR a cluster touching >1 file OR the reviewer
recommendation is itself loose-phrased. Mandatory sections:
phrase-check (4 anti-pattern classes), scope-bound (files + LOC
cap + trigger-stop), explicit out-of-scope. The risk is loose
phrasing, not missing line numbers — perfect pointer precision
without phrase discipline produces overcorrection.

**Boundary against the inter-gate loop:** the logic "NOT RELEASED
→ sharpen the spec → re-check the affected primitives" is the
inter-gate loop (the gate fails, the artifact is reworked
fundamentally, the gate runs again from the start). The
convergence loop is the intra-gate loop (within one run, the
agent iterates over its own findings). Both can occur back to
back: convergence loop CONVERGED with result NOT RELEASED →
inter-gate loop → new convergence loop on the reworked spec.

## Scope narrowing

Pass N+1 scope = {areas changed by pass-N fixes} ∪ {directly
dependent areas}.

"Directly dependent" = referenced in the same artifact or
logically coupled. Not "could theoretically be affected".
Conservatively narrow, not expansively.

**Pass 1 has no predecessor** → full scope (declared in step 0).

## Varied analysis patterns (pass 1 only)

Pass 1 is not just "read the document." The agent MUST apply
several perspectives / patterns:

| Gate | Varied patterns in pass 1 |
|------|---------------------------|
| Spec review (P1-P5) | Implementer perspective, adversarial reading, cross-reference check |
| Board review (chief / adversary / implementer / impact / consumer) | Fresh-look paraphrase, intent-alignment check, constraint-fulfilment simulation |
| Design review (DR-1 - DR-10) | Happy-path trace, error-path trace, cognitive-overhead measurement |
| L1 simulation | Happy path, error / edge path, concurrent / timing, degraded service |
| Test design | Happy path, error path, boundary, concurrent, stale state |
| Pre-impl eval | Various payload sizes, timing variants, degraded service, API mismatch |

**Pass 2 and 3 are also FRESH analyses** on the current artifact
version — NOT fix verification. Previous findings produce
anchoring bias (empirical: tainted passes miss high findings a
fresh look catches). Finding tracking (old → new mapping) is the
job of the aggregator / chief, not the individual reviewers.
Scope narrowing and the severity threshold still apply.

## Detailed boundaries

- **Not** the fix loop in `main-code-agent` (fix → review → test
  → fix). A different loop with different actors.
- **Not** the gate cascade itself. The cascade decides which gates
  run. This skill decides how a gate works internally.
- **Not** the review protocol (superseded, replaced by Spec Board
  — Task-182 F-2).
- **Not** alternatives evaluation. The convergence loop finds
  defects and converges. Divergent thinking (alternative
  approaches, better designs) belongs in the Architecture Council
  (`workflows/runbooks/build/WORKFLOW.md` specify step COUNCIL,
  `workflows/runbooks/solve/WORKFLOW.md` phase Refine) or the
  Solution Expert Council. Defect search converges, alternatives
  evaluation diverges — both in the same loop produces scope
  creep.
- **Not** applicable to execution steps (writing code, running
  tests). Only analytical / validating gates.

## DR coverage

- **DR-1 (Proof by Structure):** the state format forces explicit
  findings + a termination check per pass. The step-0 intent
  paraphrase is proof that the agent understood the brief.
- **DR-7 (Cognitive Overhead):** max 3 passes + the severity
  threshold prevents unbounded iteration. Scope narrowing reduces
  context pressure per pass.
- **DR-8 (Context = Working Memory):** only `affected_scope` +
  findings go into the next pass, not the entire artifact again.

## Outer-loop bound (inter-gate-loop termination)

The inner loop has a pass bound (default 3, override per
sub-workflow). The outer loop (inter-gate loop: NOT RELEASED →
sharpen spec → new convergence loop) is unbounded by default.
Consequence: a workflow can run any number of inner loops in
sequence as long as each pass-3 returns NOT RELEASED.

**Bound:** max 3 outer-loop cycles per gate owner. Override per
sub-workflow (analogous to the inner-loop override convention).

**Behaviour at bound hit:**
- Inner loop CONVERGED, result NOT RELEASED, outer-cycle count ==
  3 → STOP.
- Escalate to the user with:
  - List of all outer-cycle spec edits (diff trail).
  - Inner-loop findings per cycle (what didn't resolve from cycle
    N to N+1).
  - A recommendation (e.g. fundamentally rethink the spec, trigger
    a council, reduce scope).

**Risk carry-forward at bound hit (mandatory when the user accepts
the residual):** when the user decides to ship despite the
outer-bound hit, the next verdict file written by the calling
skill (spec_board / code_review_board / sectional_deep_review)
MUST contain a top-level `remaining_findings:` YAML block listing
every still-open finding (schema in those skills' SKILL.md files).
The downstream workflow step `risk-followup-routing` (build / review
/ fix workflow.yaml) consumes that block and files a single
follow-up task. No block / accept-without-carry-forward is invalid
— escalations without a carry-forward record disappear between
sessions, which is exactly the failure class this mechanism
prevents.

**Anti-pattern when the bound is missing:**
spec-edit spiral — every cycle introduces new findings via fix
side effects. Without an outer bound, workflows spiral for hours
with incremental spec edits and no convergence in sight.

**Sub-workflow override convention:**

```yaml
# In <workflow>.yaml top-level:
convergence_bounds:
  inner_pass_max: 3        # default 3
  outer_cycle_max: 3       # default 3
```

The two bounds are orthogonal — the inner bound terminates per
gate, the outer bound terminates per gate sequence.
