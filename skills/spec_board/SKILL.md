---
name: spec-board
description: >
  Multi-perspective spec quality review. Checks whether an
  existing spec is rebuild-ready: can an implementer rebuild it
  1:1 from the spec alone? 5 dimensions: completeness,
  consistency, implementability, interface contracts,
  dependencies. NOT for spec authoring (new specs) and NOT for
  retroactive code sync — those are spec_authoring and
  retroactive_spec_update. The board is the quality check AFTER
  writing.
status: active
verification_tier: 1
evidence_layout: per_finding
invocation:
  primary: workflow-step
  secondary: [user-facing, sub-skill]
disable-model-invocation: false
modes: [standard, deep, ux]
uses: [_protocols/plan-review, _protocols/discourse, _protocols/context-isolation, _protocols/content-preservation, _protocols/dispatch-template, _protocols/consolidation-preservation, _protocols/piebald-budget, _protocols/skill-guardrails, _protocols/analysis-mode-gate, convergence_loop, _protocols/evidence-pointer-schema]
---

# Skill: spec-board

Buddy checklist for board dispatch. Detail mechanics:
`REFERENCE.md`. Agent protocols:
`agents/_protocols/reviewer-base.md` +
`spec-reviewer-protocol.md`.

## 0. Plan + review (required without a frame)

On a direct board dispatch without a previous `frame`: plan block
(scope / tool / alternatives) + self-review + (non-trivial)
dispatch to `plan-adversary`. With an existing frame report:
reference instead of re-running. Bind rule: the dispatch
references the plan; deviation = rationale. Templates + triggers:
`_protocols/plan-review.md`. spec_board specifics:
`REFERENCE.md` §Plan+Review.

## Process — common

1. Decide on scope + depth (incl. foundation flag).
2. Assemble a role-based team.
3. Dispatch context-isolated reviews and consolidate.
4. Close NEEDS-WORK via fix / loop until 0C+0H.
5. Post-pass checks + task / commit / deploy cleanly closed.

## Process — mode standard

## 1. Depth mode

- **Scoped pre-check:** `board_result pass` AND change ≤3
  sections → standard (3 agents, no chief discovery). Otherwise
  → step 1.
- **Step 1 — 4 checks (≥1 YES → Deep):** cross-layer (consumers
  in another layer), interface (API / Pydantic / schema), full
  path (`dev_path: full`), security (auth / consent / crypto).
- All NO → standard. Standard escalates to Deep on ≥1C or ≥3H.

## 2. Team composition

- **Standard:** chief + adversary + implementer + impact +
  **architect-roots (CONDITIONAL on §2a trigger)**.
- **Deep pass 1:** all 7 (+ Adv-2, Adv-3 Sonnet, Consumer
  Sonnet) + **architect-roots (ALWAYS in deep pass 1)**.
- **Deep pass 2+:** 4 (Adv + Adv2 + Impl + Impact). Architect-
  roots NOT in pass 2+ (analysis-mode shifted to delta).
- **Deep final:** 2 (Adv + Impl).

Specialists by content: schema / API → code-api-contract,
readability → board-consumer, first principles →
board-adversary-2.

### 2a. Architect-roots trigger

Include `board-architect-roots` when **any** of:

- the spec has ≥ 6 locked decisions (`LD-N:` entries),
- the spec touches a state machine (state / transition / init /
  degraded / phase as a domain concept),
- the diff replaces a previously-flagged structural pattern
  (cycle workaround, smell-transfer carrier).

Otherwise architect-roots is optional (Buddy discretion on
substantial specs).

**User-review prompt (foundation specs):** "What would none of
these agents see?" → "## User-Review" in the consolidated.
Required prompt, no gate.

## 3. Flow

**Standard:** dispatch → chief (+ optional discourse) → chief
synth → **post-convergence check** → SAVE → 0C+0H: DONE /
otherwise: escalate Deep.

**Post-convergence check (after chief synth, required):** the
chief answers in the consolidated: (1) "Weakest point in PASS —
what tips it?" (2) "Which single-agent finding was downweighted
the most — rightly so?"
**Deep:** pass 1 (7) → chief → DISCOURSE → chief → SAVE; pass 2+
(4, context-isolated) → chief → discourse → SAVE → fix → next;
final (2) → Buddy direct.

Roles: agents review, chief consolidates, MCA fixes, Buddy
dispatches + commits. Chief consolidation: analysis-mode gate
(`_protocols/analysis-mode-gate.md`) before findings
classification.

### 3a. Delta-verify (standard mode, post-fix re-check)

