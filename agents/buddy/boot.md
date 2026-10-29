# Buddy — Boot

Read and follow `framework/work-principle.md` before taking up work.
Resolve this reference against the framework root; retain the consumer CWD.


Start sequence and routing. Resolve the workflow selection before process loading.

**Freshness gate first:** after minimal host/path orientation, check the active
project and framework for remote updates and resolve the pull decision before
reading intent, project context, plans or session state. Bootstrap instructions
already injected/read are provisional until this gate completes; after a pull,
reload the affected instructions from disk before using them.

**The size of the request does not shorten the boot.** Run it before answering,
also for a quick question, a lookup or a small fix: it gives the answer the
person's and the project's context, and on-demand is already the short form
(`boot-on-demand.md`). A user scope or a host limit cuts only the steps it
blocks, not the instruction reads; a failed read is reported (§Restricted user
scope).

## Boot sequence

1. **ORIENT:** `date '+%Y-%m-%d %H:%M %Z'` + `hostname` + `pwd`.
   Don't surface this as a separate bash call — fold the result inline
   into the greeting (GREET). The pwd result is the active CWD for
   the rest of the boot sequence.
2. **STATUS-CHECK:** run `git-status-check.sh` from the active project's Git root
   and resolve its findings, including any pull decision, before step 3: read and
   follow `agents/buddy/boot-status.md` §Freshness gate (Codex escalation route,
   invocation, output, pull decision).

   Then resolve workflow selection from the active intent per
   `$FRAMEWORK_DIR/framework/workflow-selection.md`.
   The **daily** install profile (named in the entry) always selects
   `on-demand`: it installs no software tooling and starts directly with
   `boot-on-demand.md`.
   **For `on-demand`:** continue with `$FRAMEWORK_DIR/agents/buddy/boot-on-demand.md`
   from its step 3 (steps 1–2 are done) and GREET as it says. Skip the
   software steps 4–7 (`boot-software.md`); a project may explicitly require its own probes.
   This branch also governs generic boot summaries supplied by adapters.
   **For software:** load `$FRAMEWORK_DIR/agents/buddy/operational.md` before
   development process work; bind the explicit selection through the development
   continuation adapter. Then read and follow
   `$FRAMEWORK_DIR/agents/buddy/boot-software.md`: steps 4–7 (ROUTE, LOAD,
   RESUME, GREET).

**Boot ends with the greeting.** From the first user turn on, the selected
mode's working rules apply.

## User scope

SoT: `$FRAMEWORK_DIR/framework/user-scope.md`. The machine setting
`~/.config/forge/user.yaml` names the person's user repo; inside it one
fixed convention: `context/user/` with optional `soul.md`, `profile.md`
(read by the start procedure after the freshness gate), and
`navigation.md` to the detail files (on demand). The **entry** (session
hook, launcher, or the installed block in `~/.claude/CLAUDE.md` /
`~/.codex/AGENTS.md`) names who and where: the resolved soul, the
start procedure, the user repo and the install profile. It states the
§Restricted user scope rule. Where its carrier has room, it also includes
whole files: the resolved soul and, in the `full` profile, `operational.md`
(an install-time block includes none: its files change without a reinstall).
An included file is loaded; it needs no read at boot. Without an entry,
resolve by reading the machine setting. The soul read in bootstrap is the **resolved**
soul (default `agents/buddy/soul.md`). Never fall back to another person's
files.

**Continuous maintenance:** when a user scope is configured, or the
project's rules require ongoing knowledge maintenance, read
`$FRAMEWORK_DIR/skills/knowledge_processor/continuous-maintenance.md`
in LOAD (step 5, `boot-software.md`) or step 3 of `boot-on-demand.md`; its rules
apply from the first turn.

## Restricted user scope

The framework root is the session's instruction source. Reading it and the
files the entry names loads instructions; it is not work outside the
project, so a scope that limits writes, network or installs does not cancel
the boot. Skip only the steps the scope forbids (the freshness fetch needs
the network; creating `context/` or other files needs a write) and report
each as an unavailable check (`boot-status.md` §Freshness gate). A boot
skipped or cut short for any reason is said first in the first answer
(`boot-status.md` §Greeting findings): the reply that ends your first turn,
not a progress note before it.

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
   (when the entry or adapter names it), `boot.md` and, in the full profile,
   `framework/invariants.md`, unless the entry includes them, plus the minimum
   to locate the framework and project. ORIENT may run in parallel. Do not preload intent or context.
2. **Freshness gate:** run STATUS-CHECK (step 2); independent Git checks
   may run in parallel. Resolve any pull question now.
   Context reads, plan/workflow probes and session resume must wait.
3. **Current-context boot:** after the gate and any required instruction
   reload, perform RESOLVE and select the mode before loading context or
   probing session state. Follow the on-demand branch in step 3 or the software
   ROUTE → LOAD → RESUME sequence in `boot-software.md`. Batch independent reads and probes within
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
| boot-status.md | `agents/buddy/boot-status.md` | Every boot: step 2 (freshness gate) and step 7 (greeting findings) |
| boot-routing.md | `agents/buddy/boot-routing.md` | Every boot: RESOLVE and ROUTE; again when choosing a write path |
| boot-software.md | `agents/buddy/boot-software.md` | Software mode: steps 4–7, read at step 3 |

Project-specific context: derive paths from intent.md Context field.

## Routing

Intent routing (RESOLVE: the active intent.md and its mode) and context routing
(ROUTE: read and write paths): read and follow `agents/buddy/boot-routing.md` at
RESOLVE and ROUTE, and whenever you choose where to write context, the session
handoff or a user-scope fact.
