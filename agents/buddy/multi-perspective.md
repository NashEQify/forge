# Buddy — Multi-perspective engagement

Step-loaded unit of `agents/buddy/operational.md` (Phase 2: ACT). Read it when
choosing a board, reviewer or council, considering waiving a required review,
or assessing returned work. It also applies before a fix brief, moving a
blocking finding, a second or later fix pass, a simpler mechanism proposal, an MCA
dispatch that replaces an existing pattern, or escalating a decision to the
user. The core's Applicability holds for software. On demand, follow the
project's working rules.

Buddy reaches for collaboration (board, council, sub-agent, user-
loop) when single-perspective error-cost exceeds coordination-cost.

**Council-before-user-escalation discipline.** When the council §1.0
proportionality gate fires (per `skills/council/SKILL.md` §1.0 — ≥3
of 4 yes across multi-path / multi-component / substantial-impact /
Buddy-uncertain) AND the next decision step would be asking the user,
dispatch council first (default light mode is enough for most cases).
The framework's autonomy bound is: *Buddy runs through workflows +
skills + boards + council semi-autonomously; user-escalation is the
exception, not the default*. Running a delegated build to done means
finishing the task, not the current design: before fix pass ≥ 2 the
Simplify-before-patch check (`skills/convergence_loop/simplify-before-patch.md`) runs,
and proposing a simpler mechanism to the caller is a design-fork
proposal, not permission-seeking (while it waits it counts as ESCALATE
for the re-review limit; when the caller is the user, council-first
below applies). The proposal shows the **whole mechanism**, not the
side the finding sat on: a state-bearing mechanism has one
`§Mechanism-Lifecycle` matrix in its owning spec
(`skills/_protocols/mechanism-model.md`) — written at authoring, or by
Buddy as a retro-model before the first fix brief when missing — and
every ruling, simplification and user decision on the mechanism edits
that matrix in the same change. Buddy owns the mechanism end to end
across passes and tasks: fix briefs and re-verify mandates are scoped
to its cells, blocking findings on `now` cells are never parked on
another task, and cells the plan places in another task or beyond the
MVP travel only as `blocked_by` edges (rule and placement:
`skills/_protocols/mechanism-model.md` §Scope and placement).

Escalate to user only when:
(a) council itself produces DISSENT that Buddy cannot adjudicate from
corpus evidence, OR
(b) the decision crosses an ADR-mandate floor (Pocock-triple:
hard-to-reverse + surprising-without-context + real-trade-off), OR
(c) the user named a scope boundary that the decision crosses, OR
(d) the §1.0 gate does NOT fire (≤2 yes) — it's not council-worthy;
Buddy decides directly per §1.0 anti-pattern note or asks user inline.

**Buddy-uncertain alone is NOT council-trigger** — uncertainty is
ONE of 4 §1.0 criteria, not the single trigger. This rule operates on
the council-vs-user axis (which seat the next decision goes to); the
mode-escalation axis (light → standard → full) stays criterion-driven
per SKILL.md §1.1.

Five facets, non-exhaustive — name what's present, not what's
counted:

- **Complexity mastery** — many interacting parts, one model can't
  hold all coherently. Symptom: summarizing instead of synthesizing.
- **Depth** — first answer reveals a deeper question. Symptom:
  "why" unanswered twice in a row. Tool depends on what the next
  layer wants: `bedrock_drill` (solo recursive axiom decomposition)
  when the deeper question is "what assumption is this question
  resting on?"; `council` (multi-perspective) when the deeper
  question is "between which paths are we choosing?". `frame`
  already pulls `bedrock_drill` as step 2 in deep mode; standalone
  `bedrock_drill` is the direct path when `frame` is overkill.
- **Plural solution-space** — multiple legitimate paths, dialectic
  needed. Symptom: picked one, can't articulate against the others.
- **Blind-spot compensation** — dimensions one perspective
  systematically misses (cancellation, race, cross-temporal).
  Symptom: reaching for confidence without evidence.
- **Reversibility** — wrong is expensive to undo (shipped code,
  locked spec, externalized decision). Symptom: "re-do if wrong"
  stops being acceptable.

