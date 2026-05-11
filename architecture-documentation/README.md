# architecture-documentation/ — start here

Public-OSS architecture, installation, and usage
documentation for **forge** — opinionated workflows +
codified discipline patterns as a Skill + Discipline
Layer between human and LLM.
Created 2026-05-01.

This documentation is aimed at **two audiences in
parallel**:
- **Humans** (maintainers, OSS contributors, curious
  readers) — reader-journey-first, prose where it helps.
- **Coding agents** (Claude Code, OpenCode, Cursor) —
  source-path-bound, invariants explicit, do / don't
  explicit.

Where the same content serves both, it is consolidated.
Where the audiences diverge, there are two files (see 09
+ 10).

---

## Reader journey

Read in this order:

| Step | File | Time | Content |
|---|---|---|---|
| 1 | [`01-overview.md`](01-overview.md) | 5 min | What is it, for whom, what problem |
| 2 | [`02-architecture.md`](02-architecture.md) | 15 min | Tier model, Buddy, skills, workflows, boards, hooks |
| 3 | [`03-repository-map.md`](03-repository-map.md) | 5 min | Where what lives, quick orientation |
| 4 | [`04-core-concepts.md`](04-core-concepts.md) | 15 min | Skill anatomy, pre-delegation, single-class, cross-loading |
| 5 | [`05-installation.md`](05-installation.md) | 10 min | Setup for Claude Code / OpenCode / (Cursor) |
| 6 | [`06-usage-workflows.md`](06-usage-workflows.md) | 15 min | Solve / build / fix / save quickstart + patterns |
| 7 | [`07-tool-integrations.md`](07-tool-integrations.md) | 10 min | Adapter details per tool |
| 8 | [`08-development-and-maintenance.md`](08-development-and-maintenance.md) | 10 min | Engines, generators, hooks, tests, conventions |

Audience-specific (parallel, not sequential):
- [`09-agent-guide.md`](09-agent-guide.md) — for coding
  agents (start-here, invariants, do / don't).
- [`10-human-guide.md`](10-human-guide.md) — for human
  readers (storyline, motivation).

Practitioner level (methodology + daily use):
- **[`13-operational-handbook.md`](13-operational-handbook.md)**
  — if you only read one file, read this. Methodology in
  practice, what's operationally different,
  commands / triggers, what a typical day looks like, how
  consumer repos actually consume the framework.

Appendix:
- [`11-source-grounding.md`](11-source-grounding.md) —
  which claims are backed by which files.
- [`12-troubleshooting.md`](12-troubleshooting.md) —
  known pitfalls.

---

## Quick entry points

**"I just want to get started"** →
[`05-installation.md`](05-installation.md) quickstart
block.

**"I want to understand what the framework does BEFORE
using it"** → [`01-overview.md`](01-overview.md) +
[`10-human-guide.md`](10-human-guide.md).

**"What's different about this repo? How do I use it
day to day?"** →
[`13-operational-handbook.md`](13-operational-handbook.md).
That is the single-file entry into methodology practice.

**"I'm a coding agent in a session, what do I need to
know?"** → [`09-agent-guide.md`](09-agent-guide.md).
Tier-0 anchors: [`../CLAUDE.md`](../CLAUDE.md) /
[`../AGENTS.md`](../AGENTS.md).

**"I want to change or add a skill / workflow /
persona"** →
[`08-development-and-maintenance.md`](08-development-and-maintenance.md)
+ [`04-core-concepts.md`](04-core-concepts.md) §skill
standard skill format.

**"I want to use the framework in a new tool (Cursor,
another harness)"** →
[`07-tool-integrations.md`](07-tool-integrations.md)
§extending with a new adapter.

---

## Quality bar

- Concrete, not generic.
- Source-grounded: every technical claim has a file
  path.
- No invented features.
- Uncertainties marked transparently.
- Reflects the May 2026 state.

Source-grounding trace:
[`11-source-grounding.md`](11-source-grounding.md).
