# Testing — lean, parallel suites

Step-loaded unit of `skills/testing/SKILL.md`. Read it when designing a test plan, ordering tests in a brief or a fix
brief, writing a test, checking the tests a change adds, retiring a mechanism that has tests, and setting up a
project's test runner. It applies in every project Forge works in. The
consumer is the developer who runs the tests after every change; the cost it prevents is a suite that grows with
near-duplicates and dead cases until every change waits on a long run.

## Each test earns its place

A test plan is checked against these rules before tests are written (`agents/tester.md`, design mode). The tests a
brief orders and the test of each finding in a fix brief follow them
(`skills/_protocols/mca-brief-template-verification.md` §Tests the brief orders,
`skills/_protocols/fix-brief-template.md` Section 5). The code review checks every test a change adds against the
first, second, fourth and sixth (`skills/code_review_board/brief-and-team.md` §2, Added tests):
- **Relevant to the change.** Each TC traces to a behaviour the change changes: an AC or a changed code path
  (`SKILL.md` §Test design from the change). Its purpose is one a consumer relies on, not the text or the presence of
  an artifact. A TC that traces to no changed behaviour, or guards only an artifact's text or presence, is
  dropped.
- **No new guard for unchanged behaviour.** A new test whose behaviour no AC, no row of the brief's test list or test
  plan (an adversary-plan row, a mechanism cell in scope and a limit the change spec names are such rows) and no
  verified finding names, and whose assertions already hold at BASE, guards what the change did not change and is
  dropped, also when it runs through a changed function. An item that must not change is guarded by an existing
  test, named where the change is ordered, or recorded there as unguarded.
- **One distinct behaviour or risk per test.** Each TC names what it alone covers (`framework/test-plan-format.md`,
  Covers): a behaviour a consumer relies on, or a risk with its bug class. A TC whose Covers repeats another's is
  dropped (`test-design.md` §Bug-class dedup).
- **No near-duplicate cases.** A parameter axis stays only where its values change an assertion or the code path under
  test (`SKILL.md` §Test design from the change); two values that pass through the same branch or the same mapping get
  one case. Two tests are judged the same way: a second test through the same entry point and the same branch, asserting
  the same outcome, becomes a case of that test or is dropped; a test through the public entry point or the real tree
  is not a duplicate of a unit test. A test that a later test supersedes (the later one fails wherever the earlier
  one fails, or the earlier one stays green with the behaviour it names removed) is removed in the change that adds
  the later one.
- **Strengthen before adding.** A gap on a path that a test already reaches (a surviving mutant, a guard no test
  pins, a vacuous assertion) is closed in that test: a stronger assertion, a further case,
  or a fixed example in an existing generator. A new test function is written only where no test reaches the path.
- **No test of the harness.** A test whose subject is test-side code (a fixture, a helper, a switch that exists for
  tests) and that no consumer outside the tests relies on is dropped; the tests that use that code are its check.
- **One test per class of findings.** Review findings of one class (one outcome reached by several routes) share one
  test with a case per route, from the first fix pass on. From the second fix pass on, a repeated class
  (Simplify-before-patch `same_class: yes`) takes its class witness, a property generator with the known findings as
  fixed examples (`skills/convergence_loop/simplify-before-patch.md` §Class witness), not a regression test each. A
  per-finding test of an earlier pass that the shared test or the witness covers is a near-duplicate: the fix brief
  of the pass that lands the shared test or the witness lists it (`skills/_protocols/fix-brief-template.md` Section
  5, `removes`), and that pass's implementer deletes it.
- **No tests for retired mechanisms.** The change that retires a mechanism removes its tests; a test kept for a
  remaining path names that path in its Covers.
- **Cheap setup, shared deliberately.** A small fixture instead of the project's live data (a test that reads the whole
  task tree or history gets slower with every entry the project adds); a fake instead of a subprocess, network or full
  tree copy where the behaviour does not live in that dependency; setup several tests share is a fixture of wider
  scope, and setup that must run once puts its tests in one group (§pytest shape); generated cases in the number the
  risk needs.
- **A test that needs the real expensive dependency** (a real install, a real service, the full case count) names it
  in its Covers and goes on the project's full-gate list with that reason.

A test the review's check rejects is deleted by the implementer in the fix pass after that review, or, when every
seat passed, as the small fix after a passing review (`skills/code_review_board/test-findings.md`).

## Parallel-safe tests

Every test is written to run in parallel with every other test, and the project's default run is parallel. A test is
parallel-safe when:
- it writes only under its own temporary directory (`tmp_path`), never to a fixed path in the repository, the home
  folder or `/tmp`;
- it uses no fixed port, lock, socket or database name: it binds port 0 and reads the port back, and a module constant
  that names a shared location is patched per test;
- it changes environment variables, the working directory and module state only through a fixture that restores them
  (`monkeypatch`);
- it does not depend on another test having run, or on the order;
- a measurement in a child process does not count what the child inherits from the worker (on Linux a forked child's
  `ru_maxrss` includes the worker's memory).

## Change-scoped runs and the full gate

After a change, the local run covers the tests the change touches: the selected set for its modules and their tests,
plus the tests that failed before it (`run-strategy.md` §Test selection). It is not the whole suite. The whole suite
runs at the project's **full gate**, which the project names with its runner and moment: CI before a merge, or without
CI the role that merges, before a merge whose broad run is due (`run-strategy.md` §Test selection) and before a
release. The full gate runs every test, the full-gate list included.

## pytest shape

Other runners take the equivalent: a worker count, a tag only the full gate includes, a variable the full gate sets.

- **Parallel default:** `pytest.ini` (or `[tool.pytest.ini_options]`) sets `addopts = -n auto --dist loadgroup`, and
  pytest-xdist is a test dependency. `-n 0` gives a serial run for debugging.
- **Full-gate list:** the root `conftest.py` keeps one dict from node ID to reason. A run of the whole suite marks those
  tests skipped with the reason; a run that names test paths (the selected set) runs them, so a listed test that
  exercises a change still runs for it; a variable the full gate sets (for example `<PROJECT>_FULL=1`) runs them in
  the whole suite.
- **Setup that must run once:** mark its tests with `xdist_group("<name>")` from `pytest_collection_modifyitems`
  decorated `@pytest.hookimpl(tryfirst=True)`, so the markers are in place before xdist's own collection hook reads
  them; check in the run's output that the group's tests carry `@<name>` and run on one worker.
- **Generated and property cases:** fewer cases outside the full gate, the full count in it, and one test that runs
  only in the full gate and asserts the full count is in effect.

```python
FULL_GATE_ONLY = {
    "tests/test_x.py::test_full_install": "real install into a scratch home",
}
FULL = os.environ.get("PROJECT_FULL") == "1"   # the full gate; a run that names test paths also runs the list

@pytest.hookimpl(tryfirst=True)
def pytest_collection_modifyitems(config, items):
    roots = {Path(config.rootpath).resolve(), Path(config.rootpath, "tests").resolve()}
    base = Path(config.invocation_params.dir)
    whole_suite = all((base / a.split("::")[0]).resolve() in roots for a in config.args)
    for item in items:
        if whole_suite and not FULL and item.nodeid in FULL_GATE_ONLY:
            item.add_marker(pytest.mark.skip(reason=f"{FULL_GATE_ONLY[item.nodeid]}; runs in the full gate"))
```
