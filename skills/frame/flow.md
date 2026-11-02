# Frame — flow (8 sub-steps)

Step-loaded unit of `skills/frame/SKILL.md`. Read it once depth and caller are set, before step 1, and follow it in
binding order through step 8. Step numbers are skill-wide: the Input, Contract, Gate and Modes in `SKILL.md` refer
to the steps defined here.

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
   anti-pattern). **When a drill output exists (step
   2):** the plan MUST reference the bedrock map (axioms as
   constraints). **Trivial = skip** (save / commit / task-update /
   bookkeeping / status-without-output / pure discussion) with a
   one-sentence rationale. **Bind rule:** subsequent steps reference
   the plan; deviation = explicit rationale. Trigger definition,
   templates, adversary prompt, existing-primitives survey:
   `_protocols/plan-review.md` (SoT).
4. **Source check** (always, source grounding). With a repository caller, grep / glob for
   similar artifacts. Mark hits as part of the solution space, or
   as "touched but different". **On >1 hit:** analysis-mode gate
   (required proof sentence per `_protocols/analysis-mode-gate.md`)
   before classification. **On predecessor-based runs:**
   cross-phase source grounding
   (`_protocols/cross-phase-source-grounding.md`) — mapping table
   required.
   Standalone: inspect supplied evidence/context instead; no repository is required.
5. **Identify constraints** (always). Hard (applicable authorization and supplied constraints,
   sovereignty, skill taxonomy) vs negotiable. Instruction size is
   a loading/coherence review signal, not a hard constraint.
6. **SOTA research** (conditional). Triggers: uncertainty + thin
   solution list + fast-evolving domain + user-explicit + hard to
   reverse. Detail: REFERENCE.md §SOTA-Trigger. **Skip** allowed
   only with a one-sentence rationale in the frame report.
7. **Open the solution space** (always). At least 3 fundamentally
   different approaches (at least 2 in quick). **Always check the
   null option.** **Orthogonality check:** name the distinguishing
   axis per approach (which core assumption it makes that another
   does not). Without an axis = variation; drop the approach.
   Examples: REFERENCE.md §Orthogonality-Check. **Variation lenses:**
   7 lenses
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

Standalone step 6 uses supplied evidence and available research tools directly.
The development research runbook is an optional caller integration, never a
standalone dependency or a requirement to create engine state.

## Source

Source of the variation lenses: agent-skills at `eb07f19` (MIT License, © 2025 Addy Osmani); Forge's register of adopted methods.
