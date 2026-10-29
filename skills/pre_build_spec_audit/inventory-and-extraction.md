# Pre-build spec audit — pre-conditions, inventory and concept extraction

Step-loaded unit of `skills/pre_build_spec_audit/SKILL.md`. Read it before Phase 1 (the Phase 0 pre-conditions come
first), and again before dispatching the Phase 1b foundation re-inventory or a Phase 2 / 2b concept-extraction round.

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
specs that are foundation-relevant but not task-relevant. Example
recurrence: integration specs, harness-core/runtime patterns,
cognitive-architecture, phase-plan specs are not HIGH in phase 1
when the task keyword is narrow (e.g. chat / intake) — but with
the foundation lens they are HIGH-FOUNDATION (worker topology,
brain architecture).

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
