---
name: council
description: >
  Structured architectural / strategic decision-making. Four modes:
  (a) light — 3 council-members + chief, default on §1.0 proportionality pass.
  (b) standard — 3 members + adversary + chief + frame-check, escalation tier.
  (c) full — 4-6 members + adversary + chief + discourse + frame-check, foundational decisions.
  (d) interactive — Buddy moderates a user dialog with perspectives.
  All non-interactive modes use context-isolated members; chief consolidates;
  Buddy decides per CLAUDE.md Invariant 1.
  Triggers when an architecture/strategy decision has more than one viable path and is hard to reverse, AND Buddy is uncertain; NOT for single-path, easily-reversible, or current-scope-decidable cross-scope contradictions.
status: active
verification_tier: 1
evidence_layout: per_finding
relevant_for: ["solution-expert"]
invocation:
  primary: workflow-step
  secondary: [user-facing]
disable-model-invocation: false
modes: [light, standard, full, interactive]
uses: [_protocols/plan-review, _protocols/context-isolation, _protocols/dispatch-template, _protocols/consolidation-preservation, _protocols/content-preservation, _protocols/piebald-budget, _protocols/analysis-mode-gate, _protocols/evidence-pointer-schema, _protocols/discourse]
---

# Skill: council

Buddy checklist + operational detail. (REFERENCE.md folded back into
SKILL.md per ADR-004 / piebald-budget update 2026-05-31 — REFERENCE
pattern deprecated; everything substantive lives here.)

## 0. Plan + review (required without a frame)

Direct council dispatch without prior `frame`: plan block (scope / tool / alternatives) + self-review + (non-trivial) `plan-adversary` dispatch. With existing frame report: reference, don't re-run. Templates + triggers: `_protocols/plan-review.md`.

## 1. Mode determination

### 1.0 Proportionality gate (MANDATORY — runs before §1.1)

Default = escalate. Answer 4:

1. >1 genuinely viable path AND hard to reverse?
2. >1 layer / component affected by the decision?
3. Substantial impact on security / sovereignty / simplicity / experience / compatibility / scale?
4. Buddy genuinely uncertain (not "looking for confirmation")?

**Answer pattern:**
- **≥3 yes** → council (proceed to §1.1).
- **≤2 yes** → no council. Document skip: *"Council not needed: <rationale>"*. Decide directly.

**Override floor (forces standard or full regardless of count):** security / sovereignty hard constraint AND multi-component · new state-vocabulary or new public-API contract · new normative cross-spec rule · foundational pattern replacement.

**Anti-pattern (cross-scope vs current-scope):** if the question presents as "spec corpus has multiple representations of X" but current-scope path is internally consistent (producer + consumer + adjacent uses all aligned) and contradictions live in different scopes → **NO council**. Preserve current path; file normalisation as follow-up task. Council on cross-scope when current is decidable wastes a cycle + introduces re-framing risk (Council recommendation adopted autonomously becomes a frame user has to unwind).

Walk-through: (1) Is CURRENT-SCOPE path internally consistent? Check producer + consumer + adjacent uses. All same representation → path IS decidable. (2) Contradictions in DIFFERENT scopes (legacy / future / cross-cutting infra)? (3) Way to preserve current path + file normalisation as follow-up? All three yes → NO council.

### 1.1 Mode choice (after gate passes)

Detailed mode-profile table (aligned with `workflows/templates/council.yaml`):

| Mode | Members | Adversary | Chief | Frame-check | Coherence-check (Buddy-side) | Discourse | ADR |
|------|---------|-----------|-------|-------------|------------------------------|-----------|-----|
| **light** (default) | 3 | — | yes (all modes — Inv 1) | — | required | — | optional |
| **standard** | 3 | yes | yes | yes (`plan-adversary`) | required | — | yes |
| **full** | 4-6 | yes | yes | yes | required | on dissent | yes |
| **interactive** | dialog-perspectives | conceptual | — | — | required | per-round | optional |

Trigger short-form:
- **light** — default on §1.0 pass.
- **standard** — ≥1 of §1.0 override-floor items, OR ≥2 of {hard-to-reverse, multi-component, security/sovereignty}.
- **full** — >2 dimensions OR foundational pattern OR ≥2 hard constraints.
- **interactive** — user explicit ask only (Buddy moderates a dialog — see §10).

**Chief is required for all council modes** per Invariant 1 — Buddy never synthesizes member outputs directly. Light is light by virtue of no-adversary + no-frame-check + no-discourse, NOT by skipping chief.

**Coherence-check** is a Buddy-side rule (`agents/buddy/operational.md` §Architecture-Comprehension B), applied unconditionally on every chief return. Not a duplicated council step.

