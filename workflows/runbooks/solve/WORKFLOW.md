# Workflow: solve

Problem-driven workflow. Starts from a **problem** (not a feature /
bug / spec / question) and ends with a **reproducible solution
artefact**. For cases where the form of the solution itself is part
of what has to be figured out.

**Forge-feed trigger (active throughout this workflow):** framework-
relevant friction → apply the pre-write filter in
`$FRAMEWORK_DIR/docs/dogfood-learnings/README.md`; if it passes, append to
`$FRAMEWORK_DIR/docs/dogfood-learnings/forge-feed.md` on notice. Not at close.

## Trigger / NOT for

**Trigger:** “Forge my idea” followed by the idea or problem, "solve: [problem]", unclear problem with no clear
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

The standard and full routes share one path through all 7 named gates. Depth scales
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
| 3 | write-artifact | `spec_authoring/SKILL.md` or build sub-workflow (with registration plan as inline sub-step) | select the exact artifact path |
| 4 | validate | choose the review method by artifact and consumer | apply the method's roster, decision owner and success policy |
| 5 | apply-artifact | direct / handoff to build / handoff to docs-rewrite / self-apply | fresh invocation evidence, agent-confirmed |
| 6 | close-bookkeeping | **distill** `close_retro` (skip-eligible) → **emit** `documentation_and_adrs/SKILL.md` + `knowledge_processor/SKILL.md` (consume the retro; each skip-eligible) |
| 7 | commit-deploy | git pre-commit hooks | — |

## State file

One state file per solve invocation: `docs/solve/YYYY-MM-DD-<slug>.md`
with YAML frontmatter (`phase`, `status`, `artefacts`). After every
phase: append `## Phase N — <name>` body section and persist the result.
Set `task_ref` to the attached task or to null. Use the original file from the first ordinary accepted Frame for all
dependent work and retries. If a path mismatches, use the original while
preserving history. Hold when that path cannot be established.
Phase commits follow `framework/process-map.md` section Authorization: commit
only under an applicable request or standing repository policy. Continue unchanged
authorized work without routine reapproval; a local phase does not authorize
push/deployment, and authorized missing publication remains an unresolved obligation.

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
under `docs/reviews/council/`. Record a one-line rationale otherwise.
Both entries reach dialogue and notes independently of the Council decision;
(c) **refinement notes** — record the chosen approach, rationale
and open points in the existing "Phase 2" section. Cite the applicable
project intent (or supplied standing intent for standalone work) and the
original local objective. Explain how the chosen approach serves both,
including a choice revised after Council. An unchanged approach still
supported by both sources may reference the grounded Frame. Record unresolved
conflicts or missing authority in open points and hold dependent artifact
writing (owner: framework/invariants.md §Intent-driven).

**3. write-artifact** — create the artefact (spec / workflow /
protocol / code plan). Keep essential guidance self-contained and conditional
detail reachable per `skills/_protocols/piebald-budget.md`. Inline
sub-step: write a "Registration" section explaining how the artefact
lands in process-map / STRUCTURE.md / handoff fields.

**4. validate** — select the review by the actual artifact and its consumer.

- For code, use `code_review_board` and `code_success`. For `spec` use
  Spec Board Standard. For `ui-spec` use Spec Board `mode=ux`. For
  `reader-facing-doc` use Spec Board `mode=ux` with `board-ux-ia` and
  `board-ux-heuristic`. Use `spec_success` for all three Spec Board classes.
  Capture the selected artifact on this exact Solve's `validate` step and
  adopt its current decision.
- For an architecture decision, run Council on the selected artifact and
  record the authorized decision maker's disposition. For an implementation
  plan, apply `impl_plan_review` after delegation and before coding when the
  actual plan, implementation task's spec and delegation exist and its trigger
  applies. Buddy reads the plan reviews directly and records `APPROVED`.
  Hold on missing prerequisites, `REVISE` or `REJECT` under that method.
