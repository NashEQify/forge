---
name: deprecation-and-migration
description: >
  Deprecation and migration discipline (code-as-liability; strangler / adapter /
  feature-flag patterns; churn + zombie-code handling). Use when removing an old
  system / API / feature, migrating users to a new implementation, or deciding
  maintain vs sunset.
status: active
invocation:
  primary: user-facing
  secondary: [workflow-step]
  trigger_patterns:
    - "deprecate"
    - "sunset"
    - "remove old system"
    - "migration plan"
    - "zombie code"
    - "altlasten"
    - "entfernen"
disable-model-invocation: false
---

# Skill: deprecation-and-migration

## Purpose

Code is liability, not asset. Every line of code carries
maintenance cost — fixing bugs, updating dependencies,
applying security patches, onboarding new engineers.
Deprecation is the discipline of removing code that no longer
earns its effort. Migration is the process of moving users
safely from old to new.

Most engineering organizations are good at building. Few are
good at removing. This skill closes the gap.

Formalizes the existing STALE-CLEANUP invariant (CLAUDE.md
§5) at the skill level — when / how to deprecate is a
methodology question, not just a cleanup sweep.

## Source

Lifted from `github.com/addyosmani/agent-skills`
(`skills/deprecation-and-migration/SKILL.md`).
**Adapted** to the forge reality:
- STALE-CLEANUP invariant (CLAUDE.md §5) as the
  same-commit cleanup discipline.
- Default to `git rm` on consolidation — git history is
  the archive; no `_archived/` shadow tree.

## Standalone

Distinct from:
- `skills/_protocols/skill-guardrails.md` —
  skill-specific anti-patterns, not the deprecation
  lifecycle.
- `framework/skill-anatomy.md` §Consolidation mechanic —
  describes the skill-as-mode-absorbed mechanism.
  deprecation-and-migration is broader (also code, APIs,
  modules, whole systems — not just skills).
- STALE-CLEANUP invariant (CLAUDE.md §5) — the same-commit
  ref-cleanup discipline Buddy applies on removal. This
  skill is the **decision discipline** (when / how) behind
  that cleanup.

What only this skill delivers:
- Deprecation-decision framework (5 questions before
  deprecation start).
- Compulsory-vs-advisory classification with trigger
  conditions.
- Migration process (build replacement first → announce →
  incremental → remove).
- 3 migration patterns (strangler / adapter / feature flag).
- The churn rule (owner responsibility for migration).
- Zombie-code diagnosis + treatment.

## When to call

- Replace an old system / API / library with a new one.
- Sunsetting a feature that is no longer needed.
- Consolidating duplicate implementations.
- Removing dead code that no one owns but everyone depends
  on (zombie code).
- Lifecycle planning for a new system (deprecation planning
  starts at design time).
- Decision: maintain a legacy system or invest in
  migration?

### Do not call for

- Pure skill-as-mode consolidation (e.g. ux_review →
  spec_board mode=ux) →
  `framework/skill-anatomy.md` §Consolidation mechanic.
- Mechanical STALE-CLEANUP after a rename → the
  stale-cleanup sweep (invariant 5).

## Process

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

### Phase 3: migration process

#### Step 1: build the replacement

Don't deprecate without a working alternative. The replacement
must:
- Cover every critical use case of the old system.
- Have documentation + a migration guide.
- Be proven in production (not just "theoretically better").

#### Step 2: announce + document

```markdown
## Deprecation Notice: OldSystem

**Status:** Deprecated as of YYYY-MM-DD
**Replacement:** NewSystem (see migration guide below)
**Removal date:** Advisory — no hard deadline OR YYYY-MM-DD (compulsory)
**Reason:** [Why: security / maintenance / better design / consolidation]

### Migration Guide
1. [Concrete step 1]
2. [Concrete step 2]
3. [Verification: how to test the migration succeeded]
```

Cross-ref to `skills/documentation_and_adrs/` for an ADR on a
substantial deprecation decision.

#### Step 3: migrate incrementally

Consumer by consumer, not all at once. Per consumer:

```
1. Identify every touchpoint with the deprecated system.
2. Update to use the replacement.
3. Verify behaviour matches (tests + integration checks).
4. Remove references to the old system.
5. Confirm: no regressions.
```

**The churn rule:** when YOU own the deprecating
infrastructure, YOU are responsible for the user migration —
or for backward-compatible updates that don't require
migration. **No announce-and-leave-users-alone.**

#### Step 4: remove the old system

Only **after** every consumer has migrated:

```
1. Verify zero active usage (metrics, logs, dependency analysis, grep).
2. Remove the code with `git rm` — git history is the archive.
3. Remove associated tests, documentation, configuration.
4. Remove the deprecation notices themselves (they served their purpose).
5. Celebrate — removing code is an achievement.
```

**STALE-CLEANUP invariant (CLAUDE.md §5) in the same commit:**
clean every active ref in non-frozen files. `grep -rn <artifact>`
+ frozen-zone filter finds the obvious refs — but it does NOT prove
the cleanup is complete. A retired name lives in an OPEN form-space
(canonical, label, spaced, prose paraphrase); a name-grep that returns
zero proves only the canonical form is gone, not the variants. Prove
completeness by the INVENTORY-FLIP: enumerate a PINNED listing of what
still EXISTS (`ls agents/`, the skill dirs, the named pre-commit-check
headers) and flag any surviving doc CLAIM of a mechanism not in that
listing. Pin the membership definition — where the listing is
unambiguous the flip closes the form-space; where membership is itself a
judgment it only narrows it (honest bound in §8.2.1). The "all clean"
claim ships the inventory-check shown (command + output) with its pinned
definition, and the verifier lens must differ from the name-grep that
did the removal. This is discipline-only — there's no pre-commit check
for it. Detail: `skills/_protocols/evidence-pointer-schema.md` §8.2.

