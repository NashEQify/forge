# Knowledge Processor — Continuous maintenance

Step-loaded unit of `skills/knowledge_processor/SKILL.md`. Read it at boot (LOAD, or step 3 of
`agents/buddy/boot-on-demand.md`) when a user scope is configured or the project's rules require ongoing knowledge
maintenance, and again after compaction; its rules apply from the first turn. Before the first write this
maintenance causes, and again after compaction, read `retrieve.md` for the baseline and follow `write.md`.

§Admission is the skill's one admission check. `write.md` §2 sends every write to it, in every mode; a reader who
comes from there without continuous maintenance reads that section only. A coordinating chat reads §Coordinator
handoff and §Admission when it takes the role and after compaction (`agents/buddy/coordinating-sessions.md`
§Coordinator), with or without continuous maintenance.

## Admission

Identify the future question/decision/continuation each candidate supports. Apply this admission check to topic
knowledge, continuation checkpoints, handoffs, history and FACTS candidates before classifying a delta:

1. **Required record:** an explicit request to retain a particular item or a domain
   audit obligation goes to its specified owner with its required evidence.
2. **Knowledge:** retain facts about the subject, the content of statements, commitments,
   decisions with their reasons, scoped preferences, events and observed experiences/outcomes. Record their meaning,
   implications and necessary detail. A statement being made, repeated or processed
   does not by itself add knowledge about its subject.
3. **Open work:** name the unfinished goal, leading owner or artifact, next action or
   blocker. Retain a constraint, approval boundary or failed attempt when it changes
   that next action. Update this checkpoint to the current state as work progresses.
4. **Conversation and execution trace:** when the candidate only records that
   something was said, drafted, attempted, rendered, processed, checked or edited, and
   adds no knowledge from step 2 or dependency from step 3, do not persist it in topic
   files, checkpoints, handoffs, history or FACTS. Tool calls, search sequences,
   intermediate outputs, draft versions, tool or rendering paths, layout fixes, routine
   confirmations, completed checks and edits are examples; their occurrence alone does
   not make them knowledge. A general wish to lose no information, or an ongoing task,
   does not make its entire course a record to preserve.

For mixed input, extract the finding, decision, outcome or remaining dependency and
drop the surrounding chronology. Before a write, name the future decision or next action
that would change without it; if there is none, do not write. If the current owner or
artifact and its pointer suffice to resume, retain the pointer and next action. A
different section name does not turn a trace into knowledge or necessary continuation
state.

## Coordinator handoff

A coordinator's handoff is current whenever a new or compacted chat would otherwise decide or act differently. In the
same turn in which the coordinator adopts or discards a return, settles a decision or a basic assumption with the user
(with its reason), starts, replaces or ends a session, or changes the programme order, it updates the handoff in place.
Where neither the user nor the project's rules exclude a commit (`agents/buddy/coordinating-sessions.md` §Commit, push
and transfer), it commits the update locally in the same turn. Nothing else triggers this write: a session's interim
notes, the coordinator's own checks and a discussion still in progress do not. At each trigger §Admission decides what
the update contains: what a future decision or next action needs. It does not push: a push needs the user's request or
the project's standing authorization. The full save runs on the user's command.

## Continuous maintenance

Configuring user scope authorizes its maintenance; project rules authorize project
maintenance. Honor explicit limits including “do not save”. Reconcile useful new
facts, decisions, corrections and changed state admitted by §Admission in the same
response cycle, before final output. Apply that admission check before preparing a
topic update or continuation checkpoint; it also governs handoff, history and FACTS.
A task-specific instruction remains with that task/topic. Checkpoint
substantive results before a topic switch; keep goal, next step, blockers and leading
files in the existing handoff. Preserve the applicable agreement, authorized changes
and unresolved requirements there or at their existing topic/task owner. New leading
drafts/results update their topic
pointer and handoff in the same operation, including externally stored results: the
pointer names the current artifact's location, state and any open review or approval,
not its version history.
After compaction/resume reread `framework/work-principle.md`, project rules,
configured boot set, full handoff and relevant topics; retrieve the applicable
agreement and unresolved requirements and apply its comparison before dependent
continuation. Check pending reconciliation before dependent work.

Every write updates rather than appends (`write.md` §5): first find where the subject already
stands in the scope, then change its leading owner in place, replace other copies by
a link or remove them once the owner is committed, and leave an unresolved
contradiction visible at the owner. A current-state section (status, open steps,
leading artifact) is rewritten to the current state, not extended by a dated paragraph;
in the same write remove open steps the current state shows done or replaced, keeping
any decision with its reason and any approval boundary they carried. Event entries,
history and dated records marked as not current stay as they are. Keep at the claim what its meaning needs (scope; a date
only where the claim's age matters; a source only when it is not the scope's own
person); the change's provenance goes into its commit, never into a second statement of
the claim (`write.md` §4). Dated records marked as not current (earlier
interpretations, retained erroneous claims, events) are not copies; leave them.

FACTS line while continuous maintenance applies:
`FACTS: keine | {Fakt} → {Ziel} [geschrieben|deferred:{Grund}]`.
Report only actual writes of admitted knowledge or continuation state. `FACTS: keine`
is the normal outcome of a turn spent working on an artifact; when such work yields an
entry in every turn, recheck those entries against §Admission. Private deferred payloads never enter another repo's
handoff. A blocked write is **not persisted**; state target and reason in the
conversation, retry only with available source and authorized writable owner.
Project deferrals may stay in that project's handoff. Conversation-only retention
cannot promise recovery after context loss.
