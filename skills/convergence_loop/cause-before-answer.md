# Convergence loop — cause before answer

Step-loaded unit of `skills/convergence_loop/SKILL.md`. Read it when writing a fix brief from a code review's
findings, the first fix pass included, when the Simplify-before-patch gate
(`skills/convergence_loop/simplify-before-patch.md`) answers each open blocking finding by its cause, when an
implementer's report has a `pushed back` or `unclear` row, when `skills/convergence_loop/at-the-cap.md` applies its
checks at the re-review limit, and when `skills/root_cause_fix/SKILL.md` Step 4 stops a fix from its third failed attempt.

### Cause before answer

A fix converges when it changes what caused the finding. A patch changes code; when the cause sits in the spec, the
intent, the mechanism, the implementer's context or the finding itself, the patch closes the reported route and the
cause stays. So every finding a fix pass is to fix gets its cause before its answer, at the first review as at every
later one, starting from its verified row (`skills/_protocols/finding-verification.md`). A fix brief written from a
code review's findings carries the result (`skills/_protocols/fix-brief-template.md` §Section 5).

Take the checks in this order; the first that holds is the cause:

| Cause | Check | Answer |
|---|---|---|
| wrong finding | The outcome the finding calls bad is what text binding this task requires or allows: the approved acceptance or its exclusions, the spec, or a ruling recorded on the same location and claim. Quote that text. A finding whose outcome is a defect but whose proposed change conflicts with such text is not wrong: take the next check. | **Rule and park.** Weigh the finding against the quoted text and record the ruling with the quote in the review decision, as `accept` with the ruling as its rationale. The finding enters no fix pass; a later review that raises the same claim at the same location gets the ruling, not a fix. When the outcome sits on a floor that `skills/code_review_board/verdict.md` §5 keeps from `accept` (a `now` mechanism cell at blocking severity, a safety floor), or the ruling would need the approved acceptance or an exclusion to be wrong, it is an intent finding instead; a spec clause that contradicts a clear acceptance is a spec finding. |
| intent | The approved acceptance admits two readings of the outcome the finding concerns, neither the spec nor the code settles which, and the two readings give the user different results. Name both readings and the result of each. | **Return to the caller** (the commissioning coordinator; when that is the user, council first per `agents/buddy/multi-perspective.md`) with both readings and one recommendation. The finding enters no fix pass until answered; the answer goes into the spec and the finding continues as a spec finding. |
| mechanism | The findings, or the claims of one finding, reach one bad outcome by different routes through one state carrier, recognizer or guiding rule ("never X", "X changes only via Y"), or the Simplify-before-patch record says `same_class: yes`. A spec clause behind the mechanism does not change this cause; the spec amendment is then part of the answer. Name the routes and the mechanism. | **Simplify or replace the mechanism, or state one structural invariant** whose checks assert effects, with a property generator over the routes. A replacement that changes the spec or the approved design goes to the caller as a proposal, as the Simplify-before-patch gate describes; from fix pass 2 on, that gate's decision rule decides. |
| spec | The spec item that governs the outcome (its clause; where the task has no spec, the acceptance criterion or the owner text the code implements) is silent, ambiguous or wrong about it, and the code follows a reading of that text. Quote the clause, or name the item that lacks it. A clause that supports both the code's reading and the finding's counts. | **Amend the spec first** (`skills/_protocols/spec-amendment-discipline.md`; the `§Mechanism-Lifecycle` matrix in the same change when a state carrier is involved). Then re-derive the unit when it is fresh (§Re-derive); otherwise patch it, or refactor it in steps, against the amended text. An amendment that would change the approved acceptance or an exclusion makes it an intent finding. |
| implementer stuck | A finding the previous fix brief carried, with no ruling on a push-back since, verifies again at the fix package's HEAD with the same location and claim, or the implementer's report says it could not fix it. | **A fresh implementer**: a new dispatch, not a resume, one tier above the row of the stuck implementer's brief (`framework/models.md`), the reason in its `MODEL` line; on the most capable tier, the same tier with that named. It gets the brief, the report files and the open rows, and is the implementer resumed from then on. |
| code | None of the above: the spec states the right outcome and the code, by one route, does otherwise. | **Patch.** |

