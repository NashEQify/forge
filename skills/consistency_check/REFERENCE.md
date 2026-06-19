# consistency-check — REFERENCE

Detail mechanics. The Buddy-facing `SKILL.md` is the checklist.
This file is reference material for definitions, full check
details, and refactoring checklists.

## Definitions

### Structural commit

A commit is structural when it **moves, renames, deletes, or
creates** files under `agents/`, `context/` (except
`context/history/`), `.claude/agents/`, `orchestrators/`,
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
(`skills/knowledge_processor/modes/process.md` §step 2).

## Check details (by number)

### 1. Dead references

Scan targets (excluding `docs/tasks/archive/`,
`context/history/`):
- Backtick paths: `` `agents/foo.md` ``,
  `` `context/bar/baz.md` ``.
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
- `.claude/agents/**/*.md`.
- `orchestrators/**/agent/*.md`.
- `orchestrators/**/command/*.md`.
- `skills/*/SKILL.md`.
- `skills/*/REFERENCE.md`.
- `skills/*/SKILL.md`.

Orphan = no incoming reference at all. → **WARNING**.

### 3. Adapter-SoT sync

Per agent: SoT under `agents/` exists · CC adapter
`.claude/agents/<name>/<name>.md` references the SoT · OC
adapter
`orchestrators/opencode/.opencode/agent/<name>.md` references
the SoT · the "load and follow" path is correct. Reconcile
against `agents/README.md`.

### 3b. CLAUDE.md ↔ AGENTS.md invariants sync

CLAUDE.md and AGENTS.md are tier 0. Process detail in
operational.md (tier 1).

Check:
1. Both have an `## Invariants` section.
2. Invariants are substantively identical.
3. operational.md references via
   `→ CLAUDE.md §Invariant N` (no duplication).
4. Both contain "load and follow" with a reference to soul.md,
   operational.md, boot.md.

ERROR: invariants missing / divergent; process detail in
CLAUDE.md / AGENTS.md; "load and follow" missing.

### 4. Navigation-tree sync

`context/navigation.md` file tree ↔ directory structure under
`context/`. Every file in the tree must exist on disk; every
file on disk must be in the tree (except `history/` generic).

### 5. Refactoring checklists

**Agent added / removed / moved:** SoT under `agents/` · CC
adapter (`.claude/agents/<name>.md`) · OC adapter
(`orchestrators/opencode/.opencode/agent/<name>.md`) · OC
command (when present) · `agents/README.md` ·
`agents/navigation.md` inventory (generator run) ·
`framework/models.md` · `agents/buddy/operational.md`
delegation table · all cross-refs in other agent SoTs · on
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
`skills/README.md` / `framework/README.md` ·
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

The alternative to check 6 would be a
`scripts/generate-boot-navigation.py` that regenerates the
boot map automatically from
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

### 8. Navigation-layer drift

**Purpose:** prevents re-drift of the navigation layer
(reverse-lookup tier for "what lives here? where to look for
which question?"). The pattern was reintroduced after historical
drift experience — this time with generator + validator together,
not hand-maintained alone.

**SoT:**
- Generator: `scripts/generate_navigation.py` (AUTO block per
  `navigation.md`).
- Targets: hardcoded in the generator's `TARGETS` (8 entries).

**Expected `navigation.md` targets (top-level depth-3 cap):**

| Target | Scope |
|---|---|
| `framework/navigation.md` | Level 1 — framework sub-areas |
| `skills/navigation.md` | Level 2 — active skills |
| `skills/_protocols/navigation.md` | Level 3 — skill protocols |
| `workflows/runbooks/navigation.md` | Level 2 — workflows |
| `references/navigation.md` | Level 2 — references |
| `agents/navigation.md` | Level 1 — personas |
| `agents/buddy/navigation.md` | Level 2 — Buddy sub-files |
| `agents/_protocols/navigation.md` | Level 2 — agent protocols |

**Three sub-checks:**

**A) Existence check (disk vs generator targets):**
Every `navigation.md` from the TARGETS block must exist. Does
not exist → **ERROR**: "generator target X missing on disk".

The other way round: every `navigation.md` on disk
(recursively under `framework/`, `agents/`) must be listed as
a target. Disk has navigation.md without a generator target →
**WARNING** ("drift candidate: not in the generator").

**B) AUTO-block sync (generator idempotency):**
Re-running the generator must produce no diff.

```bash
python3 scripts/generate_navigation.py >/dev/null
git diff --name-only -- ':(glob)**/navigation.md'
```

