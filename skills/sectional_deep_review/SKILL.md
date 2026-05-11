---
name: sectional-deep-review
description: >
  Deep review for large foundation specs (>1000 lines, many
  subsections). Splits the spec into pattern groups, reviews each
  with cross-reference context, fixes per group, then runs a
  full-spec review for composition and gaps.
status: active
verification_tier: 1
evidence_layout: per_finding
invocation:
  primary: workflow-step
  secondary: [user-facing, sub-skill]
disable-model-invocation: false
uses: [spec_board, _protocols/context-isolation, _protocols/content-preservation, _protocols/dispatch-template, _protocols/evidence-pointer-schema]
---

# Skill: sectional-deep-review

Buddy checklist for the deep review of large foundation specs.
Detail mechanics: `REFERENCE.md`. Board runs: per
`spec_board/SKILL.md`.

## When to call

- Spec > 1000 lines with > 5 subsections.
- Foundation character (consumed by many others).
- Never reviewed OR significantly changed.
- Cross-spec interfaces as the primary risk.
- A single board pass would spread reviewers thin.

## Sequence

```
PHASE 0 — PREP (structure → cross-ref → groups → order → briefs)
PHASE 1 — SECTIONAL REVIEWS (N groups, fixed individually)
PHASE 2 — FULL REVIEW (Deep Board + discourse on the complete post-fix spec)
PHASE 3 — CONVERGENCE + DONE
```

## Phase 0 — PREP (Buddy)

1. **Spec structure:** read it completely. Inventory subsections
   (number, title, lines). Identify internal dependencies.
2. **Cross-reference map:** per subsection: consumers (SPEC-MAP),
   neighbour refs (grep), code impl (`src/`), consumer
   assumptions. Targeted first, then complete.
3. **Pattern groups:** 3-5 groups by functional cohesion, shared
   consumers, internal coupling. 3-8 sections each, ~300-700
   lines. Max 800 per group. Per group: sections + core risk +
   board mode + reference brief.
4. **Order:** dependency order. Critical groups first. Max 1
   Deep.
5. **Reference briefs:** per group: neighbour passages, code
   files, consumer expectations.

## Phase 1 — SECTIONAL REVIEWS

Each group = its own board run. Fixed individually.

### Per group:

1. Agents receive: relevant sections + reference brief +
   dispatch template (GAP-03).
2. Board mode:
   - LOAD-BEARING / ARCH-marked → Deep.
   - \>500 lines → Deep.
   - Known cross-spec risks → Deep.
   - Otherwise → Standard (escalates on ≥1C / ≥3H).
3. Board run per `spec_board/SKILL.md` (team selection,
   assembly, dispatch).
4. Chief consolidates. Deep: + discourse → Chief-2.
5. **SAVE (NON-NEGOTIABLE).**
6. NEEDS-WORK → fix (MCA, only sections of this group) →
   `spec_version` bump → SAVE.

## Phase 2 — FULL REVIEW

After all sectional fixes. Complete updated spec.

1. Reference: full neighbour specs + code interfaces + consumer
   specs.
2. Focus: cross-pattern composition, gaps between groups,
   systemic issues.
3. Context-isolated — agents do NOT know the sectional findings.
4. Foundation flag → chief gets the DR scorecard.
5. Board run per `spec_board/SKILL.md` (Deep + discourse).
6. **SAVE → fix on NEEDS-WORK.**

## Phase 3 — CONVERGENCE

Standard Deep Convergence (`spec_board/SKILL.md`):
Pass 2+: 4 agents (Adv + Adv2 + Impl + Impact),
context-isolated.
Final: 2 agents (Adv + Impl). 0C + 0H → `board_result = pass`.

## Post-pass (NON-NEGOTIABLE)

- SAVE after EVERY group and after the full review.
- Sectional fixes committed individually.
- Bump `spec_version` on every fix.
- Content preservation: → `_protocols/content-preservation.md`.

## Contract

### INPUT
- **Required:** spec > 1000 lines with > 5 subsections.
- **Required:** foundation character (consumed by many others).
- **Required:** SPEC-MAP read (cross-reference map derivable).
- **Optional:** previous board results — for delta judgment.
- **Context:** `spec_board/SKILL.md` (board runs follow its
  mechanics), `_protocols/content-preservation.md`,
  `dispatch-template.md`.

### OUTPUT
**DELIVERS:**
- Sectional findings: per pattern group: board verdict +
  findings + fixes (committed individually).
- Full-spec verdict: Deep Board + discourse on the entire
  post-fix spec.
- Convergence result: 0C+0H after every pass (Deep
  Convergence).
- SAVE after every group: persisted review files.

**DOES NOT DELIVER:**
- Not for small specs (<300 lines) — use `spec_board` directly
  for those.
- No cross-spec check — use `architecture_coherence_review`.
- No standalone fixes — fixes by MCA, under Buddy's
  coordination.

**ENABLES:**
- Review: deep review for foundation specs that are too large
  for a single board pass.
- Build specify: bring a foundation spec to board-ready level.
- Convergence: structured progress across groups + a full-spec
  pass.

### DONE
- All pattern groups individually reviewed and fixed.
- Full-spec Deep Board + discourse on the entire post-fix spec
  executed.
- Convergence: 0C+0H after Deep Convergence (Pass 2+: 4→2
  agents).
- SAVE after every group and after the full review.
- `spec_version` bumped on every fix.

### FAIL
- **Retry:** NEEDS-WORK → fix within the group → `spec_version`
  bump → next pass (convergence_loop).
- **Escalate:** Deep Convergence max 3 passes without 0C+0H →
  escalate to the user.
- **Abort:** not foreseen — escalate to the user instead of
  aborting.

## Boundary

- For small specs (<300 lines) → `spec_board` Standard
  directly, not sectional.
- No code review → `code_review_board`.
- No cross-spec review → `architecture_coherence_review`.

## Anti-patterns

- **NOT** split sections arbitrarily. INSTEAD by semantic
  boundaries (subsystem, phase, component). Because: arbitrary
  splits tear context — reviewers lose the thread.
- **NOT** all groups in one pass. INSTEAD group by group, SAVE
  in between. Because: 300+ lines per group saturates
  attention; multiple groups in a row makes it worse.
- **NOT** ignore findings of one group before fixing the next
  group. INSTEAD fix within the group, bump `spec_version`,
  then the next group. Because: cascading findings + content
  preservation.
- **NOT** final review without a complete tracking table of
  all sub-group findings. INSTEAD the
  consolidation-preservation cascade. Because: silent loss
  threatens at sectional level too.
