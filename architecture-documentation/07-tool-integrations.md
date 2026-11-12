# 07 — Tool Integrations

Forge supplies portable methods plus host-specific discovery and boot integration.
A host determines actual tool access, permissions, subagent behavior and instruction
loading. Shared methodology does not establish identical host behavior.

## Architecture principle

Canonical instructions live in `agents/`, `framework/`, `skills/` and `workflows/`.
Host wrappers point to those sources with the appropriate paths and metadata.
The consumer workspace remains the active CWD and retains its own rules.

| Host | Main entry mechanism | Integration boundary |
|---|---|---|
| Codex | The plugin's `forge:boot` skill, asked for by the `AGENTS.md` activation line | Boot and `save` checked from the public marketplace; fresh-session loading, discovery and effective permissions still need verification per machine |
| Claude Code | The plugin: listed skills and roles, and a SessionStart hook that boots Buddy where the activation line or the user switch asks | Checked on Claude Code 2.1.302 (CLI); hooks depend on the entrypoint; host access rules still apply |
| OpenCode | The `forge:boot` skill `forge_setup.py` writes, asked for by the `AGENTS.md` activation line | One hosted model called the skill in every case, another never did; the TUI and local models are not verified |
| Cursor | Project rules referring to canonical sources | Rules-based adapter, outside the plugin and the setup |

The plugin serves Claude Code and Codex; `forge_setup.py` gives OpenCode the same switches.
[Installation](05-installation.md) contains the commands and the activation lines. This
page explains the runtime differences.

## Claude Code

The plugin lists its skills and the six read-only roles the host can enforce; every
other role and skill is reached by path from the framework tree and runs as a general
agent reading its role file. The plugin's SessionStart hook runs on start, resume and
compaction and boots Buddy only where the project's `AGENTS.md` carries the activation
line or the user switch is on; it yields to a leftover machine or project entry so
Buddy boots once. It is Claude-specific, not a hook for other hosts.

File access and role discovery are separate concerns. A path being readable does not
prove that its instruction files or subagent wrappers were loaded, and a plugin user
needs two `Read` allow rules (plugin root, user repository) to avoid a prompt on every
boot read.

## OpenCode

OpenCode reads the project's `AGENTS.md` and its global rules file itself and lists
skills from its skills folder. The setup writes the `forge:boot` skill there, which
names a Forge folder and the boot-entry command, and for every session the activation
line in the global `AGENTS.md`; no OpenCode JSON configuration is edited. Local project
AGENTS instructions add the consumer's rules; framework availability does not replace
them.

OpenCode has no SessionStart hook: the activation line asks the model to call the
skill. Roles run as general agents that read their file. Verify in the session that
the skill was called; do not infer host parity from shared Markdown.

## Codex

The plugin carries the skills, including `forge:boot`, and no roles; roles run as
general agents reading their role file. The activation line in the project's
`AGENTS.md` (or in `~/.codex/AGENTS.md` for every session) asks Codex to run the boot
skill. Codex copies a local plugin into its cache, so an edit in a checkout needs a
refresh there. The primary session follows the boot entry even without an explicitly
selected Buddy role. Delegated roles follow their
own canonical role rather than repeating primary-session bookkeeping.

Codex's writable workspace can retain a read-only `.git`, including linked-worktree
Git directories. For authorized Git writes and the boot fetch helper, the caller
uses the offered `require_escalated` route directly. Auto-review may approve it
without a human prompt; no success or automatic approval is guaranteed. Read-only
queries stay sandboxed where permitted. The [Codex execution contract](../agents/buddy/codex-execution.md)
keeps tool approval distinct from commit/push authority and records denial handling.
Forge neither removes this host boundary nor installs blanket Git allow rules.

Generated role defaults distinguish report-only reviewers from writers. A report
role returns its complete artifact inline; the parent persists it verbatim before
any downstream consolidation that requires it. Runtime overrides may change the
sandbox. Verify effective permissions before describing read-only enforcement.

