# Spec Reviewer Protocol

Applies to all Spec Board agents (Chief, Adversary, Adversary-2,
Implementer, Impact, Consumer). Extends `reviewer-base.md`.

The Deep-Pass-1 third adversary is a second instance of `board-adversary`
dispatched with `model=sonnet` and finding-prefix `F-A3-` — same protocol,
no separate persona file.

## Reasoning (before any substantive work)

1. INTENT:           What is this spec supposed to enable? Does it
                     fit the broader system?
2. PLAN:             Which sections first? Where are the risks?
3. SIMULATE:         Could an implementer build from this spec
                     ALONE without follow-up questions?
                     If E2E scenarios are present, walk at least 2
                     of them step by step.
4. FIRST PRINCIPLES: Which implicit assumption is shakiest?
5. IMPACT:           Effects on existing subsystems?

Each role formulates these steps in domain-specific terms inside
its persona.

**Visible-output requirement:** steps 1/2/3/5 →
`reviewer-reasoning-trace.md` (required section
`## Reviewer-Reasoning-Trace`). Step 4 → `first-principles-check.md`
(required section `## Reviewer-First-Principles-Drill`). Both
sections in the review file.

## Check sequence

1. **Completeness:** missing scenarios? Error cases? Edge cases?
   Migration paths?
2. **Consistency:** do parts of the spec contradict each other? Are
   terms used uniformly?
3. **Implementability:** can a developer build this 1:1 without
   follow-up questions?
4. **Interface contracts:** are all inputs/outputs specified
   exactly? Types, formats, bounds?
5. **Dependencies:** what must already exist for this to work? Is
   it documented?

## Reference

Read `framework/spec-engineering.md` for P1-P5 context.

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
- primitive: P1 | P2 | P3 | P4 | P5 | DR-{N} | cross-check
- evidence:
    - kind: file_range
      path: docs/specs/<spec-id>.md
      lines: <start>-<end>
      quote: "<literal snippet from the review target, max 3 lines / 200 codepoints>"
- description: {what the problem is}
- suggested_fix: {concrete suggestion}
```

Pointer requirement: every `evidence:` block is a YAML list with at
least one pointer mapping (4 valid `kind` values: `file_range`,
`grep_match`, `dir_listing`, `file_exists`). A finding WITHOUT a
pointer is not a finding — engine check + validator block.

At the end: **overall verdict** (PASS / PASS_WITH_RISKS / FAIL)
with a one-sentence rationale.
