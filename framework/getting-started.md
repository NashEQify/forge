<!-- Maintenance: informational only; not used in process.
     Update when repo structure or working model changes. -->

# forge — Getting Started

## What forge is

A **skill + discipline layer** between human and LLM that bundles
opinionated workflows and codified discipline patterns so that
vibe-at-complexity and sustained quality become possible.

In small projects an unsteered LLM gets you far. In complex projects
it crashes — not because capability is missing, but because *unsteered
capability cannot design complex systems*. forge ships the steering:
workflows that encode best-practice processes (build, solve, fix,
review, …) and a discipline layer that mechanically prevents drift.

Details: `intent.md` (vision + non-goals), `architecture-documentation/`
(OSS-facing surface).

## Topology

forge runs as an **adapter** that consumers plug into their own
project repos. Two repos in the topology:

- **`forge_dev`** — private dev SoT. All framework development,
  tasks, specs, and operational context live here.
- **`forge`** — public OSS mirror, produced solely by
  `scripts/release-sync.sh` from forge_dev. Consumers depend on this
  one. Hand-edited only for one-time release hygiene.

A consumer project (any code repo, personal project, infra repo,
external adopter, …) keeps its own intent/specs/tasks under its own
repo. The framework is referenced via path injection — see
`architecture-documentation/05-installation.md` for the per-harness
mechanisms (Claude Code `--add-dir`, OpenCode `OPENCODE_CONFIG_DIR`,
Codex global wrappers).

```
forge_dev/                       <- this repo (private dev SoT)
  intent.md                      <- vision + non-goals
  CLAUDE.md                      <- invariants (Tier 0, loaded every turn)

  docs/
    plan.yaml                    <- framework milestones, gates, DAG
    tasks/                       <- task YAMLs + MDs
    specs/                       <- spec corpus (board-reviewed)

  agents/                        <- agent definitions (tool-neutral)
    buddy/                       <- Buddy (soul, operational, boot, context-rules)
    main-code-agent.md
    code-*.md                    <- Code Review Board personas
    ...

  skills/                        <- capability + utility skills
    build/, solve/, fix/, review/
    spec_authoring/, spec_board/, code_review_board/
    ...

  workflows/                     <- runbooks per workflow
    runbooks/build/WORKFLOW.md
    runbooks/solve/WORKFLOW.md
    ...

  framework/                     <- meta-methodology, navigation
    boot-navigation.md
    spec-engineering.md
    process-map.md
    ...

  orchestrators/                 <- per-harness adapter
    claude-code/, opencode/, codex/, cursor/

  scripts/                       <- engines + tooling
    plan_engine.py, workflow_engine.py
    release-sync.sh              <- forge_dev -> forge mirror
```

## First steps

### 1. Install the Claude Code adapter (most common)

```bash
bash $FRAMEWORK_DIR/scripts/setup-cc.sh
```

This generates the per-user `.claude/path-whitelist.txt` from the
shipped example and wires the hook stack (PreToolUse +
PostToolUse + UserPromptSubmit + pre-commit). Other harnesses:
see `architecture-documentation/07-tool-integrations.md`.

### 2. Open a forge-aware session

```bash
cc                  # start Buddy in the current directory
cc <project-scope>  # start Buddy in a named scope (e.g. cc framework)
```

The `cc` launcher resolves the scope, sets `FRAMEWORK_DIR`, and
injects the framework via `--add-dir`. Buddy boots: reads soul,
operational, boot files; runs intent resolution against the active
CWD; loads the active context.

### 3. Understand current state (root sessions)

```bash
python3 $FRAMEWORK_DIR/scripts/plan_engine.py --boot
```

Shows: active target, critical path, in-progress tasks, next actions,
milestone status, warnings. Same call runs automatically in Buddy's
boot sequence for root sessions.

### 4. Pick a workflow

| Workflow | When |
|---|---|
| `build` | Implement a feature/task. Direct/Standard/Full paths. |
| `solve` | Problem with open solution shape. Frame, refine, validate. |
| `fix` | Bug/incident. Root-cause first, no symptom patching. |
| `review` | Spec(s) without code. |
| `research` | SOTA / spike. Output = knowledge, not code. |
| `save` | End-of-session persistence. |
| `docs-rewrite` | Rewrite docs, reader-journey-first. |

Routing rules: `framework/process-map.md`. Runbooks:
`workflows/runbooks/<name>/WORKFLOW.md`.

### 5. Build path (per-task flow)

| Path | When | Steps |
|------|------|----------|
| **Direct** | <=3 files, no spec, no new behavior | Buddy -> MCA directly |
| **Standard** | 1 subsystem | interview -> spec -> board -> test -> implement |
| **Full** | >1 subsystem, schema change | spec in 3 levels, board after each |

Details: `workflows/runbooks/build/WORKFLOW.md`.

## Buddy (the agent)

Buddy is the primary contact and orchestrator. Buddy knows the user,
the project, and the workflow surface. Buddy delegates code work to
main-code-agent and reviews to board agents.

```bash
cd ~/projects/<consumer> && cc   # start Buddy in a consumer project
cd $FRAMEWORK_DIR && cc           # start Buddy in forge itself
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
7. **OSS-readable repo:** public-surface files carry content + reasoning, not session forensics
8. **Public forge = read-only OSS mirror:** the consumer-facing repo
   is produced solely by `scripts/release-sync.sh`, never hand-edited
9. **Proportionality of effort:** decisions creating followup work need a value-floor justification

## Per-harness mechanics

Mechanical prevention (PreToolUse hooks) is Claude-Code-coupled and
gives the discipline layer its early-signal property. Other harnesses
degrade gracefully: OpenCode runs the discipline at full hook parity
via the TS plugin; Cursor uses rules + pre-commit; Codex uses global
wrappers + per-project `.codex/hooks.json`. Detail:
`architecture-documentation/07-tool-integrations.md`.
