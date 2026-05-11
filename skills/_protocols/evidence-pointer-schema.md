# Evidence Pointer Schema (tool-neutral)

**Source-of-truth for Spec 299 fabrication-mitigation layer 1.**

This protocol is tool-neutral. It defines the pointer
format for source claims in reviewer outputs and skill outputs. It
is consumed by the engine check
(`scripts/workflow_engine.py` `pointer_check`), the standalone
validator (`scripts/validate_evidence_pointers.py`), the CC hook
(`orchestrators/claude-code/hooks/evidence-pointer-check.sh`), and
pre-commit check 13.

Canonical spec authority:
`docs/specs/299-fabrication-mitigation.md` §1.

---

## 1. schema_version

Required field in the output frontmatter (top-level layout) OR per
finding block (per-finding layout). Accepted values:

| Value | Meaning |
|---|---|
| `schema_version: 1` | current pointer requirement. Engine + validator enforce. |
| `schema_version: 0` | legacy. Engine check and validator silent-skip (return pass / exit 0). |
| (field missing) | legacy (same as `schema_version: 0`). Backward compatible. |

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
- **Quote-match scope (CC-013, pass-1 fix):** the quote match is
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
  path: docs/reviews/council/2026-05-04-fabrication-mitigation/
  expected_files: [briefing.md, synthesis.md]
```

### 2.4 `kind: file_exists`

`test -f $path`.

**Required field:** `path`.

```yaml
- kind: file_exists
  path: docs/specs/299-fabrication-mitigation.md
```

**F-I-015 discipline note:** `kind: file_exists` is
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

### 5.3 Auto-detect

Validator + hook detect the layout automatically when
`evidence_layout` is missing from the skill frontmatter. Detection
logic:
1. Top-level frontmatter contains an `evidence:` key → `top_level`.
2. Otherwise per-finding grep for `^[ ]*evidence:` in the body →
   `per_finding`.

Default when the skill frontmatter `evidence_layout` is missing:
`per_finding`.

---

## 6. Reviewer-output-protocol migration

Three live files (edit locations documented in
`docs/specs/299-fabrication-mitigation.md` §1.6):

- `agents/_protocols/spec-reviewer-protocol.md` — output-format
  block.
- `agents/_protocols/code-reviewer-protocol.md` — output-format
  block.
- `agents/_protocols/ux-reviewer-protocol.md` — output-format
  block.

In all three: the `evidence:` prose field is replaced by the
pointer list (per-finding layout).

`agents/_protocols/reviewer-base.md` is extended with the
output-frontmatter requirement: `schema_version: 1` MUST appear in
the output frontmatter.

---

## 7. Cross-references

- Spec: `docs/specs/299-fabrication-mitigation.md`
- Engine check: `scripts/workflow_engine.py` `check_completion`
  `pointer_check`
- yaml_loader: `scripts/lib/yaml_loader.py`
  `VALID_COMPLETION_TYPES` + `_validate_completion`
- Validator: `scripts/validate_evidence_pointers.py`
- CC hook: `orchestrators/claude-code/hooks/evidence-pointer-check.sh`
- Pre-commit check 13: `orchestrators/claude-code/hooks/pre-commit.sh`
