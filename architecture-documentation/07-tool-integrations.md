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
| Codex | Managed AGENTS boot blocks, generated roles and skill wrappers | Fresh-session loading, discovery and effective permissions need verification |
| Claude Code | Configured SessionStart, discovery files and full-profile `cc` launcher | Hooks depend on configured entrypoints; host access rules still apply |
| OpenCode | Full-profile `oc` launcher and generated configuration | Wrapper and configuration loading need host verification |
| Cursor | Project rules referring to canonical sources | Rules-based adapter, outside the coordinated host installer |

The shared installer coordinates managed Codex, Claude Code and OpenCode plans.
All named setup scripts forward to it; `setup-codex.sh` does not mean Codex-only
installation. [Installation](05-installation.md) contains the commands and activation
procedure. This page explains the runtime differences.

## Claude Code

Canonical personas have Claude wrappers under `.claude/agents/`. Skill wrappers
provide discovery and forward to the real skill. Full installation prepares managed
user-level discovery, settings and a launcher; daily has a smaller boot/skill surface.
Do not assume every supported generation uses identical symlink layouts.

The `cc` launcher resolves a framework root and retains the consumer CWD unless a
scope is supplied. `framework` and `forge` select the framework checkout; other
names resolve under `PROJECTS_DIR` and require `intent.md`. `FRAMEWORK_DIR` and
`PROJECTS_DIR` can be configured. `CC_DEBUG=1` prints the resolved invocation.

The launcher provides file context and Buddy entry. File access and role discovery
are separate concerns. A path being readable does not prove that its instruction
files or subagent wrappers were loaded.

Configured Claude SessionStart scripts support boot and remote-session entry.
They are Claude-specific, not universal hooks for other hosts. Shared source
updates use stopped-session maintenance; boot must not independently pull and
reinstall the framework.

## OpenCode

The `oc` launcher resolves the framework checkout, checks installation readiness,
sets `OPENCODE_CONFIG_DIR` to the framework's wrapper directory and sets
`OPENCODE_CONFIG` to `~/.config/forge/opencode.jsonc`.

The managed configuration is machine-specific. Its source template and neutral
role definitions remain in the framework. Local project AGENTS instructions add
the consumer's rules; framework availability does not replace them.

OpenCode uses launcher/configuration entry rather than Claude's SessionStart scripts.
Verify that the selected role and required skills are available in the session.
Do not infer host parity from shared Markdown or from the existence of the launcher.

## Codex

The installer generates roles from neutral `agents/*.md` definitions and installs
skill discovery wrappers. Default destinations are `~/.codex/agents/` and
`~/.agents/skills/`; supported environment overrides are described in installation.

Managed boot blocks in the Codex home AGENTS file and supplied consumer AGENTS
files identify the framework and selected boot. The primary session follows that
entry even without an explicitly selected Buddy role. Delegated roles follow their
own canonical role rather than repeating primary-session bookkeeping.

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
managed Codex, Claude Code and OpenCode integrations.

Treat these as shipped rules, not evidence of equivalent subagent execution,
permission enforcement or installer coverage. Verify what the actual Cursor session
loads and can execute before applying a method that requires independent agents.

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
| Anti-phantom | Advisory checks for stale enforcement claims |

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
