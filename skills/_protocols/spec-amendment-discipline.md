# Protocol: Spec-Amendment Discipline

Authoring discipline for **amendments to already-locked specs**:
when to dispatch to `brief-architect mode=spec_amendment`, when to
stay Buddy-direct, and the pre-edit gate that applies in both cases.

**Consumed by:** `skills/spec_authoring/SKILL.md` §Amendments to
existing specs (pointer). `agents/brief-architect.md` §Modes
(`mode=spec_amendment`) — dispatch contract; see §Your Process +
§Required Output. `docs/specs/306-brief-architect.md §14.2`
(threshold authority).

**Why a protocol, not skill prose:** the discipline is reference
material at edit-time. Long-form rules embedded in SKILL.md don't
get re-read during fast amendment work and the skill bloats
(inflation-guard, `framework/skill-anatomy.md`). Protocol form
keeps SKILL.md scan-able and the detail one-click away.

---

## Pre-edit code-source-grounding gate (applies to all amendment paths)

Before authoring an amendment to an existing §-section that describes
runtime behavior, component placement, or any code-observable state,
ground against the actual code state:

1. **Grep the codebase** for the symbols / components referenced in
   the §-section being amended:
   - **(1a) Identifier extraction:** every backticked symbol in the
     §-section + every CapitalizedWord that names a class /
     component / module / file. Lowercase prose words ("the sidebar",
     "the cache") are not identifiers.
   - **(1b) Repo-shape grep roots:** see `docs/STRUCTURE.md §Code zones`
     for the active repo. Common roots: `src/`, `frontend/src/`,
     `agents/`, `skills/`, `scripts/`. Multi-language repos: include
     all source roots. Skip generated dirs (`dist/`, `node_modules/`,
     `.venv/`).
   - **(1c) Zero-hit handling:** zero hits = symbol no longer exists
     in code OR was renamed OR was never built. **Investigate before
     amending** — do not silently accept the §-section text as
     authoritative when the code anchor is gone.
   - **(1d) Cost ceiling:** ground the 2-3 symbols load-bearing for
     the runtime behavior the §-section describes; not every
     mentioned identifier. If the §-section describes one class doing
     three things, grep the class.
2. **Read the matching code paths** to determine actual current state.
3. **Compare** current code state vs the §-section text being amended.

### Same-commit reconciliation rule

If code state diverges from the §-section text (see §What counts as
divergence below), the divergence MUST be reconciled in the SAME
amendment commit (CLAUDE.md §Stale cleanup invariant) — adding a
"spec-drift-fix" strand to the amendment cluster, not deferring to a
separate task. Cross-doc stale references to the same artifact are
swept by `spec_amendment_verification` post-amendment per §Dispatch
shape below.

The same single-commit absorption applies to category (d)
module-boundary topics on L1+ specs via the §module-decomposition-add
strand — sister mechanism, different trigger.

**The amendment author writes the spec to match the code** — unless
the build is explicitly changing the code-shape, in which case the
spec leads.

### Applies to both paths

- **Buddy-direct sub-threshold amendments:** Buddy runs the gate
  before drafting.
- **Architect-dispatched substantial amendments**
  (`mode=spec_amendment`): the architect inherits the gate as part
  of its dispatch contract — it grounds against code BEFORE
  drafting amendment prose, and the returned prose includes any
  spec-drift-fix strands surfaced by the grounding.

### Trigger conditions (mechanical apply-test)

**Apply when ANY clause in the §-section names a symbol that exists
or should exist in code** — class / file / function / endpoint /
column / env-var / YAML key / migration / CLI flag / config key.
Identifier-mentioned → gate fires, even when other clauses in the
same paragraph are pure intent.

Skip the gate when the §-section is **identifier-free**:

- Pure design intent (no symbol references)
- Non-implementation prose (rationale, history, glossary)
- Future-direction prose without anchored symbols
- A new section for a feature that does not exist in code yet
  (handled by `spec_authoring` Phase 1 interview; zero-hit grep is
  expected, do not treat as drift)

**AC-in-locked-section-but-not-yet-built clause:** if the §-section
is locked but the AC under amendment is for unbuilt behavior, the
gate applies to the symbols it names; zero-hit grep is expected.

### What counts as divergence

Three categories, with reconciliation triggers:

- **(a) Named-symbol mismatch** — the §-section names `FooBar` but
  the code now has `BarFoo`, OR the named class has been removed.
  → **ALWAYS reconcile** in same commit.
- **(b) Structural change with semantic load** — signature change,
  file location moved with implications for consumers, contract shift.
  → **Reconcile when the §-section claims the structure.** If the
  §-section is identifier-only ("uses FooBar") without claiming
  shape, the move alone is not divergence.
- **(c) Abstraction-level mismatch** — the §-section uses paraphrase
  ("the cache layer"), the code uses literal names (`RedisCache`).
  → **NOT divergence.** Paraphrase ↔ literal is intentional
  abstraction.