### Phase 4: migration patterns

#### Strangler pattern

Old + new run in parallel. Traffic incrementally routed from
old to new. When old handles 0% traffic: remove.

```
Phase 1: New 0%, old 100%
Phase 2: New 10% (canary)
Phase 3: New 50%
Phase 4: New 100%, old idle
Phase 5: Remove old
```

Cross-ref `shipping_and_launch` phase 3 staged rollout —
same mechanism.

#### Adapter pattern

The adapter translates calls from the old interface onto the
new implementation. Consumers keep using the old interface;
migration is hidden in the backend.

```python
# Adapter: old interface, new implementation
class LegacyTaskService:
    def __init__(self, new_service: NewTaskService):
        self._new = new_service

    # Old method signature, delegates internally
    def get_task(self, task_id: int) -> OldTask:
        task = self._new.find_by_id(str(task_id))
        return self._to_old_format(task)
```

#### Feature-flag migration

Cross-ref `shipping_and_launch` phase 2 feature-flag strategy.
Consumers switch from old to new via a flag, one at a time.

```python
def get_task_service(user_id: str) -> TaskService:
    if feature_flags.is_enabled("new-task-service", user_id=user_id):
        return NewTaskService()
    return LegacyTaskService()
```

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

## Red flags

- A deprecated system without an available replacement.
- A deprecation announcement without migration tooling or
  documentation.
- "Soft" deprecation that has been advisory for years
  without progress.
- Zombie code without an owner but with active consumers.
- New features added to a deprecated system (instead of
  investment in the replacement).
- Deprecation without measuring current usage.
- Removing code without verifying zero active consumers.
- Violating the STALE-CLEANUP invariant (refs in active
  files survive after removal).

## Common rationalizations

| Rationalization | Reality |
|---|---|
| "It still works, why remove it?" | Working code that nobody maintains accumulates security debt + complexity. Maintenance cost grows silently. |
| "Maybe we'll need it again" | If we need it again, it can be rebuilt. "Just in case" costs more than rebuild. |
| "Migration is too expensive" | Compare migration cost vs ongoing maintenance cost over 2-3 years. Migration is usually cheaper long-term. |
| "We'll deprecate after the new thing is finished" | Deprecation planning starts at design time. When the new thing is finished you'll have other priorities. **Plan now.** |
| "Users will migrate themselves" | They won't. Provide tooling + documentation + incentives — or do the migration yourself (churn rule). |
| "We can maintain both indefinitely" | Two systems doing the same thing = double the maintenance + testing + documentation + onboarding cost. |
| "A stub file with a pointer is enough" | Pattern break against the user mantra "no altlasten" — on clear consolidation, delete, don't archive. A stub only when there's historic value + non-trivial lookup need. |

## Contract

### INPUT
- **Required:** clearly identified subject (system / API /
  module / feature) to be deprecated.
- **Required:** answers to the 5 decision questions (phase
  1) — all 5 deprecation-pro.
- **Required:** a replacement exists or is clearly planned.
- **Optional:** consumer list (phase 3 step 1 — who uses
  it).
- **Optional:** migration-tooling idea (required on
  compulsory).
- **Context:** `CLAUDE.md` §stale-cleanup invariant 5,
  `framework/skill-anatomy.md` §consolidation mechanic
  (skill-specific),
  `skills/documentation_and_adrs/SKILL.md` (ADR for a
  substantial deprecation decision).

### OUTPUT
**DELIVERS:**
- Deprecation decision documented (5 answers).
- Compulsory-vs-advisory classification.
- Migration plan with the chosen pattern (strangler /
  adapter / feature flag).
- Deprecation notice (status / replacement / removal date /
  reason / migration guide).
- Removed code + tests + docs + config (at the end).
- STALE-CLEANUP complete (every active ref cleaned).
- ADR on a substantial deprecation decision.

**DOES NOT DELIVER:**
- No pure STALE-cleanup sweep — that's invariant 5.
- No skill-as-mode consolidation in detail — see
  `framework/skill-anatomy.md` §consolidation mechanic.

**ENABLES:**
- Clean framework without zombie code.
- Safe migration without data loss or user disruption.
- Reduced maintenance cost long-term.

### DONE
- Replacement production-proven, every critical use case
  covered.
- Migration guide exists with concrete steps + examples.
- All active consumers migrated (verified by metrics /
  logs / grep).
- Old code + tests + docs + config completely removed.
- No references to the deprecated system in the codebase —
  completeness proven by inventory-flip (claim of mechanism vs
  closed real inventory), not name-grep alone (§Phase 3 Step 4).
- Deprecation notices themselves removed (they served
  their purpose).
- STALE-CLEANUP complete in the removal commit.
- ADR written if applicable.

### FAIL
- **Retry:** migration of a consumer fails → don't advance
  the strangler phase further; fix, then continue.
- **Escalate:** the 5 decision questions don't clearly
  yield deprecation-pro → user discussion whether the
  system should really go. Solution expert / council on a
  substantial question.
- **Abort:** the replacement isn't production-proven →
  repeat phase 1, harden the replacement first.

## See also

- `CLAUDE.md` invariant §5 STALE-CLEANUP — the same-commit
  ref-cleanup discipline.
- `skills/shipping_and_launch/SKILL.md` phase 2
  feature-flag strategy — same mechanism, pre-migration use
  case.
- `framework/skill-anatomy.md` §Consolidation mechanics —
  skill-specific sub-variant.
- `skills/documentation_and_adrs/SKILL.md` — writing an ADR
  for substantial deprecation decisions.
- `skills/_protocols/skill-guardrails.md` — anti-patterns.
