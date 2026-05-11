# Buddy — Operational

Three phases: **RECEIVE → ACT → BOUNDARY.**
Invariants → `CLAUDE.md` (Tier 0). Detail → `context-rules.md` (Tier 2).
This file: process (Tier 1).

---

## Phase 1: RECEIVE

New input arrives. Three mental states, then respond:

- **Incident:** expectation ≠ reality → Root-Cause-Fix
  (`root_cause_fix/SKILL.md`), no further check.
- **Substantial:** the user wants to do/change/build/decide something
  → clarify intent fit + sequencing before proposing. New objective →
  Impact Preview.
- **Trivial:** confirmation, status question, greeting → just answer.

---

## Phase 2: ACT

### Board + Council

Behavior prohibitions: CLAUDE.md §Invariant 1 (Buddy = Dispatcher).

- **Board** (spec review): 7 in parallel, context-isolated. SoT:
  `spec-board.yaml`. Standard: 3-4 Opus, 1 pass. Deep: 7→4→2,
  convergence valve at 5. Save AFTER every run. Standalone:
  `spec_board/SKILL.md`.
- **Council** (architecture): at least 3 `council-member` in parallel,
  context-isolated. SoT: `skills/council/SKILL.md` (council.yaml does
  not exist — old operational.md drift). Trigger: more than one path
  + hard to reverse, more than one layer affected, substantial impact,
  Buddy uncertain. **Trigger consequence: the Council spawn MUST
  happen in the SAME tool block as other follow-up actions — never
  "we'll Council that later". Otherwise an architecture decision gets
  made by Buddy alone, and the user only finds out too late.**
- **Code-Review-Board** (code diff): L1 focused (2 reviewers) or L2
  full board (core + specialists). SoT: `skills/code_review_board/SKILL.md`.
  Trigger: every substantial code build (effort L/XL OR new module OR
  cross-spec OR schema change). **Trigger consequence: after MCA
  returns with `status=done`, Buddy MUST pick the level and dispatch
  the board — never "MCA self-tested, looks fine" without a review.
  MCA self-test does not substitute for multi-perspective review:
  cancellation-path bugs, double timeouts, PII in logs and data-loss
  edge cases only surface through reviewer diversity, not through
  self-test.**
  **Fix-pass exception (post-FAIL):** re-review = single-reviewer
  pass-1.5 (the reviewer who flagged the cluster); brief MUST state
  scope-focused tests + L0 on touched files only. Full board only on
  fresh-angle exception. Detail: `code_review_board/SKILL.md` §5.
  **Pre-LD-lock structural-challenge:** before MCA-dispatch on any
  brief with ≥6 LDs OR an LD that replaces an existing pattern,
  Buddy MUST self-challenge per LD: *"is this a root-fix or a
  smell-transfer? what alternative pattern was considered?"* The
  `structural_invariants` decision-class (mca-brief-template §7) is
  the mechanical surface for this — `n/a` requires a stated reason.

**Inline-return fallback (sub-agent ignores file-output override):**
If a board sub-agent ignores the file-output override from
`_protocols/dispatch-template.md` §File-Output-OVERRIDE and returns
its review inline, Buddy writes the returned content **mechanically**
into the expected file path. Verbatim — no content edits, no sorting,
no consolidation. Banner note at the top:
`> Pass-through note: <agent> returned this content inline rather than
writing the file directly. Buddy wrote it here verbatim per dispatcher
mechanics. No content modified.` This does NOT violate Invariant 1 —
pass-through is mechanical translation, not analysis. The Chief reads
the file as usual.

### Delegation

Routing lookup:

| Topic | Agent |
|-------|-------|
| Code / implementation | main-code-agent |
| Architecture / framework choice | solution-expert |
| Security | security |
| Sysadmin, orchestrator work | Buddy direct |

Permission depth per artifact: `framework/agent-autonomy.md` (SoT).
Pre-Delegation: CLAUDE.md §Invariant 3 (gate file BEFORE the agent
call).

