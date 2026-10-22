# 03 — Repository Map

Use this map to find the owner of a behavior. The framework checkout supplies
reusable methods and tools; the active consumer workspace supplies its goals,
knowledge and local rules. They may be separate directories.

## Top-Level

| Path | What belongs here | Start with |
|---|---|---|
| `README.md` | Product introduction and reader routes | [README](../README.md) |
| `architecture-documentation/` | Public explanations and practical guides | [Documentation hub](README.md) |
| `agents/` | Canonical roles and Buddy's entry procedures | [Role navigation](../agents/navigation.md) |
| `framework/` | Shared contracts, ownership and routing | [Capability ownership](../framework/capabilities.md) |
| `skills/` | Executable methods and their references | [Skill map](../framework/skill-map.md) |
| `skills/_protocols/` | Shared method protocols | [Protocol navigation](../skills/_protocols/navigation.md) |
| `workflows/runbooks/` | Common save/housekeeping and development runbooks | [Process map](../framework/process-map.md) |
| `scripts/` | Installers, continuity helpers, engines and generators | [Script reference](../framework/scripts.md) |
| `orchestrators/` | Host launchers, adapters and integration assets | [Host integrations](07-tool-integrations.md) |
| `.claude/` | Claude wrappers and integration files | [Claude adapter](07-tool-integrations.md#claude-code) |
| `.codex/` | Repository Codex configuration and role templates | [Codex adapter](07-tool-integrations.md#codex) |
| `references/` | Supporting reference material | [Reference navigation](../references/navigation.md) |

A folder can serve more than one capability. For example, `scripts/continuity.py`
serves common knowledge storage, while `scripts/workflow_engine.py` owns development
state. Do not infer dependencies from physical proximity.

## Where each capability starts

| Question | Canonical entry |
|---|---|
| Where should a new fact go? | [Knowledge Processor](../skills/knowledge_processor/SKILL.md) |
| How are concurrent updates protected? | [Continuity](../framework/continuity.md) |
| Which files describe the person? | [User scope](../framework/user-scope.md) |
| How do I save or resume ordinary work? | [Save runbook](../workflows/runbooks/save/WORKFLOW.md) and [minimal boot](../agents/buddy/boot-on-demand.md) |
| How do I examine a problem? | [Frame](../skills/frame/SKILL.md) or [Bedrock](../skills/bedrock_drill/SKILL.md) |
| How do I compare independent perspectives? | [Council](../skills/council/SKILL.md) |
| Which software process applies? | [Process map](../framework/process-map.md) |
| What exact software state must survive? | [Development continuation](../framework/development-continuation.md) |
| What is installed together? | [Install profiles](../framework/install-profiles.yaml) |

## Consumer workspace

A consumer keeps its established content organization. These are common routes,
not a requirement to create every file for every conversation:

```text
<workspace>/
  intent.md                    goal and workflow selection
  AGENTS.md or CLAUDE.md        local working rules
  context/
    navigation.md              routes to project knowledge
    session-handoff.md         current continuation, if this is the local name
    <topic>.md                 project-owned facts and decisions
  docs/                        domain documents; software records when selected
```

Keep an existing handoff name such as `session-handover.md`; do not create a
competing file merely to match this illustration. Follow the workspace's explicit
navigation and storage instructions before defaults.

The configured user repository adds `context/user/profile.md`, optional `soul.md`,
`navigation.md` and topic files. Its profile is a short boot interface; detail is
retrieved on demand. Personal and project scope remain distinct even when both
use the same repository root.

## Local state versus shared content

The machine setting lives at `${XDG_CONFIG_HOME:-~/.config}/forge/user.yaml`, unless
`FORGE_USER_CONFIG` overrides it. It identifies the user repository and installation
selection. It is not a place to copy personal knowledge.

Installation manifests and journals track managed files and activation. Continuity
locks coordinate local writers. Pending continuity records preserve unfinished
publication in their responsible scope. These have different owners and must not
be treated as interchangeable caches.

Development `.workflow-state/` is local and gitignored in Forge. An exact workflow
reference in a committed handoff does not make its state available on another
machine. Check availability and compatibility before continuing there.

## Navigation Layer

Navigation files and generated indexes reduce the amount an agent needs to load.
Follow the current topic's route instead of reading every directory. Generated
`AUTO` blocks come from their declared sources; edit the source and regenerate
rather than correcting the generated list by hand.

The [structure contract](../docs/STRUCTURE.md) describes artifact placement and
frozen zones. Frozen history is preserved; retiring a live artifact includes
updating its live references and navigation in the same change.

Next: [Core concepts](04-core-concepts.md) · [Source grounding](11-source-grounding.md).