After fixing findings in standard mode, run a 2-agent re-check
on the delta scope only — not the whole spec. This catches
"smart-but-wrong-in-your-own-fix" (pattern D, session 99).

**Trigger (any of):**
- ≥10 normative lines changed (rule / trigger / required format /
  acceptance — not comments / whitespace / headers)
- ≥3 whole files touched
- ≥1 MAJOR finding fixed
- the fix touches gate composition, severity definition, or
  enforcement logic (meta-critical)

**Team:** 2 agents context-isolated — board-adversary +
board-implementer. Both MUST deliver the first-principles drill
(`agents/_protocols/first-principles-check.md`). No chief in the
delta-verify team.

**Acceptance:** 0 new BLOCKER + 0 new MAJOR. New findings →
another fix pass + another delta-verify (max 3 iterations, then
ESCALATE).

Detail: see `REFERENCE.md` §Delta-Verify.

## Process — mode deep

Deep uses the same flow as above, but starts with pass 1 (7
reviewers) and then loops through pass 2+ (4 reviewers) until
convergence.

## Process — mode ux

UX is no longer a separate skill in the Task-366-EF target. For
UI-heavy specs `spec_board` runs in `mode=ux` with UX personas
(`board-ux-heuristic`, `board-ux-ia`, `board-ux-interaction`)
as an extended team variant. Functional and UX findings are
carried in the same consolidated.

## 4. Buddy checklist (dispatch)

1. Determine spec path + output paths.
2. Operating mode: review or synthesize.
3. Depth mode: steps 0+1 above.
4. Check the foundation flag (→ chief receives the DR
   scorecard).
5. **Engine context** (conditional): when the spec references
   the workflow engine (engine steps, YAML definitions,
   completion types, guards) → agents receive as required
   context: `$FRAMEWORK_DIR/scripts/workflow_engine.py`,
   `$FRAMEWORK_DIR/scripts/lib/yaml_loader.py`, existing
   `workflow.yaml` definitions. Without this context: findings
   on engine limitations are unreliable.
6. Read the SPEC-MAP, identify neighbour specs for impact.
7. Agent selection (base + specialists, document the rationale).
8. Assemble the prompt: reviewer-base + spec-reviewer-protocol +
   persona + dispatch-template. Chief additionally:
   consolidation-preservation + piebald-budget.
9. Dispatch agents in parallel (context-isolated) → spawn the
   chief → read the signal → SAVE (NON-NEGOTIABLE).
10. NEEDS-WORK: fix → next pass | CONVERGED: DONE.

## 5. Discourse

Deep: ALWAYS after chief. Standard: Buddy decision
(proportional). Mechanic: `_protocols/discourse.md`.

## 6. Post-pass (NON-NEGOTIABLE)

- [ ] Chief consolidated has a tracking table
  (consolidation-preservation.md).
- [ ] Verification equation in the consolidated holds (Raw =
  Kept + Merged + Related + Removed).
- [ ] **Merge spot-check:** examine 2-3 MERGED findings — was
  the root cause really identical? Wrong merge → correct to
  RELATED.
- [ ] **Minority re-check:** scan REMOVED + low-severity,
  especially single-agent findings.
- [ ] Piebald-budget check executed on skill / runbook /
  persona reviews (piebald-budget.md).
- [ ] ALL findings fixed (C+H+M+L).
- [ ] **Delta-Verify mini-board** executed if the trigger fired
  (§3a) — 0 new highs.
- [ ] Task YAML `board_result` + `readiness` updated.
- [ ] git commit + push.
- [ ] Deploy when task YAMLs changed.

## 6a. Risk Carry-Forward

When the board terminates without a clean 0C+0H PASS but the user
accepts the result anyway (cherry-pick override, convergence-valve
hit at the safety limit, outer-loop bound reached), the
consolidated verdict file MUST carry the unfixed findings forward
in a top-level YAML block:

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
block: the workflow step skips with rationale "no remaining
findings".

**Acceptance scenarios that require the block:**
- The user says "cherry-pick: fix only blockers, defer the rest"
  — the verdict carries the deferred findings.
- Convergence valve (5 passes) hits with open findings the user
  accepts.
- Outer-loop bound reached (`convergence_loop` REFERENCE.md) and
  the user accepts the residual.
- ESCALATE returned to the user and the user decides "ship
  anyway".

**Why mechanical:** historically these residuals lived in verdict
prose or in informal session notes and disappeared between
sessions. The structured block + workflow-step pair turns
carry-forward into engine-tracked work instead of bookkeeping.

