---
name: code-review-board
description: >
  Multi-perspective code review. 2 levels: L1 (focused) + L2 (full
  board).
status: active
verification_tier: 1
evidence_layout: per_finding
invocation:
  primary: workflow-step
  secondary: [user-facing]
disable-model-invocation: false
modes: [l1, l2]
uses: [_protocols/discourse, _protocols/context-isolation, _protocols/content-preservation, _protocols/dispatch-template, _protocols/consolidation-preservation, _protocols/evidence-pointer-schema]
---

# Skill: code-review-board

Buddy checklist for code-review dispatch. Detail mechanics:
`REFERENCE.md`. Agent protocols: `agents/_protocols/reviewer-base.md`
+ `code-reviewer-protocol.md`.

## 1. Level choice

Three-path table per spec 306 §4.4a:

```
light:   ALL of (mechanically testable from `git diff --stat` + `git diff` parse):
         git diff --stat shows ≤2 files changed
         AND ≤30 net lines added
         AND no docs/specs/*.md touched
         AND no Pydantic model / type-alias / NATS subject / public-API signature change
         AND no new top-level symbol (function/class/module) introduced
         → single agents/code-verification.md persona (verbatim
         verification-agent adoption); VERDICT: PASS|FAIL|PARTIAL
         per upstream contract.
L1 (focused): small-scope but above light threshold AND ≤5 files AND no new module
              AND no schema change AND effort S-M
              → 2-3 reviewers + chief
L2 (full):    >5 files OR new module OR cross-spec OR schema change OR effort L-XL
              → 5-7 reviewers + chief
When unclear: L2.
```

**NEW MODULE vs NEW SUBSYSTEM distinction (spec 306 §4.4a):**
"NEW MODULE" alone is no longer sufficient for L2 escalation. A
new file in an existing directory tree is NEW MODULE (stays at
L1). Only NEW SUBSYSTEM (first instance of a top-level service /
domain at the same depth as existing subsystems) escalates to L2.
The distinction is mechanical: a new file in an existing directory
tree is NEW MODULE; a new top-level directory at the same depth as
existing subsystems is NEW SUBSYSTEM.

