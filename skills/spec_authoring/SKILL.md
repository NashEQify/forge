---
name: spec-authoring
description: >
  Interview-based authoring of a NEW spec. Solution-space
  exploration, artifact checklist, intent_chain + intent
  alignment validation. For updating existing specs: spec_update
  skill. For review: spec_board. For brief authoring at
  delegation time: agents/brief-architect.
  Triggers when a NEW spec or a new spec section is needed (the code does not exist yet); NOT for syncing specs to code (use retroactive_spec_update) or review (use spec_board).
status: active
relevant_for: ["main-code-agent"]
invocation:
  primary: workflow-step
  secondary: [user-facing]
disable-model-invocation: false
uses: [frame, spec_board, spec_update]
---

# Skill: spec-authoring

## Guiding principle

**The spec defines the product. Incidents are fixed in the spec,
not in the code.**

Authoring = product decision act, not documentation. What is in the
spec gets built. When something surfaces during implementation that
the spec doesn't cover: **back to the spec**, don't improvise in
code. Theory (5 primitives, conventions):
`framework/spec-engineering.md`. Detail mechanics (grilling mode,
mediator audit, lessons-table, extended anti-patterns):
`REFERENCE.md`.

## When to call

- **Write a NEW spec** (greenfield).
- **NEW section in existing spec** when the section describes a
  feature that doesn't exist yet (interview for user intent required).
- User intent exists, no structured spec yet.
- Scoping mode (high-level intent → L0-L3) identified the need.
- Specify phase in build workflow.

**Feature additions to existing specs** = `spec_authoring`, not
`retroactive_spec_update`. The feature does not yet exist in code, so
no code evidence; user intent must be clarified via interview. When
unsure: code already exists? Yes → retroactive, no → authoring.

## Do not call for

- **Bring existing spec to as-is code state** → `retroactive_spec_update`.
- **Only review** → `spec_board`.
- **Cross-spec verify after amendment** → `spec_amendment_verification`.

## Phase 1 — Interview

Buddy interviews the user:

- Probe technical and difficult details; question edge cases.
- Surface concerns and trade-offs.
- No obvious questions — ask the hard ones.
- Don't stop until the spec is self-contained.
- **For NEW L1+ specs — bug-class elicitation:** for each draft AC,
  ask "what defect class does this AC guard against? at which test
  level?". Capture noun-phrase answers as `bug_class` rows in the
  §Test-Strategy catalog (Phase 2 checklist item 6). Dedup at
  elicitation; small variations within a bug class do not warrant a
  new row (per `testing/SKILL.md` proportionality rules). When in
  doubt, drop.

Goal: **uncover gaps together that neither saw before**, not "query
the user".

**Grilling mode** (one question at a time, recommended-answer-per-
question, walk-the-tree systematic): for foundation / high-stakes /
high-uncertainty / conflict-risk specs. Detail: REFERENCE.md.

### Solution-space exploration (REQUIRED)

Mechanic: `skills/frame/SKILL.md` (SoT). 8 sub-steps run inside the
interview. Especially: reformulate problem, first-principles drill
(`bedrock_drill` on foundation specs), ≥3 fundamentally different
approaches (null option allowed), happy/edge/effort/reversibility
evaluation. Bedrock map (when drilled) flows in as constraint source
— physics/logic axioms = hard constraints, YOUR-CHOICE = soft with
rationale. If a council fires after exploration: council gets frame
approaches as input (no fresh start).

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
   (per `framework/spec-engineering.md`). Phase 1 interview elicits
   per-module: single responsibility, interface hide, sibling relations.

6. **§Test-Strategy (NEW L1+ specs):** bug-class catalog per
   `framework/spec-engineering.md` §Convention: §Test-Strategy.
   Levels in scope + real-vs-mocked policy + table of
   `bug_class | AC ref | levels | implementation`. One row per
   defect class; no duplicates. Phase 1 interview elicits the catalog.

**Without 1-3 spec is not findable. Without 4 not reviewable. Without
5 brief author re-derives surface. Without 6 test contract is implicit
— post-build coverage gaps then spawn bundle-tasks.**

### Verify-before-recommend

