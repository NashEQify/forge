---
name: spec-authoring
description: >
  Interview-based authoring of a NEW spec. Solution-space
  exploration, artifact checklist, intent_chain + intent
  alignment validation. For updating existing specs: spec_update
  skill. For review: spec_board. For brief authoring at
  delegation time: agents/brief-architect.
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

Authoring a spec is not a documentation act, it is a product
decision act. What is in the spec gets built. What isn't, doesn't
exist. When something surfaces during implementation that the
spec doesn't cover: **back to the spec**, don't improvise in the
code. The interview methodology and solution-space exploration
serve exactly that purpose — uncovering gaps BEFORE the code
fills them implicitly.

---

Active methodology for writing a NEW spec via interview.
Theory (5 primitives, conventions):
`framework/spec-engineering.md`. Updating existing specs:
`skills/spec_update/SKILL.md`. Review after authoring:
`skills/spec_board/SKILL.md`.

---

## When to call

- **Write a NEW spec** (not yet existent, greenfield).
- **NEW section in an existing spec** when the section
  describes a feature that doesn't exist yet (interview for
  user intent required).
- User intent exists, but no structured spec yet.
- Scoping mode (high-level intent → L0-L3) identified the need
  for an individual spec.
- Specify phase in the build workflow
  (`workflows/runbooks/build/WORKFLOW.md` §Phase Specify).

### Feature additions to existing specs

When a new feature is added to an existing spec topic (e.g.
"Huddle gets screen recording" added to 50-screenshare.md), that
is **also `spec_authoring`**, not `retroactive_spec_update`.
Rationale: the feature does not yet exist in the code, so there
is no code evidence. User intent must be clarified via interview,
solution space explored, then the spec section written.

The difference vs `retroactive_spec_update`:
- `spec_authoring`: feature does not yet exist → interview →
  spec → code.
- `retroactive_spec_update`: feature exists in code → read code
  → adapt spec.

When unsure which skill applies: ask "does the code already
exist?". Yes → retroactive, no → authoring.

## Do not call for

- **Bring an existing spec to as-is code state** (code is
  ahead) → `retroactive_spec_update`.
- **Only review an existing spec** → `spec_board`.
- **Cross-spec verify after an amendment** →
  `spec_amendment_verification`.

---

## Phase 1 — Interview methodology

The agent (typically Buddy) interviews the user in detail:

- Probe technical and difficult details.
- Question edge cases.
- Surface concerns and trade-offs.
- No obvious questions — ask the hard ones.
- Don't stop until the spec is self-contained.

The goal of the interview is not "to query the user" but to
**uncover gaps together that neither saw before**. The agent
brings the rigor of the 5 primitives (spec-engineering.md); the
user brings intent and product knowledge.

### Grilling mode (pattern lift Phase G tier-2 from Pocock grill-me / grill-with-docs)

For complex / controversial / high-stakes specs, an alternative
interview mode "grilling":

- **One question at a time** (matches the user TRAIT in
  `profile.md` "max one question per turn").
- **Recommended answer per question** (the agent offers its own
  proposal, instead of just asking).
- **Walk down the decision tree systematically** — don't jump
  between topics.
- **Codebase exploration before the question** when the
  question is answerable from the code (the agent greps / reads
  instead of asking).
