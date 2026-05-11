# Agent Autonomy

Tier-1 refinement of Tier-0 invariant §5 (CLAUDE.md / AGENTS.md).

SoT for the question: "who writes which artifact, with which gate,
through which routing".

---

## The three autonomy sub-questions (orthogonal)

Autonomy decisions split into three independent sub-questions.
Every write act must answer all three:

1. **Permission** — may this agent write this path at all?
   Coarse path whitelist in `CLAUDE.md §5`, mirrored in `AGENTS.md §5`.
2. **Gate** — does this act require pre-write review or peer consultation?
   Artifact-type specific, encoded in the table below.
3. **Routing** — who executes the act concretely?
   Encoded in `agents/buddy/operational.md` §Delegation Routing,
   downstream of permission + gate.

The sub-questions are logically orthogonal, but two seam cases exist
(see gate polymorphism below).

---

## Consultation cascade

Three documents form one cascade:

**CLAUDE.md §5** (coarse, Tier-0 anchor)
-> **framework/agent-autonomy.md** (specific, this file)
-> **local workflow runbook** (further refinement when workflow mechanics require it)

**Rule 1 — earlier layer beats later layer:** if CLAUDE.md §5 is explicit
(e.g. "docs/ = Buddy zone"), later layers refine it — not override it.

**Rule 2 — later layer may refine, not invent:** specific layers may
concretize generic layers (e.g. "docs/specs/*.md requires spec_board"),
but not contradict them. Contradictions are bugs and are detected by
`plan_engine --validate`.

**Rule 3 — defensive default:** if a case is unclear (gate heuristic
ambiguous, artifact type missing), **trigger gate, do not write**.
A redundant review is cheaper than a silent regression.

---

## Gate polymorphism

Pre-write gates appear in two structurally different forms:

- **Review-skill gate**: `spec_board` (incl. mode=ux), `code_review_board`,
  `impl_plan_review`, `architecture_coherence_review`.
  Gate is satisfied by running the skill.
- **Peer-consultation gate**: `council`, `solution-expert`.
  Gate is satisfied by consultation, and in merger-cases
  gate and routing are the same mechanism.

In the table below, gate is encoded as `<gate-type>:<target>`, e.g.
`review:spec_board`, `peer:council`, `none`.

### Gate composition (multiple gates in one cell)

If multiple gates are listed (`+`), execution is **sequential in notation order**:

1. Left entry first (notation order is normative).
2. If no veto, run the next gate.
3. If peer and review conflict: peer wins (highest consultation authority).
4. If a cell shows reversed order (`review:X + peer:Y`), table is wrong —
   fix the table, not agent behavior.

Conditional gates are encoded inline in parentheses and apply only when true.

### Merger cases — why not duplicated in routing

For merger cases (`peer:...`), routing is implicit:

- `peer:council` -> council is both gate and routing target.
- `peer:solution-expert` -> same.
- `review:*` agents are also merger-style at review level:
  review output is gate result.

Therefore the delegation-routing table in `operational.md` is **not a full
agent list**. It lists **pure routing decisions**.
Merger cases are represented in the gate column of this file.

---

## Table — artifact type, autonomy, conflict resolution

By artifact category, not by individual file pattern. The category
column drives permission and review; specific path patterns are listed
for reference only.

| Category | Who edits | Who must review | On conflict |
|---|---|---|---|
| **Orchestrator-text** (`agents/`, `framework/`, `skills/`, `workflows/`, `references/`, `templates/`, `context/`, `docs/`) | Buddy directly | spec_board on substantive changes; none on wording/typo | run `plan_engine --validate`; on disagreement, escalate to user |
| **Consumer code** (`src/`, `scripts/` consumer-side, `tests/`) | main-code-agent (NOT Buddy) | code_review_board post-write | MCA iterates; spec change ⇒ escalate to Buddy |
| **Spec** (`docs/specs/*.md`) | Buddy via build-workflow Specify | spec_board pre-write (Standard or Deep) | convergence_loop max 3 → user escalation |
| **ADR** (`docs/decisions/`, `decisions.md`) | Buddy | council on architecture decisions; none on small docs | council decision binds |
| **Config / hooks** (`pyproject.toml`, `package.json`, `.claude/settings.json`, `orchestrators/**/hooks/`, `scripts/hooks/`) | Buddy or main-code-agent depending on scope | code_review_board on semantic change | revert; reopen with explicit user gate |
| **Generated / AUTO blocks** (`framework/skill-map.md` AUTO, `framework/agent-skill-map.md`, `*/navigation.md` AUTO) | regenerator scripts only | hook validators (consistency_check, AGENT-SKILL-DRIFT, RUNBOOK-DRIFT) | rerun the generator; manual edits revert on next run |

### "Substantial" vs "wording" — mechanically testable

A wording/typo fix:
- no change to normative prose tokens (MUST, MUST NOT, never, only, …)
- no add/remove negations or quantifiers
- no new/removed bullet
- no new/removed subsection/header level
- no semantic interface change (field names, types, paths, agents, workflows)

If any criterion is violated, it is **substantive** → trigger the
review for the artefact category.

### Path precedence

When a path matches more than one category, the most specific category
wins for permission and routing; review obligations are unioned.
Example: `src/auth/session.py` is consumer code AND security-relevant —
MCA writes, code_review_board + security both review.

### Delegation artifact

CLAUDE.md requires: no agent call without a delegation artifact.

| Path | Artifact | Minimum content |
|---|---|---|
| Direct | plan block in turn output or state file | scope + goal + agent (1 sentence each) |
| Standard | gate file in `docs/solve/` or `docs/tasks/` | scope + goal + agent + ACs + constraints |
| Full | state file with plan + review output | full frame + plan-review block |

### "Autonomy" — two distinct meanings

- **In this file:** permission / who-reviews / conflict resolution.
- **In workflow runbooks:** phase mode (Discuss / Bounded / Agent-autonomous / Mechanical).

These are orthogonal concepts; avoid cross-document confusion.

---

## Enforcement via `plan_engine --validate`

Autonomy-specific checks:
1. mirror-check (all sections referencing this file in CLAUDE/AGENTS)
2. existence-check (this file + expected header + main table)
3. reference integrity (links in CLAUDE/AGENTS/operational/solve workflow)
4. cross-reference warning (routing/gate targets vs operational routing table,
   merger-aware to reduce false positives)

---

## Consumers of this file

Referenced by:
- `CLAUDE.md` §Code Delegation
- `AGENTS.md` §Code Delegation
- `agents/buddy/operational.md` self-execution + delegation routing
- `workflows/runbooks/solve/WORKFLOW.md` phase autonomy
- `workflows/runbooks/docs-rewrite/WORKFLOW.md`
- `workflows/runbooks/fix/WORKFLOW.md` execute skills
- `framework/process-map.md`
- `framework/getting-started.md`

Consciously not listed: build/review/research/context_housekeeping runbooks,
which use phase-mode autonomy and rely on Tier-0 reference path.

---

## Short version (cold start)

If you need a fast autonomy answer:
1. find artifact type in table
2. check permission
3. check gate (`review:X`, `peer:Y`, `none`)
4. check routing target
5. apply cascade (CLAUDE permission, this file gate+routing)
6. unknown type -> analogy rule; no analogy -> defensive default
7. wording vs substantial unclear -> apply mechanical wording test; if unsure, gate
