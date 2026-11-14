# Buddy — Concurrent writers

Step-loaded unit of `agents/buddy/operational.md` (Phase 2: ACT). Read it when a
second writer is involved (a session, a delegate or another chat writing the
same repository), before cutting a worktree for a writer, before committing in a
shared or assigned checkout, before integrating a branch, and when a writer stopped.
Applicability: the core's (`software`). Sessions and their coordinator:
`agents/buddy/coordinating-sessions.md`.

**Concurrent writers.** Independence decides, not habit. Work on the same
files or a sequence of dependent items runs one writing workstream per
checkout at a time (a session with its own delegates, or one coordinator
delegate); meanwhile others only read or write files the brief names as
theirs, and the coordinator integrates after each return before
commissioning the next writer. Independent items that the user's order needs
at the same time (§Parallel start) — for example several unrelated incidents,
or tasks in different areas — each get their own worktree and branch from the base
branch. Independence is verified, not read from task areas: the items contend
for no shared hook, test machine or installation window; the base commit is
the main checkout's `HEAD` (its index matches `HEAD`, and no path a branch
touches has uncommitted changes there); their merge targets do not overlap,
compared by file and not by task area (two items that edit one instruction unit
overlap, and an item whose planned additions take a unit past the byte cap of
`scripts/consistency_check.py --check instruction-units` counts every unit a
split of it can reach as its target); and the user's working mode
allows parallel work (§Parallel start). Cut worktrees outside the
framework tree: inside it every host and check that reads the tree in place
reads their files too. A host that cuts session worktrees inside the
checkout by default (the Claude desktop app uses `.claude/worktrees/`, and the
Claude Code CLI's `--worktree` does per its documentation) gets the worktree
path from the coordinator, cut beforehand. Otherwise run them in sequence. The spec and the code of one delivery
are one workstream: from the build workflow's Prepare phase on they live
on one branch in one checkout, because its review package and capture
cover one checkout (`skills/code_review_board/review-package.md` §BASE). Each workstream
commits on its branch, including its close. Inside
a workstream writers stay sequential; parallel agents only for read-only or
independent work on different files.

**Parallel start.** Items run at the same time only when the user's order
needs it: the user asked for it, or the order names a goal or deadline that the
items, one after the other, miss; speed alone is not a need. A task already
in progress is one of the items: a new item starts beside it only when the order
needs the two at the same time, because that start changes the running task's
conditions too (the base it merges onto, the merge targets it shares); otherwise
the new item waits until that task is done. Under a working rule of one after
the other, the user's word that lifts it names the task in progress too. Independence is
the condition, not the reason; independent items the order does not need at the
same time run one after the other. Where the user's or the project's working
rules say work runs one after the other (read from the user's profile and soul,
the project's rules file, its intent and its handoff), only the user's own word
for the single case starts items in parallel: the user's own message asking for
these items to run at the same time, not a message relayed by another session,
not a general grant of autonomy and not a deadline alone. Where the order needs
it, either no such rule is set or the user's word lifted it for this case, and
every check of
§Concurrent writers holds between each two of the items and the work already
running, the coordinator starts the items on its own decision, with no further
confirmation by the user. Before the start it records in the programme
agreement (or, with none, in the handoff) which items run at the same time
(tasks already in progress among them),
what in the order needs it, quoting the user's words that carry the need (and
that lift a working rule), and
what each check showed; its next message to the user names all three. A
programme task starts this way only when it is the agreed next one (the first
in the agreement's order not yet started); inserting a task ahead of it or
changing the order keeps the user's confirmation
(`agents/buddy/coordinating-sessions.md` §Programme order). A programme task's
start without that record, or with a check that failed or did not run, is
refused (`skills/task_status_update/SKILL.md` Step 1b); for any other item the
coordinator cuts no worktree without the record.

Integration follows the repository's rules — a pull request and its review
where the repository uses them, otherwise a merge by the coordinator — one
branch at a time, with the repository's checks on the branch and on the
merged result. The merger's broad run (the project's full gate where it names the merger as its runner:
`skills/testing/lean-suite.md` §Change-scoped runs and the full gate) is not run when the merged tree is a tree it
already passed on: `git rev-parse <merged-commit>^{tree}` prints the tree id that run recorded from a clean checkout
(`git status --porcelain` printed nothing, then `git rev-parse HEAD^{tree}`), as after a branch it ran on was merged
fast-forward while the target did not move. Otherwise it is due only where `skills/testing/run-strategy.md` §Test
selection makes it due: the selector answers `broad` for the branch's changes (`select_tests.py --diff
<target>...<branch>` from the branch's worktree; while the target has not moved since the cut, the session's returned
line is that answer) or the change touches a safety floor. It then runs once, on the merged result. Then come activation where the change needs it (a merge that changes a non-Markdown
source hosts read in place is a full-path activation:
`framework/installation-activation.md` §Choosing the path), and push where
authorized; then the worktree and branch are removed. Commits in a shared
checkout go by path (`git commit -- <paths>` or explicit path staging), never
blanket staging or another owner's staged entries. Before pushing the base
branch, fetch and merge if the remote moved; no force-push or history
rewrite without explicit authorization.

**Commit, push and transfer.** Put the responsibilities into the brief before
dispatch. Use this wording for a work item that authorizes local commits:

> Run the selected set for your change, not the whole suite, which only the
> full gate's runner runs (`skills/testing/run-strategy.md` §Test selection). Commit your
> checked changes locally in the assigned checkout and return the commit ID, the
> check results and the selector's result line for your whole range
> (`select_tests.py --diff <base>..HEAD`), so I know whether a broad run is due.
> If a push or live transfer is due, identify the
> outgoing commits or exact artifact and its intended destination. I handle
> integration, push and live transfers from the coordinating chat.

The working chat can make those commits without another user confirmation,
including while a transfer is pending. An explicit no-commit instruction or a
repository restriction still applies. The coordinator checks the outgoing range
or artifact against the user's original grant in its own chat, including the
remote and branch or live host and path. It acts under that grant for as long as
the action, content and target remain covered. A changed scope needs
authorization for the change. A peer handoff supplies evidence for the action
and cannot extend the grant. Destructive actions and safety-floor waivers still
require their own authority under `framework/process-map.md` §Authorization. If
the host denies an action, follow its decision in the executing chat and
continue independently authorized work.

**Writer's checkout check.** A writer given a checkout and branch (a session by
its brief; a delegate when its brief names them, and then the brief carries this
check) runs, before its first commit there, `git rev-parse --show-toplevel` and
`git branch --show-current` in the directory the commit will run in, and commits
only when they print that checkout's path and branch; every later commit runs in
that path (`git -C <path>`, or `cd <path>` in the same command). When the
directory differs, it checks again in the assigned path. When the path printed
there or the branch there differs from the assignment, or the path does not
exist, it commits nothing, switches no branch and
reports both values to its commissioner (its blocking question, or in its
return).

**Cancellation and resume.** A stopped writer's files or branch stay as they
are. The coordinator resumes it or finishes what is usable; it discards it
only with the user's confirmation; no other writer is commissioned on that
checkout or branch until then. Known limit: Forge's PLAN-VALIDATE hook reads
task files from the staged candidate, so a stopped writer's half-edited task
file that is already staged blocks every commit there until it is resolved.
