# `cc` Launcher — Setup & Reference

Detail companion to the [installation guide](../architecture-documentation/05-installation.md) for the `cc` launcher (optional convenience).

## Prerequisites

| Tool | Why |
|---|---|
| **Claude Code** | the harness forge runs on. [Install guide](https://docs.anthropic.com/en/docs/claude-code) |
| **git** | repo + pre-commit hook |
| **bash + jq** | hook scripts + payload parsing |
| **Python 3.10+ + PyYAML** | `workflow_engine.py`, `plan_engine.py`, generators |

## What `setup-cc.sh` does

`setup-cc.sh` forwards to the coordinated installer. Follow
[`framework/installation-activation.md`](../framework/installation-activation.md)
for source changes, installation ownership and fresh-session verification.

Full setup plans the `cc` launcher at `~/.local/bin/cc`, Claude role/skill
links and configured SessionStart integration from the settings template.
The boot injector applies to configured desktop/web entrypoints; the remote
script observes coordinated maintenance readiness and does not resume workflows
or update/install the framework. The terminal launcher supplies its own boot
injection. Existing unowned integration conflicts must be resolved through the
installer, not overwritten manually.

Full Claude setup also wires `pre-commit`, `pre-merge-commit` and `commit-msg` in the selected
framework repository. The current six check families and availability limits
are recorded in [`framework/enforcement-registry.md`](../framework/enforcement-registry.md).
Installation/file checks establish managed integration, not proof of actual
instruction loading in every host session. Ensure `~/.local/bin` is on `$PATH`.

For consumer repos (not the framework checkout itself), wire the
same hooks once per repo:

```bash
bash $FRAMEWORK_DIR/scripts/install-git-hooks.sh
```

Modes: `--check` (probe only, no writes), `--uninstall` (remove
symlinks). Worktree-safe. Full reference:
[`architecture-documentation/05-installation.md`](../architecture-documentation/05-installation.md)
§Pre-commit hook.

## How `cc` resolves scope

| Invocation | Effect |
|---|---|
| `cc forge` (or `cc framework`) | always works — `cd $FRAMEWORK_DIR`, mount forge |
| `cc` (no scope, in any directory) | use current CWD, require `intent.md` (Buddy offers to create if missing) |
| `cc <project>` | look up `$PROJECTS_DIR/<project>/` (default `~/projects/`), require `intent.md` |

`cc` makes the framework and consumer directories available via `--add-dir`
when needed. This grants access; the launcher's explicit injection identifies
the boot entry. Verify actual instruction loading in the launched session and
retain the consumer's local rules; directory access alone does not prove loading.

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
