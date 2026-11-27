# Buddy — Coordinating sessions

Step-loaded unit of `agents/buddy/operational.md` (Phase 2: ACT). Read it before
commissioning a persistent session, when the handoff has a coordinator role
entry, when starting, ordering or commissioning programme work, and when working
as or with a persistent session. Applicability: the core's (`software`). Under
`on-demand` (sessions only on request), before commissioning and while coordinating a session,
§Coordinator to §Session end, §Buddy-to-Buddy, `agents/buddy/delegation.md`
§Vehicle choice and `skills/return_summary/SKILL.md` apply too.

**Coordinator.** One chat holds the whole and sends out work whose volume would fill it.
Buddy starts a session for each task of its own (`agents/buddy/delegation.md` §Vehicle choice);
`framework/direct-eligibility.md` decides who builds and checks a change. A bounded check for the next decision
stays inline or with an agent. Inline, isolated-agent and quick work keep their own rules. A chat that
commissions no session has no coordination duty unless the user hands it the role.

One coordinator holds the request or programme and commissions its tasks. Record the role in the handoff before
the first start or a takeover authorized by the user or recorded handover. Record a handover on the user's word.
The next commissioner may take the free role if the handoff lists no running session or remaining programme item.
Leave an occupied programme, its entries and sessions to its owner. Do your own request inline or with isolated
agents. After compaction reread the named
units. Write briefs and decide on returns (§Buddy-to-Buddy), record state and integrate
(`agents/buddy/concurrent-writers.md`).

Run prerequisites in the foreground, including verification and integration of the preceding return and checks
on the integrated base for sequential work (`agents/buddy/concurrent-writers.md`). Log long checks to a file and
return the result line. Beyond the foreground limit, move the check to the session's first step on that base
and require a return on failure. Keep the base unpushed and the previous branch until a reported pass.
Start the session before any own agent, test or command whose completion begins a new turn. The host may refuse starts from that turn.

If the host refuses the start, give a further brief under §Buddy-to-Buddy when the previous
return is integrated and the model matches. Otherwise use a host proposal the user starts.
If the host needs the user to start it, say in one line that it waits for their next message
in this chat. Without a host route, work inline and with isolated agents and say so in one line
(§Vehicle choice). Keep the handoff current using `skills/knowledge_processor/continuous-maintenance.md`
§Coordinator handoff; read it on taking the role and after compaction. A session starts no
sessions of its own. It proposes any it would need in its return.

**One reading place.** Report returns and user actions or decisions in the coordinator's chat.
After a return, list programme items, states and user actions. Apply §Session end before any wake-up
reply or held wait delivery. Without a return or question, use `<session> — no return. Stopped.`
for a stopped assignment. Else if the cap holds the current wait's stated wake-up, say in one line that
the user's next message here lifts it. Otherwise stay silent where allowed or use
`<session> — no return. <status>.` with `No wait reported` or `<named work>` followed by
`(verified)`, `(unverified)` or `(output present)`.
The session sends blocking questions and return decisions through the coordinator, which follows
`skills/return_summary/SKILL.md` §Accuracy at handovers. When the user
writes in the session itself, the session answers there. If the user answers the session's
blocking question while open at the coordinator, the session reports the answer to the coordinator and
waits for its release with conditions before continuing or commissioning that
work; a conditions preview is not the release. Without messages, report in the return and await a further
brief with the release and conditions. Only a user instruction that names this hold lifts it. In the turn it forwards a blocking question, the
coordinator sends the session any option conditions, conditional on user agreement.
Answer permission prompts in the session that receives them. The host may cap messages across all
the coordinator's sessions until the user writes here. Brief everything needed up to the return.
Message sessions only for a further brief, blocking-question conditions or release, or as
`agents/buddy/background-wait.md` §Receiving a wait report directs. At the cap, questions come in the
return. If a further brief waits at the cap, say in one line that the user's next message here lifts it.

**Session end.** A confirmed stop of the current assignment preempts wait and cap notices, even with
late output. Keep usable results for recovery. Otherwise use `agents/buddy/background-wait.md` §Receiving
a wait report on the current assignment's latest open wait, with no newer evidence of resumption.
If unsure it still applies, hold ownership and delivery. If messaging is unavailable, report the blocker.
A verified current stall counts as stopped. So do two consecutive complete autonomous turn-end
reports with no return, question or named wait when no open wait, live work or hold is known.
On absent or clipped notices, poll returns and records each coordinator turn. Read the open wait's
output on reread. Count each turn once across carriers. Two polls with no new return, commit or entry
trigger a state check. Live work, questions, release holds and unknown state retain writer ownership.
Name a stopped writer next and apply `agents/buddy/concurrent-writers.md` §Cancellation and resume.
Without inter-chat messages, read questions from the return and start a session for a further brief.
After integration or discard, with no further brief planned, offer to archive and do so on the user's
yes. Without archiving, name the session to close.

