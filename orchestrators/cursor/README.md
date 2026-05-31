# Cursor Adapter

Cursor integration for forge. Cursor is an IDE (not a
CLI agent like Claude Code / OpenCode), so this adapter has a different
shape from `orchestrators/claude-code/` or `orchestrators/opencode/`:
no launcher scripts, but **project rules** that align Cursor's agent mode
with the framework behaviour.

## What this adapter delivers

1. **Tier-0 anchor via the `AGENTS.md` convention.** Cursor supports
   `AGENTS.md` as the standard repo doc for agent behaviour — that is the
   same convention OpenCode uses. `AGENTS.md` from the framework
   repo therefore applies under Cursor as well.

2. **Project rules** under `rules/`. Cursor automatically loads
   `.cursor/rules/*.md` into the composer/chat context. Here we ship the rules
   that steer Cursor's agent towards Buddy behaviour: boot-sequence hint,
   tier model, pre-delegation, persona discovery.

3. **Persona wrappers** under `agents/`. Analogous to `.claude/agents/`
   wrappers — short Cursor-specific frontmatter, the actual content
   stays under `agents/<name>.md` (orchestrator-neutral).

## Limitations vs. Claude Code / OpenCode

| Aspect | Claude Code | OpenCode | Cursor |
|---|---|---|---|
| Sub-agent discovery | `~/.claude/agents/` | `.opencode/agent/` | project rules + manual via @-mention |
| Pre-commit hook | git symlink | git symlink | git symlink |
| FACTS background hook | yes | no | no |
| Workflow-engine trigger | mechanical | mechanical | manual |

**Consequence:** Cursor's mechanical layer is the git pre-commit hook
(git triggers it independently of the agent tool) plus the project
rules + persona wrapper. There is no write-time hook on any harness;
the user + agent hold path/scope discipline mentally.

## Setup

1. Symlink `.cursor/rules/` in the consumer repo to the framework:
   ```bash
   ln -s "$FRAMEWORK_DIR/orchestrators/cursor/rules" .cursor/rules
   ```

2. Install the pre-commit hook (same mechanism as CC/OC):
   ```bash
   bash "$FRAMEWORK_DIR/scripts/install-git-hooks.sh"
   ```

3. Open the Cursor agent — the rules under `.cursor/rules/` get loaded
   automatically. `AGENTS.md` from the repo root is also honoured (Cursor convention).

## Persona invocation

Cursor's agent mode (as of late 2025) has no sub-agent-discovery mechanism
analogous to Claude Code's `@<agent>`. Personas are invoked via a mention
pattern:

```
@buddy review the plan below...
@code-review look through the diff...
```

The Cursor agent then reads the referenced persona definition from
`agents/<name>.md` and follows it.

## Known open points

- **Sub-agent spawn:** Cursor's agent mode currently has no analogous
  `Task` tool like Claude Code. Multi-persona boards therefore run under
  Cursor sequentially via @-mention instead of in parallel. Workaround: Buddy
  manually collects the outputs of the individual persona invocations.

- **Workflow engine:** workflow-engine invocations (`workflow_engine.py
  --next` etc.) run via Cursor's terminal integration manually —
  no auto-trigger.

## Status

**Minimal-viable adapter.** Sufficient to apply forge methodology under
Cursor. The parity gap vs CC is now just parallel sub-agent spawn
(open, depends on Cursor's composer roadmap) — the hook layer (git
pre-commit + boot) is portable, and there's no write-time hook to match.
