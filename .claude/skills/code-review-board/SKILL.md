---
name: code-review-board
description: Use this skill to run a multi-agent code-diff review (L1 standard or L2 deep) with adversary/quality/security perspectives and Drill+Trace enforcement. Distinct from the CC plugin `/review` slash-command — `/review` is PR-level via gh (one reviewer, PR-context); code-review-board reviews code-diffs at the file/module level with multiple parallel agents in context-isolation. Triggers when User asks to review code changes ("review meinen Code", "schau dir den Diff an", "ist das implementation-ready?"), after MCA writes substantial code (post-coding verify-step in build-workflow), when a code-diff needs structured multi-perspective validation before merge, or when fix-workflow needs L1 verification before close. NOT for PR-level checks (use /review) and NOT for spec reviews (use spec-board).
---

# Skill: code-review-board (Wrapper)

This is the Claude-Code-discoverable wrapper. The full protocol (L1/L2
stage selection, agent dispatch, Drill+Trace enforcement, finding
consolidation, convergence loop) lives in the orchestrator-neutral SoT:

**SoT:** `skills/code_review_board/SKILL.md`

Read the SoT and follow it. This wrapper exists only so Claude Code can
inject the skill into the available-skills system-reminder for proactive
discovery — the methodology is unchanged.
