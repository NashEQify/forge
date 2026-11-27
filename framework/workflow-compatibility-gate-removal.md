# Workflow compatibility — removed review checks (build and fix)

Edges to build and fix without the removed review checks.

The build and fix definitions lost obligations that caught no defect. Steps, ids, order,
routes, variables and the review adoption check are unchanged. Removed:

- the four `file_content_check` leaves on the verdict in the code review steps (build `code-review-board`, fix
  `code-review`) and the step text naming those lines;
- in build `mca-implementation` and fix `fix-execute`, the mandatory `instruction_authoring` call and the read-path
  record for instruction text;
- in fix `root-cause`, `code-review` and `commit-deploy`, the stop on a second verified failure and the independent
  counterexample on the outgoing diff; the class witness stays.

| Retained obligation | Interpretation on the current definition |
|---|---|
| Completed steps | Keep their evidence; nothing is replayed. |
| A code review step in progress | Completes on the adoption check alone; a verdict without the former lines is not refused. |
| An in-progress fix with a recorded recurrence | The class witness still runs red on both triggers; no counterexample is owed before the push. |
| Pending steps | Take the current text. |

The edges are upgrade-only, from each earlier generation that can reach the current definition directly.
