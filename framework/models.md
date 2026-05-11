# Model Assignment

Single source of truth for which agent uses which model.
Changes here -> call the model-switch skill -> adapters update automatically.

## Current assignment

| Agent               | Claude Code (cc) | OpenCode (oc)                       | Rationale                      |
|---------------------|------------------|-------------------------------------|--------------------------------|
| buddy               | opus             | anthropic/claude-opus-4-6           | orchestration, no thinking     |
| buddy-thinking      | opus             | anthropic/claude-opus-4-6           | deep conversations             |
| solution-expert     | opus             | anthropic/claude-opus-4-6           | council always max-depth       |
| main-code-agent     | opus             | anthropic/claude-opus-4-6           | autonomous planning            |
| reviewer            | sonnet           | anthropic/claude-sonnet-4-6         | pattern matching               |
| requirements-tester | sonnet           | anthropic/claude-sonnet-4-6         | reading + comparison           |
| tester              | sonnet           | anthropic/claude-sonnet-4-6         | design mode needs analysis     |
| spec-validator      | sonnet           | anthropic/claude-sonnet-4-6         | validation needs analysis      |

## Global setting per orchestrator

| Orchestrator | Global setting                |
|--------------|-------------------------------|
| cc           | opus, no extended thinking    |
| oc           | configured per agent          |

## Adapter paths

| Orchestrator | Path                                             | Model format                 |
|--------------|--------------------------------------------------|------------------------------|
| cc           | `.claude/agents/<n>/<n>.md`                      | alias: opus / sonnet / haiku |
| oc           | `orchestrators/opencode/.opencode/agent/<n>.md`  | provider/model string        |

## Model switch

Manual: update this table + both adapter files.
With skill: call `skills/model_switch/SKILL.md`.

## LiteLLM runtime router (BuddyAI harness)

**Decision:** Day 1 with cloud fallback. Ollama local as primary, cloud API as fallback.
LiteLLM container in docker-compose.yml. Model routing config: `config/litellm_config.yaml`.

Once LiteLLM router is in place (stage 1.5+):
the oc column can point to LiteLLM aliases instead of direct provider strings.
cc remains unchanged (talks directly to Anthropic API).
