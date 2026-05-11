---
name: council
description: >
  Structured decision-making. Two modes: (a) Architectural — 3-4
  council-member subagents in parallel, context isolation, Buddy
  consolidates. (b) Interactive — Buddy moderates a user dialog
  with perspectives (phase 1-2-3).
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

## Architectural Council — spawn pattern (required skeleton)

```python
# 1. Write the briefing file (self-contained):
#    docs/reviews/council/{date}-{topic}-briefing.md
#    Contains: question, intent anchoring, context-file paths,
#    Buddy's proposal (to be reviewed, NOT to be adopted),
#    constraints, output format, conflicts between perspectives.

# 2. Make sure the output directory exists:
#    mkdir -p docs/reviews/council/

# 3. Spawn N council-members — IN THE SAME TOOL BLOCK (all 5
#    Agent calls in one response: 4 domain + 1 adversary), not
#    sequentially.
#    Each receives:
#    - subagent_type: "council-member" (or "code-adversary" for
#      the adversary role)
#    - run_in_background: true (parallel)
#    - prompt: role + briefing path + output path
#
#    Adversary requirement: 1 member runs the smart-but-wrong
#    check + the explicit authority audit, without a lean
#    statement. Prevents the sole-found-drift pattern (the
#    adversary catches what the domain members miss).

# 4. Wait for all returns (notifications).
# 5. Buddy consolidates the N output files into the synthesis
#    (required format):
#    §1 Position map: per member entry MUST contain:
#      - Lean (e.g. "A+", "C+mitigations", "no-lean" for the
#        adversary)
#      - Primary rationale (one sentence, the core argument)
#      - Secondary-argument carriers (list with section ref +
#        3-5 words): further issues / sub-bugs / patterns the
#        member raised in their member file's own section, even
#        when not the primary rationale.
#    §2 Conflicts between members named.
#    §3 Convergence points (with member-file range citations on
#       a consolidation claim, e.g. "3/4 caught Y: dse + opsrel
#       + pcc (pcc.md:63-95)").
#    §4 Recommendation per sub-decision.
#    §5 Required verify steps for the follow-up task (when the
#       lean is substantial).
#    §6 The user decides finally.
#
# Rationale for the position-map format: without
# secondary-argument carriers, an external spot-check without
# member-file access is blind and produces false-positive
# "over-consolidated" accusations. Detail:
# framework/agent-patterns.md §1-Position-Map-Consolidation-
# Visibility.
```

**Trigger consequence (NON-NEGOTIABLE):** when a council trigger
from `operational.md` fires (>1 path + hard to reverse + >1
layer + impact + Buddy uncertain), the spawn MUST happen in the
SAME tool block as other follow-up actions. Never "council is
next; I'll do X first". Risk of forgetting: Buddy decides alone,
the user finds out too late. Pattern: a frame recommendation is
taken autonomously inside `frame` without a council spawn → the
user's correction has to escalate.

## Interactive Council — phases (user dialog)

Interactive council for structured decision-making with the user.

## When to call

When a decision has multiple valid paths with different
trade-offs and the user has to be involved. Not for questions
with clear consensus — a direct answer is enough there.

## How to call

The calling agent (typically Buddy) instantiates the council
with:

1. **Problem statement:** what has to be decided? (1-3
   sentences).
2. **Intent anchoring:** which operational intent does this
   serve? (one-sentence derivation chain).
3. **Perspectives:** 3-6 perspectives, ordered by rank. Each
   with an identifier and a key question.

Example call by Buddy:

> Council on: how do we structure the backup system?
> Intent: Task 042 → "harden the infrastructure" → "autonomous
> assistant".
> Perspectives (by rank):
> 1. **Reliability** — how safe is the recovery?
> 2. **Sovereignty** — where does the data live? Who has
>    access?
> 3. **Simplicity** — how few moving parts can we have?
> 4. **Cost** — what does it cost per month?

### Choosing perspectives

The calling agent picks perspectives that fit the decision
type. Orientation:

| Decision type | Typical perspectives |
|---------------|----------------------|
| Technical architecture | Security, sovereignty, simplicity, experience, compatibility, scale (→ solution-expert has these fixed) |
| Project prioritization | Impact, effort, urgency, learning, risk |
| Infrastructure / ops | Reliability, security, sovereignty, simplicity, cost |
| Personal direction | Alignment (with values), opportunity cost, reversibility, energy |
| Buy / invest | Need, sovereignty, cost, quality, alternatives |

Those are examples, not fixed lists. The agent proposes
perspectives; the user confirms or corrects before the council
starts.

Rank is the default weighting on conflicts. Higher = wins. The
user can override — that gets documented.

## Flow

Three phases. Track internally which phase you're in. Don't
jump ahead.

---

### PHASE 1 — INTAKE CHECK

Run three checks. Present the results to the user in your first
reply:

**1. Derivation chain.** Repeat the intent anchoring from the
caller. If it isn't intact or is missing: STOP, clarify with the
user. No analysis without intent.

**2. Problem vs symptom.** Is the asked question the actual
problem? When you suspect it's a symptom: name what you think
the actual problem is. Ask the user. Don't continue until that
is settled.

**3. Null option.** What happens if we do nothing? Assess in 1-2
sentences. "Do nothing" stays a candidate when the cost of
acting exceeds the cost of inaction.

