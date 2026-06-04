# Workflow: build

Implement a feature or task. From intent to done.

**This file is the human narrative** (when / why / path-shape). The
**operative per-step detail is the runtime surface**: each step's
`instruction:` in `workflows/runbooks/build/workflow.yaml`, which the engine
prints at `--next`. WORKFLOW.md is not read by the engine — do not duplicate
the step instructions here.

**Forge-feed trigger (active throughout):** framework-relevant friction (failed
assumption, brief drift, tooling gap, agent-protocol weakness) → apply the
pre-write filter in `$FRAMEWORK_DIR/docs/dogfood-learnings/README.md`; if it
passes, append to `forge-feed.md` on notice (not at close).

## Trigger / NOT for

**Trigger:** user defines a feature/task; a spec is approved and ready; a
backlog task has clear scope.
**NOT for:** problem without a clear solution → **solve**; bug/incident →
**fix**; spec validation without implementation → **review**; research/spike →
**research**.

## Path determination

```
Nested in a parent build (locked spec, parent has remaining ACs)?            → SUB-BUILD
Spec at spec_ref locked from ANY source (parent closed, predecessor, manual,
  external) AND no spec amendment in scope AND implementation-only?           → STANDARD-IMPLEMENTATION-ONLY
Authority-only task (spec / ADR / plan, no code output)?                      → AUTHORITY-ONLY
ALL three? (a) ≤3 files (b) no spec (c) no new behaviour                      → DIRECT
At least ONE? (a) >1 subsystem (b) new subsystem (c) new pattern
  (d) schema change (e) >10 ACs                                              → FULL
Otherwise                                                                     → STANDARD
```

STANDARD-IMPLEMENTATION-ONLY sits above AUTHORITY-ONLY but below SUB-BUILD: it
disambiguates "spec locked, parent workflow no longer active" — which would
otherwise fall through to FULL/STANDARD and hit a Specify gate the engine
can't skip. Proportionality release-valve at the routing surface (CLAUDE.md
Inv 9).

**"No spec amendment in scope":** a locked authority (ADR, predecessor spec)
can mandate small directed spec-patches with no interview substance — these are
**sub-threshold** amendments (`_protocols/spec-amendment-discipline.md`: no
cross-ref cascade ≥3, no cross-spec coupling, no semantic change, single
edit-round). Buddy applies them direct (running the pre-edit grounding gate)
*before* the build, so the build sees a locked-and-amended spec and routes
STANDARD-IMPLEMENTATION-ONLY cleanly. Any **substantial** amendment (a
threshold clause fires) needs the Specify phase → route STANDARD. The
amendment threshold, not the presence of an edit, decides.

DIRECT is engine-skipped (Buddy inline). The other four routes are
eager-activated via `workflow_engine.py --start build --task <id> --route
<path>`. **Route step-sequences live in `workflow.yaml` `routes:` (runtime
SoT)** — not re-listed here. What each route skips:
- **SUB-BUILD** — skips Specify (parent owns spec) + Close (parent owns task status).
- **STANDARD-IMPLEMENTATION-ONLY** — skips Specify (spec locked at `spec_ref`);
  KEEPS Close (no active parent to inherit closing from).
- **AUTHORITY-ONLY** — skips Prepare/Execute/Verify (no code surface).

## Path discipline (why each path exists)

Each path is a discipline cluster, not a gate count — picking a path chooses
which failure-modes the workflow pays tax to prevent. Triggers are
**mechanical** (file count, spec presence, schema signal — see tree), so path
choice is not a judgment call. Once a trigger fires the cluster applies as a
unit; don't cherry-pick gates across paths. Skip a gate within a path via
`--skip <step-id> --reason "<why>"`.

| Path | Optimizes for | Failure-mode prevented |
|------|---------------|------------------------|
| **DIRECT** | speed on trivial work (review cost > defect risk) | over-process tax on typo/format/comment-only |
| **STANDARD** | normal quality bar, bounded ceremony (1 architect, 1 signoff, L1) | mid-size feature shipped without spec/test discipline |
| **FULL** | high-stakes, expensive-to-undo (3 architects, multi-mode brief, L2) | locking a load-bearing decision on a single perspective |
| **SUB-BUILD** | MCA-pass nested in an in-flight parent that owns the spec | re-authoring spec / re-closing task at sub-level |
| **STANDARD-IMPLEMENTATION-ONLY** | implementing a locked-from-any-source spec on an independent child task | falling through to FULL/STANDARD's required Specify gates |
| **AUTHORITY-ONLY** | spec/ADR/plan work producing NO code | running an MCA chain on a doc-only change |

## Named gates (standard route)

12 named gates. Phase-status transitions are engine-internal. Per-gate operative
detail + conditions = the step `instruction:` in `workflow.yaml`.

