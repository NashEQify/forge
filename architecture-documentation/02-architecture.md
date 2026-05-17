# 02 — Architecture

## High-Level

```
┌─────────────────────────────────────────────────────────────────────┐
│  USER                                                               │
└──────────────────────────────┬──────────────────────────────────────┘
                               │ (CLI: cc | oc | future cursor)
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│  HARNESS-ADAPTER (orchestrators/<name>/)                            │
│  - cc / oc: scope-routing, --add-dir composition                    │
│  - hooks/: PreToolUse, Stop, SessionEnd, pre-commit                 │
│  - .claude/settings.json registers hooks for CC                     │
└──────────────────────────────┬──────────────────────────────────────┘
                               │ loads
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│  TIER 0 — INVARIANTS                                                │
│  CLAUDE.md (CC) | AGENTS.md (OC)                                    │
│  6-7 invariants, never overridden                                   │
└──────────────────────────────┬──────────────────────────────────────┘
                               │ "Load and follow"
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│  TIER 1 — OPERATIONAL                                               │
│  Buddy: agents/buddy/{soul,operational,boot,context-rules}.md       │
│  Methodology: framework/{process-map,skill-map,skill-anatomy,       │
│             boot-navigation,agent-autonomy,agent-patterns,          │
│             intent-tree,milestone-execution,task-format,...}.md     │
└──────────────────────────────┬──────────────────────────────────────┘
                               │ invokes, dispatches to
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│  WORKFLOWS (workflows/runbooks/)                                    │
│  solve | build | fix | review | research | docs-rewrite |          │
│  save | audit | context_housekeeping                                │
└──────────────────────────────┬──────────────────────────────────────┘
                               │ composes
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│  SKILLS (skills/<name>/SKILL.md)                                    │
│  38 active skills, single-class                                     │
│  invocation.primary: user-facing | workflow-step | sub-skill |      │
│                       hook | cross-cutting                          │
│                                                                     │
│  Skill-Level Protocols (skills/_protocols/)                         │
│  - discourse, context-isolation, dispatch-template, piebald-budget, │
│    plan-review, consolidation-preservation, ...                     │
└──────────────────────────────┬──────────────────────────────────────┘
                               │ delegates to
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│  PERSONAS (agents/<name>.md)                                        │
│  Buddy (Orchestrator)                                               │
│  Spec-Board (chief, adversary[-2], implementer, impact, consumer)   │
│  UX-Board (ux-heuristic, ux-ia, ux-interaction)                     │
│  Code-Review-Board (13: chief, review, adversary,                   │
│    security, data, reliability, domain-logic, api-contract, ai-llm, │
│    spec-fit, spec-drift, docs-consumer, architect-roots)            │
│  Standalone (main-code-agent, council-member, solution-expert,      │
│    security, tester, test-skeleton-writer, plan-adversary)          │
│                                                                     │
│  Persona-Level Protocols (agents/_protocols/)                       │
│  - reviewer-base, reasoning-trace, first-principles-check,          │
│    spec-/code-/ux-reviewer-protocol, code-reviewer-base-extended    │
└─────────────────────────────────────────────────────────────────────┘
```

## Tier Model

Three tiers in descending binding strength:

| Tier | Examples | Binding |
|---|---|---|
| **0 — Invariants** | `CLAUDE.md`, `AGENTS.md` | never overridden; every wrapper-adapter loads them automatically |
| **1 — Operational** | `agents/buddy/operational.md`, `framework/process-map.md`, `framework/skill-map.md`, `framework/skill-anatomy.md`, `framework/boot-navigation.md`, `framework/agent-autonomy.md`, `framework/agent-patterns.md`, `framework/agentic-design-principles.md`, `framework/external-review-bundle-format.md` | loaded at boot or on demand; refines tier 0 |
| **2 — Detail** | `agents/buddy/context-rules.md`, skill `REFERENCE.md` files | on-demand; refines tier 1 |

**Consultation cascade** (`framework/agent-autonomy.md` §Consultation Cascade):
- Earlier beats later: tier 0 decides, tier 1 refines, never the other way round.
- Later may refine, not invent: contradictions are bugs (`plan_engine --validate` catches some).
- Defensive default: when in doubt trigger the gate, do not write.

## Buddy as Orchestrator

