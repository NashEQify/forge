---
name: consistency-check
description: >
  Checks the structural integrity of the repo. Dead references,
  orphan files, adapter SoT drift, navigation desync.
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
and boot-map drift (workflows / skills in `boot-navigation.md` vs
disk). Complementary to `knowledge-processor`:
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

## The 9 checks (short form)

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

Running checks 3b, 5, 6, 7, and 8 requires `REFERENCE.md` to be
co-loaded (sub-checks, scan targets, checklist items, bash).

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
