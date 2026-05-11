# Build Workflow: Structural-Roots Gap

**Date:** 2026-05-09
**Trigger:** Two-iteration workflow failure on Task 467 (BuddyAI). In both
iterations the build workflow was about to ship symptom-patches over a
structurally-broken architecture. Root smells were caught only by an
explicit user challenge — not by any gate, reviewer, or persona.

The two patterns the user observed are summarised in
`docs/tasks/467-prep-brief.md` and `docs/tasks/467-prep-brief-fp2.md`
(BuddyAI repo). This document analyses the framework side: which step in
this repo's build workflow lets these classes through, and what to change.

---

## 1. Diagnosis

### 1.1 What the existing gates check

Walking the build workflow from spec-locked to merge:

| Step | What it checks | Structural-roots check? |
|---|---|---|
| `interview` (frame) | Solution space, ≥3 orthogonal approaches, bedrock drill (deep mode only) | Partial — only on auto-upgrade-to-deep, and only on the spec, not on locked decisions |
| `board` (spec_board) | Spec quality across 5 dimensions: completeness, consistency, implementability, interface contracts, dependencies | No — checks the spec; doesn't audit the locked decisions for pattern purity |
| `delegation-artefact` | 6 mandatory decision classes: `schema_shape`, `error_handling`, `layer_discipline`, `naming_collisions`, `return_format_spec`, `stop_conditions` | No — all six classes are *operational* (what shape, what to throw, who owns what). None asks "is the decision structurally sound?" |
| `impl_plan_review` | code-review (architecture axis) + code-adversary + optional domain-logic on MCA's plan | Partial — code-review architecture axis covers dependency direction, layer violations, coupling, pattern consistency, tech debt. Operational, not pattern-canonical. |
| `code-review-board` (L2) | 9 reviewer roles: code-review (3 axes), code-adversary, code-security, code-domain-logic, code-reliability, code-data, code-api-contract, code-ai-llm, code-docs-consumer + chief | No — none of the nine personas owns "pattern purity" as their primary focus. (See §1.2.) |
| `spec-co-evolve-check` | Did code change spec-defined behaviour? | No — drift check, not architecture audit |

The 6-class enumeration in `delegation-artefact`
(`workflows/runbooks/build/workflow.yaml:308-321`,
`framework/agents/buddy/operational.md:188-202`) is the *only* mandatory
list of decision classes Buddy must lock. It is purely operational. There
is no class for *structural invariants* (immutability, single-source-of-
truth, state-vocabulary completeness, cycle-rooted misplacement).

### 1.2 Why none of the nine code-review-board personas catches the three patterns

Walking the persona heuristics against the three documented root smells
(S-1 mutability-shift, S-2 cycle-symptom-as-cause, S-3 state-machine-
without-initial):

**`code-review` architecture axis** (`agents/code-review.md:131-149`,
`172-183`) checks:
- Dependency direction (imports), layer violations, coupling, pattern
  consistency, interface contracts (explicit vs implicit), tech debt.

This axis would catch S-2 *if* the reviewer is willing to escalate "Any-
type because of import cycle" from a tactical workaround to a structural
finding. The persona's anti-rationalization line explicitly warns "you say
'implementation detail' — if it breaks the dependency direction, it's
architecture" — but Pattern B is the *opposite* shape: the dependency-
direction *symptom* is genuine, but the *cause* is conceptual misplacement.
The heuristic doesn't include "ask why the cycle exists, not how to break
it."

This axis does **not** catch S-1 (smell-shifted): the new mechanism
(shared-mutable Pydantic model) does not violate dependency direction or
layer discipline. The architecture axis is module-graph-shaped, not
property-shaped.

This axis does **not** catch S-3: state-machines aren't part of axis-2's
focus list.

**`code-adversary`** (`agents/code-adversary.md:57-71`) checks smart-but-
wrong, races, silent corruption, off-by-one, error swallowing, timing,
state leaks. None of the three documented patterns is in scope: S-1 is
not a race (no concurrent access), S-2 is not silent corruption, S-3 is
not an off-by-one — they are pattern-canonical issues, not bug-class
issues.

