# 01 — Overview

Forge is a shared set of agent instructions, skills and supporting tools. It helps
you keep useful knowledge, reason about uncertain choices, and carry selected
software work through to verified results in your existing agent application.

You work through **Buddy**, the conversational entry. Describe the goal in ordinary
language. Your workspace's intent and rules determine the relevant context, working
style and limits on action.

## Three capabilities

| Capability | Result | Typical request |
|---|---|---|
| Knowledge and continuity | Current knowledge, usable routes to detail, and a handoff for open work | “Continue this application from the latest draft.” |
| General reasoning | A clearer problem, examined assumptions or a comparison of viable choices | “Use a Council to compare these approaches.” |
| Software development | Specifications, implementation, tests, review and tracked continuation | “Build this feature and verify the behavior.” |

Knowledge supports both reasoning and development. Reasoning can improve a
software decision. Each capability can also be used at its own scope: supplied
context is sufficient for a standalone method, and project knowledge needs no
software task system.

The [capability contract](../framework/capabilities.md) defines their ownership.

## Knowledge and continuity

Useful facts and corrections are reconciled during work under the applicable
maintenance authority. The agent reads relevant context before dependent answers,
keeps claims at a responsible owner and updates routes when leading material changes.

Personal preferences belong in the configured user scope. An activity, application
or technical setup belongs with its project or topic owner. A short profile provides
boot context; topic navigation leads to details when needed. There is no required
life-domain taxonomy or automatic transcript archive.

`save` reconciles knowledge and the session handoff. It preserves open topics,
next steps, blockers and necessary approvals. An explicit `save` also requests
commit and push to the active project's tracked upstream unless its rules restrict
that action. Ordinary continuous maintenance alone does not authorize publication.
See the [daily handbook](13-operational-handbook.md) for the practical sequence.

Continuity is file-based. The agent needs access and must read the right files;
Forge does not provide automatic access to previous chats or a hosted memory service.
Protected publication checks the baseline before replacing files and retains
recovery information for interrupted changes across multiple files. Its locks
coordinate cooperating writers, not every external editor.

## General reasoning

Three methods address different needs:

- **Frame** clarifies the problem and opens a meaningful solution space before
  recommending an approach.
- **Bedrock** examines assumptions down to logic, physical constraints and chosen
  values, then traces their implications.
- **Council** compares a choice from distinct perspectives, preserving disagreement
  and uncertainty for a better-informed decision.

A method can return a useful report directly in the conversation. It does not need
Git, a user repository, a software workflow or an automatically created task.
Persistence is separate and follows the caller's authorization. A recommendation
is still a proposal until the relevant decision is made.

See [method selection and examples](06-usage-workflows.md#general-reasoning).

## Software development

For software work, Forge composes these capabilities with specifications, coding,
tests, independent review and task/workflow tracking. It can support feature builds,
defect investigation, research and specification review across sessions.

Effort follows risk and uncertainty. A bounded reversible change can take a short
path; consequential contracts, security, migrations and live systems retain their
safeguards. The [process map](../framework/process-map.md) defines selection and
eligibility, rather than a fixed process for every request.

Explicitly selected development state can contribute to common save and resume.
Loading a session checks its exact state; it does not silently advance work or
unpause a workflow. See [development usage](06-usage-workflows.md#software-development).

## What's in the box

Forge ships one distribution with composable installation presets. `daily` provides
knowledge maintenance, save, housekeeping and Bedrock without software tooling;
Council and Frame are optional additions. `full` makes development tooling and the
general methods available. Availability does not select a software workflow.

The installer coordinates supported host integrations. Actual capabilities and
instruction loading differ by host; Cursor's rules-based integration is distinct.
Use [installation](05-installation.md) and [host support](07-tool-integrations.md)
to choose and verify your setup.

## Who is it for?

Forge suits recurring work where earlier facts, decisions and unfinished steps
matter: everyday projects, difficult choices, and software delivery. It is also
useful to maintainers who want shared methods across workspaces while keeping each
workspace's own content, vocabulary and operational approvals.

The trade-off is discipline and overhead. A small context update is inexpensive
compared with a multi-agent Council or review board. More perspectives can expose
errors, but shared assumptions can survive review. File checks and Git hooks verify
specific properties; they cannot guarantee model judgment or universal compliance.

## Next reading

[Daily handbook](13-operational-handbook.md) · [Usage and methods](06-usage-workflows.md) ·
[Installation](05-installation.md) · [Architecture](02-architecture.md) · [Documentation hub](README.md)
