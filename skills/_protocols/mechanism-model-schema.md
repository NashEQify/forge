# Mechanism lifecycle model — schema and content rules

Step-loaded unit of `skills/_protocols/mechanism-model.md`. Read it when writing or editing a
`§Mechanism-Lifecycle` section (spec interview, amendment, retro-model, any later decision that edits the matrix),
and when a board checks the section's cells. Placement of each cell follows `mechanism-model.md` §Scope and
placement.

## Schema

```markdown
## §Mechanism-Lifecycle: <mechanism name>

**Owner:** <spec §, task id> · **Carriers:** <state-bearing things, one line each> ·
**Cross-spec cells:** <spec § pointers, or none> · **Outside this model:** <retro-model only> ·
**Derived:** <drill record; owner approval of its axioms, quoted with its place; after RL-{n}, the last ruling then> (only after a drill,
`skills/convergence_loop/derive-and-exit.md`; cells it decides cite their axiom)

### States
<per carrier: every state incl. the absent / initial state and every terminal state;
 derived states name the inputs they are computed from>

### Operations
| op | kind (surface / flow) | producer (code site, or `unbuilt: Task N` / `beyond-MVP`) | consumer(s) (code site, or the vision / plan entry that names it) | actor |
|---|---|---|---|---|

### Matrix
| op ↓ / state → | <s0> | <s1> | … |
|---|---|---|---|
| <op> | →<next> · now | ✗ <guard / error> · now | →<next> · task-N | →<next> · beyond-MVP | unreachable(<reason>) |

### Invariants
| invariant | carrier | cells that enforce it | enforcement locus (record / call / transaction / derived) |
|---|---|---|---|

### Placed cells (not built in this build)
| cell | placement (`task-N` / `beyond-MVP`) | why there (caller task N builds the flow · plan places it beyond the MVP) | `blocked_by` wired | what this build does (explicit refusal; surface it builds) |
|---|---|---|---|---|
```

### Content rules

1. **No empty cell at lock.** A cell the author cannot fill is a finding
   (spec board: MAJOR/HIGH), not a blank or a `?`.
2. **Both axes.** Enumerate operations from the consumer side too: for every
   input of a derived state, which writer changes it? A writer list by key type
   alone misses the un-keyed input (673); a record-level view alone misses the
   after-the-fact routes (678).
3. **Every invariant per carrier**, not only the one the findings cluster on.
   Each names the cells that enforce it and its enforcement locus. Moving a
   check between loci (call → transaction → derived) is a matrix edit and is
   recorded as one.
4. **Producers are grepped, not recalled.** `unbuilt: Task N` requires a grep
   showing no production construction site at HEAD (test harnesses, fixtures
   and the authority's own validation code are not producers). The spec's own
   prose naming a producer is not evidence that it exists. The grep states
   what exists; it does not decide what is modelled or when it is built
   (`mechanism-model.md` §Scope and placement).
5. **Every cell carries a placement** — `now`, `task-N` or `beyond-MVP` —
   except `unreachable` cells. See `mechanism-model.md` §Scope and placement.
6. **`unreachable` carries its reason** (which guard or structural fact makes
   the cell impossible) so the spec board can refute it.
7. **The matrix is updated, never re-derived.** A later pass that finds a cell
   wrong edits the cell; it does not write a second model in a log.
