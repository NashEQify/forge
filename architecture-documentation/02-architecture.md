# 02 — Architecture

## High-Level

```
┌─────────────────────────────────────────────────────────────────────┐
│  USER                                                               │
└──────────────────────────────┬──────────────────────────────────────┘
                               │ (CLI: cc | oc | codex | cursor)
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│  HARNESS-ADAPTER (orchestrators/<name>/)                            │
│  - cc / oc: scope-routing, --add-dir composition                    │
│  - hooks/: SessionStart (boot) + git pre-commit (5 checks)          │
│  - ~/.claude/settings.json (user-global) registers SessionStart     │
└──────────────────────────────┬──────────────────────────────────────┘
                               │ loads
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│  TIER 0 — INVARIANTS                                                │
│  CLAUDE.md (CC) | AGENTS.md (OC)                                    │
│  6-8 invariants, never overridden                                   │
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
│  save | context_housekeeping                                        │
└──────────────────────────────┬──────────────────────────────────────┘
                               │ composes
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│  SKILLS (skills/<name>/SKILL.md)                                    │
│  41 active skills, single-class                                     │
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
│  PERSONAS (agents/<name>.md) — 40 total                             │
│  Buddy (Orchestrator)                                               │
│  Spec-Board (7: chief, adversary, adversary-2, implementer,         │
│    impact, consumer, architect-roots)                               │
│  UX-Board (3: ux-heuristic, ux-ia, ux-interaction)                  │
│  Code-Review-Board (15: chief, review, adversary, security, data,   │
│    reliability, domain-logic, api-contract, ai-llm, spec-fit,       │
│    spec-drift, docs-consumer, architect-roots, architect-lens,      │
│    verification)                                                    │
│  Council (3: council-member, council-chief, council-adversary)      │
│  Standalone (main-code-agent, solution-expert, security, tester,    │
│    test-skeleton-writer, plan-adversary, brief-architect,           │
│    buddy-thinking, spec-text-drift-batch)                           │
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
ROUTE   → context routing (project with context/ / external with context/ / external without)
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

### Skill Inventory

42 skill dirs under `skills/<name>/` — 41 active + 1 deprecated. The
live inventory (canonical) is the AUTO block in
[`../framework/skill-map.md`](../framework/skill-map.md):

- **Direct-invokable** (`invocation.primary: user-facing`):
  `api_and_interface_design`, `caveman`, `deprecation_and_migration`,
  `frontend_design_tty`, `improve_codebase_architecture`, `scoping`,
  `shipping_and_launch`, `show_open_tasks`, `task_creation`,
  `youtube_subtitles`, `zoom_out`.
- **Workflow-step / sub-skill**: `adversary_test_plan`,
  `architecture_coherence_review`, `bedrock_drill`, `code_review_board`,
  `convergence_loop`, `council`, `cross_spec_consistency_check`,
  `documentation_and_adrs`, `frame`, `frontend_ui_engineering`,
  `get_api_docs`, `impl_plan_review`, `knowledge_capture`,
  `pre_build_spec_audit`, `python_code_quality_enforcement`,
  `retroactive_spec_update`, `return_summary`, `risk_followup_routing`,
  `root_cause_fix`, `sectional_deep_review`, `security_and_hardening`,
  `source_spec_reduce`, `spec_amendment_verification`, `spec_authoring`,
  `spec_board`, `testing`.
- **Cross-cutting**: `consistency_check`, `knowledge_processor`,
  `task_status_update`, `transparency_header`.
- **Deprecated** (in tree, `status: deprecated`, not part of the 41
  active count): `spec_update`.

Plus 15 `_protocols/` (skill-level cross-cutting mechanisms).

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
- (Bootstrap — previously `selfhost/new-host-bootstrap`, moved into the consumer repo `~/projects/sysadmin/`.)

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
  "workflow_id": "build-123-<UTC-stamp>",
  "workflow": "build",
  "task_id": "123",
  "started_at": "<ISO-8601 UTC>",
  "current_step": 7,
  "selected_route": "sub-build",
  "steps": [{"id": "...", "status": "done|pending|skipped|route_skipped", "evidence": "..."}],
  "variables": {"state_file": "docs/build/<slug>.md"}
}
```

### Atomicity + Concurrency

- **Atomic write**: write to `<file>.tmp` + `os.replace(tmp, file)` (POSIX
  guarantees rename atomicity, anti-corruption against crash mid-write)
- **Locking**: `fcntl.flock` via `_state_lock()` context manager around
  all read/write operations — defense-in-depth against parallel CLI
  invocations reading or writing state concurrently
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

Enforcement: the engine itself is in usage standby; discipline-only.

### Cross-Session Resume

- Boot step 5 STATUS-CHECK + step 6 RESUME → `--boot-context` injects a
  resume line that `Step 7 RESUME` hands to the user
- Buddy reads workflow state on demand via `--boot-context` / `--next`.

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

Structured architectural / strategic decision. Four modes:

