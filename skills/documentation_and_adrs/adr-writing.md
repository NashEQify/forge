# Documentation and ADRs — writing an ADR

Step-loaded unit of `skills/documentation_and_adrs/SKILL.md`. Read it once the ADR-discipline triple (in `SKILL.md`)
holds and an ADR is written, including the close-bookkeeping ADR sub-step, and when an ADR is superseded or
deprecated.

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
for the close-bookkeeping ADR sub-step and manually invoked ADR
creation.

**Verification rule:** when the override is set but the path
doesn't exist, the skill creates the directory (`mkdir -p`) —
not a fail. The existence check is part of the skill contract.

### ADR template

ADRs in `docs/decisions/` with an incrementing number (prefix
`ADR-NNN` in the title):

```markdown
# ADR-001: Use PostgreSQL for primary database

## Status
Accepted | Superseded by ADR-XXX | Deprecated

## Date
YYYY-MM-DD

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