Applies across code, spec, architecture, general problem-solving
with the user. Skill-specific count fallbacks (L/XL, schema, cross-
module, ≥3 ACs) live in their skill SoTs — safety net when facets
are unclear, NOT the gate. Inhalt vor Mechanik: facet-question
first, count as fallback.

Board/council responsibility: shared Invariant 1. Reviewer investigation,
Chief consolidation, and Buddy's decision/claim verification are distinct.

**Surfaces:**

- **Board** (spec): `spec_board/SKILL.md`.
- **Council** (architecture): `skills/council/SKILL.md`. **Spawn
  MUST happen in the SAME tool block as other follow-up actions —
  never "we'll Council that later".** Otherwise the architecture
  decision is made by Buddy alone, found out too late. **≥3 members
  → `council-chief` consolidator-tool mandatory per Inv 1**; Buddy
  reads consolidation, decides. Standard / full also: `council-adversary`
  + pre-council frame check (plan-adversary on briefing draft) +
  post-council re-apply of `architecture-comprehension.md` §B (unconditional).
- **Code-Review-Board** (code diff): `skills/code_review_board/SKILL.md`
  (light / L1 default / L2 on named triggers; fix-pass re-verify per its
  §4 table). The check of DIRECT work that closes in its turn is step 3 of
  `framework/direct-eligibility.md` §The DIRECT run; it needs no board skill.
  Outside the quick and checked paths of that run, **a code change to
  behaviour MUST get a board before it is trusted — keyed on the change, not
  the author.** Whether the code came back from
  MCA (`status=done`) OR Buddy wrote it directly on the orchestrator path,
  Buddy MUST pick a level (§1.0 proportionality decides L1 / L2 / light)
  and dispatch. Author self-test does not substitute — neither MCA's
  self-test nor Buddy's own dry-run: cancellation-path bugs, double
  timeouts, PII leaks, data-loss edges, and state-machine / route-skip
  edges surface only through reviewer diversity. The author is the worst
  checker of their own mechanical code — same principle ADR-008 applies to
  code-claims in authored artifacts.
- **Pre-LD-lock self-challenge** (before MCA-dispatch on pattern-
  replacing briefs): per LD ask *"root-fix or smell-transfer?
  what alternative was considered?"* — `structural_invariants` in
  `skills/_protocols/mca-brief-template-decision-classes.md` §4 is the mechanical surface;
  `n/a` requires stated reason.

**Board-skip discipline (pre-invocation).** The decision to SKIP a board
gate is taken BEFORE the board runs — so the board's own proportionality
test (`spec_board/depth-and-team.md` §1.0) cannot vet it; that test only runs once
the board is invoked. Close the gap at the decision point: a board-skip
MUST carry an inline written rationale (silent skip is not allowed — same
posture as the council's skip-template, `skills/council/SKILL.md` §14)
that answers, in plain language, the contract-surface question §1.0 asks:
*does the change only document something that already landed in code
(clarification / rewording), or does it introduce a new rule, new
state-vocabulary, a new public-API contract, a new SSE event, or a new
schema field?* If it introduces ANY such contract surface, the board is
**not skippable** — not even when the underlying decision is ADR-locked,
a cross-spec amendment-verification already passed, or the change is
additive / optional / reversible. Those establish that the DECISION is
settled; they say nothing about the fresh contract SURFACE the
implementation introduces, which is exactly what the board scrutinizes
(an ADR-realizing amendment can ship type-safe but permanently inert).
The workflow-engine's required-step refusal is the backstop where an
engine runs; this rationale is the portable rule that holds where it does
not.

**Read-only review transport:** reviewers and Chiefs return complete
artifacts inline. Buddy persists the returned payload verbatim at the
designated path before a downstream Chief reads it. Record agent identity,
reviewed scope/revision and run identity as provenance without rewriting the
payload. Preserve frontmatter at the beginning when the format requires it.
Dispatch contract: `skills/_protocols/dispatch-template.md` section Output
transport. This is the normal transport, not a request to bypass tool policy.
Never claim read-only enforcement without checking effective runtime rights.

Before selecting the next action or adopting a bounded return, apply the
agreement comparison in `framework/work-principle.md` to the actual outputs and
evidence, not the return label alone. Retain the intended outcome, unresolved
parent requirements and specific unchecked dependencies in the next action or
existing handoff at the responsible caller. Local evidence supports its established
result; integration remains the caller's responsibility.
