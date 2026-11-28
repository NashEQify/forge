# Reviewer protocol

The one protocol every review seat reads (Spec, Code, UX Board, Council). Your persona adds your axis; a board
protocol (`spec-reviewer-protocol.md`, `ux-reviewer-protocol.md`) adds its layout.

## How you work

- **Independent and read-only.** Fresh context, no other reviewer's conclusions; open another review only when the
  dispatch assigns you a specific prior finding to verify. Create or edit no file. Return the whole review inline;
  Buddy saves it verbatim.
- **Not confined to the diff.** Read whole files, callers, callees, tests and configs, and say what you read beyond
  the diff. A claim about mechanical behaviour (engine routing, a hook, a validator's pass/fail) points at the code
  that does it (`scripts/…:line`), not only at prose that claims it.
- **Stay on your axis.** What belongs to another seat goes under "Questions for other reviewers", not into findings.

## Checked scope

Before the findings, a `## Checked scope` section with four fields, in this order:

```
## Checked scope

- **Purpose:** what the artifact must enable, one sentence in your own words
- **Paths checked:** each scenario you checked: input -> expected -> what it does, with file:line or command
- **Assumption tested:** the author's central assumption, the check that would refute it, what it showed (file:line)
- **Consequence:** the concrete consequence of the strongest finding for a named component or person; with no
  finding, what the checked paths establish and what stays unverified
```

**Bind rule:** at least one finding refers to a path checked or the assumption tested; with none, Consequence
carries the evidenced result and its limits. Zero findings is a valid result; never invent one. Record checks and evidence, not your
deliberation. A missing section is noted at adoption, not refused.

## Findings

A finding without an evidence pointer into the reviewed bytes is a guess: leave it out. Each finding gives its
checked path, evidence and conclusion (its consequence if unfixed).

**Evidence pointers** (`skills/_protocols/evidence-pointer-schema.md` holds the full schema): kinds `file_range`,
`grep_match`, `dir_listing`, `file_exists`. Every pointer resolves in the review package's checkout at the bytes under
review. A `quote` is one double-quoted string copied character for character from the cited lines (lines joined by
`\n`, leading spaces kept, no `...`, no `|` or `>` block), at most 3 lines and 200 codepoints. Code from another
branch or a scratch copy goes into the description as `<ref>:<path>:<line>`. A pointer shown as an example, not as
evidence, goes in a fence that is not `yaml` (adoption reads every `yaml` fence as evidence). Before returning, write
your draft to a temporary file outside the repository and run
`python3 <root>/scripts/validate_evidence_pointers.py --strict --repo-root <checkout> <file>`; correct what it prints.

**Severity:** critical, high, medium, low.

### Findings about tests

Decide in this order which finding you have:

1. **Required evidence is missing:** an AC with no test, a fix whose test did not fail before the fix, a test or
   class witness the brief requires, an in-scope mechanism cell without a guard or test. Grade it as your role and the
   brief say.
2. **The product is wrong now:** a run or a concrete input with expected and actual shows wrong behaviour behind the
   gap. That behaviour is the finding and sets its severity.
3. **A test finding:** the code does what is required and a test reaches the path, but no assertion fails without
   the behaviour. Name the test (`file:line`); the fix strengthens it, a new test function only where no test reaches
   the path. At most medium; it does not make your verdict FAIL.

A test the change adds that breaks a rule of `skills/testing/lean-suite.md` §Each test earns its place is a `low`
note at most.

## Output format

The return starts with its frontmatter (`schema_version: 1`). Code reviews use this layout (`per_finding`); spec and
UX boards use their board protocol's:

```markdown
---
schema_version: 1
---

## Checked scope
...

### F-{ROLE}-{NNN}: {short description}
- severity: critical | high | medium | low
- scope: local | cross-cutting | foundation
- evidence:
    - kind: file_range
      path: <repo-relative path>
      lines: <start>-<end>
      quote: "<literal text>"
- description: {checked path, evidence, conclusion}
- suggested_fix: {concrete change}

## Questions for other reviewers
## What's working well

Verdict: PASS | PASS_WITH_RISKS | FAIL — {one sentence}
```

The fences only display the example. Every board's return, spec and UX included, ends with **Questions for other
reviewers** (what your axis cannot answer, as concrete questions; the discourse round collects them) and **What's
working well** (1–3 concrete things; the chief keeps them under Patterns to Preserve), then the verdict line.

## Mandatory envelope and clean output

When the dispatch carries a captured review (run, subject, slot), read `skills/_protocols/evidence-pointer-schema.md`
§9 before writing the return, and add to the frontmatter, verbatim from the dispatch:

```yaml
review_run_id: "<captured run>"
review_subject_digest: "<captured subject>"
review_slot: "<assigned slot>"
```

With no findings, the frontmatter carries a non-empty top-level `evidence:` list for the checked scope and conclusion
instead of finding evidence; do not mix the two layouts.
