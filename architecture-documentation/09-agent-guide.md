# 09 — Agent Guide

> **Audience: AI coding agents.** Human reader → see
> [`10-human-guide.md`](10-human-guide.md).

For coding agents (Claude Code, OpenCode, Codex, Cursor, etc.). Compact required
reading before any actions are taken against the repo.

## Start here

When you see this repo for the first time:

1. **Read Tier 0:** [`../CLAUDE.md`](../CLAUDE.md) (Claude Code) or
   [`../AGENTS.md`](../AGENTS.md) (Codex / OpenCode). Shared invariants apply
   alongside effective platform instructions and permissions.
2. **Read Buddy Tier 1:** [`../agents/buddy/soul.md`](../agents/buddy/soul.md)
   + [`../agents/buddy/operational.md`](../agents/buddy/operational.md)
   + [`../agents/buddy/boot.md`](../agents/buddy/boot.md).
3. **Read the boot index:** [`../framework/boot-navigation.md`](../framework/boot-navigation.md).
4. **Finish reading this file.**
5. **Optional: Tier 2 on-demand** — `context-rules.md` + skill `REFERENCE.md` files.

Don't read it all at once — Tier 0 is mandatory, Tier 1 is loaded when
needed, Tier 2 is on-demand.

## Tier 0 invariants (Claude Code edition)

`CLAUDE.md`:

1. **Board/Council: responsibility and evidence.** Reviewers investigate
   independently; a Chief consolidates where required. Buddy decides and
   verifies pivotal claims against sources, consulting relevant findings
   without routinely repeating every review. Read-only reviewers return
   complete artifacts inline; Buddy persists them verbatim with provenance
   before Chief consumption. Effective platform permissions remain binding.

2. **Authorization.** A clear implementation instruction authorizes its
   bounded scope across phases. Ask again only for a material scope/risk
   change or an unresolved consequential decision. Diagnosis does not
   authorize repair; live, destructive and publication actions retain their
   explicit boundaries. Bookkeeping cannot authorize substantive changes.

3. **Pre-Delegation.** No agent call without a delegation artefact. Direct:
   scope, goal, agent and success criteria stated explicitly in the turn.
   Standard/Full: gate file. Routing: `framework/process-map.md`.

4. **Code delegation.** Product code → main-code-agent. Buddy writes
   within intent-scope by discipline.
   Orchestrator work (agents/, framework/, skills/, context/, docs/)
   Buddy writes directly.

5. **Stale cleanup.** Artefact declared retired/replaced/sunset: clean up
   all active references in non-frozen files in the same commit.
   `grep -rn <artefact>` + filter frozen zones + fix the rest.

6. **Deployment verification.** Verify the actual user/service outcome.
   HTTP 200 or process liveness alone is insufficient; report any unverified
   boundary. During ongoing harm, follow the fix runbook's Incident recovery
   before final RCA, within existing authorization.

DIRECT eligibility is centralized in `framework/process-map.md`: risk,
reversibility, observed patterns and executable verification determine the
path. Safety floors apply first; file counts and new local behavior do not
decide eligibility.

Codex and OpenCode use `AGENTS.md`; Claude Code uses `CLAUDE.md`. Shared
invariants apply alongside each consumer's project rules and effective
platform permissions.

## Buddy phases

Strictly observed:

```
RECEIVE → ACT → BOUNDARY
```

### RECEIVE

Classify the input before you reply:

| State | Trigger | Reaction |
|---|---|---|
| **Incident** | Active outage or ongoing harm | Authorized recovery + outcome verification before final RCA |
| **Defect** | Expectation ≠ reality without ongoing harm | Diagnose and repair; verified known fixes may qualify for DIRECT |
| **Substantive** | User wants to do/change/build | Clarify intent fit + sequencing |
| **Trivial** | Confirmation, status, greeting | answer |

### ACT

- Board/Council: independent reviewers, Chief consolidation where required,
  then Buddy's decision and verification of pivotal claims.
- Delegation: routing table (code → MCA, architecture → solution-expert,
  security → security, sysadmin → Buddy direct).
- Source grounding: read if last read >5 turns old. Before consistency
  assertion: read both files.
- Sub-agent return: read incident block, then route.

### BOUNDARY

- Context: learned something new → write (active path).
- History: task closed → persist gate.
- Backlog: status change → `task_status_update` skill (NOT raw edit), persist gate.
- Persist gate is BLOCKING on a status change.

