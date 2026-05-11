# build Workflow — REFERENCE

Detail mechanics for state tracking in the build workflow. The Buddy-facing
`WORKFLOW.md` is the checklist — this file is the reference for
frontmatter schemas, body sections and the relationship between the three state artefacts
(gates.yaml, state file, workflow_phase).

## State file (Standard/Full only)

**Path:** `docs/build/YYYY-MM-DD-task-NNN-slug.md`
**Created in:** Specify Step 0
**Form:** Append-only body, commit per phase
**DIRECT:** No state file — only `workflow_phase` in the task YAML

### Frontmatter schema

```yaml
---
workflow: build
problem: "one-line task description"
started: YYYY-MM-DD
phase: specify | prepare | execute | verify | close
status: active | paused | done | aborted
task_ref: NNN
artefacts: []
---
```

### Body sections (append-only, one per phase)

```markdown
## Specify
- Spec: {spec_path}
- Board: {PASS|NEEDS-WORK} — {0C/0H or finding summary}
- Decisions: {interview/council key decisions}

## Prepare
- Delegation: {delegation_path}
- Test design: {tc_count} TCs

## Execute
- Affected files: {list}
- MCA discoveries: {findings not present in code}
- Scope deviations: {none | description}

## Verify
- Code review: {PASS|FAIL} L{0|1|2} — {finding summary}
- UX review: {PASS|skipped} — {findings or reason for skip}
- Spec amendment: {no | yes, reason}
- ADR check: {ADR-NNN written | skipped: <which-triple-condition-missing>}

## Close
- Status: done
- Deploy: {yes|no|n/a}
```

## ADR check

Optional `adr-check` step in the verify phase, after `spec-co-evolve-check`. Triggers
`skills/documentation_and_adrs/SKILL.md` when the ADR-discipline triple is satisfied:

- **Hard-to-reverse** — meaningful cost to switch later
- **Surprising-without-context** — future reader asks "why like this?"
- **Result-of-real-trade-off** — genuine alternatives with justification

All three required. If any is missing -> one-sentence justification, skip, no ADR. Anti-
pattern: ADR inflation. `required: false`, `on_fail: warn` — discipline through
visibility, no block.

Trigger examples in build: new DB driver, auth strategy, schema shape,
API shape (REST vs events), heavy dependency with lock-in.

## workflow_phase (all paths, including DIRECT)

`task_status_update` with `workflow_phase` at every phase boundary:

```
specify -> prepare -> execute -> verify -> close -> done
```

The field is a **pointer** (WHERE the task stands), not storage (WHAT happened).
Consumer: plan_engine, boot resume, status overviews.

## Relationship gates.yaml / state file / workflow_phase

| Artefact | Function | Consumer |
|---|---|---|
| **gates.yaml** | Gate ledger: WHAT has been checked | close verification, audit |
| **State file** | Workflow journal: WHAT has happened | crash recovery, context rebuild |
| **workflow_phase** | Pointer: WHERE the task stands | plan_engine, boot resume |

Complementary, not redundant. gates.yaml is ADR-protected.

## References

| Topic | SoT |
|---|---|
| Task format | `framework/task-format.md` |
| Task status update | `skills/task_status_update/SKILL.md` |
| State model (Layer-1 ADR) | `docs/solve/2026-04-09-workflow-state-model.md` |
| Workflow template (compliance) | `workflows/workflow-template.md` |
| Gate template | `workflows/templates/gates-template.yaml` |
