# Buddy — Boot routing: intent and context

Step-loaded unit of `agents/buddy/boot.md`. Read it at RESOLVE (which intent is
active) and ROUTE (read and write paths), and whenever you choose where to write
context, the session handoff or a user-scope fact.

## Routing

Input: working directory. Output: active intent + mode.

1. The boot probe's `intent:` line names the nearest `intent.md`,
   walking up from the CWD to `/` (a filesystem check; do NOT infer from
   the context window).
2. A path → that's the active intent. Mode comes from the Context
   field (first sentence). Read with `cat` if not already in context.
3. `none` → "No intent. New project? Should I create an
   intent.md?"
   Format: `framework/intent-tree.md`, section "intent.md format". The
   intent.md is the load-bearing input for all later intent-driven work
   (`framework/invariants.md` §Intent-driven) — state the goal as **extractable facts**, not
   only argued, so agents can reason from it.

The intent.md you find is the active intent. Everything else derives
from it. The framework-wide invariants are `framework/invariants.md` under the
concrete framework root: every boot entry names it, and a session
reads it before the first answer in every project. The framework root's own
`CLAUDE.md` / `AGENTS.md` hold only the forge repository's rules and the host's
load list; they apply when the active project is that repository. Additional-directory access
alone does not prove instruction loading. Keep the consumer's own project
rules in force; shared framework rules do not replace consumer approvals.
The resolved user scope (boot.md §User scope) always applies, independent of CWD.

## Context routing

Decided once at boot (ROUTE step), holds for the entire session.

### Write paths (context)

Writes to the session handoff and other context files publish through
`framework/continuity.md`.

- **CWD with `context/`:** project-local (`<CWD>/context/`).
- **CWD without `context/`:** at the first write there (not at boot), create
  `context/` with `history/` and `overview.md`, then write project-local. The
  intent exists, so the intention is clear — no clarifying round trip.
- **Always global:** user-scope facts go to the resolved user repo
  (`<user_repo>/context/user/`, boot.md §User scope), regardless of the active
  path. No user scope → report the fact as unroutable; never guess a path.
- **Session handoff:** `<CWD>/context/session-handoff.md` (repo-
  local). Several sessions in one repository share it: the commissioning
  Buddy owns it (`agents/buddy/coordinating-sessions.md`).
- **Session buffer:** `<CWD>/docs/session-buffer.md` (repo-local).

### Project docs routing (read paths)

If RESOLVE found an intent.md AND ROUTE found a local backlog:

- `<CWD>/docs/backlog.md` → the project's active backlog for this session
- `docs/tasks/` → task files for this project
- `docs/specs/` → spec files for this project
- References inside the backlog / tasks: project-root-relative
  (`tasks/020.md`, `specs/020-*.md`)
- Cross-repo context paths: list them per the `intent.md` Context
  field; if not specified, treat as project-relative.
