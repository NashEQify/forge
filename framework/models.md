# Model Assignment

Read it before any agent call: it decides which model the call runs on and where the call names it. The consumer is
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
(`skills/_protocols/mca-dispatch.md` §A fix pass's implementer).

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
definitions (`agents/<n>.md`, read through `~/.claude/agents`) set no model, and neither do the Codex role copies
(`~/.codex/agents/*.toml`); the call names it. OpenCode sets the model in each agent file
(`orchestrators/opencode/.opencode/agent/<n>.md`): `tester` on the standard tier, `buddy`, `buddy-thinking`,
`solution-expert` and `main-code-agent` on the most capable.

## Model switch

Update the tier table and the OpenCode agent files by hand; for Codex, read the `spawn_agent` model list.

## Example: a runtime model router (one consumer's setup)

This records one consumer project's choice, not a Forge default. That project
runs a local model (Ollama) as primary and a cloud API as fallback, behind a
LiteLLM container in its own docker-compose file, with routing in
`config/litellm_config.yaml`.

With such a router in place, the OpenCode agent files can name router aliases instead of
provider strings. Claude Code is unaffected; it talks to its provider directly.

## Source

Superpowers (MIT License, © 2025 Jesse Vincent); Forge's register of adopted methods.
