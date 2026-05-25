# Protocol: MCA-Brief Implicit-Decisions Template

Mandatory decision-class enumeration in the MCA delegation brief.
Prevents brief-quality gap → implementation drift when the brief
stays sketchy and the implementer makes architecture decisions
without spec authority. Discipline-as-mechanism: structural
template fields > LLM persona review.

**Consumed by:** `workflows/runbooks/build/workflow.yaml` step
`delegation-artefact` (instruction).
`agents/main-code-agent.md` input validation as a required field
on Full / Standard.

**Pre-dispatch check:**
`orchestrators/claude-code/hooks/delegation-prompt-quality.sh`
Check C verifies presence + completeness of all 4 classes.

---

## Trigger (when the section is mandatory)

Analogous to the `impl_plan_review` trigger:

- the task has ≥ 3 acceptance criteria, **OR**
- the task contains a schema change (DB / API / event schema), **OR**
- the task has cross-module impact (>1 subsystem affected), **OR**
- the workflow is sub-build (parent has remaining scope).

Below threshold (≤2 ACs, single file, no schema): the section is
optional. Buddy may write a one-sentence rationale why it's not
enumerated.

**Bedrock (why this trigger):** facets per
`agents/buddy/operational.md §Multi-perspective engagement` —
primarily **reversibility** (decisions locked in shipped code are
expensive to undo) and **plural solution-space** (briefs at this
size cover multiple legitimate decision-paths that must be locked
explicitly before MCA fills gaps with its own choices). Count is
the fallback when facets are unclear. Facet-question first, count
as net.

## Section format

Required block in the MCA brief under
`## Implicit-Decisions-Surfaced`. Format is structured YAML —
mechanically parseable for the hook check + downstream skills.

```yaml
implicit_decisions_surfaced:
  schema_and_contract:
    locked: "<status>"
    value: "<decision>"
  error_and_stop:
    locked: "<status>"
    value: "<decision>"
  layer_discipline:
    locked: "<status>"
    value: "<decision>"
  structural_invariants:
    locked: "<status>"
    value: "<decision>"
  other:
    - klasse: "<task-specific decision class>"
      locked: "<status>"
      value: "<decision>"
```

**`locked` values (enum):**

- `"yes — spec §X.Y"` — decision is locked in the spec; MCA
  follows spec authority.
- `"yes — sub-build §X"` — decision is locked in the sub-build
  spec.
- `"no-but-derivable (<rationale>)"` — spec is implicit; MCA can
  derive without risk.
- `"no-NEEDS-LOCKING (Buddy decision: <choice>)"` — Buddy locks
  it in the brief.
- `"n/a (<rationale>)"` — class does not apply to the task.

**`value`** is the concrete decision content (1-3 sentences).

## Decision classes — detail

### 1. schema_and_contract

What shape does the data have, what does the code call it, what
does it return back. Covers:

- Data shape produced / consumed (Pydantic model, DDL schema,
  event payload, NATS subject format).
- Symbol names that could collide with existing imports (StrEnum
  values, Pydantic models, Cypher templates, NATS subjects).
- RETURN-SUMMARY structure (SPEC_VERIFICATION field, INCIDENT
  block, L0 result, files touched).

### 2. error_and_stop

What does the code do when something is wrong, and when does MCA
stop and escalate. Covers:

- How code reacts to errors (exception classes, retry vs fail,
  poison queue, cleanup transaction, compensation action).
- When MCA STOPs + escalates (architecture conflict, spec-
  authority violation, cross-layer impact > brief scope, > N
  file changes without anticipation, non-resolvable test
  failure).

### 3. layer_discipline

Which layer does what (publishing rights, ordering, state
transitions). Cross-layer calls require explicit authority.
Module-graph: who-talks-to-whom.

### 4. structural_invariants

Pattern-purity invariants the implementation MUST preserve or
break-with-rationale. Property-shaped: does the implementation
preserve the root-property the refactor claims to fix?

**Always required on substantial briefs** (NOT conditional on
self-assessed `architecture_touch`). Always-required-with-
`n/a + reason` forces meta-reflection.

**Permitted `locked` values for this class:**

- `"yes — invariant locked: <name>"` — explicit pattern-class
  invariant the implementation preserves.
- `"yes — pattern audited (paths considered: <list>)"` — Buddy
  has surveyed alternative patterns and the locked LD is the
  root-fix.
- `"no-NEEDS-LOCKING (Buddy decision: <choice>)"` — Buddy locks
  it in the brief.
- `"n/a — <why mechanical>"` — the brief is genuinely mechanical
  (mechanical refactor / typo / no-architecture-touch). The
  reason MUST name what makes it mechanical. Bare `n/a` is invalid.

