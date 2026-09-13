# Protocol: Instruction Budget

Keep the instructions loaded for a task useful and coherent. Applied when
authoring or reviewing skills, runbooks, personas and assembled prompts.
The consumer is the executing agent; the cost is irrelevant context,
duplicated authority, or missing guidance at the point it is needed.

## Loading policy

Keep purpose, essential constraints and routing in the entrypoint. Put
substantial mode-specific procedures, schemas and examples in references
when they are useful only for that mode. A short self-contained skill
does not need a split. Do not fold references back merely because they
are not automatically loaded.

Every required reference needs a discoverable path and a concrete read
trigger at its point of use. Verify that the selected workflow actually
loads the guidance before the dependent action. A link without a trigger
is insufficient for required behavior. Keep safety/authorization constraints
needed to choose the action visible before entering conditional detail.

Remove duplication or obsolete instructions before adding routing layers.
Do not compress unique requirements into opaque shorthand or distribute
one rule across files that must always be read together just to reduce
the entrypoint's line count.

## Review signals

Measure changed instruction files and, where available, the content actually
loaded for a representative task. Record line/byte counts as size measures;
they are not measured tokens, attention limits, or proof of behavioral gain.

The following are inspection prompts, not targets or pass/fail thresholds:

| Artifact | Inspect more closely when |
|---|---|
| Skill entrypoint | over 400 lines, or common tasks load unused mode detail |
| Workflow narrative | over 200 lines, or duplicates runtime step instructions |
| Standard persona | over 100 lines, or repeats shared protocols |
| Chief / consolidator persona | over 400 lines, or mixes discovery and consolidation |
| Skill / agent protocol | over 150 / 80 lines, or has multiple authorities for one rule |
| Assembled prompt | over 500 lines, or combines irrelevant roles/modes |

These inherited size signals are heuristics, not validated optimal budgets.
A shorter artifact can still be confusing or omit a required load trigger;
a longer cohesive artifact can be justified. Review only the relevant
scope, not an unrelated corpus sweep triggered by one large file.

## Finding and disposition

Ground a finding in a concrete problem: conflicting instructions, repeated
content loaded without benefit, a missing required read, or an unclear
decision path. Name the affected task/consumer and consequence. Severity
and disposition follow that consequence and the ordinary review criteria.
Line count alone never creates a HIGH finding, blocks PASS, or requires
an exception approval.

Choose the smallest useful correction: remove duplication, clarify the
read trigger, move conditional detail, or retain the current structure
with a short rationale. Check that required guidance remains reachable
after a split. Do not claim better model behavior from fewer lines alone.

## Author and reviewer check

The author checks changed files and their direct loading references.
The reviewer verifies the consequential loading and coherence claims;
reuse measurements for the same revision. Missing evidence is reported
as an unverified boundary, not converted into a claim that loading works.
Convergence follows substantive findings; there is no separate length gate.
