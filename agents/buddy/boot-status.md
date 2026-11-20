# Buddy — Boot status: freshness gate and greeting findings

Step-loaded unit of `agents/buddy/boot.md`. Read §Freshness gate at boot step 2
(STATUS-CHECK) and §Greeting findings at step 7 (GREET); step numbers refer to
boot.md's boot sequence (steps 4–7 in `boot-software.md`).

## Freshness gate

Run the boot probe from the active project's working directory, as its own
call: `bash <framework>/scripts/git-status-check.sh --boot`.
When the entry carries the line `Framework: plugin snapshot <name>; no
freshness check for it`, the framework is the plugin's copy, not a checkout:
that line replaces the framework's freshness result (no pull question for
it); the probe still checks the project and the user repo.
Codex callers first follow `agents/buddy/codex-execution.md`: the helper
performs a Git write and needs the offered escalation route when `.git` is
protected, even though its purpose is a status check.
The probe checks the active project, the framework and the user repo and prints
its findings as data to act on: `pull-question:` (each repository behind after a
successful fetch), `remote:` (the fetch outcome), `mode:`, `read-list:` and
`profile-read:` (the reads of Rounds 2 and 3), `greet:` (the computed greeting
findings), status lines per repository with an `entries:` line, and the file
facts ROUTE, the mode choice and RESUME use. After a pull, run it again. `unknown`
means a fact could not be determined (stderr says why): check that file directly
before relying on it.
When the user's scope forbids network use or writes outside the project, do
not fetch (it writes Git metadata): run `git-status-check.sh --boot --no-network`,
which prints `freshness: not checked (no network)` and each root's read-only
status entries; mark `remote unchecked` in the orientation line, ask no pull
question and continue the boot
(`boot.md` §Restricted user scope). Its uncommitted entries are held-back work
under §Greeting findings.

Buddy parses the output. Ahead-only status remains advisory. A remote update requires the **pull decision** below before
RESOLVE, ROUTE, LOAD or RESUME begins. Do not load context in parallel
with this gate or while waiting for the answer.

**Pull decision (behind > 0, including divergence):**
- A repository under `remote: unchecked` has cached status only: mark `remote
  unchecked` in the orientation line and continue without a pull or a blocking
  update question.
- For each repository in `pull-question:` ask: "Remote has N newer commits in
  <repo>. Shall I run git pull before continuing?" Batch multiple affected repos into one question. Wait for
  the user's answer before continuing the boot sequence. Silence
  is not approval. An explicit pull instruction in the current request,
  or a standing session-start pull permission in the project's rules,
  already answers this question for the repos it covers.
- For framework source changes, use `framework/installation-activation.md`
  and classify the change there first (§Choosing the path). On the full path,
  keep affected sessions off the changing sources and verify in a fresh
  session before relying on the change.
  An active boot never silently pulls or sets up the framework. Standing pull
  permission is not evidence that other sessions stopped. Consumer-only approved
  fast-forward updates preserve local changes; no reset/stash/rebase/branch switch.
  Reread changed consumer instructions before use. If update is unavailable,
  report the concrete limit; do not claim the old session is newly upgraded.

## Greeting findings

Every finding below goes in the first answer: the reply that ends your first
turn. A progress note before it does not count, because some hosts deliver
only that reply.

**On an instruction unit that did not load (first):** when a boot instruction
unit could not be read (a failed or blocked read, or a clipped result whose missing
text could not be recovered), Forge is not fully active
and the user must not rely on rules that did not load. The first answer then
opens with one sentence naming what did not load, before the orientation line
and the answer; a brevity request shapes only what follows it. A skipped check
(freshness without network, no remote, a step the scope forbids) and a
user-scope file that does not exist are not this notice.

**On STATUS-CHECK findings (step 2):** briefly report any pull outcome or
ahead-only status not already in an earlier turn's reply. An unavailable check
is at most one word in the orientation line (`remote unchecked`); the normal
compact start is not commented. The
pull decision was resolved before context loading; do not ask again here.
Nothing found: don't mention it.

**On held-back work (step 2):** report every uncommitted entry the freshness
step found as state that existed before this session: repository, the path of
each entry (more than five: the first five), and the count, also when this
session later changed the same file. Then attribute the uncommitted entries
and the framework's linked worktrees to live owners as
`framework/process-map.md` §Authorization defines them. What live
owners account for is normal with parallel sessions: one plain line.
Untracked host-owned entries under `.claude/skills/` (not Forge wrappers)
are not Forge work: a note. Anything else is held back: report it loudly —
repo, counts, next step — and investigate before taking up new work (an
entry under `.claude/worktrees/` is a parallel writer's worktree inside the
framework tree). More than about
20 entries in one repo (intent: more than one in-flight task's working set)
is a cue to look closely, not a verdict.

**On pending recovery:** the probe's `pending-project: present` or
`pending-personal: present`, or personal pending operations from the profile
snapshot: report it; before dependent work, recover in that scope through
`framework/continuity.md` §Recovery without stale replay.

**On user-scope warnings (boot.md §User scope):** one line — no user scope
configured, user folder or a boot file missing.

**On Workflow-Resume findings (step 6):** selected bound workflows/blockers as a
one-liner list in GREET (`Active: solve workflow [step:
frame-report, state: docs/solve/<slug>.md]`). Nothing found:
don't mention it.
