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
   ┌─────────────────┬───────┴────────┬──────────────────┐
   │                 │                │                  │
   ▼                 ▼                ▼                  ▼
┌──────────┐  ┌──────────────┐  ┌──────────┐      ┌──────────┐
│ Claude   │  │ OpenCode     │  │ Codex    │      │ Cursor   │
│ Code     │  │ Adapter      │  │ Adapter  │      │ Adapter  │
│ Adapter  │  │              │  │          │      │ (IDE, no │
│          │  │ orchestrators│  │ .codex/ +│      │  tool-   │
│ orches   │  │ /opencode/   │  │ ~/.codex/│      │  event   │
│ /claude- │  │              │  │ ~/.agents│      │  API)    │
│ code/    │  │              │  │          │      │          │
└────┬─────┘  └──────┬───────┘  └────┬─────┘      └────┬─────┘
     │               │                │                 │
     ▼               ▼                ▼                 ▼
 Claude Code     OpenCode         Codex Desktop      Cursor IDE
  CLI             CLI              / CLI
```

An adapter delivers three things: persona / skill discovery,
tier-0-anchor loading, and — for the SessionStart + git pre-commit
hooks — universal wiring. **Only universal-portable hooks are wired:**
SessionStart (boot inject + resume nudge) and git pre-commit (5
checks). There are no tool-event hooks (PreToolUse / PostToolUse /
UserPromptSubmit); write-time discipline is protocol-anchored. All
supported harnesses (CC-Terminal, claude-desktop, claude-web, OpenCode,
Codex, Cursor) run discipline + protocols + the same 3 hooks (Cursor
lacks SessionStart, so it boots via project rules; pre-commit fires
identically).

## Claude Code

### Prerequisites

- Claude Code CLI installed (`claude` on $PATH).
- `~/.claude/` exists or is created on the first `cc` run.

### Adapter files

```
orchestrators/claude-code/
├── bin/
│   ├── cc                   # main launcher (191 LoC)
│   └── sysadmin             # sysadmin variant
└── hooks/                  # 3 scripts only
    ├── pre-commit.sh        # git pre-commit + commit-msg, 5 checks
    ├── buddy-boot-inject.sh # SessionStart — Buddy boot trigger
    └── session-start-remote.sh # SessionStart — resume nudge
