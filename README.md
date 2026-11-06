# Forge

Forge is a discipline for software development with AI coding agents (Claude Code
and Codex). It helps single developers in particular build complex software with an
agent: you start from an idea as in vibe coding, and the result gets the quality that
specs, tests and review give.

It is a collection of skills, roles and workflows in two areas:

- **Craft:** the engineering practices themselves: specifications, test design,
  implementation briefs, code review with verified findings, root-cause fixing,
  architecture, security, UX and documentation.
- **Workflow control:** the steering around the craft: sizing a change, scoping,
  briefs that carry the approved acceptance criteria word for word, delegation to a
  coding agent and to separate reviewers, evidence before "done", and continuing a
  change across sessions.

It is written for developers who use Claude Code or Codex for real software work.
Forge is plain instruction text that the agent reads, plus small helper scripts that
check specific things (task and plan files, workflow state). The instructions carry
the method; the scripts do not enforce it.

## What is in it

- **Buddy**, the role you talk to: in a project with Forge it replaces the assistant's
  default agent. It sizes the request, runs the matching workflow,
  hands code to a coding agent and review to separate agents, and reports what the
  evidence shows.
- **Workflows:** `build` (intent → spec → plan → implementation → review → fix →
  close), `fix` (root cause first), `review`, `research`, `solve` (for a problem whose
  solution is still open), `docs-rewrite` and `save` (record decisions and open work
  for the next session). [Runbooks](workflows/runbooks/navigation.md)
- **Skills**, among them spec authoring and the spec board, test design, adversarial
  test plans, the code review board, root-cause fixing, architecture review, API
  design, security hardening, UX authoring, frontend engineering, migration,
  shipping, and documentation with decision records. [Skill map](framework/skill-map.md)
- **Roles** for the agents a workflow dispatches: the coding agent, the tester, spec
  and code reviewers (adversary, security, data, API contract, reliability and others),
  and a chief that consolidates a board's findings. [Roles](agents/README.md)
- **Reasoning methods** for decisions inside development, also usable alone: Frame
  (open the problem before choosing), Bedrock (drill assumptions to first principles)
  and Council (several isolated perspectives on one decision).

You can use the whole workflow or a single part of it: ask Buddy for a spec board on
your spec, a code review of your branch or a Council on a design choice, and only that
runs.

