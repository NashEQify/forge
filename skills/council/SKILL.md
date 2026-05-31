---
name: council
description: >
  Structured architectural / strategic decision-making. Two modes:
  (a) Architectural — 3-6 council-member subagents in parallel,
  context-isolation, chief consolidates, Buddy decides.
  (b) Interactive — Buddy moderates a user dialog with perspectives.
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

Buddy checklist. Detail mechanics: `REFERENCE.md`.

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
- **≤2 yes** → no council. Document skip: *"Council nicht nötig: <rationale>"*. Decide directly.

**Override floor (forces standard or full regardless of count):** security / sovereignty hard constraint AND multi-component · new state-vocabulary or new public-API contract · new normative cross-spec rule · foundational pattern replacement.

**Anti-pattern (cross-scope vs current-scope):** if the question presents as "spec corpus has multiple representations of X" but current-scope path is internally consistent (producer + consumer + adjacent uses all aligned) and contradictions live in different scopes → **NO council**. Preserve current path, file normalisation task. Council on cross-scope when current is decidable wastes a cycle. Detail: REFERENCE.md.

### 1.1 Mode choice (after gate passes)

| Mode | Team |
|------|------|
| **light** | 3 members + council-chief. No adversary, no frame-check, no discourse. **Default on §1.0 pass.** |
| **standard** | 3 members + chief + **council-adversary** + pre-council frame check + post-council coherence check. Fires when ≥1 of §1.0 override-floor items, OR ≥2 of {hard-to-reverse, multi-component, security/sovereignty}. |
| **full** | 4-6 members + chief + adversary + frame-check + coherence-check + discourse on dissent. >2 dimensions OR foundational pattern OR ≥2 hard constraints. |
| **interactive** | Buddy moderates dialog (REFERENCE.md). User explicit ask only. |

Default = light (proportional release valve). Escalation is criterion-driven, not Buddy-uncertain.

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

Spec review → `spec_board`. Code diff → `code_review_board`. Pre-code plan → `impl_plan_review`. Technical architecture moderator → `solution-expert` (instantiates this skill, 6 fixed perspectives per `values.md`). Non-technical → this skill with situational perspectives (REFERENCE.md).
