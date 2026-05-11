# Protocol: Plan + Review

Required mechanism for meta-planning + plan-self-review before
non-trivial actions. SoT for triggers, templates, adversary prompt.
Addresses session-99 / session-100 gaps: meta-planning ad-hoc
without proof output, plan-self-review missing before execution
(smart-but-wrong-in-your-own-plan, instance-vs-class).
Loaded by: `frame/SKILL.md` step 3 (primary), `spec_board/SKILL.md`
§0.

**Status (2026-04-09, Task 348 review):** this protocol is **not
loaded explicitly** but applied by content in the skills that
reference it:

- `frame` step 3 runs the plan block + self-review + (when
  non-trivial) plan-adversary review inline — without loading the
  protocol file.
- `spec_board` §0 does the same inline.

The **mechanics** here (templates, triggers, adversary prompt)
remain the **SoT** for the inline application. The protocol is
therefore not "never used" — it is applied **implicitly**.
Consolidation not required. If a future skill loads the protocol
explicitly, the mechanics are documented here.

## Trigger — non-trivial vs trivial

**Non-trivial (required):** solve / build / fix / review runs
unless trivial, board / council dispatch, spec creation, framework
hardenings, multi-file changes that need a scope enumeration.

**Trivial (skip):** save, commit, task updates, bookkeeping,
status updates without substantive output, pure discussion. Skip
= one-sentence rationale (analogous to the SOTA skip).

## Existing-Primitives-Survey (required before the plan block on a mechanism change)

**Trigger:** the plan block proposes new mechanism — new yaml
field, new CLI flag, new workflow step, new skill, new hook, new
validator, new state field, new protocol section.

**Required step BEFORE the plan block:**

```
### Existing-Primitives-Survey
**Mandatory greps:**
- `grep -rn <feature-keyword> scripts/`
- `grep -rn <feature-keyword> skills/`
- `grep -rn <feature-keyword> orchestrators/claude-code/hooks/`

**Existing primitives found:**
- <path:line> — <one-sentence function>
- <path:line> — <one-sentence function>

**Reuse-vs-new decision:**
- [ ] reuse existing primitive — <which one, why directly applicable>
- [ ] generalize existing primitive — <which one, what needs extending>
- [ ] genuinely new — <why no existing mechanism fits, what the survey
  produced that drives the decision>
```

**Failure mode caught:** the plan-block author sees a symptom
("a step filter is needed"), thinks "new mechanism", reaches for
add-new-field/flag — without grepping the codebase to see if the
mechanism already exists. Class-architecture mistake. Mechanically
prevented when the survey is BLOCKING.

**Anti-pattern:** "I already know what I want to build, skip the
survey." **INSTEAD:** the survey is cheap (3-4 greps); when
negative it confirms the new decision; when positive it prevents
duplication. Skip rationale only for pure wording / docs edits.

## Plan block — template

```
### Plan block
**Scope** (all categories, not just primary):
- <category A>: <affected>
- <category B>: <affected>
**Existing-Primitives-Survey reference:** <link / inline to survey
output, OR "skipped — pure wording edit" with rationale>
**Tool choice:**
- Workflow: <solve / build / fix / review / ...>
- Mode: <Direct / Standard / Full or quick / standard / deep>
- Reviewer setup: <agents / personas; board: pass sequence + team
  size>
- Council / Delta-Verify: <yes / no + rationale>
**Alternatives (min 2, one sentence why not each):**
- Alt 1: <approach> — <why not>
- Alt 2: <approach> — <why not>
**Expected artifacts:** <list>
```

## Plan-self-review block — template

```
### Plan-self-review
- **Scope check:** all categories enumerated? Who/what could be
  missing? <concretely: what was almost forgotten>
- **Instance vs class:** instance or class? If class → name a 2nd
  instance. <concretely: 2nd instance or "pure instance">
- **Rationalization reflex:** which "solid approach" / "standard
  solution" / "first-best" excuse did I almost lean on? <name it>
```

## Plan-adversary-review block — template (for non-trivial)

```
### Plan-Adversary-Review
Dispatch: `plan-adversary` with the plan block + self-review as
input.
Findings (severity BLOCKER/MAJOR/MINOR via the convergence_loop
scale):
- F-PA-NNN: <finding + scenario + severity>
Integration: <what was integrated, what rejected with reason>
```

## Persona discipline (adversary mindset, plan-specific)

### Anti-rationalization — 5 plan-specific reflexes

- "Plan looks complete" — did you walk the 6 criteria concretely
  (incl. existing-primitives reuse)?
- "Tool choice is obvious" — obvious to whom? Which risk wasn't
  modelled?
- "Scope is enumerated" — are **all** categories in there or just
  the primary ones? Where's the class?
