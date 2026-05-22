---
name: code-review-board
description: >
  Multi-perspective code review. 2 levels: L1 (focused) + L2 (full
  board).
  Triggers when a code diff needs multi-perspective review before merge (build verify, fix L1); NOT for PR-level checks (use /review) and NOT for spec review (use spec_board).
status: active
verification_tier: 1
evidence_layout: per_finding
invocation:
  primary: workflow-step
  secondary: [user-facing]
disable-model-invocation: false
cc_wrapper: true
modes: [l1, l2]
uses: [_protocols/discourse, _protocols/context-isolation, _protocols/content-preservation, _protocols/dispatch-template, _protocols/consolidation-preservation, _protocols/evidence-pointer-schema]
---

# Skill: code-review-board

Buddy checklist for code-review dispatch. Detail mechanics:
`REFERENCE.md`. Agent protocols: `agents/_protocols/reviewer-base.md`
+ `code-reviewer-protocol.md`.

## 1. Level choice

### 1.0 Proportionality gate (MANDATORY — runs before the table)

The level table below is risky-by-default: every change is escalated
until proven small. L-032 (forge-feed) surfaced the cost — a ~30-line
sibling-pattern fix with a green red test landed in L2 because the
diff included 2 tests + 2 as-built spec amendments. Six reviewers +
chief + a fix-pass cycle, 1 of 5 convergence clusters added real
signal, the rest polish. *"Theater"* was the user's word.

Before consulting the table, answer four questions:

1. **Substantive code change ≤~50 net lines in one function** (i.e.
   one cohesive change site, not splattered across the file)?
2. **Mirrors a visible sibling pattern in the same module** (the
   change reads as "another instance of an existing branch", not a
   new mechanism)?
3. **Concrete red test going green** (pre-existing failing test now
   passing) OR a new test that pins the fix?
4. **Spec touches are only as-built documentation** (Step-alt
   example, §S8.2 row, amendment-log header entry, version bump) and
   NOT a contract change (new state in a state-vocabulary, new SSE
   event type, new public API, breaking schema change)?

**3-of-4 yes → `light` path** (single `code-verification` reviewer),
regardless of file count or cross-spec triggers in the table. The
gate authorizes proportionality; the table's mechanical signals do
not override a green red test on a sibling-pattern fix.

**Override floor (trigger consequence narrowed):** the
NON-NEGOTIABLE escalation below the table fires only when the change
is **L/XL effort AND introduces a new subsystem AND changes a named
public API**. "Spec files appear in the diff" is no longer sufficient
to override the gate — bookkeeping amendments are not contracts.

**Gate is mandatory, not optional.** Skipping the gate and running
the table-default IS the L-032 failure mode. If the gate hits 0-2
yes, fall through to the table normally.

### 1.1 Level-choice table

Three-path table per spec 306 §4.4a:

```
light:   ALL of (mechanically testable from `git diff --stat` + `git diff` parse):
         git diff --stat shows ≤2 files changed (test files count 0.5×; see §1.2)
         AND ≤30 net lines added
         AND no docs/specs/*.md touched OR all spec touches are bookkeeping (see §1.2)
         AND no Pydantic model / type-alias / NATS subject / public-API signature change
         AND no new top-level symbol (function/class/module) introduced
         → single agents/code-verification.md persona (verbatim
         verification-agent adoption); VERDICT: PASS|FAIL|PARTIAL
         per upstream contract.
L1 (focused): small-scope but above light threshold AND ≤5 files (tests 0.5×)
              AND no new module AND no schema change AND effort S-M
              → 2-3 reviewers + chief
L2 (full):    >5 files (tests 0.5×) OR new module OR contract-amendment cross-spec
              OR schema change OR effort L-XL
              → 5-7 reviewers + chief
When unclear: L2 — UNLESS §1.0 gate fired light.
```

### 1.2 Counting rules (resolves table ambiguity)

**Test files count 0.5× toward the file-count threshold.** Tests
scale with thoroughness, not with risk surface. A diff that grows
from 2 files to 5 files because the agent wrote 3 thorough tests
should not cross the L1→L2 boundary on file-count alone. The 0.5×
weight is a single number applied to the count, not a sliding scale.

**Spec amendments split into bookkeeping vs contract:**

| Category | Examples | Cross-spec trigger fires? |
|---|---|---|
| Bookkeeping | Step-alt example block, §S8.2 table row, amendment-log header entry, version bump, lessons-table row | No |
| Contract | New state in a state-vocabulary, new SSE event type, new public API, breaking schema change, new invariant | Yes |

Only contract amendments fire the cross-spec L2 trigger.
Bookkeeping amendments document what landed; the level is decided by
the code, not the documentation.

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

**Trigger consequence (NON-NEGOTIABLE, narrowed by §1.0):** after
every MCA return with `status=done` for **L/XL tasks AND new
subsystems AND named public-API changes**, Buddy MUST check the
level. The earlier blanket "L/XL OR new modules" floor over-fired
for sibling-pattern fixes that happened to touch many files (tests
+ as-built specs); §1.0's proportionality gate handles those
correctly. "MCA tested it itself, looks good" is NOT a valid skip
signal **when the gate did not authorize light**. MCA self-test
covers L0+L1+L2 tests, NOT architecture drift, cancellation-path
bugs, race conditions, PII-logging issues, or edge-case data loss —
those are caught only by multi-reviewer diversity, and they are
exactly what the §1.0 gate's question 2 ("mirrors a visible sibling
pattern") screens for.

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

**Level is the input.** Team composition reads from §1 — §1.0 may
have authorized `light` (single `code-verification`); §1.1 picks
L1 / L2; §1.2's counting rules (test files 0.5×, bookkeeping
amendments excluded from cross-spec trigger) decide where the
file-count threshold lands. If §1.0 fired `light`, none of the
below applies — `code-verification` is the whole team.

