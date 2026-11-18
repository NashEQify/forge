# Spec Reviewer Protocol

Applies to all Spec Board agents (Chief, Adversary, Adversary-2,
Implementer, Impact, Consumer). Extends `reviewer-base.md`.

The Deep-Pass-1 third adversary is a second instance of `board-adversary`
dispatched with `model=sonnet` and finding-prefix `F-A3-` — same protocol,
no separate persona file.

## Review questions (before the findings)

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

**Output:** the answers go into the `## Checked scope` section
(`reviewer-checked-scope.md`): step 1 → Purpose, steps 2 and 3 → Paths
checked, step 4 → Assumption tested, step 5 → Consequence. Each finding
carries its checked path, evidence and conclusion.

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
