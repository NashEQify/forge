# Coordinated installation activation

Canonical shared source/update/install/recovery procedure of the OpenCode machine
installation (`full-ai-integration`, host `opencode`). Claude Code and Codex take
Forge through the plugin and its own update, not through this installer.

**Which machines this procedure governs.** On the user path, `git pull` in the
checkout is the update: each `oc` start runs `forge_install.py --refresh`,
which brings the installed entries to the checkout's commit. On a
`full-ai-integration` machine an install refuses, a refresh skips and readiness
fails while tracked non-Markdown sources have uncommitted changes. A
`full-ai-integration` installation takes the user path by default, including one made with an earlier
version. The procedure below governs a
machine whose setting records `maintenance: coordinated` (opt-in with
`--coordinated`, for changing Forge's own sources) and a checkout without a Git
commit. There, instruction-only changes take the light path below; everything else
uses stopped-session maintenance, not live switching of mutable framework sources.
Ordinary knowledge work still uses its existing folder and commands.

## Choosing the path

Classify each change before editing and state the classification in its brief,
decision or return record. Unclear whether a path is read directly or through an
installed copy or an engine → resolve the fact (`readlink`, the generator, the
installer inventory); still unclear → full path.

**Light path — instruction-only.** Every changed path is Markdown at an existing
owner that hosts read directly from the framework root: `framework/`, `skills/`,
`workflows/` runbook text, `agents/` (the plugin and the OpenCode installation
read it from the checkout), the root adapters `CLAUDE.md`
and `AGENTS.md`, `orchestrators/` rule text, and project docs. Steps: edit in the
framework root; when skill frontmatter or the skill inventory changes, regenerate
the derived wrappers (`scripts/generate_skill_wrappers.py`, then `--check`) and
the generated navigation; run the router check
(`scripts/generate_workflow_router.py --check`), the consistency check and the read-only
`scripts/forge_install.py --profile full-ai-integration --host opencode --check` (closure preflight; it also lists stale
installed copies); commit under the repository's commit rules. No prepare, journal operation, install or
fresh-session validation. Between operations the installer accepts drift of
recorded `.md` sources, lists it as `instruction_drift` in `--maintenance
status`, and the next `prepare` records it as the new baseline. Sessions read
the change on their next read; a session that already loaded a changed boot or
always-loaded file keeps the old text, so start a fresh session before relying
on such a change. Markdown that the closure or an engine reads as data is
not plain instruction text: the common-delivery directive and skill
frontmatter fields such as `status`, `invocation` and `evidence_layout` —
resolve the fact with `--check`; still unclear → full path. A new or changed
non-Markdown source next to the edit makes it a mixed change; the installer
then refuses until the full path runs.
Known limit: host- or editor-written non-Markdown files inside the source
roots (for example `.claude/settings.local.json` from a project-scoped
permission, a scheduler lock, editor swap files) count as unrecorded sources
too, so readiness refuses until the file is removed or a full-path operation
records it.

**Installed copies.** The plugin reads the checkout it was installed from; a
change reaches a plugin session through the plugin's own update. The OpenCode
installation (`full-ai-integration`, host `opencode`) links skills and roles to
the checkout; a light change to a role body or to skill frontmatter reaches
installed copies only through the next install (`--check` lists them); record
that host as not yet activated for it, or use the full path when OpenCode use
depends on it.

**Full path — everything else.** Scripts, hooks, launchers, host settings and
integrations, the installer, workflow definitions and compatibility mappings,
engine-read YAML/JSON, profiles and state formats, and every mixed change, use
the procedure below. Inside an operation the journal stays strict for every
recorded source, Markdown included, and rollback restores all of them.

## Full-path procedure

Once a change is classified as full path, before stopping sessions or changing source, and through prepare, install,
validation, retry and rollback: read and follow `framework/installation-activation-full-path.md` (§Before changing
source (full path), §One activation owner, §Install and verify, §Failure, retry and rollback).

## Owned boot blocks

The installer owns marker-delimited blocks (older installations left a
`FORGE-CODEX-BOOT` block in `AGENTS.md` / `AGENTS.override.md` and a
`FORGE-CLAUDE-BOOT` block in `~/.claude/CLAUDE.md`; they are only removed) through hash state
files and byte snapshots in the install plan. Continuity publication refuses the home copies under `.codex/` and
`.claude/` as reserved paths; a project `AGENTS.md` is a shared file that continuity
may write, and the block hash keeps install authority over a block (an edited
block refuses the next install). Text before and after a block, including Unicode
and CRLF line endings, survives create, replace and remove; removal returns the
outer text (keeping one line break where outer text without a final newline is
followed by text after the block), and a re-run with unchanged content plans no
change. Duplicate, reversed or partial markers, an edited owned block, an unowned
block with the same markers and non-UTF-8 content refuse without writes. A change
between plan and apply fails the preflight; the installer never retries over it.
Evidence: `scripts/managed_install.py` (`plan_block`, `plan_block_removal`,
`plan_text_block`),
`scripts/install_activation.py` (the production apply and its preflight) and
`tests/capabilities/test_owned_regions.py`.

## Consumer integration

Only authorized small reviewed changes remove duplicated general algorithms from
consumer rules. Keep concrete topic owners, storage, language, safety and approvals.
No automatic content reorganization or re-import belongs to the upgrade. Separately
authorized migrations preserve working-tree baselines, claim maps and usable routes.
A withheld/coordinate-before-access consumer must not be inspected until that boundary
is met; a synthetic fixture is not live acceptance. Keep each target's outcome distinct.
