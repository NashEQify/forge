# Testing — run strategy

Step-loaded unit of `skills/testing/SKILL.md`. Read it when deciding a test plan's run strategy, before running tests
in an implementation round, fix pass, review or verification, and before reusing an already executed check as
evidence. The spec-freshness check before execution stays in `SKILL.md`.

## Run strategy

| Trigger | Scope |
|---------|-------|
| Commit | L0 |
| Spec / process | L0 + L1 |
| Code | L0 + L2 + L3 (the selected set, below) |
| Workflow | L0 + L1 + L4 |
| Milestone | L0 - L5 |
| Boot | Entropy audit (L5 light) |

Spec-process integration: `Interview → Spec → Review → TEST
DESIGN → PRE-IMPL EVAL → Decomposition → Delegation`.

**Qualified execution evidence.** An already executed check may satisfy the same
execution obligation only after inspecting its complete original receipt and
establishing applicability. Compare the checked source/subject and relevant later
changes; environment, tool and configuration assumptions; covered consumers and
test/oracle scope; actual producer; results, failures and limits. Record that
comparison in the existing brief or verification return, without a separate form.

Reused execution does not substitute for independent source, approach or oracle
scrutiny, required reviewer perspectives, or actual direct adversarial probes.
Changed assumptions or oracles, unexplained failures or unestablished applicability
reopen the relevant execution. Attribute reused results to their actual producer;
never describe them as reviewer-executed.

### Test selection

This is the single home of the suite-scope rule; other instructions point here.

**Run the tests that exercise the change.** Implementation rounds, fix passes, reviews and
verification run the test files that exercise the changed paths:
`python3 "$FRAMEWORK_DIR/scripts/select_tests.py"`, run from the project root with the
changes (`--staged`, `--worktree`, `--diff <base>..HEAD` for committed work, or the
paths), prints `result: targeted` and the files, or `result: broad` with its reasons.
Read the result line first. An empty targeted set means no test exercises the change, and
`--format args` then prints nothing; no changed paths at all is an error (exit 2), not an
empty set. With `broad`, the listed targeted files may run first for an early signal; the
broad run is still due. Do not replace the
selection with a hand-picked set: tests coupled through an imported module or a script run
by name are what hand selection misses. `--explain <path>` shows why a test was
chosen. Where the selector does not apply (no pytest suite), list the tests that
reference the changed files and how you found them.

**Instruction-only Markdown runs no pytest.** The selector lists Markdown that no test reads
directly as `light-path: <path>`. Its verification is the light-path checks
(`framework/installation-activation.md` §Light path). A test that reads the file's content
directly is selected and runs.

**Code selects the tests that exercise it.** For code the selector follows imports, exact
paths and scripts run by name. A test that only copies the framework tree is not selected
for a code change unless it also exercises the changed module. A code path no test exercises directly answers `broad`.

**No whole-suite run per change.** The whole suite runs at the project's full gate
(`lean-suite.md` §Change-scoped runs and the full gate). It is due for a change only when the
selector returns `broad` (shared test infrastructure, a path no test maps, a cross-cutting
entry) or when the change touches a safety floor (`skills/adversary_test_plan/SKILL.md` §When
to call). That due run is the broad run: once, after the last change to the code under test
and before the merge, by the full gate's runner (without a named runner, the role that merges). A small code change after that run, such as a fix pass, runs only the tests
that exercise the changed module directly. The broad run stands when no other code changed
after it. A small fix after a review in which every seat passed runs only the tests that
failed before it, until green (`skills/code_review_board/review-package.md` §Small fix after a
passing review).

**Every run is parallel** (`lean-suite.md`). A selected-set run, which names test paths, runs
the tests on the project's full-gate list that it picks (`lean-suite.md` §pytest shape).

**No rerun after a hash-checked transfer.** When the tested bytes reach their target
unchanged and each path is hash-checked, the broad suite is not run again: activation
verifies the installation (entrypoints, fingerprint, closure, a fresh session), not the
code. A selected-set run on the target is optional evidence about its environment.

**Test runs are rounds.** A budget names its test runs, and a run beyond the selected
sets and a due broad run takes the same comparison as any further round
(`agents/buddy/delegation.md` §Delegation hygiene, Cumulative effort).

The selector follows imports, repository paths written in test and module code, copied
trees and scripts named in shell scripts. It cannot follow paths or module names computed
at runtime (for example targets read from a YAML file) or inputs read only inside
isolated subprocesses (plan validation reads `CLAUDE.md`, `AGENTS.md` and other framework
files that way). The commit hooks cover plan-validation inputs (PLAN-VALIDATE); a replay that
shows another such load adds a cross-cutting entry, which then answers `broad`. For data files
(YAML, JSON, templates) tree copies still count, so such a targeted set can be large. Failure
attribution for the broad run:
`skills/convergence_loop/SKILL.md` §Net-new failures from the full-suite sweep.

**Shared fixtures are collision surfaces.** Before each gate run, check
`git status` on shared `tests/**` fixtures (`conftest.py`, fixture
data). An uncommitted change from a parallel session is resolved before
the round, not worked around in scratch copies.
