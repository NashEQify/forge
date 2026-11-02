# Coordinated installation activation — full-path procedure

Step-loaded unit of `framework/installation-activation.md`. Read it once §Choosing the path there classifies a change
as full path: before stopping sessions or changing source, and through prepare, install, validation, retry and
rollback.

## Before changing source (full path)

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

Installed is not committed. Status and `prepare` list `uncommitted_sources`:
recorded or current framework sources whose live bytes Git does not have in `HEAD`
(ignored host-owned paths and nested repositories excluded), and status says
`operation_open` while a prepared or validation-pending operation is open — the
phase, not proof that anyone drives it. It is a
warning, not a readiness refusal, because an activation's commit follows its
validation. `validate` records `completion_commit_state` — `HEAD` and
`uncommitted_count_at_completion`, a snapshot not updated by later commits;
rollback removes it. The activation's owner commits the installed generation, or
records why not and who will, before the next task starts. Before `prepare`, the
previous generation is committed or its deferral recorded; otherwise generations
pile up uncommitted under successive baselines. Known limit: installed bytes moved
out of the working tree afterwards (stash, reset, revert) are not reported as
uncommitted; status still lists them as `instruction_drift`. A linked worktree
inside the framework tree enters the source inventory and makes readiness refuse
(`recovery_required`); cut worktrees outside it.

## Install and verify

Preflight the complete selected dependency closure, old installed routes, ownership
and exact legacy state interpretation before changing integration. Preserve the recorded
profile, hosts and method selection on repeat installation. Generated wrappers stay
thin forwards to canonical contracts. Full availability does not select development.

Apply within the established window. Validate actual installed entrypoints, source
fingerprint, profile, configuration and selected closure. Use a fresh session for the
installed generation: normal entry, relevant retrieval, capture/save/resume, and exact
selected development continuation where applicable. For the fresh acceptance session, use `cc --forge-validation-operation <UUID>` or
`oc --forge-validation-operation <UUID>` with the exact pending operation. This
checks the fully applied source/integration generation without marking ordinary
sessions ready. An incorrect ID, partial application or changed source refuses entry.
The readiness guard has one form: `forge_install.py --maintenance status
--require-ready`, with `--validation-operation <UUID>` for the acceptance session.
`--require-ready` or `--validation-operation` without `--maintenance status` is a
usage error (rc 2) and installs nothing.
Existing sessions are not silently upgraded. Record evidence and concrete limits; mark complete only for verified targets.
This procedure verifies the installation, not the code: after a hash-checked transfer of
identical bytes the test suite is not rerun (development capability: the testing skill's
§Test selection).
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


Compatibility inventory uses engine-owned maintenance validation for every retained
active/archive record. Supported, structurally valid archived completion or abort
is historical observation even when its old step/route vocabulary has retired.
Archive placement alone does not establish terminality. All unfinished carriers
retain strict current-definition interpretation and exact directional mappings;
ordinary selected-work continuation/export is unchanged. State bytes, identities,
revisions, paths, evidence and pause/progress are never rewritten by inventory.

If the installed predecessor cannot prepare that inventory, reviewed candidate
installer modules may use the existing `forge_install.main(argv, framework=target)`
interface with `--maintenance prepare --consumer-root <root>`. Resolve imports to
the reviewed coordinator/policy while `framework` names the actual installed source
root. The genuine target inventory and integration before-images form the baseline;
this is not an alternate journal format or permission to change source first.
Preparation persists a prepared operation before compatibility export: a failure
may leave an unfinished operation requiring supported recovery. Preserve its exact
identity and journal; never replace it with a fabricated successful baseline.
