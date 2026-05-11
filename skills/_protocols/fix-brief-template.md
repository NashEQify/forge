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

## Trigger (when these sections are mandatory)

Every fix-pass brief in pass N+1 (N ≥ 1), if:

- Pass N reports ≥1 MAJOR/HIGH or MEDIUM with spillover risk, **OR**
- Pass N produces a cluster touching >1 file, **OR**
- Fix scope spans more than one section/module, **OR**
- The reviewer recommendation itself contains universal quantifiers or hedges
  (the brief author MUST then **not** copy reviewer phrasing — see AP-4).

Below threshold (single-line, single-file, single-MINOR with pointer block):
sections optional, brief author writes a one-line rationale why.

---

## Mandatory sections in the fix brief

Three mandatory sections (in addition to the pointer block + authority refs):

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

### Section 2: Scope bound (reference + LOC cap)

Self-correction signal for the reviewer/MCA. Brief explicitly contains:

```yaml
scope_bound:
  files:        ["<file1:section>", "<file2:lines-X-Y>"]   # concrete locators
  loc_cap:      "<N> lines changed total expected"          # +/-30% acceptable
  loc_rationale: "<why N — based on which clusters/findings>"
  trigger_stop: "if LOC > <1.5N>: STOP + escalate to Buddy"
```

The LOC cap is a plausibility gate, not a hard limit. If the reviewer/MCA
needs more than 1.5x cap, that signals either bad scope estimation by the
author OR overcorrection in flight. Both cases want a user decision, not
silent expansion.

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

---

## Anti-pattern classes (detail)

### AP-1: Universal quantifier

**Problem:** "all / clean up / delete all / refactor all references" — the
brief delegates the scope decision to the reviewer/MCA. Universal phrasing
permits an expansive reading that goes beyond the pass-N findings.

**Examples:**
- ❌ "Clean up all references to the deprecated API" → reviewer/MCA touched
  20 files, 12 of them legitimate.
- ❌ "Delete all dead code in the module" → MCA killed code that was
  spec-defined but unused (spec violation through brief vagueness).
- ❌ "Refactor all the test fixtures" → MCA modified fixtures not mentioned
  in any pass-N finding.

**Better pattern:**
- ✅ "Replace 4 references to API X listed in cluster C2-001 (pointer block).
  Do not touch other API X references; those are legitimate per spec §3.2."
- ✅ "Delete the 3 specific dead-code blocks identified at file:lines.
  No other dead-code search."
- ✅ "Refactor only fixtures used in tests/foo/test_bar.py:23-89 per
  cluster C2-005."

Heuristic: replace "all / alle / clean up" with a numeric count + pointer.

### AP-2: Hedges

**Problem:** "also / additionally / weitere / further / if needed / ggf." —
appends unspecified follow-up actions. Hedges are often the brief author's
attempt to suggest "completeness" without being concrete.

**Examples:**
- ❌ "Fix the validator regex AND also clean up related tests" → MCA modified
  unrelated test logic.
- ❌ "Update the schema, also other consumers if needed" → MCA touched 6
  consumers, 4 of them unrelated.
- ❌ "Refactor function X — additionally check call sites" → MCA refactored
  call-site signatures unannounced.

**Better pattern:**
- ✅ "Fix the validator regex per C2-004 (line 47). Tests are out-of-scope —
  the next pass reviewer will catch any test breakage."
- ✅ "Update the schema. Affected consumers: A.py, B.py (listed). Other
  consumers out-of-scope per scope_bound."
- ✅ "Refactor function X signature per C2-002. Call sites: explicit list of
  3 sites in scope_bound. Do not touch others."

Heuristic: every "also / further / additionally" is a red flag — either list
concretely or declare out-of-scope.

### AP-3: Optionalities

**Problem:** "if needed / where applicable / as needed / bei Bedarf" — the
brief delegates the necessity check to the reviewer/MCA. Under "better safe
than sorry" pressure they will expand.

**Examples:**
- ❌ "Add type hints where applicable" → MCA touched 30 functions that
  pragmatically didn't need hints.
- ❌ "Handle errors as needed" → MCA added try/except cascades where the spec
  mandates fail-fast.
- ❌ "Update docstrings if relevant" → MCA touched 15 docstrings out-of-scope.

**Better pattern:**
- ✅ "Add type hints to the 6 functions listed in C2-003. No other functions."
- ✅ "Add `except FabricationError` at line 47 only. Other error paths follow
  spec §4.3 fail-fast — do not touch."
- ✅ "Update docstrings for 3 functions changed in this fix pass. Other
  docstrings out-of-scope."

Heuristic: "if-clauses" are a brief deficit. The author has to do the check
upfront, not delegate it.

