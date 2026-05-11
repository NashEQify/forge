# Workflow Template — BuddyAI

Canonical structure for BuddyAI workflows. Every runbook under
`workflows/runbooks/<name>/WORKFLOW.md` MUST contain all the mandatory
fields defined here.

Workflow-specific deviations are permitted but must be explicitly
justified (`— (<reason>)` instead of being omitted).

This template is a reference document, not a runbook. It defines
WHAT MUST be present — the runbooks fill it out workflow-specifically.

---

## Workflow-level mandatory fields

### 1. Header

```
# Workflow: <name>

<one-sentence description>
```

### 2. Trigger

When is this workflow invoked? List the triggers:
user command, system trigger, sub-workflow invoke.

### 3. NOT for

Demarcation: when NOT this workflow but which other instead?
Prevents misrouting. At least 2-3 demarcations with a reference
to the correct workflow.

### 4. Path determination

If more than one depth/path exists: decision tree
(e.g. Build: DIRECT / STANDARD / FULL).
If single path: explicitly state `Single path: <one-sentence justification>`.

### 5. Phase blocks

At least 3 phases: Specify-equivalent + Execute-equivalent +
Close-equivalent. Phase names are workflow-specific
(e.g. Solve: Frame instead of Specify).

Fields per phase: see Phase-level mandatory fields below.

### 6. Iteration bounds (NON-NEGOTIABLE)

```
| Phase | Max | On exceed |
|-------|-----|-----------|
```

Every phase with repetition or retry potential MUST have an
entry. Missing entries = template violation.

### 7. Cross-workflow handoffs

```
| Parent | Sub/Target | Trigger |
|--------|-----------|---------|
```

Which workflows can this one spawn or hand over to?
Omitted only if no handoffs exist
(`— (<justification>)`).

### 8. References

```
| Step/Topic | Detail SoT |
|-----------|-----------|
```

Every referenced skill, protocol or external artefact
MUST be listed here with its path.

---

## Phase-level mandatory fields

Each phase (`### Phase: <name>`) contains exactly these fields
in this order:

| Field | Definition |
|-------|------------|
| **Skills** | Which skills are invoked (name, plus path on first mention) |
| **Input** | What comes in (artefacts, data, context) |
| **Output** | What comes out (artefacts, decisions, signals) |
| **Gate** | When is this phase done (verifiable condition) |
| **Failure** | What happens on error (retry, escalation, abort) |
| **Autonomy** | Decision level: Discuss / Bounded / Agent-autonomous / Mechanical |
| **Protocols** | Loaded protocols (`—` if none) |

After that: numbered steps (concrete flow of the phase).

Fields not applicable to a phase:
`— (<justification>)` instead of being omitted.

---

## Cross-cutting calls

Calls that MUST appear in EVERY workflow at defined points.
Missing calls = template violation.

### knowledge_processor (mode=process)

At phase transitions where new knowledge arises. Not blanket
at every transition, but: where EXTRACT would find something.

**Minimum calls (MUST):**

| Point | What is extracted |
|-------|-------------------|
| After Specify-equivalent | Scope, frame, root cause, decisions |
| After Execute-equivalent | Code changes, findings, artefact results |
| Close | Wrap-up: history entry, context update, IMPACT CHAIN |

Format in the runbook:
`knowledge_processor mode=process: <concrete what gets extracted>`

A phase transition with new knowledge but WITHOUT a knowledge_processor call:
only with explicit justification
(`— (no new extractable knowledge: <reason>)`).

### task_status_update

**MUST calls:**

| Point | Status |
|-------|--------|
| Workflow start | -> in_progress (Step 0 of the first phase) |
| Close | -> done (before commit guard) |

Format in the runbook: `task_status_update -> <status>`

---

## State tracking

### State file (mandatory for Standard+ workflows)

Every workflow with more than one phase and a non-trivial analysis result keeps a
state file: `docs/{workflow}/YYYY-MM-DD-slug.md`.

**Frontmatter schema (workflow-agnostic):**

```yaml
---
workflow: solve | build | review | fix | research | docs-rewrite
problem: "one line"
started: YYYY-MM-DD
phase: {workflow-specific}
status: active | paused | done | aborted
task_ref: NNN | null
artefacts: []
---
```

The body is append-only (new phase = new H2 block). Commit on every phase transition.

### workflow_phase in task YAML

Orientation field (where the task stands, not what happened). Soft-validated.
Set at every phase boundary via `task_status_update`.

### Proportionality rule

- DIRECT / trivial (< 15 min, clear scope): only `workflow_phase`, no state file.
- Standard+: state file from completion of phase 1 onwards (first analysis result is in).

### Sync requirement

`workflow_phase` in the task YAML and `phase` in the state-file frontmatter
MUST always be updated simultaneously. Drift = error.

---

## Compliance check

A runbook is template-compliant when:

1. All workflow-level mandatory fields are present (or justifiably absent)
2. All phases contain all phase-level mandatory fields
3. Cross-cutting calls appear at defined points
4. Iteration-bounds table complete (every phase with loop/retry)
5. References table complete (every referenced skill/protocol)
6. State tracking: state-file path defined (or proportionally justified absent), sync requirement documented
7. No mandatory field silently omitted
