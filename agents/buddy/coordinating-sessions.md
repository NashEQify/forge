# Buddy — Coordinating sessions and writers

Step-loaded unit of `agents/buddy/operational.md` (Phase 2: ACT). Read it when
starting, ordering or commissioning programme work, when working as or with a
persistent session, when a second writer is involved, and before committing in
a shared checkout. The core's Applicability holds: these requirements apply to
`software`; for `on-demand` follow the project's working rules.

**Programme order.** The agreement's order is the reference for which task
comes next; a plan file's critical path counts only where it matches the
agreement (stale or empty → ask). Before starting, inserting or reordering a
task while a programme is active, compare it with that order, whether or not
the task is listed in it; the agreement comparison in
`framework/work-principle.md` covers order as well as scope. Inserting a task
ahead of the agreed next one, starting tasks in parallel, or changing the order
in the agreement needs the user's confirmation, recorded with the change
("confirmed by …"), unless the user explicitly delegated that choice; a general
grant of autonomy or permissions is not that delegation. A rationale alone makes
it a proposal: the agreed next task runs, or nothing does. The coordinator
starts a programme task itself (`task_status_update` → `in_progress`, which runs
this check) before commissioning its session, worktree or staging copy, and the
brief names the start; the session does not repeat it. Before commissioning the
next task, reconcile what the previous one held back (`framework/process-map.md`
§Authorization).

**Buddy-to-Buddy.** A persistent session boots as Buddy. Its brief names the
outcome and stop condition, the effort budget (Cumulative effort), the
checkout (shared, or its own worktree and branch), the division of work below,
the return and record location and any parsed-artifact contracts; for
work on a task it carries the block `## Approved acceptance (read-only)`
(`skills/_protocols/approved-acceptance.md`). Before writing such a brief, read
and follow `framework/spec-engineering-implementation-specs.md` §Convention: one
goal per change (one goal per session, the size budget). The
session owns its work item: its task or incident files, its build/research
artifacts, the paths in its manifest and its own close (where the project
uses Forge tasks: `task_status_update` with persist gate and cross-task
sweep). The commissioning Buddy owns integration, the handoff, plan or
programme agreements and other items, including the shared save. After compaction or resume the
session rereads its brief and its own build record (the decision file holds
its budget, design and dispositions) before continuing, and works from the
brief's approved-acceptance block as written. The session keeps its workflow's
review floors and returns a return artifact at the named location (plus the
host's notification where it has one), with its decisions list
(`skills/return_summary/SKILL.md` §Decisions I took for you), which the
coordinator checks and carries into its own message to the user. The coordinator
verifies load-bearing claims before integrating and does not read the transcript mid-flight. At
most one blocking question to the coordinator at a time.

**Commit, push and transfer.** Put the responsibilities into the brief before
dispatch. Use this wording for a work item that authorizes local commits:

> Commit your checked changes locally in the assigned checkout and return the
> commit ID and check results. If a push or live transfer is due, identify the
> outgoing commits or exact artifact and its intended destination. I handle
> integration, push and live transfers from the coordinating chat.

The working chat can make those commits without another user confirmation,
including while a transfer is pending. An explicit no-commit instruction or
a repository restriction still applies. The coordinator checks the outgoing
range or artifact against the user's original grant in its own chat, including
the remote and branch or live host and path. It acts under that grant for as
long as the action, content and target remain covered. A changed scope needs
authorization for the change. A peer handoff supplies evidence for the action
and cannot extend the grant. Destructive actions and safety-floor waivers still
require their own authority under `framework/process-map.md` §Authorization.
If the host denies an action, follow its decision
in the executing chat and continue independently authorized work.

**Concurrent writers.** Independence decides, not habit. Work on the same
files or a sequence of dependent items runs one writing workstream per
checkout at a time (a session with its own delegates, or one coordinator
delegate); meanwhile others only read or write files the brief names as
theirs, and the coordinator integrates after each return before
commissioning the next writer. Independent items that should progress at
the same time — for example several unrelated incidents, or tasks in
different areas — each get their own worktree and branch from the base
branch. Independence is verified, not read from task areas: the items contend
for no shared hook, test machine or installation window; the base commit is
the installed generation (installer status is `complete` with no uncommitted
sources, the main checkout's index matches `HEAD`, and no path a branch touches
has uncommitted changes there); their merge targets do not overlap; and the
user's working mode allows parallel work. A parallel start of programme tasks
also needs the confirmation in §Programme order. Cut worktrees outside the
framework tree: inside it the installer counts their files as unrecorded
sources and readiness refuses. A host that cuts session worktrees inside the
checkout by default (the Claude desktop app uses `.claude/worktrees/`) gets
the worktree path from the coordinator, cut beforehand. Otherwise run them in sequence. The spec and the code of one delivery
are one workstream: from the build workflow's Prepare phase on they live
on one branch in one checkout, because its review package and capture
cover one checkout (`skills/code_review_board/review-package.md` §BASE). Each workstream
commits on its branch, including its close. Inside
a workstream writers stay sequential; parallel agents only for read-only or
independent work on different files.

Integration follows the repository's rules — a pull request and its review
where the repository uses them, otherwise a merge by the coordinator — one
branch at a time, with the repository's checks on the branch and on the
merged result (the project's full gate where it names the merger as its runner:
`skills/testing/lean-suite.md` §Change-scoped runs and the full gate), activation where the change needs it (on a coordinated
machine, a merge that changes a non-Markdown installed source is a full-path
activation: prepare before the merge, `framework/installation-activation.md`
§Choosing the path), and push where
authorized; then the worktree and branch are removed. Commits in a shared
checkout go by path (`git commit -- <paths>` or explicit path staging), never
blanket staging or another owner's staged entries. Before pushing the base
branch, fetch and merge if the remote moved; no force-push or history
rewrite without explicit authorization.

**Cancellation and resume.** A stopped writer's files or branch stay as they
are. The coordinator resumes it, finishes what is usable, or discards it
only with the user's confirmation; no other writer is commissioned on that
checkout or branch until then. Known limit: Forge's PLAN-VALIDATE hook reads
task files from the staged candidate, so a stopped writer's half-edited task
file that is already staged blocks every commit there until it is resolved.
