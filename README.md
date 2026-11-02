# Forge

<img src="assets/vibeforge-logo.png" align="right" width="220" alt="Forge mascot: a furnace working at an anvil" />

**Forge helps you turn an idea into a solution you can try.** You work with
**Buddy** inside your AI coding assistant. Start by saying what you want to
change and why it matters to you.

- **Have an idea or a problem? Start with Solve.** Buddy explores possible
  solutions with you, helps you choose one, and works out how to tell whether
  it helped. You might end up with a new way of doing something, a script,
  or an app.
- **Already know what to build? Go straight to Build.** Give Buddy the feature
  and the behaviour you expect. Build takes it through implementation and
  testing. Solve hands off to the same Build workflow when you choose software.

When you `save`, Buddy records what you decided and what is still open so you
can pick up the work in the next session.

## What a run looks like

*"Every time my family asks for photos from a trip, I spend an evening finding
them. Can you help?"*

That's a starting point for **Solve**. Buddy asks how you look for photos and
what would make the next request easier. If a shared album in your existing
photo app does the job, you can try it on one trip. If you decide you want a
tool that copies photos into dated folders, you now have a feature for **Build**.
Here's how building that tool might go.

1. **Buddy asks what matters.** Where should the copies go? What happens to a
   photo without a date? Your answers become checks you can try on a few photos,
   including one that confirms the originals stayed untouched. You approve them.
2. **Buddy sizes the work from written facts:** the open points you would notice,
   what is hard to undo (moving your photos instead of copying them), and how much the
   change touches. How many steps the
   work gets follows from them. Had you asked for a slideshow of the photos as well,
   Buddy would offer to make that its own task.
3. **A coding agent builds it** from a written brief that carries your approved checks
   word for word, and tests the cases you named.
4. **A separate reviewer checks the change.** Each finding is verified before anything
   is fixed, and a fix goes at the cause.
5. **Buddy shows you the result with its evidence:** which tests ran and what they
   cover, plus any decision it took for you, with what it would cost if wrong and how
   to undo it.

