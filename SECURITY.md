# Security Policy

## Scope

Forge supplies instructions and executable helpers for AI-agent work. Relevant
surfaces include scoped knowledge reads/writes, installation and recovery journals,
managed host configuration, development engines, installed hooks and agent delegation.

The helpers execute with their process user's effective permissions. The host
controls tool access and sandboxing; generated role instructions do not establish
an independent security boundary. Personal knowledge and recovery records belong
in their configured private scope and must not leak into another project's context.

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

- Path traversal, unsafe link handling or unintended disclosure in continuity helpers.
- Installation ownership, recovery or source-validation defects that overwrite
  unrelated content or activate an incomplete generation.
- Code execution from untrusted workflow/configuration input.
- Adapter or hook behavior that exceeds the intended authorization or scope.
- Incorrect security claims that cause users to rely on a missing protection.

## Boundaries and limitations

Forge targets trusted individual workspaces; multi-tenant isolation is not provided.
Cooperating writers use scoped locks and conditional publication. External editors
can bypass those locks, and cross-repository updates are not globally atomic.

The agent host controls its permissions and provider interaction. Report upstream
host or dependency vulnerabilities to the relevant project, and report Forge's
contribution if its configuration or code exposes them. Include Codex, Claude Code,
OpenCode or Cursor version/configuration when relevant.

Prompt instructions, role separation and review methods cannot guarantee correct
model behavior. Forge runs no tool-event enforcement layer. Shared Git hooks run
only when installed and invoked, can be bypassed by Git options, and provide bounded
checks. Secret scanning is a warning check and may be unavailable if its tool is
missing. It is not permission to commit secrets.

## Implemented protections

The [continuity contract](framework/continuity.md) describes scoped path checks,
protected snapshots, baseline comparison and durable multi-file recovery. The
[installation contract](framework/installation-activation.md) describes managed
ownership, coordinated activation and matched rollback. These mechanisms complement
local approval and storage rules; they do not replace them.

Frozen-history conventions and source-evidence protocols support traceability.
They are distinct from operating-system access controls. Verify effective host
permissions and actual instruction loading for the installation you use.

## Maintainer commitment

We treat reported vulnerabilities seriously even when they're in
opinionated single-user-design code. If you report something that turns
out to be a design-tradeoff rather than a bug, we'll acknowledge it
publicly in the response so the community can see the threat-model gap.
