---
name: improve-codebase-architecture
description: >
  Codebase-wide architecture improvement via the deep-modules
  pattern (Ousterhout / Feathers). Strict glossary (module /
  interface / implementation / depth / seam / adapter /
  leverage / locality). Deletion test. 3 phases (explore /
  present / grill). Use when refactoring opportunities,
  consolidating tightly-coupled modules, making the codebase
  more testable + AI-navigable. Periodic (every few days), not
  diff-centric.
status: active
invocation:
  primary: user-facing
  secondary: [workflow-step]
  trigger_patterns:
    - "improve architecture"
    - "find refactoring opportunities"
    - "deepening opportunities"
    - "consolidate modules"
    - "make testable"
    - "codebase walk"
disable-model-invocation: false
---

# Skill: improve-codebase-architecture

## Purpose

Surface architectural friction and propose **deepening
opportunities** — refactors that turn shallow modules into
deep modules. The goal is testability + AI-navigability.

Complementary to existing review skills:
- `code_review_board` (L1/L2) is **diff-centric** — review of
  recent changes.
- `architecture_coherence_review` is **cross-spec** — interface
  contracts between specs.
- `improve_codebase_architecture` is **codebase-wide +
  periodic** — an every-few-days friction walk, not
  diff-centric.

Distinct: not "what's wrong with this PR?", but "where does
friction accumulate across the whole codebase, and where would
deepening concentrate complexity?".

## Source

Lifted from `github.com/mattpocock/skills`
(`skills/engineering/improve-codebase-architecture/SKILL.md` +
`LANGUAGE.md`, 2026-04-30). **Adapted** to the
forge reality:
- Glossary inlined (instead of a separate LANGUAGE.md file —
  the "no altlasten" tendency).
- Concrete deep-module example in the repo, not abstract.
- The CONTEXT.md-per-project convention as a cross-ref
  (Pocock pattern, no skill — Pocock self-deprecated, but the
  pattern is valuable).
