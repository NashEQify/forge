# Deprecation and migration — migration process and patterns

Step-loaded unit of `skills/deprecation_and_migration/SKILL.md`. Read it once the deprecation decision stands: before
building the replacement and announcing it, while migrating consumers, when choosing a migration pattern, and before
removing the old system. Phases 1, 2 and 5 (the decision) are in `decision.md`.

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

**STALE-CLEANUP invariant (`framework/invariants.md` §5) in the same commit:**
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
judgment it only narrows it (honest bound in `skills/_protocols/evidence-author-claims.md` §8.2.1). The "all clean"
claim ships the inventory-check shown (command + output) with its pinned
definition, and the verifier lens must differ from the name-grep that
did the removal. This is discipline-only — there's no pre-commit check
for it. Detail: `skills/_protocols/evidence-author-claims.md` §8.2.

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

Cross-ref `shipping_and_launch/rollout.md` phase 3 staged rollout —
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

    # Translate the new shape back into what old consumers expect
    def _to_old_format(self, task: Task) -> OldTask:
        return OldTask(id=int(task.id), title=task.title, done=task.status == "done")
```

#### Feature-flag migration

Cross-ref `shipping_and_launch/rollout.md` phase 2 feature-flag strategy.
Consumers switch from old to new via a flag, one at a time.

```python
def get_task_service(user_id: str) -> TaskService:
    if feature_flags.is_enabled("new-task-service", user_id=user_id):
        return NewTaskService()
    return OldTaskService()
```
