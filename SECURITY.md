# Security Policy

## Scope

forge is a methodology + tooling repo for personal AI-agent
setups. Security-relevant surface:

- **Hooks** in `orchestrators/claude-code/hooks/` (Bash, run by Claude
  Code with user permissions).
- **Engines** in `scripts/` (Python, run by user with full PATH access).
- **Adapter configs** that route paths and external_directory permissions
  (`opencode.jsonc`, `~/.claude/settings.json` — forge hooks slot,
  provisioned by `setup-cc.sh` from
  `orchestrators/claude-code/settings.json.template`).
- **Sub-agent dispatch** flows that can lead to LLM-driven file/code edits.

## Reporting a vulnerability

**Do not open a public issue for security-sensitive reports.**

Email the maintainer directly: see GitHub profile of repository owner.
PGP available on request.

Include:
- Description of the vulnerability
- Repro steps (sanitized — do not include actual exploit payloads against
  third-party systems)
- Affected files / commit hash
- Proposed fix if you have one

## Response timeline

This is a one-maintainer project. Best-effort response:
- **Acknowledgment:** within 7 days
- **Initial assessment:** within 14 days
- **Fix or written decision:** within 30 days (longer for design-level issues)

If you don't hear back within 14 days, follow up via a different channel
(direct email, Discord/Twitter DM if known).

## What we consider in-scope

- Hook scripts (SessionStart / git pre-commit) that escalate privileges
- Pre-commit-hook bypass that lets unsafe content into commit history
- Plan-engine / workflow-engine arbitrary-code-execution from YAML input
- Adapter-config injection (untrusted opencode.jsonc / settings.json)

## Out of scope (not vulnerabilities)

- **Single-user assumptions** — the framework is designed for trusted
  single-user setups. Multi-user / shared-host concerns require explicit
  threat-modeling work that hasn't been done.
- **LLM hallucinations** producing harmful suggestions — the framework's
  anti-drift posture is via protocol-anchored discipline + git pre-commit
  validation, not via prompt-level filtering.
- **Generic supply-chain risks** of Python deps (PyYAML, etc.) — see
  https://github.com/advisories for upstream.
- **Claude Code / OpenCode / Cursor agent-tool privilege scope** — that's
  upstream's threat model.

## Hardening that's already in place

- **Pre-commit hook** (universal, git-triggered) runs `plan_engine.py
  --validate`, commit-convention + SKILL-frontmatter validation (BLOCK)
  plus secret-scan + source-verification (WARN) before a commit lands.
- **Frozen Zones** — `context/history/**` is append-only WORM by
  convention (corrections via `.correction.md` sidecars).
- **No external network calls** in hooks.

## Known weak points

- **No write-time enforcement on any harness** — the framework runs no
  tool-event hooks (PreToolUse / PostToolUse); path-write discipline is
  protocol-anchored, not blocked at the tool call. The mechanical layer
  is git pre-commit (universal) + SessionStart boot.
- **Cursor adapter** (and any harness without a tool-event API): the
  workflow phase model + git pre-commit checks are the mechanical
  layer there; path-write discipline is workflow-driven rather than
  blocked at the tool call.
- **Pre-commit `--no-verify`** can bypass all 6 checks. Discipline-only
  protection.

## Maintainer commitment

We treat reported vulnerabilities seriously even when they're in
opinionated single-user-design code. If you report something that turns
out to be a design-tradeoff rather than a bug, we'll acknowledge it
publicly in the response so the community can see the threat-model gap.
