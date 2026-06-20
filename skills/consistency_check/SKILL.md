---
name: consistency-check
description: >
  Checks the structural integrity of the repo. Dead references,
  orphan files, adapter SoT drift, navigation desync, doc-currency
  drift (stale banners + reading-map index-omission).
  Triggers when structural repo integrity must be validated after structural changes or before commit (dead refs, orphans, adapter drift, stale "Task N pending" banners, reading-map gone stale); NOT for content/logic review.
status: active
invocation:
  primary: cross-cutting
  secondary: [user-facing, workflow-step]
disable-model-invocation: false
uses: []
---

# Skill: consistency-check

## Purpose

Checks the structural integrity of the repo. Finds dead
references, orphan files, adapter-SoT drift, navigation desync,
boot-map drift (workflows / skills in `boot-navigation.md` vs
disk), and doc-currency drift (a doc or reading-map entry whose
content has gone stale while its structure still resolves).
Complementary to `knowledge-processor`:
`knowledge-processor` processes information (brain logic);
`consistency-check` checks structure. The two trigger each other
during the consistency cascade (detail: `REFERENCE.md`).

Detail mechanics (definitions, full checks, refactoring
checklists, frozen-zone bash): `REFERENCE.md`.

## When to call

### As a blocking gate (MUST)

| Trigger | Gate condition |
|---------|----------------|
| Structural commit | CLEAN before the next work step. ERROR = fix loop. |
| Refactoring task done | CLEAN before commit. |

### As a check (SHOULD)

| Trigger | Who |
|---------|-----|
| User says `consistency-check` | Buddy |
| Methodology change (consistency cascade) | Buddy |
| Suspicion of drift | Any agent |

Definitions of "structural commit" and "methodology change":
`REFERENCE.md`.

Gate enforcement: pre-harness via
`agents/buddy/context-rules.md` §Consistency-Check Gate
(blocking). Post-harness via the pre-commit hook (when
implemented).

## The 12 checks (short form)

1. **Dead references** — scan `*.md` for path refs (backticks,
   "load and follow", SoT tables). Miss → ERROR.
2. **Orphan files** — agents / skills / adapters without an
   incoming reference → WARNING.
3. **Adapter-SoT sync** — `agents/` SoT ↔ `.claude/agents/` ↔
   `orchestrators/opencode/` → ERROR on divergence.
3b. **Invariants sync (CLAUDE.md ↔ AGENTS.md)** — both have
   `## Invariants`, invariants substantively identical,
   `operational.md` delegates without duplication, "load and
   follow" block present → ERROR on divergence (detail:
   `REFERENCE.md` §3b).
4. **Navigation-tree sync** — `context/navigation.md` ↔
   directory structure → ERROR on miss.
5. **Refactoring checklists** — on structural changes: a check
   per category (agent / context area / skill / spec / rename
   / skill move).
6. **Boot-map drift** — `framework/boot-navigation.md`
   workflows + skills ↔ `workflows/runbooks/*/WORKFLOW.md` +
   `skills/*/SKILL.md` (excluding `_protocols/`). New / deleted
   / moved workflow or skill without a boot-map update → ERROR.
   Detail: `REFERENCE.md` §6.
7. **Rationalization test** — on framework refactorings,
   verify that the change is methodologically justified (not
   just housekeeping), considers the solution space, and
   documents explicit trade-offs. Missing rationalization
   artifacts → WARNING (on structural refactoring without
   rationale: ERROR). Detail: `REFERENCE.md` §7.
8. **Navigation-layer drift** — `navigation.md` per top-level
   depth-3 directory exists; the AUTO block is regenerated (no
   diff on a re-run of `scripts/generate_navigation.py`); the
   manual reader-journey sections are filled (no placeholder
   text left). Expected `navigation.md` targets + bash diff:
   `REFERENCE.md` §8. Disk has `navigation.md` without a
   generator target, or a generator target without a disk file
   → **ERROR**. AUTO-block drift → **ERROR**. Placeholder
   manual → **WARNING**.
9. **Folder-taxonomy drift** — `docs/` subdirs/files vs
   `docs/STRUCTURE.md`. Undeclared path → **WARNING**; drift
   alias → **ERROR**. Detail: `REFERENCE.md` §9.
10. **Wrapper + router drift** — two chained generators.
   (a) `skills/workflow_router/SKILL.md` (the workflow-router SoT)
   vs a fresh `scripts/generate_workflow_router.py` run; (b) CC
   skill-wrappers (`.claude/skills/*/SKILL.md`) vs a fresh
   `scripts/generate_skill_wrappers.py` run. A missing wrapper
   for an eligible skill, an orphan wrapper, or a hand-edited /
   stale wrapper/router that doesn't match generator output →
   drift. Mechanically `generate_workflow_router.py --check` THEN
   `generate_skill_wrappers.py --check` (non-zero exit on drift).
   **Chained-run ordering (discipline, not mechanically enforced):**
   when REgenerating, run router-gen before wrapper-gen — wrapper-gen
   reads the router SoT, so regenerating the wrapper from a stale
   router SoT bakes in stale content. This *check* still catches it
   (router `--check` fires non-zero on a stale router SoT), so the
   check is order-independent; the ordering only matters on the
   write/regen path. Mirrors the skill-map idempotence sub-check.
   Drift → **WARNING** (WARN-first calibration; escalate to BLOCK
   after burn-in). Detail: `REFERENCE.md` §10.