| # | Gate | Phase | Skill |
|---|------|-------|-------|
| 1 | interview | Specify | `frame/SKILL.md` (+ cross-spec-consistency-check sub-step) |
| 2 | spec-write | Specify | `spec_authoring/SKILL.md` (+ source-spec-reduce sub-step) |
| 3 | board | Specify | **classification** → `--route board-spec` (`spec_board`) or `board-council` (`council`, the ADR-007 spec-board substitute) |
| 4 | test-design | Prepare | `testing/SKILL.md` (+ `adversary_test_plan` + `test-skeleton-writer` on substantial dispatch) |
| 5 | architect-lens | Prepare | `agents/code-architect-lens.md` (preventive plan-time module lens; idle below scope-threshold) |
| 6 | brief-author | Prepare | `agents/brief-architect.md` (single or multi-mode; inline only if DIRECT-eligible) |
| 7 | brief-signoff | Prepare | user approval before MCA dispatch (DIRECT skips) |
| 8 | mca-implementation | Execute | `main-code-agent` (Plan → impl_plan_review cond. → Implement → L0) |
| 9 | code-review-board | Verify | `code_review_board/SKILL.md` (light / L1 / L2 per §1) |
| 10 | spec-drift-check | Verify | `spec_amendment_verification/SKILL.md` (when diff changes spec-defined behaviour) |
| 11 | close-bookkeeping | Close | **distill** `close_retro` (FULL / new-pattern-STANDARD; skip-eligible) → **emit** `documentation_and_adrs` + `task_creation` + `knowledge_processor` + `risk_followup_routing` (consume the retro; each skip-eligible) |
| 12 | commit-deploy | Close | engine + git pre-commit hooks |

`board` is a mid-flow classification: `--complete board --route
board-spec|board-council`. The amendment path (mid-build mechanism shift,
class rename, contract retraction on an EXISTING spec): if the substantial
threshold fires, Buddy dispatches `brief-architect mode=spec_amendment` rather
than authoring inline; sub-threshold edits stay Buddy-direct.

## Phase intent (one line each)

- **Specify** — what behaviour does this add (interview → spec → board)?
- **Prepare** — what do we test, how do we hand off (test-design → delegation)?
- **Execute** — implement the change (MCA writes code, runs L0).
- **Verify** — does the code do what the spec said (review → spec-drift)?
- **Close** — distill→emit bookkeeping + commit (`close_retro` distill → ADR + risk + knowledge → commit).

## Conditional sub-flows folded into named gates

Several earlier-version named steps are now sub-steps; the condition is
mechanical and lives in the parent gate's `instruction:`:
- **cross-spec-consistency-check** → interview (frame step 4 source-grounding).
- **source-spec-reduce** → final sub-step of spec-write.
- **adversary-test-plan + test-skeleton-write** → optional adversary mode of test-design.
- **close_retro distill + adr-check + risk-followup-routing + knowledge-process** → close-bookkeeping (distill→emit).
- **spec-amendment-verify + spec-co-evolve-check** → one spec-drift-check.

**Coverage rule (post-build):** reviewers verify the pre-build test plan was
honored (every planned TC in `tests/` and green); they do NOT re-design
coverage. Test-coverage findings are `code-spec-fit`'s sole lens; imagined
edge-case TCs without an AC or known bug-class are out-of-scope.

## Conditional evaluations the user actually faces

≤5 explicit yes/no on a typical standard build:
1. Path: STANDARD / FULL / SUB-BUILD / AUTHORITY-ONLY / DIRECT?
2. Spec already exists? (Specify skip vs run)
3. Adversary test mode? (substantial dispatch?)
4. Code review L1 vs L2?
5. ADR write? (decision meets the triple?)

## References

| Step | Detail SoT |
|------|------------|
| Interview / spec | `skills/frame/SKILL.md`, `skills/spec_authoring/SKILL.md`, `framework/spec-engineering.md` |
| Spec board | `skills/spec_board/SKILL.md` |
| Test design | `skills/testing/SKILL.md`, `skills/adversary_test_plan/SKILL.md` |
| MCA brief / execute | `skills/_protocols/mca-brief-template.md`, `agents/main-code-agent.md` |
| Code review | `skills/code_review_board/SKILL.md` |
| Close | `skills/documentation_and_adrs/SKILL.md`, `skills/knowledge_processor/SKILL.md` |
| Engine CLI + routing + skip-list | `framework/workflow-engine-cookbook.md` |

## Workflow-engine integration

Tracked by `scripts/workflow_engine.py` when engine-driven (some lifecycle/ad-hoc
runs skip-eligible — see the cookbook). State in `.workflow-state/<id>.json`
(SoT for the step pointer; cross-session-recoverable). **Buddy-driven
`[WORKFLOW]`** — advances only on `--complete`, a discipline-run state-tracker,
not an autonomous runtime (ADR-007 O-4, affirming ADR-004: no force-gate). The
generic `--start / --next / --complete / --skip / --retry` cycle, path routing,
`on_fail` policy, extension API, and multi-machine constraint are identical
across runbooks and live in `framework/workflow-engine-cookbook.md`. Operational
invariant: `agents/buddy/operational.md` §Workflow engine.
