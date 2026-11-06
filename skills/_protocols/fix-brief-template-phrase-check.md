# Fix-brief template — phrase check and fill-in checks

Step-loaded unit of `skills/_protocols/fix-brief-template.md`. Read it when the brief author runs the Section 1
phrase check and fills Sections 1–3 of a fix brief, before dispatch.

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

## Anti-patterns when applying the template

- **DO NOT** select phrase-check "all absent" pro forma without actually
  reading the brief text against the 4 classes. Mechanical test: take the
  brief text, mentally grep for "all / alle / clean up / also / further /
  if-clauses / where-applicable", and for each hit decide absent (not
  relevant) vs present-justified (with quote + rationale).
- **DO NOT** fill the scope bound with an unrealistic stop limit (e.g. "1000
  lines" for 3 clusters). Both limits must derive from cluster magnitude —
  if the author can't estimate, they over-estimate and the self-correction
  signal stops working.
- **DO NOT** leave out-of-scope empty without a bleed check. The bleed check
  is active: the author iterates over adjacent code/sections and asks "could
  the reviewer/MCA slip in here?". Empty-with-rationale is fine; empty
  without check is compliance theatre.

---
