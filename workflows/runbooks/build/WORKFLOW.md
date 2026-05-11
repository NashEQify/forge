# Workflow: build

Implement a feature or task. From intent to done.

## Trigger

- The user defines a feature / task to implement.
- A spec is approved and ready for implementation.
- A task is in the backlog with a clear scope.

## NOT for

- A problem without a clear solution → **solve**.
- Bug / incident → **fix**.
- Spec validation without implementation → **review**.
- Research / spike → **research**.

## Path determination

```
Nested in a parent build (existing locked spec, parent has remaining ACs)? → SUB-BUILD
Authority-only task (spec / ADR / plan without code output)?              → AUTHORITY-ONLY
ALL three? (a) ≤3 files (b) no spec (c) no new behaviour                  → DIRECT
At least ONE? (a) >1 subsystem (b) new subsystem (c) new pattern
  (d) schema change (e) >10 ACs                                            → FULL
Otherwise                                                                 → STANDARD
```

DIRECT is engine-skipped (Buddy handles inline). The other four routes
are eager-activated via `workflow_engine.py --start build --task <id>
--route <path>`.

## Path discipline (why each path exists)

Each path is a discipline cluster, not a gate count. Picking a path
chooses which failure-modes the workflow is paying tax to prevent.

| Path | Optimizes for | Tolerates | Failure-mode prevented |
|------|---------------|-----------|------------------------|
| **DIRECT** | speed on trivial work where review cost > defect risk | no test-first, no review, single-reviewer L0 | over-process tax on typo / format / comment-only changes |
| **STANDARD** | normal-case quality bar with bounded ceremony | one architect, one signoff, L1 review by default | mid-size feature work shipped without spec or test discipline |
| **FULL** | high-stakes work where wrong implementation is expensive to undo | three parallel architects, multi-mode brief synthesis, L2 board, full close-bookkeeping | locking a load-bearing decision on a single perspective |
| **SUB-BUILD** | nesting an MCA-pass inside an in-flight parent build that owns the spec | skips Specify (parent owns it) and Close bookkeeping (parent owns task status) | re-authoring the spec or re-closing the task at sub-level |
| **AUTHORITY-ONLY** | spec / ADR / plan-authority work that produces NO code | skips Prepare/Execute/Verify (no implementation surface) | running an MCA-dispatch chain on a doc-only change |

The **path triggers are mechanical** (count of files, presence of spec,
schema-change signal, etc. — see decision tree above) **so the path
choice is not a judgment call**. Once the trigger fires, the path's
discipline cluster applies as a unit; do not cherry-pick gates across
paths. To skip a gate within an active path: `--skip <step-id>
--reason "<why>"` per `framework/workflow-engine-cookbook.md`.

## Named gates (standard route)

The build workflow has **11 named gates**. Phase-status transitions
are engine-internal and do not appear here.

| # | Gate | Phase | Skill | Conditional |
|---|------|-------|-------|-------------|
| 1 | interview | Specify | `frame/SKILL.md` (with cross-spec-consistency-check as sub-step) | — |
| 2 | spec-write | Specify | `spec_authoring/SKILL.md` (with source-spec-reduce as final sub-step) | — |
| 3 | board | Specify | `spec_board/SKILL.md` (Standard or Deep) | — |
| 4 | test-design | Prepare | `testing/SKILL.md` (+ `adversary_test_plan` + `test-skeleton-writer` on substantial dispatch) | adversary mode: ≥3 ACs OR schema change OR cross-module OR sub-build |
| 5 | brief-author | Prepare | `agents/brief-architect.md` (single OR multi-mode per spec 306 §4.2) | DIRECT path: Buddy-inline; STANDARD/FULL with §4.1 trigger fired: architect dispatched; AUTHORITY-ONLY: skipped via `skip_when` |
| 6 | brief-signoff | Prepare | gate (user approval) per spec 306 §4.4 | mirrors upstream Plan Mode Step 4; user approves before MCA dispatch (DIRECT path skips) |
| 7 | mca-implementation | Execute | `main-code-agent` inline (Plan + impl_plan_review + Implement + L0) | impl_plan_review: ≥3 ACs OR schema change OR cross-module |
| 8 | code-review-board | Verify | `code_review_board/SKILL.md` (light / L1 / L2 per §1) | level: light on ≤2 files mechanical-trigger / L1 ≤5 files / L2 otherwise |
| 9 | spec-drift-check | Verify | `spec_amendment_verification/SKILL.md` | when MCA's diff changes spec-defined behaviour OR an authority log exists with new spec edits |
| 10 | close-bookkeeping | Close | `documentation_and_adrs/SKILL.md` + `task_creation/SKILL.md` + `knowledge_processor/SKILL.md` + `risk_followup_routing/SKILL.md` (per spec 306 §4.7) | each sub-check skip-eligible with one-line rationale |
| 11 | commit-deploy | Close | engine + git pre-commit hooks | — |

