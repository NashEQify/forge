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

## BuddyAI-specific checks

- structlog instead of print/logging
- asyncpg: connection-pool patterns, transaction timeouts
- Pydantic: `model_dump()` vs `dict()`, `model_validate()` vs
  constructor, `extra="forbid"`
- AppError instead of HTTPException (Task 265)
- Resource cleanup: `async with` for connections, subscriptions,
  locks

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
