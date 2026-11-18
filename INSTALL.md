# Installing Forge — instructions for the AI agent

You are an AI coding agent (Claude Code, Codex, OpenCode or another) and the user asked you to install Forge from
this repository. Carry it out yourself: the user answers at most two questions and never writes or edits a file. Every
file the setup touches is written by `scripts/forge_setup.py`; you run commands and report.

Forge is one plugin for Claude Code and Codex. Installed, it adds its skills; Buddy, its orchestrator, starts only
where the user switches him on: in one project (a line in that project's `AGENTS.md`) or in every session (a setting
in the user's home). OpenCode has no plugin, but the same switches work there: the setup gives it a `forge:boot`
skill pointing at a Forge folder, and OpenCode reads the `AGENTS.md` lines itself.

## 1. Check the prerequisites

Run, each as its own call:

- `command -v claude`, `command -v codex` and `command -v opencode`: the hosts on this machine. Set Forge up for
  each one found; say which. None found: stop and tell the user Forge needs Claude Code, Codex or OpenCode.
- `git --version` and `python3 -c "import yaml"`: Git and Python 3.10+ with PyYAML, for the `python3` on `PATH`
  (the boot calls plain `python3`). PyYAML missing: offer `python3 -m pip install --user pyyaml` and run it on the
  user's yes.

## 2. Add the plugin

For Claude Code and Codex, each one found (these commands write the host's own configuration; where your sandbox
blocks them, ask the user to approve the command):

```bash
claude plugin marketplace add NashEQify/forge
claude plugin install forge@forge --scope user
```

```bash
codex plugin marketplace add NashEQify/forge
codex plugin add forge@forge
```

OpenCode has no plugin step.

## 3. Find the plugin's folder

`<root>` is the installed plugin's folder:

- Claude Code: `claude plugin list --json`, the entry `forge@forge`: its `readFromFolder` when present, else its
  `installPath`.
- Codex: `${CODEX_HOME:-~/.codex}/plugins/cache/forge/forge/local`.

It holds `.claude-plugin/plugin.json`. Either host's folder serves; the setup finds every host itself. OpenCode's
boot skill names the folder the setup runs from; when that is Claude Code's versioned plugin folder, it names Codex's
stable folder if Codex has the plugin, else the versioned folder, and then the setup must be run again after a plugin
update. On a machine with only OpenCode clone Forge first (`git clone https://github.com/NashEQify/forge ~/forge`) and
use `~/forge` as `<root>`.

## 4. Set Buddy up

This session started before the plugin existed, so the plugin's skills are not listed here yet. Read
`<root>/skills/setup/SKILL.md` and follow it: it asks the user project-only or every session (and, for every session,
where personal context lives), writes the activation line or the switch on each host, the `Read` allow rules
Claude Code needs and OpenCode's boot skill, and checks that a fresh session opens with Buddy's orientation line.

## 5. Report

Tell the user what was installed on which host, which scope is on, what the fresh-session check showed (or that they
should open a new session and look for the orientation line), and that a project's `AGENTS.md` line takes effect for
teammates once it is committed. In later sessions the same setup is reachable as the `forge:setup` skill ("switch
Buddy on for every session", "remove Forge").

## Remove

Read `<root>/skills/setup/SKILL.md` and run its removal (`forge_setup.py remove`) first, while the plugin's folder
still exists, then the host commands below. On OpenCode that removal is all there is (no plugin to uninstall); a
Forge clone made only for OpenCode stays until the user deletes it. Removal is these commands only; other files stay
as they are, as the setup skill says.

```bash
claude plugin uninstall forge@forge --scope user
claude plugin marketplace remove forge
```

```bash
codex plugin remove forge@forge
codex plugin marketplace remove forge
```

The user's personal-context folder stays; it is theirs. Hosts keep cache copies of a removed plugin for a while.