When spec recommends a library / API / tool / pattern: invoke
`get_api_docs` (or first-party verification) BEFORE locking. A spec
that recommends X claims X exists, is current, does what spec says.
Verify; do not carry from training memory. SoT principle:
`agents/buddy/operational.md` §Source-Grounding.

### Mediator pass-through audit

When spec captures state downstream of a proxy / aggregator / broker /
wrapper SDK: run the 3-question audit BEFORE locking — forward-what,
compute-vs-pass, timing. Document answers in the §-section.
Unverified → `[mediator-audit-pending]` marker; resolve before board
review (board chief raises finding if marker present). Detail:
REFERENCE.md.

### Apply the 5 primitives (from spec-engineering.md)

P1 self-contained problem statements (no hidden assumptions).
P2 ACs testable, ≤3 sentences each. P3 constraint architecture (MUST
/ MUST NOT / PREFER / ESCALATE). P4 decomposition (subtasks <2h,
independently verifiable). P5 evaluation design (measurable, not
"looks OK").

## Phase 3 — intent_chain + alignment validation

`intent_chain` format / variants / inheritance rules:
`framework/intent-tree.md` (SoT). Required on delegation (CLAUDE.md
invariant 3); optional in direct conversation.

**Intent alignment validation** (MUST — receiving agents): every
agent that receives an intent_chain validates before its first plan
step. Distill received intent in one sentence; phrase own plan in
one sentence; check consistent yes/no; document. Deviation → STOP,
escalate. Direct user conversation without intent_chain: skip.

## Brief authoring (separate skill)

Brief-time MCA delegation artifact lives in `agents/brief-architect.md`,
not here. spec_authoring produces the spec; brief-architect produces
the per-task brief that translates spec → MCA-ready instructions.

## Amendments to existing specs

This skill covers **greenfield specs** and **new sections that need
an interview**. It does NOT cover mechanism-shift / class-rename /
contract-retraction amendments to locked specs — those go through
`brief-architect mode=spec_amendment` when the substantial-amendment
threshold fires.

**Amendment discipline** (pre-edit gate, dispatch threshold, dispatch
shape, greenfield-direct rationale): `_protocols/spec-amendment-discipline.md`.

## Contract

**INPUT:** user intent, no existing spec file for this scope,
access to `framework/spec-engineering.md` + `docs/specs/Spec header.md`.
Optional: scoping output, frame report.

**OUTPUT:** new spec under `docs/specs/`, SPEC-MAP entry, README
entry, failure-modes section, implementation-surface estimate.

**DOES NOT:** board review (→ `spec_board`), code, implementation,
brief authoring (→ `agents/brief-architect.md`).

**DONE:** spec file with header + content + failure modes +
implementation surface; SPEC-MAP bidirectional; README entry; 5
primitives applied.

**FAIL handling:** interview gaps → more rounds. User cannot answer
fundamental intent questions → ESCALATE back to scoping or intent.md
sharpening.

## Boundary

- No update of existing specs → `spec_update`.
- No board review → `spec_board`.
- No cross-spec verify → `spec_amendment_verification`.

## Anti-patterns

- **NOT** write spec without solution-space exploration. INSTEAD
  `frame` sub-steps 1-8 as required interview part.
- **NOT** treat failure modes as "I'll add later". INSTEAD required
  Phase 2 output.
- **NOT** treat `intent_chain` as checkbox. INSTEAD actively derive
  vision → operational → action.
- **NOT** author multiple new specs in parallel. INSTEAD sequential,
  full interview per spec.
- **NOT** ask "does the spec look complete?" as meta-question.
  INSTEAD identify specific uncertainties; ask sharp questions with
  agent's own recommendation attached.
- **NOT** lock structural-refactor on visible-edge analysis only.
  INSTEAD trace transitive import graph per
  `_protocols/mca-brief-template.md` §Structural-refactor pre-lock
  checklist BEFORE brief locks the decision.
- **NOT** generate two-option questions from handoff/spec disagreement
  without code-grounding first.
- **NOT** assume mediator pass-through; verify it (3-question audit).

Extended anti-patterns + Lessons-table (full failure-shape +
discipline-rule rows): REFERENCE.md.
