# Protocol: Instruction form

Read it before writing or changing a rule in standing instruction text, the text later sessions load (framework
rules, skills, protocols, runbooks, personas, adapters). It applies to the author. It decides which form a rule takes
from the failure the rule must prevent, and when a change must first reproduce that failure. The consumer is the agent
that later reads the rule; the cost it prevents is a rule that fixes one failure and causes another. A brief written
for one dispatch follows `skills/_protocols/dispatch-template.md` and `skills/_protocols/fix-brief-template.md`
instead.

## What keeps its form

- A fact update (a path, a name, a count) or a split of a unit at a step boundary keeps the form of the text it
  corrects or moves.
- Sections a Forge template requires keep their required form: a skill's Red Flags and Common Rationalizations
  (`framework/skill-anatomy.md`), a persona's anti-rationalization list (`agents/_protocols/reviewer-base.md`).
- Existing wording the change does not target stays as it is.

Everything else a change writes takes its form from the sections below.

## Classify the failure, then pick the form

Name the failure in one sentence: what the agent did, what it should have done. Then ask first: **does the current
instruction text, read literally in this case, prescribe the right action?** "The text" is the instruction text, not
the user's request.
- **No:** the text is a cause, and the type is one of the last three rows.
- **Yes, and the agent did otherwise:** rule-skipping.

| The agent … | Failure type | Form | Wrong form |
|---|---|---|---|
| had text that prescribes the right action and did otherwise | rule-skipping | A prohibition, plus each excuse a reproduction shows, with its answer | Advice ("prefer", "consider") |
| follows the text, but its output has the wrong parts, size or order | wrong output shape | A recipe: the output's parts in order, and its count | A list of things not to produce |
| produces the right thing without a part it needs | missing element | A required slot or field in the template or record the author already fills | A reminder in prose next to the template |
| acts the same way in cases that need different actions | conditional behaviour | A condition keyed to something the agent can check at that moment, with the check named ("when a newer dump passed a restore check, …") | One unconditional rule, in either direction, plus exemption clauses |

A new rule with no observed failure takes the form of the failure it would prevent, and adds no slot or excuse list
for a failure nobody has seen.

## Rules for every form

- **No nuance clauses.** A qualifier such as "unless it matters", "where appropriate" or "that may have value" hands
  the decision back to the reader's judgement, under the same pull that produced the failure. Upstream wording tests
  saw one such clause turn a consistent recipe noisy. Write a real exception as its own condition on a checkable
  predicate. A predicate that needs judgement ("verified" with no named check) or that is true in every case is a
  nuance clause in another form. A stated purpose next to a rule is not a nuance clause; an exception that depends on
  the reader's reading of that purpose is.
- **Exemption clauses do not scope.** A rule followed by "this does not apply to X" still pushes behaviour in X: the
  reader carries the rule's direction into the exempt case. When the exempt set is defined as "every other case", an
  item that fits both falls to the rule. Restructure so the rule cannot reach X: test the exception first as its own
  condition, or narrow the rule's own subject.

## Persuasion wording

Wording that states a required step, part or condition is the recipe form, whatever its case or mood: "Run the check
before the commit", "Coverage matrix (MUST output)". Persuasion wording is wording added to raise pressure on a rule
already stated: emphasis, "no exceptions", "always" where the rule leaves the case to the reader, excuse lists,
loophole lists, red-flag lists, "the letter is the spirit".

Persuasion wording raises compliance and also over-application: the reader applies the rule beyond its case. On a
conditional failure it pushes one branch harder; on a shape failure it invites negotiation. Use it only where a Forge
reproduction (below) shows rule-skipping.

## Reproduce before rewriting

This step applies when a change to standing instruction text is meant to stop a behaviour someone observed.

1. **Scenario.** Write the observed case as a task the reader can act on: the situation, the request and the
   competing pull the live session had (the user's push, time, sunk cost), without the answer or the failure.
2. **Reading of the current text.** A fresh-context reader without tools gets the scenario and the instruction units
   as a session loads them at that step (whole units, not extracted sentences). It says what it would do; for a shape
   failure it produces the output.
   - **The reading shows the failure:** classify it by the table.
   - **The failure sits in a loaded unit outside the change's scope** (a consumer, host or platform rule): record that
     unit as a cause, route it to its owner, and judge the new text with that unit named as the remaining cause.
   - **It does not show the failure:** check what the live session had loaded at the decision moment (a missing read
     trigger, a unit that was not loaded) and fix that (`skills/_protocols/piebald-budget.md` §Loading policy). When
     the current text prescribes the right action and the scenario lacked the live pull, add the pull and read again.
     A wording change still needs a reading that shows the failure.
3. **Write the new text** in the form its row prescribes: the smallest text whose readings pass step 4.
4. **Readings of the new text.** At least two fresh-context readings, with the same scenario and the same loaded
   context. Accept when both act as the rule intends. When they differ from each other, the wording does not bind:
   change the form, not the length. When a review changes what the new text tells the reader to do, the readings run
   again on the final text.
5. **Record** the scenario, each reading verbatim, the classification and the result in the change's record.

Readings count as rounds under `agents/buddy/delegation.md` §Cumulative effort; a gap past the budget is recorded as
a watch item. Two readings catch a failure that shows in most sessions, not a rare one, and a reading shows how the
text is understood, not how a live session behaves under pressure. A later live failure starts this step again.

## Source

Superpowers (MIT License, © 2025 Jesse Vincent); Forge's register of adopted methods.
