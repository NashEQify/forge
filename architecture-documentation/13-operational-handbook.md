# 13 — Operational Handbook

How the framework actually *operates* day-to-day. The methodology behind
the file structure. What's different from baseline Claude Code or
OpenCode usage. How sessions, commands, and workflows fit together.

If you only read one file in `architecture-documentation/`, this is a
strong candidate.

---

## The methodology in one paragraph

You open a terminal, run `cc <scope>`. Buddy boots — reads Tier-0
invariants, the operational rules, the boot routing. He greets you and
asks what's up. Whatever you say, he routes through three phases:
**RECEIVE** (incident? substantive? trivial?), **ACT** (delegate, dispatch
boards, work skills), **BOUNDARY** (persist context, update task state,
close the loop). Mechanical hooks block paths that aren't whitelisted,
freeze WORM zones, and validate every commit against 12 checks. When
Buddy needs to do something non-trivial, he writes a Plan-Block before
acting. When he needs multiple perspectives, he dispatches a Board and
reads only the chief signal — never the individual reviewer outputs.
When he's unsure, he asks. Default is *discuss*, not *implement*.

That's the loop. Everything else is detail.

---

## What's different from baseline Claude Code / OpenCode usage

If you've used Claude Code without this framework, here's what changes:

### 1. Buddy is the only entry point

You don't talk to specialized agents directly. You talk to **Buddy**.
Buddy decides whether to do it himself, dispatch a sub-agent, or invoke a
multi-perspective board. This collapses the "which agent should I call?"
question into a single conversation.

### 2. Default is "discuss before doing"

Vanilla Claude Code defaults to action — you ask, it acts. Buddy defaults
to *discuss* unless the imperative is unambiguous. Self-triggered changes
(things Buddy noticed on his own) **always** go through discussion first.
This is `CLAUDE.md §2`.

The cost: more turns. The benefit: you don't wake up to find Buddy "fixed"
something you didn't want fixed.

### 3. Pre-Delegation is not negotiable

Before any sub-agent call, Buddy writes a Plan-Block:

```
Scope:        what's touched, what's not
Tool/Agent:   which sub-agent, with which constraints
Alternatives: min 2, with reason why-not
Expected:     what artefacts come back
```

Plus a Self-Review (Scope-Check, Instance-vs-Class, Rationalization-Reflex).
For non-trivial actions, additionally a Plan-Adversary review (a
context-isolated persona that argues why the plan is wrong).

This is `CLAUDE.md §3` + `skills/_protocols/plan-review.md`.
The `delegation-prompt-quality.sh` hook warns when sub-agent prompts are
shorter than 200 chars — a proxy for "Buddy skipped writing a real brief".

### 4. Boards run multi-perspective, Buddy doesn't co-read

Spec-Board (4-7 reviewers depending on depth) and Code-Review-Board (L1
focused / L2 full) operate by **anchoring discipline**: Buddy spawns
context-isolated reviewers, waits for them all to complete, lets the
chief persona consolidate, and reads ONLY the chief signal.

He does NOT read individual reviewer files. If he did, his interpretation
would corrupt the multi-perspective. This is `CLAUDE.md §1` and is the
hardest discipline to get right — multiple architectures of the framework
have evolved to make it robust (`_protocols/dispatch-template.md`,
`_protocols/context-isolation.md`, `_protocols/consolidation-preservation.md`).

### 5. Skills, Workflows, Personas — three separate layers

Vanilla Claude Code has agents and slash-commands. The framework adds:

- **Skills** (`skills/<name>/SKILL.md`): methodology with
  7-section anatomy + 5-mode invocation axis. Skills don't run, they're
  *applied*.
- **Workflows** (`workflows/runbooks/<name>/WORKFLOW.md`): phase
  sequences that compose skills (e.g. `build` has Specify → Prepare →
  Execute → Verify → Close).
- **Personas** (`agents/<name>.md`): tool-neutral agent definitions
  with their own discipline (reviewer-base, reasoning-trace, first-
  principles-check).

The User triggers Workflows. Workflows invoke Skills. Skills (sometimes)
dispatch Personas. Three layers, clear contract.