**`code-domain-logic`** (`agents/code-domain-logic.md`) covers business
state-machines (session gates, transitions, audit invariants). Would
plausibly catch S-3 *if* the `_health_state` lifecycle were modelled as a
business state-machine — but the persona's anchor pattern is BuddyAI
session/audit, not generic state vocabulary.

**`code-reliability`, `code-security`, `code-data`, `code-api-contract`,
`code-ai-llm`, `code-docs-consumer`** — none of these owns structural
purity as a primary axis.

**`code-chief`** consolidates; it doesn't introduce findings.

The asymmetry from the user's data is the proof: 5 HIGH + 12 MED + 10 LOW
findings emerged in pass-1, *none* of which was the three roots. That is
not a calibration issue — it is a heuristic-coverage gap.

### 1.3 Why Buddy's persona doesn't backstop this

`agents/buddy/soul.md` says:
> "Discuss until intent and the core decisions are sharp ... Probe, push
>  back, flag inconsistencies. Ask the hard questions, not the obvious
>  ones."

That is the right intent, but it is generic ("the hard questions") and
sits behind two structural incentives that pull the other way:

1. **CLAUDE.md §Invariant 1 (Buddy = Dispatcher).** On Board/Council,
   Buddy explicitly does NOT analyse findings. The invariant correctly
   prevents Buddy from over-stepping into review work — but it also means
   that *if* the board misses a class of problem, Buddy has no licensed
   surface to add the missing perspective.

2. **`agents/buddy/operational.md` §Delegation hygiene** asks Buddy:
   *"design decision or mechanical writing?"* — but the question is
   delegation-shape-driven, not structural-soundness-driven. Buddy locks
   decisions and asks *which agent gets them*, not *are these decisions
   architecturally sound*.

So when Buddy lands at the `delegation-artefact` step with 15 PARKED
findings or 6 implicit decisions, the persona prompt nudges toward
"package and dispatch" — not "audit for pattern purity first."

### 1.4 Locating the gap

The gap is one shape, three places:

> **No agent or gate in the build workflow owns "pattern-canonical
> structural purity" as a primary axis between `interview` and merge.**

Three places where a check could live:

1. **Pre-decision-lock** (between `board` and `delegation-artefact`):
   audit the locked-decision set against pattern-canonical invariants
   *before* MCA receives them. Catches Pattern A and Pattern C at the
   cheapest stage.
2. **Pre-implementation** (in `impl_plan_review`): augment the existing
   3-agent panel with a structural-roots reviewer. Catches MCA's plan
   choices that re-introduce the smell at the implementation layer.
3. **Post-implementation** (in `code-review-board` L2): a new persona that
   reads the diff with structural-pattern-canon as primary axis. Catches
   what survives the first two gates.

All three patterns from `467-prep-brief-fp2.md` have a single common
shape: they are detectable *only* when the reviewer asks
"is the property the previous solution was meant to enforce still
enforced?" — not when they ask "is this code well-engineered?"

---

## 2. Recommendation

I recommend a **three-layered fix**, with the heaviest investment at
layer 2 (new persona):

| # | Where | Change | Cost | Catches |
|---|---|---|---|---|
| 1 | `delegation-artefact` step | Add a 7th mandatory decision class: `structural_invariants` | Low (mechanical: prompt, hook, doc) | Forces Buddy to *name* what invariant the spec/decisions preserve, before MCA. Catches A + C cheaply. |
| 2 | new persona `code-architect-roots` + parallel `board-architect-roots` | New reviewer persona with the three patterns as canonical heuristic. Added to `code_review_board` L2 (always) and `impl_plan_review` (conditional). | Medium (new agent file + skill wiring + few-shot training) | Catches all three patterns post-plan and post-impl. The asymmetry data (5H+12M+10L found, 3 roots missed) directly justifies a dedicated persona. |
| 3 | `agents/buddy/operational.md` §Delegation hygiene | Add a third question: *"are the locked decisions structurally sound, or are they symptom-shaped?"* with the three pattern-class triggers inlined | Low (4 lines) | Backstop in Buddy's own prompt. Won't replace the persona — but reduces the rate at which symptom-patches reach `delegation-artefact` in the first place. |

