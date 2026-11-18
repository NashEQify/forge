# Protocol: Reviewer checked scope

Required section for reviewer and council artifacts. It shows the reader what the review checked and why its result
holds: the artifact's purpose, the paths checked with their results, the author's assumption with the check that
tested it, and the consequence of the strongest finding. It records checks and their evidence, not the reviewer's
inner deliberation.

Loaded by every reviewer and council persona that names it, and by the role that checks the artifacts:

- **Spec Board:** `board-chief` checks `board-adversary`, `board-adversary-2`, `board-implementer`, `board-impact`;
  also `board-architect-roots`, `code-architect-roots`, `solution-expert`.
- **Code Board:** `code-chief` checks every raw reviewer when a Chief consolidates; with three or fewer reviewers Buddy
  checks at triage (`agents/_protocols/code-reviewer-base-extended.md` §Checked-scope convention).
- **UX Board:** `board-ux-heuristic` (primus) carries it and checks itself; its consolidation gives the checked scope
  for the UX verdict.
- **Architectural Council:** `council-chief` checks `council-member` and `council-adversary`.

**Exceptions:** `board-consumer` does not load this protocol; its first-reader role reports what a reader meets,
without a structured check record. `board-ux-ia` and `board-ux-interaction` do not load it either; they are focused
sub-reviewers under the UX primus.

## Section

The section is named **`## Checked scope`**, placed before the findings. It has four fields, in this order:

```
## Checked scope

- **Purpose:** {what the artifact must enable, one sentence in your own words}
- **Paths checked:** {each focus area or concrete scenario you checked, in the order checked: input -> expected ->
  what the artifact does, with its result and a file:line or command}
- **Assumption tested:** {the author's central assumption; the check that would refute it; what the check showed,
  with file:line; the class of problem it belongs to, with a second instance beyond this artifact}
- **Consequence:** {the concrete consequence of the strongest finding for a named component or person; with no
  finding, what the checked paths establish and what remains unverified}
```

## Per finding

Each finding carries, besides the board's own fields (severity, evidence pointer, suggested fix):

- **checked path:** the scenario, input or reading that led to it;
- **evidence:** file:line with the quoted text, or the reproduction command and its output;
- **conclusion:** what follows from the evidence, and its consequence if unfixed.

## Bind rule (checked scope ↔ findings)

When findings exist, at least one refers to a path checked or to the assumption tested. When none exist, the
Consequence field names the checked paths, their evidence and the limits that support that result. Apply this
separately to each reviewed axis. Zero findings is a valid result; never invent a finding to satisfy the bind.

The checking role (Chief, primus, or Buddy at triage) verifies the section and this substantive connection. A keyword
match alone does not establish it; zero findings alone does not violate it. Missing section or connection → finding
`F-{C|UX|CC}-SCOPE-MISSING` and one re-dispatch of the same reviewer with a hint (context-isolated, append only, no
full re-review); missing again → ESCALATE.
A seat that ended in an abort, and the substitute that replaced it, are handled by
`skills/_protocols/dispatch-template.md` §Aborted seat; the substitute is checked against its own output format.

## What each field guards

| Field | Guards against |
|---|---|
| Purpose | a review that never understood what the artifact is for |
| Paths checked | a review at random, or one that never tested the artifact against a concrete case |
| Assumption tested | an unexamined assumption: the bias layer the author could not see |
| Consequence | severity without a grounded consequence |

## Trigger

Every reviewer and council artifact, every pass. Not for bookkeeping or mechanical consolidation without a content
judgment.

## Anti-patterns

- **NOT:** the artifact's title copied as Purpose. **INSTEAD:** your own words.
- **NOT:** "I looked at everything" as Paths checked. **INSTEAD:** the concrete areas and scenarios, each with its
  result.
- **NOT:** a hypothetical scenario without concrete input. **INSTEAD:** "when agent X gets prompt Y, the artifact makes
  it do Z (file:line)".
- **NOT:** a class that rephrases the problem. **INSTEAD:** a class with a second, nameable instance.
- **NOT:** "could cause problems" as Consequence. **INSTEAD:** the concrete downstream break and who is affected.
- **NOT:** a narrative of how you thought about the artifact. **INSTEAD:** what you checked, what it showed, and where.