### 6. Mechanical enforcement at multiple levels

| Level | Mechanism | Examples |
|---|---|---|
| Tool-use | PreToolUse hooks | `path-whitelist-guard`, `frozen-zone-guard`, `delegation-prompt-quality` |
| Commit-time | Pre-commit hook | 12 checks (PLAN-VALIDATE, CG-CONV, SKILL-FM-VALIDATE = BLOCK; TASK-SYNC, OBLIGATIONS, STALE-CLEANUP, PERSIST-GATE, ENGINE-USE, RUNBOOK-DRIFT, AGENT-SKILL-DRIFT, SECRET-SCAN, SOURCE-VERIFICATION = WARN) |
| Index-level | Generator + Validator | `generate_skill_map.py` + `consistency_check` Check 6, `generate_navigation.py` + Check 8 |

Vanilla Claude Code has none of these. They are user-installed during
`scripts/setup-cc.sh` plus a single git-hook symlink per repo.

---

## How to use it well

Frame, drill, council, board — these are not "magic-think" tools. Garbage
in, garbage out applies more, not less, to multi-agent runs: parallel
reviewers all multiply the same mush.

| Tool | What it needs |
|---|---|
| **Frame** (8-step problem analysis) | A sharp problem statement. Not "think about X" — your current best understanding, named. |
| **Bedrock-drill** (recursive axiom challenge) | A candidate axiom. *"I believe X because Y"* — the drill challenges Y. Without Y, no drill. |
| **Council** (3-7 architects + adversary) | A real decision: >1 option, irreversibility risk, your trade-off sketch. Not "what do you think generally". |
| **Spec-Board** (4-7 reviewers + chief) | A written spec. Run spec-authoring first, then board the spec. Boarding a vibe wastes parallel reviewers. |
| **Code-Review-Board** (L1: 2 / L2: 13 reviewers) | A diff to review. Narrower scope = sharper review. |
| **`solve` workflow** (open-ended problem) | A problem you can't see the shape of. If you can — `build` is faster. |
| **`fix` workflow** (root-cause first) | A bug with reproduction path. If reproduction is unclear — `solve` first. |

Common short-circuit: *"drill my intent first"* — if Buddy starts producing
without asking, you can force the clarification step. Don't accept solution-
output before intent is sharp.

The cost of bringing weak input is high — the multi-perspective machinery
amplifies the input quality. Sharp input + 4 reviewers = 4× sharp signal.
Mush input + 4 reviewers = 4× confused noise.

Pattern detail: see [`../framework/agent-patterns.md`](../framework/agent-patterns.md)
(in particular *Reader-Facing-Surface-Detection* for documentation drift detection).

---

## Commands and triggers

The framework has **no slash-commands**. Buddy responds to natural-language
trigger words, defined in `agents/buddy/operational.md §Commands`:

| User says | Buddy does |
|---|---|
| (initial greeting) | Boot sequence ORIENT → RESOLVE → ROUTE → LOAD → STATUS-CHECK → RESUME → GREET |
| `wakeup` | Re-boot session continuity from `session-handoff.md` + `plan_engine --boot` |
| `save` | End-of-session persist via `workflows/runbooks/save/WORKFLOW.md` |
| `quicksave` | Mid-session light persist (subset of save) |
| `checkpoint` | Save + drift-check + sculpting (deep version) |
| `sleep` | Forget the session (no persist) |
| `think!` | THINK-Stance: deeper analysis mode (`agents/buddy/think-operational.md`) |
| `consistency check` | Invoke `consistency_check` skill (8 checks) |
| `solve <problem>` | Trigger solve-Workflow (problem with open solution-form) |
| `build <task>` | Trigger build-Workflow |
| `fix <bug>` | Trigger fix-Workflow (root-cause-first) |
| `review <spec>` | Trigger review-Workflow (no code) |
| `research <topic>` | Trigger research-Workflow (knowledge artefact) |
| `frame <problem>` | Standalone frame-Skill (8-step problem analysis) |
| `task: <description>` | Invoke `task_creation` skill |
### Council mechanics
- **External-Review-Bundle** (`framework/external-review-bundle-format.md`):
  when argument-decisive override + re-council inversion + high-effort
  follow-on task + architectural decision (all four) align, an
  external-discipline check pays off. Bundle with mandatory upload
  list + self-sanity-check + substantive-vs-structural output format.