Buddy is the **only user-facing persona**. All other personas are dispatched
via Buddy (Board, Council, Standalone). Buddy never leaves the phase model:

### RECEIVE → ACT → BOUNDARY

`agents/buddy/operational.md`:

- **RECEIVE**: three mental states.
  - **Incident** (expectation ≠ reality) → `root_cause_fix/SKILL.md` mandatory.
  - **Substantive** (user wants something) → clarify intent-fit + sequencing.
  - **Trivial** (acknowledgement, status, greeting) → reply.
- **ACT**: Board/Council, delegation, source-grounding, sub-agent return.
  - Routing table (`agents/buddy/operational.md` §Delegation):
    code → main-code-agent · architecture → solution-expert · security → security
    · sysadmin → Buddy directly.
- **BOUNDARY**: post-action obligations (Context, History, Backlog), persist gate,
  mode determination (CWD lookup).

### Boot Sequence

`agents/buddy/boot.md`:

```
ORIENT  → date '+%Y-%m-%d %H:%M %Z' + hostname + pwd
RESOLVE → ls $CWD/intent.md (upward search)
ROUTE   → context routing (inside BuddyAI / external with context/ / external without)
LOAD    → always-load (values.md, profile.md, boot-navigation.md) + intent-load
RESUME  → session-buffer + session-handoff + plan_engine --boot (root sessions)
GREET   → short greeting (style: soul.md)
```

Parallelisation: at most 2 tool-call rounds (see `agents/buddy/boot.md`
§Parallelisation). Boot ends with the greeting — from the first user turn
all obligations from `operational.md` apply.

## Skill Model

### Single-class skill model

The old 4-class model is abolished. All skills are
ontologically equal. Variation lives on the orthogonal `invocation` axis.

```yaml
---
name: <skill-name>
description: >
  <What does the skill do in 1-3 sentences. Plus "Use when ..." trigger.>
status: active | draft | deprecated
invocation:
  primary: user-facing | workflow-step | sub-skill | hook | cross-cutting
  secondary: [<path>:<modifier>?, ...]
  trigger_patterns: ["..."]    # only when primary = user-facing
disable-model-invocation: true | false    # default false
modes: [<mode-name>, ...]    # omit when monomodal
---
```

**7 mandatory sections** (mentally enforced via Spec-Board L1):

1. Frontmatter (top, YAML)
2. Purpose (1-3 paragraphs)
3. When to invoke
4. Process (numbered steps; with modes: modes-process pattern)
5. Red Flags
6. Common Rationalizations (anti-excuse table, at least 2 rows)
7. Contract (INPUT / OUTPUT / DONE / FAIL)

**2 optional sections:** Verification (evidence requirements), Standalone-justification
(mandatory for new skills).

**Mechanical enforcement** via `scripts/skill_fm_validate.py` (Pre-Commit
Check 7, BLOCK for mandatory-field violations and unknown `invocation.primary`).

Detail: [`../framework/skill-anatomy.md`](../framework/skill-anatomy.md).

### Skill Inventory (as of May 2026)

38 active skills under `skills/<name>/`. The live inventory (canonical)
is the AUTO block in [`../framework/skill-map.md`](../framework/skill-map.md):

- **Direct-invokable** (`invocation.primary: user-facing`): `api_and_interface_design`,
  `caveman`, `deprecation_and_migration`, `improve_codebase_architecture`, `scoping`,
  `shipping_and_launch`, `task_creation`, `youtube_subtitles`, `zoom_out`.
- **Workflow-step / sub-skill**: `adversary_test_plan`,
  `architecture_coherence_review`, `bedrock_drill`, `code_review_board`,
  `convergence_loop`, `council`, `cross_spec_consistency_check`,
  `documentation_and_adrs`, `frame`, `frontend_design_tty`,
  `frontend_ui_engineering`, `get_api_docs`, `impl_plan_review`,
  `pre_build_spec_audit`, `python_code_quality_enforcement`,
  `retroactive_spec_update`, `return_summary`, `root_cause_fix`,
  `sectional_deep_review`, `security_and_hardening`,
  `source_spec_reduce`, `spec_amendment_verification`, `spec_authoring`,
  `spec_board`, `task_status_update`, `testing`.
- **Cross-cutting**: `consistency_check`, `knowledge_processor`,
  `transparency_header`.
