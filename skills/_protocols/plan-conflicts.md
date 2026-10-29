# Protocol: Conflicts between a plan's tasks

Read it before the first dispatch of a plan, and before the dispatch of a brief written or changed after that plan's
conflict table. A plan's implementation tasks are its stages, dispatches or Buddy-inline parts that each change files
for one piece of approved work. It decides what Buddy checks across those tasks before any of them runs, where the result lives and how each conflict is ruled. The consumers are the
implementers, whose briefs carry the rulings, and the review owner; the cost it prevents is two tasks built on
different readings of one file or interface, found only in review after both are built. The brief signoff and
`skills/impl_plan_review/SKILL.md` check one brief or one implementer's plan; neither compares tasks.

## When

- **One implementation task:** no table. The record named in §The table (on the build workflow, the route
  decision's record, `workflows/runbooks/build/WORKFLOW.md` §Path determination) says
  `conflict table: single implementation task`.
- **Two or more:** write the table below before the first dispatch, from every task's brief; a Buddy-inline task
  enters with its files and outcome. A task whose files are not named yet gets its self row with that as the
  conflict.
- **A brief written or changed after the table:** check that task's rows again before its dispatch, and record the
  recheck in the table.

## The table

Write it into the route decision's record, under `## Conflicts between tasks`; outside the build workflow, into the
decision or state file of the record directory (`skills/_protocols/mca-dispatch.md` §The files). It is the only
record of the check.

| Item | Tasks | Produces → consumes | Found | Ruling |
|---|---|---|---|---|
| `<file or interface>` | `<task> × <task>` | what one writes or defines → what the other reads, cites or builds on | `agrees`, or the conflict | the ruling, the text it rests on and the brief it changed; `—` when it agrees |
| `<task>` (self) | `<task>` | the tests it specifies → the code it specifies; the files it creates → the files it later touches | `agrees`, or the conflict | as above |

- **Pair rows:** one per file or interface per pair of tasks that both touch it. An interface is anything one task
  defines and the other uses: a shape, a name, a value, a section number, a behaviour, a line it cites. The plan's own
  constraints (a file that stays unchanged, a frozen definition) count as a task that consumes: a pair row each, with
  the task whose change reaches them.
- **Self rows:** one per task.

A clean check shows every row with `agrees`.

## Rulings

Rule on each conflict before the next dispatch, against the binding text: the approved acceptance and its exclusions
(`skills/_protocols/approved-acceptance.md`), then the decisions of the architecture spine the spec links, parent
first (`skills/_protocols/architecture-spine.md`), then the spec at `spec_ref`. The plan and the briefs argue for a reading;
they do not bind. Record the ruling in its row with the quoted text it rests on, or with `no binding text` and the
reason for the choice when neither text settles it, and change the brief it affects before that brief's dispatch (exact values live only in the brief, `skills/_protocols/mca-dispatch.md` §The dispatch).

- **The binding text admits two readings, or settles nothing, and the readings give the user different results:**
  take both readings and one recommendation to the caller before the next dispatch (`framework/process-map.md` §Authorization).
- **Every ruling Buddy takes** goes on the list of decisions taken for the user when that list's two tests hold
  (`skills/return_summary/SKILL.md` §Decisions I took for you); the table holds the rest.

## After the dispatches

A review finding on a conflict between tasks is verified (`skills/_protocols/finding-verification.md`) and given its
cause (`skills/convergence_loop/cause-before-answer.md` §Cause before answer) like any other finding. A ruling in the
conflict table on the same location and claim is binding text for that section's wrong-finding check. Conflicts that
only show in the implementation are left to the review.

## Who writes it

Buddy. When Buddy dispatches the check, the call names its model (`framework/models.md` §Naming the model; a plan
review is the Design row), and Buddy persists the return before writing the table from it.

## Source

Superpowers (MIT License, © 2025 Jesse Vincent); Forge's register of adopted methods.
