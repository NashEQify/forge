# Code reviewer persona conventions

Read it when writing or changing a code-reviewer persona (`agents/code-*.md`). Review seats do not load it; they read
`_protocols/reviewer-base.md` and their persona.

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

Protocols: `_protocols/reviewer-base.md`.

## Anti-rationalization
<persona-specific phrases — see convention below>

## Anti-patterns (P3)
<persona-specific anti-patterns — see convention below>

## Review questions (role-specific)
<persona-specific 5-step fill — see convention below>

## Check focus
<persona-specific check points>

## Finding prefix
<F-{ROLE-CODE}-{NNN}>

REMEMBER: <persona-specific tagline>
```

---

## Anti-rationalization — convention

Each persona has **at least 3** persona-specific anti-rat phrases
in bullet form. Pattern:

> "You say X — [counter-question / context-specific sharpening]"

Generic ones ("well structured", "otherwise solid", "can be changed later", accepting a hedge) need no repeat.

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

## Review questions — convention

The persona fills five steps with domain sharpening:

```markdown
## Review questions (role-specific)

1. INTENT:           <domain-specific INTENT question>
2. PLAN:             <domain-specific PLAN question>
3. SIMULATE:         <domain-specific SIMULATE question>
4. FIRST PRINCIPLES: <domain-specific first-principles question>
5. IMPACT:           <domain-specific IMPACT question>
```

The answers go into the `## Checked scope` section of `_protocols/reviewer-base.md`: step 1 → Purpose, steps 2
and 3 → Paths checked, step 4 → Assumption tested, step 5 → Consequence.

---

## Check focus — convention

Bullet list of persona-specific check points. **Domain specifics in
clear order**: what most often produces C/H findings comes first.

---

## Consumer-specific extension point

**Optional extension point** for consumers that want to add domain-
specific check patterns on top of the framework persona.

Framework personas do **not** carry a consumer section. Consumer
repos that use the framework personas as a base may add a
`### Consumer-specific` sub-section via persona-override files in
their own repo with concrete patterns / calls / schemas for their
stack (typical content: ORM parameterisation rules, lock-key
namespace, schema migration order, framework-specific exception
hierarchies, logging conventions, broker-reconnect logic). The
framework SoT carries no consumer content.

Language-stack conventions (e.g. Python structlog vs print, asyncpg
pool patterns, Pydantic `model_dump`/`model_validate`/`extra="forbid"`)
live in the matching language-stack skill (e.g.
`skills/python_code_quality_enforcement/`), not under this
extension point — they are stack-generic, not consumer-specific.

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
