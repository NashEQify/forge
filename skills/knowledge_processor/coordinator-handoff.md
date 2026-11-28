# Knowledge Processor — Coordinator handoff

Step-loaded unit of `skills/knowledge_processor/SKILL.md`. Read it when a chat takes the coordinator role and after
compaction (`agents/buddy/coordinating-sessions.md` §Coordinator), with `continuous-maintenance.md` §Admission, which
decides what each update contains.

A coordinator's handoff is current whenever a new or compacted chat would otherwise decide or act differently. In the
same turn in which the coordinator adopts or discards a return, settles a decision or a basic assumption with the user
(with its reason), starts, replaces or ends a session, understands why something it tried failed, or changes the programme
order, it updates the handoff in place.
Where neither the user nor the project's rules exclude a commit (`agents/buddy/concurrent-writers.md` §Commit, push
and transfer), it commits the update locally in the same turn. Nothing else triggers this write: a session's interim
notes, the coordinator's own checks and a discussion still in progress do not. At each trigger §Admission decides what
the update contains: what a future decision or next action needs. It does not push: a push needs the user's request or
the project's standing authorization. The full save runs on the user's command.

**Learned through failure.** The handoff's running part (the role entry, the programme agreement, running sessions,
open decisions, under one heading of their own) opens with a list `Learned through failure`: each entry a constraint this programme learned when
something it tried failed, written as what was tried, why it failed and what to do instead, in the turn the failure is
understood. Only a failure that happened enters, not a warning or a guess. A chat that takes the role and a compacted
coordinator read this list before acting on the rest of the handoff. An entry is rewritten in place when the lesson
changes, and leaves when the programme ends or when a framework or project rule carries it.

**Bound.** The running part stays within 6,000 bytes (`wc -c` over its heading's section, the list included; intent: a
new or compacted chat reads it whole before acting, beside its boot units). An update that would pass the bound first
moves out what is done or settled (finished items, decisions with their reasons) to the work unit's records or the
project's history (`history-imports.md` §6), leaving one pointer line per moved item, then writes the update. When the running part still passes the bound, the coordinator says so to
the user in one line and asks whether to split the programme.

