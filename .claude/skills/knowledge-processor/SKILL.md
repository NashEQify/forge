---
name: knowledge-processor
description: 'The context-write mechanism — reconcile new information against existing knowledge so `context/` and the user''s own repo stay accurate. Triggers when new information must be folded in: a fact, decision, correction or changed state in the conversation (same response cycle under continuous maintenance), a task status change, save, or an agent return; NOT a standalone workflow — it is cross-cutting infrastructure.'
---

# Skill: knowledge-processor (Wrapper)

<!-- generated-by: scripts/generate_skill_wrappers.py (do not hand-edit) -->

This is the Claude-Code-discoverable wrapper. The full
orchestrator-neutral protocol — methodology, contract, modes,
red flags — lives in the SoT:

**SoT:** `skills/knowledge_processor/SKILL.md`

Read the SoT and follow it. This wrapper is a generated derived
artifact (`scripts/generate_skill_wrappers.py`); it exists only so
Claude Code can inject the skill into the available-skills
system-reminder for proactive discovery. Do not hand-edit — edits
are reverted on the next generator run and flagged by
`consistency_check`.
