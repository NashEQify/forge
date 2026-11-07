# 05 — Installation

## Ask your agent

```text
Install Forge from github.com/NashEQify/forge
```

Your agent follows [INSTALL.md](../INSTALL.md) in the repository: it checks the prerequisites, adds the plugin on
each host it finds (Claude Code, Codex; OpenCode needs no plugin step), asks whether Buddy runs in this project only or in every session (and, for
every session, which folder holds your personal context, creating it on your yes), and runs
`scripts/forge_setup.py`, which writes the activation line, the user switch, the `Read` allow rules and OpenCode's
boot skill. Then it
checks that a fresh session opens with Buddy's orientation line. Nobody edits a file by hand. Once installed, the
`forge:setup` skill changes the scope later or removes Forge, and the plugin's other skills offer it once when they
run where Buddy is off.

What the live proof showed: Claude Code as the agent, on a machine with Forge taken off, installed the plugin for
Claude Code and Codex from that one request, asked the scope question, set up each scope, changed it back, made the
offer once, and removed Forge again through the agent, with fresh sessions checked after each step. Not shown: Codex
as the agent receiving the request, a fresh Codex session after the setup, the desktop apps, and macOS or WSL.

The rest of this page is the reference: what the agent runs, and how to do it by hand.

## The plugin

Forge reaches Claude Code and Codex as one **plugin**. The plugin carries the skills,
the boot hook and the framework tree; two small switches turn Buddy on: one line in a
project's `AGENTS.md` (Buddy in that project), or one setting in your user file (Buddy
in every session). OpenCode has no plugin, but the same two switches reach it through a
boot skill the setup writes ([OpenCode](#opencode), below).

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

- Claude Code, Codex or OpenCode. Host applications and model access are separate from Forge.
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
user scope in the checks. On OpenCode, the activation line goes into
`~/.config/opencode/AGENTS.md` ([OpenCode](#opencode)). On every host, `user.yaml` also names
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
checkout follows the checkout (`git -C ~/forge pull`) on Claude Code, and OpenCode's
boot skill reads the Forge folder it names in place. Sessions already running keep what
they loaded. Changing Forge's own sources on a machine whose sessions read them follows
[installation activation](../framework/installation-activation.md).

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

## OpenCode

OpenCode has no plugin, but it reads a project's `AGENTS.md` itself (walking up from the
folder) and a global rules file `${XDG_CONFIG_HOME:-~/.config}/opencode/AGENTS.md`, and it
lists skills from `${XDG_CONFIG_HOME:-~/.config}/opencode/skills/`. `forge_setup.py` uses
these, so the same switches as on Claude Code and Codex start Buddy: the project's
activation line, or for every session the activation line in OpenCode's global
`AGENTS.md`. With `opencode` on `PATH`, `project` and `every-session` write the boot skill
`forge:boot` (`opencode/skills/forge-boot/SKILL.md`), a short file that names a Forge
folder and the boot-entry command. That folder is the one the setup ran from; when that
is Claude Code's versioned plugin cache, it is Codex's stable plugin folder if Codex has
the plugin, else the versioned folder, and then the setup is run again after a plugin
update (`status` reports the folder chosen); `every-session` also writes the
global line, `every-session --off` takes the line out and keeps the skill, and `remove`
takes out both. No OpenCode JSON config is edited. The skill points at a Forge folder:
one found for Claude Code or Codex serves; on a machine with only OpenCode, clone Forge
(`git clone https://github.com/NashEQify/forge ~/forge`) and run
`python3 ~/forge/scripts/forge_setup.py`. `--host opencode` limits the host files a run
writes to OpenCode's; `every-session`, its `--off` and `remove` still write the shared
machine setting `~/.config/forge/user.yaml`, whose switch Claude Code reads too. An
edited or foreign `forge-boot` skill stops the setup with its path, and `remove` keeps an
edited one and names it. The check: `opencode run "hi"` in the project folder; the reply
opens with Buddy's orientation line. `opencode debug skill` lists `forge:boot` without
starting a model.

Next: [Host integrations](07-tool-integrations.md) · [Troubleshooting](12-troubleshooting.md).
