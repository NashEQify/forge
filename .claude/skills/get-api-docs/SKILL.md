---
name: get-api-docs
description: Use this skill to fetch current documentation for external APIs/libraries via the chub CLI before writing code that uses them. Required when implementing against an external API/library where actual current behavior matters more than training-data snapshot (which can be months old). Triggers when about to write code calling an unfamiliar API, when API behavior is version-sensitive, when User asks "wie funktioniert X aktuell", when MCA hits an external integration without recent docs in context. Examples: before coding FastAPI/Pydantic/SQLAlchemy integrations, before consuming a third-party REST API, when investigating breaking changes between library versions.
---

# Skill: get-api-docs (Wrapper)

This is the Claude-Code-discoverable wrapper. The full protocol (chub CLI
invocation pattern, doc-extraction, integration into spec/code) lives in
the orchestrator-neutral SoT:

**SoT:** `skills/get_api_docs/SKILL.md`

Read the SoT and follow it. This wrapper exists only so Claude Code can
inject the skill into the available-skills system-reminder for proactive
discovery — the methodology is unchanged.
