# Deprecation and migration — deprecation decision

Step-loaded unit of `skills/deprecation_and_migration/SKILL.md`. Read it before starting a deprecation, when deciding
whether to maintain a system or sunset it, and when code shows zombie signs. Phases 3–4 (migration process and
patterns) are in `migration.md`.

### Phase 1: deprecation decision (5 mandatory questions)

Answer before starting deprecation:

```
1. Does this system still provide unique value?
   → Yes → maintain. No → continue.

2. How many users / consumers depend on it?
   → Quantify the migration scope (count, don't estimate).

3. Does a replacement exist?
   → No → build the replacement first. Never deprecate
   without an alternative.

4. What is the migration cost per consumer?
   → Trivially automatable → do it. Manual + high effort →
   weigh against maintenance cost.

5. What is the ongoing maintenance cost of NOT
   deprecating?
   → Security risk, engineer time, opportunity cost of the
   complexity.
```

**Decision:** when all 5 answers are deprecation-pro:
continue to phase 2. Otherwise: maintain with an owner
assignment + improve what is weak.

### Phase 2: classify compulsory vs advisory

| Type | When | Mechanism |
|---|---|---|
| **Advisory** | Migration optional, the old system is stable | Warnings + documentation + nudges. Users migrate on their own timeline. |
| **Compulsory** | Old system has security issues, blocks progress, or maintenance cost is unsustainable | Hard deadline. The old system is removed at date X. **Migration tooling required.** |

**Default:** advisory. Compulsory only when maintenance cost
or risk justifies forcing migration. Compulsory **requires**
migration tooling + documentation + support — not just a
deadline announcement.

### Phase 5: zombie-code handling

Zombie code = code that no one owns but everyone depends on.
Not actively maintained, no clear owner, accumulating
security vulnerabilities + compatibility issues.

**Signs:**
- No commits in 6+ months but active consumers exist.
- No assigned maintainer or team.
- Failing tests no one fixes.
- Dependencies with known vulnerabilities no one updates.
- Documentation referencing systems that no longer exist.

**Response (binary):**
- Assign an owner + maintain it properly — OR
- Start deprecation with a concrete migration plan.

**Zombie code must not stay in limbo** — either investment or
removal.
