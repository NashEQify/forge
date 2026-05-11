# Agents

Tool-neutral agent definitions (source of truth).
Adapters under `orchestrators/` and `.claude/agents/` reference
these files.

## Agent landscape

| Agent | Role | SoT | Model | Intent |
|-------|------|-----|-------|--------|
| **Buddy** | Personal assistant, orchestrator, planner | `agents/buddy/` (soul, operational, boot, context-rules) | Opus | Yes |
| **buddy-thinking** | Buddy with maximum thinking depth (deep thinking for spec interviews, strategic questions) | `agents/buddy-thinking.md` | Opus | Yes |
| **Solution Expert** | Architecture sparring, Architecture Board (6 personas) | `agents/solution-expert.md` | Opus | Yes |
| **main-code-agent** | Full development agent — direct recipient of Buddy delegations (plan → implement → review → test). Workflow detail in `skills/return_summary/SKILL.md`. Execute steps inlined into the build runbook. | `agents/main-code-agent.md` | Opus | Yes |
| **Security** | Offensive security agent — recon, exploitation, credential audit, forensics | `agents/security.md` | Sonnet | Yes |


### Sub-agents (orchestrated by Buddy in parallel)

| Agent | Role | SoT | Model | Intent |
|-------|------|-----|-------|--------|
| **board-chief** | Spec Board: consistency, completeness, final arbiter | `agents/board-chief.md` | Opus | No |
| **board-adversary** | Spec Board: smart-but-wrong, E2E, boundary tracing, edge cases. **Double instance in deep pass 1**: once Opus (prefix F-A-), once Sonnet (prefix F-A3-) for a cheaper third E2E perspective. | `agents/board-adversary.md` | Opus / Sonnet | No |
| **board-adversary-2** | Spec Board: like adversary + first-principles analysis | `agents/board-adversary-2.md` | Opus / Sonnet | No |
| **board-implementer** | Spec Board: buildability, API check, integration | `agents/board-implementer.md` | Sonnet | No |
| **board-impact** | Spec Board: blast radius, interface breaks, dependency chains | `agents/board-impact.md` | Opus | No |
| **board-consumer** | Spec Board: readability, clarity, self-containment | `agents/board-consumer.md` | Sonnet | No |
| **council-member** | Architecture Council: single-perspective analysis | `agents/council-member.md` | Sonnet | No |

### Sub-agents (delegated by main-code-agent)

| Agent | Role | SoT | Model | Intent |
|-------|------|-----|-------|--------|
| **test-skeleton-writer** | TDD red phase: test skeletons without impl code in context | `agents/test-skeleton-writer.md` | Sonnet | No |
| **tester** | Spec-driven test engineer: derive tests from spec, write, run, PASS / FAIL | `agents/tester.md` | Sonnet | No |

**Intent levels:** *Yes* = actively runs the agent check,
verifies the derivation chain, can say STOP when intent isn't
intact. *Reads* = receives `intent_chain` as context for
orientation but doesn't run an own agent check. *No* = works
against specs / criteria; intent is irrelevant for the task.

## Delegation pattern

```
User
  +-- Buddy (planned work: spec → board → delegate → track)
  |     +-- Spec Board (parallel: board-chief, board-adversary [Opus + Sonnet double instance in deep pass 1, prefix F-A- / F-A3-], board-adversary-2, board-implementer, board-impact, board-consumer)
  |     +-- Architecture Council (parallel: N x council-member)
  |     +-- Solution Expert (architecture / framework decisions)
  |     +-- main-code-agent
  |     |     +-- test-skeleton-writer (TDD red phase)
  |     |     +-- tester (test design + execution)
  |     |     +-- code-review / code-adversary / code-spec-fit / code-* (Code Review Board, dispatched by Buddy after the MCA return)
  |     +-- security (security assessments, pentests, forensics)
  +-- Agent direct (direct conversation; the agent writes into the shared memory)
```

Development process: `framework/process-map.md` + workflow
runbooks under `workflows/runbooks/`.
Board detail: `workflows/templates/spec-board.yaml`.
Council detail: `workflows/templates/council.yaml`.

## Adapters

Every SoT file here is tool-neutral (no frontmatter).
Adapters are thin and reference here:

- **Claude Code:** `.claude/agents/<name>/<name>.md`.
- **OpenCode:** `orchestrators/opencode/.opencode/agent/<name>.md`.
