---
name: convergence-loop
description: >
  Intra-gate iteration protocol. Bounded convergence with a rising
  severity threshold and narrowing scope. Max 3 passes.
  Triggers when a fix-then-review cycle needs bounded iteration with a rising severity threshold (review verify, spec_board internal); NOT for one-shot reviews.
status: active
relevant_for: ["main-code-agent", "tester"]
invocation:
  primary: sub-skill
  secondary: [workflow-step]
disable-model-invocation: false
uses: []
---

# Skill: convergence-loop

## Purpose

Intra-gate iteration protocol: how a gate step iterates internally
instead of running single-pass. Bounded convergence — max 3 passes
with a rising severity threshold and narrowing scope. Not a new
gate; a mechanic inside existing gates (cascade:
`workflows/runbooks/build/WORKFLOW.md` phase Specify / Verify,
`workflows/runbooks/review/WORKFLOW.md` phase Verify).

Detail mechanics (override, fix responsibility, scope narrowing,
analysis patterns, outer-loop bound): `REFERENCE.md`.

## Who and when

Every agent with a gate step that produces findings: board agents
(every `board-*`), Buddy (L1 simulation), `tester` (design / eval
mode). The agent loads this skill in addition to the gate-specific
skill. Full path and standard path alike.

Not applicable: `tester` execution mode (the fix loop in
`main-code-agent`) · pure execution steps (writing code, running
tests).

## The protocol

### Step 0: entry (before pass 1)

1. **Intent paraphrase:** the agent formulates the artifact's
   purpose in one sentence. If paraphrase isn't possible → P1
   problem (self-containedness), immediately a BLOCKER.
2. **Scope declaration:** "full scope" on pass 1. Pass 2-3:
   `affected_scope` from the predecessor.

### Three passes, narrowing analytical lens

Iterations with progressively narrowing scope and rising severity
threshold. Each pass has a different analytical lens that can
surface different findings. They are NOT three chances at the same
work — but they are also not three rigidly-separated phases. The
narrowing lens itself is the load-bearing mechanism.

| Pass | Scope | Severity threshold | What the lens surfaces |
|------|-------|--------------------|------------------------|
| 1 | Full artifact scope | All (BLOCKER + MAJOR + MINOR) | Broad analysis, varied patterns — what's there at full scope |
| 2 | `affected_scope` from pass 1 + direct dependencies | BLOCKER + MAJOR | Second-order effects from pass-1 fixes; the narrower scope + tighter threshold can also surface things the broad lens missed at depth |
| 3 | `affected_scope` from pass 2 | BLOCKER only | Verification of pass-2 fix side-effects AND deeper findings the focused BLOCKER-only lens surfaces that pass 1/2 couldn't see |

Pass 3 surfaces NEW BLOCKERs from multiple legitimate sources:
(a) caused by pass-2 fix side-effects; (b) deeper findings only the
narrow lens reveals; (c) rare pass-1 broad-lens miss. All three are
real outcomes of the narrowing-lens mechanism.

**Mechanical stop after pass 3 (with one conditional pass-4
extension — see §Pass-3 termination).** Sub-workflow overrides
preserved (e.g. `spec-board.yaml` safety valve at pass 5, →
`REFERENCE.md`).

### Pass-3 termination (and conditional pass-4 extension)

When pass 3 surfaces BLOCKERs, the agent classifies before
terminating:

| Pass-3 result | Decision |
|---------------|----------|
| 0 BLOCKERs | **CONVERGED** (MINORs carried as annex) |
| BLOCKERs are architectural / cross-cutting / require human decision | **ESCALATE immediately** — not iteration territory |
| BLOCKERs are scoped + clearly fixable within current scope without architecture change | **Pass-4 extension** (one focused fix-verify cycle) |

**Pass-4 extension (one-shot, conditional):**
- Scope = the specific pass-3 BLOCKER(s) only
- Threshold = BLOCKER only
- Buddy fixes between pass 3 and pass 4 per normal fix scope
- Pass-4 outcomes: 0 BLOCKERs → CONVERGED; BLOCKERs remain →
  ESCALATE (no further extension)

**Hard mechanical cap at pass 4.** No pass 5 from convergence_loop;
sub-workflow safety valves apply on top (spec-board at 5, etc).

### Severity definitions (L2 constrained judgment)

| Severity | Definition |
|----------|------------|
| BLOCKER | Artifact unusable as written. The next step cannot start. |
| MAJOR | Usable but with a known defect. Predictably leads to problems / follow-up questions in the next step. |
| MINOR | Improvement, not a defect. The next step's outcome doesn't change. |

Definitions anchored at the next step — mechanically checkable.
Guidance questions: `REFERENCE.md`.

### Fix scope (NON-NEGOTIABLE)

Between passes, **ALL findings** are fixed — not just those above
the current threshold. The threshold determines when CONVERGENCE
is reached, not what gets FIXED. Rationale: high-only fixes
accumulate M/L debt that compounds across passes. Exception: a
`code_review_board` FAIL fixes only the *fix-now set* per its §5
proportionality triage.

