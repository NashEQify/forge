# 07 — Tool Integrations

How the framework runs under the supported (and potential) agent
harnesses.

## Architecture principle

The framework is **harness-agnostic**. The methodology (`agents/`,
`framework/`, `skills/`, `workflows/`) does not know which harness it
runs under. Adapter layers (`orchestrators/<harness>/`) translate
between harness-specific discovery / hook mechanics / tool vocabulary
and the harness-neutral methodology.

```
        ┌──────────────────────────────────────────────────┐
        │   agents/, framework/, skills/, workflows/ (SoT) │
        │   harness-agnostic                               │
        └────────────────────┬─────────────────────────────┘
                             │
       ┌─────────────────────┼──────────────────────┐
       │                     │                      │
       ▼                     ▼                      ▼
┌──────────────┐      ┌──────────────┐       ┌──────────────┐
│ Claude Code  │      │ OpenCode     │       │ Cursor       │
│ Adapter      │      │ Adapter      │       │ Adapter      │
│              │      │              │       │ (IDE, no     │
│ orchestrators│      │ orchestrators│       │  tool-event  │
│ /claude-code/│      │ /opencode/   │       │  API)        │
└──────┬───────┘      └──────┬───────┘       └──────┬───────┘
       │                     │                      │
       ▼                     ▼                      ▼
   Claude Code CLI       OpenCode CLI           Cursor IDE
```

An adapter delivers three things: persona / skill discovery,
tier-0-anchor loading, and — where the harness exposes a tool-event
API — wiring of forge's PreToolUse / PostToolUse hooks. The bash
hooks under `orchestrators/claude-code/hooks/` are the SoT for all
adapters; CC fires them natively, OC fires them via a thin TS
translator plugin, Cursor has no event API so they only fire via the
git pre-commit symlink (drift catches at commit instead of at write).

## Claude Code

### Prerequisites

- Claude Code CLI installed (`claude` on $PATH).
- `~/.claude/` exists or is created on the first `cc` run.

### Adapter files

```
orchestrators/claude-code/
├── bin/
│   ├── cc                   # main launcher (191 LoC)
│   ├── cc.bak-session132    # backup before the Session-132 refactor
│   └── sysadmin             # sysadmin variant
└── hooks/
    ├── pre-commit.sh
    ├── path-whitelist-guard.sh
    ├── frozen-zone-guard.sh
    ├── delegation-prompt-quality.sh
    ├── state-write-block.sh
    ├── workflow-commit-gate.sh
    ├── workflow-reminder.sh
    └── post-commit-dashboard.sh
```

`.claude/` (in the repo root) additionally contains:
- `agents/` — 30+ persona wrapper files (each `<name>.md` is a wrapper)
- `skills/` — skill wrappers for user-level discovery
- `path-whitelist.txt`, `frozen-zones.txt` — SoT for the guards
- `settings.json` — hook registration

### Wrapper pattern

Each persona has two files:
- **SoT:** `agents/<name>.md` (tool-neutral)
- **Wrapper:** `.claude/agents/<name>.md` (Claude-Code-specific frontmatter
  + "load and follow the SoT" instruction)

Example `.claude/agents/buddy.md`:
```markdown
---
name: buddy
description: Primary orchestrator and user-facing agent ...
---

You are Buddy.

This file is the Claude Code wrapper for the tool-neutral Buddy
definition that lives in `agents/buddy/`. Load:
1. agents/buddy/soul.md
2. agents/buddy/operational.md
3. agents/buddy/boot.md

Then follow boot.md's ORIENT/Intent-detection and greet per soul.md.
```

Benefit: persona logic changes → update SoT, wrapper unchanged.

### cc launcher detail

`orchestrators/claude-code/bin/cc <scope>`:

1. **Pre-flight symlinks** — ensures `~/.claude/agents` and
   `~/.claude/skills` point at the framework. Idempotent. WARN on
   diverging target.
2. **Scope routing** — argument 1 determines the CWD:
   - `framework` → `$FRAMEWORK_DIR`
   - `buddyai` → `$BUDDYAI_DIR`
   - `sysadmin` / `infra` → `$PROJECTS_DIR/sysadmin`
   - `<dir>` → dynamic lookup under `$PROJECTS_DIR/<dir>` with `intent.md` filter
   - (no scope) → CWD stays; Buddy does the intent.md lookup
3. **--add-dir composition:**
   - Always: `--add-dir $FRAMEWORK_DIR`
   - When CWD ≠ FRAMEWORK_DIR: also `--add-dir $CWD`
