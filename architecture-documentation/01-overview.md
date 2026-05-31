# 01 — Overview

> **A note on context:** Task IDs that appear in this documentation
> point to internal development tasks in consumer repos that exercised
> a particular mechanism while it was being built. They are
> traceability anchors for *why* a particular mechanism exists, not
> required reading and not authoritative for the framework itself.

## The loop, in one paragraph

You start a session, you talk to Buddy, the state survives the close.
That's the loop. The framework is what makes that loop survive at scale —
across multiple repos, across many sessions, across drift. It's an
opinionated methodology + tooling layer that sits on top of an existing
agent harness (Claude Code primary, OpenCode + Cursor supported) and
replaces "remember to" rules with mechanical enforcement.

## What's in the box

- A defined orchestrator persona ("Buddy") with a strict three-phase model
  (RECEIVE / ACT / BOUNDARY) and an explicit boot sequence.
- A skill anatomy that all skills must conform to —
  mechanically validated at commit time.
- Multi-perspective review boards (Spec-Board, Code-Review-Board, UX-Board)
  with configurable depth and chief-consolidation.
- An architectural Council with parallel context-isolated members for
  irreversible decisions.
- A workflow runbook system (8 active workflows, e.g. solve / build / fix /
  review / research / save) with explicit phase models.
- 3 hook scripts: `buddy-boot-inject` + `session-start-remote`
  (SessionStart) + `pre-commit.sh` (git pre-commit, 5 checks: 3 BLOCK
  + 2 WARN). All three are universally portable — git pre-commit runs
  on every harness, SessionStart works on CC-Terminal / claude-desktop
  / claude-web / Codex. An earlier CC-Terminal-only PreToolUse /
  PostToolUse / UserPromptSubmit layer was removed in favor of this
  portable set; discipline replicates via protocols.

It is consumed by other repos (code projects, personal-management
repos, infra/sysadmin setups) without re-installation: consumers point
at the framework via `--add-dir` (Claude Code) or `OPENCODE_CONFIG_DIR`
(OpenCode), and the framework methodology becomes active in their
session.

## Who is it for?

This framework targets people who:

- Run AI coding agents seriously and have already hit the **discipline
  drift** problem — conventions in system prompts get forgotten, sub-agent
  delegations skip constraints, multi-perspective reviews collapse into
  single-perspective.
- Want a **methodology layer** above the agent harness (not a replacement
  for it). Claude Code / OpenCode / Cursor remain the underlying runtimes;
  the framework adds shape on top.
- Maintain **multiple repos** that should share the same agent personas,
  skills, and conventions without duplicating them.
- Are willing to accept **opinionated constraints** in exchange for
  predictability — Single-Class skills, Pre-Delegation Non-Negotiable,
  Buddy-as-Dispatcher rule for boards. Not negotiable per session.

It is **not** for:

- Marketplace-style "skill libraries" you cherry-pick. The framework is a
  coherent system; lifts from external skill-libraries are punctual and
  source-attributed.
- Multi-tenant or enterprise setups. Single-user assumptions are baked in
  (auto-detected paths, single PROJECTS_DIR convention).
- Replacing a productive Claude Code / OpenCode setup. It augments, doesn't
  substitute.

## What problems does it actually solve?

### Problem 1 — Cross-repo duplication

You run several repos: a coding project, a personal-management repo
in `~/projects/personal`, a sysadmin/infra repo. Each starts wanting
Buddy. Each duplicates the persona definition. Drift follows.

**The framework's answer:** one Source-of-Truth (`agents/buddy/`,
`framework/`), N adapters (`orchestrators/<harness>/`, `.claude/agents/`,
OC-config). Consumer repos *point at* the framework — they don't vendor it.
A change to Buddy's `operational.md` is live in every consumer repo at the
next session start.

### Problem 2 — Drift between rule-text and behavior

You write a system-prompt rule. The agent follows it for 20 turns. By turn
50, it's forgotten. You discover a state-corruption that the rule was
supposed to prevent.

**The framework's answer:** discipline-as-
methodology anchored in protocols (`_protocols/dispatch-template.md`,
`context-isolation.md`, `mca-brief-template.md`, `plan-review.md`,
`evidence-pointer-schema.md`), backed by a thin universal-portable
reinforcement layer (git pre-commit 5 checks + SessionStart hooks).
The earlier CC-Terminal-only mechanical hooks (`path-whitelist-guard`,
`frozen-zone-guard`, etc.) were dropped because (a) they only fired on
one harness, breaking forge's adapter promise, and (b) several had
bypass vectors and gave false trust. Buddy's reasoning is the
load-bearing substrate; protocols carry the rules; hooks catch what's
mechanically cheap-and-cross-portable.

For methodology correctness (content-quality, completeness): mandatory
multi-perspective review via Spec-Board / Code-Review-Board / Council
with chief consolidator + anti-anchoring (Invariant 1).

### Problem 3 — Multi-perspective reviews collapse

