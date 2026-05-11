# Protocol: Skill Guardrails (boundary + anti-patterns)

Required structure for skill failure-mode documentation. Loaded by
spec_board when reviewing SKILL.md artifacts. Ensures every skill in
the framework names its mis-application risks explicitly.

## Two distinct guardrails

The framework has two functionally related but semantically distinct
protective sections:

| Section | Purpose | Format | Focus |
|---------|---------|--------|-------|
| **Boundary** | routing protection (wrong-skill selection) | "This skill is NOT for X — use Y instead" | skill boundary |
| **Anti-patterns** | execution protection (wrong-execution-within-skill) | "NOT X — INSTEAD Y. Because: Z" | usage discipline |

**Boundary** prevents the wrong skill from being selected.
**Anti-patterns** prevents the right skill from being executed
wrongly.

Both are guardrails, but for different failure sources. Many skills
need both. Some need only one.

## Required matrix

Which section(s) are required per skill type:

| Skill type | Boundary | Anti-patterns | Rationale |
|-----------|:---:|:---:|-------------|
| **Workflow** (end-to-end flow) | required | required | long flows, drift risk, phases can be misused |
| **Capability** (callable capability) | required | required | discretion in dispatch, agent behaviour can drift |
| **Protocol** (rule set) | required | optional | small rule sets; anti-patterns only when interpretation latitude exists |
| **Utility** (single function) | required | optional | mostly mechanical; anti-patterns only on complex utilities with modes / routing |

**Default:** boundary is ALWAYS required (every skill must say what
it does NOT do). Anti-patterns are required only where interpretation
latitude enables wrong execution.

## Format conventions

### Boundary format

```markdown
## Boundary

- **No X.** That's what skill Y is for. (If Y exists: provide the
  path.)
- **Not Z.** Z belongs in <other area / other skill / other
  process>.
```

3-5 entries. Each line: what NOT + where instead.

### Anti-patterns format (standard: NOT / INSTEAD)

```markdown
## Anti-patterns

- **NOT** [wrong action]. **INSTEAD** [right action]. Because:
  [reason].
- **NOT** [...]. **INSTEAD** [...]. Because: [...].
```

3-5 entries. Each entry: concrete misapplication + correction +
why.

### Anti-patterns exception: board-agent personas

Board-agent personas (`agents/board-*.md`, `agents/code-*.md`)
keep their **"You're saying X — did you check Y?"** format. That's
a different kind of anti-pattern (named traps as inner-dialog
triggers) which works specifically for reviewer agents. That
format is NOT carried over to skills, and skills do NOT use it.

Rationale: reviewer agents are guarded against their own
rationalization. Skills are executed procedures, where
NOT/INSTEAD is more direct.

## Self-check for skill authors

1. **Boundary:** how would the wrong skill be picked for a task?
   What would you have to say to prevent it?
2. **Anti-patterns:** when the skill is picked correctly but
   executed wrongly — which concrete traps? At least 3.
3. **Skill-specific, not generic:** "DO NOT work superficially" is
   worthless. "DO NOT skip step 3 because it looks like a
   protocol" is skill-specific.

## Spec Board enforcement

When reviewing a SKILL.md artifact via spec_board:

1. Chief checks the required matrix against the skill type.
2. Missing required section → automatic HIGH finding.
3. Generic anti-patterns (not skill-specific) → MEDIUM finding.
4. Fewer than 3 anti-patterns for a required type → HIGH finding.
5. The board cannot PASS while a guardrail finding is open.

## Relation to other protocols

- `consolidation-preservation.md`: prevents silent loss in board
  consolidation.
- `piebald-budget.md`: prevents budget drift on refactoring.
- `skill-guardrails.md` (this one): prevents skills being created
  without misapplication protection.

All three are hard gates in the spec_board review loop.
