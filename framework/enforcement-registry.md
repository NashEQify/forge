# Enforcement Registry

Single source of truth for **what actually enforces what** in forge.
The framework makes enforcement claims throughout its docs ("X BLOCKs",
"Y guards Z"). After the hook paradigm shift removed the tool-event hook
layer, several of those claims described mechanisms that no longer have
a runnable artifact. This registry exists so every enforcement claim can
be checked against reality: each live mechanism carries a **class tag**
and a **resolvable artifact pointer**.

Discipline rule (enforcement-honesty): **no doc may state an enforcement
verb (`BLOCKs`, `guards`, `re-runs`, `enforces`) for a mechanism that is
not in the Live table below.** The `ANTI-PHANTOM` pre-commit WARN
(`orchestrators/claude-code/hooks/pre-commit.sh`) is the tripwire for the
clearest violations; `consistency_check` Check 11 validates this
registry's own integrity.

## Class tags

Every enforcement reference carries exactly one:

- **`[STRUCTURAL]`** — the agent topology or tool grant makes the
  violation *impossible*, not merely discouraged. Nothing to remember;
  the wrong action cannot be taken. Example: a context-isolated
  reviewer cannot see sibling reviews; `disallowedTools` removes Write
  from a read-only persona.
- **`[GATE]`** — a mechanical boundary check that runs *independently of
  whether Buddy chooses to run it*. Today this is exactly the git
  pre-commit/commit-msg hook and the SessionStart hooks (the harness
  runs them). Severity is **BLOCK** (halts the action) or **WARN**
  (mechanical detection, advisory — does not halt); SessionStart
  injectors carry **always-run** — they neither block nor warn, they
  fire on every session start.
- **`[WORKFLOW]`** — a workflow step tracked by `workflow_engine.py`.
  The engine evaluates `completion` + `on_fail` **only when Buddy drives
  `--complete`** — it is a discipline-run state-tracker, not an
  autonomous runtime. So a workflow gate has teeth only inside an
  engine-driven run; it is stronger than bare discipline but weaker than
  a `[GATE]`.
- **`[DISCIPLINE]`** — a rule Buddy or an agent applies by reading it.
  No mechanical detection, no block. This is the honest class for most
  of the framework's "rules": their force is the agent following them.

The honest test for a claim: *if no human and no agent were watching,
would the mechanism still catch the violation?* `[STRUCTURAL]` and
`[GATE]` pass; `[WORKFLOW]` passes only mid-run; `[DISCIPLINE]` does not.

## Live mechanisms

Single-path `Artifact` pointers (one backticked path per row, optional
`§section` suffix) so Check 11 can resolve them.

