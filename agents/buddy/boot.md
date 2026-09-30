# Buddy — Boot

Start sequence and routing. Same for every case.

**Freshness gate first:** after minimal host/path orientation, check the active
project and framework for remote updates and resolve the pull decision before
reading intent, project context, plans or session state. Bootstrap instructions
already injected/read are provisional until this gate completes; after a pull,
reload the affected instructions from disk before using them.

## Boot sequence

1. **ORIENT:** `date '+%Y-%m-%d %H:%M %Z'` + `hostname` + `pwd`.
   Don't surface this as a separate bash call — fold the result inline
   into the greeting (GREET). The pwd result is the active CWD for
   the rest of the boot sequence.
2. **STATUS-CHECK:** run `git-status-check.sh` from the active project's Git root,
   passing the concrete framework root as `FRAMEWORK_DIR` and setting
   `GIT_STATUS_CHECK_INCLUDE_FRAMEWORK=1`. This checks both the active
   project and the framework whose instructions this session uses (deduped
   when they are the same repo). It fetches and reports ahead/behind status.
   5-second network timeout. Output: one line per non-clean repo,
   `<path> [ahead N | behind N | ahead M, behind N]`. Empty = sync.

   In the same round: `bash $FRAMEWORK_DIR/scripts/chub-status-check.sh`
   — presence check for the `chub` CLI (get_api_docs prerequisite).
   Empty output = chub installed. Non-empty = single advisory line
   (install hint). Converts the runtime-surprise — get_api_docs
   silently falls back to WebFetch when chub is missing — into a
   boot-time nudge.

   Buddy parses both outputs. Ahead-only status and missing chub remain
   advisory. A remote update requires the **pull decision** below before
   RESOLVE, ROUTE, LOAD or RESUME begins. Do not load context in parallel
   with this gate or while waiting for the answer.

   **Pull decision (behind > 0, including divergence):**
   - The script can report cached tracking refs after a failed fetch. Before
     claiming an online update, confirm a successful bounded fetch for the
     affected repo and re-read its status. If offline or fetch fails, report
     the unavailable check, label any cached status as such, and continue
     without a pull or a blocking update question.
   - If still behind, name the repo and ahead/behind counts and ask:
     "Remote has N newer commits in <repo>. Shall I run git pull before
     continuing?" Batch multiple affected repos into one question. Wait for
     the user's answer before continuing the boot sequence. Silence
     is not approval. An explicit pull instruction in the current request
     already answers this question for the named repos.
   - On approval, inspect the working tree and run `git pull --ff-only` in
     each approved repo. Preserve local work: no automatic stash, reset,
     rebase, merge commit or branch switch. If the pull cannot fast-forward
     or local changes block it, report the concrete blocker and ask how to
     proceed; do not silently resume against the old state.
   - After a successful pull, reload the affected adapters (`AGENTS.md` /
     `CLAUDE.md`) and framework `soul.md`, `operational.md`, `boot.md` from
     disk. Follow their updated sequence; only then begin RESOLVE and load
     context/session state. Do not rely on pre-pull copies or repeat an
     already resolved pull question for the same remote revision. If the
     user declines, acknowledge that and boot from the current local state.

3. **RESOLVE:** run routing (see Routing below).
4. **ROUTE:** decide context routing (read and write paths for the
   session). CWD comes from ORIENT.
   - Run `ls <CWD>/context/` (MUST — filesystem check, don't infer
     from intent.md).
     Found → context write path = `<CWD>/context/`.
     Not found → auto-create `<CWD>/context/` with `history/` +
     `overview.md`, then write project-local (see Context Routing).
   - **Project docs:** if RESOLVE found an intent.md, run
     `ls <CWD>/docs/backlog.md` (MUST).
     Found → the project has a local docs/ (backlog, tasks, specs)
     for the session.
     Not found → no local backlog.
   The result holds for the entire session. Rules: see "Context
   routing".
