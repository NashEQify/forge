# Spec Engineering — implementation-spec conventions

Step-loaded unit of `framework/spec-engineering.md`. Read it when authoring or reviewing a spec that prescribes code
(public interfaces, a new container or component, added structure), when deciding what of a change belongs in a
durable spec (at spec-write and at close), when writing an implementation or fix brief, when the route decision counts
two or more deliverables or a change spec passes 12,000 bytes, and when review traces a diff back to its
§Complexity-Tracking rows.

### Convention: spec carriers

A code change's specification lives in three carriers. Each holds what the others cannot:

| Carrier | Holds | Lifetime |
|---|---|---|
| Change spec: the task's acceptance, brief, plan, design note | What this change does and how, including its matrix of promised behaviours | Binding during the change. Afterwards it stays with the task's records and is not maintained; git is the record |
| Tests | The behaviour itself, case by case, as the executable spec (`skills/testing/SKILL.md` §Test design from the change) | Permanent, maintained with the code |
| Durable spec: the spec at `spec_ref`, its L1+ sections, and the UX contracts and architecture spine its header links (`skills/ux_authoring/contracts.md`, `skills/_protocols/architecture-spine.md`) | The authority for what it defines: behaviour at the level of its contract, contracts between independently built units, invariants and architecture decisions, mechanism models, UX contracts, limits a test only samples, the rationale of non-obvious choices, and what the system must not do beyond the tested cases | Permanent. Code follows it (`code-spec-fit`); the spec-drift check runs when spec-defined behaviour changes |

- **Not restated.** The durable spec names a behaviour and its contract; the cases that tests pin are not repeated
  there as prose.
- **Nothing durable left behind.** Before close, what the change decided that tests cannot hold moves from the change
  spec into the durable spec. A rationale, a limit or a cross-unit contract that lives only in a brief goes stale
  with it.
- **Readers.** `code-spec-fit` and the spec-drift check read the durable spec as the authority. Rebuild-readiness
  (the spec board) and the retroactive spec update take the durable spec together with the test matrix or the tests it
  names: behaviour at contract level in the spec, its cases in the tests.
- **No retrofit.** New specs and amendments follow this; existing specs are not rewritten to it.

Source: Superpowers (MIT License, © 2025 Jesse Vincent); Forge's register of adopted methods.

### Convention: one goal per change

A change works toward one user-facing goal, and its change spec states that goal in one sentence. Two goals means two
or more deliverables that could each be reviewed, tested and shipped without the others; the layers, files and steps
of one result are one goal.

- **Split and defer.** A request with two or more goals keeps one goal for this change: the one the others build on;
  otherwise the one the request names first. Each other goal becomes its own task (`skills/task_creation/SKILL.md`)
  with the reason for the split in its notes. The split is offered before the spec is written:
  - when it moves a criterion of the approved acceptance out of this change, to the user, through the acceptance's
    own change path (`skills/_protocols/approved-acceptance.md` §Change, resume and re-brief);
  - otherwise to the caller, who is the user for a direct request (`framework/process-map.md` §Authorization: the
    scope changes).
  The answer and its reason go into the route decision's record; outside the build workflow, into the decision or
  state file of the record directory (`skills/_protocols/mca-dispatch.md` §The files).
- **Size budget, a proposal and not a gate.** Its purpose: a long change spec hides a second goal and crowds the
  implementer's context. Of 40 recent session briefs, the single-goal ones measured 1,100 to 11,000 bytes; the one
  above 12,000 held two goals. When a change spec passes 12,000 bytes (`wc -c`), state its size to the caller and
  offer a split by goal or keeping it whole. The caller's choice stands; a kept spec records its size and the reason
  where a split's answer goes. A durable spec at `spec_ref` is not measured by this budget.
- **Fit to the delegate's context.** A brief is also cut so that its delegate finishes inside its context with room to
  spare: what it must read before it starts leaves most of its window for the work (reading the code it changes, test
  runs, a fix round). Before dispatch, the briefing agent adds up the bytes (`wc -c`) of the brief and of every file
  the brief tells the delegate to read and, for a session, of its boot units, and compares the sum with the delegate's
  context window as its host or the model's documentation states it, at about 3 bytes per token; when neither states
  it, the window assumed is written in the dispatch file. When the sum passes a third of the window, it splits by goal as above, or narrows the
  files to read to those the change touches; one goal that still does not fit is cut into steps that each end in a
  commit and a report. The brief's stop limit (`skills/_protocols/mca-brief-template.md` §Stop limit) counts what the
  delegate changed, not what it had to hold.

