# Spec Engineering

## Guiding principle

**The spec defines the product. Incidents are fixed in the spec, not in
code.**

Specs are not documentation of code — they are the prescription from
which code is produced. Ideal flow: a bug report leads to a spec diff,
and code adapts to that spec diff. Where the spec already defines the right
behaviour, it already holds the fix: a reproducing test pins it, and code
adapts. Drift between spec and code is an
alarm, not normal state. Each of the 5 primitives and every convention
in this document serves this principle. If a rule does not support the
principle, it does not belong here.

---

HOW to write specs: primitives, methodology, artifacts, templates.
For WHEN each step runs in development flow: `workflows/runbooks/build/WORKFLOW.md`
(per-task flow SoT) and its stages, `workflows/runbooks/build/lifecycle.md`.

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

### Convention: spec carriers

When deciding what of a code change belongs in the durable spec, the change spec or the tests (at spec-write and at
close): read and follow `framework/spec-engineering-implementation-specs.md` (§Convention: spec carriers: what each
carrier holds, its lifetime, what moves to the durable spec before close).

### Convention: one goal per change

When the route decision counts two or more deliverables, when a change spec (a session or implementation brief
included) passes 12,000 bytes, and before dispatching any brief (its fit to the delegate's context): read and follow
`framework/spec-engineering-implementation-specs.md` (§Convention: one goal per change: one user-facing goal, split
and defer, the size budget).

### Convention: interfaces & protocols; architecture diagram maintenance

When authoring an implementation spec that defines public interfaces, or a spec that introduces a new container or
component: read and follow `framework/spec-engineering-implementation-specs.md` (§Convention: interfaces &
protocols, §Convention: architecture diagram maintenance).

### Convention: §Module-Decomposition for L1+ specs

When authoring a new L1+ spec, when an amendment to a legacy L1+ spec touches module-boundary topics, at the
spec-board pre-gate and at code-spec-fit review: read and follow `framework/spec-engineering-l1-sections.md`
(§Module-Decomposition: vocabulary, schema, worked example, enforcement, no-retrofit boundary, what it is not).

### Convention: §Test-Strategy for L1+ specs

When authoring a new L1+ spec, when an amendment to a legacy L1+ spec touches AC scope, at the spec-board pre-gate,
at test design and at code-spec-fit review: read and follow `framework/spec-engineering-l1-sections.md`
(§Test-Strategy: bug-class vocabulary, schema, worked example, enforcement, no-retrofit boundary, what it is not).

### Convention: §Mechanism-Lifecycle for state-bearing specs

When a spec above L0, new or amended, introduces or changes a state carrier, when a later ruling or a blocking
finding touches a mechanism, at the spec-board pre-gate, at test design and when a code-board brief carries the
matrix: read and follow `framework/spec-engineering-mechanism-lifecycle.md` (the section's content, its single
home, enforcement, no-retrofit boundary, what it is not).

### Convention: §Complexity-Tracking for specs and briefs

When writing a spec that prescribes code or an implementation or fix brief, and when review traces a diff back to
its rows: read and follow `framework/spec-engineering-implementation-specs.md` (§Complexity-Tracking: the table, its
kinds, the need rule, where the rows go, project extension).

## Spec authoring, delegation, task logs

Extracted into `skills/spec_authoring/SKILL.md` (interview methodology
with solution-space exploration, spec writing, planner/worker model,
task logs, intent_chain, delegation-ready artifact).

References from `workflows/runbooks/build/WORKFLOW.md` phase Specify/Prepare:
- Specify step INTERVIEW -> `spec_authoring/SKILL.md` §Phase 1 interview methodology
- Specify step SPEC -> `spec_authoring/writing.md` §Phase 2 spec writing
- Prepare step DELEGATION -> `spec_authoring/SKILL.md` §Brief authoring

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
