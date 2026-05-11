---
description: How to invoke specialized personas under Cursor (no Task-tool yet)
---

# Personas under Cursor

Cursor's Composer / Chat does not have an analog of Claude Code's
`Agent`/`Task` tool with sub-agent isolation (as of late 2025). When the
methodology calls for a specialized persona (Spec-Board reviewer, Code-
Review-Board reviewer, Council member), use the **manual @-mention pattern**:

```
@<persona> <task>
```

When invoked, you (Cursor agent) read the persona definition from
`agents/<persona>.md` plus its associated protocols
(`agents/_protocols/<protocol>.md`) and follow them strictly.

## Persona index (selected)

| Persona | File |
|---|---|
| `buddy` | `agents/buddy/` |
| `main-code-agent` | `agents/main-code-agent.md` |
| `solution-expert` | `agents/solution-expert.md` |
| `code-review` (multi-axis) | `agents/code-review.md` |
| `code-adversary` | `agents/code-adversary.md` |
| `code-chief` (consolidator) | `agents/code-chief.md` |
| `board-chief` (Spec-Board) | `agents/board-chief.md` |
| `board-adversary` | `agents/board-adversary.md` |
| `board-implementer` | `agents/board-implementer.md` |
| `board-impact` | `agents/board-impact.md` |
| `board-consumer` | `agents/board-consumer.md` |
| `board-ux-heuristic` | `agents/board-ux-heuristic.md` |
| `board-ux-ia` | `agents/board-ux-ia.md` |
| `board-ux-interaction` | `agents/board-ux-interaction.md` |
| `council-member` | `agents/council-member.md` |
| `tester` | `agents/tester.md` |

Full list: `agents/navigation.md`.

## Protocol-Loading

When a persona references protocols via "loaded by" or `uses:`, load those
inline before responding. Examples:

- `agents/_protocols/reviewer-base.md` — all review agents
- `agents/_protocols/<board>-reviewer-protocol.md` — board-specific
- `agents/_protocols/reviewer-reasoning-trace.md` + `first-principles-check.md`
  — mandatory for review output

## Multi-perspective trade-off

Without parallel sub-agent spawn, Spec-Board / Code-Review-Board reviews
run **sequentially** under Cursor. Buddy (you) coordinates: invoke each
reviewer in turn via @-mention, collect outputs, then invoke
`code-chief` / `board-chief` to consolidate. This is slower but
methodologically equivalent — anchoring discipline (Buddy-as-dispatcher
rule) still applies: don't read each review result mentally before all
reviewers have produced theirs.