A bigger change gets more stages on the way: a written spec, a design for a screen or
flow a person uses, drawn from your answers, an architecture when separately built parts must fit together (the few decisions they
all follow, and what is left open on purpose), a
plan whose tasks are checked against each other. A small one
skips what it does not need. Anything that touches security, data or live systems
always keeps its safeguards.
[The path, stage by stage](architecture-documentation/01-overview.md#software-development-from-intent-to-verified-result)

## What makes it different

- **Your goal leads.** Every agent works from the goal you approved. Buddy helps you
  sharpen the goal; it never makes one up.
- **Evidence, not claims.** "Done" comes with what shows it, such as the tests that
  ran, or Buddy says what actually holds. When a session goes wrong, Buddy can read
  its transcript and show line by line what happened, starting with whether Forge
  loaded at all.
- **A second look where it matters.** On a change with real uncertainty, the agent
  that builds is not the one that reviews. Buddy checks what the reviewer reports and
  decides what gets fixed; a question about your goal comes back to you. A wording fix
  or a small tested change gets a lighter check, and the reply says which.
- **You stay in charge.** Looking into a problem does not let Buddy change anything;
  publishing, live changes and deleting each need your go.
- **It remembers.** Knowledge and open work stay as files in your own folders, not
  in a hosted service.
- **It runs where you already work:** Claude Code, Codex or OpenCode. Forge is plain
  instruction text plus small helper tools; the tools check specific things, they do
  not enforce the methods.

[How Forge does each of these](architecture-documentation/04-core-concepts.md#how-forge-works)

## Get started

Setup happens in a terminal, the window where you type commands. You need Git,
Python 3.10 or newer with the PyYAML package, Bash (Linux, macOS, or WSL on Windows),
and Claude Code or Codex; a chat window like ChatGPT is not enough.

```bash
git clone https://github.com/NashEQify/forge ~/forge
mkdir -p ~/my-app
python3 ~/forge/scripts/forge_install.py --check ~/my-app
python3 ~/forge/scripts/forge_install.py ~/my-app
```

The first command downloads Forge into `~/forge`. The second creates a folder for your
project; `~/my-app` is an example name, and an existing folder works as well. The
project does not have to be software: notes for a decision or a piece of writing work
the same way. The third command lists the files Forge would write there and writes
nothing. The fourth installs Forge into that folder. Then start your assistant there:

```bash
cd ~/my-app
claude
```

Use `codex` instead of `claude` for Codex, or open a Claude Code session in that
folder in the Claude desktop app. Claude Code asks once whether you trust the folder;
Forge's settings apply after you say yes. Buddy greets you. Tell it your idea; it
starts by writing the project's goal into a file called `intent.md` with you.

There are two ways to install Forge:

- **`project`** (the default, the commands above): Forge in this one folder.
  *What changes:* only files inside that folder: Buddy's settings and role entries
  in `.claude/`, `AGENTS.override.md` for Codex, and a record of what it wrote. In a
  Git project these paths are listed in `.git/info/exclude`, so Git never commits
  them. Nothing in your home folder or in other projects changes. *Removal:*
  `python3 ~/forge/scripts/forge_install.py --remove ~/my-app` removes what it wrote;
  if you changed one of those files since, it stops, names the file and removes nothing.
- **`full-ai-integration`** (the big installation): Buddy in every session of your
  assistants on this machine, with a folder of your own for personal context, so
  what Buddy learns about you and your open work carry across projects. Preview it
  (`~/forge-context` is an example name for that folder; the installer creates it):

  ```bash
  python3 ~/forge/scripts/forge_install.py --profile full-ai-integration \
    --user-repo ~/forge-context --create-user-repo --check
  ```

  *What changes:* entries in your home folder: Claude Code's start hooks in
  `~/.claude/settings.json`, links in `~/.claude/skills` and `~/.claude/agents`,
  Codex's block in `~/.codex/AGENTS.md` and its roles and skills, the `cc` and `oc`
  launchers in `~/.local/bin`, and the machine setting `~/.config/forge/user.yaml`;
  in the Forge checkout it links Forge's Git hooks. In the terminal you then start
  Claude Code with `cc` instead of `claude`. OpenCode works only with this
  installation. *Removal:* `python3 ~/forge/scripts/forge_install.py --profile
  full-ai-integration --remove` takes out what it wrote and keeps your own settings,
  your context folder and your projects' own text; add `--check` to see the list first.

Choose one per machine: the project install refuses on a machine that has the big
installation, because Buddy already runs there in every session. The
[installation guide](architecture-documentation/05-installation.md) has the details.

To update Forge, run `git -C ~/forge pull`. That is the whole update, also for an
installation made with an earlier version: the next session start brings the installed
entries up to the new version. If you changed files in the checkout yourself, commit
or discard them first; the start names them.

## What it costs, and how you choose

At startup Buddy reads your goal, the project context and the rules that apply
throughout the work. It loads detailed instructions when a step needs them.
For example, a wording fix can stay with Buddy. When a change needs independent
review, Buddy loads the review instructions before choosing a reviewer.

These October measurements on a small Python project predate the change to
how Buddy loads instructions. Each case ran five times with Claude Opus 5.5
and GPT-6 Astra.

| Request | Claude Code with Forge | without | Codex with Forge | without |
|---|---|---|---|---|
| A quick question about the code | 14–27 s | 4–8 s | 29–43 s | 7–10 s |
| A one-line fix, quick path | 39–43 s | 17–32 s | 2–2.5 min | 40–44 s |
| The same fix, reviewed path | 2–3 min | 16–49 s | 4–5 min | 35–63 s |

A question gets no choice and no warning: the start-up is all it costs. For a code
change Buddy picks one of three paths from what a mistake would cost, how easily it is
undone and how sure he is:

- **quick:** a change that alters no behaviour, or a trivially reversible one its
  existing test shows. Buddy makes it himself and runs the test; nothing else checks it.
- **checked:** a small behaviour change an existing test covers. The coding agent
  builds it; Buddy reads the change and reruns the tests himself.
- **reviewed:** anything with remaining uncertainty or a wider effect. The coding
  agent builds it and a separate agent run checks it.

When he is unsure between two, he asks you in one sentence. You can always decide:
say "quick" or "reviewed" in your request, or write a standing preference into your
profile (`context/user/profile.md`). Security, data, contracts and live systems keep
their safeguards whatever you say. The reply should tell you who made the change
and who checked it. [Choosing the path](framework/direct-eligibility.md#choosing-the-path)

## Limits

Forge is opinionated and pre-1.0. It gives the model methods and checks; it cannot
guarantee that a model follows every instruction or judges correctly, and reviewers can
share a wrong assumption. Buddy spends time reading the project at startup.
In the October measurements above, even the quick path took longer than a bare
prompt. Independent review adds time and is worth asking for when a mistake
would be hard to catch or undo.

The project install reaches sessions that run on your machine. A Claude Code session
in the cloud works from the repository's committed files, so it starts without Forge.
Start Codex in the project root to refresh the installation. In a local CLI test,
Codex loaded the root's `AGENTS.override.md` even from a subfolder, but the
refresh looked in that subfolder and skipped the update.

## Where Forge's methods come from

Forge took everything it found worth stealing from these projects, openly, under their
MIT licenses and with credit, and rewrote or adapted it (some nearly word for word) to
answer to one set of rules: your goal, your go-ahead, evidence, and effort matched to
the stakes. Each project is known for something of its own:

- [Superpowers](https://github.com/obra/superpowers): subagent-driven development,
  systematic debugging, verification before completion.
- [Addy Osmani's agent-skills](https://github.com/addyosmani/agent-skills): a broad
  set of engineering skills, from security to shipping.
- [BMAD-METHOD](https://github.com/bmad-code-org/BMAD-METHOD): right-sized agile
  planning and review triage.
- [spec-kit](https://github.com/github/spec-kit): the specification as the source of
  the code.
- [Matt Pocock's skills](https://github.com/mattpocock/skills): small, sharp skills
  for architecture, diagnosis and design interviews.

What Forge adds is the one process: the methods work together, from your goal to the
evidence. This is not a ranking; each of these projects stands on its own. [What Forge took from each](architecture-documentation/01-overview.md#forge-and-the-frameworks-it-learned-from) ·
[Register of adopted methods](framework/adopted-methods.md) · [NOTICE](NOTICE)

## Read more

| You want to… | Read |
|---|---|
| Work out what to make from an idea | [Start with an idea](architecture-documentation/06-usage-workflows.md#start-with-an-idea) |
| Use Forge every day and keep context | [Daily use](architecture-documentation/13-operational-handbook.md) |
| See what Forge is and how its parts fit | [Overview](architecture-documentation/01-overview.md) |
| Think through a hard decision (the Frame, Bedrock and Council methods) | [Reasoning methods](architecture-documentation/06-usage-workflows.md#general-reasoning) |
| Build or maintain software | [Software development](architecture-documentation/06-usage-workflows.md#software-development) |
| Change Forge itself | [Architecture](architecture-documentation/02-architecture.md) · [Maintainer guide](architecture-documentation/08-development-and-maintenance.md) |

More routes: the [documentation hub](architecture-documentation/README.md).
Contributions: [CONTRIBUTING.md](CONTRIBUTING.md). Security:
[SECURITY.md](SECURITY.md). Community: [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).
[MIT license](LICENSE).
