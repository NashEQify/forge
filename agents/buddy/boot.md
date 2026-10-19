# Buddy — Boot

Start sequence and routing. Resolve the workflow selection before process loading.

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
   When a user repo is configured (§User scope) and differs from the
   active project, run the same script from the user repo's root too:
   user-scope facts are written there, so it must not be stale.

   Buddy parses the output. Ahead-only status remains advisory. A remote update requires the **pull decision** below before
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
     is not approval. An explicit pull instruction in the current request,
     or a standing session-start pull permission in the project's rules,
     already answers this question for the repos it covers.
   - On approval, inspect the working tree and run `git pull --ff-only` in
     each approved repo. Preserve local work: no automatic stash, reset,
     rebase, merge commit or branch switch. If the pull cannot fast-forward
     or local changes block it, report the concrete blocker and ask how to
     proceed; do not silently resume against the old state.
   - After a successful pull, reload the affected adapters (`AGENTS.md` /
     `CLAUDE.md`), the resolved soul and the framework boot files from
     disk. Follow their updated sequence; only then begin RESOLVE and load
     context/session state. Do not rely on pre-pull copies or repeat an
     already resolved pull question for the same remote revision. If the
     user declines, acknowledge that and boot from the current local state.

3. **RESOLVE:** run routing (see Routing below).
   Then resolve workflow selection from the active intent per
   `$FRAMEWORK_DIR/framework/process-map.md` section Workflow selection.
   The **daily** install profile (named in the entry) always selects
   `on-demand`: it installs no software tooling and starts directly with
   `boot-on-demand.md`.
   **For `on-demand`:** continue with `$FRAMEWORK_DIR/agents/buddy/boot-on-demand.md`
   from its step 3 (steps 1–2 are done) and GREET as it says. Skip the
   generic steps 4–6 here; a project may explicitly require its own probes.
   This branch also governs generic boot summaries supplied by adapters.
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
     - **User profile** — `<user_repo>/context/user/profile.md`
       (§User scope: who the user is, including values and priorities), CWD-independent (who the user is —
       minimal context). No user scope → nothing to load.
     - `bash $FRAMEWORK_DIR/scripts/chub-status-check.sh` — presence
       check for the `chub` CLI (get_api_docs prerequisite). Empty
       output = installed; non-empty = one advisory line for GREET.
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

   **On user-scope warnings (§User scope):** one line — no user scope
   configured, user folder or a boot file missing.

   **On Workflow-Resume findings (step 6):** active workflows as a
   one-liner list in GREET (`Active: solve workflow [step:
   frame-report, state: docs/solve/<slug>.md]`). Nothing found:
   don't mention it.

**Boot ends with the greeting.** From the first user turn on, the selected
mode's working rules apply. No transition period.

## User scope

SoT: `$FRAMEWORK_DIR/framework/user-scope.md`. The machine setting
`~/.config/forge/user.yaml` names the person's user repo; inside it one
fixed convention: `context/user/` with optional `soul.md`, `profile.md`
(read by the start procedure after the freshness gate), and
`navigation.md` to the detail files (on demand). The **entry** (session
hook, launcher, or the installed block in `~/.claude/CLAUDE.md` /
`~/.codex/AGENTS.md`) names only who and where: the resolved soul, the
start procedure, the user repo and the install profile. Without an entry,
resolve by reading the machine setting. The soul read in bootstrap is the **resolved**
soul (default `agents/buddy/soul.md`). Never fall back to another person's
files.

**Continuous maintenance:** when a user scope is configured, or the
project's rules require ongoing knowledge maintenance, read
`$FRAMEWORK_DIR/skills/knowledge_processor/SKILL.md` §Continuous
maintenance in LOAD (software) or step 3 of `boot-on-demand.md`; its rules
apply from the first turn.

## Boot rules

Apply ONLY during steps 1-5.

- Software mode: intake gate, intent verification, planning primitive are
  suspended during boot and required from the first user turn on. On-demand use
  follows the project's working rules.
- Boot output: hostname + HH:MM DD.MM.YYYY + timezone + CWD.
- Use paths exactly as listed (table below). Not found → report,
  skip, continue. No `find`.

### Parallelization (respect the freshness gate)

1. **Bootstrap:** read the resolved soul (§User scope), `operational.md`
   (when the injected boot list names it) and `boot.md`, plus the minimum
   adapter instructions needed to locate the framework and active project. ORIENT may run in parallel. Do not preload intent or context.
2. **Freshness gate:** run STATUS-CHECK (step 2); independent Git checks
   may run in parallel. Resolve any pull question now.
   Context reads, plan/workflow probes and session resume must wait.
3. **Current-context boot:** after the gate and any required instruction
   reload, perform RESOLVE and select the mode before loading context or
   probing session state. Follow the on-demand branch in step 3 or the software
   ROUTE → LOAD → RESUME sequence. Batch independent reads and probes within
   that sequence, respecting dependencies. Then GREET.

The early pull question is an allowed interruption before GREET. A round-count
optimization never permits loading stale context ahead of the freshness gate.

**Probe isolation (MUST).** Result-bearing probes (`workflow_engine
--boot-context`, `plan_engine --boot`, STATUS-CHECK) = own Bash call,
never `;`-chained behind an optional `ls` (compound rc = last cmd's →
ENOENT masks the probe).

### Boot paths

Relative paths = framework-relative (via `--add-dir $FRAMEWORK_DIR`)
or CWD-relative (session-specific). User-scope paths resolve through
§User scope, CWD-independent.

| File | Path | Scope |
|-------|------|-------|
| context-rules.md | `agents/buddy/context-rules.md` | Only when listed in the Context field |
| user profile | `<user_repo>/context/user/profile.md` | always-load (§User scope, CWD-independent) |
| boot-navigation.md | `$FRAMEWORK_DIR/framework/boot-navigation.md` | always-load (skill + workflow index, scope-independent). Explicit-absolute because consumer sessions (CWD≠FRAMEWORK_DIR) resolve relative `framework/` paths through `--add-dir` — the explicit form is more fail-safe. |
| session-buffer.md | `<CWD>/docs/session-buffer.md` | Only when present (repo-local) |
| plan_engine --boot | `$FRAMEWORK_DIR/scripts/plan_engine.py --boot` | Root sessions only (bash call) |
| chub-status-check | `$FRAMEWORK_DIR/scripts/chub-status-check.sh` | Software mode, LOAD step (bash call). Empty stdout = chub installed; non-empty = single advisory line surfaced in GREET. |
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
Code, resolved from the concrete framework root. The daily profile loads no
framework root adapter: its injected boot entry carries the rules it needs. Additional-directory access
alone does not prove instruction loading. Keep the consumer's own project
rules in force; shared framework rules do not replace consumer approvals.
The resolved user scope (§User scope) always applies, independent of CWD.

## Context routing

Decided once at boot (ROUTE step), holds for the entire session.

### Write paths (context)

- **CWD with `context/`:** project-local (`<CWD>/context/`).
- **CWD without `context/`:** create `context/` with `history/` and
  `overview.md`, then write project-local. The intent exists, so the
  intention is clear — no clarifying round trip.
- **Always global:** user-scope facts go to the resolved user repo
  (`<user_repo>/context/user/`, §User scope), regardless of the active
  path. No user scope → report the fact as unroutable; never guess a path.
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
