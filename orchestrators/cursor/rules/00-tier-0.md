---
description: Tier-0 invariants for forge — load first
alwaysApply: true
---

# Tier 0 — Invariants (forge)

This repo follows the forge methodology. The two Tier-0 anchor
files are `AGENTS.md` (this repo's root) and `CLAUDE.md` (also at root, for
Claude Code adapter — applies even outside CC since the invariants are
orchestrator-agnostic).

**Read those first.** They define non-negotiable invariants:

1. **Board/Council: Buddy = Dispatcher** — when running multi-perspective
   reviews, the orchestrator (Buddy or you-as-Cursor-agent) does NOT read
   review files, analyze findings, or write consolidations. Spawn → read
   chief-signal → save → escalate. Anchoring corrupts multi-perspective.

2. **Default: Discuss, don't implement** — only act on a clear imperative.
   When unclear, ask. Self-triggered changes: always discuss first.
   Context-writes and bookkeeping are exceptions (no gate).

3. **Pre-Delegation Non-Negotiable** — no sub-agent / sub-task call without
   a Plan-Block (scope, tool/agent, alternatives, expected artifacts) or
   a Gate-File. Routing: `framework/process-map.md`.

4. **Code-Delegation** — production code → main-code-agent. Orchestrator
   work (agents/, framework/, scripts/, context/, docs/) → write directly.

5. **Stale-Cleanup** — when archiving/replacing/deprecating an artifact,
   clean ALL active references in the same commit. `grep -rn <artifact>` +
   filter frozen zones + fix the rest.

6. **Deployment-Verification** — after deploy, verify visually, not just
   HTTP-200. If visual not possible: report explicitly and ask the user.

These rules apply regardless of which IDE/CLI invokes you.
