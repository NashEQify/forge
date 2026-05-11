# Agent Patterns

Patterns for agent behaviour, captured from real drift cases. Each
entry has a problem, the mechanism that catches it, and a status line.
Live-fire only — patterns documented without an active mechanism are
not in this file.

---

## Pattern: Hook + Handoff (Session Continuity)

Status: active
Activated: 2026-03-05

### Problem

Claude Code sessions are ephemeral. Context compaction and fresh sessions
are normal. Without explicit persistence, every restart loses precise
execution position.

### Solution

Two complementary persistence artifacts written on `save` and read on `wakeup`:

- **Hook (computed):** `plan_engine --boot` gives machine-readable session state
  (task, step, since, short note).
- **Session log (`context/session-log.md`):** optional decision notes
  (open points, pending input, first checks).

They solve different problems and are not redundant.

### Hook format

```text
# Current Hook
agent: [buddy|main-code-agent]
task_id: [int]
task_title: [string]
step: [int]
step_description: [string]
since: [ISO timestamp]
context_note: >
  [max 3 sentences]

# If no active task:
status: idle
```

Scope: Buddy state only. Project-internal state belongs in project context.

### Handoff format

```text
# Session Handoff
session_end: [ISO timestamp]
written_by: [agent]
session: [int]

## Session N — [main theme]

### Core outcomes
[numbered factual list]

### User decisions
[all substantive user decisions/corrections in chronology]

### Errors and fixes
[what failed, how fixed, what did not work]

### Next session
[prioritized first actions]

### Open points
[pending decisions, waiting inputs, unknowns]
```

### Save behavior

Order:
1. write history entry
2. update hook (or idle)
3. overwrite handoff fully (never append)
4. update context files (impact chain)
5. update convoy when objective task is active

### Wakeup behavior

Boot sequence:
1. load static context
2. read hook
3. read handoff
4. if hook non-idle: offer resume with handoff context

GUPP-light: offer + user confirmation, no blind auto-execute.

### Reconciliation on divergence

Hook and workflow checklist can diverge across crashes.
Rule: workflow checklist is SoT for step status.
Wakeup behavior: read hook for quick orientation, then checklist as source of truth.

---

## Pattern: NDI via Workflow Checklist

Status: active
Activated: 2026-03-05

### Problem

Narrative history is imprecise for crash recovery.

### Solution

Task file `## Workflow` checklist is machine-readable persistence layer.
Last `in_progress` step is exact resume point.

Result: nondeterministic idempotence with Git as persistence substrate.

---

## Pattern: Briefing Depth (Crew vs Polecat)

Status: active (implicit), formalized 2026-03-05

Not all agents need the same context depth.
Key question: does this agent need to know *why* or only *whether correct*?

| Briefing type | Character | Agents |
|---|---|---|
| Full brief | full intent context, autonomous planning, persistent | Buddy, solution-expert, main-code-agent, sysadmin |
| Minimal brief | task-spec only, ephemeral, no state | code-review, code-* board roles, tester |
| Read brief | reads intent for validation, no autonomous decision | code-spec-fit |

Consequence: minimal-brief delegations carry task spec, not full intent tree.

---

## Pattern: Re-Council Inversion (positive) (421 audit)

### Problem

Initial council majority can be argument-decisive wrong when new inputs
fundamentally alter risk assumptions.

### Solution

Structured re-council mechanics:
1. NEW INPUTS in briefing
2. mandatory per-member diff sentence (first lean vs re-lean)
3. adversary member mandatory
4. synthesis lock only when voting and argument-decisive logic converge,
   otherwise STOP + user escalation

Empirical: 421 moved 1/4 -> 4/4 with substantive revision rationale.

---

## Pattern: Adversary-Sole-Found Drift (421 audit)

### Problem

Domain reviewers can all pass while structural citation drift remains invisible.

### Solution

Adversary member as orthogonal layer catches smart-but-wrong patterns
content reviewers miss. Class-level lesson: adversary output is
orthogonal to domain-review output. Both are required in multi-reviewer
setups.

---

## Pattern: §1 Position-Map Consolidation Visibility (421 audit spot check)

### Problem

Synthesis convergence claims can rely on secondary arguments that are present
in member files but not visible in §1 position map.
External reviewers without member-file access flag false over-consolidation.

### Solution

Per member in §1 include:
- primary lean
- primary reason
- **secondary argument carriers** with section refs and short anchors

This makes convergence claims externally auditable without full member-file access.

---

## Pattern: External Discipline Review as Structural Mitigation (post-421)

### Problem

Re-council synthesis is still synthesizer output. Who validates synthesizer quality?

### Solution

External reviewer validates synthesis against member files:
1. spot-check §1 vs member files
2. verify §3 convergence claims against member outputs
3. verify argument-decisive overrides against evidence

Trigger when all 4 hold:
- voting override or major inversion
- substantial re-council shift
- high-effort follow-up or spec-co-evolution requirement
- architecture-level decision

Output tiers: verified / observations with severity / methodological break.

---

## Pattern: External Reviewer Bundle Mechanics (post-423)

### Problem

External review without correct member files becomes structural-only,
not substantive.

