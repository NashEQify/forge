---
name: documentation-and-adrs
description: 'Capture decisions and documentation — why, alternatives, trade-offs. ADR discipline, README / changelog, API docs, agent-ready rules (CLAUDE.md). Adapted from addyosmani/agent-skills; MIT, see ## Source. Triggers when an architecture/API decision needs capturing (ADR / README / changelog) after the decision or before save; NOT for inline code comments.'
---

# Skill: documentation-and-adrs (Wrapper)

<!-- generated-by: scripts/generate_skill_wrappers.py (do not hand-edit) -->

This is the Claude-Code-discoverable wrapper. The full
orchestrator-neutral protocol — methodology, contract, modes,
red flags — lives in the SoT:

**SoT:** `skills/documentation_and_adrs/SKILL.md`

Read the SoT and follow it. This wrapper is a generated derived
artifact (`scripts/generate_skill_wrappers.py`); it exists only so
Claude Code can inject the skill into the available-skills
system-reminder for proactive discovery. Do not hand-edit — edits
are reverted on the next generator run and flagged by
`consistency_check`.
