# docs/dogfood-learnings/

Forensic capture of framework-relevant friction surfaced during real
work. The framework's own forge-feed — lessons accumulator that the
workflow narratives reference and that periodic triage promotes into
durable discipline.

## Two file shapes

- **`forge-feed.md`** — rolling accumulator for small entries. One
  bullet per friction, sequential `L-NNN` numbering, status field
  (`open` / `codified` / `dropped`). Default for everyday observations
  that pass the pre-write filter.
- **`<YYYY-MM-DD>-<title>.md`** — standalone deep-analysis report
  when a single incident warrants its own document (root-cause prose,
  multiple sub-issues, specific framework-change proposal). Example:
  `2026-05-14-brief-architect-overhead-on-small-fixes.md`.

When in doubt, write a `forge-feed.md` entry first. Promote to a
standalone file only if the entry grows past ~10 lines of substantive
analysis.

Either shape: written **direct on notice**, not buffered in consumer-
side `context/` files, not distilled only at workflow-close.

## Trigger

Workflow narratives (`workflows/runbooks/{build,fix,solve,research}/WORKFLOW.md`)
set the trigger at workflow start. When something during the work
suggests a framework change (failed assumption, brief drift, ad-hoc
convention, tooling gap, agent-protocol weakness), Buddy:

1. Runs the pre-write filter below.
2. If it passes → appends an entry to `forge-feed.md` immediately —
   close to the moment of observation, while context is concrete.
3. If it fails (2+ checks fire skip) → does not write. A missed
   lesson costs one recurrence; theater costs permanent confusion
   about which rules are load-bearing.

The workflow-close `workflow-retro` sub-check is a safety net only
(verify nothing fell through). Not the primary write mechanism.

## Pre-write filter

Six checks. **Drop the entry when 2+ fire skip.**

1. **Coverage-check** — `grep` what you would write against
   `skills/`, `agents/`, `_protocols/`, workflows, hooks. Hit? Either
   skip or update the existing SoT (pointer-edit), don't add a
   parallel entry.

2. **Judgment-vs-rule** — would codifying remove judgment that the
   orchestrator should keep? Rules that fire on every task become
   checklist-tick. If "a competent agent does this naturally when
   paying attention" → skip. The friction is attention, not absent
   rule.

3. **Frequency-of-fire** — how often does this pattern recur across
   workflows? Less than once per quarter → not durable enough for a
   rule. Worth a one-line example, not a framework edit.

4. **Proportionality** — match fix size to failure-evidence size.
   5min editing-overhead → new sub-skill = no. Multi-workflow
   recurrence → discipline rule = maybe. Two production bugs from
   one cause → structural gate = yes.

5. **Structural-vs-decorative** — structural pattern Buddy can apply
   broadly, or interesting prose about one situation? Decorative
   belongs in the commit message of the originating work.

6. **Already-implicit** — would a competent agent reach this
   conclusion without the rule? If yes, codification adds friction
   without signal.

### Forbidden categories (auto-skip — do not even open the filter)

Patterns that recurred in the 468 distillation and produced pure
theater:

- **Coverage-duplicating rules** for things `frame` step 4 (repo-
  check), `consistency_check` (stale references), or CLAUDE.md
  invariants (Stale-cleanup) already enforce.
- **Per-AC / per-step triage rules** replacing orchestrator
  judgment.
- **Estimation / prediction tools** (amendment-cost estimators,
  effort predictors, complexity scorers). Overhead exceeds signal.
- **"Always audit X" rules where X fires <1× per quarter.**
  Conditional audits OK; universal audits become checklist-tick.
- **Methodology prose lifted from a single research cluster** —
  bus-factor framings, license-analysis decorations, framework-
  evaluation aesthetic. Keep in cluster file; do not promote.
- **Sub-skill proposals to replace MultiEdit + discipline.** If the
  problem is "many similar edits", the answer is MultiEdit + grep-
  discipline, not a new orchestration skill.

When in doubt: do NOT write.

## What passes the filter (concrete reference)

Examples of shapes that pass the filter:

- **Registry-drift** — hallucinated agent / specialist names silently
  fall through at dispatch. Mechanical to fix, cheap, fires every time
  the registry is referenced.
- **Cycle-symptom-cause at a boundary** — a brief hardcodes a literal
  at a call-site even though the upstream domain object already
  carries the value. Works coincidentally today, latent bug when
  upstream changes.
- **Verify-against-reality before encoding** — a spec amendment is
  drafted without grounding against the code; code is the tiebreaker
  and a fresh grep would have caught the drift.

All three: cheap to apply, fires often, structural shape. Shared
root: verify against reality before encoding a prescription.

## Entry format

Append to `forge-feed.md` under the "Live entries" header. Each
entry:

```markdown
### L-NNN [tag] short title

**Date:** YYYY-MM-DD
**When:** <workflow gate / situation>
**What:** <1-3 sentences — what happened, why it matters>
**Pattern class:** smell-transfer | cycle-symptom | state-vocab |
  registry-drift | verify-don't-assume | other
**Filter result:** <which checks fired pass — short>
**Status:** open
**Forge-feed candidate:** <proposed framework change, 1-2 sentences>
```

Tags: `[FRAMEWORK]` `[DISCIPLINE]` `[OBSERVATION]` `[BUG]`.

Numbering is sequential across the whole file (L-001..L-NNN). Don't
restart per session.

## Triage cycle

Periodic pass (every few weeks): walk `open` entries, decide
codify-or-drop, link SoT for codified items. Dropped entries stay
in record — the fact that the idea surfaced and was rejected is
itself signal.

## Not for

- Code patterns / fix-recipes — commit messages + the code itself.
- Per-task progress notes — workflow state-files / handoffs.
- Spec-board / code-board verdicts — own archive.
- Session-summary or history entries — `context/history/`.