**Discipline in proportion.** The full workflow is for complex changes. A small change
gets a short path: Buddy picks it from what a mistake would cost, how
easily it is undone and how sure it is, and the reply says who built the change and
who checked it. Changes that touch authorization, secrets, data migrations, public
contracts or live systems never take the short path.
[Choosing the path](framework/direct-eligibility.md#choosing-the-path)

## Where it comes from

The idea, the concept and how the parts work together are Forge's own: Buddy as the
one role you talk to, the workflow control around the craft, the project goal every
step works from, and the hand-over between skills, roles and workflows under one set
of rules (the approved goal, your go-ahead for consequential steps, evidence before
"done", effort matched to the stakes).

For the individual practices, Forge took the best of what these projects published
and built it into that design, some of it word for word, under their licenses and
with credit:

- [Superpowers](https://github.com/obra/superpowers) (Jesse Vincent): subagent-driven
  development, systematic debugging, verification before completion.
- [agent-skills](https://github.com/addyosmani/agent-skills) (Addy Osmani): engineering
  skills from security to shipping.
- [BMAD-METHOD](https://github.com/bmad-code-org/BMAD-METHOD): right-sized planning,
  approved acceptance carried verbatim, review triage.
- [spec-kit](https://github.com/github/spec-kit) (GitHub): the specification as the
  source of the code.
- [skills](https://github.com/mattpocock/skills) (Matt Pocock): small engineering
  skills for architecture, diagnosis and design interviews.

[What came from where](framework/adopted-methods.md) · [NOTICE](NOTICE)

## Install and remove

You need Claude Code or Codex, Git, Bash (Linux, macOS, or WSL on Windows) and Python
3.10 or newer with PyYAML (`python3 -m pip install pyyaml`). The boot hook calls plain
`python3`, so PyYAML must be available to that interpreter, not only inside a virtual
environment.

Forge is one plugin for both hosts. Add it from the Forge repository:

```bash
claude plugin marketplace add NashEQify/forge
claude plugin install forge@forge --scope user
```

On Codex the commands are `codex plugin marketplace add NashEQify/forge` and `codex
plugin add forge@forge`. The plugin adds eleven skills and six read-only roles; it does
not start Buddy by itself.

**Buddy in one project.** Commit this line in the project's `AGENTS.md`:

```text
Forge: start Buddy. Before the first answer, run the forge:boot skill and follow the boot entry it returns.
```

Start your assistant in that folder. Buddy's first reply opens with a line naming the
machine, the time and the folder; if the assistant answers without it, Forge did not
load. On the first start Buddy writes the project's goal into `intent.md` with you;
every later step works from it. A teammate who clones the project gets the same
behaviour once they add the plugin.

**Buddy in every session (optional).** On Claude Code, set `buddy: every-session` in
`~/.config/forge/user.yaml`, which also names a folder of personal context (who you are,
how you work, open topics) that carries across projects. On Codex, add the same
activation line as above to `~/.codex/AGENTS.md`; the personal-context folder is still
named in `user.yaml`.

**Remove:** `claude plugin uninstall forge@forge --scope user` and `claude plugin
marketplace remove forge` (on Codex `codex plugin remove forge@forge` and `codex plugin
marketplace remove forge`), then delete the `AGENTS.md` line (and the line in `~/.codex/AGENTS.md`) and the `buddy:` setting.

Checked so far: Claude Code on two machines, one with a local checkout as the
marketplace (boot, roles, resume, knowledge maintenance, removal) and one with the public
marketplace; Codex with the public marketplace (boot, user scope, knowledge maintenance).
An update to a newer version is not checked yet. A Claude Code session in the
cloud works from committed files only, and plugin users need two `Read` allow rules to
avoid a prompt on every boot. OpenCode has no plugin; it installs through
`scripts/forge_install.py --profile full-ai-integration --host opencode`.

The [installation guide](architecture-documentation/05-installation.md) has the details,
the allow rules and the OpenCode route.

## A run on real code

A change to a long-running server process with an existing suite of about 1,100
tests: its main loop had slowed down and its memory grew every day. The fix needed a
rework of the loop and a migration of live data. Forge sized it for the full workflow.
What happened:

- **Spec review before code.** The first pass of the spec board (six reviewer agents
  reading the spec, each from its own angle, plus one that consolidates) found two
  critical and ten high issues, among them when written data becomes visible and how
  the service stays up until delivery. The spec was rebuilt, and an urgent fix was
  split off as a first delivery of its own.
- **The urgent fix.** Three reviewers checked it. Three planned parts turned out
  unreachable after the first one and were dropped instead of patched. It was tried on
  a copy of the live data first, then went live with a 4.5-minute outage; the loop's
  cycle went from 280–376 s to 52–71 s.
- **The rework.** Before the brief, an architecture check found three statements in
  the spec that did not match the code. After implementation, a code review board of
  six reviewers found three high-severity defects; two of them would only have shown
  up live, after a rollback. The migration was proven on a copy of the live data
  before the cutover.
- **What did not go well.** An owner's decision to drop a feature was not carried
  through the spec, so its leftovers drew three review findings later. The plan allowed
  two fix passes; a third was needed. Test skeletons written before the code had
  oracles that were never checked, and eleven tests failed for test reasons. Each of
  these became a proposed change to Forge's workflow text.
- **Cost**, counted from the session transcripts up to the third fix pass: about seven
  hours of build work, 45 agent runs and about 13 million tokens.

A one-line fix takes the short path instead: Buddy or the coding agent makes it, the
tests run, and the reply says who checked it.

## Limits

- Forge gives the model methods and checks. It cannot guarantee that a model follows
  every instruction or judges correctly, and reviewers can share a wrong assumption.
- It costs time. Buddy reads the project's goal and context at the start of every
  session, so even a quick question takes longer than a bare prompt. Independent review
  adds more; it is worth it where a mistake would be hard to catch or undo.
- Hosts differ in what they load and allow. The installer checks what it can; whether a
  fresh session actually loaded Forge is something to verify, not to assume.
- One `intent.md` per repository. Forge is pre-1.0: file layouts and commands can still
  change between versions.

## Read more

| You want to… | Read |
|---|---|
| See how the parts fit | [Overview](architecture-documentation/01-overview.md) |
| Build or fix software with Forge | [Software development](architecture-documentation/06-usage-workflows.md#software-development) |
| Use the reasoning methods | [Reasoning methods](architecture-documentation/06-usage-workflows.md#general-reasoning) |
| Work with Forge day to day | [Daily use](architecture-documentation/13-operational-handbook.md) |
| Check host support | [Host integrations](architecture-documentation/07-tool-integrations.md) |
| Change Forge itself | [Architecture](architecture-documentation/02-architecture.md) · [Maintainer guide](architecture-documentation/08-development-and-maintenance.md) |

All pages: the [documentation hub](architecture-documentation/README.md).
Contributions: [CONTRIBUTING.md](CONTRIBUTING.md). Security: [SECURITY.md](SECURITY.md).
Community: [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md). [MIT license](LICENSE).
