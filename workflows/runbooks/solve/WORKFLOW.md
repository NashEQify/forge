# Workflow: solve

Problem-driven workflow. Starts from a **problem** (not a feature /
bug / spec / question) and ends with a **reproducible solution
artefact**. For cases where the form of the solution itself is part
of what has to be figured out.

## Trigger / NOT for

**Trigger:** "solve: [problem]", unclear problem with no clear
workflow allocation, meta-problems (new processes, structural
questions, methodology decisions).

**NOT for:** clear features → build, clear bugs → fix, spec
validation → review, knowledge questions → research, objective with a
foreseeable L0–L3 hierarchy → scoping.

**solve vs. scoping:** solve = solution form still open (spec?
runbook? code? process?). scoping = done criterion stands; only the
spec hierarchy is missing. On uncertainty: run frame mode quick first
and then route.

## Path determination

Single path: every solve traverses all 7 named gates. Depth scales
over the frame modes (quick / focused / deep) inside the
`frame-report` gate. For "directed" runs where the user already has
the problem + direction defined, Buddy can short-circuit through
`refine` (one-line approach) and move on.

## Named gates

The solve workflow has **7 named gates**. Phase-status transitions
are engine-internal.

| # | Gate | Skill | Conditional |
|---|------|-------|-------------|
| 1 | frame-report | `frame/SKILL.md` (8 sub-steps) | depth: quick / focused / deep |
| 2 | refine | — (user dialog + optional council + refinement notes) | council: only if >1 path AND hard-to-reverse |
| 3 | write-artifact | `spec_authoring/SKILL.md` or build sub-workflow (with registration plan as inline sub-step) | artefact type drives skill choice |
| 4 | validate | classify → board → convergence → delta-verify (per artifact_class) | board: spec_board / code_review_board / impl_plan_review / spec_board(mode=ux) per artifact_class |
| 5 | apply-artifact | direct / handoff to build / handoff to docs-rewrite / self-apply | per `framework/agent-autonomy.md` |
| 6 | close-bookkeeping | `documentation_and_adrs/SKILL.md` + `knowledge_processor/SKILL.md` | each sub-check (ADR, knowledge processor) skip-eligible |
| 7 | commit-deploy | git pre-commit hooks | — |

## State file

One state file per solve invocation: `docs/solve/YYYY-MM-DD-<slug>.md`
with YAML frontmatter (`phase`, `status`, `artefacts`). After every
phase: append `## Phase N — <name>` body section + `git add + commit`.

Phase-status updates (engine-internal): `phase-frame → phase-refine →
phase-artifact → phase-validate → phase-execute`. The state file
frontmatter mirrors the engine state; on drift, re-derive from the
engine.

## Detail per gate

**1. frame-report** — `frame/SKILL.md` 8 sub-steps: reformulate,
plan + review, first-principles, repo-check, constraints, SOTA,
solution-space, evaluate + recommend. Result is a connected frame
report in the state file.

**2. refine** — three sub-steps:
(a) **user dialog** — present frame report, discuss recommendation,
sharpen direction (purely dialogic);
(b) **council** — invoke ONLY if >1 path AND hard-to-reverse. Output
under `docs/reviews/council/`. Skip with one-line rationale otherwise;
(c) **refinement notes** — chosen approach, rationale, open points
as a "Phase 2" section in the state file.

**3. write-artifact** — create the artefact (spec / workflow /
protocol / code plan). Self-contained, within piebald budget. Inline
sub-step: write a "Registration" section explaining how the artefact
lands in process-map / STRUCTURE.md / handoff fields.

**4. validate** — internal sub-flow:
(a) classify the artefact (Pattern 7 reader-facing-surface
detection — code / spec / impl-plan / ui-spec / reader-facing-doc);
(b) dispatch the routed board (`spec_board` / `code_review_board` /
`impl_plan_review` / `spec_board(mode=ux)`);
(c) Buddy reads ONLY the chief signal (CLAUDE.md §1);
(d) post-convergence + post-pass checklists per `spec_board` §3, §6;
(e) on NEEDS-WORK: convergence_loop max 3 passes;
(f) delta-verify on PASS when triggered (≥10 normative lines OR ≥3
files OR ≥1 MAJOR fixed OR meta-critical change);
(g) update task-YAML `board_result` + `readiness` via
`task_status_update`.

**5. apply-artifact** — variants per `framework/agent-autonomy.md`:
direct (process-map register + stale cleanup + deploy), handoff to
build (spec/plan → build workflow), handoff to docs-rewrite,
self-apply.

**6. close-bookkeeping** — two skip-eligible sub-checks:
(a) ADR-discipline triple — solve hits this trigger more often than
build (open-solution shape → real trade-off decisions);
(b) `knowledge_processor` wrap-up — history entry with
frame-report-ref + IMPACT CHAIN under `context/history/`.

**7. commit-deploy** — `git commit + push` + dashboard deploy. Engine
auto-advances `workflow_phase=done`; task-level `status=done` is set
unconditionally on standard route (solve closes its own task by
definition).

## References

| Topic | Detail SoT |
|-------|------------|
| Frame | `skills/frame/SKILL.md` |
| Spec authoring | `skills/spec_authoring/SKILL.md` |
| Spec board | `skills/spec_board/SKILL.md` |
| Code review board | `skills/code_review_board/SKILL.md` |
| Impl plan review | `skills/impl_plan_review/SKILL.md` |
| Knowledge processor | `skills/knowledge_processor/SKILL.md` |
| Council template | `workflows/templates/council.yaml` |
| Workflow engine CLI | `framework/workflow-engine-cookbook.md` |
