# 11 — Source Grounding

Which technical statements are backed by which files. Traceability is a
mandatory part of the public-OSS quality bar — no invented features.

## Methodology

Every technical claim in `architecture-documentation/` is traceable back
to a file path. The mapping below is the audit table.

## Mapping: claim → evidence

### Tier-0 invariants

| Claim | Evidence |
|---|---|
| 6 Buddy invariants under Claude Code | [`../CLAUDE.md`](../CLAUDE.md) §1-6 |
| 7 Buddy invariants under OpenCode (additional FACTS check) | [`../AGENTS.md`](../AGENTS.md) §1-7 |
| Boot instruction: `Load and follow: agents/buddy/{soul,operational,boot}.md` | [`../CLAUDE.md`](../CLAUDE.md):4-5, [`../AGENTS.md`](../AGENTS.md):4-5 |
| Frozen-zones SoT: `docs/STRUCTURE.md` (Note: `docs/STRUCTURE.md` does not exist in the repo — see drift notes in §Drift notes) | [`../CLAUDE.md`](../CLAUDE.md):46-47 |
| Stale-cleanup invariant (all refs in the same commit) | [`../CLAUDE.md`](../CLAUDE.md):29-34 |
| Pre-delegation non-negotiable | [`../CLAUDE.md`](../CLAUDE.md):18-22 |

### Buddy model

| Claim | Evidence |
|---|---|
| RECEIVE → ACT → BOUNDARY structure | [`../agents/buddy/operational.md`](../agents/buddy/operational.md):3-5 |
| Three mental states (incident / substantive / trivial) | [`../agents/buddy/operational.md`](../agents/buddy/operational.md):11-15 |
| Routing table (code → MCA, architecture → solution-expert, security → security, sysadmin → Buddy) | [`../agents/buddy/operational.md`](../agents/buddy/operational.md):37-42 |
| Boot sequence ORIENT → RESOLVE → ROUTE → LOAD → STATUS-CHECK → RESUME → GREET | [`../agents/buddy/boot.md`](../agents/buddy/boot.md):22-79 |
| Persist gate blocking on status change | [`../agents/buddy/operational.md`](../agents/buddy/operational.md):99-104 |
| Source-grounding discipline (>5 turns old → read) | [`../agents/buddy/operational.md`](../agents/buddy/operational.md):54-57 |

### Skill anatomy

| Claim | Evidence |
|---|---|
| Single-class skill model | [`../framework/skill-anatomy.md`](../framework/skill-anatomy.md) §Format definition |
| Mandatory frontmatter fields | [`../framework/skill-anatomy.md`](../framework/skill-anatomy.md) §Frontmatter |
| 7 mandatory sections + 2 optional | [`../framework/skill-anatomy.md`](../framework/skill-anatomy.md) §Required sections |
| `invocation.primary` vocabulary (5 values) | [`../framework/skill-anatomy.md`](../framework/skill-anatomy.md) §invocation |
| Anti-inflation: new skills only with a standalone-justification | [`../framework/skill-anatomy.md`](../framework/skill-anatomy.md) §Inflation guard |
| Naming convention `verb_object` default | [`../framework/skill-anatomy.md`](../framework/skill-anatomy.md) §Naming convention |
| Mode convention: max 3 modes per skill | [`../framework/skill-anatomy.md`](../framework/skill-anatomy.md) §Modes |
| Token budget ≤120 lines for v2 skills | [`../skills/_protocols/piebald-budget.md`](../skills/_protocols/piebald-budget.md):17 |

### Skill inventory

| Claim | Evidence |
|---|---|
| 38 active skills | [`../framework/skill-map.md`](../framework/skill-map.md) AUTO block + `find skills -maxdepth 2 -name SKILL.md \| xargs -I{} grep -l 'status: active' {}` |
| 13 skill-level protocols | `ls skills/_protocols/` |
| Direct-invocable capabilities list | [`../framework/skill-map.md`](../framework/skill-map.md):71-73 (AUTO block) |
| Cross-cutting skills | [`../framework/skill-map.md`](../framework/skill-map.md):85 (AUTO block) |

### Workflows

| Claim | Evidence |
|---|---|
| 8 active workflows | `ls workflows/runbooks/` (`build`, `context_housekeeping`, `docs-rewrite`, `fix`, `research`, `review`, `save`, `solve`) |
| Workflow-routing table "what do I want → which workflow" | [`../framework/process-map.md`](../framework/process-map.md):14-31 |
| 5-phase standard for producer class (specify/prepare/execute/verify/close) | [`../workflows/runbooks/build/WORKFLOW.md`](../workflows/runbooks/build/WORKFLOW.md) phase sections |
| build path-determination (DIRECT/STANDARD/FULL) | [`../workflows/runbooks/build/WORKFLOW.md`](../workflows/runbooks/build/WORKFLOW.md):21-26 |
| solve 5 phases | [`../workflows/runbooks/solve/WORKFLOW.md`](../workflows/runbooks/solve/WORKFLOW.md) |
| save 3 groups (A pre-write, B content-writes parallel, C post-write) | [`../workflows/runbooks/save/WORKFLOW.md`](../workflows/runbooks/save/WORKFLOW.md):5-25 |

