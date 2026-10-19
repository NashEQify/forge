# Workflow: save

Session persistence — the single command for both mid-session and
end-of-session saves (there is no separate `quicksave`), for software and
on-demand projects alike. Goal: a new session continues with confirmed
knowledge and the full conversation context, and the save is verifiable.
The context window is the primary source; read only what the merge and the
checks need. The footprint self-adapts on real signals, not a mode flag:
the handoff merge is always safe to re-run, the history entry fires on
durable outcomes, software-only steps run only where their files exist,
and buffer cleanup skips when the buffer is empty. Every step runs; a
blocked step stays explicitly open in the report.

Work in the active project, not in a fixed personal repository. Use the
project's existing conventions; never invent a second status system.
Document only the current work and preserve parallel changes.

## Steps

Three groups; group order is mandatory. Inside group B:
parallel (one tool-call batch).

### A. Pre-write (sequential)

1. **Orient** — date and time zone, project root, `git status`. Read the
   project's rules for save, commit and push permissions, its navigation
   entry and the existing handoff (full read happens in step 6).
2. **Dispatcher** — triage PENDING entries from `docs/session-buffer.md`
   (act / defer / drop; never silently delete an unresolved entry).
   Buffer absent or empty → skip.
   - **`[framework-feedback]` routing (safety-net):** a
     `[framework-feedback]` PENDING entry is framework-friction
     that belongs in the framework's forge-feed, not the consumer
     buffer. Only where `$FRAMEWORK_DIR/docs/dogfood-learnings/` exists.
     Write-direct on notice stays **primary**
     (`$FRAMEWORK_DIR/docs/dogfood-learnings/README.md` §39-40);
     this step only catches what slipped into the buffer. Per
     entry: run the 6-check pre-write filter (README §Pre-write
     filter) — 2+ skip ⇒ mark `PROCESSED` + one-line drop-note,
     don't route; pass ⇒ allocate the next `L-NNN` (max across
     `forge-feed.md` + `implemented-forge-feeds.md`, +1), append
     to `$FRAMEWORK_DIR/docs/dogfood-learnings/forge-feed.md` in
     the README entry format, then mark the buffer entry
     `PROCESSED` (step 8 removes it).
3. **Reconciliation** — from the context window:
   - **Gap check:** info in the window, not on disk → step 4 writes it.
     Every `deferred:` item from a FACTS line is resolved now or carried
     into the handoff.
   - **Task status** (only where `docs/tasks/` exists):
     `git diff HEAD -- docs/tasks/*.yaml | grep -E '^[+-]\s*(status|readiness):'`.
     A hit without a visible `task_status_update` call in
     the session log → warning + correct via the skill now.
     Content edits (scope, description, notes) are NOT a
     status change.
   - **Task-graph integrity** (only where `docs/plan.yaml` exists):
     `plan_engine --validate` must PASS — a sanity gate only.
4. **Knowledge processing** — `knowledge_processor` on the session's
   actual findings: mode `process` for project context, `user-signal`
   for user-scope facts (resolved user repo, `framework/user-scope.md`).
   Delta check and EXTRACT → IMPACT CHAIN → SIGNAL CHECK; invent no new
   work for the save. New or changed content is reachable through its
   navigation: check the full read chain from the central entry
   (area navigation → intent / local notes → topic file); new or changed
   intents are linked from their navigation. Check local links.
5. **Workflow state** —
   `python3 $FRAMEWORK_DIR/scripts/workflow_engine.py --handoff-context`
   when active workflows exist. Output goes into step 6.
   Otherwise skip.

### B. Content writes (PARALLEL — one batch)

6. **Session handoff** — primary artifact. **Merge default,
   never blind overwrite.** The handoff is the CURRENT working
   state for the next session, NOT a session log or archive — it
   stays lean. Closed blocks are **deleted**, not accumulated;
   their durable record is `context/history/` + git.
   - **Path:** `<CWD>/context/session-handoff.md` (a project that uses
     `session-handover.md` keeps that name; auto-create `context/` if
     absent, per `boot.md` §Context routing).
   - **Merge protocol:**
     1. `cp <handoff> <handoff>.bak` (gitignored).
     2. Read the handoff fully.
     3. Per 9-point block: **closed** (task done / closed /
        superseded, explicit user "done", PR merged,
        work committed+pushed, durable record written) → **DELETE the
        block** (record lives in `context/history/` + git); at most a
        one-liner in the current meta-summary. **Open, not touched** →
        unchanged. **Open, worked on** → update. The
        "when in doubt keep" leniency applies ONLY to genuinely
        ambiguous OPEN items — never to a clearly-closed session.
        Long-lived open work belongs in a **task** where the project
        has a task system (plan_engine surfaces it at boot), not as
        perpetual handoff prose.
     4. New open topics appended at the bottom.
     5. Rewrite the meta-summary (3-5 sentences: this
        session + continuity).
     6. Write tool (not edit — merge result, not a
        re-invention).
   - **Structure:** meta-summary · open topics (9-point
     each: intent, key concepts, files, decisions,
     errors and failed attempts, user statements including approvals
     in force with their scope and limits, open points, status, next
     step) · one line on running jobs or background changes, or
     explicitly "no active job". Name the active topic paths.
   - **Workflow state (from step 5):** as its own topic
     or embedded.
   - **Parallel session:** write failed or file changed → re-read,
     second merge, write. The `.bak` then shows the
     second-to-last version.
   - **Defer-durability re-list:** carry OPEN `revisit-when:`
     defer-premises (`_protocols/mca-brief-template.md` §5)
     forward as handoff open-points and re-list them at each
     save, so an aged "no named consumer" premise resurfaces
     deterministically. Closes when a consumer appears (promote
     to a task) or is re-confirmed absent.
