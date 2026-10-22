# Protected continuity operations

This is the common storage interface; semantic decisions belong solely to
`skills/knowledge_processor/SKILL.md`, location/privacy to `framework/user-scope.md`.
No development engine is required. All cooperating Forge writers (including
migration and housekeeping) use this boundary. A project-only visitor checks only
project recovery, without resolving or reading another person's pending facts.

## Scope and authorization

`python3 <framework>/scripts/continuity.py <snapshot|publish|recover>
--scope <project|personal> --project-root <verified-project>` accepts JSON on stdin
and emits versioned JSON. Keep private payloads out of arguments and foreign files.
Personal scope uses the existing machine user configuration, never an invented root.
Project paths are relative to the project root; personal paths are relative to the
resolved personal content root. Resolve the helper's returned scope before writing.

Project recovery is `context/maintenance-pending.md`; personal recovery is
`context/user/maintenance-pending.md` in the user repo. Distinct scopes remain
distinct when roots coincide. A project operation cannot access `context/user/`.
The helper rejects traversal, unsafe links and reserved control files. Never bypass
that rejection with raw writes or disable containment to make an operation succeed.

The stable lock files are local coordination metadata, not knowledge. Keep them
out of Git using a scoped `.gitignore` entry (`.continuity-*.lock`); never unlink
a lock after use because another cooperating process may still hold its inode.
A consumer integration may add this ignore without moving knowledge.

Locks protect cooperating participants only. An external editor/nonparticipating
agent requires an established exclusive maintenance window or equivalent storage
protection. Otherwise defer affected writes. A flag is not evidence that writers
have stopped. Read-only filesystem permissions or unavailable locking may prevent
a coherent snapshot; state the limit rather than assert coherence.

## Snapshot before dependent reasoning

Send `{"schema_version":1,"paths":["context/topic.md","context/navigation.md"]}`
to `snapshot` for project scope (personal paths use its returned content root).
Response includes `scope`, `files` keyed by path with `text`/`sha256` (null for absent),
`pending_operations`, `snapshot_token`, and `invalidated_paths`.
The helper captures pending status and all requested files under one scope lock,
then releases it before model reasoning. Do not hold locks while waiting for a user
or model. Required reads must be in this coherent set.

For additional dependent reads send `{"paths":["context/evidence.md"],"previous":
<prior-token>}`. The union is recaptured. If earlier observations were invalidated,
reason from the new complete set; never combine old A with new B. Two empty pending
checks are insufficient: a publication may complete between them. This is a
same-scope guarantee; cross-repository coherence is not globally atomic.

On boot/resume check each authorized relevant scope via snapshot before dependent
profile/handoff/topic use. A nonempty pending result requires recovery inspection
and reconciliation, or a qualified/blocked dependent answer. It cannot be bypassed
by PRESENT or by finding the desired text already in an owner.

## Conditional publication

After semantic reconciliation prepare one JSON request with:

- `schema_version: 1`, the `snapshot_token`, and unique `operation_id`;
- concise `intended_change`, `source_references` and complete `affected_paths`;
- `replacements`, mapping affected paths to intended text (null means deletion).

Include every depended-on baseline in the snapshot; absence must also be captured.
Do not edit these files directly after snapshot. Publish protects comparison through
atomic replacement and rejects stale baselines. Exit 3 means recapture and reconcile,
never retry prepared text blindly. Exit 2 means invalid scope/access/request; exit 4
means pending/blocked recovery. Exit 0 alone is insufficient: inspect returned status.

For multifile changes a durable scoped pending record precedes the first content
mutation. It records operation identity, baselines, intended changes/sources,
proposed results and completed/remaining work. If it cannot be written, nothing is
published. Atomic single-file replacement needs no separate journal. No-op changes
do not produce content churn. Report `complete`, `not_persisted`, or
`owner_updated_reconciliation_pending` accurately.

## Recovery without stale replay

Call `recover` in the same scope with relevant extra `paths` if needed. It returns
`snapshot` (fresh coherent files/token) and `operations` with actual-file
classifications. Inspect intended changes, original/proposed/current bytes and
known dependents. A crash can occur after replacement but before progress recording;
completion flags alone are not authority. Later corrections must survive.

Reconcile semantics outside the lock. Publish against `snapshot.snapshot_token`,
include `recovery_operation_id`, and cover the whole affected set with reconciled
results. Clear only the completed target operation when all its owners/routes agree;
other operations remain. Another recovery/writer may have changed state: stale token
means fresh inspection, not resurrection of an old operation. If recovery is blocked,
retain scoped evidence, report partial persistence and qualify dependent answers.
No complete-save claim while required reconciliation remains pending.

For migrations capture working-tree content (including uncommitted qualifiers),
keep private source/claim maps in their consumer, and reconcile in bounded batches.
Each completed batch must have usable routes; pending recovery survives interruption.
Authorization and source preservation are not supplied by the helper itself.
