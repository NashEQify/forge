# convergence-loop — REFERENCE

Detail mechanics. `SKILL.md` carries the core (passes, severity,
termination, state format); this file carries the rest.

## Severity guide questions

Complement to the SKILL.md definitions — the guide question makes
the classification mechanical:

| Severity | Guide question |
|----------|----------------|
| BLOCKER | "Can the next step proceed with this artifact?" No → BLOCKER |
| MAJOR | "Will the next step fail or trigger follow-up questions?" Yes → MAJOR |
| MINOR | "Does the outcome of the next step change?" No → MINOR |

Severity is set by the executing agent, not the caller — anchored
at the next step, which is why it is mechanically checkable.

## Sub-workflow override

A sub-workflow may define its own convergence parameters that
override the SKILL defaults (3 passes, BLOCKER / MAJOR / MINOR) —
pass limits, severity labels, or scope-narrowing rules. When it
does, the sub-workflow values apply; without an override the SKILL
defaults apply mechanically.

**Example `spec-board.yaml`:** safety valve at 5 passes, severities
critical / high / medium / low. Mapping: BLOCKER = critical, MAJOR =
high, MINOR = medium + low.

## Fix responsibility

Between passes, who fixes the findings depends on the gate type:

| Gate type | Who fixes | Examples |
|-----------|-----------|----------|
| Review gate (agent reviews someone else's artifact) | Caller (Buddy / user) | Board review (chief, adversary, implementer, impact, consumer) |
| Self-service gate (agent iterates on its own artifact) | The agent itself | Tester design / eval mode, L1 simulation |

Review-gate flow: agent pass 1 → caller fixes → agent pass 2 on
`affected_scope` → caller fixes → agent pass 3 → CONVERGED /
ESCALATE. Self-service runs entirely inside the agent, no hand-off.

**Fix-brief obligation (inter-pass):** the brief handed to the
next-pass reviewer/MCA MUST follow `_protocols/fix-brief-template.md`
whenever pass N reports ≥1 MAJOR/HIGH, a cluster touching >1 file, or
a loose-phrased recommendation. Mandatory sections: phrase-check,
scope-bound (files + LOC cap + trigger-stop), explicit out-of-scope.
The risk is loose phrasing, not missing line numbers — pointer
precision without phrase discipline produces overcorrection.

**Intra- vs inter-gate:** the convergence loop is the intra-gate
loop (one run, the agent iterates over its own findings). "NOT
RELEASED → sharpen the spec → re-run the gate" is the inter-gate
loop — see §Outer-loop bound.

## Scope narrowing

Pass N+1 scope = {areas changed by pass-N fixes} ∪ {directly
dependent areas}. "Directly dependent" = referenced in the same
artifact or logically coupled — not "could theoretically be
affected". Conservatively narrow. Pass 1 has no predecessor → full
scope (declared in step 0).

## Varied analysis patterns (pass 1)

Pass 1 applies several perspectives, not a single read:

| Gate | Varied patterns in pass 1 |
|------|---------------------------|
| Spec review (P1-P5) | Implementer perspective, adversarial reading, cross-reference check |
| Board review | Fresh-look paraphrase, intent-alignment check, constraint-fulfilment simulation |
| Design review (DR-1–DR-10) | Happy-path trace, error-path trace, cognitive-overhead measurement |
| L1 simulation | Happy path, error / edge, concurrent / timing, degraded service |
| Test design | Happy path, error path, boundary, concurrent, stale state |
| Pre-impl eval | Payload sizes, timing variants, degraded service, API mismatch |

Passes 2-3 are also FRESH analyses on the current version, NOT fix
verification — previous findings produce anchoring bias. Finding
tracking (old → new mapping) is the aggregator/chief's job. Scope
narrowing and the severity threshold still apply.

## Outer-loop bound (inter-gate loop)

The inner loop has a pass bound (default 3). The outer loop —
inter-gate: NOT RELEASED → sharpen spec → new convergence loop — is
unbounded by default and can spiral (each cycle introduces new
findings via fix side effects, workflows churn for hours with no
convergence in sight).

**Bound:** max 3 outer-loop cycles per gate owner, override per
sub-workflow.

**At bound hit** (inner CONVERGED, result NOT RELEASED, outer count
== 3): STOP, escalate to the user with the outer-cycle spec-edit
diff trail, the per-cycle unresolved findings, and a recommendation
(rethink the spec, trigger a council, reduce scope).

**Risk carry-forward (mandatory when the user ships the residual):**
the next verdict file written by the calling skill (spec_board /
code_review_board / sectional_deep_review) MUST contain a top-level
`remaining_findings:` block listing every still-open finding (schema
in those skills' SKILL.md). The `risk-followup-routing` workflow step
consumes it and files a single follow-up task. Accept-without-carry-
forward is invalid — escalations without a record disappear between
sessions, the exact failure class this prevents.

**Sub-workflow override:**

```yaml
# In <workflow>.yaml top-level:
convergence_bounds:
  inner_pass_max: 3        # default 3
  outer_cycle_max: 3       # default 3
```

The two bounds are orthogonal — inner terminates per gate, outer per
gate sequence.
