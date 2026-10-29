# Protocol: Architecture spine

Read it when the Architecture stage of the build lifecycle runs (`workflows/runbooks/build/lifecycle.md`, its
trigger), when a spec, plan or brief touches a unit a spine binds, and when a board or lens reviews a spine. A spine is
a short file of the decisions that keep separately built units consistent. Its consumers are the authors, implementers
and reviewers of those units and the specs below it; the cost it prevents is two units built on incompatible choices,
found only when they meet.

## What goes in: the inclusion test

Candidates come from the route decision's footprint line (each `new:` entry and its consumer), the contracts the change
defines, and the parent spine's Deferred list. Ask three questions of each:

1. **Divergence:** could two units one level down, built in separate tasks or dispatches, choose incompatibly if this
   stays open?
2. **Not readable:** would a competent builder of either unit miss the right choice, because neither the contract it
   consumes, the code, nor a check that refuses the wrong choice shows it?
3. **Trade-off:** are there at least two workable choices, each with a cost?

Three yes: a decision, `AD-<n>`, unless no unit at this altitude needs it yet (`can wait` below). Any no: a Deferred
entry, with the reason below. The spine decides nothing that fails the test.

| Reason | Use it when | Write |
|---|---|---|
| `one unit` | question 1 fails: only one unit chooses | the unit or spec that decides it; a state carrier inside it goes to that spec's `§Mechanism-Lifecycle` (`skills/_protocols/mechanism-model.md` §Trigger) |
| `readable` | question 2 fails | where it is read: the contract section, the code path, or the check that refuses the wrong choice |
| `no trade-off` | question 3 fails | the one workable choice |
| `can wait` | all three pass, but no unit at this altitude is built before it matters | the event that makes it due: a named task, or the child spine that must decide it |

The contract's own shape (fields, channels, signatures) stays in the spec's Interfaces & Protocols section
(`framework/spec-engineering-implementation-specs.md`); the spine holds the decisions every unit on either side must
follow, such as a delivery guarantee or a representation used across contracts.

**Who decides.** Buddy proposes each decision in the spec interview with the realistic alternative it beats. Each
proposed choice is an intent gap (`workflows/runbooks/build/lifecycle.md` §Sizing facts): `asked` when
`framework/process-map.md` §Authorization names a reason to ask, otherwise settled; a settled choice that passes the
two tests of `skills/return_summary/SKILL.md` §Decisions I took for you goes on that list. A choice the user, an ADR or
the existing code already made is `adopted`, not proposed again.

## Format

```markdown
# Architecture spine — <scope>

Altitude: initiative | feature | unit
Governs: <the specs, units or tasks one level down>
Parent: <path to the parent spine> | none

## Inherited

| Parent decision | Binds here |
|---|---|
| AD-<n> (<parent spine path>) | <what it constrains in this scope> |

## Decisions

### AD-1 — <the decision in a few words>

- **Binds:** <the units or contracts it constrains>
- **Prevents:** <the pair of incompatible choices it stops>
- **Rule:** <what each unit must do, checkable in its code or contract>
- **Settled:** proposed | asked: "<the user's words>" | adopted: <ADR, spec section or code path>
- **Mechanism:** <spec> §Mechanism-Lifecycle: <name>

## Deferred

- <candidate> — <reason>: <what the reason table asks for>
```

- `## Inherited` only when `Parent:` names a spine; with no parent decision binding here, one line: `- none`. Each row
  cites the `Parent:` path. A decision the parent itself inherits binds through the parent and is not listed again.
- `## Deferred` always; with no candidate left, one line: `- none`. An entry may wrap onto indented lines.
- `Mechanism:` only when the decision constrains a state carrier; the other four lines always.
- IDs ascend and are never renumbered or reused. A retired decision keeps its heading and lines; its Rule becomes
  `retired, replaced by AD-<m>`.
- Decisions, not rationale. Why a hard-to-reverse choice was made goes into an ADR when
  `skills/documentation_and_adrs/SKILL.md` §ADR-discipline triple holds, and `Settled:` names it; otherwise the
  interview record holds it.
- **Where it lives:** its own file in the project's spec directory, linked from the header of every spec it governs
  (`Spine: <path>`). Linked that way it is part of the durable spec
  (`framework/spec-engineering-implementation-specs.md` §Convention: spec carriers).

## Altitudes and inheritance

| Altitude | Governs | Typical home |
|---|---|---|
| initiative | the features of one system or milestone | beside the L1 architecture spec (`skills/scoping/SKILL.md`) |
| feature | the units of one feature, built in separate tasks or dispatches | beside the feature's durable spec |
| unit | parts of one unit built in separate dispatches | beside the unit's spec |

- Write only the altitudes the work has. One change with one separately built consumer needs one spine, `Parent: none`.
- A child spine reads its parent first. Parent decisions bind read-only: listed under `## Inherited` by their parent
  ID, not restated, renumbered or re-decided. The child decides only what the parent left open: the parent's Deferred
  entries that are due, and divergences that first appear at this level. A parent entry the child decides gets
  `decided in <child path> AD-<n>` appended in the parent.
- A child decision that contradicts or weakens an inherited one is a conflict, not a local override. The change goes
  through the parent: amend the parent's decision, settled as its `Settled:` line requires (an `asked` decision goes
  back to the user), then cite the amended ID in the child.

## The mechanism model inside a unit

The mechanism model (`skills/_protocols/mechanism-model.md`) stays the tool for one mechanism inside its owning spec:
its states, operations and transition invariants. The spine never copies its cells.
- When a decision constrains a state carrier, its Rule states what every unit must do across the boundary, and
  `Mechanism:` points at the owning spec's section.
- A candidate about one unit's state carrier fails question 1 and is a `one unit` entry pointing at that model.
- A brief's `structural_invariants` cites the decisions that bind the units it touches, beside the matrix invariants
  (`skills/_protocols/mca-brief-template-decision-classes.md`).

## Binding order

A conflict ruling (`skills/_protocols/plan-conflicts.md` §Rulings) reads the approved acceptance and its exclusions
first, then the spine's decisions (parent before child), then the spec. A spec text that contradicts its spine is a
spec defect, or it asks for a spine amendment as above; the spec does not override the spine.

## Checks

- **Form:** `python3 $FRAMEWORK_DIR/scripts/consistency_check.py --check spine --spine <path>`, run from the project
  root, after each change to the spine and before the board; exit `1` lists each failure.
- **Substance:** at the spec board, `board-architect-roots` (it joins when the spec links a spine the change writes or
  amends, `skills/spec_board/depth-and-team.md` §2a) checks that each Rule is checkable and prevents its stated
  divergence, that no decision fails the inclusion test, that no Deferred entry lets two units diverge, and that no
  child decision weakens an inherited one. When `code-architect-lens` runs at plan time, it treats the decisions that bind the
  brief's modules as constraints on its recommendation.

## Source

BMAD-METHOD (MIT License, © 2025 BMad Code, LLC); Forge's register of adopted methods.