```

`.claude/` (in the repo root) additionally contains:
- `agents/` — 40 persona wrapper files (each `<name>.md` is a wrapper)
- `skills/` — skill wrappers for user-level discovery
- `frozen-zones.txt` — legacy SoT (convention-only; no hook)
- `settings.json` — SessionStart hook registration

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
   - `framework` / `forge` → `$FRAMEWORK_DIR` (built-in)
   - `<name>` → case-insensitive lookup under `$PROJECTS_DIR/<name>/` with `intent.md` filter
   - (no scope) → CWD stays; Buddy does the intent.md lookup
3. **--add-dir composition:**
   - Always: `--add-dir $FRAMEWORK_DIR`
   - When CWD ≠ FRAMEWORK_DIR: also `--add-dir $CWD`
4. **Launch:** `claude --add-dir ... --agent buddy -n <session>` with user args.

Debug mode: `CC_DEBUG=1 cc <scope>` shows the resolved invocation, no
actual call.

### Hook registration

`~/.claude/settings.json` (user-global) registers the hooks for Claude
Code's lifecycle events. Forge owns the top-level `hooks` slot;
`setup-cc.sh` merges them in from
`orchestrators/claude-code/settings.json.template` (substituting
`__FRAMEWORK_DIR__` with the detected forge checkout) without touching
user-owned keys like `effortLevel` or `permissions`. Hooks fire in
every CC session regardless of CWD or entrypoint:

| Event | Hook |
|---|---|
| `SessionStart` | `session-start-remote.sh` + `buddy-boot-inject.sh` |

Plus git hooks (not in `settings.json` but via symlink in `.git/hooks/`):

| Trigger | Hook |
|---|---|
| `pre-commit` + `commit-msg` | `pre-commit.sh` (5 checks) |

### Install the pre-commit hook

From any repo (idempotent, worktree-safe, self-probing):
```bash
bash $FRAMEWORK_DIR/scripts/install-git-hooks.sh
```

Wires `.git/hooks/{pre-commit,commit-msg}` to
`orchestrators/claude-code/hooks/pre-commit.sh`. The 5 checks run on
the next `git commit`. Detail:
[`02-architecture.md`](02-architecture.md) §Pre-Commit 5 Checks.

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

| Aspect | OC behaviour |
|---|---|
| PreToolUse hooks | **None.** No tool-event hook layer on either harness — the CC-Terminal PreToolUse/PostToolUse layer was dropped framework-wide |
| Pre-commit hook | Identical — git-side, runs the same 5 checks |
| Consumer context | manual via `--add-dir <consumer-repo>` |
| Project AGENTS.md | applies in addition, never instead |
| Commands | trigger words without prefix (`wakeup`, `save`, `checkpoint`, `think!`) |

### Tier 0 under OpenCode

`AGENTS.md` is the Tier 0 anchor for OC. Content analogous to
`CLAUDE.md`.

### Parity with CC

CC and OC now run identically — both have only the pre-commit hook
universally wired (OC lacks SessionStart, so the boot mechanism is
prompt-side via `oc` launcher rather than hook-injected). Discipline +
protocols carry everything on the discipline layer. OC has no
tool-event surface (no UserPromptSubmit); the framework does not rely
on one.

## Codex

Codex Desktop / CLI reads agent definitions from `~/.codex/agents/`
(global, user-level) and project-local hooks from `<project>/.codex/
hooks.json`. Skills are discovered globally from `~/.agents/skills/`.
There is no `--add-dir`-style runtime path resolution; Codex expects
agent files to carry concrete absolute paths.

### Prerequisites

- Codex Desktop or Codex CLI installed (`codex --version`).
- The active repository carries an `AGENTS.md` (project Tier-0
  surface; identical convention to OpenCode).

### Adapter files

```
.codex/
├── agents/              # 38 agent wrappers (TOML, generated/curated)
│   ├── buddy.toml       # template stub — overwritten at install time
│   ├── main-code-agent.toml
│   ├── board-chief.toml
│   ├── code-chief.toml
│   └── … (one per persona)
└── hooks.json           # project-local hook wiring (uses
                         # ${CLAUDE_PROJECT_DIR} as the in-repo form;
                         # overwritten with concrete paths on install)