### AP-4: Paraphrase instead of reviewer quote

**Problem:** the brief author paraphrases the reviewer recommendation
instead of **quoting** it. Paraphrase introduces drift — the brief author
reads the reviewer finding, rewords it, and in doing so loses precision or
adds the brief author's own interpretation.

Spicy special case: the **reviewer themselves** uses a universal quantifier
("eliminate all stale references") and the brief author copies the phrasing
verbatim → AP-1 propagates. The brief author MUST NOT copy reviewer phrasing
when it is itself loose; instead, narrow-quote and force a scope bound.

**Examples:**
- ❌ Reviewer: "C2-004: regex `^schema_version:\s*1$` rejects quoted v1 forms
  (line 47, validate_evidence_pointers.py)" → brief paraphrases: "Fix the
  schema validator to handle v1 forms" → MCA understood "all v1 forms" and
  touched parsing logic in 3 unrelated files.
- ❌ Reviewer: "Eliminate stale references" → brief: "Eliminate stale
  references" (verbatim copy of loose phrasing) → AP-1 propagated.

**Better pattern:**
- ✅ Brief quotes the reviewer verbatim with a locator: `> "C2-004: regex
  ^schema_version:\s*1$ rejects quoted v1 forms (line 47)" — fix this
  specific regex at line 47, no other validator changes.`
- ✅ When the reviewer is itself loose, the brief explicitly narrows: `>
  Reviewer recommends "eliminate all stale references". Narrowed scope per
  C2-001 pointer block: 4 specific refs at lines X, Y, Z, W. No others.`

Heuristic: reviewer recommendation as a **quote block** (`>`) with the
cluster ID, brief author's narrow-bind directly underneath. No "in other
words".

---

## Self-correction signal (reviewer/MCA side)

A reviewer/MCA receiving a fix brief with all 3 mandatory sections:

1. **Read the phrase check:** if `present-justified` is declared, the
   reviewer/MCA knows the brief author deliberately quantified loosely —
   don't push interpretation further.
2. **Respect the scope bound:** the file list is a hard bound. The LOC cap
   is a plausibility bound — if exceeded, STOP + escalate, do not silently
   expand.
3. **Honour out-of-scope:** explicit out-of-scope is HARD. The reviewer/MCA
   only addresses those entries if Buddy explicitly amends the brief.

Brief without sections (below threshold): reviewer/MCA works from the pointer
block precision alone. On ambiguity STOP + escalate, do not expand.

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

## Anti-patterns when applying the template

- **DO NOT** select phrase-check "all absent" pro forma without actually
  reading the brief text against the 4 classes. Mechanical test: take the
  brief text, mentally grep for "all / alle / clean up / also / further /
  if-clauses / where-applicable", and for each hit decide absent (not
  relevant) vs present-justified (with quote + rationale).
- **DO NOT** fill the scope bound with an unrealistic LOC cap (e.g. "1000
  lines" for 3 clusters). The LOC cap must derive from cluster magnitude —
  if the author can't estimate, they over-estimate and the self-correction
  signal stops working.
- **DO NOT** leave out-of-scope empty without a bleed check. The bleed check
  is active: the author iterates over adjacent code/sections and asks "could
  the reviewer/MCA slip in here?". Empty-with-rationale is fine; empty
  without check is compliance theatre.

---

## Failure mode

**Theatre compliance:** sections present but semantically empty/generic.

Mitigation:
1. **Phrase-check `present-justified` without quote** = invalid. The quote
   block is mandatory so the author cannot normalize the exception silently.
2. **Scope bound without LOC rationale** = invalid. `loc_rationale` forces
   the author to explain why N — no magic numbers.
3. **Out-of-scope without `why_close`** = invalid. The author has to name
   the bleed mechanism — otherwise the entry is not declaratively
   verifiable.

A reviewer/MCA receiving a brief with theatre sections rejects it with
"section X formally filled but semantically empty — please tighten". No
silent proceed.

---

## Discipline rationale

Loose phrasing in fix briefs is the single most common overcorrection root —
observed across multiple build/full workflows. More precise line numbers do
not solve it (pointer blocks were already there). What is missing is
**phrase discipline + scope bound + explicit out-of-scope acknowledgement**.

Mechanism approach (3 mandatory sections + quote-block convention) >
persona approach (brief-adversary review post-hoc). The author is forced
during the fill-in step to actively check the anti-patterns — the mandatory
section is the pressure, not a persona audit.

Complementary to `mca-brief-template.md` (implicit-decisions in the
implementation brief) — both address brief-quality gaps but at different
phases: the implementation brief locks decisions upfront, the fix brief
prevents scope bleed in the iteration pass.
