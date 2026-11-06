# Protocol: MCA dispatch with brief and report files

Read it before every main-code-agent dispatch with a brief: every dispatch except DIRECT work that closes in its turn
(`framework/direct-eligibility.md` §The DIRECT run), which carries its record in the prompt. Read it also before
adopting such a dispatch's return, and, as the implementer, before the first change (§The size limit),
before changing code for a fix brief and before the return. It decides where the brief and the report live, what the
dispatch prompt holds, which implementer takes a fix pass, how it answers each finding of a fix brief, when the
implementer stops on size and what the return holds. The consumers
are the implementer, who works from the brief file, and Buddy and the review seat, who work from the report. The cost
it prevents: a brief that exists only as a prompt, so no reviewer, fix brief or resume can open it; a dispatch that
repeats the brief; and a return whose full detail fills Buddy's context although the review seat reads it anyway.

Before the first dispatch of a plan, and before dispatching a brief written or changed after that plan's conflict
table, read and follow `skills/_protocols/plan-conflicts.md` (the table across the plan's tasks, or a single task's
recorded skip).

## The files

- **Record directory:** the work unit's records.
  - On the build workflow's STANDARD or FULL path, the brief is the bound `brief_path` file, and its directory is the
    record directory.
  - Otherwise it is `docs/<workflow>/<date>-task-<id>-<slug>/`, with `build` as the workflow when none runs, and
    `<date>-<slug>/` for work without a task.

  These files are the only state carrier for the dispatch: no separate ledger or workspace directory.
- **Brief file:** the whole brief, in the form its template sets (`skills/_protocols/mca-brief-template.md` or
  `skills/_protocols/fix-brief-template.md`), with its exact values and, for work on a task with acceptance criteria,
  the checked `## Approved acceptance (read-only)` block (`skills/_protocols/approved-acceptance.md`). Name it
  `mca-brief.md` when no bound path exists, and `mca-fix-<n>-brief.md` for fix pass n.
- **Dispatch and report files:** beside the brief, named after it: `-brief` becomes `-dispatch` or `-report`
  (`mca-brief.md` → `mca-dispatch.md`, `mca-report.md`); a brief name without `-brief` gets the suffix before `.md`.

## The dispatch

The prompt holds these five parts, in this order:

1. **Where it fits:** the task's `intent_chain` (`framework/intent-tree.md`), or for work without a task one line
   naming the defect, and who integrates the result.
2. **Brief:** the brief file's path, with the instruction to read it first, as the requirements whose values are used
   as written.
3. **From earlier work:** each interface or decision from an earlier task or pass that the brief cannot know, with
   its path or commit, and each open finding or accepted limit in the area this work touches, by pointer to the review
   verdict or task that holds it. Otherwise `none`.
4. **Resolved:** for each brief sentence Buddy found ambiguous, the sentence quoted and the reading Buddy chose.
   Otherwise `none`.
5. **Report:** the report file's path, and the instruction to write the full return there and reply with the short
   return (`skills/return_summary/SKILL.md` §Short return).

Exact values (paths, counts, signatures, test cases, boundaries) appear only in the brief: a new value or boundary
goes into the brief file, and the acceptance check runs again on the file. The dispatch holds one piece of work;
part 3 holds only what that work uses, never a summary of earlier tasks, passes or the session. Buddy saves the
dispatch text in the dispatch file before dispatching, under a first line `BASE: <sha>`
(`skills/code_review_board/review-package.md` §BASE) and a second line `MODEL: <model> (<role row>)`, the model the
call passes (`framework/models.md` §Naming the model).

When the brief requires `skills/impl_plan_review/SKILL.md`, the implementer writes its plan to the report file and
replies `PARTIAL` with `plan ready for review` in Concerns; Buddy runs the review and dispatches again with the gate's
result in part 3.

## A fix pass's implementer

A fix pass goes to the implementer of the previous pass of the same change (for the first fix pass, the implementer
of the change), resumed: Buddy sends that agent a message (Claude Code: `SendMessage` to its agent id) instead of a
new dispatch, so it keeps what it learned of the code and of its own choices. The message holds the five parts, with
the fix brief and its report file; Buddy saves it as the pass's dispatch file, with the `MODEL` line
`MODEL: <the resumed agent's model> (<the fix brief's role row>; resumed <agent id>)`.

A new dispatch takes the pass instead in these cases, checked in this order:
- the stuck cause holds (`skills/convergence_loop/cause-before-answer.md`): one tier above, as that row says; from then
  on this implementer is the one resumed;
- the resumed agent's model is below the fix brief's row (`framework/models.md`): the row's tier;
- the host refuses the message or has no way to send one: the fix brief's row.

