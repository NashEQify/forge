# 03 — Repository Map

How the repo is organised and where to look for which question.

## Top-Level

```
forge/
├── CLAUDE.md                      # Tier 0 — Claude Code invariants
├── AGENTS.md                      # Tier 0 — OpenCode invariants
├── README.md                      # Public OSS entry point
├── intent.md                      # Vision / Done / Non-Goals / Context
│
├── agents/                        # Persona definitions (tool-neutral SoT)
│   ├── buddy/                     # Buddy tier 1 (soul, operational, boot, ...)
│   ├── _protocols/                # Persona-level cross-cutting protocols
│   ├── templates/                 # Persona templates
│   ├── navigation.md              # Reader journey + auto inventory
│   └── <persona>.md               # 34 personas (board, code, council, etc.)
│
├── framework/                     # Methodology — tier-1 .md files only
│   ├── README.md
│   ├── navigation.md              # Reader journey for framework/
│   ├── process-map.md             # Tier 1 — workflow routing
│   ├── skill-map.md               # Tier 1 — skill inventory (AUTO block)
│   ├── skill-anatomy.md           # Tier 1 — format standard for skills
│   ├── boot-navigation.md         # Tier 1 — boot index
│   ├── agent-autonomy.md          # Tier 1 — permission/gate/routing
│   ├── agent-patterns.md          # Tier 1 — pattern catalogue
│   ├── intent-tree.md             # Tier 1 — intent inheritance
│   ├── milestone-execution.md     # Tier 1 — multi-task orchestration
│   ├── convoy.md                  # Objective-progress tracking
│   ├── spec-engineering.md        # Spec theory (5 primitives)
│   ├── spec-authoring.md          # Redirect → skills/spec_authoring/
│   ├── task-format.md             # Task-format SoT
│   ├── test-plan-format.md        # Test-plan SoT
│   ├── scripts.md                 # Script inventory
│   ├── agent-skill-map.md         # Persona × skill map
│   ├── agentic-design-principles.md # Design rules (DR-1 … DR-13)
│   ├── context-and-loading.md     # Context loading semantics
│   ├── external-review-bundle-format.md
│   ├── getting-started.md
│   ├── models.md
│   └── workflow-engine-cookbook.md  # CLI cookbook + multi-machine warnings
│
├── skills/                        # 38 active skills (+1 deprecated, +1 draft = 40 dirs)
│   ├── _protocols/                # Skill-level cross-cutting protocols
│   ├── navigation.md              # Reader journey
│   └── <skill>/SKILL.md           # Per skill: frontmatter + 7 sections
│       └── REFERENCE.md           # Optional tier-2 detail
│
├── workflows/                     # 9 workflow runbooks
│   ├── runbooks/
│   │   ├── navigation.md
│   │   └── <workflow>/WORKFLOW.md
│   └── templates/
│
├── references/                    # Reference docs (a11y, perf, orch, ctx-md)
│   └── navigation.md
│
├── templates/                     # session-handoff-template.md
│
├── tests/                         # TESTCASES.md + hook tests + fabrication-mitigation
│
├── orchestrators/                 # Adapter layer
│   ├── claude-code/
│   │   ├── bin/                   # cc, sysadmin launcher
│   │   └── hooks/                 # 13 active hooks
│   ├── opencode/
│   │   ├── bin/oc                 # OC launcher
│   │   ├── .opencode/             # agent + command wrappers
│   │   └── opencode.jsonc.example
│   └── cursor/
│       └── rules/                 # Cursor rules
│
├── scripts/                       # Engines + generators
│   ├── plan_engine.py             # Computed planning layer
│   ├── workflow_engine.py         # YAML-driven workflow orchestration
│   ├── generate_skill_map.py      # AUTO-block skill-map
│   ├── generate_navigation.py     # AUTO-block navigation
│   ├── skill_fm_validate.py       # Pre-commit skill-frontmatter validator
│   ├── generate-{architecture,control,dashboard,status}.py
│   ├── consistency_check.py
│   ├── import_graph_check.py
│   ├── validate_evidence_pointers.py
│   ├── validate_runbook_consistency.py
│   ├── deploy-docs.sh
│   ├── setup-cc.sh / setup-oc.sh
│   ├── lib/                       # yaml_loader.py etc.
│   ├── vendor/
│   └── hooks/  →  ../orchestrators/claude-code/hooks  (symlink)
│
├── .claude/                       # Claude Code workspace config
│   ├── agents/                    # 30+ persona wrappers
│   ├── skills/                    # Skill wrappers (user-level discovery)
│   ├── path-whitelist.txt         # PreToolUse path-whitelist-guard SoT
│   ├── frozen-zones.txt           # PreToolUse frozen-zone-guard SoT
│   └── settings.json              # Hook registration
│
├── docs/                          # Project bookkeeping (no public content)
│   ├── plan.yaml                  # North Star + operational + phases + milestones
│   ├── tasks/                     # Self-contained tasks
│   ├── specs/                     # Specs (pre-build, implementation, reference)
│   ├── reviews/                   # Board + council outputs
│   │   ├── board/                 # Spec-Board / Code-Review-Board reviews
│   │   └── council/               # Architectural-Council synthesis
│   ├── architecture/              # Architecture notes
│   └── solve/                     # Solve workflow state files
│
├── architecture-documentation/    # Public OSS docs (THIS directory)
│   ├── README.md                  # Start here
│   └── 01-overview.md … 13-operational-handbook.md
│
├── context/                       # Session bookkeeping
│   ├── session-handoff.md
│   ├── session-log.md
│   ├── system/                    # System description
│   └── history/                   # Frozen Zone (WORM)
│
├── CONTRIBUTING.md, CODE_OF_CONDUCT.md, SECURITY.md, LICENSE
└── .gitignore, .git/, .claude/, .venv/
```

