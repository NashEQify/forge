# Buddy — On-demand start

Read and follow `framework/work-principle.md` before taking up work.
Resolve this reference against the framework root; retain the consumer CWD.


The complete start procedure for `on-demand` work: projects whose intent selects
on-demand, and every session of the `daily` install profile. The full
`boot.md` hands its on-demand branch to this file. The entry (installed per
machine) has already named the person's soul, user repo and install profile;
files it includes in full are loaded and need no read.

1. **Orient:** date, time zone, host and CWD (fold into the greeting).
2. **Freshness first:** Codex callers first follow `agents/buddy/codex-execution.md`
   and invoke the metadata-writing helper through the offered escalation route
   when `.git` is protected. In the active project's Git root run
   `FRAMEWORK_DIR=<framework> GIT_STATUS_CHECK_INCLUDE_FRAMEWORK=1 bash <framework>/scripts/git-status-check.sh`,
   and once more with `GIT_STATUS_CHECK_INCLUDE_FRAMEWORK=0` from the user repo
   only if its canonical Git root differs from both project and framework roots.
   This avoids duplicate framework fetches, including path aliases. When the
   user's scope forbids network use or writes outside the project, skip the helper and report remote
   freshness as not checked (`agents/buddy/boot.md` §Restricted user scope). Empty
   stdout means "no difference to the cached remote state" — claim an
   up-to-date remote only after a bounded `git fetch` succeeded. Per-repository
   stderr diagnostics identify failed fetches and cached status. On a failed
   fetch, report remote freshness as unavailable and label any ahead/behind
   values cached; continue without a pull or blocking update question. Only
   after a successful bounded fetch, for a repo that is behind: ask once, batched,
   before reading anything else ("Remote has N newer commits in <repo>. Pull
   first?") unless the project's rules grant a standing session-start pull.
   Framework sources are shared mutable runtime inputs: do not pull or reinstall
   them from an active boot. Follow `framework/installation-activation.md` and
   its path classification; on the full path stop affected sessions before source
   changes, preserve a matched baseline, install and validate, then start a fresh
   session. Standing pull permission does not
   prove that other sessions stopped. Consumer-only fast-forward follows local
   authorization and preserves changes; reread affected instructions. Ahead is a note.
   `[uncommitted: …]`, `[installed-not-committed: K]` and `[installer: …]`
   groups report uncommitted and installed state; they never block the
   freshness step. (The soul itself is
   read before this step, from the entry: it shapes even the pull question.)
3. **Recovery and the person:** read `framework/continuity.md` and capture the
   configured user profile plus personal pending status in a coherent snapshot;
   check project pending with required project entry/handoff separately. Reconcile
   pending work or qualify/block dependent work. Then read `<user repo>/context/user/profile.md` (if present;
   who the person is, including values and priorities) and `<framework>/skills/knowledge_processor/continuous-maintenance.md`
   — its rules apply from the first answer. Detail
   about the person is reached later through `context/user/navigation.md`.
   No user scope configured → say so once in the greeting.
4. **The project's rules:** its `CLAUDE.md`, else its `AGENTS.md` (Claude Code
   does not load `AGENTS.md` by itself), and `intent.md`. Follow the start
   files they name; skip files already read in step 3.
5. **Default resume** when the project names no start files:
   - read the boot entry the intent names, else `navigation.md` /
     `context/navigation.md`; follow it to the topic at hand and read
     `intent.md`, local `AGENTS.md` and named instructions along that path
     before working on it — also on a later topic switch. Do not read all
     subfolders or archives;
   - read `context/session-handoff.md` completely (keep an existing
     `session-handover.md` name; never create a second one) and
     `docs/session-buffer.md` if present; missing → fresh start, reconstruct
     nothing;
   - take over goal, decisions, user statements, errors, failed attempts,
     open points, status and next step; re-measure running jobs and other
     changeable state before relying on them;
   - approvals keep their stated scope: do not renew an old host/session
     approval or carry it to other targets, do not re-ask one already given
     for this continuation; diagnosis-only stays diagnosis;
   - catch up scoped pending recovery before dependent work. Carry opaque domain
     bindings from the handoff; only a present explicit development binding loads
     `framework/development-continuation.md` to restore exact selected state. Do not
     infer selection from task/plan/state files or start unrelated open topics.
6. **Greet:** one short line with status and next step (style: soul). A
   skipped or cut-short start comes first in the first answer, the reply that
   ends your first turn (a progress note before it does not count): what did
   not load and which checks are unavailable (`agents/buddy/boot.md`
   §Restricted user scope). Otherwise mention
   only a pull outcome, an unchecked remote, ahead status, held-back work or a
   user-scope warning, if any. Uncommitted or installed-not-committed state is
   a note with its counts. It gates new work only where the project's rules
   ask for that or the checkout is the framework of a coordinated programme;
   then follow `framework/process-map.md` §Authorization. An `[installer: …]`
   group without `operation open` is a maintenance need: say so.

After the applicable freshness, recovery and project-context sequence, read and
follow `framework/context-and-loading.md` §Buddy coordination refresh. It applies
to resumed coordination, meaningful task/topic changes and consequential
decision/adoption boundaries in on-demand work, without loading development
operational rules or selecting a software workflow.

Not part of on-demand start: the chub check, plan/workflow probes, the Forge
skill index, automatic `context/` creation and development `operational.md` (read it only
for explicitly selected development work). Generic methods use their own contracts. Forge workflows, Councils and boards run
only on explicit request. Authorization, secrets and the project's own
approvals stay binding. Before the final message of a turn that changed
something or delegated work, read and follow `skills/return_summary/SKILL.md`
§Decisions I took for you and, for each completion claim,
`skills/_protocols/evidence-author-claims.md` §8.5.
