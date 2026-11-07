# Convergence loop — simplify-before-patch gate

Step-loaded unit of `skills/convergence_loop/SKILL.md`. Read it before writing the brief for any fix pass ≥ 2 on a
mechanism (counted across review owners, workflows and tasks), before approving a new review owner or extension on
it, and before the pass-4 extension. The causes and their answers it applies are in
`skills/convergence_loop/cause-before-answer.md`.

### Simplify-before-patch gate (before every fix pass ≥ 2, MUST)

This pass-count safeguard does not postpone purpose reassessment. Apply
`agents/buddy/architecture-comprehension.md` before introducing
additional machinery and when returned findings call its necessity into
question; use the existing brief and triage record.

Applies to spec boards and code boards alike. The gate first asks why the
earlier fix passes did not converge, and then answers each open blocking
finding by its cause (`cause-before-answer.md` §Cause before answer). When the cause is a mechanism,
route-by-route fixing does not converge: each pass closes the reported route
and the next pass finds a new route of the same class. Convergence then comes
when the mechanism is simplified or one structural invariant is stated.

**Counting.** Fix passes count across the task's whole review history
of the mechanism: spec-board passes and code-board passes both count.
A first code-board fix pass on a mechanism that already drew blocking
findings in a spec pass is fix pass ≥ 2. Same mechanism means the same state
carrier (`skills/_protocols/mechanism-model.md`), whatever the finding, defect,
extension, workflow or task is called. A new review owner, SUB-FIX,
extension, task or reframed defect on that carrier continues its count and
this gate while the carrier's blocking findings are unresolved; it never
starts at fix pass 1. The coordinator who approves a new owner or extension
checks this before approving.

**Gap inventory (before the record).** The diagnosis starts from what the code
at the fix package's HEAD does against the spec, not from the implementer's
report or an earlier verdict: a completion claim is not evidence. On a
spec-only review the spec at the reviewed revision takes the code's place,
assessed against the task's acceptance and the matrix, and its findings take
the causes other than stuck and code. For every
spec item that governs a unit an earlier fix pass changed (each acceptance
criterion, each spec clause, each matrix cell), one row: the item and its
source, its state against the present code (met, missing, partial or
contradicts) and the code location; code that no item asks for gets a row of
its own as unrequested. Persist the inventory beside the record. It is input to
`why` and the causes, not a list of tasks: a gap enters a fix pass only as a
verified finding or through the answer the gate chooses.

**Record (before dispatching the fix pass).** When writing a re-review or
fix brief, check each earlier `accept` / `watch` / removed or refuted
finding whose rationale names an input (a file, contract, dependency or
assumption) that the change touches. If that input changed since the
disposition, the finding reopens for fresh judgement, even when its own
line is unchanged. In the build log / task
state file (a spec-only review: the consolidated file), write:

```
### Simplify-before-patch check — before fix pass {N}
- model: present|written-now|n/a — {spec § of the §Mechanism-Lifecycle section, or why no state carrier}; derived: {its Derived: line} | no | n/a (model: n/a)
- inventory: {path} — missing {n}, partial {n}, contradicts {n}, unrequested {n}
- why: {one sentence: why the earlier passes did not converge, read from the inventory and the prior vs new findings}
- same_class: yes|no — {mechanism or guiding rule}; prior {ids} vs new {ids}; cells: {matrix cells the findings sit on}
- simpler_mechanism: yes|no — {named candidate + the cells / invariant locus it removes + the finding ids}
- spec_is_problem: yes|no — {clause}; open readings: {n} ({RL ids})
- causes: {id}: wrong-finding|intent|spec|mechanism|stuck|code — {the check that holds}; … one per open blocking finding
- decision: per cause group — patch ({cells changed}; {cells confirmed intact}) | propose-simplification → {caller / PMO / user} | amend-spec ({§}) → re-derive {unit} | patch | ask → {caller} | fresh-implementer {model} | rule {ids} | accept-limit {ids}
- class_witness: {command} — red: {open ids} at {HEAD}, {prior ids} at {rev}; sharpened: {what was added for a finding it missed} | n/a (same_class: no)
```

**`model` first (show the whole mechanism before asking for a simpler
one).** `present` cites the `§Mechanism-Lifecycle` section
(`skills/_protocols/mechanism-model.md`); `written-now` means the
retro-model trigger fired (protocol §Trigger: a blocking finding on a
mechanism without a section) and the orchestrator wrote the bounded
section before the fix brief; `n/a` names why — no state carrier, or no
blocking finding on one. The remaining rows are answered **against the
matrix**: `same_class` locates the prior and new findings in cells;
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
ids; `spec_is_problem: yes` requires the clause, or five or more open readings
(`cause-before-answer.md` §Ruling record) in its place. Without them
the answer is `no`, and the `same_class: yes` row below still forces the
invariant + property generator. Findings on different cells of one
`§Mechanism-Lifecycle` matrix (or different rows of the
`skills/spec_board/checklist-and-dispatch.md` §4b derived-state columns) are the same
class.