**Accept with a recorded limit** is the answer for any cause where the triage of `skills/code_review_board/verdict.md`
§5 allows `accept` and `agents/buddy/delegation.md` §Delegation hygiene allows closing as a limit: record the limit and
its cause. Blocking findings on a `now` mechanism cell,
change-introduced regressions and required floors take one of the other answers.

Simplification answers one of these causes, the mechanism; non-convergence alone does not select it.

### A defect after three failed fixes

`skills/root_cause_fix/SKILL.md` Step 4 records an attempt for each fix of a defect, planned from its Step 1, whose
retest failed. A fix pass that a code review requested is not an attempt: the Counting rule of `simplify-before-patch.md`
counts it, whatever its retest shows. From the third recorded attempt, the defect goes through the table above:
- **The finding** is the defect. **Its routes** are the failures the attempts' retests showed (each new error,
  location or symptom), not the attempts themselves.
- **The record:** a ruling or a recorded limit goes into the fix state file (outside the fix workflow, the owning work
  unit's record) where the table names the review decision, and Step 5 closes the fix with it in place of a retest
  PASS.
- **`implementer stuck` or `code`:** the attempts found no cause outside the code. STOP and escalate to the user with
  the attempts and the checks that did not hold; on `implementer stuck`, recommend its fresh implementer.
- **An answer whose retest fails:** STOP and escalate to the user in the same way.

### Spec gaps a fix reveals

When a fix decides an outcome that no spec item states (an edge case, an error path, a limit), the spec item that
governs the unit gets that outcome in the same change, through the amendment path, also when spec-defined behaviour
is unchanged. The fix brief asks the implementer to report each such outcome under Concerns
(`skills/_protocols/fix-brief-template.md` §Section 5); Buddy carries them into the spec before the re-review. Where the task has no spec, the owner text that states the unit's
contract takes the outcome; the approved acceptance stays read-only.

### Ruling on a pushed-back finding

An implementer's report holds one result per finding (`skills/_protocols/mca-dispatch.md` §A fix brief's findings).
Buddy rules on each `pushed back` and `unclear` row before the fix's review package is built:
- **unclear:** the table above runs for the finding, with the implementer's question as input.
- **pushed back:** Buddy reads the implementer's evidence at its location.
  - It does not hold: the finding keeps its cause and answer; the brief's change is to be made, and a change made
    instead is to be undone by its undo.
  - It holds: the table above runs again for the finding, with the evidence as input. A change made instead stays
    only when Buddy takes it as the answer, on the check the report names for it; otherwise it is to be undone.

When the answer ends in a patch (`code`, or `spec` after its amendment), the patch and any undo go into the brief file,
and the implementer is dispatched again on that brief; the re-dispatch records rows only for the findings it is sent
for. Any other cause takes its own answer, and the finding goes into the next fix brief or to the caller as that answer
says.

The ruling goes into the review decision beside the finding's disposition: the implementer's evidence or question, the
read Buddy made, and the cause and answer that follow. A later fix brief that carries the finding quotes the ruling in
its cause entry's `check`.


### Re-derive

Re-deriving removes a unit's code and implements it again from the amended spec, in a fresh dispatch. It is allowed
only for a fresh unit: every line of it was added since the task's BASE (`skills/code_review_board/review-package.md`
§BASE). The check reads line origin, not the path: `git blame -C -C <BASE>..<HEAD> -- <path>`, at the review
package's HEAD, follows renames and moved lines and marks with `^` each line that already existed at BASE; none of the
unit's lines carries it. A unit with any line older than BASE is long-lived: patch it, or refactor it in steps, each step reviewed like a fix
pass.

The fix brief for a re-derivation carries:
- the unit: its paths, its functions or sections, and the BASE its lines go back to;
- the amended spec item, quoted;
- KEEP notes, what worked and must survive: each acceptance item already met with its test, each closed finding with
  its reproduction, each ruling and decision recorded on the unit.

The unit's tests stay and must pass against the new code. The spec-drift check (`skills/spec_amendment_verification/SKILL.md`)
runs on the amended spec in the same change.

## Source

BMAD-METHOD (MIT License, © 2025 BMad Code, LLC) and Superpowers (MIT License, © 2025 Jesse Vincent); Forge's register of adopted methods.
