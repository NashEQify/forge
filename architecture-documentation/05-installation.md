# 05 — Installation

Forge installs instructions and tools into agent hosts you already use. One
installer, `scripts/forge_install.py`, offers two profiles:

- **`project`** (the default): Forge in one named folder. Nothing outside that
  folder changes.
- **`full-ai-integration`** (the big installation): Buddy in every session of the
  machine, with a folder of personal context that carries knowledge and open work
  across projects.

Both profiles load the same start instructions and offer the same methods. The
difference is where the entries live and whether a personal context folder (the
user scope) exists. A project does not have to be software; see
[workflow selection](../framework/workflow-selection.md).

## Prerequisites

- An agent host: Claude Code or Codex. OpenCode has an entry only in
  `full-ai-integration`.
- Git and Python 3.10+ with PyYAML available to the Python interpreter that runs the
  installer and the session-start hooks.
- Bash and the Unix command-line tools the hooks and launchers use.
- A local Forge checkout. The examples use `~/forge`.

Host applications and model access are separate from Forge. Cursor has a
[rules-based adapter](07-tool-integrations.md#cursor), outside this installer.

## Quickstart

Clone the distribution and read the installer's help:

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

The session-start hooks and the `cc` and `oc` launchers call `python3`; their
environment must also provide PyYAML. Creating a virtual environment does not change
every host's runtime.

## Install into one project (`project`)

Preview, install, and later remove Forge in one folder:

```bash
python3 ~/forge/scripts/forge_install.py --check ~/my-app
python3 ~/forge/scripts/forge_install.py ~/my-app
python3 ~/forge/scripts/forge_install.py --remove ~/my-app
```

Without `--profile`, the installer installs `project`; `--profile project` is the
same. It works in any existing folder, with or without Git, and for any kind of
work. It writes only inside that folder:

| Path | What it is |
|---|---|
| `.claude/agents/<role>.md` | One short wrapper per Forge role. It names the role file in your Forge checkout; no instruction text is copied. |
| `.claude/agents/.forge-managed.json` | The installer's manifest of those wrappers. |
| `.claude/settings.local.json` | `agent: buddy` and one SessionStart group: the refresh hook, then the boot hook. Keys you or the host add stay. |
| `AGENTS.override.md` | The Codex entry, when Codex is a chosen host. |
| `.claude/.forge-project.json` | The record of what the install owns, with a hash of each part. |
| `.git/info/exclude` | In a Git project: one marked block that lists the paths above, so Git never tracks or commits them. |

It never reads, asks for or creates a user scope, and it writes nothing in your home
folder. The entries name the checkout's path, so keep `~/forge` where it is.

**Hosts.** `--host claude-code` or `--host codex` (repeat it or separate with commas)
chooses the assistants. Without it, a first install covers those whose command
(`claude`, `codex`) is on `PATH`; a later run keeps the recorded hosts, and a run
with a different `--host` removes the entry of a host it no longer names.

**Starting a session.** Start `claude` or `codex` in the folder, or open a Claude Code
session in that folder in the Claude desktop app. Claude Code asks once whether
you trust the folder; the project settings apply after that. A Claude Code session
in the cloud works from the repository's committed files, so it starts without
Forge. In a local Codex CLI test, starting at the project root loaded
`AGENTS.override.md`, ran its refresh command first and read the project's
`AGENTS.md` for local rules. A start in a Git subfolder also loaded the root
entry, but `--refresh .` looked for an installation in the subfolder and skipped
the update. Start at the root when you want the project install refreshed.

The Codex project install supplies the entry only. In a fresh Codex home the
`code-verification` role was unavailable by name. Buddy used a general agent
with the role's instructions to complete the check.

**The installer refuses** (exit 2, nothing written) when:

- the machine has the `full-ai-integration` installation, because Buddy already runs
  there in every session;
- the folder is the Forge checkout or lies inside it;
- the folder lies inside a Git work tree without being its top level, or is a linked
  worktree or submodule that shares another repository's Git directory;
- Git already tracks a path the install would write;
- `.claude/settings.json` or `.claude/settings.local.json` sets another `agent`;
- `AGENTS.override.md` exists without Forge's block, or a file Forge does not own
  sits at a wrapper path;
- only OpenCode is chosen or found: it has no project entry.

**Removal.** `--remove ~/my-app` deletes each recorded part whose bytes still match
what the install wrote. If you changed a part since, it stops before deleting
anything and names that part; reinstalling stops the same way. Keys and hooks you
added to `settings.local.json` and your own text around the blocks stay.

## Install for every session (`full-ai-integration`)

```bash
python3 ~/forge/scripts/forge_install.py --profile full-ai-integration \
  --user-repo ~/forge-context --create-user-repo --check
```

**User scope.** This profile keeps your personal context (who you are, how you want
to work) in a folder of your own, the user repository. `~/forge-context` is an
example name. `--user-repo PATH` names it: an existing folder, or with
`--create-user-repo` a new or empty one, which the installer creates with
`context/user/profile.md` (headings only) and `context/user/navigation.md`. The
layout is [the user-scope convention](../framework/user-scope.md). Without
`--user-repo` and without a machine setting, the installer asks once on a terminal
(an existing folder or a new one, then its path); without a terminal, and in
`--check`, it refuses and names `--user-repo`. Once the machine setting names the
folder, later runs need no `--user-repo`.

**What it changes.** The `--check` listing names every path. In an empty home folder
it lists:

- the machine setting `~/.config/forge/user.yaml` and the selection record under
  `~/.local/state/forge/`;
- the `cc` launcher in `~/.local/bin`, a fixed stub that runs the launcher in your
  checkout, and for OpenCode the `oc` launcher and `~/.config/forge/opencode.jsonc`;
- Claude Code: the SessionStart hooks in `~/.claude/settings.json` and the links
  `~/.claude/skills` and `~/.claude/agents`;
- Codex: the boot block in `~/.codex/AGENTS.md`, role files in `~/.codex/agents/` and
  skill wrappers in `~/.agents/skills/`;
- with Claude Code, in the Forge checkout: links to Forge's Git hooks in `.git/hooks/`.

Hosts are chosen as above, with `opencode` as a third choice; on this profile a host
you no longer name keeps its entries (no removal). If you already have your own Claude
Code hooks or a `~/.claude/agents` folder, the installer stops and reports it instead
of overwriting them; your own folders under `~/.claude/skills` (and the ones Claude
Code keeps there, such as `synced/`) are left alone, beside Forge's entries. The installation then owns the whole `hooks` key of
`~/.claude/settings.json`: a hook you add there later is reported as a changed Forge
entry. `--skill-link PATH` links one of your own skill folders next to Forge's.
Positional `PROJECT` arguments here add a Codex boot block to each named project's
`AGENTS.md`; the installation records those projects, so every refresh updates their
blocks and the removal takes them out again.

**Starting a session.** In the terminal, start Claude Code with `cc` and OpenCode
with `oc` from `~/.local/bin`; that directory must come before other commands of the
same name on `PATH` (`cc` can otherwise resolve a C compiler), or type the full
path. The Claude desktop app and Codex start Buddy through their entries without a
launcher. [`cc` reference](../docs/cc-launcher.md).

**Removal.** `python3 ~/forge/scripts/forge_install.py --profile full-ai-integration
--remove` takes out what this installation wrote, read from its own records: the
files and links it placed, its block in `~/.codex/AGENTS.md`, its hooks in
`~/.claude/settings.json` and its keys in the machine setting, the links to Forge's
Git hooks it created in the checkout, and its records. Keys and text you or your
assistant added to those files stay, and so do your user repository, the checkout's
files and hook links that were there before the install. In each
recorded Codex project it removes Forge's block and leaves your text byte for byte;
it deletes the project's `AGENTS.md` only when Forge created it and nothing else is
left. If you changed a project's block, that block stays and the removal prints the
markers to delete by hand, names it in `--check` too, and exits 1 (the rest is
removed). If you changed another part Forge wrote, or an installation step is still
open, it stops, names it and removes nothing (exit 2). Add `--check` to list the
paths first. If it is interrupted, the next session start says so and asks you to
run it again; the rerun finishes the job. It stages and commits nothing, and it
refuses a record that names a path outside Forge's folders or one with `..`.

A project install made earlier stays in its folder, and its boot hook steps aside
for the machine-wide installation so Buddy starts at most once: in the desktop and
web apps through the machine-wide hook, in the terminal through `cc` (plain `claude`
there starts without Buddy). `--remove ~/my-app` takes it out.

## One installer for every host

`setup-cc.sh`, `setup-codex.sh` and `setup-oc.sh` are compatibility entrypoints for
the machine-wide installation: each runs `forge_install.py --profile
full-ai-integration --host <its host>` and passes further arguments on.

`--check` writes nothing. Exit 0 means nothing would change, 1 means changes are
planned, and 2 means a reported conflict or error. Read the output before applying,
then run the same command without `--check`.

Managed-file hashes protect ownership. Unknown files, edited managed files and
unexpected links stop the installation. Preserve those changes and reconcile the
conflict; do not replace directories or links from a generic cleanup recipe.
`--migrate-legacy` only adopts recognized byte-identical legacy content.

`CODEX_HOME` and `AGENTS_HOME` environment variables can select Codex destinations.
Changing the user repository of a configured machine needs `--user-repo`; do not use
`--force-user-config` as a substitute for understanding that change. A profile name
from an older Forge version is refused with a message naming the current one.

### Codex

The project install writes the boot block into the project's
`AGENTS.override.md`. The machine installation manages role files, skill wrappers
and a boot block in the Codex home `AGENTS.md` and in the `AGENTS.md` of projects
named on its command line. Surrounding project instructions remain local authority.
Test discovery and instruction loading in a fresh session; file presence alone does
not prove either.

### Claude Code

The project install makes Buddy the main agent of every Claude Code session in the
project and gives it the roles under their plain names. The machine installation
prepares Claude discovery, the SessionStart integration and the `cc` launcher; its
boot hook serves the desktop and web apps, and `cc` boots Buddy in the terminal.

### OpenCode

The machine installation prepares `oc` and its generated configuration. The launcher
uses `~/.config/forge/opencode.jsonc` and the framework's OpenCode wrapper directory.
Keep the consumer as the active working directory.

## Updating

`git -C ~/forge pull` is the whole update, on both profiles, also for an installation
made with an earlier Forge version (its first start after the pull takes a few seconds
longer, once). Each session start runs
`forge_install.py --refresh` first: the Claude Code SessionStart hook and the `cc`
and `oc` launchers call it, and the Codex boot blocks ask Codex to run it before the boot. When the checkout's
commit changed since the install, it brings the installed entries up to that
commit; otherwise it does nothing. It never stops a start: when it may not run, it
skips with one line and the session starts with the entries it has.

You can run it by hand: `python3 ~/forge/scripts/forge_install.py --refresh` for the
machine installation, or `--refresh ~/my-app` for a project.

On the machine installation, a refresh skips, an install refuses, and `cc` and `oc`
refuse to start while a tracked file other than Markdown has uncommitted changes in
the checkout; commit or discard the change. They also stop when a part Forge wrote
into a shared file (its hooks in `~/.claude/settings.json`, its block in
`~/.codex/AGENTS.md`) was changed; restore that part. A part you deleted or cut out
is written again by the next start; a project folder you delete leaves the
installation's records at the next install or the first start after a pull, and a
file of a host you no longer name is left alone. A project refresh follows commits
only. An interrupted refresh is completed by the next one.
The installation's lock lives in `/tmp/forge-install-<uid>`; on a machine with several
local accounts another account can create that folder first, and starts then refuse
until it is removed.

## The coordinated maintenance path (changing Forge itself)

This path is for people who change Forge's own sources on the machine they work on.
It is opt-in: add `--coordinated` (with `--user-repo`) to a `full-ai-integration`
install. The machine setting then records `maintenance: coordinated`, later installs
keep it, and the refresh skips. A checkout without a Git commit takes this path too.

On this path, changes follow [coordinated activation](../framework/installation-activation.md):
prepare a baseline before changing sources, install, then accept the new generation
in a fresh session.

### Verification

An install on this path can succeed while returning **`validation_pending`**.
Ordinary sessions must remain stopped until acceptance of that exact generation.
Inspect:

```bash
python3 ~/forge/scripts/forge_install.py --maintenance status
```

Record the returned operation ID. For a controlled fresh acceptance session through
a launcher, substitute that exact ID:

```bash
~/.local/bin/cc --forge-validation-operation "<operation-id>"
~/.local/bin/oc --forge-validation-operation "<operation-id>"
```

These are alternatives for the host being checked, not instructions to launch both.
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

### Updating on this path

Classify the change first: instruction-only Markdown takes its light path (edit,
regenerate derived files when needed, consistency check, commit). Every other
change takes these steps:

1. Identify the source checkout, affected integrations and authorized consumers.
   Preserve configuration and local changes.
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

### Interrupted installation

Inspect `--maintenance status` first. Use `--maintenance retry` or
`--maintenance rollback` for the journaled operation as appropriate. Retry accepts
journal-proven states; unknown later edits remain conflicts. Rollback checks the
matched source/integration baseline and selected workflow compatibility, preserving
consumer content. It is not a repository reset.

Keep sessions stopped during `applying`, `recovery_required` or unresolved
`validation_pending`. Do not unlink coordination locks, erase journals or hand-edit
workflow state to make an installation appear ready.

Next: [Host integrations](07-tool-integrations.md) · [Troubleshooting](12-troubleshooting.md).