When the list is non-empty → **ERROR**: "AUTO-block drift in
<file>". Auto-repair hint: the generator already regenerated;
just commit the diff.

**C) Manual-section-filled check:**
The two manual sections (`## What lives here?` and `## Where
to look for which question?`) must no longer contain the
placeholder text:

```bash
grep -l '_(manual reader-journey description' \
  framework/navigation.md skills/navigation.md \
  skills/_protocols/navigation.md \
  workflows/runbooks/navigation.md \
  references/navigation.md \
  agents/navigation.md agents/buddy/navigation.md \
  agents/_protocols/navigation.md 2>/dev/null
```

Hits → **WARNING**: "placeholder in <file>" (reader journey
not filled). It is a WARNING not an ERROR because new
navigation.md files immediately after a generator run
legitimately contain placeholders until manual fill.

**Bash help (minimal):**

```bash
# Sub-check A: targets exist
for f in framework/navigation.md skills/navigation.md \
         skills/_protocols/navigation.md \
         workflows/runbooks/navigation.md \
         references/navigation.md \
         agents/navigation.md agents/buddy/navigation.md \
         agents/_protocols/navigation.md; do
  [ -f "$f" ] || echo "MISSING: $f"
done

# Sub-check A reverse: navigation.md without a target
find framework agents -name 'navigation.md'

# Sub-check B: generator idempotency. The glob pathspec matches navigation.md at
# any depth and excludes boot-navigation.md (the check applies only
# to the 8 generator targets, not to manual tier-1 files).
python3 scripts/generate_navigation.py >/dev/null && \
  git diff --quiet -- ':(glob)**/navigation.md' || echo "AUTO-block drift"

# Sub-check C: placeholder detection
grep -rln '_(manual reader-journey description' \
  framework/ agents/ --include='navigation.md'
```

**Triggers for check 8:**
- **Blocking gate:** structural commits under `framework/`
  or `agents/` (top-level depth-3 path changes) → MUST CLEAN
  before commit (A + B).
- **Check (SHOULD):** `context_housekeeping` run, periodic.
- **WARNING (C) is non-blocking** — reader-journey fill is
  follow-up work.

**Self-test:** this file
(`consistency_check/REFERENCE.md`) is part of
`skills/<name>/`; the parent `navigation.md` is
`skills/navigation.md` and must be listed in the inventory.

**Why generator + check 8 (instead of just hand maintenance):**

The navigation pattern was purely hand-maintained in early
framework versions and was retired again because of drift.
Re-introduction was only accepted with a drift mechanism.
The generator makes the AUTO block hands-off (disk = SoT).
The validator hook (this check) makes manual sections +
idempotency verifiable. Together the pattern is
self-stabilizing; alone neither half is enough.

### 9. Folder-taxonomy drift

**Purpose:** prevents sediment growth in the `docs/` tree.
New paths that aren't declared in `docs/STRUCTURE.md` get
flagged as drift — a human or agent has to consciously
decide whether (a) STRUCTURE.md should be extended or (b)
the new path should be consolidated into an existing one.

**SoT:** `docs/STRUCTURE.md` (rule doc for the `docs/`
hierarchy).

**Scan:** every top-level subdir under `docs/` + every
explicitly tracked file:

