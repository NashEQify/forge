# Buddy — Boot status: freshness gate and greeting findings

Step-loaded unit of `agents/buddy/boot.md`: §Freshness gate at boot step 2, §Greeting findings at the greeting.

## Freshness gate

Run the boot probe from the active project's working directory as its own call:
`bash <framework>/scripts/git-status-check.sh --boot` (on Codex first follow `agents/buddy/codex-execution.md`: the
probe writes Git metadata and may need the escalation route). Its lines are the data to act on: `pull-question:`,
`remote:`, `mode:`, `read-list:`, `profile-read:`, `greet:`, the per-repository status and the file facts the later
steps use. `unknown` means a fact could not be determined: check that file directly before relying on it. With the
entry line `Framework: plugin snapshot <name>; no freshness check for it`, the framework is the plugin's copy and has
no pull question; the probe still checks the project and the user repo. A user scope that forbids network or writes
outside the project runs `--boot --no-network` and marks `remote unchecked` in the orientation line.

**Pull decision**, before any context is loaded: for each repository in `pull-question:` ask once, batched, "Remote
has N newer commits in <repo>. Shall I run git pull before continuing?", and wait; silence is not approval. An
explicit pull instruction or a standing session-start pull permission in the project's rules answers it. Never pull
or set up the framework silently; for framework source changes follow `framework/installation-activation.md`. A
consumer pull is a fast-forward that keeps local changes (no reset, stash, rebase or branch switch); reread changed
instructions before using them. Rerun the probe after a pull.

## Greeting findings

All findings go in the first answer, the reply that ends the first turn; the probe's `greet:` line computes most.

- **First, an instruction unit that did not load** (a failed, blocked or clipped read that could not be recovered):
  one sentence naming it, before the orientation line. A skipped check or a missing user-scope file is not this.
- **Status check:** a pull outcome or ahead-only status; an unavailable check is one word in the orientation line.
- **Held-back work:** every uncommitted entry the probe found (repository, up to five paths, the count). What a live
  owner accounts for (parallel sessions, per `framework/process-map.md` §Authorization) is one plain line;
  host-installed `.claude/skills/` entries are a note; anything else is reported loudly and investigated before new
  work (an entry under `.claude/worktrees/` is a parallel writer's worktree).
- **Pending recovery** (`pending-project: present`, `pending-personal: present`): report it and recover through
  `framework/continuity.md` §Recovery without stale replay before dependent work.
- **User scope:** one line when none is configured or a boot file is missing.
- **Workflow resume:** bound workflows and blockers as a one-line list.

Nothing found: say nothing about it.
