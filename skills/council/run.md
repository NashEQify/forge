# Council — running the council

Step-loaded unit of `skills/council/SKILL.md`. Read it once the §1 mode is picked: before drafting the briefing and
dispatching members (light / standard / full), and before opening an interactive council. Section numbers are
skill-wide: §0–§1, §5–§8, §11 and §14 in `SKILL.md`, §2–§4 and §9–§10 in `run.md`, §12–§13 in `development.md`.

## 2. Pre-council frame check (standard / full)

**Trigger:** Buddy-drafted briefing without upstream frame report. (When `frame/SKILL.md` already produced a frame-report for this question, reference it — don't re-run.) Mode determines whether the trigger applies; light skips frame-check by mode.

Buddy drafts briefing → dispatches `plan-adversary` cold-start on the draft (criteria 1-6 per `_protocols/plan-review.md`; focus: does question pre-decide by shape? option-set complete? stakeholders missing?) → persists return verbatim at the declared execution-root frame-check path (§7; private temporary storage is sufficient) → distills concerns into FINAL briefing.

Members see FINAL briefing only. Council-chief reads BOTH at CHIEF-1.0.

## 3. Briefing format (cold-start clean — MANDATORY)

**MUST:** question (1 sentence) · intent_chain anchoring · context-file paths · null option (1-2 sentences) · perspectives + ranks · per-option reversibility cost-band (S/M/L/XL effort × named consumers impacted) · artifact destinations · inline return contract (`_protocols/dispatch-template.md` section Output transport).

**MUST NOT:** Buddy's proposal · pre-classified conflicts · severity tags · lean hints. Brief-contagion empirically demonstrated.

> **`intent_chain anchoring` is REQUIRED and load-bearing — not droppable.** Its
> one-line `vision` (from supplied intent, or the active `intent.md` for a repository caller) is the
> **standing** intent grounding a cold member receives: a standardized alignment
> derivation, NOT decision-curated content. It is the sanctioned exception to the
> "cold-analysis gets nothing" anti-anchoring rule — the author-separability line: a standing
> anchor is not the proposer's per-decision framing, a Buddy-selected fact/premise/hint
> is (those stay in MUST-NOT). A briefing missing its `intent_chain` block is
> **incomplete**, not merely terse.

## 4. Buddy checklist (dispatch)

1. §1.0 gate → mode pick.
2. §2 pre-council frame check (standard / full).
3. Write briefing per §3 (clean). Path: §7.
4. Spawn N members + adversary in ONE tool block, parallel, `run_in_background: true` (the call per `skills/_protocols/role-dispatch.md` + perspective + briefing path + output path + file-output OVERRIDE).
5. Wait, then spawn `council-chief` (called per `skills/_protocols/role-dispatch.md`) with all member outputs + adversary + (when present) frame-check artifact.
6. Read chief consolidated → recommended verdict + tracking-table verification.
7. (Full + dissent) Discourse one round per `_protocols/discourse.md`, except the user-decided case of `SKILL.md` §6 FAIL handling.
8. Buddy checks pivotal claims against sources and the recommendation against supplied intent/constraints (§1.1), then owns the decision. Carry unresolved risks into the result. An explicitly selected development caller adds its own coherence and ADR obligations (§12).

## 9. Perspective profiles

### architecture (default for ARCH-XXX decisions)

Ranks from the user's constraint hierarchy (values and priorities in `<user_repo>/context/user/profile.md`,
`framework/user-scope.md`); without one, this default order applies:

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