A new dispatch's part 3 names the implementation brief and report and every earlier fix brief and report of the
change: these files are the record of what was tried. A re-dispatch on the same brief after Buddy's rulings
(`## Re-dispatch <n>` below) belongs to the same fix pass: it goes to the same implementer in the same way and is not a
pass of its own.

## A fix brief's findings

As the implementer, before changing code for a fix brief: read and follow
`skills/_protocols/mca-dispatch-fix-findings.md` (per finding: check the briefed change, then one `applied`,
`pushed back` or `unclear` row under `## Findings received`).

## The size limit

The brief states a product-code limit and a test limit (`skills/_protocols/mca-brief-template.md` §Stop limit; in a
fix brief, `scope_bound.stop_limit`). After each commit, and after each test run when the brief forbids commits (new
files first marked with `git add -N`), the implementer runs `git diff --stat BASE -- <the brief's product paths>`, with
BASE from the dispatch file's first line, and takes the changed lines (insertions plus deletions) from its last line.
When they reach the product-code limit, the implementer stops: no further change, the report with that diffstat and
the remaining work, and the short return `PARTIAL` with the Concerns line
`product-code limit reached: <n> of <limit> lines`. The test limit stops nothing; a test diff above it is the Concerns
line `test limit exceeded: <n> of <limit> lines`. A brief without limits gets the Concerns line
`no stop limit in the brief`, and nothing is measured.

## Tests still failing at the return

The implementer changes no test the skeleton return lists (its assertions or its fixtures) at any point of the
dispatch. When a test the brief requires to pass still fails at the return, the report has one row per failing TC under
`## Still-failing tests`:

```markdown
| TC | Failing assertion | Class | Why this class |
|---|---|---|---|
| <id> | <file:line, expected and actual as the run printed them> | product / oracle / fixture | <the brief or spec item, or the observed setup fact, that decides it> |
```

- **product:** the code does not do what the brief or spec item the TC tests requires.
- **oracle:** the code does what that item requires, and the expected value or the assertion contradicts the item or
  another test the brief requires.
- **fixture:** the setup (data, patches, clock, host, the test's own instrumentation) does not reach the TC's
  precondition, or itself produces the effect the TC measures.

Each row is one Concerns line `<TC> <class>: <assertion>`, and the Status is `PARTIAL`. Buddy routes the rows before
any ruling (`mca-dispatch.md` §The return, step 2).

## The return

The implementer writes the report file and replies with the short return. A re-dispatch on the same brief appends to
the report under `## Re-dispatch <n>`. Buddy then:
1. persists the short return verbatim in the work unit's record: its state or decision file, or, when it has neither,
   at the end of the report file under `## Short return (as received)`. The report file already holds the full
   RETURN-SUMMARY, so it is not copied again. Buddy commits the brief, dispatch and report files with the work unit's
   records;
2. routes on the `INCIDENT` line as `agents/buddy/operational.md` §Sub-Agent Return sets, on `Status` (`PARTIAL` or
   `BLOCKED`: Concerns holds the remaining work or the blocker), on each Concerns line (a discovery goes to
   `knowledge_processor`, a test written but not run is run before adoption), on a `SPEC_VERIFICATION: NEEDED`
   line, and on each `pushed back` or `unclear` row under `## Findings received`, which gets a ruling before step 3
   (`skills/convergence_loop/cause-before-answer.md` §Ruling on a pushed-back finding), and on each
   `## Still-failing tests` row before any ruling on it:
   - an oracle or fixture row on a test the skeleton return lists goes back to the skeleton writer with the row and
     the spec item it cites (`agents/test-skeleton-writer.md` §Repair of a failing test);
   - an oracle or fixture row on a test the skeleton return does not list gets Buddy's ruling;
   - a product row, a row the repair returns as `stands`, and a `repaired` test that still fails are the
     implementer's open work for a re-dispatch;
   - a row the repair returns as `spec conflict` gets Buddy's ruling;
3. builds the review package (`skills/code_review_board/review-package.md`) and hands it, the brief path and the
   report path to the review owner; `skills/code_review_board/SKILL.md` decides which seat receives which input. A
   fix brief is written from the report and the review, not from the short return.

## Left to their owners

- **Review:** comes from Buddy after the report, at the depth `skills/code_review_board/SKILL.md` selects by risk.
  The implementer starts no agents (`agents/main-code-agent.md` §What the coder does NOT do).
- **Commits:** the implementer commits only where the request or the repository's standing policy allows it
  (`agents/main-code-agent.md` §Workflow); the brief says which applies.
- **Authorization:** `framework/process-map.md` §Authorization.

## Source

Superpowers (MIT License, © 2025 Jesse Vincent); Forge's register of adopted methods.