## 7. Output paths

Review files: `docs/reviews/board/{spec-name}-{role}-pass{N}.md`
Consolidated:
`docs/reviews/board/{spec-name}-consolidated-pass{N}.md`

## Contract

### INPUT
- **Required:** spec file (`docs/specs/*.md`) exists and is
  committed.
- **Required:** SPEC-MAP read (neighbour specs identified for
  impact).
- **Optional:** frame report (from `frame`) — as context for
  reviewers.
- **Optional:** engine context
  (`$FRAMEWORK_DIR/scripts/workflow_engine.py`, YAML
  definitions) — when the spec references the workflow engine.
- **Context:** `agents/_protocols/reviewer-base.md`,
  `spec-reviewer-protocol.md`, `dispatch-template.md`,
  `consolidation-preservation.md`, `piebald-budget.md`.

### OUTPUT
**DELIVERS:**
- Board verdict: PASS (0C+0H) or NEEDS-WORK (with severity
  distribution).
- Consolidated findings: finding ID, severity (C/H/M/L),
  finding text, tracking status.
- Tracking table (on NEEDS-WORK): finding → fix status →
  re-review status.
- `board_result`: `pass` | `needs-work` (machine-readable status
  for task YAMLs).
- Review files: individual agent reviews under
  `docs/reviews/board/`.

**DOES NOT DELIVER:**
- No fixes — only findings. Fixes are Buddy / MCA work.
- No code changes — spec-level review.
- No spec authoring — the board reviews existing specs, doesn't
  write them.

**ENABLES:**
- Build prepare: findings (`scope: implementation`) as MUST
  constraints for delegation.
- Fix: NEEDS-WORK findings as the fix scope.
- Convergence: re-review after fixes (max 3 passes via
  `convergence_loop`).
- Task status: `board_result` updates `readiness` in the task
  YAML.

### DONE
- Board verdict: 0C+0H (PASS) after every required pass.
- Tracking table complete (verification equation holds).
- Merge spot-check and minority re-check executed.
- ALL findings fixed (C+H+M+L).
- Delta-Verify executed if the trigger fired (§3a).
- Task YAML `board_result` + `readiness` updated.
- git commit + push + deploy when task YAMLs changed.

### FAIL
- **Retry:** NEEDS-WORK → fix → next pass (`convergence_loop`,
  max 3 passes).
- **Escalate:** standard escalates to Deep on ≥1C or ≥3H. After
  `convergence_loop` max → escalate to the user.
- **Abort:** not foreseen — escalate to the user instead of
  aborting.

## 7a. Review-mode variants

### Standard (role-based, default)

Agents review according to their default role perspective.
Findings grouped by agent. See §2 team composition.

### 5-dimensions mode (optional, corpus sweeps)

Agents **additionally** review along 5 quality dimensions
(completeness, consistency, implementability, interface
contracts, dependencies). Each finding carries a DIM tag in the
finding ID (`ADV-COMP-001`, etc.). The chief consolidates
**per dimension** instead of per agent. Verdict per dimension
(PASS / NEEDS-WORK).

**When to use:**
- After a `spec_update` skill run (phase 5).
- Pre-launch corpus sweep (run every spec once).
- When a standard pass leaves the suspicion "one dimension has
  failed" unresolved.

**Do not use:**
- Delta-Verify after a small fix (overhead too high).
- Runbook / template reviews (different semantics for
  implementability).

Mechanics + dispatch prompt template:
`spec_board/5-dimensions-review.md`. Buddy checklist §4 step 8
extended: "If 5-dim mode: also include the dimension prompt
block from `5-dimensions-review.md` in the dispatch."

---

## 8. Boundary

- No code review → `code_review_board`.
- No pre-code plan review → `impl_plan_review`.
- No standalone legacy UX board in the new model: UI / docs
  review runs as `mode=ux` in `spec_board`.
- No as-is spec update → `spec_update` (writes, before the board
  reviews).

## 9. Anti-patterns

- **NOT** pass findings on without chief consolidation. INSTEAD
  check the chief signal + tracking table. Because: silent loss
  (consolidation-preservation).
- **NOT** close standard without discourse when findings
  diverge. INSTEAD trigger discourse. Because: reviewers see
  different problems; convergence has to be earned.
- **NOT** start a spec fix as a new full pass. INSTEAD scoped
  pre-check + delta review. Because: pass inflation wastes
  tokens.
- **NOT** dispatch agents without context isolation. INSTEAD
  every agent gets ONLY the spec. Because: anchoring bias.