**Three pattern classes the invariant should defend against**
(mirror of `code-architect-roots` / `board-architect-roots`):

- **Smell-transfer:** new pattern has identical root-property
  to old. State the invariant the new pattern preserves.
- **Cycle-symptom-as-cause:** type erosion (`Any` / `dict`)
  justified by import-cycle. State why the cycle is necessary
  OR why the module placement is correct.
- **State-vocabulary half-coverage:** initial state squeezed
  into a working state. State the lifecycle vocabulary
  explicitly.

### 5. other (free-text list)

Task-specific decision classes that don't fit the standard 4.
Examples:

- idempotency-guarantee (event-driven systems)
- retry-policy (NATS consumer config)
- state-machine-transitions (workflow specs)
- ordering-guarantees (concurrent flows)

Format: list of mappings with `klasse + locked + value`.

---

## Anti-patterns

- **DO NOT** fill the section pro forma ("everything locked").
  **INSTEAD** check honestly per class — more `no-NEEDS-LOCKING`
  is more honest than unjustified `yes`.
- **DO NOT** mark `structural_invariants: n/a` without a reason.
  **INSTEAD** name what makes the brief mechanical.
- **DO NOT** drop the section below threshold without rationale.
  **INSTEAD** write `<!-- Below threshold (1 AC, single-file, no
  schema): no decision-class enumeration -->` so the hook WARN
  is explicitly acknowledged.
- **DO NOT** put the section at the end of the brief as a
  postscript. **INSTEAD** place it before `## Acceptance-Criteria`
  — MCA reads top-down; decision locks belong before the AC list.
- **DO NOT** let MCA touch fields, files, or symbols outside the
  brief's explicit scope, even when an identical pattern would
  apply. **INSTEAD** the brief MUST name forbidden adjacent
  scope-changes prescriptively.

- **DO NOT** prescribe a hardcoded literal at a call-site boundary
  (e.g. `cost_currency="USD"`, `tenant_id="default-tenant"`,
  `role="assistant"`) without first grepping the upstream domain
  object for the same field. **INSTEAD** for every literal in a
  §code-touch snippet, grep the upstream model (e.g.
  `grep -n "<field_name>" src/<module>/models.py`). If the field
  exists upstream and is already validated, the brief MUST
  prescribe pass-through (`upstream.field`), NOT a re-derived
  literal. Hardcoding upstream-validated values at boundaries is
  cycle-symptom-cause: works coincidentally today (when the
  upstream value happens to equal the literal), latent bug when
  upstream emits a different value. Briefs ARE code-as-text and
  carry the same grep-verify-discipline as the §-section
  amendment gate in `_protocols/spec-amendment-discipline.md`.

## Bind rule

Subsequent workflow steps must reference the decision locks by
name:

- `mca-implementation` step: MCA's plan MUST contain every
  `no-NEEDS-LOCKING` decision as a constraint (instead of making
  its own decision).
- `code-review-board` step: reviewers check the code against the
  decision locks. Code deviates from a lock → finding.
- `spec-co-evolve-check` step: when a `no-NEEDS-LOCKING` decision
  becomes spec-defined behaviour, apply a spec patch in the same
  block-commit.

---

## Test/Verification scope (DoD guidance)

Distinct from Implicit-Decisions above. Governs the `Test plan` /
DoD section of the MCA brief — what scope MCA tests after each
fix-phase between convergence-loop passes.

**Default:** the brief MUST encode **scope-focused tests**, not
the full repo suite. Full-suite is reserved for convergence-end +
pre-deploy + cross-cutting refactor.

### Per-fix scope rules

Each finding / AC has a known affected scope. The DoD encodes:

1. **Unit tests:** the test file(s) for the modules touched —
   explicit paths (`tests/<module>/test_<file>.py`), not a
   `tests/` glob.
2. **Cross-pass-binding test:** the RED skeleton's test file
   (where applicable) — locks the convergence cluster.
3. **Integration smoke:** 0-1 integration test if the change
   touches a public-API contract or spec-defined behaviour.
4. **L0:** `ruff check <touched-files> && mypy <touched-files>`
   — only on changed files. Not the whole repo.

### Convergence-end full-suite

ONE full-suite run at the END of all convergence-loop fixes,
before close. Not per fix-phase.

### Bind rule (test scope)

`mca-implementation` step: MCA's RETURN-SUMMARY MUST report
per-fix test scope (which scope-files were run + L0 scope) per
fix-phase, plus the single full-suite run at convergence-end.
A blanket `pytest tests/` run with no scope breakdown is a
brief-discipline failure.

---

## Verification-gate cadence

Distinct from test SCOPE above. Governs **when** a verification
gate fires across the brief's commits — per-commit vs once-at-HEAD.