**Decision rule.** Each open blocking finding takes the answer of its
cause (`cause-before-answer.md` §Cause before answer). For the findings whose cause is mechanism or
code, the table decides:

| Answers | Decision |
|---|---|
| `model: written-now` | Write the section first; re-read every new and prior finding against the matrix before answering the rows below. Cells the matrix shows empty or unspecified are findings of this pass, whether or not a reviewer reported them. |
| `same_class: yes` AND (`simpler_mechanism: yes` OR `spec_is_problem: yes`) | **Stop route patching.** Propose the simplification to the caller (PMO / user) unprompted: a spec amendment and/or one structural invariant whose checks assert effects, not classifications, plus a property generator whose axes are the matrix axes (the class witness below). The proposal names the cells it removes and shows the **whole updated matrix**, not the changed side. This is a legitimate design fork, not permission-seeking. |
| `same_class: yes`, both others `no` | Patch, but the effect-asserting invariant + property generator above MUST stand as the class witness before the fix brief (below), the record names why no simpler mechanism exists, and the fix brief carries the `§Mechanism-cells` block (`_protocols/fix-brief-template.md`). |
| `same_class: yes` in two consecutive checks, `model` not `n/a`, and `derived: no` or five or more open readings | **Drill the mechanism** (`derive-and-exit.md`) instead of a further invariant or patch: its owner-approved axioms go into the spec and the matrix. |
| `same_class: yes` in two consecutive checks, the drill row not met | **Propose-simplification regardless** of the other answers: the invariant route already failed once. |
| `same_class: no` | Patch normally (cells named). |

The proposal carries one recommended simplification with its evidence
(the recurring finding ids and cells), not an option menu. A spec
simplification runs through the existing amendment path (build workflow
amendment threshold, spec-drift check) and edits the matrix in the same
change. Cells placed in another planned task or beyond the MVP travel
as `blocked_by` edges (`_protocols/mechanism-model.md` §Scope and
placement); every open `now` cell at blocking severity is closed by the
simplification or the patch — never carried as a risk or filed as a new
task (lower severities: §Bind rules, verdict floor). While the proposal, a drill or an intent question waits for an answer it counts as the
ESCALATE of `SKILL.md` §Termination for the re-review limit, which counts the
simplified fix pass like any other. When the caller is the user (no
PMO session in between), the council-before-user rule of
`agents/buddy/operational.md` applies first: a light council shapes the
recommendation when its §1.0 gate fires.

A spec stays changeable while no real data (persisted, non-test) or
shipped consumer depends on it; a locked status alone is no reason to
keep patching.

**Two rules read with this gate.** "HIGHs are fixed, not accepted"
stays: a simplification that removes the class fixes every HIGH of the
class (each is then closed by re-running its reproduction and the class
witness). Running a delegated build to done means finishing the task,
not the current design.

### Class witness (every `same_class: yes` row, before the fix brief)

Tests per finding cover only the reported routes, so a suite can be green after each pass while the next review finds
new routes of the same class. The property generator the rows above require therefore exists before the fix brief is
written, not as part of the fix pass. Its axes are the matrix axes and its oracle is written from the matrix by
someone other than the fix pass's implementer (`skills/testing/test-design.md` §Derivation from §Mechanism-Lifecycle,
§Oracle discipline); for a proposed simplification they are the axes of the updated matrix. It must turn red every
known blocking finding of the class, each on the code before its fix: the open (new) ids at the fix package's HEAD,
each prior id at its pre-fix revision or with its fix reverted (`red at {rev}`). When it misses one, sharpen it (the
axis, value or route the finding needs) and run it again before any code changes; a finding no generator over the
matrix axes can produce is an empty or missing cell, which the matrix gets first (the `model: written-now` row); for a
proposed simplification, a finding on a cell the simplification removes is witnessed by that removal, not by adding
the cell back. The known findings become fixed examples of the generator, so they run in every run, also with the
smaller case count outside the full gate (`skills/testing/lean-suite.md` §pytest shape). The record's `class_witness`
row and the fix brief carry its command and the findings it turned red (`_protocols/fix-brief-template.md` Section 4).
The fix pass does not edit the witness; an edit to it in the fix diff is an oracle hunk for the re-verify. The class
witness replaces the hand-written regression test per finding of the class (`skills/testing/SKILL.md` §Meaningful
pre-fix witness). After the fix, the same command passes: the reported findings and the routes the generator spans are
closed. The review still judges the rest of the mechanism.

## Source

spec-kit (MIT License, © GitHub, Inc.); Forge's register of adopted methods.
