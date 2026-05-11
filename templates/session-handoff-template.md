# Session-Handoff Template

Written by save (Step 4) and quicksave (Step 3).
Loaded at boot (RESUME step).
Path is CWD-based: `BuddyAI/context/session-handoff[-<workspace>].md` (CWD under BuddyAI/) or `<CWD>/context/session-handoff.md` (CWD external).

## Purpose

Reconstruct the discussion context for the next session.
Complementary to `plan_engine --boot` (project state) — this one carries
the **conversation context**: what was discussed, what was decided,
what is open, where we stand.

## Rules

1. **Meta-summary ALWAYS** — 3-5 sentences over the entire session.
   Name all topics, completed and open.
2. **9-point blocks ONLY for open/recent topics** — topics that affect
   continuing. Do not replay the whole session.
3. **Completed topics** belong in the meta-summary (1 sentence),
   not in their own 9-point block.
4. **Concrete on open topics** — file names, code snippets, user quotes
   verbatim where relevant. No summary of summaries.
5. **Overwrite** — the file is fully overwritten on every save/quicksave,
   not appended.
6. **Checkpoint aggregation** — if quicksave intermediates exist,
   use them as input rather than reconstructing from scratch.

## Format

```markdown
# Session Handoff

Session: [number] | Date: [YYYY-MM-DD HH:MM]

## Meta-Summary

[3-5 sentences: what was done in this session? Which topics?
Which completed, which open? Overall direction.]

---

## [Open topic 1: speaking title]

1. **Primary intent:** [what does the user want? What is the goal?]
2. **Key concepts:** [important technical concepts, frameworks, patterns]
3. **Files and code:** [which files discussed/changed? Code snippets]
4. **Decisions:** [design decisions with justification]
5. **Errors and fixes:** [what went wrong? How resolved?]
6. **User statements:** [relevant user statements, verbatim where important]
7. **Open points:** [what is still unresolved?]
8. **Current state:** [what was last done? Where do we stand?]
9. **Next step:** [logical next step, if derivable]

---

## [Open topic 2: speaking title]

[Same 9-point structure]
```

## Example meta-summary

> Session 73: Fixed the dashboard infrastructure (deploy-docs.sh, Dockerfile, nginx),
> updated architecture docs, designed and implemented the session-handoff mechanism.
> Dashboard fixes complete. Workflow audit in progress — stale references cleaned up,
> CLAUDE.md changes still open.

## Proportionality

- **Short session (1 topic, completed):** only meta-summary, no 9-point block.
- **Medium session (2-3 topics, partly open):** meta-summary + 1-2 blocks.
- **Long session (5+ topics):** meta-summary + blocks only for the last 2-3 open ones.
  Older completed topics: meta-summary suffices, detail lives in the history entry.
