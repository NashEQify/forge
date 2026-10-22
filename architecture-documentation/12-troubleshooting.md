# 12 — Troubleshooting

Start with the boundary that failed: host entry, installation, continuity or selected
development state. Preserve the current files and diagnostic output before trying
a repair. A generic reset can destroy the evidence needed to recover safely.

## Setup problems

### Missing Python dependency or host command

Use the Python environment that provides PyYAML, and verify the intended host CLI
is installed and on the launcher's PATH. Creating a virtual environment does not
change the environment of every desktop host. Follow [installation prerequisites](05-installation.md#prerequisites).

### `--check` exits nonzero

Exit 1 means changes are planned; exit 2 indicates a reported conflict or error.
Read the paths and error text before applying. A preview is read-only and does
not complete installation.
Use the shared installer's current `--help`; old host-specific setup flags may no
longer exist because all setup aliases now forward to the coordinator.

### Managed file, directory or symlink conflict

An ownership check found content it cannot safely replace. Preserve the current
content, identify whether it is user-owned or an edited generated file, and compare
it with the intended managed output. Reconcile through the coordinated procedure.

Do not delete host directories, replace symlinks by hand or remove ownership
manifests as a general workaround. `--migrate-legacy` recognizes only specific
byte-identical legacy content; it is not a force-overwrite option.

### Installation says `validation_pending`

Application finished but fresh acceptance has not. Keep ordinary sessions stopped.
Inspect `--maintenance status`, use the exact operation ID for a controlled
acceptance session, and record the checks actually performed. Submit that evidence
only after the installed generation works for the claimed targets.

See [verification](05-installation.md#verification). Writing “passed” into a file
without running acceptance does not establish a verified installation.

### Installation was interrupted or source changed unexpectedly

Inspect maintenance status. Keep affected sessions stopped during partial activation
or recovery. The coordinator's retry and rollback operate on journaled, matched
states; unknown later edits remain conflicts. Preserve the journal and locks.

If sources were updated before baseline preparation, say so: a later preparation
cannot recover the missing old working-tree state. Do not reset the repository or
reconstruct an old generation from wrappers alone. Use
[the activation contract](../framework/installation-activation.md) to assess recovery.

## Host entry problems

### `cc` cannot resolve a project scope

Named scopes resolve under `PROJECTS_DIR` and require `intent.md`; `framework` and
`forge` are built-in scopes. Check the intended directory and configuration.
Running from the consumer directory without a scope preserves that CWD.
For ambiguous names, use the exact matching name or enter the intended directory.

### Buddy did not load the intended instructions

Check the actual host entry: Codex managed AGENTS block, configured Claude boot,
OpenCode launcher/configuration, or Cursor project rules. Verify the framework root,
consumer CWD and selected profile in a fresh session. Access to a directory does
not prove that its instructions loaded.

A generated role's read-only default is not proof of effective sandbox restrictions.
Inspect runtime permissions and report any mismatch. The
[host guide](07-tool-integrations.md) separates these mechanisms.

### A software board starts during ordinary work

Check the workspace's intent and workflow selection. `full` makes tools available;
it does not select development. On-demand work follows local rules and explicitly
requested methods. Correct the selection at its source rather than deleting useful
skills from the installation.

## Knowledge and save problems

### A personal fact would be written into the project

Stop that write. Personal facts belong only to the configured user scope. If access
is unavailable, report the fact as deferred; do not park it in a shared project
handoff. Check [user-scope resolution](../framework/user-scope.md#3-resolution).

### A pending continuity operation remains

Use the continuity helper's scoped recovery interface. Inspect original, proposed
and current content plus dependent routes, then reconcile against a fresh snapshot.
Do not delete the pending record because one destination already contains the text.
An interrupted write may have completed before progress was recorded.

### Conditional publication reports a stale baseline

Recapture the required same-scope files and reconcile the intended change with the
new evidence. Do not retry prepared text blindly or bypass the helper with raw
writes. External writers may require an actual exclusive maintenance window.
See [continuity](../framework/continuity.md).

### Save cannot report completion

Identify whether the blocker is common knowledge reconciliation, a separate
repository's publication policy, or selected development obligations. Report partial
persistence accurately. An unrelated development blocker need not prevent ordinary
work, but it must remain visible and must not be silently cleared.

## Development problems

### A handoff refers to missing workflow state

The handoff does not contain the complete engine state. `.workflow-state/` is local
and gitignored in Forge; pushing the handoff does not transfer it. Confirm the exact
selected run and its authoritative state location. Do not recreate progress from
prose or bind every locally discovered workflow.

### A workflow definition is incompatible

Preserve the selected state and inspect the definition fingerprint and reviewed
compatibility mapping. Names and step counts do not prove equivalent semantics.
Restore is read-only with respect to progression; an engine resume command can
change pause state. Follow [development continuation](../framework/development-continuation.md).

### A Git hook blocks a commit

Read the named check. Applicable plan errors, commit format and skill frontmatter
can block. Secret scan, source verification and anti-phantom diagnostics are advisory.
Correct the responsible source or investigate a reproducible validator defect.
Do not remove the hook to turn a failing check into a success claim.

### Navigation or generated wrappers are stale

Edit the canonical source and run the relevant generator, then inspect its diff
and check idempotency. Installed integration changes still need coordinated
activation. See [maintenance](08-development-and-maintenance.md#generators).

## When nothing helps

Record the exact command, selected profile, host, operation or workflow identity,
observed output and preserved local changes. Remove secrets and personal content
before sharing a report. Use [CONTRIBUTING.md](../CONTRIBUTING.md) for a reproducible
issue, or [SECURITY.md](../SECURITY.md) for a security concern.

Next: [Daily operations](13-operational-handbook.md).
