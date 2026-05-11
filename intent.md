# Intent — forge

## Vision

**forge** bundles **opinionated workflows + codified discipline
patterns** into a **Skill + Discipline Layer** between human and LLM,
so **vibe-at-complexity and sustained quality become possible**.

In small projects an unsteered LLM gets you far. In complex projects
it crashes — not because capability is missing, but because *unsteered
capability cannot design complex systems*. forge ships the steering:
workflows that encode best-practice processes (build, solve, fix,
review, …) and a discipline layer that mechanically prevents drift.

**Primary audience:** single-dev on complex projects.
**Secondary audience:** small teams adopting forge as a shared
discipline layer.

**Self-claim:** *trust must be earned, not claimed.* forge grew wildly
into what it is today. The framework itself must reach the bar it
offers consumers — that's both roadmap and ongoing self-imposition.

## Positioning

- **opinionated workflows** — build, solve, fix, review, research,
  save, docs-rewrite, context_housekeeping. *Not* "best practice"
  (no industry consensus exists yet in agentic engineering).
  Opinionated in the Rails sense: deliberate defaults, take or leave.
- **codified discipline patterns** — Hooks, Gates, Frozen-Zones,
  Path-Whitelist, Pre-Commit checks, persistent State Engine.
  Mechanical enforcement, not rules-as-text.

Together: a *skill + discipline layer* that lifts the LLM-design-
ceiling on complex systems.

## Pillars (as of May 2026)

- **Skills as Fertigkeiten** — the framework's unit of value. Skills
  encode processes (how to build, how to solve, how to fix, how to
  spec, …) that an unsteered LLM wouldn't reliably apply. Have today:
  build, solve, fix, design, spec, review, research, save,
  docs-rewrite, context_housekeeping (37 active skills total). **Roadmap
  gaps:** tool-use, multi-agent / teamwork — explicit, not implicit.
- **Codified discipline patterns** — mechanical enforcement instead of
  rule text. Hooks fire on tool-call, gates fire on workflow step,
  pre-commit fires on commit. *"Hooks catch schema drift, reviews
  catch content drift. Both required."* The LLM cannot rationalize
  away a shell hook.
- **Tier-0/1/2 model** — Tier 0 (invariants in `CLAUDE.md`/`AGENTS.md`)
  is never overridden; Tier 1 (operational files in `agents/buddy/` +
  `framework/`) is process; Tier 2 (`context-rules.md`, skill
  `REFERENCE.md`) is detail. CLAUDE.md wins on conflict (project
  sovereignty).
- **Standards where they exist; mechanical prevention is CC-coupled** —
  the framework uses portable standards wherever they exist: SKILL.md +
  frontmatter (parsed identically by Claude Code and Codex), git
  pre-commit for commit-time checks, `workflow_engine.py` CLI + JSON
  state for cross-session continuity, post-commit hooks for derived
  views. Per-harness setup (`--add-dir`, `OPENCODE_CONFIG_DIR`, Codex
  plugin install, symlink conventions, env vars) lives in
  `orchestrators/<runtime>/` — those are setup mechanisms, not
  portability concerns. **What's genuinely not portable: mechanical
  prevention.** The discipline layer (path-whitelist, frozen-zones,
  state-write-block, engine-bypass-block) requires `PreToolUse`-class
  hooks that fire *before* a tool-call writes a file. Claude Code
  provides this; pre-commit-only would catch violations *after* the
  LLM already polluted its context, which defeats prevention and
  forces rollback. No cross-runtime standard for `PreToolUse` exists
  today. **Consequence:** on Claude Code, the framework runs at full
  mechanical prevention. On other harnesses it runs at methodology +
  state + post-hoc validation; the early-signal layer degrades by
  what the host harness offers. This is a deliberate trade-off, not a
  planned-fix gap.
- **Workflow engine** — persistent, cross-session-recoverable state
  in `.workflow-state/<id>.json` for non-trivial workflows. Externally
  readable, externally drivable. Roadmap: wrappable as MCP server so
  any MCP-aware harness can drive the discipline mechanism, not just
  Claude Code.
- **Pre-Delegation non-negotiable** — routing via
  `framework/process-map.md` + workflow runbooks. No sub-agent call
  without a delegation artifact (plan block or gate file). The brief
  is the contract.
- **Generator + validator** — drift-prone indexes (skill-map,
  navigation) are generated (disk = SoT) and checked for idempotence
  by validator hooks (`consistency_check` checks 6 + 8). Schema drift
  catches itself.

## Consumers

| Repo | Role | Status |
|---|---|---|
| `BuddyAI` | Memory Infrastructure for AI (primary product) | primary |
| `personal` | user context + 5-month plan tasks | primary |
| `Huddle` | Discord alternative | light consumer |
| `infra` (`sysadmin`) | Linux admin, self-hosting, Hetzner | planned |
| Small-team external adopters | shared discipline layer | possible, no first reference yet |

**Adapter layers:**

| Harness | Mechanism | Status |
|---|---|---|
| Claude Code | `--add-dir $FRAMEWORK_DIR` (bin + hooks) | active, fully mechanized |
| OpenCode | `OPENCODE_CONFIG_DIR` (bin + opencode.jsonc) | active, hook-translator pending (Task 298) |
| Cursor | rules + persona wrapper | minimum viable, no hook parity |
| Codex | plugin export (skills + engine-as-MCP-server) | planned, post-1.0 (Task 313) |

## Non-Goals

- **No generic AI-agent-framework clone** (no LangChain, no Autogen,
  no marketplace export of arbitrary skills). External skill libraries
  are picked up selectively, not adopted wholesale.
- **No replacement for Claude Code / OpenCode / Codex** — adapter-
  based, not re-implemented.
- **No monolith** — consumers decide for themselves what they need.
  Tier-0/1/2 ships with the framework; consumer bookkeeping (tasks,
  specs, builds) lives in the consumer repo.
- **No class hierarchy between skills** — single-class is enforced.
  Skills vary on `invocation.primary`, not on type.
- **No new skill without a Spec-Board L1 PASS** on the standalone
  argument (inflation guard, `framework/skill-anatomy.md`
  §Inflation guard).
- **No "best practice" claim** — opinionated, not authoritative.
  Agentic engineering has no industry consensus to lean on; forge
  ships its own opinions and says so.
- **No multi-tenant / SaaS** — single-dev tool, optionally adopted
  by small teams. Not a platform.
- **No marketplace push pre-1.0** — Codex plugin export (Task 313)
  is a roadmap item, not a 1.0 blocker. Discipline-tightening +
  skill-inventory expansion take priority.

## Context

- **Program SoT:** `docs/plan.yaml` (north_star, operational_intent,
  phases, milestones). Tasks under `docs/tasks/<id>.{md,yaml}`.
- **Public OSS docs** for GitHub readers: `architecture-documentation/`.
- **Skill inventory state:** see `framework/boot-navigation.md`
  (active skills + workflows index) and `framework/skill-map.md`
  (taxonomy + maturity registry). Roadmap gaps explicitly tracked:
  tool-use, multi-agent / teamwork.

## Agent Check

See `CLAUDE.md` invariants + observability. Detail:
`framework/intent-tree.md`.
