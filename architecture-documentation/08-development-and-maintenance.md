# 08 — Development + Maintenance

How the framework itself is developed and maintained.

## Repo-internal workflows

`docs/plan.yaml` defines the programme:
- **north_star:** opinionated workflows + codified discipline patterns as a
  Skill + Discipline Layer; mechanical prevention is Claude-Code-coupled,
  methodology + state engine are standards-portable
- **operational_intent:** the active workstream pulling toward the north star
- **Phases:** Foundation, Harness Refactor, Deferred
- **Milestones:** dev-infra, reliable-execution, tier2-harness, opencode-compat,
  cc-patterns-advanced, context-assembly, deferred

Tasks under `docs/tasks/<id>.{md,yaml}`. Self-contained format
(`framework/task-format.md` SoT).

## Engines

### plan_engine.py (~3.6k LoC)

`scripts/plan_engine.py` — computed planning layer.

```bash
python3 scripts/plan_engine.py --boot          # session boot state
python3 scripts/plan_engine.py --status        # current state
python3 scripts/plan_engine.py --next [-l N]   # follow-up tasks
python3 scripts/plan_engine.py --critical-path # critical path
python3 scripts/plan_engine.py --check [MS]    # milestone check
python3 scripts/plan_engine.py --validate      # pre-commit gate
python3 scripts/plan_engine.py --after TASK    # after task X
python3 scripts/plan_engine.py --dashboard-json # dashboard feed
```

Reads `docs/tasks/*.yaml` + `docs/plan.yaml`, builds DAGs, computes
milestone status, critical path, next actions.

**Pre-commit integration:** `--validate` must show 0 errors, otherwise
BLOCK (pre-commit Check 1).

**Auto-venv:** when the PyYAML library is missing and a `.venv` is
present, the script restarts itself under `.venv/bin/python3` (PEP-668
bypass).

### workflow_engine.py (~2.5k LoC)

`scripts/workflow_engine.py` — YAML-driven workflow orchestration.

```bash
python3 scripts/workflow_engine.py --start <workflow> [--task <id>]
python3 scripts/workflow_engine.py --next [--id <wf-id>]
python3 scripts/workflow_engine.py --complete <step-id> [--route <key>] [--evidence <text>]
python3 scripts/workflow_engine.py --skip <step-id> --reason "<text>"
python3 scripts/workflow_engine.py --status [--id <wf-id>]
python3 scripts/workflow_engine.py --validate [--before-commit]
python3 scripts/workflow_engine.py --recover [--id <wf-id>]
python3 scripts/workflow_engine.py --abort <wf-id> --reason "<text>"
python3 scripts/workflow_engine.py --pause [--id <wf-id>]
python3 scripts/workflow_engine.py --resume [--id <wf-id>]
python3 scripts/workflow_engine.py --handoff-context  # save workflow group A
python3 scripts/workflow_engine.py --boot-context     # boot resume
python3 scripts/workflow_engine.py --find --task <id>
python3 scripts/workflow_engine.py --guard <guard> [<task-id>]
```

Encapsulates workflow definitions (`workflows/runbooks/*/WORKFLOW.md`)
with state-file tracking.

## Generators (Drift pattern Gen+Validator)

### generate_skill_map.py

Reads all SKILL frontmatter under `skills/*/SKILL.md`. Writes the AUTO
block in `framework/skill-map.md`:

```
<!-- SKILL-MAP-AUTO-START -->
### Direct-Invokable Capabilities (`invocation.primary: user-facing`)
<list>
### Workflow-Step / Sub-skill (`workflow-step` | `sub-skill`)
<list>
...
<!-- SKILL-MAP-AUTO-END -->
```

Idempotent. Validator: `consistency_check` Check 6 (boot-map drift).

### generate_navigation.py

Regenerates the AUTO block in 8 navigation.md files under the top-level
3-cap. Targets are hard-coded in the `TARGETS` constant.

```bash
python3 scripts/generate_navigation.py
# → "generate_navigation: all up to date" or list of updated files
```

Validator: `consistency_check` Check 8 (navigation-layer drift). Three
sub-checks:
- A: existence (all targets exist, no disk drift)
- B: AUTO-block sync (idempotency: no diff on second run)
- C: manual-section filled (no placeholder text remaining)

### skill_fm_validate.py

Pre-commit Check 7. Validates the frontmatter of all active SKILL.md files:

| Check | Severity |
|---|---|
| YAML validity | BLOCK |
| Required fields present (`name`, `description`, `status`, `invocation.primary`) | BLOCK for modified/added |
| `invocation.primary` in vocabulary | BLOCK |
| `invocation.secondary` list format / element vocabulary | WARN on unknown element |
| `disable-model-invocation` bool | BLOCK on non-bool |
| `modes` list format | BLOCK on non-list |
| max 3 modes | WARN |
| `relevant_for` list format | BLOCK on non-list |
| `relevant_for` references unknown agent | WARN |

Skip on repos without `skills/` (graceful degradation for consumers).

### generate_agent_skill_map.py

Generator + validator for agent-skill awareness (pre-commit Check 10).

```bash
python3 scripts/generate_agent_skill_map.py            # write
python3 scripts/generate_agent_skill_map.py --check    # exit 1 on drift
python3 scripts/generate_agent_skill_map.py --agent main-code-agent
```

Reads `relevant_for: [agents]` from each `skills/*/SKILL.md`. Writes the
AUTO block between markers in opt-in `agents/<name>.md` (markers:
`<!-- AGENT-SKILLS-AUTO-START -->` / `<!-- AGENT-SKILLS-AUTO-END -->`).
Plus aggregated `framework/agent-skill-map.md` as a reverse lookup.

Wildcard skills (`relevant_for: ["*"]`) are injected into every opt-in
agent. Unknown-agent refs → WARN. Path stability: uses the directory
name (underscored), not the `name` field (which can be hyphenated).

### validate_runbook_consistency.py

Pre-commit Check 9. Heuristic check workflow.yaml ↔ WORKFLOW.md:
paired existence, derived_from format (`WORKFLOW.md@YYYY-MM-DD`),
step-name keyword presence in md, phase-comment parity.

```bash
python3 scripts/validate_runbook_consistency.py            # all
python3 scripts/validate_runbook_consistency.py --staged   # pre-commit mode
python3 scripts/validate_runbook_consistency.py --runbook build
```

WARN-only — drift is heuristic (not every yaml step has to appear in md).

## Hooks

`orchestrators/claude-code/hooks/`:

```
delegation-prompt-quality.sh   ~170 LoC  PreToolUse(Task) WARN (length + keyword + MCA-Brief decision classes)
frozen-zone-guard.sh           171 LoC  PreToolUse BLOCK
path-whitelist-guard.sh        203 LoC  PreToolUse BLOCK
post-commit-dashboard.sh        85 LoC  git post-commit
pre-commit.sh                  ~400 LoC  git pre-commit, 12 checks (3 BLOCK + 9 WARN)
state-write-block.sh            25 LoC  PreToolUse, state-file protection (.workflow-state/)
workflow-commit-gate.sh         68 LoC  git pre-commit, workflow state
workflow-reminder.sh            ~70 LoC  UserPromptSubmit, additionalContext inject (timeout 2s, 200-char cap)
mca-return-stop-condition.sh   ~150 LoC  PostToolUse(Task) WARN on MCA-return stop-condition keywords
board-output-check.sh          ~135 LoC  PostToolUse(Task) WARN on missing expected file output
```

Total ~1210 LoC bash. Each hook is self-contained with:
- Header doc block
- Spec reference
- Exit-code convention
- Standalone test mode

### Hook tests

`tests/hooks/`:
- `test-delegation-prompt-quality.sh`
- `test-persist-gate.sh`
- `test-stale-cleanup.sh`

Manual smoke testing. Run:
```bash
bash tests/hooks/test-<name>.sh
```

### Hook care

Add a hook:
1. Write `orchestrators/claude-code/hooks/<name>.sh` (header doc mandatory)
2. Register in `.claude/settings.json` (matching lifecycle event)
3. Test in `tests/hooks/test-<name>.sh`
4. Doc update in `CLAUDE.md §Active Hooks` and `02-architecture.md` table

Remove a hook:
1. Stale cleanup (CLAUDE.md §5): clean up all refs in one commit
2. Remove from `.claude/settings.json`
3. Delete the hook file
4. Delete the test file
5. Doc update

## Conventions

### Commit format (CG-CONV, pre-commit Check 4)

Conventional-Commits format. Examples:

```
feat(framework): close 366 D.5 navigation-layer-re-introduction
fix(scripts): explicit utf-8 encoding for cross-platform (Windows)
chore(save): session 2026-04-28 — phase F.1 spec-board pass 1 needs-work
docs(framework): boot-navigation entry for new skill X
refactor(agents): consolidate code-quality + code-architecture + code-performance
```

Allowed types: `feat`, `fix`, `chore`, `docs`, `refactor`, `test`, `style`,
`perf`, `revert`.

The pre-commit hook BLOCKS on the wrong form.

### Path whitelist + frozen zones