**Optional L1+ mid-tier:** L1 + 1 risk-specialist (drawn from L2
specialist set per the brief's risk-assessment top-1 entry) is a
precision-escalation option when effort=S/M but a single risk-
class dominates (e.g. error path with security implications →
core + 1× security). Documented in §3 Team composition.

**Structural-roots specialist required (L2 trigger):** any of
`effort: L|XL OR new-module OR pattern-replacement OR
LD-count >= 6` → `code-architect-roots` REQUIRED in the L2
specialist set (see §3). Rationale: existing reviewer
heuristic-set (correctness / contract / domain-logic /
adversary) systematically misses pattern-purity smells
(smell-transfer, cycle-symptom-as-cause, state-vocab-half).
Distribution-as-signal observed: L2 pass-1 producing 5H+12M+10L
without naming structural roots = heuristic gap, not thorough
review.

**Trigger consequence (NON-NEGOTIABLE):** after every MCA return
with `status=done` for L/XL tasks or new modules, Buddy MUST
check the level. "MCA tested it itself, looks good" is NOT a
valid skip signal. MCA self-test covers L0+L1+L2 tests, NOT
architecture drift, cancellation-path bugs, race conditions,
PII-logging issues, or edge-case data loss — those are caught
only by multi-reviewer diversity.

## 2. Review brief (MUST — before agent dispatch)

5 analysis steps, each producing output:

1. **TOPOLOGY:** `git diff --stat` → change topology (file,
   package, kind, LOC).
2. **DEPENDENCY TRACE:** who imports the changed files? New /
   changed signatures?
3. **RISK ASSESSMENT:** derived from 1+2 — concurrent access, new
   error paths, interface break, state machine, external deps.
4. **REQUIREMENTS MAP:** spec_ref → read ACs. Delegation file →
   done criteria.
5. **TEAM COMPOSITION:** from the risk assessment → which agents,
   with what specific focus points.

## 3. Team composition

**Core (ALWAYS):** code-review + code-adversary.

`code-review` covers three quality axes sequentially (correctness
/ architecture / performance) — absorbed `code-quality` +
`code-architecture` + `code-performance` into one multi-axis
persona. Drill+Trace per axis is required.

`code-adversary` runs in parallel — orthogonal smart-but-wrong +
race-conditions discipline.

**L2 specialists (from the risk assessment):**

| Risk area | Agent |
|-----------|-------|
| Auth / input / secrets | code-security |
| State machine / business logic | code-domain-logic |
| Infra / worker / NATS / DB | code-reliability |
| Schema / queries / migrations | code-data |
| API contracts (REST / SSE) | code-api-contract |
| LLM / prompt / token budget | code-ai-llm |
| Code docs + spec readability | code-docs-consumer |
| Pattern-purity / structural roots | **code-architect-roots (REQUIRED on §1 trigger)** |
| Spec exists (spec_ref) | code-spec-fit (conditional) |
| Retroactive spec drift | code-spec-drift (conditional) |

L2 minimum: core + 2 specialists. Maximum: core + all.

**`code-architect-roots`** is property-shaped (smell-transfer,
cycle-symptom-cause, state-vocab-half), distinct from
`code-review` Architecture-Axis 2 which is module-graph-shaped
(dependency direction, coupling, layer violations). Both run
in parallel on substantial L2.

**Migration note (2026-04-30):** before 2026-04-30 the L2 table
had separate entries for `code-architecture` (dependency /
cross-package) and `code-performance` (hot path / N+1 / memory).
Both are absorbed into `code-review` since the hybrid migration.
The risk areas dependency / architecture and hot path / performance
are covered by `code-review` — no separate specialist dispatch
needed.

## 4. Buddy checklist (dispatch)

1. Write the review brief (5 steps above).
2. Decide on the level (L1 / L2).
3. Check the L0 return summary from MCA (ruff 0 errors, mypy 0
   errors).
4. Assemble agent prompts:
   - Read `agents/_protocols/reviewer-base.md`.
   - Read `agents/_protocols/code-reviewer-protocol.md`.
   - Read `agents/_protocols/reviewer-reasoning-trace.md`
     (required trace).
   - Read `agents/_protocols/first-principles-check.md` (required
     drill).
   - Read the agent persona.
   - Dispatch: review brief + changed files + L0 output + spec
     when relevant.
5. Dispatch agents in parallel (context-isolated).
6. **L1:** Buddy reads both reviews directly → verifies that the
   drill + trace sections are present → verdict.
7. **L2:** chief consolidates (**drill + trace enforcement
   active:** F-C-DRILL-MISSING / F-C-TRACE-MISSING when sections
   are missing) → [discourse] → chief synthesizes → verdict.
8. SAVE.

**Fix-pass dispatch (post-FAIL, NON-NEGOTIABLE):**

When dispatching MCA after FAIL, the brief MUST explicitly state:

- **Test scope:** scope-focused on touched files
  (`uv run pytest <scope-files> -x --tb=short`), NOT
  `uv run pytest tests/`. Per `skills/convergence_loop/SKILL.md`
  §"Test scope between passes".
- **L0 scope:** `ruff check <touched-files>` +
  `mypy <touched-files>` only. NOT the full repo.
- **Full-suite sweep:** ONCE at convergence-end, not per
  fix-phase.
- **Re-review composition:** single reviewer per cluster (see §5
  Re-review composition), not full-board redo.

Don't rely on MCA picking the right default — the test-driven
mindset baked into prompts and skills defaults to full-suite.
Make scope-focused testing explicit in the brief.

## 5. Verdict

```
PASS:            0C + 0H
PASS_WITH_RISKS: 0C + ≤2H (documented + carry-forward MANDATORY)
FAIL:            ≥1C or >2H → MCA fixes ALL findings → re-review (max 2)
```

**Risk carry-forward (MANDATORY on PASS_WITH_RISKS, user-override
cherry-pick, and ESCALATE-with-open-findings):** the verdict file
MUST contain a YAML block `remaining_findings:` listing every
unfixed finding (including MEDIUM/LOW where present). Per spec 306
§4.7, every entry MUST have a `target:` field with one of six
values (`spec_text` / `new_task` / `watch_item` / `absorb_next` /
`closes_with` / `re_review`). Schema:

```yaml
remaining_findings:
  - id: C2-003                                 # cluster / finding ID
    target: new_task                           # routing target — see below
    severity: high                             # critical | high | medium | low
    locator: src/foo.py:47-52                  # file:lines or spec §
    title: "Validator regex rejects v1 forms"
    rationale_for_carry_over: >
      PASS_WITH_RISKS — H-finding, within 2H budget, documented per
      re-review-limit hit without severity drop
    proposed_action: "Tighten regex per C2-004 — ~10 LOC"
  - id: C2-006
    target: spec_text                          # batch-patched, no task
    severity: low
    locator: docs/specs/<spec>:651
    title: "Example block shows v1 syntax; should be v2"
    proposed_action: "Replace `foo_v1(...)` with `foo_v2(...)` at line 651"
  - id: C2-005
    target: absorb_next                        # logged, no immediate action
    severity: low
    locator: tests/foo/test_bar.py:123
    ...
```

**6-value `target:` enum (spec 306 §4.7):**

| `target` | Action | When to use |
|---|---|---|
| `spec_text` | batch-patched in same commit by `agents/spec-text-drift-batch.md` (per spec 306 §4.8) — no task | spec wording, example blocks, cross-ref drift, mirror-line inconsistency |
| `new_task` | `task_creation` skill dispatched per entry | real follow-up work (≥M effort, new module, new behaviour) |
| `watch_item` | appended to `context/risk-watch.md` per `skills/_protocols/risk-watch-template.md` | forward-looking risk that fires only on a future trigger |
| `absorb_next` | logged to chief-verdict-archive only — no immediate action | LOW finding the next code-touch on the same file will trivially close |
| `closes_with: <id>` | no action — references another finding's fix | duplicate / convergence — same root, two angles |
| `re_review: <reviewer>` | dispatch the named reviewer with the finding cluster as scoped focus | chief uncertain, contradiction across reviewers, second specialist look |

Chief MUST annotate every entry. Empty `target:` fails chief
output validation (per `skills/risk_followup_routing/SKILL.md`).
Distribution check: if all entries have the same `target:`,
chief surfaces as anti-pattern (likely missed triage).

The workflow step `risk-followup-routing` (build / review / fix
workflow.yaml) reads this block and mechanically files a follow-up
task via `task_creation` — empty/absent block: skip. A verdict
file without the block on PASS_WITH_RISKS is an invalid verdict
(chief re-synth mandatory).

**Rationale:** PASS_WITH_RISKS was historically "≤2H documented"
with "documented" as an unspecified string — findings ended up in
the verdict prose and never became follow-up tasks. Structured
block + workflow step makes carry-forward mechanically enforced,
not bookkeeping-dependent.

**On FAIL — fix scope (NON-NEGOTIABLE):**

MCA fixes **ALL consolidated findings** (CRITICAL + HIGH + MEDIUM
+ LOW + spec drift), not just CRITICAL or the top cluster.
Rationale:

- **Convergence clusters are systematic patterns:** when 4
  reviewers find the same defect from different angles, a
  cherry-pick fix is symptom treatment. Architecture drift gets
  carried forward.
- **MEDIUM / LOW are follow-up debt, not a free pass:** code
  hygiene issues accumulate systematically and cost more later
  than fixing now.
- **Buddy MUST NOT offer paths A/B/C** ("only CRITICALs now, the
  rest later") — that undermines the board verdict.

Fix-scope exception only on **explicit user override** (the user
says "only CRITICALs now, the rest as follow-up tasks"). Default
is always: fix everything.

**Re-review limit (foundation override):**

Default: **max 2 re-reviews → ESCALATE**. But:

- **Foundation tasks** (intake-mvp, brain-foundation,
  brain-schema, schema-foundation, harness-runtime-patterns,
  other tier-1 builds): Buddy may override the limit if
  convergence / severity drop per re-review is measurable (e.g.
  pass 1 FAIL 3C+16H → pass 2 FAIL 0C+4H → pass 3 FAIL 0C+1H →
  pass 4 PASS). Foundation work needs to settle — better 4
  reviews than permanent architecture drift.
- **Buddy decision per pass:** if severity does NOT drop from
  pass N to pass N+1 (e.g. the same convergence cluster shows up
  again) → ESCALATE instead of continuing. The limit override
  applies only on measurable progress.
- **User-override pattern:** the user may say "re-review more
  than 2x if needed — your call", which explicitly empowers
  Buddy without pre-escalation.

Non-foundation tasks: max 2 re-reviews stays strict.

**Re-review composition (NON-NEGOTIABLE):**

Default re-review on FAIL = **single-reviewer pass-1.5**: the
SAME reviewer that flagged the finding cluster reads the fix.
Not full L1 / L2 redo.

| Re-review type | Composition | When |
|----------------|-------------|------|
| Fix verification (default) | Single reviewer per cluster, scope = the finding's `affected_scope` | After every MCA fix-pass on FAIL |
| Fresh angle (exception) | Full board (L1 / L2 per the original level) | Only if pass-1.5 surfaces an architecture concern OR Buddy explicitly wants a fresh take |

Rationale: the verdict file documents `file:line` per finding;
the fix touches that scope, nothing else can change. A 5-reviewer
redo of unaffected modules is risk-theater + 2-3× wallclock /
token cost without new signal. Full-board re-runs are reserved
for fresh analysis at a new convergence-pass scope, not for
"did the fix land?" verification.

**F-AR (architect-roots) re-review exception:** pattern-class
fixes touch multiple files by definition (smell-transfer
fix = pattern moved out of every site). Default re-review for
F-AR findings = pass-1.5 with **extended scope** (all files
affected by the pattern, not just one finding-locator).
Fresh-angle exception fires when the fix introduces a
DIFFERENT pattern-class than the one flagged
(pattern-class-mismatch in fix) — then full-board redo on the
new class.

## 6. Discourse

**L2:** optional (Buddy decision). **L1:** no discourse.
Mechanic: `skills/_protocols/discourse.md`.

## 7. Output paths

Agent reviews: `docs/reviews/code/{task-id}-{role}.md`
Verdict: `docs/reviews/code/{task-id}-verdict.md`

## Contract

### INPUT
- **Required:** code diff (git diff) — changed files must be
  committed or staged.
- **Required:** L0 PASS (ruff 0 errors, mypy 0 errors) — BEFORE
  the board dispatch.
- **Required:** MCA return summary with L0 result.
- **Optional:** spec (`spec_ref` from the task YAML) — for the
  requirements map.
- **Optional:** delegation file — for done-criteria reconciliation.
- **Context:** `agents/_protocols/reviewer-base.md`,
  `code-reviewer-protocol.md`, `dispatch-template.md`,
  `consolidation-preservation.md`.

### OUTPUT
**DELIVERS:**
- Review verdict: PASS / PASS_WITH_RISKS / FAIL.
- Review brief: topology + dependencies + risk assessment +
  requirements map.
- Agent reviews: per agent under `docs/reviews/code/`.
- On FAIL: findings with severity, affected files, concrete fix
  hints.

**DOES NOT DELIVER:**
- No code fixes — only findings and judgment.
- No spec review — only code against the spec (`spec_ref`).
- No linting / type checking — L0 (ruff, mypy) runs BEFORE the
  board.

**ENABLES:**
- Build verify: the verdict drives whether an MCA fix is needed.
- Fix: FAIL findings as structured fix input for MCA.
- Merge: PASS as a gate for commit / deploy.

### DONE
- Verdict decided: PASS (0C+0H) or PASS_WITH_RISKS (0C, ≤2H
  documented) or FAIL.
- Review brief written (5 analysis steps).
- Agent reviews persisted under `docs/reviews/code/`.
- L2: chief consolidation + tracking table present.
- SAVE executed.

### FAIL
- **Retry:** FAIL (≥1C or >2H) → MCA fixes all findings → L0
  after fix → re-review.
- **Re-review limit:** default max 2. Foundation tasks
  (intake-mvp, brain-*, schema-*, harness-*) more on Buddy's
  judgment when severity drops measurably. Non-foundation: strict
  max 2.
- **Escalate:** after the limit without PASS AND without severity
  drop → escalate to the user. With measurable progress: continue
  (foundation only).
- **Abort:** not foreseen — escalate to the user instead of
  aborting.

## 8. Boundary

- No spec review → `spec_board`.
- No pre-code plan review → `impl_plan_review`.
- No standalone UX board → `spec_board` (mode=ux).
- No lint / type check → L0 (ruff, mypy before L1).

## 9. Anti-patterns

- **NOT** dispatch without a review brief. INSTEAD run the 5
  analysis steps first, then dispatch. Because: agents without
  focus points search generically and find less specific issues.
- **NOT** use L1 on cross-package / schema / new-module changes.
  INSTEAD when unclear, use L2. Because: L1 has only 2 agents;
  an under-specified scope misses cross-cutting issues.
- **NOT** FAIL → MCA fix → immediate re-review without a new L0.
  INSTEAD run L0 (ruff + mypy) after every fix. Because: a fix
  can break linting; re-review otherwise sees it later.
- **NOT** accept a chief signal without a tracking table (L2).
  INSTEAD run the preservation check
  (consolidation-preservation). Because: silent loss happens in
  the code board too.
- **NOT** re-run the full L1 / L2 board for fix verification
  post-FAIL. INSTEAD single-reviewer pass-1.5 of the finding
  cluster (§5 Re-review composition). Because: 5 reviewers
  re-doing unaffected scope = risk-theater + 2-3× wallclock /
  token cost without new signal.
- **NOT** brief MCA with `pytest tests/` as DoD on fix-pass
  dispatch. INSTEAD scope-files explicit. Because: re-running
  untouched modules is signal-noise; test-driven mindset baked
  into MCA prompts defaults to full-suite — must be overridden
  in the brief.
