# Spec Engineering — L1+ spec sections

Step-loaded unit of `framework/spec-engineering.md`. Read it when authoring a new L1+ spec, when an amendment to a
legacy L1+ spec touches module-boundary topics or AC scope, at the spec-board pre-gate, when test design derives
cases from the bug-class catalog, and at code-spec-fit review.

### Convention: §Module-Decomposition for L1+ specs

Every **new L1+ spec** (per `skills/scoping/SKILL.md` §Spec hierarchy)
declares a `§Module-Decomposition` section. The section is the
design-time anchor for the implementation shape: which modules
realize the contract, what each module is responsible for, what its
interface hides, how it relates to siblings inside the same spec.

A spec stays a conceptual unit — one contract, one spec. The
decomposition is implementation-distribution, not spec-split.
Multiple modules under one spec is the norm; one spec per output
file is **not** the pattern. Modules are listed as file paths
**or** conceptual module names — author's choice per spec.
Prefer file paths when the files already exist or the spec drives
existing-file edits; prefer conceptual names when the spec is
greenfield and the file layout is still in flux.

**L0 specs are exempt.** L0 (intent / vision specs) declare goal +
scope, not implementation — there is no decomposition to anchor.
The rule applies from L1 (capability spec) upwards.

#### Vocabulary (strict)

Use the deep-modules glossary from
`skills/improve_codebase_architecture/glossary.md` §Glossary —
**module / interface / implementation / depth / seam / leverage /
locality**. Vocabulary drift into "service / component / boundary /
API / signature" in this section breaks the rule's anchor and is a
finding at review-time.

#### Schema (prose-per-module, 4 components)

```markdown
## §Module-Decomposition

This spec describes one contract (<one-line contract restatement>),
distributed across N modules:

### Module: <name-or-path>

- **Responsibility (one sentence):** <single-responsibility statement>.
- **Interface (what callers see, what the module hides):** <interface-narrowness statement>.
- **Relation to siblings:** <one sentence per neighbour module — calls go through declared seams; no leaky dependencies>.

### Module: <next>

...
```

#### Worked example

For the planned code-architect-lens spec (when authored):

```markdown
## §Module-Decomposition

This spec describes one contract (code-architect-lens — preventive
Ousterhout deep-modules review pre-brief-architect), distributed
across three conceptual modules:

### Module: Persona

- **Responsibility:** carry the deep-modules glossary + 3-phase
  exploration protocol verbatim into a fresh-context agent identity.
- **Interface:** input — Read tool + repo access; output — structured
  module-state per touched module (no execution, no Edit). Hides the
  prompt-assembly mechanics from callers.
- **Relation to siblings:** consumes Trigger-decision's "should fire"
  boolean as gate; emits to Output-contract for orchestrator ingestion.

### Module: Trigger-decision

- **Responsibility:** decide whether a brief-architect dispatch crosses
  the scope-shape threshold (≥3 touched modules OR new subsystem OR
  effort L|XL).
- **Interface:** input — brief-architect dispatch params; output —
  fire-or-skip boolean + one-line rationale. Threshold-rationale is
  part of the interface (callers need it for observability).
- **Relation to siblings:** upstream of Persona (gates whether the
  lens runs at all); independent of Output-contract.

### Module: Output-contract

- **Responsibility:** define the structured output the orchestrator
  parses (module-state + decomposition-recommendation + sign-off
  field: lens_clear | lens_with_decomposition | escalate).
- **Interface:** input — lens-persona returns; output —
  schema-validated block that brief-architect ingests as plan-input.
  The schema is the load-bearing surface; the prose is unconstrained.
- **Relation to siblings:** downstream of Persona; orthogonal to
  Trigger-decision.
```

#### Enforcement

- **Design-time gate:** `skills/spec_board/depth-and-team.md` §1.0 carries a
  pre-gate FAIL — a new L1+ spec submitted for board review without
  a §Module-Decomposition section FAILs before the proportionality
  gate runs.
- **Review-time conformance:** `agents/code-spec-fit.md` reads the
  section at code-review-time and judges whether the implemented
  module split matches the declared split (semantic alignment, not
  mechanical 1:1 path-match).

#### No-retrofit boundary

The ~300 specs in `docs/specs/` that pre-date this rule stay
unchanged. The pre-gate FAIL and the code-spec-fit conformance check
**silent-skip** legacy specs that lack the section. Incremental
coverage flows through
`skills/_protocols/spec-amendment-discipline-reconcile.md` §What counts as
divergence — category (d): when an amendment to a legacy L1+ spec
touches module-boundary topics (interface, dependency, layer, seam,
responsibility-split), the §Module-Decomposition section MUST be
added in the same commit as a §module-decomposition-add strand.

#### What this convention is NOT

- **NOT** spec-per-output-file. One spec per contract; multiple
  modules per spec.
- **NOT** a LOC budget per module. Judgment over mechanics — module
  size is a code-review judgment per `agents/_protocols/reviewer-base.md`
  §Cumulative file totals.
- **NOT** a hook-layer check. No pre-commit enforcement of section
  presence; spec_board's pre-gate FAIL is the only enforcement.