- **Conflict surfacing:** when the user uses a term / concept
  that conflicts with the existing CONTEXT.md / spec / ADR →
  flag it immediately ("the glossary defines X as Y, but you
  mean Z — which?").

Triggers for grilling mode instead of the standard interview:
- Foundation spec (cascading constraints).
- Spec with high user uncertainty.
- Spec with existing-system conflict risk.
- User request ("grill me", "stress-test the design").

Standard interview vs grilling: standard is multi-aspect, high
frequency. Grilling is single-aspect-deep, recommended-answer-
first, walk-the-tree systematic.

Cross-ref `skills/improve_codebase_architecture/SKILL.md` phase
3 for the grilling loop on architecture refactor (same pattern,
different domain).

### Solution-space exploration (REQUIRED on every spec)

Before fixing a solution, the agent systematically opens the
solution space. That holds inside the interview — NOT only
later in the council (the council fires only conditionally).

**Mechanic:** `skills/frame/SKILL.md` (SoT).

Apply during the interview: the 8 sub-steps of the skill run as
part of the interview. Especially:
- Sub-step 1: reformulate the problem.
- Sub-step 2: first-principles drill — on foundation specs, run
  the full `bedrock_drill` drill with bedrock map.
- Sub-step 7: ≥3 fundamentally different approaches; null
  option allowed.
- Sub-step 8: happy path / edge case / effort / reversibility +
  recommendation with anti-rationalization.

**Bedrock map as constraint input:** when the drill (step 2)
produced a bedrock map, it flows into the spec as a constraint
source. Physics / logic axioms → hard constraints. "YOUR CHOICE"
axioms → soft constraints with explicit rationale. The bedrock
map is referenced in the frame report and is available as
context for board reviewers.

When a council trigger fires after the exploration: the council
gets the approaches from the frame report as input (no fresh
start).

---

## Phase 2 — Write the spec (collaborative)

User and agent write the spec together. The agent makes
proposals; the user gives the answers and final decisions.

### Artifact checklist (REQUIRED on every new spec)

1. **Header:** use the template from `docs/specs/Spec header.md`
   (design-spec or impl-spec variant). `intent_chain` +
   metadata table (layer, status, `spec_version`, consumers) +
   "What this spec describes" (3-6 sentences).

2. **SPEC-MAP:** add an entry to `docs/specs/SPEC-MAP.md` —
   intent in the format "role / purpose — key components".
   Update consumer columns of all consumed specs (bidirectional).

3. **README:** add an entry to `docs/specs/README.md`.

4. **Failure modes:** section in the spec (see
   `spec-engineering.md` primitive 3). Without a failure-modes
   section: P3 FAIL on the later board review.

5. **Implementation surface:** bullet list of files this spec is
   expected to touch or strongly depend on (3-7 paths). Declared
   at author-time as an estimate, refined by brief-architect at
   delegation-time. The list is not binding; it makes the spec ↔
   code surface explicit so downstream brief authoring does not
   re-derive it from spec content.

**Without 1-3 the spec is not findable. Without 4 it is not
reviewable. Without 5 the brief author re-derives the surface.**

### Verify-before-recommend (when the spec proposes a library / API / tool / pattern)

When the spec recommends a specific library, API, tool, or pattern as
the solution: invoke `get_api_docs` (or equivalent first-party
verification) BEFORE locking the recommendation. A spec that recommends
X is a claim that X exists, is current, and does what the spec says X
does — verify the claim explicitly rather than carrying it from
training-data memory. The same discipline applies when the
recommendation evolves: re-verify, do not re-assume. SoT for the
underlying principle: `framework/agentic-design-principles.md` DR-12.

### Apply the 5 primitives (from spec-engineering.md)

While writing each section, treat the 5 primitives as
discipline:
- **P1 self-contained problem statements:** no hidden
  assumptions.
- **P2 acceptance criteria:** stated testably, 3 sentences per
  AC.
- **P3 constraint architecture:** MUST / MUST NOT / PREFER /
  ESCALATE.
- **P4 decomposition:** subtasks <2h, independently
  verifiable.
- **P5 evaluation design:** measurable, not "looks OK".

---

## Phase 3 — intent_chain + alignment validation

### intent_chain

Format, variants (build / life), rules, and inheritance:
`framework/intent-tree.md` (SoT). Required field on delegation
(`CLAUDE.md` §invariant 3 Pre-Delegation), optional in direct
conversation.

### Intent alignment validation (MUST — receiving agents)

Every agent that receives an intent_chain validates before its
first own plan step:

1. Distill the received intent_chain in one sentence (don't
   copy it).
2. Phrase your own plan in one sentence.
3. Check explicitly: consistent?
4. Document the result:

```
Intent alignment:
  Received: [distilled intent_chain in 1 sentence]
  Plan: [your own plan in 1 sentence]
  Consistent: yes — [rationale] / no — [deviation, STOP]
```

On deviation: STOP, escalate to the caller. Direct user
conversation without an intent_chain: skip.

---

## Brief authoring (separate skill)

Brief-time authoring of the MCA delegation artifact lives in
`agents/brief-architect.md` — not in this skill. spec_authoring
produces the spec; brief-architect produces the per-task brief
that translates the spec into MCA-ready instructions.

---

## Amendments to existing specs (architect-dispatched on substantial threshold)

This skill covers **greenfield new specs** and **new sections that
need an interview** (Phase 1). It does NOT cover mechanism-shift /
class-rename / contract-retraction amendments to already-locked
specs — those are authored via `brief-architect` in `mode=spec_amendment`
when the substantial-amendment threshold per spec 306 §14.2 fires.

### When the architect dispatches (spec 306 §14.2 threshold — Variante B)

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
Buddy-direct — no architect dispatch, no spec_authoring entry.

### Dispatch shape

Buddy dispatches via the `Agent` tool:

- `subagent_type: brief-architect`
- prompt sets `mode: spec_amendment`
- prompt provides: target spec file(s) + change-trigger description
  (mechanism shift / class rename / contract retraction) + affected
  ACs/sections + cross-spec references that need coordination +
  `intent_chain`. Architect explores freely from there — no
  whitelist on what it reads.

The architect returns amendment prose + cross-ref edit-list +
spec_version bump suggestion + §Changelog entry, **inline** (no
Write target — orchestrator writes per spec 306 §14.4). Buddy
integrates the prose into the spec file(s), bumps `spec_version`,
and dispatches `spec_amendment_verification` (= `skills/spec_amendment_verification/SKILL.md`)
for cross-spec coherence.

### What stays in this skill

- Phase 1 (interview) for greenfield + new sections needing
  interview.
- Phase 2 (collaborative writing) for greenfield + new sections.
- Phase 3 (intent_chain validation) — applies to any artifact this
  skill produces.
- 5-primitives discipline + artifact checklist + verify-before-
  recommend.

### What dispatches out of this skill

- Mechanism-shift / class-rename / contract-retraction amendments
  → `brief-architect mode=spec_amendment` per the threshold above.
- Code-as-evidence catch-up of an existing spec →
  `retroactive_spec_update/SKILL.md` (which itself dispatches
  `brief-architect mode=retro_spec_update` for Phase 2 walkthrough
  per spec 306 §14.5).
- MCA delegation brief from a locked spec → `brief-architect`
  default `mode=brief`.

### Why greenfield stays Buddy-direct (per spec 306 §14.1)

Phase 1 interview is collaborative-iterative with the user
(grilling-mode, one-question-at-a-time, recommended-answer-first).
The information source is the user, not the corpus. A pass-through-
via-architect pattern would add round-trip cost (User → Buddy →
Architect → Buddy → User per question) without a corresponding
fresh-context win. Architect dispatch makes sense where the
information source is the corpus (existing specs + source code) —
i.e., amendments and retro updates, not new-spec interviews.

---

## Contract

### INPUT

- **Required:** user intent (vision / operational / action).
- **Required:** no existing spec file for this scope (otherwise
  `spec_update`).
- **Required:** access to `framework/spec-engineering.md` (5
  primitives).
- **Required:** access to `docs/specs/Spec header.md` (header
  template).
- **Optional:** scoping-mode output
  (`skills/scoping/SKILL.md`) for high-level intent
  decomposition.
- **Optional:** frame report from `frame` for solution-space
  exploration.

### OUTPUT

**DELIVERS:**
- New spec file under `docs/specs/`.
- SPEC-MAP entry (bidirectional).
- README entry.
- Failure-modes section (required).
- Implementation-surface estimate (required).

**DOES NOT DELIVER:**
- No board review (that is `spec_board`, after authoring).
- No code — the spec is not code, but the prescription for code.
- No implementation.
- No brief authoring — that is `agents/brief-architect.md`.

**ENABLES:**
- `spec_board` review (after authoring).
- `agents/brief-architect.md` brief authoring at delegation time.
- `spec_update` (later, when code evolves and a spec sync is needed).

### DONE

- Spec file exists, with header + content + failure modes +
  implementation surface.
- SPEC-MAP updated (bidirectional with consumers).
- README entry set.
- All 5 primitives applied.

### FAIL

- **Retry:** interview gaps → further rounds with the user.
- **Escalate:** the user cannot answer fundamental intent
  questions → back to scoping mode or intent.md sharpening.
- **Abort:** not foreseen.

---

## Boundary

- **No update of existing specs** → `spec_update` (an interview
  is not needed when behaviour is already in the code).
- **No board review** → `spec_board` (comes after authoring).
- **No cross-spec verify** → `spec_amendment_verification`
  (post-amendment).

---

## Anti-patterns

- **NOT** write a spec without solution-space exploration.
  INSTEAD `frame` sub-steps 1-8 as a required part of the
  interview. Because: the first solution is almost never the
  best, and without explicit exploration the user falls back
  on the first one.

- **NOT** treat failure modes as "I'll add that later".
  INSTEAD as required output of phase 2. Because: P3 FAIL on
  the board review, and the author at the time of authoring is
  best placed to answer "what can go wrong" — later the
  intuition is gone.

- **NOT** treat `intent_chain` as a checkbox ("set, next
  line"). INSTEAD actively derive vision → operational →
  action. Because: an intent_chain without derivation is prose
  that disambiguates nothing.

- **NOT** author multiple new specs in parallel. INSTEAD one
  after the other, with a full interview per piece. Because:
  context switching between specs leads to shallow interviews
  and missed edge cases.

- **NOT** ask the user "does the spec look complete?" or "is the
  approach right?" as a meta-question. INSTEAD identify the
  specific uncertainties and ask about each one with the agent's
  own recommendation attached. Because: whole-spec validation
  outsources the spec author's job — uncovering gaps the user
  did not see — back to the user. Ask sharp questions about
  concrete uncertainties; do not ask the user to judge
  completeness.

- **NOT** lock a structural-refactor decision on visible-edge
  analysis only ("single-cycle focus"). INSTEAD trace the
  transitive import graph from every entry-point that touches
  the affected module (per `_protocols/mca-brief-template.md`
  §Structural-refactor pre-lock checklist) BEFORE the brief
  locks the decision. Because: a brief that examines the
  obvious cycle and misses an adjacent back-edge binds MCA to
  a broken design — the implementation is correct per spec,
  the spec is wrong.

---

## Lessons-table

Failure patterns that shaped current discipline. Each entry: the
failure shape + the discipline rule it produced + the SoT for the
rule.

| Anti-pattern | Failure shape | Discipline rule |
|---|---|---|
| **Single-cycle-focus misses transitive cycles** | Brief examines a visible import cycle (A ↔ B), locks the decision to break it, MCA implements per spec. Post-implementation a *different* test entry-point fails with ImportError because a back-edge elsewhere in the transitive graph was never inspected. The brief's reasoning was correct for the visible cycle, but the visible cycle was not the whole graph. | Pre-lock checklist for any brief mentioning import / cycle / extraction / move-module: walk transitive imports from every entry-point that touches the affected module, run baseline `pytest --collect-only` on those entry-points, document any prior workarounds with rationale. SoT: `_protocols/mca-brief-template.md` §Structural-refactor pre-lock checklist. |
| **MCA scope-creep on adjacent identical patterns** | Brief locks decision X for field A. MCA implements X for A and "helpfully" applies X to adjacent fields B, C in the same file because the pattern looks identical. The brief had described the deferral descriptively, not prescriptively. | Briefs MUST forbid adjacent scope-changes by name when the migration pattern is reusable. Post-implementation grep: `git diff --name-only` vs brief-named files; anything outside is scope-creep. SoT: `_protocols/mca-brief-template.md` §Anti-patterns + §Structural-refactor pre-lock checklist post-impl grep. |
| **Full-suite tests per fix-pass instead of scope-focused** | Convergence-loop runs `pytest tests/` after every fix-phase, burning 2-3× wallclock without surfacing new signal. The fix touched a documented `file:line` scope; re-testing untouched modules adds noise, not safety. | Brief DoD encodes scope-focused tests + L0 on touched files. ONE full-suite run at convergence-end + pre-deploy + cross-cutting refactor. Re-review on FAIL = single-reviewer pass-1.5 of the finding cluster, not full-board redo. SoT: `convergence_loop/SKILL.md` §Test scope between passes + `code_review_board/SKILL.md` §5 Re-review composition + `_protocols/mca-brief-template.md` §Test/Verification scope. |