I deliberately do **not** recommend:

- **Option (b)** as proposed in the brief (a hard `architect-attest` gate
  before `delegation-artefact`) as a *standalone* mechanism. A
  human-in-the-loop attestation without a persona-owned heuristic is
  performative — Buddy would tick the gate without new signal. The
  combination of (1) + (2) is the actual mechanism; the gate is just the
  surface that makes (1) mandatory.
- **Just option (d)** (extend `code-review` architecture axis). The axis
  is already saturated with three sub-personas (correctness +
  architecture + performance) inside one persona. Adding a fourth axis
  inside the same agent dilutes the drill+trace discipline. A separate
  persona is cleaner and parallelizable.

### 2.1 Why a separate persona, not a heuristic-extension

`code-review`'s architecture axis is *module-graph-shaped* (imports,
layers, coupling). Pattern-canonical reasoning is *invariant-shaped*
(does property X still hold after this refactor?). Mixing the two in one
persona produces drill+trace overload — the persona already runs three
drills, three traces, with bind rules per axis. A fourth would dilute.

A standalone `code-architect-roots` persona has one job and one drill,
trained on the three pattern classes as canonical few-shot examples. The
operational cost is one extra reviewer in L2 dispatch (10-15% wallclock
on the parallel pass — meaningful but not blocking).

### 2.2 Why a 7th decision class, not a separate gate

The 6 existing decision classes work because they are mechanically
enforced by `delegation-prompt-quality.sh` Check C. Adding a 7th class
inherits that machinery for free. A standalone gate would need its own
mechanic.

The 7th class — `structural_invariants` — forces Buddy to write down,
per substantial dispatch, "what property does the spec/decisions
*preserve* that a naive implementation could *break*?" If Buddy can't
name a property, the question itself is signal. (The class also
acknowledges the legitimate "no invariant — pure mechanical work" case
with `n/a + value: <reason>`, mirroring the existing class structure.)

---

## 3. Concrete edits

### 3.1 NEW FILE: `agents/code-architect-roots.md`

