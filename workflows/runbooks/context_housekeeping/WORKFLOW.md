# Workflow: context-housekeeping

## Purpose

Periodic upkeep of the context system. Triggered manually
when you suspect that the context has become inconsistent,
overloaded, or poorly structured over time.

The context system is a living system: areas emerge, grow,
get restructured or merged. This workflow ensures the
structure stays healthy.

## When to run

- After larger restructuring work.
- When you feel that context is stale or unwieldy.
- Periodically (e.g. monthly) as a health check.

## Phase 1: analysis

Check the entire context system:

1. **Line counts:** check every MD file under `context/`
   for >200 lines.
2. **Navigation consistency:** every file must be linked
   in the corresponding `navigation.md`.
3. **Orphan files:** files that exist but are not linked
   in any `navigation.md`.
4. **Dead links:** links in `navigation.md` pointing at
   non-existent files.
5. **Currency:** is the content still correct? Have facts
   changed?
6. **Structure assessment:** are the areas still
   sensibly cut? Are there topics that justify their own
   area? Are there areas that could be merged?

Emit a report with problems and recommendations.

## Phase 2: curation

### Preparation

Before the first write: create the status file
(`workspace/.housekeeping-progress.md`). Enter every area
from the phase-1 report with status "pending":

```
# Housekeeping Progress
Phase: 2
Started: YYYY-MM-DD
Areas:
  - <area-1>: pending
  - <area-2>: pending
  [...]
```

### Per area

For every problem found, call the knowledge_processor skill
(`skills/knowledge_processor/SKILL.md`):

- Files >200 lines: the skill decides what stays in the
  overview and what moves into detail files.
- Stale content: the skill updates or removes.
- Missing areas: the skill creates a new area
  (navigation.md + overview.md).
- Oversized areas: the skill splits into sensible
  sub-areas.
- Too-small areas: the skill folds into an appropriate
  existing area.

The skill works editorially (from coarse to fine) and asks
before changes to existing files.

**After every area: update the status file** (done /
skipped + reason). That is a MUST — DR-9 checkpoint
obligation. On abort or session restart: read the status
file, continue at the last "done".

### Closing

Delete the status file when every area is done / skipped.
Leave no artifacts.

## Guardrails

- Phase 1 is read-only (analysis only).
- Phase 2 uses the knowledge_processor skill with its own
  guardrails (diff before write, new files direct).
- No automatic bulk fixes — review every change
  individually.
