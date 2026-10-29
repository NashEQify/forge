---
name: session-diagnosis
description: Read a session's transcript and its subagent transcripts in place, check first whether Forge loaded, then report per dimension what happened, with a path:line for every finding and the question whether the problem occurs without Forge. Use when a session went wrong and the user asks why (a skill that did not fire, an ignored plan or rule, repeated work, stumbles, unsupported claims, cost or time), or to gather evidence for a Forge report; NOT for repairing the defect (use root_cause_fix) or reviewing code (use code_review_board).
---

# Skill: session-diagnosis (Wrapper)

<!-- generated-by: scripts/generate_skill_wrappers.py (do not hand-edit) -->

Read and follow `framework/work-principle.md` before taking up work.
Resolve it against the same framework root as the SoT; retain the consumer CWD.

This is the Claude-Code-discoverable wrapper. The full
orchestrator-neutral protocol — methodology, contract, modes,
red flags — lives in the SoT:

**SoT:** `skills/session_diagnosis/SKILL.md`

Read the SoT and follow it. This wrapper is a generated derived
artifact (`scripts/generate_skill_wrappers.py`); it exists only so
Claude Code can inject the skill into the available-skills
system-reminder for proactive discovery. Do not hand-edit — edits
are reverted on the next generator run and flagged by
`consistency_check`.