## Do — obligations

### DO 1: Observe the boot sequence

First turn: read Tier 0 + Buddy Tier 1, then boot per
`agents/buddy/boot.md` (ORIENT/RESOLVE/ROUTE/LOAD/RESUME/GREET).

### DO 2: Delegation artefact before sub-agent call

Plan block or gate file. Content: scope, tool/agent, alternatives,
expected artefacts. For non-trivial: also self-review + possibly a
plan-adversary dispatch.

### DO 3: Routing via process-map.md

For a workflow trigger: look in `framework/process-map.md`. What I want
→ which workflow → which runbook.

### DO 4: Stale cleanup in the same commit

When you archive/delete something: `grep -rn <name>` with a frozen-zone
filter, fix all active refs in the same commit. This is discipline-only — no pre-commit check for it.

### DO 5: Respect generator output

The `framework/skill-map.md` AUTO block is generated. Edit only the
sections outside the `<!-- SKILL-MAP-AUTO-START -->` /
`<!-- SKILL-MAP-AUTO-END -->` markers. Same for the 8 navigation.md files.

### DO 6: Skill anatomy for new skills

Mandatory frontmatter fields: `name`, `description` (with "Use when"),
`status`, `invocation.primary`. Anatomy-v2 conformant. Pre-commit Check 3
(SKILL-FM-VALIDATE) BLOCKS otherwise.

### DO 7: Persist gate on status change

Status change without context update is half. This is discipline-only —
there's no pre-commit check for it; habit closes the gap.

### DO 8: Source-grounding discipline

Before str_replace on spec/code: read if last read >5 turns old.
Before consistency assertion across 2+ artefacts: read both, mandatory.
Summaries are heuristic, not ground truth.

### DO 9: Observability on state-changing actions

One-line note in the turn:
```
{action} → {target} ({reason})
```
Examples:
- `→ main-code-agent (src/-scope)`
- `Buddy direct (orchestrator-path)`
- `task <id> → done`

Not for analysis/discussion/framing.

## Don't — prohibitions

### DON'T 1: Bias reviewers or skip verification

CLAUDE.md §1. Keep reviewers independent. A Chief's signal informs Buddy's
decision; verify pivotal claims against sources and inspect relevant findings
when needed to resolve contradictions.

### DON'T 2: Exceed authorization or repeatedly ask for the same approval

CLAUDE.md §2. Carry approved scope across phases. Clarify unresolved decisions
or material changes to scope/risk; diagnosis-only and bookkeeping do not
authorize implementation.

### DON'T 3: Sub-agent call without a delegation artefact

CLAUDE.md §3. Violation = constraints get forgotten, sub-agent does
"something other than meant", refactoring later.

### DON'T 4: Writes outside intent scope

Buddy writes within `intent.md` scope by discipline; out-of-scope
writes are self-flagged or user-flagged at review.

### DON'T 5: Writes into frozen zones

Convention: `context/history/**` is WORM (write-once-read-many).
Corrections via a `.correction.md` sidecar (convention,
discipline-enforced).

### DON'T 6: Raw edits on task YAMLs (status/readiness)

Status/readiness ALWAYS via the `task_status_update` skill. Raw edits
are caught by discipline + `consistency_check`, not a pre-commit check —
but that is just a symptom, not the diagnosis.

### DON'T 7: Edit the AUTO block manually

`framework/skill-map.md` and the 8 navigation.md have marker blocks.
Editing leads to drift on the next generator run. Disk = SoT, index
follows.

### DON'T 8: Skill inflation

New capability → "I need a new skill". **Wrong.** First check whether an
existing skill with `modes` extension covers the use case. Inflation
guard: `framework/skill-anatomy.md §Inflation Guard`.

### DON'T 9: Mentally simulate hooks pre-emptively

Hooks are mechanical. You don't have to guess "would the hook block
this?". Try, read the block output, react. Mental simulation is a
drift source.

### DON'T 10: Patch symptoms without root cause

Verify the cause before claiming permanent repair. During ongoing harm, follow
the fix runbook's authorized Incident recovery first; restoration is distinct
from resolution of the cause.

## Where do I find what?

