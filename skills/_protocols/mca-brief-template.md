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

**Pre-dispatch check (discipline):**
Buddy verifies presence + completeness of all 5 classes before
dispatching the brief: Buddy reads this protocol before drafting
and self-checks all 5 classes against the dispatch.

---

## Trigger (when the section is mandatory)

Analogous to the `impl_plan_review` trigger:

- the task has ≥ 3 acceptance criteria, **OR**
- the task contains a schema change (DB / API / event schema), **OR**
- the task has cross-module impact (>1 subsystem affected), **OR**
- the workflow is sub-build (parent has remaining scope).

Below threshold (≤2 ACs, single file, no schema): optional; Buddy
may write a one-sentence rationale why it's not enumerated.

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
  vision_alignment:
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

## Workflow scope (instance stamping — when a sibling workflow is live)

When this brief dispatches an agent **inside a workflow step** and
`workflow_engine.py --next` reports a `NOT-YOURS:` line (≥2 workflows live in
the checkout), paste the engine's `SCOPE:` + `NOT-YOURS:` block from `--next`
verbatim into the brief. This **stamps the agent with its own file pointers** so
it never reconstructs "which files are mine" by browsing `docs/<workflow>/` or
`.workflow-state/` — the failure that let a parallel workflow's agent (solve-593)
trip over a sibling's files (solve-594).

- Hand the agent its OWN concrete paths (state file, task file). Do **not** hand
  it a directory to browse — fewer cues beat more warnings.
- The `NOT-YOURS:` line names the sibling files to ignore.
- `--next` shows no `NOT-YOURS:` (single workflow live): omit the block —
  nothing to disambiguate.

This is content the agent NEEDS, so it lives **here in the brief**, never in the
anti-bias `dispatch-template.md` (whose contract is to STRIP Buddy's context out,
the opposite operation).

## Decision classes — detail

Decision classes are load-bearing downstream: MCA references
`no-NEEDS-LOCKING` decisions as plan constraints; `code_review_board`
reviewers check code against decision locks (deviation = finding);
chief uses them for triage; proportionality gates
(`code_review_board` §1.0 / `spec_board` §1.0) use the same vocabulary
(new state-vocab / new SSE type / new public API / schema break).

### 1. schema_and_contract

What shape does the data have, what does the code call it, what does
it return back. Covers:
- Data shape produced / consumed (Pydantic model, DDL schema, event
  payload, NATS subject format).
- Symbol names that could collide with existing imports (StrEnum
  values, Pydantic models, Cypher templates, NATS subjects).
- RETURN-SUMMARY structure (SPEC_VERIFICATION field, INCIDENT block,
  L0 result, files touched).

### 2. error_and_stop

What does the code do when something is wrong, and when does MCA
stop and escalate. Covers:
- Error reactions: exception classes, retry vs fail, poison queue,
  cleanup transaction, compensation action.
- STOP+escalate conditions: architecture conflict, spec-authority
  violation, cross-layer impact > brief scope, > N file changes
  without anticipation, non-resolvable test failure.

### 3. layer_discipline

Which layer does what (publishing rights, ordering, state
transitions). Cross-layer calls require explicit authority.
Module-graph: who-talks-to-whom.

### 4. structural_invariants

Pattern-purity invariants the implementation MUST preserve or
break-with-rationale. Property-shaped: does the implementation
preserve the root-property the refactor claims to fix?

**Always required on substantial briefs** (NOT conditional on
self-assessed `architecture_touch`). `n/a` requires named reason;
bare `n/a` invalid (forces meta-reflection).

Permitted `locked` values for this class:
- `"yes — invariant locked: <name>"` — explicit pattern-class
  invariant the implementation preserves.
- `"yes — pattern audited (paths considered: <list>)"` — Buddy has
  surveyed alternative patterns and the locked LD is the root-fix.
- `"no-NEEDS-LOCKING (Buddy decision: <choice>)"` — Buddy locks in
  the brief.
- `"n/a — <why mechanical>"` — mechanical refactor / typo /
  no-architecture-touch. Reason MUST name what makes it mechanical.

Three pattern classes the invariant should defend against (mirror
`code-architect-roots` / `board-architect-roots`):
- **Smell-transfer:** new pattern has identical root-property to old.
  State the invariant the new pattern preserves.
