---
name: show-open-tasks
description: >
  Render a fast terminal overview of the OPEN tasks in a docs/tasks/
  tree (status not in a terminal set), grouped by priority and sorted
  by created date then effort. Script-less: the methodology below is
  run directly. Triggers when the user wants a task list/overview/
  status table ("liste aller tasks", "zeig offene tasks", "task
  overview"); NOT for changing task status (use task-status-update) or
  creating a task (use task-creation).
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

A read-only, at-a-glance overview of the open work in a project:
*what is still on the list, how urgent, how old, how big.* One
compact terminal table, **grouped by priority, sorted by created date
then effort** — no file-by-file hand-reading.

Project-neutral: works in any repo following the
`docs/tasks/NNN.yaml` convention. Read-only — never edits task files.
Status changes go through `task-status-update`; creation through
`task-creation`.

## Script-less

This skill carries **no `.py` script**. The procedure below is run
directly with standard shell tools. The data extraction is one shell
loop; the table is rendered from the resulting rows.

## Definition of "open"

Open = `status` NOT in the terminal set:
`done, wontfix, superseded, absorbed, obsolete, cancelled, canceled,
closed, moot`. Everything else (pending, in_progress, blocked, any
in-flight label) is open. Default tasks dir: `docs/tasks` (override
per the active project's docs routing).

## Priority normalization

`priority` is read tolerantly: first word, lowercased; alias map
`mid|med|normal → medium`, `hi → high`, `lo → low`; trailing notes
(e.g. `high (2026-05-18)`) stripped. Missing/unrecognized → `unknown`.

> SoT note: once Task 327 lands the canonical task-schema SoT, this
> normalization references that SoT instead of restating the alias
> map here (single source for `mid→medium`).

## Procedure

### 1. Extract one row per open task

```bash
TASKS=docs/tasks   # or the project's docs/tasks dir
for f in "$TASKS"/[0-9]*.yaml; do
  [ -e "$f" ] || continue
  id=$(basename "$f" .yaml)
  st=$(awk -F':[ ]*' '/^status:/{print tolower($2); exit}' "$f")
  case "$st" in
    done|wontfix|superseded|absorbed|obsolete|cancelled|canceled|closed|moot)
      continue;;
  esac
  pr=$(awk -F':[ ]*' '/^priority:/{print tolower($2); exit}' "$f")
  pr=${pr%%[ "]*}
  case "$pr" in
    mid|med|normal) pr=medium;; hi) pr=high;; lo) pr=low;;
    high|medium|low) ;; *) pr=unknown;;
  esac
  cr=$(awk -F':[ ]*' '/^created:/{gsub(/[ "'\''\r]/,"",$2);print $2; exit}' "$f")
  ef=$(awk -F':[ ]*' '/^effort:/{gsub(/[ "'\''\r]/,"",$2);print $2; exit}' "$f")
  ti=$(awk -F'title:[ ]*' '/^title:/{print $2; exit}' "$f" \
        | sed 's/^"//;s/"$//')
  printf '%s\t%s\t%s\t%s\t%s\t%s\n' \
    "${pr:-unknown}" "${cr:-—}" "${ef:-—}" "$id" "${st:-(unset)}" "$ti"
done
```

### 2. Group + sort

- **Group by priority**, group order: `high → medium → low →
  unknown`.
- **Within a group**, sort by `created` ascending (oldest first),
  tie-break by `effort` ascending with the order `S < M < L < XL`
  (unknown effort last).

### 3. Render

A compact box-drawing table (TTY aesthetic, `┌┬┐ │ ├┼┤ └┴┘`),
columns `ID │ STATUS │ CREATED │ EFFORT │ TITLE`, hard-truncated to
terminal width (never wraps). One **priority section per group** with
the priority as a section header (or a horizontal rule + label
between groups). Footer = open-task count + per-priority counts.

Keep it scannable: this is a fast glance, not a detail dump. Title
is the last column (absorbs remaining width).

### 4. Optional: last git change

When the user asks for the factual trail, add a `LAST CHANGE` column:
`git -C <repo> log -1 --date=short --format='%ad — %s' --
"$TASKS/$id.yaml" "$TASKS/$id.md"` (→ `uncommitted` if empty, `—` if
not in git). Off by default — it costs one git call per task.

## Boundaries

- Read-only. No status mutation, no file writes, no commits.
- Not a backlog renderer — reads task YAMLs, not `backlog.md`.
- Not a plan/critical-path tool — that is `plan_engine`. This skill
  is the fast human glance, deliberately decoupled from plan_engine.
- The YAML `updated:`/`created:` dates are the intended-state signal;
  the optional git line is the factual-trail signal.
