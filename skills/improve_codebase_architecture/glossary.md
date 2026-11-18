# Improve codebase architecture — strict glossary

Step-loaded unit of `skills/improve_codebase_architecture/SKILL.md`. Read it before exploring (Phase 1) and before
writing any candidate, proposal or finding in deep-module vocabulary (module, interface, implementation, depth, seam,
adapter, leverage, locality), including when another skill or persona applies this vocabulary.

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
