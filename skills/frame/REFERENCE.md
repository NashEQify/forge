# frame — REFERENCE

Detail mechanics, examples, edge cases. Reference for special cases.
The Buddy-facing SKILL.md (`SKILL.md` in this directory) is the checklist.

## First-Principles drill (Step 2) — detail

Runs AFTER reformulation (Step 1), BEFORE the plan (Step 3). This way the
axioms are fixed before solution paths are planned — no anchoring bias from the plan.

Decompose the reformulated problem: "What is X really? Why this and
not Y? Which assumption sits behind it?" Drill until a fundamental point is
reached — do not stop at the first plausible explanation.

**Full drill (bedrock_drill):** MUST in solve context or
deep mode. Output: bedrock map as its own section in the frame report. Flows
as constraint input into all subsequent steps.

## Plan + Review (Step 3) — detail

Templates, trigger definition, adversary prompt: `_protocols/plan-review.md` (SoT).
Step 3 calls the protocol; frame-specific is only the
integration point (frame-report body after Step 2 First-Principles) and the
bind-rule anchor (subsequent steps reference the plan).
With drill output present: the plan MUST reference the bedrock map.

**Minimum in quick mode (mechanically checkable):**
- At least one explicit assumption naming ("The problem presupposes that X")
- At least one counter-question to that assumption ("Does X hold under all conditions?")

Without these two elements: First-Principles not satisfied, the gate does not turn green.

**Standard depth:** 2-3 assumptions + counter-questions. For at least one
counter-question the answer should be non-trivial.

**Deep depth:** multiple assumption layers. Assumptions about assumptions. "What
does that presuppose, which presupposes that X holds?" Down to the actual first principle.

## SOTA trigger — detail

Trigger (at least one for research):
- Buddy is unsure about the domain (self-assessment)
- Solution space looks too thin (<3 serious approaches generatable)
- Domain evolves quickly (best practices may have changed)
- User explicitly asks ("look at what others do")
- Stakes justify the effort (large / hard to reverse)

**Action on trigger:** invoke the research workflow as a sub-workflow
(`workflows/runbooks/research/WORKFLOW.md`), or Buddy calls
WebSearch/WebFetch directly for quick checks.

**Skip rule:** if the repo check (Step 4) already provides enough signal ->
documented skip with one-sentence justification in the frame report. Example:
"SOTA skip: repo check already covers pattern X (see `docs/research/<date>-<topic>.md`)."
No silent skip — the justification is mandatory.

## Orthogonality check — examples

For each approach: name the **distinguishing axis** — which core assumption
does this approach make that the others do NOT?

### Example 1: variations, not fundamental approaches

- Approach A (script in Python): assumption "language doesn't matter, Python is just preference"
- Approach B (script in Bash): assumption "language doesn't matter, Bash is just preference"
- Approach C (script in Node): assumption "language doesn't matter, Node is just preference"
- -> No distinguishing axis. All three make the same core assumption
  ("the problem is solved imperatively by a script"). These are variations,
  not fundamentally different approaches. Back to the brainstorm.

### Example 2: real orthogonality

- Approach A (code generator): assumption "logic is static, generatable at build time"
- Approach B (runtime interpreter): assumption "logic is dynamic, decidable at run time"
- Approach C (table-driven): assumption "logic is data-driven, configurable via tables"
- -> Each approach makes a different core assumption about the nature of the logic
  (static vs. dynamic vs. data-driven). Fundamentally different.

### Rule

Without a nameable distinguishing axis for each pair: the approaches are
variations, not fundamental alternatives. Back to the brainstorm.

## Null option — detail

"Do nothing / accept the current state" is a fully fledged approach.
MUST always be checked explicitly (even if not chosen as the recommendation).

**Format like any other approach:**
- Core idea: "leave the status quo, accept the problem explicitly"
- Happy path: when does doing nothing work? (e.g. the problem is self-
  resolving, cost of acting > cost of not acting)
- Edge case: when does doing nothing break? (e.g. the problem escalates, costs rise)
- Effort: 0
- Reversibility: trivial (no action = nothing to revert)

The null option is not an "escape candidate" — it is a valid approach that is
often the best choice under high uncertainty or low impact.

## Edge cases

**The problem is actually a bug with a reproduction path:**
-> abort frame, inform user, redispatch to fix workflow. Do not force it through
  all 8 sub-steps.

**The problem is actually a knowledge question:**
-> redispatch to research workflow. Frame is not the right mechanism.

**The problem is too large for one frame report:**
-> decompose into sub-problems, one frame block per sub-problem in the same
  state file. See solve/WORKFLOW.md §body structure "exception on problem decomposition".

**User feedback after the frame report:**
-> does NOT count as a new frame pass. That is Phase 2 Refine of the solve
  workflow. Frame stays at "1 pass".

**Step 2/3 overturns the Step-1 reformulation (drill or plan shows wrong reformulation):**
-> internal iteration, not a new frame. Revise Step 1, inform the user,
  document tracking in the frame report ("Step 1 revised on the basis
  of repo-check findings").
