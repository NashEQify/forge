# consistency-check — REFERENCE

Detail mechanics. The Buddy-facing `SKILL.md` is the checklist.
This file is reference material for definitions, full check
details, and refactoring checklists.

## Definitions

### Structural commit

A commit is structural when it **moves, renames, deletes, or
creates** files under `agents/`, `context/` (except
`context/history/`), `.claude-plugin/`, `orchestrators/`,
`skills/`, `workflows/`. Pure content changes to existing files
are NOT structural. History entries are not structural changes.

### Methodology change

A change is methodological when it influences **how agents
derive meaning, run processes, or make decisions**. Even small
changes that touch derivation chains (example: "operational
intent is activity-based instead of phase-based" — a wording
change with fundamental effect). Test: "Do other files /
agents / processes read this text and derive behaviour from
it?" Yes → consistency cascade (→ `CLAUDE.md`). Flow: recursive
IMPACT CHAIN pattern
(`skills/knowledge_processor/modes/process.md` §IMPACT CHAIN).

## Check details (by number)

### 1. Dead references

Scan targets (excluding `docs/tasks/archive/`,
`context/history/`):
- Backtick paths: `` `agents/<name>.md` ``,
  `` `context/<area>/<name>.md` ``.
- "Load and follow" lines in adapters.
- Table columns with paths (SoT, path columns).
- "→ tasks/" references in the backlog.

Per reference: does the target file exist? No → **ERROR**.

**Task-ref resolver (archive fallback):** refs to
`docs/tasks/<id>.{yaml,md}` and `tasks/<id>.{yaml,md}`
(backlog style) resolve with the fallback order:

1. `docs/tasks/<id>.{yaml,md}` (active tasks at top level).
2. `docs/tasks/archive/<id>.{yaml,md}` (archived done tasks
   per task_status_update auto-move).

Only when both paths do NOT exist → **ERROR** (dead
reference). Otherwise the reference counts as valid — the
auto-archive mechanism moves done tasks into archive/
automatically; cross-refs do not need rewriting.

### 2. Orphan files

Paths with orphan check:
- `agents/*.md` (except README.md).
- `orchestrators/**/agent/*.md`.
- `orchestrators/**/command/*.md`.
- `skills/*/SKILL.md`.
- `skills/*/REFERENCE.md`.
- `skills/*/SKILL.md`.

Orphan = no incoming reference at all. → **WARNING**.

### 3. Adapter-SoT sync

Per agent: SoT under `agents/` exists · each `agents` entry of
`.claude-plugin/plugin.json` names an existing SoT · OC
adapter
`orchestrators/opencode/.opencode/agent/<name>.md` references
the SoT · the "load and follow" path is correct. Reconcile
against `agents/README.md`.

### 3b. Framework invariants and the adapters

`framework/invariants.md` is tier 0 and the only home of the framework-wide
invariants; CLAUDE.md and AGENTS.md hold the forge repository's own rules and
the host's load list. Process detail in operational.md (tier 1).

Check:
1. `framework/invariants.md` has an `## Invariants` section; neither CLAUDE.md
   nor AGENTS.md has one (no second copy).
2. Both adapters point to `framework/invariants.md`.
3. operational.md references via
   `→ framework/invariants.md` (no duplication).
4. Both adapters contain "load and follow" with a reference to soul.md,
   framework/invariants.md, operational.md, boot.md.

ERROR: invariants missing or duplicated in an adapter; process detail in
CLAUDE.md / AGENTS.md; pointer or "load and follow" missing.

### 4. Navigation-tree sync

`context/navigation.md` file tree ↔ directory structure under
`context/`. Every file in the tree must exist on disk; every
file on disk must be in the tree (except `history/` generic).

### 5. Refactoring checklists

