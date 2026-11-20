Skeleton: implementer-brief 2

# Implementer brief — task <id>: <goal>

<!-- Copy this file into the work unit's records as the brief. Keep the line above: the brief-acceptance check reads
it; at build signoff the brief opens with the `brief_contract` frontmatter (`---` block, mca-brief-template.md),
and this line follows the frontmatter's closing `---`. Fill every slot; a slot that does not apply keeps its one-line `n/a` or `None.` form with the reason. What each
slot means: skills/_protocols/mca-brief-template.md. A slot change raises the number on line 1 (owner:
approved-acceptance.md §The check). Delete this comment. -->

MODEL: <model> (<role row of framework/models.md>)
Size: goal: <the one user-facing goal, one sentence>; brief <bytes> bytes (`wc -c`), with the files it tells the
implementer to read <bytes>, against a third of the implementer's window (<window> tokens, about 3 bytes each);
past it: split by goal, narrow the files to read, or cut the goal into steps that each end in a commit
Effort budget: <rounds, agent calls and test runs expected for the task's value>; more only if <what would justify it>
Report: <path of the report file> (skills/_protocols/mca-dispatch.md)

## Approved acceptance (read-only)

<Copy the block from the task file (skills/_protocols/approved-acceptance.md), then run
`python3 $FRAMEWORK_DIR/scripts/consistency_check.py --check brief-acceptance --brief <this file>`.>

## Implicit-Decisions-Surfaced

```yaml
implicit_decisions_surfaced:
  schema_and_contract:   {locked: "<status>", value: "<decision>"}
  error_and_stop:        {locked: "<status>", value: "<decision>"}
  layer_discipline:      {locked: "<status>", value: "<decision>"}
  structural_invariants: {locked: "<status>", value: "<decision>"}
  vision_alignment:      {locked: "<status>", value: "<decision>"}
  other: []
```

<Below the template's trigger: replace the block by one sentence why it is not enumerated.>

## Complexity-Tracking

<The table of framework/spec-engineering-implementation-specs.md §Convention: §Complexity-Tracking, or `None.`. An
addition the table does not list is dropped, or reported in the return with a proposed row.>

## Acceptance-Criteria

| Criterion | Obligation | Test |
|---|---|---|
| AC-<n> | <what the implementer does for it> | <test name, or the command that shows it> |

## Tests

<!-- The tests the implementer writes: these and no others (skills/_protocols/mca-brief-template-verification.md
§Tests the brief orders). -->
- <test name> — <the behaviour it covers> — relied on by <whom>; cases: <the cases that change an assertion>
- Unchanged: <behaviour> — guarded by <existing test> | unguarded
- Run: the selected set (`python3 $FRAMEWORK_DIR/scripts/select_tests.py <changed paths>`), not the whole suite
- Commit trailer: a commit touching a path in `.forge-product-paths` carries `Route: <brief|engine> <this brief's path
  or the workflow id>, tests: <number of tests run>`; the commit-msg hook refuses it without one

## Stop limit

```yaml
stop_limit: {product_paths: [<glob>], product_lines: <N>}
```

## Scope

- Fit: <cite the applicable project goal and constraints and the original local objective. Explain how the
  proposed scope serves both. Resolve missing or conflicting intent before dispatch (owner: framework/invariants.md §Intent-driven).>
- Implementer: apply this fit before a substantive implementation choice. Hold the dependent choice on unresolved intent
  and report it to the commissioner (owner: framework/invariants.md §Intent-driven).
- Files: <the files and sections to change>
- Not to touch: <adjacent files, fields or symbols where the same pattern would apply>
