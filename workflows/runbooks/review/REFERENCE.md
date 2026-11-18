# review Workflow — REFERENCE

Detail mechanics for state tracking in the review workflow. The Buddy-facing `WORKFLOW.md`
is the checklist — this file is the reference.

## State file

**Path:** `docs/review/YYYY-MM-DD-<slug>.md` — one file per review run with
YAML frontmatter. After each phase: extend the body, update frontmatter `phase`,
and persist the result. Phase commits follow `framework/process-map.md` section
Authorization: commit only under an applicable request or standing repository
policy. Continue unchanged authorized actions without routine reapproval; local
review work grants no push/deployment authority. Authorized missing publication
remains an unresolved obligation, not successful publication on local review closure.
Crash recovery via `ls docs/review/`.

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
  - docs/specs/<name>.md
  - docs/reviews/board/<name>-consolidated-pass1.md
  - docs/reviews/board/<NNN>-spec-verdict.md   # task-less run: <name>-verdict.md
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
update frontmatter `phase` in the state file -> persist; commit only when authorized
under the State file rule above.

## Current evidence and required success

Before mandatory dispatch, load `skills/_protocols/evidence-pointer-schema.md` §9.
The run's exact board-dispatch owner captures before production and remains the
owner after dispatch completes while the workflow is live. Pass this identity to
nested skills. Persist complete attributed returns, write an explicit current
decision, and adopt it. Dispatch uses evidence policy so NEEDS-WORK can reach repair.
After relevant fixes: retry that owner, fresh-capture, run the existing applicable
verification, adopt the resulting decision and return through existing steps.
Required phase-close checks spec_success BEFORE review-derived task YAML writes;
optional convergence skip cannot bypass it. Refusal/error leaves requested fields
unchanged. Result/readiness mapping is public §9.6, not a task-existence predicate.
Canonical locators must match retained bytes; earlier payloads remain history.

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
task ref); a commit is recommended only when authorized under the State file rule
above. Retain the local state file when no commit is authorized.

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
| State model | `framework/workflow-engine-cookbook.md` |
| Task status update | `skills/task_status_update/SKILL.md` |
| Workflow template (compliance) | `workflows/workflow-template.md` |
| Spec board | `skills/spec_board/SKILL.md` |
| Sectional Deep Review | `skills/sectional_deep_review/SKILL.md` |
| Architecture Coherence Review | `skills/architecture_coherence_review/SKILL.md` |
| UX Review (mode=ux) | `skills/spec_board/SKILL.md` |
| Convergence loop | `skills/convergence_loop/SKILL.md` |
