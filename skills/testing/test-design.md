# Testing — test design

Step-loaded unit of `skills/testing/SKILL.md`. Read it in design mode, before deriving a test plan's test cases from
the spec. The plan's scope rule (§Test design from the change), the pre-fix witness and the coverage matrix stay in
`SKILL.md`.

### Derivation from specs

For the behaviour the change adds or changes (`SKILL.md` §Test design from the
change):

| Spec element | Test-case type | Level |
|---|---|---|
| Every AC | One positive test per changed behaviour it names | L2 / L3 |
| Every MUST NOT an AC names as a refusal | Negative test | L2 / L3 |
| Every ESCALATE | Boundary test | L3 / L4 |
| Edge cases (interview) | Regression test, only where the spec makes the case required behaviour | L2 |
| Failure modes (constraint architecture) | Smart-but-wrong caught? On a safety floor, through the adversary test plan | L2 / L3 |
| Process definitions | Simulation of concrete cases | L1 |
| Verifiable assumptions | Eval test (hypothesis with code) | Eval (3e) |
| Architecture invariants the change touches | Structural test | L0 |

### Derivation from §Test-Strategy catalog (L1+ specs only)

When spec has §Test-Strategy bug-class catalog (per
`framework/spec-engineering-l1-sections.md` §Convention: §Test-Strategy for L1+
specs), the catalog **is the test contract**:

- One TC per `bug_class` row (multi-level verification = one row).
- TC name = `test_<bug_class_slug>`.
- **New bug_class discovered (incl. adversary mode) → inline append
  to §Test-Strategy.** Bookkeeping-tier amendment, no spec_board
  re-spin (per `_protocols/spec-amendment-discipline-reconcile.md` category f).
  Single commit at adversary-run end (or folded later).
- Legacy specs without catalog: derive per upstream table above.

### Derivation from §Mechanism-Lifecycle (state carriers)

When the spec has a `§Mechanism-Lifecycle` section
(`skills/_protocols/mechanism-model.md`), the matrix is the test
contract for that mechanism, beside the bug-class catalog:

- **Generator axes = matrix axes.** A property generator over the
  mechanism produces every state × every operation (including the
  consumer-side inputs of each derived state), not the shapes the
  implementer happened to think of. A generator whose axes span a cell
  **is** that cell's coverage, asserted by the matrix oracle; a
  generator that cannot produce a cell is a plan gap.
- **Explicit TCs only where the generator does not reach:** a `→` or
  `✗` cell outside the generator's axes gets its own TC (next state +
  invariants, or guard + error); a placed (`task-N` / `beyond-MVP`)
  cell gets a refusal TC only — no fixture composes the absent caller's
  call shape; an `unreachable` cell needs its stated reason in the
  matrix, not a TC.
- **Oracle from the matrix, not from the code.** The reference oracle
  (derived-state function, invariant checker) is written as separate
  arms from the matrix rows and invariants, by someone other than the
  implementer (§Oracle discipline). A memo-equals-oracle test where both
  read the same implementation proves nothing about the cells.
- **Tests in the right world.** A TC for an exemption or a guard runs in
  the state the matrix names (e.g. "after the demotion exists"), not in a
  world where the clause trivially holds. A fixture that produces the
  defect as setup is a finding.
- Cells and bug classes are complementary: a `✗` cell without a
  `bug_class` row gets one (category (f) append); a bug class without a
  cell names which carrier it guards.

### Bug-class dedup (at creation time)

Before adding TC for a new `bug_class`, check catalog/plan for
existing coverage. Duplicate or "small variation within a class" →
do not add. **When in doubt, drop.** Real gaps surface later as
real defects (real follow-up tasks), not preemptive imagined edges.

### Execution-faithfulness (test-design)

**A test artifact is not coverage until a collected test EXECUTES it
against the real surface.** A green per-module suite is
necessary-not-sufficient — it proves module contracts, not assembled
behaviour. General discipline: for each AC's GREEN test, name the
production producer of every hand-passed input; if that producer is
the function-under-test's own caller (or an async/upstream service),
the unit is necessary-not-sufficient — require a wired companion that
drives the real producer, do not fabricate its output. Three
design-time triggers:

- **Multi-module pipeline / instrument / orchestrator** — when the
  public entry point drives a real downstream **producer whose output
  the unit tests construct by hand** (the trigger is the *producer
  seam*, not module count — pure-function composition like
  `format(parse(x))` does not qualify): design ≥1 **wire-proving
  end-to-end test** (L4) that drives the public entry point through
  the real dependency (or its sanctioned testcontainer) and asserts
  the *commissioned outcome* (the headline number / verdict-bearing
  field) — RED before implementation, alongside the per-module units.
  Board backstop: `code_review_board/brief-and-team.md` §2 REQUIREMENTS MAP
  producer/`*Consumer` tripwire (do not duplicate it here — it is the
  post-code net; this is the design-time net).
