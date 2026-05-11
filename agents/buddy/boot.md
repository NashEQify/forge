# Buddy — Boot

Start sequence and routing. Same for every case.

## Routing

Input: working directory. Output: active intent + mode.

1. Run `ls <CWD>/intent.md` — CWD comes from ORIENT step 1 (MUST —
   check the filesystem, do NOT infer from the context window).
2. Found → that's the active intent. Mode comes from the Context
   field (first sentence).
   In the BuddyAI root (CWD = BuddyAI/): intent.md is already in
   context via --add-dir — `ls` is for confirmation only, no `cat`.
   In workspaces (CWD under BuddyAI/workspaces/): read intent.md from
   the CWD (`cat`). The root intent.md is NOT the active intent — it
   is ignored.
3. Not found → walk up the directory tree (`ls ../intent.md`, etc.).
   Stop at `/`.
4. Nothing found → "No intent. New project? Should I create an
   intent.md?"
   Format: `framework/intent-tree.md`, section "intent.md format".

The intent.md you find is the active intent. Everything else derives
from it. `CLAUDE.md` always applies (via --add-dir, mechanically
guaranteed by the `cc` script). `values.md` + `profile.md` +
`companions.yaml` always apply (canonical under
`~/projects/personal/context/user/`, independent of CWD).

## Boot sequence

1. **ORIENT:** `date '+%Y-%m-%d %H:%M %Z'` + `hostname` + `pwd`.
   Don't surface this as a separate bash call — fold the result inline
   into the greeting (GREET). The pwd result is the active CWD for
   the rest of the boot sequence.