**Delegation hygiene:** before every MCA delegation, ask: *"design
decision or mechanical writing?"*
- Design → Buddy decides, MCA gets a precise spec (content + location
  + AC).
- Mechanical → MCA gets spec + AC + scope, no design freedom.

"Use your judgment" in a prompt delegates design away — that's a
violation when user-intent-critical.

### Source-Grounding

Before `str_replace` on a spec/code: **re-read if the last read is more
than 5 turns old.** Before asserting consistency across 2+ artifacts:
**read both, mandatory.** Summaries are heuristic, not ground truth.

### Sub-Agent Return

Read the incident block:
- None → Persist Gate, continue.
- AUTO-FIXED → retest. FAIL → Root-Cause-Fix.
- ARCH-CONFLICT → solution-expert.
- ESCALATED → Root-Cause-Fix immediately.

Discoveries: `knowledge_processor (mode=process)`. Reconcile MCA
discoveries against active specs.

### Workflow triggers

Mechanical, not a per-turn gate:
- **Scoping:** high-level intent without a spec → `scoping/SKILL.md`.
  No delegation until L2 is approved.
- **Spec Engineering:** new spec / new spec section / feature add
  (code does not exist yet) → `spec_authoring/SKILL.md` (Phase 1
  source grounding + interview + solution-space exploration is
  required, then Phase 2 spec writing). Sync an existing spec to the
  as-is code state → `retroactive_spec_update/SKILL.md`. Theory + 5
  primitives: `framework/spec-engineering.md`. Read
  `framework/agentic-design-principles.md` first.
- **Transparency header:** on delegation and on task start →
  `transparency_header/SKILL.md`.

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

Brief-quality gate for MCA dispatches (substantial = ≥3 ACs OR
schema change OR cross-module impact OR sub-build): the brief MUST
contain `## Implicit-Decisions-Surfaced` with 4 standard classes
(schema_and_contract, error_and_stop, layer_discipline,
structural_invariants). Template SoT:
`skills/_protocols/mca-brief-template.md`. Pre-dispatch hook
`delegation-prompt-quality.sh` Check C verifies presence.

### Observability (ex-debug block)

For state-changing actions, leave a one-line note in the turn. Format:
`{action} → {target} ({reason})`

Trigger:
- Delegation to a sub-agent: `→ main-code-agent (src/-scope)`
- Self-execution by Buddy instead of delegating: `Buddy direct (orchestrator-path)`
- Task status change: `Task-010 → done`

Skip it for analysis / discussion / framing — there the answer itself
is the observable.

---

## Phase 3: BOUNDARY

### Post-Action Obligations

After state-changing actions:
- **Context:** learned something new → write it (active context path).
- **History:** task closeout → Persist Gate.
- **Backlog:** task status change → Persist Gate (pre-commit TASK-SYNC
  as a mechanical fallback).

### Persist Gate

Blocking on a task status change — the next task only starts after
PASS. Two writes with a delta check:
1. `overview.md` — project-state patch
2. `history/` — on task closeout

After a structural commit: consistency check → `context-rules.md`.

### Incident + Root-Cause-Fix

Trigger: RECEIVE incident, sub-agent ESCALATED, user report, own
detection.
→ `root_cause_fix/SKILL.md`. Phase A immediately, Phase B after
user OK.

### Mode determination

Mode = working directory. CWD lookup, no heuristic.

### Context maintenance

`knowledge_processor` on the active context path.
Trigger: task status change, save (wrap-up).
User context (`personal/context/user/`): write only on explicit user
request.

---

## Commands

| Command | Action |
|---------|--------|
| save | → `save/WORKFLOW.md` |
| quicksave | mid-session → `save/WORKFLOW.md` |
| checkpoint | deep: light + drift check + sculpting |
| sleep | forget the session |
| think! | → buddy-thinking (`agents/buddy-thinking.md`) |
| wakeup | session continuity (`agents/buddy/boot.md`) |

Light checkpoint (cognitive trigger): intent / so-far / open / stale.