11. **Enforcement-registry integrity** — every Live-table row in
   `framework/enforcement-registry.md` carries a valid class tag
   (`[STRUCTURAL]`/`[GATE]`/`[WORKFLOW]`/`[DISCIPLINE]`) and an
   artifact pointer that resolves on disk. Stale pointer or bad tag
   → **ERROR**. Mechanically `scripts/consistency_check.py --check
   enforcement-registry` (non-zero exit on failure). Guards against
   the phantom-enforcement class — a registry that claims a mechanism
   whose artifact was renamed or removed.
12. **Doc-currency** — the content-currency the structural checks
   are blind to (a doc whose structure resolves but whose content or
   index entry lied). Judgment-applied (not regex): the agent reads
   the current-state doc-set (`docs/{specs,architecture}/**/*.md`) +
   the project's reading-map (the §0 entry its `intent.md` names) and
   flags (a) a banner naming a Task as pending/open while
   `docs/tasks/<N>.yaml` status is terminal → **WARNING** (the stale
   "Task N pending" rot); (b) a doc whose `last_updated` predates a
   date on one of its own banner lines → **WARNING** (the stamp lags
   the banner); (c) a reading-map SoT pointer that no longer resolves
   to the current doc, or a doc-of-record the map should index but
   omits → **WARNING** (index-omission — the rot a spec born on a
   bypass route leaves, which no diff-scoped step sees); (d) a
   `docs/plan.yaml` milestone `desc` carrying a hardcoded status label
   ("Status: pending/done/blocked/…") that contradicts the status
   `plan_engine.py --status` computes for that milestone key →
   **WARNING** (shadow state the engine computes authoritatively — the
   fix is deletion, not re-sync; no `docs/plan.yaml` → (d) skips). The
   "banner / currency claim / right SoT?" calls are read semantically — the
   LLM-strength judgment a pattern-match gets wrong. No reading-map
   declared → (c) skips. Contract + vocabulary: `REFERENCE.md` §12.

Running checks 3b, 5, 6, 7, 8, and 10 requires `REFERENCE.md`
to be co-loaded (sub-checks, scan targets, checklist items,
bash).

## Frozen-zone integrity

Every run checks the frozen zones (`docs/tasks/archive/`,
`context/history/`, `documents/`, `docs/backlog-archive.md`)
for modify / rename / delete since the baseline tag. `A` = OK
(WORM); `M / R / D` = INCIDENT. Exception:
`.correction.md` (corrections addendum).

Bash command + repair flow: `REFERENCE.md`.

## Output format

```
→ CONSISTENCY-CHECK
Checked: <N> files, <M> references, <K> adapters

ERRORS (must be fixed):
  - <file:line>: dead reference to `<path>`
  - <adapter>: points at `<path>`, SoT is `<correct>`

WARNINGS (review):
  - <file>: orphan

CHECKLIST (<category>):
  ✅ <done item>
  ❌ <missing item> — action: <what to do>

Result: CLEAN / <N> ERRORS, <M> WARNINGS
```

On ERROR: fix before task done. On WARNING: agent decision.

## Boundary

- **No content review** — that's `spec_board` or
  `code_review_board`.
- **No knowledge check** — that's `knowledge_processor` (IMPACT
  CHAIN).
- **No linting** — that's `python_code_quality_enforcement`.
- **No auto-fix** — the check reports; it does not fix itself.
- **No self-growth** — on convention changes the skill must
  grow manually (rules: `REFERENCE.md`
  §Self-Update-Rules).

## Anti-patterns

- **NOT** run on every content change. **INSTEAD** only on
  structural commits (definition + full path list:
  `REFERENCE.md` §Structural commit). Because: content edits
  don't produce structural drift — the check is expensive and
  gains nothing.
- **NOT** treat WARNINGS as ERRORS. **INSTEAD** the agent
  decides whether action is needed. Because: orphan files can
  be legitimate (templates, draft specs with a planned
  consumer).
- **NOT** skip the check because "it's just a small rename".
  **INSTEAD** trigger the rename category of the refactoring
  checklist. Because: small renames are the most frequent drift
  source.
- **NOT** check archive / history as ref sources. **INSTEAD**
  frozen zones are WORM — historical paths are correct for
  their point in time; only check modifications. Because: a
  ref check on archive produces false-positive drift.