- **Council adversary mandatory:** 4 domain members + 1 adversary. The
  adversary does smart-but-wrong + explicit authority check, no lean
  statement. Empirically: ~20-30% catch rate for drift the domain
  members miss.

Detail of council patterns:
[`../framework/agent-patterns.md`](../framework/agent-patterns.md).

Workflow-Engine has CLI commands too:

```bash
python3 $FRAMEWORK_DIR/scripts/workflow_engine.py --start <wf> --task <id>
python3 $FRAMEWORK_DIR/scripts/workflow_engine.py --next --id <wf-id>
python3 $FRAMEWORK_DIR/scripts/workflow_engine.py --complete <step-id>
python3 $FRAMEWORK_DIR/scripts/workflow_engine.py --status
```

These are run by Buddy (or you) via terminal-integration. State files live
under `docs/<workflow>/<date>-<slug>.md`.

---

## Workflow-Engine — cross-session workflow continuity

The framework's most important state mechanism for multi-session work.
Buddy uses it (mandatory, per `agents/buddy/operational.md §Workflow-Engine`)
for non-trivial workflows (`build` STANDARD/FULL, `fix`, `review`, `solve`,
`research`, `docs-rewrite`).

### What it is

`scripts/workflow_engine.py` is a YAML-driven state machine. Workflow
definitions live alongside their runbooks: `workflows/runbooks/<name>/workflow.yaml`.
Each definition has steps with `id`, `instruction`, `completion`-check,
`on_fail`-policy, optional `skill_ref` and `context_refs`.

State persists in `.workflow-state/<workflow-id>.json` (gitignored — runtime
state per local checkout). The workflow-state JSON contains: workflow-id,
current step, step-history (completed/skipped/failed), variables, parent
linkage for sub-workflows.

### Why it exists

Three failure modes it prevents:

1. **Orchestrator forgets mid-workflow.** Buddy is in build Phase Verify
   on turn 47, gets a side-question, comes back, forgets where he was. The
   engine's `--next` and the UserPromptSubmit-hook `workflow-reminder.sh`
   inject the current step into every turn's context.

2. **Cross-session resumption.** Session crashes, new agent boots. Boot-step
   `WORKFLOW-RESUME` calls `--boot-context`. Active workflows surface in
   the greeting. Buddy reads the corresponding state-files (`docs/<workflow>/<slug>.md`)
   to rehydrate content state. Picks up exactly where left off.

3. **External reviewer / new agent need to know state.** `--status` lists
   all active workflows. Each workflow's state-file has its phase outputs
   in markdown. Anyone reading the repo can see "currently in solve workflow,
   step `frame-report`, here's what's been done so far" without asking Buddy.

### CLI

```bash
# Start a workflow
python3 $FRAMEWORK_DIR/scripts/workflow_engine.py --start solve --task 123

# Show next step (instruction + skill_ref + context_refs)
python3 $FRAMEWORK_DIR/scripts/workflow_engine.py --next

# Mark step complete (advances to next, runs completion-check)
python3 $FRAMEWORK_DIR/scripts/workflow_engine.py --complete frame-report

# Skip step with reason (when step is conditional and N/A)
python3 $FRAMEWORK_DIR/scripts/workflow_engine.py --skip discovery --reason "AC empirically clear"

# All active workflows (compact summary)
python3 $FRAMEWORK_DIR/scripts/workflow_engine.py --status

# After crash: restart in-progress steps
python3 $FRAMEWORK_DIR/scripts/workflow_engine.py --recover

# Pause / resume
python3 $FRAMEWORK_DIR/scripts/workflow_engine.py --pause --id <wf-id>
python3 $FRAMEWORK_DIR/scripts/workflow_engine.py --resume --id <wf-id>

# Compact resume-block for boot
python3 $FRAMEWORK_DIR/scripts/workflow_engine.py --boot-context

# Workflow-state for session-handoff
python3 $FRAMEWORK_DIR/scripts/workflow_engine.py --handoff-context

# Find workflow by task-id
python3 $FRAMEWORK_DIR/scripts/workflow_engine.py --find --task 123
```

