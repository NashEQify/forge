# Code Reviewer Base Extended

**Loaded by:** all Code Review Board personas (`code-review`,
`code-adversary`, `code-security`, `code-data`, `code-reliability`,
`code-domain-logic`, `code-api-contract`, `code-ai-llm`,
`code-docs-consumer`, `code-spec-fit`, `code-spec-drift`,
`code-chief`).

**Position:** extends `_protocols/reviewer-base.md` (generic) and
`_protocols/code-reviewer-protocol.md` (code-specific) with the
code-reviewer persona conventions. Loaded in addition to both.

**Created:** 2026-04-30 (Cluster 5 council hybrid migration).
**Purpose:** code-reviewer persona standard pattern as a single
source of truth — pattern replication in persona files reduced,
consistency centralized.

---

## Pattern convention per code-reviewer persona

Each code-reviewer persona MUST share the same **section structure**
(order, section headers). Content per section is persona-specific.

### Required sections in every persona

```markdown
---
name: <persona-name>
description: <core role in 1 sentence, with "Use when ..." trigger>
---

# Agent: <persona-name>

<1-2 sentences for role + boundary where needed>

Protocols: `_protocols/reviewer-base.md`,
`_protocols/code-reviewer-protocol.md`,
`_protocols/code-reviewer-base-extended.md` (this file).
[Plus optional: `_protocols/reviewer-reasoning-trace.md`,
`_protocols/first-principles-check.md` when drill+trace are
required.]

## Anti-rationalization
<persona-specific phrases — see convention below>

## Anti-patterns (P3)
<persona-specific anti-patterns — see convention below>

## Reasoning (role-specific)
<persona-specific 5-step fill — see convention below>

## Check focus
<persona-specific check points>

### BuddyAI-specific (optional)
<domain-specific BuddyAI patterns when relevant>

## Finding prefix
<F-{ROLE-CODE}-{NNN}>

REMEMBER: <persona-specific tagline>
```

---

## Anti-rationalization — convention

Each persona has **at least 3** persona-specific anti-rat phrases
in bullet form. Pattern:

> "You say X — [counter-question / context-specific sharpening]"

Generic anti-rat patterns (defined in
`_protocols/reviewer-base.md`, do NOT replicate them in personas):
- "Well structured" — structure isn't correctness
- "Otherwise solid" — did you actually check everything?
- "Can be changed later" — is it really reversible?
- Vague phrasing ("if needed", "as appropriate") — every hedge is
  a hole

Persona-specific anti-rat extends these with domain patterns.

**Closing sentence (convention):** *"If you're writing an
explanation instead of a counter-argument: stop."* OR an equivalent
persona closing.

---

## Anti-patterns (P3) — convention

Format: **NOT: ... INSTEAD: ...** bullet list.

