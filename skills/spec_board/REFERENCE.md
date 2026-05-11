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