### Sub-build route

Sub-build skips Specify entirely (parent owns the spec) and Close
bookkeeping at the workflow level (parent's commit-deploy closes
the task). 9 gates: `phase-prepare → test-design → brief-author →
brief-signoff → phase-execute → mca-implementation → phase-verify
→ code-review-board → spec-drift-check`.

### Authority-only route

For spec / ADR / plan-authority work without code implementation. 5
gates: `phase-specify → interview → spec-write → board →
phase-close → close-bookkeeping → commit-deploy`.

## Phase intent (one sentence per phase)

- **Specify** — what behaviour does this task add (interview → spec → board)?
- **Prepare** — what do we test, how do we hand off (test-design → delegation)?
- **Execute** — implement the change (MCA writes code, runs L0).
- **Verify** — does the code do what the spec said (code-review-board → spec-drift-check)?
- **Close** — bookkeeping + commit (ADR + risk follow-up + knowledge process → commit).

## Conditional sub-flows folded into named gates

Several earlier-version named steps are now sub-steps of a parent gate;
the condition is mechanical and lives in the parent gate's instruction:

- **cross-spec-consistency-check** → frame step 4 (source-grounding).
  High-severity conflict resolution before interview proceeds.
- **source-spec-reduce** → final sub-step of spec-write.
- **adversary-test-plan + test-skeleton-write** → optional adversary mode
  of test-design.
- **adr-check + risk-followup-routing + knowledge-process** → close-bookkeeping.
- **spec-amendment-verify + spec-co-evolve-check** → merged into one
  spec-drift-check.

## Detail per gate

### Specify phase

**1. interview** — open the solution space via `frame/SKILL.md`
(8 sub-steps, standard mode). Pre-interview source-grounding catches
cross-spec conflicts in the spec consumed-list; high-severity
conflicts must be resolved before the interview proceeds.
**Deep-mode trigger** (all 4): foundation spec + cross-layer impact +
new subsystem + schema change → frame deep mode (with `bedrock_drill`).

**2. spec-write** — 6 required elements (`spec-engineering.md` §Spec).
On external library APIs: `get_api_docs` BEFORE AC formulation.
Source-spec-reduce as a final sub-step when a NEW spec overlays an
existing one (3-way triage → patches + drift-items.yaml).

