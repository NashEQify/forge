---
name: frame
description: >
  Board-style problem-analysis discipline. Forces multi-perspective
  thinking before solutions are developed. Output: a structured
  frame report with reformulated problem, solution space, and
  recommendation in one turn.
status: active
relevant_for: ["solution-expert"]
invocation:
  primary: workflow-step
  secondary: [user-facing, sub-skill]
disable-model-invocation: false
modes: [quick, standard, deep]
uses: [research, bedrock_drill, _protocols/plan-review, _protocols/analysis-mode-gate, _protocols/cross-phase-source-grounding]
---

# Skill: frame

Prevents Buddy from jumping to the first-best solution. Forces a
disciplined analysis of **the problem itself** before solutions are
developed. Detail mechanics (examples, orthogonality-check case
studies, edge cases): `REFERENCE.md`.

## Who runs it

Buddy (primary). Used as a building block in: solve workflow
(phase 1, main call), build workflow (specify interview), scoping
skill (L0 elicitation when problem framing is unclear), council
preparation (solution-candidate input).

## Input

| Parameter | Required | Description |
|-----------|----------|-------------|
| problem | yes | The user's raw problem description |
| context | no | Additional context (task, spec, existing artifacts) |
| depth | no | quick \| standard \| deep. Default: standard |
| caller | no | solve \| build \| scoping \| standalone. Default: standalone. **Drives the step-2 drill trigger:** solve → full drill always (solve override). Others → per the mode table. MUST be set explicitly by the calling workflow. |

## Output context

- **Inside solve:** the frame report goes into the state-file body
  under `## Phase 1: Frame`.
- **Outside solve** (build, scoping, council): the frame report is
  inline in the chat.

## Flow — 8 sub-steps (binding order)

1. **Reformulate the problem** (always). In your own words, more
   precise than the user's wording. Replace surface language with
   concrete terms.
