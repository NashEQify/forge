Skeleton: fix-brief 2

# Fix brief — task <id>, fix pass <n>

<!-- Copy this file into the work unit's records as the fix brief. Keep the line above: the brief-acceptance check
reads it. Fill every slot; a slot that does not apply keeps its one-line `n/a` or `[]` form with the reason. What each
slot means: skills/_protocols/fix-brief-template.md. A slot change raises the number on line 1 (owner:
approved-acceptance.md §The check). Delete this comment. -->

MODEL: <model> (<role row of framework/models.md>)
Verdict: <path of the verdict file>
Report: <path of the implementer's report file>, one result per finding (skills/_protocols/mca-dispatch.md)

## Workflow scope

<Inside a workflow step where `workflow_engine.py --next` prints a `NOT-YOURS:` line: paste its `SCOPE:` and
`NOT-YOURS:` block here verbatim. Otherwise delete this section.>

## Approved acceptance (read-only)

<Copy the block from the task file, not from an earlier brief (skills/_protocols/approved-acceptance.md), then run
`python3 $FRAMEWORK_DIR/scripts/consistency_check.py --check brief-acceptance --brief <this file>`. Work on no task:
delete this section.>

## Round

```yaml
round: "<n> of <the rounds in the task's effort budget>"
machinery: "<none | the findings concern machinery this solution added: <what>; kept because <the outcome it serves> | removed>"
choice: "<another pass, within the budget | close: <the limit recorded> | narrow: <what leaves> | escalate: <to whom, with cost and risk>>"  # never close: a review floor, a regression this change caused, a blocking defect in retained or acceptance-required behaviour, a blocking live mechanism cell
tasks: "<none | <finding id>: <what breaks if it is not done, for whom>>"  # never solely because a finding exists
```

## Section 1: phrase check

```yaml
phrase_check:
  universal_quantifiers: "<absent | present-justified: <quote+rationale>>"
  hedges:                "<absent | present-justified: <quote+rationale>>"
  optionalities:         "<absent | present-justified: <quote+rationale>>"
  paraphrase_vs_quote:   "<reviewer-quoted | paraphrase-justified: <rationale>>"
```

## Section 2: scope bound

- Fit: <cite the governing project intent and original repair objective and explain how the remedy serves both,
  or point to the current decision that does so. Hold dispatch on unresolved intent (owner: framework/invariants.md §Intent-driven).>
- Implementer: recheck fit before a substantive alternative. Hold the dependent change and report unresolved intent
  in the existing report or finding response (owner: framework/invariants.md §Intent-driven).

```yaml
scope_bound:
  files:         ["<file:section>", "<file:lines-X-Y>"]
  stop_limit:    {product_paths: [<glob>], product_lines: <N>}
  loc_rationale: "<why N, from which findings>"
```

## Section 3: out of scope

```yaml
out_of_scope:   # or: out_of_scope: []  # no adjacent bleed-risk identified
  - location:  "<file:section>"
    why_close: "<why it is near the scope>"
    do_not:    "<what not to do there>"
```

## Section 4: mechanism cells

```yaml
mechanism_cells: n/a  # no state carrier touched; otherwise the block of the template's Section 4
```

## Section 5: causes

```yaml
causes:
  - id: <finding id>
    cause: <wrong-finding | intent | spec | mechanism | stuck | code>
    check: "<the check that holds, quoted; a ruling by its RL id>"
    answer: "<rule | ask <caller> | amend <§> → re-derive <unit> or patch | invariant or replacement | fresh implementer <model> | patch | accept-limit>"
    test: "<covered: <existing test> | reproduction: <test> | command: <command>>"
removes: []   # or ["<test> — covered by <test>"]
spec_gaps: report under Concerns each outcome this pass decides that no spec item states
```

## Findings

- <finding id> — `<file:line>` — "<the reviewer's words, quoted>"
