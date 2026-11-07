# Code review board — small fix on a live path

Step-loaded unit of `skills/code_review_board/SKILL.md`. Read it at the level choice (§1.0) when live infrastructure
is a safety floor of the change and no other floor applies. Section numbers are skill-wide: §1 and §6–§10 in
`SKILL.md` (§1.0a here), §2–§3 in `brief-and-team.md`, §4–§4a in `checklist-and-dispatch.md`, §5–§5a in `verdict.md`,
§11 in `review-package.md`.

## 1.0a Small fix on a live path

The live-infrastructure floor exists so that a failure in a running system is
not missed; a single verifier covers that for a small fix when the evidence
reaches every way the changed path can end. `light` applies when live
infrastructure is the change's only safety floor and all four hold, each
checked on the diff and the records before dispatch:

(a) **Small and local:** the diff stays inside one existing mechanism (its
    functions and their tests; checked by reading each hunk of the review
    package against the mechanism the dispatch names), follows that
    mechanism's existing pattern, and adds no component, state carrier,
    concurrency or retry path, external call or configuration key; the other
    DIRECT criteria
    (`framework/direct-eligibility.md` §DIRECT eligibility, its list) hold.
(b) **Reproduced exits:** every exit or outcome the diff changes has a test
    that ran red before the change and green after it (command and output in
    the record).
(c) **Mechanism mandate:** the `code-verification` dispatch names the
    mechanism and carries its exit table: each way the path ends (success,
    each error, retry, timeout, partial state), whether the diff changes it,
    and the test from (b) for each changed one. A `§Mechanism-Lifecycle`
    matrix for the mechanism serves as the table when it lists the exits.
(d) **Full gate before merge:** the project's named full gate (its CI, or the
    role that merges) runs the whole suite before the merge
    (`skills/testing/lean-suite.md` §Change-scoped runs and the full gate),
    also when no broad run is otherwise due; the dispatch and the verdict
    name it.

The seat runs on the review package (§11); the verdict records (a)–(c) with
their evidence and names the gate of (d). The role that merges reads the
gate's result before the merge and adds it to the verdict; a failing gate
blocks the merge, and the level is set again by §1.1. When the seat finds a
condition false, an exit the diff changes without a reproduction, an exit the
code has that the table misses, or a dangerous invariant falsification
(`_protocols/finding-verification.md` step 4), its PASS does not decide the
review: the level is set again by §1.1. Live infrastructure stays a
safety floor for every later step: a fix after this review takes the §4
re-verify table (`review-package.md` §Small fix after a passing review).
