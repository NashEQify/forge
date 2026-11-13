# Buddy — Coordinating sessions

Step-loaded unit of `agents/buddy/operational.md` (Phase 2: ACT). Read it before
commissioning a persistent session, when the handoff has a coordinator role
entry, when starting, ordering or commissioning programme work, and when working
as or with a persistent session. Applicability: the core's (`software`). Under
`on-demand` (sessions only on request), once a chat has commissioned one,
§Coordinator to §Session end, §Buddy-to-Buddy, `agents/buddy/delegation.md`
§Vehicle choice and `skills/return_summary/SKILL.md` apply too.

**Coordinator.** Intent: one chat holds the whole and stays small, work whose
volume would fill it runs elsewhere and only its result comes back; context is
steered, not the chat count. `agents/buddy/delegation.md` §Vehicle choice alone
decides whether work leaves the chat, and there Buddy starts the session
himself. Taking up work of more than one task, do not choose any task's path
before reading §Vehicle choice. That each task is small enough for DIRECT (the
quick or checked path, `framework/direct-eligibility.md`) does not answer it:
that file says who builds and checks one change, §Vehicle choice where the work
runs. Work the chat keeps inline or gives to an isolated agent, and the quick
path, run as before: a chat that commissions no session has no duty from these
three paragraphs. From its first commissioned session on, a chat coordinates the
request or programme that session serves: before the start it writes the
handoff's role entry as taken by this chat; then it holds that whole and does
not carry out its task work itself; §Vehicle choice decides where each piece
runs, its own checks and other requests included. A project has one coordinator.
A chat finding the entry held by another chat (at boot or before a start) leaves
the programme, the coordination entries and the sessions to it and does its own
request inline or with isolated agents, unless the entry says handed over or the
user hands it the role (then it writes the entry as taken by this chat first),
or the handoff lists no running session and no programme item left (the entry is
free). The coordinator records the role as handed over when the user asks; a
compacted coordinator rereads what its rules name and continues. It writes
briefs, decides on a return after verifying its load-bearing claims at their
source (§Buddy-to-Buddy), records state and integrates
(`agents/buddy/concurrent-writers.md`). In a turn in which it will start a
session (after a return or on the user's word), it starts it before any
background work of its own (an agent, a test run or another command whose
completion begins a new turn): a host may refuse a start in a turn its own
agent's completion began (`architecture-documentation/07-tool-integrations.md`
§Delegation vehicles), and a turn begun by other background work is treated the
same. What must come before the start runs in the foreground of that turn (inline,
or a command or agent whose result returns within it): a check the brief needs
and, for the next task in sequence, the previous return's verification and its
integration with the checks that integration runs on the merged result
(`agents/buddy/concurrent-writers.md`), because that result is the next
writer's base and a failure found after the start falls on two writers. A long
check runs as a command that writes its log to a file and returns its result
line; a check whose run time exceeds the host's limit for one foreground command
goes into the brief as the session's first step on that base, and the session
returns if it fails; until the session reports it passed, the coordinator does
not push that base or remove the previous branch. When the
start is refused all the same, Buddy gives the work as a further brief to a
session whose return is integrated and whose model the new brief's model
matches, where §Buddy-to-Buddy allows it; otherwise
he uses what the host offers (a proposal the user starts; where the host asks
the user to start it, one line saying the start waits for the user's next
message in this chat) or, without it, does the work inline and with isolated
agents, and says so in one line (§Vehicle choice). Its state lives in the
handoff (the role entry, the list learned through failure, the programme agreement, each running session with its
brief and checkout, the open decisions), kept current as
`skills/knowledge_processor/continuous-maintenance.md` §Coordinator handoff says
(read it on taking the role and after compaction). A session starts no sessions
of its own; work it finds that needs one goes into its return as a proposal.

