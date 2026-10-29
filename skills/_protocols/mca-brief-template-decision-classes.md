# MCA brief template — decision classes

Step-loaded unit of `skills/_protocols/mca-brief-template.md`. Read it when filling the brief's
`## Implicit-Decisions-Surfaced` block (each class's `locked` and `value`) and when writing its `## Mechanism-cells`
block. Section numbers §1–§6 are the decision classes, all in this unit; the core's sections are named, not numbered.

## Decision classes — detail

Decision classes are load-bearing downstream: MCA references
`no-NEEDS-LOCKING` decisions as plan constraints; `code_review_board`
reviewers check code against decision locks (deviation = finding);
chief uses them for triage; proportionality gates
(`code_review_board` §1.0 / `spec_board/depth-and-team.md` §1.0) use the same vocabulary
(new state-vocab / new SSE type / new public API / schema break).

### 1. schema_and_contract

What shape does the data have, what does the code call it, what does
it return back. Covers:
- Data shape produced / consumed (Pydantic model, DDL schema, event
  payload, NATS subject format).
- Symbol names that could collide with existing imports (StrEnum
  values, Pydantic models, Cypher templates, NATS subjects).
- RETURN-SUMMARY structure (SPEC_VERIFICATION field, INCIDENT block,
  L0 result, files touched).

### 2. error_and_stop

What does the code do when something is wrong, and when does MCA
stop and escalate. Covers:
- Error reactions: exception classes, retry vs fail, poison queue,
  cleanup transaction, compensation action.
- STOP+escalate conditions: architecture conflict, spec-authority
  violation, cross-layer impact > brief scope, > N file changes
  without anticipation, non-resolvable test failure.

### 3. layer_discipline

Which layer does what (publishing rights, ordering, state
transitions). Cross-layer calls require explicit authority.
Module-graph: who-talks-to-whom.

### 4. structural_invariants

Pattern-purity invariants the implementation MUST preserve or
break-with-rationale. Property-shaped: does the implementation
preserve the root-property the refactor claims to fix?

**Always required on substantial briefs** (NOT conditional on
self-assessed `architecture_touch`). `n/a` requires named reason;
bare `n/a` invalid (forces meta-reflection).

Permitted `locked` values for this class:
- `"yes — invariant locked: <name>"` — explicit pattern-class
  invariant the implementation preserves.
- `"yes — pattern audited (paths considered: <list>)"` — Buddy has
  surveyed alternative patterns and the locked LD is the root-fix.
- `"no-NEEDS-LOCKING (Buddy decision: <choice>)"` — Buddy locks in
  the brief.
- `"n/a — <why mechanical>"` — mechanical refactor / typo /
  no-architecture-touch. Reason MUST name what makes it mechanical.

Three pattern classes the invariant should defend against (mirror
`code-architect-roots` / `board-architect-roots`):
- **Smell-transfer:** new pattern has identical root-property to old.
  State the invariant the new pattern preserves.
- **Cycle-symptom-as-cause:** type erosion (`Any` / `dict`) justified
  by import-cycle. State why the cycle is necessary OR why the module
  placement is correct.
- **State-vocabulary half-coverage:** initial state squeezed into a
  working state. State the lifecycle vocabulary explicitly.

**Spine decisions.** When the spec links an architecture spine
(`_protocols/architecture-spine.md`), `structural_invariants.value` also
cites, by ID, each decision whose Binds names a unit the brief touches.

**Mechanism cells (MUST when the brief touches a state carrier).** When
the owning spec has a `§Mechanism-Lifecycle` section
(`_protocols/mechanism-model.md`), `structural_invariants.value` cites
its invariants by name, and the brief carries a `## Mechanism-cells`
block before `## Acceptance-Criteria`:

```yaml
mechanism_cells:
  section: "<spec> §Mechanism-Lifecycle: <name>"
  in_scope: ["<state> × <op>", ...]      # each maps to a code site + a test in the plan
  placed: ["<state> × <op> → task-N | beyond-MVP", ...]  # explicit refusal now; refusal tests only; blocked_by wired
  forbidden_adjacent: ["<state> × <op>", ...] # cells another task or a later build owns
```

A cell the MCA finds it cannot honour as written is STOP + spec
amendment (the matrix is edited in the same change), not a local
decision; a mid-build ruling that changes a cell without editing the
matrix is drift of category (g)
(`_protocols/spec-amendment-discipline-reconcile.md`). When the build changes a
state carrier whose spec has no section, the section comes with the spec
amendment (category (g)) or the retro-model
(`_protocols/mechanism-model.md` §Trigger) before dispatch; on a legacy
spec the build does not change, the block is `mechanism_cells: n/a —
legacy spec, carrier unchanged`. Build signoff additionally requires an explicit
`brief_contract.mechanism_cells: {status: exempt, reason: "<specific reason>"}`
declaration; the legacy scalar alone does not establish exemption. Canonical
`placed` and `forbidden_adjacent` lists may legitimately be empty.

### 5. vision_alignment

What the active `intent.md` Vision says the touched surface IS, so MCA
decides the forks the brief leaves OPEN top-down, not local-default —
the product-vision-root as an INPUT to in-flight decisions. MCA is the
one decision point where a sub-agent decides scope / defer / build
without Buddy in the loop, so the Vision-premise must travel IN the
brief.

Observable, not posture: name what the Vision calls this surface
(product deliverable / PoC consumer / internal scaffold / out-of-scope)
and the decision that follows from it. A surface the Vision names as a
deliverable is a product surface even at zero built consumers — "no
consumer yet" is not a defer-signal (cross-ref `framework/invariants.md` Inv 9 +
`code_review_board` value-floor Vision-named-surface carve-out). Uses
the standard `locked` enum.

