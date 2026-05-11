# framework/

Methodology layer of forge: Tier-1 operational docs, design
principles, and format specs. Skills, workflows, references, and templates
are siblings at the repo root, not children of this directory.
Tool-neutral; consumed by Claude Code, OpenCode, and future adapters
through wrappers.

**Public OSS docs for readers:** [`../architecture-documentation/`](../architecture-documentation/).
**Reader journey:** [`navigation.md`](navigation.md).

---

## Tier-1 top-level files

| File | Purpose |
|---|---|
| `process-map.md` | workflow routing (what-do-I-want -> which workflow) |
| `skill-map.md` | skill inventory (AUTO block via `scripts/generate_skill_map.py`) |
| `skill-anatomy.md` | format standard for skills |
| `boot-navigation.md` | boot index (workflows + skills) |
| `agent-autonomy.md` | permission/gate/routing triple per artifact type |
| `agent-patterns.md` | active agent patterns from real drift cases |
| `agentic-design-principles.md` | design rules (DR-1 to DR-13) |
| `intent-tree.md` | intent inheritance + constraint hierarchy |
| `milestone-execution.md` | multi-task orchestration |
| `models.md` | model assignment (agent -> model, CC + OC) |
| `context-and-loading.md` | context mechanics + loading order |
| `convoy.md` | objective progress tracking format |
| `spec-engineering.md` | spec theory (5 primitives) |
| `task-format.md` | task format SoT |
| `test-plan-format.md` | test plan SoT |
| `scripts.md` | script inventory |
| `getting-started.md` | onboarding notes |

---

## Skills (`../skills/`)

38 active skills. Full inventory + composition:
[`skill-map.md`](skill-map.md). Reader-journey lookup:
[`../skills/navigation.md`](../skills/navigation.md).

**Skill-class model:** single-class. Variation lives in `invocation.primary`
(`user-facing | workflow-step | sub-skill | hook | cross-cutting`).
Frontmatter is mandatory; pre-commit SKILL-FM-VALIDATE BLOCK enforced.

**Skill-level protocols:** [`../skills/_protocols/`](../skills/_protocols/) —
cross-cutting mechanics inlined by skills via the `uses:` list.

---

## Workflows (`../workflows/runbooks/`)

9 active workflows. Producer class (5-phase standard):
`build`, `fix`, `review`, `solve`. Others: `audit`, `research`,
`docs-rewrite`, `save`, `context_housekeeping`. Routing:
[`process-map.md`](process-map.md). Reader journey:
[`../workflows/runbooks/navigation.md`](../workflows/runbooks/navigation.md).

---

## References (`../references/`)

External pattern lifts + reference material:
`accessibility-checklist.md`, `performance-checklist.md`, `orchestration-patterns.md`,
`context-md-convention.md`. Details: [`../references/navigation.md`](../references/navigation.md).

---

## Tests (`../tests/`)

`tests/TESTCASES.md` — structural tests for Buddy behavior (T01-Tnn,
manual walkthrough). `tests/hooks/` — hook smoke tests (bash).

---

## Consumed by

Consumer repos via `--add-dir $FRAMEWORK_DIR` (Claude Code) and
`OPENCODE_CONFIG_DIR` (OpenCode). Adapter details:
[`../architecture-documentation/07-tool-integrations.md`](../architecture-documentation/07-tool-integrations.md).