**Core (ALWAYS, L1 + L2):** code-review + code-adversary.

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

**Specialist-name registry-check (NON-NEGOTIABLE):** every
specialist name in a brief's pre-arranged specialist-set OR in
Buddy's dispatch list MUST resolve to a real file in
`agents/code-*.md`. Hallucinated labels (e.g. `code-async`,
`code-concurrency`) silently fall through at dispatch-time and
cause specialist-set drift — the risk-area they were meant to
cover ships unreviewed. Run `ls agents/code-*.md` at
dispatch-prep to verify; if a name does not match, substitute
from the canonical table above (Infra/worker → `code-reliability`,
async/race → `code-adversary` + `code-architect-roots`). Log
substitutions in the dispatch transparency-header.

**State-vocabulary-property trigger:** when the brief's
§Implicit-Decisions-Surfaced contains a `structural_invariants`
LD with pattern-class "state-vocab" OR "smell-transfer" OR
"cycle-symptom-cause" for ANY LD, `code-architect-roots` is
REQUIRED on the specialist-set, not optional. The state-vocab
half-coverage concern is structurally invisible to the other
specialists.

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
FAIL:            ≥1C or >2H → proportionality triage → MCA fixes the
                 fix-now set → re-review (max 2)
```

**Risk carry-forward (MANDATORY on PASS_WITH_RISKS, FAIL with
non-fix-now findings, user-override cherry-pick, and
ESCALATE-with-open-findings):** the verdict file
MUST contain a YAML block `remaining_findings:` listing every
unfixed finding (including MEDIUM/LOW where present). Per spec 306
§4.7, every entry MUST have a `target:` field with one of seven
values (`spec_text` / `new_task` / `watch_item` / `accept` /
`absorb_next` / `closes_with` / `re_review`). Schema:

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
  - id: C2-009
    target: accept                               # known limitation — no fix, no task
    severity: medium
    locator: src/stream.py:88-94
    title: "Narrow late-release race on the slot pool"
    rationale_for_carry_over: >
      Non-blocking — backstopped by the reaper; does not block the
      reported defect. Default accept per §5 proportionality triage.
```

**7-value `target:` enum (spec 306 §4.7):**

| `target` | Action | When to use |
|---|---|---|
| `spec_text` | batch-patched in same commit by `agents/spec-text-drift-batch.md` (per spec 306 §4.8) — no task | spec wording, example blocks, cross-ref drift, mirror-line inconsistency |
| `new_task` | `task_creation` skill dispatched per entry | real follow-up work (≥M effort, new module, new behaviour) |
| `watch_item` | appended to `context/risk-watch.md` per `skills/_protocols/risk-watch-template.md` | forward-looking risk that fires only on a future trigger |
| `accept` | recorded in the verdict as a known accepted limitation — no fix, no task, no trigger | non-blocking finding that is narrow + backstopped, latent, or introduced by a prior fix-pass in this chain and narrower than the original defect — the DEFAULT disposition for any non-blocking finding |
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

**On FAIL — proportionality triage (NON-NEGOTIABLE):**

A finding's *blocking-ness* is not its isolated severity. Before
the fix-pass brief is written, the chief assigns every consolidated
finding exactly ONE disposition. **Only the fix-now set enters the
fix-pass brief.**

| Disposition | Criterion | Routing |
|---|---|---|
| **fix-now** | blocks a user-facing requirement OR reproduces a reported defect — ALWAYS includes every CRITICAL and every convergence cluster (multiple reviewers converging on one defect = systematic pattern, not a narrow edge) | enters the fix-pass brief |
| **accept** | non-blocking AND one of: narrow + already backstopped (reaper / retry / higher guard); latent (reachable only on a config / version / scale change that is not current reality); introduced by a prior fix-pass in this chain and narrower than the original defect. **The default for any non-blocking finding.** | `target: accept` — recorded, no fix, no task |
| **watch** | as `accept`, plus a named concrete future trigger that would re-open the calculus | `target: watch_item` |
| **fix-later** | promoted out of `accept` only with an explicit cost-justification — not a dumping ground for non-blocking findings | `target: new_task` |

**Hard floor — no cherry-pick:** every CRITICAL and every
requirement-blocking finding is fix-now, non-negotiable. The triage
is the distinction between *blocks the requirement* and *hardens a
narrow edge* — NOT a re-licensing of CRITICAL-only fixing. A
MEDIUM / LOW finding that reproduces a reported defect is fix-now; a
HIGH finding that is a narrow latent edge is `accept`. Convergence
clusters are systematic patterns and stay fix-now — a cherry-pick
there is symptom treatment.

**No "leanest fix" for non-fix-now findings:** a minimal fix is a
flavour of fix-now for when a fix IS warranted — never a disposition
for a finding that did not clear the fix-now gate. `accept` means
closed: no fix, no task, no follow-up investigation.

**Self-introduced findings:** a finding introduced by a prior
fix-pass in the same chain, narrower than the original defect, is
`accept` by default — chasing it ratchets the next pass's scope
upward (the fix-pass-manufactures-the-next-pass's-finding spiral).

**Buddy MUST NOT offer paths A/B/C** ("only CRITICALs now, the rest
later") — phased scope negotiation undermines the board verdict. The
proportionality triage is the chief's principled per-finding
disposition, not a severity menu offered to the user.

The non-fix-now findings populate the FAIL verdict's
`remaining_findings:` block (same schema as PASS_WITH_RISKS);
`risk-followup-routing` processes them.

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
- **Retry:** FAIL (≥1C or >2H) → proportionality triage → MCA
  fixes the fix-now set → L0 after fix → re-review.
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
