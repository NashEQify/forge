# Council — running the council

Step-loaded unit of `skills/council/SKILL.md`. Read it once the §1 mode is picked: before drafting the briefing and
dispatching members (light / standard / full), and before opening an interactive council. Section numbers are
skill-wide: §0–§1, §5–§8, §11 and §14 in `SKILL.md`, §2–§4 and §9–§10 in `run.md`, §12–§13 in `development.md`.

## 2. Pre-council frame check (standard / full)

**Trigger:** Buddy-drafted briefing without upstream frame report. (When `frame/SKILL.md` already produced a frame-report for this question, reference it — don't re-run.) Mode determines whether the trigger applies; light skips frame-check by mode.

Buddy drafts the briefing → dispatches `plan-adversary` cold-start on the draft and its intent sources (criteria 1–6 per
`_protocols/plan-review.md`) → persists the return verbatim at the declared execution-root frame-check path (§7;
private temporary storage is sufficient) → distills concerns into the FINAL briefing.

Ask in that dispatch: Does the question's shape pre-decide the outcome? Are options or stakeholders missing?
Does an applicable intent sentence missing from the anchor decide between options, including a project-wide goal
or standing constraint outside the local framing? Cite the sentence and show which options it distinguishes.

Members see FINAL briefing only. Council-chief reads BOTH at CHIEF-1.0.

## 3. Briefing format (cold-start clean — MANDATORY)

**MUST:** question (1 sentence) · intent_chain anchoring and derivation · context sources · null option (1–2 sentences) · perspectives + ranks · per-option effort (S/M/L/XL), reversal cost and consumer impact · artifact destinations · inline return contract (`_protocols/dispatch-template.md` section Output transport).

**MUST NOT:** Buddy's proposal · pre-classified conflicts · severity tags · lean hints. Brief-contagion empirically demonstrated.

Fill the `intent_chain` block before relying on the question:

1. **Anchor rows** — Give each applicable overarching vision or goal, standing constraint and local objective its own
   row: `ID | intent sentence | named source and locator | user confirmation (confirmed / unconfirmed / unknown)`.
   Use the active project's intent and applicable standing sources for repository work. For standalone work, use the
   supplied goals and constraints, citing the message or supplied material. Use sourced intent for the anchor; a row
   whose only source is your own record is an author derivation, not a row.
   Put any author inference needed to explain the framing on a separate line labeled **author derivation — unconfirmed**.
2. **Question derivation** — Write `This question advances [anchor IDs] by [how resolving the local objective serves
   the overarching goal within the standing constraints].` State any conflict among these sources or with the proposed
   framing before relying on it. Resolve it from the supplied authority or keep the question conditional and name the
   unresolved point. An author derivation carries no authority to settle the conflict. Check that no intent sentence
   that decides between the options is missing from the anchor (§2's question; in light mode the only such check).

**Briefing examples to check while drafting**, before sending to the frame checker or, in light mode, the members:

- State the actual null state in 1–2 neutral sentences. Cite the commit for repository state and the supplied
  snapshot or observation for standalone state.
- Ranking perspectives is itself a lean. Cite any user-confirmed priorities. Label fallback ranks as framework
  defaults (§9) and keep them outside the intent anchor.
- Give reversal cost separately from implementation effort. Use one named consumer list for all options and show each
  option's impact on each consumer, including none.
- Present “measure first” and “change nothing” as options. For measurement, name what result would change the choice.

## 4. Buddy checklist (dispatch)

1. §1.0 gate → mode pick.
2. §2 pre-council frame check (standard / full).
3. Write briefing per §3 (clean). Path: §7.
4. Spawn N members + adversary in ONE tool block, parallel, `run_in_background: true` (the call per `skills/_protocols/role-dispatch.md` + perspective + briefing path + output path + file-output OVERRIDE).
5. Wait, then spawn `council-chief` (called per `skills/_protocols/role-dispatch.md`) with all member outputs, the final briefing's intent anchor for grounding deferrals, and the adversary and frame-check artifacts when present (owner: agents/council-chief.md §Output structure).
6. Read chief consolidated → recommended verdict + tracking-table verification.
7. (Full + dissent) Discourse one round per `_protocols/discourse.md`, except the user-decided case of `SKILL.md` §6 FAIL handling.
8. Verify pivotal claims at their sources (§1.1). Before presenting the recommendation or commissioning work,
   cite the applicable project goal and standing constraints (or supplied intent for standalone work) and the current
   local objective in the existing decision or inline result. Explain how the choice serves both. When recommending
   which work goes first or is deferred, record for each option being compared:
   - The outcome it delivers and how that outcome relates to the current objective. Identify a direct contribution,
     a necessary prerequisite, or work serving a separate objective. Ground a prerequisite in the result needed
     and the work that cannot proceed without it.
   - The consequence for the current objective of spending the next work slot on that option.
   - What the existing agreement authorizes and whose decision a change to that order requires.
   Use the comparison to explain the proposed order. Hold any choice that depends on a missing or conflicting source
   until its authority resolves it. Obtain any required order approval before commissioning work (owner:
   framework/invariants.md §Intent-driven and Invariant 2). Buddy owns the decision and carries unresolved risks.
   A selected development caller adds its coherence and ADR obligations (§12).

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

Moderation: drift against higher-ranked → object visibly. Consensus forming → summarise + phase 3. Record a user override of perspective rank. Apply the synthesis intent check before relying on it to change the outcome. Apply §4 step 8 before presenting
an ordering recommendation or asking the user to choose an order, including at the two-round exit. No convergence after 2 rounds → summarise open conflicts, ask user directly.

### Phase 3: Synthesis
(1) Recommendation (1-2 options), applying §4 step 8 before presenting it. (2) What's sacrificed (which perspective loses + concrete consequence). (3) Open risks. (4) Demand decision ("Are we going with X?", not "looks good?"). Done only when user has chosen.