- ADR format from `documentation_and_adrs` (instead of
  Pocock's separate ADR-FORMAT.md).
- The grilling loop as a cross-ref to the pattern lift in
  `spec_authoring` + `frame` (see Phase G tier-2 pattern
  lifts).

## Standalone

Distinct from:
- `code_review_board` (L1/L2) — diff-centric, post-MCA
  return. This skill is codebase-wide + periodic; no diff
  required.
- `architecture_coherence_review` — cross-spec interface
  contracts (≥2 specs). This skill is codebase-wide within a
  single repo, not cross-spec.
- `code-architecture` persona (absorbed into code-review since
  2026-04-30) — diff-review architecture axis. This skill
  finds refactor candidates, not review-of-existing-code.
- `frame` — problem-analysis discipline. This skill is the
  codebase-walk discipline (anchored on concrete files +
  modules).

What only this skill delivers:
- **Strict glossary** (module / interface / implementation /
  depth / seam / adapter / leverage / locality) —
  disciplinary vocabulary, not "component / service / API /
  boundary".
- **Deletion test** as an identification tool for shallow
  modules.
- **One-adapter-hypothetical / two-adapters-real rule** as
  anti-YAGNI for abstractions.
- 3-phase loop (explore organic → present numbered candidates
  → grilling loop with the user).
- Inline side effects: update CONTEXT.md / offer an ADR on
  rejection.

## When to call

- The user wants to improve architecture, find refactor
  opportunities, or make the codebase AI-navigable +
  testable.
- Periodic (Pocock recommendation: every-few-days continuous
  refactor).
- After larger feature additions when "it feels messy".
- Before onboarding a new maintainer / agent — friction map
  as an entry tool.
- When tests test implementation instead of behaviour —
  symptom that modules are shallow.

### Do not call for

- PR diff review → `code_review_board` L1 / L2.
- Cross-spec interface check → `architecture_coherence_review`.
- Single-module refactor with a clear plan → direct MCA
  delegation.
- Performance optimization (hot path) → `code-review`
  performance axis.

## Glossary (strict)

Use these terms consistently in **every** proposal. Drift is
forbidden — not "component / service / API / boundary"
instead.

### Terms

**Module**
Anything with an interface and an implementation. Deliberately
scale-agnostic — applies equally to function / class /
package / tier-spanning slice.
*Avoid:* unit, component, service.

**Interface**
Everything a caller must know to use the module correctly.
Includes the type signature, but also invariants, ordering
constraints, error modes, required configuration, performance
characteristics.
*Avoid:* API, signature (too narrow — they only refer to the
type-level surface).

**Implementation**
What sits inside the module — the code body. Distinct from
**adapter**: a thing can be a small adapter with a large
implementation (a Postgres repo) or a large adapter with a
small implementation (an in-memory fake). "Adapter" when the
seam is the topic; "implementation" otherwise.

**Depth**
Leverage at the interface — the amount of behaviour a caller
(or test) can exercise per unit of interface learned. A module
is **deep** when a large amount of behaviour sits behind a
small interface. A module is **shallow** when the interface is
nearly as complex as the implementation.

**Seam** *(after Michael Feathers)*
A place where behaviour can be altered without editing in
place. The *location* at which a module's interface lives.
Where the seam lies is its own design decision, distinct from
what sits behind it.
*Avoid:* boundary (overloaded with DDD's bounded context).

**Adapter**
A concrete thing that satisfies an interface at a seam.
Describes the *role* (which slot is filled), not the substance
(what's inside).

**Leverage**
What callers gain from depth. More capability per unit of
interface they have to learn. One implementation pays back
across N call sites + M tests.

**Locality**
What maintainers gain from depth. Change, bugs, knowledge,
verification concentrate in one place instead of spreading
across callers. Fix once, fixed everywhere.

### Principles

- **Depth is a property of the interface, not the
  implementation.** A deep module can be internally composed
  of small, mockable, swappable parts — those just aren't
  part of the interface. A module can have **internal seams**
  (private to the implementation, used by its own tests) as
  well as an **external seam** at the interface.

- **Deletion test.** Imagine deleting the module. If
  complexity vanishes — the module was a pass-through (it
  wasn't productive). If complexity reappears across N
  callers — the module earned its keep.

- **The interface is the test surface.** Caller and tests
  cross the same seam. When you want to test *past* the
  interface, the module is probably the wrong shape.

- **One adapter = hypothetical seam. Two adapters = real
  seam.** Don't introduce a seam unless something actually
  varies across it. Anti-YAGNI for abstractions.

### Relationships

- A **module** has exactly one **interface** (the surface it
  presents to callers + tests).
- **Depth** is a property of a **module**, measured against
  its **interface**.
- A **seam** is where a **module**'s **interface** lives.
- An **adapter** sits at a **seam** and satisfies the
  **interface**.
- **Depth** produces **leverage** for callers + **locality**
  for maintainers.

### Rejected framings (DO NOT use)

- **Depth as the ratio of implementation lines to interface
  lines** (Ousterhout's original): rewards
  padding-the-implementation. We use depth-as-leverage.
- **"Interface" as the TypeScript `interface` keyword or a
  class's public methods**: too narrow — interface here
  includes every fact a caller has to know.
- **"Boundary":** overloaded with DDD's bounded context. Say
  **seam** or **interface** instead.

## Process

### Phase 1: Explore

Read the project's domain glossary (CONTEXT.md if it exists)
and any ADRs in the area you're touching first.

Then use the Agent tool with `subagent_type=Explore` (CC
native) to walk through the codebase. Don't follow rigid
heuristics — explore **organically** and note where you
experience friction:

- Where does understanding one concept require bouncing
  between many small modules?
- Where are modules **shallow** — interface nearly as complex
  as implementation?
- Where were pure functions extracted just-for-testability,
  but the real bugs hide in HOW they are called (no
  **locality**)?
- Where do tightly coupled modules leak across their seams?
- Which parts of the codebase are untested or
  hard-to-test through their current interface?

**Apply the deletion test** to anything you suspect is
shallow: would deletion concentrate complexity or just shift
it? A "yes, it concentrates" is the signal you want.

#### BuddyAI-specific friction hotspots

- **Brain facade:** deep module (every DB access on brain
  tables flows through a single interface). When new code
  goes direct-DB instead of facade — seam break.
- **5-layer model** (knowledge → runtime → intelligence →
  cross-cutting → interface): imports must flow downwards or
  within. Friction on cross-layer imports.
- **NATS subjects:** the events/ package is shared. Local
  event definitions are friction.
- **Pydantic AppError vs HTTPException:** mixed pattern is
  friction.
- **asyncpg vs Brain-Facade direct access:** bypass is
  friction.

### Phase 2: present candidates

Present a numbered list of deepening opportunities. Per
candidate:

- **Files** — which files / modules are involved.
- **Problem** — why the current architecture causes friction
  (use the glossary: shallow / leaky seam / no locality /
  etc).
- **Solution** — plain-English description of what would
  change.
- **Benefits** — explained in terms of **locality** +
  **leverage**, and how tests get better.

**Use CONTEXT.md vocabulary for the domain, and the strict
glossary for the architecture.** When `CONTEXT.md` (if
present) defines "Order", talk about "the Order intake
**module**" — not "the FooBarHandler", not "the Order
**service**".

**ADR conflicts:** when a candidate contradicts an existing
ADR, only surface it when the friction is real enough to
revisit the ADR. Mark clearly (e.g. *"contradicts ADR-0007 —
but worth reopening because…"*). Don't list every theoretical
refactor an ADR forbids.

**Important:** do NOT propose interfaces yet. Ask the user:
*"Which of these opportunities do you want to explore?"*

### Phase 3: grilling loop

Once the user picks a candidate, drop into a grilling
conversation. Walk the design tree with them — constraints /
dependencies / the shape of the deepened module / what sits
behind the seam / which tests survive.

**Side effects happen inline as decisions crystallize:**

- **Naming a deepened module after a concept that isn't in
  `CONTEXT.md`?** Add the term to CONTEXT.md (lazy-create if
  the file doesn't exist). Same discipline as the
  `grill-with-docs` pattern.

- **Sharpening a fuzzy term during the conversation?** Update
  CONTEXT.md right there.

- **User rejected the candidate with a load-bearing reason?**
  Offer an ADR, framed as: *"Want me to record this as an ADR
  so future architecture reviews don't re-suggest it?"* Only
  offer if:
  1. **Hard to reverse** (cost meaningful).
  2. **Surprising without context** (a future reader asks
     "why this way?").
  3. **Result of a real trade-off** (genuine alternatives,
     picked one for specific reasons).

  When any of the three are missing → skip the ADR.
  Cross-ref `documentation_and_adrs` for ADR format. When
  Pattern lift G.6 is done: ADR-discipline triple is
  absorbed into knowledge_capture.

- **Want to explore alternative interfaces for the deepened
  module?** → cross-ref
  `skills/api_and_interface_design/SKILL.md` phase 3
  contract-first.

## Red flags

- A proposal that uses "service" / "component" / "boundary"
  vocabulary instead of the strict glossary (drift).
- A candidate without a files list (too abstract to decide
  on).
- Solution description without locality + leverage
  argumentation.
- A proposal that increases test coverage without changing
  the module (that's symptom treatment, not deep-module).
- Proposing a new seam with only one adapter ("diamond" risk
  — hypothetical seam).
- A proposal that violates its own CONTEXT.md vocabulary
  (domain drift).
- A refactor plan without checking whether tests still test
  the right thing.

## Common rationalizations

| Rationalization | Reality |
|---|---|
| "It's just a small refactor" | Several small refactors without glossary discipline accumulate as vocabulary drift. |
| "Component / service / API is standard language" | Standard isn't precise enough for deep-modules discipline. The strict glossary prevents drift. |
| "We extract that into a util module" | Util is a pattern break. A deep module has behaviour + locality. Util is pass-through. |
| "Several small modules are more testable" | Test against implementation, not behaviour. A deep module with a small interface is easier to test (the interface is the test surface). |
| "We add the adapter prophylactically" | One adapter = hypothetical seam. Two adapters = real seam. Adapter only when something actually varies across it. |
| "Pure function = automatically good" | A pure function without locality (bug hides in HOW it's called) is shallow + leaky. |
| "We use DDD's bounded context" | "Boundary" is overloaded. Say **seam** + **interface** in this skill's vocabulary. |

## Contract

### INPUT
- **Required:** codebase access (repo locally or via Read
  tool).
- **Required:** clear trigger (user request for an
  architecture improvement, or a periodic
  every-few-days run).
- **Optional:** CONTEXT.md with a domain glossary (the skill
  uses it when present, lazy-creates when absent).
- **Optional:** docs/decisions/ or docs/adr/ with ADRs.
- **Context:** this skill (with the strict glossary),
  `skills/_protocols/skill-guardrails.md`,
  `skills/documentation_and_adrs/SKILL.md`.

### OUTPUT
**DELIVERS:**
- Phase 1 friction map (organic, qualitative — where does the
  reviewer experience friction?).
- Phase 2 numbered candidate list (files / problem / solution
  / benefits) with strict-glossary vocabulary.
- Phase 3 grilling conversation per picked candidate with a
  design-tree walk.
- Inline side effects: CONTEXT.md updates / ADRs on rejection
  / cross-ref to api_and_interface_design when interface
  design is needed.

**DOES NOT DELIVER:**
- No implementation of the refactors — only decision
  material.
- No diff review — `code_review_board` is a different
  domain.
- No cross-spec review — `architecture_coherence_review` is
  a different domain.

**ENABLES:**
- A codebase-wide refactor roadmap.
- Vocabulary discipline (anti-drift).
- Clear decisions about seams / adapters / module shapes.
- Testability improvement via the deep-module pattern.

### DONE
- Friction map documented (phase 1 output).
- ≥3 numbered candidates presented in the complete format.
- The user has picked which candidates to explore (phase 2
  gate).
- Grilling loop for picked candidates done with the
  design-tree walk (phase 3).
- CONTEXT.md updates / ADRs / cross-refs done inline.
- Strict glossary used consistently (no "service" /
  "component" / "boundary" drift).

### FAIL
- **Retry:** vocabulary drift detected → rewrite candidates
  with the strict glossary.
- **Escalate:** ≥2 candidates contradict an existing ADR →
  user decision whether to revisit the ADRs.
- **Abort:** no friction found → the codebase is already
  deep + clean. The skill is not needed now; defer to the
  next run.

## See also

- `skills/_protocols/skill-guardrails.md` — anti-patterns.
- `skills/api_and_interface_design/SKILL.md` — phase 3
  grilling loop invokes contract-first when interface design
  is needed.
- `skills/documentation_and_adrs/SKILL.md` — ADR format on
  rejection.
- `skills/code_review_board/SKILL.md` — diff counterpart.
- `skills/architecture_coherence_review/SKILL.md` —
  cross-spec counterpart.
- `skills/deprecation_and_migration/SKILL.md` — when a
  refactor retires an old system.
