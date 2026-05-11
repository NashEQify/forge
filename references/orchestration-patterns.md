# Orchestration Patterns

> **Source:** lift from `github.com/addyosmani/agent-skills`
> (`references/orchestration-patterns.md`, 2026-05-01). MIT licence.
>
> **Adaptation status:** content adopted 1:1 — the patterns are
> orchestrator-agnostic and map our multi-agent stack (spec board /
> code review board / council / sub-skills) well. The **mapping table**
> below shows how our existing patterns map to Addy's catalog.

Reference catalog of agent orchestration patterns this repo endorses, plus
anti-patterns to avoid. Read this before adding a new slash command that
coordinates multiple personas, or before introducing a new persona that
"wraps" existing ones.

The governing rule: **the user (or a slash command) is the orchestrator.
Personas do not invoke other personas.** Skills are mandatory hops inside a
persona's workflow.

---

## Mapping to forge patterns

| Addy pattern | Our equivalent |
|---|---|
| Direct invocation | Buddy delegates directly to a single persona (e.g. `code-review`, `security`, `solution-expert`) |
| Single-persona slash command | Skills like `frame`, `task_creation`, `youtube_subtitles` (user-invocable) |
| Parallel fan-out with merge | `spec_board` (standard 4 / deep 7 personas) + `code_review_board` (L1 core / L2 full) + `council` architectural mode + UX board |
| Sequential lifecycle | `build` / `solve` / `fix` / `review` workflows (user-driven phase by phase) |
| Agent teams (debate) | Not adopted — council is parallel fan-out, not debate. Phase-G council synthesis is Buddy consolidation, not direct teammate-message. |

| Addy anti-pattern | Our risk |
|---|---|
| Router persona | Before the multi-axis consolidation: code-review-board pattern replication across 14 personas had a similar smell, resolved through the hybrid (1 skill with 3 axes + 11 specialists) |
| Persona calling persona | Strictly upheld — every multi-persona run goes through Buddy as the orchestrator |
| Sequential orchestrator paraphrases | Workflows have user gates (e.g. root_cause_fix phase A → B user gate) — anti-pattern actively avoided |
| Deep persona trees | spec_board → board-chief consolidation is 1-layer; no deep nesting |

---

## Endorsed patterns

### 1. Direct invocation (no orchestration)

Single persona, single perspective, single artifact. The default and the cheapest option.

```
user → code-reviewer → report → user
```

**Use when:** the work is one perspective on one artifact and you can describe it in one sentence.

**Examples in forge:**
- "Review this PR" → `code-review` persona via the L1 code review board.
- "Find security issues in `auth.py`" → `code-security` persona or `security` (offensive).
- "What tests are missing for the checkout flow?" → `tester` design mode.

**Cost:** one round trip. The baseline you should always compare orchestrated patterns against.

---

### 2. Single-persona slash command

A slash command that wraps one persona with the project's skills. Saves the user from re-explaining the workflow every time.

```
/review → code-reviewer (with code-review-and-quality skill) → report
```

**Use when:** the same single-persona invocation happens repeatedly with the same setup.

**Examples in forge (skills-not-slashcommands equivalent):**
- `frame` skill — wraps problem-analysis discipline (8 sub-steps).
- `shipping_and_launch` skill — wraps production-launch discipline.
- `task_creation` skill — wraps task-creation discipline.

**Cost:** same as direct invocation. The slash command is just a saved prompt.

**Anti-signal:** if the slash command's body is mostly "decide which persona to call," delete it and let the user call the persona directly.

---

### 3. Parallel fan-out with merge