```bash
# Disk: existing docs/ subdirs + top-level files
DISK_DIRS=$(find docs -mindepth 1 -maxdepth 1 -type d | sed 's|docs/||' | sort)
DISK_FILES=$(find docs -mindepth 1 -maxdepth 1 -type f | sed 's|docs/||' | sort)

# Schema: declared in STRUCTURE.md (table "Tracked" + "Gitignored")
DECLARED=$(grep -oE '`docs/[^`]+`' docs/STRUCTURE.md | sed 's|^.docs/||; s|/.*$||; s|.$||' | sort -u)
```

For every `docs/<dir>/` or `docs/<file>` that is NOT in
DECLARED → **WARNING**: "folder-taxonomy drift: `docs/<X>`
not in `docs/STRUCTURE.md` — either extend the schema or
consolidate the path".

**Assessment:** WARNING (not ERROR) because new skills /
workflows can legitimately need new paths — a schema update
is the right reaction, not a block.

**Drift aliases explicit:** when a disk path is in the
"drift aliases" table in STRUCTURE.md (e.g. `docs/review/`
instead of `docs/reviews/`) → **ERROR**: "drift alias
`docs/<X>` used — canonical is `docs/<Y>`."

**Triggers for check 9:**
- **Blocking gate (ERROR on a drift alias):** structural
  commits that touch `docs/`.
- **Check (WARNING on undeclared path):** periodic in
  `context_housekeeping`.
- **Refactoring help:** on a docs-folder reorg, consult the
  schema BEFORE creating a new path.

**Self-test:** this file verifies that `docs/STRUCTURE.md`
exists (SoT requirement). Missing STRUCTURE.md → **ERROR**:
"consistency_check check 9 needs docs/STRUCTURE.md as SoT".

### 10. Wrapper + router drift

**Purpose:** prevents re-drift of the Claude-Code skill-wrapper
layer (`.claude/skills/<kebab>/SKILL.md`) AND of the
workflow-router SoT it depends on. Wrappers were a hand-authored
side-artifact; skills got built without one (so they were
invisible to the `Skill` tool) and existing wrappers drifted
from their source frontmatter. Re-introduction was only accepted
with a generator + validator together, mirroring the skill-map
and navigation-layer patterns. The workflow-router
(`skills/workflow_router/SKILL.md`) is a second whole-file
generated SoT whose `description` catalog is built from the 8
`workflows/runbooks/*/workflow.yaml` `need_phrase:` fields; it
feeds the wrapper generator, so it joins this check.

**SoT:**
- Router generator: `scripts/generate_workflow_router.py` (sole
  writer of `skills/workflow_router/SKILL.md`; whole-file
  emission from the `need_phrase:` catalog source).
- Wrapper generator: `scripts/generate_skill_wrappers.py` (sole
  writer under `.claude/skills/`).
- Inclusion predicate + wrapper contract:
  `framework/skill-anatomy.md` §Wrapper — required derived
  artifact.

**Chained-run ordering (discipline, not mechanically enforced):** on
the REGEN path, run router-gen before wrapper-gen. The router writes
its SKILL.md SoT; `generate_skill_wrappers.py` then reads that SoT (it
is just another `skills/*/SKILL.md`) and emits the injected CC wrapper.
If wrapper-gen regenerates first from a STALE router SoT, its own
`--check` passes GREEN on stale content. This `consistency_check` step
still catches the drift because it runs router-gen `--check` too (which
fires non-zero on a stale router SoT) — so the CHECK is order-
independent; only the regen/write path needs router-gen first. No seam
sequences them; the discipline is "run router-gen, then wrapper-gen".

**The check (generator idempotency, parallel to check 6's
skill-map sub-check):**
Re-running each generator must produce no diff, and `--check`
must agree. Run router `--check` first, then wrapper `--check`.

```bash
python3 scripts/generate_workflow_router.py --check
python3 scripts/generate_skill_wrappers.py --check
```

Router `--check` non-zero exit → **WARNING**: "router SoT drift
in `skills/workflow_router/`". Drift kinds:
- `+ missing router SKILL.md` — the router SoT is absent.
- `~ stale router SKILL.md` — the SoT diverged from generator
  output (hand-edit, a changed `need_phrase:`, or an added /
  removed workflow). A missing / empty `need_phrase:` in any
  `workflow.yaml` is a HARD error (non-zero, no write), not a
  drift line.

Non-zero exit → **WARNING**: "wrapper drift in
`.claude/skills/`". The `--check` output enumerates the drift
kind per wrapper:
- `+ missing wrapper: <name>` — an eligible skill has no wrapper.
- `- orphan wrapper: <name>` — wrapper whose source skill is
  gone or no longer eligible.
- `~ stale wrapper: <name>` — wrapper content diverged from
  generator output (hand-edit or source frontmatter changed).

Auto-repair hint: run `python3 scripts/generate_skill_wrappers.py`
(no flag) and commit the diff — the generator is the SoT, the
wrapper is fully derived.

**Scope caveats:**
- The drift check is **SKILL.md-content-scoped**: it compares each
  wrapper dir's `SKILL.md` against generator output and detects
  missing / orphan / stale wrappers. It does NOT flag stray extra
  files inside an otherwise-present, content-correct wrapper dir
  (e.g. a leftover `REFERENCE.md` or backup). The generator owns the
  tree and nothing legitimate writes there, so this is an accepted
  limitation, not a gap to close here.
- Check 10 is a **no-op without PyYAML**: the generator returns 0
  with a `SKIP` when `yaml` is unavailable, so in a PyYAML-less
  environment `--check` passes vacuously (verifies nothing). Same
  implicit caveat as the skill-map sub-check (check 6); the repo
  CI/dev env always has PyYAML.

**Calibration:** WARNING (not ERROR) for now — WARN-first per
framework convention; escalate to BLOCK after burn-in, same as
the skill-map sub-check (less critical than boot-navigation:
wrappers are discovery hints, not load-bearing routing).

**Bash help (minimal):**

```bash
# Idempotency: a fresh run must leave the tree unchanged.
# Router-gen FIRST (the wrapper reads the router SoT), then wrapper-gen.
python3 scripts/generate_workflow_router.py >/dev/null && \
python3 scripts/generate_skill_wrappers.py >/dev/null && \
  git diff --quiet -- skills/workflow_router/ .claude/skills/ \
  || echo "router/wrapper drift"

# Or non-mutating: --check exits non-zero on any drift (router first).
python3 scripts/generate_workflow_router.py --check && \
python3 scripts/generate_skill_wrappers.py --check
```

**Triggers for check 10:**
- **Blocking gate:** structural commits that add / remove /
  archive a skill, or change a skill's `name` / `description` /
  `invocation.primary` / `disable-model-invocation` /
  `cc_wrapper` → MUST be drift-free (regenerate + commit).
- **Check (SHOULD):** any edit under `.claude/skills/`
  (wrappers are generated — a hand-edit is drift by
  definition).
- **Periodic:** every `context_housekeeping` run.

**Self-test:** `consistency_check` itself is `cross-cutting`
→ wrapper-eligible → `.claude/skills/consistency-check/SKILL.md`
must exist and match generator output.

**Why generator + check 10 (instead of hand maintenance):**

The wrapper was purely hand-maintained and produced exactly the
drift class this check now closes (skills with no wrapper; stale
wrapper descriptions after a source rewrite). The generator
makes `.claude/skills/` hands-off (skill frontmatter = SoT); the
validator hook makes idempotency verifiable. Together the
pattern is self-stabilizing — same rationale as the skill-map
and navigation-layer patterns; alone neither half is enough.

### 12. Doc-currency

Discipline-applied (like checks 1–9), WARN-level. Closes the
content-currency gap the structural checks (1, 6, 8) are blind to: a
doc whose *structure* still resolves while its *content or index entry*
has gone stale. Judgment, not regex — "is this a banner / a currency
claim / the right SoT?" is exactly the semantic call an LLM makes well
and a pattern-match makes badly; that is why this is an agent-read
discipline, not a script.

**Scan scope:** the current-state doc-set — `docs/specs/**/*.md` +
`docs/architecture/**/*.md`; skip anything under `/archive/`.
Historical trees (`docs/reviews`, `docs/build`, `docs/audit`,
`docs/research`) are point-in-time — a banner there is a record, not a
live claim. Nothing to check in a repo without those dirs.

**Sub-check (a) — stale "Task N pending".** For each banner that
states a task's status, resolve the task against `docs/tasks/<N>.yaml`.
Banner says pending / open / "not yet" / in-progress (or equivalents)
but the task's `status` is terminal (`done` / `closed` / `completed` /
`merged` / `cancelled` / `dropped` / `archived` / `superseded` /
`resolved`) → WARN. Only the contradiction direction fires; a banner
that agrees the task is done is fine.

**Sub-check (b) — `last_updated` lags a banner date.** If a doc
declares `last_updated: YYYY-MM-DD` and one of its banner lines
(SUPERSEDED / AS-BUILT / stale / deprecated / retired / REDIRECT /
hibernated / Status / "updated") carries a later date → WARN. Implied
discipline: **bump `last_updated` whenever you add or edit a banner**,
else the stamp claims the doc is older than its own content.

**Sub-check (c) — reading-map index-currency.** When the project's
`intent.md` names an architecture reading-map (the §0 entry), check it:
every SoT pointer still resolves to the current doc (not a moved /
renamed / superseded one), and every doc-of-record the map should index
is indexed. A pointer to a moved/missing SoT, or a doc-of-record absent
from the map → WARN. This is the index-omission rot a spec born on a
bypass route (DIRECT / SUB-BUILD, no `spec_authoring` checklist) leaves
— no diff-scoped step sees it. No reading-map declared → skip (c).

**Why banner-scoped, not every date:** a doc legitimately mentions
many dates in prose; only a date that IS a currency claim (a banner)
counts. That scoping is itself a judgment — which is why check 12 is an
agent-read discipline, not a date-lint.

## Frozen-zone integrity check

```bash
# Baseline: tag 'frozen-zone-verified' (set after the last successful check)
# Fallback when the tag is missing: HEAD~1
BASELINE=$(git rev-parse --verify frozen-zone-verified 2>/dev/null || echo "HEAD~1")
git diff --name-status "$BASELINE"..HEAD -- \
  docs/tasks/archive/ \
  docs/backlog-archive.md \
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
