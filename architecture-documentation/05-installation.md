# 05 — Installation

Forge installs instructions and tools into existing agent hosts. Use the shared
installer to preview, apply and verify one coherent installation. Existing installs
must preserve their current generation **before** updating framework sources.

## Prerequisites

- An installed agent host: Codex, Claude Code or OpenCode for its managed integration.
- Git and Python 3.10+ with PyYAML available to the Python interpreter running setup.
- Bash and the Unix command-line tools used by the shell launchers.
- A local Forge checkout and permission to update the intended managed host files.
- An existing user workspace if you want persistent personal context.

Host applications and model access are separate from Forge. Cursor has a
[rules-based adapter](07-tool-integrations.md#cursor), outside the coordinated
host installation described here.

## Quickstart

Clone the distribution and inspect the installer:

```bash
git clone https://github.com/NashEQify/forge ~/forge
python3 ~/forge/scripts/forge_install.py --help
```

If PyYAML is unavailable, create an isolated environment and activate it before
running the remaining Python commands:

```bash
python3 -m venv ~/forge/.venv
source ~/forge/.venv/bin/activate
python3 -m pip install pyyaml
```

The `cc` and `oc` launchers call `python3`; their environment must also provide
PyYAML. Do not assume creating a virtual environment changes every host's runtime.

## User and install profile

| Preset | Available capabilities |
|---|---|
| `daily` | Knowledge maintenance, save, housekeeping, minimal boot and Bedrock; no software tooling or full host launchers |
| `full` | All roles, skills, software tooling, hooks and launchers, plus on-demand use |

Council and Frame can be added to `daily` through `--method council` and
`--method frame`. Selection persists on repeat installs when no replacement method
selection is supplied. See [profile definitions](../framework/install-profiles.yaml).

Use an **existing** user workspace. The installer records its path; it does not
invent a profile or reorganize its content. Personal context follows
[the user-scope convention](../framework/user-scope.md). Without `--user-repo`, an
existing machine configuration is retained; an unconfigured installation has no
user scope. Project-only continuity and supplied-context reasoning remain useful.

Preview a daily installation:

```bash
python3 ~/forge/scripts/forge_install.py \
  --profile daily --user-repo ~/projects/personal --check
```

Add optional methods by including the same options in preview and application:

```bash
python3 ~/forge/scripts/forge_install.py \
  --profile daily --user-repo ~/projects/personal \
  --method council --method frame --check
```

`--check` writes nothing. Exit 0 means no planned changes, 1 means changes are
planned, and 2 indicates a reported conflict or error. Inspect the output before
applying. A check is not live acceptance.
Once the intended targets are reviewed and affected sessions are stopped, apply
with the same arguments and omit `--check`.

For full installation and a managed Codex boot block in an existing project:

```bash
python3 ~/forge/scripts/forge_install.py \
  --profile full --user-repo ~/projects/personal \
  ~/projects/my-app --check
```

The positional project path adds a Codex boot entry. `--consumer-root PATH` has a
different purpose: explicitly scope development-state compatibility checks during
maintenance. Include authorized affected consumers when that check is needed.

## One installer for managed hosts

`setup-cc.sh`, `setup-codex.sh` and `setup-oc.sh` are compatibility entrypoints;
**all forward their arguments to `forge_install.py`**. Their names do not restrict
installation to one host. `full` plans the managed Codex, Claude Code and OpenCode
surfaces together. Preview the whole plan, including configuration and hooks.

Managed-file hashes protect ownership. Unknown files, edited managed files and
unexpected links may stop installation. Preserve those changes and reconcile the
conflict; do not replace directories or links from a generic cleanup recipe.
`--migrate-legacy` only adopts recognized byte-identical legacy content.

`CODEX_HOME` and `AGENTS_HOME` environment variables can select Codex destinations.
The current shared CLI has no `--codex-home` or `--agents-home` flags. Changing a
configured profile may require passing `--user-repo` to update its machine setting.
Do not use `--force-user-config` as a substitute for understanding that change.

### Codex

The installer manages role files, skill wrappers and a boot block in the Codex home
AGENTS file and supplied projects' AGENTS files. Surrounding project instructions
remain local authority. Test discovery and instruction loading in a fresh session;
file presence alone does not prove either.

### Claude Code

Full installation prepares Claude discovery, configured SessionStart integration
and the `cc` launcher. Daily uses managed boot/skill entries without the full
launcher setup. A full-to-daily conflict needs a reviewed migration; do not delete
existing host directories simply because a diagnostic mentions them.

### OpenCode

Full installation prepares `oc` and its generated configuration. The launcher uses
`~/.config/forge/opencode.jsonc` and the framework's OpenCode wrapper directory.
Keep the consumer as the active working directory.

## Verification

An apply command can succeed while returning **`validation_pending`**. Ordinary
sessions must remain stopped until acceptance of that exact generation. Inspect:

```bash
python3 ~/forge/scripts/forge_install.py --maintenance status
```

Record the returned operation ID. For a controlled fresh acceptance session through
a full-profile launcher, substitute that exact ID:

```bash
~/.local/bin/cc --forge-validation-operation "<operation-id>"
~/.local/bin/oc --forge-validation-operation "<operation-id>"
```

The full installer places these launchers in `~/.local/bin`. Bare `cc` and `oc`
require that directory to precede competing commands on PATH; `cc` can otherwise
resolve a C compiler. These are alternatives for the host being checked, not
instructions to launch both.
A wrong operation ID, partial installation or source drift refuses entry. For other
host entrypoints, start a controlled fresh acceptance session and verify the same
installed generation and selected capabilities. Before that session, check the
exact pending generation without marking ordinary sessions ready:

```bash
python3 ~/forge/scripts/forge_install.py --maintenance status \
  --validation-operation "<operation-id>" --require-ready
```

Verify what was actually installed: normal entry and instruction loading, relevant
retrieval, authorized capture/save/resume, and exact selected development continuation
where applicable. Record host, profile, source generation, observations and limits
in an evidence file. Check runtime permissions separately from role defaults.

Only after those checks have actually succeeded, submit the evidence:

```bash
python3 ~/forge/scripts/forge_install.py --maintenance validate \
  --operation-id "<operation-id>" --validation-evidence /path/to/actual-evidence.md
python3 ~/forge/scripts/forge_install.py --maintenance status --require-ready
```

The evidence file must contain real observations. The installer records its hash;
it cannot establish the truth of a written “passed” claim. Skipped or inaccessible
targets must remain explicitly unverified.

## Updating an existing installation

Follow [coordinated activation](../framework/installation-activation.md):

1. Identify the source checkout, affected integrations, selected methods and
   authorized consumers. Preserve configuration and local changes.
2. Stop affected sessions before any pull or source edit, and keep them stopped.
3. From the currently installed generation, prepare the actual working-tree baseline:

```bash
python3 ~/forge/scripts/forge_install.py --maintenance prepare \
  --consumer-root /path/to/authorized-consumer
```

4. Perform the authorized source update without discarding local work.
5. Preview and apply the intended installation, then perform fresh acceptance above.

Repeat `--consumer-root` for additional explicitly authorized consumers. Omit it
when no consumer development state is selected for checking. Do not scan unrelated
workspaces. Preparing after an update cannot retroactively preserve the old baseline.

## Interrupted installation

Inspect `--maintenance status` first. Use `--maintenance retry` or
`--maintenance rollback` for the journaled operation as appropriate. Retry accepts
journal-proven states; unknown later edits remain conflicts. Rollback checks the
matched source/integration baseline and selected workflow compatibility, preserving
consumer content. It is not a repository reset.

Keep sessions stopped during `applying`, `recovery_required` or unresolved
`validation_pending`. Do not unlink coordination locks, erase journals or hand-edit
workflow state to make an installation appear ready.

Next: [Host integrations](07-tool-integrations.md) · [Troubleshooting](12-troubleshooting.md).