`.claude/path-whitelist.txt` and `.claude/frozen-zones.txt` are the SoT.
Changes there are structural — `consistency_check` Check 5 verifies
refactoring checklists.

### Skill anatomy (v2)

Every new SKILL.md follows `framework/skill-anatomy.md`:
- Frontmatter with required fields
- 7 mandatory sections + 2 optional
- `Standalone` block on new skills (mandatory)
- Token budget ≤120 lines (Single-Class v2)
- Naming: `verb_object` default

Pre-commit Check 7 (BLOCK) catches structural frontmatter drift; spec-board
L1 catches content drift (process quality, standalone, naming).

### Persona format

`agents/<name>.md` (SoT) + wrapper under `.claude/agents/<name>.md`. Persona
token budget ≤70 lines. Detail in `skills/_protocols/piebald-budget.md`.

### Workflow format

`workflows/runbooks/<name>/WORKFLOW.md`. Producer class has 5 phases.
Token budget ≤150 lines. Per phase: skills, input, output, gate, failure,
autonomy, protocols.

### Protocol format

Skill-level (`skills/_protocols/`) and persona-level (`agents/_protocols/`).
Self-contained, with a clearly referenced "Loaded by:" list.

## Tests

### TESTCASES.md

`tests/TESTCASES.md` contains T01-Tnn patterns for Buddy behaviour:
- T01: boot in BuddyAI (intent.md in WD)
- T02-Tnn: boot variations, intent detection, delegation routing, etc.

Manual walkthrough — Buddy guides through it.

### Hook smoke tests

```bash
bash tests/hooks/test-delegation-prompt-quality.sh
bash tests/hooks/test-persist-gate.sh
bash tests/hooks/test-stale-cleanup.sh
```

### Generator idempotency (effectively a self-test)

```bash
python3 scripts/generate_skill_map.py
python3 scripts/generate_navigation.py
git diff --name-only -- ':(glob)**/navigation.md'
git diff --name-only -- 'framework/skill-map.md'
# Both empty = idempotent
```

### Lints

```bash
ruff check .
mypy scripts/
```

`skills/python_code_quality_enforcement/SKILL.md` records the conventions
(ruff config, mypy strictness, naming patterns).

### CI

Currently **no automated CI**. Lifecycle is primarily pre-commit. Adding
a GitHub Actions workflow would be sensible (running pre-commit checks +
generator idempotency + lints in CI).

## Maintenance routines

### context_housekeeping (workflow)

`workflows/runbooks/context_housekeeping/WORKFLOW.md` — periodic
maintenance of the context system.

Trigger: user imperative "context cleanup", or a drift suspicion.

Phases:
1. Inventory + drift detection (`consistency_check` several checks)
2. Cleanup + consolidation

### Audit triggers

On every structural change check:
- Adapter sync (Check 3)
- Boot-map drift (Check 6)
- Navigation drift (Check 8)
- Stale refs (Check 1)
- Refactoring checklists (Check 5)

Detail: `skills/consistency_check/REFERENCE.md`.

### Skill migration v1 → v2

Migration corridor:
- Phase 1 hot skills (6 of them) immediately
- Phase 2 on-touch (8 weeks)
- Phase 3 cut-off bulk (remaining)

As of May 2026 effectively all active skills are on v2. New skills MUST
go directly to v2 (pre-commit Check 7 BLOCK).

### Persona migration / consolidation

For persona consolidation (multi-axis hybrid):
1. Document council decision or user mandate
2. Extend the target persona (multi-axis or mode)
3. Delete the old persona file (git history is the archive)
4. Stale cleanup in the same commit (all refs)
5. Update adapter wrappers (`.claude/agents/`)

Detail: `framework/skill-anatomy.md` §Consolidation mechanics.

## Release / versioning

Currently **no formal version scheme**. Tags are operations markers:

| Tag | Meaning |
|---|---|
| `frozen-zone-verified` | Last successful `consistency_check` run (frozen zones intact) |

If needed semver could be introduced (e.g. after larger refactor waves). A
big consolidation phase would be a logical v0.x → v1.0 trigger but it has
not been tagged that way.

## Contribution notes

Today this is more of a single-user project. For external contributions
the following would need clarifying:
- Add a LICENSE file (probably MIT)
- CONTRIBUTING.md with conventions (standard skill format, pre-commit hook, stale
  cleanup, frozen zones)
- Add CI pipeline
- Issue templates
- PR template with pre-commit-check list

Until then: the pre-commit hook is the primary quality gate.

## Next step

Audience-specific guides: [`09-agent-guide.md`](09-agent-guide.md) and
[`10-human-guide.md`](10-human-guide.md).
