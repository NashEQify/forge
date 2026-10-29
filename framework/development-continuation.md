# Development contribution to continuity

Development owns software task/plan validation, workflow interpretation and closeout
audit requirements. Common continuity carries its envelope opaquely. This file is
loaded only for software work selected by intent, explicit development invocation,
or an existing durable binding—not by install profile or file presence.

## Select before progressing

Use `scripts/development_continuation.py bind` with the canonical project root,
existing handoff path and an explicit selection basis/evidence. Bind selected
workflow identities and authoritative state references; task/plan-only software work
binds required checks with an empty workflow list. Retain all unfinished bindings,
including those created in previous sessions. Do not select unrelated engine runs.
Use existing handoff names (`session-handover.md` and workspace variants included).

The envelope identifies version, binding ID, basis, project root, exact workflow IDs
and state references, observed revisions/fingerprints, checks, status and blockers.
Its lifecycle belongs to the adapter; do not hand-edit or reconstruct it from a
truncated `--handoff-context` display. Export after selected work changes and before
common save. Common save carries the resulting contribution once, with no repeat
engine discovery or checks.

## Export and restore

`export` captures only bound workflows through the engine's protected exact-state
API. Authoritative files retain full route, variables, progress and evidence. Run
required task-status reconciliation through the existing task_status_update process
and validate the selected project's plan when applicable. A missing required state
or failed check yields partial/blocked contribution, never a cached complete claim.
Software closeout retains SPEC-374 history/retro obligations; common history rules
do not erase them.

`restore` validates bound references, schemas and current state without advancing,
unpausing or completing anything. Do not call engine `--resume` for session loading:
that command changes pause status. Valid newer revisions are current evidence,
never overwritten with the saved revision. Resolve completed archived instances by
exact unambiguous identity. Revalidate before actual progression.

Legacy state without binding needs explicit session evidence naming selected runs
or task-only software work. Ambiguity blocks exact continuation; it is not permission
to bind everything in `.workflow-state`. The user may continue unrelated ordinary
work while the domain blocker remains visible in common context.

## Checks, envelope and close

When the adapter's task or plan checks run, when an export changes the envelope or its owned handoff region, and
when selected obligations are reconciled or closed: read and follow `framework/development-continuation-close.md`
(check receipts, legacy compatibility obligations, the owned envelope region, reconcile and close, definition
compatibility, creation-bound observational checks).

## Lock ownership

Engine locks protect exact engine state; continuity locks protect handoff publication.
Acquire/release engine snapshots before publishing the envelope; do not hold nested
cross-owner locks. The common layer imports no engine and promises no global
cross-repository transaction. State references remain authoritative after export.
