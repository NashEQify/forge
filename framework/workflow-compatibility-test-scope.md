# Reviewed workflow compatibility — test-scope transitions

Step-loaded unit of `framework/workflow-compatibility.md`. Read it when a retained build or fix run is interpreted,
installed or rolled back under the test-design challenge, fix verification-scope, test-volume, fix test-count
and review-round or instruction-text branch pairs, and when a change to those definitions is reviewed.

## Build test-design challenge transition

The additional exact build pair allows upgrade only. Its sole semantic change is
the `test-design` step instruction: an adversary challenge may add zero cases when
its challenge is substantive, and the count-only addition retry is removed.

| Retained obligation | Preserved interpretation |
|---|---|
| Build definition shape | Step identifiers, routes, dependencies, completion predicates, guards and commit gates are unchanged. |
| Adversary test challenge | Independent adversary/skeleton separation, invocation thresholds, required cases, meaningful witnesses and all planned assertions passing remain. Vacuous approval and unresolved coverage/oracle defects still fail. |
| Retained runs | Workflow state, completed step evidence and pauses are not rewritten, replayed or recertified. |
| Review currentness | Applicable current capture/adoption remains required; earlier reports do not become current through this mapping. |

There is no reverse or transitive allowance: the older instruction's count-only
retry is not reinstated by rollback, and older build pairs do not chain to this
one. Any further definition change fails closed until separately reviewed.


## Fix verification-scope transition

The additional exact fix pair allows upgrade only. Its semantic changes are two step
instructions. `fix-execute`: "Verify regression suite is still green before completing"
becomes "run the selected set for the fix's changes before completing", and the task's one
broad run follows the last code change. `commit-deploy`: before the status flip, the task's
broad run must have followed its last code change, and is run then if not. Both point to the
testing skill's suite-scope rule.

| Retained obligation | Preserved interpretation |
|---|---|
| Fix definition shape | Step identifiers, routes, dependencies, completion predicates, guards and commit gates are unchanged. |
| Regression evidence | The fix still makes its RED test green and runs the tests that exercise its changes before completing; the task's broad run is retained, once, after the last code change, owned by `commit-deploy`. |
| Retained runs | Workflow state, completed step evidence and pauses are not rewritten, replayed or recertified. |
| Review currentness | Applicable current capture/adoption remains required; earlier reports do not become current through this mapping. |

There is no reverse or transitive allowance: older fix pairs do not chain to this one. Any
further definition change fails closed until separately reviewed.


## Test-volume transition

The two additional exact pairs, build and fix, allow upgrade only. Their semantic changes are
step instructions. The build pair points to the testing skill's §Test design from the change and
to the adversary skill's §When to call; the fix pair points to the testing skill's §Test
selection. Both point to `skills/risk_followup_routing/SKILL.md` for review findings.
- **Build `test-design`:** the plan holds one test per changed behaviour an AC names. The
  adversary test plan and the skeleton writer run only when the change touches a safety floor
  (`skills/adversary_test_plan/SKILL.md` §When to call), no longer on AC count, cross-module
  impact or sub-build.
- **Build and fix `close-bookkeeping` (b):** remaining review findings are routed by their
  `target:` through `skills/risk_followup_routing/SKILL.md` instead of one follow-up task.
- **Fix `fix-execute` and `commit-deploy`:** the fix runs the tests that exercise its changes.
  Before the status flip, the tests the testing skill asks for have run after the last code
  change. A broad run is due only where that skill calls for one.

| Retained obligation | Preserved interpretation |
|---|---|
| Definition shape | Step identifiers, routes, dependencies, completion predicates, guards and commit gates are unchanged. |
| Regression evidence | A fix still makes its RED test green and runs the tests that exercise its changes; a due broad run still follows the last code change. |
| Adversary test challenge | On a safety floor, independent adversary/skeleton separation, meaningful witnesses and all planned assertions passing remain. |
| Review findings | Every remaining finding still reaches an owner; routing by `target:` changes its destination, not whether it is recorded. |
| Retained runs | Workflow state, completed step evidence and pauses are not rewritten, replayed or recertified. |
| Review currentness | Applicable current capture/adoption remains required; earlier reports do not become current through this mapping. |

There is no reverse or transitive allowance: older build and fix pairs do not chain to these.
Any further definition change fails closed until separately reviewed.


## Fix test-count and review-round transition

