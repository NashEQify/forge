# Mode: process

Guardrails (delta check, write-quality gate, unloading) apply — see SKILL.md.

## Triggers

| Trigger | Who | Scope |
|---------|-----|-------|
| After a structural commit (files moved/renamed/deleted) | All agents | all repos |
| On task status change (open→in-progress, done, etc.) | All agents | all repos |
| Project/system discoveries from agent return | Buddy (consumes return summaries) | active project context |

**User facts are NOT listed here** — they are NOT extracted automatically.
If the user wants facts persisted, they say so explicitly; Buddy then invokes
this skill (mode=user-signal) against the user-context path. No background
mechanism, no prompt gate.

"New factual information": the agent has OBSERVED something (SSH output, server state), CHANGED something (fix, config change), LEARNED something (user mentions a fact, document read), or RECEIVED something (agent result, delegation return).

**Context write = IMPACT CHAIN trigger (mechanical link).** Every write to a context file is evidence that the agent identified a new fact. A context write WITHOUT a subsequent IMPACT CHAIN is incomplete — saving is not processing. At a minimum LOCATE must run: "Are there other places that could be affected by this fact?" If no: document why, move on. If yes: full recursion.

**Timing:** Context writes OUTSIDE a running IMPACT CHAIN trigger a new IMPACT CHAIN. Context writes INSIDE ACT/RECURSE are already part of the running chain — no fresh external trigger.

Known failure mode: the fact feels "small", the agent is busy with something else, the context write feels "done". That is exactly when this gate kicks in.

## Core Logic: Brain Logic (Pre-Brain)

New information is processed against all existing knowledge — not just context files. "Existing knowledge" includes: context areas, task files (design notes, ACs, constraints, schema drafts), decisions (premises, alternatives), backlog (status, dependencies), and where needed agent definitions and skills. For every hit: read the full content, check semantically. Not "does the keyword appear?" but "does the new information change the meaning, validity or assumptions?"

### Step 1: EXTRACT

**Relevance threshold (proportionality — before full EXTRACT):**

Before full extraction starts: "Does this turn contain knowledge-relevant information?"
Knowledge-relevant = changes the system's knowledge about entities, relations, or states.

Not knowledge-relevant (examples): typo fixes, formatting changes, whitespace,
syntax corrections, pure code refactorings without behavioural change, logging changes.

If not knowledge-relevant → no EXTRACT, no IMPACT CHAIN, no SIGNAL CHECK.
Instead a one-line proof:
```
7e: no knowledge-relevant fact — [type: typo/format/syntax/refactor]
```

**CAUTION:** When in doubt, treat it as knowledge-relevant. The threshold is deliberately low.
New dependencies, config changes, schema changes, status changes,
anything that touches entities or relations — always full pipeline.
The skip is ONLY for obviously non-knowledge-relevant changes.

From the raw information, identify ALL discrete facts/claims. Not "the most important" — ALL. For SSH output: every version, every port, every service, every path, every status.

For EVERY extracted fact: **relevance check.** (Proportionality: with very large output the relevance check may filter at a coarser granularity — but never skip.)
- "Does this fact touch anything in my system?"
- Know existing knowledge:
  1. **Context areas**: `context/navigation.md` — which knowledge areas exist?
  2. **Active tasks**: `docs/tasks/*.yaml` — which tasks are open/in-progress?
  3. **Decisions**: `decisions.md` — which architecture decisions rest on which premises?
- Relevant if anything in existing knowledge is touched — whether context area, task, or decision.

Output: list of relevant facts with suspected impact areas. Discard the irrelevant ones (in the brain later: store anyway with low relevance).

**Person extraction (mandatory whenever a natural person is mentioned):**
If the input mentions a natural person (name, role, relationship):
1. Check: is there a person entity in the graph/context with this name?
2. If no: create a person entity with at least `name` + `relation_to_user`.
   If the relationship is unclear: default to 'acquaintance', confidence:medium.