**Agent added / removed / moved:** SoT under `agents/` · plugin
manifest entry (`.claude-plugin/plugin.json`, when listed) · OC adapter
(`orchestrators/opencode/.opencode/agent/<name>.md`) · OC
command (when present) · `agents/README.md` ·
`agents/navigation.md` inventory (generator run) ·
`framework/models.md` (when the agent's role has no row) ·
`agents/buddy/delegation.md`
routing table · all cross-refs in other agent SoTs · on
primitives / gates / agent workflows: check that the primitive
enforces output (proof, not signal), every stage gates independently,
and new primitives absorb existing ones rather than adding.

**Skill added / removed / archived:** `skills/<name>/SKILL.md`
· `skills/<name>/REFERENCE.md` (on a split skill, linked from
SKILL.md) · the agent SoT that uses the skill ·
`framework/README.md` · **`framework/boot-navigation.md`
§Skills** · **`framework/skill-map.md` §Skills — AUTO +
§Maturity Registry** (generator run) · `skills/navigation.md`
lookup table (manual) · every `uses:` declaration in other
skills (grep `uses:.*<name>`) · every `Boundary` section in
other skills that points at the skill.

**Workflow added / removed:**
`workflows/runbooks/<name>/WORKFLOW.md` ·
**`framework/boot-navigation.md` §Workflows** ·
**`framework/process-map.md` routing table** ·
`framework/README.md` workflow list ·
`framework/skill-map.md` §composition map (when an own
column is needed) · `workflows/runbooks/navigation.md` lookup
table (manual).

**Spec added / removed:** `docs/specs/README.md` index ·
`docs/specs/SPEC-MAP.md` deps + consumers (when present) · at
least one task with `spec_ref` (required for implementation
specs; exception: REFERENCE_SPECS list) · regenerate the
status overlay.

**File / folder moved or renamed:** every active cross-ref
grep + update · navigation / file trees · adapter paths (when
agent) · navigation.md generator re-run.

**Skill moved (skills ↔ skills/):** `git mv` ·
`framework/README.md` ·
`skills/navigation.md` lookup · all path refs grep ·
`framework/models.md` (on a model switch) ·
`framework/boot-navigation.md` §Skills · skill-map.md
generator re-run.

### 6. Boot-map drift

**Purpose:** prevents orphan blindness — skills / workflows on
disk that are missing from `framework/boot-navigation.md`, and
vice versa. The boot context must stay in sync with the actual
framework landscape.

**SoT for the boot context:**
- `framework/boot-navigation.md` (quick index for boot).
- `framework/skill-map.md` (detail: taxonomy, maturity
  registry).
- `framework/process-map.md` (routing table).

**Two scans:**

**A) Disk → boot map (missing in the map?):**

```bash
# Workflows on disk
find workflows/runbooks -name 'WORKFLOW.md' \
  | sed 's|workflows/runbooks/||' | sed 's|/WORKFLOW.md||'

# Skills on disk (excluding _protocols)
find skills -maxdepth 2 -name 'SKILL.md' \
  -not -path '*/_protocols/*' \
  | sed 's|skills/||' | sed 's|/SKILL.md||'
```

Every entry must appear in `framework/boot-navigation.md` (as
a workflow-table row or skill-table row). Missing → **ERROR**:
"disk has X, boot map doesn't".

**B) Boot map → disk (ghost in the map?):**
Every workflow / skill listed in boot-navigation.md must exist
on disk. Missing on disk → **ERROR**: "boot map shows X, disk
doesn't have it".

**Exceptions (legitimate, not an error):**
- Skills under `skills/_protocols/` → not in boot-navigation
  (by definition not directly callable).

**Skill-map consistency (sub-check):**
Parallel to A) and B), check 6 verifies:

1. **AUTO block:** between `<!-- SKILL-MAP-AUTO-START -->` and
   `<!-- SKILL-MAP-AUTO-END -->` in `framework/skill-map.md`,
   every skill dir (`skills/<name>/SKILL.md`) must appear
   **exactly once** in one of the sub-sections — direct-
   invokable, workflow-step, service, cross-cutting, hook-
   triggered, or deprecated. A `status: deprecated` skill is
   routed to the Deprecated sub-section (in tree, not active);
   all others route by `invocation.primary`. Regenerator:
   `python scripts/generate_skill_map.py`.

Drift in skill-map.md → **WARNING** (less critical than
boot-navigation, since skill-map is loaded only on demand,
but still SoT).

**Bash help (minimal):**

```bash
# Diff disk vs boot-map (workflows)
diff <(find workflows/runbooks -mindepth 1 -maxdepth 1 -type d \
  -not -name '_*' | sed 's|.*/||' | sort) \
     <(grep -oE '`workflows/runbooks/[^/]+/WORKFLOW\.md`' framework/boot-navigation.md \
  | sed 's|^`workflows/runbooks/||; s|/WORKFLOW\.md`$||' | sort -u)

# Diff disk vs boot-map (skills, capability/utility)
diff <(find skills -mindepth 1 -maxdepth 1 -type d \
  -not -name '_*' | sed 's|.*/||' | sort) \
     <(grep -oE '^\| `[a-z_]+`' framework/boot-navigation.md \
  | sed 's|^\| `||; s|`$||' | sort -u)
```

Differences are candidates for ERROR / WARNING. Verify in
content (e.g. `consistency_check` is a utility → goes under
the utilities table, not the capabilities table).

**Triggers for check 6:**
- **Blocking gate:** structural commits that touch skills /
  workflows (new / deleted / archived / moved) → MUST CLEAN
  before commit.
- **Check (SHOULD):** methodology changes to boot-navigation
  or skill-map.
- **Periodic:** every `context_housekeeping` run.

**Self-test:** `consistency_check` itself is a utility → must
appear in the boot map under the "Utilities (directly
callable by the orchestrator)" table.

### 7. Rationalization test

**Purpose:** prevents the "housekeeping instead of
rationalization" pattern on framework refactorings. A
structural rebuild has to demonstrate not only "what
changed", but also "why this solution instead of
alternatives".

