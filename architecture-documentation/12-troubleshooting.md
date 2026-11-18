# 12 — Troubleshooting

Start with the boundary that failed: host entry, installation, continuity or selected
development state. Preserve the current files and diagnostic output before trying
a repair. A generic reset can destroy the evidence needed to recover safely.

## Setup problems

### Missing Python dependency or host command

Use the Python environment that provides PyYAML, and verify the intended host CLI
is installed and on the host's PATH. Creating a virtual environment does not
change the environment of every desktop host. Follow [installation prerequisites](05-installation.md#prerequisites).

### The setup stops and names a file

`forge_setup.py` reads and checks every target before its first write. It stops with
exit 2 and names the file and the reason when a target is edited, foreign or unreadable
(for example an edited `forge-boot` skill, or a `user.yaml` it cannot parse); nothing is
written then. Preserve that file, decide whether its content is yours, and run the setup
again once it is reconciled. `status` lists what the setup finds without writing.

### The plugin did not load or Buddy did not start

Check `claude plugin list` (or `codex plugin list`, with input from `/dev/null`) for
`forge@forge`. Buddy starts only where the project's `AGENTS.md` carries the activation
line, or the user switch is on (Claude Code: `buddy: every-session` in
`~/.config/forge/user.yaml`; Codex: the line in `~/.codex/AGENTS.md`); without either
the plugin only lists its skills. If `env.FRAMEWORK_DIR` is set in
`~/.claude/settings.json`, the boot's status probe reads that checkout instead of the
plugin root. A prompt on every boot read means the two `Read` allow rules are missing
([installation](05-installation.md#switch-buddy-on)).

### OpenCode did not start Buddy

`opencode debug skill` lists `forge:boot` without starting a model; `forge_setup.py status`
names the Forge folder the skill points at. A skill that names a versioned Claude Code
plugin folder needs the setup run again after a plugin update
([OpenCode](05-installation.md#opencode)).

## Host entry problems

### Buddy did not load the intended instructions

Check the actual host entry: the plugin's activation line or user switch,
OpenCode's boot skill, or Cursor project rules. Verify the framework root and
consumer CWD in a fresh session. Access to a directory does
not prove that its instructions loaded. Buddy runs the whole start before its first
answer, also for a quick question, and its first answer opens with the orientation
line (time, host, CWD; a blocked check is one word in it, such as `remote
unchecked`). An instruction file that could not be read is named first, before that
line. An answer without the orientation line suggests the start did not run. For a session that already ran, the
[session diagnosis](../skills/session_diagnosis/SKILL.md) checks its transcript first
for whether Forge loaded, with the lines that show it.

A generated role's read-only default is not proof of effective sandbox restrictions.
Inspect runtime permissions and report any mismatch. The
[host guide](07-tool-integrations.md) separates these mechanisms.

### Git reports a read-only `.git` inside a writable workspace

`cannot open .git/FETCH_HEAD: Read-only file system` during fetch/pull or an
`index.lock` write failure can come from Codex's protected Git metadata. Normal
file mode bits and trusted-project configuration do not override that mount.
For a concrete already-authorized write, use `exec_command` with
`sandbox_permissions="require_escalated"` when the host offers it; avoid a known
failing first attempt. Auto-review can handle eligible requests without involving
the user. A denied or unavailable approval remains a concrete host limit.

Do not change sandbox settings, move `.git`, add writable roots or grant blanket
Git access as a workaround. Fetch/pull authorization does not imply publication.
See the [Codex execution contract](../agents/buddy/codex-execution.md). A failed boot
fetch is reported on stderr; cached ahead/behind values do not prove remote freshness.

### A software board starts during ordinary work

Check the workspace's intent and workflow selection. The installation makes tools
available; it does not select development. On-demand work follows local rules and explicitly
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
can block. Secret scan and source verification diagnostics are advisory.
Correct the responsible source or investigate a reproducible validator defect.
Do not remove the hook to turn a failing check into a success claim.

### Navigation or generated wrappers are stale

Edit the canonical source and run the relevant generator, then inspect its diff
and check idempotency. A change to a host integration then follows
[installation activation](../framework/installation-activation.md). See [maintenance](08-development-and-maintenance.md#generators).

## When nothing helps

Record the exact command, selected profile, host, operation or workflow identity,
observed output and preserved local changes. Remove secrets and personal content
before sharing a report. A session diagnosis report names the failed layer with the
cited lines; share its shared copy, not the transcript. Use
[CONTRIBUTING.md](../CONTRIBUTING.md) for a reproducible issue, or
[SECURITY.md](../SECURITY.md) for a security concern.

Next: [Daily operations](13-operational-handbook.md).