3. If yes: check whether new information is present (organisation, context).

Person entities are the foundation for relational-context analysis
(Analysis Library). Better to capture one person too many than one too few.

**Feedback capture (confirmations AND corrections):**
If the user explicitly confirms an approach, accepts a result, or implements a
recommendation — that is a feedback signal. Capture it as a fact with an impact area.
Do not persist only corrections (incidents, "that was wrong"); also persist
confirmations ("that worked", "good approach", user implements the recommendation).
Rationale: if only corrections are stored, the system drifts away from
validated approaches and becomes overcautious (CC eval finding: anti-drift).

**Explicit-save gate (what is NOT persisted):**
Even if information seems knowledge-relevant — the following categories are NOT
written into context files because they are derivable:
- Code patterns, conventions, architecture, file paths, project structure — visible in the code
- Git history, recent changes, who changed what — `git log`/`git blame` are authoritative
- Debug solutions, fix recipes — the fix is in the code, the commit has the context
- Ephemeral task details: ongoing work, temporary state, current conversation context
- Already documented in CLAUDE.md, intent.md, or agent definitions

Test: "Can an agent derive this information by reading the code, the git history, or
existing documents?" If yes → do not persist.
Exception: non-obvious connections, gotchas, known traps that are not
apparent from the code alone → persist with a source reference.

Applies EVEN on explicit user request. If the user says "save the PR list":
ask back what was surprising or non-obvious about it — THAT is the part
worth saving.

### Step 2: IMPACT CHAIN (recursive tree traversal)

For every relevant fact: start an impact tree. Depth-first: follow each branch to exhaustion before moving to the next sibling branch.

**IMPACT_CHAIN(information):**

**a. LOCATE** — Two questions, both mandatory.

**Question 1 — Impact:** Where does this information matter? (Entity-based)
- DIRECT: Navigation-guided — read the obviously affected area(s) (navigation.md + overview.md + relevant detail files)
- BROAD: Keyword grep across `context/`, `docs/tasks/`, `docs/tasks/*.yaml`, `decisions.md`. As needed also `agents/`, `framework/`, `intent.md`. Search terms: entities from the information.
- **On EVERY hit: read the full file.** A grep hit is a pointer, not a result.

**Question 2 — Convention check:** What governs how I am allowed to perform this action? (Action-class-based)

Fires on structure-altering actions: CREATE_DIR, CREATE_FILE, RENAME, MOVE, DELETE, WRITE (qualified — only if the path pattern matches a known format spec, see fallback table in `docs/STRUCTURE.md`).

**Never searches by entity name** — searches by action class + path context.

3 steps:
1. **Determine the action class** — which of the 6 action classes applies?
2. **Path prefix → load convention sources** — always `docs/STRUCTURE.md`, plus `<parent-dir>/README.md` and `<parent-dir>/navigation.md` if present. For WRITE: only if the path is in the fallback table.
3. **Search the convention sources for action class + path context**

Result:
- Convention found → **apply before execution**
- Not found → **document explicitly**: "No convention found for [action class] under [path]"

No silent continuation. Both outcomes are visible.

**Boundary:** DELETE reference check ("is this file referenced anywhere?") is an impact question (Question 1), not a convention question.

**b. ASSESS** — For EVERY hit: what is the impact?
- **New**: What exactly does the new information say?
- **Existing**: What exactly is at the hit? Read the full content. Design assumptions, constraints, premises, schema drafts.
- **Impact classification — check ALL, don't pick one.** A fact can have several impacts at once:
  - **CONTRADICTS**: Existing statement is now wrong → correct it
  - **EXTENDS**: New info extends the existing → add it
  - **IMPLIES**: Consequences not stated explicitly → derive and check
  - **ENABLES**: Something becomes possible that was previously blocked → flag opportunity
  - **OBSOLETES**: Existing info is no longer relevant → remove/archive
  - **ACTIONABLE**: Concrete future work identified → **task gate** (see ACT). Test: "Would anyone want or need to do this at some point?" Better one task too many than one forgotten intention.