**Programme order.** The programme agreement's order is the reference for which
task comes next; a plan file's critical path counts only where it matches the
agreement (stale or empty → ask). Before starting, inserting or reordering a
task while a programme is active, compare it with that order, whether or not the
task is listed in it; the agreement comparison in `framework/work-principle.md`
covers order as well as scope. Only the agreed next task starts: after the one
before it is done, or beside it where `agents/buddy/concurrent-writers.md`
§Parallel start allows it, with its record written before the start. Inserting
a task ahead of the agreed next one or changing the order in the agreement
needs the user's confirmation, recorded with the change ("confirmed by …"),
unless the user explicitly delegated that choice; a general grant of autonomy
or permissions is not that delegation. A rationale alone makes it a proposal:
the agreed next task runs, or nothing does. The coordinator starts a programme
task itself (`task_status_update` → `in_progress`, which runs this check) before
commissioning its session, worktree or staging copy, and the brief names the
start; the session does not repeat it. Before commissioning the next task,
reconcile what the previous one held back (`framework/process-map.md`
§Authorization).

**Buddy-to-Buddy.** A persistent session boots as Buddy. Before its brief: a
session only for a task of its own, work that would fill this chat, or work the user
wants to see or steer; a bounded check your next decision needs runs as an agent or
inline.

Brief contents for a first or further session brief. Before writing, read and follow
`framework/spec-engineering-implementation-specs.md` §Convention: one goal per change
(one goal per brief, including its size budget).

- **Outcome and stop condition.** The outcome the brief serves and the stop condition.
- **Task file.** Its path, the agreement the session resumes from; a further brief names the task-file change it
  carries, and the session updates the task file when its work changes plan, steps or `Not yet`.
- **Model.** Name the session's model (`framework/models.md` §A persistent session's model).
- **Effort budget.** Label the coordinator's estimate (Cumulative effort).
- **Checkout.** Name the shared checkout or the assigned worktree and branch (`agents/buddy/concurrent-writers.md`).
- **Division of work.** Name ownership under this section and, for programme tasks, the coordinator's recorded start.
- **Open approval boundaries.** Compare the order with the handoff, the programme agreement, earlier returns and this chat's user turns. Quote every open boundary that concerns the brief's subject with its source, or state that none is open; mark a constraint you set yourself as yours. Complete this before dispatch.
- **Date source.** In brief and task prose, cite the user's words for each delivery date and mark other timing as the writer's estimate. A hard domain limit goes into the plan as a sourced fact; a brief names it as context, never as a deadline.
- **Commit duties and session tests.** State both. When authorizing local commits, copy the exact wording from `agents/buddy/concurrent-writers.md` §Commit, push and transfer.
- **Return and record place.** Name versioned paths and require keeping results there; host-local or scratch storage is temporary and never the only copy.
  Mark poll-only or clipping-prone routes in the brief.
  Include in the brief: “Keep the coordinator's chat for actionable reports. Label interim entries in your return
  file. End autonomous turns only on a return, blocking question or named wait under `agents/buddy/background-wait.md`.
  On a clear boot, work in the same turn and include the greeting in its first reply. If the owner answers here a
  question open at the coordinator, report it to the coordinator and wait for its release before continuing (a conditions preview is not the release; without
  messages, report in your return and await a further brief). If briefed to use polling for
  absent or clipped notices, append each wait note to the named return or record before ending the
  turn. Mark it ended before resuming work
  (owner: `agents/buddy/coordinating-sessions.md` §Buddy-to-Buddy).”
- **Parsed-artifact contracts.** Carry the applicable contracts.
- **Approved acceptance.** For task work, carry `## Approved acceptance (read-only)` (`skills/_protocols/approved-acceptance.md`).

A session takes a further task only through a further brief, after its previous return is integrated, with
its checkout named again; it orders or commissions no programme work. A
compacted session rereads and can take a further brief. It is replaced
by a new session briefed from its returns and records when its return shows that
context it needs is missing, or when the user asks. The session owns its work
item: its task or incident files, its build/research artifacts, the paths in its
manifest and its own close (where the project uses Forge tasks:
`task_status_update` with persist gate and cross-task sweep). The commissioning
Buddy owns integration, the handoff, plan or programme agreements and other
items, including the shared save. After compaction or resume the session rereads
its brief and its own build record (the decision file holds its budget, design
and dispositions) before continuing, and works from the brief's
approved-acceptance block as written. Keep workflow review floors and return at the named versioned
path, never only in host-local storage. Send the host notification where available. Include the decisions list and adoption line
(`skills/return_summary/SKILL.md`), which the coordinator checks and carries to the user. The coordinator verifies
load-bearing claims at source before integrating and leaves the live transcript alone. Send at most one blocking
question at a time.
