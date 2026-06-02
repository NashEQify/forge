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

Buddy checklist. Detail: REFERENCE.md. Protocols:
`agents/_protocols/reviewer-base.md` + `code-reviewer-protocol.md`.

## 1. Level choice

### 1.0 Proportionality gate (MANDATORY — runs before table)

Default = escalate. Gate cuts theater. Answer 4:

1. Change ≤~50 net lines in one function (cohesive site)?
2. Mirrors visible sibling pattern in same module?
3. Red test going green OR new test pins fix?
4. Spec touches bookkeeping only — NOT contract (new state-vocab, new SSE type, new public API, schema break)?

**3-of-4 yes → `light` path** (single `code-verification`). Table ignored.

**Override floor:** non-negotiable escalation below fires only on
**L/XL effort AND new subsystem AND named-public-API change**.
Spec-in-diff alone insufficient.

### 1.1 Level-choice table

```
light:   ≤2 files (test 0.5×) AND ≤30 net LOC AND no contract spec change
         AND no Pydantic/type/NATS/public-API signature change
         AND no new top-level symbol → single code-verification.
L1:      above light AND ≤5 files AND no new module AND no schema
         change AND effort S-M → 2-3 reviewers + chief.
L2:      >5 files OR new exported behavior (new public API, state vocab,
         error taxonomy) OR contract-cross-spec OR schema OR L-XL
         → 5-7 reviewers + chief.
         Shape-preserving extraction (brief: shape-preserving=true
         AND existing tests cover) → L1.
Unclear: L2 UNLESS §1.0 fired light.
```

### 1.2 Counting + triggers

- **Test files = 0.5×** toward file count.
- **Spec amendments:** bookkeeping = no cross-spec trigger; contract
  (new state-vocab, SSE type, public API, schema break, invariant) = trigger.
- **NEW MODULE vs NEW SUBSYSTEM:** file in existing dir = MODULE (L1);
  new top-level dir at subsystem depth = SUBSYSTEM (L2).
- **`code-architect-roots` REQUIRED on L2** when `effort: L|XL OR
  pattern-replacement OR LD-count ≥ 6` AND change introduces new
  exported contract or replicable-downstream pattern. Shape-preserving
  extractions: idle (see `agents/code-architect-roots.md`).
- **Optional L1+:** L1 + 1 risk-specialist when one risk-class dominates.

Detail (incl. post-MCA-return trigger consequence): REFERENCE.md.

## 2. Review brief (MUST before dispatch)

5 steps, each producing output:

1. **TOPOLOGY** — `git diff --stat` (file, package, kind, LOC).
2. **DEPENDENCY TRACE** — who imports? New/changed signatures?
3. **RISK ASSESSMENT** — concurrent access, error paths, interface
   breaks, state machines, external deps.
4. **REQUIREMENTS MAP** — spec_ref ACs + delegation done-criteria.
5. **TEAM COMPOSITION** — risk → agents + focus points.

## 3. Team composition

**Core (L1 + L2):** `code-review` + `code-adversary`.

**L2 specialists (from risk assessment):**

| Risk area | Agent |
|---|---|
| Auth / input / secrets | code-security |
| State machine / business logic | code-domain-logic |
| Infra / worker / NATS / DB | code-reliability |
| Schema / queries / migrations | code-data |
| API contracts (REST / SSE) | code-api-contract |
| LLM / prompt / token budget | code-ai-llm |
| Code docs + spec readability | code-docs-consumer |
| Pattern-purity / structural roots | **code-architect-roots** (REQUIRED on §1.2 trigger) |
| Spec exists (spec_ref) | code-spec-fit (conditional; **sole test-coverage owner**) |
| Retroactive spec drift | code-spec-drift (conditional) |

L2 minimum: core + 2. Maximum: core + all.

**Specialist names MUST resolve to real `agents/code-*.md`.**
Hallucinated labels (`code-async`, `code-concurrency`) fall through
silently — verify at dispatch-prep. Substitution table: REFERENCE.md.

## 4. Buddy checklist