- **Draft / deprecated** (kept for back-compat, not part of the 38
  active count): `knowledge_capture` (draft), `spec_update` (deprecated).

Plus 13 `_protocols/` (skill-level cross-cutting mechanisms).

### Modes Convention

One axis per skill: **depth** (`quick/standard/deep`), **topic** (skill-specific),
**phase** (lifecycle), **level** (`L0/L1/L2/L3`), **scope** (`focused/broad/exhaustive`).
Hard convention: max 3 modes per skill (exception: phase axis).

## Workflow Model

Workflows (`workflows/runbooks/<name>/WORKFLOW.md`) are the
**user-facing layer** — the user triggers "solve" / "build" / "fix" /
"save"; skills are invoked by workflow steps.

### Producer Class (5-Phase Standard)

`build`, `fix`, `review`, `solve`:

```
Specify → Prepare → Execute → Verify → Close
```

Per phase: skills, input, output, gate, failure-behaviour, autonomy, protocols.
For detail see `workflows/runbooks/<name>/WORKFLOW.md`.

### Other Classes

- **Documentation**: `docs-rewrite` — reader-journey first.
- **Operations**: `save` — end-of-session persistence, 3 groups (A pre-write,
  B content-writes parallel, C post-write).
- **Maintenance**: `context_housekeeping` — periodic upkeep.
- (Bootstrap — previously `selfhost/new-host-bootstrap`, removed 2026-05-02 and moved into the consumer repo `~/projects/sysadmin/`.)

### Path Determination (build)

`workflows/runbooks/build/WORKFLOW.md` §Path Determination:

```
ALL three? (a) ≤3 files (b) no spec (c) no new behaviour → DIRECT
At least ONE? (a) >1 subsystem (b) new subsystem (c) new pattern
  (d) schema change (e) >10 ACs → FULL
Otherwise → STANDARD
```

DIRECT: inline delegation → MCA → L0 → return. No board, no gate file,
no state file. Exception: pre-commit hooks remain (NON-NEGOTIABLE).

## Workflow Engine (Cross-Session State Machine)

`scripts/workflow_engine.py` is the **runtime orchestration layer** between
Buddy and the workflows. Workflows exist in two representations:

- `WORKFLOW.md` — prose SoT, reader-oriented, describes phases + steps in full depth
- `workflow.yaml` — machine-readable state machine, engine input

Without the engine: workflows would be a reading document that Buddy mentally works through
— failure mode on long workflows / session changes is "Buddy forgets where
he is". With the engine: every step has a unique id, completion check, on_fail
policy, persisted state.

### CLI Interface

| Command | Effect |
|---|---|
| `--start <wf> --task <id>` | New workflow → state file `.workflow-state/<wf>-<task-id>-<ts>.json`. Step pointer at step 0. |
| `--start ... --route <name>` | Path routing activated (top-level `routes:` in workflow.yaml). Steps in OTHER routes eager-skipped as `STATUS_ROUTE_SKIPPED`. Default `--route standard` if yaml has routes but no flag is set. Distinct from `--complete --route` (mid-flow classification step). |
| `--next` | Returns the instruction of the current step + completion condition. Idempotent. |
| `--complete --evidence "..."` | Marks current step done, advances pointer. Idempotent — re-run without effect. |
| `--complete <step> --route <key>` | Mid-flow route selection at a classification step. Differs from `--start --route` (eager at-creation). |
| `--retry <step> --reason "..."` | Reset terminal-or-in-progress step → in_progress, iteration counter +1. State file tracks `retry_history`. Iteration cap default 3 (overridable via top-level `iteration_cap` in workflow.yaml OR `--reason "override: <rationale>"`). |
| `--status` | Active workflows + step list with done/pending/route_skipped. |
| `--boot-context` | Compact resume line for boot.md GREET incl. `route: sub-build` when active. |
| `--validate` | State-file integrity (no YAML/doc validator — see `validate_runbook_consistency.py`). |
| `--abort <id> --reason "..."` | Archive move + audit trail. |
| `--recover` | Repairs broken state files (corrupt JSON from a crash). |

### State-File Layout

`.workflow-state/<workflow>-<task-id>-<timestamp>.json` (gitignored, per
checkout). Schema:

```json
{
  "schema_version": "2",
  "workflow_id": "build-380-20260501T1505",
  "workflow": "build",
  "task_id": "380",
  "started_at": "2026-05-01T15:05:42Z",
  "current_step": 7,
  "selected_route": "sub-build",
  "steps": [{"id": "...", "status": "done|pending|skipped|route_skipped", "evidence": "..."}],
  "variables": {"state_file": "docs/build/2026-05-01-task-380-feature.md"}
}
```

### Atomicity + Concurrency

- **Atomic write**: write to `<file>.tmp` + `os.replace(tmp, file)` (POSIX
  guarantees rename atomicity, anti-corruption against crash mid-write)
- **Locking**: `fcntl.flock` via `_state_lock()` context manager around
  all read/write operations — prevents race conditions when
  the UserPromptSubmit hook + Buddy access state in parallel
- **Corrupt warning**: corrupt state files are reported (stderr) instead of
  silently skipped — the user notices the problem, rather than "workflow vanished"

### Mandatory-Use vs Skip-List

Per `agents/buddy/operational.md` §Workflow Engine: build/fix/refactor/solve/
review/research/docs-rewrite **MUST go through the engine**. Skip list:

- DIRECT-path build/fix (≤3 files, no spec, no new behaviour)
- save/quicksave/checkpoint/wakeup/sleep (no multi-step state)
- context_housekeeping (maintenance workflow without pause points)
- frame/bedrock_drill standalone (sub-skills)
- think! (open discussion)

Enforcement: pre-commit Check 8 (ENGINE-USE) WARNs for feat/fix/refactor with
`[Task-NNN]` without an active workflow.

### Cross-Session Resume

- Boot step 5 STATUS-CHECK + step 6 RESUME → `--boot-context` injects a
  resume line that `Step 7 RESUME` hands to the user
- UserPromptSubmit hook (`workflow-reminder.sh`) renders `WORKFLOW-ENGINE:
  NEXT: <wf> [Task N] > step-i/n: <instruction>` as `additionalContext` in
  every user turn — Buddy sees it before each reply
- Hard cap: 200 characters so the hook does not cause context bloat
- Fast path: `timeout 2 python3 ...` so boot is not slowed down

### Multi-Machine Constraint

`.workflow-state/` is gitignored — per checkout, per machine. If you start a task
on laptop A and continue on laptop B:

- The state file is NOT on laptop B
- Buddy on laptop B sees no active workflow
- Corrections: either start over (`--start <wf> --task <id>`, current_step=0)
  or transfer the state file manually via a sync mechanism (rsync/scp)

This is a deliberate constraint — it prevents conflicts on concurrent state
writes from two CC sessions at the same time. Cross-repo: the `BUDDY_PROJECT_ROOT`
env var (set by the `cc` launcher) determines which `.workflow-state/`
applies — for `cc framework` the framework repo, for `cc <project>` the project repo.

### Three-SoT Reconciliation

Workflow phase information exists in three places:

| SoT | Content | Authoritative for |
|---|---|---|
| `.workflow-state/<id>.json` | engine state, step pointer | step-by-step progress |
| `docs/<wf>/<slug>.md` frontmatter | `phase: specify\|prepare\|...` | high-level phase |
| `docs/tasks/<id>.yaml` | `workflow_phase` field | task-driven view |

Reconciliation rule (operational.md §Workflow Engine): on conflict
between the three → engine state is authoritative for step pointer,
docs frontmatter is authoritative for phase name, task yaml follows.
The `task_status_update` skill writes all three in one move.

## Boards

### Spec-Board (`skills/spec_board/SKILL.md`)

Multi-perspective review for **specs** (rebuild fitness). 5 dimensions:
completeness, consistency, implementability, interface contracts, dependencies.

| Mode | Team |
|---|---|
| Standard | Chief + Adversary + Implementer + Impact (4) |
| Deep Pass 1 | + Adversary-2 + a second instance of Adversary (model=sonnet, finding-prefix F-A3-) + Consumer = 7 |
| Deep Pass 2+ | 4 (Adv + Adv2 + Impl + Impact) |
| Deep Final | 2 (Adv + Impl) |
| `mode=ux` | UX-Board (Heuristic + IA + Interaction) — absorbs the former `ux_review` |

Convergence via `convergence_loop` (max 3 passes).

