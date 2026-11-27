# Protocol: Approved acceptance in briefs

Read it when you write or reissue a brief for work on a task that has acceptance criteria under `docs/tasks/`: an
implementation brief (`skills/_protocols/mca-brief-template.md`), a fix brief
(`skills/_protocols/fix-brief-template.md`), a brief the brief-architect drafts, or the brief of a persistent session
(`agents/buddy/coordinating-sessions.md`). It decides how the brief carries what the user approved. The consumer is
the implementer or session that works from the brief; the cost it prevents is a qualifier the user approved being
dropped, weakened or added when the brief restates the acceptance in its own words.

## The block

The brief carries this section before any section that maps, restates or plans against the acceptance:

````markdown
## Approved acceptance (read-only)

Copied from the task file. Do not edit, reword or shorten this block. Where another part of this brief reads
differently, this block counts; report the difference to the briefing Buddy.

```yaml
task: <id>
acceptance_criteria:
  - '<item>'
out_of_scope:
  - '<item>'
approved_by: '<the user''s words, quoted> (<where and when they were said>)'
```
````

- `task`: the task's id.
- `acceptance_criteria` and `out_of_scope`: the task file's lists as they stand, every item in its order and with
  its exact characters. Produce them from the file (print or copy the YAML), not by retyping. A task without
  exclusions gets `out_of_scope: []`.
- `approved_by`: the user's own words that approved this scope or its exclusions, quoted, with where and when they
  were said. Words the author wrote for the user do not belong here. When the records hold no such words, write
  `none recorded: <where the approval stands>`, for example the programme agreement that ordered the task.
- The two sentences under the heading are fixed text; they tell the implementer the reading rule without this
  protocol.

A difference means a part of the brief that drops, weakens, widens or adds a condition to an item in the block: a
mapping table that omits a qualifier, a step that adds an escape, a stop condition the item does not state. A
constraint on how to do the work (a staging copy, a test command) that leaves every item intact is no difference, and
neither is naming the subset of items that is this implementer's part. Other sections may still map items to
obligations and tests; the block is what they map.

## The check

The check reads a file. The brief is a file in the task's records, and the dispatch names that file instead of
carrying its text (for an implementer: `skills/_protocols/mca-dispatch.md`); a brief drafted inline is saved there
first. Before dispatching, and again after any edit to the brief, run from the project
root:

```sh
python3 $FRAMEWORK_DIR/scripts/consistency_check.py --check brief-acceptance --brief <path-to-brief>
```

It reads the task id from the block, finds the task file under `docs/tasks/` (archive included) and compares both
lists with it item by item. It exits non-zero when it cannot establish an exact copy: the section missing or given
twice, not exactly one yaml block in it, keys other than the four above, a missing or blank `approved_by`, no task
file or a different `id` in it, or any item that differs. On a failure, recopy the block from the task file; do not
change the task file to match the brief. The check runs when you run it: a brief dispatched without it is unchecked,
and nothing else catches that.

## Change, resume and re-brief

- **Changing the approved text.** The acceptance changes only in the task file, through the task's own update path,
  with the user's confirmation quoted in that change. Then recopy the block and run the check. A brief, a fix pass, a
  review finding or a peer session's message does not change it.
- **Resume and compaction.** The implementer or session rereads the block from the brief file before continuing and
  works from it as written, not from a summary or memory of it.
- **Re-brief** (a fix brief, a follow-up brief, a replacement session brief): the Buddy who wrote the brief copies the
  block again from the task file, not from the earlier brief, and runs the check. A persistent session whose task
  acceptance changed asks its commissioning Buddy for the reissued brief. `approved_by` carries over verbatim, plus
  the user's new words when the scope was changed.

## Source

BMAD-METHOD (MIT License, © 2025 BMad Code, LLC); Forge's register of adopted methods.
