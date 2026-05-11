---
name: pre-build-spec-audit
description: >
  Concept mining + MVP reconciliation against pre-existing specs.
  Looks at pre-MVP / pre-build specs for methodology, architecture
  ideas, and patterns — compared in the current MVP scope, not as
  a compliance check. Phase 1 inventory, phase 2 parallel concept
  extraction, phase 3 triage (MATCH / MVP-INTEGRATE /
  NEW-METHODOLOGY / POST-MVP-VISION / PRE-MVP-DROPPED), phase 4
  conditional council.
status: active
invocation:
  primary: workflow-step
  secondary: [user-facing, sub-skill]
disable-model-invocation: false
uses: [council, _protocols/context-isolation, _protocols/dispatch-template]
---

# Skill: pre-build-spec-audit

Concept and architecture mining across pre-existing specs against
a concrete build / task. Prevents pre-thought methodology from
being lost during MVP construction AND prevents obsolete pre-MVP
pictures from being misread as a prescription.

## Guiding principle

**Foundation builds can't be over-thought.** Pre-MVP specs are
not prescriptions — they are a thinking source from a larger
(often post-MVP) picture. The skill is a depth tool, not a
compliance check.

## When to call

Required on:

- **Foundation build** (AI brain, memory, intake pipeline,
  knowledge graph, auth layer, etc.) — where "not quite right"
  is expensive later.
- **Cross-domain construction** (>2 domain boundaries) —
  pre-MVP specs likely thought through cross-cutting patterns.
- **Repo with a large spec history** (>20 specs from older
  iterations).
- **Retroactive after a code-review FAIL** with spec-drift
  findings — is the drift class a pre-MVP picture or a real
  build bug?
- **User question** "was that already thought through?" —
  immediately this skill.

Optional on smaller builds when the cross-spec relationship is
unclear.

## Boundary against related skills

| Skill | Scope | When |
|-------|-------|------|
| **spec_board** | Single-spec review (NEW spec) | A new spec is reviewed |
| **spec_corpus_review** | Full corpus, milestone gate | Before milestone release, all specs together |
| **sectional_deep_review** | One large spec, sectional | Foundation spec >1000 lines |
| **spec_amendment_verification** | Code vs spec post-build | Verify code follows the spec (spec=SoT) |
| **retroactive_spec_update** | Code → spec (fix drift) | Code is SoT, the spec is adapted |
| **pre-build-spec-audit (this)** | Concept mining + MVP reconciliation | What did pre-MVP think through — what of it is viable? |

Other skills treat specs as SoT.
**This skill treats specs as a thinking corpus.**

## Phase 0 — pre-conditions

Buddy checks before phase 1:

1. The build / task scope is clear (concrete modules + patterns
   + APIs nameable).
2. **An MVP definition exists** (what is in the current
   milestone, what is explicitly post-MVP?). Without an MVP
   boundary the skill cannot triage.
3. **Check the roadmap mapping.** When the repo has
   task-milestone mappings (e.g. `docs/tasks/*.yaml` with a
   `milestone:` field), build the milestone index:
   `grep -h "^milestone:" docs/tasks/*.yaml | sort | uniq -c`.
   That is the roadmap topology — POST-MVP concepts from
   pre-MVP specs often already have a roadmap slot (e.g.
   `intake-mvp` → `intake-worker` → `enterprise-intake`). The
   triage in phase 3 links to existing slots instead of
   creating new backlog entries.
4. The spec directory exists and is filled
   (`docs/specs/*.md`, at least 5 specs).
5. Output directory: `mkdir -p docs/reviews/audits/`.
6. Briefing snippet ready: what was built / planned + the MVP
   boundary + roadmap mapping (post-MVP milestone list).

If the MVP boundary is unsharp: STOP, clarify the milestone
scope with the user first.

## Phase 1 — inventory + relevance scoring

**Goal:** a table of every spec in the corpus with relevance
scoring for the concrete build. Prevents phase 2 from reading
every spec in depth.

