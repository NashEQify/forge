# ADR-003: Council mechanism aligned with Board discipline layer (chief, adversary, cold-start brief, evidence-pointer, post-coherence)

## Status
Accepted

## Date
2026-05-31

## Context

The Architectural Council skill (`skills/council/SKILL.md`) had fallen behind the Spec Board / Code Review Board discipline layer over a 14-day period of board hardening (cold-start brief discipline L-046, evidence-chain DoD L-047, chief role-constraint, CHIEF-1.0 chain-of-custody audit, CHIEF-1.1 evidence-pointer gate, CHIEF-1.2 live-state-vs-claim, CHIEF-1.5 value-floor, proportionality §1.0 gate, post-return Architecture-Comprehension B). Concrete asymmetry: council skill frontmatter carried `uses: []` while `spec_board` carried 10 protocols and `code_review_board` carried 6.

Council was structurally:
- Buddy-synthesizes (no chief) — violating CLAUDE.md Inv 1 ("Board/Council: Buddy = Dispatcher")
- Briefing carried "Buddy's proposal" — L-046 brief-contagion violation
- Adversary slot used `code-adversary` whose `Cold-start pre-mission` is L2-code-board-scoped (grep-scans on tests/, schema-parity against alembic/, scope-skepticism on producer/consumer chains) — not architecture-decision-tuned
- No pre-council frame check
- No post-council coherence check
- No evidence-pointer mandate in member output
- No proportionality gate (only narrow cross-scope anti-pattern)

## Decision

Align council structurally with board, with one explicit deviation: council retains light mode as proportional release valve below standard/full.

**Three new personas** (analog to board-chief / code-adversary):
- `agents/council-chief.md` — consolidator-tool (MAY/MAY-NOT scoping; CHIEF-1.0 / 1.1 / 1.2 gates; tracking-table with verification equation; recommended-verdict labels with mechanical predicates: CONVERGED / FRAGILE-CONVERGENCE / DISSENT / NO-CONVERGENCE)
- `agents/council-adversary.md` — architecture-decision adversary (framing-trap / reversibility-trap / missing-stakeholder / default-bypass; rationalization catalogue authored from architectural-decision first principles, not transplanted from `verification-specialist`)
- `agents/council-member.md` — extended with evidence-pointer mandate per `_protocols/evidence-pointer-schema.md` §2

**Council SKILL.md restructured** with 9 protocol loads (was `uses: []`):
- `_protocols/plan-review` (for pre-council frame check)
- `_protocols/context-isolation`, `_protocols/dispatch-template`
- `_protocols/consolidation-preservation`, `_protocols/content-preservation`
- `_protocols/piebald-budget`, `_protocols/analysis-mode-gate`
- `_protocols/evidence-pointer-schema`, `_protocols/discourse`

**Mode shape** (`skills/council/SKILL.md` §1.1, mirrored in `workflows/templates/council.yaml`):
- **light (default on §1.0 pass):** 3 members + chief. No adversary, no frame-check, no discourse. Chief is REQUIRED at N≥3 always (Inv 1).
- **standard:** + council-adversary + plan-adversary pre-council frame check. Fires on ≥2 of {hard-to-reverse, multi-component, security/sovereignty}.
- **full:** 4-6 members + discourse on dissent. Foundational pattern / ≥2 hard constraints / >2 dimensions.

**§1.0 proportionality gate** with 4-question screen + override floor (security/sovereignty multi-component, new state-vocabulary, new public-API contract, new normative cross-spec rule, foundational pattern replacement).

**Briefing format** is cold-start clean: MUST contain question + intent_chain + context-file-paths + null option + perspectives + per-option reversibility cost-band + output paths + file-output OVERRIDE. MUST NOT contain Buddy's proposal / pre-classified conflicts / severity tags / lean hints (L-046 brief-contagion prevention).

**Post-council coherence check** is a Buddy-side rule via `agents/buddy/operational.md` §Architecture-Comprehension B (unconditional re-apply on chief return) — not duplicated as a council step.