4. **Launch:** `claude --add-dir ... --agent buddy -n <session>` with user args.

Debug mode: `CC_DEBUG=1 cc <scope>` shows the resolved invocation, no
actual call.

### Hook registration

`.claude/settings.json` registers the hooks for Claude Code's
lifecycle events:

| Event | Hook |
|---|---|
| `PreToolUse` (Edit/Write/NotebookEdit/Bash) | `path-whitelist-guard.sh` |
| `PreToolUse` (Edit/Write/NotebookEdit/Bash) | `frozen-zone-guard.sh` |
| `PreToolUse` (Task) | `delegation-prompt-quality.sh` |
| `PreToolUse` (state-file paths) | `state-write-block.sh` |
| `UserPromptSubmit` | `workflow-reminder.sh` (workflow-engine `additionalContext` inject) |

Plus git hooks (not in `settings.json` but via symlink in `.git/hooks/`):

| Trigger | Hook |
|---|---|
| `pre-commit` | `pre-commit.sh`, `workflow-commit-gate.sh` |
| `post-commit` | `post-commit-dashboard.sh` |

### Install the pre-commit hook

From any repo (idempotent, worktree-safe, self-probing):
```bash
bash $FRAMEWORK_DIR/scripts/install-git-hooks.sh
```

Wires `.git/hooks/{pre-commit,commit-msg}` to
`orchestrators/claude-code/hooks/pre-commit.sh`. The 13 checks run on
the next `git commit`. Detail:
[`02-architecture.md`](02-architecture.md) §Pre-Commit 12 Checks.

### Discovery + tool use

Claude Code discovers sub-agents via:
1. Walk-up from CWD (looks for `.claude/agents/`)
2. User-level (`~/.claude/agents/`)

`cc` sets the user-level via symlink so framework personas are available
in any working directory. Skills the same (`~/.claude/skills/`).

`--add-dir <path>` grants read access to the path — no sub-agent
discovery. That is the separation: `--add-dir` for files, symlink for
personas.

## OpenCode

### Prerequisites

- OpenCode CLI installed (`opencode` on $PATH).
- `OPENCODE_CONFIG_DIR` and `OPENCODE_CONFIG` exported.

### Adapter files

```
orchestrators/opencode/
├── bin/
│   └── oc                   # 5-line wrapper
├── opencode.jsonc           # OC config
└── .opencode/agent/<name>.md  # OC-specific wrapper
```

### oc launcher

`orchestrators/opencode/bin/oc` is an auto-detect wrapper:
```bash
# Detect FRAMEWORK_DIR via dirname (env-overridable).
FRAMEWORK_DIR="$(cd "$(dirname "$(readlink -f "$0")")/../../.." && pwd)"
export OPENCODE_CONFIG_DIR="$FRAMEWORK_DIR/orchestrators/opencode/.opencode"
export OPENCODE_CONFIG="$FRAMEWORK_DIR/orchestrators/opencode/opencode.jsonc"
exec opencode "$@"
```

`opencode.jsonc` itself is a **template** (`opencode.jsonc.example`) with
`${FRAMEWORK_DIR}` and `${HOME}` placeholders. `scripts/setup-oc.sh`
generates the user-specific `opencode.jsonc` (gitignored).

### OC constraints

`AGENTS.md §OC Constraints`:

| Aspect | OC behaviour |
|---|---|
| Path guard | **present** via `forge-hooks.ts` plugin (`tool.execute.before` → `path-whitelist-guard.sh`) |
| Hook parity | PreToolUse + PostToolUse via plugin (Edit/Write/Bash/Task); pre-commit identical (git-side) |
| BuddyAI context | manual via `--add-dir ~/BuddyAI` |
| Project AGENTS.md | applies in addition, never instead |
| Commands | trigger words without prefix (`wakeup`, `save`, `checkpoint`, `think!`) |
| FACTS check | prompt-side (`AGENTS.md §2`), no background hook |

### Tier 0 under OpenCode

`AGENTS.md` is the Tier 0 anchor for OC. Content analogous to
`CLAUDE.md` plus an additional Invariant 2 (FACTS check per turn).

### Limitations

- No `workflow-reminder` hook — OC has no UserPromptSubmit event.
  Workflow state lives on disk in `.workflow-state/<id>.json`, so the
  gap is mostly cosmetic (the per-turn nudge is missing, the state is
  still readable on demand). PLUGIN.md §"UserPromptSubmit gap" lists
  three workaround options if the gap becomes load-bearing.