| Mechanism | Class | Severity | Artifact | Enforces |
|---|---|---|---|---|
| PLAN-VALIDATE | `[GATE]` | BLOCK | `orchestrators/claude-code/hooks/pre-commit.sh` | `plan_engine.py --validate` reports 0 errors before commit |
| CG-CONV | `[GATE]` | BLOCK | `orchestrators/claude-code/hooks/pre-commit.sh` | Conventional-Commits message format (commit-msg authoritative) |
| SKILL-FM-VALIDATE | `[GATE]` | BLOCK | `orchestrators/claude-code/hooks/pre-commit.sh` | staged `SKILL.md` frontmatter subset |
| SECRET-SCAN | `[GATE]` | WARN | `orchestrators/claude-code/hooks/pre-commit.sh` | gitleaks over staged content (skipped if gitleaks absent) |
| SOURCE-VERIFICATION | `[GATE]` | WARN | `orchestrators/claude-code/hooks/pre-commit.sh` | board/council reviews cite line-numbered evidence pointers |
| ANTI-PHANTOM | `[GATE]` | WARN | `orchestrators/claude-code/hooks/pre-commit.sh` | active-surface docs bind no live-enforcement verb to a purged hook-name (narrow tripwire: 3 named purged hooks × a fixed live-verb list — not universal) |
| buddy-boot-inject | `[GATE]` | always-run | `orchestrators/claude-code/hooks/buddy-boot-inject.sh` | SessionStart injects the Buddy boot sequence |
| session-start-remote | `[GATE]` | always-run | `orchestrators/claude-code/hooks/session-start-remote.sh` | SessionStart resume-nudge (active workflow / recent handoff) |
| brief-architect read-only | `[STRUCTURAL]` | — | `agents/brief-architect.md` | `disallowedTools` removes Edit/Write/NotebookEdit/ExitPlanMode/Agent (no Write-tool target, cannot sub-delegate — structural); `Bash` is granted for read-only commands, so disk writes via Bash redirection are blocked only by the agent's read-only-Bash `[DISCIPLINE]`, not structurally |
| reviewer context-isolation | `[STRUCTURAL]` | — | `skills/_protocols/context-isolation.md` | board/council members cannot see each other's output (anti-anchoring) |
| workflow `on_fail` gates | `[WORKFLOW]` | BLOCK-in-run | `scripts/workflow_engine.py` | step `completion` is met before advance — only while the engine drives the run |
| DIRECT-eligibility predicate | `[DISCIPLINE]` | — | `workflows/runbooks/build/workflow.yaml` | brief-author inline-vs-architect routing (fail-safe UP); `skip_when` is NOT engine-evaluated |
| dispatch-package allowlist | `[DISCIPLINE]` | — | `docs/specs/306-brief-architect.md` | a Buddy-authored draft in a brief-architect package is a contract violation |
| Pre-Delegation artifact | `[DISCIPLINE]` | — | `CLAUDE.md` | no sub-agent call without a delegation artifact (Invariant 3) |
| STALE-CLEANUP | `[DISCIPLINE]` | — | `CLAUDE.md` | retired artifact → every live reference cleaned in the same commit (Invariant 5) |
| piebald-budget | `[DISCIPLINE]` | — | `skills/_protocols/piebald-budget.md` | per-file-type length budget, applied by reviewers at review time |

## Purged mechanisms (no runnable artifact)

These names appear in historical records (decision logs, review
artifacts) but have **no live artifact**. The hook paradigm shift
removed the tool-event hook layer (`PreToolUse` / `PostToolUse` /
`UserPromptSubmit`); the observability checks they carried are now
`[DISCIPLINE]` (see `agents/buddy/operational.md` §Observability) or
were dropped. A doc on the active surface that states present-tense
enforcement for any of these is a phantom claim — reframe it to the
honest class above or mark it historical.

- `BRIEF-CLAIMS` — claimed to re-run an evidence grep at write/commit;
  never built as a live hook.
- `path-whitelist-guard` — claimed to block writes outside the intent
  scope; now the `[DISCIPLINE]` path-scope rule (Invariant 4).
- `frozen-zone-guard` — claimed to block WORM-zone edits; now the
  `[DISCIPLINE]` frozen-zone convention (`.correction.md` sidecars).
- `TASK-SYNC`, `OBLIGATIONS`, `PERSIST-GATE`, `ENGINE-USE`,
  `RUNBOOK-DRIFT`, `AGENT-SKILL-DRIFT`, `PIEBALD-BUDGET` — former
  pre-commit observability checks, dropped or downgraded to discipline.
  Several names double as live *concepts* (the STALE-CLEANUP invariant,
  the PERSIST-GATE discipline, the piebald-budget protocol) — those are
  `[DISCIPLINE]`, listed in the Live table; only the *hook/BLOCK* claim
  is phantom.

## Maintenance

- Add a row to the Live table whenever a new enforcement mechanism
  ships; pick the class by the honest test above.
- When a mechanism is removed, move its name to Purged and run the
  Invariant-5 sweep (`grep -rn <name>`, fix every live present-tense
  enforcement claim).
- `consistency_check` Check 11 (`scripts/consistency_check.py --check
  enforcement-registry`) validates that every Live row carries a valid
  class tag and that its artifact pointer resolves on disk. Scope limit:
  it is **skill-run, not commit-wired** (no `pre-commit.sh` call), and it
  checks tag *membership* + pointer *resolution* — NOT tag *honesty* (an
  over-claimed but well-formed tag passes). Honest tagging stays a
  `[DISCIPLINE]` judgment against the honest-test above.
