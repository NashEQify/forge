# Spec Board — Reference

Detail mechanics. Buddy loads SKILL.md for dispatch. This file is
reference material for special cases, invariants, and paths.

## Plan + review (§0) — detail

Mechanic, templates, triggers, adversary prompt:
`_protocols/plan-review.md` (SoT). Spec_board-specific
application: §0 fires only when board dispatch happens **without**
a previous frame (e.g. re-review of an existing spec, ad-hoc
scoped pre-check). When a frame report is already in place,
plan + review was executed there — `spec_board` §0 references
the frame report and does not re-execute (avoiding duplicate
work; the bind rule still applies).

**Output anchor:** plan + review goes into the dispatch report or
the task state file, not into the agents' review files.

## 4 NON-NEGOTIABLEs

1. **Convergence threshold:** 0C + 0H. HIGHs are never accepted
   risk.
2. **Fix scope:** synthesize fixes ALL findings (C+H+M+L), not
   just HIGHs.
3. **Context isolation:** pass 2+ reviewers receive NO previous
   findings.
4. **Evidence grounding:** a finding without a concrete spec
   pointer → the chief removes it.

## Content preservation on fixes

→ `skills/_protocols/content-preservation.md` (SoT). Also:
`docs/specs/interface-contract.md` S-001, CLAUDE.md §3b.

## Finding IDs

- Individual: `F-{role}-{NNN}` (C=Chief, A=Adversary, A2=Adv2,
  A3=Adv3, I=Implementer, X=Impact, S=Consumer).
- Consolidated (chief): `C-{NNN}` with mapping to the original
  IDs.

## Extended output paths

| Artifact | Path |
|----------|------|
| Review files | `docs/reviews/board/{spec-name}-{role}-pass{N}.md` |
| Synthesize files | `docs/reviews/board/{spec-name}-synthesize-pass{N}.md` |
| Consolidated | `docs/reviews/board/{spec-name}-consolidated-pass{N}.md` |
| Final arbiter | `docs/reviews/board/{spec-name}-final.md` |
| Board artifact | `docs/reviews/board/{spec-name}-board-review.yaml` |
| Discourse files | `docs/reviews/board/{spec-name}-discourse-{role}-pass{N}.md` |
| Discourse results | `docs/reviews/board/{spec-name}-discourse-results-pass{N}.md` |

## Model override

v6.0: standard = all-Opus. Deep pass 1: Adv-3 + Consumer = Sonnet.
Deep pass 2+: Opus only.

## Extra dimensions (board-specific)

- **Chief:** DR scorecard on foundation specs. E2E scenario
  validation when the spec contains E2E scenarios.
- **Impact:** cross-spec E2E (trace data across spec
  boundaries). Infrastructure impact.

## SoT

Full workflow mechanics:
`workflows/templates/spec-board.yaml` (v6.0).

## Delta-Verify (§3a details)

**SoT relationship:** §3a in SKILL.md is **normative** (rule,
trigger, team, acceptance). This section is **additive detail
mechanics** for the implementation — no contradiction with
SKILL.md, no own normative rules. On a conflict, SKILL.md wins.

### Normative-line definition (mechanically checkable)

"Normative" = a line that defines a **rule**, a **trigger
criterion**, a **required format**, or an **acceptance
condition**. Count:

- Statements with MUST / MUSS / SHALL / MAY NOT / should / not /
  all / only / at least.
- New bullet entries in rule lists.
- Required output formats (incl. code fences with structure).
- Trigger criteria with thresholds.

**Don't count:** comments, whitespace, header levels, examples
without normative content, cross-references, boundary text
without prohibitions.

### Scope "direct neighbour sections"

Section level (not file level). A section is a neighbour when:
(a) it lives in the same file and shares a sub-heading level OR
(b) it is referenced explicitly inside the fixed area OR (c) it
contains a cross-reference into the fixed area.

### Meta-critical trigger — sharpening

"Gate composition" = a rule for ordering / dominance / replace
between multiple gates at the same slot. "Severity definition"
= mapping rule between severity names or acceptance thresholds.
"Enforcement logic" = rule for how / where / who triggers the
gate. If a fix touches such places, Delta-Verify is required
**regardless of line count** — even on a 1-line change, because
gate composition has cascading effects.

### Drill + trace enforcement without a chief

Buddy (the dispatcher) checks four things after the return of
the 2 Delta-Verify reviewers:

1. **Drill existence:** `grep -l
   "## Reviewer-First-Principles-Drill"` to confirm both review
   files contain the section.
