# Workflow: save

End-of-session persistence. The context window is the primary
source — no redundant reads.

## Steps

Three groups; group order is mandatory. Inside group B:
parallel (one tool-call batch).

### A. Pre-write (sequential)

1. **Dispatcher** — Buddy inline: triage PENDING entries from
   `docs/session-buffer.md` (act / defer / drop). Buffer
   empty → skip. Note: the dispatcher skill is archived
   (Task 161 tier-1 mitigation) — the mechanic now runs
   inline.
2. **Reconciliation** — from the context window:
   - **Gap check:** info in the window, not on disk →
     write it now.
   - **Task status:**
     `git diff HEAD -- docs/tasks/*.yaml | grep -E '^[+-]\s*(status|readiness):'`.
     A hit without a visible `task_status_update` call in
     the session log → warning + correct via the skill now.
     (The pre-commit hook TASK-SYNC additionally warns
     mechanically — CLAUDE.md §commit-guard.) Content
     edits (scope, description, notes) are NOT a status
     change.
3. **Workflow state** —
   `python3 $FRAMEWORK_DIR/scripts/workflow_engine.py --handoff-context`
   when active workflows exist. Output goes into step 4.
   Otherwise skip.

### B. Content writes (PARALLEL — one batch)

4. **Session handoff** — primary artifact. **Merge default,
   never blind overwrite.**
   - **Path (CWD-based, see `boot.md` §context routing):**
     - CWD under `BuddyAI/workspaces/<name>/` →
       `BuddyAI/context/session-handoff-<name>.md`.
     - CWD under `BuddyAI/` root →
       `BuddyAI/context/session-handoff.md`.
     - CWD external (with or without `context/`) →
       `<CWD>/context/session-handoff.md` (auto-create).
   - **Merge protocol:**
     1. `cp <handoff> <handoff>.bak` (gitignored).
     2. Read the handoff fully.
     3. Per 9-point block: **closed** (task done / closed /
        superseded, explicit user "done", PR merged) →
        out, one-liner in the meta-summary. **Open, not
        touched** → unchanged. **Open, worked on** →
        update. When in doubt, leave it (overkeep >
        overkill).
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
5. **History entry** —
   `<context>/history/YYYY-MM-DD-<slug>.md`. Guard: the
   active context path must support history (otherwise
   skip). Workspace sessions: always
   `BuddyAI/context/history/` (global); the filename
   contains the workspace name.

### C. Post-write (sequential)

6. **TC detection** — 1 grep call: UNTESTED in
   `tests/TESTCASES.md`. Match → note PASS / FAIL. No
   match / 0 UNTESTED → skip. No second call.
7. **Convoy** — update when an objective task was active.
8. **Commit + push** — convention: CLAUDE.md §commit
   convention. Push MUST come before deploy (Hetzner does
   `git pull`). SSH passphrase failure → ask the user to
   push manually.
9. **Dashboard deploy** (BACKGROUND, conditional) — only
   when dashboard-relevant content changed:
   `git diff <last-deploy-tag>..HEAD -- docs/tasks/ docs/plan.yaml`
   (without the tag: last 5 commits). Hit →
   `bash $FRAMEWORK_DIR/scripts/deploy-dashboard-lite.sh`
   via `run_in_background`. The script is idempotent —
   the redundant call to the Task-370 post-commit hook is
   only network latency. Precondition: step 8
   succeeded. Result as a notification — error in the
   handoff note.
10. **Buffer cleanup** — remove `PROCESSED` entries from
    `docs/session-buffer.md`. The header stays. Empty →
    skip.

---

## quicksave — mid-session checkpoint

Trigger: the user says `quicksave`. Proportional, not a
full cycle.

Steps: **1 (dispatcher) → 2 (recon) → 3 (handoff, like
step 4 above with `.bak` + merge default)** sequentially.

What quicksave does NOT do: history entry, TC detection,
convoy, deploy, buffer cleanup. No replacement for full
`save` at end of session.

When: secure state while continuing to work, before a
context switch, intermediate save on a large context.

## Checkpoint aggregation

When checkpoints (light / deep) happened in the session:
save aggregates their deltas instead of reconstructing
fresh. Checkpoint unwritten lists are the primary input
for the history entry. Without checkpoints: full
reconstruction — more prone to completeness errors.