**c. ACT** — For EVERY impact: act on it
- Context files: correct (show diff for existing, create directly for new)
- Tasks/specs: **flag concretely** — comment in the task file under "Comments / progress" with date, what changed, which assumption/AC/constraint is affected. Notify the user. Don't auto-edit (specs/ACs are agreements).
- Decisions: flag if a premise has changed
- Backlog: update status if affected
- Constraints: report violations
- **ACTIONABLE → task gate (mandatory):** the fact MUST land as a task in the backlog — assigned to an existing task or as a new one. "We'll do this later" without a task is an integrity violation.

**d. RECURSE** — Every change from ACT is new information
- For EVERY change: invoke **IMPACT_CHAIN(change)** — full recursion
- Depth-first: follow one branch fully before moving to the next
- **Stop conditions**: no further impact, or the impact is trivial
- **Proportionality** applies to the DEPTH of analysis, not to SKIPPING facts or impact classes. Check every fact against every class — the check may be brief, it may not be missing. Never skip ACTIONABLE.

**Resolve rule:** Observed state (SSH output, live-checked) > documented state (context file). More recent source > older source. On uncertainty: ask the user.

**This pattern is the canonical definition.** The consistency cascade (CLAUDE.md) and consistency-check use the same pattern.

### Step 3: SIGNAL CHECK

If IMPACT CHAIN found a contradiction (CONTRADICTS or OBSOLETES):

1. **Root cause:** Why was the context wrong? Missing trigger, missing check, missing constraint?
2. **Systemic?** One-off or pattern that can recur?
3. **If systemic:** propose an improvement or a backlog entry.

Every contradiction is a signal: "the environment allowed context to become wrong."

### Proof Output (MUST — in line)

Every Brain Logic run MUST emit a compact proof block proving that all three steps were actually executed. A label without content is not proof.

**Format:**
```
EXTRACT: [what concretely was extracted, 1 sentence] — [count] entities
IMPACT: CONTRADICTS [x] / EXTENDS [x] / IMPLIES [x] / ENABLES [x] / OBSOLETES [x] / ACTIONABLE [x]
SIGNAL: [what is signalled / "no signal"] — [action or "none"]
```

**Rules:**
- EXTRACT "none": `EXTRACT: no extractable entities — [reason]`
- IMPACT: All 6 classes MUST be listed. Use `-` for those that don't apply. Do not omit.
- IMPACT all `-`: no context write needed. If one is performed anyway: explain why.
- At least one class must be non-`-` for a context write to be justified.
- SIGNAL "no signal": `SIGNAL: no signal — no action`

**Example:**
```
EXTRACT: Brave apt instead of Snap on T480s, PWA functional — 3 entities
IMPACT: CONTRADICTS t14.md "PWA does not work" / EXTENDS t480s.md / IMPLIES - / ENABLES PWA migration T14 / OBSOLETES - / ACTIONABLE Task 081
SIGNAL: no signal — no action
```

Without this proof block, Brain Logic counts as not executed.

**Commit Gate proof:** Commit Gate is Brain Logic with mode=process. The proof block is identical. Without this block the Commit Gate counts as not executed. No separate format.

## Structural and methodological changes → consistency check

**Structural:** A commit moves/renames/deletes/creates files under `agents/`, `context/` (except `context/history/`), `.claude/agents/`, `orchestrators/`, `skills/`, `workflows/`. → Additionally run consistency-check. History entries are not structural changes.

**Methodological:** Change influences how agents derive meaning, run processes, or make decisions. Test: "Do other files/agents/processes derive behaviour from this?" → impact analysis, semantic check, fix inconsistencies immediately.

Pure content changes without process impact are neither structural nor methodological.
