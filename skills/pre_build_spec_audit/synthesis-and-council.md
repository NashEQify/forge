# Pre-build spec audit — synthesis, triage and conditional council

Step-loaded unit of `skills/pre_build_spec_audit/SKILL.md`. Read it when the Phase 2 returns are in, before the
synthesis and the user dialog, and before spawning a council on a NEW-METHODOLOGY entry. When the synthesis shows
imminent foundation decisions, the Phase 1b trigger in `inventory-and-extraction.md` applies.

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
Council). Mode per `council/SKILL.md` §1.0 proportionality (light = 3 members +
chief; standard = + council-adversary + pre-council frame
check; full = 4-6 members). The briefing file contains:
- Phase-3 synthesis (NEW-METHODOLOGY section).
- Pre-MVP prescription(s) verbatim + context (spec era,
  picture).
- Current MVP build status.
- Solution-candidate enumeration (MVP stays / adopt pre-MVP idea
  / hybrid / post-MVP migration with bridge) — listed without
  lean / recommendation / severity per `council/run.md` §3
  cold-start brief (candidates are domain-derived solution-space
  mapping, not Buddy's proposal — but the briefing must not
  flag any as preferred).
- Per-option reversibility cost-band.

If audit fires in build context: Buddy starts the workflow
engine (`workflow_engine.py --start build --task <id>`) in the
same tool block as council spawn — see `skills/council/
REFERENCE.md` §Workflow_engine handshake.

The user decides finally.
