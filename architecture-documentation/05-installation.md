# 05 — Installation

## Ask your agent

```text
Install Forge from github.com/NashEQify/forge
```

Your agent follows [INSTALL.md](../INSTALL.md) in the repository: it checks the prerequisites, adds the plugin on
each host it finds (Claude Code, Codex), asks whether Buddy runs in this project only or in every session (and, for
every session, which folder holds your personal context, creating it on your yes), and runs
`scripts/forge_setup.py`, which writes the activation line, the user switch and the `Read` allow rules. Then it
checks that a fresh session opens with Buddy's orientation line. Nobody edits a file by hand. Once installed, the
`forge:setup` skill changes the scope later or removes Forge, and the plugin's other skills offer it once when they
run where Buddy is off.

The rest of this page is the reference: what the agent runs, and how to do it by hand.

## The plugin

Forge reaches Claude Code and Codex as one **plugin**. The plugin carries the skills,
the boot hook and the framework tree; two small switches turn Buddy on: one line in a
project's `AGENTS.md` (Buddy in that project), or one setting in your user file (Buddy
in every session). OpenCode has no plugin route yet; it keeps the installer
(`forge_install.py`, below).

What the live proof showed, and what it did not, is stated per item. Observed so far:

- **Claude Code:** boot through the activation line and the user switch, role dispatch,
  resume and compaction, knowledge maintenance and removal, on Claude Code 2.1.302 with
  a local directory as the marketplace (CLI). On a second machine the plugin was
  installed, listed and updated from the public marketplace (Claude Code 2.1.299), and a
  desktop session in the user's workspace booted.
- **Codex:** the plugin from the public marketplace (Codex 0.163): the `AGENTS.md` line
  and the user switch ran `forge:boot` with the user scope, a fact was saved with its
  `FACTS` line (on a copy of the user repository), and `save` and `housekeeping` reached
  their workflows.
- **Not shown:** that an update brings a newer version (the public repository did not
  move during the checks), the Claude desktop app without a permission prompt, and
  OpenCode.

## Prerequisites

- Claude Code or Codex. Host applications and model access are separate from Forge.
- Git, and Python 3.10+ with PyYAML available to the `python3` the boot hook runs. The
  hook calls plain `python3`; a virtual environment does not change what a host runs.
- Bash and the Unix command-line tools the hook uses.

