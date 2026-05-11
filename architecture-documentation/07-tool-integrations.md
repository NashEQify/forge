# 07 — Tool Integrations

How the framework runs under the supported (and potential) agent
harnesses.

## Architecture principle

The framework is **harness-agnostic**. The methodology (`agents/`,
`framework/`) does not know whether it runs under Claude Code or
OpenCode. Adapter layers (`orchestrators/<harness>/`) translate between
harness-specific discovery / hook mechanics / tool vocabulary and the
harness-neutral methodology.

```
        ┌──────────────────────────────────────────┐
        │       agents/, framework/ (SoT)          │
        │       harness-agnostic                   │
        └────────────┬─────────────────────────────┘
                     │
       ┌─────────────┴──────────────┐
       │                            │
       ▼                            ▼
┌──────────────┐            ┌──────────────┐
│ Claude Code  │            │ OpenCode     │
│ Adapter      │            │ Adapter      │
│              │            │              │
│ orchestrators│            │ orchestrators│
│ /claude-code/│            │ /opencode/   │
└──────┬───────┘            └──────┬───────┘
       │                           │
       ▼                           ▼
   Claude Code CLI             OpenCode CLI
```

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

From any repo:
```bash
ln -sf $FRAMEWORK_DIR/orchestrators/claude-code/hooks/pre-commit.sh \
       .git/hooks/pre-commit
```

The 12 checks run on the next `git commit`. Detail: [`02-architecture.md`](02-architecture.md) §Pre-Commit 12 Checks.

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
| Path guard | **missing** — Buddy must delegate mentally |
| BuddyAI context | manual via `--add-dir ~/BuddyAI` |
| Project AGENTS.md | applies in addition, never instead |
| Commands | trigger words without prefix (`wakeup`, `save`, `checkpoint`, `think!`) |
| FACTS check | prompt-side (`AGENTS.md §2`), no background hook |

### Tier 0 under OpenCode

`AGENTS.md` is the Tier 0 anchor for OC. Content analogous to
`CLAUDE.md` plus an additional Invariant 2 (FACTS check per turn).

### Limitations

- No mechanical path guard → user trust that Buddy delegates mentally
- No FACTS hook → per-turn prompt obligation is costly
- No workflow-reminder hook → user must trigger `save` actively

For engineering discipline, Claude Code is currently the more strongly
mechanised adapter. The OpenCode adapter is functional, but discipline is
more prompt-driven.

## Cursor (planned, not implemented)

`README.md` lists Cursor inspiration but no active adapter under
`orchestrators/cursor/`. Extension point:

### Pattern template

Analogous to `orchestrators/claude-code/`:

```
orchestrators/cursor/
├── bin/
│   └── cur            # launcher with Cursor-specific scope routing
├── hooks/             # Cursor hook equivalents (or workflow-engine CLI)
└── .cursorrules       # Cursor-specific Tier 0 file (analogous to CLAUDE.md)
```

### Open questions for the Cursor adapter

1. **Discovery mechanics:** how does Cursor discover personas? If via
   `.cursor/agents/` analogous to Claude Code: adopt the symlink pattern.
2. **Hook equivalent:** does Cursor support PreToolUse hooks? If not:
   alternative mechanic anchor (pre-action confirmation, custom wrapper).
3. **Tier 0 file:** `.cursorrules` as the Cursor standard. Content
   analogous to `CLAUDE.md`, with Cursor-specific constraints in their
   own section.
4. **Tool vocabulary:** Cursor's Composer/Chat have their own tool names.
   The adapter must adapt persona wrappers accordingly or cross-reference
   to neutral tool descriptions.

The implementation plan is not in the repo; it is a pending extension
task.

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

Skills and workflows must run identically under both active adapters
(CC + OC). `consistency_check` Check 3 (Adapter-SoT-Sync) verifies:

```
agents/<name>.md                              <- SoT
.claude/agents/<name>.md                      <- CC wrapper, "load SoT"
orchestrators/opencode/.opencode/agent/<name>.md  <- OC wrapper, "load SoT"
```

When a wrapper points at a different path than the SoT, that is an ERROR.
The pre-commit hook + `consistency_check` skill catch it.

## Next step

How the framework is maintained (engine details, generator care, tests):
[`08-development-and-maintenance.md`](08-development-and-maintenance.md).
