# ADR-001: Claude-Code skill-wrappers are a generated derived artifact, with an implicit-plus-override inclusion rule

## Status
Accepted

## Date
2026-05-19

## Context

Claude Code discovers skills via thin wrapper files under
`.claude/skills/<name>/SKILL.md` — frontmatter (`name`,
`description`) plus a pointer body to the orchestrator-neutral SoT
in `skills/<name>/SKILL.md`. Only skills with such a wrapper enter
the available-skills system-reminder, i.e. only they are proactively
invocable via the `Skill` tool.

These wrappers had been hand-authored. Consequences observed:

- New skills shipped without a wrapper and were silently
  undiscoverable (the same skill is present and correct in
  `skills/`, but invisible to the tool).
- Hand-authored wrapper `description`s drifted from the source
  skill `description`s once the source was later improved — the
  wrappers became stale copies with no mechanism detecting it.
- The set of which skills had wrappers was ad-hoc: a mix of
  user-facing and a few workflow-step skills, with no rule that
  explained the membership.

This is the framework's own "generator + validator" pillar not
being applied to one of its own structured artifacts. The
distribution path is also non-obvious: the global
`~/.claude/skills` symlink resolves to the **public OSS mirror**,
so wrappers reach consumer sessions only after the release-sync
propagates them — making "committed + generated" the only model
under which discovery works at all.

## Decision

1. **Wrappers are a generated derived artifact**, produced by
   `scripts/generate_skill_wrappers.py` (mirroring the existing
   `generate_skill_map.py` generator+validator pattern). Hand-edits
   are overwritten on the next run and flagged by `consistency_check`
   (check 10, wrapper-drift). Each generated wrapper carries a
   generation marker so the generator only ever deletes directories
   it provably authored.

2. **Single source of truth** for the wrapper `description` is the
   source skill's frontmatter `description` (token-normalized; block
   scalars collapse to one line, trigger tokens preserved). The
   wrapper never carries independent prose.

3. **Inclusion rule (Option C — implicit base + explicit override):**
   a skill is wrapper-eligible iff
   `status ∉ {archived, deprecated}` **and**
   `disable-model-invocation ≠ true` **and**
   ( `invocation.primary ∈ {user-facing, cross-cutting}` **or**
   `cc_wrapper: true` ) **and** `cc_wrapper ≠ false`.
   `cc_wrapper` is a new optional, override-only frontmatter field
   (absent ⇒ the implicit rule decides).

## Alternatives considered

- **A — explicit opt-in flag only.** Every wrapped skill must carry
  `cc_wrapper: true`. Rejected: re-introduces the exact "someone
  forgot to tag it" failure class this work exists to eliminate.
- **B — pure implicit (invocation semantics only), no override.**
  Rejected: silently drops workflow-step skills that have a
  legitimate standalone user-facing trigger, and offers no opt-out
  for noise cases; over-publishes with no escape hatch.
- **C — hybrid (chosen).** Self-maintaining for the common case
  (kills the failure class), explicit override for the genuine
  exceptions. Matches how the framework already layers
  `disable-model-invocation` / `relevant_for` over implicit rules.

## Consequences

- New skills are discoverable by construction; drift is mechanically
  detected, not noticed by chance.
- The first generator run intentionally rewrites the previously
  hand-authored wrappers to match current source — that diff is the
  drift correction, not a regression.
- Workflow-step skills with a real standalone-review use-case (e.g.
  the code-review board) are *not* wrapped under the implicit rule;
  re-including them via `cc_wrapper: true` is a deliberate,
  separately-evaluated decision (it may even warrant its own spec
  for a "review any existing code" mode) rather than an accident.
- All in-criterion wrappers are committed and reach the public OSS
  mirror via release-sync — accepted as the honest discovery
  surface, and in fact the only mechanism by which consumer repos
  discover wrappers given the symlink target.
- A residual robustness gap (generator crash on a symlinked orphan
  directory) is tracked as a separate hardening follow-up; it is
  fail-stop, not data loss.

Originating work: tasks 326 (mechanism), 325 (audit + override
follow-up), 327 (sibling task-schema generator+validator).
