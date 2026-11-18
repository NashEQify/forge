# Protocol: Instruction form

Read it before writing or changing a rule in standing instruction text, the text later sessions load (framework
rules, skills, protocols, runbooks, personas, adapters). It applies to the author. It decides where a rule must stand
to reach its actor, which form it takes from the failure it must prevent, what a unit may hold, when a change must
first reproduce that failure, and what the commit records. The consumer is the agent
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

## Which text the actor has at the moment

Before writing or moving a rule, name its actor, the moment it acts and the text that actor has in front of it then.
Give the rule every carrier that reaches that text, strongest first (`references/agent-reading-findings.md` E1 to E10):
(a) a check that refuses on a fact it can compute; (b) a text in front of the actor without anyone writing it at the
moment: the engine's step text, the role file as the host loads it, the host's start text; (c) a fixed form the actor
repeats from its own previous output; (d) an element of the artifact being written; (e) the brief or dispatch that
commissions the work; (f) a sentence of the standing block in the start text; (g) a check that prints. A "read X when
Y" paragraph in a unit loaded at start is not a carrier, and a named path is a hop that loses readers (E1, E4). A rule
no carrier reaches stays in its unit for lookup, with no claim that it is read.

Where the actor reads it, the rule stands as one statement: the act, its limit and its purpose, then the marker
`(owner: <path> §<section>)`. The owner unit keeps the rule's full text; a duty and its limit stand in one statement
(E8). When the owner changes, the statements that carry its marker change with it.

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

## Writing rule

A unit holds what its agent needs for the unit's immediate purpose. History, delimitation (what the unit is not, what
another owner holds, a rule restated in negative form) and explanation beyond the purpose leave; form follows what an
agent reads best, not what a person reads; each rule keeps its purpose in one phrase. Before cutting a sentence, ask:
does deleting it change what an actor does at a moment? Then it is a rule and stays, also when it is negative ("no
task solely because a finding exists"). A sentence that sends the reader on to the unit that does apply ("not for X:
use Y", in a skill description or a unit's head) routes, and stays. A unit read whole stays within its byte cap
(`python3 scripts/consistency_check.py --check instruction-units`); over it, cut by this rule first, then split at a
step boundary and give the moved part a carrier at that step (§Which text the actor has at the moment). The cap
bounds one read; it does not prove that a batch of reads arrived whole (`framework/work-principle.md`).

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
     trigger, a unit that was not loaded) and place it (§Which text the actor has at the moment). When
     the current text prescribes the right action and the scenario lacked the live pull, add the pull and read again.
     A wording change still needs a reading that shows the failure.
3. **Write the new text**, after stating what it must deliver, in the form its row prescribes: the smallest text whose readings pass step 4.
4. **Readings of the new text.** At least two fresh-context readings, with the same scenario and the same loaded
   context. Accept when both act as the rule intends. When they differ from each other, the wording does not bind:
   change the form, not the length. When a review changes what the new text tells the reader to do, the readings run
   again on the final text.
5. **Record** the scenario, each reading verbatim, the classification and the result in the change's record.

Readings count as rounds under `agents/buddy/delegation.md` §Cumulative effort; a gap past the budget is recorded as
a watch item. Two readings catch a failure that shows in most sessions, not a rare one, and a reading shows how the
text is understood, not how a live session behaves under pressure. A later live failure starts this step again.

## Read-path record

A commit in the framework repository that changes standing instruction text (under `agents/`, `framework/`,
`skills/`, `workflows/`, `orchestrators/*/rules/`, or `CLAUDE.md`, `AGENTS.md`) carries in its message, for each
rule it changes, four lines:

```
Read-path-reader: <who acts on the changed sentence>
Read-path-moment: <the decision at which it acts>
Read-path-text: <what that reader has in front of it then, and how it got there>
Read-path-carrier: <the letter of §Which text the actor has at the moment, or on-demand>
```

Write them by walking the reader's path from its session start or dispatch to that moment, text by text. When the
changed sentence is not in the text the reader has then, the record says `on-demand` or the change moves the sentence
to a carrier. The commit-message hook refuses such a commit without the four lines (a merge commit excepted); it checks
that they are there, not that they are true. The review of such a change checks the record against the text the named
reader has at the named moment, and its dispatch says so. Purpose: a rule its actor does not have at the decision does
nothing, and the author is the one who can see that before the commit.

## Source

Superpowers (MIT License, © 2025 Jesse Vincent); Forge's register of adopted methods.
