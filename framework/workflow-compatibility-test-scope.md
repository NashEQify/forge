# Reviewed workflow compatibility — test-scope transitions

Step-loaded unit of `framework/workflow-compatibility.md`. Read it when a retained build or fix run is interpreted,
installed or rolled back under the test-design challenge, fix verification-scope or test-volume pairs, and when a
change to those definitions is reviewed.

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
