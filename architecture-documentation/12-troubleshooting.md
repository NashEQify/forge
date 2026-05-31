# 12 — Troubleshooting

Known stumbling blocks and workarounds.

## Setup problems

### "claude: command not found"

The Claude Code CLI is not installed or not on `$PATH`. Install:
https://docs.anthropic.com/claude/docs/claude-code (or equivalent).

### "Unknown scope: <name>"

`cc` could not resolve the scope you passed. Built-in scope:
`framework` (alias `forge`). All other scopes resolve dynamically
under `$PROJECTS_DIR/<scope>/` (case-insensitive, requires
`intent.md`).

Solutions:
- Create an `intent.md` in the project, OR
- Use the exact directory name, OR
- `cd` into the project and run `cc` without a scope argument.

### "Ambiguous scope '<name>'"

Several directories under `$PROJECTS_DIR/` match the scope name
case-insensitively. `cc` lists all matches. Solution: use the exact
case-sensitive directory name.

### "WARNING: ~/.claude/agents points at X, not at the framework"

The symlink exists but points at a different path than expected
(`$FRAMEWORK_DIR/.claude/agents`). Typically means: an old setup
state.

Solution:
```bash
rm ~/.claude/agents
ln -s $FRAMEWORK_DIR/.claude/agents ~/.claude/agents
```

Same idea for `~/.claude/skills`.

### "WARNING: ~/.claude/agents is a real directory (not a symlink)"

You have a real directory there, probably from an early manual setup.
Back up the contents, then replace the directory with a symlink:
```bash
mv ~/.claude/agents ~/.claude/agents.bak
ln -s $FRAMEWORK_DIR/.claude/agents ~/.claude/agents
# Merge any mergeable content from ~/.claude/agents.bak into the framework repo
```

### `plan_engine.py: ERROR: PyYAML required`

PyYAML is missing. `plan_engine.py` itself attempts to switch to a
`.venv` if one is present:

```bash
python3 -m venv $FRAMEWORK_DIR/.venv
$FRAMEWORK_DIR/.venv/bin/pip install pyyaml
```

After that, `plan_engine.py` runs automatically under `.venv` (auto
relaunch).

## Hook problems

### A hook BLOCKs a write

The hook is doing what it should — check the block output. Typical
causes:

| Check | Block reason | Fix |
|---|---|---|
| `pre-commit` Check 1 (PLAN-VALIDATE) | `plan_engine.py --validate` reports errors | Run `python3 scripts/plan_engine.py --validate` locally and fix the errors |
| `pre-commit` Check 2 (CG-CONV, commit-msg) | Commit message format | Use conventional-commit form (`feat(scope): msg`) |
| `pre-commit` Check 3 (SKILL-FM-VALIDATE) | SKILL frontmatter incomplete or unknown invocation | Check the frontmatter against `framework/skill-anatomy.md` |
| `pre-commit` Check 5 (SOURCE-VERIFICATION) | Board/council review missing line-numbered evidence pointers | Add evidence pointers per `_protocols/evidence-pointer-schema.md` |
| (historical, removed 2026-05-31) `path-whitelist-guard` / `frozen-zone-guard` | Write outside whitelist / into frozen zones | Discipline only post-ADR-004: write within intent scope; corrections in frozen paths via `.correction.md` sidecar |

### Pre-commit hook BLOCKs with "PLAN-VALIDATE"

Tasks or plan have an inconsistency. Locally:

```bash
python3 $FRAMEWORK_DIR/scripts/plan_engine.py --validate
```

The output shows concrete errors — typically: blocked_by cycles,
missing spec_ref, invalid status values.

### Hook does not seem to fire

Check:
1. Is the hook registered in `~/.claude/settings.json` (user-global)?
   `jq '.hooks' ~/.claude/settings.json` should list it. If missing, the
   template was edited without re-running setup: `bash $FRAMEWORK_DIR/scripts/setup-cc.sh`.
2. Is the hook executable? (`chmod +x orchestrators/claude-code/hooks/<name>.sh`)
3. For claude-desktop / claude-web: verify the entrypoint gate inside the
   hook script doesn't `exit 0` early (some hooks intentionally fire only
   on specific `CLAUDE_CODE_ENTRYPOINT` values).
4. For git hooks: is the symlink at `.git/hooks/<name>` correct?

## Buddy problems

