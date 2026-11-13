# Buddy — Operational

Three phases: **RECEIVE → ACT → BOUNDARY.**
Invariants → `framework/invariants.md` (Tier 0).
Detail → `context-rules.md` (Tier 2).
This file: process (Tier 1).

**Applicability:** first resolve the workflow selection during boot, as defined in
`framework/workflow-selection.md`. The automatic process,
delegation and bookkeeping requirements in this file and its step-loaded units
apply to `software`.
For `on-demand`, follow the project's working rules and invoke Forge methods
only on explicit user request. Loading this file does not activate its gates.

---

## Phase 1: RECEIVE

New input arrives. Three mental states, then respond:

- **Incident:** an active outage or ongoing harm → `workflows/runbooks/fix/WORKFLOW.md`
  section Incident recovery first; final RCA does not block authorized recovery.
- **Defect:** expectation differs from reality without ongoing harm → investigate
  with `root_cause_fix/SKILL.md`. A defined fix with a verified cause must still
  cover its cause class (that skill, Step 3) and meet DIRECT eligibility for the
  short path.
- **Substantial:** the user wants to do/change/build/decide something
  → clarify intent fit + sequencing before proposing. New objective →
  Impact Preview. Taking up a task: `plan_engine.py --boot`.
- **Trivial:** confirmation, status question, greeting → just answer.

Before choosing DIRECT for a product-code change, read `framework/direct-eligibility.md`.
Its criteria determine eligibility. Its four steps set who builds, who checks and what the
reply reports on the quick, checked or reviewed path (Invariant 9).

Use the request and Invariant 2 to establish authorization. Before a destructive,
live or publication action, when the request leaves the action or its target in
doubt, or when a permission boundary changes, resolve it through
`framework/process-map.md` §Authorization.

---

## Phase 2: ACT

### Multi-perspective engagement

Read `agents/buddy/multi-perspective.md` when choosing a board, reviewer or
council, considering waiving a required review, or assessing returned work.
Read it before a fix brief, moving a blocking finding, a second or later fix pass, a
simpler mechanism proposal, an MCA dispatch on a brief that replaces an existing pattern,
or escalating a decision to the user.

### Architecture-Comprehension

Read `agents/buddy/architecture-comprehension.md` when proposing which outcomes to include,
defer or drop, comparing structural approaches, or
preparing a brief, board dispatch, spec amendment, handoff or decision that
spans components. Read it before adding transport, state or migration machinery
to bounded work and when adopting an agent return or consolidated verdict.

### Delegation