```diff
+++ agents/code-architect-roots.md (new file)
@@
+---
+name: code-architect-roots
+description: Structural-roots reviewer in the Code Review Board — pattern-
+  canonical purity. Asks "is the smell shifted or solved?", "is the cycle a
+  symptom of misplaced module?", "does the state vocabulary cover all real
+  lifecycle phases?". Distinct from code-review (operational architecture
+  axis): code-architect-roots owns invariant-shaped reasoning, not
+  module-graph-shaped reasoning.
+---
+
+# Agent: code-architect-roots
+
+Structural-roots reviewer. One drill, one trace, three pattern classes.
+
+Boundary — what this persona does NOT do:
+- Module imports / layer violations / coupling → `code-review` (axis 2).
+- Smart-but-wrong / races → `code-adversary`.
+- Business state-machines (session gates, audit invariants) →
+  `code-domain-logic`.
+
+This persona owns *property-shaped* reasoning: does the new code preserve
+the invariant the previous solution (or the spec) implicitly relied on?
+
+Protocols: `_protocols/reviewer-base.md`,
+`_protocols/code-reviewer-protocol.md`,
+`_protocols/reviewer-reasoning-trace.md` (required trace),
+`_protocols/first-principles-check.md` (required drill — one per pattern
+class hit).
+
+## Three pattern classes (canonical heuristic)
+
+### Pattern A — Smell shifted, not solved
+
+The previous solution violated property P. The new solution uses a
+different mechanism but **also** violates property P. The change moved the
+smell into a new vehicle.
+
+Few-shot canonical example (Task 467 S-1, BuddyAI):
+`RequestContext` had ContextVar-distance-action (one writer, one reader,
+far apart, coupled only via process state). Refactor replaced ContextVar
+with a shared-mutable Pydantic model. Same invariant violation
+(shared-mutable across distant boundaries), different vehicle.
+
+Trigger questions for the reviewer:
+1. What property did the previous solution **try** to enforce?
+2. Does the new solution enforce the same property, or just hide its
+   violation behind a different surface?
+3. If you delete the new code and re-derive from first principles, do
+   you arrive at the same shape?
+
+Severity floor: **HIGH** when a refactor's stated motivation is to fix
+property X, but the new code does not enforce X.
+
+### Pattern B — Cycle-symptom kept as cause
+
+An import cycle (or a `Any`-type, or a forward-reference, or a runtime
+import) is treated as the *cause* of friction, when it is actually the
+*symptom* of misplaced module ownership. The fix accepts the workaround
+instead of asking why the symbol lives in the wrong module.
+
+Few-shot canonical example (Task 467 S-2.1, BuddyAI):
+`AppState` half-migration, `Any`-typed field, justified with "would
+create import cycle". The cycle is symptom: the symbol the cycle drags
+in conceptually belongs to a different module. Move-and-the-cycle-is-
+gone.
+
+Trigger questions for the reviewer:
+1. Why does this cycle exist? What is the conceptual ownership of the
+   symbol that cycles?
+2. If the symbol moved to module Z, does the cycle disappear without a
+   workaround?
+3. Is the workaround (`Any`, `TYPE_CHECKING`, runtime import, forward
+   reference) load-bearing for the architecture, or just for the import
+   graph?
+
+Severity floor: **HIGH** when a cycle workaround is in code touched by
+this diff and a moved-symbol fix exists.
+
+### Pattern C — State machine without modelled initial state
+
+A state machine's vocabulary squeezes a real lifecycle phase into a
+state that semantically means something else. Most common: an
+`uninitialized` phase coerced into a healthy-but-degraded state, or a
+`transitioning` phase coerced into the destination state.
+
+Few-shot canonical example (Task 467 S-3, BuddyAI):
+`_health_state` initialised to `"degraded"`. Semantically wrong:
+`degraded` means "I checked and I'm not fully healthy" — but the initial
+state is "I haven't checked yet". A separate `"uninitialized"` state
+belongs in the vocabulary.
+
+Trigger questions for the reviewer:
+1. List every real lifecycle phase the entity actually passes through.
+   Does the state vocabulary cover all of them, or do some collapse into
+   states that mean something different?
+2. Is the initial value of the state field a *named* state, or a
+   *coerced* one?
+3. What invariant does each state guarantee? If two states share an
+   invariant, the vocabulary is too coarse; if a phase has no
+   invariant, the vocabulary is too narrow.
+
+Severity floor: **MEDIUM** (escalates to **HIGH** when the coerced
+state crosses a behaviour gate, e.g. health check → traffic routing).
+
+## Anti-rationalization
+
+- You say "tactical fix" — does the tactic preserve the invariant?
+- You say "small refactor" — name the property the small refactor
+  preserves; if you can't name it, the refactor isn't small.
+- You say "the cycle is unavoidable" — list the moves you considered.
+- You say "initial state doesn't matter — it's quickly overwritten" —
+  then it should be a separate named state, not coerced.
+- You see five reviewers found 27 findings without flagging structural
+  roots. **That is the signal.** Operational reviewers cluster on
+  symptom-level findings; you own the roots. If you have zero findings
+  per axis, you didn't search hard enough.
+
+## Reasoning (role-specific)
+
+1. INTENT: What property is this code/refactor *meant* to enforce?
+2. PLAN: Which of the three patterns plausibly applies here? (May be
+   none — say so.)
+3. SIMULATE: Pattern A — replay the previous-solution-violation against
+   the new mechanism. Pattern B — list the conceptual-ownership moves
+   that would dissolve the cycle. Pattern C — enumerate real lifecycle
+   phases vs vocabulary states.
+4. FIRST PRINCIPLES: From scratch, ignoring the existing implementation,
+   what shape does the property require?
+5. IMPACT: If the root smell stays, what's the next class of bug it
+   produces?
+
+## Required output fields
+
+- **Per finding:** `pattern_class: A | B | C | other` (other allowed
+  but rare — explain why it's structural-roots and not another
+  persona's territory).
+- **Per finding:** `invariant_violated: <one sentence>`.
+- **Per finding:** `concrete_alternative: <one sentence>` (no "needs
+  refactor" — name the move).
+- **Required drill section:** `## Reviewer-First-Principles-Drill —
+  Architect-Roots`.
+- **Required trace section:** `## Reviewer-Reasoning-Trace —
+  Architect-Roots`.
+
+## Finding prefix
+
+`F-AR-{NNN}`.
+
+REMEMBER: property-shaped, not module-graph-shaped. If you find
+yourself writing a coupling/imports/layers finding, hand it back to
+`code-review`. If you find yourself writing a race/off-by-one/error-
+swallow finding, hand it back to `code-adversary`. Your domain is "is
+the invariant the previous solution preserved still preserved?".
```

