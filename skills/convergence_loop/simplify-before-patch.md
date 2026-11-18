# Convergence loop — simplify-before-patch gate

Step-loaded unit of `skills/convergence_loop/SKILL.md`. Read it before writing the brief for any fix pass ≥ 2 on a
mechanism (§Counting), before approving a new review owner or extension on it, and before the pass-4 extension.

### Simplify-before-patch gate (before every fix pass ≥ 2, MUST)

Apply `agents/buddy/architecture-comprehension.md` before adding machinery and when findings call its purpose into
question. Use the existing brief and triage record. Diagnose why earlier passes failed, then answer each blocking
finding by its cause (`cause-before-answer.md` §Cause before answer). Recurring mechanism failures need a simpler
mechanism or one structural invariant that covers the class.

**Counting.** Count spec and code fix passes across the same state carrier (`skills/_protocols/mechanism-model.md`).
Prior blocking spec findings make the first code fix on that carrier pass ≥ 2. While blocking findings remain, a new owner,
SUB-FIX, extension, task, workflow or renamed defect continues the count and gate. The coordinator checks before
approving an owner change or extension.

**Gap inventory (before the record).** Compare behaviour at the fix package's HEAD with the governing spec, using the
reviewed spec against acceptance and the matrix for spec-only reviews (causes other than stuck and code). For every
AC, clause and cell governing an earlier fix's changed units, record source, implementation location and state
(met, missing, partial, contradicts). Give each unrequested code item its own row. Persist this input to `why` and `causes`
beside the record. A gap enters the fix only through a verified finding or the gate's answer.

**Record (before dispatching the fix pass).** When writing a fix brief or re-review, reopen earlier accept/watch,
removed or refuted findings for fresh judgement if an input to the rationale changed. Write in the build log or task
state file (spec-only review: consolidated file):

```
### Simplify-before-patch check — before fix pass {N}
- model: present|written-now|n/a — {spec § of the §Mechanism-Lifecycle section, or why no state carrier}; derived: {its Derived: line} | no | n/a (model: n/a)
- inventory: {path} — missing {n}, partial {n}, contradicts {n}, unrequested {n}
- why: {one sentence: why the earlier passes did not converge, read from the inventory and the prior vs new findings}
- same_class: yes|no — {mechanism or guiding rule}; prior {ids} vs new {ids}; cells: {matrix cells the findings sit on}; defined_by: {unit, place} | n/a | none | unsure ({candidates})
- deciders: {question; every predicate caller and independent decider with location; owner or unresolved candidates; duplicate → delete or delegate} | n/a (same_class: no)
- simpler_mechanism: yes|no — {named candidate + the cells / invariant locus it removes + the finding ids}
- spec_is_problem: yes|no — {clause}; open readings: {n} ({RL ids})
- causes: {id}: wrong-finding|intent|spec|mechanism|stuck|code — {the check that holds}; … one per open blocking finding
- decision: per cause group — derive-from ({unit}) | patch ({cells changed}; {cells confirmed intact}) | propose-simplification → {caller / PMO / user} | amend-spec ({§}) → re-derive {unit} | patch | ask → {caller} | fresh-implementer {model} | rule {ids} | accept-limit {ids}
- class_witness: {command} — red: {open ids} at {HEAD}, {prior ids} at {rev}; sharpened: {what was added for a finding it missed} | table: {command; revisions, affected cells and results} | n/a (same_class: no)
```

**`model` first.** Cite the `§Mechanism-Lifecycle` section (`skills/_protocols/mechanism-model.md`). On a blocking
mechanism finding without one, write the bounded section before the fix brief (`written-now`). Use `n/a` for no state
carrier or no blocking finding on one. Answer against the whole matrix: locate findings, name cells or the locus a
candidate removes, and for a patch list changed cells and confirm the rest intact. A change local to entry, exit or
undo with other cells still route-based or unspecified is a patch.

Compare new blocking findings (C/H, BLOCKER/MAJOR) with all earlier ones on this mechanism or guiding rule using
finding IDs, cells and symbols or rules changed by the last fix. Findings on different cells of one lifecycle matrix or different rows of the
derived-state columns (`skills/spec_board/checklist-and-dispatch.md` §4b) are the same class. A `no` names the different
mechanism. Unsure counts as `yes` for `same_class` only. `simpler_mechanism: yes` needs a candidate, removed cells and
finding IDs. `spec_is_problem: yes` needs the clause or ≥ 5 open readings (`cause-before-answer.md` §Ruling record).
Without the evidence, the corresponding answer is `no`.

