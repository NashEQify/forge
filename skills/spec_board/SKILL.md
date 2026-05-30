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
  Triggers when an existing spec must be checked for rebuild-readiness AFTER writing; NOT for spec authoring (use spec_authoring) or retroactive code sync (use retroactive_spec_update).
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

Buddy checklist. Detail: `REFERENCE.md`. Agent protocols:
`agents/_protocols/reviewer-base.md` + `spec-reviewer-protocol.md`.

## 0. Plan + review (required without a frame)

Direct board dispatch without prior `frame`: plan block (scope /
tool / alternatives) + self-review + (non-trivial) `plan-adversary`
dispatch. With existing frame report: reference, don't re-run.
Templates + triggers: `_protocols/plan-review.md`.

## Process — common

1. Decide scope + depth (incl. foundation flag).
2. Assemble role-based team.
3. Dispatch context-isolated reviews; consolidate via chief.
4. Close NEEDS-WORK via fix-loop until 0C+0H.
5. Post-pass checks + task / commit / deploy cleanly closed.

## 1. Depth mode

### 1.0 Proportionality gate (MANDATORY — runs before §1.1)

Default = escalate. Bookkeeping spec edits (amendment-log rows,
Step-alt examples, lessons-table rows, version bumps) systematically
fire the cross-layer / interface checks and burn a Deep pass. Gate
cuts theater. Answer 4:

1. Substantive edit ≤~30 net lines AND ≤2 sections (single change
   site, not a sweep)?
2. Mirrors visible sibling pattern in same spec (new amendment-log
   row alongside existing, new Step-alt alongside existing alts)?
3. Descriptive, not prescriptive — documents what already landed in
   code OR clarification / rewording, NOT a new rule / state / contract?
