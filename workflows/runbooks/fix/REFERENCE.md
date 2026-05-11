# fix Workflow — REFERENCE

Detail mechanics for state tracking in the fix workflow. The Buddy-facing `WORKFLOW.md`
is the checklist — this file is the reference.

## workflow_phase (ALWAYS)

At every phase boundary: `task_status_update workflow_phase=<phase>`.
Valid phases: `specify`, `prepare`, `execute`, `verify`, `close`, `done`.

Prerequisite: the `task_status_update` skill supports the workflow_phase parameter
(migration point from `docs/solve/2026-04-09-workflow-state-model.md` §Migration plan).

## State file (PROPORTIONAL)

**When:** the fix requires non-trivial analysis (>3 files OR root cause not
obvious OR estimated duration >15 min). Decision is made in Specify Step 0.

**When not:** trivial fixes (≤3 files, clear root cause, <15 min). Only
workflow_phase.

**Path:** `docs/fix/YYYY-MM-DD-<slug>.md` (`<slug>` = kebab-case of the error topic,
max 40 characters).

**Upgrade path:** if the trivial assessment in Specify turns out wrong -> create the
state file retroactively in Specify Step 6 UPGRADE-CHECK. Prior analysis results
get added to `## Root Cause Analysis`.

### Frontmatter schema

```yaml
---
workflow: fix
problem: "one-line root cause or error description"
started: YYYY-MM-DD
phase: specify
status: active
task_ref: NNN | null
artefacts: []
---
```

### Body sections (append-only, after phase completion)

| After phase | Section | Content | Value |
|---|---|---|---|
| **Specify** | `## Root Cause Analysis` | Root-cause hypothesis (proof sentence), evidence, signal-check result, fix scope | **HIGHEST** — 20+ min of analysis work, lost on abort |
| **Prepare** | `## Fix Plan` | Order of changes, affected files, risks | Low for simple fixes, medium for complex ones |
| **Execute** | `## Fix Details` | What was changed, regression insights | Medium — knowledge_processor exists, state file complements |
| **Verify** | `## Verify Result` | Review findings, retest result, any rework rounds | Medium — closes the persistence gap |
| **Close** | `## Lessons Learned` | Pattern, signal-check follow-up tasks | Low — kp takes over |

### Commit rhythm

Commit state-file + frontmatter update at every phase boundary (like solve).

## State-file handling on prepare collapse

For simple fixes (prepare collapses with execute):

- `workflow_phase` jumps straight from `specify` -> `execute`
- State-file frontmatter: directly `phase: execute` (no intermediate `phase: prepare`)
- Prepare body section: stays empty or as a one-liner
  `## Fix Plan\n\nPrepare collapsed — plan emerges inline in Execute.`
- **No drift between `workflow_phase` (task YAML) and state-file frontmatter**

## Authoritative note on drift

The state-file Verify section contains review findings that may also appear in
`docs/reviews/board/*` (when a formal code review has run) and in the context
system (via `knowledge_processor mode=process` of the verify phase).

On inconsistency: **the state file is authoritative for workflow resume** (run-
bound journal). Context-system entries are evergreen knowledge. The
redundancy is by design — two consumer classes (workflow resume vs. pattern
knowledge) with different TTLs.

## References

| Topic | SoT |
|---|---|
| State model (Layer-1 ADR) | `docs/solve/2026-04-09-workflow-state-model.md` |
| Task status update | `skills/task_status_update/SKILL.md` |
| Workflow template (compliance) | `workflows/workflow-template.md` |
| Root-cause-fix primitive | `skills/root_cause_fix/SKILL.md` |
| Code review | `skills/code_review_board/SKILL.md` |