- **Pooled / singleton resource with a teardown path** — a fix that
  introduces a pooled/singleton resource carrying a
  close/teardown/invalidate path requires a test that EXECUTES the
  lifecycle (build-once + reuse + close-awaits + rebuild-on-invalidate)
  against a fake whose surface matches the **INSTALLED** SDK — plus an
  audit of whether an autouse reset-fixture masks the singleton (if so,
  the lifecycle test opts out of the reset). A memoized pure helper
  (`@lru_cache`, no teardown, no shared mutable state) does NOT qualify.
- **Golden / byte-identity / snapshot corpus** — a corpus introduced
  to satisfy a no-behaviour-change (refactor) AC MUST be imported and
  asserted by a collected pytest test in the SAME change.
  Captured-but-orphaned is an incomplete AC, not a deferred nicety. A
  present-but-inert net reads as coverage while guarding nothing.

### Oracle discipline (test-design, MUST when an oracle exists)

A differential test is only as independent as its oracle (reference
implementation, golden, property, spec-bullet arms).

- **Independence.** The implementing agent does not edit the oracle in
  the same hunk as the implementation. Oracle edits go in a separate
  diff hunk, each citing the ruling or spec clause it implements, and
  are reviewed by someone other than the implementer (adversary or
  verifier). An oracle that mirrors the code line for line, or is
  written in the same change as its spec by the same author, hides the
  gaps it shares with the code: write it from the spec bullets as
  separate arms.
- **RED skeletons against the reference.** Before the MCA dispatch, run
  every record-level RED assertion against the in-repo reference oracle
  (when one exists) and list each disagreement in the test plan. A
  skeleton that contradicts the reference is fixed or the reference is
  ruled wrong — before handoff, not during implementation.
- **Single-owner decompositions.** When a plan-time lens merges two
  copies of a rule into one contract owner, add an independent oracle
  for that owner (spec-bullet arms or properties) and relabel the old
  parity tests between the former copies as wiring tests: both sides
  now share one implementation and can no longer disagree.
- **A difference between production and oracle.** A red differential test shows that the two disagree, not which
  one is wrong. Before either side changes, decide the origin against the spec item the case tests, quoting it. The
  classes are those of the implementer's still-failing table (`skills/_protocols/mca-dispatch.md` §Tests still
  failing at the return):
  - **product:** production contradicts the item; production is fixed.
  - **oracle:** the expected value or the reference contradicts the item and production follows it; the oracle is
    repaired under Independence above.
  - **fixture:** the setup or the test's tooling (an adapter, a sort, a clock) produces the difference; it is repaired
    like the oracle.
  - **spec:** the item is silent, ambiguous or contradicted by another item, and each side follows a reading. The
    spec is amended through its owner's path (`skills/convergence_loop/cause-before-answer.md`, the spec row); the
    case stays red until the amendment lands, and the reference then follows the amended text
    (`skills/_protocols/spec-amendment-discipline-reconcile.md` §Independent references of a changed clause).
  The record that holds the difference (the still-failing row, the skeleton writer's repair line, the finding's
  verification row) names the class, the quoted item and the origin: where the wrong side took its expectation (an
  amendment the reference did not follow, an adapter, a sort). An oracle or fixture repair keeps the case and every
  assertion the item implies for it: deleting or skipping the case, marking it expected to fail, widening a tolerance
  or asserting less is not a repair, and a difference only such a change would close is of the spec class. The class
  is decided by the skeleton writer's repair, which has no implementation in context (`agents/test-skeleton-writer.md`
  §Repair of a failing test), or by Buddy's ruling on the quoted item; the implementer and a review seat only
  propose it.
- **Latency on a growing log or store.** A latency AC carries a
  two-size slope leg: measure at N and 4N and assert the growth stays
  within the stated complexity, not only the absolute budget at one
  size. One size hides superlinear terms.

### L1 Logic / semantic + Iteration protocol

L1 = simulation, completeness, consistency, DRY check, constraint
satisfaction (for process / workflow / agent-behaviour specs).
`tester` (design) defines L1 checks; Buddy runs L1-SIM in
Specify phase; `main-code-agent` calls `tester` (execution) after
implementation. Design runs inside `convergence_loop` (pass 1 full
derivation; passes 2-3 coverage gaps with rising threshold; tester
self-service gate). Detail: REFERENCE.md.