**Trigger (when this section is mandatory):** the brief covers
multiple commits (strangler extraction, shape-preserving refactor,
sequential capability moves, any brief with ≥5 planned commits).
For single-commit briefs, this section is implicit (one commit,
one gate-set; no cadence question).

**Default cadence by bug-class shape:**

| Bug-class shape | Per-commit gate | Once-at-HEAD gate |
|---|---|---|
| **In-process behaviour** — start/stop, dep-order, kwarg migration, fixture-shape, type-check, lint, scope-suite | `pytest <scope-suite>` + L0 (`ruff <touched> && mypy <touched>`) | — |
| **Real-container behaviour** — reverse-stop on SIGTERM, container restart, ansible compose-recreate, real-process signal handling | — | `make app-e2e` + targeted real-container test |
| **Cross-process / external** — Playwright, app-e2e-live, deploy-verify, external-system integration | — | manual or `make app-e2e-live` post-deploy |

**Rule:** if a bug-class is fully covered by an in-process gate
that fires at every commit's scope-suite, the corresponding heavy
external-system gate (e.g. `make app-e2e`) belongs **once at HEAD**,
not per commit. Per-commit external-system gates that an existing
in-process suite already covers are checklist-tick and consume the
brief's time budget without information gain.

**Auto-detection — `code-architect-lens` axis "over-specified gate
cadence":** when the lens runs pre-brief on a multi-commit brief,
check the brief's prescribed verification gates against the cadence
table above. A per-commit external-system gate where an in-process
gate covers the same bug-class is a lens finding (sibling of
smell-transfer, state-vocab-half, cycle-symptom-cause).

**Bind rule (cadence):** for any brief with ≥5 commits, the brief
MUST name per gate (per-commit OR once-at-HEAD) and cite the
bug-class shape that justifies the cadence. *"`make app-e2e` per
commit"* on a strangler brief without naming a real-container
bug-class not covered by chat-suite is a brief-discipline failure
— re-author to once-at-HEAD with the named real-container check.

**Example — strangler extraction of `lifespan` capabilities (14
commits, shape-preserving):** chat-suite (532 tests, in-process
via `TestClient` + lifespan_context) covers BC-1/3/4/5/6 every
commit. BC-2 (reverse-stop drift on real container SIGTERM) is the
only bug-class chat-suite cannot cover (in-process teardown ≠
SIGTERM on pid-1). Brief encodes: per-commit `pytest chat-suite +
L0`; once-at-HEAD `make app-e2e + manual docker SIGTERM + log
inspection`. Cost: 14× chat-suite (already running per commit) +
1× heavy gate at HEAD, vs the naive 14× heavy gate.

**Reject the unsafe shortcut:** NOT *"skip app-e2e entirely on
strangler refactors"*. Real-container bug-classes (reverse-stop,
restart semantics, container-recreate) are real and need their gate
— just once, at HEAD, where the bug-class can actually surface.
The release-valve is cadence, not coverage.

---

## Structural-refactor pre-lock checklist (transitive import graph)

When a brief locks a decision that rearranges the import graph
(extract module / move symbol / break cycle / re-type field
unblocked-by-cycle), the visible-edge analysis is not enough.

### Trigger (when this section is mandatory)

The brief mentions any of:

- `import` / `import cycle` / `circular import`
- `extract` / `extraction` (module/class/symbol)
- `move from X to Y` / `relocate` (module-level symbol motion)
- `unblock typing` / `eliminate Any`
- `forward reference` / `runtime import` / `TYPE_CHECKING`

If the brief contains any of these tokens, the checklist below
MUST be completed and its result documented in the brief BEFORE
locking the decision.

### Pre-lock checklist

1. **List ALL modules that import the affected module.**
   `grep -rn "from <affected>"` — every entry-point that triggers
   the affected module on import.
2. **List ALL modules the affected module imports.** Forward
   direction.
3. **For each (caller, target) pair, check if the new design
   creates a back-edge.** A back-edge from `target` into any
   module already mid-init in the caller chain is a cycle that
   only manifests at import time.
4. **Run baseline collection BEFORE lock.** `pytest --collect-only`
   on every test directory that imports the affected module.
5. **Document any prior workarounds with rationale.** If a prior
   pass typed `Any` or used `TYPE_CHECKING`, restate why.

For static (non-runtime) traversal, use
`scripts/import_graph_check.py` (AST-based).

### Bind rule (structural-refactor briefs)

The brief MUST contain, before the `## Acceptance-Criteria`
section:

- A `## §Import-Graph-Spike` block with the result of steps 1-4
  above.
- The `structural_invariants` decision class MUST cite the spike
  result in its `value:`.
