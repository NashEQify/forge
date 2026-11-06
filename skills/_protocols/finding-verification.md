# Protocol: Finding verification

Read it when a review's findings are in and consolidated (the chief's keep/refute, or Buddy's own reading where Buddy
consolidates), before any disposition or fix brief that depends on a finding's grade; when commissioning a
verification seat; and when writing a fix brief from review findings. It applies to the code review board at every
level and to the spec board. It decides how each finding is checked where it points and who grades it. The consumers
are Buddy deciding the verdict, the seat that verifies, and the fix pass that receives the findings; the cost it
prevents is a finding that does not hold at its location driving a fix pass and a re-review, and a real finding
graded too low being parked.

## When and where

- **Every kept finding gets a row.** Its grade is set by the verification, so which findings enter a fix pass is
  known only afterwards. Findings the chief refuted keep their row in the chief's tracking table; where Buddy
  consolidated, a finding refuted at keep/refute takes a row here with verdict `false` and the reviewer-surface
  evidence that refuted it.
- **At the reviewed bytes:** the HEAD of the review package the seat reviewed (`skills/code_review_board/review-package.md`,
  the review's Range line); for a spec board, the spec at the reviewed revision. Not the working tree after a later
  edit.
- **After the mechanical checks:** a finding whose evidence quote does not resolve is rejected at intake
  (`skills/_protocols/evidence-pointer-schema.md`); verification checks the claim, not the quote.

## Who

- **Buddy** verifies where Buddy consolidated the reports (`skills/code_review_board/SKILL.md` §1.3: the light level
  and boards of up to three reviewers), since the reports are already in the deciding context.
- **Where a chief consolidated, one `code-verification` seat** in fresh context, read-only. It receives the package
  path (spec board: the spec path and revision), this protocol, and per finding its id, cited location, claimed
  outcome, claimed grade and the reviewer's evidence. Its model is the "Review by diff size and risk" row of
  `framework/models.md`, named in the call; on a spec board that row is read with the spec's changed lines in place of
  the package's stat. On a mandatory review the capture names this seat as a planned `verification` slot from the
  start (`skills/_protocols/evidence-review-capture.md` §9.2), so it is not added after the chief's consolidation.
- Buddy owns the verdict either way and reads the seat's rows before adopting them.

## Verifying one finding

1. At the cited file and line, at the reviewed bytes: does the bad outcome the finding describes occur? Read beyond
   the cited lines (callers, guards, the units that load the text) until the answer is yes or no. A different problem
   nearby does not settle this one. Judge the claimed outcome, not the proposed fix.
2. A finding whose report carries a check executed on those bytes, or on the host state its claim names (command and
   observed output showing the outcome), or whose claim Buddy's pivotal-claim check
   (`agents/buddy/architecture-comprehension.md` §B) already re-executed, is verified from that output when the
   check's input reaches the outcome through the entry point the claim names (its caller, boot or command path);
   otherwise step 1 reads on. Such a check is not run again here. Buddy's pivotal-claim check before the verdict still re-executes a claim only its asserter ran.
3. Give exactly one verdict:
   - **`critical`, `high`, `medium` or `low`:** the outcome occurs. Grade it by the harm on the scale of the
     reviewer protocols (`agents/_protocols/code-reviewer-protocol.md` and
     `agents/_protocols/spec-reviewer-protocol.md`, §Output format), without regard to the reviewer's or the chief's
     grade. The evidence names the harm the grade rests on; a harm only to maintainers names where it causes trouble
     (which caller diverges, which rule breaks). When the harm is real and its size unclear, take the higher grade.
   - **`false`:** the outcome does not occur at the location. The evidence states what disproves this claim; a true
     fact about nearby code that leaves the claim standing does not count. A finding that names no bad outcome is
     `false`.
   - **`maybe-false`:** the reads leave it open. The evidence names the check that would settle it and the grade the
     claim would take if true. Where the reads decide the question, the verdict is one of the others.
4. For a graded finding that falsifies a stated invariant, say which way the deviation goes; the verdict floor on
   mechanism cells applies only to the dangerous one (`skills/code_review_board/verdict.md` §5):
   - **`dangerous`:** the outcome is the one the invariant exists to prevent: a wrong, lost, leaked or unsafe value
     or state reaches a consumer, or a refusal the invariant requires does not happen.
   - **`cautious`:** the code errs toward the side the invariant protects and the only cost is waste or delay: it
     counts a reservation twice for one step, refuses or waits longer than needed, reports a conservative bound.
   - Where the reads show neither, it is `dangerous`.

## The row

The verification record is a table with one row per claim of each kept finding: a finding that makes several claims
gets one row per claim (`F-07a`, `F-07b`), each with its own verdict. No row is merged, dropped or skipped:

```markdown
| Finding | Location (at the reviewed bytes) | Claimed | Verdict | Evidence |
|---|---|---|---|---|
| <id> | <path:lines, or the host path a claim rests on> | <reviewer's or chief's grade> | <verdict> | <one line: the read or output that settled it and the harm; for maybe-false, the settling check and the grade if true; for a falsified invariant, dangerous or cautious> |
```

It is persisted in the directory of the board's persisted reviews as
`{task-id}-verified-<first 7 of the reviewed HEAD>.md` (spec board: `{spec-name}-verified-pass<N>.md`, following its
output paths), with the review's Range line under its title, so a re-review's verification does not overwrite the
first. A seat's rows are persisted verbatim before adoption.

## What follows

- **Disposition runs on the verified grades** (`skills/code_review_board/verdict.md` §5, `skills/spec_board/post-pass.md`
  §6). A cluster takes the highest verified grade among its members.
- **`false`:** rejected on its refutation. The row stays; it takes no target and is not carried forward.
- **`maybe-false`:** enters no fix pass unsettled. When its grade if true is high or above, or it would block an
  acceptance criterion, Buddy runs the settling check before the verdict and replaces the verdict. Otherwise, on the
  code board, a grade if true of `low` takes `accept` and `medium` takes `watch_item` or `re_review`; on the spec
  board it is carried forward (`skills/spec_board/post-pass.md` §6a). Either way the settling check goes into its
  rationale, and a carried `severity` is the grade if true, marked unverified.
- **The fix brief** carries, per finding it fixes, the finding's row: location at the reviewed bytes, verdict and
  evidence. The fix pass receives verified findings only; the implementer's own check of what it receives starts
  from these rows.
- **Unchanged:** the chief's consolidation and its REFUTED rule, the routing targets, and the evidence-quote check.

## Source

BMAD-METHOD (MIT License, © 2025 BMad Code, LLC); Forge's register of adopted methods.