Source: BMAD-METHOD (MIT License, © 2025 BMad Code, LLC) and, for the fit to the delegate's context, Get Shit Done (MIT
License, © 2025 Lex Christopherson); Forge's register of adopted methods.

### Convention: interfaces & protocols (optional, recommended for implementation specs)

Implementation specs that define public interfaces SHOULD include an
"Interfaces & Protocols" section. It is not required; it gives readers one
overview of the public contracts the spec defines.

Contents (as applicable; the technologies in parentheses are examples):
1. **Request/response endpoints** — method, path, request/response schema (for example a REST API)
2. **Message channels** — channel or subject name, payload type, transport, publisher/consumer (for example NATS subjects with JetStream or plain transport)
3. **Code-level interfaces** — interface or protocol types, method signatures (for example Python protocols)
4. **Config files** — path, format, what they control

Section is a summary — detailed specification stays in each relevant
spec section. Goal: fast overview of public contracts defined by this spec.
A table per channel kind (name, payload, transport, publisher, consumer)
is a useful form for message channels.

### Convention: architecture diagram maintenance

If a spec introduces a **new container** (deployable unit) or a
**new component** (module inside a container), in the project's
repository:

1. Update `<project>/docs/architecture/workspace.dsl` (C4 model: element + relations + view)
2. Check/extend affected flow diagrams in `<project>/docs/architecture/flows/`
3. Extend `<project>/docs/architecture/module-flow-matrix.md` (new row/column)

The C4 model is single source of truth for system structure.
New specs that change structure without updating model create drift.

Consumer repos export C4 diagrams to their own deploy target
(e.g. via Structurizr + MkDocs). Pattern, not central service.

### Convention: §Complexity-Tracking for specs and briefs

Added code structure needs a stated need, as added process effort does
(Invariant 9). Every spec that prescribes code, and every implementation
or fix brief, carries a `§Complexity-Tracking` table with one row per
layer, abstraction, dependency, configuration option or guard the change
adds:

| Addition | Need | Simpler alternative it beats |
|---|---|---|
| <what, where> | <the acceptance criterion, the demonstrated failure or the named consumer that requires it> | <the more direct option, and why it does not meet that need> |

- **Kinds.** Layer: a new module boundary, wrapper or indirection.
  Abstraction: a new interface, base class, registry, generic helper or
  second representation of one model. Dependency: a library, service or
  tool. Configuration option: a flag, parameter, setting or environment
  variable. Guard: a check, branch, fallback, retry or exception handler
  for a state other than the inputs and outcomes the acceptance criteria
  name; handling those is the requested behavior, not a guard. Calling
  existing code or following an existing pattern adds no layer or
  abstraction, but what the new code does still counts: a retry through an
  existing helper is still a guard.
- **Need.** An acceptance criterion, a failure demonstrated through the
  real entry point, or a consumer the intent or plan names (a specific
  caller, user or system, not "users who might want it"). "Might be
  needed", "defensive", "symmetry" or "flexibility" without such a
  consumer is not a need: drop the addition instead of writing the row.
- **Nothing added:** the section reads `None.`, with no rows.
- **Where the rows go.** The spec holds the rows of its design; a brief
  carries the rows it implements plus its own
  (`skills/_protocols/mca-brief-template.md` §Complexity-Tracking, which
  is also the home of the stricter rule for fixes). Review traces the diff
  back to these rows (`skills/code_review_board/brief-and-team.md` §2 step 4).
- **Project-owned and extensible.** These rules are deliberately few. A
  project extends them in its own rules, for example with further kinds of
  addition or a dependency policy a row's need must meet; an extension adds
  to the rules and never removes the need column. Forge sets no fixed
  project count and no architecture style.

Source: spec-kit (MIT License, © GitHub, Inc.); Forge's register of adopted methods.

---