### How it integrates

- **Boot-Step `WORKFLOW-RESUME`** (`agents/buddy/boot.md` §6 RESUME) calls
  `--boot-context` automatically. Active workflows surface in GREET.
- **UserPromptSubmit Hook** `workflow-reminder.sh` (registered in
  `.claude/settings.json`) calls `--next --brief` on every user turn,
  injects current step into the model context as `WORKFLOW-ENGINE: <step info>`.
- **Save-Workflow Step A.3** calls `--handoff-context` to bake state into
  session-handoff.

### When to use, when to skip

**Mandatory** for: `build` STANDARD/FULL, `fix`, `review`, `solve`,
`research`, `docs-rewrite`.

**Optional / skip-eligible**:
- `build` DIRECT path (≤3 files, no spec, no new behaviour)
- `save` / `quicksave` (lifecycle workflows, no multi-session continuity)
- `context_housekeeping` (ad-hoc maintenance)

When in doubt: trigger the engine. CLI overhead is low (~3 calls per
workflow), cost-of-forgetting is high.

### State-file convention vs engine

The two are **complementary**:

| Mechanism | What it tracks | Persistence |
|---|---|---|
| `workflow_engine` `.workflow-state/<id>.json` | Step-pointer (which step is current) | Local-only, gitignored |
| State-File `docs/<workflow>/<slug>.md` | Phase content (findings, decisions, outputs) | Git-committed, version-controlled |
| Task-YAML `workflow_phase` field | Atomic phase status (specify/prepare/...) | Git-committed |

The engine knows *where you are*; the state-file knows *what's been done*;
the task-yaml knows the *phase boundary*. Together they make workflow
state durable across sessions and visible to outsiders.

---

## A typical session, step by step

You open a terminal:

```
$ cc framework
```

`cc` script (auto-detected `FRAMEWORK_DIR`):
- Verifies `~/.claude/agents` symlink → `$FRAMEWORK_DIR/.claude/agents`
- Verifies `~/.claude/skills` symlink
- `cd $FRAMEWORK_DIR`
- Calls `claude --add-dir $FRAMEWORK_DIR --agent buddy -n framework`

Claude Code finds `.claude/agents/buddy.md` (the wrapper). Wrapper says:
*"Load `agents/buddy/{soul,operational,boot}.md` and follow boot.md".*

Buddy (you, in agent-mode) reads the three files and runs the boot
sequence:

```
ORIENT  → date / hostname / pwd
RESOLVE → ls $CWD/intent.md → found, read it
ROUTE   → CWD inside framework, no consumer-context wiring
LOAD    → values.md + profile.md + boot-navigation.md + intent-load
RESUME  → session-buffer + session-handoff + plan_engine --boot
GREET   → "Boot done. What's up?"
```

You: *"There's a bug in `scripts/generate_skill_map.py`. It misses skills
whose frontmatter `status` field is on a folded line."*

Buddy classifies: **substantive** (you want him to do something).
Buddy writes a Plan-Block:

```
Scope: scripts/generate_skill_map.py + tests
Tool/Agent: main-code-agent (production code, not orchestrator)
Alternatives:
  - Alt 1: Buddy direct — would violate Code-Delegation invariant
  - Alt 2: Inline patch via Edit — no test, regression-prone
Expected: fix + failing test reproducing the bug + Pre-commit pass
```

Plus self-review (Scope-Check, Instance-vs-Class, Rationalization-Reflex).
For non-trivial: also Plan-Adversary.

Buddy routes to the **fix** workflow. Phase Specify:
- `root_cause_fix` skill, Phase A: Symptom → Hypothesis → Drill
- Test plan: failing test that reproduces the folded-line frontmatter gap

Phase Execute: `main-code-agent` is dispatched (with the Plan-Block as
delegation-artefact and the test plan). The sub-agent works in isolation.
PreToolUse hooks check every Edit/Write — `path-whitelist-guard` confirms
the path is OK. It produces a fix + green test.