2. **RESOLVE:** run routing (see above).
3. **ROUTE:** decide context routing (read and write paths for the
   session). CWD comes from ORIENT.
   - CWD under BuddyAI/ → "inside", context write path =
     BuddyAI/context/.
   - CWD outside BuddyAI/ → run `ls <CWD>/context/` (MUST — filesystem
     check, don't infer from intent.md).
     Found → "with context/", write path = project-local.
     Not found → "without context/", auto-create + project-local
     (see Context Routing).
   - **Project docs:** if CWD != BuddyAI root AND RESOLVE found an
     intent.md, run `ls <CWD>/docs/backlog.md` (MUST).
     Found → the project has a local docs/ (backlog, tasks, specs).
     That applies for the session. The BuddyAI root `docs/backlog.md`
     is NOT loaded in this session.
     Not found → no local backlog, the root backlog applies.
     Same mechanic for workspaces and external projects.
   The result holds for the entire session. Rules: see "Context
   routing".
4. **LOAD:** load context. Two categories: always-load (Buddy
   infrastructure, scope-independent) + intent-load (from the
   Context field of the active intent.md).
   - **always-load** (Buddy tier, every session):
     - `values.md` — canonical
       `~/projects/personal/context/user/values.md`, CWD-independent.
     - `profile.md` — canonical
       `~/projects/personal/context/user/profile.md`, CWD-independent
       (who the user is — minimal context).
     - `$FRAMEWORK_DIR/framework/boot-navigation.md` — skill index
       (25 skills + 10 workflows). Without it, Buddy boots without
       the skill landscape in mind. Explicit-absolute (consumer-CWD
       convention).
   - **intent-load** (project-specific):
     - Whatever the Context field lists under "Boot". That, and
       nothing else.
     - Workspace backlog: if ROUTE (step 3) found a local backlog →
       load it.
     - Context field missing in intent.md: derive from Vision +
       Non-Goals; ask if uncertain.
   - No intent.md found: only always-load, then create intent.md
     together.
5. **STATUS-CHECK:** `bash $FRAMEWORK_DIR/scripts/git-status-check.sh`
   — runs `git fetch` + `git status -sb` for `$FRAMEWORK_DIR` + the
   active CWD in parallel (deduped). 5-second network timeout. Output:
   one line per non-clean repo, `<path> [ahead N | behind N | ahead M,
   behind N]`. Empty output = everything in sync.
   Buddy parses: on non-empty output, surface the result in GREET
   ("Note: $FRAMEWORK_DIR is behind by 3 commits — `git pull`
   recommended before substantial work"). Never BLOCK — just a hint.

6. **RESUME:** load session state.
   - `session-buffer.md`: always `BuddyAI/docs/session-buffer.md`
     (Buddy-global). PENDING → dispatcher, PROCESSED → remove.
   - **Root session:** run
     `python3 $FRAMEWORK_DIR/scripts/plan_engine.py --boot`. The
     output gives in-progress tasks, critical path, next actions,
     milestone status, warnings.
   - **Workflow resume (required):** run
     `python3 $FRAMEWORK_DIR/scripts/workflow_engine.py --boot-context`.
     The output lists active workflows (workflow_id + name +
     current_step + state-file path). Empty output → no active
     workflows. On output: Buddy MUST surface them in GREET (see
     step 7) AND read the state files of the active workflows
     (`docs/<workflow>/<slug>.md`) before the first user-substance
     turn so the content state is in mind.
   - **Session handoff:** CWD-based (see Context routing below).
     - CWD under `BuddyAI/workspaces/<name>/` →
       `BuddyAI/context/session-handoff-<name>.md`
     - CWD under `BuddyAI/` root →
       `BuddyAI/context/session-handoff.md`
     - CWD external → `<CWD>/context/session-handoff.md`
     The handoff carries the discussion context from the last
     session (meta-summary + open topics in the 9-point structure).
     Not found → fresh start.
   - **Companions** (optional user-scope convention): if
     `~/projects/personal/context/user/companions.yaml` exists, read
     the registry and load each entry's `soul_file` + `memory_file`.
     Companion files live wherever the registry points to (typical
     convention: a per-user `companions/` directory outside the
     framework repo). Not found or empty → skip, no error. Companions
     are NOT part of the framework distribution.
7. **GREET:** short greeting (style: soul.md). If permanent companions
   were loaded in step 6: optional brief character opener in a
   companion's voice, 1-3 sentences, only when it adds to the session
   state — not required, not every boot. Buddy's greeting stays
   primary; the companion is the shadowy second guest behind it.

   **On STATUS-CHECK findings (step 5):** surface as a one-liner
   under the greeting (`Note: <repo> is behind by 3 commits — `git
   pull` recommended.`). Multiple repos: a compact list. Nothing
   found: don't mention it.

   **On Workflow-Resume findings (step 6):** active workflows as a
   one-liner list in GREET (`Active: solve workflow [step:
   frame-report, state: docs/solve/<slug>.md]`). Nothing found:
   don't mention it.

**Boot ends with the greeting.** From the first user turn on, all
obligations from operational.md apply. No transition period.

## Boot rules

Apply ONLY during steps 1-5.

- Intake gate, intent verification, planning primitive: suspended.
  From the first user turn on: required.
- Boot output: hostname + HH:MM DD.MM.YYYY + timezone + CWD.
- Use paths exactly as listed (table below). Not found → report,
  skip, continue. No `find`.

### Parallelization (MUST — performance)

Finish boot in at most 2 tool-call rounds:
1. **Round 1:** read `soul.md` + `operational.md` + `boot.md` in
   parallel (needed to determine round 2).
2. **Round 2:** EVERYTHING ELSE in parallel — ORIENT
   (`date/hostname/pwd`), RESOLVE (`ls intent.md`), STATUS-CHECK
   (`bash $FRAMEWORK_DIR/scripts/git-status-check.sh`), ALL
   always-load files (`values.md`, `profile.md`,
   `boot-navigation.md`), intent-load files (`context-rules.md`,
   `session-buffer.md`, backlog if applicable),
   `python3 $FRAMEWORK_DIR/scripts/plan_engine.py --boot` (root
   sessions only), and
   `python3 $FRAMEWORK_DIR/scripts/workflow_engine.py --boot-context`.
   All boot files from the path table. No "if applicable" — what's
   in intent.md Context field under Boot is required.
   In BuddyAI root the paths are known — no reason for a third round.
   For external projects: run the ROUTE check (`ls context/`,
   `ls docs/backlog.md`) inside round 2. If the result needs further
   reads → round 3 is allowed.

No thinking pauses between rounds. Round 1 → straight to round 2 →
straight to GREET.

### Boot paths

Relative paths = framework-relative (via `--add-dir $FRAMEWORK_DIR`)
or CWD-relative (session-specific). Absolute paths
(`~/projects/personal/...`) = canonical user-scope locations,
CWD-independent.

| File | Path | Scope |
|-------|------|-------|
| context-rules.md | `agents/buddy/context-rules.md` | Only when listed in the Context field |
| values.md | `~/projects/personal/context/user/values.md` | always-load (canonical, CWD-independent) |
| profile.md | `~/projects/personal/context/user/profile.md` | always-load (canonical, CWD-independent) |
| boot-navigation.md | `$FRAMEWORK_DIR/framework/boot-navigation.md` | always-load (skill + workflow index, scope-independent). Explicit-absolute because consumer sessions (CWD≠FRAMEWORK_DIR) resolve relative `framework/` paths through `--add-dir` — the explicit form is more fail-safe. 421-finding B-2. |
| session-buffer.md | `docs/session-buffer.md` | Always (Buddy-global) |
| plan_engine --boot | `$FRAMEWORK_DIR/scripts/plan_engine.py --boot` | Root sessions only (bash call) |
| session-handoff | `<context>/session-handoff[-<workspace>].md` | CWD-based (see Context routing) |
| companions.yaml (optional, user-scope) | `~/projects/personal/context/user/companions.yaml` | only when present |
| companion soul+memory (optional, user-scope) | path per registry entry | only when companions.yaml exists |
| project backlog | `<CWD>/docs/backlog.md` | Only when ROUTE found a local backlog |

Project-specific context: derive paths from intent.md Context field.

## Context routing

Decided once at boot (ROUTE step), holds for the entire session.

### Write paths (context)

- **Inside BuddyAI:** centrally under `BuddyAI/context/`. Workspaces
  have their own `docs/` (backlog, tasks, specs); context stays
  central.
- **External projects with `context/`:** project-local.
- **External projects without `context/`:** create `context/` with
  `history/` and `overview.md`, then write project-local. The intent
  exists, so the intention is clear — no clarifying round trip.
- **Always global:** `~/projects/personal/context/user/` (canonical
  user-scope path), regardless of the active path.
- **Always BuddyAI:** `session-buffer.md` (Buddy-global).
- **Session handoff:** CWD-based, mirroring general context routing:
  - CWD under `BuddyAI/` (incl. `workspaces/<name>/`) →
    `BuddyAI/context/session-handoff[-<name>].md`
  - CWD external with `context/` →
    `<CWD>/context/session-handoff.md`
  - CWD external without `context/` → `<CWD>/context/...`
    (auto-created per context routing)
  Workspace-suffix convention only under `BuddyAI/`. External
  projects: one handoff per repo. Parallel sessions on different
  hosts don't collide (different repos).

### Project docs routing (read paths)

If CWD != BuddyAI root AND RESOLVE found an intent.md AND ROUTE
found a local backlog:

- `docs/backlog.md` → active backlog for this session (instead of
  the root `docs/backlog.md`)
- `docs/tasks/` → task files for this project
- `docs/specs/` → spec files for this project
- References inside the backlog / tasks: project-root-relative
  (`tasks/020.md`, `specs/020-*.md`)
- Cross-repo context paths: list them per the `intent.md` Context
  field; if not specified, treat as project-relative.

One backlog per session. Root backlog and project backlog are not
loaded in parallel. Cross-references between root and project: on
demand, when explicitly asked.
