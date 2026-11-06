# Framework scripts — path table + caller convention

Central overview of executable scripts under `$FRAMEWORK_DIR/scripts/`.

## Convention

**From consumer repos:**
always call scripts as `$FRAMEWORK_DIR/scripts/<name>`. The variable is
set by the `oc` wrapper at Buddy startup (`--add-dir $FRAMEWORK_DIR`,
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
| `workflow_engine.py` | Development workflow state machine; explicit selected runs only. Common save and boot do not enumerate engine state. | Selected development caller through `development_continuation.py` | `$FRAMEWORK_DIR/scripts/workflow_engine.py` |
| `git-status-check.sh` | parallel git fetch + porcelain v1 branch status (untranslated labels) for FRAMEWORK_DIR + active CWD. 5s network timeout. Output shows non-clean repos: ahead/behind, uncommitted entry counts and, for the framework checkout, installed sources not committed in `HEAD` and a non-ready installer phase (from installer status). Prevents working on stale state in multi-machine workflows and leaving held-back work unnoticed. | Buddy boot step 2 STATUS-CHECK | `$FRAMEWORK_DIR/scripts/git-status-check.sh` |
| `select_tests.py` | static selector: maps changed paths to the pytest files that exercise them, or answers `broad`; read-only, stdlib only | testing skill §Test selection in `skills/testing/run-strategy.md` (implementation, fix, review, verification rounds), run from the project root | `$FRAMEWORK_DIR/scripts/select_tests.py` |
| `deploy-docs.sh` | mkdocs build + server sync for `docs/` | solve/spec_board/docs-rewrite/fix workflows | `$FRAMEWORK_DIR/scripts/deploy-docs.sh` |
| `generate-architecture.py` | architecture doc generator | docs-rewrite workflow | `$FRAMEWORK_DIR/scripts/generate-architecture.py` |
| `generate-control.py` | control-plane doc generator | docs-rewrite workflow | `$FRAMEWORK_DIR/scripts/generate-control.py` |
| `generate-status.py` | status report generator | manual, reports | `$FRAMEWORK_DIR/scripts/generate-status.py` |
| `generate_skill_map.py` | regenerates AUTO block in `framework/skill-map.md` from SKILL frontmatter | manual + after skill changes | `$FRAMEWORK_DIR/scripts/generate_skill_map.py` |
| `generate_navigation.py` | regenerates AUTO block in 8 navigation.md files | manual + after structure changes | `$FRAMEWORK_DIR/scripts/generate_navigation.py` |
| `skill_fm_validate.py` | Skill frontmatter validation with supported working-tree CLI behavior and explicitly selected indexed hook evaluation; see `enforcement-registry.md` §Indexed standalone input contract. | git pre-commit hook | `$FRAMEWORK_DIR/scripts/skill_fm_validate.py` |
| `board-depth.py` | board-pass depth-mode resolver (Quick vs Deep, 4 checks) | spec_board skill | `$FRAMEWORK_DIR/scripts/board-depth.py` |
| `board-synthesize-input.py` | board-pass input synthesizer — extracts ALL findings from consolidated-passN.md | spec_board / code_review_board skills | `$FRAMEWORK_DIR/scripts/board-synthesize-input.py` |
| `setup-oc.sh` | OpenCode machine install: forwards its arguments to `forge_install.py --profile full-ai-integration --host opencode` | manual | `$FRAMEWORK_DIR/scripts/setup-oc.sh` |

## Library

`$FRAMEWORK_DIR/scripts/lib/` holds helpers (`yaml_loader.py`, etc.).
Callers always reference `$FRAMEWORK_DIR/scripts/lib/<name>` from
consumer repos.

Standalone indexed checks share the bounded candidate-data adapter described in `enforcement-registry.md` §Indexed standalone input contract. It supplies captured membership and blob data, without executing candidate code or implying indexed plan/evidence validation.

## Background

Scripts live under `$FRAMEWORK_DIR/scripts/` and are referenced by
consumer repos via that path.

If an agent (MCA, council-member, etc.) works in a consumer repo and sees
a script call in a skill/workflow without the `$FRAMEWORK_DIR` prefix:
**that's a drift bug**. Flag it in the next sweep or fix it directly.

## Shared continuity and installation

| Script | Public responsibility | Contract |
|---|---|---|
| `continuity.py` | Scoped coherent snapshots and protected semantic publication/recovery | [Continuity](continuity.md) |
| `development_continuation.py` | Explicit development bindings exported into common handoffs | [Development continuation](development-continuation.md) |
| `forge_install.py` | The OpenCode-only machine installer: `--profile full-ai-integration --host opencode`; `--check`, `--remove`, `--refresh` (Claude Code and Codex use the plugin) | [Installation](../architecture-documentation/05-installation.md) |
| `install_activation.py` | Installation mutation exclusion and durable recovery | [Installation activation](installation-activation.md) |
| `forge_install.py --maintenance …` | Public prepare/status/retry/rollback/validate entry of the machine installation | [Installation activation](installation-activation.md) |
