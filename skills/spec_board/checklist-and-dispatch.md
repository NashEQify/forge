# Spec board — Buddy checklist, cross-task ACs and mechanism cells

Step-loaded unit of `skills/spec_board/SKILL.md`. Read it when assembling prompts and dispatching reviewers, when the
spec carries cross-subsystem ACs or a `§Mechanism-Lifecycle` section in scope, and before a fix pass. Section numbers
are skill-wide: §0, §3, §5 and §7–§10 in `SKILL.md`, §1–§2 in `depth-and-team.md`, §4–§4b in
`checklist-and-dispatch.md`, §3a and §6–§6a in `post-pass.md`.

## 4. Buddy checklist (dispatch)

1. Spec path + output paths.
2. Operating mode (review or synthesize).
3. Depth mode: §1.0 first (MANDATORY), then §1.1.
4. Foundation flag check (→ chief receives DR scorecard).
5. **Engine context** (conditional): spec references workflow engine
   → agents receive `$FRAMEWORK_DIR/scripts/workflow_engine.py`,
   `yaml_loader.py`, existing `workflow.yaml`. Detail: REFERENCE.md.
6. Read SPEC-MAP; identify neighbour specs for impact.
7. Agent selection (base + specialists; document rationale).
8. Name by path for the seat to read: reviewer-base +
   spec-reviewer-protocol + reviewer-checked-scope + persona; follow
   dispatch-template. Chief additionally: consolidation-preservation
   + piebald-budget.
9. Dispatch parallel (context-isolated) → spawn chief, each seat and the chief
   called as `skills/_protocols/role-dispatch.md` says → read signal
   → verify each kept finding at its cited location
   (`skills/_protocols/finding-verification.md`)
   → **decision-grounding C-VERIFY** on the verdict's pivotal code/spec
   claims (`agents/buddy/architecture-comprehension.md` §B:
   re-execute unless independently re-executed; FALSIFIED → re-frame)
   → SAVE (NON-NEGOTIABLE).
10. NEEDS-WORK: fix → next pass; CONVERGED: DONE. Before fix pass ≥ 2
    (counted across the task's passes on the mechanism), record the
    Simplify-before-patch check (`skills/convergence_loop/simplify-before-patch.md`
    §Simplify-before-patch gate), `model` row first: a mechanism
    without a `§Mechanism-Lifecycle` section gets one before the fix
    brief; a recurring class with a simpler mechanism or a faulty spec
    clause → propose the spec simplification or invariant to the caller
    instead of patching the next route, and the proposal names the
    cells it removes. Every fix on a mechanism edits its matrix in the
    same change.

## 4a. Cross-task AC validation

Trigger patterns (cross-subsystem flow implied):
"user types ... → ... lands in ..."; "X publishes Y; Z consumes Y"
(across components); "after deploy, ... is visible / active /
produced"; "UI displays state X after backend action Y";
"milestone-level user-promise activation across components".

Per such AC: list subsystems traversed; per subsystem identify
OWNING task (via `blocked_by` / `blocks` / sibling-task references).
If owning-task ≠ this task for ANY subsystem → AC cannot close in
this task alone — finding.

Resolution (board recommends, author / orchestrator chooses):
(a) **Split** — this task gets owned half; others become separate
ACs in owning tasks. (b) **Move** — full AC reassigned to whichever
task owns the LAST subsystem to land. (c) **Conditional (task-YAML ACs only)** — prefix
"(after `<blocking-task>` ships) ...". Applies to task-YAML ACs
only. For spec-level ACs in L1+ specs (durable shared surface — specs
outlive transient task-IDs), use (a) Split or (b) Move — NEVER (c) in
a spec, to keep forensic task-IDs out of the spec. Spec-level ACs
needing dependency: use semantic phrasing ("when consumer-side X is
wired") instead of task-ID prefix.

Unaddressed cross-task AC = NEEDS-WORK blocker. Defense-in-depth pair
with `agents/buddy/architecture-comprehension.md` §B
(post-return).

## 4b. Mechanism cells — the review unit (MUST before PASS)

When a `§Mechanism-Lifecycle` section is in scope
(`skills/_protocols/mechanism-model.md`), reviewers review **cells, not
prose**, and the consolidated reports cell coverage:

- **Adversary:** every `→` cell with the next state's invariants
  re-checked, every `✗` cell with a constructed scenario against its
  guard, every `unreachable` cell with an attempt to reach it; findings
  name the cell. A textual contradiction — "X is exempt from Y" inside a
  section that states "X changes only via Y" — is a cell conflict and a
  HIGH.
- **Verification / implementer:** every operation has a grepped
  producer site or `unbuilt: Task N`; every cell is placed per the plan
  (`task-N` cells have their owning task `blocked_by`-wired; nothing is
  left out for lack of a consumer); every cross-spec pointer resolves to
  the owning section; every invariant names its cells and locus.
- **No PASS with an empty cell.** A blocking finding on a `now` cell is
  never `residual`; a blocking route "accepted, routed" to another task
  is NEEDS-WORK at HIGH. Lower-severity residuals carry the cell
  annotation (`_protocols/mechanism-model.md` §Bind rules).

**Derived-state invariants (special case).** For an invariant of the
form "X changes only via Y" (or "X is derived from Z", "never X except
Y") over state derived from a log or store, the matrix columns MUST
include **every operation that changes the derivation's inputs after the
introducing record**, at least: withdraw / retraction; processing or
meaning successor (replacement, revision); scope move; field edits of a
replacement (quality / confidence / provenance fields); cross-principal
acts (another actor touching the same inputs). Each cell carries a guard
(spec clause that enforces Y on that route) or a stated unreachability
reason. A cell with neither = NEEDS-WORK at HIGH. A gate that only checks
what the introducing record carries misses every after-the-fact route;
recurring findings on one mechanism go to the Simplify-before-patch gate
(`skills/convergence_loop/simplify-before-patch.md`), which usually answers with a
derived-state rule instead of more guards — and must then update the
matrix, not add a log entry.

**Fix values and rulings are cross-spec claims.** A reviewer-proposed
validator / rule, or a Buddy ruling on a cross-task contract, is checked
against every spec that produces or consumes the field (SPEC-MAP) and
cites the contract-owner spec, before the spec edit — the citing
(consuming) spec may have drifted from the owner.