Scope narrowing (pass 2+) refers to the ANALYSIS scope of the next
pass, not to the FIX scope.

Before fix pass ≥ 2, the §Simplify-before-patch gate decides whether
the fix patches routes or replaces the mechanism.

### Test scope between passes (NON-NEGOTIABLE)

Between passes, MCA fixes findings (per `Fix scope` above). The
**test scope per fix is narrow, not full-suite** — each finding has
a known `file:line` documented in the verdict; re-testing modules
that weren't touched produces zero new signal at 2-3× wallclock
+ token cost.

| Fix touches | Run |
|-------------|-----|
| One module | unit-test file for that module — explicit path, not `tests/` glob |
| Cross-pass-binding test (RED skeleton) | that specific test file |
| Public-API / spec-defined contract | + 0-1 integration smoke |
| L0 (ruff + mypy) | only on touched files |

**ONE full-suite sweep at the END** — after the last pass converges,
one full repo run confirms no cross-cutting regression. Not per
fix-phase. Same for pre-deploy and cross-cutting refactors.

### Net-new failures from the full-suite sweep

A failure in the end-of-convergence full run but absent from per-fix
scope MUST be classified before it blocks a commit. Three classes:
**(a)** real regression the fix introduced — blocks; **(b)**
test-pollution (`conftest` fixture bleed) — route to the
fixture-pollution task, no block; **(c)** order-dependent pre-existing
bug the new ordering exposed — route to a fix-task, no block.

The isolation-run is one input, not the verdict: passing-in-isolation
rules out (a) but not (b)-vs-(c) — both pass isolated. Second step: is
the bleeding state a test fixture (→b) or a production singleton (→c)?
Never fold an unclassified net-new failure into a fix-pass.

### Termination (general)

| Situation | Decision |
|-----------|----------|
| Pass N has 0 findings above the threshold | **CONVERGED** — proceed to the next gate |
| Pass 1 zero findings | **CONVERGED** — early termination after pass 1 |
| Finding requires an architecture decision | **ESCALATE immediately** — not an iteration problem (any pass) |
| Pass 3 BLOCKERs | see §Pass-3 termination (and conditional pass-4 extension) |
| Pass 4 (extension) BLOCKERs remain | **ESCALATE** — no further extension |

ESCALATE signals "this needs architect / human judgment, not more
agent iteration".

### Simplify-before-patch gate (before every fix pass ≥ 2, MUST)

Applies to spec boards and code boards alike. Route-by-route fixing of
one mechanism does not converge: each pass closes the reported route
and the next pass finds a new route of the same class. Convergence
comes when the mechanism is simplified or one structural invariant is
stated. The orchestrator usually knows this when asked; this gate asks.

**Counting.** Fix passes count across the task's whole review history
of the mechanism: spec-board passes and code-board passes both count.
A first code-board fix pass on a mechanism that already drew blocking
findings in a spec pass is fix pass ≥ 2.

**Record (before dispatching the fix pass).** In the build log / task
state file (a spec-only review: the consolidated file), write:

```
### Simplify-before-patch check — before fix pass {N}
- model: present|written-now|n/a — {spec § of the §Mechanism-Lifecycle section, or why no state carrier}
- same_class: yes|no — {mechanism or guiding rule}; prior {ids} vs new {ids}; cells: {matrix cells the findings sit on}
- simpler_mechanism: yes|no — {named candidate + the cells / invariant locus it removes + the finding ids}
- spec_is_problem: yes|no — {clause}
- decision: patch ({cells changed}; {cells confirmed intact}) | propose-simplification → {caller / PMO / user}
```

**`model` first (show the whole mechanism before asking for a simpler
one).** `present` cites the `§Mechanism-Lifecycle` section
(`skills/_protocols/mechanism-model.md`); `written-now` means the
retro-model trigger fired (protocol §Trigger: a blocking finding on a
mechanism without a section) and the orchestrator wrote the bounded
section before the fix brief; `n/a` names why — no state carrier, or no
blocking finding on one. The remaining rows are answered **against the
matrix**: `same_class` locates the prior and new findings in cells (two
findings in different cells of one carrier are the same class);
`simpler_mechanism` names the cells or the enforcement locus the
candidate removes; a `patch` decision names every cell it changes and
confirms the others intact — a patch that cannot name its cells is not
yet a fix brief. A simplification that stays local to one side (entry,
exit or undo) while other cells remain route-based or unspecified is a
patch, not a simplification; the gate records it as `patch`.

`same_class` compares the new blocking findings (C/H, BLOCKER/MAJOR)
with those of every earlier pass on the same mechanism or guiding rule
("never X", "X changes only via Y"), judged from the findings, the cells
they sit on, and the symbols / rules the previous fix diff touched. Prior
ids are the evidence; a `no` names the different mechanism. Unsure
counts as `yes` for `same_class` only. `simpler_mechanism: yes` requires
a named candidate (mechanism or invariant), the cells it removes and the
finding ids; `spec_is_problem: yes` requires the clause. Without them
the answer is `no`, and the `same_class: yes` row below still forces the
invariant + property generator. Findings on different cells of one
`§Mechanism-Lifecycle` matrix (or different rows of the
`skills/spec_board/SKILL.md` §4b derived-state columns) are the same
class.