| Question | Place to start |
|---|---|
| Which workflow for which work? | [`../framework/process-map.md`](../framework/process-map.md) |
| Which skills exist? | [`../framework/skill-map.md`](../framework/skill-map.md) |
| How do I write a skill? | [`../framework/skill-anatomy.md`](../framework/skill-anatomy.md) |
| Which personas + their roles? | [`../agents/navigation.md`](../agents/navigation.md) |
| How is Buddy structured? | [`../agents/buddy/`](../agents/buddy/) |
| Which hooks are active? | `CLAUDE.md §Active Hooks` + [`../orchestrators/claude-code/hooks/`](../orchestrators/claude-code/hooks/) |
| Which workflows? | [`../workflows/runbooks/`](../workflows/runbooks/) |
| Which protocols? | [`../skills/_protocols/navigation.md`](../skills/_protocols/navigation.md) + [`../agents/_protocols/navigation.md`](../agents/_protocols/navigation.md) |
| Which references? | [`../references/navigation.md`](../references/navigation.md) |
| Which engines/generators? | [`../framework/scripts.md`](../framework/scripts.md) |
| Permission/gate/routing per artefact? | [`../framework/agent-autonomy.md`](../framework/agent-autonomy.md) |
| Boot sequence detail? | [`../agents/buddy/boot.md`](../agents/buddy/boot.md) |

## Change pattern

| Change type | Where | Mandatory steps |
|---|---|---|
| New skill | `skills/<name>/SKILL.md` | standard skill format, `Standalone` block, spec-board L1, pre-commit Check 3 (SKILL-FM-VALIDATE) PASS |
| New workflow | `workflows/runbooks/<name>/WORKFLOW.md` | Routing in `process-map.md`, entry in `boot-navigation.md`, new line in skill-map composition map |
| New persona | `agents/<name>.md` (SoT) + `.claude/agents/<name>.md` (CC wrapper) + possibly OC wrapper | Adapter-SoT-Sync (`consistency_check` Check 3) |
| New hook | `orchestrators/claude-code/hooks/<name>.sh` | Header doc, entry in `orchestrators/claude-code/settings.json.template` + re-run `setup-cc.sh`, `tests/hooks/test-<name>.sh`, doc in `CLAUDE.md §Active Hooks` |
| New reference | `references/<name>.md` | Document lift source, add to `references/navigation.md` lookup table |
| Retire a skill | `git rm -r skills/<name>/` (git history is the archive) | Stale cleanup in the same commit |
| Retire a persona | `git rm agents/<name>.md` | Delete adapter wrapper too, stale cleanup |
| Tier 0 change | `CLAUDE.md` / `AGENTS.md` | Verify consistency cascade (`consistency_check` Check 3b), both files in sync |

## Mandatory pre-commit checks (summary)

| # | Check | Severity | Trigger |
|---|---|---|---|
| 1 | PLAN-VALIDATE | BLOCK | Structural plan inconsistency (`plan_engine.py --validate`) |
| 2 | CG-CONV | BLOCK | Wrong commit-message form |
| 3 | SKILL-FM-VALIDATE | BLOCK | Required frontmatter field missing / unknown invocation |
| 4 | SECRET-SCAN | WARN | gitleaks finding in staged content |
| 5 | SOURCE-VERIFICATION | WARN | Board/council review missing line-numbered evidence pointers |

WARN is **not ignorable** — the real failure class is "Buddy forgets",
not "actively bypasses". You belong to the first class; respect warnings.

## Emergency pattern

When something doesn't fit:

| Situation | Reaction |
|---|---|
| Hook blocks | Read the block output, correct disposition, retry |
| Sub-agent ESCALATED | `root_cause_fix` mandatory, no "ignore" |
| Delegation artifact missing | Record scope, goal, agent and success criteria inline for DIRECT; use a persisted brief for other paths |
| Adjust write-scope | No path-whitelist enforcement; if your write was out of intent scope, surface the scope-conflict to the user explicitly |
| Frozen-zone modify wanted | Not without explicit user OK; convention-enforced (WORM) — use a `.correction.md` sidecar |
| Inconsistency detected | Invoke `consistency_check` skill, fix findings systematically |
| User intent unclear | Ask. Default is discuss (CLAUDE.md §2). |

## Next step

When you as an agent change the repo, read [`08-development-and-maintenance.md`](08-development-and-maintenance.md) first
for engine details and conventions. If you need workflow patterns:
[`06-usage-workflows.md`](06-usage-workflows.md).
