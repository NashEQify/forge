# 10 — Human Guide

> **Audience: human readers** — maintainers, OSS contributors, curious
> engineers. A prose introduction, storyline, motivation. Coding agent →
> see [`09-agent-guide.md`](09-agent-guide.md).

## What is this about?

Imagine you work as a **single-person engineering team** on half a dozen
projects in parallel — memory infrastructure for a personal AI assistant,
a few frontend apps, a bit of sysadmin work, a handful of life topics.
You want to work with AI agents — one for code writing, one for
architectural sparring, several for multi-perspective reviews.

The problem: each project repository would otherwise have its own Buddy,
its own skills, its own conventions. Drift is guaranteed. On top of that,
you use Claude Code **and** OpenCode in parallel — both need the same
personas and skills, otherwise the methodology has to be maintained
twice.

`forge` is the answer to this. A **methodology repository**
that holds the Buddy definition, skills, workflows, personas, and hooks
**once** and makes them available to all consumer repositories and agent
harnesses.

## The central idea

Three layers, clearly separated:

1. **Methodology (`agents/`, `framework/`)** — tool-neutral.
   What Buddy is, how he thinks, what he can do, when he is allowed to do
   what. Single source of truth.

2. **Adapter (`orchestrators/<name>/`)** — a thin layer per agent
   harness that translates between harness-specific discovery / hook
   mechanics / tool vocabulary and the harness-neutral methodology.
   Today: Claude Code in full, OpenCode reduced, Cursor planned.

3. **Consumer repositories** (e.g. `~/projects/BuddyAI`,
   `~/projects/personal`) — they use the methodology via
   `--add-dir $FRAMEWORK_DIR` (Claude Code) or via `OPENCODE_CONFIG`.
   **No re-implementation.**

When you change something about Buddy, the change is immediately active
in all repositories and under both harnesses — at the next session
start.

## Why mechanical enforcement?

Anyone who has worked with AI agents knows the pattern: you write a
convention into the system prompt, the agent sticks to it for the first
few turns, and after 50 turns the convention is completely forgotten.
Drift is unavoidable as soon as the rule lives only in the prompt text.

The framework attempts to anchor every important rule **mechanically**:
- Path whitelist as a hook (PreToolUse blocks; the agent simply cannot
  write anywhere else).
- Frozen zones as a hook (history and archive are read-only).
- Pre-commit hook with 12 checks (plan-validate, skill frontmatter,
  commit convention, etc.).
- Frontmatter validator (a skill-map without the standard frontmatter is rejected).
- Generator + validator hook for drift-prone indices.

What cannot be checked mechanically (content quality, spec
completeness, whether a new skill is genuinely standalone) remains a
matter of **spec-board discipline** — multiple personas review in
parallel, a chief consolidates. That is the second pillar: *hooks catch
schema drift, reviews catch content drift. Both are needed.*

## How did this come about?

The framework grew as a response to recurring drift problems that
appeared in vanilla Claude Code sessions:

- **Anchoring during multi-perspective review:** Buddy spawns three
  reviewers, reads the first one, and gets coloured by it. Several
  architectural iterations were needed to mechanically anchor the
  anti-anchoring discipline (Buddy = dispatcher, chief-only-read) as a
  Tier-0 invariant.
- **Skip-pattern at pre-delegation:** "implement feature X" was
  delegated to sub-agents without complete constraints. The
  pre-delegation non-negotiable model + the
  `delegation-prompt-quality.sh` hook arose as a fix.
- **Skill-class inflation:** an organically grown four-class division
  (workflow / capability / utility / protocol) drifted over months. An
  architectural-council decision consolidated it onto a single-class
  model with an orthogonal `invocation` axis.
- **Cross-repo double-maintenance:** several consumer repositories had
  their own Buddy definition, their own skills. The adapter
  architecture with the `--add-dir` pattern arose to enforce a single
  SoT.

## Storyline of a typical session

You open a terminal and type `cc framework`. Bash starts the `cc`
script:

1. **Resolve the framework path** (`$FRAMEWORK_DIR` from env, default
   `~/projects/forge`).
2. **Check symlinks** (`~/.claude/agents` and `~/.claude/skills` must
   point at the framework — otherwise the personas would not be
   discovered).
3. **Scope routing** (the `framework` argument means: cd into
   `$FRAMEWORK_DIR`).
4. **Start Claude Code** with `--add-dir $FRAMEWORK_DIR` and
   `--agent buddy`.

