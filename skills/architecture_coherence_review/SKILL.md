---
name: architecture-coherence-review
description: >
  Cross-spec coherence review for specs that share contracts.
  7-dimension extraction, interface-contract assembly, advisory
  board. Formalized from Task 274 experience.
status: active
verification_tier: 1
evidence_layout: per_finding
invocation:
  primary: workflow-step
  secondary: [user-facing, sub-skill]
disable-model-invocation: false
uses: [spec_board, convergence_loop, _protocols/evidence-pointer-schema]
---

# Skill: architecture-coherence-review

## Purpose

Checks whether 2+ specs that share interfaces (API routes, NATS
subjects, Pydantic models, schema definitions) are actually
consistent. Single board reviews check specs in isolation —
coherence reviews check the seams BETWEEN specs.

Formalized from the process developed for Task 274 (foundation
specs).

## When to call

- ≥2 specs share contracts (API signatures, event schemas, type
  definitions).
- Significant change to a foundation spec consumed by others.
- Before a milestone gate when several specs are implemented
  together.

## 7 dimensions

| Dim | What is checked |
|-----|-----------------|
| 1. Signatures | Function / method signatures, return types, parameters |
| 2. Types | Pydantic models, enums, literal types, type aliases |
| 3. Schemas | DB DDL, event payloads, JSON schemas |
| 4. Naming | Same term = same spelling (subjects, endpoints, fields) |
| 5. Config | Consumer configs, ENV vars, feature flags |
| 6. Error | Error taxonomies, error codes, fallback behaviour |
| 7. Lifecycle | State machines, retry policies, timeouts, cleanup |

## Phases

```
PHASE 0 — PREP
  Read the specs, consult the SPEC-MAP, identify interface points.
  Output: extraction scope (which sections in which specs, per
  dimension).

PHASE 1 — EXTRACT
  Per spec: extract interface definitions across all 7 dimensions.
  Output: extraction matrix (spec × dimension → concrete values).

PHASE 2 — ASSEMBLE
  Compare extractions. Per interface point:
  - CONSISTENT: all specs aligned.
  - DIVERGENT: specs contradict each other (detail: what diverges).
  - GAP: interface defined in one spec, missing in another.

  Output: interface contract (CONSISTENT + DIVERGENT + GAP lists).

PHASE 3 — ADVISORY
  Board review of the DIVERGENT + GAP findings.
  Skill: spec_board (standard mode) on the interface-contract
  document.
  Agents check: is the divergence a real bug or intentional
  asymmetry?
  Prioritization: which divergences must be fixed before
  implementation.

PHASE 4 — FIX
  Fix divergences and gaps — edits in the affected specs.
  Per fix: which spec is SoT? The SoT spec stays; the consumer
  spec is adapted.
  Ownership: docs/spec-ownership.md (when present).
  Content preservation: → _protocols/content-preservation.md.

PHASE 5 — VERIFY (optional)
  On >5 fixes: a verification pass on the fixed places.
  Otherwise: Buddy checks mechanically (grep on the fixed
  patterns).
```

## Artifact paths

```
docs/reviews/coherence/
  {review-name}-extraction.md      Phase 1 output
  {review-name}-contract.md        Phase 2 output (interface contract)
  {review-name}-advisory-*.md      Phase 3 board files
  {review-name}-fixes.md           Phase 4 fix log
```

## Contract

### INPUT
- **Required:** ≥2 specs that share contracts (API signatures,
  event schemas, type definitions).
- **Required:** SPEC-MAP (`docs/specs/SPEC-MAP.md`) — for
  interface identification.
- **Required:** all involved specs must be board-reviewed
  (single spec first).
- **Optional:** previous interface contract — for delta updates
  instead of starting from scratch.
- **Context:** `spec_board/SKILL.md` (phase 3 uses spec_board as
  a sub-skill).

### OUTPUT
**DELIVERS:**
- Extraction matrix: spec × 7 dimensions → concrete interface
  values.
- Interface contract: CONSISTENT + DIVERGENT + GAP lists
  (persistent artifact).
- Advisory findings: board-checked judgment (real bug vs
  intentional asymmetry).
- Fix log: per fix: SoT spec, consumer spec, what was changed.

**DOES NOT DELIVER:**
- No single-spec review — only interfaces BETWEEN 2+ specs.
- No code analysis — spec level only.
- No full corpus — max 4-5 specs per review (otherwise the
  matrix grows too large).

**ENABLES:**
- Build verify (multi-spec): cross-spec consistency as a gate
  before implementation.
- Milestone gate: interface alignment as a precondition for
  parallel implementation.
- Spec fixes: SoT assignment per divergence → clear fix
  routing.

### DONE
- Extraction matrix complete (every spec × 7 dimensions).
- Interface contract persisted (CONSISTENT + DIVERGENT + GAP).
- Advisory board executed on DIVERGENT + GAP.
- Every DIVERGENT finding decided (kept with rationale OR
  aligned with a fix).
- Fixes committed individually.
- Verification pass executed on >5 fixes.

### FAIL
- **Retry:** advisory NEEDS-WORK → fix → verification pass on
  the fixed places.
- **Escalate:** divergence requiring an architectural
  ground-decision → council or solution-expert.
- **Abort:** >4-5 specs → split by subsystem (the matrix grows
  too large).

## Constraints

- PREP is Buddy work (read specs, SPEC-MAP, grep). No agent
  dispatch in phases 0-2.
- ADVISORY (phase 3) uses `spec_board` as a sub-skill — same
  mechanics, same protocols.
- Fixes are committed individually (not batched).
- The interface contract is a persistent artifact — updated on
  future reviews.

## Lessons learned (Task 274)

- Foundation specs (HC4 × GBWI × HRP × brain-foundation): 182
  interfaces extracted, 99 consistent, 56 divergent, 21 gaps,
  11 HIGH decisions.
- Typical effort: 2-3 sessions for 3-4 specs.
- Batching the fixes by theme (schema, auth, error,
  observability) worked well.

## Boundary

- No single-spec review → `spec_board` (coherence checks
  interfaces BETWEEN specs; the board checks spec quality).
- No code analysis → `code_review_board` (spec level only).
- No single-interface change → `spec_amendment_verification`
  (when amendment-character).
- Max 4-5 specs per review — split by subsystem on a larger
  corpus.

## Anti-patterns

- **NOT** start a coherence review before a Spec Board pass.
  INSTEAD review every spec individually first, then run
  coherence on the result. Because: spec-internal
  inconsistencies hide interface divergences.
- **NOT** bundle >4-5 specs into one coherence review. INSTEAD
  split by subsystem. Because: the interface matrix becomes
  quadratic; attention is unrecoverable.
- **NOT** accept divergent findings without an explicit
  decision. INSTEAD per divergence: kept (rationale) or aligned
  (fix plan). Because: "known" is not "resolved".
- **NOT** ADVISORY phase without a spec_board dispatch. INSTEAD
  fixes must pass through the board before being finalized.
  Because: coherence fixes can degrade spec quality; the board
  catches that.
