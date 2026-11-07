# Protocol: Fix-Brief Anti-Loose-Phrasing Template

Mandatory sections in fix-pass briefs (handed to the reviewer/MCA after pass-1
findings). Prevents overcorrection caused by briefs that are too broad.
Loose-phrasing risk is the single most common fix-pass failure class — not
missing line numbers.

**Consumed by:** `skills/convergence_loop/REFERENCE.md` (fix responsibility,
inter-pass brief generation), `skills/code_review_board/SKILL.md` (fix-pass
brief), `skills/spec_board/SKILL.md` (fix-pass after pass 1).

**Pre-dispatch check:** no hook (semantically not regex-checkable). Discipline
through mandatory template sections in the brief plus downstream scope-bind on
the reviewer/MCA side.

---

## Core claim

> **The risk is loose phrasing, not missing line numbers.**

Line numbers and pointer blocks are necessary (locator precision), but **not
sufficient**. A brief with perfect line refs but loose-phrased recommendations
produces overcorrection. Observed across multiple tasks with high-precision
pointer blocks combined with linguistically vague fix instructions —
reviewers/MCA add out-of-scope changes the brief left linguistically open.

The mechanical countermeasure is **phrase discipline + scope bound + explicit
out-of-scope**, not "even more precise line refs".

---

## Architecture reading-map (orientation, not a scope license)

When the fix touches a subsystem AND the project's `intent.md` names an
as-built architecture reading-map, point the fixer at it so it understands
the seam it is repairing instead of re-deriving the architecture from
`src/`. **Orientation only:** the map informs *what the seam is* — it never
licenses widening the fix; the scope bound + out-of-scope sections below
stay the hard boundary. Generic by contract — reference the map only if the
project's `intent.md` declares one; no path is hard-coded here (it lives in
the consumer's `intent.md`). Same deliberate selectivity as
`mca-brief-template-decision-classes.md` §5 — and the same reason it is kept OUT of
`dispatch-template.md` / the board scaffolds: those strip context for
anti-bias fresh-read review.

---

## Trigger (when these sections are mandatory)

Every fix-pass brief in pass N+1 (N ≥ 1), if:

- Pass N reports ≥1 MAJOR/HIGH or MEDIUM with spillover risk, **OR**
- Pass N produces a cluster touching >1 file, **OR**
- Fix scope spans more than one section/module, **OR**
- The reviewer recommendation itself contains universal quantifiers or hedges
  (the brief author MUST then **not** copy reviewer phrasing — see AP-4 in `fix-brief-template-phrase-check.md`).

Below threshold (single-line, single-file, single-MINOR with pointer block):
sections optional, brief author writes a one-line rationale why. Section 5 has
its own trigger, below.

---

## Mandatory sections in the fix brief

Three mandatory sections (in addition to the pointer block + authority refs),
plus a fourth whenever the fix touches a state carrier, and a fifth in every
brief written from a code review's findings:

**Workflow scope (instance stamping):** when the fix runs inside a workflow step
and `workflow_engine.py --next` reports a `NOT-YOURS:` line (≥2 workflows live),
paste the engine's `SCOPE:` + `NOT-YOURS:` block into the brief verbatim — same
rule as `mca-brief-template.md` §Workflow scope. Stamps the agent with its own
file pointers so it does not trip over a sibling workflow's files.

**Approved acceptance:** a fix brief for work on a task recopies the block
`## Approved acceptance (read-only)` from the task file, not from the earlier
brief, and runs its check before dispatch
(`skills/_protocols/approved-acceptance.md` §Change, resume and re-brief).

**Dispatch to the implementer:** the fix brief is a file in the work unit's records, dispatched by path with a report
file (`skills/_protocols/mca-dispatch.md`); the report holds one result per finding.

### Section 1: Anti-pattern phrase check

Brief author audits the brief text against 4 anti-pattern classes **before**
dispatch. Block entry documents the result:

```yaml
phrase_check:
  universal_quantifiers: "<absent | present-justified: <quote+rationale>>"
  hedges:                "<absent | present-justified: <quote+rationale>>"
  optionalities:         "<absent | present-justified: <quote+rationale>>"
  paraphrase_vs_quote:   "<reviewer-quoted | paraphrase-justified: <rationale>>"
```

Default expectation: all four `absent`. `present-justified` is the exception —
when the brief author legitimately needs a universal quantifier (e.g. the
reviewer finding genuinely is "all X in the file"), quote + rationale make
the exception explicit so it doesn't normalize silently.

### Section 2: Scope bound (reference + stop limit)

Self-correction signal for the reviewer/MCA. Brief explicitly contains:

```yaml
scope_bound:
  files:        ["<file1:section>", "<file2:lines-X-Y>"]   # concrete locators
  stop_limit:   {product_paths: [<glob>], product_lines: <N>, test_paths: [<glob>], test_lines: <M>}  # mca-brief-template.md §Stop limit
  loc_rationale: "<why N and M — based on which clusters/findings>"
```

Reaching the product limit (measured per commit, `mca-dispatch.md` §The size limit) signals bad scope estimation or
overcorrection in flight; both want Buddy's decision, not silent expansion.

### Section 3: Explicit out-of-scope (bleed risk)

When the brief author anticipates that the reviewer/MCA could be pulled into
adjacent code/spec by spatial or semantic proximity: list explicitly what
must NOT be touched:

```yaml
out_of_scope:
  - location:  "<file:section>"
    why_close: "<why near-scope and therefore a bleed candidate>"
    do_not:    "<concretely what NOT to do>"
```

Bleed-risk examples:
- Recommendation in section A, but section B has a similar pattern → author
  lists B as out-of-scope when B is a legitimate separate case.
- Fix touches function X, neighbouring function Y has a similar smell but is
  a separate issue → Y explicitly out-of-scope.