4. No new state-vocabulary, no new public-API contract, no new SSE
   event, no new schema field, no new normative rule (cross-spec-impact
   lens — if neighbour specs need to learn the change, it's contract)?

**3-of-4 yes → standard mode** regardless of §1.1 signals. spec_board
has no `light` tier; gate authorizes *staying-in-standard*, not
skipping the board.

**Override floor (hard escalation regardless of gate):**
- YES on **security** check (auth / consent / crypto) → ALWAYS Deep.
- YES on **full-path** (`dev_path: full`) → ALWAYS Deep.

**Pre-gate FAIL (new L1+ specs only) — two required sections:** new
L1+ spec submitted without either section → **FAIL before §1.0 runs:

1. **§Module-Decomposition missing** → FAIL. Author adds per
   `framework/spec-engineering.md` §Convention: §Module-Decomposition.
2. **§Test-Strategy missing** → FAIL. Author adds bug-class catalog
   per §Convention: §Test-Strategy.

**Board review of §Test-Strategy** (when present): every AC ≥1
bug_class row (no orphan); no duplicate bug_class (semantic dedup);
each bug_class is a noun phrase (not test-case name). Vague /
duplicate / orphan = findings (severity per impact).

Legacy specs **silent-skip** both — touch-it-fix-it via
`_protocols/spec-amendment-discipline.md` categories (d) and (e).
Cross-layer / interface triggers yield to gate on bookkeeping;
standard→Deep on ≥1C or ≥3H still applies.

### 1.1 Scoped pre-check + 4 checks

- **Scoped pre-check:** `board_result pass` AND change ≤3 sections
  → standard (3 agents, no chief discovery). Otherwise → step 1.
- **Step 1 — 4 checks (≥1 YES → Deep):** cross-layer (consumers
  in another layer), interface (API / Pydantic / schema), full path
  (`dev_path: full`), security (auth / consent / crypto).
- All NO → standard. Standard escalates Deep on ≥1C or ≥3H.

## 2. Team composition

- **Standard:** chief + adversary + implementer + impact +
  **architect-roots** (CONDITIONAL on §2a).
- **Deep pass 1:** all 7 (+ Adv-2, Adv-3 Sonnet, Consumer Sonnet)
  + **architect-roots** (ALWAYS in pass 1).
- **Deep pass 2+:** 4 (Adv + Adv2 + Impl + Impact).
- **Deep final:** 2 (Adv + Impl).

Specialists by content: schema/API → `code-api-contract`;
readability → `board-consumer`; first principles → `board-adversary-2`.

### 2a. Architect-roots trigger

Include `board-architect-roots` when ANY of: spec has ≥6 LDs;
spec touches a state machine; diff replaces a previously-flagged
structural pattern.

**User-review prompt (foundation specs):** "What would none of
these agents see?" → `## User-Review` in consolidated. Required, no gate.

## 3. Flow

**Standard:** dispatch → chief (+ optional discourse) → chief synth
→ post-convergence check → SAVE → 0C+0H DONE; else escalate Deep.

**Post-convergence check (required after chief synth):** chief
answers in consolidated: (1) "Weakest point in PASS — what tips it?"
(2) "Which single-agent finding was downweighted the most — rightly so?"

**Deep:** pass 1 (7) → chief → DISCOURSE → chief → SAVE; pass 2+
(4) → chief → discourse → SAVE → fix → next; final (2) → Buddy direct.

Chief consolidation: analysis-mode gate
(`_protocols/analysis-mode-gate.md`) before findings classification.

### 3a. Delta-verify (standard mode, post-fix re-check)

After fix in standard mode: 2-agent re-check on delta scope only.
Trigger (any): ≥10 normative lines changed; ≥3 files touched; ≥1
MAJOR fixed; fix touches gate composition / severity / enforcement.
Team: `board-adversary` + `board-implementer` (both deliver
first-principles drill; no chief). Acceptance: 0 new BLOCKER + 0 new
MAJOR. Max 3 iterations → ESCALATE. Detail: REFERENCE.md.

## Process — mode deep

Same flow as above; starts with pass 1 (7) and loops through pass 2+
(4) until convergence.

## Process — mode ux

UX is not a separate skill. For UI-heavy specs `spec_board` runs in
`mode=ux` with UX personas (`board-ux-heuristic`, `board-ux-ia`,
`board-ux-interaction`) as extended team variant. Functional + UX
findings in same consolidated.

## 4. Buddy checklist (dispatch)

1. Spec path + output paths.
2. Operating mode (review or synthesize).
3. Depth mode: §1.0 first (MANDATORY), then §1.1.
4. Foundation flag check (→ chief receives DR scorecard).
5. **Engine context** (conditional): spec references workflow engine
   → agents receive `$FRAMEWORK_DIR/scripts/workflow_engine.py`,
   `yaml_loader.py`, existing `workflow.yaml`. Detail: REFERENCE.md.
6. Read SPEC-MAP; identify neighbour specs for impact.
7. Agent selection (base + specialists; document rationale).
8. Assemble prompt: reviewer-base + spec-reviewer-protocol + persona
   + dispatch-template. Chief additionally: consolidation-preservation
   + piebald-budget.
9. Dispatch parallel (context-isolated) → spawn chief → read signal
   → SAVE (NON-NEGOTIABLE).
10. NEEDS-WORK: fix → next pass; CONVERGED: DONE.

## 4a. Cross-task AC validation

Trigger patterns (cross-subsystem flow implied):
"user types ... → ... lands in ..."; "X publishes Y; Z consumes Y"
(across components); "after deploy, ... is visible / active /
produced"; "UI displays state X after backend action Y";
"milestone-level user-promise activation across components".

Per such AC: list subsystems traversed; per subsystem identify
OWNING task (via `blocked_by` / `blocks` / sibling-task references).
If owning-task ≠ this task for ANY subsystem → AC cannot close in
this task alone — finding.

Resolution (board recommends, author / orchestrator chooses):
(a) **Split** — this task gets owned half; others become separate
ACs in owning tasks. (b) **Move** — full AC reassigned to whichever
task owns the LAST subsystem to land. (c) **Conditional (task-YAML ACs only)** — prefix
"(after `<blocking-task>` ships) ...". Applies to task-YAML ACs
only. For spec-level ACs in L1+ specs (public-surface OSS mirror per
CLAUDE.md Inv 7+8), use (a) Split or (b) Move — NEVER (c) in a spec,
to keep forensic task-IDs out of public surface. Spec-level ACs
needing dependency: use semantic phrasing ("when consumer-side X is
wired") instead of task-ID prefix.

Unaddressed cross-task AC = NEEDS-WORK blocker. Defense-in-depth pair
with `agents/buddy/operational.md` §Architecture-Comprehension B
(post-return).

## 5. Discourse

Deep: ALWAYS after chief. Standard: Buddy decision (proportional).
Mechanic: `_protocols/discourse.md`.

## 6. Post-pass (NON-NEGOTIABLE)

- [ ] Chief consolidated has tracking table.
- [ ] Verification equation holds (Raw = Kept + Merged + Related + Removed).
- [ ] Merge spot-check (2-3 MERGED findings — root cause really identical?).
- [ ] Minority re-check (scan REMOVED + low-severity single-agent).
- [ ] Piebald-budget check on skill / runbook / persona reviews.
- [ ] All findings fixed (C+H+M+L).
- [ ] Delta-Verify mini-board if §3a trigger fired — 0 new highs.
- [ ] Task YAML `board_result` + `readiness` updated.
- [ ] git commit + push; deploy if task YAMLs changed.

## 6a. Risk carry-forward (MANDATORY on user-override / cherry-pick / valve-hit / ESCALATE-accepted)

Verdict file MUST carry unfixed findings forward in top-level YAML
block `remaining_findings:` listing every unfixed finding with `id`,
`severity`, `locator`, `title`, `rationale_for_carry_over`,
`proposed_action`. Workflow step `risk-followup-routing` reads the
block and files ONE follow-up task per workflow run via `task_creation`.
Empty/absent block → skip with rationale.

Full schema, example, acceptance scenarios: REFERENCE.md
§Risk carry-forward.

## 7. Output paths

Reviews: `docs/reviews/board/{spec-name}-{role}-pass{N}.md`
Consolidated: `docs/reviews/board/{spec-name}-consolidated-pass{N}.md`

## 7a. Review-mode variants

**Standard (default):** agents review per role; findings grouped by agent.
**5-dimensions (corpus sweeps):** agents additionally review along 5
quality dimensions; chief consolidates per dimension. Use after
`spec_update` or pre-launch sweep. Mechanics:
`spec_board/5-dimensions-review.md`.

## 8. Contract

**INPUT:** spec file (committed), SPEC-MAP read. Optional: frame
report, engine context. Context: protocols (reviewer-base, spec-
reviewer-protocol, dispatch-template, consolidation-preservation,
piebald-budget).

**OUTPUT:** board verdict (PASS 0C+0H or NEEDS-WORK with severity
distribution), consolidated findings, tracking table on NEEDS-WORK,
`board_result` (machine-readable), review files under
`docs/reviews/board/`.

**DOES NOT:** fixes (Buddy/MCA work), code, spec authoring.

**DONE:** verdict 0C+0H every required pass; tracking table complete;
merge + minority checks executed; all findings fixed; Delta-Verify
done if triggered; Task YAML updated; commit + push + deploy as needed.

**FAIL handling:** NEEDS-WORK → fix → next pass (max 3 via
`convergence_loop`). Standard → Deep on ≥1C or ≥3H. After max →
ESCALATE.

## 9. Boundary

- Code review → `code_review_board`.
- Pre-code plan review → `impl_plan_review`.
- Legacy UX board → `mode=ux` here.
- As-is spec update → `spec_update` (writes before board reviews).

## 10. Anti-patterns

- **NOT** pass findings on without chief consolidation. INSTEAD
  check chief signal + tracking table (silent-loss prevention).
- **NOT** close standard without discourse when findings diverge.
  INSTEAD trigger discourse.
- **NOT** start spec fix as new full pass. INSTEAD scoped pre-check
  + delta review (pass inflation = wasted tokens).
- **NOT** dispatch agents without context isolation. INSTEAD every
  agent gets ONLY the spec (anchoring bias).
- **NOT** run §1.1's 4 checks before §1.0's proportionality gate.
  INSTEAD §1.0 first; security + full-path remain hard overrides.
- **NOT** skip the §Module-Decomposition OR §Test-Strategy pre-gate
  on a NEW L1+ spec by assuming legacy. INSTEAD verify creation-date
  or section-history before silent-skipping.
