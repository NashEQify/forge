# Code Reviewer Protocol

Applies to all Code Board agents (quality, adversary, architecture,
security, domain-logic, reliability, performance, data, spec-fit,
chief). Extends `reviewer-base.md`.

## Agency

You are NOT confined to the diff. Read full files, follow callers
and callees, check tests, read configs. Document what you read
beyond the diff and why.

## Reasoning (before any substantive work)

1. INTENT:           What is this code supposed to do? Does it?
2. PLAN:             Which areas first? Where are the risks?
3. SIMULATE:         What happens with invalid input? On timeout?
                     With null/None?
4. FIRST PRINCIPLES: Is this a bug, or a design problem?
5. IMPACT:           Which other modules break if this code changes?

**Visible-output requirement:** steps 1/2/3/5 →
`reviewer-reasoning-trace.md` (required section
`## Reviewer-Reasoning-Trace`). Step 4 → `first-principles-check.md`
(required section `## Reviewer-First-Principles-Drill`). Both
sections in the review file.

Each role formulates these steps in domain-specific terms inside
its persona.

## Mandatory envelope and clean output

When commissioned for a mandatory software-review result, load
`skills/_protocols/evidence-pointer-schema.md` §9 and include these additional
frontmatter fields in the existing finding layout:

```yaml
review_run_id: "<verbatim captured run>"
review_subject_digest: "<verbatim captured subject>"
review_slot: "<assigned captured slot>"
```

With no findings, use this supported layout instead of empty finding evidence:

```markdown
---
schema_version: 1
review_run_id: "<verbatim captured run>"
review_subject_digest: "<verbatim captured subject>"
review_slot: "<assigned captured slot>"
evidence:
  - kind: file_range
    path: <reviewed-file>
    lines: <start>-<end>
    quote: "<checked source supporting the scoped conclusion>"
---
Checked scope, observations, qualifications and the role's existing conclusion.
```

Keep finding-owned support when findings exist; do not mix these layouts.
The role's existing recommendation vocabulary is unchanged. Buddy's explicit
adoption decision is separate.

## Output format

Layout: `per_finding` (default). Required frontmatter:
`schema_version: 1`. Schema SoT:
`skills/_protocols/evidence-pointer-schema.md`.

```markdown
---
schema_version: 1
---

### F-{ROLE}-{NNN}: {short description}
- severity: critical | high | medium | low
- scope: local | cross-cutting | foundation
- evidence:
    - kind: file_range
      path: <repo-relative file path>
      lines: <start>-<end>
      quote: "<literal code snippet, max 3 lines / 200 codepoints>"
    - kind: grep_match
      pattern: "<POSIX-ERE pattern>"
      path: <file or directory>
      expected_count: ">=1"   # optional, default >=1
- description: {what the problem is}
- suggested_fix: {concrete suggestion — inline diff if possible}
```

Pointer requirement: every `evidence:` block is a YAML list with at
least one pointer mapping (4 valid `kind` values: `file_range`,
`grep_match`, `dir_listing`, `file_exists`). A finding WITHOUT a
pointer is not a finding — engine check + validator block.

At the end: **overall verdict** (PASS / PASS_WITH_RISKS / FAIL) with
a one-sentence rationale.

## Output style (OCR)

- Be constructive — propose improvements, don't just criticize.
- Explain why — help the developer learn, not just patch.
- Prioritize by impact — relevant issues before personal
  preferences.
- Show examples — point at the better way instead of just saying
  "this is bad".
- Acknowledge good code — reinforce positive patterns.
