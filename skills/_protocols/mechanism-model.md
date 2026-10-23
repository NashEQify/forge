# Protocol: Mechanism Lifecycle Model (`§Mechanism-Lifecycle`)

One table that states a mechanism end to end — every state carrier, every
operation that changes it, who produces and consumes each, which invariant
holds on each transition, and which build places each cell —
written once in the authoring seat and read by every later step. The unit of
spec review, test design, brief, fix brief and re-verify on a mechanism is a
**cell of this table**, not a finding and not the last diff.

**Consumed by:** `framework/spec-engineering.md` §Convention:
§Mechanism-Lifecycle; `skills/spec_authoring/SKILL.md` artifact checklist;
`skills/spec_board/SKILL.md` §1.0 pre-gate, §2, §4b, §6;
`skills/spec_amendment_verification/SKILL.md` CHECK; `skills/testing/SKILL.md`
§Derivation from §Mechanism-Lifecycle; `agents/brief-architect.md`;
`skills/_protocols/mca-brief-template.md` §structural_invariants;
`skills/_protocols/fix-brief-template.md` §Mechanism-cells;
`skills/code_review_board/SKILL.md` §2 step 4, §3 checklist, §4 re-verify;
`skills/convergence_loop/SKILL.md` §Simplify-before-patch gate (`model` row);
`agents/code-adversary.md`, `agents/code-domain-logic.md`,
`agents/board-adversary.md`, `agents/board-implementer.md`,
`agents/code-chief.md`, `agents/code-architect-roots.md`,
`agents/code-architect-lens.md`; `agents/buddy/operational.md`;
`workflows/runbooks/build/workflow.yaml` (spec-write, board-spec, test-design,
brief-author, code-review-board).

**Why (evidence):** `docs/research/2026-10-23-end-to-end-gap/analysis.md`.
Five builds found defects of one mechanism one route at a time across many
rounds; in every case the operations × states enumeration was done post hoc
by reviewers, never once up front as an artifact. Where it was written down
(673 head soundness, 676 class edge) the side converged in one round.

---

## Trigger (when the section is required)