7. **History entry** —
   `<CWD>/context/history/YYYY-MM-DD-<slug>.md` (name collision → add
   the time). Fires on a task closeout (Persist Gate, operational.md)
   or on substantive completed work / new durable decisions; an
   interim save without durable content writes none (the handoff is
   still updated). Content: assignment and approvals, work done,
   results, verification evidence, decisions, errors, remaining limits;
   no secrets; never derive a completed setup from plans alone. Never
   overwrite an existing entry; link it from the project's history
   navigation if one exists. Guard: the active context path must
   support history (otherwise skip).

### C. Post-write (sequential)

8. **Buffer cleanup** — remove only `PROCESSED` entries (fully carried
   into knowledge / handoff / history) from `docs/session-buffer.md`;
   keep open ones and the header. Before the commit, so the cleanup is
   saved with the rest. Empty → skip.
9. **Commit + push** — review the diff and staged content for secrets,
   temporary output and unintended changes; run an available secret
   scanner in addition. Stage concrete own paths — no blind
   `git add .`; never commit foreign staged changes; in a mixed file
   select own hunks or report the conflict. Commit per the project's
   commit policy (no empty commit). An explicit `save` from the user is a
   commit-and-push request for the active project's tracked upstream
   unless the project's rules forbid or restrict it; otherwise push only
   when the project's rules or the user authorize push to that remote
   (process-map §Authorization). A save never widens permissions.
   **User repo:** when user-scope files changed and the user repo is not
   the active project, persist it the same way under the user repo's own
   rules; changes under its `context/user/` from other sessions count as
   its own content there. No force-push,
   reset, automatic stash, rebase or branch switch. Conflict, missing
   access or SSH passphrase prompt → keep the local save, name the
   concrete blocker, no unchecked retry loop.
10. **Verify and report** — check written files and links,
    `git diff --check`, commit and status. After a push compare the local
    commit with `git ls-remote origin refs/heads/<branch>` — for each
    repository pushed; without a push record `not pushed: <reason>`. Foreign
    unchanged working-tree diffs are not a failure of this save. Report
    briefly and separately: knowledge/navigation maintained, handoff and
    history paths, commit, push result; on partial failure, what is
    saved and the concrete open step.

---

## Checkpoint aggregation

When checkpoints (light / deep) happened in the session:
save aggregates their deltas instead of reconstructing
fresh. Checkpoint unwritten lists are the primary input
for the history entry. Without checkpoints: full
reconstruction — more prone to completeness errors.

## Workflow-Engine Integration

This runbook is tracked by `scripts/workflow_engine.py` when engine-driven
(some lifecycle / ad-hoc runs are skip-eligible — see the cookbook's *Skip
allowed for* list). The engine holds step state in `.workflow-state/<id>.json`
(SoT for the step pointer; persistent + cross-session-recoverable) and is
**Buddy-driven `[WORKFLOW]`** — it advances only when Buddy drives
`--complete`, a discipline-run state-tracker, not an autonomous runtime
(ADR-007 O-4, affirming ADR-004: no force-gate).

Generic cycle (identical across every workflow):

```bash
python3 $FRAMEWORK_DIR/scripts/workflow_engine.py --start <name> --task <id> [--route <path>]
python3 $FRAMEWORK_DIR/scripts/workflow_engine.py --next                       # current step + instruction
python3 $FRAMEWORK_DIR/scripts/workflow_engine.py --complete <step> --evidence "<short>"
#   classification step (mid-flow route): --complete <step> --route <key>
#   skip-eligible step: --skip <step> --reason "<why>"   ·   re-run: --retry <step> --reason "<why>"
#   >=2 workflows live? add --id <wf> (from --next `ID:`) — engine refuses keyless (exit 5)
```

`on_fail` per step: `block` (fix + retry), `warn` (`--complete --force` + reason),
`skip` (auto `warn_skipped`), `escalate` (pauses, user decision). Cross-session
resume surfaces active workflows at session start (`--boot-context`).

Full CLI + path-routing + extension API (`--guard` / `--handoff-context`) +
multi-machine constraint + skip-eligible list:
`framework/workflow-engine-cookbook.md`. Operational invariant:
`agents/buddy/operational.md` §Workflow engine.
