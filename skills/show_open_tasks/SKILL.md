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

Open = `status` NOT in the terminal set. Per the schema SoT
(`framework/task-schema.yaml` → `terminal_status`): terminal =
`done, superseded, wontfix, absorbed`. Everything else (`pending,
in_progress, blocked`, any unknown/in-flight label) is **open** —
unknown values are read tolerantly as open, never silently terminal.
Default tasks dir: `docs/tasks` (override per the active project's
docs routing).

## Priority normalization

`priority` is read tolerantly per the schema SoT
(`framework/task-schema.yaml` → `fields.priority.read_aliases`): first
word, lowercased; the alias map (`mid|med|normal → medium`,
`hi → high`, `lo → low`) is **defined there, not here** — this skill
applies it, the schema owns it. Trailing notes (e.g.
`high (2026-05-18)`) stripped. Missing/unrecognized → `unknown`.

## Procedure

One self-contained pipeline. `TASKS` = the active project's tasks dir
(per docs routing — e.g. `docs/tasks`, or an absolute path). Run it
verbatim; it is quote-safe (no awk single-quote traps) and tested.

```bash
TASKS=docs/tasks   # or an absolute path to the project's docs/tasks
for f in "$TASKS"/[0-9]*.yaml; do
  [ -e "$f" ] || continue
  id=$(basename "$f" .yaml)
  case "$id" in *[!0-9]*) continue;; esac          # pure-numeric task files only
  val() { v=$(sed -n "s/^$1:[[:space:]]*//p" "$f" | head -1); \
          v=${v%$'\r'}; v=${v#[\"\']}; v=${v%[\"\']}; printf '%s' "$v"; }
  st=$(val status | tr '[:upper:]' '[:lower:]')
  case "$st" in done|superseded|wontfix|absorbed) continue;; esac   # schema terminal_status
  pr=$(val priority | tr '[:upper:]' '[:lower:]'); pr=${pr%% *}
  case "$pr" in mid|med|normal) pr=medium;; hi) pr=high;; lo) pr=low;; high|medium|low) ;; *) pr=unknown;; esac
  case "$pr" in high) pk=0;; medium) pk=1;; low) pk=2;; *) pk=3;; esac
  ef=$(val effort); case "$ef" in S) ek=0;; M) ek=1;; L) ek=2;; XL) ek=3;; *) ek=9;; esac
  cr=$(val created); ti=$(val title)
  printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n' \
    "$pk" "${cr:-9999-99-99}" "$ek" "$pr" "$id" "${ef:-?}" "${st:-?}" "$ti"
done | sort -t$'\t' -k1,1n -k2,2 -k3,3n | awk -F'\t' '
  $4!=g{g=$4; printf "\n━━ %s ━━\n",toupper(g)}
  {n++; t=$8; if(length(t)>60)t=substr(t,1,59)"…";
   printf "  %-5s %-3s %-10s %-11s %s\n",$5,$6,$2,$7,t}
  END{printf "\n%d open\n",n}'
```

**What it does, by stage:**

1. **Extract** — per pure-numeric task YAML, read `status`,
   `priority`, `effort`, `created`, `title` with a quote-safe `val()`
   helper (strips one layer of surrounding `"`/`'` + `\r`). Terminal
   statuses skipped. `priority` normalized per the rules above; a
   sort-key triple is emitted: priority-rank · `created` ·
   effort-rank (`S<M<L<XL`, unknown last).
2. **Sort** — `sort` on priority-rank, then `created` ascending,
   then effort-rank.
3. **Render** — `awk` prints a `━━ PRIORITY ━━` header at each group
   boundary, then `ID  EFFORT  CREATED  STATUS  TITLE` (title clipped
   to 60). Footer = open count.

Adjust column widths/clip length to taste; the pipeline is the
contract, the awk formatting is cosmetic. Keep it scannable — this
is a fast glance, not a detail dump.

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