A parallel `agents/board-architect-roots.md` (spec-board variant, same
heuristic but reading specs instead of code) is the natural pair —
diff-shape identical except for protocol references
(`spec-reviewer-protocol.md` instead of `code-reviewer-protocol.md`)
and few-shot examples drawn from the spec-phase iteration of 467
(`docs/tasks/467-prep-brief.md` v3, the 6 LDs that emerged on
challenge).

### 3.2 EDIT: `skills/code_review_board/SKILL.md`

```diff
--- skills/code_review_board/SKILL.md
+++ skills/code_review_board/SKILL.md
@@ §3 Team composition
-**Core (ALWAYS):** code-review + code-adversary.
+**Core (ALWAYS):** code-review + code-adversary +
+code-architect-roots.
+
+`code-architect-roots` covers structural-pattern-canon (smell-shifted,
+cycle-symptom, state-vocabulary). Distinct from `code-review` axis 2
+(module-graph-shaped) — `code-architect-roots` is property-shaped.
+Required at L2 always; conditional at L1 only when the diff carries
+a refactor of a previously-flagged smell, an import-cycle workaround,
+or a state-machine touch.
```

Plus a row in the L2 specialists table (`SKILL.md:67-79`):

```diff
+| Refactor / cycle-workaround / state-machine | code-architect-roots |
```

Plus a row in `REFERENCE.md:34-49` agent overview:

```diff
+| code-architect-roots | Smell-shifted, cycle-symptom, state-vocabulary | conditional | ✓ |
```

### 3.3 EDIT: `skills/impl_plan_review/SKILL.md` §Agents

```diff
--- skills/impl_plan_review/SKILL.md
+++ skills/impl_plan_review/SKILL.md
@@ ## Agents (board pattern, code-review pool)
 - **code-review** (ALWAYS, architecture axis): module structure,
   dependency graph, pattern fit. ...
 - **code-adversary** (ALWAYS): edge cases, smart-but-wrong
   interpretations.
+- **code-architect-roots** (conditional, on a refactor / cycle-
+  workaround / state-machine touch): structural-roots audit of MCA's
+  plan against the three pattern classes.
 - **code-domain-logic** (conditional, on business logic):
   state-machine correctness.

-Min 2 agents, max 3.
+Min 2 agents, max 4.
```

### 3.4 EDIT: `workflows/runbooks/build/workflow.yaml` `delegation-artefact`

Add a 7th class to the implicit-decisions enumeration. The change is
mechanical:

```diff
--- workflows/runbooks/build/workflow.yaml
+++ workflows/runbooks/build/workflow.yaml
@@ delegation-artefact step
       Modul-Impact ODER sub-build): Pflicht-Section
       `## Implicit-Decisions-Surfaced` mit 6 Standard-Decision-Klassen
       (schema_shape, error_handling, layer_discipline, naming_collisions,
-      return_format_spec, stop_conditions). Jede Klasse: `locked: <status>`
+      return_format_spec, stop_conditions, structural_invariants). Jede
+      Klasse: `locked: <status>`
       + `value: <decision>`. Below-threshold trivial: `<!-- Below threshold -->`
       Ein-Zeiler. Pre-Dispatch Hook checkt mechanisch.
