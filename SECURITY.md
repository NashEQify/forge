# Security Policy

## Scope

forge is a methodology + tooling repo for personal AI-agent
setups. Security-relevant surface:

- **Hooks** in `orchestrators/claude-code/hooks/` (Bash, run by Claude
  Code with user permissions).
- **Engines** in `scripts/` (Python, run by user with full PATH access).
- **Adapter configs** that route paths and external_directory permissions
  (`opencode.jsonc`, `.claude/settings.json`, `.claude/path-whitelist.txt`).
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

- Hook scripts that escalate path-write privileges
- Path-whitelist bypass via creative path crafting
- Frozen-zone-guard bypass
- Pre-commit-hook bypass that lets unsafe content into commit history
- Plan-engine / workflow-engine arbitrary-code-execution from YAML input
- Adapter-config injection (untrusted opencode.jsonc / settings.json)

## Out of scope (not vulnerabilities)

- **Single-user assumptions** — the framework is designed for trusted
  single-user setups. Multi-user / shared-host concerns require explicit
  threat-modeling work that hasn't been done.
- **LLM hallucinations** producing harmful suggestions — the framework's
  Anti-Hallucination posture is via mechanical hooks (path-whitelist,
  pre-commit-validate), not via prompt-level filtering.
- **Generic supply-chain risks** of Python deps (PyYAML, etc.) — see
  https://github.com/advisories for upstream.
- **Claude Code / OpenCode / Cursor agent-tool privilege scope** — that's
  upstream's threat model.

## Hardening that's already in place

- **Path-Whitelist** (`path-whitelist-guard.sh`) blocks Edit/Write to
  unwhitelisted paths.
- **Frozen Zones** (`frozen-zone-guard.sh`) block writes to
  `context/history/**` (append-only WORM).
- **Pre-Commit-Hook** runs `plan_engine.py --validate` and frontmatter
  validation before allowing commits.
- **No external network calls** in hooks.

## Known weak points

- **OC-Adapter has no PreToolUse-Hook equivalent** — path-write discipline
  under OpenCode is mental, not mechanical.
- **Cursor adapter** has no PreToolUse-Hook either (Cursor's API doesn't
  expose one). Pre-commit-hook is the only mechanical gate there.
- **Pre-commit `--no-verify`** can bypass all 12 checks. Discipline-only
  protection.

## Maintainer commitment

We treat reported vulnerabilities seriously even when they're in
opinionated single-user-design code. If you report something that turns
out to be a design-tradeoff rather than a bug, we'll acknowledge it
publicly in the response so the community can see the threat-model gap.
