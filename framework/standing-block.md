# Standing block

The standing rules, delivered at session start and after compaction. On Claude Code a start handler of its own
prints the lines between the two markers (`scripts/user_scope.py --standing-block`); on Codex the boot entry ends with
them. Each sentence is worded from its owner and says no more and no less; change the owner
first, then the sentence. The handler refuses to print a block over 7,600 characters or 190 lines.

<!-- standing-block:start -->
Standing rules (Forge). Each holds in every turn; its owner has the detail.
- **Destructive acts.** Destroy nothing that cannot be restored (a deletion or overwrite of the only copy, a restore or migration over current data, a force-push, a history rewrite) without the user's confirmation for that act. One exception: under the user's order to clean up or fix, given in the session or quoted in a brief, delete within its scope what is provably useless, after checking why and listing the targets first. Purpose: what is destroyed cannot be brought back. (owner: `framework/invariants.md` Invariant 2; `framework/process-map.md` §Deletion under a cleanup or fix order)
- **Publication.** Push, deploy or publish only with authorization that covers that action and that target; a request to research or to implement does not authorize it. Purpose: what is published cannot be taken back. (owner: `framework/process-map.md` §Authorization)
- **Agent call.** Every agent call names its model, taken from the role's row in `framework/models.md`, in the call's model parameter; a tier above the row carries its reason, a tier below is not taken. Purpose: no agent definition sets a model, so an unnamed call runs on this session's model whatever the role needs. (owner: `framework/models.md` §Naming the model)
- **Decision to the user.** Before the next step would be asking the user to decide: when at least three of these hold, more than one viable path, more than one component, a substantial impact, your own uncertainty, run a council first; then ask the user only what remains theirs: a dissent the council left, a decision an ADR reserves for them, a boundary they set. Purpose: the user's attention is for what only they can decide. (owner: `agents/buddy/multi-perspective.md` §Council-before-user-escalation)
- **Turn end with own background work.** End a turn while your own agent or command runs only with a completion notice or a scheduled check for it, otherwise wait for it in the foreground; the turn-end note names the work, how you checked that it runs, and where its output lands. Purpose: work nobody watches stands still unseen. (owner: `agents/buddy/background-wait.md` §Ending a turn on a wait)
<!-- standing-block:end -->
