# Fix workflow boundary guarantees transition

Two exact upgrade edges land on `4c092f8c…`. From `b67deec2…`, the transition changes the `root-cause`,
`test-plan`, `code-review` and `commit-deploy` instructions. From `5ee38866…`, it also carries the reviewed
authoring instruction at `fix-execute`, whose condition is a fix that edits text an agent follows.

Both edges preserve all steps, routes, dependencies, required status, completion checks, review adoption and the
commit gate. They permit no rollback or transitive edge. Export preserves the stored creation fingerprint, pause
and review evidence. Pending work sees the current step instruction on the normal workflow entry.

| Retained obligation | Interpretation on the candidate |
|---|---|
| Confirmed recurrence | Both triggering findings need a red class witness on their respective pre-fix revisions. Review severity and source leave that duty intact. |
| Review complete with publication pending | Preserve the original review and its evidence, including when the workflow is already closed locally. The publication owner checks the exact outgoing diff for the independent counterexample on a fix that changes input to a downstream decision or action. Missing evidence holds that push pending a scoped independent check. Record it with the publication work. |
| Other fixes and completed actions | Other fixes use their existing path. Completed reviews, pushes and deployments stay historical. The upgrade adds no replay, reassessment or action to unrelated retained runs. |

Both predecessor engines created fixture runs with completed review and pending publication. The candidate
export preserved the paused carrier bytes. After explicit resume, `--next` surfaced the publication instruction
while retaining the review and original fingerprint. The compatibility check accepts each exact forward pair and
refuses unknown, reverse and cross-workflow pairs.