**Amendment path (per spec 306 §14):** when this gate operates on
an EXISTING spec (mid-build mechanism shift, class rename, contract
retraction surfaced after spec-lock) and the substantial-amendment
threshold per spec 306 §14.2 fires (cross-ref cascade ≥3 OR
cross-spec coupling OR class-rename / mechanism-shift /
contract-retraction OR Buddy-heuristic "more than 1 edit-round
anticipated"), Buddy dispatches `brief-architect mode=spec_amendment`
via Agent tool rather than authoring inline. The architect explores
the relevant spec corpus + source code freely, returns amendment
prose + cross-ref edit-list + spec_version bump suggestion +
§Changelog entry inline; Buddy integrates the prose into the
spec(s) and dispatches `spec_amendment_verification` for cross-spec
coherence. Sub-threshold amendments (1-line correction, typo,
§Changelog-only append) stay Buddy-direct.

**3. board** — `spec_board/SKILL.md` Standard or Deep mode.
Convergence_loop (max 3 passes). PASS = 0C+0H. Output:
`docs/reviews/board/{spec_name}-consolidated*.md`.

### Prepare phase

**4. test-design** — `testing/SKILL.md` §Design produces TC plan v1.
On substantial dispatch (≥3 ACs OR schema change OR cross-module OR
sub-build): adversary augmentation via `adversary_test_plan` (extends
plan v1 with edge-case TCs targeting implementer cognitive bias)
followed by `test-skeleton-writer` (writes RED skeletons, context-
isolated). All RED tests MUST FAIL via pytest before MCA dispatch.
Below threshold: skip with one-line rationale.

**5. brief-author** — On STANDARD/FULL paths with §4.1 trigger
fired (per spec 306 §4.1 — seven mechanically-evaluable triggers
including "multiple valid approaches", "architectural decisions",
"multi-file changes >2-3 files"): dispatch `agents/brief-architect.md`
via Agent tool (single mode `perspective: generalist`; multi-mode
on §4.2 escalation: three parallel dispatches with `pattern` /
`integration` / `scope` perspectives in one tool message). Architect
authors the MCA delegation brief end-to-end in fresh context per
spec 306 §3.1 (read-only via `disallowedTools`). DIRECT path
(≤3 files, no spec, no new behaviour): Buddy authors brief inline
as today. AUTHORITY-ONLY: skipped (no MCA boundary).

**6. brief-signoff** — Mirrors upstream Plan Mode Step 4. Multi-
mode: Buddy synthesizes the candidate briefs first per spec 306
§6 (Buddy is the synthesizer per upstream `coordinatorMode.ts` §5
— "Always synthesize — your most important job"; not delegated to
a separate agent). Single-mode: brief is the architect's direct
output. Then in BOTH modes (STANDARD / FULL): Buddy presents the
brief to user for approval before MCA dispatch (in multi-mode also
surfaces the §Divergence Rationale block). User approval required;
on `escalate: <reason>` from architect, no MCA dispatch until
escalation is resolved (council / file follow-up / amend spec /
pull in-scope). DIRECT path skips this gate.

**(legacy 5. delegation-artefact)** — MCA brief with board findings,
test-plan-ref, spec-ref, and on substantial dispatch the required
`## Implicit-Decisions-Surfaced` section with 4 standard classes
(`schema_and_contract`, `error_and_stop`, `layer_discipline`,
`structural_invariants`). Pre-dispatch hook check
`delegation-prompt-quality.sh` Check C verifies presence.
Template SoT: `skills/_protocols/mca-brief-template.md`.

### Execute phase

**6. mca-implementation** — `main-code-agent` inline.
Plan → impl_plan_review (conditional: ≥3 ACs OR schema change OR
cross-module impact) → Implement → L0 (`ruff check` + `mypy` on
touched files only).

### Verify phase

**7. code-review-board** — `code_review_board/SKILL.md`.
L1 ≤5 files / L2 otherwise (L2 also on new module, cross-spec,
schema change, or doubt). Output: `docs/reviews/code/{spec_name}-verdict.md`.

**8. spec-drift-check** — implementation-decision drift to spec body
(Cypher templates, state machines, schemas, interface contracts):
did MCA's diff change behaviour defined in a spec? Yes → spec patch
in the SAME block-commit, then re-verify with
`spec_amendment_verification`.

### Close phase

**9. close-bookkeeping** — three skip-eligible sub-checks:
(a) ADR-discipline triple (hard-to-reverse + surprising-without-
context + result-of-real-trade-off → write ADR);
(b) risk follow-up (file ONE follow-up task per non-empty
`remaining_findings:` block in verdict files);
(c) knowledge-process (`knowledge_processor mode=process`).

**10. commit-deploy** — git commit (pre-commit hooks run), git push,
optional dashboard deploy. Engine auto-advances `workflow_phase=done`
when this step completes; task-level `status=done` is conditional on
whether the workflow closes the whole task (skip on sub-build —
parent owns task status).

## Conditional evaluations the user actually faces

Conditions are documented mechanically in each gate's instruction; the
user faces ≤5 explicit yes/no questions on a typical standard build:

1. Path: STANDARD / FULL / SUB-BUILD / AUTHORITY-ONLY / DIRECT?
2. Spec already exists? (Specify phase skip vs run)
3. Adversary test mode? (substantial dispatch?)
4. Code review L1 vs L2?
5. ADR write? (does the decision meet the triple?)

## References

| Step | Detail SoT |
|------|------------|
| Interview | `skills/frame/SKILL.md`, `framework/spec-authoring.md` |
| Spec write | `skills/spec_authoring/SKILL.md`, `framework/spec-engineering.md` |
| Spec board | `skills/spec_board/SKILL.md` |
| API docs lookup | `skills/get_api_docs/SKILL.md` |
| Test design (with adversary) | `skills/testing/SKILL.md`, `skills/adversary_test_plan/SKILL.md` |
| MCA brief | `skills/_protocols/mca-brief-template.md` |
| MCA execute | `agents/main-code-agent.md` |
| Code review | `skills/code_review_board/SKILL.md` |
| Spec drift | `skills/spec_amendment_verification/SKILL.md` |
| Close bookkeeping | `skills/documentation_and_adrs/SKILL.md`, `skills/task_creation/SKILL.md`, `skills/knowledge_processor/SKILL.md` |
| Workflow engine CLI | `framework/workflow-engine-cookbook.md` |
