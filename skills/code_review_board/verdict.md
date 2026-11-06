# Code review board — verdict and re-review

Step-loaded unit of `skills/code_review_board/SKILL.md`. Read it when reviewer returns are in and a verdict is
consolidated or decided, and before dispatching a multi-reviewer re-review. Section numbers are skill-wide: §1 and §6–§10 in `SKILL.md`, §2–§3 in `brief-and-team.md`, §4–§4a in
`checklist-and-dispatch.md`, §5–§5a in `verdict.md`, §11 in `review-package.md`.

## 5. Verdict

**Reality first, then disposition.** At L2 the chief first applies the
recall-biased keep/refute triage (KEEP / REFUTED) per
`agents/code-chief.md` §CHIEF-1 step 3 — REFUTED removes only on
existing reviewer-surface evidence, never the chief's own re-reading; a
KEPT finding carries the reviewer's own trigger-certainty verbatim (the
chief authors no confidence rating). Then each KEPT finding is verified
at its cited location, which sets its grade
(`skills/_protocols/finding-verification.md`); the severity-verdict and
disposition-triage RULES below operate on the verified grades. Recall-bias deliberately keeps that population larger than a
precision filter would, so more real-but-uncertain findings reach
disposition (the intended effect) — each then dispositioned normally (a
narrow latent HIGH still → `accept`). Keep-or-refute and verification
are upstream of disposition (fix-now / accept / watch / fix-later):
triaged once, verified once, then dispositioned once.

**Before adopting the verdict**, qualify the current reports of the final
applicable review under `evidence-pointer-schema.md` §9. Buddy's decision uses PASS / PASS_WITH_RISKS / FAIL / PARTIAL;
light/reproduction PARTIAL stays incomplete environmental evidence and cannot
satisfy `code_success`. Check before review-derived writes: PASS → APPROVED,
PASS_WITH_RISKS → APPROVED_WITH_RISKS (existing alias allowed), FAIL → REJECTED,
PARTIAL → null. Only success permits forward readiness under existing risk rules.
Refusal/error leaves requested fields unchanged. Buddy also applies the decision-grounding
C-VERIFY (`agents/buddy/architecture-comprehension.md` §B):
for the pivotal code claims the verdict rests on, re-execute any not
already independently re-executed by a non-asserter lens (a present
pointer ≠ verified); SILENT rendered loud; FALSIFIED → re-frame, don't
adopt.

