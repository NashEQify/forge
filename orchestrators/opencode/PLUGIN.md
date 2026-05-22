# OpenCode plugin: forge-hooks

OpenCode-side translator for the forge hook-discipline layer. Wires
OpenCode's `tool.execute.before` / `tool.execute.after` events to the
existing CC bash hooks under `orchestrators/claude-code/hooks/`. The bash
hooks are the SoT; this plugin is a thin adapter so they stay unchanged.

File: `.opencode/plugins/forge-hooks.ts`. OpenCode auto-loads it at
startup (Bun runtime transpiles TS — no build step).

## Setup

One command does everything (idempotent, safe to re-run):

```
bash $FRAMEWORK_DIR/scripts/setup-oc.sh
```

It does three things:

1. Generates `orchestrators/opencode/opencode.jsonc` from the
   `.example` template, substituting `${FRAMEWORK_DIR}` and `${HOME}`.
2. Installs `~/.local/bin/oc` with install-time `FRAMEWORK_DIR`
   substitution. This is what makes the `oc` alias work — without it
   you'd have to invoke the launcher by full path
   (`$FRAMEWORK_DIR/orchestrators/opencode/bin/oc`).
3. Verifies the plugin file exists and that `opencode` is on PATH.

**The `oc` alias requires this script.** OpenCode itself reads
`opencode.jsonc` from `OPENCODE_CONFIG`, which the launcher exports —
running plain `opencode` from CWD will use OC's default config, not
forge's. Always launch via `oc` (or set up your own alias / wrapper
that exports the same env vars; see `orchestrators/opencode/bin/oc`).

Prerequisites:

- `opencode` CLI installed (https://opencode.ai).
- `~/.local/bin/` in `PATH`. Add this to `~/.bashrc` / `~/.zshrc` if
  missing:
  ```
  export PATH="$HOME/.local/bin:$PATH"
  ```

After setup, run `oc` from any directory to launch OpenCode with the
forge config + hooks active.

## Hook coverage

| Layer        | Tool  | Hooks fired                                                                                          |
| ------------ | ----- | ---------------------------------------------------------------------------------------------------- |
| PreToolUse   | Edit  | path-whitelist-guard, frozen-zone-guard, state-write-block, engine-bypass-block, plan-adversary-reminder |
| PreToolUse   | Write | (same as Edit)                                                                                       |
| PreToolUse   | Bash  | path-whitelist-guard, workflow-commit-gate                                                           |
| PreToolUse   | Task  | delegation-prompt-quality                                                                            |
| PostToolUse  | Task  | mca-return-stop-condition, board-output-check, evidence-pointer-check                                |

NotebookEdit: OpenCode does not expose a notebook-edit tool; the
matcher is intentionally absent.

## BLOCK behaviour

PreToolUse blocks via either:

1. `exit 2` with the deny reason on stderr (standalone bash convention).
2. `exit 0` with a `hookSpecificOutput.permissionDecision: "deny"` JSON
   envelope on stdout (CC's recommended PreToolUse output format).

The plugin honours both and converts a BLOCK into a thrown `Error` —
which OpenCode renders as a tool-call failure with the message visible
to the user, equivalent to CC's denial UI.

## UserPromptSubmit gap

OpenCode has no direct equivalent of CC's UserPromptSubmit hook, which
is where `workflow-reminder.sh` injects the active workflow + next step
into every turn's context. Three workarounds, ordered by quality:

1. **Accept the gap** (current state). The `workflow-reminder.sh` output
   is helpful but not load-bearing — workflow state lives on disk in
   `.workflow-state/<id>.json` and Buddy reads it on demand.
2. **Instruction-file injection.** Have an `oc` launcher pre-pass that
   runs `workflow_engine.py --next --brief` and appends the result to
   `AGENTS.md` (gitignored portion). Refreshes on every `oc` invocation
   but not mid-session.
3. **Hook on `session.updated`** (overfires, noisy). Each user turn
   triggers multiple `session.updated` events; deduping them turn-wise
   is non-trivial. Not recommended.

We ship with (1). If the gap becomes load-bearing, escalate to (2).

## Project-root resolution

The bash hooks resolve their state files (whitelist, frozen zones,
workflow engine) relative to `CLAUDE_PROJECT_DIR`. The plugin sources
this in priority order:

1. `process.env.CLAUDE_PROJECT_DIR` — explicit override.
2. `ctx.worktree` — OpenCode's git-worktree path.
3. `ctx.directory` — OpenCode's cwd.
4. `process.cwd()` — final fallback.

The `bin/oc` launcher exports `CLAUDE_PROJECT_DIR=$FRAMEWORK_DIR` so the
hooks find the right whitelist / frozen-zones files even when OpenCode
is launched from a consumer project under `~/projects/<name>/`.

## Smoke test

`tests/smoke-shim.sh` exercises the CC-shaped JSON-on-stdin contract
that the plugin depends on — runs each bash hook with sample payloads,
asserts the expected exit code / deny envelope. Run it after touching
any hook in `orchestrators/claude-code/hooks/`:

```
bash orchestrators/opencode/tests/smoke-shim.sh
```

The TS plugin itself can only be exercised under a real OpenCode
session — there's no headless harness for the plugin event loop.