### Solution

External-review bundle must include:
1. explicit required upload list with unambiguous paths
2. reviewer self-sanity pre-check
3. reviewer output markers (`substantive` vs `structural`)
4. maintainer pre-dispatch upload inventory verification
5. filename disambiguation convention

Format spec:
`framework/external-review-bundle-format.md`.

---

## Pattern: Reader-Facing Surface Detection (post-commit 82657bc defect B)

### Problem

Validators check structural correctness, not reader-facing usability
(findability, IA coherence, recognition).

### Solution

Classify artifact by primary consumer before choosing verify strategy:
- reader-facing -> require presentation audit (UX/IA/a11y/comprehension)
- non-reader-facing -> structural validators sufficient

Trigger is consumer class, not file extension.

Planned mechanics:
- allowlist `is_reader_facing(path)`
- pre-commit presentation-layer verify check
- workflow branching by artifact class
- engine bypass block for multi-file reader-facing edits without active workflow

---

## Pattern: Pre-Step Hypothesis Falsification

### Problem

Workflow steps often execute on implicit assumptions. When false,
steps fail late and expensively.

### Solution

Require hypothesis section for non-trivial steps (`requires_hypothesis_check: true`):
1. hypothesis (explicit)
2. pre-check mechanism
3. fallback path on failure

Workflow engine should render this in `--next` output.

---

## Pattern: Spec vs Code Drift in Cross-Repo setups

### Problem

Specs in framework repo and implementation in consumer repo evolve independently.
No cross-repo pre-commit catches this.

### Solution

Optional cross-repo drift mode in `spec-co-evolve-check`:
1. detect framework spec changes
2. map to consumer repos
3. grep for referenced anchors/signatures in consumer code
4. report behavior mismatch

Trigger: spec change + consumer repo locally available.
Warn-level, not hard block.

---

## Pattern: Spec-only Framing as Engine-Bypass Trap

### Problem

Substantial work gets framed as "spec-only", then run inline without
workflow tracking, phase boundaries, or quality gates.

### Solution

Engine trigger decision must be based on substance class, not spec/code label:

| Substance class | Engine trigger |
|---|---|
| New spec/section/feature addition | required |
| Spec update with cross-file impact (>1 file) | required |
| Single-file spec edit, no cross impact | skip eligible |
| Pure wording rephrase | skip eligible |

Decision must happen before work starts. If unclear: run engine first,
then evaluate skip eligibility.

Failure mode without this: erosion of workflow discipline, weak recovery,
and broken cross-session continuity.

## Pattern: SoT-prose-vs-engine-ground-truth

### Problem

Spec author writes a claim about mechanical behaviour ("the
sub-build route inherits brief-architect via the parent's gate";
"the path-whitelist hook scopes per-agent"; "this validator
rejects malformed input"). The claim is internally coherent in
prose. Reviewer reads the prose, finds it consistent with the
spec's other prose, and signs off.

After implementation: the consuming engine doesn't implement the
asserted behaviour. The brief-author authored against an
aspirational SoT; the implementer built per the brief; the bug
appears at runtime — not at any review pass.

### Worked example (synthetic illustration)

A spec author claims a sub-route in a workflow.yaml inherits
the parent route's step list "via YAML alias". A board pass
accepts the claim without verification. A later mechanical check
shows:

```yaml
routes:
  standard: &main_steps
    - step-a
    - step-b
    ...
  full: *main_steps      # YES this is an alias — inherits
  sub-route:             # NOT an alias — independently authored
    - step-a
    - step-b
    ...
```

The claim was prose-coherent. Mechanical truth: `sub-route` is
a separately-authored literal list. Editing `&main_steps` does
NOT propagate to `sub-route`.

### Solution

**Discipline rule (cross-persona):** when a finding, brief, or
spec claim cites mechanical behaviour in a consuming engine —
workflow_engine route handling, state propagation, hook-layer
scoping, validator semantics — the locator MUST point at the
consuming-engine code, not at the SoT prose claiming the
behaviour.

Applies to:

- **brief-architect** (anti-rationalization): "The spec says
  mechanism X works that way" — verify by reading the engine.
- **board-chief / code-chief** (consolidation discipline): when a
  finding cites mechanical behaviour, chief MUST verify the cited
  mechanism exists in the consuming-engine code before consolidation.
- **reviewer-base** (universal protocol): finding locators MUST
  point at the consuming-engine file/function for any mechanical
  claim.

**Mechanical surface candidates** (not yet implemented, future
work): pre-spec-lock hook that checks all spec claims about
mechanical behaviour have engine-pointer references — analogous
to the evidence-pointer-check from Task 299.

### Anti-pattern signature

If a board pass accepts a claim that contains "the engine
inherits", "the validator scopes", "the hook applies" without an
explicit pointer at the consuming-engine code → this pattern is
firing. Demand the pointer; if absent, the claim is unverified.

### Failure mode without this

Spec drift between prose and engine accumulates silently. Each
spec generation believes the prior generation's mechanical claims;
runtime is the only ground truth that surfaces gaps. Multi-pass
board iterations re-discover the same gap at different sites.
