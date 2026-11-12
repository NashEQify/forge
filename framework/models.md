# Model Assignment

Read it before any agent call and before commissioning a persistent session: it decides which model the call or
session runs on and where it is named. The consumer is
the agent that dispatches. The cost it prevents: no Claude Code or Codex agent definition sets a model, so a call
without one runs on the session's model whatever the role needs, and the same role runs on different tiers from
session to session.

## Naming the model

Every agent call names its model:
- in the call's model parameter, as the host cases below set;
- where the dispatch is saved as a file (`skills/_protocols/mca-dispatch.md`), also in its line
  `MODEL: <model> (<role row>)`;
- on a board seat, also in the pre-dispatch check line (`skills/_protocols/dispatch-template.md`).

A call without a named model is a brief defect; name it before the call. A tier above the row's is named with its
reason: in the `MODEL` line as `MODEL: <model> (<role row>; <reason>)`, otherwise in the dispatch's model rationale.
A tier below the row's is not taken.

Hosts differ in the parameter:
- **The call takes no model parameter:** the `MODEL` line names the model the delegate runs on, and the call
  proceeds.
- **The tool asks to omit the parameter unless an override is needed** (Codex `spawn_agent`): pass it when the row's
  model differs from the session's; when they match, the `MODEL` line, the check line or the dispatch's model rationale still
  names it.

## Defaults per dispatch role

Each check is made at the dispatch, from the brief, the review package or the selected review level. A Spec Board
seat takes the model its depth table sets (`skills/spec_board/REFERENCE.md` §Model override). Every other call takes
its role's row below; when two rows fit, take the higher tier.

| Role | Check at the dispatch | Tier |
|---|---|---|
| Mechanical implementation | The brief holds the code to write, or the fix is in one file at the lines the brief names | cheapest |
| Integration | Implementation or a fix from a prose brief that the next row does not take; a debugging dispatch | standard |
| Structural or safety-floor implementation | The brief meets the brief-time lens threshold (≥3 touched modules, a new subsystem, or effort L or XL; `agents/code-architect-lens.md`), or it touches a safety floor (`skills/code_review_board/SKILL.md` §1.0) | most capable |
| Review by diff size and risk | The package covers one task's range inside a larger change, or a fix range (a re-review, also when its verdict closes the change); a finding verification (`skills/_protocols/finding-verification.md`), whatever range its package covers | standard; most capable when the package's stat (`skills/code_review_board/review-package.md`) shows more than 300 changed lines or the selected review level names a safety floor (§1.0) |
| Final review | A review seat's package covers the change's whole range (for a single task, its first review), and every seat of an L2 board | most capable |
| Design | A Council member, adversary or Chief; solution-expert, brief-architect, code-architect-lens; a plan review; the adversary test plan; the security agent | most capable |
| Reading | A fresh-context reading of instruction text (`skills/_protocols/instruction-form.md` §Reproduce before rewriting) | standard |
| Any other role | — | standard |

The 300-line threshold's intent: a diff past it no longer fits one careful read, so a weaker reader misses more.
Inside a fix loop, a fix pass whose cause is a stuck implementer runs one tier above the row of the stuck
implementer's brief, with that reason in its `MODEL` line (`skills/convergence_loop/cause-before-answer.md`). Every
other fix pass takes the row of its own brief. A resumed implementer keeps its model: it takes the pass when that
model is at or above the row, with `resumed` as the reason; otherwise a new dispatch on the row's tier does
(`skills/_protocols/mca-dispatch.md` §A fix pass's implementer). A persistent session below the most capable tier
is stuck when its return reports a finding or check it fixed that came back, or one it could not fix. It runs no
further round on that tier: the coordinator moves its work one tier up, to a new session briefed from its return and
records, with the line `MODEL: <model> (session; stuck: <evidence>)` (§A persistent session's model).

## A persistent session's model

Read it before commissioning a persistent session (`agents/buddy/coordinating-sessions.md`). A session is not one
dispatch role: besides its task it writes briefs, adopts reviews and returns, and closes its item, and a miss at those
points costs a round. Its tier is the highest row of §Defaults per dispatch role that matches work the session carries
inline, not through an agent call; writing standing instruction text or a spec, and choosing between design options,
count as the Design row. The floor is the standard tier (§Why turns decide). The session's own agent calls keep taking
their rows, whatever the session runs on. A coordinator on the most capable tier names the standard tier for a session
whose inline work is implementation from a prose brief, integration or mechanical steps, with every design choice
settled in the brief or given to an agent call on its own row. A tier below what the session's inline work needs is
not taken.

The brief names the model in its line `MODEL: <model> (session; <the most demanding inline work>)`, and the start call
passes it where the host's call takes a model; where it does not, the coordinator asks the user to start the session
on that model, and without that start does the work as on a host without sessions (`agents/buddy/delegation.md`
§Vehicle choice). A host whose start call caps the model at the starting chat's
(`architecture-documentation/07-tool-integrations.md` §Delegation vehicles) cannot start a session above the
coordinator's tier: the coordinator asks the user to start it on the named model, or does the work as on a host
without sessions; it never starts it on a lower tier.

## Why turns decide

Count the cost in turns, wall time and usage against the plan's limits, not in token price. A weaker model that
takes more turns, or misses what a later round then has to find, costs more of all three than its lower price per
token saves. Hence:
- the standard tier is the floor for reviews and for implementation from prose;
- the cheapest tier takes only transcription plus tests: the code is already written in the brief, or the fix is
  located to its lines;
- the most capable tier goes where a miss costs a round: structure, safety floors, design and the final review.

## Tiers per host

| Tier | Claude Code (`model` parameter) | Codex (`spawn_agent` `model`) | OpenCode |
|---|---|---|---|
| cheapest | `haiku` | `gpt-6-luna` | — |
| standard | `sonnet` | `gpt-6.1-sol` | `anthropic/claude-sonnet-4-6` |
| most capable | `opus` | `gpt-6-astra` | `anthropic/claude-opus-4-6` |

The Codex column follows the host's own model list in the `spawn_agent` tool ("fast and affordable", "workhorse",
"frontier intelligence for the most demanding work"); check it there on a model switch. Claude Code agent
definitions (`agents/<n>.md`, the roles the plugin lists) set no model; the call names it, also for a role run as a
general agent (`skills/_protocols/role-dispatch.md`). On OpenCode roles run as general agents in the session's model.

## Model switch

Update the tier table by hand; for Codex, read the `spawn_agent` model list.

## Example: a runtime model router (one consumer's setup)

This records one consumer project's choice, not a Forge default. That project
runs a local model (Ollama) as primary and a cloud API as fallback, behind a
LiteLLM container in its own docker-compose file, with routing in
`config/litellm_config.yaml`.

With such a router in place, the OpenCode agent files can name router aliases instead of
provider strings. Claude Code is unaffected; it talks to its provider directly.

## Source

Superpowers (MIT License, © 2025 Jesse Vincent); Forge's register of adopted methods.
