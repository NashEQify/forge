<!-- Maintenance: informational only; not used in process.
     Update when repo structure or working model changes. -->

# BuddyAI — Getting Started

## What BuddyAI is

**Memory Infrastructure for AI.** BuddyAI builds a knowledge graph from
any data source and assembles a context-rich, intent-aware prompt for
each LLM call. First instance: personal operating system. Target market:
enterprise AI.

Details: `intent.md` (vision), `docs/architecture/` (architecture docs).

## Repo structure

```
BuddyAI/
  intent.md                 <- vision + non-goals + agent check
  CLAUDE.md                 <- invariants (Tier 0, loaded every turn)
  decisions.md              <- ADRs

  docs/
    plan.yaml               <- milestones, gates, requires DAG, target
    tasks/                  <- task YAMLs + MDs (SoT for all work)
    specs/                  <- design documents (board-reviewed)
    architecture/           <- public architecture docs (consumer deploy target)

  scripts/
    plan_engine.py          <- computed planning layer (--boot, --next, --check, etc.)
    generate-control.py     <- operations center generator
    deploy-docs.sh          <- MkDocs + dashboard -> consumer-configured remote

  agents/                   <- agent definitions (tool-neutral)
    buddy/                  <- Buddy (soul, operational, boot, context-rules)
    main-code-agent.md      <- development agent
    tester.md, reviewer.md  <- quality agents

  context/                  <- domain knowledge (curated, max 200 lines/MD)
    user/                   <- user profile, values
    system/                 <- system knowledge
    history/                <- session summaries (frozen zone)
    session-log.md          <- decisions from recent sessions

  framework/                <- generic methodology, skills, workflows
    milestone-execution.md  <- multi-task milestone orchestration
    task-format.md          <- task YAML/MD schema
    spec-engineering.md     <- spec methodology
    workflows/runbooks/build/WORKFLOW.md  <- per-task flow: Direct/Standard/Full

  src/                      <- Python code (brain, events, gateway, worker)
```

## First steps

### 1. Understand current state

```bash
python3 scripts/plan_engine.py --boot
```

Shows: active target, critical path, in-progress tasks, next actions,
milestone status, warnings.

### 2. Find the next task

```bash
python3 scripts/plan_engine.py --next --limit 20
```

Sorted by: critical path -> target path -> blocking score -> effort.
Tasks on the target path rank higher than others.

### 3. Work on a task

```bash
# Read task YAML
cat docs/tasks/242.yaml

# Read task MD (context, workflow, scope)
cat docs/tasks/242.md

# Read related spec (if spec_ref is set)
cat docs/specs/archive/gateway-buddy-worker-impl.md
```

### 4. Create a task

Create a new task: `docs/tasks/NNN.yaml` + `NNN.md`.
Required fields: `id`, `title`, `status`, `milestone`, `blocked_by`,
`created`, `updated`.
`milestone` MUST be a key from `docs/plan.yaml`.
Afterwards: `python3 scripts/plan_engine.py --validate` (0 errors).

Details: `framework/task-format.md`.

### 5. Development process

| Path | When | Steps |
|------|------|----------|
| **Direct** | <=3 files, no spec, no new behavior | Buddy -> MCA directly |
| **Standard** | 1 subsystem | interview -> spec -> board -> test -> implement |
| **Full** | >1 subsystem, schema change | spec in 3 levels, board after each |

Details: `workflows/runbooks/build/WORKFLOW.md` (per-task flow),
`framework/milestone-execution.md` (milestone level).

## Planning system

**SoT:** task YAMLs (`docs/tasks/*.yaml`) + `docs/plan.yaml`.
**Engine:** `scripts/plan_engine.py` computes everything — milestone status,
critical path, next actions.
**Dashboard:** generated via `scripts/generate-dashboard.py`, deployed via
`scripts/deploy-dashboard-lite.sh` to a consumer-configured remote
(env: `DASHBOARD_HOST` + `DASHBOARD_TARGET`).

No manual backlog. No session handoff. Task state IS the plan.

Details: `docs/architecture/project/planning.md`.

## Roadmap

Milestone DAG, not linear phases. S2/S3/S4 run in parallel. All feature
milestones (intelligence, life-os, scale, middleware) technically require
only S1. Strategic prioritization runs through `target` in plan.yaml.

```
S1 -> mvp -> memory-platform (fundraising) -> production
```

Details: `docs/architecture/project/roadmap.md`.

## Buddy (the agent)

Buddy is the primary contact and orchestrator.
Buddy knows the user, projects, and infrastructure.
Buddy delegates code work to main-code-agent and reviews to board agents.

```bash
cd ~/BuddyAI && cc          # start Buddy (BuddyAI development)
cd ~/projects/foo && cc     # start Buddy (different project)
```

Boot sequence: `agents/buddy/boot.md`.
Personality: `agents/buddy/soul.md`.
Working style: `agents/buddy/operational.md`.

## Key invariants (CLAUDE.md)

1. **Board/Council:** Buddy = dispatcher, no spec analysis
2. **Discuss before implementing:** default is discussion
3. **Pre-delegation:** no agent call without a delegation artifact
4. **Code delegation:** Buddy does not code directly (except orchestrator work).
   Artifact-type refinement: `framework/agent-autonomy.md`
5. **Stale cleanup:** removed artifacts must be reference-free in the same commit
6. **Deployment verification:** verify visually, not only via HTTP status

**FACTS check:** in the Claude Code adapter this is mechanical via the
Stop+SessionEnd hook (user-global in `~/.claude/settings.json`). In the
OpenCode adapter it is prompt-level (`AGENTS.md` §2) until an equivalent
hook mechanism exists.