1. Write brief (5 steps).
2. Decide level.
3. Check L0 from MCA return (ruff 0, mypy 0).
4. Assemble prompts: `reviewer-base` + `code-reviewer-protocol` +
   `reviewer-reasoning-trace` + `first-principles-check` + persona;
   dispatch with brief + diff + L0 + spec.
   **L2 brief content (per §4a):** persona-prompt + scope + diff +
   spec links + code paths ONLY. NO prior cycle findings, NO prior
   chief verdict, NO lens framing as autonomous authority, NO
   brief-author rationale.
5. Dispatch.
   - **L1:** parallel, context-isolated.
   - **L2:** pre-board frame check + board dispatch per §4a — Buddy
     runs adversary (+ architect-roots when §1.2 trigger) cold-start
     first, persists their returns verbatim as the frame-check
     artifact (`docs/reviews/code/<date>-<task-id|slug>-frame-check.md`,
     slug fallback when no task), distills the substantive findings
     (severity-preserving) into the board brief as scope/context
     content, then dispatches the board (code-review + risk
     specialists) parallel cold-start.
6. **L1:** Buddy reads both → verify drill+trace → verdict.
7. **L2:** chief consolidates (F-C-DRILL-MISSING / F-C-TRACE-MISSING
   enforced; chain-of-custody audit per `agents/code-chief.md`
   §CHIEF-1.0 — chief reads frame-check artifact and audits board
   coverage of its substantive concerns; pre-consolidation gates
   §CHIEF-1.1, 1.2; reject every claim without ≥1 verbatim
   `file:line` code-quote) → discourse → synthesis → verdict.
8. SAVE.

**Fix-pass dispatch (post-FAIL):** scope-focused tests + L0 on touched
files only, full-suite once at convergence-end, single-reviewer-per-cluster
re-review. Detail: REFERENCE.md.

## 4a. L2 dispatch — pre-board frame check + board

The board itself is one cold-start parallel dispatch (no internal
"layers" the reviewers need to know about). Buddy's pre-board work
incorporates an adversarial frame-check so the board brief reflects
substantive scope/parity/spec-citation concerns before reviewers
read it. The frame-check returns are persisted so chief can audit
the chain at consolidation.

**Cold-start brief (board reviewers):** persona + scope + diff +
spec links (locked) + code paths. NO prior cycle findings, NO chief
verdict, NO lens framing as autonomous authority, NO brief-author
rationale. Exception: narrow verify-single-fix gates (NOT board
iterations).

*Lens framing as autonomous authority defined.* Lens-produced
`## Claim-Verifications` rows (mechanical evidence: `file:line` +
grep command + grep output + disposition) ARE allowed in the brief
— the reviewer can independently re-verify each row with one grep.
What's NOT allowed: lens-produced depth/seam/responsibility-purity
JUDGMENTS presented as conclusions the reviewer must accept. The
distinction is mechanical-evidence (allowed) vs persona-judgment
(blocked).

**Pre-board frame check** (Buddy runs before assembling the board
brief, cold-start):
- Adversary — FULL review per `agents/code-adversary.md`
  §Cold-start pre-mission + persona Check focus. One pass.
- Architect-roots (when §1.2 trigger fires) — pattern-purity review
  per `agents/code-architect-roots.md` §Pre-board frame check role.

**Frame-check artifact (chain-of-custody, MANDATORY).** Buddy
persists both returns verbatim to
`docs/reviews/code/<date>-<task-id|slug>-frame-check.md` BEFORE
assembling the board brief. `<slug>` is a Buddy-derived short
identifier when no task-id exists (e.g. ad-hoc review). The
artifact is the raw evidence chain — chief reads it at consolidation
alongside the board reviews per
`agents/code-chief.md` §Chain-of-custody audit.

**Buddy intermezzo (substantive distillation, brief stays clean).**
Read both returns. Distill the substantive concerns into the board
brief as scope clarifications + named open verifications + code-path
emphasis. The brief contains SUBSTANCE, NOT findings-with-severity
or other finding-shaped framing. Severity stays in the frame-check
artifact for chief audit. Adding `[severity:CRITICAL]` or other
finding-shaped framing into brief content would re-create the
brief-contagion L-046's cold-start rule prevents (reviewer reads
against the brief's framing, not against spec → code).