Claude Code finds `.claude/agents/buddy.md` (the wrapper), which loads
the real Buddy files (`agents/buddy/soul.md`, `operational.md`,
`boot.md`). Buddy runs his **boot sequence**:

- ORIENT: determine date / hostname / pwd
- RESOLVE: look for `intent.md` in CWD (or upwards)
- ROUTE: determine the context path
- LOAD: `values.md`, `profile.md` (user scope), `boot-navigation.md`
- RESUME: read `session-handoff.md`, run `plan_engine --boot` if needed
- GREET: short greeting in Buddy's style

Buddy is now in the picture. You say "I want to fix the bug in
src/foo.py".

Buddy:
- recognises that this is **ACTIONABLE** (a substantive imperative,
  not trivial).
- classifies it as a **fix workflow**.
- writes a **plan-block** ("Scope: src/foo.py + test, Agent:
  main-code-agent, Route: fix-Workflow Phase Specify, expected
  artefacts: fix diff + failing test going green").
- self-reviews the plan (scope check, instance-vs-class,
  rationalisation reflex).
- triggers Phase Specify with the `root_cause_fix` skill (Phase A:
  symptoms → hypotheses → drill).
- writes a **test plan** that reproduces the bug.

In Phase Execute, Buddy delegates to `main-code-agent`. The sub-agent
implements the fix, makes the test pass, and returns a summary.

Buddy reads **no code** — only the return summary plus the code diff,
and only if needed for the next decision.

In Phase Verify, Buddy triggers `code_review_board L1`. Two reviewer
personas (`code-review` multi-axis + `code-adversary`) review in
parallel. `code-chief` consolidates. Buddy reads **only the chief
signal**.

On PASS: Phase Close with `task_status_update → done`, commit. The
pre-commit hook runs (12 checks). On BLOCK: Buddy fixes, then makes a
new commit attempt.

That is what a typical session looks like. The framework gives you the
discipline without you having to rewrite it by hand every day.

## What sets this apart from?

### Skill-bag style (skills are slash-commands, no orchestrator above)

A number of very good agent-skills repositories follow the model: 15-25
skills as directly callable slash-commands, each skill with its own
anatomy (frontmatter, process, anti-rationalisation, verification). The
user triggers `/spec`, `/plan`, `/build`, `/test`, `/review`, `/ship`.
The skill runs and is done.

The model is very good for single-repo / per-task work. It does **not**
solve:

- **Anchoring during multi-perspective review.** When the user calls the
  N reviewers themselves one after another and reads along, every
  output read colours the next ones. Intentic solves this via the
  Buddy = dispatcher invariant (CLAUDE.md §1) plus
  `_protocols/dispatch-template.md` and `_protocols/context-isolation.md`.
- **Pre-delegation leaks.** Skill-bag puts discipline on the user's
  shoulders. Intentic makes it a Tier-0 invariant (CLAUDE.md §3) plus
  the `delegation-prompt-quality.sh` hook (which warns at <200
  characters).
- **Cross-repo drift.** Skill-bag gets installed per repo. Intentic
  exports via `--add-dir $FRAMEWORK_DIR` — one SoT, N adapters, nothing
  vendored.
- **Long-running coherence.** Skill-bag thinks per skill call. Intentic
  has `session-handoff` + `plan_engine` + `workflow_engine` as a
  persistence layer across sessions.
- **Orchestrator persona.** Skill-bag has none. Intentic has **Buddy**
  with a RECEIVE/ACT/BOUNDARY phase model, routing table, persist gate.
- **Architectural Council.** Skill-bag has none. Intentic spawns 3-4
  council members in parallel, context-isolated, with a briefing file
  and a synthesis output.
- **Multi-stage workflow phases.** Skill-bag has the lifecycle implicit
  (the slash-commands are the stages). Intentic has an explicit
  five-phase model (specify / prepare / execute / verify / close) for
  producer-class workflows.
- **Mechanical hook layer.** Skill-bag has optional session hooks.
  Intentic has 13 active hooks: PreToolUse BLOCK for path whitelist +
  frozen zone, pre-commit with 12 checks.
- **Anti-inflation.** Skill-bag allows "more skills = better". Intentic
  requires a `Standalone-justification` block for every new skill +
  spec-board L1 review + pre-commit validator.

**When skill-bag is the better fit:**
- One repo. No multi-repo sharing need.
- Per-task speed > long-running coherence.
- Slash-commands are the desired mental mode.
- No need for council or multi-stage boards.

**When forge is the better fit:**
- Multiple repos with shared discipline.
- You have already felt the anchoring / pre-delegation / drift
  problems.
- Architectural decisions need irreversibility rigour.
- Compounding coherence across weeks matters more than per-task speed.

### LangChain / Autogen / generic agent frameworks

`forge` is **not a generic agent framework**. It does not
model "how does one agent talk to another via JSON". It models "how
**my** Buddy thinks, what he is allowed to do, who helps him". It is
personal, not generic.

External lifts are adopted selectively (the `addyosmani/agent-skills`
pattern for skill anatomy + anti-rationalisation, the
`mattpocock/skills` pattern for strict glossary + deletion test), but
not as wholesale adoption.

### Claude Code's built-in sub-agents

Claude Code has built-in sub-agent discovery (CLAUDE.md,
.claude/agents/). `forge` builds on top of that, but adds:
- A **methodology layer** (skills, workflows, protocols) above the
  agents.
- Multiple **boards + a council** instead of single reviewers.
- **Mechanical hooks** instead of just prompt-text conventions.
- **Cross-adapter consistency** (Claude Code + OpenCode + planned
  Cursor).

### Classic spec-driven development

Conventional spec-driven development is linear: spec → code → test →
done. `forge` models specs as a **multi-perspective review
subject**: after writing comes the spec-board with 4-7 reviewer
personas all looking at the spec in parallel, a chief consolidates, a
convergence loop closes NEEDS-WORK findings. That is markedly closer to
"software architecture review meeting", implemented for a single user.

## Where does what live?

The most important files in one column, from specific to general:

```
CLAUDE.md / AGENTS.md            — Tier 0, invariants
agents/buddy/soul.md             — Buddy's personality
agents/buddy/operational.md      — Buddy's phases
agents/buddy/boot.md             — Buddy's start sequence
framework/skill-anatomy.md       — Format standard for skills
framework/process-map.md         — Workflow routing
framework/skill-map.md           — Skill inventory
framework/boot-navigation.md     — Boot index
skills/<name>/SKILL.md           — Per skill
workflows/runbooks/<name>/WORKFLOW.md — Per workflow
agents/<persona>.md              — Per persona
orchestrators/<harness>/         — Adapter layer
scripts/                         — Engines (plan_engine, workflow_engine) + generators
```

Reader-journey lookups live in the `navigation.md` files under the
respective top-level-3 directories — introduced 2026-05-01.

## The most important disciplines

In order of importance:

1. **Buddy = dispatcher in boards.** If Buddy reads along in a board,
   he colours the findings — the multi-perspective guarantee is lost.
2. **Pre-delegation non-negotiable.** A plan-block or gate file before
   every sub-agent call. Constraints are materialised, not handed
   over implicitly.
3. **Single-class skill model.** All skills equal. Variation along the
   `invocation` axis. No class inflation.
4. **Stale cleanup in the same commit.** When something is archived,
   fix all references in one atomic commit.
5. **Frozen zones.** History and archive are WORM. Mechanically blocked.
6. **Generator + validator.** Generate drift-prone indices; the
   validator checks idempotency.
7. **Source grounding.** Before any edit or consistency assertion: read.
8. **Persist gate.** A status change without a context update is half
   done.

## What the framework is not

- **Not a generic AI-agent framework clone** (LangChain, Autogen).
- **Not a replacement for Claude Code / OpenCode** — adapter-based, not
  re-implemented.
- **Not a marketplace product** — open source as a reference, not as a
  generic framework. External lifts are selective, not wholesale
  adoption.
- **Not a multi-user setup today** — single-user defaults run all the
  way through (paths, whitelist, symlinks). Generalisation would be
  follow-on work.

## If you want to contribute

Today this is more of a single-user project, but the setup is open
source. Contribution requires (as of May 2026, not all in place yet):
- A LICENSE file (probably MIT)
- CONTRIBUTING.md with conventions
- A CI pipeline (today no auto CI, only pre-commit)
- Issue / PR templates

Until then: the pre-commit hook is the primary quality gate, and all
changes follow the standard skill format (SKILL-FM-VALIDATE BLOCK).

## Next steps

- Setup via [`05-installation.md`](05-installation.md).
- Practical workflows in [`06-usage-workflows.md`](06-usage-workflows.md).
- Tool-specific setup details in [`07-tool-integrations.md`](07-tool-integrations.md).
- For issues: [`12-troubleshooting.md`](12-troubleshooting.md).
- Source-grounding trace for individual statements:
  [`11-source-grounding.md`](11-source-grounding.md).
