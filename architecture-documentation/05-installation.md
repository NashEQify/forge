# 05 — Installation

## Prerequisites

| Tool | Use |
|---|---|
| **git** | repo cloning + pre-commit hook |
| **bash** | hooks + launcher (`cc`, `oc`) |
| **jq** | hook logic (Stop/SessionEnd JSON-payload parsing) |
| **Python 3.10+** | engines (`plan_engine.py`, `workflow_engine.py`) + generators |
| **PyYAML** | plan/task/workflow YAML parsing |
| **Claude Code CLI** | when using the CC adapter |
| **OpenCode CLI** | when using the OC adapter |
| `chub` CLI | optional, for the `get_api_docs` skill |
| `gitleaks` | optional, for the SECRET-SCAN pre-commit check (`brew install gitleaks` or via [GitHub releases](https://github.com/gitleaks/gitleaks/releases)) |

## Quickstart

```bash
# 1. Clone the repo
git clone https://github.com/NashEQify/forge ~/projects/forge

# 2. Set FRAMEWORK_DIR (overridable, default $HOME/projects/forge)
export FRAMEWORK_DIR=$HOME/projects/forge

# 3. Python venv (PEP-668 bypass if needed)
cd $FRAMEWORK_DIR
python3 -m venv .venv
.venv/bin/pip install pyyaml

# 4. Setup script for Claude Code (symlinks + whitelist)
bash scripts/setup-cc.sh

# 5. Test launch
$FRAMEWORK_DIR/orchestrators/claude-code/bin/cc framework
```

If everything is running, `cc framework` opens a Claude Code session with Buddy
as the initial agent, the framework repo as the working directory, and `--add-dir
$FRAMEWORK_DIR` (which is identical here).

## Tool-Specific Setup Guides

### Claude Code

#### 1. Workspace symlinks (`scripts/setup-cc.sh` does this automatically)

`cc` expects two user-level symlinks:

```bash
ln -s $FRAMEWORK_DIR/.claude/agents ~/.claude/agents
ln -s $FRAMEWORK_DIR/.claude/skills ~/.claude/skills
```

**Why:** Claude Code discovers sub-agents via walk-up from the CWD or via
`~/.claude/agents/`. We use the user-level location so that framework
agents are available in every working directory, regardless of the consumer repo.

`cc` creates these symlinks idempotently on first run when missing
(`orchestrators/claude-code/bin/cc:38-89`). On a divergent target there is
a warning, no auto-fix.

#### 2. Pre-commit hook (per repo)

From every consumer repo:

```bash
ln -sf $FRAMEWORK_DIR/orchestrators/claude-code/hooks/pre-commit.sh \
       .git/hooks/pre-commit
```

On the next `git commit` the 12 pre-commit checks run (see
[`02-architecture.md`](02-architecture.md) §Pre-Commit 12 Checks).

#### 3. Hook registration (`.claude/settings.json`)

`.claude/settings.json` registers the hooks for Claude Code's PreToolUse,
Stop, SessionEnd triggers. Already included in the framework repo. Consumer repos
inherit this via `--add-dir`.

#### 4. cc launcher

`orchestrators/claude-code/bin/cc <scope>`:

| Scope | Effect |
|---|---|
| `framework` / `forge` | `cd $FRAMEWORK_DIR` |
| `buddyai` / `BuddyAI` | `cd $BUDDYAI_DIR` |
| `sysadmin` / `infra` | `cd $PROJECTS_DIR/sysadmin` |
| `life` | Legacy: `cd $BUDDYAI_DIR/workspaces` |
| `<dir>` (dynamic) | searches under `$PROJECTS_DIR/<dir>` for `intent.md` |
| (no scope) | stays in the current CWD (Buddy does the intent.md lookup) |

`cc` automatically sets:
- `--add-dir $FRAMEWORK_DIR` (always)
- `--add-dir $CWD` (when CWD ≠ FRAMEWORK_DIR)
- `--agent buddy` (boot agent)
- `-n <session_name>` (terminal title)

**Debug mode:** `CC_DEBUG=1 cc <scope>` shows the resolved invocation without
calling Claude.

#### 5. First session start

```bash
cc framework  # or: cc buddyai
```

Buddy boots:
1. ORIENT — `date / hostname / pwd`
2. RESOLVE — `ls $CWD/intent.md` (upward search)
3. ROUTE — context path
4. LOAD — `values.md` + `profile.md` + `boot-navigation.md` + intent-load
5. RESUME — `session-buffer.md` + `session-handoff.md` + optionally `plan_engine --boot`
6. GREET

If `intent.md` is missing: Buddy offers to create it. Format:
`framework/intent-tree.md` §intent.md format.

### OpenCode

#### 1. Configuration

```bash
export OPENCODE_CONFIG_DIR=$FRAMEWORK_DIR/orchestrators/opencode/.opencode
export OPENCODE_CONFIG=$FRAMEWORK_DIR/orchestrators/opencode/opencode.jsonc
```

#### 2. Launcher

`orchestrators/opencode/bin/oc` is a minimal wrapper:

```bash
$FRAMEWORK_DIR/orchestrators/opencode/bin/oc
```

#### 3. OC constraints (`AGENTS.md §OC Constraints`)

- The consumer repo is the CWD; the framework is mounted via the
  OpenCode launcher (`$FRAMEWORK_DIR/orchestrators/opencode/bin/oc`).
- A consumer's project-level `AGENTS.md` (in the consumer repo root)
  applies in addition to the framework AGENTS.md, never instead — both
  are loaded.
- Commands: trigger words without prefix (`wakeup`, `save`, `checkpoint`, `think!`).
- **Path guard missing under OC** — Buddy must delegate mentally rather than be mechanically blocked

### Cursor (planned)

Not implemented. Extension point for future adapters:

1. Write `orchestrators/cursor/bin/cur` analogous to `cc`
2. Hooks equivalent or workflow-engine CLI
3. Wrapper files `.claude` equivalent for Cursor's workspace discovery
4. Tier-0 anchor file Cursor-specific (analogous to `CLAUDE.md` / `AGENTS.md`)

Pattern template: the `claude-code/` adapter layout. The methodology stays under
`framework/` and `agents/`; the adapter does the harness-specific routing.

## Consumer-Repo Setup

A consumer repo (e.g. your own project) needs:

1. **`intent.md`** at the repo root — format `framework/intent-tree.md` §intent.md format:
   ```markdown
   # Intent — <name>
   ## Vision
   <1-3 sentences>
   ## Done
   <What does "done" mean?>
   ## Non-Goals
   <What explicitly not>
   ## Context
   <mode signal + boot/on-demand/not-relevant split>
   ```

2. **Optional `context/` directory** with `history/` and `overview.md`. Buddy
   auto-creates this when missing.

3. **Optional `docs/backlog.md` + `docs/tasks/`** when the repo has its own tasks.

4. **Pre-commit hook symlink** when the repo should operate under Buddy's
   engineering discipline:
   ```bash
   ln -sf $FRAMEWORK_DIR/orchestrators/claude-code/hooks/pre-commit.sh \
          .git/hooks/pre-commit
   ```

Buddy finds these files automatically via the `ls` boot sequence (`agents/buddy/boot.md`).

## Adjusting the Path Whitelist

`.claude/path-whitelist.txt` is currently single-user (`/home/xxx/projects/...`).
For public OSS adoption this needs to be generalised per user. Candidates:
- env-var substitution (`$HOME/projects/**`)
- per-machine `~/.claude/path-whitelist-local.txt` as supplement
- run `setup-cc.sh` with a user-specific patch

Today this is still hand-maintained — see [`12-troubleshooting.md`](12-troubleshooting.md).

## Verification

After setup, check the following:

```bash
# 1. Symlinks correct?
ls -la ~/.claude/agents      # → $FRAMEWORK_DIR/.claude/agents
ls -la ~/.claude/skills      # → $FRAMEWORK_DIR/.claude/skills

# 2. cc debug
CC_DEBUG=1 cc framework
# → shows FRAMEWORK_DIR, BUDDYAI_DIR, CWD, session_name, add-dir args, would exec

# 3. plan_engine
python3 $FRAMEWORK_DIR/scripts/plan_engine.py --validate
# → Summary: 0 errors

# 4. skill validator
python3 $FRAMEWORK_DIR/scripts/skill_fm_validate.py
# → no BLOCK output

# 5. generators idempotent?
python3 $FRAMEWORK_DIR/scripts/generate_skill_map.py
python3 $FRAMEWORK_DIR/scripts/generate_navigation.py
# → "all up to date" or no git diff

# 6. Pre-commit hook installed?
ls -la $FRAMEWORK_DIR/.git/hooks/pre-commit
# → symlink to orchestrators/claude-code/hooks/pre-commit.sh
```

If 1-6 are all clean, the setup is correct.

## Next Step

How to actually use the framework: [`06-usage-workflows.md`](06-usage-workflows.md).