The anti-dilution mechanism is the **chief audit at consolidation**:
chief reads frame-check artifact AND board reviews, cross-references
by substance + severity (per `agents/code-chief.md` §CHIEF-1.0
audit), surfaces unaddressed artifact concerns at their original
severity. Severity carries the weight via the chief's existing §5 +
CHIEF-1.5 consolidation — without needing severity-tags in the brief.

The board reviewers receive the enriched brief. They do their normal
persona Check focus on what the brief shows them — no "frame-
challenges to verify or reject" framing, because special framing
invites special handling and the substantive concerns are already
in the brief content with their severity tags. They do NOT read the
frame-check artifact — that's chief-audit surface, not reviewer-
input surface.

**Board dispatch** (parallel, cold-start): code-review + risk
specialists per team composition.

**Code-quote mandate (all reviewers):** every finding AND every
"verified X" non-finding carries ≥1 verbatim `file:line` quote
(1-3 lines). Chief rejects claim-without-quote and re-dispatches.

## 5. Verdict

```
PASS:            0C + 0H
PASS_WITH_RISKS: 0C + ≤2H (carry-forward MANDATORY)
FAIL:            ≥1C or >2H → triage → MCA fixes fix-now → re-review (max 2)
```

**Risk carry-forward** (on PASS_WITH_RISKS / FAIL non-fix-now /
cherry-pick / ESCALATE-with-open): verdict YAML
`remaining_findings:` per entry: `id`, `target`, `severity`,
`locator`, `title`, `rationale_for_carry_over`, `proposed_action`.
Schema + example: REFERENCE.md.

**7-value `target:` enum:**

- `spec_text` — batch-patched, no task
- `new_task` — MEDIUM+ only; LOW FORBIDDEN
- `watch_item` — appended to `context/risk-watch.md`
- `accept` — DEFAULT non-blocking; MANDATORY standalone LOW
- `absorb_next` — logged, next file-touch closes
- `closes_with: <id>` — duplicate / convergence to another fix
- `re_review: <reviewer>` — scoped specialist re-look

Empty `target:` = validation fail. All same `target:` = missed
triage anti-pattern. `risk-followup-routing` files new_tasks
mechanically.

**Proportionality triage (NON-NEGOTIABLE on FAIL):**

| Disposition | Criterion |
|---|---|
| **fix-now** | blocks requirement OR reproduces reported defect. ALWAYS every CRITICAL + every convergence cluster (≥3 reviewers same evidence). MEDIUM/LOW reproducing defect = fix-now. HIGH narrow latent = `accept` |
| **accept** | non-blocking AND (narrow+backstopped OR latent OR self-introduced narrower than original). DEFAULT non-blocking |
| **watch** | `accept` + named future trigger |
| **fix-later** | MEDIUM+ only. Named concrete defect + measurable downstream cost. LOW FORBIDDEN |

**Hard floor LOW:** standalone LOW → `accept`. LOW → `new_task`
FORBIDDEN. LOW feels important = severity wrong; re-classify MEDIUM
with named defect, or accept.

**Value-floor `new_task`:** before chief writes `new_task` for any
finding (HIGH included), inline-rationale answers "what operational
impact does NOT doing this followup have?":
- "Nothing breaks" / no named consumer / no measurable cost →
  re-route `accept`.
- "Future-edit safety" / "follows convention" without named consumer
  → re-route `accept` or `watch_item`.
- Real measurable cost + named consumer + reproducible failure
  shape → `new_task` justified.

`new_task` without operational-impact sentence = validation fail.
Hard floors override: CRITICAL, security/auth/consent/crypto, schema
/ public-API contract, full-path tasks stay `fix-now` / `new_task`.

**Bundling content-split:** bundled items tagged
`value_class: real-impact | nice-to-have`. ≥3 reviewers same evidence
= convergence → fix-now. Solo LOWs never escape `accept`.

**Test-coverage findings = `code-spec-fit` sole owner.** Coverage
findings name (a) concrete failure-mode missing tests catch, (b) why
existing test surface (integration, indirect, contract-pinning)
doesn't catch it, (c) smallest test set that closes gap. "Coverage at
integration level" = valid `accept`.

**Process discipline:** no "leanest fix" for non-fix-now (`accept`
= closed); self-introduced narrower than original → `accept`; Buddy
MUST NOT offer paths A/B/C.

