# Spec Engineering — §Mechanism-Lifecycle

Step-loaded unit of `framework/spec-engineering.md`. Read it when a spec above L0, new or amended, introduces or
changes a state carrier, when a later ruling or a blocking finding touches a mechanism, at the spec-board pre-gate,
at test design and when a code-board brief carries the matrix. Schema SoT: `skills/_protocols/mechanism-model.md`.

### Convention: §Mechanism-Lifecycle for state-bearing specs

A spec (new or amended, any level above L0) that introduces or changes a
**state carrier** — anything with two or more states and two or more
operations that change it, including every derived state and every
"X changes only via Y" / "never X" invariant — declares a
`§Mechanism-Lifecycle: <name>` section: states per carrier, every
operation with its producer and consumer, the states × operations
matrix with every cell filled (`→next | ✗ guard | unreachable(reason)`)
and placed (`now | task-N | beyond-MVP`), the invariants per carrier
with the cells that enforce them and their enforcement locus, and the
placed cells with their owning task. The vision decides what is
modelled (the whole mechanism, beyond-MVP parts included); the plan
decides when each cell is built. Schema, trigger, authorship, the scope
and placement rule and the downstream bind rules:
`skills/_protocols/mechanism-model.md` (SoT).

The section is the mechanism's single home; other specs that carry part
of it point at it. It is written once at authoring and **updated, never
re-derived**: every later ruling, simplification or mid-build decision on
the mechanism edits the matrix in the same change as the spec text. The
unit of spec review, test design, brief, fix brief and re-verify on a
mechanism is a cell of this table, not a finding and not the last diff.

#### Enforcement

- **Design-time gate:** `skills/spec_board/depth-and-team.md` §1.0 pre-gate FAIL
  when the trigger fires and the section is missing; no PASS with an
  empty cell; a blocking finding on a `now` cell is not `residual`.
- **Test design:** `skills/testing/SKILL.md` derives the property
  generator's axes and the oracle from the matrix.
- **Review-time:** the code-board brief carries the matrix; adversary and
  domain-logic report uncovered or wrong cells.

#### No-retrofit boundary

Legacy specs stay unchanged until touched. A mechanism is "touched" by an
amendment that adds a state, operation or invariant
(`skills/_protocols/spec-amendment-discipline-reconcile.md` category (g)) **or by a
blocking finding at any board** — the bounded retro-model of
`skills/_protocols/mechanism-model.md` §Trigger.

#### What this convention is NOT

- **NOT** a state diagram in prose. The matrix is the artifact; the
  cells are where the defects live.
- **NOT** §Module-Decomposition (module shape) or §Test-Strategy (bug
  classes). It feeds both: cells name the modules' invariants and give
  the test catalog its axes.
- **NOT** a sidecar file. In-spec, one home per mechanism.
- **NOT** required where no state carrier exists; see the trigger in
  the protocol.
