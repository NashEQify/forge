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

An adapter provides persona / skill discovery, tier-0 instruction loading,
and host-specific boot integration. Shared Git hooks provide six commit-time
checks when installed in the active repository. The two SessionStart scripts
run on configured Claude entrypoints. Codex uses explicit managed AGENTS boot
instructions, OpenCode uses its launcher, and Cursor uses project rules.
There are no framework tool-event hooks (PreToolUse / PostToolUse /
UserPromptSubmit); write-time discipline is protocol-anchored.

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
    ├── pre-commit.sh        # git pre-commit + commit-msg, 6 checks
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
| `pre-commit` + `commit-msg` | `pre-commit.sh` (6 checks) |

### Install the pre-commit hook

From any repo (idempotent, worktree-safe, self-probing):
```bash
bash $FRAMEWORK_DIR/scripts/install-git-hooks.sh
```

Wires `.git/hooks/{pre-commit,commit-msg}` to
`orchestrators/claude-code/hooks/pre-commit.sh`. The 6 checks run on
the next `git commit`. Detail:
[`02-architecture.md`](02-architecture.md) §Pre-Commit 6 Checks.

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
| Pre-commit hook | Identical — git-side, runs the same 6 checks |
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

Forge's Codex installer generates roles from the neutral `agents/*.md`
sources and installs explicit AGENTS instructions for primary-session boot.
It does not use Claude SessionStart scripts as Codex boot hooks. Giving a
session directory access or selecting a Buddy role alone does not prove
that the framework instructions were loaded.

### Prerequisites

- Codex Desktop or Codex CLI installed (`codex --version`).
- Python 3.10+ with PyYAML available to `python3`.
- A framework checkout and an existing consumer project directory.
  The installer can create `AGENTS.md` or merge its managed boot block
  into existing project instructions.

### Adapter files

| Surface | Purpose |
|---|---|
| `agents/*.md` | Canonical neutral role definitions |
| `scripts/generate_codex_agents.py` | Generates all 40 active roles as TOML |
| `scripts/setup-codex.sh` | Managed installation of roles, skills and boot entries |
| `~/.codex/agents/*.toml` | Installed roles with concrete framework paths |
| `~/.agents/skills/*/SKILL.md` | Generated discovery wrappers with concrete skill paths |
| `~/.codex/AGENTS.md`, `<consumer>/AGENTS.md` | Managed boot block plus preserved user/project instructions |

Portable role templates use `<FRAMEWORK_ROOT>` with instructions to resolve
it from the framework checkout or the managed AGENTS entry in a consumer
session. Installed roles use the concrete framework path. Both forms come
from neutral sources; edit those sources and regenerate. Project paths
remain relative to the active consumer CWD.

### setup-codex.sh

```bash
bash "$FRAMEWORK_DIR/scripts/setup-codex.sh" --check "$HOME/projects/my-app"
bash "$FRAMEWORK_DIR/scripts/setup-codex.sh" "$HOME/projects/my-app"
```

Operations:

1. Resolve the framework root from the script's location and generate roles
   and skill wrappers with concrete targets.
2. Preflight all managed targets. Hash manifests identify owned files;
   unknown or edited files and symlinks are conflicts. `--check` never writes:
   exit 0 means current, exit 1 means pending changes or a conflict (read
   the output).
3. Install owned role/skill files and merge the boot block into the Codex
   home AGENTS file and each supplied consumer's AGENTS file, preserving
   surrounding instructions.
4. Remove only recognized obsolete Forge Claude-hook command entries from
   existing Codex `hooks.json` files. Preserve unrelated commands and group
   metadata. `config.toml`, credentials and Git hooks are untouched.

`CODEX_HOME` and `AGENTS_HOME` (or `--codex-home` and `--agents-home`) select
alternative destinations. `--migrate-legacy` adopts only byte-identical known
legacy roles and wrappers. Review and preserve custom changes before resolving
a conflict; there is no force-overwrite option. Each file replacement is atomic,
but installation across directories is not a single filesystem transaction.

### Boot and Git hooks

The managed AGENTS entry tells the primary session to read Buddy's `soul.md`,
`operational.md` and `boot.md`, even without explicit Buddy role selection.
The consumer CWD and its project rules remain active; delegated roles follow
their canonical role without repeating primary-session boot/bookkeeping.

Install shared Git hooks separately with `scripts/install-git-hooks.sh`, then
run its `--check` mode. Verify the actual AGENTS loading in a fresh consumer
session. No framework tool-event hooks enforce write-time discipline.

### Discovery + tool use

The default installation places roles in `~/.codex/agents/` and skill wrappers
in `~/.agents/skills/`. The explicit boot entry identifies the framework root;
consumer `AGENTS.md` supplies project rules. Verify the installed roles and
skills are available in the host session instead of inferring discovery from
file presence alone.

Of the 40 generated roles, 34 report roles default to `sandbox_mode = "read-only"`
and `approval_policy = "never"`. They return complete reports inline, including
intended artifact paths, evidence and provenance. The parent persists them
verbatim before downstream Chief consumption. Shell and temporary-file writes
are outside the report-only contract.

The six writer roles (`buddy`, `main-code-agent`, `tester`, `test-skeleton-writer`,
`spec-text-drift-batch`, `security`) inherit their runtime settings. Parent
runtime overrides can supersede role defaults; verify effective permissions
before claiming sandbox enforcement. A report role retains report-only behavior
and reports any mismatch.

### Limitations

- Generated role/skill edits become ownership conflicts on a later install.
  Change canonical sources and rerun setup; preserve custom files separately.
- A passing installation check verifies managed files, not live instruction
  loading, role discovery or effective sandbox rights. Check those in the
  actual parent session.

For the complete setup sequence, see [Installation: Codex](05-installation.md#codex).

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
| Boot integration | Configured Claude SessionStart / launcher | launcher | explicit managed AGENTS entry | project rules |
| Pre-commit hook | git symlink | git symlink | git symlink | git symlink |
| Workflow-engine | available, on-demand | available, on-demand | available, on-demand | available, on-demand |

**Consequence:** the discipline is shared across adapters. Boot differs:
configured Claude SessionStart / launcher, OpenCode launcher, Codex managed
AGENTS, Cursor project rules. Shared Git checks run when installed in the
active repo; effective runtime permissions and discovery must be verified
on the host.

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
scripts/generate_codex_agents.py             <- Codex TOML generated from neutral SoT
```

Codex roles are generated from all 40 active neutral `agents/*.md` sources.
Portable templates resolve `<FRAMEWORK_ROOT>` explicitly; `setup-codex.sh`
generates installed roles and skill wrappers with concrete framework paths.
Use its `--check` mode to detect managed-install drift. The normal generation
source is the neutral role, not a curated TOML copy.

Cursor has no per-persona wrapper file (personas resolve via
`@`-mention into `agents/<name>.md` directly), so Check 3 does not
apply there.

When a wrapper points at a different path than the SoT, that is an ERROR.
The pre-commit hook + `consistency_check` skill catch it.

## Next step

How the framework is maintained (engine details, generator care, tests):
[`08-development-and-maintenance.md`](08-development-and-maintenance.md).
