# Code review board — findings about tests

Step-loaded unit of `skills/code_review_board/SKILL.md`. Read it at the verdict (§5) before dispositioning a finding
whose subject is a test or a test the added-tests check rejects, and before a fix brief that carries one. The
reviewers' side is `agents/_protocols/code-reviewer-protocol.md` §Findings about tests; the rules for tests are
`skills/testing/lean-suite.md` §Each test earns its place. The consumer is Buddy at the verdict; the cost it prevents
is a review round, or a new test function, for a gap that a stronger assertion closes, and a rejected test that stays.

## Which finding this is

Checked in this order; the first that holds decides.

1. **Required evidence is missing.** A rule requires the evidence by name and it is absent: an AC with no test; a fix
   whose test did not fail before the fix; the wire-proving, lifecycle or corpus test of `brief-and-team.md` §2
   step 4; the class witness of a `same_class: yes` pass; an in-scope mechanism cell without a guard, a test or a
   generator that spans it. That rule and §5's triage grade it.
2. **The product is wrong now.** A run, or a concrete input with expected and actual, shows behaviour behind the gap
   that contradicts the brief or the spec. That behaviour is the finding and is graded as a product finding.
3. **An open part of an owner-approved exit criterion** (for example surviving mutants):
   `skills/convergence_loop/at-the-cap.md` §Exit criterion decides. It is the next fix pass's input and never a
   limit.
4. **A test finding.** The code does what is required and a test reaches the path, but no assertion fails without
   the behaviour: a surviving mutant, a guard no test pins, a vacuous assertion. It is at most medium and does not
   change the verdict.
5. **A rejected added test** (`brief-and-team.md` §2, Added tests). It does not change the verdict.

## What follows

| Finding | Disposition | Who and when |
|---|---|---|
| A test finding on the guarding test of a HIGH-risk AC | `fix-now`: that test is strengthened | the implementer, in the fix pass when one follows, else as the small fix after a passing review (`review-package.md` §Small fix after a passing review) |
| A rejected added test | `fix-now`: the test is removed; a duplicate case is folded into the test it repeats | the same |
| Any other test finding | `absorb_next`: closed in the test that reaches the path, with the next product pass on those files; or `accept` with the limit recorded | the implementer of that pass |

None of the three opens a fix pass or a re-review of its own: a fix pass is opened by product findings and by the
findings of 1 to 3, and these ride with it. A test is strengthened by an assertion, a case or a fixed example in an
existing generator; that adds no test function and is not a changed expected value. The small fix's evidence is the
strengthened test red on the recorded mutant and green without it, or, for a removal, the selected set green.