Multiple personas operate on the same input concurrently, each producing an independent report. A merge step (in the main agent's context) synthesizes them into a single decision.

```
                ┌──→ persona-A → report-A ─┐
user → /command ┼──→ persona-B → report-B ─┼→ main agent merges → user
                └──→ persona-C → report-C ─┘
```

**Use when:**
- Multiple distinct perspectives are genuinely needed
- The perspectives are independent (no persona needs another's output)
- The merge logic is straightforward (severity ranking, dedup, conflict resolution)

**Examples in forge:**
- **Spec board:** standard (adversary + implementer + impact + chief) or deep (+ adversary-2 + adversary-sonnet + consumer).
- **Code review board L2:** core (code-review + code-adversary) + specialists (code-security / code-data / code-reliability / code-domain-logic / code-api-contract / code-ai-llm / code-docs-consumer) + code-chief consolidation.
- **UX board:** board-ux-heuristic (primus + consolidator) + board-ux-ia + board-ux-interaction.
- **Council architectural mode:** 3–7 council-members in parallel + Buddy consolidates.

**Validation checklist (before a new fan-out):**
- [ ] Each persona contributes a **distinct** perspective (not paraphrases of each other).
- [ ] Merge logic is **explicit** (consolidation-preservation.md tracking table mandatory).
- [ ] Cost is **justified** (vs single-persona summary).
- [ ] Failure mode is **named** (what if 2 of 3 personas disagree?).
- [ ] Drill + trace enforcement on reviewer fan-out (chief-enforced).

---

### 4. Sequential lifecycle (user as orchestrator)

User invokes commands in sequence — each phase produces an artifact the next phase consumes. **The user is the orchestrator**, not an agent.

```
user → /spec → spec.md → review → /plan → plan.md → /build → code → /ship → deployed
        ↓                            ↓                   ↓                ↓
    User checks    User checks      User checks      User checks
```

**Use when:**
- A multi-phase workflow needs human checkpoints (specify → review → build → ship)
- Each phase output is an artifact the user inspects before moving on
- Phases can be skipped or re-run independently

**Examples in forge:**
- `build` workflow: specify → prepare → execute → verify → close.
- `solve` workflow: frame → refine → artifact → validate → execute.
- `fix` workflow: specify → prepare → execute → verify → close.

**Anti-signal:** if you're tempted to write an agent that automates the whole pipeline → STOP. That's anti-pattern C.

---

### 5. Agent Teams (debate, experimental)

Multiple personas spawned as **teammates** (not subagents) that can message each other directly. Used for adversarial investigation where the right answer must emerge from cross-examination.

**Status in forge:** **Not yet adopted.** Our council is parallel fan-out (pattern 3) — Buddy consolidates the isolated outputs. **Council is decision-making, not adversarial investigation.**

A use case that might benefit from agent teams: a multi-axis council
with 4 council-members. On convergent recommendations, pattern-sharing
insights would stay siloed (no direct teammate-message). On a complex
council with divergent perspectives: check whether an agent-teams setup
fits better.

**Setup note (carried over from Addy):** Agent Teams is experimental. In `~/.claude/settings.json`:

```json
{
  "env": {
    "CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS": "1"
  }
}
```

Requires Claude Code v2.1.32 or later.

---

## Anti-patterns

### A. Router persona ("meta-orchestrator")

A persona whose job is to decide which other persona to call.

```
/work → router-persona → "this needs a review" → code-reviewer → router (paraphrases) → user
```

**Why it fails:**
- Pure routing layer with no domain value
- Adds two paraphrasing hops → information loss + roughly 2× token cost
- The user already knew they wanted a review; they could have called `/review` directly
- Replicates the work that slash commands and intent mapping in `AGENTS.md` already do

**forge avoidance:**
- `framework/process-map.md` is the routing doc — no router persona.
- Buddy IS the router, but not as a router-persona skill — Buddy uses process-map.md and delegates directly.

**What to do instead:** add or refine slash commands / skills. Document intent → command mapping in `framework/process-map.md` and `agents/buddy/operational.md`.

---

### B. Persona that calls another persona

A `code-reviewer` that internally invokes `security-auditor` when it sees auth code.

**Why it fails:**
- Personas were designed to produce a single perspective; chaining them defeats that
- The summary the calling persona passes loses context the called persona needs
- Failure modes multiply (which persona's output format wins? whose rules apply?)
- Hides cost from the user

**forge avoidance:**
- Strictly upheld: every multi-persona dispatch goes through Buddy. code-review (axis persona) has it explicit in its anti-patterns section: "NOT: produce findings of another persona domain. INSTEAD: invoke a specialist at L2."
- The multi-axis hybrid actively respects it: code-review covers 3 axes (correctness / architecture / performance) and RECOMMENDS specialists — does not start them itself.

**What to do instead:** have the calling persona **recommend** a follow-up audit in its report. The user or a slash command runs the second pass.

---

### C. Sequential orchestrator that paraphrases

An agent that calls `/spec`, then `/plan`, then `/build`, etc. on the user's behalf.

**Why it fails:**
- Loses the human checkpoints that catch wrong-direction work
- Each hand-off summarizes context — accumulated drift over a long pipeline
- Doubles token cost: orchestrator turn + sub-agent turn for every step
- Removes user agency at exactly the points where judgment matters most

**forge avoidance:**
- Workflows have phase gates with user checkpoints (e.g. `root_cause_fix` phase A → user gate → phase B).
- `build` workflow: specify → spec_board PASS gate → prepare → MCA plan-review gate → execute → ... — every gate is a user-visibility point.

**What to do instead:** keep the user as the orchestrator. Document the recommended sequence in `README.md` / a workflow runbook and let users invoke it.

---

### D. Deep persona trees

`/ship` calls a `pre-ship-coordinator` that calls a `quality-coordinator` that calls `code-reviewer`.

**Why it fails:**
- Each layer adds latency and tokens with no decision value
- Debugging becomes a multi-level investigation
- The leaf personas lose context to multiple summarization steps

**forge avoidance:**
- Max depth is 1: Buddy → skill / persona. Skills load `_protocols/`; that's flat load, not a deep tree.
- Spec board: Buddy → 7 personas in parallel + 1 chief = depth 1, no deep tree.
- The consolidation role (board-chief / code-chief / board-ux-heuristic primus) is its own persona, not a "coordinator layer".

**What to do instead:** keep the orchestration depth at most 1 (slash command → personas). The merge happens in the main agent.

---

## Decision flow

When considering a new orchestrated workflow, walk this flow:

```
Is the work one perspective on one artifact?
├── Yes → Direct invocation. Stop.
└── No  → Will the same composition repeat?
         ├── No  → Direct invocation, ad hoc. Stop.
         └── Yes → Are sub-tasks independent?
                  ├── No  → Sequential lifecycle (user-driven workflow). Pattern 4.
                  └── Yes → Parallel fan-out with merge (pattern 3).
                           Validate against the checklist above.
                           If any check fails → fall back to single-persona skill (pattern 2).
```

---

## When to add a new pattern to this catalog

Add a new entry only after:

1. You've used the pattern at least twice in real work
2. You can name a concrete artifact in this repo that demonstrates it
3. You can explain why an existing pattern wouldn't have worked
4. You can describe its anti-pattern shadow (what people will mistakenly build instead)

Premature catalog entries become aspirational documentation that no one follows.

## See Also

- `framework/agentic-design-principles.md` — DRs (design rules) for agent architecture.
- `skills/spec_board/SKILL.md` — pattern 3 example.
- `skills/code_review_board/SKILL.md` — pattern 3 example.
- `skills/council/SKILL.md` — pattern 3 example (architecture council).
- `workflows/runbooks/build/WORKFLOW.md` — pattern 4 example.
- `skills/_protocols/consolidation-preservation.md` — merge discipline.
- `references/accessibility-checklist.md` + `performance-checklist.md` — other references.