A passing managed-file check does not establish live AGENTS loading or role discovery.
A fresh acceptance session must demonstrate those behaviors for its installed
profile. Claude SessionStart scripts are not Codex boot hooks.

## Cursor

The [Cursor adapter](../orchestrators/cursor/README.md) supplies project rules for
reading Forge's canonical instructions. Its layout and setup differ from the
plugin (Codex, Claude Code) and OpenCode's boot skill.

Treat these as shipped rules, not evidence of equivalent subagent execution,
permission enforcement or setup coverage. Verify what the actual Cursor session
loads and can execute before applying a method that requires independent agents.

## Delegation vehicles

Buddy chooses inline work, an isolated agent or a persistent session
(`agents/buddy/delegation.md` §Vehicle choice). What each host
offers differs; treat unverified rows as unknown, not as parity.

| Host | Isolated agent | Persistent user-visible session | Own worktree per writer |
|---|---|---|---|
| Claude desktop app | Subagents | Yes. A session started without a worktree shares the commissioning checkout and branch (observed: `git rev-parse --show-toplevel` → the main checkout, branch `main`) | Optional at session start (own worktree and branch) |
| Claude Code CLI | Subagents | Background sessions per the host documentation; not verified here | Per the host documentation (subagent and background-session isolation); not verified here |
| Codex | Generated roles | Not verified | Not verified |
| OpenCode | General agents reading the role file | Not verified | Not verified |
| Cursor | Not verified | Not verified | Host worktree feature; not verified here |

Where §Vehicle choice gives work a session, Buddy starts it himself, within the
host limits and authorization that section names. A chat that commissions a
session coordinates that work and is where the user reads
(`agents/buddy/coordinating-sessions.md` §Coordinator, §One reading place); a
session's model follows `framework/models.md` §A persistent session's model.
Host boundaries there: on the Claude desktop app the start call takes a model at
or below the starting chat's (per its start tool's description; not verified by
a run); per its tool descriptions, also not verified by a run, it reports a
session's turn end to the starting chat, quoting the start of its last message,
and can archive a session. A host's permission prompts for a session's tool
calls appear in that session, not in the coordinating chat. Other hosts' start
models, turn-end notices and archiving are not verified here.

Fallbacks: without a persistent-session vehicle, Buddy does the work himself,
inline and with isolated agents, and finishes it (`agents/buddy/delegation.md`
§Vehicle choice); a brief the user opens in a chat of their own is an option
only when the user asks for it. Without turn-end notices, archiving or messages
between chats, the coordinator reads the return and record locations at its own
turns, names the session to close, takes a session's questions from its return
and starts a new session for a further brief
(`agents/buddy/coordinating-sessions.md` §Session end). Without per-writer
worktrees, only one writing workstream runs per checkout.

## Hooks and enforcement

Shared Git hooks run at commit time when installed in the active repository.
Their source happens to live under the Claude adapter but they are Git mechanisms.
They do not intercept each agent write.

| Check | Behavior |
|---|---|
| Plan validation | Blocks on applicable plan errors |
| Commit convention | Blocks invalid commit messages in commit-msg mode |
| Skill frontmatter | Blocks invalid applicable skill metadata |
| Secret scan | Advisory; scanner availability affects coverage |
| Source verification | Advisory evidence-pointer checks |

Forge has no `PreToolUse`, `PostToolUse` or `UserPromptSubmit` tool-event hook layer.
Write-time behavior relies on instructions, protocols and the host's real permissions.
See the [enforcement registry](../framework/enforcement-registry.md) for distinctions.

## Adding a new adapter

Keep wrappers thin, preserve consumer scope, and document actual discovery and boot
mechanisms. Exercise the selected capability closure and fresh-session behavior.
An adapter must state unsupported behavior rather than imply universal parity.

Integration changes participate in coordinated activation when they affect managed
installation state. Do not introduce an independent background updater or bypass
managed-file ownership checks.

Next: [Maintainer guide](08-development-and-maintenance.md) · [Agent guide](09-agent-guide.md).
