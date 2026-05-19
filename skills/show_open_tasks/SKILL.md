---
name: show-open-tasks
description: >
  Render an overview table of the OPEN tasks in a docs/tasks/ tree
  (status not in a terminal set). Each row shows the task intent
  (title + summary first sentence), status, the YAML updated date, and
  the last git change (date + commit subject) that touched the task
  files. Triggers when the user wants a task list/overview/status table
  ("liste aller tasks", "zeig offene tasks", "task overview"); NOT for
  changing task status (use task-status-update) or creating a task
  (use task-creation).
status: active
relevant_for: ["buddy"]
invocation:
  primary: user-facing
  secondary: [orchestrator]
disable-model-invocation: false
uses: []
---

# Skill: show-open-tasks

## Purpose

A read-only overview of the open work in a project. Answers "what is
still on the list and when did each item last move" in one table,
without the orchestrator hand-reading every task file.

Project-neutral: works in any repo that follows the
`docs/tasks/NNN.yaml` convention.

## Who runs it

Buddy (as orchestrator), directly. Read-only — it never edits task
files. Status changes go through `task-status-update`; creation goes
through `task-creation`.

## Definition of "open"

Open = `status` NOT in the terminal set:
`done, wontfix, superseded, absorbed, obsolete, cancelled, closed,
moot`. Everything else (pending, in_progress, blocked, and any
non-standard in-flight label such as `spec-draft-pass2`) is open.
Pass `--all` to include terminal tasks too.

## Input

| Parameter | Required | Default | Description |
|-----------|----------|---------|-------------|
| `--tasks-dir` | no | `docs/tasks` | Directory of `NNN.yaml` task files. |
| `--repo` | no | git-toplevel of tasks-dir | Repo root for the git-log lookup. |
| `--all` | no | off | Include terminal (done/wontfix/…) tasks. |
| `--format` | no | `term` | `term` (aligned, terminal-readable, default), `md` (table + intent + git column), or `csv`. |

Field-name tolerance: `summary` or `objective` or `intent_chain.action`
for the intent text; `updated` or `created` for the date; files named
`<digits>.yaml` only (review-artefact yamls like `020-review-*` are
skipped).

## Output

Sorted in_progress → blocked → pending → other, then by numeric id.

**`term` (default)** — box-drawing ASCII table (`┌┬┐ │ ├┼┤ └┴┘`),
columns `ID │ STATUS │ PRIO │ UPDATED │ TITLE`, hard-truncated to the
terminal width (never wraps — readable in a TTY). Sorted status →
priority (high→medium→low→unknown) → id, with a horizontal rule
between status groups. Footer = open-task count. Priority is read
tolerantly (`priority`|`prio`, alias `mid`→`medium`, trailing notes
stripped); a task whose YAML has no priority field shows `—`.

**`md`** — full Markdown table for detail/handoff:
`| ID | Status | Intent | Updated | Last change (git) |`
- **Intent** = `**title**` + first sentence of the summary/objective.
- **Updated** = the YAML `updated:` date (falls back to `created:`).
- **Last change (git)** = `YYYY-MM-DD — <commit subject>` of the last
  commit touching `NNN.yaml`/`NNN.md` (`uncommitted` if not yet
  committed; `—` if not in git).

**`csv`** — machine-readable export (all six fields).

## Run

```bash
python3 skills/show_open_tasks/show_open_tasks.py \
  --tasks-dir <project>/docs/tasks
```

PyYAML is used when available; otherwise a built-in flat-key parser
(handles the scalar fields + `>`/`|` folded blocks this tool reads)
is the fallback, so the skill has no hard dependency.

## Boundaries

- Read-only. No status mutation, no file writes, no commits.
- Not a backlog renderer — it reads task YAMLs, not `backlog.md`.
- "Last change (git)" reflects file-touch history, not semantic task
  progress; the YAML `updated:` date is the intended-state signal,
  the git line is the factual-trail signal. Both are shown on purpose.
