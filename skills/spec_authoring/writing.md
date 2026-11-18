# Spec authoring — write the spec

Step-loaded unit of `skills/spec_authoring/SKILL.md`. Read it when the interview moves to writing the spec, before
drafting a new spec or section, and before locking a recommendation or a named external or internal surface in it.

## Phase 2 — Write the spec

User + agent write together. Agent proposes; user decides.

### Artifact checklist (REQUIRED on every new spec)

1. **Header:** template from `docs/specs/Spec header.md` (design or
   impl variant). `intent_chain` + metadata table (layer, status,
   `spec_version`, consumers) + "What this spec describes" (3-6 sentences).
2. **SPEC-MAP:** entry in `docs/specs/SPEC-MAP.md` (role / purpose
   — key components). Update consumer columns of all consumed specs
   (bidirectional).
3. **README:** entry in `docs/specs/README.md`.
4. **Failure modes:** section in the spec (per spec-engineering.md
   primitive 3). Missing → P3 FAIL on board review.
5. **Implementation surface:** bullet list of files this spec is
   expected to touch (3-7 paths). Estimate at author-time; refined
   by brief-architect at delegation-time. Not binding; makes the
   spec↔code surface explicit.

   **For NEW L1+ specs:** paired with `§Module-Decomposition` section
   (per `framework/spec-engineering-l1-sections.md`). Phase 1 interview elicits
   per-module: single responsibility, interface hide, sibling relations.

6. **§Test-Strategy (NEW L1+ specs):** bug-class catalog per
   `framework/spec-engineering-l1-sections.md` §Convention: §Test-Strategy.
   Levels in scope + real-vs-mocked policy + table of
   `bug_class | AC ref | levels | implementation`. One row per
   defect class; no duplicates. Phase 1 interview elicits the catalog.

7. **Stored-data shape change:** when the spec changes a persisted
   payload / event / record shape, record the migration-needed check
   (`skills/deprecation_and_migration/SKILL.md` §Migration-needed check):
   decode path named, and version bump, upcast or empty-store
   precondition with its ending trigger.

8. **§Mechanism-Lifecycle (state carrier present):** when the spec
   introduces a thing with two or more states and two or more operations
   that change it — a derived state, a hold / settlement / undo flow, an
   "X changes only via Y" invariant — write the section per
   `skills/_protocols/mechanism-model.md` **before** the board: states
   per carrier, every operation with its grepped producer and its
   consumer, the states × operations matrix with every cell filled and
   placed (`now` / `task-N` / `beyond-MVP` — the vision decides what is
   modelled, the plan when it is built), invariants with enforcement
   locus. Rule: protocol §Scope and placement. Phase 1 elicits it with the user: walk each
   state and ask "what can happen to it, who does that, what must hold
   afterwards?" — one table instead of one rule per scenario.

**Without 1-3 spec is not findable. Without 4 not reviewable. Without
5 brief author re-derives surface. Without 6 test contract is implicit
— post-build coverage gaps then spawn bundle-tasks. Without 8 the
mechanism is reviewed one route at a time, across many passes.**

### Verify-before-recommend

When spec recommends a library / API / tool / pattern: invoke
`get_api_docs` (or first-party verification) BEFORE locking. A spec
that recommends X claims X exists, is current, does what spec says.
Verify; do not carry from training memory. SoT principle:
`agents/buddy/operational.md` §Source-Grounding.

### Integration-surface grounding (REQUIRED)

`Verify-before-recommend` covers *external* surfaces; this covers the
framework's *own*. When the spec names an existing internal surface it
plugs into — an enum value, a contract field, a gate / close sub-step, a
skill / agent name, a config key — **ground each against the live SoT
before board**: open the authoritative file, confirm the surface exists
*as named*, and cite `file:line` in the spec next to the claim. A spec
that says "feeds the N-value `target:` enum" or "consumes sub-step (b)"
asserts that enum / sub-step exists as named — verify it.

**Existence ≠ behavior.** Confirming the surface exists *as named*
grounds only that it is *declared*. A **behavioral** premise about it —
that it is *written / read / populated / reserved / live / never-called*
— is NOT grounded by the declaration; ground it at the **write/read
path** (the mutation / query site) and cite *that* `file:line`. The verb
is the trigger: if you write "is reserved / populated / never called /
live", you owe the write/read site, not the declaration.

Do NOT carry it
from a source task's framing or from training memory: a source task's
claim about a *third* surface is the least-trustworthy source (it may
itself be stale, and the drift then propagates verbatim into the new
spec). Ungrounded → `[integration-pending]` marker; resolve before board
(the chief raises a finding if the marker is present). SoT principle:
`agents/buddy/operational.md` §Source-Grounding.

### Mediator pass-through audit

When spec captures state downstream of a proxy / aggregator / broker /
wrapper SDK: run the 3-question audit BEFORE locking — forward-what,
compute-vs-pass, timing. Document answers in the §-section.
Unverified → `[mediator-audit-pending]` marker; resolve before board
review. Final adoption refuses while the marker is operative
(`spec_success`, evidence-pointer protocol §9.5); drafts stay writable.
Detail: REFERENCE.md.

### Apply the 5 primitives (from spec-engineering.md)

P1 self-contained problem statements (no hidden assumptions).
P2 ACs testable, ≤3 sentences each. P3 constraint architecture (MUST
/ MUST NOT / PREFER / ESCALATE). P4 decomposition (subtasks <2h,
independently verifiable). P5 evaluation design (measurable, not
"looks OK").
