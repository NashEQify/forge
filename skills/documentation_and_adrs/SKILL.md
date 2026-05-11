---
name: documentation-and-adrs
description: >
  Capture decisions and documentation — why, alternatives,
  trade-offs. ADR discipline, README / changelog, API docs,
  agent-ready rules (CLAUDE.md). Adapted from
  addyosmani/agent-skills; MIT, see ## Source.
status: active
invocation:
  primary: workflow-step
  secondary: [user-facing]
disable-model-invocation: false
uses: []
---

# Skill: documentation-and-adrs

## Source

Upstream:
[documentation-and-adrs/SKILL.md](https://github.com/addyosmani/agent-skills/blob/main/skills/documentation-and-adrs/SKILL.md)
(MIT, Copyright Addy Osmani, 2025). Content for
forge extended with repo paths and contracts.

## Purpose

Document **decisions**, not just code. The valuable part is
the *why* context: constraints, rejected alternatives,
trade-offs. Code shows *what* was built; docs explain *why
this way* and *what was not chosen*. That's what later humans
and agents need.

## Framework paths (consumer repo)

| Artifact | Canonical location (BuddyAI / framework consumer) |
|----------|---------------------------------------------------|
| ADR / architecture decision | `docs/decisions/` (see also the `knowledge_capture` skill, knowledge type **Decision**) |
| Solve / large research | `docs/solve/`, `docs/research/` |
| Architecture notes | `docs/architecture/` |

### ADR path override (project-local adaptation)

Lookup order when an ADR is written:

1. **`<repo-root>/.adr-config.yaml`** — when present, use the
   `decisions_path:` field. Format:
   ```yaml
   decisions_path: docs/architecture/decisions/
   ```
2. **`<repo-root>/docs/STRUCTURE.md`** — when present, grep
   for the pattern `decisions: <path>` OR a table row with an
   ADR / decisions column. The first match wins.
3. **Default:** `docs/decisions/` (forge
   convention).

The override applies to ALL ADR writes via this skill — also
for `adr-check` workflow steps and manually invoked ADR
creation.

**Verification rule:** when the override is set but the path
doesn't exist, the skill creates the directory (`mkdir -p`) —
not a fail. The existence check is part of the skill contract.

## When to use

**Mechanically triggered by an optional `adr-check` step in:**

| Workflow | Position | File |
|---|---|---|
| `build` (standard / full / sub-build) | Verify phase, after `spec-co-evolve-check`, before `task-status-done` | `workflows/runbooks/build/workflow.yaml` |
| `solve` | Phase 5 execute, after `apply-artifact`, before `knowledge-processor` | `workflows/runbooks/solve/workflow.yaml` |

The step is `required: false`, `on_fail: warn` — discipline
through visibility, no block on trivial iterations. The
substantive check is the **ADR-discipline triple** below — the
workflow step triggers the skill; the skill verifies the
triple.

**Substantive triggers (independent of the workflow step):**

- Significant architecture decision.
- A choice between competing approaches.
- Public API change or new introduction.
- Feature with user-visible behaviour.
- Onboarding / agent context (the same explanation comes up
  again and again).

**Not:** commenting on obvious code. No docs for throwaway
prototypes without a persistence decision.

## Architecture Decision Records (ADRs)

### When to write an ADR

#### ADR-discipline triple (required threshold, pattern lift Phase G tier-2 from Pocock grill-with-docs)

Offer / write an ADR **only when all three** conditions are
met:

1. **Hard-to-reverse** — the cost to change again is
   meaningful.
2. **Surprising-without-context** — a future reader (human or
   agent) would ask "why this way? why not X?".
3. **Result-of-real-trade-off** — there were genuine
   alternatives; you chose this one for concrete reasons.

If even **one** of the three is missing → no ADR. Skip is fine
on:
- Ephemeral reasons ("not the focus right now", "not worth the
  effort").
- Self-evident decisions ("obviously the standard way").
- Reversible choices ("can change next week if it's wrong").

Anti-pattern: ADR inflation. Every decision becoming an ADR is
documentation theatre.

#### Typical triggers (when the triple holds)

- Framework, library, heavy dependency.
- Data model / schema.
- Auth strategy.
- API form (REST vs events vs ...).
- Build hosting / infra with high switching cost.
- Any decision that is expensive to undo.

### ADR template

ADRs in `docs/decisions/` with an incrementing number (prefix
`ADR-NNN` in the title):

```markdown
# ADR-001: Use PostgreSQL for primary database

## Status
Accepted | Superseded by ADR-XXX | Deprecated

## Date
2025-01-15

## Context
We need a primary database for the task management application. Key requirements:
- Relational data model (users, tasks, teams with relationships)
- ACID transactions for task state changes
- Support for full-text search on task content
- Managed hosting available (for small team, limited ops capacity)

## Decision
Use PostgreSQL with Prisma ORM.

## Alternatives Considered

### MongoDB
- Pros: flexible schema, easy to start with
- Cons: our data is inherently relational; we'd have to manage relationships manually
- Rejected: relational data in a document store leads to complex joins or data duplication

### SQLite
- Pros: zero configuration, embedded, fast for reads
- Cons: limited concurrent write support, no managed hosting for production
- Rejected: not suitable for a multi-user web application in production

### MySQL
- Pros: mature, widely supported
- Cons: PostgreSQL has better JSON support, full-text search, and ecosystem tooling
- Rejected: PostgreSQL is the better fit for our feature requirements

## Consequences
- Prisma provides type-safe database access and migration management.
- We can use PostgreSQL's full-text search instead of adding Elasticsearch.
- Team needs PostgreSQL knowledge (standard skill, low risk).
- Hosting on a managed service (Supabase, Neon, or RDS).
```

### ADR lifecycle

```
PROPOSED → ACCEPTED → (SUPERSEDED or DEPRECATED)
```

- Don't **delete** old ADRs — historical context.
- Change: write a new ADR, link the old one via "superseded
  by".

## Inline documentation

Comment on **why**, not **what** (see upstream good / bad
examples in TS / JS — same logic in Python: magic numbers,
race windows, invariants before call X).

**Gotchas:** non-obvious constraints at the call site;
reference an ADR when the rationale is longer.

## API documentation

- Public APIs: types / docstrings (Python), OpenAPI where
  available.
- Document failure cases and throws — that's part of the
  contract.

## README / changelog

README: a one-paragraph purpose, quickstart, command table,
architecture pointer to ADRs.
Changelog: for releases with Added / Fixed / Changed —
consistent with the consumer-repo convention.

## Documentation for agents

- `CLAUDE.md` / `AGENTS.md` — project rules.
- Specs — let them build what is specified.
- ADRs — prevent agents from re-negotiating old decisions.
- Inline gotchas — avoid known traps.

## Common rationalizations (upstream)

| Rationalization | Reality |
|---|---|
| "Code is self-explanatory" | Code shows what, not why or alternatives. |
| "Docs when the API is stable" | The API gets more stable when docs find the design flaw early. |
| "Nobody reads docs" | Agents and you in three months read them. |
| "ADRs are overhead" | A short ADR saves long reviews later. |

## Red flags

- Architecture without written rationale.
- Public API without docs / types.
- README without quickstart.
- Commented-out code instead of deletion.
- TODOs that linger for weeks.
- No ADRs despite heavy decisions.
- Docs that just repeat the code.

## Verification

After documentation work:

- [ ] ADRs for significant architecture decisions (or
  intentionally dropped with a short note).
- [ ] README: quickstart + commands + architecture reference.
- [ ] Public APIs documented with params / return / errors.
- [ ] Gotchas where they apply.
- [ ] No dead commented-out code.
- [ ] Rule files consistent with behaviour.

## Contract

### INPUT

- **Required:** decision context (problem, options,
  constraints) or an existing ADR on update.
- **Optional:** link to a task ID / spec ref.
- **Context:** consumer `docs/STRUCTURE.md`,
  `knowledge_capture` for routing Decision → `docs/decisions/`.

### OUTPUT

**DELIVERS:** an ADR draft or a README / changelog section,
consistent paths.
**DOES NOT DELIVER:** changing production code (→ MCA); fixing
spec content (→ spec_authoring / spec workflow).
**ENABLES:** council / review traceable; agents use the
why context.

### DONE

- ADR has status, date, context, decision, alternatives,
  consequences (or a deliberately shortened variant with a
  reference).
- Paths fit the target repo.

### FAIL

- **Retry:** missing alternatives section on a real choice —
  pull it in.
- **Escalate:** opposite of an existing ADR without a
  supersede chain.
- **Abort:** no write access to the target path (frozen zone)
  — escalate to Buddy.

## Boundary

- No **spec_board** / spec-quality review — only the
  decision / docs artifact.
- No **knowledge_processor** fact stream — here structured
  decisions, not session facts.
- No **testing** — test plans stay with the tester / testing
  skill.

## Anti-patterns

- **NOT** the why in a 20-line comment instead of an ADR on
  hard-to-reverse choices. **INSTEAD** ADR + a one-line
  reference in the code.
- **NOT** an ADR without a rejected alternative. **INSTEAD**
  at least one real alternative with pros / cons.
- **NOT** a README duplicate of the spec. **INSTEAD** the
  README links specs and ADRs.