- "The self-review already found that" — your job is to find what
  the self-review MISSED.
- "The plan is just like last time" — same structure ≠ same risk.
  Check the instance.

If you're writing a confirmation instead of a counter-argument:
stop.

### Anti-patterns (P3) on plan reviews

- NOT: weakening findings to make the plan pass. INSTEAD: sharpness
  is the value of the review.
- NOT: hypothetical scope gaps without a concrete missing category.
  INSTEAD: name the missing category by name.
- NOT: "small improvement" without severity. INSTEAD: BLOCKER /
  MAJOR / MINOR explicitly.
- NOT: "plan is overall solid" as a conclusion. INSTEAD: what is
  the weakest spot?

### Check focus (plan-specific, complements the 6 criteria)

- **Scope blind spots:** reference updates (step numbers,
  cross-file links), consumer skills, frozen-zone filters,
  task-yaml fields, deploy triggers.
- **Class hunting:** when a change creates a "type" (protocol,
  persona, skill step), look for **all** instances of the type in
  the plan scope.
- **Silent downstream:** which consumers of the changed artifact
  does the plan not know about? Grep result, not assumption.
- **Existing primitives reuse:** the plan builds new mechanism
  (field / flag / step / skill / hook / state field) — does the
  codebase already have a mechanism that does THE SAME? Survey
  output present in the plan block? If not, the mandatory
  `## Existing-Primitives-Survey` step is missing → BLOCKER. If
  the survey is there but the reuse decision is weakly justified,
  MAJOR.
- **Tool under-escalation:** Standard where Deep is needed. Direct
  where Spec is needed. MCA where Buddy directly is in the
  whitelist path.
- **Tool over-engineering:** board for a wording fix; council for
  a reversible decision; Delta-Verify without a normative-line
  trigger.
- **Bootstrap rationalization:** "we're building the mechanism
  right now, so we can't apply it yet" is often a workaround —
  check whether the mechanism is applicable in its current form.
  (Mirrors existing-primitives reuse: there "it exists, plan
  ignores it"; here "it's being built, plan ignores it".)

## Adversary prompt template (dispatch to plan-adversary, optional)

```
You are plan-adversary. Review the plan block + self-review below.
Find at least 3 weaknesses, no confirmations.

Criteria (6, each = potential finding):
1. Scope coverage: which category / reference / consequence was
   missed?
2. Instance vs class: a single case treated as instance when it's a
   class (or vice versa)?
3. Tool fit: does the tool match the risk? Under-escalated or
   over-engineered?
4. Evidence base: which assumption is unsupported? Which point
   needs verification?
5. Rationalization reflex: which excuse bypasses a hard check?
6. Existing-primitives reuse: the plan proposes new mechanism
   (field / flag / step / skill / hook / state field) — does the
   codebase already have one that does the same? Mandatory grep:
   `grep -rn <feature-keyword> scripts/ skills/`. If the plan
   block has no `Existing-Primitives-Survey` output → BLOCKER. If
   the survey is present but the reuse-vs-new decision is weakly
   justified → MAJOR. Bootstrap-rationalization variant: "we're
   building it right now in parallel" while an existing primitive
   is directly applicable.

Finding format: F-PA-NNN + severity + concrete scenario +
suggested_fix. No "overall solid".

Input: <plan block> <self-review block>
```

## Output paths

| Consumer | Where |
|-----------|-------|
| frame in solve | state-file phase 1 body (after step 2 first principles, before step 4 repo check) |
| frame outside solve | frame report / elicitation inline |
| spec_board direct | Buddy checklist §0 / dispatch report / state file |

## Bind rule (plan ↔ execution coupling)

Subsequent phases MUST reference the plan by name OR explicitly
justify the deviation (analogous to the analysis-mode-gate bind
rule). Without the bind = filler → re-dispatch.

## Anti-patterns

- **NOT** plan as post-hoc justification. **INSTEAD** before
  execution.
- **NOT** skipping self-review / adversary on a non-trivial
  because "cheaper". **INSTEAD** dispatch is required; when in
  doubt, run it.
- **NOT** integrating findings pro forma. **INSTEAD** concrete plan
  change or justified rejection.
- **NOT** "I already know what I want to build" → skipping the
  existing-primitives survey. **INSTEAD** 3-4 greps are cheap and
  catch class-architecture mistakes. Empirically: on 2026-05-02
  the adversary found that the `paths:` plan would have duplicated
  the `routes:` mechanic — the survey would have caught it
  pre-adversary.

## Gate rule

Hard gate. Consumer skills reject runs without a visible plan
block + self-review + (non-trivial) adversary review. On a
mechanism change, the existing-primitives survey before the plan
block is also required — a missing survey = plan-adversary
BLOCKER per criterion 6.