Then present solution candidates. When a **frame report** (from
`frame` via solve phase 1 or build specify interview) has
already worked out a solution space: take those candidates as
the starting point. Check whether, from the council's
perspective, additional approaches are missing that didn't show
up in the frame. When no frame input is available: present 2-4
candidates of your own.

Frame-report format (as input): a list of approaches with name,
core idea, distinguishing axis, happy path, edge case, effort,
reversibility (see `frame/SKILL.md` §sub-step 7+8). Council
compatible.

2-3 sentences each: what is it, what is the core idea? Include
the null option when realistic. No assessment — only candidates
on the table.

Close with: any missing candidate? Should one go? Is the problem
statement right? Are the perspectives right?

**Wait for the user's reply.**

---

### PHASE 2 — COUNCIL ROUNDS

Perspectives argue. Per round:

**1. Pick 2-3 perspectives** that contribute most to the current
state. Not all every time — only those with substantive
contribution.

**2. Each perspective speaks in first person, with its
identifier.** Short, focused, 2-4 sentences. No repetitions.
Only what this perspective sees that others don't:

> **Reliability:** what worries me about option A is...
> **Simplicity:** option B has a clear advantage —...
> **Cost:** I see hidden costs in option C in...

**3. Name conflicts immediately.** When perspectives contradict
each other: say which rank wins by default. Ask the user
whether to follow the default or weigh differently.

**4. Every round ends with a concrete question.** No open "what
do you think?" question. Instead: "Reliability says X,
simplicity says Y. What weighs more for you here?"

**Wait for the user's reply.**

The next round builds on the user's answer. Pick up new aspects,
bring in other perspectives, sharpen or drop options.

**Moderation rules:**
- When the user drifts in a direction that violates a
  higher-ranked perspective: object. Don't block — make it
  visible.
- When consensus is forming: don't keep talking artificially.
  Summarize, phase 3.
- When the user explicitly overrides a perspective: accept, but
  document it in the synthesis.
- When there is no convergence after two rounds: summarize the
  open conflicts, ask the user directly for direction.

---

### PHASE 3 — SYNTHESIS

When the user is ready or there has been enough discussion:

**1. Recommendation.** 1-2 options, clearly stated.

**2. What gets sacrificed.** Explicitly: which perspective
loses on this choice and what that means concretely.

**3. Open risks.** What don't we know yet? What could go
wrong?

**4. Demand a decision.** Not "looks good?" but: "Are we going
with option X?"

The council is only finished when the user has made a clear
choice.

---

## Done criteria

Check at the end whether all are met:

1. **Intent anchoring:** the derivation chain is documented.
2. **Problem validated:** the user has confirmed the problem
   statement.
3. **Perspectives heard:** the relevant perspectives have
   argued; the user has responded.
4. **Conflicts resolved:** contradictions named; the user has
   decided. Overridden ranks justified.
5. **Trade-offs named:** what gets sacrificed is explicit.
6. **Decided:** the user has made a clear choice.

## Result

After the council, the moderating agent delivers to the caller
(or documents directly):
- Decision (one sentence).
- Rationale (2-3 sentences, references the perspectives).
- Trade-offs (what was sacrificed).
- Open risks.
- Overridden ranks (where applicable, with rationale).

For substantial decisions: offer an ADR in `decisions.md`.

## Contract

### INPUT
- **Required:** problem statement (what has to be decided, 1-3
  sentences).
- **Required:** intent anchoring (which operational intent it
  serves, one-sentence derivation chain).
- **Required:** perspectives (3-6, ordered by rank, each with
  identifier and key question).
- **Optional:** frame report (from `frame`) — solution
  candidates as a starting point.
- **Context:** no extra files needed — the council works in a
  dialog with the user.

### OUTPUT
**DELIVERS:**
- Decision: one sentence, explicitly confirmed by the user.
- Rationale: 2-3 sentences, references perspectives + rank
  weighting.
- Trade-offs: what gets sacrificed, explicitly named.
- Open risks: what we don't know.
- Overridden ranks: where applicable, with the user's
  rationale.

**DOES NOT DELIVER:**
- No implementation — only decision-making.
- No spec — the decision must be transferred separately into a
  spec / ADR.
- No autonomous choice — the user always decides; the council
  moderates.

**ENABLES:**
- Solve refine: a sharpened approach for the artifact phase.
- Build specify: an architecture decision as a spec
  constraint.
- ADR: on substantial decisions → `decisions.md` entry.

### DONE
- Intent anchoring documented.
- Problem validated (the user has confirmed the problem
  statement).
- Relevant perspectives have argued; the user has responded.
- Conflicts resolved (contradictions named, the user has
  decided, overridden ranks justified).
- Trade-offs named (what gets sacrificed is explicit).
- The user has made a clear choice.

### FAIL
- **Retry:** no convergence after 2 rounds → summarize the
  open conflicts, ask the user directly for direction.
- **Escalate:** user uncertainty despite dialog → re-check the
  null option, possibly research handoff.
- **Abort:** not foreseen — the council always ends with a
  user decision or an explicit defer.

## Relation to solution-expert

`solution-expert` is a preconfigured specialization of this
skill for technical architecture decisions. It has fixed
perspectives (security, sovereignty, simplicity, experience,
compatibility, scale) and runs the council itself as moderator.

For all other decision types Buddy (or another agent)
instantiates this skill directly with situational perspectives.
