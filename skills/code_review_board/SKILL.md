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
L2 (full):    >5 files (tests 0.5×) OR new exported behavior (new public
              API surface, new state vocabulary, new error taxonomy)
              OR contract-amendment cross-spec OR schema change OR effort L-XL
              → 5-7 reviewers + chief
              Shape-preserving extraction (brief declares
              `shape-preserving: true` AND existing tests cover the
              moved behavior) → L1 regardless of module count.
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

**NEW MODULE vs NEW SUBSYSTEM:** new file in an existing directory
tree = NEW MODULE (stays at L1). New top-level directory at the
same depth as existing subsystems = NEW SUBSYSTEM (escalates to L2).
Aligned with the §1.1 "new exported behavior" trigger. Detail:
REFERENCE.md §"NEW MODULE vs NEW SUBSYSTEM".

**Optional L1+ mid-tier:** L1 + 1 risk-specialist when one risk-class
dominates (e.g. error path with security implications → core + 1×
security). Detail: REFERENCE.md §"Optional L1+ mid-tier".

**Structural-roots specialist trigger:** `code-architect-roots` is
REQUIRED on L2 specialist set when `effort: L|XL OR pattern-replacement
OR LD-count >= 6` AND the change introduces a new exported contract
or replicable-downstream pattern (see `agents/code-architect-roots.md`
for the post-build gating rule — shape-preserving extractions do
NOT fire post-build architect-roots).

**Trigger consequence (NON-NEGOTIABLE, narrowed by §1.0):** after
every MCA return with `status=done` for L/XL tasks introducing new
subsystems or named public-API changes, Buddy MUST check the level.
"MCA tested it itself, looks good" is NOT a valid skip signal when
the gate did not authorize light. MCA self-test does not catch
architecture drift, cancellation-path bugs, races, PII logging, or
edge-case data loss.

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

**Specialist-name registry-check:** every specialist name MUST
resolve to a real `agents/code-*.md`. Hallucinated labels (e.g.
`code-async`, `code-concurrency`) silently fall through at dispatch.
Detail + substitution table: REFERENCE.md §"Specialist-name
registry-check".

**Coverage finding ownership:** test-coverage findings are
`code-spec-fit`'s sole lens (see `agents/code-spec-fit.md`). Other
specialists CANNOT file coverage-gap findings — if behavior is
unverified, they file in their own axis with severity per impact.
See SKILL §5 hard floors.

**State-vocab trigger + roots-vs-Axis2 distinction + 2026-04-30
migration:** detail in REFERENCE.md (state-vocab pattern-class
auto-requires architect-roots; property-shaped vs module-graph-shaped
boundary; absorbed personas).

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

**Fix-pass dispatch (post-FAIL):** scope-focused tests on touched
files (NOT `pytest tests/`), scope-focused L0, full-suite once at
convergence-end, single-reviewer-per-cluster re-review. Detail:
REFERENCE.md §"Fix-pass dispatch".

## 5. Verdict

```
PASS:            0C + 0H
PASS_WITH_RISKS: 0C + ≤2H (documented + carry-forward MANDATORY)
FAIL:            ≥1C or >2H → proportionality triage → MCA fixes the
                 fix-now set → re-review (max 2)
```

**Risk carry-forward (MANDATORY on PASS_WITH_RISKS, FAIL with
non-fix-now findings, user-override cherry-pick, and
ESCALATE-with-open-findings):** verdict file MUST contain a YAML
block `remaining_findings:` listing every unfixed finding. Each
entry has `id`, `target`, `severity`, `locator`, `title`,
`rationale_for_carry_over`, `proposed_action`. Full schema +
example: REFERENCE.md §"Risk carry-forward — full YAML schema".

**7-value `target:` enum (one-liner each; full table in REFERENCE):**

- `spec_text` — batch-patched in same commit, no task
- `new_task` — follow-up task created (**MEDIUM+ only**; LOW forbidden — see hard floor)
- `watch_item` — appended to `context/risk-watch.md`
- `accept` — known limitation, no action (DEFAULT for non-blocking; MANDATORY for standalone LOW)
- `absorb_next` — logged, next touch on the file closes it
- `closes_with: <id>` — duplicate / convergence to another finding's fix
- `re_review: <reviewer>` — scoped specialist re-look