```

(Plus `6 Standard-Decision-Klassen` → `7 Standard-Decision-Klassen` in
the same block.)

### 3.5 EDIT: `framework/agents/buddy/operational.md` §Brief-quality gate

Mirror the YAML change:

```diff
--- agents/buddy/operational.md
+++ agents/buddy/operational.md
@@ §Brief-quality gate for MCA dispatches
-build/workflow.yaml step `delegation-artefact` MUST contain a required
-section `## Implicit-Decisions-Surfaced` for any substantial dispatch
-(>=3 ACs OR schema change OR cross-module impact OR sub-build), with
-6 standard decision classes:
+build/workflow.yaml step `delegation-artefact` MUST contain a required
+section `## Implicit-Decisions-Surfaced` for any substantial dispatch
+(>=3 ACs OR schema change OR cross-module impact OR sub-build), with
+7 standard decision classes:

 1. `schema_shape` — data shape (Pydantic/DDL/event payload)
 2. `error_handling` — exception classes, retry vs. fail
 3. `layer_discipline` — who does what (knowledge / pipeline / bridge)
 4. `naming_collisions` — symbol-shadowing checks
 5. `return_format_spec` — RETURN-SUMMARY structure
 6. `stop_conditions` — when MCA STOPs and escalates
+7. `structural_invariants` — which property the spec/locked decisions
+   are *meant* to preserve that a naive implementation could break
+   (shared-mutability across boundaries / cycle-rooted misplacement /
+   state-vocabulary completeness). Three pattern classes:
+   A (smell-shifted), B (cycle-symptom), C (state-vocab-coercion).
+   Detail: `agents/code-architect-roots.md`.
+   Acceptable values: `n/a + reason: pure mechanical work`, or a named
+   property (e.g. "RequestContext is per-request, never shared
+   across distant boundaries").
```

### 3.6 EDIT: `agents/buddy/operational.md` §Delegation hygiene

A 4-line addition to the existing question pair:

```diff
--- agents/buddy/operational.md
+++ agents/buddy/operational.md
@@ §Delegation hygiene
 **Delegation hygiene:** before every MCA delegation, ask: *"design
 decision or mechanical writing?"*
 - Design → Buddy decides, MCA gets a precise spec (content + location
   + AC).
 - Mechanical → MCA gets spec + AC + scope, no design freedom.
+
+**Plus a structural-soundness check before locking decisions:** ask
+*"are these decisions structurally sound, or are they symptom-shaped?"*
+Three triggers (cheap mechanical check, not a full review):
+(a) Does any locked decision replace a previous mechanism that violated
+a property? → name the property + verify the new mechanism enforces it
+(Pattern A — smell-shifted).
+(b) Does any locked decision accept an import-cycle workaround
+(`Any`, `TYPE_CHECKING`, runtime import)? → ask why the cycle exists
+before locking the workaround (Pattern B — cycle-symptom).
+(c) Does any locked decision touch a state-machine? → enumerate real
+lifecycle phases vs vocabulary states (Pattern C — vocab-coercion).
+If any trigger fires and the answer is unclear: hand to
+`code-architect-roots` via `impl_plan_review` (extra agent), don't
+lock blind. Detail: `agents/code-architect-roots.md`.

 "Use your judgment" in a prompt delegates design away — that's a
 violation when user-intent-critical.
```

### 3.7 EDIT: `workflows/runbooks/build/WORKFLOW.md` §Phase Prepare step 4

Mirror the YAML and operational.md change in the prose runbook:

```diff
--- workflows/runbooks/build/WORKFLOW.md
+++ workflows/runbooks/build/WORKFLOW.md
@@ Prepare step 4 DELEGATION
-   `## Implicit-Decisions-Surfaced` on a
-   substantial dispatch (≥3 ACs OR schema change OR
-   cross-module impact OR sub-build route): 6 standard
-   decision classes (`schema_shape`, `error_handling`,
-   `layer_discipline`, `naming_collisions`,
-   `return_format_spec`, `stop_conditions`), each with
-   `locked + value`.
+   `## Implicit-Decisions-Surfaced` on a
+   substantial dispatch (≥3 ACs OR schema change OR
+   cross-module impact OR sub-build route): 7 standard
+   decision classes (`schema_shape`, `error_handling`,
+   `layer_discipline`, `naming_collisions`,
+   `return_format_spec`, `stop_conditions`,
+   `structural_invariants`), each with `locked + value`.
+   `structural_invariants` names the property the
+   decisions are *meant* to preserve (Pattern A
+   smell-shifted / Pattern B cycle-symptom / Pattern C
+   state-vocab-coercion — see
+   `agents/code-architect-roots.md`).
```

### 3.8 OPTIONAL: `skills/_protocols/mca-brief-template.md`

Wherever the template enumerates the 6 decision classes, add the 7th
with the same diff-shape as 3.5.

### 3.9 OPTIONAL: parallel `board-architect-roots`

For symmetry on the spec side (catches Pattern A/B/C in the spec phase,
i.e. what would have caught the user's iteration-1 case):

- New file `agents/board-architect-roots.md` (mirror of 3.1, swapped
  protocols + few-shot from `467-prep-brief.md` v3).
- Add to `skills/spec_board/SKILL.md` §2 team composition: standard team
  unchanged, deep-pass-1 adds `board-architect-roots`. Conditional at
  standard mode when the spec's locked decisions touch a refactor of a
  flagged smell / import-cycle workaround / state-machine.

---

## 4. Why this works (the mechanism)

The three changes interlock:

1. **Class 7 (`structural_invariants`)** forces Buddy to *name* the
   invariant before dispatch. Naming-as-mechanism: if Buddy can write
   the property in one sentence, the dispatch is safe; if Buddy can't,
   the question itself is signal that an `impl_plan_review` with
   `code-architect-roots` is warranted.

2. **`code-architect-roots` persona** owns the invariant-shape heuristic
   that no current persona owns. The asymmetry data
   (5H+12M+10L found, 3 roots missed) directly justifies a dedicated
   reviewer — that's the quantified gap.

3. **Buddy operational delegation-hygiene update** is the cheap
   backstop. Two of the three pattern triggers are mechanical (does the
   diff replace a previous mechanism? does it accept a cycle-workaround?
   does it touch a state-machine?) — Buddy can run them as a 30-second
   check before lock, without a full review.

The 7th class + the persona is the heaviest investment; the operational
update is a near-free addition that captures the cases too small to
warrant an `impl_plan_review` extra-agent dispatch.

---

## 5. Estimated cost

| Layer | Cost | Recurring cost |
|---|---|---|
| 7th decision class | ~30 lines across 4 files | None — Buddy fills in one extra class per substantial dispatch (~5 lines) |
| `code-architect-roots` persona file | ~250 lines (new agent file) | One extra reviewer at L2 (~10-15% wallclock + token cost on the parallel pass) |
| Buddy operational hygiene update | ~10 lines | None — three trigger checks per substantial dispatch (~30 sec wallclock) |
| `board-architect-roots` (optional) | ~250 lines | Conditional — only on spec-phase refactor / cycle / state-machine triggers |

The recurring cost is bounded because the heuristic is *triggered*
(Pattern A requires a previous-mechanism-replacement, Pattern B requires
a cycle workaround in the diff, Pattern C requires a state-machine
touch). On a typical "add a feature, no refactor, no cycle, no state-
machine" build, the persona reports zero findings without spending much
budget — the drill is "is any of A/B/C plausibly applicable here?", and
the answer is often "no, none — return zero findings with rationale".

---

## 6. Spot-check across other repos (sub-output)

The brief asked for a 2-3 task spot-check in consumer repos for the same
pattern. This document is framework-side (no consumer-repo access from
here). The spot-check belongs in the consumer repo session — the right
shape is: pick 2-3 closed tasks per consumer repo where the build
workflow shipped a refactor of a previously-flagged smell, an import-
cycle workaround, or a state-machine touch, and replay the three
trigger questions against the closed code. Any "we shifted the smell" /
"we kept the cycle workaround" / "we coerced the initial state" hit is
quantified evidence that the gap is repo-cross-cutting, not 467-
specific. The user's two-iteration data on 467 is already strong signal
on its own; cross-repo evidence sharpens prioritisation but isn't
required to act.
