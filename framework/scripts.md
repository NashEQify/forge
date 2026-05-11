# Framework scripts — path table + caller convention

Central overview of executable scripts under `$FRAMEWORK_DIR/scripts/`.

## Convention

**From consumer repos (BuddyAI, Huddle, personal, external projects):**
always call scripts as `$FRAMEWORK_DIR/scripts/<name>`. The variable is
set by the `cc` wrapper at Buddy startup (`--add-dir $FRAMEWORK_DIR`,
default `~/projects/forge`).

**From the framework repo itself (CWD = forge/):**
`scripts/<name>` also works (CWD-relative). User docs in
`framework/getting-started.md` and `framework/milestone-execution.md`
deliberately use the shorter CWD-relative form because they are written
for someone who just cloned the framework repo.

**Buddy/skill/workflow instructions** (boot.md, save-WORKFLOW.md,
task_creation SKILL.md, spec_board SKILL.md, etc.): ALWAYS use
`$FRAMEWORK_DIR/scripts/<name>` — because they are loaded from
consumer-repo sessions.

## Script inventory

| Script | Purpose | Callers | Path (canonical) |
|--------|-------|----------|------------------|
| `plan_engine.py` | plan state + critical path + validate + boot output | Buddy boot, task_creation step 5, wakeup | `$FRAMEWORK_DIR/scripts/plan_engine.py` |
| `workflow_engine.py` | YAML-driven workflow state machine. Cross-session continuity. `--start` / `--next` / `--complete` / `--status` / `--recover` / `--boot-context` / `--handoff-context`. State persists in `.workflow-state/` (gitignored). Required for non-trivial workflows (operational.md §Workflow Engine). | Buddy boot (`--boot-context`), workflow-reminder hook (`--next --brief`), save workflow A.3 (`--handoff-context`), MUST be called at workflow start | `$FRAMEWORK_DIR/scripts/workflow_engine.py` |
| `git-status-check.sh` | parallel git fetch + status-sb for FRAMEWORK_DIR + active CWD. 5s network timeout. Output shows non-clean repos (ahead/behind). Prevents working on stale state in multi-machine workflows. | Buddy boot step 5 STATUS-CHECK | `$FRAMEWORK_DIR/scripts/git-status-check.sh` |
| `deploy-docs.sh` | mkdocs build + Hetzner sync for `docs/` | save step 10 (BACKGROUND), solve/spec_board/docs-rewrite/fix workflows | `$FRAMEWORK_DIR/scripts/deploy-docs.sh` |
| `deploy-dashboard-lite.sh` | dashboard regen + (env-configured) server rsync | save step 10 (dashboard variant), post-commit hooks | `$FRAMEWORK_DIR/scripts/deploy-dashboard-lite.sh` |
| `generate-dashboard.py` | dashboard HTML from plan.yaml + tasks (multi-repo) | called by deploy-dashboard-lite.sh | `$FRAMEWORK_DIR/scripts/generate-dashboard.py` |
| `generate-architecture.py` | architecture doc generator | docs-rewrite workflow | `$FRAMEWORK_DIR/scripts/generate-architecture.py` |
| `generate-control.py` | control-plane doc generator | docs-rewrite workflow | `$FRAMEWORK_DIR/scripts/generate-control.py` |
| `generate-status.py` | status report generator | manual, reports | `$FRAMEWORK_DIR/scripts/generate-status.py` |
| `generate_skill_map.py` | regenerates AUTO block in `framework/skill-map.md` from SKILL frontmatter | manual + after skill changes | `$FRAMEWORK_DIR/scripts/generate_skill_map.py` |
| `generate_navigation.py` | regenerates AUTO block in 8 navigation.md files | manual + after structure changes | `$FRAMEWORK_DIR/scripts/generate_navigation.py` |
| `skill_fm_validate.py` | pre-commit check 7 SKILL-FM-VALIDATE — frontmatter validator | git pre-commit hook | `$FRAMEWORK_DIR/scripts/skill_fm_validate.py` |
| `board-depth.py` | board-pass depth-mode resolver (Quick vs Deep, 4 checks) | spec_board skill | `$FRAMEWORK_DIR/scripts/board-depth.py` |
| `board-synthesize-input.py` | board-pass input synthesizer — extracts ALL findings from consolidated-passN.md | spec_board / code_review_board skills | `$FRAMEWORK_DIR/scripts/board-synthesize-input.py` |
| `install-dashboard-hooks.sh` | post-commit hook installer (symlinks per consumer repo) | manual, once per repo | `$FRAMEWORK_DIR/scripts/install-dashboard-hooks.sh` |
| `setup-cc.sh` | Claude Code adapter setup (cc launcher + path whitelist generation) | manual, once | `$FRAMEWORK_DIR/scripts/setup-cc.sh` |
| `setup-oc.sh` | OpenCode adapter setup (generate opencode.jsonc from .example) | manual, once | `$FRAMEWORK_DIR/scripts/setup-oc.sh` |

## Library

`$FRAMEWORK_DIR/scripts/lib/` holds helpers (`yaml_loader.py`, etc.).
Callers always reference `$FRAMEWORK_DIR/scripts/lib/<name>` from
consumer repos.

## Background

Scripts live under `$FRAMEWORK_DIR/scripts/` and are referenced by
consumer repos via that path.

If an agent (MCA, council-member, etc.) works in a consumer repo and sees
a script call in a skill/workflow without the `$FRAMEWORK_DIR` prefix:
**that's a drift bug**. Flag it in the next sweep or fix it directly.
