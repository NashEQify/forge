# Coordinated installation activation

Canonical shared source/update/install/recovery procedure. One release and installer
serve all profiles and users. This release supports stopped-session maintenance,
not live switching of mutable framework sources. Ordinary knowledge work still uses
its existing folder and commands; this procedure is for the maintainer's upgrade.

## Before changing source

1. Identify explicitly affected local source checkout, installed host integrations,
   selected profile/methods and authorized consumer roots. Preserve current user
   configuration and local edits. Do not discover or operate on unrelated machines.
2. Establish that affected agent/editor sessions will not read or write the changing
   source/integration set. Stop them **before** pull or source edits and through
   install/verification. A standing pull permission is not this evidence. A running
   agent may load another skill later even if its earlier instructions are cached.
3. From the currently installed generation prepare a recoverable actual working-tree
   source/integration baseline through the installer maintenance entry. Git HEAD or
   old wrappers alone are insufficient. Include local edits, old routes, new closure
   and exact explicitly selected legacy workflow state compatibility.
4. Only then perform an authorized source update. No hidden reset, stash, rebase or
   hand-moving skills. Missing sparse sources may be supplied safely within the normal
   procedure or produce a recoverable preflight failure before integration changes.

Boot and remote SessionStart hooks must not independently pull/setup the framework.
They report the maintenance need and use this procedure. Consumer-only Git updates
still follow their own authorization and preservation rules.

## One activation owner

`scripts/forge_install.py` coordinates `scripts/install_activation.py` with existing
managed-file ownership checks. All ordinary setup entrypoints participate. Public
maintenance operations: `--maintenance prepare|status|retry|rollback|validate`, with
`--operation-id` for the exact prepared operation, explicit `--consumer-root` values
and `--validation-evidence` for fresh-session verification. Inspect current `--help`
for request shape; never manufacture validation evidence to close a journal.

The activation owner serializes overlapping machine-local operations across checkouts
under one stable effective-UID lock. Protection starts before journal/resource baseline
reads and spans durable phase updates; retry/rollback revalidate after acquiring it.
Do not unlink a lock or use an environment flag to bypass it. Journal operation identity
and lease prevent replacement of unfinished work between maintenance commands.

Phases: `prepared`, `applying`, `validation_pending`, `complete`, `recovery_required`,
`rolled_back`. The private installation journal stores the matched source/integration
baseline and action progress; it is not a consumer knowledge file. `--check` and status
are read-only observations, not installations or completion evidence. A skipped host
integration cannot be reported as a completed whole installation.

## Install and verify

Preflight the complete selected dependency closure, old installed routes, ownership
and exact legacy state interpretation before changing integration. Preserve daily/full
presets and optional method selection on repeat installation. Generated wrappers stay
thin forwards to canonical contracts. Full availability does not select development.

Apply within the established window. Validate actual installed entrypoints, source
fingerprint, profile, configuration and selected closure. Use a fresh session for the
installed generation: normal entry, relevant retrieval, capture/save/resume, and exact
selected development continuation where applicable. For the fresh acceptance session, use `cc --forge-validation-operation <UUID>` or
`oc --forge-validation-operation <UUID>` with the exact pending operation. This
checks the fully applied source/integration generation without marking ordinary
sessions ready. An incorrect ID, partial application or changed source refuses entry.
Existing sessions are not silently upgraded. Record evidence and concrete limits; mark complete only for verified targets.
Repeating a completed install must be idempotent and never rewrite consumer content.

## Failure, retry and rollback

On conflict keep integration unchanged. If the preceding source update already changed
referenced files, unchanged wrappers do not prove the old generation usable: keep
sessions stopped until repair/retry or matched restoration. Interrupted application
remains unverified with a durable journal; do not resume a partially applied generation.
Retry accepts only journal-proven states. Unknown later edits cause conflict, never
silent overwrite. Rollback selectively restores matched source/integration and retains
all consumer knowledge and subsequent work. Do not reset a repository.

Legacy save/housekeeping/development identities, step meanings, routes, variables,
evidence and pending obligations remain valid through compatibility forwarding.
Validate retained state before activation and rollback, including state created or
advanced since upgrade. If the target engine cannot interpret it safely, refuse
activation/resumption until a validated mapping or compatible generation exists.
Restoring bytes alone is not compatibility. No blanket workflow-state rewrite.

## Consumer integration

Only authorized small reviewed changes remove duplicated general algorithms from
consumer rules. Keep concrete topic owners, storage, language, safety and approvals.
No automatic content reorganization or re-import belongs to the upgrade. Separately
authorized migrations preserve working-tree baselines, claim maps and usable routes.
A withheld/coordinate-before-access consumer must not be inspected until that boundary
is met; a synthetic fixture is not live acceptance. Keep each target's outcome distinct.