Cursor has a [rules-based adapter](07-tool-integrations.md#cursor), outside the plugin.

## Add the plugin

The marketplace is the Forge repository (`.claude-plugin/marketplace.json`); the plugin
is `forge`. Claude Code:

```bash
claude plugin marketplace add <marketplace>
claude plugin install forge@forge --scope user
```

Codex:

```bash
codex plugin marketplace add <marketplace>
codex plugin add forge@forge
```

`<marketplace>` is `NashEQify/forge` for the public repository, or the path of a local
Forge checkout. A local checkout is read in place by Claude Code: an uncommitted edit
in the checkout reached the next session without an update. Claude Code fell back to
HTTPS for the GitHub shorthand where no SSH key was configured. Codex copies the plugin
into its cache, so an edit in a checkout does not reach a session until the plugin is
removed and added again (`codex plugin marketplace upgrade` answered "up to date" and
was not shown to bring a new commit). The copy includes the checkout's `.git`: about 20
MB from the public marketplace, 165 MB from a local checkout of a large working copy.
Codex's boot status line then names a few uncommitted entries of that copy beside your
own.

The plugin lists twelve stand-alone skills (`council`, `frame`, `bedrock-drill`,
`code-review-board`, `root-cause-fix`, `spec-board`, `testing`,
`security-and-hardening`, `workflow-router`, `zoom-out`, `boot`, `setup`) and six read-only roles
whose tool limits the host enforces. Claude Code's own estimate of its always-on cost, in a
clean home, is about 1,120 tokens for the skill descriptions and about 1,620 with the roles;
the `setup` skill adds about 80 of them. Estimates for the same package have differed between
installs by a few hundred tokens. Every other skill and
role is reached by path from the framework tree and runs as a general agent reading its
role file.

## Switch Buddy on

`python3 <plugin root>/scripts/forge_setup.py` makes each of the writes below and is what the agent runs:
`status` (what is set), `project --project DIR` (the line), `every-session --user-repo DIR [--create-user-repo]`
(the switch on each host and the allow rules), `every-session --off`, `project --project DIR --off` and `remove`.
Each prints what it wrote; running it again changes nothing, and `--dry-run` writes nothing.

**In one project.** Add this line to the project's `AGENTS.md` and commit it, so a
teammate who clones the project gets Buddy too:

```text
Forge: start Buddy. Before the first answer, run the forge:boot skill and follow the boot entry it returns.
```

Codex reads `AGENTS.md` itself and runs the skill. Claude Code does not read
`AGENTS.md`; the plugin's boot hook looks for the same line and injects the boot. Where
the line is absent, the hook does nothing, so the plugin costs a project without it only
the skill listing. Buddy's first reply opens with a line naming the machine, the time and
the folder; if the assistant answers without it, Forge did not load.

**In every session (the personal extension).** The switch differs by host. On Claude
Code, set `buddy: every-session` in `~/.config/forge/user.yaml`. On Codex, append the
activation line (the one above) to `~/.codex/AGENTS.md`; it started the boot with the
user scope in the checks. On either host, `user.yaml` also names
your user repository, the folder of personal context (who you are, how you work, open
topics) that carries across projects; the layout is
[the user-scope convention](../framework/user-scope.md).
In plugin mode the user scope resolves whenever `user.yaml` configures one, with the
line or with the switch.

**Reads outside the project.** A plugin user needs two allow rules so the boot's reads do
not prompt on every start: `Read(//<plugin root>/**)` for the checkout or cache that
holds the plugin, and, with a user scope, `Read(//<user repo>/**)` for the user
repository. The proof showed prompts without them. `additionalDirectories` is not a
substitute: it also loads that folder's `.claude/skills` and `.claude/agents`.

**Known limits.** A Claude Code session in the cloud works from committed files only
and starts without the machine's plugin. If `env.FRAMEWORK_DIR` is set in
`~/.claude/settings.json`, the boot's status probe reads that checkout instead of the
plugin root; unset it. The activation line starts the boot for the session you open;
a subagent a session spawns does not need its own.

## Updating

Claude Code and Codex update the plugin through their own commands (`claude plugin
marketplace update forge` and `claude plugin update forge@forge`; `codex plugin
marketplace upgrade forge`). Both answered "already at the latest version" when nothing
had changed; an update to a newer commit was not shown. A local marketplace on a Forge
checkout follows the checkout (`git -C ~/forge pull`) on Claude Code. Sessions already
running keep what they loaded.

## Removal

```bash
claude plugin uninstall forge@forge --scope user
claude plugin marketplace remove forge
codex plugin remove forge@forge
codex plugin marketplace remove forge
```

The host keeps its cache copies of a removed plugin for a while, and the marketplace
declaration it wrote to its settings goes with `marketplace remove`. The proof's
removal passed on Claude Code and left the host's settings as before. Remove the
activation lines and `buddy: every-session` yourself; they are your files. On Codex,
run `codex plugin list` with input from `/dev/null`. Both hosts' removal passed in the
checks; Codex also leaves entries in its `config.toml` (the marketplace, the plugin and
trust levels of the folders it ran in), which are the host's.

## OpenCode (the installer)

OpenCode has no plugin route. For it, `scripts/forge_install.py` installs Buddy in every
session of the machine (`--profile full-ai-integration --host opencode`), and
`setup-oc.sh` runs that command. OpenCode has no entry of its own yet; until it does, this
installer is what OpenCode uses, and nothing else of it is offered. It earlier served
Claude Code and Codex too; those paths were retired when the plugin proved out, and a
machine that still carries them is moved off with the installer of the Forge version
before this change: check that version out, run its `--remove`, then add the plugin.
That removal also unlinks the Git hooks it had linked into the Forge checkout and the
skill links it registered, and it prunes the folders it emptied; re-link a skill folder
of your own, and run `bash scripts/install-git-hooks.sh` in the checkout if you commit
there. The current installer refuses the `project` profile and the hosts `claude-code` and `codex`
with a message naming the plugin.

```bash
git clone https://github.com/NashEQify/forge ~/forge
python3 ~/forge/scripts/forge_install.py --profile full-ai-integration --host opencode \
  --user-repo ~/forge-context --create-user-repo --check
```

`--check` writes nothing: exit 0 means nothing would change, 1 means changes are
planned, 2 means a reported conflict or error. It lists every path: the machine setting
`~/.config/forge/user.yaml`, the selection record under `~/.local/state/forge/`, the `oc`
launcher in `~/.local/bin` and `~/.config/forge/opencode.jsonc`. Start OpenCode with
`oc`; that directory must come before other commands of the same name on `PATH`.
`--user-repo PATH` names the user repository (an existing folder, or with
`--create-user-repo` a new one with `context/user/profile.md` and `navigation.md`);
once the machine setting names it, later runs need no `--user-repo`. Managed-file
hashes protect ownership: unknown files, edited managed files and unexpected links stop
the installation, and `--remove` takes out exactly what it wrote and stops, naming the
file, if you changed one.

Update with `git -C ~/forge pull`; each `oc` start runs `forge_install.py --refresh`
first, which brings the installed entries up to the checkout's commit and never stops
a start (it skips with one line when it may not run). `oc` refuses to start while a
tracked file other than Markdown has uncommitted changes in the checkout.

## The coordinated maintenance path (changing Forge itself)

This path is for people who change Forge's own sources on the machine they work on.
It is opt-in: add `--coordinated` (with `--user-repo`) to the OpenCode
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
the launcher, substitute that exact ID:

```bash
~/.local/bin/oc --forge-validation-operation "<operation-id>"
```

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