- No FACTS background hook — per-turn FACTS check is prompt-level
  (`AGENTS.md §2`), no Stop+SessionEnd equivalent wired.

CC and OC now share the same mechanical-prevention layer for tool
events. The bash hooks under `orchestrators/claude-code/hooks/` are the
SoT for both; the OC plugin
(`orchestrators/opencode/.opencode/plugins/forge-hooks.ts`) is a thin
adapter that translates `tool.execute.{before,after}` into CC-shaped
JSON. CC retains the UserPromptSubmit + Stop/SessionEnd hook surfaces
(workflow-reminder, FACTS check) which have no OC equivalent — those
remain CC-only.

## Cursor

Cursor is an IDE (not a CLI agent like CC / OC), so the adapter has a
different shape: no launcher script, but **project rules** that align
Cursor's agent mode with the framework behaviour. Full readme:
`orchestrators/cursor/README.md`.

### Adapter files

```
orchestrators/cursor/
├── README.md               # adapter doc + setup
└── rules/                  # auto-loaded into Cursor composer/chat
    ├── 00-tier-0.md
    ├── 01-buddy-orchestrator.md
    ├── 02-personas.md
    ├── 03-skills.md
    └── 04-workflows.md
```

Tier-0 anchor reuses the `AGENTS.md` convention (same as OC). Personas
are invoked via `@<name>` mentions; the Cursor agent reads
`agents/<name>.md` and follows it.

### Limitations vs. CC / OC

| Aspect | CC | OC | Cursor |
|---|---|---|---|
| Sub-agent discovery | `~/.claude/agents/` | `.opencode/agent/` | project rules + `@`-mention |
| PreToolUse hooks | native | translator plugin | **none** |
| Pre-commit hook | git symlink | git symlink | git symlink |
| Workflow-engine trigger | mechanical | mechanical | manual (terminal) |

**Consequence:** the mechanical write-time discipline (path-whitelist,
frozen-zone, delegation-prompt-quality, …) does not fire under Cursor.
The pre-commit hook remains mechanical (git triggers it independent of
the agent), so drift catches at commit instead of at write. Skills,
workflows, runbooks, the workflow engine, personas, task / plan YAMLs
all run identically.

### Status

**Minimal-viable adapter.** Sufficient to apply forge methodology
under Cursor. Full mechanical parity with CC requires a Cursor
PreToolUse-equivalent (open, depends on Cursor) and a sub-agent
spawn API (open, depends on Cursor's composer roadmap).

## Adding a new adapter

General approach:

1. **Create the layout:** `orchestrators/<harness>/` with sub-dirs `bin/`,
   `hooks/` (or equivalent), wrapper files.
2. **Write Tier 0:** `<HARNESS>.md` (analogous to CLAUDE.md/AGENTS.md)
   with invariants 1-N. Check which of the CC invariants apply there too
   and which are harness-specific.
3. **Create wrapper files:** for each persona under
   `<harness>/<discovery-path>/<name>.md` a wrapper that loads the SoT file
   under `agents/<name>.md`.
4. **Hook equivalent:** if the harness supports hooks — bash scripts
   analogous to `orchestrators/claude-code/hooks/`. If not — alternative
   mechanic (workflow engine as CLI, manual confirmation, etc.).
5. **Launcher:** bash script analogous to `cc` with scope routing +
   harness-specific discovery-path setup + Tier 0 anchor loading.
6. **Pre-commit:** if the adapter needs its own pre-commit logic (e.g.
   harness-specific validation), extend the hook accordingly or write a
   dedicated one.
7. **Update AGENTS.md / CLAUDE.md:** if a new invariant is harness-spanning.
8. **Methodology unchanged:** `agents/`, `framework/` stay **unchanged** —
   that is the point of the adapter layer.

## Cross-adapter consistency

Skills and workflows must run identically under all shipped adapters.
For CC + OC `consistency_check` Check 3 (Adapter-SoT-Sync) verifies the
persona-wrapper chain:

```
agents/<name>.md                              <- SoT
.claude/agents/<name>.md                      <- CC wrapper, "load SoT"
orchestrators/opencode/.opencode/agent/<name>.md  <- OC wrapper, "load SoT"
```

Cursor has no per-persona wrapper file (personas resolve via
`@`-mention into `agents/<name>.md` directly), so Check 3 does not
apply there.

When a wrapper points at a different path than the SoT, that is an ERROR.
The pre-commit hook + `consistency_check` skill catch it.

## Next step

How the framework is maintained (engine details, generator care, tests):
[`08-development-and-maintenance.md`](08-development-and-maintenance.md).