**One reading place.** The coordinator's chat is where the user reads. It writes
to the user when a return has arrived or the user has something to decide or do;
a session's turn end with neither gets no message of its own. Where such a turn
end starts a coordinator turn that must end in a reply, the reply is one line:
the session, that no return has arrived, and what the session says it waits for
and whether that wait is verified or its output is there
(`agents/buddy/background-wait.md` §Receiving a wait report), or, when §Session
end counts it as stopped, that it is stopped; nothing else
goes in it (a decision this needs from the user is a message of its own). After
each return, not in that line, it gives a status overview of the programme: each
item, its state and what waits on the user. A session's questions and decisions
for the user go to the coordinator (the blocking question below, the decisions
list in its return), which carries them to the user as
`skills/return_summary/SKILL.md` §Accuracy at handovers says. When the user
writes in the session itself, the session answers there. A session's permission
prompts appear in that session; the coordinator cannot answer them. A host
may stop a session's messages to other sessions after a number of them since
the user last wrote in it (`architecture-documentation/07-tool-integrations.md`
§Delegation vehicles); the coordinating chat is such a session, and its
messages to all its sessions count against its one cap. So a brief carries
everything the session needs up to its return, and the coordinator messages a session only
with a further brief, the answer to its blocking question or the one message
of `agents/buddy/background-wait.md` §Receiving a wait report. When the cap is
reached, a session's questions come in its return, a further brief waits for the
user's next message in this chat, and the coordinator tells the user in one line
that this message lifts the cap.

**Session end.** Once a session's result is integrated or discarded and no
further brief is planned for it, the coordinator offers the user to archive it
and archives it only on the user's yes. A session's wait notes are checked as
`agents/buddy/background-wait.md` §Receiving a wait report says. A session that stops, fails or stalls (a wait the
check finds neither running nor done; two turn-end notes in a row that bring no
return or question and name no wait; on a host without turn-end notices, two
coordinator turns with no new return, commit or record entry) is a stopped
writer under `agents/buddy/concurrent-writers.md` §Cancellation and resume,
named in the coordinator's next message. Without turn-end notices the
coordinator reads the return and record locations at each of its turns; without
archiving it names the session to close; without messages between chats a
question comes in the return and a further brief starts a new session. Host
abilities: `architecture-documentation/07-tool-integrations.md` §Delegation
vehicles.

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

**Buddy-to-Buddy.** A persistent session boots as Buddy. Its brief names the
outcome and stop condition, the session's model (`framework/models.md` §A
persistent session's model), the effort budget (Cumulative effort), the checkout
(shared, or its own worktree and branch, chosen by
`agents/buddy/concurrent-writers.md`), the division of work below, the commit duties
(`agents/buddy/concurrent-writers.md` §Commit, push and transfer), the return and
record location and any parsed-artifact contracts; for work on a task it
carries the block `## Approved acceptance (read-only)`
(`skills/_protocols/approved-acceptance.md`). Before writing such a brief, read
and follow `framework/spec-engineering-implementation-specs.md` §Convention: one
goal per change (one goal per brief, the size budget). A session takes a further
task only through a further brief, after its previous return is integrated, with
its checkout named again; it orders or commissions no programme work. A
compacted session rereads (below) and can take a further brief. It is replaced
by a new session briefed from its returns and records when its return shows that
context it needs is missing, or when the user asks. The session owns its work
item: its task or incident files, its build/research artifacts, the paths in its
manifest and its own close (where the project uses Forge tasks:
`task_status_update` with persist gate and cross-task sweep). The commissioning
Buddy owns integration, the handoff, plan or programme agreements and other
items, including the shared save. After compaction or resume the session rereads
its brief and its own build record (the decision file holds its budget, design
and dispositions) before continuing, and works from the brief's
approved-acceptance block as written. The session keeps its workflow's review
floors and returns a return artifact at the named location (plus the host's
notification where it has one), with its decisions list
(`skills/return_summary/SKILL.md` §Decisions I took for you), which the
coordinator checks and carries into its own message to the user. The coordinator
verifies load-bearing claims before integrating and does not read the transcript
mid-flight. At most one blocking question to the coordinator at a time.
