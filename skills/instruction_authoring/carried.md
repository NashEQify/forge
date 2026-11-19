# instruction-authoring — carried from the owners

Lookup unit of `skills/instruction_authoring/SKILL.md`. The acts stand in SKILL.md's Process; this unit carries what
an author in a project without Forge's units would otherwise have to find in them: the carrier letters in that
project's terms, the findings with their counts and limits, and the owners' detail behind three steps. It holds no
rule and no finding of its own; each section names its owner, and an owner's change changes the section with it.

## The carrier letters in a project without Forge

Owner: `skills/_protocols/instruction-form.md` §Which text the actor has at the moment. The letters and their order
are the owner's; the right column names the text that plays the part in a plain project on Claude Code or Codex.

| Letter | Owner's carrier | In a project without Forge |
|---|---|---|
| (a) | a check that refuses on a fact it can compute | a pre-commit hook, a CI job or a script step whose non-zero exit stops the act |
| (b) | a text in front of the actor without anyone writing it at the moment: the engine's step text, the role file as the host loads it, the host's start text | the body of the skill the host delivers on the call; a sub-agent's definition file, which the host gives that agent as its prompt; text a start hook injects |
| (c) | a fixed form the actor repeats from its own previous output | a closing line or output section the skill makes the agent produce every time |
| (d) | an element of the artifact being written | a required heading or field in the template the agent fills |
| (e) | the brief or dispatch that commissions the work | the prompt an agent or a person writes to start a sub-agent or a task |
| (f) | a sentence of the standing block in the start text | a sentence in the project rules file (`CLAUDE.md`, `AGENTS.md`) the host loads at start |
| (g) | a check that prints | a script or hook that prints a reminder and lets the act go on |

## Findings

Owner: `references/agent-reading-findings.md`. Its common limits apply to every line: **measured** 2026-11-14 over the
transcripts of one machine from 2026-10-31 on, Claude Code sessions in a checkout and their sub-agents; **models**
mostly two Claude models, which the data cannot separate from session role (E12); **not measured:** Codex,
plugin-copy sessions, other machines. They are observations of that setup, not general laws; a repeat after a model
change or a host release that changes hooks, compaction or skill loading updates them. Fourteen entries:

- **E1** A "read X when Y" paragraph loaded at start rarely produces the read at its moment: 12 of 207 moments with
  no other text naming the unit.
- **E2** A rule sentence loaded at start does not reliably produce its act later when nothing else names the act; in
  one session it fell with age (4 of 4, then 2 of 99) until the host re-delivered it. Standing prohibitions held at
  97 to 100%, with no control group.
- **E3** Text that arrives with the work is read: units named in a dispatch in 562 of 686 call-unit pairs.
- **E4** A named path is still a hop: a path the workflow engine printed was read afterwards in 0 of 7 and 6 of 17
  session-path pairs.
- **E5** A required element gets filled when the author's own earlier artifact of the kind is in context (23 of 23
  briefs carried the block); it is lost at compaction.
- **E6** A rule stated in context is planned for in a single reading (8 of 8; 0 of 4 with no rule); a pointer was not
  followed in 0 of 29 live cases without another cue.
- **E7** After compaction, what the host delivers is back (16 of 16); what the agent was asked to reread mostly is not.
- **E8** Limits stand where they are not read, duties where they are: one fix loop ran 17 full test runs under a step
  text that had the duties and not the limits.
- **E9** Read is not applied; form decides: an unconditional text gave a wrong verdict in 2 of 2 readings, a condition
  list with a named output section the right one in 4 of 4.
- **E10** An agent's own previous output predicts its next: a closing line in 221 of 237 turns after a turn that had
  it, 16 of 1,258 after one that had not.
- **E11** The room is not where it was assumed: explanation, history and delimitation are 7.7% of the measured text,
  while 31% of the start-loaded set serves a later moment.
- **E12** Model and session role outweigh every form factor in the data and cannot be separated in it.
- **E13** On Claude Code, each start handler has its own budget: about 9,500 characters arrived whole; about 11,600
  went to a file with a preview the model did not open.
- **E14** On Claude Code, host events that are not tool calls (an incoming message, a sub-agent's start, a turn end)
  deliver their text before the model acts.

## Detail behind the steps

Owner: `skills/_protocols/instruction-form.md`, the sections named.

- **Step 2, the failure** (§Classify the failure, then pick the form). "The text" in the question is the instruction
  text, not the user's request.
- **Step 5, rules for every form** (§Rules for every form). A predicate that needs judgement ("verified" with no named
  check) or that is true in every case is a nuance clause in another form. A stated purpose next to a rule is not a
  nuance clause; an exception that depends on the reader's reading of that purpose is. When an exempt set is defined
  as "every other case", an item that fits both falls to the rule.
- **Step 6, the writing rule** (§Writing rule). Form follows what an agent reads best, not what a person reads. Over
  the cap: cut by the writing rule first, then split at a step boundary and give the moved part a carrier at that
  step. The cap bounds one read; it does not prove that a batch of reads arrived whole.
- **Step 7, reproduce before rewriting** (§Reproduce before rewriting).
  - The scenario carries the competing pull the live session had (the user's push, time, sunk cost), not the answer.
  - When the reading shows the failure in a loaded unit outside the change's scope (a host or platform rule), record
    that unit as a cause, route it to its owner, and judge the new text with that unit named as the remaining cause.
  - When it does not show the failure, check what the live session had loaded at the decision moment and place it;
    when the current text prescribes the right action and the scenario lacked the live pull, add the pull and read
    again.
  - When a review changes what the new text tells the reader to do, the readings run again on the final text.
  - Two readings catch a failure that shows in most sessions, not a rare one; a later live failure starts the step
    again.
- **Step 8, the read-path record** (§Read-path record). The review of such a change checks the record against the text
  the named reader has at the named moment. When the changed sentence is not in that text, the record says `on-demand`
  or the change moves the sentence to a carrier.

## Source

The rule set this skill carries adapts Superpowers (MIT License, © 2025 Jesse Vincent); Forge's register of adopted
methods.