2. **Drill bind rule:** `grep -c` to confirm at least one of
   the keywords (`Annahme | Gegenfrage | 1st-Principle`) appears
   outside the drill section — proxy for finding bind. Zero
   count = bind missing.
3. **Trace existence:** `grep -l
   "## Reviewer-Reasoning-Trace"` to confirm both review files
   contain the section.
4. **Trace bind rule:** `grep -c` to confirm at least one of
   the keywords (`INTENT | PLAN | SIMULATE | IMPACT`) appears
   in findings. Zero count = bind missing.

Drill / trace OR bind missing on ≥1 reviewer: re-dispatch the
same reviewer context-isolated with a hint at the missing
section / bind. No full re-review. Loop bound: max 1
re-dispatch per reviewer; then ESCALATE.

## Risk carry-forward (full schema + acceptance scenarios)

When the board terminates without a clean 0C+0H PASS but the user
accepts the result anyway (cherry-pick override, convergence-valve
hit at safety limit, outer-loop bound reached), the consolidated
verdict file MUST carry the unfixed findings forward in a top-level
YAML block:

```yaml
remaining_findings:
  - id: F-H-014                                # finding ID
    severity: high                             # critical | high | medium | low
    locator: docs/specs/foo.md:§3.4 lines 88-104
    title: "Pipeline phase 4 lacks fail-fast"
    rationale_for_carry_over: >
      User-override cherry-pick — only blockers fixed in this pass; H/M
      findings deferred per explicit decision.
    proposed_action: >
      Add fail-fast condition per pattern in §3.2; ~20 LOC spec edit, no
      cross-spec impact expected.
  - id: F-M-006
    severity: medium
    locator: docs/specs/foo.md:§5.1
    ...
```

The workflow steps `risk-followup-routing` (build / review / fix
workflow.yaml) read this block and file ONE follow-up task per
workflow run via `skills/task_creation/SKILL.md`. Empty/absent
block: workflow step skips with rationale "no remaining findings".

**Acceptance scenarios that require the block:**
- User says "cherry-pick: fix only blockers, defer the rest" — verdict
  carries deferred findings.
- Convergence valve (5 passes) hits with open findings the user accepts.
- Outer-loop bound reached (`convergence_loop` REFERENCE.md) and user
  accepts the residual.
- ESCALATE returned to user and user decides "ship anyway".

**Why mechanical:** historically these residuals lived in verdict
prose or informal session notes and disappeared between sessions.
Structured block + workflow-step pair turns carry-forward into
engine-tracked work instead of bookkeeping.

## Engine context (§4 step 5 detail)

When the spec references the workflow engine (engine steps, YAML
definitions, completion types, guards), agents receive as required
context:

- `$FRAMEWORK_DIR/scripts/workflow_engine.py`
- `$FRAMEWORK_DIR/scripts/lib/yaml_loader.py`
- Existing `workflow.yaml` definitions in `workflows/runbooks/*/`

Without this context: findings on engine limitations are unreliable
(reviewers extrapolate from spec prose instead of grounding against
the actual engine API).

## Extended anti-patterns (rationale prose)

- **NOT** pass findings on without chief consolidation. INSTEAD
  check chief signal + tracking table. **Because:** silent loss is
  the historic failure mode (consolidation-preservation discipline).
- **NOT** close standard without discourse when findings diverge.
  INSTEAD trigger discourse. **Because:** reviewers see different
  problems; convergence has to be earned, not assumed.
- **NOT** start a spec fix as a new full pass. INSTEAD scoped
  pre-check + delta review. **Because:** pass inflation wastes tokens
  on unaffected scope.
- **NOT** dispatch agents without context isolation. INSTEAD every
  agent gets ONLY the spec. **Because:** anchoring bias from prior
  findings reduces independent signal.
- **NOT** run §1.1's 4 checks before answering §1.0's proportionality
  gate. INSTEAD §1.0 first; 3-of-4 yes → standard regardless of
  cross-layer / interface triggers. **Because:** any YES → Deep is
  risky-by-default; bookkeeping edits (amendment-log row, Step-alt
  example, clarification) systematically fire cross-layer / interface
  checks without justifying a Deep board (L-033 failure mode).
  Security and full-path remain hard overrides.
- **NOT** skip the §Module-Decomposition OR §Test-Strategy pre-gate
  check on a NEW L1+ spec by assuming legacy. INSTEAD verify
  creation-date or section-history before silent-skipping. **Because:**
  the no-retrofit rule applies to specs that PRE-DATE these rules,
  not to new specs that omitted the sections. Net-new L1+ spec
  without either section = FAIL; only legacy absence is silent-skip.
