# Buddy — Concurrent writers

Step-loaded unit of `agents/buddy/operational.md` (Phase 2: ACT). Read it when a
second writer is involved (a session, a delegate or another chat writing the
same repository), before cutting a worktree for a writer, before committing in a
shared checkout, before integrating a branch, and when a writer stopped.
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
checkout by default (the Claude desktop app uses `.claude/worktrees/`) gets
the worktree path from the coordinator, cut beforehand. Otherwise run them in sequence. The spec and the code of one delivery
are one workstream: from the build workflow's Prepare phase on they live
on one branch in one checkout, because its review package and capture
cover one checkout (`skills/code_review_board/review-package.md` §BASE). Each workstream
commits on its branch, including its close. Inside
a workstream writers stay sequential; parallel agents only for read-only or
independent work on different files.

**Parallel start.** Items run at the same time only when the user's order
needs it: the user asked for it, or the order names a goal or deadline that the
items, one after the other, miss; speed alone is not a need. Independence is
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
agreement (or, with none, in the handoff) which items run at the same time,
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
merged result (the project's full gate where it names the merger as its runner:
`skills/testing/lean-suite.md` §Change-scoped runs and the full gate), activation where the change needs it (a merge that changes a non-Markdown
source hosts read in place is a full-path activation:
`framework/installation-activation.md` §Choosing the path), and push where
authorized; then the worktree and branch are removed. Commits in a shared
checkout go by path (`git commit -- <paths>` or explicit path staging), never
blanket staging or another owner's staged entries. Before pushing the base
branch, fetch and merge if the remote moved; no force-push or history
rewrite without explicit authorization.

**Cancellation and resume.** A stopped writer's files or branch stay as they
are. The coordinator resumes it or finishes what is usable; it discards it
only with the user's confirmation; no other writer is commissioned on that
checkout or branch until then. Known limit: Forge's PLAN-VALIDATE hook reads
task files from the staged candidate, so a stopped writer's half-edited task
file that is already staged blocks every commit there until it is resolved.