2. **First-principles drill** (always, even on quick). Decompose
   the assumptions of the reformulated problem down to the
   fundamental point. Runs BEFORE the plan (step 3) so axioms are
   in place before solution paths are planned — no anchoring bias
   from the plan. **Full drill (`bedrock_drill` skill invoke) MUST
   fire when:** (a) called from the solve workflow (always, focused
   as default mode), (b) mode = deep, (c) user-explicit.
   **Otherwise:** minimum — 1 explicit assumption naming + 1
   counter-question (mechanically checkable, no skill invoke).
   **On full drill — output disposition:** `bedrock_drill` returns
   5 sections. All go into the frame report: (1) **Bedrock map**
   → its own section `## Bedrock Map` (required artifact, gate
   relevant). (2) **Axiom tree** → part of the bedrock-map section
   (node hierarchy). (3) **Blind spots** → required prompt to the
   user in the same turn (not deferred). (4) **Bottom-up
   derivation** → reference inside the bedrock map ("Given X → Y
   because Z"). (5) **Axiom alternatives** → its own subsection
   after the bedrock map. **Bedrock-map bind rules (steps 3-8):**
   step 3 (plan) MUST reference axioms as constraints. Step 5
   (constraints) MUST adopt physics/logic axioms as hard
   constraints, YOUR-CHOICE axioms as soft constraints. Step 7
   (solution space) MUST check whether approaches violate bedrock
   axioms. Step 8 (recommendation) MUST keep axiom compatibility
   as an evaluation criterion. Steps 4 + 6: bedrock map available
   as context, no bind required. Detail: REFERENCE.md
   §First-Principles-Drill. Skill: `bedrock_drill/SKILL.md`.
3. **Plan + review** (required for non-trivial; skip for trivial).
   Plan block (scope + tool choice + min 2 alternatives + expected
   artifacts) + self-review (scope check, instance-vs-class,
   rationalization reflex) + on non-trivial dispatch to the
   `plan-adversary` persona. **On a mechanism change** (new field
   / flag / step / skill / hook / state field): existing-primitives
   survey BEFORE the plan block — 3-4 greps + reuse-vs-new decision
   (prevents class-architecture mistakes; the paths-vs-routes
   pattern from 2026-05-02). **When a drill output exists (step
   2):** the plan MUST reference the bedrock map (axioms as
   constraints). **Trivial = skip** (save / commit / task-update /
   bookkeeping / status-without-output / pure discussion) with a
   one-sentence rationale. **Bind rule:** subsequent steps reference
   the plan; deviation = explicit rationale. Trigger definition,
   templates, adversary prompt, existing-primitives survey:
   `_protocols/plan-review.md` (SoT).
4. **Repo check** (always, DR-12 source grounding). Grep / glob for
   similar artifacts. Mark hits as part of the solution space, or
   as "touched but different". **On >1 hit:** analysis-mode gate
   (required proof sentence per `_protocols/analysis-mode-gate.md`)
   before classification. **On predecessor-based runs:**
   cross-phase source grounding
   (`_protocols/cross-phase-source-grounding.md`) — mapping table
   required.
5. **Identify constraints** (always). Hard (CLAUDE.md invariants,
   sovereignty, Piebald budgets, skill taxonomy) vs negotiable.
6. **SOTA research** (conditional). Triggers: uncertainty + thin
   solution list + fast-evolving domain + user-explicit + hard to
   reverse. Detail: REFERENCE.md §SOTA-Trigger. **Skip** allowed
   only with a one-sentence rationale in the frame report.
7. **Open the solution space** (always). At least 3 fundamentally
   different approaches (at least 2 in quick). **Always check the
   null option.** **Orthogonality check:** name the distinguishing
   axis per approach (which core assumption it makes that another
   does not). Without an axis = variation; drop the approach.
   Examples: REFERENCE.md §Orthogonality-Check. **Variation lenses
   (pattern-lift Phase G tier-2 from Addy idea-refine):** 7 lenses
   as a tool to generate orthogonal approaches — Inversion ("what
   if the opposite?"), Constraint removal ("what if budget / time
   / tech weren't constraints?"), Audience shift ("what if for a
   different user?"), Combination ("what if merged with an
   adjacent idea?"), Simplification ("what would the 10x simpler
   variant be?"), 10x scale ("what at massive scale?"), Expert
   lens ("what would a domain expert find obvious?"). Not all
   lenses per frame — pick the 2-3 that produce orthogonal
   approaches.
8. **Evaluate + recommend** (always). Per approach: happy path +
   edge case + effort + reversibility. A recommendation FOR THIS
   context, not "best practice".

FIRST present all approaches fairly, THEN evaluate. No
favourite-approach-first + strawmen.

## Contract

### INPUT
- **Required:** the user's raw problem description.
- **Optional:** context — additional context (task, spec, existing
  artifacts).
- **Optional:** depth — quick | standard | deep (default:
  standard).
- **Optional:** caller — solve | build | scoping | standalone
  (default: standalone). Drives the step-2 drill trigger.
- **Context:** solve context → state file (`docs/solve/*.md`).
  Outside solve → no state file required.

### OUTPUT
**DELIVERS:**
- Frame report: reformulated problem, first-principles result,
  plan + review, repo hits, constraints, solution space (≥3
  approaches with distinguishing axes), context-specific
  recommendation.
- Bedrock map (on full drill — solve context or deep mode): its
  own section in the frame report with typed axioms.
- On decomposition: one frame per sub-problem in the same report.

**DOES NOT DELIVER:**
- No solution / implementation — only solution-space analysis.
- No spec — frame is input for spec authoring, not the spec itself.
- No implementation decision — recommendation only; the user
  decides.

**ENABLES:**
- Solve phase 2 (refine): user can challenge and sharpen the
  frame.
- Build specify: frame as the basis for the spec interview.
- Council: solution candidates as input for a structured decision.

### DONE
- All "always" steps (1, 2, 4, 5, 7, 8) executed (step 3 skipped
  on trivial; step 6 skipped with rationale).
- Step 2: ≥1 assumption naming + ≥1 counter-question
  (mechanically checkable).
- Step 2 on full drill: bedrock map as a dedicated section in the
  frame report.
- Step 7: ≥3 approaches (≥2 in quick), each with a distinguishing
  axis; null option checked.
- Recommendation justified context-specifically.
- Output: reformulated problem + first principles + constraints +
  approaches + recommendation.

### FAIL
- **Retry:** problem too large → decompose inline; one frame per
  sub-problem in the same state file.
- **Escalate:** problem not decomposable, or user uncertainty even
  with the frame → invoke council.
- **Abort:** not foreseen — decompose or escalate.

## Gate

Frame is done when:
- All "always" steps (1, 2, 3, 4, 5, 7, 8) are executed (step 3
  skipped on trivial).
- Step 2 has ≥1 assumption naming + ≥1 counter-question
  (mechanical check).
- Step 2 on full drill (solve context or deep): bedrock map as a
  dedicated section `## Bedrock Map` in the frame report MUST be
  present.
- Step 3 has plan block + self-review block + (on non-trivial)
  adversary review block.
- Step 6 executed OR skipped with a one-sentence rationale.
- Step 7 has ≥3 approaches (≥2 in quick), each with a
  distinguishing axis; null option checked.
- Output: reformulated problem + first principles + bedrock map
  (when drill) + plan + review + repo hits + constraints +
  approaches-with-axes + recommendation.
- Recommendation justified context-specifically.

## Modes

| Mode | When | What changes |
|------|------|--------------|
| quick | Small problem, solution space obvious | Step 2 minimum* (1 assumption + 1 counter-question, no skill invoke), SOTA skipped (documented), ≥2 approaches |
| standard | Default | All "always" steps run normally, SOTA conditional, ≥3 approaches. Step 2 minimum* (no skill invoke) |
| deep | Foundation / cross-layer / schema / new subsystem | + SOTA triggered + 4+ approaches + step 2 MUST invoke `bedrock_drill` (full drill, bedrock map required) |

*\*Solve override: in solve context, step 2 ALWAYS fires the full
drill (`bedrock_drill`, focused as default mode), regardless of
mode level. Solve is by definition for uncertain problems — the
drill is proportional. The mode table then only governs the rest
(SOTA trigger, approaches minimum, etc.), not the drill level.*

**Hard gate — auto-upgrade to deep (MUST):**
- Foundation spec (defines constraints that cascade).
- Cross-layer impact (>1 layer / >2 specs affected).
- New subsystem (first time, no predecessor artifact).
- Schema change (DB / API schema definition).

**Soft upgrade to deep (SHOULD, documented skip allowed):**
- Hard to reverse.
- New domain.

Buddy downgrades to quick when: solution space clear from the repo
check, small, reversible. User override wins.

## Boundary

- No feature build (feature already clear) → build workflow.
- No bug fix (reproduction path clear) → fix workflow.
- No spec review (artifact exists) → spec_board / review workflow.
- No knowledge question (answer to be found) → research workflow.
- No objective with spec hierarchy (done state clear) → scoping
  skill.

## Anti-patterns (short)

- **NOT** ticking the template mechanically. **INSTEAD** every step
  delivers substance. Because: a checklist without content = a
  formal gate without value.
- **NOT** favourite-approach-first + strawmen against the rest.
  **INSTEAD** open the space first, then evaluate. Because:
  rationalization blocks real alternatives.
- **NOT** research as default. **INSTEAD** only on a trigger,
  otherwise documented skip. Because: research is expensive; not
  every problem needs SOTA.
- **NOT** skipping first principles because "it's obvious".
  **INSTEAD** drill exactly when the problem looks clear.
  Because: that's where the wrong assumptions hide.
- **NOT** frame for bugs with a clear reproduction path.
  **INSTEAD** fix workflow. Because: frame is for open solution
  shape, not clear malfunctions.

## References

| Topic | SoT |
|-------|-----|
| Detail mechanics, examples, edge cases | `REFERENCE.md` (this directory) |
| Plan + review (step 3) | `skills/_protocols/plan-review.md` |
| Source grounding (step 4) | `framework/agentic-design-principles.md` DR-12 |
| Research sub-workflow (step 6) | `workflows/runbooks/research/WORKFLOW.md` |
| Use in workflow | `workflows/runbooks/solve/WORKFLOW.md` |