### "Buddy ignores a convention"

If Buddy systematically violates a convention:
1. Check whether the convention can be anchored mechanically (a hook).
   If yes: add a hook instead of repeating the prompt-text convention.
2. If only mentally anchorable: extend the Tier-1 operational rules
   (Buddy loads them at boot).

Convention drift in the prompt text is a well-known pattern and the
reason the framework leans so heavily on mechanical enforcement.

### Buddy starts without a greeting / without booting

The boot did not run. Check:
- Was Buddy initiated correctly (`cc framework` or `--agent buddy`)?
- Are `agents/buddy/{soul,operational,boot}.md` accessible?
- Under OpenCode: is `oc` running with the correct
  `OPENCODE_CONFIG_DIR`?

### Buddy writes to the wrong directory

Post-ADR-004 there is no mechanical hook for this; discipline replaces
the earlier `path-whitelist-guard`. If you see it happening: tell
Buddy directly that the write was out of scope; check whether
`intent.md` scope is unclear or the touched file's intent isn't
documented.

### Buddy runs a board without a plan-block

CLAUDE.md §3 violated. Fix: explicitly tell Buddy to "write a
plan-block first and then trigger the board". The earlier
`delegation-prompt-quality.sh` WARN hook was removed in ADR-004 —
discipline lives in `_protocols/plan-review.md`; if Buddy repeatedly
skips plan-blocks, the discipline is being internalized poorly and
needs explicit reinforcement.

## Skill / workflow problems

### Skill-FM-Validate BLOCKs a new skill

Mandatory fields are missing or `invocation.primary` has an unknown
value. Check:
- `name`: present, `lower_snake_case` or `kebab-case`
- `description`: present with a "Use when" trigger
- `status`: `active | draft | archived`
- `invocation.primary`: one of the 5 values (`user-facing |
  workflow-step | sub-skill | hook | cross-cutting`)
- `disable-model-invocation`: bool if present
- `modes`: list if present, otherwise omit

Detail: `framework/skill-anatomy.md §Frontmatter-Schema`.

### Skill over the 120-line token budget

Piebald budget exceeded. Typical fixes:
- Move detail to `REFERENCE.md` (the skill keeps a Buddy-facing
  checklist, REFERENCE holds the detail mechanics).
- Check for mode consolidation.
- Mega-skill test: if more than 50% of the content is disjoint per
  mode, split the skill.

### Workflow engine says "step not found"

The state file is out of sync with the runbook. Fix:
```bash
python3 scripts/workflow_engine.py --recover --id <wf-id>
```

OR check the state file manually under `docs/build|fix|review|solve/...`.

### `consistency_check` shows ERRORS

Structural drift. The output indicates concretely which check produced
which findings.

| Check | Typical cause | Fix |
|---|---|---|
| 1 (Dead refs) | Skill/workflow archived without stale-cleanup | `grep -rn <name>`, fix all refs |
| 2 (Orphan files) | Skill without a caller | Check whether legitimate or a real orphan |
| 3 (Adapter-SoT-Sync) | `agents/<name>.md` and `.claude/agents/<name>.md` diverge | Update the wrapper |
| 6 (Boot-map drift) | A skill on disk is not in `boot-navigation.md` | Add to `boot-navigation.md` |
| 8 (Navigation-layer drift) | Generator not run or manual section empty | `python3 scripts/generate_navigation.py` |

## Workflow-specific problems

### `save` hangs at "reconciliation"

Pre-write Group A Step 2 found unmatched status changes. The output
indicates which YAMLs. Solution:
```bash
git diff HEAD -- docs/tasks/*.yaml
```
Check whether the status change was legitimate. If yes: invoke the
`task_status_update` skill to set the status change cleanly. If no:
revert.

### `build` Phase Verify fails with code-review findings

The code-review-board produced findings. Buddy reads **only
chief-signal.md**. Fix:
- Work through HIGH/MAJOR findings systematically.
- On architectural conflict: consult solution-expert.
- On spec conflict: back to the spec (spec-engineering mantra).
- Re-review after the fix (`code_review_board L1` is usually enough).

### Sub-agent ESCALATED without a clear reason

Read the return summary, check the incident block. Typical causes:
- Spec was not clear enough → `spec_authoring` or spec update
- MUST constraints were missing in delegation → extend the gate file
- Architectural conflict → solution-expert

