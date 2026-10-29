# consistency-check — REFERENCE: checks 8 to 13

Lookup unit of `skills/consistency_check/REFERENCE.md`. Read the check you run or whose finding you resolve:
navigation-layer drift (8), folder-taxonomy drift (9), wrapper and router drift (10), doc-currency (12), user-scope
drift (13). Check numbers are skill-wide.

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
python3 scripts/generate_navigation.py --check
```

Exit 1 (the output names each drifted file) → **ERROR**: "AUTO-block
drift in <file>". `--check` never writes. Auto-repair: run the
generator without `--check` and commit the diff.

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
(`consistency_check/REFERENCE-drift.md`) is part of
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
  `framework/skill-anatomy-wrapper-and-checks.md` §Wrapper — required derived
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
`docs/architecture/**/*.md`; skip anything under `/archive/`. Sub-check (d)
additionally reads `docs/plan.yaml` (milestone descs).
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

**Sub-check (d) — plan.yaml milestone-status shadow.** When the repo has a
`docs/plan.yaml`, run `plan_engine.py --status` (the authoritative computed
milestone status) and read each milestone's `desc`. A `desc` carrying a
hardcoded status label ("Status: pending / done / blocked / in-progress /
DONE-ROLLING" or equivalent) that contradicts the computed status for that
milestone `key` → WARN. `compute_milestone_status` never reads `desc` (status
is derived from each task's `milestone` + `status`), so a status label in
`desc` is shadow state that can only drift. Generic — keyed on the computed
status per milestone key, no project-specific milestone names. The fix is
deletion (the engine already renders live status), not a re-sync of the label.
No `docs/plan.yaml` → skip (d).

**Why banner-scoped, not every date:** a doc legitimately mentions
many dates in prose; only a date that IS a currency claim (a banner)
counts. That scoping is itself a judgment — which is why check 12 is an
agent-read discipline, not a date-lint.

### 13. User-scope drift

Discipline-applied, WARN-level, read-only. Catches the drift the knowledge
processor's write rules are meant to prevent (`skills/knowledge_processor/write.md`
§3, §4 and `history-imports.md` §6), after the fact: copies of a claim and leftover facet metadata in the
person's user scope. Resolve `<user_repo>` through `framework/user-scope.md`; read
`context/user/`, and for sub-check (b) the activity areas of the user repo that use a
person-wide fact, read-only.

**Sub-check (a) — legacy facet tags, badges, counters.** Exact search:

```bash
grep -n -E '\[(ROLE|COMPETENCE|KNOWLEDGE_AREA|LEARNING_EDGE|CONTEXT_ENV|HARDWARE|SOFTWARE|RELATIONSHIP|TRAIT|STANCE|BELIEF|INTEREST|PREFERENCE|DRIVE|VALUE|GOAL|FEAR|CONCERN|ASPIRATION|PREOCCUPATION|REFLECTION)\]|\[(stable|new|changed|emerging|growing)([ ,][^]]*)?\]([^(]|$)|obs:[0-9>]|confidence:|[→←] ?(VALUE|GOAL|BELIEF|Objective):|^#+ *(VALUE|DRIVE|BELIEF|GOAL|FEAR|CONCERN|INTEREST|ASPIRATION|STANCE|TRAIT|COMPETENCE|ROLE|RELATIONSHIP|CONTEXT_ENV|PREOCCUPATION):|--[A-Z_]+-->|^#+ *(Promotion-History|Aufgeloest|Aufgelöst)' "$USER_REPO"/context/user/*.md
```

Any hit → WARN with file and count. A tag, graph node or edge, or a section of a
retired promotion mechanism is legacy metadata, not knowledge; its meaning moves into
plain words when the claim is next written (`skills/knowledge_processor/write.md` §3
translation table).

**Sub-check (b) — one claim, two statements.** Read `soul.md`, `profile.md` and the
topic files. Is any claim — a rule, default, value, preference or fact — stated in more
than one place? Flag a restatement in another file, a dated "origin"/provenance section
beside the current statement, a summary that says something its owner no longer says,
or a user-scope statement of a person-wide fact (employment, location) that is older
than same-subject evidence of equal or better support in an activity area of the user
repo → WARN naming both places and the current statement. A link, a one-line pointer
to the owner or a short source note at the claim is not a copy. Dated entries whose
date and source are the content (events, observations, source indexes) and dated
records marked as not current (earlier interpretations, retained erroneous claims) are
not copies. Judgment, not regex: a copy is usually a paraphrase.

**Sub-check (c) — unrouted topic file.** A `*.md` in `context/user/` other than
`navigation.md` and the recovery file `maintenance-pending.md` that no row of
`navigation.md` routes to → WARN.

**Why report-only:** the check runs where the person's maintenance authority may not
apply (another repository's session, a review). Fixes follow the knowledge processor
when that authority is present.