### Code-Review-Board (`skills/code_review_board/SKILL.md`)

Multi-perspective review for **code diffs**. 2 levels:

```
L1 (Focused): ≤5 files AND no new module AND no schema change AND effort S-M
L2 (Full):    >5 files OR new module OR cross-spec OR schema change OR effort L-XL
When in doubt: L2.
```

**Core (always):** `code-review` (multi-axis correctness/architecture/performance) +
`code-adversary` (concurrency, edge cases, data corruption).

**Specialists (after risk assessment):** `code-security`, `code-data`,
`code-reliability`, `code-domain-logic`, `code-api-contract`, `code-ai-llm`,
`code-spec-fit`, `code-spec-drift`, `code-docs-consumer`.

**Chief:** `code-chief` (consolidation, dedup, severity ranking, noise filtering).

Multi-axis hybrid: code-quality + code-architecture + code-performance
absorbed into the **`code-review` multi-axis persona** (3 → 1, council decision).

### Council (`skills/council/SKILL.md`)

Structured architectural decision. Two modes:

- **Architectural Council**: 3-4 `council-member` subagents in parallel,
  context isolation, Buddy consolidates.
- **Interactive Council**: Buddy moderates a user dialogue with perspectives
  (phase 1-2-3).

Trigger: >1 path + hard to reverse, >1 layer, substantial impact, Buddy unsure.

## Hooks (Mechanism)

`orchestrators/claude-code/hooks/`:

| Hook | Trigger | Behaviour |
|---|---|---|
| `path-whitelist-guard.sh` | PreToolUse(Edit/Write/NotebookEdit/Bash) | BLOCK writes outside `.claude/path-whitelist.txt` |
| `frozen-zone-guard.sh` | PreToolUse | BLOCK writes inside `.claude/frozen-zones.txt` |
| `delegation-prompt-quality.sh` | PreToolUse(Task) | WARN <200 characters + missing plan-block keyword + (Check C) MCA dispatch without `implicit_decisions_surfaced` section on a substantive dispatch (Item 4 brief-quality gate) |
| `mca-return-stop-condition.sh` | PostToolUse(Task) | WARN when subagent_type=main-code-agent + the MCA return contains Stop-Condition / ESCALATE / ARCH-CONFLICT / AUTO-FIXED keywords. Pattern-Lesson 388 F-CR-004 (Item 2 mechanical Stop-Condition enforcement). |
| `board-output-check.sh` | PostToolUse(Task) | WARN on a dispatch prompt with a file-output pattern when the expected file is missing post-task. Pass-through fallback suggestion in the WARN. |
| `pre-commit.sh` | git pre-commit | 12 checks (see below) |
| `state-write-block.sh` | PreToolUse | state-file protection |
| `workflow-commit-gate.sh` | git pre-commit | workflow-state consistency |
| `workflow-reminder.sh` | UserPromptSubmit | workflow-engine `additionalContext` injection (NEXT step + task) every turn |
| `post-commit-dashboard.sh` | git post-commit | dashboard refresh |

### Pre-Commit 12 Checks

`orchestrators/claude-code/hooks/pre-commit.sh`:

| # | Check | Severity | Implementation |
|---|---|---|---|
| 1 | PLAN-VALIDATE | BLOCK | `plan_engine.py --validate` 0 errors |
| 2 | TASK-SYNC | WARN | status/readiness changes without `task_status_update` |
| 3 | OBLIGATIONS | WARN | docs/dashboard/plan_engine touched → deploy needed |
| 4 | CG-CONV | BLOCK | conventional-commit format |
| 5 | STALE-CLEANUP | WARN | STALE/RETIRED/SUNSET marker with live refs |
| 6 | PERSIST-GATE | WARN | status change without context update |
| 7 | SKILL-FM-VALIDATE | BLOCK | `skill_fm_validate.py` mandatory fields + invocation + `relevant_for` |
| 8 | ENGINE-USE | WARN | feat/fix/refactor + `[Task-NNN]` without an active workflow in `.workflow-state/` |
| 9 | RUNBOOK-DRIFT | WARN | `validate_runbook_consistency.py --staged` — workflow.yaml ↔ WORKFLOW.md drift (phase comments, step-name keywords, derived_from) |
| 10 | AGENT-SKILL-DRIFT | WARN | `generate_agent_skill_map.py --check` — `agents/<name>.md` AUTO block out of sync with skill `relevant_for:` frontmatter |
| 11 | SECRET-SCAN | WARN | `gitleaks protect --staged` (skipped when gitleaks is not installed, 24h-suppressed note WARN) |
| 12 | SOURCE-VERIFICATION | WARN | board/council reviews must cite source files (line-numbered evidence pointers) |

