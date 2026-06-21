# Spec Engineering

## Guiding principle

**The spec defines the product. Incidents are fixed in the spec, not in
code.**

Specs are not documentation of code — they are the prescription from
which code is produced. Ideal flow: a bug report leads to a spec diff,
and code adapts to that spec diff. Drift between spec and code is an
alarm, not normal state. Each of the 5 primitives and every convention
in this document serves this principle. If a rule does not support the
principle, it does not belong here.

---

HOW to write specs: primitives, methodology, artifacts, templates.
For WHEN each step runs in development flow: `workflows/runbooks/build/WORKFLOW.md`
(per-task flow SoT).

Specs do not exist in a vacuum. They derive from the intent tree (see
`intent.md`): vision intent -> operational intent -> action intent -> spec.
A spec without a traceable derivation chain has no intent and should
not be written.

**Scoping mode:** for high-level intent (objective, not task), scoping
mode (`skills/scoping/SKILL.md`) runs before the development process.
This file describes authoring one spec — scoping mode orchestrates L0-L3.

## Why spec engineering

Specification engineering sets the quality ceiling of the whole system.
Execution without a spec phase produces broken work that requires costly
human cleanup. Planning quality determines output quality — not the raw
capability of the executing agent.

Goal: write specs so agents only ask questions when the specification
corpus is in conflict or ambiguous.

## Hierarchy: prompt -> context -> intent -> spec

Four stacked disciplines. Errors higher in the hierarchy are more
expensive (spec is top category, so this is where focus must be highest):

| Level | Question | Error impact |
|-------|-------|---------------|
| **Prompt** | How do I say it? | Low — easy to correct |
| **Context** | What information does the agent have? | Medium — agent works with wrong/missing knowledge |
| **Intent** | What is the goal? | High — agent works in the wrong direction |
| **Spec** | What exactly should come out? | Critical — everything after that is waste |

Disciplines are cumulative: good intent needs good context. Good specs
need good intent AND good context. You can have perfect context and still
have poor intent alignment.

- **Context engineering**: shape context window so the agent has exactly
  the relevant tokens — not too many, not too few.
- **Intent engineering**: communicate goals and objectives so agents can
  work autonomously over longer time. Strategy layer.
- **Spec engineering**: treat the whole document structure as a
  specification. Refine, sharpen, validate specs for individual agent runs.

## The 5 primitives

### 1. Self-contained problem statements

Everything the agent needs is inside the spec. No hidden assumptions,
no implicit constraints. Agent should be able to solve task without
fetching extra information.

Self-contained discipline forces clarity. It exposes hidden assumptions.
It forces you to state constraints that would otherwise stay implicit.

**Who provides this:** the user. The agent (Buddy) challenges hard — asks
the difficult questions, stress-tests edge cases, uncovers gaps. But the
answers come from the user. If user notices they do not yet know enough
to delegate, that is a valid outcome.

### 2. Acceptance criteria

What does "done" mean? Three sentences an independent observer can use
to verify output — without follow-up questions.

Bad example: "Build a login page."
Good example: "Build a login page with email/password, social OAuth via
Google and GitHub, progressive 2FA display, 30-day session persistence,
and rate limiting after 5 failed attempts."

**Test question:** can I give acceptance criteria to someone who does
not know the project, and they can still decide clearly whether output
meets criteria? If no: sharpen.

### 3. Constraint architecture

Four categories that turn a loose spec into a reliable one:

| Category | Question |
|-----------|-------|
| **MUST** | What must the agent do? |
| **MUST NOT** | What is forbidden? |
| **PREFER** | If multiple valid paths exist — which one is preferred? |
| **ESCALATE** | What may the agent not decide alone? |

Every line in a constraint file must earn its place. Test: "Would
removing this line cause agent errors?" If no: remove.

**Failure modes (MUST output in every spec):** per AC ask: "What could
a smart, well-meaning agent do that technically satisfies requirement
but produces wrong outcome?" Answers become MUST NOT constraints.
A spec without failure-modes section is incomplete — P3 FAIL in spec review.

**Subtask escalation threshold (main-code-agent -> Buddy):** when
main-code-agent creates subtasks autonomously, it must escalate to Buddy
if at least one applies: (1) new DB schema or schema change,
(2) new external dependency (library, service, API), (3) interface change
affecting other agents/tasks/components, (4) touches >3 files outside
immediate task scope, (5) estimated effort deviates >50% from original
plan. On escalation: pause subtask, add incident block with
`Type: SCOPE-CREEP` or `ARCH-CONFLICT` to Buddy. Buddy decides whether
subtask needs its own spec.

