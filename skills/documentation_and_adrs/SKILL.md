---
name: documentation-and-adrs
description: >
  Capture decisions + documentation with the why, alternatives, and trade-offs
  — ADRs, README / changelog, API docs, agent-ready rules (CLAUDE.md). Triggers
  when an architecture/API decision needs capturing (after the decision, or
  before save); NOT for inline code comments.
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

| Artifact | Canonical location (framework consumer) |
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

#### Close-phase: consume the close_retro retro (build / solve)

At a build or solve close where `close_retro` fired, run the triple over the
retro's **§Stale-Decisions** rows (each = a T0 decision + a T1 invalidator,
`docs/<workflow>/<slug>-retro.md`) instead of re-extracting from raw
artifacts: which of those met hard-to-reverse + surprising-without-context +
result-of-real-trade-off → write the ADR. No retro present, or no qualifying
row → one-line skip. (spec 374 §6.)

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

## Independent verify-pass (code-mechanics claims)

The author is the worst checker of their own mechanical claims:
evidence-pointer-at-write (`CLAUDE.md` Inv 10) makes a claim auditable
but does NOT catch a MISREAD — the author can cite the right line and
still conclude wrong. The only thing that catches a misread is an
independent reader. So for the artifact class most prone to it, the
verify-pass is a **default, not a user-initiated "send it to council"**.

Design rationale + the rejected alternatives: **ADR-008**
(`docs/decisions/ADR-008-independent-verify-pass-semantics.md`). Read it
before changing the trigger or the tiers — the semantics below are a
deliberate hard-to-reverse call, not a default.

### Trigger — observable signal, NOT author self-assessment

The firing condition must NOT rest on the author judging "is my claim
consequential?" — that re-imports the exact author-lens the discipline
distrusts, and lets a misreading author self-declare out of the check
(the under-coverage failure). Fire on an OBSERVABLE property instead:

> **The artifact NAMES or CITES code mechanics** — a code symbol, a
> `file:line`, a hook / check / engine-field / step name, or a sentence
> asserting what a subsystem *does* ("the engine reads X", "the hook
> blocks Y", "A publishes to B"). If it does → the verify-pass fires by
> DEFAULT.

Skip is allowed only on a SHORT, explicit, RECORDED exception — never a
silent self-waiver:

- the artifact is throwaway scratch (not propagated, not authoritative);
- the claim is trivially self-evident at the cited line (a one-token
  read, no interpretation);
- the claim is reversible within the session and nothing downstream acts
  on it yet.

A skip costs a one-line reason next to the claim (`verify-pass skipped:
<which exception>`), so the skip is itself auditable. Default = fire;
the burden is on skipping, not on firing. (Contrast the ADR-triple above,
which gates AGAINST inflation — here under-coverage is the enemy, so the
bias is reversed: fire broadly.)

### Two tiers — breadth by default, depth by stakes (Hybrid, ADR-008)

A single same-model cold-start reader does NOT reliably catch a misread
— empirically the historical misreads were caught by a human + a
multi-perspective council, not one cold reader. So the floor is honest
about its ceiling, and stakes escalate depth:

- **Floor (default, broad):** dispatch ONE context-isolated cold-start
  reviewer that reads the cited code and returns a verdict. It RAISES
  the odds of catching a misread; it does NOT guarantee it. Cheap, fires
  on the whole observable-signal class — this is the breadth that closes
  the under-coverage gap.
- **Stakes-escalation (depth):** when the code-claim is
  consequential/hard-to-reverse (a downstream consumer will act on it as
  authority — schema, contract, public surface, a claim that gates other
  work), escalate to MULTI-perspective: ≥2 different lenses / an
  adversary / a council. One reader is structurally insufficient for the
  misread at this stakes level; the diversity is the catch.

Stakes here gate DEPTH (floor vs multi-perspective), never WHETHER the
pass fires — that is the §Trigger's observable signal. This is the
correction of the original single-tier design (see ADR-008).

### Reviewer contract + Invariant-1 boundary

The verify-pass is a DISPATCHED reviewer, never Buddy self-verifying —
Buddy dispatches + reads the verdict signal (Invariant 1: Buddy is the
dispatcher, not the verifier). The reviewer is context-isolated per
`skills/_protocols/dispatch-template.md` and returns:

- a verdict label — `CLAIMS-HOLD` / `CLAIMS-HOLD-WITH-NITS` /
  `CLAIMS-BROKEN`;
- per claim checked: an evidence pointer
  (`skills/_protocols/evidence-pointer-schema.md`) to the line it read;
- the lens it used (so "different lens" is shown, not asserted).

`CLAIMS-BROKEN` blocks the artifact from being treated as authoritative
until re-authored + re-passed.

### Enforcement class (honest)

This is **[WORKFLOW] / [DISCIPLINE]**, not **[STRUCTURAL]**: there is no
pre-commit hook and no script that fires it. It is wired as a contract of
THIS skill — when `documentation_and_adrs` is invoked (the `adr-check`
step in build-verify / solve-execute, see §When to use) AND the
§Trigger's observable signal is present, running the verify-pass is part
of the skill's DONE. That is as mechanical as it gets without a hook; do
not over-state it as automatic enforcement. The pre-commit
SOURCE-VERIFICATION check governs *reviewer* outputs (machine-checked
pointers); this governs *authored* artifacts (a dispatched reader
verifies the claims).

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
- [ ] Code-mechanics claims: load-bearing positive claims carry an
  evidence pointer at write time (Inv 10); on the verify-pass trigger
  (§Independent verify-pass — observable-signal fire, not self-assessed),
  a dispatched cold-start reviewer verified them (floor), escalated to
  multi-perspective when the claim is consequential, before the artifact
  was treated as authoritative.

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