You spawn three reviewer personas to look at a spec. You read the first
one's findings. By the time you read the third, you're anchored. The
"multi-perspective" was wishful.

**The framework's answer:** `CLAUDE.md §1` Buddy = Dispatcher. The
orchestrator doesn't read review files. Reviewers run context-isolated
(via `_protocols/context-isolation.md`). A `chief` persona consolidates;
the orchestrator reads only the chief signal and acts.

### Problem 4 — Sub-agent delegations skip constraints

You delegate "implement feature X" to a coding agent. You forget to mention
the cross-cutting constraint from spec Y. The agent produces something
that passes its own tests but breaks Y. You catch it in review, having
wasted a cycle.

**The framework's answer:** `CLAUDE.md §3` Pre-Delegation Non-Negotiable.
No sub-agent call without a Plan-Block (Scope, Tool, Alternatives,
Expected Artefacts) or a Gate-File. The orchestrator must materialize
constraints into an artefact before delegating. Brief shape is
codified in `_protocols/mca-brief-template.md` (with 6 standard
decision classes). An earlier `delegation-prompt-quality.sh` PreToolUse
hook warned when sub-agent prompts were under 200 chars; it has been
removed — discipline now lives in Buddy reading the protocol before
each dispatch.

### Problem 5 — Skill-class inflation

You start with a clean skill model. Over 30 sessions, "this is a
*workflow*", "this is a *capability*", "this is a *utility*", "this is a
*protocol*" — the taxonomy fragments. Some skills get mis-classified.
"Add a new skill" becomes the default reflex even when an existing skill
could absorb the use-case as a mode.

**The framework's answer:** Single-Class model. All skills are ontologically
equal. Variation lives in one orthogonal axis:
`invocation.primary` ∈ {user-facing, workflow-step,
sub-skill, hook, cross-cutting}. The 7-section anatomy is
mandatory and mechanically enforced (`scripts/skill_fm_validate.py`,
pre-commit Check 7 BLOCK).

A new skill must include a `Standalone` block arguing why it isn't a
mode of an existing skill. Spec-Board L1 reviews that argument.

## Why forge vs. directly-invoked skills (skill-bag model)

If you've seen "skill-bag" frameworks where each skill is a slash-command
the user invokes directly, you've seen the alternative model. It works for
short tasks. It does not survive the failure modes that show up at scale.

**The skill-bag model:**
- User triggers a skill → skill runs its workflow → done.
- No persona orchestration above the skills.
- Reviewer-skills exist, but the user reads each output as it arrives —
  no anti-anchoring discipline.
- Each repo carries its own copy of the skills.
- Pre-delegation hygiene is "remember to do it".
- Lifecycle is implicit (slash-commands map to phases).

**What forge adds (high-level):** orchestrator-persona above skills,
multi-perspective boards with chief-consolidation + anti-anchoring, mandatory
Plan-Block / Gate-File before sub-agent calls, a thin reinforcement-hook layer (git pre-commit + SessionStart),
single-source-of-truth + N adapters, generator+validator for drift-prone
indices, cross-session continuity via workflow-engine.

Detail comparison: §Why forge vs. directly-invoked skills (above).

## Trade-offs vs. lighter alternatives

The framework adds substantial process overhead (multi-perspective
boards, mandatory pre-delegation, mechanical hooks, cross-session
state). The honest trade-offs:

- **Multi-perspective review** costs 5-15k tokens per board and 10-30k
  per council. It earns its keep when it catches a spec-violation that
  would otherwise cost a day of re-work; on a typo-fix it is overhead.
- **Pre-delegation discipline** (mandatory plan-block / gate-file) adds
  one turn per substantive action. The win is "no agent call without a
  briefing"; the cost is more conversational round-trips.
- **Cross-session state** (workflow engine + state file + session-handoff)
  adds operational complexity; the win is that a multi-day build resumes
  where it stood. For one-shot tasks the overhead is unjustified.
- **Universal-portable hooks** (git pre-commit 5 checks + SessionStart
  for boot) impose a small setup cost (`scripts/setup-cc.sh` plus a
  git-hook symlink per consumer repo) and require investigating BLOCKs
  rather than bypassing. An earlier CC-Terminal-only PreToolUse layer
  has been removed.
- **Single-class skill model + anatomy validation** prevents skill
  inflation; the cost is a learning curve for skill authors.

Lighter frameworks (slash-command catalogs, "bag of skills" libraries)
are faster for short tasks. forge earns its keep on long, multi-
session work where coherence is the bottleneck.

## Next reading

- [02-architecture.md](02-architecture.md) — how it's structured.
- [04-core-concepts.md](04-core-concepts.md) — the 29 disciplines that
  define the framework.
- [10-human-guide.md](10-human-guide.md) — story, motivation, "what does a
  session actually look like".
- [13-operational-handbook.md](13-operational-handbook.md) — daily use,
  commands, methodology in practice.
