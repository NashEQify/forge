# Save — common session continuity

Read and follow `framework/work-principle.md` before taking up work.
Resolve this reference against the framework root; retain the consumer CWD.


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

Read the whole existing handoff through the common snapshot. The handoff is the
current state the next session needs, not a log. Every write rewrites it to that
state and does not append to it. It keeps:
- current coordination and actual running-job status;
- the held-back list (`framework/process-map.md` §Authorization): one entry per
  held-back task or path set with reason, owner and releasing event, cleared once its
  work is committed or published;
- open topics, each with goal, current state, leading file and next step or blocker,
  plus the decisions, failed attempts, approvals with scope/limits and deferred work
  the next step needs.

Remove closed work and superseded facts entirely; their results live at their owners
(commit, task return, history, overview). Keep a one-line pointer only while an open
item still depends on it. Preserve open topics another session owns and concurrent
changes; completion of one topic does not close others. No nine compulsory
headings. A handoff much longer than a screen per open topic carries history: prune it.

Prepare affected knowledge, navigation, latest-result pointers, handoff and any
warranted history as a scoped operation. Knowledge changes update existing owners in
place (KP §5); a restructuring the session showed to be due (KP §6) may run here. Publish through the protected helper, with
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
`git add .` or foreign staged changes. Follow the repository's commit policy. The
commit message of the repository that holds a knowledge change carries its provenance
and any restructuring mapping (KP §4, §6); provenance of a user-scope change never
enters another repository's commit (`framework/user-scope.md` §4).
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


### Observational workflow checks

Navigation/recovery never execute commands. Use existing authorized tools for
actions and observe their actual current outcome. The manual action checkpoints
require nonblank evidence supplied with the current `--complete --evidence`
invocation, including force. Missing/failed/timed-out/unknown outcomes stay open
with the concrete blocker; no-new-commit save still requires current persistence
observations for applicable project/user roots and required remotes. Completion
is agent-confirmed, never engine proof of free-text truth or remote correctness.
See `framework/workflow-engine-cookbook.md` for the retained completion contract.