The additional exact fix pair (`143ba156…` to `1599a24a…`) allows upgrade only. It spans several
definition changes in one step, for a run whose binding last observed the fix definition at `143ba156…`, where
the earlier fix pairs end. Five step instructions changed; steps, order, routes, dependencies, completion
predicates, guards, commit gates and variables did not.
- **`test-plan`:** one test triggers the symptom, or the existing test that reaches its path is strengthened; several
  routes to the defect are cases of that test. It is still RED before the fix.
- **`fix-brief`:** the brief's test list follows the count rule: the reproduction, one test per further behaviour the
  fix promises, none for unchanged behaviour.
- **`fix-execute`:** the reproduction is the fix's test; a further test is written only for behaviour the fix brief
  lists. "Add regression coverage where it makes sense" is removed.
- **`code-review`:** the same inserted text as the build pair's `code-review-board`
  (`framework/workflow-compatibility-review-gates.md` §Review-round and architect-lens transition).
- **`commit-deploy`:** the tests that exercise the fix have run after the last code change, and are run then if not.
  A due broad run belongs to the full gate's runner (without a named runner, the role that merges): this step runs
  it only when its actor is that runner and it has not followed the last code change, and not again after a
  hash-checked transfer. The earlier text had the closing actor run it before the status flip in every case.

| Retained obligation | Preserved interpretation |
|---|---|
| Completed steps | A step completed under the earlier definition keeps its evidence; it is not replayed. Tests an earlier `fix-execute` added as regression coverage are not removed by this pair; where the run's code review is unfinished, the current added-tests check judges them, and one it rejects is removed as `fix-now` without changing the verdict (`skills/code_review_board/test-findings.md`). |
| Steps not yet run | A run that reaches one of the five steps takes its current instruction. A fix brief authored under the earlier definition is not re-authored: `fix-execute` writes the tests that brief lists. |
| Reproduction | The defect still has a test, new or strengthened, that fails before the fix and passes after it. |
| Regression evidence | The fix still runs the tests that exercise its changes before `fix-execute` completes, and in `commit-deploy` when code changed after. A due broad run (`skills/testing/run-strategy.md` §Test selection) is retained, once, after the last code change and before the merge, by the full gate's runner. It moves from `commit-deploy`, which owned it before the status flip under §Fix verification-scope transition: where the closing actor is not that runner, the status flip and the local commit may precede it. Where no merge follows the commit, the closing actor is the role that merges and runs a due broad run before the status flip. |
| Review adoption, findings and rounds | As the build pair's rows Review adoption, Review findings and Rounds already run state them, except that fix's `code-review` carries no commit gate; the commit gates stay on `fix-execute` and `commit-deploy`. |
| Retained runs | Workflow state, completed step evidence and pauses are not rewritten, replayed or recertified. The sub-fix route still skips `commit-deploy`. |
| Review currentness | Applicable current capture/adoption remains required; earlier reports do not become current through this mapping. |

Owner units the instructions point to are not fingerprinted: their current text governs retained runs with or without
this pair. There is no reverse allowance: a rollback would put a current run on a `commit-deploy` text that orders a
closing actor who is not the runner to run the whole suite, and on a `fix-execute` text inviting tests the current
added-tests check removes. There is no transitive allowance: the intermediate definitions of those days have no pair,
and older fix pairs do not chain to this one. Any further definition change fails closed until separately reviewed.

## Instruction-text branch transition

The build definition changed only in the `mca-implementation` step's `instruction:` text. Its main-code-agent
sentence is narrowed to product code, and a second sentence covers instruction text, text an agent follows (a skill,
a role or agent file, a rules file, a step text; in the Forge repository a planned path under the instruction roots
of `skills/_protocols/instruction-form.md` §Read-path record): Buddy writes it himself, calls the
`instruction_authoring` skill before writing it, and puts the read-path record into the commit message, which the
Forge repository's commit hook checks. Steps, ids, order, routes, gates, completion checks and variables are
unchanged.

| Retained obligation | Preserved interpretation |
|---|---|
| Completed `mca-implementation` | Keeps its evidence; it is not replayed. |
| In-progress `mca-implementation` | Work already written keeps its evidence; instruction text not yet written follows the current text. A commit of instruction text, written before or after, carries the read-path record where the commit hook checks it. |
| Brief authored under the earlier definition | Not re-authored; the current step text decides who writes an instruction-text path, over the brief's writer. |
| Pending `mca-implementation` | Takes the current text; product code goes to main-code-agent as before. |
| Read-path record | In the Forge repository unchanged: the commit-message hook already refused an instruction-root commit without it; the text names it earlier. |

The pair is upgrade-only: the earlier text sends instruction text to main-code-agent, which the current text does not,
so no reverse allowance. There is no transitive allowance. Any further definition change fails closed until
separately reviewed.