## Per-Directory Reader Journey (compact)

| Directory | What lives here? | Where for which question? |
|---|---|---|
| Repo root | tier-0 + vision files + public-doc entry | "Who is the agent?" → CLAUDE.md / AGENTS.md. "What is the project?" → README.md / intent.md |
| `agents/` | Persona definitions | "What does persona X look like?" → `<name>.md`. Buddy → `buddy/`. Protocols → `_protocols/` |
| `agents/buddy/` | Buddy tier 1 | Who-is-Buddy → `soul.md`. How-he-runs → `operational.md`. How-he-boots → `boot.md` |
| `framework/` | Methodology | Routing → `process-map.md`. Skills → `skill-map.md` (skills live at repo-root `skills/`). Workflows → repo-root `workflows/runbooks/` |
| `skills/` | 38 active skills (+1 deprecated, +1 draft = 40 dirs) | "Which skill for X?" → see `navigation.md` lookup table |
| `skills/_protocols/` | Skill-level mechanisms | "How do I isolate reviewer context?" → `context-isolation.md` |
| `workflows/runbooks/` | 9 workflows | "What does workflow X do?" → `<name>/WORKFLOW.md` |
| `references/` | Reference docs | a11y → `accessibility-checklist.md`. Orch pattern → `orchestration-patterns.md` |
| `agents/_protocols/` | Persona-level mechanisms | "Reviewer base rules?" → `reviewer-base.md` |
| `orchestrators/` | Adapter layer | Claude Code → `claude-code/`. OpenCode → `opencode/` |
| `scripts/` | Engines + generators | "plan_engine.py" + "workflow_engine.py" are the two central ones |
| `.claude/` | Workspace config for Claude Code | wrappers, hook registration, path whitelist |
| `docs/` | Project bookkeeping | plan → `plan.yaml`. Tasks → `tasks/`. Reviews → `reviews/` |
| `architecture-documentation/` | Public OSS docs | You are here |

## Navigation Layer

For each top-level-3 directory there is a `navigation.md` with
- `## What lives here?` (manual, reader journey)
- `## Where for which question?` (manual, lookup table)
- `## Inventory (auto)` (generated by `scripts/generate_navigation.py`)

8 targets:
- `framework/navigation.md`
- `skills/navigation.md`
- `skills/_protocols/navigation.md`
- `workflows/runbooks/navigation.md`
- `references/navigation.md`
- `agents/navigation.md`
- `agents/buddy/navigation.md`
- `agents/_protocols/navigation.md`

Drift protection: `consistency_check` Check 8 (existence + idempotency + manual-filled).

## Convention Notes

### Frozen Zones

`.claude/frozen-zones.txt` lists glob patterns whose writes are mechanically
blocked (`frozen-zone-guard.sh`). Files in those paths are WORM
(write-once-read-many) — corrections via `.correction.md` sidecar.

The canonical entry is `context/history/**` (session-history append-only log).

### Path Whitelist

`.claude/path-whitelist.txt` is generated per user by `scripts/setup-cc.sh`.
The committed `.claude/path-whitelist.txt.example` is the template; the live
file lists absolute paths the agent may write under. See `12-troubleshooting.md`
for setup notes.

### Naming Convention (skills)

`framework/skill-anatomy.md` §Naming:
- Default: `verb_object` (`task_creation`, `verify_amendment`)
- Allowed: `object` when the verb is implicit (`spec_board`, `council`, `testing`)
- Maximum 3 words / underscore segments

### Skill format

Every active skill is a directory under `skills/` containing a single
`SKILL.md` (frontmatter + 7 sections) and an optional tier-2 `REFERENCE.md`.
See `framework/skill-anatomy.md` for the format specification.
