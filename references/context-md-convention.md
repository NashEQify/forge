# CONTEXT.md per-project convention

> **Source:** pattern from `github.com/mattpocock/skills`
> (formerly `skills/deprecated/ubiquitous-language/SKILL.md` plus
> `skills/engineering/grill-with-docs/CONTEXT-FORMAT.md`,
> 2026-05-01). MIT licence.
>
> **Adaptation status:** the `ubiquitous_language` skill is
> self-deprecated by Pocock, **but the pattern lives on** in
> `grill-with-docs`. Documented as a convention here, not as a separate
> skill (avoids inflation, was the 366-G.4 decision correction).

**Pattern in one sentence:** one `CONTEXT.md` per repo at the repo
root with a domain glossary — term / definition / aliases-to-avoid.
Lazy-create when the first term is resolved.

## When to apply

**Repo scope:**
- Repos with their own domain vocabulary (BuddyAI / Huddle / personal /
  infra).
- When terms like "Order" / "Customer" / "Brain" / "Context-Assembly"
  are interpreted differently by devs / agents (drift risk).
- When CLAUDE.md / AGENTS.md hold consensus but domain terminology is
  not centrally fixed.

**Don't apply:**
- Greenfield project without enough domain maturity (premature).
- Repos with existing domain docs that already do this (e.g. an
  existing `glossary.md` or `domain-model.md`).
- Pure generic code without a domain (tools / utilities / etc).

## Format

`CONTEXT.md` at the repo root or in the consuming area:

```markdown
# Project Context

## [Subdomain 1] (e.g. "Order lifecycle")

| Term        | Definition                                  | Aliases to avoid     |
| ----------- | ------------------------------------------- | -------------------- |
| **Order**   | A customer's request to purchase items      | Purchase, transaction|
| **Invoice** | Request for payment after delivery          | Bill, payment request|

## [Subdomain 2] (e.g. "People")

| Term         | Definition                                 | Aliases to avoid       |
| ------------ | ------------------------------------------ | ---------------------- |
| **Customer** | Person/Org that places orders              | Client, buyer, account |
| **User**     | Authentication identity in the system      | Login, account         |

## Relationships

- An **Invoice** belongs to exactly one **Customer**
- An **Order** produces one or more **Invoices**

## Example dialogue

> **Dev:** "When a **Customer** places an **Order**, do we create the
> **Invoice** immediately?"
>
> **Domain expert:** "No — an **Invoice** is only generated once a
> **Fulfillment** is confirmed."

## Flagged ambiguities

- "account" was used to mean both **Customer** and **User** — these are
  distinct concepts: a **Customer** places orders, while a **User** is
  an authentication identity.
```

## Multi-context repos: CONTEXT-MAP.md

For repos with multiple distinct sub-contexts (e.g. BuddyAI with brain /
context-assembly / materialization as separate concepts): at repo
root, a `CONTEXT-MAP.md` pointing to sub-CONTEXT.md files.

```
/
├── CONTEXT-MAP.md
├── docs/
│   └── adr/                          ← system-wide ADRs
├── src/
│   ├── brain/
│   │   ├── CONTEXT.md                ← brain vocabulary (entity / edge / materialization)
│   │   └── docs/adr/
│   ├── context_assembly/
│   │   ├── CONTEXT.md                ← assembly vocabulary (greedy allocation / token budget)
│   │   └── docs/adr/
│   └── api/
│       ├── CONTEXT.md                ← API vocabulary (endpoint / schema / boundary)
│       └── docs/adr/
```

Lazy-create: files emerge when the first term is resolved. No
"define everything upfront".

## Discipline

**Be opinionated.** When several words exist for the same concept,
pick the best and list the others as aliases-to-avoid.

**Flag conflicts explicitly.** When a term is used ambiguously in a
conversation, call it out in the "Flagged ambiguities" section.

**Only domain terms.** Skip generic programming concepts (array,
function, endpoint) **unless** they have domain-specific meaning in
your repo.

**Tight definitions.** One sentence max. Define what it IS, not what
it does.

**Show relationships.** Bold term names + cardinality where obvious.

**Example dialogue.** Short conversation (3–5 exchanges) between dev
and domain expert that makes term boundaries clear.

## Update discipline (inline)

When a term is resolved during a conversation → update CONTEXT.md
**inline**. Don't batch. Pattern from `improve_codebase_architecture`
and `spec_authoring` grilling mode (phase G tier-2 pattern lifts).

## Status for forge itself

The forge repo already has established domain glossaries:

| Concept | SoT |
|---|---|
| Skill / workflow / persona / protocol | `framework/skill-anatomy.md` §ontological separation |
| Capability vs utility (single-class) | `framework/skill-anatomy.md` §D.6 decision |
| L1 / L2 code review board | `skills/code_review_board/SKILL.md` |
| Standard / deep spec board | `skills/spec_board/SKILL.md` |
| Mode convention (quick / standard / deep, depth / topic / phase) | `framework/skill-anatomy.md` §mode convention |
| Invocation axis (user-facing / workflow-step / sub-skill / hook / cross-cutting) | `framework/skill-anatomy.md` frontmatter schema |
| Frame step names | `skills/frame/SKILL.md` |
| Build / solve / fix workflow phases | the respective `WORKFLOW.md` |

**Consequence for forge:** no separate `CONTEXT.md` at
the framework root needed — the existing files are the glossary SoT.
A CONTEXT.md would be duplication.

**Consequence for consumer repos:** when BuddyAI / Huddle / personal /
infra have their own domain vocabularies (brain / context-assembly /
materialization for BuddyAI, LiveKit channel / room / user for
Huddle, etc.): **lazy-create their own CONTEXT.md there**.

## See also

- `skills/spec_authoring/SKILL.md` phase 1 grilling mode — uses the
  CONTEXT.md inline update pattern.
- `skills/improve_codebase_architecture/SKILL.md` phase 3 — invokes
  the CONTEXT.md pattern on naming decisions.
- `skills/documentation_and_adrs/SKILL.md` — ADR format complementary.
- `framework/skill-anatomy.md` — framework-internal glossary SoT.