```
PASS:            0C + 0H
PASS_WITH_RISKS: 0C + ≤2H (carry-forward MANDATORY), no open finding the Mechanism-cell floor blocks
FAIL:            ≥1C or >2H, or an open finding the Mechanism-cell floor below blocks
                 → triage → MCA fixes fix-now → re-review (max 2)
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
- `absorb_next` — kept in the verdict, next file-touch closes
- `closes_with: <id>` — duplicate / convergence to another fix
- `re_review: <reviewer>` — scoped specialist re-look

Empty `target:` = validation fail. All same `target:` = missed
triage anti-pattern. `risk-followup-routing` files new_tasks
mechanically.

**Proportionality triage (NON-NEGOTIABLE on FAIL):**

| Disposition | Criterion |
|---|---|
| **fix-now** | blocks requirement OR reproduces reported defect; every CRITICAL and the safety floors below. MEDIUM/LOW reproducing defect = fix-now. HIGH narrow latent = `accept` unless a safety floor applies |
| **accept** | non-blocking AND (narrow+backstopped OR latent OR self-introduced narrower than original). DEFAULT non-blocking |
| **watch** | `accept` + named future trigger |
| **fix-later** | MEDIUM+ only. Named concrete defect + measurable downstream cost. LOW FORBIDDEN |

**Cause before the fix brief.** Every fix-now finding, and every blocking
one the pass leaves, gets its cause and answer first, every review
(`skills/convergence_loop/cause-before-answer.md`; fix brief Section 5): a
wrong finding leaves with a ruling, an intent one as a question to the
caller; a spec-caused one goes to the spec in this pass.

**Pre-existing defects.** A finding about behavior this change neither
introduced nor exposed (its observable outcome reproduces on the pre-change
baseline through the same entry point, and it is not the reported defect) does not block this change: `accept` with the limit
recorded in the verdict, `watch`, or `new_task` under the value floor. An
acceptance criterion about what the fix or change does binds this change,
not prior state; it is in scope only when its observable outcome fails now.
A pre-existing CRITICAL or safety-floor defect goes to the user as a scope
decision, not into this fix pass.

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
- **Vision-named-surface carve-out (observable, not posture):** a
  surface the active `intent.md` Vision names as a product deliverable,
  or a consumer the Vision / plan names, IS a **named consumer even at
  zero built instances** — "not built yet" is not "no consumer." Do NOT
  re-route to `accept` on no-consumer grounds for a Vision-named product
  surface; on a platform / middleware the consumable surface IS the
  deliverable and zero-built-consumers is the normal pre-launch state.
  Decided by reading the Vision (observable), not by judging intent.
  On a mechanism, "no consumer yet" only places the work in its
  caller's task (`_protocols/mechanism-model.md` §Scope and placement,
  rule 4 — the one home of the rule).

`new_task` without operational-impact sentence = validation fail.
Hard floors override: CRITICAL, security/auth/consent/crypto, schema
/ public-API contract, full-path tasks stay `fix-now` / `new_task`.

**Mechanism-cell floor (blocking severities only):** a CRITICAL / HIGH
finding, or one that falsifies a stated invariant dangerously
(`_protocols/finding-verification.md` step 4), on a `now` cell of a
`§Mechanism-Lifecycle` matrix is `fix-now` or goes to the
Simplify-before-patch gate — never `new_task`, `accept`, `watch_item` or
`absorb_next`. An open live cell at blocking severity makes the verdict
FAIL (with the gate record), not PASS_WITH_RISKS. MEDIUM / LOW on a live
cell follow the triage above, with the cell annotated in the matrix (`✗ accepted: <reason>`
or `→ task-N` plus the `blocked_by` edge). Cells placed in another task
or beyond the MVP leave as `blocked_by` edges (beyond-MVP: the plan /
milestone entry), not `remaining_findings` rows. Rule and placement: `_protocols/mechanism-model.md` §Scope and
placement, §Bind rules — parking an invariant's open blocking routes on
the next producer's task was the recurring way one mechanism stayed
defective across tasks.

**Bundling content-split:** bundled items tagged
`value_class: real-impact | nice-to-have`. Preserve each reviewer's
provenance when merging duplicate evidence. Agreement can strengthen
confidence; reviewer count alone changes neither severity nor disposition.
Apply the same impact criteria to solo and convergent findings.

**Test-coverage findings = the L2 coverage owner** (`code-spec-fit` with a
spec_ref, else `code-domain-logic` working the §3 checklist; L1: the §3
checklist's AC-coverage item). Coverage
findings name (a) concrete failure-mode missing tests catch, (b) why
existing test surface (integration, indirect, contract-pinning)
doesn't catch it, (c) smallest test set that closes gap. "Coverage at
integration level" = valid `accept`.

**Process discipline:** no "leanest fix" for non-fix-now (`accept`
= closed); self-introduced narrower than original → `accept`; Buddy
MUST NOT offer paths A/B/C.

**Re-review:** max 2, counted per mechanism across review
owners, workflows and tasks (`skills/convergence_loop/simplify-before-patch.md`
§Simplify-before-patch gate, Counting), then
`skills/convergence_loop/at-the-cap.md` §At the cap. Default: §4 re-verify
(light if line-local, else light + scoped adversary).
Without a reproduction: single-reviewer
pass-1.5 (scope = `affected_scope`); bundled (>5 clusters/files),
replaced mechanism, other multi-reviewer → §5a.
Full table: REFERENCE.md.

## 5a. Re-review two-phase (multi-reviewer re-reviews)

The default re-review is the §4 re-verify table; its scoped adversary
and replaced-mechanism cases use this section's two-phase. Before the fix pass that precedes a pass-2+ re-review,
the §4 Simplify-before-patch gate runs; a recurring class is answered by
a simpler mechanism or invariant, not by another route patch.

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
Second exception: the reproduction re-run of the §4 re-verify (one
`code-verification`) is mechanical red→green evidence per finding, so it
needs no two-phase. The scoped adversary and the replaced-mechanism
re-verify follow the two-phase, with every subsumed prior finding's
reproduction re-run in the Phase-2 table.

**Phase 1 — cold-derive (60-70%):** diff + scope + persona + spec
(locked) + code paths. FORBIDDEN: prior board findings / brief
rationale / chief verdict / lens framing. Output: findings on
as-coded state per §4a code-quote; closure-claims carry 4-link chain
per `_protocols/mca-brief-template-verification.md` §Reviewer Checkpoints.

**Phase 2 — reconcile (30-40%):** prior findings as appendix.
Output: table — prior finding | addressed? | evidence | correct fix?
| new shape (smell-transfer +1/+2).

Chief: Phase-1 = primary evidence, Phase-2 = closure-verification.
`remaining_findings` = Phase-1 minus prior-cycle-confirmed-closed.

**Fix-completeness C-VERIFY (extends verdict-adoption C-VERIFY to the
fix-pass's OWN claims):** a fix-pass introduces NEW load-bearing claims
("I closed it on shutdown") the original C-VERIFY never covered. When a
fix-claim names a third-party teardown / lifecycle API (`close` /
`aclose` / `shutdown` / `__aexit__`), the claim is NOT "addressed"
until the **installed** SDK surface is shell-verified (e.g. `python3 -c
"import openai; print(hasattr(openai.AsyncOpenAI,'close'),
hasattr(openai.AsyncOpenAI,'aclose'))"`) — not the remembered API.
Observed: a `_close_client_quietly` resolved only `aclose`, absent on
the installed openai 2.41.1 → `close()` a silent no-op, the pooled
transport leaked at every drain. A "wired-but-ineffective" fix passes
the Phase-2 "addressed?" column until the installed surface is checked
(`evidence-author-claims.md` §8.3, re-review layer).