| Mode | Team | When |
|---|---|---|
| **light** | 3 `council-member` + `council-chief` (no adversary, no frame-check) | default on §1.0 proportionality pass — single-component, mid-reversible decisions |
| **standard** | 4 members + `council-adversary` + `council-chief` + pre-council frame-check (plan-adversary on briefing draft) | escalation tier: ≥2 of {hard-to-reverse, multi-component, security/sovereignty} |
| **full** | 5-7 members + `council-adversary` + `council-chief` + discourse + frame-check | foundational decisions / ≥2 hard constraints / >2 dimensions |
| **interactive** | Buddy moderates a user dialog with perspectives (phase 1-2-3) | user wants to think through together, not parallel-isolation |

**Consolidator-tool mandatory for ≥3 members** per CLAUDE.md Invariant 1
— Buddy reads only the chief signal, never the individual member files.

**Post-council coherence-check** (`agents/buddy/operational.md`
§Architecture-Comprehension B) re-applies unconditionally on chief return.

Personas added in the Stage-1 rewrite:
`agents/council-chief.md` (consolidator-tool, DISSENT preservation,
predicate-based verdict labels) and `agents/council-adversary.md`
(frame-acceptance / charity-overflow / past-similarity hunt;
challenges briefing framing itself).

Trigger: >1 viable path, hard to reverse, >1 component, Buddy uncertain
about which path is right.

## Hooks (Mechanism)

`orchestrators/claude-code/hooks/` — **3 hook scripts on disk**. The
hooks are universally portable (SessionStart + git pre-commit); there are
no tool-event hooks (PreToolUse / PostToolUse / UserPromptSubmit).
Write-time discipline is protocol-anchored (`agents/buddy/operational.md`).

| Hook | Trigger | Behaviour |
|---|---|---|
| `buddy-boot-inject.sh` | SessionStart | Triggers Buddy boot in claude-desktop / claude-web (where `--agent buddy` isn't an entrypoint flag). Load-bearing for boot on non-Terminal entrypoints. |
| `session-start-remote.sh` | SessionStart | Resume-nudge — checks for recent session-handoff at session start. |
| `pre-commit.sh` | git pre-commit + commit-msg | 5 checks (see below) — universally available across harnesses (git is portable). |

### Pre-Commit 5 Checks

`orchestrators/claude-code/hooks/pre-commit.sh` — 3 BLOCK + 2 WARN.

| # | Check | Severity | Implementation |
|---|---|---|---|
| 1 | PLAN-VALIDATE | BLOCK | `plan_engine.py --validate` must report 0 errors |
| 2 | CG-CONV | BLOCK | Conventional-Commits format (commit-msg authoritative; pre-commit mode skips to avoid F-102 amend-with-m stale-message false-positive) |
| 3 | SKILL-FM-VALIDATE | BLOCK | `skill_fm_validate.py` mandatory fields + invocation + `relevant_for` |
| 4 | SECRET-SCAN | WARN | `gitleaks protect --staged` (skipped when gitleaks not installed, 24h-suppressed note WARN) |
| 5 | SOURCE-VERIFICATION | WARN | Board/council reviews must cite source files (line-numbered evidence pointers per `_protocols/evidence-pointer-schema.md`) |

## Engines + Generators

`scripts/`:

| Script | Role |
|---|---|
| `plan_engine.py` (~4.6k LoC) | Computed planning layer. DAG, critical path, validate, --boot, --status, --check |
| `workflow_engine.py` (~2.5k LoC) | YAML-driven workflow orchestration. --start, --next, --complete, --status, --recover |
| `generate_skill_map.py` (230 LoC) | Regenerates the AUTO block in `framework/skill-map.md` from disk frontmatter |
| `generate_navigation.py` (310 LoC) | Regenerates the AUTO block in 8 navigation.md files |
| `generate_skill_wrappers.py` (~520 LoC) | Regenerates `.claude/skills/<name>/SKILL.md` Claude-Code discovery wrappers from skill frontmatter (Option-C inclusion + `cc_wrapper` override; marker-gated deletion); validator `consistency_check` Check 10 |
| `generate_agent_skill_map.py` (~360 LoC) | Regenerates the AUTO block in opt-in `agents/<name>.md` + the aggregated `framework/agent-skill-map.md` from skill frontmatter `relevant_for:` |
| `skill_fm_validate.py` (~300 LoC) | Pre-commit Check 3 (SKILL-FM-VALIDATE) — frontmatter validator incl. `relevant_for` |
| `validate_runbook_consistency.py` (~300 LoC) | `consistency_check` Check 9 — workflow.yaml ↔ WORKFLOW.md drift heuristic |
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

### Dashboard-redeploy reminder

When `docs/dashboard/` or plan-relevant files (tasks, plan) change in a
commit, the dashboard should be redeployed — otherwise the hosted version
drifts from the repo state. Redeploy is discipline.

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
      (Brief discipline lives in _protocols/mca-brief-template.md +
       dispatch-template.md; no PreToolUse hook)
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
| New hook | `orchestrators/claude-code/hooks/<name>.sh` + entry in `orchestrators/claude-code/settings.json.template` (re-applied to `~/.claude/settings.json` via `setup-cc.sh`) | `session-start-remote.sh` |
| New reference | `references/<name>.md` with lift source documented | `orchestration-patterns.md` |
| New skill protocol | `skills/_protocols/<name>.md`; referenced via `uses:` in skills | `analysis-mode-gate.md` |

## Repository Structure in Detail

→ see [`03-repository-map.md`](03-repository-map.md).

## Next step

Repository topology and where what lives:
[`03-repository-map.md`](03-repository-map.md).