- **Cycle-symptom-as-cause:** type erosion (`Any` / `dict`) justified
  by import-cycle. State why the cycle is necessary OR why the module
  placement is correct.
- **State-vocabulary half-coverage:** initial state squeezed into a
  working state. State the lifecycle vocabulary explicitly.

### 5. vision_alignment

What the active `intent.md` Vision says the touched surface IS, so MCA
decides the forks the brief leaves OPEN top-down, not local-default —
the product-vision-root as an INPUT to in-flight decisions. MCA is the
one decision point where a sub-agent decides scope / defer / build
without Buddy in the loop, so the Vision-premise must travel IN the
brief.

Observable, not posture: name what the Vision calls this surface
(product deliverable / PoC consumer / internal scaffold / out-of-scope)
and the decision that follows from it. A surface the Vision names as a
deliverable is a product surface even at zero built consumers — "no
consumer yet" is not a defer-signal (cross-ref `CLAUDE.md` Inv 9 +
`code_review_board` value-floor Vision-named-surface carve-out). Uses
the standard `locked` enum.

**Required when the brief touches a product surface** the Vision names;
`n/a (<why — internal / mechanical / no product surface>)` otherwise.
Bare `n/a` invalid.

**Architecture reading-map — point, don't re-derive.** When the touched
surface spans a subsystem AND the project's `intent.md` names an as-built
architecture reading-map, the brief MUST point the MCA at it (the project's
coarse→fine orientation entry + the as-built flow / spec docs it indexes),
so the MCA arrives oriented instead of re-deriving the architecture from
`src/`. Per-agent re-derivation is the recurring failure: each delegated
agent re-greps the same chokepoints, and a change spanning stages silently
drops a leg / seam. Generic by contract — name the map ONLY if the
project's `intent.md` declares one; never hard-code a path here (the path
lives in the consumer's `intent.md`; this template is project-agnostic).
This is the brief-layer of a deliberate selectivity: the same pointer is
kept OUT of `dispatch-template.md` and the board scaffolds, whose contract
is to STRIP context for fresh-read anti-bias review — a map ref there would
corrupt the isolation. A build brief is the opposite contract (the MCA
SHOULD arrive oriented).

### 6. other (free-text list)

Task-specific decision classes that don't fit the standard 5.
Examples: idempotency-guarantee (event-driven systems), retry-policy
(NATS consumer config), state-machine-transitions (workflow specs),
ordering-guarantees (concurrent flows). Format: list of mappings with
`klasse + locked + value`.

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

- **DO NOT** prescribe a code-touch on a file or region (e.g.
  "extend the SSE handler in `chatAdapter.ts`", "add the audit fold
  to `orchestrator.py:1406`") without first grepping the upstream
  surface for whether the contract is already satisfied by existing
  wiring. **INSTEAD** for every prescribed code-touch: grep the
  upstream wiring (parent handler, mediator, capability boundary).
  If the upstream surface already satisfies the prescribed contract,
  the brief MUST say "verify X unchanged" not "extend X".
  Prescribing extension of pre-existing wiring is cycle-symptom-cause
  at the file / region level — same class as the hardcoded-literal
  bullet above with broader trigger. Catches the implicit "extend X"
  case where the brief prescribes a code-touch WITHOUT the
  `## Claim-Verifications` trigger phrases (`reuses existing`,
  `supersedes`, `already implemented`, etc.).

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

## Test/Verification scope (DoD)

Brief encodes **scope-focused tests**, not full repo suite.
Full-suite reserved for convergence-end + pre-deploy + cross-cutting
refactor.

Per-fix DoD:
1. **Unit tests** — explicit paths (`tests/<module>/test_<file>.py`),
   not a `tests/` glob.
2. **Cross-pass-binding test** — RED skeleton's test file (where
   applicable) locks the convergence cluster.
3. **Integration smoke** — 0-1 test only if public-API contract or
   spec-defined behaviour touched.
4. **L0** — `ruff check <touched-files> && mypy <touched-files>` —
   touched files only.
