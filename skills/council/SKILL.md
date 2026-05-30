---
name: council
description: >
  Structured decision-making. Two modes: (a) Architectural — 3-4
  council-member subagents in parallel, context isolation, Buddy
  consolidates. (b) Interactive — Buddy moderates a user dialog
  with perspectives (phase 1-2-3).
  Triggers when an architecture/strategy decision has more than one viable path and is hard to reverse; NOT for single-path or easily-reversible decisions (decide directly).
status: active
relevant_for: ["solution-expert"]
invocation:
  primary: workflow-step
  secondary: [user-facing]
disable-model-invocation: false
modes: [architectural, interactive]
uses: []
---

# Skill: council

Structured decision-making in two mode flavours.

## Mode choice (MUST — decide before calling)

| Mode | When | How |
|------|------|-----|
| **Architectural Council** | Buddy has its own proposal but is uncertain; architecture decision with pattern debt; >1 layer; hard to reverse; user does NOT want to decide alone | 4 domain `council-member` subagents + **1 adversary member (required)** in parallel via the Agent tool. Each domain member has its own role (e.g. architecture, pragmatist, operations, pipeline-architect). The adversary runs the smart-but-wrong check + an explicit authority audit (no lean statement). Each is context-isolated. A briefing file is the input. Buddy consolidates the returns into the synthesis. |
| **Interactive Council** | User wants to decide in dialog; perspectives should argue visibly; user feedback loop per round | Buddy moderates phase 1-2-3 (see below). Perspectives speak in first person. The user answers between rounds. |

Default on a trigger from `operational.md` (architecture decision,
Buddy uncertain): **Architectural Council**. Use Interactive only
when the user explicitly asks for a dialog mode.

## Anti-patterns — when NOT to council

### Cross-scope contradiction ≠ current-scope undecidable

If the question presents as "spec corpus has multiple representations
of X across different scopes", FIRST run the scope-check:

1. Is the CURRENT-SCOPE path internally consistent? Check producer +
   consumer + adjacent uses. If all use the same representation
   internally, the path IS decidable.
2. Are the contradicting representations in DIFFERENT scopes (legacy
   code path / future planned work / cross-cutting infrastructure)?
3. Is there a way to preserve the current-scope path + file the
   cross-scope normalization as a separate follow-up task?

If 1 + 2 + 3 = yes: **NO council**. Preserve current-scope path; file
the normalization task. Council is OVER-ESCALATION for cross-scope
contradictions when current-scope is internally consistent.

Council IS triggered by: current-scope has no decidable path;
multiple viable options exist WITHIN scope; choice is M-level-blocking;
reversibility is low.

"Spec corpus has multiple representations" sounds like undecidability
but can be just legacy + future + current-active living side by side.
If the active scope's producer + consumer + adjacent uses all align
on one representation, the path IS decidable; council on the broader
contradiction wastes a cycle and introduces orchestrator-re-framing
risk (a Council recommendation taken autonomously becomes a frame
the user has to unwind). The check is mechanical:
scope-internal-consistency first, cross-scope normalization second.

## Architectural Council — spawn pattern

1. **Briefing file** (self-contained): `docs/reviews/council/{date}-{topic}-briefing.md`
   — question, intent anchoring, context-file paths, Buddy's
   proposal (to review, NOT to adopt), constraints, output format,
   known conflicts.
2. `mkdir -p docs/reviews/council/`.
3. **Spawn N members in ONE tool block** (4 domain + 1 adversary):
   - subagent_type: `council-member` (domain) or `code-adversary` (adversary)
   - `run_in_background: true`
   - prompt: role + briefing path + output path
   - Adversary mandatory: smart-but-wrong + explicit authority audit,
     no lean statement.
