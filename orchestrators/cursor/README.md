# Cursor rules and persona templates

This directory supplies Forge-oriented rules under `rules/` and persona templates
under `agents/`. It is a rules-based integration, not a managed installation target
of `scripts/forge_install.py` and not proof of parity with another host.

Use the [host integration guide](../../architecture-documentation/07-tool-integrations.md)
and inspect the templates before adopting them in a project's Cursor configuration.
Verify the rule format, loading behavior and tool permissions against the Cursor
version you actually use. Preserve existing project rules; do not replace a user's
rule directory blindly.

## Scope

The consumer's intent and local rules still determine whether software workflows
apply. Installed instructions must not force everyday knowledge work into tasks,
boards or test chains. The common Knowledge Processor and continuity contracts stay
authoritative; project rules retain storage, privacy and operational approvals.

A persona template supplies instructions. It does not prove that a separate agent
ran independently. If the host cannot execute a selected method's required agent
separation, report that limitation or choose an applicable interaction mode. Do not
label sequential role-playing as an independent Council.

Forge has no FACTS background hook or universal automatic engine trigger. Shared
Git hooks can run independently of the editor when installed in the repository.
They do not enforce every tool call or establish host-specific sandboxing.

## Verification

Open a fresh session in the intended consumer and check which rules were loaded,
which files/tools are accessible and whether the intended method can actually run.
This repository's templates alone do not establish current Cursor feature support.
For coordinated Forge source upgrades, follow
[installation activation](../../framework/installation-activation.md) and preserve
any separately managed Cursor configuration.
