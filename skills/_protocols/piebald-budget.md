# Protocol: Piebald-Budget Hard Gate

Prevents budget drift in skills, runbooks, personas, and assembled
prompts. Loaded by: spec_board, code_review_board,
sectional_deep_review, architecture_coherence_review. Applied by
the board review to every review target whose type has a budget.

> **Policy update.** SKILL.md budget loosened from ≤120
> to **≤400 lines** following empirical evidence that the earlier
> tight cap drove content into REFERENCE.md split-files that the
> framework's skill-loading mechanism never auto-loads (Buddy reads
> SKILL.md via the Skill tool; REFERENCE.md is a manual on-demand
> read that effectively never happens). REFERENCE.md pattern is
> **deprecated** — fold the content back into SKILL.md as touched.
> Modern LLM context windows handle 400-line skills trivially; the
> earlier 120-line cap was a piebald optimization for an older
> attention-budget that no longer constrains us at this scale.

## The problem this protocol still solves

Token bloat through accreting prose. Skills + workflows + personas
need to stay focused. Past hard-cap was 120 lines per SKILL.md;
loosened to 400 in light of (a) modern context windows + (b) the
REFERENCE.md split-file pattern empirically not delivering its
intended benefit.

Skill *count* inflation is the higher-leverage concern now, not
*size* — inflation guard sits in `skill-anatomy.md` §Inflation guard.

## Budget table (hard gate)

| Artifact type | Budget | Path pattern |
|---------------|--------|--------------|
| **Skill SKILL.md** (single-class v3, REFERENCE.md folded back) | ≤400 lines | `skills/*/SKILL.md` |
| **Skill SKILL.md** (legacy with REFERENCE.md split, transitional) | ≤180 lines while REFERENCE.md exists | `skills/*/SKILL.md` + paired `REFERENCE.md` |
| ~~Skill REFERENCE.md~~ | **deprecated, fold back to SKILL.md** | `skills/*/REFERENCE.md` |
| Workflow runbook | ≤200 lines | `workflows/runbooks/*/WORKFLOW.md` |
| ~~Runbook REFERENCE.md~~ | **deprecated, fold back to WORKFLOW.md** | `workflows/runbooks/*/REFERENCE.md` |
| Agent persona (standard) | ≤100 lines | `agents/*.md` |
| Agent persona (chief / moderator / consolidator) | ≤150 lines | `agents/board-chief.md`, `agents/code-chief.md`, `agents/council-chief.md`, `agents/solution-expert.md` |
| Skill protocol | ≤150 lines | `skills/_protocols/*.md` |
| Agent protocol | ≤80 lines | `agents/_protocols/*.md` |
| Assembled prompt (protocol + persona + dispatch) | ≤500 lines | runtime check on dispatch |

**Per-skill REFERENCE.md fold-back triage** (12 active files, 2444
LoC total; 2 done):

| Skill | REF lines | Status |
|---|---|---|
| council | 102 | **DONE** — folded into SKILL (206 LoC merged) |
| sectional_deep_review | 87 | **DONE** — folded into SKILL (259 LoC merged) |
| consistency_check | 636 | TODO — heaviest: triage forensic history; likely 80% drop, 20% inline |
| code_review_board | 313 | TODO — review-mode detail merges into SKILL §Process |
| testing | 282 | TODO — L0-L5 pyramid detail belongs in SKILL |
| spec_board | 220 | TODO — mode profiles + chief routing merge into SKILL |
| spec_authoring | 160 | TODO — phase detail merges |
| adversary_test_plan | 146 | TODO |
| task_creation | 139 | TODO |
| frame | 120 | TODO — 8-step process detail |
| bedrock_drill | 120 | TODO |
| convergence_loop | 119 | TODO |

Per-skill fold-back is **per-skill content judgment** (not mechanical
replace) and runs as a follow-up sweep or as each skill is next
touched. The transitional 180-line cap applies while paired
REFERENCE.md still exists.

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
permanent drift. Multiple fix passes (docs-rewrite, solve-framing,
others) overshot the original budget calibration. Without a hard
gate the drift repeats.
