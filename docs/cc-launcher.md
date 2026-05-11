# `cc` Launcher — Setup & Reference

Detail companion to README §Get `cc` running.

## Prerequisites

| Tool | Why |
|---|---|
| **Claude Code** | the harness forge runs on. [Install guide](https://docs.anthropic.com/en/docs/claude-code) |
| **git** | repo + pre-commit hook |
| **bash + jq** | hook scripts + payload parsing |
| **Python 3.10+ + PyYAML** | `workflow_engine.py`, `plan_engine.py`, generators |

## What `setup-cc.sh` does

Load-bearing — without it, `cc` doesn't exist on your `$PATH` and
Claude Code can't find the framework personas. Four steps, all
idempotent:

1. **Installs the `cc` launcher to `~/.local/bin/cc`**, with the
   absolute install-time path to forge substituted into the script. The
   launcher needs to know where forge lives without an env var; the
   substitution bakes that in once.
2. **Creates two user-level symlinks** — `~/.claude/agents` and
   `~/.claude/skills` — pointing into forge. Claude Code discovers
   personas and skills via these paths, so framework agents are
   available from every working directory regardless of which repo
   you're in.
3. **Generates `.claude/path-whitelist.txt`** from `.example`,
   substituting `${FRAMEWORK_DIR}` and `${HOME}`. The PreToolUse
   `path-whitelist-guard` hook reads this file and blocks writes
   outside the declared paths — first line of mechanical defense
   against drift.
4. **Warns** if `~/.local/bin` isn't on your `$PATH`. Fix with
   `export PATH="$HOME/.local/bin:$PATH"` in your shell rc.

## How `cc` resolves scope

| Invocation | Effect |
|---|---|
| `cc forge` (or `cc framework`) | always works — `cd $FRAMEWORK_DIR`, mount forge |
| `cc` (no scope, in any directory) | use current CWD, require `intent.md` (Buddy offers to create if missing) |
| `cc <project>` | look up `$PROJECTS_DIR/<project>/` (default `~/projects/`), require `intent.md` |

`cc` mounts both forge and your CWD via `--add-dir`, so every session
sees the framework rules (CLAUDE.md, agents, skills) on top of the
local repo content.

Project directories can live anywhere on disk — `cc` from inside the
directory always works regardless of path. `cc <name>` only short-cuts
to `$PROJECTS_DIR/<name>/`; everything outside that dir is reached via
`cd /path/to/repo && cc`.

**Debug:** `CC_DEBUG=1 cc forge` prints the resolved invocation
without launching Claude — useful for verifying scope routing or
`--add-dir` paths.

## `intent.md` — per-directory anchor

Every directory that uses forge needs an `intent.md` at its root —
forge's per-project anchor (vision, done-criteria, non-goals, context).
The first time you run `cc` in a directory without one, Buddy notices
the missing anchor and offers to create it through a short interview
(usually 5-10 minutes). That interview is forge's stable per-directory
onboarding: intent comes from a conversation about what the project
IS, not from a template.

After `intent.md` exists, `cc` in that directory boots Buddy directly
— picks up active workflows, session-handoff, project backlog. Format
documented in [`framework/intent-tree.md`](../framework/intent-tree.md);
you can also write it by hand if you prefer.

`cc forge` keeps working from anywhere. The framework has its own
`intent.md`; you never need to onboard forge itself.

## Common gotchas

- `cc: command not found` → `~/.local/bin` not in `$PATH`. Add to shell
  rc: `export PATH="$HOME/.local/bin:$PATH"`
- `intent.md not found` → expected on first `cc` in a new directory;
  Buddy will offer to create one. Or hand-write per
  [`framework/intent-tree.md`](../framework/intent-tree.md).
- `framework_dir resolution failed` → set explicitly:
  `export FRAMEWORK_DIR=$HOME/projects/forge`
- agents-Symlink warnings → re-run `bash scripts/setup-cc.sh`
  (idempotent)
- pre-commit blocks → see
  [`architecture-documentation/12-troubleshooting.md`](../architecture-documentation/12-troubleshooting.md)

## Full installation reference

For multi-machine, OpenCode adapter, per-repo pre-commit hook, and
other adapter-level setup:
[`architecture-documentation/05-installation.md`](../architecture-documentation/05-installation.md).