### Personas

| Claim | Evidence |
|---|---|
| 34 personas including Buddy + boards + standalone | `ls agents/*.md` plus `agents/buddy/` |
| Spec-Board: chief, adversary[-2], implementer, impact, consumer (5) | `ls agents/board-*.md` |
| UX-Board: ux-heuristic, ux-ia, ux-interaction (3) | `ls agents/board-ux-*.md` |
| Code-Review-Board: 13 personas (multi-axis hybrid) | `ls agents/code-*.md` |
| Standalone: main-code-agent, council-member, solution-expert, security, tester, test-skeleton-writer, plan-adversary | `ls agents/<name>.md` |
| Persona token budget ≤70 lines | [`../skills/_protocols/piebald-budget.md`](../skills/_protocols/piebald-budget.md) |

### Hooks

| Claim | Evidence |
|---|---|
| 13 active hooks | `ls orchestrators/claude-code/hooks/*.sh` |
| Pre-commit 12 checks (PLAN-VALIDATE, TASK-SYNC, OBLIGATIONS, CG-CONV, STALE-CLEANUP, PERSIST-GATE, SKILL-FM-VALIDATE, ENGINE-USE, RUNBOOK-DRIFT, AGENT-SKILL-DRIFT, SECRET-SCAN, SOURCE-VERIFICATION) | [`../orchestrators/claude-code/hooks/pre-commit.sh`](../orchestrators/claude-code/hooks/pre-commit.sh) |
| 3 checks BLOCK (PLAN-VALIDATE, CG-CONV, SKILL-FM-VALIDATE), 9 checks WARN | [`../orchestrators/claude-code/hooks/pre-commit.sh`](../orchestrators/claude-code/hooks/pre-commit.sh) |
| Path-whitelist + frozen-zones SoT | [`../.claude/path-whitelist.txt.example`](../.claude/path-whitelist.txt.example) (template; `setup-cc.sh` generates the live `path-whitelist.txt`) + [`../.claude/frozen-zones.txt`](../.claude/frozen-zones.txt) |

### Adapter

| Claim | Evidence |
|---|---|
| Claude-Code adapter active | `ls orchestrators/claude-code/` |
| OpenCode adapter active with constraints | `ls orchestrators/opencode/` + [`../AGENTS.md`](../AGENTS.md) §OC constraints |
| Cursor adapter present | `ls orchestrators/cursor/` (rules-only adapter) |
| `cc` launcher scope routing | [`../orchestrators/claude-code/bin/cc`](../orchestrators/claude-code/bin/cc):91-191 |
| OC wrapper single-liner | [`../orchestrators/opencode/bin/oc`](../orchestrators/opencode/bin/oc) |
| `~/.claude/agents` as a mandatory symlink | [`../orchestrators/claude-code/bin/cc`](../orchestrators/claude-code/bin/cc):38-89 |

### Engines + generators

| Claim | Evidence |
|---|---|
| `plan_engine.py` ~3.6k LoC | `wc -l scripts/plan_engine.py` |
| `workflow_engine.py` ~2.5k LoC | `wc -l scripts/workflow_engine.py` |
| `generate_skill_map.py` regenerates the AUTO block | [`../scripts/generate_skill_map.py`](../scripts/generate_skill_map.py) + [`../framework/skill-map.md`](../framework/skill-map.md) marker |
| `generate_navigation.py` regenerates AUTO blocks in 8 navigation.md files | [`../scripts/generate_navigation.py`](../scripts/generate_navigation.py) |
| `skill_fm_validate.py` pre-commit Check 7 | [`../scripts/skill_fm_validate.py`](../scripts/skill_fm_validate.py) + [`../orchestrators/claude-code/hooks/pre-commit.sh`](../orchestrators/claude-code/hooks/pre-commit.sh) |
| Generator + validator pattern | [`../skills/consistency_check/REFERENCE.md`](../skills/consistency_check/REFERENCE.md) §6 + §8 |

### Consumer repositories

| Claim | Evidence |
|---|---|
| Framework is mounted INTO consumer repos (consumer repo is CWD; framework via `--add-dir $FRAMEWORK_DIR`) | [`../orchestrators/claude-code/bin/cc`](../orchestrators/claude-code/bin/cc) §"Build --add-dir args" |

## How to verify this documentation

If you find a claim in this documentation doubtful:

1. Look up the relevant mapping in the table above.
2. Open the evidence file at the given path / line number.
3. Read the context.
4. If the evidence does not hold up: that is a documentation bug —
   please report it.

## Next step

For issues / known stumbling blocks: [`12-troubleshooting.md`](12-troubleshooting.md).