- **(d) Module-boundary topic in an L1+ spec without §Module-Decomposition
  (touch-it-fix-it for the new-class L1+ discipline)** — when the
  amendment scope touches module-boundary topics (interface, dependency,
  layer, seam, responsibility-split) AND the host spec is L1+ AND the
  host spec does NOT yet have a §Module-Decomposition section, the
  amendment MUST add the §Module-Decomposition section in the SAME
  commit (per the schema in `framework/spec-engineering.md`
  §Convention: §Module-Decomposition for L1+ specs).
  → **Reconcile in same commit** as a §module-decomposition-add strand.
  Mirrors the §spec-drift-fix strand semantics from §Same-commit
  reconciliation rule above. Triggers only on amendment-into-topic;
  unrelated amendments to legacy L1+ specs (typo, §Changelog, cross-ref
  bump) do NOT trigger the absorption.

**Strand-scope stop rule:** the spec-drift-fix strand covers the
§-sections that name the diverged symbol(s). Recursion stops at the
first §-section that doesn't name the symbol — even if that
section is conceptually adjacent.

### Why

Without re-reading the code, the amendment author is biased toward
the existing spec text even when it has drifted from reality.
Handoff wording and current spec text can disagree; **code is the
tiebreaker**. Neither handoff nor spec is automatically authoritative
on as-is implementation state.

**Concrete failure mode (pattern-level):** an amendment drafted
from handoff text disagreeing with current spec text, both sources
stale relative to the code. A two-option question generated from
the disagreement becomes a false dichotomy when code-grounding
would surface a third state. Pre-edit grounding also surfaces drift
in adjacent sections (e.g. layout diagrams describing the moved
component), pulling stale-cleanup into the same commit instead of
a separate task.

### Cross-ref

`spec_amendment_verification` — post-amendment cross-spec coherence
check (dispatched by Buddy after architect integration; see
§Dispatch shape below). The §-prose ↔ code-symbol gate is currently
human-only; mechanical mirror at the §-section level is not
implemented (`consistency_check` covers path-reference drift, not
§-prose drift). Sub-skill expansion possible as a future task.

---

## Architect-dispatch threshold (spec 306 §14.2 — Variante B)

Dispatch `brief-architect mode=spec_amendment` when **any** of:

- Cross-reference cascade ≥3 in one spec (e.g. a class rename
  touches ≥3 active-text occurrences).
- Cross-spec coupling — ≥2 specs need coordinated amendment.
- Class-rename / mechanism-shift / contract-retraction (semantic
  change, not just wording).
- Buddy-heuristic: "interactively more than 1 edit-round with
  cross-ref-sights anticipated".

Sub-threshold amendments (1-line correction, typo, §Changelog-only
append, single-sentence rewording without cross-ref impact) stay
Buddy-direct — no architect dispatch.

## Dispatch shape

Buddy dispatches via the `Agent` tool:

- `subagent_type: brief-architect`
- prompt sets `mode: spec_amendment`
- prompt provides: target spec file(s) + change-trigger description
  (mechanism shift / class rename / contract retraction) + affected
  ACs/sections + cross-spec references that need coordination +
  `intent_chain`. Architect explores freely from there — no
  whitelist on what it reads.

The architect returns amendment prose + cross-ref edit-list +
`spec_version` bump suggestion + §Changelog entry, **inline** (no
Write target — orchestrator writes per spec 306 §14.4). Buddy
integrates the prose into the spec file(s), bumps `spec_version`,
and dispatches `spec_amendment_verification`
(= `skills/spec_amendment_verification/SKILL.md`) for cross-spec
coherence.

## What stays in `spec_authoring` skill

- Phase 1 (interview methodology) for greenfield specs and new
  sections needing user-interview.
- Phase 2 (collaborative writing) for greenfield + new sections.
- Phase 3 (intent_chain validation) for any artifact this skill
  produces.
- 5-primitives discipline + artifact checklist + verify-before-
  recommend.
- Mediator pass-through audit (general spec-write discipline, not
  amendment-specific — applies during greenfield Phase 2 too).
- Sub-threshold amendments (1-line correction, typo, §Changelog-only
  append, single-sentence rewording without cross-ref impact) —
  Buddy-direct, no architect dispatch. The pre-edit gate above
  still applies.

## What dispatches out of `spec_authoring` skill

- Mechanism-shift / class-rename / contract-retraction amendments
  → `brief-architect mode=spec_amendment` per the threshold above.
- Code-as-evidence catch-up of an existing spec →
  `retroactive_spec_update/SKILL.md` (which itself dispatches
  `brief-architect mode=retro_spec_update` for Phase 2 walkthrough
  per spec 306 §14.5).
- MCA delegation brief from a locked spec → `brief-architect`
  default `mode=brief`.

## Why greenfield stays Buddy-direct (per spec 306 §14.1)

Phase 1 interview is collaborative-iterative with the user
(grilling-mode, one-question-at-a-time, recommended-answer-first).
The information source is the user, not the corpus. A pass-through-
via-architect pattern would add round-trip cost (User → Buddy →
Architect → Buddy → User per question) without a corresponding
fresh-context win. Architect dispatch makes sense where the
information source is the corpus (existing specs + source code) —
i.e., amendments and retro updates, not new-spec interviews.