The 9 WARN checks are deliberately not BLOCK — trace markers would be faux
mechanism (trivially settable). The real failure class: Buddy forgets a skill, not
"actively bypasses". WARN is enough and does not disturb pure cosmetic commits.

## Engines + Generators

`scripts/`:

| Script | Role |
|---|---|
| `plan_engine.py` (~3.6k LoC) | Computed planning layer. DAG, critical path, validate, --boot, --status, --check |
| `workflow_engine.py` (~2.5k LoC) | YAML-driven workflow orchestration. --start, --next, --complete, --status, --recover |
| `generate_skill_map.py` (230 LoC) | Regenerates the AUTO block in `framework/skill-map.md` from disk frontmatter |
| `generate_navigation.py` (310 LoC) | Regenerates the AUTO block in 8 navigation.md files |
| `generate_agent_skill_map.py` (~270 LoC) | Regenerates the AUTO block in opt-in `agents/<name>.md` + the aggregated `framework/agent-skill-map.md` from skill frontmatter `relevant_for:` |
| `skill_fm_validate.py` (~280 LoC) | Pre-commit Check 7 — frontmatter validator incl. `relevant_for` |
| `validate_runbook_consistency.py` (~210 LoC) | Pre-commit Check 9 — workflow.yaml ↔ WORKFLOW.md drift heuristic |
| `generate-architecture.py` (475 LoC) | architecture-doc generator |
| `generate-control.py` / `generate-dashboard.py` / `generate-status.py` | dashboard + control + status generation |

**Generator + validator pattern**: drift-prone indices are generated
(disk = SoT), validator hooks check idempotency. `consistency_check` Check 6
for skill-map, Check 8 for navigation. workflow yaml ↔ md via Check 9.
Agent-skill awareness via Check 10 — skill frontmatter `relevant_for: [agents]`
is SoT, the generator writes the AUTO block in opt-in agent files.

## Runtime Components

Components that live in the framework but are not directly visible as a skill
or workflow. The reader typically encounters them via a WARN or output —
this is the anchor explanation.

### `plan_engine.py`

Computed-planning layer: reads `docs/plan.yaml` + `docs/tasks/*.yaml`,
builds the DAG from tasks/milestones/north-star, computes the critical path,
returns boot status (`--boot`), validates (`--validate`).