- Keep the original reports and apply the routed method's ownership, roster
  and convergence rules. Complete with fresh evidence and its applicable
  proof. Council and implementation-plan decisions are operator-confirmed.
  See [decision fields](REFERENCE.md#validation-decision).
- Update review-derived readiness only for the actual bound task using its
  applicable current decision through `task_status_update`.

**5. apply-artifact** — variants per `framework/agent-autonomy.md`:
direct (process-map register + stale cleanup + authorized deployment), handoff to
build (spec/plan → build workflow), handoff to docs-rewrite,
self-apply. Complete with `--complete apply-artifact --id WORKFLOW` and
fresh `--evidence TEXT` recording the current validated artifact and version.
For a handoff, include the receiving owner, its acknowledgment and the next
authorized action. For direct execution, record the observed outcome. The
manual completion is agent-confirmed. Task-dependent execution starts once
an applicable real task exists.

**6. close-bookkeeping** — distill → emit. **Distill:** `close_retro`
(skill `skills/close_retro/SKILL.md`, spec 374) fires on a decision-heavy /
new-pattern solve (else skip with a one-liner) → read-only `close-retro`
agent on the frame report + verdict + ACs → retro 1-pager at
`docs/solve/<slug>-retro.md`. **Emit** (consume the retro when present, else
current behaviour):
(a) ADR-discipline triple ← §Stale-Decisions — solve hits this trigger more
often than build (open-solution shape → real trade-off decisions);
(b) `knowledge_processor` wrap-up ← §Patterns-Emerged — history entry with
frame-report-ref + IMPACT CHAIN under `context/history/` (this is the gate's
completion artifact; the retro does not satisfy it);
(c) §Framework-Feed — forge-feed entries (replaces the old workflow-retro
safety net; on skip, reverts to capture-now of missed entries).

**7. commit-deploy** — apply `framework/process-map.md` section Authorization:
commit, push and dashboard deploy only when the respective action is authorized.
Close the state file checked in Frame with `phase: done` and `status: done`.
For a bound run, close its actual task via `task_status_update`. Complete
the exact Solve with fresh evidence of current local persistence and any
applicable authorized outcomes. The engine checks the terminal record and
the bound task's done status. Retain a missing authorized outcome as an
open obligation.

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

## Workflow-Engine Integration

This runbook is tracked by `scripts/workflow_engine.py` when engine-driven
(some lifecycle / ad-hoc runs are skip-eligible — see the cookbook's *Skip
allowed for* list). The engine holds step state in `.workflow-state/<id>.json`
(SoT for the step pointer; persistent + cross-session-recoverable) and is
**Buddy-driven `[WORKFLOW]`** — it advances only when Buddy drives
`--complete`, a discipline-run state-tracker, not an autonomous runtime
(ADR-007 O-4, affirming ADR-004: no force-gate).

Generic cycle (identical across every workflow):

```bash
python3 $FRAMEWORK_DIR/scripts/workflow_engine.py --start solve --task <id> [--route <path>]
python3 $FRAMEWORK_DIR/scripts/workflow_engine.py --start solve --set state_file docs/solve/<date-slug>.md  # taskless
python3 $FRAMEWORK_DIR/scripts/workflow_engine.py --next                       # current step + instruction
python3 $FRAMEWORK_DIR/scripts/workflow_engine.py --complete <step> --evidence "<short>"
#   classification step (mid-flow route): --complete <step> --route <key>
#   skip-eligible step: --skip <step> --reason "<why>"   ·   re-run: --retry <step> --reason "<why>"
#   >=2 workflows live? add --id <wf> (from --next `ID:`) — engine refuses keyless (exit 5)
```

`on_fail` per step: `block` (fix + retry), `warn` (`--complete --force` + reason),
`skip` (auto `warn_skipped`), `escalate` (pauses, user decision). Cross-session
resume surfaces active workflows at session start (`--boot-context`).

Full CLI + path-routing + extension API (`--guard` / `--handoff-context`) +
multi-machine constraint + skip-eligible list:
`framework/workflow-engine-cookbook.md`. Operational invariant:
`agents/buddy/operational.md` §Workflow engine.


### Observational workflow checks

Navigation/recovery never execute commands. Use existing authorized tools for
actions and observe their actual current outcome. The manual action checkpoints
require nonblank evidence supplied with the current `--complete --evidence`
invocation, including force. Missing/failed/timed-out/unknown outcomes stay open
with the concrete blocker; no-new-commit save still requires current persistence
observations for applicable project/user roots and required remotes. Completion
is agent-confirmed, never engine proof of free-text truth or remote correctness.
See `framework/workflow-engine-cookbook.md` for the retained completion contract.