A spec (new or amended) introduces or changes a **state carrier**: anything
with two or more states and two or more operations — records, calls, acts,
derivations — that change it. Always included: a derived state ("X is derived
from Z"), an invariant of the form "X changes only via Y" / "never X except
Y", a lifecycle vocabulary (`open | closed | …`), a hold / pending / settlement
/ undo flow.

Not required: pure functions, formats and wording, perf work, UI text,
bookkeeping, a single-writer flag with no derived reader. Size follows the
mechanism: a two-state flag with three writers is a six-cell table.

**Retro-model (the one mid-build trigger).** A mechanism without a section
that draws a **blocking finding** (CRITICAL/HIGH, BLOCKER/MAJOR) at any board
gets a section before the first fix brief on it, written by the orchestrator
from spec + code. It is **bounded by carrier**: the carriers the finding
touches, each with every state and every operation on it (both axes, future
and beyond-MVP operations included), plus one line `Outside this model:
<carriers / mechanisms not modelled>`. Lower-severity findings and fixes
without a blocking finding do not trigger it. Skills point here; they do not
restate the trigger. Legacy specs otherwise stay untouched (no-retrofit
boundary, as for §Module-Decomposition).

## Who writes it

| Situation | Author | When |
|---|---|---|
| New spec with a state carrier | Buddy with the user in the spec interview (`spec_authoring` Phase 1–2) | before the spec board |
| Substantial amendment adding a state, operation or invariant | `brief-architect mode=spec_amendment` (returned inline, orchestrator integrates) | in the amendment return |
| Retro-model (§Trigger) | the orchestrator | before fix pass 1 on that mechanism |
| Any later decision on the mechanism — board ruling, simplification, user decision, mid-build LD | whoever makes the decision edits the matrix in the same change as the spec text | same commit |

The section lives **in the owning spec** (one home). Other specs that carry
part of the mechanism point at it (`see <spec> §Mechanism-Lifecycle: <name>`)
and do not copy the matrix.

## Schema

```markdown
## §Mechanism-Lifecycle: <mechanism name>

**Owner:** <spec §, task id> · **Carriers:** <state-bearing things, one line each> ·
**Cross-spec cells:** <spec § pointers, or none> · **Outside this model:** <retro-model only>

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
   (§Scope and placement).
5. **Every cell carries a placement** — `now`, `task-N` or `beyond-MVP` —
   except `unreachable` cells. See §Scope and placement.
6. **`unreachable` carries its reason** (which guard or structural fact makes
   the cell impossible) so the spec board can refute it.
7. **The matrix is updated, never re-derived.** A later pass that finds a cell
   wrong edits the cell; it does not write a second model in a log.

## Scope and placement (the vision decides what, the plan decides when)

This is the single home of the rule. Skills, personas and the runbook point
here and do not restate it.

1. **Model everything.** The vision — the active `intent.md` plus the approved
   plan, not the specs — decides **what** is modelled. The table always covers
   the whole mechanism end to end: future flows and beyond-MVP parts included.
   A part is never left out of the table because nothing calls it yet.
2. **The plan decides when.** Each cell is placed: `now` (this build),
   `task-N` (built in planned task N) or `beyond-MVP` (the plan places it
   after the MVP). A cell whose operation a production producer already calls
   at HEAD is `now`: a route that runs cannot be placed later.
3. **Flows go to their caller's task.** A **flow** — multi-step orchestration,
   call construction, flow-shaped acceptance rules (settlement, undo,
   supplement, retry, completion) — is built in the task that builds its
   caller / producer, provided that task exists in the plan **and** carries a
   `blocked_by` edge on this task. Until then this build's code **refuses the
   flow explicitly** (a guard and a refusal test, both `now`). If no such task
   is planned and the plan does not place the flow `beyond-MVP`, the flow is
   built now. A `beyond-MVP` flow is refused explicitly too and cites its plan
   / milestone entry instead of a `blocked_by` edge. A **surface** — records, types,
   validators, invariant checks, refusals — of a mechanism this task owns is
   `now` unless the plan places that part beyond the MVP.
4. **Never drop scope for lack of a consumer.** "No consumer yet" only places
   work in the right task; it never removes a cell, never marks it
   `beyond-MVP`, and never re-routes a finding to `accept`. A consumer the
   vision or plan names is a consumer at zero built instances
   (`skills/code_review_board/SKILL.md` §5 Vision-named-surface carve-out is
   the disposition-side form of this rule).

Corollaries:

- **Tests on a `task-N` / `beyond-MVP` cell are refusal tests only.** A
  fixture that fabricates the absent caller's call shape to drive the flow is
  a finding (the fixture encodes one reviewer's guess at an unbounded shape
  set). The refusal itself is a `now` cell and is fully tested.
- **"Resolved on paper" is forbidden.** A spec sentence "Task N produces
  this" places nothing; the plan entry plus the `blocked_by` edge does. The
  caller's build lifts the refusal and then owns those cells (matrix rows move
  to its scope; the pointer stays).
- The `blocked_by` edge (or, for `beyond-MVP`, the plan / milestone entry) is
  wired at the moment the cell is placed, not at close; this task's close
  checks it exists.

## Bind rules (downstream)

- **spec_board:** pre-gate FAIL when the trigger fires and the section is
  missing (specs above L0); reviewers check cells and placements; no PASS
  with an empty cell; a blocking finding on a `now` cell cannot be `residual`;
  `board-implementer` joins the pass that adds or changes a cell whose
  producer is `unbuilt` or whose placement is `task-N` / `beyond-MVP`.
- **test-design:** the property generator's axes are the matrix axes, and a
  generator whose axes span a cell **is** that cell's coverage; explicit TCs
  only for cells the generator cannot reach and for refusals of placed cells;
  `unreachable` cells need their stated reason, not a TC. The oracle is
  written from the matrix, not from the code.
- **brief:** names the cells in scope; cells outside scope are
  forbidden-adjacent or placed (`task-N` / `beyond-MVP`), never silent;
  `structural_invariants` cites matrix invariants. MCA maps each in-scope cell
  to a code site and a test (or the generator that covers it); a cell the code
  cannot honour is STOP + spec amendment, not a local decision.
- **code board:** the review brief's REQUIREMENTS MAP carries the matrix;
  adversary and domain-logic report uncovered or wrong cells as findings; the
  L1 checklist item "every in-scope cell has a guard or a test".
- **fix brief:** `§Mechanism-cells` block (cells changed · cells that must
  stay intact with their guards · matrix updated in the same change).
- **re-verify:** the scoped adversary's mandate is the mechanism, with the
  whole matrix as context; its coverage table lists the invariants and the
  matrix rows / columns the fix touches, not every cell.
- **simplify-before-patch gate:** `model` row first; `simpler_mechanism` is
  answered against the matrix; `patch` names every cell it changes.
- **verdict floor (blocking severities only):** a finding at a blocking
  severity (CRITICAL/HIGH, BLOCKER/MAJOR), or one that falsifies a stated
  invariant, on a `now` cell is `fix-now` or goes to the simplify gate —
  never `new_task`, `accept`, `watch_item` or `absorb_next`; a verdict that
  carries one open is FAIL, not PASS_WITH_RISKS. Lower severities follow the
  normal triage (`accept`, `new_task` at MEDIUM+), with the cell annotated in
  the matrix: `✗ accepted: <reason>` or `→ task-N` with the `blocked_by` edge.
  Placed cells travel as `blocked_by` edges (`beyond-MVP` cells: their plan /
  milestone entry), not as `remaining_findings` rows.
- **after a mechanism redesign** (spec gate or simplify gate): the next pass
  is a cold seat over the matrix (adversary + domain-logic on the whole
  mechanism), never an orchestrator-only verification.

## Anti-patterns

- **NOT** a states list without operations, or an operations list without
  states. INSTEAD the matrix; the cells are where the defects live.
- **NOT** writers by key / record type only. INSTEAD also every input of each
  derived state and who changes it.
- **NOT** leaving a future flow or a beyond-MVP part out of the table because
  nothing calls it yet. INSTEAD model it and place it.
- **NOT** placing a cell in another task that is not in the plan or has no
  `blocked_by` edge. INSTEAD build it now, or add the plan entry and the edge.
- **NOT** building a flow before its caller's task, driven by a fixture that
  guesses the caller's call shape. INSTEAD refuse it explicitly until then.
- **NOT** a second model in the build log after a finding. INSTEAD edit the
  section's cell in the same change.
- **NOT** a residual list of blocking routes "accepted, routed" to other
  tasks. INSTEAD placed cells with `blocked_by` wired; every blocking open
  `now` cell is fix-now or a simplification.