**Important — lens:** phase 1 uses the **task lens** (keywords
from the concrete build). That is fine for initial filtering.
But when phase 3 shows that foundation decisions are needed
(architecture re-topology, schema-authority refactor, mass-intake
path), trigger phase 1b with an extended **foundation lens** —
see below.

**Dispatch:** 1 Explore agent (very-thorough), background.

**Agent prompt skeleton:**

```
List every spec under docs/specs/ (*.md, excluding archive/).
Per spec:
  - read the header (first 50 lines)
  - grep for build keywords (provided by the caller)
  - classify HIGH / MEDIUM / LOW / NONE

Calibration:
  - HIGH = direct concept / architecture link to the build
  - MEDIUM = adjacent, likely relevant patterns
  - LOW = touches similar concepts
  - NONE = orthogonal

Output format (table):
  | Spec | Size | Relevance | Reason | Key sections |

Plus a short list of HIGH-relevance specs at the end.
Output file: docs/reviews/audits/{date}-{task-id}-pre-build-audit-phase1.md
```

**Output expectation:** 5-15 HIGH-relevance specs out of a
typical 30-50 spec corpus. When > 20 HIGH: build scope too
broad, consider sub-tasking.

## Phase 1b — re-inventory with the foundation lens (CONDITIONAL)

**Trigger:** the phase-3 synthesis shows that foundation
decisions are imminent (worker topology, schema-authority
refactor, mass-intake path, cross-domain patterns). The phase-1
task lens is then too narrow.

**Mechanic:**
- 1 Explore agent (very-thorough), background.
- Re-scan the non-HIGH specs from phase 1 (i.e. LOW / MEDIUM /
  NONE).
- **Extended keyword sets** (provided by the caller): worker /
  async-topology / schema-authority / mass-intake /
  cross-cutting / outbox / observability.