**Member model config** (yaml `member_config`): minimum 2× Opus + 1× Sonnet per non-light mode for cognitive diversity. Light: 2× Opus + 1× Sonnet or 3× Opus.

Default = light (proportional release valve). **Mode escalation** (light → standard → full) is criterion-driven, not Buddy-uncertain — picking standard/full just because Buddy feels uncertain is mode inflation. (Separate axis: **user escalation** vs council — see `agents/buddy/operational.md` §Multi-perspective engagement Council-before-user-escalation rule; that rule says when §1.0 fires AND the alternative is asking the user, council wins. Both rules coexist: §1.0 governs whether council fires AND which mode; council-before-user-escalation governs council-vs-user when §1.0 fires.)

## 2. Pre-council frame check (standard / full)

**Trigger:** Buddy-drafted briefing without upstream frame report. (When `frame/SKILL.md` already produced a frame-report for this question, reference it — don't re-run.) Mode determines whether the trigger applies; light skips frame-check by mode.

Buddy drafts briefing → dispatches `plan-adversary` cold-start on the draft (criteria 1-6 per `_protocols/plan-review.md`; focus: does question pre-decide by shape? option-set complete? stakeholders missing?) → persists return verbatim as `docs/reviews/council/<date>-<topic>-frame-check.md` → distills concerns into FINAL briefing.

Members see FINAL briefing only. Council-chief reads BOTH at CHIEF-1.0.

## 3. Briefing format (cold-start clean — MANDATORY)

**MUST:** question (1 sentence) · intent_chain anchoring · context-file paths · null option (1-2 sentences) · perspectives + ranks · per-option reversibility cost-band (S/M/L/XL effort × named consumers impacted — lets adversary §Reversibility-trap check verify the claim rather than reconstruct from scratch) · output paths · file-output OVERRIDE block (`_protocols/dispatch-template.md` §File-Output-OVERRIDE).

**MUST NOT:** Buddy's proposal · pre-classified conflicts · severity tags · lean hints. Brief-contagion empirically demonstrated (L-046).

## 4. Buddy checklist (dispatch)

1. §1.0 gate → mode pick.
2. §2 pre-council frame check (standard / full).
3. Write briefing per §3 (clean). Path: §7.
4. Spawn N members + adversary in ONE tool block, parallel, `run_in_background: true` (subagent_type + perspective + briefing path + output path + file-output OVERRIDE).
5. Wait, then spawn `council-chief` with all member outputs + adversary + (when present) frame-check artifact.
6. Read chief consolidated → recommended verdict + tracking-table verification.
7. (Full + dissent) Discourse one round per `_protocols/discourse.md`.
8. Buddy decides. Post-council coherence check applies via `agents/buddy/operational.md` §Architecture-Comprehension B (unconditional Buddy-side rule — not duplicated as a council step). Risk carry-forward when positions unresolved. ADR per `documentation_and_adrs/SKILL.md` on substantial decisions.

## 5. Anti-patterns

- **NOT** Buddy's proposal in briefing → cold-start per §3; proposal stays in frame-check artifact.
- **NOT** consolidate without council-chief (≥3 members) → Inv 1 hard rule; chief is consolidator-tool.
- **NOT** skip pre-council frame check on standard/full → frame-check IS how you find brief contamination.
- **NOT** adopt chief recommendation without post-council coherence check per `agents/buddy/operational.md` §Architecture-Comprehension B → unconditional Buddy-side, escalate on topology contradiction.
- **NOT** `code-adversary` for council adversary → `council-adversary` (architecture-decision-tuned).
- **NOT** light mode on hard-to-reverse → standard or full.

## 6. Contract

**INPUT:** decision-question + intent_chain + context-files. Optional: frame report, ADR catalogue, deploy-state observations.

**OUTPUT:** council-decision artifact (`docs/reviews/council/<date>-<topic>-decision.md`) with: chief consolidation + recommended-verdict label + Buddy's actual decision + rationale + risk carry-forward (when applicable) + ADR pointer (when substantial). Backward-compat: also valid for `docs/tasks/{task_id}-council-decision.md` per existing `workflows/templates/council.yaml`.

**DOES NOT:** implement; write spec; choose autonomously (user decides on user-facing decisions; Buddy decides on framework-internal per soul.md).

**FAIL handling:** chief reports NO-CONVERGENCE → check whether briefing framing is wrong (re-frame + new council on revised question) OR escalate to user. Standard → Full on ≥1 adversary BLOCKER + member disagreement.

## 7. Output paths

Base: `docs/reviews/council/<date>-<topic>-{briefing,frame-check,{perspective},consolidated,decision}.md`. Build-context backward-compat: `docs/tasks/{task_id}-council-*.md` per `workflows/templates/council.yaml`.

## 8. Boundary

Spec review → `spec_board`. Code diff → `code_review_board`. Pre-code plan → `impl_plan_review`. Technical architecture moderator → `solution-expert` (instantiates this skill, 6 fixed perspectives per `values.md`). Non-technical → this skill with situational perspectives (see §9 below).

## 9. Perspective profiles

### architecture (default for ARCH-XXX decisions)

Ranks from `~/projects/personal/context/user/values.md` constraint hierarchy:

| Rank | Perspective | Focus |
|------|-------------|-------|
| 1 | Security | attack surface, credentials, data flow |
| 2 | Sovereignty | open source, self-hosting, vendor lock-in |
| 3 | Simplicity | absorption (new primitives absorb existing), maintainability |
| 4 | Experience | dev/user happy path, friction count |
| 5 | Compatibility | stack fit, migration cost, downstream consumers |
| 6 | Scale | 10x volume, future-proofing, cost-per-month |

Simplicity (rank 3) may propose closed-source ONLY when substantial benefit + explicit sovereignty trade-off documented.

### life_domain (non-technical decisions)

| Perspective | Focus |
|-------------|-------|
| pragmatist | fastest path to result, cost/benefit |
| risk_analyst | worst case, reversibility |
| long_term_thinker | 2 / 5 / 10 year view |
| devils_advocate | why is the preferred option WRONG? |

### Other profiles (instantiate situationally)
- **project prioritization:** impact / effort / urgency / learning / risk
- **infrastructure / ops:** reliability / security / sovereignty / simplicity / cost
- **personal direction:** alignment / opportunity cost / reversibility / energy
- **buy / invest:** need / sovereignty / cost / quality / alternatives

## 10. Interactive council — phases 1-2-3

### Phase 1: Intake check
(1) Derivation chain — repeat intent anchoring; broken → STOP. (2) Problem vs symptom — name suspected real problem. (3) Null option — 1-2 sentences. Present candidates (2-4; frame-report candidates first). Close with: missing candidate? perspectives right? WAIT for user.

### Phase 2: Council rounds
Per round: pick 2-3 perspectives contributing most (not all every time). Each first-person, identifier prefixed, 2-4 sentences. Name conflicts immediately; default = rank wins; ask user if weighing differently. End with concrete question. WAIT for user.

Moderation: drift against higher-ranked → object visibly. Consensus forming → summarise + phase 3. User overrides perspective → accept + document. No convergence after 2 rounds → summarise open conflicts, ask user directly.

### Phase 3: Synthesis
(1) Recommendation (1-2 options). (2) What's sacrificed (which perspective loses + concrete consequence). (3) Open risks. (4) Demand decision ("Are we going with X?", not "looks good?"). Done only when user has chosen.

## 11. Risk carry-forward schema (council-side)

Mirrors `code_review_board/SKILL.md` §Risk carry-forward. Decision artifact YAML `remaining_positions:` per entry: `id`, `severity`, `option`, `argument_summary`, `rationale_for_carry_over`, `proposed_action` (`re_council` / `ADR` / `monitor` / `accept`).

## 12. ADR-trigger conditions

ADR REQUIRED on:
- Hard-to-reverse decision (data/schema/contract/identity)
- Decision spans ≥2 components or layers
- ≥1 HARD constraint (security, sovereignty per values.md) explicitly traded off
- Council mode = standard or full (light optional)

Via `documentation_and_adrs/SKILL.md`. Decision-file references ADR id.

## 13. Workflow_engine handshake

**Build-context council** (specify-phase substitute for spec_board): Buddy MUST trigger `python3 scripts/workflow_engine.py --start build --task <id>` in the SAME tool block as council spawn. Engine state SoT for cross-session recovery. This is Buddy-side discipline — `workflows/runbooks/build/workflow.yaml` board step has `alternative_skill_refs: skills/council/SKILL.md` as documentation-intent only (engine reads `skill_ref`).

**Solve-refine council** (opt-in via state-file marker): the `council-needed` guard at `scripts/workflow_engine.py` greps the solve state file for `council-required: true` (frontmatter or body). If present → guard exits 0, council step fires automatically. If absent → guard exits 1, refine step proceeds with user-dialog only. Buddy writes the marker when frame report's >1-path + hard-to-reverse criteria fire.

Default = skip (council is Buddy-judgmental per §1.0; engine does not auto-fire architectural decisions). See `framework/workflow-engine-cookbook.md` for engine shape.

## 14. Skip rationales (template)

Acceptable §1.0 skip phrases (write inline at decision point):
- `"Council not needed: single viable path (X), reversible (Y)."`
- `"Council not needed: cross-scope contradiction, current-scope decidable (producer/consumer/adjacent all aligned on X)."`
- `"Council not needed: HARD constraint already binds choice (sovereignty rules out cloud-only options)."`

Unacceptable: silent skip, "obvious", "no time".
