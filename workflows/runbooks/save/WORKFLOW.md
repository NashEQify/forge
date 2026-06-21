# Workflow: save

Session persistence — the single command for both mid-session and
end-of-session saves (there is no separate `quicksave`). The context
window is the primary source — no redundant reads. The footprint
self-adapts on real signals, not a mode flag: the handoff merge is
always safe to re-run, the history entry fires on task-closeout, and
buffer cleanup skips when the buffer is empty. Running `save`
mid-session and at session end is the same command.

## Steps

Three groups; group order is mandatory. Inside group B:
parallel (one tool-call batch).

### A. Pre-write (sequential)

1. **Dispatcher** — Buddy inline: triage PENDING entries from
   `docs/session-buffer.md` (act / defer / drop). Buffer
   empty → skip. Note: the dispatcher skill is archived —
   the mechanic now runs inline.
   - **`[framework-feedback]` routing (safety-net):** a
     `[framework-feedback]` PENDING entry is framework-friction
     that belongs in forge_dev's forge-feed, not the consumer
     buffer. Write-direct on notice stays **primary**
     (`$FRAMEWORK_DIR/docs/dogfood-learnings/README.md` §39-40);
     this step only catches what slipped into the buffer. Per
     entry: run the 6-check pre-write filter (README §Pre-write
     filter) — 2+ skip ⇒ mark `PROCESSED` + one-line drop-note,
     don't route; pass ⇒ allocate the next `L-NNN` (max across
     `forge-feed.md` + `implemented-forge-feeds.md`, +1), append
     to `$FRAMEWORK_DIR/docs/dogfood-learnings/forge-feed.md` in
     the README entry format, then mark the buffer entry
     `PROCESSED` (step 7 cleanup removes it). Destination is
     always `$FRAMEWORK_DIR` — cross-repo from a consumer CWD.
2. **Reconciliation** — from the context window:
   - **Gap check:** info in the window, not on disk →
     write it now.
   - **Task status:**
     `git diff HEAD -- docs/tasks/*.yaml | grep -E '^[+-]\s*(status|readiness):'`.
     A hit without a visible `task_status_update` call in
     the session log → warning + correct via the skill now.
     Content edits (scope, description, notes) are NOT a
     status change.
   - **Task-graph integrity:** `plan_engine --validate` must
     PASS — a sanity gate only. Substantive critical-path
     placement + blocked_by reconciliation live in
     `task_creation` / `task_status_update` at mutation time,
     not here.
3. **Workflow state** —
   `python3 $FRAMEWORK_DIR/scripts/workflow_engine.py --handoff-context`
   when active workflows exist. Output goes into step 4.
   Otherwise skip.

### B. Content writes (PARALLEL — one batch)

4. **Session handoff** — primary artifact. **Merge default,
   never blind overwrite.** The handoff is the CURRENT working
   state for the next session, NOT a session log or archive — it
   stays lean. Closed blocks are **deleted**, not accumulated;
   their durable record is `context/history/` + git.
   - **Path:** `<CWD>/context/session-handoff.md` (auto-create
     `context/` if absent, per `boot.md` §Context routing).
   - **Merge protocol:**
     1. `cp <handoff> <handoff>.bak` (gitignored).
     2. Read the handoff fully.
     3. Per 9-point block: **closed** (task done / closed /
        superseded, explicit user "done", PR merged,
        work committed+pushed) → **DELETE the block** (record
        lives in `context/history/` + git); at most a one-liner
        in the current meta-summary. **Open, not touched** →
        unchanged. **Open, worked on** → update. The
        "when in doubt keep" leniency applies ONLY to genuinely
        ambiguous OPEN items — never to a clearly-closed session.
        Long-lived open work belongs in a **task** (plan_engine
        surfaces it at boot), not as perpetual handoff prose.
     4. New open topics appended at the bottom.
     5. Rewrite the meta-summary (3-5 sentences: this
        session + continuity).
     6. Write tool (not edit — merge result, not a
        re-invention).
   - **Structure:** meta-summary · open topics (9-point
     each: intent, key concepts, files, decisions,
     errors, user statements, open points, status, next
     step) · deploy-status one-liner on a background
     deploy.
   - **Workflow state (from step 3):** as its own topic
     or embedded.
   - **Parallel session:** write failed → re-read, second
     merge, write. The `.bak` then shows the
     second-to-last version.
5. **History entry** (on task-closeout) —
   `<CWD>/context/history/YYYY-MM-DD-<slug>.md`. Fires when a
   task closed out this session (Persist Gate, operational.md);
   a mid-session save with no closeout skips it. Guard: the
   active context path must support history (otherwise skip).

### C. Post-write (sequential)

6. **Commit + push** — per CLAUDE.md §commit convention.
   `git add` the relevant files → commit → push. SSH
   passphrase failure → ask the user to push manually.
7. **Buffer cleanup** — remove `PROCESSED` entries from
   `docs/session-buffer.md`. The header stays. Empty →
   skip.

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