Each persona has **at least 3** persona-specific anti-patterns. At
least one anti-pattern addresses the persona's domain boundary
(e.g. code-adversary: "NOT: code-quality findings. INSTEAD: that's
code-quality's job."). The Code Review Board is a multi-persona
board — domain bleed is the standard anti-pattern.

---

## Reasoning — convention

The 5 steps are filled in **role-specifically**. The generic
5-step frame is defined in `_protocols/code-reviewer-protocol.md`.
The persona fills each step with domain sharpening:

```markdown
## Reasoning (role-specific)

1. INTENT:           <domain-specific INTENT question>
2. PLAN:             <domain-specific PLAN question>
3. SIMULATE:         <domain-specific SIMULATE question>
4. FIRST PRINCIPLES: <domain-specific first-principles question>
5. IMPACT:           <domain-specific IMPACT question>
```

**Visible-output requirement** (from
`_protocols/code-reviewer-protocol.md`):
- Steps 1/2/3/5 → `## Reviewer-Reasoning-Trace` section in the
  output (via `_protocols/reviewer-reasoning-trace.md`).
- Step 4 → `## Reviewer-First-Principles-Drill` section in the
  output (via `_protocols/first-principles-check.md`).
- Bind rule: ≥1 finding references a drill element / trace element.

---

## Check focus — convention

Bullet list of persona-specific check points. **Domain specifics in
clear order**: what most often produces C/H findings comes first.

---

## BuddyAI sub-section — convention

**Optional but recommended** when the persona's domain has
recognizable specifics in BuddyAI / forge code patterns.
Sub-section header: `### BuddyAI-specific`.

Bullet list with concrete BuddyAI patterns / calls / schemas.
Examples:
- code-data: `asyncpg: $1, $2 parameters (no f-string)`,
  `Alembic: migration order`, `pg_advisory_lock: lock-key
  namespace`
- code-reliability: `pg_advisory_lock cleanup on connection drop`,
  `NATS reconnect resume logic`

Generic BuddyAI checks (from `_protocols/code-reviewer-protocol.md`,
do NOT replicate):
- structlog instead of print/logging
- asyncpg connection-pool patterns
- Pydantic `model_dump` vs `dict`, `model_validate` vs constructor,
  `extra="forbid"`
- AppError instead of HTTPException (Task 265)
- Resource cleanup with `async with`

---

## Required output fields per persona — convention

Some personas have **domain-specific required output fields**
(output-schema constraint, semantic discipline anchor). These fields
MUST appear in every finding from that persona — not optional.

Today's required fields:

| Persona | Required output field | Threshold |
|---|---|---|
| code-adversary | `attack_scenario` | every finding |
| code-security | `attack_vector` | C/H |
| code-performance (in code-review) | `cost_estimate` | C/H |
| code-reliability | `failure_scenario` | C/H |
| code-domain-logic | `concrete_input`, `expected_output`, `actual_output` | C/H |
| code-data | `data_impact` | every finding |
| code-spec-fit | `spec_ref` | every finding |
| code-spec-drift | `Type` (MATCH/SPEC-GAP/SPEC-DRIFT/CODE-BUG), `Spec Section`, `Code Evidence`, `What the code does`, `What the spec says`, `Proposed spec update`, `DIM affected` | every finding |

**Convention:** required output fields are documented explicitly
inside the persona (last line before REMEMBER, e.g. *"Additional
output field: `attack_scenario` (REQUIRED — no finding without a
concrete scenario)."*).

---

## Finding prefix — convention

Format: `F-{ROLE-CODE}-{NNN}`.

Today's role codes:
- F-CR-: code-review (multi-axis: correctness + architecture +
  performance)
- F-CA-: code-adversary
- F-CS-: code-security
- F-CB-: code-data
- F-CL-: code-reliability
- F-CD-: code-domain-logic
- F-CC-: code-api-contract
- F-AI-: code-ai-llm
- F-DC-: code-docs-consumer
- F-CF-: code-spec-fit
- F-CSD-: code-spec-drift
- C-: code-chief (consolidated, no F prefix)

**Multi-axis consolidation:** F-CQ (formerly code-quality), F-CR
(formerly code-architecture), F-CP (formerly code-performance) were
consolidated to F-CR (code-review). Axis marker in the finding body
(`Axis: Correctness | Architecture | Performance`).

---

## Drill+Trace convention

**For L2 Full Board:** code-chief enforces on every raw reviewer:
- `## Reviewer-First-Principles-Drill` (required section)
- `## Reviewer-Reasoning-Trace` (required section)

Bind rule: ≥1 finding references a drill element / trace element.

Missing → F-C-DRILL-MISSING / F-C-TRACE-MISSING from the chief,
re-dispatch (max 1), then ESCALATE.

**For code-review (multi-axis persona):** drill+trace are enforced
**per axis**. One drill section per axis with its own bind rule to
at least 1 axis finding. One trace section per axis analogously.
This prevents a single-agent / single-drill setup from "satisfying"
all 3 axes with one bind.

---

## Output style (OCR — from code-reviewer-protocol.md)

- Be constructive — propose improvements, don't just criticize.
- Explain why — help the developer learn.
- Prioritize by impact — relevant issues before personal
  preferences.
- Show examples — point at the better way instead of just saying
  "this is bad".
- Acknowledge good code — reinforce positive patterns (see `## What's
  Working Well` from reviewer-base.md).

---

## Boundary against code-reviewer-protocol.md and reviewer-base.md

This file **extends** code-reviewer-protocol.md, it does not
**duplicate** it. On conflict: code-reviewer-protocol.md wins (it
is the original code-reviewer protocol). This file conventionalizes
persona patterns and documents required output fields.

reviewer-base.md is **generic for all reviewers** (Spec / Code /
UX). This file is **Code-Board-specific** and may extend
reviewer-base.md with code-domain conventions.

**Load order in every code-reviewer persona:**
1. `_protocols/reviewer-base.md` (generic)
2. `_protocols/code-reviewer-protocol.md` (code domain)
3. `_protocols/code-reviewer-base-extended.md` (this file —
   code-persona pattern convention)
4. `_protocols/reviewer-reasoning-trace.md` (drill required)
5. `_protocols/first-principles-check.md` (trace required)