## General workarounds

### "I want to change a skill manually that lives in the AUTO block"

Wrong question. The AUTO block is regenerated from the frontmatter.
Fix:
- Change the skill frontmatter (`skills/<name>/SKILL.md`)
- Run `python3 scripts/generate_skill_map.py`
- Commit the diff.

### "I want to edit a frozen zone"

Mechanically blocked. If truly necessary:
- Corrections via `.correction.md` sidecar (a convention, not a file
  modification)
- Or an explicit user override (bypass the hook — rarely justified).

### "I want to disable a hook"

Typically means: you are working against the framework. The first
question is *"why does the hook bother me?"* — most of the time the
answer is that the hook is pointing out a real drift problem, not that
the hook is wrong.

If genuinely necessary (e.g. during a massive refactor): temporarily
edit `~/.claude/settings.json` (the user-global file `setup-cc.sh`
writes) to remove the offending hook entry, or comment out the entry
in `orchestrators/claude-code/settings.json.template` and re-run
`setup-cc.sh`. Either way: do not commit a template change that
disables hooks; restore before pushing.

### "git commit hangs"

The pre-commit hook is running, probably `plan_engine.py --validate`.
For large repos this can take a few seconds. If it hangs longer than
30s: check the hook output (run `.git/hooks/pre-commit` locally).

## Public-OSS adoption issues

As of May 2026, the framework is not fully public-OSS-ready. Known
issues:

### LICENSE missing

No LICENSE file in the repo. To be added for public-OSS status
(probably MIT, in line with the lift source `addyosmani/agent-skills`).

### Single-user defaults

Paths are hard-coded to `/home/xxx/projects/...`. On adoption these
need to be generalised per user:
- `.claude/path-whitelist.txt`
- `orchestrators/claude-code/bin/cc` (FRAMEWORK_DIR / PROJECTS_DIR
  defaults)
- `orchestrators/opencode/bin/oc` (OPENCODE_CONFIG_DIR default)

An env-var-driven generalisation would be the way.

### CI missing

Today no automated CI. Pre-commit hooks are the only gate. A GitHub
Actions workflow would make sense:
- Pre-commit checks
- Generator idempotency
- Lints
- TESTCASES.md smoke tests

### CONTRIBUTING.md / issue templates missing

For external contributions the setup would have to be extended:
- CONTRIBUTING.md with conventions (standard skill format, pre-commit,
  stale-cleanup)
- Issue templates
- PR template with a pre-commit-check list

### Cursor: harness parity

Post-ADR-004 (2026-05-31) the framework runs identically on every
supported harness. The earlier CC-Terminal-only PreToolUse /
PostToolUse / UserPromptSubmit hook layer was removed; only universally-
portable hooks remain (git pre-commit + SessionStart). Cursor no longer
needs a special "limitation" note — write-time discipline lives in
Buddy reasoning + protocols, identical to CC-Terminal. Full adapter
shape: [`07-tool-integrations.md`](07-tool-integrations.md) §Cursor.

## When nothing helps

1. `python3 $FRAMEWORK_DIR/scripts/plan_engine.py --validate` — check
   whether the framework itself is consistent.
2. Run `python3 $FRAMEWORK_DIR/scripts/generate_skill_map.py` and
   `python3 $FRAMEWORK_DIR/scripts/generate_navigation.py` — both must
   be idempotent (no diff).
3. Read the logs: `~/.claude/logs/...` (CC logs), repo `logs/` (hook
   logs).
4. Open an issue in the GitHub repo.

## When the framework is blocking you

The 5 pre-commit checks (PLAN-VALIDATE, CG-CONV, SKILL-FM-VALIDATE,
SECRET-SCAN, SOURCE-VERIFICATION) exist to catch schema + format
drift before it ships. If you are pushing back against a BLOCK:
re-examine the assumption that you are really on the right path. Most
of the time the conflict is in a drift in your mental model of the
repo, not in the framework.

But: if there is a genuine bug in the framework — a hook BLOCKs
something it should not, a generator is not idempotent, a convention
is contradictory — document it transparently (an issue, an ADR via
`documentation_and_adrs/SKILL.md`). The public-OSS quality bar is
honest drift labelling, not drift hiding.

## Next step

Daily-use methodology + commands:
[`13-operational-handbook.md`](13-operational-handbook.md).
