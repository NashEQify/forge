# UX Reviewer Protocol

Applies to all UX Board agents (ux-heuristic, ux-ia,
ux-interaction). Extends `reviewer-base.md`.

## Reasoning (before any substantive work)

1. INTENT:           What is the primary user task this UI
                     supports?
2. PLAN:             Which views/flows do I check? In what order?
3. SIMULATE:         I am a user opening this app for the FIRST
                     time. What do I see? What do I do? Where do I
                     stall?
4. FIRST PRINCIPLES: Which review framework matters most for THIS
                     app?
5. IMPACT:           Where does a usability problem make the user
                     give up?

Each role formulates these steps in domain-specific terms inside
its persona.

**Visible-output requirement:** steps 1/2/3/5 →
`reviewer-reasoning-trace.md` (required section
`## Reviewer-Reasoning-Trace`). Step 4 → `first-principles-check.md`
(required section `## Reviewer-First-Principles-Drill`). Both
sections in the review file.

## Output format

Layout: `per_finding` (default). Required frontmatter:
`schema_version: 1`. Schema SoT:
`skills/_protocols/evidence-pointer-schema.md`.

```markdown
---
schema_version: 1
---

### UX-{ROLE}-{NNN}: {short description}
- severity: critical | high | medium | low
- {framework_ref}: {heuristic ID | pattern ID | interaction ID}
- evidence:
    - kind: file_range
      path: <repo-relative file path to the spec / mockup description>
      lines: <start>-<end>
      quote: "<literal snippet, max 3 lines / 200 codepoints>"
- affected_view: {which view/flow is affected}
- description: {what the usability problem is}
- user_impact: {concrete scenario: what happens to the user}
- suggested_fix: {concrete suggestion}
```

Pointer requirement: every `evidence:` block is a YAML list with at
least one pointer mapping (4 valid `kind` values: `file_range`,
`grep_match`, `dir_listing`, `file_exists`). A finding WITHOUT a
pointer is not a finding — engine check + validator block.

At the end: summary (critical/high/medium/low counts + overall +
top_risk).

## Output style

- Simulate concrete user scenarios, not abstract checks.
- "N3 violated" is not enough — describe WHAT the user
  experiences.
- Compute contrast values, don't estimate.
- User impact in one sentence: "user does X, experiences Y,
  expects Z".
- Severity by user frustration, not by framework weight.

## Output enforcement

A finding WITHOUT `user_impact` (concrete scenario) is not a UX
finding — it is checklist box-ticking.
