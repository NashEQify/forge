# Evidence Pointer Schema (tool-neutral)

**Source-of-truth for Spec 299 fabrication-mitigation layer 1.**

This protocol is tool-neutral. It defines the pointer
format for source claims in reviewer outputs and skill outputs. It
is consumed by the engine check
(`scripts/workflow_engine.py` `pointer_check`), the standalone
validator (`scripts/validate_evidence_pointers.py`), and pre-commit
Check 5 SOURCE-VERIFICATION
(`orchestrators/claude-code/hooks/pre-commit.sh`).

Canonical spec authority:
`docs/specs/299-fabrication-mitigation.md` §1.

---

## Standalone reasoning scope

Pointer syntax and evidence honesty apply without an engine or Git repository.
A caller-owned private temporary execution root may hold supplied evidence and
complete reviewer returns; paths/ranges resolve relative to that root. Use explicit
structural arguments for reasoning not supported by a file. Validator/engine/hook
references in this protocol describe optional software integrations, not mandatory
standalone dependencies. Final inline conclusions include usable excerpts/references
rather than relying solely on temporary paths that may disappear. Developer-specific
schema/API/code examples illustrate evidence; they do not select development work.

## 1. schema_version

Required in report frontmatter for both layouts. Accepted values:

| Value | Meaning |
|---|---|
| `schema_version: 1` | current pointer requirement. Engine + validator enforce. |
| `schema_version: 0` | legacy. Engine check and validator silent-skip (return pass / exit 0). |
| (field missing) | legacy (same as `schema_version: 0`). Backward compatible. |

The table describes default validation. Optional library `strict=True` or CLI `--strict` rejects missing/0 schema with exit 1; engine `min_schema_version` retains its existing policy. Unsupported schema forms/versions remain invalid, and malformed YAML remains a parse error. Historical reports are never automatically rewritten or relabelled.

Default pointer validation and historical reading retain this compatibility. Mandatory current software-review adoption requires supported current-schema validation and the identity contract in §9. Historical reports are neither rewritten nor relabelled to satisfy it. Historical context used by a current scoped verification is distinct from mandatory current producer reports.

Future versions: schema migration via version bump (e.g.
`schema_version: 2`) with its own spec amendment.

---

## 2. Pointer format — 4 kinds

Every pointer is a YAML mapping with the required field `kind` and
kind-specific required fields.

### 2.1 `kind: file_range`

Existence check + range check + `grep -F "$quote" $path`.

**Required fields:** `path`, `lines`, `quote`.

```yaml
- kind: file_range
  path: agents/_protocols/reviewer-base.md
  lines: 24-27
  quote: "A finding WITHOUT evidence (a concrete pointer into the review target)"
```

- `path` is repo-relative (no `./` prefix).
- `lines` as `<start>-<end>` (same number for single-line, e.g.
  `40-40`). Both numbers must lie within the file's line count.
- `quote` is a literal text snippet from the file. The validator
  uses fixed-string matching (substring check, semantically like
  `grep -F`); special chars (`$`, `*`, `[]`) match literally.
- **Quote-match scope:** the quote match is
  RESTRICTED to the declared line range `lines: <start>-<end>`,
  not the whole file. Rationale: self-affirmation mitigation —
  without range restriction the quote could accidentally match
  somewhere else in the file and the `lines:` anchor would be
  cosmetic. Pre-quote cap (max 3 lines, §3) keeps the checked
  block tractable.

### 2.2 `kind: grep_match`

`grep -cE "$pattern" $path`; validate the count against
`expected_count`.

**Required fields:** `pattern`, `path`. **Optional:**
`expected_count` (default `">=1"`).

```yaml
- kind: grep_match
  pattern: "PreToolUse"
  path: orchestrators/claude-code/hooks/
  expected_count: ">=1"
```

- `pattern` is POSIX-ERE (compatible with `grep -E`).
- `path` may be a file OR a directory. For a directory: recursive
  grep.
- `expected_count` see §4 DSL grammar.

### 2.3 `kind: dir_listing`

`test -d $path` + every file in `expected_files` must exist.

**Required fields:** `path`, `expected_files` (list).

```yaml
- kind: dir_listing
  path: docs/reviews/council/<date>-<topic>/
  expected_files: [briefing.md, synthesis.md]
```

### 2.4 `kind: file_exists`

`test -f $path`.

**Required field:** `path`.

```yaml
- kind: file_exists
  path: docs/specs/299-fabrication-mitigation.md
```

**Discipline note:** `kind: file_exists` is
explicit-trivial — the mechanically cheapest pointer. Reviewer
personas should have at least one non-trivial pointer (`file_range`
OR `grep_match`) per finding. The validator + hook emit a
WARN/discipline hint on outputs whose findings reference only
`file_exists` — mechanically valid, disciplinarily an anti-pattern
(smart-but-wrong risk). Trivial-only outputs PASS the validator
mechanically (exit 0), but produce a stderr WARN so tier-1
reviewers don't quietly use the defeating pattern.

---

## 3. Quote length cap

Required for `kind: file_range`. Constraints:

- **<= 3 lines** AND
- **<= 200 characters**

**Metric (ADV-TC-008 decision):** characters are counted as
**Python codepoints** (`len(quote)` in Python). Not bytes, not
grapheme clusters, not UTF-8 octets.

Rationale: Python `len()` is deterministic, platform-independent,
and matches validator + engine + hook when they are all
Python-based. A byte or grapheme cap would be a multi-layer drift
risk. Codepoint semantics make the combining-marks bypass
(200 codepoints = 1 visible grapheme) an explicit accepted
trade-off — such outputs are extremely uncommon and reviewer
discipline catches them.

