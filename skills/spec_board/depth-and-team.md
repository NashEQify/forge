# Spec board — depth mode and team composition

Step-loaded unit of `skills/spec_board/SKILL.md`. Read it when deciding scope and depth mode (including the pre-gates
and the foundation flag) and assembling the team, before dispatching the board and before each later pass's team.
Section numbers are skill-wide: §0, §3, §5 and §7–§10 in `SKILL.md`, §1–§2 in `depth-and-team.md`, §4–§4b in
`checklist-and-dispatch.md`, §3a and §6–§6a in `post-pass.md`.

## 1. Depth mode

### 1.0 Proportionality gate (MANDATORY — runs before §1.1)

Default = escalate. Bookkeeping spec edits (amendment-log rows,
Step-alt examples, lessons-table rows, version bumps) systematically
fire the cross-layer / interface checks and burn a Deep pass. Gate
cuts theater. Answer 4:

1. Substantive edit ≤~30 net lines AND ≤2 sections (single change
   site, not a sweep)?
2. Mirrors visible sibling pattern in same spec (new amendment-log
   row alongside existing, new Step-alt alongside existing alts)?
3. Descriptive, not prescriptive — documents what already landed in
   code OR clarification / rewording, NOT a new rule / state / contract?
4. No new state-vocabulary, no new public-API contract, no new SSE
   event, no new schema field, no new normative rule (cross-spec-impact
   lens — if neighbour specs need to learn the change, it's contract)?

**3-of-4 yes → standard mode** regardless of §1.1 signals. spec_board
has no `light` tier; gate authorizes *staying-in-standard*, not
skipping the board.

**Skip-decision pointer:** the decision to SKIP the board entirely (a
pre-invocation call, distinct from this gate's standard-vs-Deep depth
choice) routes through these same Q3/Q4 contract-surface questions,
authored inline at the decision point per `agents/buddy/multi-perspective.md`
(board-skip discipline) — a new contract
surface there is a hard stop on the skip, regardless of an ADR-lock or a
passed amendment-verification.

**Override floor (hard escalation regardless of gate):**
- YES on **security** check (auth / consent / crypto) → ALWAYS Deep.
- YES on **full-path** (`dev_path: full`) → ALWAYS Deep.

**Pre-gate FAIL (new L1+ specs only) — two required sections:** new
L1+ spec submitted without either section → **FAIL before §1.0 runs:

1. **§Module-Decomposition missing** → FAIL. Author adds per
   `framework/spec-engineering-l1-sections.md` §Convention: §Module-Decomposition.
2. **§Test-Strategy missing** → FAIL. Author adds bug-class catalog
   per §Convention: §Test-Strategy.

**Pre-gate FAIL (any spec above L0, new or amended) — §Mechanism-Lifecycle:** the
diff introduces or changes a state carrier (two or more states, two or
more operations; any derived state; any "X changes only via Y" / "never
X" invariant; a hold / settlement / undo flow) and the owning spec has no
`§Mechanism-Lifecycle` section for it, or the section has an empty cell →
**FAIL before §1.0 runs.** Author adds / completes it per
`skills/_protocols/mechanism-model.md`. This gate applies to legacy specs
too once the amendment touches the mechanism (the no-retrofit boundary
ends at the touch).

**Board review of §Test-Strategy** (when present): every AC ≥1
bug_class row (no orphan); no duplicate bug_class (semantic dedup);
each bug_class is a noun phrase (not test-case name). Vague /
duplicate / orphan = findings (severity per impact).

Legacy specs **silent-skip** both — touch-it-fix-it via
`_protocols/spec-amendment-discipline-reconcile.md` categories (d) and (e).
Cross-layer / interface triggers yield to gate on bookkeeping;
standard→Deep on ≥1C or ≥3H still applies.

### 1.1 Scoped pre-check + 4 checks

- **Scoped pre-check:** `board_result APPROVED` (or historical `pass`) AND change ≤3 sections
  → standard (3 agents, no chief discovery). Otherwise → step 1.
- **Step 1 — 4 checks (≥1 YES → Deep):** cross-layer (consumers
  in another layer), interface (API / Pydantic / schema), full path
  (`dev_path: full`), security (auth / consent / crypto).
- All NO → standard. Standard escalates Deep on ≥1C or ≥3H.

## 2. Team composition

- **Standard:** chief + adversary + implementer + impact +
  **architect-roots** (CONDITIONAL on §2a).
- **Deep pass 1:** all 7 (+ Adv-2, Adv-3 Sonnet, Consumer Sonnet)
  + **architect-roots** (ALWAYS in pass 1).
- **Deep pass 2+:** 4 (Adv + Adv2 + Impl + Impact).
- **Deep final:** 2 (Adv + Impl).

Specialists by content: schema/API → `code-api-contract`;
readability → `board-consumer`; first principles → `board-adversary-2`.

### 2a. Architect-roots trigger

Include `board-architect-roots` when ANY of: spec has ≥6 LDs;
spec touches a state machine; diff replaces a previously-flagged
structural pattern; spec links an architecture spine the change
writes or amends (`skills/_protocols/architecture-spine.md`).

### 2b. Implementer trigger (producer check)

Include `board-implementer` — in any mode, including a lean
verification-only pass — on the pass that **adds or changes** a cell
whose producer is `unbuilt: Task N` or whose placement is `task-N` /
`beyond-MVP`, or that specifies a flow (settlement, undo, retry,
supplement, completion) whose caller does not exist in `src/` at HEAD.
A pass that leaves those cells untouched does not add the seat. Its
mandate: for each such operation, grep the producer site and confirm
the placement (planned caller task with `blocked_by` and an explicit
refusal now, or built now when no caller task is planned) or raise a
finding; a producer "specified in another task" is not a producer
(`_protocols/mechanism-model.md` §Scope and placement). The one lens
that asks "who produces this field" has caught the no-producer
CRITICALs where it ran and was absent where the flows were built on
speculation.

### 2c. After a mechanism redesign

When a pass or the Simplify-before-patch gate replaces the mechanism
(new derived state, new sole exit, new state vocabulary), the next pass
is a cold seat over the **whole updated matrix** — `board-adversary` +
`board-implementer` (or `spec-verification`) with the mandate "attack
every cell", no chief — never an orchestrator-only verification of the
fix.

**User-review prompt (foundation specs):** "What would none of
these agents see?" → `## User-Review` in consolidated. Required, no gate.