**Defer-durability — `revisit-when:` premise tag.** The inverse case:
when the surface is NOT vision-named and the brief DOES defer on an Inv-9
"no named consumer" / value-floor-0 rationale, that defer rests on a
premise that can age — a later review with more surface can re-classify
the same degrade as a real regression. Tag the defer record with a
one-line `revisit-when:` premise (e.g.
`revisit-when: any consumer of <column> appears`) so the premise is
re-audited, not inherited as settled. The `save` close-step re-lists
OPEN `revisit-when` premises at the save boundary — the deterministic
re-surface a bare tag (attention-dependent, no performer) would not get.

**Required when the brief touches a product surface** the Vision names;
`n/a (<why — internal / mechanical / no product surface>)` otherwise.
Bare `n/a` invalid.

**Architecture reading-map — point, don't re-derive.** When the touched
surface spans a subsystem AND the project's `intent.md` names an as-built
architecture reading-map, the brief MUST point the MCA at it (the project's
coarse→fine orientation entry + the as-built flow / spec docs it indexes),
so the MCA arrives oriented instead of re-deriving the architecture from
`src/`. Per-agent re-derivation is the recurring failure: each delegated
agent re-greps the same chokepoints, and a change spanning stages silently
drops a leg / seam. Generic by contract — name the map ONLY if the
project's `intent.md` declares one; never hard-code a path here (the path
lives in the consumer's `intent.md`; this template is project-agnostic).
This is the brief-layer of a deliberate selectivity: the same pointer is
kept OUT of `dispatch-template.md` and the board scaffolds, whose contract
is to STRIP context for fresh-read anti-bias review — a map ref there would
corrupt the isolation. A build brief is the opposite contract (the MCA
SHOULD arrive oriented).

### 6. other (free-text list)

Task-specific decision classes that don't fit the standard 5.
Examples: idempotency-guarantee (event-driven systems), retry-policy
(NATS consumer config), state-machine-transitions (workflow specs),
ordering-guarantees (concurrent flows). Format: list of mappings with
`klasse + locked + value`.

---