Phase Verify: `code_review_board` L1 (because effort=S, ≤5 files). Two
reviewers in parallel: `code-review` (correctness/architecture/performance
multi-axis) + `code-adversary` (concurrency/edge/data-corruption). Then
`code-chief` consolidates.

Buddy reads ONLY `code-chief`'s signal. If PASS → Phase Close. If
NEEDS-WORK → fix iteration via `convergence_loop` (max 3 passes, rising
severity threshold).

Phase Close:
- `task_status_update` skill: status=done, workflow_phase=done
- `knowledge_processor mode=process`: extract any new learning to context
- Pre-commit hook fires:
  - PLAN-VALIDATE: 0 errors → PASS
  - CG-CONV: commit message format → PASS
  - SKILL-FM-VALIDATE: no skill changes → SKIP
  - TASK-SYNC: status changed via skill → PASS (no warn)
  - PERSIST-GATE: context updated → PASS
- Commit lands.

Total turns: ~15-25 depending on depth. The framework adds 5-10 turns of
overhead vs. raw "fix this bug" Claude Code use. The trade is that you
get a documented plan, an isolated review, and a state that's persisted
for next session.

---

## How consumer repos consume the framework

You have a consumer repo, say `~/projects/personal/`. It has its own
`intent.md`, its own `docs/tasks/`, its own context. You want Buddy in
that repo, with the same methodology.

### What you do once

```bash
# 1. Pre-commit hook — same hook everywhere
ln -sf "$FRAMEWORK_DIR/orchestrators/claude-code/hooks/pre-commit.sh" \
       ~/projects/personal/.git/hooks/pre-commit

# 2. (optional) post-commit dashboard hook
bash $FRAMEWORK_DIR/scripts/install-dashboard-hooks.sh
```

That's it. No vendoring. No version pinning. No re-install on framework
update.

### What happens at session start

```
$ cc personal       # or: cd ~/projects/personal && cc
```

`cc` looks up `personal` under `$PROJECTS_DIR/`, finds `intent.md`, cds
there, calls Claude Code with `--add-dir $FRAMEWORK_DIR --add-dir <CWD>`.