**Re-review:** max 2 → ESCALATE. Default single-reviewer pass-1.5
(scope = `affected_scope`). Bundled (>5 clusters/files) or pass-2+
→ §5a two-phase. Full table: REFERENCE.md.

## 5a. Re-review two-phase (multi-reviewer re-reviews)

Triggers: any re-review with >1 reviewer dispatched
(multi-reviewer pass-1.5, bundled clusters, pass-2+). Warm-start
anchoring + brief contagion are precisely the failure modes that
fire when multiple reviewers share a prior-cycle frame.

Exception (narrow): a re-review with exactly one reviewer dispatched
AND scope = single named finding AND single cluster (e.g. "verify
F-CR-007 patched at the cited line") stays single-reviewer pass-1.5,
no two-phase. All three conditions required — single-reviewer alone
is not enough (a bundled multi-cluster dispatch with one reviewer
still inherits cross-cluster prior-frame contagion). The exception
is scoped by reviewer count + cluster count + single-finding focus.

**Phase 1 — cold-derive (60-70%):** diff + scope + persona + spec
(locked) + code paths. FORBIDDEN: prior board findings / brief
rationale / chief verdict / lens framing. Output: findings on
as-coded state per §4a code-quote; closure-claims carry 4-link chain
per `_protocols/mca-brief-template.md` §Reviewer Checkpoints.

**Phase 2 — reconcile (30-40%):** prior findings as appendix.
Output: table — prior finding | addressed? | evidence | correct fix?
| new shape (smell-transfer +1/+2).

Chief: Phase-1 = primary evidence, Phase-2 = closure-verification.
`remaining_findings` = Phase-1 minus prior-cycle-confirmed-closed.

## 6. Discourse

L2: optional (Buddy). L1: none. Mechanic: `_protocols/discourse.md`.

## 7. Output paths

Agent reviews: `docs/reviews/code/{task-id}-{role}.md`.
Verdict: `docs/reviews/code/{task-id}-verdict.md` — the **canonical
engine-facing pointer**. Writing it at exactly this path (task-id,
undated) is a `[DISCIPLINE]` convention the verdict author follows;
re-review passes UPDATE this file in place. The workflow completion gate
is the `[WORKFLOW]` safety net: its `pointer_check` blocks `--complete`
(→ `--force`) when the canonical file is missing — so a dated or
pass-suffixed name (`<date>-{task-id}-rereviewN-*.md`, kept only as
supplementary history) fails-safe rather than passing wrongly. There is
**no** mechanical interception that renames a deviant verdict to
canonical: no proportional enforcement class exists for it post-hook (a
`[WORKFLOW]` rename would need a fuzzy task-id glob — the false-match the
council rejected; the glob-free path collapses back to this
`[DISCIPLINE]` write-canonical rule). See
`framework/enforcement-registry.md`. On L2 the chief also writes
`{task-id}-consolidated.md` (REFERENCE.md §Extended output paths), but
the gate keys on the **verdict only**.

## 8. Contract

**INPUT:** diff (committed/staged), L0 PASS, MCA return summary.
Optional: spec_ref, delegation file.

**OUTPUT:** verdict, brief, per-agent reviews under `docs/reviews/code/`.
On FAIL: findings + severity + locators + fix hints.

**DOES NOT:** code fixes, spec review (→ `spec_board`), lint/type (→ L0).

**DONE:** verdict decided, brief written, reviews persisted, L2 chief
tracking table present, SAVE done.

## 9. Boundary

- Spec review → `spec_board`.
- Pre-code plan review → `impl_plan_review`.
- UX board → `spec_board` (mode=ux).
- Lint / type → L0 (ruff, mypy before L1).

## 10. Anti-patterns

- **NOT** dispatch without brief. INSTEAD run 5 steps first.
- **NOT** L1 on cross-package / schema / new-exported-behavior.
  INSTEAD when unclear → L2.
- **NOT** route LOW to `new_task` or write cost-justification escape.
  INSTEAD `accept` or re-classify MEDIUM with named defect. Text
  justifications hallucinate; only mechanical rule enforces.

Extended (L0-after-fix, tracking-table preservation, single-reviewer
pass-1.5, scope-files in fix-pass brief): REFERENCE.md.