**Decision rule.**

| Answers | Decision |
|---|---|
| `model: written-now` | Write the section first; re-read every new and prior finding against the matrix before answering the rows below. Cells the matrix shows empty or unspecified are findings of this pass, whether or not a reviewer reported them. |
| `same_class: yes` AND (`simpler_mechanism: yes` OR `spec_is_problem: yes`) | **Stop route patching.** Propose the simplification to the caller (PMO / user) unprompted: a spec amendment and/or one structural invariant whose checks assert effects, not classifications, plus a property generator whose axes are the matrix axes. The proposal names the cells it removes and shows the **whole updated matrix**, not the changed side. This is a legitimate design fork, not permission-seeking. |
| `same_class: yes`, both others `no` | Patch, but the fix pass MUST add the effect-asserting invariant + property generator above, the record names why no simpler mechanism exists, and the fix brief carries the `§Mechanism-cells` block (`_protocols/fix-brief-template.md`). |
| `same_class: yes` in two consecutive checks | **Propose-simplification regardless** of the other answers: the invariant route already failed once. |
| `same_class: no` | Patch normally (cells named). |

The proposal carries one recommended simplification with its evidence
(the recurring finding ids and cells), not an option menu. A spec
simplification runs through the existing amendment path (build workflow
amendment threshold, spec-drift check) and edits the matrix in the same
change. Cells placed in another planned task or beyond the MVP travel
as `blocked_by` edges (`_protocols/mechanism-model.md` §Scope and
placement); every open `now` cell at blocking severity is closed by the
simplification or the patch — never carried as a risk or filed as a new
task (lower severities: §Bind rules, verdict floor). The proposal is a design-fork proposal,
not permission-seeking; while it waits for an answer it counts as the
ESCALATE of §Termination for the re-review limit, which counts the
simplified fix pass like any other. When the caller is the user (no
PMO session in between), the council-before-user rule of
`agents/buddy/operational.md` applies first: a light council shapes the
recommendation when its §1.0 gate fires.

A spec stays changeable while no real data (persisted, non-test) or
shipped consumer depends on it; a locked status alone is no reason to
keep patching.

**Two rules read with this gate.** "HIGHs are fixed, not accepted"
stays: a simplification that removes the class fixes every HIGH of the
class (each is then closed by re-running its reproduction). Running a
delegated build to done means finishing the task, not the current
design.

## State format between passes

```
## Convergence Pass {N} — {gate name}
### Scope: {pass 1: full scope; pass 2+: affected_scope from N-1}
### Findings
- F{N}.{X}: [{BLOCKER|MAJOR|MINOR}] {description}
  Root cause: {...} | Affected scope: {...}
### Below-threshold: {findings under the threshold — annex}
### Termination: CONTINUE → pass {N+1} | CONVERGED | ESCALATE
```

CONVERGED: annex with below-threshold findings from every pass.
ESCALATE: concrete reason + question ("BLOCKER F3.1 needs a
decision: {...}"), not "there are problems".

## Integration into gate steps

The gate skill = **lens** (what is being checked). The convergence
loop = **iteration** (how often, which scope, when to stop).
Agents load it in addition to their gate skill: step 0 → pass 1
with varied patterns → fixes → pass 2 `affected_scope` → fixes →
pass 3 → CONVERGED / ESCALATE. Varied patterns per gate type +
fix responsibility: `REFERENCE.md`.

## Boundary

- **Not** the fix loop in `main-code-agent` · **not** the gate
  cascade itself (the cascade decides which gates run).
- **Not** the review protocol (replaced by Spec Board).
- **Not** alternatives evaluation — divergent thinking belongs in
  council / solution-expert.
- **Not** execution steps (writing code, running tests) — only
  analytical / validating gates.

## Anti-patterns

- **NOT** fix only findings above the threshold between passes.
  **INSTEAD** fix ALL findings — the threshold determines
  convergence, not fix scope. Because: MINOR accumulation compounds
  across passes. Exception: `code_review_board` FAIL fixes the
  fix-now set per its §5 proportionality triage.
- **NOT** treat pass 2 / 3 as fix verification. **INSTEAD** every
  pass is a fresh analysis. Because: anchoring bias — tainted
  passes miss high findings a fresh look catches.
- **NOT** iterate over architecture findings. **INSTEAD**
  ESCALATE immediately. Because: architecture is not an
  iteration problem.
- **NOT** set severity abstractly. **INSTEAD** anchor it at the
  next step ("can the next step proceed?"). Because: only that
  is mechanically checkable.
- **NOT** force CONVERGED at pass 3 to avoid ESCALATE or skip the
  pass-4 extension. **INSTEAD** classify pass-3 BLOCKERs honestly:
  architectural → ESCALATE; scoped + fixable → pass-4 extension;
  none → CONVERGED. Because: deadline framing produces premature
  CONVERGED + severity-downgrade.