Buddy boots. RESOLVE finds `~/projects/personal/intent.md`. ROUTE
determines context-paths:
- consumer has `context/`? → write context-updates there
- consumer has `docs/backlog.md`? → use that backlog (not framework's)

LOAD pulls in the always-load files (values.md from `~/projects/personal/context/user/`
canonical, profile.md, boot-navigation.md from framework) + intent-load
files specified in the consumer's intent.md "Context" field.

The framework methodology is now live: pre-delegation discipline,
boards, hooks, all of it. Consumer-specific content (its tasks, specs,
context) is what the work happens *on*. The framework is what defines
*how*.

### Path discipline across repos

The pre-commit-hook is the single mechanical gate that runs in any repo
where you've symlinked it. It calls `plan_engine.py --validate` (which
auto-detects `BUDDY_PROJECT_ROOT` vs `FRAMEWORK_ROOT`), runs `skill_fm_validate.py`
(skipped gracefully in consumer repos that don't have `skills/`),
and enforces commit-message convention.

Path-whitelist-guard runs at Claude Code's PreToolUse — its file lives at
`$FRAMEWORK_DIR/.claude/path-whitelist.txt` (generated user-specific by
`setup-cc.sh`, gitignored). Patterns are `$HOME/projects/**` and
`$HOME/.claude/settings.json` — broad enough to cover all consumer repos.

OpenCode under a consumer: same `oc` command, same auto-detected config.
Cursor: project-rules under `.cursor/rules/` symlink to
`$FRAMEWORK_DIR/orchestrators/cursor/rules/`.

---

## What's different operationally vs. just "using Claude Code"

If you're used to vanilla Claude Code, here's what changes:

| Aspect | Vanilla CC | with forge |
|---|---|---|
| Session start | greet, go | Boot sequence with intent.md detection, parallel file loads, plan_engine state |
| First task | "fix this" → fix | "fix this" → Plan-Block → fix → review → close |
| Multi-perspective review | manual spawn | Spec-Board / Code-Review-Board with depth modes, chief consolidation, anti-anchoring discipline |
| Decisions | one-shot | Architectural Council for irreversible (3-4 personas in parallel, context-isolated) |
| State persistence | manual `/save` if you remember | `save` workflow with 3 groups (Pre-Write, Content-Writes parallel, Post-Write), session-handoff + session-log |
| Config drift | "let me update the prompt" | Tier-0 invariants + Tier-1 operational + Skill-Anatomy enforced via hook |
| Skill management | text in prompts | Single-class skills with `invocation` axis, frontmatter mechanically validated |
| Cross-repo | duplicate everything | Single SoT + adapters; consumers point at framework |
| Drift detection | none | `consistency_check` skill with 8 checks |
| Stale cleanup | manual sweep | Stale-Cleanup invariant + pre-commit STALE-CLEANUP warn |

The cost is higher per-task overhead. The win is that work compounds:
nothing falls through the cracks, multi-session continuity is real,
methodology drift is bounded.

---

## Daily use patterns

### Start a feature (clear intent)

```
You: "build feature X — spec is at docs/specs/x.md"
Buddy: → Path determination (DIRECT/STANDARD/FULL based on file count, spec, scope)
       → Phase Specify (frame interview if no spec, spec_board if spec exists)
       → Phase Prepare (test-design + delegation artefact)
       → Phase Execute (main-code-agent)
       → Phase Verify (code-review-board L1 or L2)
       → Phase Close (task_status_update done, commit)
```

### Investigate a bug

```
You: "the FACTS hook is failing on Linux"
Buddy: → fix workflow Phase Specify with root_cause_fix Phase A
       → Symptoms → Hypotheses → Drill (1-3 hypotheses, narrowest first)
       → Test plan reproducing the bug
       → Phase Execute: implement + green test
       → Phase Verify: code-review-board L1
       → Lessons Learned via knowledge_processor
```

### Research a topic

```
You: "research SOTA on agentic-skill libraries"
Buddy: → research workflow
       → CONTEXT-LOAD (existing research in <active-context>/research/)
       → SCOPE + QUALITY-LEVEL (Standard or High?)
       → WebFetch / WebSearch / synthesis
       → PERSIST via knowledge_capture
       → State-File at docs/research/<date>-<topic>.md
```

### Write a new spec

```
You: "we need a spec for the new dashboard panel"
Buddy: → spec_authoring skill
       → Phase 1: source-grounding + interview + solution-space exploration
       → Phase 2: spec writing (5 primitives)
       → spec_board for quality review (4-7 reviewers depending on depth)
       → convergence_loop for NEEDS-WORK iterations (max 3)
```

### Architectural decision

```
You: "should we use SQLite or Postgres for the new feature?"
Buddy: → council skill, Architectural mode
       → Briefing-file written to docs/reviews/council/<date>-<topic>-briefing.md
       → 3-4 council-members spawned in parallel, context-isolated
       → Each member writes <date>-<topic>-<role>.md
       → Buddy synthesizes to <date>-<topic>-synthesis.md
       → User-acceptance per decision
```

### End of session

```
You: "save"
Buddy: → save workflow
       → Group A (Pre-Write, sequential): dispatcher + reconciliation + workflow-state
       → Group B (Content-Writes, parallel batch):
         - session-handoff.md (merge, never blind-overwrite)
         - session-log.md (decisions/errors)
         - context updates (overview.md + history)
       → Group C (Post-Write): commit, pre-commit hooks fire
```

---

## When the framework gets in your way

Pre-Commit-Hook BLOCKs your commit. Path-whitelist denies a write.
`consistency_check` flags drift. Generators show diff after running.

These are not bugs in the framework. They're the framework working — it's
catching something that would have been latent drift in your repo.

The right responses:

| Block | Reason | Action |
|---|---|---|
| `path-whitelist-guard` BLOCK | Path outside `.claude/path-whitelist.txt` | Add the path to whitelist (template + setup-cc.sh) OR write somewhere allowed |
| `frozen-zone-guard` BLOCK | Trying to modify `context/history/**` | Use `.correction.md` sidecar convention; don't fight WORM |
| Pre-commit Check 7 BLOCK | Skill frontmatter invalid | Read `framework/skill-anatomy.md` §Frontmatter-Schema; fix fields |
| Pre-commit Check 4 BLOCK | Commit message format | Use `<type>(<scope>): <message>`. Types: feat/fix/chore/docs/refactor/test/style/perf/revert |
| `consistency_check` ERROR | Stale ref / orphan / drift | Fix in same commit (Stale-Cleanup invariant) |

When you're tempted to bypass with `--no-verify`: don't. Investigate the
root cause. The framework's whole value proposition is that the discipline
isn't optional.

---

## Files you'll touch in daily work

| File | When | Why |
|---|---|---|
| `intent.md` | New project; intent shift | Vision/Done/Non-Goals/Context |
| `docs/tasks/<id>.{md,yaml}` | New task | Self-contained task with intent_chain |
| `docs/plan.yaml` | Milestone change | Programme SoT (north_star, phases, milestones) |
| `skills/<name>/SKILL.md` | New skill / skill update | Skill anatomy mandatory |
| `workflows/runbooks/<name>/WORKFLOW.md` | New workflow / workflow update | 5-phase model for producer-class |
| `agents/<persona>.md` | Persona behavior change | SoT for both CC + OC adapter |
| `context/session-handoff.md` | Auto, via save | Don't hand-edit during session |
| `framework/skill-map.md` | Auto-block via generator | Don't hand-edit AUTO section |

When in doubt: `framework/process-map.md` (workflow routing) or `agents/navigation.md`
(persona lookup) for "where do I go for X?".

---

## Cross-references for deep dives

| Topic | Read |
|---|---|
| Tier-0 invariants in detail | [`../CLAUDE.md`](../CLAUDE.md) + [`../AGENTS.md`](../AGENTS.md) |
| Buddy's operational rules | [`../agents/buddy/operational.md`](../agents/buddy/operational.md) |
| Boot sequence detail | [`../agents/buddy/boot.md`](../agents/buddy/boot.md) |
| Skill anatomy spec | [`../framework/skill-anatomy.md`](../framework/skill-anatomy.md) |
| Workflow routing | [`../framework/process-map.md`](../framework/process-map.md) |
| Permission/Gate/Routing triple | [`../framework/agent-autonomy.md`](../framework/agent-autonomy.md) |
| Plan-Block + Self-Review mechanic | [`../skills/_protocols/plan-review.md`](../skills/_protocols/plan-review.md) |
| Frame skill (problem analysis) | [`../skills/frame/SKILL.md`](../skills/frame/SKILL.md) |
| Bedrock-Drill (first principles) | [`../skills/bedrock_drill/SKILL.md`](../skills/bedrock_drill/SKILL.md) |
| Spec-Board mechanics | [`../skills/spec_board/SKILL.md`](../skills/spec_board/SKILL.md) |
| Code-Review-Board mechanics | [`../skills/code_review_board/SKILL.md`](../skills/code_review_board/SKILL.md) |
| Council mechanics | [`../skills/council/SKILL.md`](../skills/council/SKILL.md) |
| Convergence loop | [`../skills/convergence_loop/SKILL.md`](../skills/convergence_loop/SKILL.md) |
| Consistency check (8 checks) | [`../skills/consistency_check/SKILL.md`](../skills/consistency_check/SKILL.md) |
| Pre-commit hook script | [`../orchestrators/claude-code/hooks/pre-commit.sh`](../orchestrators/claude-code/hooks/pre-commit.sh) |
| Workflow-Engine source | [`../scripts/workflow_engine.py`](../scripts/workflow_engine.py) |
| Workflow-YAML schema example | [`../workflows/runbooks/solve/workflow.yaml`](../workflows/runbooks/solve/workflow.yaml) |
| Workflow-Reminder hook (UserPromptSubmit) | [`../orchestrators/claude-code/hooks/workflow-reminder.sh`](../orchestrators/claude-code/hooks/workflow-reminder.sh) |
| Boot status-check script | [`../scripts/git-status-check.sh`](../scripts/git-status-check.sh) |
