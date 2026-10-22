# Framework contracts

This directory holds the shared rules and boundaries behind Forge's three
capabilities. For an introduction, start with the
[public documentation](../architecture-documentation/README.md). For a complete
file index, use [navigation.md](navigation.md).

## Start with the boundary you need

| Question | Canonical contract |
|---|---|
| What belongs to each capability? | [Capabilities](capabilities.md) |
| Where does personal or project context belong? | [User scope](user-scope.md) |
| How are coherent reads, publication and recovery protected? | [Continuity](continuity.md) |
| Who decides whether software workflows apply? | [Process map](process-map.md) |
| How is selected development state resumed? | [Development continuation](development-continuation.md) |
| How is an installed generation updated and verified? | [Installation activation](installation-activation.md) |
| What source dependencies does each installation need? | [Install profiles](install-profiles.yaml) |

Semantic knowledge reconciliation belongs to the
[Knowledge Processor](../skills/knowledge_processor/SKILL.md). The continuity helper
protects file operations; it does not decide the meaning or ownership of a fact.
General methods have their own contracts under `skills/`. Development processes
live in [runbooks](../workflows/runbooks/navigation.md); common save and housekeeping
use direct entries and do not require the development engine.

## Reference for maintainers

- [Skill map](skill-map.md) and [skill anatomy](skill-anatomy.md): discovery,
  invocation and extension rules.
- [Context and loading](context-and-loading.md): selection and loading boundaries.
- [Agent autonomy](agent-autonomy.md) and [intent tree](intent-tree.md): authority,
  scope and delegation.
- [Spec engineering](spec-engineering.md), [task format](task-format.md) and
  [test plan format](test-plan-format.md): selected development artifacts.
- [Scripts](scripts.md): mechanical helpers and their responsibilities.
- [Enforcement registry](enforcement-registry.md): which checks exist and how they run.

Host adapters expose these shared contracts rather than copying their algorithms.
Codex uses managed AGENTS instructions and generated discovery; Claude Code and
OpenCode use their installed integrations. Effective permissions and instruction
loading need host-specific verification. See [host integrations](../architecture-documentation/07-tool-integrations.md).