```

The committed `.codex/agents/buddy.toml` is a TEMPLATE with a
`${FRAMEWORK_DIR}` placeholder. `scripts/setup-codex.sh` writes the
installed copy at `~/.codex/agents/buddy.toml` with the placeholder
substituted to the user's absolute path. This indirection exists
because Codex Desktop has no runtime environment-variable resolution
for agent file paths; concrete paths must be baked in at install
time. The 37 other wrappers carry no absolute paths and are copied
unchanged.

### setup-codex.sh

```bash
bash $FRAMEWORK_DIR/scripts/setup-codex.sh [project-dir ...]
```

Operations:

1. **Detect `FRAMEWORK_DIR`** from the script's own location (same
   pattern as `setup-cc.sh`, portable across clones).
2. **Install agent wrappers** at `~/.codex/agents/` from
   `.codex/agents/*.toml`.
3. **Overwrite `~/.codex/agents/buddy.toml`** with a Codex-specific
   wrapper carrying the concrete `FRAMEWORK_DIR`.
4. **Write `~/.codex/AGENTS.md`** — a global fallback that points at
   the active repo's `AGENTS.md` as the project Tier-0.
5. **Generate skill wrappers** at `~/.agents/skills/` via
   `scripts/generate_skill_wrappers.py --output-root ~/.agents/skills
   --tool-label Codex`. Same generator as the Claude Code wrappers,
   different output root.
6. **For each `project-dir` argument:** write `<project-dir>/.codex/
   hooks.json` with SessionStart entries pointing at the same scripts
   CC uses (`buddy-boot-inject.sh` + `session-start-remote.sh`). The
   per-project hooks.json carries SessionStart-only; the
   git pre-commit symlink is wired separately via
   `scripts/install-git-hooks.sh`.

### Hook registration

`.codex/hooks.json` registers SessionStart only:

| Event | Hooks |
|---|---|
| `SessionStart` | `buddy-boot-inject.sh` + `session-start-remote.sh` |

There are no PreToolUse / PostToolUse / UserPromptSubmit hooks.
Discipline + protocols + git pre-commit (5 checks, universally
available) carry the write-time layer.

### Discovery + tool use

Codex discovers:
- **Agents:** globally from `~/.codex/agents/`. No project-local
  `.codex/agents/` lookup (unlike Claude Code's walk-up).
- **Skills:** globally from `~/.agents/skills/`. Wrappers are
  generated derived artefacts.
- **Tier-0:** from the active project's `AGENTS.md` (same convention
  as OpenCode). If the project has no `AGENTS.md`, the global
  `~/.codex/AGENTS.md` fallback points at it as the missing Tier-0.

### Limitations

- **No project-local agent override.** Codex has no walk-up agent
  discovery; consumer repos cannot ship per-project agent variants.
  Workaround: edit the global `~/.codex/agents/` directly, or use a
  per-repo `AGENTS.md` that re-routes via prompt.
- **Skill wrappers are install-time, not repo-tracked.** Unlike
  `.claude/skills/` (committed, exposed via symlink), the Codex skill
  wrappers under `~/.agents/skills/` regenerate on every
  `setup-codex.sh` run. When a skill's frontmatter changes, re-run
  `setup-codex.sh` (or the generator directly) to refresh the
  wrappers.

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

### Limitations vs. CC / OC / Codex

| Aspect | CC | OC | Codex | Cursor |
|---|---|---|---|---|
| Sub-agent discovery | `~/.claude/agents/` | `.opencode/agent/` | `~/.codex/agents/` | project rules + `@`-mention |
| Skill discovery | `~/.claude/skills/` (symlink) | `.opencode/skill/` | `~/.agents/skills/` (generated) | project rules |
| SessionStart hook | native | n/a (boot via launcher) | native (`.codex/hooks.json`) | n/a (boot via project rules) |
| Pre-commit hook | git symlink | git symlink | git symlink | git symlink |
| Workflow-engine | available, on-demand | available, on-demand | available, on-demand | available, on-demand |

**Consequence:** the framework runs identically on every
adapter. Boot mechanism varies (SessionStart on CC/Codex, launcher on
OC, project rules on Cursor); pre-commit is identical (git symlink);
discipline + protocols + skills + workflows + personas are 1:1.

### Status

Cursor adapter is feature-complete — the framework runs no tool-event
hooks, so Cursor has parity with CC on the substantive layer. Personas
resolve via `@`-mention into `agents/<name>.md` directly.

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
.codex/agents/<name>.toml                     <- Codex wrapper, "load SoT"
```

Codex wrappers (`.codex/agents/<name>.toml`) live in the repo as a
checked-in adapter surface; `setup-codex.sh` copies them to
`~/.codex/agents/`. The Buddy wrapper is a template stub with a
`${FRAMEWORK_DIR}` placeholder — substituted at install time. The
other 37 wrappers are generated-then-curated (no install-time
substitution needed).

Cursor has no per-persona wrapper file (personas resolve via
`@`-mention into `agents/<name>.md` directly), so Check 3 does not
apply there.

When a wrapper points at a different path than the SoT, that is an ERROR.
The pre-commit hook + `consistency_check` skill catch it.

## Next step

How the framework is maintained (engine details, generator care, tests):
[`08-development-and-maintenance.md`](08-development-and-maintenance.md).
