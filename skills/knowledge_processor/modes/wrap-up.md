# Mode: wrap-up

Guardrails (delta check, write-quality gate, unloading) apply — see SKILL.md.

Brain Logic is part of wrap-up. First read `modes/process.md` and run EXTRACT → IMPACT CHAIN → SIGNAL CHECK.

The proof block from process.md applies to the Brain Logic part. wrap-up adds a history delta as a separate section — no second EXTRACT/IMPACT/SIGNAL block.

## plan_engine --boot output refresh

On every save: regenerate `context/plan_engine --boot output` from the source files. Overwrite completely (DR-3). No append, no merge. The template is in the header of plan_engine --boot output itself. Missing source → omit the section.

## History entry

- Has a history entry already been written this session?
- If no AND the session had substantial work: create a history entry (`context/history/YYYY-MM-DD-HHMM-<topic>.md`)
- If no substance: no history entry. Message: "Nothing substantial to document."

### Format

```markdown
# <Speaking title>

Date: YYYY-MM-DD HH:MM
Agent: <which agent>

## What it was about

<Context: starting situation, goal. 2-4 sentences>

## What was done

<Summary. 3-10 sentences. Key statements, not every detail.>

## Decisions and outcomes

- <Concrete decisions>
- <Changes>
- <New findings>

## Open points

- <What remains to do>
- <Open questions>
```

## Checkpoint aggregation + delta mode

If checkpoints have happened: aggregate checkpoint deltas as the primary input, the delta check runs against unwritten lists. Without checkpoints: full reconstruction against all potentially affected context files (more error-prone).

## Intent drift check

Does the session's work fit the operational intent (plan.yaml)? Drift → document as an open point, suggest an intent update.

## Working-document cleanup

Temporary working documents? Completed → absorb + delete. Still in progress → keep.

## Open points from history → backlog (cross-check)

The primary gate is ACTIONABLE in the IMPACT CHAIN ACT step and Agent Check 7c. In the history entry, "open points" serves as a safety net:

- Every open point that requires concrete action MUST reference a task (→ Task NNN). No task → incident — flow did not trigger the task gate. Create the task immediately.
- Pure observations, questions, "user decides later" → no task, but mark explicitly.
- At the end: `Backlog: → Task NNN, NNN` or `Backlog: no action needed — <reason>`.