- **NOT** a replacement for the implementation-surface bullet list in
  `skills/spec_authoring/writing.md` §Artifact checklist item 5 — the
  file list is informational and stays; §Module-Decomposition adds
  the responsibility / interface / relation layer ABOVE it.

### Convention: §Test-Strategy for L1+ specs

Every new L1+ spec declares a `§Test-Strategy` section. It is the
design-time anchor for the **test contract**: which bug classes the
spec guards against, which AC each bug class belongs to, which test
levels verify them, and where the test implementation lives.

A **bug_class** is a noun-phrase naming a class of defect — not a
single test case, not a stack trace. *"empty-string DB-fallback emits
malformed catch_up"* is a bug class; *"test_X_returns_None_on_empty_input"*
is a test case derived from it. The bug class is the contract; the
test case is the implementation.

**L0 specs are exempt.** L1 (capability spec) upwards must include
the section.

#### Vocabulary (strict)

- **bug_class:** noun phrase, one per defect class. Free-text;
  semantic dedup, not ID encoding.
- **AC ref:** AC-N matching the §Acceptance Criteria section.
- **levels:** L0 / L1 / L2 / L3 / L4 / L5 per
  `skills/testing/SKILL.md` 6-level pyramid. Multiple levels allowed
  on one row (same bug class verified at multiple levels = one row,
  not multiple).
- **implementation:** `tests/` path pointer (filled when tests land;
  empty until then).

#### Schema

```markdown
## §Test-Strategy

**Levels in scope:** <which test levels apply, e.g. L2 unit + L3 integration>.
**External dependencies:** <real-vs-mocked policy, e.g. testcontainers Postgres real; LLM mocked>.

**Bug-class catalog** (one row per defect class; no duplicate bug_class):

| bug_class | AC ref | levels | implementation |
|---|---|---|---|
| <noun phrase naming defect class> | AC-1 | L2 | tests/path/to/test.py::test_name |
| <next bug class> | AC-2 | L2, L3 | tests/path |
```

#### Worked example

For a hypothetical chat-resume-attach spec:

```markdown
## §Test-Strategy

**Levels in scope:** L2 unit (peer-surface) + L3 integration (route-level).
**External dependencies:** asyncpg pool real (testcontainers); LLM mocked.

**Bug-class catalog:**

| bug_class | AC ref | levels | implementation |
|---|---|---|---|
| empty-string DB-fallback emits malformed catch_up | AC-2 | L2 | tests/chat/test_resume_attach.py::test_from_db_path_empty_partial |
| GeneratorExit on consumer aclose suppressed silently | AC-4 | L2 | tests/chat/test_resume_attach.py::test_from_live_path_client_disconnect |
| race on registry detach during route disconnect | AC-5 | L3 | tests/chat/ux_flows/test_abort_state_cleanup.py |
| graceful-degradation regression on missing in_flight_registry | AC-3 | L2, L3 | tests/chat/test_resume_attach.py + tests/chat/ux_flows/test_abort_state_cleanup.py |
```

Four bug classes, four AC mappings, all rows with non-empty `bug_class`
and named `tests/` pointer.

#### Enforcement

- **Design-time gate:** `skills/spec_board/SKILL.md` pre-gate FAIL —
  a new L1+ spec submitted for board review without a §Test-Strategy
  section FAILs before the proportionality gate runs (mirrors
  §Module-Decomposition enforcement).
- **Spec-board review:** vague / duplicate bug_classes (semantic
  overlap, "small variation within a bug class") = board finding;
  missing AC coverage (AC-N has no bug_class row) = board finding.
- **Review-time conformance:** `agents/code-spec-fit.md` reads the
  section at code-review-time and verifies every AC has at least one
  bug_class row, every bug_class has a `tests/` pointer once tests
  land, and no duplicate bug_class survived. Spec-fit is the
  sole owner of test-coverage findings per
  `skills/code_review_board/verdict.md` §5.
- **Derivation gate (testing skill):** the test-design phase DERIVES
  TC names from the bug_class catalog — `testing/SKILL.md` forbids
  adding bug_classes that are not in the spec. A new bug_class needed
  during implementation = spec amendment, not a test plan addition.

#### No-retrofit boundary

The ~300 specs in `docs/specs/` that pre-date this rule stay
unchanged. Pre-gate FAIL and code-spec-fit conformance check
**silent-skip** legacy specs that lack the section. Incremental
coverage flows through
`skills/_protocols/spec-amendment-discipline.md`: when an amendment
to a legacy L1+ spec touches **AC scope** (new AC, AC boundary shift,
new behavior, new failure mode), the §Test-Strategy section MUST be
added in the same commit as a §test-strategy-add strand.

#### What this convention is NOT

- **NOT** a full test plan. TC bodies (names, assertions, fixtures)
  stay in the task plan as ephemeral derivation; the spec carries
  the bug_class contract only.
- **NOT** a sidecar file. In-spec, mirrors the §Module-Decomposition
  pattern. Sidecar would split a contract across two files (sync drift,
  discovery overhead).
- **NOT** a coverage report. The `implementation` column points to
  `tests/` paths but the spec does not track green/red state — that
  lives in run-time.
- **NOT** a replacement for `tests/` as the asserting SoT. The spec
  declares what bugs are guarded against; `tests/` proves the guard
  exists; the task plan is the ephemeral build artifact between them.
