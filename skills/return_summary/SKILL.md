---
name: return-summary
description: >
  Format and rules for sub-agent return summaries. Load before
  step 8 (return).
status: active
relevant_for: ["main-code-agent", "tester", "security", "solution-expert"]
invocation:
  primary: sub-skill
  secondary: [workflow-step]
disable-model-invocation: false
uses: []
---

# Skill: return-summary

Format and rules for the return summary. Load this skill before
step 8 (return).

---

## Spec-assumption diff (MUST — before discoveries)

1. Read the spec assumptions (constraints, external
   dependencies, schema, service behaviour).
2. Compare with what was actually found.
3. Every deviation is a discovery — even if worked around in the
   code.

Examples: NATS reconnect not natively available, IVFFlat only
effective from 1000 rows on, an env var is ignored, an API
signature changed.

`Discoveries: none` only after an explicit diff. Not as a
default.

## Format

```
RETURN-SUMMARY:
  Task:    <task ID + title>
  Status:  DONE | PARTIAL | BLOCKED
  Changes:
    - <path>: <what changed, one sentence>
  New-Files:
    - <path>: <purpose, one sentence>
  Deleted-Files:
    - <path>: <reason, one sentence>
  Spec-Assumption-Diff: executed
  Discoveries:
    - <fact that may concern context / decisions / backlog, one sentence>
  Spec-Updates: v<old> → v<new> | none
  SPEC_VERIFICATION: NEEDED | NOT_NEEDED
    Changed: [file list, only on spec changes]
    Reason: ">1 spec" | "DESIGN/ARCHITECTURE" | "interface contract" | "single-spec PATCH"
  INCIDENT: No | Yes (see below)

Tester: SIGNED OFF (N tests, M new) | NOT SIGNED OFF — <reason>
```

## Incident block (MUST always be present — even when no incident)

Buddy can't read along during execution (ARCH-007). Incidents
have to be visible structurally in the return.

No incident:

```
INCIDENT: No
```

On an incident:

```
INCIDENT: Yes
Type: [SPEC-STALE / TEST-FAIL / MISSING-FILE / LOGIC-ERROR / ARCH-CONFLICT / SCOPE-CREEP / OTHER]
Scope: trivial / substantial
Description: [1-2 sentences]
Action: [AUTO-FIXED / ESCALATED / STOPPED]
```

## Closing line (hard gate)

The **last line** of the return summary MUST be:
`Tester: SIGNED OFF (N tests, M new)` or
`Tester: NOT SIGNED OFF — <reason>`.

If the line is missing → the task counts as not closed.

Applies on non-code tasks too:
`Tester: NOT SIGNED OFF — no testable code, only <type>`.

## Boundary

- No test design → testing skill.
- No code review → code_review_board.
- No test execution → tester agent (return_summary only
  documents the result).

## Anti-patterns

- **NOT** set SIGNED OFF without tester confirmation. INSTEAD
  the tester confirms; the return summary reproduces.
  Because: self-assignment makes the gate worthless.
- **NOT** drop the incident block when nothing notable
  happened. INSTEAD say "Incident: none" explicitly. Because:
  absence of incident is information too.
- **NOT** write the return summary before retest closure.
  INSTEAD retest → result → summary. Because: a premature
  summary skews the status.
