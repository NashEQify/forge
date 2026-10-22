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

## Legacy compatibility obligations

Old save and housekeeping definitions keep workflow/step IDs, routes, completion
checks, variables and evidence interpretation. For `validate-reconciliation`, retain
its unfinished task-status/plan checks when the legacy session selected development;
for `workflow-handoff-context`, restore/export exactly the selected authoritative
runs through this adapter. Missing legacy selection is an explicit blocker, never a
silent no-op. Existing checked evidence is not reset or reinterpreted by a new label.
Housekeeping area progress remains readable, while the shared publication journal
protects actual multi-file mutation.

Installation validates explicitly supplied project runs before activation and before
rollback, including state created/advanced after upgrade. Incompatible state keeps
sessions stopped until repair or validated mapping; no blanket state rewrite.

## Lock ownership

Engine locks protect exact engine state; continuity locks protect handoff publication.
Acquire/release engine snapshots before publishing the envelope; do not hold nested
cross-owner locks. The common layer imports no engine and promises no global
cross-repository transaction. State references remain authoritative after export.

## Reconcile and close selected obligations

A required task check has the stable identity `task:<numeric task ID>`; a plan
check has `plan:docs/plan.yaml`. Task archive relocation retains its identity and
must agree with the authoritative task file's `id`. Task statuses come from the
plan/task owner. Rebinding adds obligations; changing an existing expectation
requires explicit `reconcile`, which replaces that identity's expectation while
retaining every other obligation and records its prior value, reason and evidence.
It cannot remove an obligation or invent a successful task transition. Run the
owner's task-status process first, then submit the observed authoritative status:

```json
{"binding_id":"selected-work","reason":"Task owner completed and archived work",
 "evidence":"docs/tasks/archive/123.yaml",
 "required_checks":[{"kind":"task","path":"docs/tasks/archive/123.yaml",
                     "expected_status":"done"}]}
```

Use the same project/handoff CLI arguments with `reconcile`. Failed target checks
leave the persisted envelope unchanged. Other bindings retain their independent
status and unfinished work.

Task-only work remains unfinished until explicit `close` with `binding_id`,
`reason`, and `evidence`. Close revalidates every selected obligation: workflows
must be terminal according to the engine; tasks must have an owner-recognized
terminal status. Plan validity alone and an empty selection cannot prove completion.
Failed close preserves all obligations. A successful close retains a verified
receipt and becomes historical; later export/restore preserves that receipt without
reopening completed checks. New work requires a new binding identity.

The engine exports `lifecycle: {status, terminal}` for each selected workflow.
An authoritative abort is terminal even when untouched steps remain pending or a
prior pause flag remains set. Abort does not discharge task/plan checks. Archived
identity must be unique across active and archive storage even after a retained
reference has relocated. Loading and inspection never change pause or progress.

## Definition compatibility

The engine fingerprints all loaded definition fields conservatively, including
manual instructions, completion checks, required flags, dependencies, commit gates,
iteration limits, skill/context references and unknown future fields. Only display
step names and top-level discovery/provenance metadata (`description`, `need_phrase`,
`trigger`, `derived_from`) are excluded; engine defaults normalize omitted values.
Schema and status validation remain independent of definition compatibility.

`continuation_compatible(workflow, observed_fingerprint, current_fingerprint,
direction=None)` accepts identical fingerprints or an exact reviewed transition in
`framework/workflow-compatibility.yaml`. Explicit `upgrade`/`rollback` restricts the
permitted direction; omitted direction infers it from the exact pair. The manifest
records workflow, prior/current hashes, allowed directions, acceptance and the
preserved-obligation review pointer. That pointer is review provenance, not a runtime
requirement to install private review documents. There is no name/step-count bypass.
The reviewed Task398 save/housekeeping pairs cover only their exact definitions;
any further instruction or execution change requires another reviewed transition.