**When does the reader touch this?** Indirectly at boot — `plan_engine --boot`
returns the status block ("In Progress / Critical Path / Next Actions /
Milestones"). Plus pre-commit Check 1 (PLAN-VALIDATE BLOCK) enforces
consistency: blocked_by cycles, missing spec_ref, invalid status values
are caught at commit time.

### `docs/dashboard/` + `generate-dashboard.py`

Tasks-based visualisation as static HTML
(`docs/dashboard/index.html`, ~1.8 MB). The generator reads plan/tasks from
one or more repos (multi-repo via the `DASHBOARD_PROJECTS` env var)
and writes the HTML.

**Local vs server**: the dashboard can be viewed **locally** —
`generate-dashboard.py` produces the HTML, `xdg-open docs/dashboard/index.html`
opens it in the browser. Server push is optional via `deploy-docs.sh`
and only useful for multi-device setups or sharing.

**Hacky caveat**: the dashboard is one big script without
component architecture. Deliberate pragmatism (read-only visualisation,
nothing production-grade) — for a serious dashboard a framework-native
rebuild would be needed.

### `deploy-docs.sh` + `deploy-dashboard-lite.sh`

Optional deploy scripts for users who want to push the dashboard to their own
server. Configuration via `~/.config/forge/deploy.env`
(env-driven, **no user-specific defaults in the code**). Script-required:
`DEPLOY_REMOTE`, `DEPLOY_REMOTE_PATH`, `DASHBOARD_PROJECTS`,
`DASHBOARD_HOST_REPO`. Without deploy.env: the script fails fast with a clear
error message, no default Hetzner push.

**Can be ignored**: anyone who only works locally does not need this.
The dashboard is generated regardless (by `generate-dashboard.py`,
not by deploy-docs).

### Pre-Commit `OBLIGATIONS` Check

Pre-commit Check 3 WARN. Triggers when `docs/dashboard/` or plan-relevant
files (tasks, plan) are changed in a commit. A reminder that the dashboard
should be redeployed (otherwise the hosted version drifts away
from the repo state).

**When does the reader see this live?** On every commit that touches tasks or plan
— a typical daily-user experience. The reader thereby learns that there is a
dashboard and that the lifecycle is active.

## Data Flows (Three Examples)

### Boot

```
$ cc framework
  → orchestrators/claude-code/bin/cc resolves $FRAMEWORK_DIR
  → ensures ~/.claude/agents → $FRAMEWORK_DIR/.claude/agents
  → ensures ~/.claude/skills → $FRAMEWORK_DIR/.claude/skills
  → exec claude --add-dir $FRAMEWORK_DIR --add-dir $CWD --agent buddy
  → CC finds .claude/agents/buddy.md (wrapper)
  → Wrapper loads agents/buddy/{soul,operational,boot}.md
  → Boot sequence: ORIENT → RESOLVE → ROUTE → LOAD → STATUS-CHECK → RESUME → GREET
                                                  ▲              ▲
                                                  │              │ workflow_engine.py
                                                  │              │ --boot-context (active
                                                  │              │ workflows + state files)
                                                  │
                                                  │ git-status-check.sh
                                                  │ (parallel fetch + status for
                                                  │  FRAMEWORK_DIR + CWD, realpath-deduped)
```

### Build (Standard Path)

```
User: "implement feature X"
  → Buddy: path determination (DIRECT/STANDARD/FULL)
  → Phase Specify
      task_status_update → in_progress
      Create gate file
      INTERVIEW via frame (8 sub-steps)
      Write SPEC
      BOARD via spec_board (standard, 4 reviewers)
        → Chief consolidation → Buddy reads ONLY the chief signal
  → Phase Prepare
      TEST-DESIGN via testing
      DELEGATION artefact with MUST constraints
  → Phase Execute
      MCA inline (plan → plan-review → implement → L0)
  → Phase Verify
      code_review_board (L1 or L2)
        → 2-N reviewers in parallel → code-chief consolidation
  → Phase Close
      task_status_update → done
      Commit guard (pre-commit hooks)
      Deploy
```

### Sub-Agent Dispatch

```
Buddy has a plan block or gate file
  → Buddy invokes the Agent tool with subagent_type, prompt, isolation?
  → CC PreToolUse: delegation-prompt-quality.sh
      WARN if <200 characters
  → Sub-agent boot:
      .claude/agents/<name>.md found
      Wrapper loads agents/<name>.md (SoT)
      Persona protocol(s) inlined
  → Sub-agent runs, writes review file / code diff
  → Returns
  → Buddy reads the return summary (return_summary/SKILL.md format)
  → For a board: chief consolidates, Buddy reads ONLY the chief signal (CLAUDE.md §1)
  → Persist gate
```

## Extension Points

| Point | Mechanism | Example |
|---|---|---|
| New skill | `skills/<name>/SKILL.md` with the standard frontmatter; `Standalone` block; Spec-Board L1 PASS | `improve_codebase_architecture` |
| New workflow | `workflows/runbooks/<name>/WORKFLOW.md` + routing in `process-map.md` | `docs-rewrite` |
| New persona | `agents/<name>.md` (SoT) + `.claude/agents/<name>.md` (wrapper) | `code-review` multi-axis persona |
| New adapter | `orchestrators/<harness>/bin/<wrapper>` + hooks equivalent + wrapper files | (planned) Cursor |
| New hook | `orchestrators/claude-code/hooks/<name>.sh` + registration in `.claude/settings.json` | `mca-return-stop-condition.sh` |
| New reference | `references/<name>.md` with lift source documented | `orchestration-patterns.md` |
| New skill protocol | `skills/_protocols/<name>.md`; referenced via `uses:` in skills | `analysis-mode-gate.md` |

## Repository Structure in Detail

→ see [`03-repository-map.md`](03-repository-map.md).