**Engine handshake** (L-058 partial closure):
- Solve-refine: `workflow_engine.py council-needed` guard greps state file for `council-required: true` marker; Buddy opt-in.
- Build-context: `workflows/runbooks/build/workflow.yaml` board step has `alternative_skill_refs` documentation-intent (engine reads `skill_ref` only); Buddy MUST start engine manually when council substitutes.

## Alternatives considered

**Alternative A: keep council as island, port only 3 patterns.** Rejected: Buddy would carry two parallel discipline models indefinitely; consistency cost recurring.

**Alternative B: merge council-chief into board-chief with mode switch.** Rejected: persona role-constraints diverge (code/spec ground truth vs architecture decision); cross-contamination risk on prompt-injection mode handling.

**Alternative C: ship rework + auto-fire council from engine on detected criteria.** Rejected: council is Buddy-judgmental per §1.0; mechanical auto-fire would over-trigger on routine decisions; Buddy retains the proportionality call.

## Trade-offs

- **Per-invocation overhead increases** (pragmatist F-CP-001 from review): standard mode is ~6 spawns vs prior ~4. Mitigated by **flipping default to light** (~4 spawns) — most decisions ride light path.
- **Briefing-discipline burden on Buddy** (no Buddy-proposal MUST-NOT): briefing-quality is the new failure mode. CLAUDE.md Inv 10 (verify mechanical claims with shell, ship-time) is the Buddy-side mitigation.
- **Chief vocabulary "fuzzy" risk** (discipline F-CM-001 from review): mitigated by predicate-sharpening of CONVERGED / FRAGILE-CONVERGENCE / DISSENT / NO-CONVERGENCE to convergence-cluster + action-count predicates (chief verdict auditable from tracking table).

## Council review of this decision

Stage 1 council ran 5 members + plan-adversary frame check + council-chief consolidation on the rework itself (eat-our-own-dogfood). Verdict: REWORK-PARTIAL — axis E (council-adversary ClaudeCode fold-in) flagged as CARGO-CULTED BLOCKER. Re-council on axis E rework: NEAR-TARGETED-WITH-RESIDUE, recommended 2 surgical edits (move misplaced §Self-awareness bullet, swap runtime primitives for decision-cognitive primitives in §Recognize). Both applied. Axis E now TARGETED.

Open watch-items (not flip-blockers):
- §1.0 audit-surface mechanically un-auditable (Discipline F-CM-003) — trigger: first observed silent skip
- §Self-awareness opener scaffold mirrors verification-specialist shape (DISSENT in re-council) — trigger: first external OSS-reader comment citing template-mirror
- Mode trichotomy vs composable-knobs (Pragmatist F-CP-003) — trigger: 3rd "fits but doesn't quite fit" mode pick

## Consequences

- Every future architectural decision that passes §1.0 gate flows through council with chief consolidation + evidence-pointer mandate + post-coherence check.
- `pre_build_spec_audit/SKILL.md` Phase 4 updated to reflect new council mechanics (council-adversary + frame-check awareness, candidates listed without lean per L-046).
- `framework/agent-patterns.md` Review-board discipline family row added: "council-discipline parity with board".
- L-058 partial closure: solve-refine has opt-in marker mechanism; build-context council requires Buddy-side engine-start discipline.

## Evidence trail

- Pre-work gap analysis: turn 1 of this session.
- Stage 1 consolidated review: `docs/reviews/council/2026-05-31-council-board-parity-consolidated.md`.
- Axis E re-council consolidated: `docs/reviews/council/2026-05-31-axis-e-rework-consolidated.md`.
- Framework artifacts: 11 files (skills/council/, agents/council-*, workflows/templates/council.yaml, workflows/runbooks/build/workflow.yaml, agents/buddy/operational.md, agents/_protocols/first-principles-check.md, framework/agent-patterns.md, framework/agent-skill-map.md, scripts/workflow_engine.py:2483-2502, CLAUDE.md Inv 10).
