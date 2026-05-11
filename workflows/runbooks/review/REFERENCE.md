# review Workflow — REFERENCE

Detail mechanics for state tracking in the review workflow. The Buddy-facing `WORKFLOW.md`
is the checklist — this file is the reference.

## State file

**Path:** `docs/review/YYYY-MM-DD-<slug>.md` — one file per review run with
YAML frontmatter. After each phase: extend the body, update frontmatter `phase`,
commit. Crash recovery via `ls docs/review/`.

### Frontmatter schema

```yaml
---
workflow: review
problem: "one-line review scope"
started: YYYY-MM-DD
phase: specify | prepare | execute | verify | close
status: active | paused | done | aborted
task_ref: NNN | null
artefacts:
  - docs/specs/foo.md
  - docs/reviews/board/foo-consolidated-pass1.md
---
```

### Body content (append-only, per phase)

| Phase | What gets written |
|---|---|
| **Specify** | Review scope (specs, review type, depth), routing decision |
| **Execute** | Board findings summary, recurring patterns, spec weaknesses |
| **Verify** | Convergence result per pass (CONVERGED/NEEDS-WORK + severity distribution) |
| **Close** | Verdict (PASS/NEEDS-WORK), board_result, readiness |

### workflow_phase updates

At every phase boundary: `task_status_update workflow_phase=<next_phase>` ->
update frontmatter `phase` in the state file -> commit.

## Proportionality + upgrade check

**State file with task ref:** mandatory for every review run with a task ref.
Full state persistence, crash recovery guaranteed.

**State file without task ref (ad-hoc / milestone gate check):** initially no
state file, only workflow_phase. The review starts lightweight.

**Upgrade check in Execute Step 3.5** (see `WORKFLOW.md`) can create the state
file retroactively when the review becomes substantial. Trigger:

- (a) **>10 findings cumulated** across all specs of the gate check
- (b) **Systemic patterns visible** that need documentation
- (c) **Processing time clearly above initial estimate** (>30 min)
- (d) **Cross-spec patterns** valuable for other reviews

On trigger: `mkdir -p docs/review` -> state file `docs/review/YYYY-MM-DD-milestone-<slug>.md`
with frontmatter `phase: execute`. Enter prior scope + findings retrospectively in the body.
No `task_status_update` needed (milestone gate checks have no
task ref), but commit recommended.

## Authoritative note on drift

The state-file body contains the severity distribution and top-3 findings that also appear in
`docs/reviews/board/*-consolidated-*.md`. On inconsistency: **the state file
is authoritative for workflow resume** (run context). Consolidated files are
audit trail (evergreen, post-review auditing).

The redundancy is by design — two consumer classes with different TTL and
read patterns:
- **State file:** read on boot resume, transient bound to the run, lives
  until `status: done`
- **Consolidated file:** read at post-review audit and by other specs,
  evergreen, lives beyond the session

## References

| Topic | SoT |
|---|---|
| State model (Layer-1 ADR) | `docs/solve/2026-04-09-workflow-state-model.md` |
| Task status update | `skills/task_status_update/SKILL.md` |
| Workflow template (compliance) | `workflows/workflow-template.md` |
| Spec board | `skills/spec_board/SKILL.md` |
| Sectional Deep Review | `skills/sectional_deep_review/SKILL.md` |
| Architecture Coherence Review | `skills/architecture_coherence_review/SKILL.md` |
| UX Review (mode=ux) | `skills/spec_board/SKILL.md` |
| Convergence loop | `skills/convergence_loop/SKILL.md` |
