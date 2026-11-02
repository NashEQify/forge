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

1. **ORIENT:** the boot probe's `orient:` line (date, time zone, host, CWD;
   `boot-status.md` §Freshness gate).
   Don't surface this as a separate bash call — fold the result inline
   into the greeting (GREET). The pwd result is the active CWD for
   the rest of the boot sequence.
2. **STATUS-CHECK:** run the boot probe from the active project's working directory
   and resolve its findings, including any pull decision, before step 3: read and
   follow `agents/buddy/boot-status.md` §Freshness gate (Codex escalation route,
   invocation, output, pull decision).

   Then resolve workflow selection from the active intent per
   `$FRAMEWORK_DIR/framework/workflow-selection.md`.
   **For `on-demand`:** continue with `$FRAMEWORK_DIR/agents/buddy/boot-on-demand.md`
   from its step 3 (steps 1–2 are done) and GREET as it says. Skip the
   software steps 4–7 (`boot-software.md`); a project may explicitly require its own probes.
   This branch also governs generic boot summaries supplied by adapters.
   **For software:** load `$FRAMEWORK_DIR/agents/buddy/operational.md` before
   development process work. Then read and follow
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
hook, launcher, or the installed block in `~/.codex/AGENTS.md` / a
project's `AGENTS.override.md`) names who and where: the resolved soul, the
start procedure, the user repo and the install profile. It states the
§Restricted user scope rule. Where its carrier has room, it also includes
whole files: the resolved soul and `operational.md` (an install-time block
includes none: its files change without a reinstall). A `project` install
has no user scope: its entry names Forge's soul.
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
the network; creating `context/` or other files needs a write); a skipped
check is at most one word in the orientation line (`boot-status.md`
§Freshness gate). An instruction unit that could not be read is said first in
the first answer (`boot-status.md` §Greeting findings): the reply that ends
your first turn, not a progress note before it.

## Boot rules

Apply ONLY during steps 1-5.

- Software mode: intake gate, intent verification, planning primitive are
  suspended during boot and required from the first user turn on. On-demand use
  follows the project's working rules.
- Boot output: hostname + HH:MM DD.MM.YYYY + timezone + CWD, with at most one
  word for an unavailable check (`remote unchecked`), after a notice that an
  instruction unit did not load (`boot-status.md` §Greeting findings). It comes
  before the first answer on every start, so the session first orients itself.
- Use paths exactly as listed (table below). Not found → report,
  skip, continue. No `find`.

### Parallelization (respect the freshness gate)

Each round is one batch of tool calls; every round re-sends the whole context,
so the boot keeps to these three:

1. **Round 1, instructions and checks, before the gate:** read the resolved
   soul (§User scope) and the units the entry names, unless it includes them,
   together with `agents/buddy/boot-status.md`, `agents/buddy/boot-routing.md`,
   `framework/workflow-selection.md` and `framework/work-principle.md` (on
   Codex, `codex-execution.md` first, as the entry says). Run the boot probe
   (`git-status-check.sh --boot`, ORIENT and STATUS-CHECK in one call) in the
   same round. Do not preload intent or context.
2. **Freshness gate:** resolve any pull question now; context reads,
   plan/workflow probes and session resume wait for it. After a pull, reread
   the changed instructions.
3. **Round 2, context after the gate:** read `intent.md` (RESOLVE), the
   project's rules file the host has not loaded, the user profile through the
   personal snapshot (`boot-software.md` step 5, `boot-on-demand.md` step 3)
   and the session handoff the probe found, and select the mode; the probe's lines already tell which continuing-work
   files exist. With an explicit `mode-line`, read the mode's unit in this round.
4. **Round 3, the mode's unit:** read `boot-software.md` with `operational.md`
   (unless the entry includes it), or `boot-on-demand.md`; with a user scope,
   the continuous-maintenance rules; the intent's Context "Boot" files.
   Every other unit loads at the step that uses it, through that step's own
   read trigger. Then GREET.

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
| boot-navigation.md | `$FRAMEWORK_DIR/framework/boot-navigation.md` | Not at boot: at its read trigger (`boot-software.md` step 5, `boot-on-demand.md`). Explicit-absolute because consumer sessions (CWD≠FRAMEWORK_DIR) resolve relative `framework/` paths through `--add-dir` — the explicit form is more fail-safe. |
| session-buffer.md | `<CWD>/docs/session-buffer.md` | Only when present (repo-local) |
| plan_engine --boot | `$FRAMEWORK_DIR/scripts/plan_engine.py --boot` | Not at boot: when choosing or taking up a task, where `docs/plan.yaml` exists (bash call; `operational.md` §Phase 1, `task_status_update` Step 1b) |
| chub-status-check | the boot probe's `chub:` line | Software mode, LOAD step. `installed`, or exactly `not installed` (no check in this installation): nothing to report; otherwise a single advisory line surfaced in GREET. |
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
