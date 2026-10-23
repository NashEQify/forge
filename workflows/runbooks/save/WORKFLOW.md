# Save — common session continuity

One entry for mid-session and end-of-session persistence, independent of development.
Apply `skills/knowledge_processor/SKILL.md` and `framework/continuity.md`. Use the
verified active workspace and its existing handoff naming; no fixed personal CWD,
software task graph or engine is a prerequisite. Availability and file presence do
not select development. No new daily user command is required.

## 1. Orient and reconcile

Read project permissions, navigation and current handoff under the protected
snapshot boundary. Check scoped pending recovery before dependent work. Personal
scope is separately authorized/resolved; private deltas never enter project recovery
or a project handoff. Follow actual workspace ownership when CWD is an external
artifact directory. Inspect Git status only where Git exists.

Reconcile useful session/checkpoint deltas at their existing owners through KP.
Triage an existing session buffer without dropping unresolved work (step
`dispatcher-final`, the inline dispatcher final run). Framework-feedback
routing is optional only when an authorized framework contribution is actually in
scope; generic save requires neither that repo nor its development files.

Carry any explicitly selected domain contribution in the handoff. That domain's
adapter validates and returns its contribution once. No binding/selection means no
domain checks. Unavailable required contribution makes save partial; common context
can still be saved with its concrete blocker. Mere task/plan/state files are not
selection. Keep opaque unfinished contributions from previous sessions unchanged
unless their owner supplies an updated contribution.

## 2. Publish coherent continuation

Read the whole existing handoff through the common snapshot. Preserve untouched
open topics and concurrent changes; update worked-on topics with goal/current state,
leading file and next step/blocker. Include necessary decisions, failed attempts,
approvals with scope/limits, deferred work and actual running-job status. No nine
compulsory headings. Closed work needs at most a leading-result pointer; useful
history/evidence stays at its owner. Completion of one topic does not close others.

Prepare affected knowledge, navigation, latest-result pointers, handoff and any
warranted history as a scoped operation. Publish through the protected helper, with
durable pending recovery before multifile mutation. Do not parallelize dependent
writes or overwrite after an unprotected last reread. Stale baseline: recapture and
reconcile. Crash/blocked dependency: keep scoped recovery and report partial save.
For separate repositories use separate authorized operations; no global transaction.

History follows KP's meaningful trajectory/decision/obligation threshold, not session
length or save frequency. Domain-mandated audit evidence remains effective through
the selected contribution. Preserve immutable history and unique source meaning.
Remove only buffer items actually reconciled (step `buffer-cleanup`, the
session-buffer cleanup). Verify all required routes and pending
work before claiming complete. Keep useful open defer premises with their revisit
condition in the handoff; no software task system is invented for this purpose.

## 3. Commit, push and verify where authorized

Review diff/staged content for secrets, temporary output and unintended changes; use
an available secret scanner. Stage concrete authorized paths/hunks, never a blanket
`git add .` or foreign staged changes. Follow the repository's commit policy.
An explicit user `save` is a commit-and-push request for the active project's tracked
upstream unless its rules restrict it. This runbook never widens permissions. User
repo changes are persisted separately under that repo's own rules. No force-push,
reset, automatic stash, rebase or branch switch. Without Git, local continuity still
works; no repository is manufactured to save ordinary knowledge.

Check written files, routes and pending status. In Git run `git diff --check` and
status; after an authorized push compare local commit with the tracked remote branch.
Report actual knowledge/handoff/history outcome, commit/push or reason omitted, and
concrete partial-persistence/domain blockers. Foreign untouched diffs are not failures.
Do not represent a successful local save as a successful push.

## Compatibility

The existing `save` skill/command and runbook path remain entrypoints. New ordinary
save invokes this common procedure directly. Historical engine-driven save retains
`workflow.yaml` step IDs and completion meanings; the development adapter forwards
those steps without discarding pending task reconciliation or workflow export
obligations. Engine-specific interpretation lives solely in
`framework/development-continuation.md`, loaded only for selected/bound development.
