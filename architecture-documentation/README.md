# Forge documentation

Forge helps you carry useful context across sessions, reason through difficult
questions, and deliver software with appropriate verification. These capabilities
share one conversational entry, **Buddy**, while remaining independently useful.

Start with the outcome you want. You do not need to learn the workflow engine to
maintain knowledge or use a reasoning method.

## Choose a route

| Your goal | Start here | Continue with |
|---|---|---|
| Understand what Forge does | [Overview](01-overview.md) | [Human guide](10-human-guide.md) |
| Use it for recurring everyday work | [Daily handbook](13-operational-handbook.md) | [Knowledge and continuity](06-usage-workflows.md#knowledge-and-continuity) |
| Clarify a problem or compare options | [Reasoning methods](06-usage-workflows.md#general-reasoning) | [Visual guide](workflow-diagrams.md#general-reasoning) |
| Build or maintain software | [Software development](06-usage-workflows.md#software-development) | [Development flows](workflow-diagrams.md#software-development) |
| Install or upgrade | [Installation](05-installation.md) | [Host integrations](07-tool-integrations.md) |
| Extend or maintain Forge | [Architecture](02-architecture.md) | [Maintainer guide](08-development-and-maintenance.md) |

## First use

1. [Install and verify the selected profile](05-installation.md) in your agent host.
2. Open your working folder. Its intent and rules establish the goal and boundaries.
3. Describe the result you want, the relevant context and any limits on action.
4. Review the result and its evidence. Use `save` when you want session persistence
   and the active project's authorized commit/push behavior.

For example: “Continue the application using the current draft and our earlier
constraints.” That is ordinary knowledge work. “Use Frame to examine why this plan
keeps slipping” invokes a reasoning method. “Implement the approved change” selects
development work in the applicable project context.

## Reader journey

These pages answer different questions; they are not a mandatory reading sequence.

| Page | Question it answers |
|---|---|
| [01 — Overview](01-overview.md) | What does Forge help with, and what does it require? |
| [02 — Architecture](02-architecture.md) | Which component owns each responsibility? |
| [03 — Repository map](03-repository-map.md) | Where are the implementation and reference files? |
| [04 — Core concepts](04-core-concepts.md) | What do the main terms mean? |
| [05 — Installation](05-installation.md) | How do I install, activate and update safely? |
| [06 — Usage and workflows](06-usage-workflows.md) | Which capability or method fits this request? |
| [07 — Tool integrations](07-tool-integrations.md) | What differs between agent hosts? |
| [08 — Development and maintenance](08-development-and-maintenance.md) | How do I change Forge itself? |
| [09 — Agent guide](09-agent-guide.md) | How should an agent load and follow the contracts? |
| [10 — Human guide](10-human-guide.md) | What should I delegate, decide and check? |
| [11 — Source grounding](11-source-grounding.md) | Where can I verify these explanations? |
| [12 — Troubleshooting](12-troubleshooting.md) | What do I do when setup or continuity fails? |
| [13 — Daily handbook](13-operational-handbook.md) | How do I start, continue, correct and save work? |
| [Visual guide](workflow-diagrams.md) | How do the capabilities and development flows connect? |

## Quick entry points

- **Existing user updating:** follow [coordinated installation](05-installation.md).
  A source update and successful installer exit do not alone prove activation.
- **Context is missing or stale:** start with the [daily handbook](13-operational-handbook.md#retrieve-and-correct-context),
  then [troubleshooting](12-troubleshooting.md) if retrieval or recovery is blocked.
- **A decision needs more scrutiny:** compare [Frame, Bedrock and Council](06-usage-workflows.md#general-reasoning).
- **A software workflow was interrupted:** use [selected development continuation](13-operational-handbook.md#continue-software-work).
- **You need the exact rule:** consult [source grounding](11-source-grounding.md).

## Documentation and authority

These pages explain the reader experience. Exact lifecycle rules live in the
[capability contract](../framework/capabilities.md), [Knowledge Processor](../skills/knowledge_processor/SKILL.md),
[process map](../framework/process-map.md) and linked method/runbook sources.
Installation profiles make capabilities available; project intent selects their use.

Examples describe intended operation, not proof that a particular host has loaded
its instructions. Check the actual host, permissions, files and outcome when that
matters. Review depth costs time and model calls; use it where consequences and
uncertainty justify it.

[Project home](../README.md) · [Contributing](../CONTRIBUTING.md) · [Security](../SECURITY.md)
