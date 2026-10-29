# Forge

<img src="assets/vibeforge-logo.png" align="right" width="220" alt="Forge mascot: a furnace working at an anvil" />

**Bring an idea. Forge guides the work to the result you want.**

Forge is a guided process for building with AI. You describe your idea in plain words.
**Buddy**, Forge's guide inside your AI coding assistant, asks what matters, writes
down the goal with you, plans the work, has a coding agent build and test it, gets it
checked by a separate reviewer, and shows you the result with the tests behind it.
A small, reversible change can take a short path; a bigger one gets the structure it
needs.

Forge is made first for building software and small solutions: a script, a tool, an
app. The same guidance helps with a decision you need to get right, and when you
`save`, it keeps what you learned and what is still open, so the next session can pick
up where you left off.

Forge is for one person building with AI, "vibe coding" included: you say what you
want, and Forge keeps the work tied to that goal as it grows.

## What a run looks like

You: *"I want a small tool that sorts my holiday photos into folders by date."*

1. **Buddy asks what matters.** Which folder? What happens to photos without a date?
   Move the originals or copy them? Your answers become the goal and the
   checks that say when it is done. You approve them.
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
- **A second look.** The agent that builds is not the one that reviews. Buddy checks
  what the reviewer reports and decides what gets fixed; a question about your goal
  comes back to you.
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
and one of the AI coding assistants above; a chat window like ChatGPT is not enough.

```bash
git clone https://github.com/NashEQify/forge ~/forge
python3 ~/forge/scripts/forge_install.py --profile full ~/projects/my-app --check
```

The first command downloads Forge. The second only lists what Forge would add or
change; replace `~/projects/my-app` with your project folder (for a new idea, create an
empty one first). What the installer changes on your machine:

- **`full`** (software work) writes Forge's entries for the assistants you pick with
  `--host claude-code`, `codex` or `opencode`, or else for those it finds installed,
  and stops if it finds none; later runs keep that choice until you pass `--host`
  again. They sit in your home folder, so Forge's start entry is
  active in every session of those assistants, not only in this project. If you
  already have your own Claude Code hooks or `~/.claude/agents` folder, the installer
  stops and reports it instead of overwriting them.
- **`daily`** (knowledge and reasoning, no software tools) writes the start entries
  for Codex and Claude Code, whichever of them that choice covers, also in your home
  folder and also active in every session.

There is no uninstall command yet. When the list looks right, run the command again
without `--check`. The installer then asks for one acceptance check, and `cc` and `oc`
start only after it; the
[installation guide](architecture-documentation/05-installation.md#verification) walks
you through it, along with the `daily` profile, a folder for personal knowledge and
updating an existing installation. After that, start your assistant in the project
folder: `cc` for Claude Code or `oc` for OpenCode, the launchers the installer puts in
`~/.local/bin` (the guide says when to type that full path), or open Codex there. Buddy
greets you. Tell it your idea; it starts by writing the project's goal into a file
called `intent.md` with you.

## Limits

Forge is opinionated and pre-1.0. It gives the model methods and checks; it cannot
guarantee that a model follows every instruction or judges correctly, and reviewers can
share a wrong assumption. The full path costs more time and tokens than a quick prompt,
so use it where the stakes justify it. Even the short path costs more than a bare
prompt: Buddy first runs its start-up reads and checks, and a one-line fix still goes
to a coding agent and then to a separate check, so it takes several times as long as
a bare prompt, often minutes.

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
| Use Forge every day and keep context | [Daily use](architecture-documentation/13-operational-handbook.md) |
| See what Forge is and how its parts fit | [Overview](architecture-documentation/01-overview.md) |
| Think through a hard decision (the Frame, Bedrock and Council methods) | [Reasoning methods](architecture-documentation/06-usage-workflows.md#general-reasoning) |
| Build or maintain software | [Software development](architecture-documentation/06-usage-workflows.md#software-development) |
| Change Forge itself | [Architecture](architecture-documentation/02-architecture.md) · [Maintainer guide](architecture-documentation/08-development-and-maintenance.md) |

More routes: the [documentation hub](architecture-documentation/README.md).
Contributions: [CONTRIBUTING.md](CONTRIBUTING.md). Security:
[SECURITY.md](SECURITY.md). Community: [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).
[MIT license](LICENSE).
