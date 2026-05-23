# 2026-05-23 — Code-review-board default calibration (Task 333 AC-4)

**Status:** decided — **KEEP** current L2-default; §1.0 proportionality
gate stays as the per-task release-valve.
**Owner:** Task 333 AC-4
**Sources:** forge-feed §L-032; `skills/code_review_board/SKILL.md` §1.0–1.2;
24 closed fix-task verdicts across BuddyAI + forge_dev.

## Question

Should `code_review_board/SKILL.md` §1 flip its default from
**"L2 unless the table says light"** to **"light unless an escalation
criterion fires"**?

L-032 codified the per-task proportionality gate at §1.0 (Task 333
AC-1..3, AC-5). AC-4 is the orthogonal calibration question: is the
table's *baseline* miscalibrated, or is the gate the right release-valve
on top of a correctly-calibrated baseline?

**Decision rule (from Task 333):**
- HIT-rate <30% across closed fix-tasks → flip the default.
- HIT-rate ≥30% → keep the default; §1.0 gate carries the load.

A HIT is defined as: the board surfaced a CRITICAL or
requirement-blocking finding that BOTH (a) the green red test did not
catch AND (b) a single `code-verification` reviewer reading the diff
against the spec would not plausibly have caught. "The board flagged
it" is not sufficient — the test is whether a focused single reviewer
on the same diff + spec would have found the same issue.

## Method

1. Enumerated the 24 most recent closed fix-tasks across BuddyAI +
   forge_dev that ran a board (status `done`, verdict file present in
   `docs/reviews/code/`).
2. For each, read the chief consolidation (or the latest-pass
   equivalent), the task YAML, and where relevant the reviewer
   outputs.
3. Classified each as **HIT**, **MISS**, or **N/A** (see definitions
   above; N/A = not a fix-task with green red test — greenfield
   feature, new module commission, board never ran due to timeout, or
   single-reviewer code-verification rather than a board).
4. Computed the ratio over the in-scope population (HIT + MISS).

## Data

24 tasks classified. Per-task rationale lives in the dispatch trace
(forge_dev session 2026-05-23). Summary table:

| Task | Scope | Diff | Red test | Class | One-line rationale |
|---|---|---|---|---|---|
| 493 (BuddyAI) | Orchestrator inspects `LLMResultV1.status`; terminal-status branch | ~30 LOC + 2 tests + 2 e2e + 2 spec amendments | green | **MISS** | The L-032 motivating case. Single code HIGH (`or "llm_unavailable"` blanket fallback) is latent + spec-documented. Rest is text accuracy. |
| 471 (BuddyAI) | X-Correlation-ID middleware (469 carry-forward) | ~30 LOC + 60→61 tests | green | **MISS** | Zero HIGH/CRITICAL surfaced. Buddy's own process note flagged the L1 dispatch as a light-path mis-route. |
| 463 (BuddyAI) | Council FE wire-shape re-mirror against BE Pydantic SoT | ~150 LOC FE + 2 TCs | green snapshot | **MISS** | Spec-fit + adversary both PASS, one MINOR cosmetic, rest observations. |
| 324 (forge_dev) | Skill-corpus C2/C3 regression guards (pre-commit Check 13 + validator) | Pre-commit bash + Python | yes | **MISS** | CRIT was a single-file bash pipefail slip (`grep \| head`) — a focused bash-aware reviewer catches it from the diff. |
| 438 (BuddyAI) | DEFAULT_TENANT_ID layer-discipline refactor (brain-sentinel vs app-default split) | Medium, 12 ACs / 6 LDs | green (w/ C-003 mock-fidelity caveat) | **HIT** | C-001 future-caller divergence of two independent defaults (adversary-only; chief explicitly: "without an adversary this would not have surfaced"). C-002 cross-module half-migration of 9+ string literals the dedup claim didn't dedup. |
| 459 (BuddyAI) | Welle-Y-v2 Council-Cooperation-Hooks (Reaper-Scan-SQL) | L2; 41 tests | green | **HIT** | FakePool blindspot — 41 tests green pre-board, but FakePool short-circuited the actual SQL; real-Postgres pgvector repro from adversary caught a `DatatypeMismatchError`. Tests-give-false-confidence class. |
| 462 (BuddyAI) | Council backend Pflicht-Fix (council_runs UPDATEs + drill state-machine) | 13 files / 1716 ins | green (27/27) | **HIT** | Pass-3 BLOCKERs: REFINE-gate over-applies to legitimate directives (spec-scope misread); engine-vs-reaper LWW state overwrite (concurrency cross-subsystem). |
| 467 (BuddyAI) | Task 461 follow-up (5 HIGH + 3 MED + 7 LOW parked items) | 24 ADV+v1 TCs | green | **HIT** | C-003 cost_future first-fire-wins drops real cost on SDK retry (cross-SDK boundary, no test coverage). C-005 `no_poll_yet` phantom state lies for 2.5 min (state-vocab call). |
| 458 (BuddyAI) | M1 frontend polish (cost-footer + ApiErrorV1 DE-mapping + 409 toast) | ~10 FE files | green (37/37) | **HIT** | `instanceof ApiError` always false through assistant-ui runtime (strips class identity). Required cross-bundle runtime trace into vendor JS. Tests construct ApiError directly, bypassing the runtime — tests are the trap. |
| 464 (BuddyAI) | 457c Council user-cancel e2e + V1.5 hardening | ~400-500 LOC cross-stack | partial (test green on wrong code path) | **HIT** | `council.completed{cancelled:true}` instead of `council.aborted` (SSE-state-vocab + FE state machine cross-axis). Cancel-during-drill emits `all_members_failed` not `user_cancelled` (audit subtype). Smart-but-wrong test TC-464-004 hid via wrong code path. |
| 468-D (BuddyAI) r2 | userFeedback Items 1-7 + cost-persistence + Groq adapter (fix-pass regression) | Large FE-dominant + BE pump detach | route-level abort test (r2) | **HIT** | r2 C-201: detached `release_active_op` runs unconditional unkeyed UPDATE → stomps a slot a later turn re-claimed. Pattern-transfer hazard (turn-private DELETE pattern copied verbatim to shared-slot clear). Chief verified against persistence.py ground truth. |
| 326 (forge_dev) | Skill-wrapper generator + validator | Generator + 22 tests | green (22/22) | **HIT** | `write_wrappers` rmtree's any non-`desired` child under `.claude/skills/` with no ownership guard → destroys hand-authored CC-plugin wrappers; reaches public OSS mirror via release-sync. **Green test (TC-9) endorses the bug.** Classic test-certifies-bug + blast-radius cross-axis. |
| 327 (forge_dev) | Task-schema SoT + validator (kill priority/prio + mid/medium drift) | Validator + plan_engine | yes (`327-anchor` self-test) | **HIT** | Recurrence-class flagging across 3 passes — single-axis tightenings missed the structural class; only adversary's refusal-to-converge reached the "redesign vs patch" valve (Approach C: single declarative-data trust boundary at parse seam). A single reviewer would have signed off Pass-1.5. |
| 301 (forge_dev) | Fabrication-Mitigation Pass-2/3 Backlog cleanup (10 findings) | ~50 LOC engine + 11 tests | partial | **HIT** | F-ENGINE-001 lazy-resolution fix doesn't cover `spec_ref: null` (self-referent tasks like 299 itself). AC-6 verification command unfulfillable on the very task containing the fix. Mock workflow tests hid the gap. |
| 492 (BuddyAI) | Mid-stream refresh persistence (3-phase write, let-it-run inversion) | Large feature, spec v2.3 | partial | **N/A** | Not a small fix-task — substantial feature rewrite. (Findings *were* board-class — concurrency × state-vocab × prompt-poisoning — but the unit doesn't fit the AC-4 calibration shape.) |
| 480 (BuddyAI) | App-E2E harness greenfield | Net-new test infra | the harness IS the test apparatus | **N/A** | Greenfield commission with no prior red test baseline. |
| 495 (BuddyAI) | App-E2E harness follow-up (480 clusters) | Mixed | green | **N/A** | Single-reviewer code-verification, not a board run. |
| 469 (BuddyAI) | `error_envelope.py` FastAPI middleware module | Medium-Large new module + 52 tests + spec amendments | green | **N/A** | Greenfield middleware module + cross-module FE consumer trace. Not a small fix; would escalate under any rule. |
| 457 (BuddyAI) | Council Mode V1 (backend engine + chat-UI + new schema + new spec) | L2 feature commission | tests structurally wrong (mocked FE-shape, not BE-payload) | **N/A** | Large greenfield feature. 6 CRIT clusters surfaced — board did its job, but not a calibration data point. |
| 428 (BuddyAI) | M2 Memory Basic (BrainCapability + Postgres sub-cap + history) | NEW MODULE, ~2,690 LOC, L effort | yes (17 TCs + real-PG E2E) | **N/A** | Greenfield. Board deferred (predicted reviewer timeouts) — no board signal to calibrate against. |
| 461 (BuddyAI) | Provider Budget/Rate-Limit Display (new module + new spec) | 14+ files / ~970 LOC src | partial | **N/A** | Greenfield new module + new spec. Board fixed 2 CRIT + parked 15 findings to 467, but not a fix-task population member. |
| 460 (BuddyAI) | 458 visual-verify fix-pack | 14 files / ~120 src + ~1,900 test LOC | green (16/16) | **N/A** | Both L1 reviewers timed out; Buddy meta-verdict on test-evidence alone. No board signal to calibrate. |
| 465 (BuddyAI) | Council UI bug pack (pre-check + start-drill + rename) | 18 files / ~1,200 LOC | green (15 TCs) | **N/A** | Both L1 reviewers timed out. No board signal. |
| 299 (forge_dev) | Fabrication-Mitigation: Evidence-Pointer-Schema + Engine-Step-Gate | Large multi-pass framework build | n/a | **N/A** | Multi-pass framework commission, not a fix-task. (For the record: Pass-2 caught CC-006 regression — cross-layer filter-strictness drift only adversary surfaced — would be HIT had it been a fix-task.) |

## Counts

- **HIT:** 10 (438, 459, 462, 467, 458, 464, 468-D, 326, 327, 301)
- **MISS:** 4 (493, 471, 463, 324)
- **N/A:** 10 (greenfield commissions / board-didn't-run / single-reviewer)

In-scope population: 14
**HIT-rate: 10/14 ≈ 71%**

## Decision

**KEEP** the current L2-default. The §1.0 proportionality gate (Task
333 AC-1..3) stays as the per-task release-valve.

The ratio (71%) is more than double the 30% flip threshold. The data
argues *against* a default flip and *for* the gate-on-default
architecture currently codified.

## Rationale — what the data actually shows

Two patterns are clear:

**1. The smallest fix-tasks (the L-032 motivating profile) are all
MISS, but the §1.0 gate already routes them to `light`.**
All four MISSes (493, 471, 463, 324) match the L-032 shape: ~30–150 LOC,
sibling pattern or local refactor, single green red test. Under the
new §1.0 gate, every one of them would have answered 3-of-4 yes and
landed on the `light` path. The gate is doing exactly the job L-032
asked for. A default flip would be redundant with the gate at this
band, and would expose the next band up (medium fixes) without
compensating safety.

**2. At the medium-fix-task band (where the §1.0 gate does *not*
short-circuit), the board repeatedly catches things a single reviewer
would miss.** The HIT cluster (438, 459, 462, 467, 458, 464, 468-D r2,
326, 327, 301) reveals the recurring catch-only-by-board failure
modes:

- **Tests-certify-the-bug** — 326 (TC-9 endorses the destructive
  `rmtree`), 458 (tests construct `ApiError` directly, bypass the
  runtime), 459 (FakePool short-circuits the SQL that breaks under
  real Postgres).
- **State-vocabulary half-coverage** — 464 (`council.completed`
  vs `council.aborted`), 467 (`no_poll_yet` lies for 2.5 min), 492
  (`stream_status` collapses abnormal-end), 438 (two-default
  divergence between `ctx` and `fact`).
- **Pattern-transfer hazards** — 468-D r2 (turn-private DELETE
  pattern copied verbatim to a shared-slot UPDATE site; same syntax,
  opposite safety profile).
- **Recurrence-class detection across passes** — 327 (three passes
  to reach "redesign vs patch" valve; single reviewer would have
  signed off Pass-1.5 on the narrow fix).
- **Cross-subsystem concurrency** — 462 (engine-vs-reaper LWW race),
  468-D (cross-turn slot-stomp via detached task).
- **Self-reference / scope-coverage gaps** — 301 (fix doesn't cover
  the very task containing the fix).
- **Cross-SDK / cross-boundary corners** — 467 C-003 (retry-path
  cost-loss across SDK seam).

These are precisely the classes the per-reviewer team-composition was
designed to surface: adversary's smart-but-wrong probes, domain-logic's
state-machine reading, architect-roots' pattern-purity, spec-fit's
contract-vs-implementation walk. A single light reviewer with the diff
+ spec + green red test would plausibly miss most of these — not
because they are bad reviewers, but because the failure modes require
the diversity-of-axes the multi-reviewer board provides.

## What stays in place

- `code_review_board/SKILL.md` §1.0 (Proportionality gate) — unchanged.
  3-of-4 yes → `light`. The gate is the calibrated release-valve and
  the data above is its empirical validation.
- §1.1 level-choice table — unchanged. L2-default for everything the
  gate doesn't authorize as light.
- §1.2 counting rules (tests 0.5×, bookkeeping vs contract amendments)
  — unchanged.
- Override floor (NON-NEGOTIABLE escalation: L/XL AND new subsystem AND
  named public-API) — unchanged.

## Threats to validity

- **Sample size.** 14 in-scope cases is small. The 71% point estimate
  has wide uncertainty bounds; a true rate as low as 50% is consistent
  with the data and would still keep the default.
- **HIT classification is a judgment call.** The "single reviewer
  would plausibly have missed it" test is calibrated by reading
  reviewer outputs in retrospect, with knowledge of which findings
  proved real. The classifier may be over-attributing leverage to the
  board. Even if 3 of the borderline HITs (301, 467-C005, 327) are
  reclassified MISS, the rate falls to 7/14 = 50% — still above the
  30% flip threshold.
- **Selection bias toward "boards that ran".** The N/A bucket (10/24)
  is large because it includes greenfield commissions where the
  board's role is uncontested. The fix-task population may be smaller
  than the corpus suggests; a future sweep at +3 months should
  re-check the calibration once more pure-fix-task data accumulates.
- **The §1.0 gate is new (2026-05-23 itself).** None of the 14 data
  points was decided under the gate. They are the *base-rate before
  the gate*. After 3 months of gate operation, re-run the same
  analysis: the in-scope population should shift down (the 4 MISSes
  would have routed to `light` under the gate and disappear from the
  board population). A future HIT-rate near 100% on the
  post-gate population is the expected outcome and is what
  validates the current architecture.

## Follow-ups (deferred — NOT folded into this decision)

- **Re-evaluate at +3 months (≈2026-08).** Pull the next ~20 closed
  fix-tasks decided *under* the §1.0 gate. Expected outcome: the
  L-032-shape tasks have routed to `light` (no board verdict to
  classify), and the remaining board-verdict population shows a
  higher HIT-rate. If observed: confirm the architecture. If the
  board HIT-rate falls below 30% even on the post-gate population,
  re-open the flip question.
- **Per-band HIT-rate stratification.** With more data, split HIT-rate
  by effort (S/M/L) and by the §1.0 gate-question profile (which of
  the 4 questions failed). May reveal a sharper rule than 3-of-4.

## Forge-feed §L-032 amendment

L-032 status flips from "AC-4 still open" to "AC-4 closed (keep
default)" with a link to this decision. See
`docs/dogfood-learnings/forge-feed.md` §L-032 (Status field).
