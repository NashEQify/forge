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

Every implementation spec (not design spec, not ADR) MUST include a
"Test Strategy" section that defines at least:

1. Which test levels are relevant (unit, integration, contract, E2E)
2. Which external dependencies are mocked vs. tested real
3. At least one concrete test scenario per acceptance criterion

Example (from brain-foundation.md — reference):
- testcontainers for Neo4j + Postgres (real, not mocked)
- pytest fixtures for BrainFacade lifecycle
- one test scenario per AC: "search finds entity" -> AC 1, etc.

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