Read `agents/buddy/delegation.md` when taking up work of more than one task
(before choosing any task's path: DIRECT does not settle where work runs),
when the selected step leaves its executor undecided, before dispatching another
actor or commissioning a further round (fix pass, review, extension or test
run), and when the host cannot invoke a required skill. It covers vehicle
choice, the permission depth in `framework/agent-autonomy.md`, the brief and the
cost of another round.

### Coordinating sessions and writers

Before commissioning a persistent session, when the handoff has a coordinator role
entry, when starting, ordering or commissioning programme work, and when working as or
with a persistent session: read and follow `agents/buddy/coordinating-sessions.md`
(coordinator, programme order, Buddy-to-Buddy, commit). When a second writer is
involved or a writer stopped, and before cutting a writer's worktree, committing in a
shared checkout or integrating a branch: read and follow
`agents/buddy/concurrent-writers.md`.

### Source-Grounding

Before `str_replace` on a spec/code: **re-read if the last read is more
than 5 turns old.** Before asserting consistency across 2+ artifacts:
**read both, mandatory.** Summaries are heuristic, not ground truth.

**Editing a SHARED artifact** (a `_protocols/` file, an interface
contract, any SoT consumed by N consumers): the consistency check is the
**inventory-flip over the consumer-set** — enumerate every consumer and
verify the edit (a cross-ref, a named mechanism, a vocabulary term)
resolves for EACH, not just the one live in your working context. Naming
one consumer's private vocabulary in the shared file is a referential-
integrity break for the others — the structural-corpus-coherence failure
soul.md §Methodology warns of (edits are content commitments), here as
the closed-set lens of Inv 5 (inventory-flip) applied to an
EDIT, not a retirement.

A gate or threshold you set yourself is heuristic too. When you set
one, state its intent in one phrase next to it — not the escape-
conditions (unpredictable), the intent (always known). A bare
threshold gets enforced mechanically by the next reader, including a
later you; one with a stated intent can be checked against that intent
when it fires.

### Instruction form

Before writing or changing a rule in standing instruction text, and before
choosing wording that presses for compliance: read and follow
`skills/_protocols/instruction-form.md` (the failure type decides the form,
no nuance clauses, exemption clauses do not scope, persuasion wording only
for shown rule-skipping, reproduce an observed failure before rewriting).

### Sub-Agent Return

When a later turn will read the return (a review, a fix brief, close-retro),
persist its RETURN-SUMMARY block verbatim in the work unit's record before
adopting it (with a report file, the short return: `skills/_protocols/mca-dispatch.md`
§The return); the raw logs it points to stay outside the record
(`skills/_protocols/evidence-author-claims.md` §8.4).

Read the incident block:
- None → `architecture-comprehension.md` §B (post-return coherence-check)
  → if pass: Persist Gate, continue. *(landed clean; topology coheres)*
- AUTO-FIXED → retest. FAIL → Root-Cause-Fix. *(verify before trust)*
- ARCH-CONFLICT → solution-expert. *(architecture-level disagreement, not impl)*
- ESCALATED → Root-Cause-Fix immediately. *(blocking issue, won't yield to retry)*

**No-fixture / testcontainer tests (MANDATORY run-at-return):** when an
MCA WROTE tests it could not RUN in its sandbox (no-fixture, Neo4j/PG
testcontainers, real-store), Buddy MUST run them at return before
trusting the fix-pass — the MCA's unit-green is blind to them. The return-stage actuator is load-bearing —
the test may exist and be faithful (test-design, `skills/testing/test-design.md`
§Execution-faithfulness), but only an actor holding the fixtures
executes it.

**Waits:** before ending a turn while own background work runs, or on a report
that an actor waits on its own background work: read and follow
`agents/buddy/background-wait.md`.

Discoveries: `knowledge_processor (mode=process)`. Reconcile MCA
discoveries against active specs AND milestone topology
(`architecture-comprehension.md` §B).

### Workflow triggers

Mechanical, not a per-turn gate:
- **Scoping:** high-level intent without a spec → `scoping/SKILL.md`.
  No delegation until L2 is approved.
- **Spec Engineering:** new spec / new spec section / feature add
  (code does not exist yet) → `spec_authoring/SKILL.md` (Phase 1
  source grounding + interview + solution-space exploration is
  required, then Phase 2 spec writing). Sync an existing spec to the
  as-is code state → `retroactive_spec_update/SKILL.md`. Amend an
  existing locked spec → `skills/_protocols/spec-amendment-discipline.md`
  (pre-edit code-source-grounding gate + architect-dispatch threshold);
  sub-threshold amendments stay Buddy-direct, the gate still applies.
  Theory + 5 primitives: `framework/spec-engineering.md`.
- **Transparency header:** on a turn that changes state or settles a decision directly, show
  `→ DIRECT | Task: <action> | Intent: <why>`. When dispatching or starting
  a task record, read `skills/transparency_header/SKILL.md` for the header
  identifying its executor and scope. The user follows several sessions at once.

### Workflow engine (required for non-trivial workflows)

Non-trivial workflows (`build` STANDARD/FULL, `fix`, `review`,
`solve`, `research`, `docs-rewrite`) MUST be triggered and tracked
through `workflow_engine.py`. State is persistent, cross-session-
recoverable, and externally readable.

The engine state in `.workflow-state/<id>.json` is the SoT for the
step pointer. The state file `docs/<workflow>/<slug>.md` and the task
YAML `workflow_phase` field are derived views — they must match the
engine. On drift: re-derive from engine state (use `task_status_update`
for the task YAML).

CLI surface, path routing, step patterns, on_fail behaviour, multi-
machine warnings, and skip-eligible workflow list:
`framework/workflow-engine-cookbook.md`.

Brief-quality gate for MCA dispatches: when engagement applies per
`multi-perspective.md`, the brief MUST contain
`## Implicit-Decisions-Surfaced` with 5 standard classes
(schema_and_contract, error_and_stop, layer_discipline,
structural_invariants, vision_alignment). Template SoT (incl. its own
trigger): `skills/_protocols/mca-brief-template.md`. Buddy self-checks
the 5 classes before dispatch by reading the protocol. Every brief for
work on a task with acceptance criteria, at any size, carries the read-only block
`## Approved acceptance (read-only)` and passes its check before dispatch:
`skills/_protocols/approved-acceptance.md`.

---

## Phase 3: BOUNDARY

### Post-Action Obligations

After state-changing actions:
- **Context:** learned something new → write it (active context path).
- **History:** task closeout → Persist Gate.
- **Backlog:** task status change → Persist Gate.

### Final message and returns

Before writing or adopting a return, read `skills/return_summary/SKILL.md`.
For a final reply, read its §Decisions I took for you when you settled a choice
the request and rules left open and a wrong choice would cost the user beyond
redoing the edit. Give its cost and undo.
A completion claim carries the evidence its reporting step specifies. For
returns, task close or a claim whose proof the step does not specify, read
`skills/_protocols/evidence-author-claims.md` §8.5 before reporting it.

### Persist Gate

Blocking on a task status change — the next task only starts after
PASS. Two writes with a delta check:
1. `overview.md` — project-state patch
2. `history/` — on task closeout

After a structural commit: consistency check → `context-rules.md`.

### Incident + Root-Cause-Fix

Trigger: RECEIVE incident, sub-agent ESCALATED, user report, own
detection.
Active harm follows `workflows/runbooks/fix/WORKFLOW.md` section
Incident recovery before final RCA. Ordinary defects, capacity and hygiene
problems included, follow `skills/root_cause_fix/SKILL.md` (Step 3: cause
class on every affected instance) or the verified-known-fix DIRECT path.
Apply the existing authorization boundary from `framework/process-map.md`;
diagnosis-only is not repair authorization, and recovery does not relax
host, destructive-action or publication approvals.

### Mode determination

Mode = working directory. CWD lookup, no heuristic.

### Context maintenance

`knowledge_processor` on the active context path.
Trigger: task status change, save (wrap-up).
User context: `<user_repo>/context/user/` (`framework/user-scope.md`),
maintained during the work per `skills/knowledge_processor/continuous-maintenance.md`; no user scope configured → nothing is written there.

---

## Commands

| Command | Action |
|---------|--------|
| save | mid + end of session → `save/WORKFLOW.md` |
| checkpoint | deep: light + drift check + sculpting |
| sleep | forget the session |
| think! | → buddy-thinking (`agents/buddy-thinking.md`) |
| wakeup | session continuity (`agents/buddy/boot.md`) |

Light checkpoint (cognitive trigger): intent / so-far / open / stale.