### 4. Decomposition

Break large tasks into components that are independently executable,
testable, and integratable.

**Target granularity:** subtasks each <2 hours, with clear input/output
boundaries, independently verifiable.

Not all subtasks need full pre-specification. But you need to understand
all subtasks and describe what "done" looks like for each component.

**Break patterns:** abstraction layer above decomposition. Domain-specific
patterns by which a planner agent can reliably split larger work into
subtasks. They come from the user, not the agent. Examples:
- coding: setup phase -> progress documentation -> incremental implementation
- content: scoring -> gap analysis -> recommendations

### 5. Evaluation design

Not "does it look OK?" — measurable, consistent, demonstrably good.

For long-running agents, evaluation design is the only protection against
unusable output. Prompt engineering is the art of input. Evaluation
design is the art of knowing whether input worked.

Detailed evaluation patterns for different domains evolve over time.

### Convention: test section in implementation specs

Superseded by the rigorous §Test-Strategy convention below (see
§Convention: §Test-Strategy for L1+ specs). The legacy loose form
("3 items: levels, mocks, AC scenarios") is replaced by the
bug-class catalog — same intent (levels + AC coverage), enforceable
shape (named bug classes, no duplicates).

### Convention: interfaces & protocols (optional, recommended for implementation specs)

Implementation specs that define public interfaces SHOULD include an
"Interfaces & Protocols" section. Not required — but L4 interface catalog
(`docs/architecture/interfaces.md`) auto-extracts from it.

Contents (as applicable):
1. **REST API endpoints** — method, path, request/response schema
2. **NATS subjects** — subject, payload type, transport (JetStream/plain), publisher/consumer
3. **Python protocols/interfaces** — protocol classes, method signatures
4. **Config files** — path, format, what they control

Section is a summary — detailed specification stays in each relevant
spec section. Goal: fast overview of public contracts defined by this spec.

Reference examples: archive/gateway-buddy-worker-impl.md §2 (package
structure with endpoint comments), harness-core-4.md §3.2/3.3
(NATS topology tables).

### Convention: architecture diagram maintenance

If a spec introduces a **new container** (deployable unit) or a
**new component** (module inside a container):

1. Update `docs/architecture/workspace.dsl` (C4 model: element + relations + view)
2. Check/extend affected flow diagrams in `docs/architecture/flows/`
3. Extend `docs/architecture/module-flow-matrix.md` (new row/column)

The C4 model is single source of truth for system structure.
New specs that change structure without updating model create drift.

Consumer repos export C4 diagrams to their own deploy target
(e.g. via Structurizr + MkDocs). Pattern, not central service.

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
`skills/improve_codebase_architecture/SKILL.md` §Glossary —
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

- **Design-time gate:** `skills/spec_board/SKILL.md` §1.0 carries a
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
`skills/_protocols/spec-amendment-discipline.md` §What counts as
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
  `skills/spec_authoring/SKILL.md` §Artifact checklist item 5 — the
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
  `skills/code_review_board/SKILL.md` §5.
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

---

## Spec authoring, delegation, task logs

Extracted into `skills/spec_authoring/SKILL.md` (interview methodology
with solution-space exploration, spec writing, planner/worker model,
task logs, intent_chain, delegation-ready artifact).

References from `workflows/runbooks/build/WORKFLOW.md` phase Specify/Prepare:
- Specify step INTERVIEW -> `spec_authoring/SKILL.md` §Phase 1 interview methodology
- Specify step SPEC -> `spec_authoring/SKILL.md` §Phase 2 spec writing
- Prepare step DELEGATION -> `spec_authoring/SKILL.md` §Phase 4 delegation-ready

## Spec-related skills (map)

```
spec_authoring              (NEW specs + new feature sections, interview-based)
     ?
retroactive_spec_update     (EXISTING specs, code-as-evidence catch-up,
                             prevents feature creep)
     ?
spec_amendment_verification (read-only cross-spec consistency check)
     ?
spec_board                  (rebuild-ready quality review against 5 dimensions)
```

All four skills share the guiding principle: **spec defines the product.
Incidents are fixed in the spec, not in code.** Different phases in the
spec lifecycle — one shared goal.

**Boundary `spec_authoring` vs `retroactive_spec_update`:**
if code for the new section **does not yet exist** -> authoring
(interview, user intent, solution space). If code **already exists**
and spec only needs to catch up -> retroactive (code walkthrough,
no feature suggestions).

**`spec_update`** (old skill) is **deprecated** — it was ambiguous because
it mixed both cases. Its stub points to the two successors.