After two failed reviews at the same transition between roles, first ask what interface governs the transition and
who owns it. Record the answer or open question in `why` before choosing the fix.

Before choosing a changed cut, cite the applicable project intent and the original local objective in
the existing `decision` rationale. Explain how the cut serves both, and hold a cut that depends on an
unresolved conflict or missing governing source (owner: framework/invariants.md §Intent-driven).

At `same_class: yes`, fill `deciders` by tracing uses of the predicate and searching for equivalent decisions,
including fallbacks. Distinguish calls to the owner from duplicate decisions. `derive-and-exit.md` governs uncertainty
and defects in the defining unit. If competing deciders lack a settled owner, record `ask → caller` before the decision
rule and hold dependent choices until ownership is settled (`ESCALATE` while waiting), including with `defined_by: n/a`.
In the fix brief carry the inventory, name the one owner, and delete or delegate each duplicate in the same phase.
A stricter caller keeps its stated difference after delegating the shared decision.

**Decision rule.** Each open blocking finding takes the answer of its
cause (`cause-before-answer.md` §Cause before answer). For the findings whose cause is mechanism or
code, the table decides:

| Answers | Decision |
|---|---|
| `defined_by:` names a unit | **Derive from it** (`derive-and-exit.md` §Derive from the defining unit), the rows below do not apply to the class; no further channel, case or invariant in the copy. |
| `model: written-now` | Write the section first; re-read every new and prior finding against the matrix before answering the rows below. Cells the matrix shows empty or unspecified are findings of this pass, whether or not a reviewer reported them. |
| `same_class: yes` AND (`simpler_mechanism: yes` OR `spec_is_problem: yes`) | **Stop route patching.** Propose the simplification to the caller (PMO / user) unprompted: a spec amendment and/or one structural invariant whose checks assert effects, not classifications, plus the applicable class witness below. The proposal names the cells it removes and shows the **whole updated matrix**, not the changed side. |
| `same_class: yes`, both others `no` | Patch, but the effect-asserting invariant and applicable class witness must stand before the fix brief, the record names why no simpler mechanism exists, and the fix brief carries the `§Mechanism-cells` block (`_protocols/fix-brief-template.md`). |
| `same_class: yes` in two consecutive checks, `model` not `n/a`, and `derived: no` or five or more open readings | **Drill the mechanism** (`derive-and-exit.md`) instead of a further invariant or patch: its owner-approved axioms go into the spec and the matrix. |
| `same_class: yes` in two consecutive checks, the drill row not met | **Propose-simplification regardless** of the other answers: the invariant route already failed once. |
| `same_class: no` | Patch normally (cells named). |

Recommend one simplification with recurring IDs and cells. Use the existing spec amendment threshold and spec-drift
check for spec simplifications and edit the matrix in the same change. Deferred cells travel as `blocked_by` edges
(`_protocols/mechanism-model.md` §Scope and placement). Close every blocking `now` cell in this fix (lower severities:
§Bind rules, verdict floor). Waiting on a proposal, drill or intent question counts as ESCALATE (`SKILL.md` §Termination).
A simplified fix counts as a pass. When the caller is the user, apply the council-before-user rule
(`agents/buddy/operational.md`) before making the recommendation. A spec remains changeable while no real data (persisted, non-test) or
shipped consumer depends on it, even if locked.

**Two rules read with this gate.** "HIGHs are fixed, not accepted"
stays: a simplification that removes the class fixes every HIGH of the
class (each is then closed by re-running its reproduction and the class
witness). Running a delegated build to done means finishing the task,
not the current design.

### Class witness (every `same_class: yes` row, before the fix brief)

**State/transition-table specs.** After two review rounds with the same class, use the executable table recomputation
(`skills/spec_board/SKILL.md` §4.–4b) before the next round, including on the simplification route. Derive the axes from
the governing rules and operations (§4b in `skills/spec_board/checklist-and-dispatch.md`). Show gaps or contradictions
for the class's open and prior cells on their pre-fix revisions. Re-run on the revised spec. Record the command,
revisions, cells and results in `class_witness`; the next seats receive the current output, with earlier results in
the review history.

**Code.** Tests per finding cover only the reported routes, so a suite can be green after each pass while the next review finds
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