Violation output: `quote exceeds cap: <N> lines (max 3) / <M>
chars (max 200)`.

Enforcement point: `quote_length_cap_ok()` in `validate_pointer()`
BEFORE `grep -F` runs (see
`scripts/validate_evidence_pointers.py` §6.4).

---

## 4. expected_count DSL grammar (kind=grep_match)

```
EXPR := OPERATOR INTEGER | INTEGER
OPERATOR := ">=" | "<=" | ">" | "<" | "==" | "!="
INTEGER := [0-9]+
```

| Example | Meaning |
|---|---|
| `">=1"` | at least 1 match (default when not set) |
| `"==5"` | exactly 5 matches |
| `"<10"` | fewer than 10 matches |
| `"!=0"` | any value != 0 |
| `"3"` | bare integer = exact match (`==3`) |

Default value when `expected_count` is not set: `">=1"`.

---

## 5. Layout classes

Per skill (skill frontmatter `evidence_layout`), one of:

### 5.1 `evidence_layout: per_finding` (default)

`evidence:` block per finding, embedded in the finding markdown
block. Pattern for reviewer outputs.

```markdown
### F-CHIEF-001: Example finding
- severity: high
- evidence:
    - kind: file_range
      path: docs/specs/299-fabrication-mitigation.md
      lines: 24-27
      quote: "A finding WITHOUT evidence"
- description: ...
```

`schema_version: 1` is required in the output frontmatter
(top-level YAML between `---` markers).

Supported finding headings are ATX levels 2–4 (`##` through `####`) whose leading identifier matches `(F|UX)-[A-Z][A-Z0-9]*(?:-[A-Z][A-Z0-9]*)*-[0-9]+`, followed by a word boundary. Trailing titles, severity labels and punctuation are permitted.

A finding remains open until the next heading of equal or shallower depth. Ordinary deeper subsections retain that owner. A deeper finding owns its own evidence; its pointers do not support its parent. After a nested finding closes, the nearest still-open parent resumes ownership.

Both standalone `evidence:` and bullet `- evidence:` blocks are supported with their existing indentation forms. Each finding needs at least one non-empty evidence list; multiple blocks and pointers are allowed within that owner. Every block must contain a non-empty list of pointer mappings. Missing/empty evidence, wrong list shape or nonmapping entries fail validation; malformed YAML remains a parse error.

Ordinary YAML comments remain inside an evidence block. A line within its indented
body that also matches an ATX finding-like heading is ambiguous and fails structural
validation; move the report heading outside the YAML indentation, or rewrite the
comment so it does not resemble a finding heading. The diagnostic identifies the
ambiguous line. This avoids silently discarding a finding or later source pointers.

Ignore headings and evidence inside backtick or tilde fenced examples. Reject duplicate finding identifiers, orphan evidence and conflicting ownership. Diagnose unsupported finding-like headings beginning `F-` or `UX-`, and historical consolidation identifiers matching `C[0-9]+-[0-9]+`, rather than silently accepting them. Historical C2 reports require caller-owned normalization before current revalidation.

Structural diagnostics identify the finding identifier and heading line, or the offending line when no owner exists, plus the reason. Pointer checks establish source structure/existence, not the truth of a conclusion.

### 5.2 `evidence_layout: top_level`

`evidence:` block as a top-level frontmatter block. Pattern for
skill outputs without finding structure (e.g. `spec_authoring`
output with source claims in the body).

```markdown
---
schema_version: 1
evidence:
  - kind: file_range
    path: docs/specs/299-fabrication-mitigation.md
    lines: 24-27
    quote: "A finding WITHOUT evidence"
---

Body with source claims...
```

Finding-bearing current reports retain per-finding evidence ownership. Reports with no findings use the existing top-level layout with non-empty evidence supporting the checked scope and conclusion. This includes clean light-verification reports and discourse supplements without new findings.

Review adoption (§9.4) resolves every parseable quote in a current report and turns structural problems into diagnostics; it does not validate the decision artifact's layout. Ordinary pointer checks and the commit hook keep the structural validation of this section.

### 5.3 Auto-detect

Honor an explicit `per_finding` or `top_level` selection. In `auto`, select `top_level` when frontmatter contains `evidence`; otherwise select `per_finding`. A top-level report requires non-empty frontmatter evidence and no finding structure or body evidence. A per-finding report requires supported findings with owned evidence and no frontmatter evidence. Conflicting layouts fail explicitly; fences do not contribute body structure. Never infer support by comparing global counts.

---

## 6.–7. Reviewer-protocol migration and cross-references

When changing the pointer format or one of its consumers: read `skills/_protocols/evidence-pointer-integrations.md`
(§6 which reviewer protocols carry the format; §7 engine check, loader, validator and pre-commit check).

## 8. Author-side pointers (Buddy-authored artifacts)

Before writing an artifact a downstream consumer will trust as authority for code behaviour (a positive mechanical
claim, a completeness or absence claim, a committed record that keeps evidence), and before a completion claim in a
return, a final message or a task close: read and follow `skills/_protocols/evidence-author-claims.md` (§8.1 pointer
at write time; §8.2 inventory-flip and its honest bound; §8.3 layers where the asserter owes the grounding; §8.4 what
a committed record keeps; §8.5 the evidence each completion claim requires).

## 9. Mandatory software-review adoption

Only for a software review meant to satisfy a mandatory result, readiness or completion boundary:
- before initiating it or producing a report for it: read and follow
  `skills/_protocols/evidence-review-capture.md` (§9 receipt, §9.1–§9.3 owner, capture request, reports);
- before consuming its reports, adopting, checking the current result or writing review-derived tasks: read and
  follow `skills/_protocols/evidence-review-adoption.md` (§9.4–§9.6).
