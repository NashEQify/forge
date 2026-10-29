# Buddy — Boot status: freshness gate and greeting findings

Step-loaded unit of `agents/buddy/boot.md`. Read §Freshness gate at boot step 2
(STATUS-CHECK) and §Greeting findings at step 7 (GREET); step numbers refer to
boot.md's boot sequence (steps 4–7 in `boot-software.md`).

## Freshness gate

Run `git-status-check.sh` from the active project's Git root.
Codex callers first follow `agents/buddy/codex-execution.md`: the helper
performs a Git write and needs the offered escalation route when `.git` is
protected, even though its purpose is a status check.
Pass the concrete framework root as `FRAMEWORK_DIR` and set
`GIT_STATUS_CHECK_INCLUDE_FRAMEWORK=1`. This checks both the active
project and the framework whose instructions this session uses (deduped
when they are the same repo). It fetches and reports ahead/behind status.
5-second network timeout. Failed fetches produce a per-repository diagnostic
on stderr; treat the associated ahead/behind values as cached. Output on
stdout: one line per non-clean repo, `<path>` followed by the groups that
apply: `[ahead N | behind N | ahead M, behind N]`,
`[uncommitted: S staged, M modified, U untracked]` (entries; an untracked
directory is one) and, for the framework checkout, from the installer's
read-only status: `[installed-not-committed: K]` (framework sources whose
live bytes are not in `HEAD`; K counts files) and `[installer: <phase>]`
for any phase other than `complete`, `rolled_back` or `unprepared`, with
`, operation open` while a prepared or validation-pending operation is open
(the installer knows the phase, not whether anyone drives it). Unavailable
checks are stderr diagnostics; inside a linked worktree "journal belongs to
a different source checkout" is expected, as installer state belongs to the
main checkout. Empty stdout with empty stderr means no cached divergence and
no uncommitted work in the checked working trees; linked worktrees and
staging copies are outside them (`git worktree list` names the linked ones).
Only a successful fetch establishes remote freshness.
When the user's scope forbids network use or writes outside the project, do
not run the helper (it fetches and writes Git metadata): report remote freshness as not checked, with the
scope as the reason, ask no pull question and continue the boot
(`boot.md` §Restricted user scope).
When the configured user repo's canonical Git root differs from both the
active project and framework roots, run the script once more from that
user root with `GIT_STATUS_CHECK_INCLUDE_FRAMEWORK=0`. This checks the
user scope without fetching the framework a second time. Compare canonical
roots so path aliases do not cause duplicate checks.

Buddy parses the output. Ahead-only status remains advisory. A remote update requires the **pull decision** below before
RESOLVE, ROUTE, LOAD or RESUME begins. Do not load context in parallel
with this gate or while waiting for the answer.

**Pull decision (behind > 0, including divergence):**
- The script can report cached tracking refs after a failed fetch. Before
  claiming an online update, confirm a successful bounded fetch for the
  affected repo and re-read its status. If offline or fetch fails, report
  the unavailable check, label any cached status as such, and continue
  without a pull or a blocking update question.
- If still behind, name the repo and ahead/behind counts and ask:
  "Remote has N newer commits in <repo>. Shall I run git pull before
  continuing?" Batch multiple affected repos into one question. Wait for
  the user's answer before continuing the boot sequence. Silence
  is not approval. An explicit pull instruction in the current request,
  or a standing session-start pull permission in the project's rules,
  already answers this question for the repos it covers.
- For framework source changes, use `framework/installation-activation.md`
  and classify the change there first (§Choosing the path). On the full path,
  stop affected sessions before updating shared sources, preserve a matched
  source/integration baseline, install and validate before fresh-session use.
  An active boot never silently pulls/reinstalls the framework. Standing pull
  permission is not evidence that other sessions stopped. Consumer-only approved
  fast-forward updates preserve local changes; no reset/stash/rebase/branch switch.
  Reread changed consumer instructions before use. If update is unavailable,
  report the concrete limit; do not claim the old session is newly upgraded.

## Greeting findings

**On a skipped or cut-short boot (first):** when a boot step or file was
skipped, declined, blocked or cut — by a user scope, a host limit or a
failed read — the first answer starts with that: what did not load and which
checks are unavailable. The first answer is the reply that ends your first
turn; a progress note before it does not count, because some hosts deliver
only that reply. The user must never assume Forge is fully active when it is
not.

**On STATUS-CHECK findings (step 2):** briefly report any pull outcome,
ahead-only status or unavailable check not already in an earlier turn's
reply. The
pull decision was resolved before context loading; do not ask again here.
Nothing found: don't mention it.

**On held-back work (step 2):** attribute the uncommitted entries,
installed-not-committed sources and the framework's linked worktrees to
live owners as `framework/process-map.md` §Authorization defines them;
`forge_install.py --maintenance status` lists the source paths. What live
owners account for is normal with parallel sessions: one plain line.
Untracked host-owned entries under `.claude/skills/` (not Forge wrappers)
are not Forge work: a note. Anything else is held back: report it loudly —
repo, counts, next step — and investigate before taking up new work. An
`[installer: …]` group without `operation open` (for example
`recovery_required`), an open operation no running session drives, or an
unavailable installer status is loud; next step: inspect
`forge_install.py --maintenance status` (a reason under `.claude/worktrees/`
is a parallel writer's worktree inside the framework tree). More than about
20 entries in one repo (intent: more than one in-flight task's working set)
is a cue to look closely, not a verdict.

**On user-scope warnings (boot.md §User scope):** one line — no user scope
configured, user folder or a boot file missing.

**On Workflow-Resume findings (step 6):** selected bound workflows/blockers as a
one-liner list in GREET (`Active: solve workflow [step:
frame-report, state: docs/solve/<slug>.md]`). Nothing found:
don't mention it.