5. **Resource-lifecycle audit** (only when the fix introduces a
   pooled/singleton resource carrying a close/teardown/invalidate
   path) — the lifecycle test (`skills/testing/SKILL.md`
   §Execution-faithfulness) must EXECUTE build-once/reuse/close-awaits/
   rebuild against a fake matching the INSTALLED SDK surface, AND audit
   whether an autouse reset-fixture masks the singleton (if so, the
   lifecycle test opts out of the reset). A green suite over a
   masked singleton proves nothing about teardown.

**Convergence-end full-suite:** ONE run at END of convergence-loop
fixes, before close.

**Bind rule:** MCA RETURN-SUMMARY reports per-fix scope + the
single convergence-end full-suite. Blanket `pytest tests/` without
scope breakdown = brief-discipline failure.

---

## Verification-gate cadence

Governs **when** a gate fires — per-commit vs once-at-HEAD. Mandatory
when brief covers multiple commits (strangler, shape-preserving
refactor, sequential moves, ≥5 commits). Single-commit briefs:
implicit (one commit, one gate-set).

**Default cadence:**

| Bug-class shape | Per-commit | Once-at-HEAD |
|---|---|---|
| In-process (start/stop, dep-order, kwarg, fixture-shape, type-check, lint, scope-suite) | `pytest <scope-suite>` + L0 (`ruff <touched> && mypy <touched>`) | — |
| Real-container (reverse-stop on SIGTERM, restart, ansible compose-recreate, real-process signals) | — | `make app-e2e` + targeted real-container test |
| Cross-process / external (Playwright, app-e2e-live, deploy-verify) | — | manual or `make app-e2e-live` post-deploy |

**Rule:** bug-class fully covered by an in-process gate firing per
commit → the heavy external-system gate belongs ONCE at HEAD, not
per commit. Per-commit external gates duplicating in-process
coverage = checklist-tick, no information gain.

**Auto-detection:** `code-architect-lens` axis "over-specified gate
cadence" flags per-commit external-system gates whose bug-class an
in-process gate already covers.

**Bind rule:** brief with ≥5 commits MUST name per gate (per-commit
OR once-at-HEAD) and cite the bug-class shape that justifies the
cadence. Re-author per-commit gates without a named real-container
bug-class to once-at-HEAD.

**Reject the unsafe shortcut:** NOT "skip app-e2e entirely on
strangler refactors". Real-container bug-classes are real; the
release-valve is cadence (once at HEAD), not coverage.

---

## Claim-Verifications (MUST when trigger formulations present)

If any AC, `intent_chain`, or brief section uses one of the trigger
formulations below, the brief MUST include a `## Claim-Verifications`
table with one row per claim:

- **Existing-impl triggers:** `supersedes`, `reuses existing`,
  `already implemented`, `wraps existing`, `delivered in Task`,
  `existing-code verifications confirm`.
- **Spec-citation triggers:** `spec requires X`, `AC says Y`,
  `per <file>.md §Z`, `<file>.md:N`.
- **Cross-producer dedup/collision/reconcile triggers:** any AC/brief
  that dedups, collides, or reconciles facts/events from ≥2 producers
  on a shared key (`reconcile`, `dedup`, `collapse the fork`,
  `more-specific-wins`, `same (key) different (type)`). The check is
  NOT "does the key exist?" but "does the key CO-LOCATE what the two
  producers actually EMIT?" Emit **one row per producer** (≥2 rows):
  for each, grep the *key-assignment site* — the line where that
  producer constructs the value that becomes the shared key (grep the
  key field-name, not a `build_*`/`emit_*` naming convention) — and
  quote the literal value. Then add a **co-location verdict** line: do
  the quoted values land under the SAME key? `FALSIFIED` = they do NOT
  co-locate (the seam is a production no-op). The key is often *derived*
  (`normalize(name)`, a tuple) — quote the value AFTER the derivation
  the seam keys on, not the raw emit. A premise inherited from a
  council/ADR is a claim, not a settled fact.

| Claim | Source-ref | grep command | grep output | Disposition |
|---|---|---|---|---|
| <verbatim claim phrase> | `<file:line>` for spec-cite OR `<scope-path>/` for existing-impl | `grep -n "<pattern>" <target>` | <verbatim stdout OR `(no output)`> | `CONFIRMED` / `FALSIFIED` / `SILENT` |

Disposition values:

- `CONFIRMED` — grep evidence supports the claim
- `FALSIFIED` — zero hits OR hits contradict the claim
- `SILENT` — target exists but doesn't address the claim
  (spec-cite only; escalation flag for council / user)

Producer is `code-architect-lens` (fresh-context-isolated reads
code / spec, runs grep — see lens §Claim-Verifications, single
merged table). Brief-architect copies the verbatim rows. **Adversary
re-verifies at L2 dispatch** per `agents/code-adversary.md`
§Cold-start pre-mission — two-pass author / verifier separation.
SKILL text remains binding; adversary's L2 re-verification is the
load-bearing check.

Any `FALSIFIED` row → brief is INCOMPLETE, return to author for AC
re-scope before MCA dispatch.

### Bind to the resolved seam, not a proxy (verification depth)

A Claim-Verifications row — or any VERIFY / CONFIRM gate that names a seam an
artifact MUST hit — has to resolve to the *runtime binding the claim rests on*,
never a name-match or a runtime symptom that a wrong target also satisfies. Two
recurring proxy-traps; both are the same root (the gate certified a **proxy** of
the obligation, not the obligation at its **real seam**):

- **Existing-impl / DTO-reuse claims → verify at the construction site.** When a
  `reuses existing` row asserts a wire / transport / envelope surface reuses an
  internal or sibling DTO, the grep MUST reach the first-party client / SDK that
  *constructs* the typed envelope — not merely confirm the field or type exists.
  Nominal typing (e.g. Pydantic) rejects a structurally-identical sibling
  instance at construction: field-presence reads GREEN while the constructor is
  RED. A `reuses existing` row whose grep stops at field-presence is SILENT on
  the claim, not CONFIRMED.
- **Test-seam obligations → verify the resolved callee identity.** When a gate
  mandates a test be (re-)pointed at a named production seam and asserts
  execution / `0 skipped`, pair that with a callee-identity check: grep the
  test's *resolved* target and assert it `==` the production caller, not a
  same-named orphan / twin. `0 skipped` reads GREEN while the test binds dead
  code that carries the same symbol the skip-guard probes.

---

## Reviewer Checkpoints — 4-link Evidence Chain DoD (MANDATORY for L2)

Every claim "C-N closed" / "INV-N satisfied" in MCA RETURN-SUMMARY or
reviewer verdict MUST carry the 4-link evidence chain:

| Variant | Link 1 | Link 2 | Link 3 | Link 4 |
|---|---|---|---|---|
| Signal-routing | Producer site | Boundary translation site | Consumer ACK / NAK / TERM site | Test that fails if boundary re-flattens |
| Schema / data | Write site | Read site | Constraint site (DDL / model) | Test |

Each link: `file:line` + 1-3 line verbatim code-quote (test variant:
`test:line` + assertion shape).

Fewer links = claim does NOT qualify as "closed". Chief rejects and
re-dispatches with the missing link explicit
(`agents/code-chief.md` + `agents/board-chief.md` §4-link
enforcement). Value-floor + bundle-laundering rules apply to
disposition; 4-link is a separate (and prior) gate on whether a
closure-claim is even valid.

Forces opening the file at each link → prevents single-layer
verification (helper repaired but signal-exit boundary still broken).

---

## Structural-refactor pre-lock checklist

Mandatory when brief mentions any of: `import` / `import cycle` /
`circular import` / `extract` / `extraction` / `move from X to Y` /
`relocate` / `unblock typing` / `eliminate Any` /
`forward reference` / `runtime import` / `TYPE_CHECKING`.

Pre-lock steps (result documented in brief BEFORE locking):
1. List ALL modules importing the affected module
   (`grep -rn "from <affected>"`).
2. List ALL modules the affected module imports (forward direction).
3. For each (caller, target) pair: check if new design creates a
   back-edge into a module already mid-init in caller chain.
4. Baseline collection BEFORE lock: `pytest --collect-only` on every
   test dir importing the affected module.
5. Document prior workarounds with rationale (typed `Any`,
   `TYPE_CHECKING`).

Static traversal: `scripts/import_graph_check.py` (AST-based).

**Bind rule:** brief contains, before `## Acceptance-Criteria`, a
`## §Import-Graph-Spike` block with steps 1-4 results; the
`structural_invariants` class cites the spike result in its
`value:`.
