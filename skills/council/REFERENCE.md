# Council — REFERENCE

Detail mechanics. SKILL.md is the Buddy checklist.

## Mode profiles (aligned with `workflows/templates/council.yaml`)

| Mode | Members | Adversary | Chief | Frame-check | Coherence-check (Buddy-side) | Discourse | ADR |
|------|---------|-----------|-------|-------------|------------------------------|-----------|-----|
| light (default) | 3 | — | yes (all council modes — Inv 1) | — | required | — | optional |
| standard | 3 | yes | yes | yes (`plan-adversary`) | required | — | yes |
| full | 4-6 | yes | yes | yes | required | on dissent | yes |
| interactive | dialog-perspectives | conceptual | — | — | required | per-round | optional |

**Chief is required for all council modes** per Inv 1 — Buddy never synthesizes member outputs directly. Light is light by virtue of no-adversary + no-frame-check + no-discourse, NOT by skipping chief.

**Coherence-check** is a Buddy-side rule (`agents/buddy/operational.md` §Architecture-Comprehension B), applied unconditionally on every chief return. Not a duplicated council step.

Member model config (yaml `member_config`): minimum 2× Opus + 1× Sonnet per non-light mode for cognitive diversity. Light: 2× Opus + 1× Sonnet or 3× Opus.

## Perspective profiles

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

## Cross-scope vs current-scope (§1.0 anti-pattern detail)

If question presents as "spec corpus has multiple representations of X":

1. Is CURRENT-SCOPE path internally consistent? Check producer + consumer + adjacent uses. All same representation → path IS decidable.
2. Contradictions in DIFFERENT scopes (legacy / future / cross-cutting infra)?
3. Way to preserve current path + file normalisation as follow-up?

1+2+3 = yes: **NO council**. Preserve current path; file normalisation task. Council on broader contradiction wastes a cycle + introduces re-framing risk (Council recommendation adopted autonomously becomes a frame user has to unwind).

## Interactive council — phases 1-2-3

### Phase 1: Intake check
(1) Derivation chain — repeat intent anchoring; broken → STOP. (2) Problem vs symptom — name suspected real problem. (3) Null option — 1-2 sentences. Present candidates (2-4; frame-report candidates first). Close with: missing candidate? perspectives right? WAIT for user.

### Phase 2: Council rounds
Per round: pick 2-3 perspectives contributing most (not all every time). Each first-person, identifier prefixed, 2-4 sentences. Name conflicts immediately; default = rank wins; ask user if weighing differently. End with concrete question. WAIT for user.

Moderation: drift against higher-ranked → object visibly. Consensus forming → summarise + phase 3. User overrides perspective → accept + document. No convergence after 2 rounds → summarise open conflicts, ask user directly.

### Phase 3: Synthesis
(1) Recommendation (1-2 options). (2) What's sacrificed (which perspective loses + concrete consequence). (3) Open risks. (4) Demand decision ("Are we going with X?", not "looks good?"). Done only when user has chosen.

## Risk carry-forward schema (council-side)

Mirrors `code_review_board/SKILL.md` §Risk carry-forward. Decision artifact YAML `remaining_positions:` per entry: `id`, `severity`, `option`, `argument_summary`, `rationale_for_carry_over`, `proposed_action` (`re_council` / `ADR` / `monitor` / `accept`).

## ADR-trigger conditions

ADR REQUIRED on:
- Hard-to-reverse decision (data/schema/contract/identity)
- Decision spans ≥2 components or layers
- ≥1 HARD constraint (security, sovereignty per values.md) explicitly traded off
- Council mode = standard or full (light optional)

Via `documentation_and_adrs/SKILL.md`. Decision-file references ADR id.

## Workflow_engine handshake

**Build-context council (specify-phase substitute for spec_board):** Buddy MUST trigger `python3 scripts/workflow_engine.py --start build --task <id>` in the SAME tool block as council spawn. Engine state SoT for cross-session recovery. This is Buddy-side discipline — `workflows/runbooks/build/workflow.yaml` board step has `alternative_skill_refs: skills/council/SKILL.md` as documentation-intent only (engine reads `skill_ref`).

**Solve-refine council (opt-in via state-file marker):** the `council-needed` guard at `scripts/workflow_engine.py` greps the solve state file for `council-required: true` (frontmatter or body). If present → guard exits 0, council step fires automatically. If absent → guard exits 1, refine step proceeds with user-dialog only. Buddy writes the marker when frame report's >1-path + hard-to-reverse criteria fire.

Default = skip (council is Buddy-judgmental per §1.0; engine does not auto-fire architectural decisions). See `framework/workflow-engine-cookbook.md` for engine shape.

## Skip rationales (template)

Acceptable §1.0 skip phrases (write inline at decision point):
- `"Council nicht nötig: single viable path (X), reversible (Y)."`
- `"Council nicht nötig: cross-scope contradiction, current-scope decidable (producer/consumer/adjacent all aligned on X)."`
- `"Council nicht nötig: HARD constraint already binds choice (sovereignty rules out cloud-only options)."`

Unacceptable: silent skip, "obvious", "no time".
