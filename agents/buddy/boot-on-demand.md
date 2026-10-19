# Buddy — On-demand start

The complete start procedure for `on-demand` work: projects whose intent selects
on-demand, and every session of the `daily` install profile. The full
`boot.md` hands its on-demand branch to this file. The entry (installed per
machine) has already named the person's soul, user repo and install profile.

1. **Orient:** date, time zone, host and CWD (fold into the greeting).
2. **Freshness first:** in the active project's Git root run
   `FRAMEWORK_DIR=<framework> GIT_STATUS_CHECK_INCLUDE_FRAMEWORK=1 bash <framework>/scripts/git-status-check.sh`,
   and once more from the user repo when it differs from the project. Empty
   output means "no difference to the cached remote state" — claim an
   up-to-date remote only after a bounded `git fetch` succeeded; otherwise say
   the remote was not checked. A repo that is behind: ask once, batched,
   before reading anything else ("Remote has N newer commits in <repo>. Pull
   first?") unless the project's rules grant a standing session-start pull.
   Fast-forward only, keep local changes; after a pull re-read the changed
   instructions, including the soul. Ahead is only a note. (The soul itself is
   read before this step, from the entry: it shapes even the pull question.)
3. **The person:** read `<user repo>/context/user/profile.md` (if present;
   who the person is, including values and priorities) and `<framework>/skills/knowledge_processor/SKILL.md`
   §Continuous maintenance — its rules apply from the first answer. Detail
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
   - catch up pending maintenance items from the handoff before dependent
     work; do not start other open topics unasked.
6. **Greet:** one short line with status and next step (style: soul). Mention
   only a pull outcome, an unchecked remote, ahead status or a user-scope
   warning, if any.

Not part of on-demand start: the chub check, plan/workflow probes, the Forge
skill index, automatic `context/` creation and `operational.md` (read it only
for explicit Forge method work). Forge workflows, Councils and boards run
only on explicit request. Authorization, secrets and the project's own
approvals stay binding.