Chief MUST annotate every entry. Empty `target:` fails validation.
If all entries share the same `target:`, chief surfaces as
anti-pattern (likely missed triage). The workflow step
`risk-followup-routing` reads this block and files follow-up tasks
mechanically.

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
| **fix-later** | MEDIUM+ severity only that names a concrete defect or interface gap with measurable downstream cost. **LOW severity is FORBIDDEN to route here** — see hard-floor rule below. | `target: new_task` (MEDIUM+ only) |

**Hard floor — no cherry-pick:** every CRITICAL and every
requirement-blocking finding is fix-now, non-negotiable. The triage
is the distinction between *blocks the requirement* and *hardens a
narrow edge* — NOT a re-licensing of CRITICAL-only fixing. A
MEDIUM / LOW finding that reproduces a reported defect is fix-now; a
HIGH finding that is a narrow latent edge is `accept`. Convergence
clusters are systematic patterns and stay fix-now — a cherry-pick
there is symptom treatment.

**Hard floor — LOW severity (MANDATORY):** every standalone LOW
finding → `accept`. No exceptions, no escape via cost-justification
(text fields hallucinate; the only enforceable rule is mechanical).
LOW → `new_task` is FORBIDDEN. If a LOW feels important, the
severity assessment was wrong — re-classify as MEDIUM with a named
defect statement, or accept. Rationale: Task 511 was a whole task
spawned for 5 LOW additive test-coverage gaps, none of which
blocked correctness. The protocol that allowed it ("LOW with
cost-justification → new_task") was rubber-stamped because text
fields admit any justification. Mechanical floor closes the gap.

**Single exception — convergence:** when ≥3 reviewers independently
flag the same evidence, the cluster is fix-now per the existing
convergence rule (the convergence IS the signal). The standalone
LOWs in a convergence cluster ride that route, not the LOW→accept
floor. Solo LOWs without cluster never escape `accept`.

**Test-coverage findings (sole owner = `code-spec-fit`):** other
reviewers may NOT file coverage-gap findings. If behavior X is
unverified, the reviewer files in their own axis ("error path
not exercised → silent corruption risk") with severity per impact.
Coverage as coverage is spec-fit's lens, scoped to AC × TC mapping.
Imagined edges without a corresponding AC or named bug class are
out-of-scope. See `agents/code-spec-fit.md` for the full ownership
boundary.

**Process discipline (detail in REFERENCE.md):**

- No "leanest fix" for non-fix-now findings (`accept` means closed).
- Self-introduced findings (prior fix-pass narrower than original)
  → `accept` by default.
- Buddy MUST NOT offer paths A/B/C — chief's per-finding disposition
  is binding; no severity menu to the user.
- Non-fix-now findings populate the `remaining_findings:` block;
  `risk-followup-routing` processes them.

**Re-review limit:** max 2 → ESCALATE (foundation tasks: Buddy may
override on measurable severity drop; non-foundation: strict).
Detail: REFERENCE.md §"Re-review limit".

**Re-review composition:** default = **single-reviewer pass-1.5**
(SAME reviewer that flagged reads the fix; scope = finding's
`affected_scope`). Bundled fix (>5 clusters / >5 files / cross-spec):
convergence-axis grouping, ~3 reviewers. Fresh-angle (full board)
is exception only. F-AR pattern-class re-review = pass-1.5 with
extended scope. Full table + rationale: REFERENCE.md §"Re-review
composition".

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
- **NOT** use L1 on cross-package / schema / new-exported-behavior
  changes. INSTEAD when unclear, use L2. Because: L1 has only 2
  agents; an under-specified scope misses cross-cutting issues.
- **NOT** route a LOW finding to `new_task` or write a
  cost-justification text trying to escape the LOW→accept floor.
  INSTEAD `accept` it, or re-classify to MEDIUM with a named
  defect statement. Because: text justifications hallucinate;
  the only enforceable rule is mechanical.

Extended anti-patterns (L0-after-fix, tracking-table preservation,
single-reviewer pass-1.5, scope-files in fix-pass brief):
REFERENCE.md §"Extended anti-patterns".
