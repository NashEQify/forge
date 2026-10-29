---
description: Tier-0 invariants for forge — load first
alwaysApply: true
---

Read and follow `framework/work-principle.md` before taking up work.
Resolve this reference against the framework root; retain the consumer CWD.


# Tier 0 — Invariants (forge)

This repo follows the forge methodology. The Tier-0 anchor is
`framework/invariants.md` (orchestrator-agnostic); `AGENTS.md` and `CLAUDE.md`
at the root add the forge repository's own rules and the host's load list.

**Read it first.** It defines the non-negotiable invariants; in short:

1. **Board/Council:** reviewers investigate independently; Chiefs consolidate where
   selected. Buddy owns the decision and checks load-bearing source claims. Inspect
   relevant findings to resolve contradictions without routinely repeating reviews.
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
