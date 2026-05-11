# Contributing to forge

Thanks for your interest. This repo is a personal OSS reference — primary
maintainer is one person, and the methodology is opinionated by design.
Contributions are welcome but expect direct, blunt feedback.

## Before you open an issue

1. **Read** [`architecture-documentation/`](architecture-documentation/) —
   especially `01-overview.md`, `04-core-concepts.md`, and `09-agent-guide.md`.
   Many "issues" are working-as-designed once the discipline model is clear.
2. **Search existing issues** — including closed.
3. **Distinguish bug vs. preference** — opinionated design choices (Single-
   Class skills, Pre-Delegation Non-Negotiable, Buddy=Dispatcher rule for
   boards) are not bugs. They're the methodology. Disagreement is fine but
   the bar for changing them is high.

## Bug reports

Include:
- Repro steps (exact commands)
- Expected vs. actual behavior
- Adapter (Claude Code / OpenCode / Cursor) + version
- `python3 scripts/plan_engine.py --validate` output if relevant
- `git log --oneline -5` so we know the state

## PRs

### Before coding

- For non-trivial changes: open an issue first to discuss scope.
- Read [`architecture-documentation/04-core-concepts.md`](architecture-documentation/04-core-concepts.md)
  §Single-Class Skill-Modell if you're touching skills.
- Read [`framework/skill-anatomy.md`](framework/skill-anatomy.md) if you're
  adding a new skill (mandatory: 7 sections, frontmatter, "Use when",
  standalone-justification block for new skills).

### Coding conventions

- **Anatomy v2** for new skills. Pre-commit Check 7 (`SKILL-FM-VALIDATE`,
  BLOCK) enforces frontmatter.
- **Stale-Cleanup** in same commit when archiving/replacing artifacts
  (CLAUDE.md §5). Pre-commit Check 5 (WARN) flags marker-without-cleanup.
- **No raw-edit on task-YAMLs** — status/readiness via `task_status_update`
  skill. Pre-commit Check 2 (WARN) flags raw edits.
- **Conventional Commits**. Pre-commit Check 4 (CG-CONV, BLOCK) enforces
  format: `<type>(<scope>): <message>`. Types: feat | fix | chore | docs |
  refactor | test | style | perf | revert.
- **Generators idempotent.** If your change touches `skills/` or
  navigation-relevant paths, re-run:
  ```bash
  python3 scripts/generate_skill_map.py
  python3 scripts/generate_navigation.py
  ```
  and commit the diff (or verify no diff).

### Pre-commit hook

Install before working on this repo:
```bash
ln -sf "$(pwd)/orchestrators/claude-code/hooks/pre-commit.sh" .git/hooks/pre-commit
```

(Yes, `claude-code/hooks/` — the hook itself is harness-agnostic.)

12 checks (3 BLOCK + 9 WARN): PLAN-VALIDATE (BLOCK) · TASK-SYNC (WARN) ·
OBLIGATIONS (WARN) · CG-CONV (BLOCK) · STALE-CLEANUP (WARN) · PERSIST-GATE
(WARN) · SKILL-FM-VALIDATE (BLOCK) · ENGINE-USE (WARN) · RUNBOOK-DRIFT
(WARN) · AGENT-SKILL-DRIFT (WARN) · SECRET-SCAN (WARN) · SOURCE-VERIFICATION
(WARN).

Don't `--no-verify`. If a hook blocks, fix the underlying issue.

### Tests

- Hook smoketests: `bash tests/hooks/test-<name>.sh`
- TESTCASES.md walkthrough: manually verify the affected T01-Tnn cases
- Lints: `ruff check . && mypy scripts/`

### Regenerate AUTO-block indices

When you add, rename, or change `invocation` on a skill, regenerate the
indices (the AUTO blocks are checked by pre-commit `RUNBOOK-DRIFT` and
`AGENT-SKILL-DRIFT`):

```bash
python3 scripts/generate_skill_map.py        # framework/skill-map.md
python3 scripts/generate_navigation.py       # 8 navigation.md files
python3 scripts/generate_agent_skill_map.py  # framework/agent-skill-map.md + per-agent AUTO blocks
```

No automated CI today. Pre-commit-hook is the primary quality gate.

### PR description template

```
## What
<one paragraph>

## Why
<intent / problem solved>

## Affected files
- <file>: <change>

## Pre-commit checks
- [ ] PLAN-VALIDATE pass
- [ ] CG-CONV pass
- [ ] SKILL-FM-VALIDATE pass (if skills touched)
- [ ] generators idempotent

## Open questions / risks
<...>
```

## What we don't accept

- **PRs that delete frozen zones** (`context/history/**`) without explicit
  user mandate.
- **PRs that disable hooks** (`--no-verify`, hook deletion) without
  replacement.
- **PRs that add new skill classes** beyond the Single-Class model. The
  `invocation.primary` axis is the variance dimension. New axes would
  require Architecture-Council re-decision.
- **Marketplace-style additions** — generic agent skills not specifically
  needed by this framework's stated objectives. We do punctual lifts from
  upstream (Addy, Pocock) when a standalone-justification holds.
- **Refactors that re-introduce hardcoded user paths**. Auto-detect via
  `dirname` or env-var-with-no-default is the pattern.

## Dev setup

See [`architecture-documentation/05-installation.md`](architecture-documentation/05-installation.md).
Quickstart:

```bash
git clone https://github.com/NashEQify/forge ~/projects/forge
cd ~/projects/forge
python3 -m venv .venv && .venv/bin/pip install pyyaml
bash scripts/setup-cc.sh   # Claude Code adapter + path-whitelist
bash scripts/setup-oc.sh   # OpenCode adapter (optional)
ln -sf "$(pwd)/orchestrators/claude-code/hooks/pre-commit.sh" .git/hooks/pre-commit
```

## License

By contributing you agree your work is licensed under MIT (see [LICENSE](LICENSE)).
