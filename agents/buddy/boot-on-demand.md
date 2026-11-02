# Buddy — On-demand start

Read and follow `framework/work-principle.md` before taking up work.
Resolve this reference against the framework root; retain the consumer CWD.


The complete start procedure for `on-demand` work: projects whose intent selects
on-demand (`framework/workflow-selection.md`). `boot.md` hands its on-demand
branch to this file. The entry (installed per machine or per project) has
already named the soul, the user repo when one is configured, and the install
profile; files it includes in full are loaded and need no read.

1. **Orient:** the boot probe's `orient:` line (date, time zone, host and CWD;
   fold into the greeting).
2. **Freshness first:** run the boot probe as `agents/buddy/boot-status.md`
   §Freshness gate says, before reading anything else (Codex callers first follow
   `agents/buddy/codex-execution.md`); on-demand ignores its `chub:` line. Its held-back entries and unavailable
   checks go into step 6. `[uncommitted: …]`, `[installed-not-committed: K]` and
   `[installer: …]` groups never block the freshness step. (The soul itself is
   read before this step, from the entry: it shapes even the pull question.)
3. **The person:** read the configured user profile (who the person is,
   including values and priorities) through one personal snapshot, which also
   returns personal pending status:
   `python3 <framework>/scripts/continuity.py snapshot --scope personal --project-root <project>`
   with `{"schema_version":1,"paths":["profile.md"]}` on stdin (the helper finds
   the user repo; personal paths are relative to its `context/user/`); read its
   JSON output directly, without writing it to a file. Non-empty
   `pending_operations` is pending recovery (`agents/buddy/boot-status.md` §Greeting findings). With a user scope, or when
   the project's rules require ongoing knowledge maintenance (`boot.md` §User
   scope), then read `<framework>/skills/knowledge_processor/continuous-maintenance.md`
   — its rules apply from the first answer. Detail about the person is reached later through
   `context/user/navigation.md`. No user scope configured → say so once in the
   greeting.
4. **The project's rules:** its `CLAUDE.md`, else its `AGENTS.md` (Claude Code
   does not load `AGENTS.md` by itself), and `intent.md`. Follow the start
   files they name; skip files already read in step 3.
5. **Default resume** when the project names no start files:
   - read the boot entry the intent names, else `navigation.md` /
     `context/navigation.md`; follow it to the topic at hand and read
     `intent.md`, local `AGENTS.md` and named instructions along that path
     before working on it — also on a later topic switch. Do not read all
     subfolders or archives;
   - read the session handoff the probe found (`handoff:`; keep an existing
     `session-handover.md` name; never create a second one) completely, with a
     pending session buffer; none → fresh start, reconstruct nothing. Approvals
     recorded there keep their stated scope: do not renew an old host/session
     approval or carry it to other targets, do not re-ask one already given for
     this continuation; diagnosis-only stays diagnosis. Before relying on its
     running jobs or other changeable state, re-measure them;
   - every other unit loads at the step that uses it, through that step's own
     read trigger; an explicit development binding in the handoff is restored
     through `framework/development-continuation.md` before that work
     progresses. Do not infer selection from task/plan/state files or start
     unrelated open topics.
6. **Greet** in the first answer, the reply that ends your first turn (a
   progress note before it does not count, because some hosts deliver only
   that reply): one short line with status and next step (style: soul). An
   instruction unit that did not load opens that reply with the notice
   `agents/buddy/boot-status.md` §Greeting findings defines. After that, mention
   only a pull outcome, ahead status, held-back work or a user-scope warning, if
   any; an unchecked remote is at most one word in the orientation line. Uncommitted or installed-not-committed state is
   a note in the shape `agents/buddy/boot-status.md` §Greeting findings gives it: found before this session,
   with path and count. It gates new work only where the project's rules
   ask for that or the checkout is the framework of a coordinated programme;
   then follow `framework/process-map.md` §Authorization. An `[installer: …]`
   group without `operation open` is a maintenance need: say so.

When coordination resumes from a handoff, at a meaningful task/topic change and
at a consequential decision/adoption boundary, read and follow
`framework/context-and-loading.md` §Buddy coordination refresh, without loading
development operational rules or selecting a software workflow.

Not part of on-demand start: the chub check, plan/workflow probes, the Forge
skill index, automatic `context/` creation and development `operational.md` (read it only
for explicitly selected development work). Read the skill index
`framework/boot-navigation.md` when the user asks for a Forge skill, workflow,
Council or board, and on Codex before choosing any skill or workflow: routing
without it misses skills no workflow names. Generic methods use their own contracts. Forge workflows, Councils and boards run
only on explicit request. Authorization, secrets and the project's own
approvals stay binding. Before the final message of a turn that changed
something or delegated work, read and follow `skills/return_summary/SKILL.md`
§Decisions I took for you and, for each completion claim,
`skills/_protocols/evidence-author-claims.md` §8.5.