- Spec section §3.4 fix, §3.5 has related phrasing but different authority →
  §3.5 explicitly out-of-scope.

Below threshold (no adjacent bleed risk identified): section is a one-liner
`out_of_scope: []  # no adjacent bleed-risk identified`.

### Section 4: Mechanism cells (MUST when the fix touches a state carrier)

A fix on one side of a mechanism moves the next defect to an adjacent cell
(observed as entry → exit → undo across three consecutive re-checks on one
build). The scope bound above keeps the fix from widening; this section keeps
it from being a slice. It names the fix's position in the owning spec's
`§Mechanism-Lifecycle` matrix (`_protocols/mechanism-model.md`):

```yaml
mechanism_cells:
  section:   "<spec> §Mechanism-Lifecycle: <name>"
  changed:   ["<state> × <op>: <old cell> → <new cell>", ...]   # every cell the fix changes
  intact:    ["<state> × <op>: <guard that still holds>", ...]  # the cells the fix must leave as they are
  matrix_edit: "same change — <spec>:<lines>"                   # the section is updated with the fix, never only the build log
  class_witness: "<command> — red before each fix: <id> @ <rev>, ..."  # same_class: yes, else n/a (simplify-before-patch.md §Class witness); the fix leaves it unedited, adds no test per finding
  exit_criterion: "<parts and their state> — owner-approved <where>"  # drilled mechanism, else n/a (derive-and-exit.md)
```

`changed` is the fix's whole effect on the mechanism — a fix that cannot list
its cells is not yet a fix brief, and the Simplify-before-patch record's
`decision: patch (...)` quotes this list. `intact` is the re-verify
adversary's starting point: its mandate is the mechanism against the matrix,
so every `intact` cell gets probed, not only the `changed` ones. A fix that
would re-place a `now` cell into another task or beyond the MVP is a design
fork for the caller (a plan change), not a fix.

Below threshold (the fix touches no state carrier): one-liner
`mechanism_cells: n/a  # no state carrier touched`.

### Section 5: Cause per finding (MUST in every brief from a code review's findings)

One entry per finding this pass fixes and per blocking finding it does not,
from its verified row; causes, checks and answers:
`skills/convergence_loop/cause-before-answer.md`.

```yaml
causes:
  - id: F-…
    cause: wrong-finding | intent | spec | mechanism | stuck | code
    check: "<the check that holds, quoted; a ruling by its RL id>"
    answer: "<rule | ask <caller> | amend <§> → re-derive <unit> or patch | invariant or replacement | fresh implementer <model> | patch | accept-limit>"
spec_gaps: report under Concerns each outcome this pass decides that no spec item states
```

A finding without an entry is not yet in the brief. A re-derivation also
carries its §Re-derive part (unit, amended item, KEEP notes).

---

## Anti-pattern classes (detail) and fill-in checks

When running the Section 1 phrase check and filling Sections 1–3, before dispatch: read and follow
`skills/_protocols/fix-brief-template-phrase-check.md` (AP-1 universal quantifier, AP-2 hedges, AP-3 optionalities,
AP-4 paraphrase instead of reviewer quote, each with examples, better pattern and heuristic; the anti-patterns when
applying the template).

## Self-correction signal (reviewer/MCA side)

A reviewer/MCA receiving a fix brief with all 3 mandatory sections:

1. **Read the phrase check:** `present-justified` means the author
   quantified loosely on purpose; don't push interpretation further.
2. **Respect the scope bound:** the file list is a hard bound. The product-code
   limit is the stop: measured after each commit, and at it STOP + escalate
   (`mca-dispatch.md` §The size limit); do not silently expand.
3. **Honour out-of-scope:** explicit out-of-scope is HARD. The reviewer/MCA
   only addresses those entries if Buddy explicitly amends the brief.

Brief without sections (below threshold): reviewer/MCA works from the pointer
block precision alone. On ambiguity STOP + escalate (an implementer: an `unclear` row,
`skills/_protocols/mca-dispatch.md`), do not expand.

---

## Bind rule (downstream)

- **`code_review_board` pass N+1 reviewer:** verifies in the pass-N+1 review
  that the fix implementation respected the scope bound. Out-of-scope bleed
  in the diff = finding (severity by bleed impact).
- **`spec_board` pass N+1:** analogous for spec fixes — out-of-scope sections
  edited without authority = finding.
- **convergence_loop outer-cycle bound:** if outer cycle 2+ is repeatedly
  triggered by bleed findings, that is a brief-quality signal — the brief
  author improves the phrase check or escalates.

---

## Failure mode

**Theatre compliance:** sections present but semantically empty/generic.

Mitigation:
1. **Phrase-check `present-justified` without quote** = invalid. The quote
   block is mandatory so the author cannot normalize the exception silently.
2. **Scope bound without LOC rationale** = invalid: `loc_rationale` explains
   N and M.
3. **Out-of-scope without `why_close`** = invalid: without the bleed
   mechanism named, the entry is not verifiable.

A reviewer/MCA receiving a brief with theatre sections rejects it with
"section X formally filled but semantically empty — please tighten". No
silent proceed.

---

## Discipline rationale

What fixes loose phrasing (§Core claim) is **phrase discipline + scope bound +
explicit out-of-scope acknowledgement**.

Mechanism approach (3 mandatory sections + quote-block convention) >
persona approach (brief-adversary review post-hoc). The author is forced
during the fill-in step to actively check the anti-patterns — the mandatory
section is the pressure, not a persona audit.

Complementary to `mca-brief-template.md` (implicit-decisions in the
implementation brief) — both address brief-quality gaps but at different
phases: the implementation brief locks decisions upfront, the fix brief
prevents scope bleed in the iteration pass.
