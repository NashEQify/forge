# Agent roles

These files define Forge's roles. The [role index](navigation.md) lists their
current owners. Host adapters expose selected roles through their discovery
mechanisms; an installed role is not an instruction to delegate every request.

## Responsibilities

| Role family | Responsibility |
|---|---|
| [Buddy](buddy/) | Understand the user's intent, retrieve relevant context, coordinate authorized work and own decisions |
| [Council members](council-member.md), [adversary](council-adversary.md), [Chief](council-chief.md) | Independent decision perspectives, challenges and consolidation when the selected method requires them |
| [Main code agent](main-code-agent.md) | Implement delegated software work and supply verification evidence |
| Spec and code review roles | Investigate the supplied specification or implementation from distinct perspectives |
| [Tester](tester.md) and [test skeleton writer](test-skeleton-writer.md) | Design or execute the selected testing work |
| [Security](security.md) | Authorized security investigation within its defined scope |

A Chief consolidates findings and disagreement. Buddy owns the resulting decision
and verifies load-bearing claims against their sources. Role names do not prove
independent execution, model diversity or effective read-only permissions.

## Context and delegation

Every delegation supplies its scope, question, relevant evidence and success
criteria. Reviewers investigate independently under the selected method's
[dispatch protocol](../skills/_protocols/dispatch-template.md). Complete returns
are preserved before consolidation. The supplied intent and constraints matter;
reviewers need not inherit the parent conversation to understand them.

Ordinary knowledge work can remain in the primary conversation. Council and other
general methods can be invoked without software bookkeeping. Development delegation
follows the [selected process](../framework/process-map.md) and its runbook.

## Host discovery

- Claude Code wrappers are under `.claude/agents/` in the framework.
- OpenCode wrappers are under `orchestrators/opencode/.opencode/agent/`.
- Codex roles are generated into its configured agents directory by the installer.
- Cursor includes separate rules and persona templates; these alone do not provide
  independent-agent execution.

Model selection and runtime permissions depend on the installed host configuration.
[Host integrations](../architecture-documentation/07-tool-integrations.md) explains
the supported surfaces and the limits of each setup.