**Trigger (MUST):**
- Commits with changes under `skills/`, `workflows/`,
  `framework/process-map.md`,
  `framework/boot-navigation.md`,
  `framework/agent-autonomy.md`.
- Task / spec texts with a rationalization claim
  (`docs/tasks/*.md`, `docs/specs/**/*.md`).

**Evidence requirement (at least 2 of 3):**
1. **Problem / target picture clearly named** (which
   structural problem is being solved?).
2. **Alternatives / trade-offs documented** (at least 2
   options or a justified null option).
3. **Impact chain documented** (which callers / gates /
   artifacts are affected).

**Assessment:**
- **ERROR:** structural refactoring without demonstrable
  rationalization (0/3 evidence points).
- **WARNING:** partial rationalization present (1/3) or
  only implicit.
- **CLEAN:** ≥2/3 evidence points.

**Recommended sources for evidence:**
- `docs/tasks/<id>.md` progress / decisions.
- `docs/reviews/board/*.md` (chief / board verdicts).
- `docs/decisions/*.md` (ADR).
- A commit message with a justified "why".

**Lightweight check (manual):**
1. Does the diff touch structural framework paths? If no:
   check 7 SKIP.
2. In the co-changed task / spec / ADR files, look for
   problem + alternative + impact.
3. Score 0-3, report the result as ERROR / WARNING / CLEAN.

**Why check 6 instead of an auto-generate script:**

The alternative to check 6 would be a generator script
that regenerates the boot map automatically from
`workflows/runbooks/*/WORKFLOW.md` + `skills/*/SKILL.md`
frontmatter. That script
would make drift impossible because the map would derive
from disk.

Decision: **B + check 6 instead of E**. Rationale:
- Check 6 catches drift on the next structural commit →
  manual upkeep stays safe; no silent accumulation.
- An auto-generate script requires generator logic +
  frontmatter discipline in every SKILL / runbook (extra
  maintenance surface).
- Manual upkeep + check 6 is cheaper than generator +
  maintenance at the current rate of change (structural
  changes are rare).
- E remains an open follow-up option in case check 6
  regularly finds drift (i.e. manual upkeep doesn't scale).

This decision is captured so follow-up discussions don't
re-raise "why don't we have a generator?" without context.

### 8.–13. Navigation, taxonomy, wrapper, doc-currency and user-scope checks

When running check 8, 9, 10, 12 or 13 or resolving its finding: read that check in
`skills/consistency_check/REFERENCE-drift.md`.

## Frozen-zone integrity check

```bash
# Baseline: tag 'frozen-zone-verified' (set after the last successful check)
# Fallback when the tag is missing: HEAD~1
BASELINE=$(git rev-parse --verify frozen-zone-verified 2>/dev/null || echo "HEAD~1")
git diff --name-status "$BASELINE"..HEAD -- \
  docs/tasks/archive/ \
  context/history/ \
  documents/ \
  | grep -E '^[MRD]'
```

**Assessment:**
- `A` (added): OK — WORM-conformant, new records.
- `M / R / D` (modified / renamed / deleted): INCIDENT.
- Exception: `.correction.md` files (corrections addendum).

**Auto-archive exceptions (`docs/tasks/archive/`):**

The following diff patterns are LEGITIMATE (no INCIDENT) when
triggered by the task_status_update skill:

1. **`R docs/tasks/<id>.{yaml,md} -> docs/tasks/archive/<id>.{yaml,md}`** —
   forward move (auto-archive on `status=done`). Validation:
   the source file disappears from top level, the target shows
   up under archive/.
2. **`R docs/tasks/archive/<id>.{yaml,md} -> docs/tasks/<id>.{yaml,md}`** —
   reverse move (reopen pattern, status away from done).
   Validation: mirror image.
3. **`M docs/tasks/archive/<id>.{yaml,md}`** — modify on an
   already-archived file by task_status_update (e.g. a
   subsequent `workflow_phase` update after auto-archive).
   Tolerated because task_status_update is the only writer
   contract for tasks.

Other `M / R / D` on `docs/tasks/archive/` (hand edits,
external tools, wrong skills) remain INCIDENT.

**On INCIDENT:** list files + change kind. Repair:
`git checkout "$BASELINE" -- <file>`. The executing agent
must fix before a task is done.

**After CLEAN:**

```bash
git tag -f frozen-zone-verified
```

## Self-update rules

This skill binds to concrete paths, conventions, and
checklists. When structure changes, the skill must grow with
it:

- **On structural changes:** the executing agent verifies
  completeness and updates as part of the commit.
- **Refactoring-checklist extension:** new category → new
  checklist.
- **Path conventions:** on a convention change, adjust the
  checks here.

The knowledge_processor skill stays current the same way.
Both keep each other current: consistency_check verifies that
knowledge_processor is working correctly; knowledge_processor
triggers consistency_check.