4. Wait for returns.
5. **Buddy synthesises** (required format):
   - §1 Position map per member: Lean ("A+", "C+mitigations",
     "no-lean" for adversary) + Primary rationale (1 sentence) +
     Secondary-argument carriers (list with section ref + 3-5 words
     per sub-issue).
   - §2 Conflicts between members named.
   - §3 Convergence points with member-file range citations
     ("3/4 caught Y: dse + opsrel + pcc (pcc.md:63-95)").
   - §4 Recommendation per sub-decision.
   - §5 Required verify steps for the follow-up task (when lean
     substantial).
   - §6 User decides.

**Trigger consequence (NON-NEGOTIABLE):** Council trigger from
`operational.md` (>1 path + hard to reverse + >1 layer + impact +
Buddy uncertain) → spawn MUST be in the SAME tool block as other
follow-up actions. Never "council later; X first". Forgetting →
Buddy decides alone, user finds out too late.

## Interactive Council — user dialog

When a decision has multiple valid paths and the user has to be
involved. Not for clear-consensus questions (direct answer suffices).

**Inputs (caller provides):** problem statement (1-3 sentences);
intent anchoring (one-sentence derivation chain); 3-6 perspectives
ordered by rank, each with identifier + key question. Optional:
frame report (candidates from `frame/SKILL.md` §sub-step 7+8).

**Perspective orientation:**

| Decision type | Typical perspectives |
|---|---|
| Technical architecture | Security, sovereignty, simplicity, experience, compatibility, scale (→ solution-expert fixed) |
| Project prioritization | Impact, effort, urgency, learning, risk |
| Infrastructure / ops | Reliability, security, sovereignty, simplicity, cost |
| Personal direction | Alignment, opportunity cost, reversibility, energy |
| Buy / invest | Need, sovereignty, cost, quality, alternatives |

Rank = default weighting on conflicts (higher wins). User can
override; document it.

### Phase 1 — Intake check

(1) **Derivation chain** — repeat intent anchoring; if missing/broken,
STOP and clarify. (2) **Problem vs symptom** — name the suspected
real problem if you smell one; don't continue until settled.
(3) **Null option** — what if we do nothing? 1-2 sentences.

Then present candidates (2-4; frame-report candidates first if
available; null option if realistic). 2-3 sentences each, no
assessment.

Close: missing candidate? perspectives right? **Wait for user.**

### Phase 2 — Council rounds

Per round:
1. Pick 2-3 perspectives that contribute most; not all every time.
2. Each speaks in first person, identifier prefixed, 2-4 sentences:
   "**Reliability:** what worries me about option A is ...".
3. Name conflicts immediately; default = rank wins; ask user if
   they want to weigh differently.
4. End with a concrete question (not "what do you think?"): "X says
   A, Y says B. What weighs more here?". **Wait for user.**

Moderation: user drifts against higher-ranked perspective → object,
make it visible. Consensus forming → summarize, phase 3. User
overrides a perspective → accept + document. No convergence after
2 rounds → summarize open conflicts, ask user directly.

### Phase 3 — Synthesis

(1) Recommendation (1-2 options). (2) What gets sacrificed (which
perspective loses + what that means concretely). (3) Open risks.
(4) Demand decision ("Are we going with X?", not "looks good?").
Council finished only when user has chosen.

## Done

Intent anchoring documented; problem validated; perspectives
argued + user responded; conflicts resolved (overridden ranks
justified); trade-offs named; user chose. Substantial decisions →
offer ADR in `decisions.md`.

## Contract

**INPUT:** problem statement + intent anchoring + perspectives
(required); optional frame report.

**OUTPUT:** decision (1 sentence, user-confirmed) + rationale
(references perspectives + rank weighting) + trade-offs + open risks
+ overridden ranks (where applicable).

**DOES NOT:** implement; write spec; choose autonomously (user
always decides).

**FAIL:** no convergence after 2 rounds → summarize conflicts, ask
direct; user uncertainty → re-check null option, research handoff.

## Relation to solution-expert

`solution-expert` = preconfigured specialization for technical
architecture (fixed perspectives: security, sovereignty, simplicity,
experience, compatibility, scale). For other decision types: Buddy
instantiates this skill directly with situational perspectives.
