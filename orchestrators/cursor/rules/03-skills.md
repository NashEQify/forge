---
description: Skill discovery + invocation under Cursor
---

# Skills

Skills live under `skills/<name>/SKILL.md` (Anatomy v2). Inventory
+ routing:

- `framework/skill-map.md` — full skill inventory (auto-generated from
  frontmatter)
- `framework/skill-anatomy.md` — format standard (v2 mandatory)
- `skills/navigation.md` — Reader-Journey lookup table
- `framework/process-map.md` — workflow routing (which workflow for what)

## Invocation pattern

A skill is invoked by reading `skills/<name>/SKILL.md` (and
`REFERENCE.md` if present), then following its 7 mandatory sections —
in particular Process. No tool call needed; skills are methodology, not
RPC.

## Direct-Invokable skills (`invocation.primary: user-facing`)

These can be invoked directly by user:
- `task_creation`, `scoping`, `frame`, `improve_codebase_architecture`,
  `shipping_and_launch`, `deprecation_and_migration`,
  `api_and_interface_design`, `caveman`, `zoom_out`,
  `youtube_subtitles`

## Cross-cutting (`invocation.primary: cross-cutting`)

Loaded by Buddy's operational rules in multiple phases:
- `consistency_check`, `knowledge_processor`, `task_status_update`,
  `transparency_header`

## Skill-Level Protocols

`skills/_protocols/` — loaded inline when a skill's `uses:`
list references them. Examples:
- `discourse.md` — board cross-validation
- `context-isolation.md` — anti-anchoring
- `dispatch-template.md` — board-dispatch without buddy-bias
- `piebald-budget.md` — token-budget hard gate
- `plan-review.md` — plan-self-review mechanic
