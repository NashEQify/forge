# 09 — Agent Guide

> **Audience: AI coding agents.** Human reader → see
> [`10-human-guide.md`](10-human-guide.md).

For coding agents (Claude Code, OpenCode, Cursor, etc.). Compact required
reading before any actions are taken against the repo.

## Start here

When you see this repo for the first time:

1. **Read Tier 0:** [`../CLAUDE.md`](../CLAUDE.md) (Claude Code) or
   [`../AGENTS.md`](../AGENTS.md) (OpenCode). 6-7 invariants — never override.
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

1. **Board/Council: Buddy = dispatcher.** On board/council do not read
   review files, do not analyse findings, do not write consolidations,
   do not verify fixes. Only: spawn → read chief signal → SAVE → escalate.

2. **Default: discuss, don't implement.** Implement only on a clear
   imperative. Unclear → ask. Self-triggered → always discuss. Context
   writes and bookkeeping: no gate.

3. **Pre-Delegation.** No agent call without a delegation artefact. Direct:
   plan block or scope/goal/agent stated explicitly in the turn.
   Standard/Full: gate file. Routing: `framework/process-map.md`.

4. **Code delegation.** Product code → main-code-agent. Path whitelist
   enforced mechanically by `path-whitelist-guard` — don't simulate
   mentally, react to a block. Orchestrator work (agents/, framework/,
   skills/, context/, docs/) Buddy writes directly.

5. **Stale cleanup.** Artefact declared retired/replaced/sunset: clean up
   all active references in non-frozen files in the same commit.
   `grep -rn <artefact>` + filter frozen zones + fix the rest.

6. **Deployment verification.** After deploy: visually verify, not just
   HTTP 200. If a visual check is not possible: report explicitly and ask
   the user to verify.

OpenCode (`AGENTS.md`) may have additional adapter invariants — under OC
the relevant `AGENTS.md` is the source, the CC `CLAUDE.md` is
adapter-specific.

## Buddy phases

Strictly observed:

```
RECEIVE → ACT → BOUNDARY
```

### RECEIVE

Three mental states before you reply:

| State | Trigger | Reaction |
|---|---|---|
| **Incident** | Expectation ≠ reality | `root_cause_fix/SKILL.md` mandatory |
| **Substantive** | User wants to do/change/build | Clarify intent fit + sequencing |
| **Trivial** | Confirmation, status, greeting | answer |

### ACT

- Board/Council: spawn, do **NOT** read along.
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
filter, fix all active refs in the same commit. Pre-commit Check 5 warns.

### DO 5: Respect generator output

The `framework/skill-map.md` AUTO block is generated. Edit only the
sections outside the `<!-- SKILL-MAP-AUTO-START -->` /
`<!-- SKILL-MAP-AUTO-END -->` markers. Same for the 8 navigation.md files.

### DO 6: Skill anatomy for new skills

Mandatory frontmatter fields: `name`, `description` (with "Use when"),
`status`, `invocation.primary`. Anatomy-v2 conformant. Pre-commit Check 7
BLOCKS otherwise.

### DO 7: Persist gate on status change

Status change without context update is half. Pre-commit Check 6
(PERSIST-GATE) is only WARN — discipline closes the gap.

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

### DON'T 1: Read along on board reviews

CLAUDE.md §1. If you read along in the board, your interpretation
colours the findings, multi-perspective guarantee is lost.

### DON'T 2: Implement without a clear imperative

CLAUDE.md §2. Default is discuss. Self-triggered always discuss.
Context writes + bookkeeping are the exception.

### DON'T 3: Sub-agent call without a delegation artefact

CLAUDE.md §3. Violation = constraints get forgotten, sub-agent does
"something other than meant", refactoring later.

### DON'T 4: Writes outside the path whitelist

`.claude/path-whitelist.txt` defines the allowed paths.
`path-whitelist-guard.sh` blocks mechanically. React to the block, do
not simulate mentally.

### DON'T 5: Writes into frozen zones

`.claude/frozen-zones.txt` lists glob patterns enforced by
`frozen-zone-guard.sh`. Canonical entry: `context/history/**`.
WORM. Corrections via a `.correction.md` sidecar (convention).

### DON'T 6: Raw edits on task YAMLs (status/readiness)

Status/readiness ALWAYS via the `task_status_update` skill. Pre-commit
Check 2 (TASK-SYNC) warns otherwise — but that is just a symptom, not
the diagnosis.

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

For a bug → `fix` workflow Phase A is not optional. Even for a "small" bug.

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
| New skill | `skills/<name>/SKILL.md` | standard skill format, `Standalone` block, spec-board L1, pre-commit Check 7 PASS |
| New workflow | `workflows/runbooks/<name>/WORKFLOW.md` | Routing in `process-map.md`, entry in `boot-navigation.md`, new line in skill-map composition map |
| New persona | `agents/<name>.md` (SoT) + `.claude/agents/<name>.md` (CC wrapper) + possibly OC wrapper | Adapter-SoT-Sync (`consistency_check` Check 3) |
| New hook | `orchestrators/claude-code/hooks/<name>.sh` | Header doc, `.claude/settings.json`, `tests/hooks/test-<name>.sh`, doc in `CLAUDE.md §Active Hooks` |
| New reference | `references/<name>.md` | Document lift source, add to `references/navigation.md` lookup table |
| Retire a skill | `git rm -r skills/<name>/` (git history is the archive) | Stale cleanup in the same commit |
| Retire a persona | `git rm agents/<name>.md` | Delete adapter wrapper too, stale cleanup |
| Tier 0 change | `CLAUDE.md` / `AGENTS.md` | Verify consistency cascade (`consistency_check` Check 3b), both files in sync |

## Mandatory pre-commit checks (summary)

| # | Check | Severity | Trigger |
|---|---|---|---|
| 1 | PLAN-VALIDATE | BLOCK | Structural plan inconsistency |
| 2 | TASK-SYNC | WARN | Status/readiness edit without skill |
| 3 | OBLIGATIONS | WARN | docs/dashboard/plan_engine touched, deploy needed |
| 4 | CG-CONV | BLOCK | Wrong commit-message form |
| 5 | STALE-CLEANUP | WARN | Marker `STALE:|RETIRED:|SUNSET:` with live refs |
| 6 | PERSIST-GATE | WARN | Status change without context update |
| 7 | SKILL-FM-VALIDATE | BLOCK | Required frontmatter field missing / unknown invocation |

WARN is **not ignorable** — the real failure class is "Buddy forgets",
not "actively bypasses". You belong to the first class; respect warnings.

## Emergency pattern

When something doesn't fit:

| Situation | Reaction |
|---|---|
| Hook blocks | Read the block output, correct disposition, retry |
| Sub-agent ESCALATED | `root_cause_fix` mandatory, no "ignore" |
| Gate file missing | Create it, then sub-agent call — not without |
| Extend path whitelist | Edit `.claude/path-whitelist.txt` (this is not a frozen zone) |
| Frozen-zone modify wanted | Not without explicit user OK; mechanically blocked |
| Inconsistency detected | Invoke `consistency_check` skill, fix findings systematically |
| User intent unclear | Ask. Default is discuss (CLAUDE.md §2). |

## Next step

When you as an agent change the repo, read [`08-development-and-maintenance.md`](08-development-and-maintenance.md) first
for engine details and conventions. If you need workflow patterns:
[`06-usage-workflows.md`](06-usage-workflows.md).