- Classification HIGH-FOUNDATION / MEDIUM-FOUNDATION / NONE.
- Expectation: 5-15 additional HIGH-FOUNDATION specs (on top
  of phase 1's HIGH list).

**Pattern observed:** phase 1 with task keywords filters out
specs that are foundation-relevant but not task-relevant.
Example task 380: `cognee-integration-spec.md`,
`harness-core-4.md`, `harness-runtime-patterns.md`,
`proactive-surfacing-impl.md`, `phase-6-plan.md`,
`cognitive-architecture.md` were not HIGH in phase 1 (no chat /
intake keyword), but with the foundation lens they are
HIGH-FOUNDATION (worker topology, brain architecture).

**When phase 1b is not needed:**
- The build is single-domain without cross-cutting (e.g. a UI
  component).
- Phase 3 synthesis shows only surgical MVP-INTEGRATEs, no
  architecture drift.
- The roadmap has no adapter extension within reach.

**Output:**
`docs/reviews/audits/{date}-{task-id}-pre-build-audit-phase1b.md`.

Phase 2b follows analogously to phase 2 for the HIGH-FOUNDATION
specs.

## Phase 2 — concept extraction (parallel)

**Goal:** per HIGH spec extract methodology / architecture /
patterns / data models — structurally compared with what we are
building, in MVP scope.

**IMPORTANT:** phase 2 is **concept mining**, not "drift
hunting". Pre-MVP specs must NOT be treated as prescriptions —
many patterns inside them are explicitly post-MVP picture
(worker service, event bus, multi-region, etc.) and not in MVP
scope.

**Dispatch:** N parallel agents (1 per HIGH spec), all in ONE
tool block. Recommended agent type: `general-purpose` with
spec reading + cross-reference.

**Agent prompt skeleton:**

```
Read fully: {spec-path}

Extract concepts / methodology / architecture patterns / data
models that this spec already thought through. Compare against
the current build:

Per concept entry, structured:

| Concept | Pre-MVP spec says | Current build does | MVP assessment |

MVP assessment (5 classes):

- **MATCH**         — concept is implemented in the build (with naming / spec drift, spec maintenance)
- **MVP-INTEGRATE** — concept is MVP-viable and should land — now or in the next pass
- **NEW-METHODOLOGY** — pre-MVP spec has an approach that could improve our current solution architecturally — council trigger
- **POST-MVP-VISION** — concept belongs to the larger roadmap picture (e.g. worker service, NATS, multi-tenancy); MVP intentionally goes without; post-MVP picks it up. Check the roadmap mapping: does a post-MVP milestone / task already cover it? (link instead of recreating backlog)
- **PRE-MVP-DROPPED** — pre-MVP idea isn't in the current picture at all (neither MVP nor post-MVP). Rare. Spec note "dropped" or spec archival.

**Bias avoidance:**
- Do NOT frame everything as "DRIFT" — pre-MVP specs were the
  bigger picture.
- POST-MVP-VISION is OK and expected; it is NOT a build deficit
  and NOT obsolete.
- POST-MVP-VISION is NOT a "backlog task" — it is a roadmap
  position, often already mapped to a milestone.
- Honest check: does our MVP build make the concept point worse
  than the pre-MVP spec? If yes → NEW-METHODOLOGY council
  material.
- Inspiration question required: "What could we have learned
  from this spec that we haven't yet considered?"

Output file: docs/reviews/audits/{date}-{task-id}-pre-build-audit-phase2-{spec-name}.md
```

**Pattern requirement:**
- Dispatch all agents in the SAME tool block (parallel
  wall-clock).
- `run_in_background=true` when > 3 agents.
- Every agent context-isolated (sees ONLY its spec + the build
  brief + the MVP boundary).
- The build brief + MVP boundary are identical for every
  agent.

## Phase 3 — synthesis + triage (Buddy direct + user dialog)

**Goal:** consolidated list from the phase-2 returns. Buddy does
this herself, NO agent — the map-reduce-reduce step.

**Different from drift audits:** phase 3 is not "off into the
fix loop", it is **dialog with the user**. Foundation builds
deserve discussion. Buddy presents the synthesis; the user
decides per class:

**5 triage classes from the phase-2 assessment:**

| Class | Definition | Default consequence |
|-------|------------|---------------------|
| **MATCH** | Concept implemented, possibly naming drift | Spec maintenance via `retroactive_spec_update` (low effort) |
| **MVP-INTEGRATE** | Concept viable, MVP-relevant, missing | Next code-review pass with the fix set |
| **NEW-METHODOLOGY** | Pre-MVP spec has the better approach | Council spawn (phase 4) |
| **POST-MVP-VISION** | Roadmap position, intentionally MVP-deferred | **Check roadmap mapping first:** existing post-MVP milestone / task? Link to it. Only if none: `task_creation` with the correct milestone (NOT a generic "backlog") |
| **PRE-MVP-DROPPED** | Really not in the picture anymore (rare) | Spec note "dropped" or spec archival (with user approval) |

**Output:**
`docs/reviews/audits/{date}-{task-id}-pre-build-audit-synthesis.md`.

Format:
- Section per triage class.
- Per entry: spec path + concept + current build status +
  recommendation + effort.
- Closing: user-dialog questions (not autonomous decision):
  - "MVP-INTEGRATE points X, Y, Z — all in the next pass? Or
    prioritize?"
  - "NEW-METHODOLOGY A — council? Or stay in the current
    build?"
  - "POST-MVP-VISION B, C — already mapped to roadmap milestone
    {X}; D, E — no slot, new milestone entry or task in
    {Y}?"
  - "PRE-MVP-DROPPED F — archive the spec or note?"

**Buddy does NOT decide autonomously** between the classes —
foundation builds are user decisions. Buddy synthesizes; the
user chooses.

## Phase 4 — conditional council (NEW-METHODOLOGY)

**Trigger:** phase 3 marks a NEW-METHODOLOGY entry AND user
approval for a council spawn.

NEW-METHODOLOGY means: the pre-MVP spec has an architectural
approach that could improve our current MVP solution. A
trade-off analysis is needed.

NEW-METHODOLOGY examples:
- Pre-MVP had an outbox pattern for brain-vs-DB consistency —
  we do best-effort. Outbox MVP-viable or too complex?
- Pre-MVP had a trust pipeline with weighted confidence — we
  have binary quarantine. Pipeline MVP-relevant?
- Pre-MVP had AMEND-01 IMPACT-CHAIN-mutator architecture — we
  do direct update. Mutator pattern MVP-relevant?

**NOT council** for:
- API diff, field-name drift, const-value drift.
- Sub-section adjustments of the spec.
- Spec-maintenance candidates.

**Council spawn:** via `council/SKILL.md` (Architectural
Council, 3-4 council-members in parallel). The briefing file
contains:
- Phase-3 synthesis (NEW-METHODOLOGY section).
- Pre-MVP prescription(s) verbatim + context (spec era,
  picture).
- Current MVP build status.
- 2-4 solution candidates (MVP stays / adopt pre-MVP idea /
  hybrid / post-MVP migration with bridge).

The user decides finally.

## Output paths

```
docs/reviews/audits/
  {date}-{task-id}-pre-build-audit-phase1.md         # inventory
  {date}-{task-id}-pre-build-audit-phase2-{spec}.md  # 1 per HIGH spec
  {date}-{task-id}-pre-build-audit-synthesis.md      # triage + user dialog
  # if phase 4 was triggered:
  docs/reviews/council/{date}-{task-id}-pre-build-audit-{role}.md
```

## Contract

### INPUT

- **Required:** build / task ID + module list + pattern list +
  decisions list.
- **Required:** **MVP boundary** (what is in, what is post-MVP)
  — explicit.
- **Required:** `docs/specs/` directory with pre-existing specs.
- **Optional:** frame report from `frame` (shortens
  inventory).
- **Context:** task file `docs/tasks/{task-id}.md` with build
  notes.

### OUTPUT

**DELIVERS:**
- Inventory table (every spec with a relevance score).
- Phase-2 concept-extraction files (1 per HIGH spec).
- Synthesis file with the 5 triage classes.
- User-dialog questions (instead of autonomous decisions).
- Recommendation to Buddy / user per class (pass-fix /
  backlog / council / spec maintenance).

**DOES NOT DELIVER:**
- No spec edits — triage shows what; `retroactive_spec_update`
  does the editing.
- No code edits — found MVP-INTEGRATEs are fixed in the next
  pass loop.
- No ADR entries — phase-4 council may recommend an ADR.
- No autonomous triage decisions — the user chooses per class.

**ENABLES:**
- Next code-review pass with the MVP-INTEGRATE fix set.
- Follow-up tasks (post-MVP backlog, `retroactive_spec_update`
  for MATCH).
- Council spawn on NEW-METHODOLOGY.
- Spec cleanup on PRE-MVP-OBSOLETE.

### DONE

- Phase 1 inventory persisted.
- Phase 2 every HIGH spec concept-extracted.
- Phase 3 synthesis + triage persisted.
- The user has decided per triage class.
- Phase 4 (if triggered) council decision documented.

### FAIL

- **Retry:** phase 1 finds > 20 HIGH specs → build scope too
  broad, sub-tasking, the skill runs again per sub-task.
- **Escalate:** phase 3 finds > 3 NEW-METHODOLOGY with
  substantial architecture implication → build pause; council
  spawn unavoidable; possibly spec authoring for a revised
  architecture.
- **Abort:** the build is withdrawn by the user → the skill
  terminates without synthesis.

## Boundary

- **No single-spec review.** That is `spec_board`.
- **No full-corpus review.** That is `spec_corpus_review`
  (milestone gate).
- **No spec edits.** The synthesis shows what;
  `retroactive_spec_update` or `spec_update` makes the edits.
- **No code edits.** MVP-INTEGRATE findings land in the next
  code-review pass loop.
- **No compliance check.** Pre-MVP specs are a thinking
  corpus, not SoT — for code-vs-spec compliance use
  `spec_amendment_verification`.

## Anti-patterns

- **NOT** treat pre-MVP specs as prescriptions. **INSTEAD** as
  a thinking corpus — many pre-MVP patterns were thought for
  post-MVP (worker, event bus, multi-region) and are not a
  build deficit in MVP but a scope decision. Because: a
  "DRIFT / BLOCKER" framing creates compliance pressure on the
  MVP scope; that is anti-foundation building.

- **NOT** start phase 2 without phase 1 ("read all 45 specs in
  depth"). **INSTEAD** always run phase 1 filter first, then
  read only HIGH-relevance deeply. Because: phase 2 deep on 45
  specs is 30+ agent calls, token burn without value — most
  specs are orthogonal.

- **NOT** dispatch phase 2 sequentially. **INSTEAD** all N
  HIGH-spec agents in the SAME tool block, `run_in_background`
  on N>3. Because: wall-clock advantage is the point of map
  reduce — sequential takes 5x as long.

- **NOT** triage phase 3 autonomously and head into the fix
  loop. **INSTEAD** dialog with the user across the 5 classes
  — foundation builds deserve discussion; autonomous triage
  decisions burn pre-thought concepts. Because: Buddy can't
  draw the MVP boundary finally; the user decides what is
  MVP-viable.

- **NOT** lump everything as POST-MVP-VISION because "the
  pre-MVP picture was different". **INSTEAD** check honestly
  per concept whether the underlying methodology is MVP-viable
  (sometimes the idea is good and only the topology was
  post-MVP). Because: blanket POST-MVP throws away foundation
  maturity.

- **NOT** frame POST-MVP-VISION as a "backlog task" and
  blindly file it via `task_creation`. **INSTEAD** check the
  roadmap mapping — many pre-MVP concepts already have a
  post-MVP milestone slot (e.g. `intake-mvp` →
  `intake-worker` → `enterprise-intake`). Only when no slot
  exists: a new task in the right milestone, not generic
  "backlog". Because: the roadmap topology is lost when
  everything ends up as a generic backlog task.

- **NOT** classify worker-service / NATS / event-bus /
  multi-tenancy concepts as PRE-MVP-DROPPED just because MVP
  doesn't have them. **INSTEAD** that's almost always
  POST-MVP-VISION with an existing roadmap slot. DROPPED is
  the rare class — only when the idea appears neither in the
  current MVP nor in the post-MVP roadmap. Because:
  foundation skipping of post-MVP concepts devalues the
  vision.

- **NOT** trigger NEW-METHODOLOGY council on API diff or
  field-name drift. **INSTEAD** that's MATCH or MVP-INTEGRATE,
  not council. Because: the council is for architectural
  trade-offs, not surgical patches — council inflation
  devalues the instrument.

## Relation to the code-review loop

The skill is a companion to the code-review-board loop:

```
Foundation build planned OR code-review pass N FAIL
  → pre-build-spec-audit (this skill)
  → 5-class triage (MATCH / MVP-INTEGRATE / NEW-METHODOLOGY / POST-MVP-VISION / DROPPED)
  → user dialog per class
  → MVP-INTEGRATE in the next code-review pass
  → NEW-METHODOLOGY potentially council spawn (phase 4)
  → POST-MVP-VISION linked to an existing roadmap milestone or a new task in the right milestone
  → MATCH potentially spec maintenance via retroactive_spec_update
  → DROPPED spec note or archival
  → code-review pass N+1 with a better-thought-through foundation
```

## Relation to spec_corpus_review

| Axis | spec_corpus_review | pre-build-spec-audit |
|------|--------------------|-----------------------|
| Scope | Full corpus, every spec | Subset, task-focused |
| Frame | Specs as SoT, consistency check | Specs as a thinking corpus, concept mining |
| Trigger | Milestone gate | Before / after a build pass |
| Phases | 7+ (phase 0-7) | 4 (1-2-3-4 conditional) |
| Triage | Cross-spec findings | 5-class MVP reconciliation |
| Wall-clock | Days | < 1 hour |
| Output | Cross-spec findings, impl order | Triage list + user dialog |

The two coexist. `corpus_review` is a heavyweight milestone
gate. `pre-build-spec-audit` is lightweight per-build with a
concept-mining focus.
