# Knowledge Processor — Continuous maintenance

Step-loaded unit of `skills/knowledge_processor/SKILL.md`. Read it at boot (LOAD, or step 3 of
`agents/buddy/boot-on-demand.md`) when a user scope is configured or the project's rules require ongoing knowledge
maintenance, and again after compaction; its rules apply from the first turn. Before the first write this
maintenance causes, and again after compaction, read `retrieve.md` for the baseline and follow `write.md`.

## Continuous maintenance

Configuring user scope authorizes its maintenance; project rules authorize project
maintenance. Honor explicit limits including “do not save”. Reconcile useful new
facts, decisions, corrections and changed state admitted by `write.md` §2 in the same
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

**Admission core** (summary of `write.md` §2; read `write.md` before the first write,
this summary does not replace it). Persist: an item the person explicitly asked to
retain or an audit obligation requires, at its specified owner; knowledge about the
subject (facts, the content of statements, decisions with reasons, scoped preferences,
events and outcomes); open work (goal, leading artifact, next step or blocker, plus a
constraint, approval boundary or failed attempt that changes that next step). Do not
persist a trace whose only content is that something was said, drafted, attempted,
rendered, checked or edited, such as draft versions, tool or rendering paths, layout
fixes or completed checks. Before a write, name the later question or next step that
would change without it; if there is none, do not write.

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
entry in every turn, recheck those entries against the admission core. Private deferred payloads never enter another repo's
handoff. A blocked write is **not persisted**; state target and reason in the
conversation, retry only with available source and authorized writable owner.
Project deferrals may stay in that project's handoff. Conversation-only retention
cannot promise recovery after context loss.
