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
5. Dispatch parallel, context-isolated.
6. **L1:** Buddy reads both → verify drill+trace → verdict.
7. **L2:** chief consolidates (F-C-DRILL-MISSING / F-C-TRACE-MISSING
   enforced) → discourse → synthesis → verdict.
8. SAVE.

**Fix-pass dispatch (post-FAIL):** scope-focused tests + L0 on touched
files only, full-suite once at convergence-end, single-reviewer-per-cluster
re-review. Detail: REFERENCE.md.

## 5. Verdict

```
PASS:            0C + 0H
PASS_WITH_RISKS: 0C + ≤2H (carry-forward MANDATORY)
FAIL:            ≥1C or >2H → triage → MCA fixes fix-now → re-review (max 2)
```

**Risk carry-forward (MANDATORY on PASS_WITH_RISKS / FAIL non-fix-now
/ override cherry-pick / ESCALATE-with-open):** verdict file has YAML
`remaining_findings:` block. Per entry: `id`, `target`, `severity`,
`locator`, `title`, `rationale_for_carry_over`, `proposed_action`.
Schema + example: REFERENCE.md.

**7-value `target:` enum** (full table REFERENCE.md):

- `spec_text` — batch-patched, no task
- `new_task` — follow-up task (**MEDIUM+ only**; LOW forbidden, see hard floor)
- `watch_item` — appended to `context/risk-watch.md`
- `accept` — known limitation, no action (DEFAULT non-blocking; MANDATORY standalone LOW)
- `absorb_next` — logged, next file-touch closes
- `closes_with: <id>` — duplicate / convergence to another fix
- `re_review: <reviewer>` — scoped specialist re-look

Chief annotates every entry. Empty `target:` = validation fail. All
same `target:` = anti-pattern (missed triage). Workflow
`risk-followup-routing` files new_tasks mechanically.

**Proportionality triage (NON-NEGOTIABLE on FAIL):**

| Disposition | Criterion | Routing |
|---|---|---|
| **fix-now** | blocks requirement OR reproduces reported defect. ALWAYS every CRITICAL + every convergence cluster (≥3 reviewers same evidence). MEDIUM/LOW reproducing defect = fix-now. HIGH narrow latent = `accept`. | fix-pass brief |
| **accept** | non-blocking AND (narrow+backstopped OR latent OR self-introduced narrower than original). **DEFAULT non-blocking.** | `target: accept` |
| **watch** | as `accept` + named future trigger. | `target: watch_item` |
| **fix-later** | MEDIUM+ only. Named concrete defect + measurable downstream cost. **LOW FORBIDDEN.** Value-floor check applies (see below). | `target: new_task` |

**Hard floor — LOW (MANDATORY, bundle-proof):** any LOW → `new_task`
FORBIDDEN. Bundling LOWs (`bundle_with:`, `bundle:`) does NOT
promote severity — a bundle of N LOWs is still LOW. Real-impact
LOWs route to `absorb_next`; nice-to-have LOWs route to `accept`.
LOW feels important = severity wrong; re-classify MEDIUM with named
defect, or accept. No cost-justification escape (text hallucinates).
Enforced mechanically by `risk_followup_routing/SKILL.md` Gate L.

**Value-floor — `new_task` (MANDATORY):**
mirrors `task_creation/SKILL.md` §1.5 on the consumption side. Before
chief writes `target: new_task` for any finding (HIGH included),
answer in the disposition rationale: *"what operational impact does
NOT doing this followup have?"*

- **Nothing breaks** — no contract violation, no consumer blocked, no
  named bug-surface, no measurable downstream cost → re-route to
  `accept` (carry-forward note, no task).
- **Hand-wavy "future-edit safety" / "new contract needs coverage" /
  "follows convention" with no named consumer or failure-mode** →
  re-route to `accept` or `watch_item` (with named trigger).
- **Real measurable cost + named concrete consumer + reproducible
  failure shape** → `new_task` justified.

A `new_task` disposition without an *operational-impact sentence*
inline in the rationale is a validation fail. If the impact reduces
to "should have tests" / "could be cleaner" / "consistency with
convention" → re-route. Hard floors retain override: CRITICAL,
security / auth / consent / crypto, schema or public-API contract
changes, full-path tasks always stay `fix-now` or `new_task`
regardless of value-floor outcome.

**Critical-path lens — MANDATORY for `new_task` (Gate C surrogate).**
`target: new_task` requires `consumers:` containing AT LEAST ONE
in-flight task in an active milestone (IN_PROGRESS, NEXT ACTIONS, or
the active-milestone `ready` set per `plan_engine.py --boot`).
Consumer pointing only to dormant work (POST-MVP task, BLOCKED
milestone, future-event, generic user-role) → reroute to
`watch_item` with the consumer-activation as `trigger:`. This is
mechanically enforced by `risk_followup_routing/SKILL.md` Gate C;
chief writes the right disposition first time by asking *"does this
finding have a named consumer that is in flight TODAY?"* before
emitting `target: new_task`.

**Goldplating self-admission (Gate G surrogate).** `value_class:
nice-to-have` + `target: new_task` is invalid — the label IS the
goldplating answer. Either upgrade `value_class` to `real-impact`
with named cost OR route to `accept`. Mechanically rejected by
`risk_followup_routing/SKILL.md` Gate G.

**Bundling content-split (when chief bundles related findings into one
new_task):** each bundled item tagged `value_class: real-impact |
nice-to-have` so the followup task can be scoped down without
re-reading the originating reviews. **Bundling does NOT lift the
severity floor (Gate L) — a bundle of N LOWs is still LOW and
cannot be `new_task`.**

**Exception — convergence:** ≥3 reviewers same evidence → fix-now.
Solo LOWs never escape `accept`.

**Test-coverage findings = `code-spec-fit` sole owner.** Others cannot
file coverage gaps. Behavior-unverified → finding in own axis with
severity per impact. Coverage findings MUST name (a) the concrete
failure-mode the missing tests would catch, (b) why the existing test
surface (integration, indirect via consumers, contract-pinning) does
not catch it, (c) the smallest test set that closes the gap. "Coverage
exists at the integration level" is a valid `accept` disposition;
chief honors it. See `agents/code-spec-fit.md`.

**Process discipline** (detail REFERENCE.md): no "leanest fix" for
non-fix-now (`accept` = closed); self-introduced narrower than
original → `accept`; Buddy MUST NOT offer paths A/B/C.

**Re-review:** max 2 → ESCALATE (foundation override on measurable
severity drop). Default = **single-reviewer pass-1.5** (same reviewer
reads fix; scope = `affected_scope`). Bundled (>5 clusters/files):
convergence-axis ~3 reviewers. F-AR pattern-class = pass-1.5 extended
scope. Full table: REFERENCE.md.

## 6. Discourse

L2: optional (Buddy). L1: none. Mechanic: `_protocols/discourse.md`.

## 7. Output paths

Agent reviews: `docs/reviews/code/{task-id}-{role}.md`.
Verdict: `docs/reviews/code/{task-id}-verdict.md`.

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
