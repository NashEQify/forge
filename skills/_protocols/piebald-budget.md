# Protocol: Piebald-Budget Hard Gate

Prevents budget drift in skills, runbooks, personas, and assembled
prompts. Loaded by: spec_board, code_review_board,
sectional_deep_review, architecture_coherence_review. Applied by
the board review to every review target whose type has a budget.

## The problem this protocol solves

During fix passes, skills and runbooks grow past the Piebald budget
(Task 273: Buddy-facing ≤100 lines, agent-facing ≤200 lines
assembled, runbook ≤150 lines, persona ≤70 lines). The
rationalization "substance justifies budget, split later if
critical" causes permanent drift, because later splits do not get
re-triggered.

Demonstrated on solve-framing fix pass (session 98): `frame/SKILL.md`
177 lines (budget 100), `solve/WORKFLOW.md` 237 lines (budget 150).
User feedback: that's not reliable enough.

## Budget table (hard gate)

**Single-class skill model:** the **unified budget ≤120 lines**
applies to **`skills/*/SKILL.md`**. Large skills that were originally
authored as workflows may sit between 120–180 lines; new skills
must come in under 120.

| Artifact type | Budget | Path pattern |
|---------------|--------|--------------|
| **Skill SKILL.md (single-class v2, no `type:`)** | ≤120 lines | `skills/*/SKILL.md` with new schema (`invocation`, no `type:`) |
| **Skill SKILL.md (workflow type, legacy)** | ≤180 lines | `skills/*/SKILL.md` with **`type: workflow`** while still set |
| **Skill SKILL.md (capability type, legacy)** | ≤120 lines | `skills/*/SKILL.md` with **`type: capability`** |
| **Skill SKILL.md (protocol type, legacy)** | ≤100 lines | `skills/*/SKILL.md` with **`type: protocol`** |
| **Skill SKILL.md (utility type, legacy)** | ≤100 lines | `skills/*/SKILL.md` with **`type: utility`** |
| Skill REFERENCE.md (detail mechanics) | ≤120 lines | `skills/*/REFERENCE.md` |
| Workflow runbook | ≤150 lines | `workflows/runbooks/*/WORKFLOW.md` |
| Runbook REFERENCE.md | ≤120 lines | `workflows/runbooks/*/REFERENCE.md` |
| Agent persona (standard) | ≤70 lines | `agents/*.md` |
| Agent persona (special: chief, consolidation roles, moderator roles) | ≤120 lines | `agents/board-chief.md`, `agents/code-chief.md`, `agents/board-ux-heuristic.md`, `agents/solution-expert.md` |
| Skill protocol | ≤100 lines | `skills/_protocols/*.md` |
| Agent protocol | ≤60 lines | `agents/_protocols/*.md` |
| Assembled prompt (protocol + persona + dispatch) | ≤200 lines | runtime check on dispatch |

**Differentiation by skill type (calibrated 2026-04-05):**
- **Single-class v2** (`invocation`, no `type:`): **120 lines** —
  target state Task 366.
- **Workflow** (legacy `type: workflow`): 180 lines. Scoping needs
  room for 5+ phases.
- **Capability** (legacy `type: capability`): 120 lines.
  `frame` 96/120 (hardened in session 99).
- **Protocol** (legacy `type: protocol`): 100 lines. Has to stay
  tight or it loses its rule character.
- **Utility** (legacy `type: utility`): 100 lines. Low-discretion.

**Moderator special case:** `agents/solution-expert.md` is the
moderator of a 6-perspective Architecture Council mechanic with
intake check + research check — structurally not splittable
without losing moderator context. Special-case list budget
≤120 lines, analogous to chief personas.

Rationale: Piebald benchmark (CC's own prompts 200-600 tokens =
~50-150 lines). Attention degrades above those sizes.

## Gate rule

**Budget is a HARD GATE, not a soft target.**

On board review of an artifact whose type appears in the table:

1. The chief (or a named agent) measures the line count of the
   review target.
2. If line count > budget: automatic HIGH finding.
3. Finding format:
   ```
   ### F-C-BUDGET: Piebald budget exceeded
   - severity: high
   - scope: local
   - primitive: P2 (consistency)
   - evidence: `<path>` has <N> lines, budget is ≤<M>.
   - description: budget is a hard gate. The "substance justifies
     it" rationalization is not allowed — attention degradation is
     empirically confirmed.
   - suggested_fix: (a) split into SKILL.md + REFERENCE.md (move
     detail mechanics out), OR (b) trim content (shorten examples,
     remove redundancy), OR (c) document an exception with user
     approval in the persona / SKILL (only for special cases with
     unique content that cannot be split).
   ```
4. The board CANNOT signal PASS while this finding is open.
5. Acceptable resolutions:
   - **Fix:** split or trim the artifact below budget.
   - **Exception:** explicitly documented in the artifact
     ("Piebald exception: <reason>") with review-board approval.
     Only for special cases like `board-chief.md` where the
     consolidation logic cannot be split.

## Pre-write self-check (for the author)

Before committing an artifact whose type is in the table:
1. Run `wc -l <path>`.
2. Compare against the budget.
3. If over budget: take the split decision BEFORE the commit, not
   "later".

That is the author-side check. The board review is the
enforcement-side check. Both are needed: the author check catches
most violations, the board check catches the rest.

## Relation to convergence_loop

`convergence_loop` MUST signal PASS only when the Piebald-budget
finding is closed (either fixed or explicit exception approved).
Automatic NEEDS-WORK on an open budget finding, until resolved.

## Why a hard gate?

Soft target + "split later" rationalization empirically leads to
permanent drift. Task 273 defined budgets; the docs-rewrite fix
pass exceeded them; the solve-framing fix pass did too. Three data
points = pattern. Without a hard gate the drift repeats.
