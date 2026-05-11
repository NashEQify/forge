# System — Context Mechanics & Loading Order

Detail extracted from overview.md. Referenced by consistency_check,
context-management.md. overview.md carries the short version; this file
holds the deeper model.

## Context system — mechanics

**Pattern per area:** `context/<area>/navigation.md` (index) +
`overview.md` (curated top level) + detail files.

**Active areas:** user/, life/, selfhosting/, machine-setup/, system/
(this area), history/.

**Context maintenance:** the knowledge-processor skill implements
brain-logic as agent behavior for project/system context. Triggers:
task status changes (all repos), save, entropy audit at boot.
User context (`~/projects/personal/context/user/`) is written only on
explicit user request — no automatic extraction. Store facts without
clarification when instructed by the user; verify interpretations
before storing.

**Intake gate (pre-harness enforcement, Buddy):** 4-point MUST checklist
immediately on new information — BEFORE acting (FACTS, ACTIONABLE,
INCIDENT, INTERPRETATION). Definition: `agents/buddy/operational.md`.

**Session continuity (ARCH-008):** `plan_engine --boot` (project state),
`context/session-handoff.md` (discussion context from the previous
session), `context/session-log.md` (history index). Project sessions:
`<CWD>/docs/current-hook.md` (step pointer, optional).

**Context routing:** boot.md sets the active context path (4 cases).
All skills/triggers operate on that path.

**Context management (dynamic):** based on the **Context Availability
Model** — three states: available (in workspace), loaded (in context
window), active (referenced in reasoning). Transitions are tier-dependent.
**Context Manifest** declares which context must be available per task.
**Context Switch Protocol** defines the 4-step transition
(FLUSH -> UNLOAD -> LOAD -> ORIENT). **Active Context Register**
persists as `workspace/.context-register.md`. **Proactive sculpting**
releases on-demand context. Details: `docs/specs/context-management.md`.

## Loading order (compaction safety)

**Tier 0 — system-injected (highest priority, ALWAYS visible):**
`CLAUDE.md` / `AGENTS.md` — invariants + adapter constraints.
Injected by CC/OC runtime.

**Tier 1 — boot-loaded (compaction-safe):**
`agents/buddy/soul.md`, `operational.md`, `boot.md`,
`~/projects/personal/context/user/values.md` — process rules,
character, commands.

**Tier 2 — boot-read (compaction-prone):**
`context/plan_engine --boot` (curated distillate),
`docs/session-buffer.md`.

**Tier 3 — on-demand (only when needed):**
`context-rules.md`, task files, detail context, skills, specs,
design principles, ADRs.

Consequence: invariants belong in tier 0. Process rules belong in
tier 1. If a rule is forgotten after compaction, it was in the wrong
tier.

## Adapter pattern

SoT under `agents/` is tool-neutral. Adapters are thin:
- **Claude Code**: `.claude/agents/<n>/<n>.md` — frontmatter
  (name, tools, model) + "Load and follow"
- **OpenCode**: `orchestrators/opencode/.opencode/agent/<n>.md` —
  frontmatter + "Load and follow"
- Model field is mandatory. Switch via model-switch skill.