5. **LOAD:** load context. Two categories: always-load (Buddy
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
     - Local backlog: if ROUTE (step 4) found one → load it.
     - Context field missing in intent.md: derive from Vision +
       Non-Goals; ask if uncertain.
   - No intent.md found: only always-load, then create intent.md
     together.
6. **RESUME:** load session state.
   - `session-buffer.md`: `<CWD>/docs/session-buffer.md` (repo-
     local). PENDING → dispatcher, PROCESSED → remove. Not found →
     skip.
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
   - **Session handoff:** `<CWD>/context/session-handoff.md`. The
     handoff carries the discussion context from the last session
     (meta-summary + open topics in the 9-point structure). Not
     found → fresh start.
7. **GREET:** short greeting (style: soul.md).

   **On STATUS-CHECK findings (step 2):** briefly report any pull outcome,
   ahead-only status or unavailable check not already communicated. The
   pull decision was resolved before context loading; do not ask again here.
   Nothing found: don't mention it.

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

### Parallelization (respect the freshness gate)

1. **Bootstrap:** read `soul.md`, `operational.md` and `boot.md`, plus the
   minimum adapter instructions needed to locate the framework and active
   project. ORIENT may run in parallel. Do not preload intent or context.
2. **Freshness gate:** run STATUS-CHECK (step 2); independent Git checks and
   the chub check may run in parallel. Resolve any pull question now.
   Context reads, plan/workflow probes and session resume must wait.
3. **Current-context boot:** after the gate and any required instruction
   reload, perform RESOLVE → ROUTE → LOAD → RESUME. Batch independent reads
   and probes within this phase, respecting dependencies. Then GREET.

The early pull question is an allowed interruption before GREET. A round-count
optimization never permits loading stale context ahead of the freshness gate.

**Probe isolation (MUST).** Result-bearing probes (`workflow_engine
--boot-context`, `plan_engine --boot`, STATUS-CHECK) = own Bash call,
never `;`-chained behind an optional `ls` (compound rc = last cmd's →
ENOENT masks the probe).

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
| boot-navigation.md | `$FRAMEWORK_DIR/framework/boot-navigation.md` | always-load (skill + workflow index, scope-independent). Explicit-absolute because consumer sessions (CWD≠FRAMEWORK_DIR) resolve relative `framework/` paths through `--add-dir` — the explicit form is more fail-safe. |
| session-buffer.md | `<CWD>/docs/session-buffer.md` | Only when present (repo-local) |
| plan_engine --boot | `$FRAMEWORK_DIR/scripts/plan_engine.py --boot` | Root sessions only (bash call) |
| chub-status-check | `$FRAMEWORK_DIR/scripts/chub-status-check.sh` | Always (bash call; parallel with git-status-check). Empty stdout = chub installed; non-empty = single advisory line surfaced in GREET. |
| session-handoff | `<CWD>/context/session-handoff.md` | Only when present (repo-local) |
| project backlog | `<CWD>/docs/backlog.md` | Only when ROUTE found a local backlog |

Project-specific context: derive paths from intent.md Context field.

## Routing

Input: working directory. Output: active intent + mode.

1. Run `ls <CWD>/intent.md` — CWD comes from ORIENT step 1 (MUST —
   check the filesystem, do NOT infer from the context window).
2. Found → that's the active intent. Mode comes from the Context
   field (first sentence). Read with `cat` if not already in context.
3. Not found → walk up the directory tree (`ls ../intent.md`, etc.).
   Stop at `/`.
4. Nothing found → "No intent. New project? Should I create an
   intent.md?"
   Format: `framework/intent-tree.md`, section "intent.md format". The
   intent.md is the load-bearing input for all later intent-driven work
   (CLAUDE.md §Intent-driven) — state the goal as **extractable facts**, not
   only argued, so agents can reason from it.

The intent.md you find is the active intent. Everything else derives
from it. Load the framework's adapter explicitly when the host has not
already injected it: `AGENTS.md` for Codex/OpenCode, `CLAUDE.md` for Claude
Code, resolved from the concrete framework root. Additional-directory access
alone does not prove instruction loading. Keep the consumer's own project
rules in force; shared framework rules do not replace consumer approvals.
`values.md` + `profile.md` always
apply (canonical under `~/projects/personal/context/user/`,
independent of CWD).

## Context routing

Decided once at boot (ROUTE step), holds for the entire session.

### Write paths (context)

- **CWD with `context/`:** project-local (`<CWD>/context/`).
- **CWD without `context/`:** create `context/` with `history/` and
  `overview.md`, then write project-local. The intent exists, so the
  intention is clear — no clarifying round trip.
- **Always global:** `~/projects/personal/context/user/` (canonical
  user-scope path), regardless of the active path.
- **Session handoff:** `<CWD>/context/session-handoff.md` (repo-
  local). Parallel sessions on different hosts don't collide
  (different repos).
- **Session buffer:** `<CWD>/docs/session-buffer.md` (repo-local).

### Project docs routing (read paths)

If RESOLVE found an intent.md AND ROUTE found a local backlog:

- `docs/backlog.md` → active backlog for this session
- `docs/tasks/` → task files for this project
- `docs/specs/` → spec files for this project
- References inside the backlog / tasks: project-root-relative
  (`tasks/020.md`, `specs/020-*.md`)
- Cross-repo context paths: list them per the `intent.md` Context
  field; if not specified, treat as project-relative.
