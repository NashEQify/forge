# Buddy — Delegation

Step-loaded unit of `agents/buddy/operational.md` (Phase 2: ACT). Read it when
the selected step leaves its executor undecided, before dispatching another
actor or commissioning a further round, and when the host cannot invoke a
required skill. The core's Applicability holds for software. On demand, follow
the project's working rules.

Routing lookup:

| Topic | Agent |
|-------|-------|
| Code / implementation | main-code-agent |
| Architecture / framework choice | solution-expert |
| Security | security |
| Sysadmin, orchestrator work | Buddy direct |

Permission depth per artifact: `framework/agent-autonomy.md` (SoT).
Pre-Delegation: framework/invariants.md §3 (gate file BEFORE the agent
call).

**Delegation hygiene:**

For each substantial delegation, bound the existing brief by the unresolved
question or consumer decision it serves, the independent perspective needed,
reasoning-effort rationale, relevant context, required
return shape and stopping/escalation condition. Another call needs an
incremental purpose that can change the next decision. Every agent call names
its model, taken from its role's row in `framework/models.md` (read it before
the call), which also says where the call names it and how a higher tier
records its reason. Select effort for uncertainty and consequence, including
the likely completion path; lowest call cost is not the objective.

Ground the purpose in the authorized outcome and actual evidence gap. State what
plausible different results would change the next action or acceptance, why
current evidence cannot answer it, and which concrete relevant failure would
become less protected if the call were omitted. A role label, generic confidence
gain or a process requirement alone is not that grounding; required review
floors retain their underlying risk/independence purpose. If no such distinction
or assurance need can be grounded, reuse current evidence or omit the extra
call. This belongs in the existing brief; no extra form or gate.
When the delegate writes review or decision artifacts that a checker parses,
the brief points to their format contract
(`skills/_protocols/evidence-pointer-schema.md`) instead of restating it.

**Cumulative effort.** When a task, repair or extension starts, its owner
states in the existing brief or first decision record the expected effort for
the task's value (rounds, calls and test runs) and what would justify more.
Test runs count as rounds (`skills/testing/run-strategy.md` §Test selection). Before
commissioning any further round — a fix pass, an added or
repeated review, a new review owner or sub-fix for the same task, an extension
or re-prepare, a test run beyond the selected sets and a due broad run —
compare the task's actual cumulative effort across all owners, and the
remaining risk, with that statement. Within it, proceed. Beyond it, record one
choice in that decision before commissioning: **close** with the remaining
risk recorded as a known limit (the default when the risk is pre-existing,
latent or has a known fallback), **narrow** (remove scope or machinery so the
next round is smaller than the last), or **escalate** to the user, through the
commissioning coordinator, with cumulative cost and remaining risk. A new
owner, workflow, iteration counter or defect name does not reset the
cumulative effort. The coordinating Buddy applies the same check before
recommending or approving an extension or a new review owner; acceptance
completeness alone does not justify one. Both name the state carrier the next
round touches: work on a carrier that already drew unresolved blocking
findings, in this task or an earlier one, continues that mechanism's count and Simplify-before-patch gate
(`skills/convergence_loop/simplify-before-patch.md`), whatever it is now called. Required
review floors, change-introduced regressions, blocking defects in retained
required behavior and blocking defects in behavior this change introduces to
meet an acceptance criterion are never closed as limits; narrow or escalate them.

Preserve required independent investigation and review floors. Apply
`skills/_protocols/dispatch-template.md` before dispatch and
`skills/_protocols/piebald-budget.md` when assembling its context.

Reuse current evidence and the applicable scoped correction/re-review rules.
Widen verification when changed shared assumptions, affected consumers or new
failures justify it; stop when the commissioned outcome and required
verification are satisfied.

When evaluating cost, use the existing work/evaluation log. Separate available
preparation, coordinator, reviewer, implementation and retry costs; mark
unavailable values unknown. Distinguish cached input from total input and
reasoning already included in output. Preserve setup failures and all attempts.
Line counts and one aggregate sample do not establish savings.

**Vehicle choice.** Each piece of work gets one vehicle:
- **Inline** — the default: Buddy holds the context, the result is needed
  for this turn, and no independent perspective is required. Never for
  product code, whatever its size, except the quick path (Inv 4).
- **Isolated agent** — a bounded question, a code piece (main-code-agent,
  Inv 4) or an independent perspective a review floor requires, whose result
  Buddy needs before its next decision.
- **Persistent session**, where the host offers one — when the user asked
  for it or a standing agreement says so, or for a task of its own (it
  outlives the turn and ends in its own result) whose length would otherwise
  fill the coordinating context. It has the highest fixed cost: full boot and
  context re-derived from the brief.
Multi-agent work pays on parallelizable, high-value work and costs on
sequential work; a spawn needs an isolation or independence gain. Host
vehicles and fallbacks: `architecture-documentation/07-tool-integrations.md`
§Delegation vehicles. Sessions and concurrent writers:
`agents/buddy/coordinating-sessions.md`. The MCA questions below are the code case of this choice.

Before every MCA delegation, ask two questions in order:

*"which delegation form is proportional?"* (per framework/invariants.md Inv 9). Inv 4
holds at any size outside its quick-path exception, so the question is
how the work reaches main-code-agent: DIRECT-eligible work goes with the
record written in the turn (`framework/direct-eligibility.md` §The DIRECT
run), other work with a brief file. Judgment across five axes, not a numeric
threshold:
- **context-locality** — Buddy already holds the context live
  (diagnose + implement same thread); transferring it as a brief
  costs more than it conveys. **Bound (ADR-005):** this axis does
  NOT license inline brief-authoring for a brief that touches
  EXISTING code. Spec-derived held context ≠ as-is grounding (the
  spec is the least-trustworthy source for a brief's code claims).
  Any code-touching brief outside `framework/process-map.md` DIRECT
  eligibility → dispatch `brief-architect` (fresh context,
  greps `src/`), with a dispatch package of spec authority + ACs +
  scope + intent_chain + optional lens_output ONLY — never a
  Buddy-authored draft/spec-summary. DIRECT may include clear local new
  behavior after reading the actual code; existing spec context alone is
  insufficient grounding. Resolve missing facts before classifying; unresolved
  consequential decisions remain outside DIRECT.
- **failure-mode-class** — failure is visible pass/fail and
  locally-bounded (not race, not security, not invisible-until-prod).
- **specialization-need** — work that needs MCA's planned toolchain
  (long test runs, large-refactor coordination, adversary review)
  needs a brief file; the record in the turn carries the rest.
- **cognitive-load** — the record in the turn stays in Buddy's
  orchestrator role; a change whose description would take Buddy into
  design or long coding detail needs a brief file.
- **safety-floor** — no security / auth / schema / public-API /
  secrets / data migration / live infrastructure / full-path touch
  (Inv 9: safety floors precede any shortcut and rule out the light
  review; which floors need L2 is named in
  `skills/code_review_board/SKILL.md` §1.1, the rest run L1 + lens).

Intent of the judgment: cut the cost when context-transfer would
cost more than it conveys; preserve MCA's specialization where it
genuinely adds value. Self-check: if writing a brief file would take
longer than writing the code would, the record in the turn is the
vehicle — but that is one signal, not the rule.

*"design decision or mechanical writing?"* (when delegating):
- Design → Buddy decides, MCA gets a precise spec (content + location
  + AC).
- Mechanical → MCA gets spec + AC + scope, no design freedom.

"Use your judgment" in a prompt delegates design away — that's a
violation when user-intent-critical.

**Writing an MCA dispatch with a brief** (every dispatch except DIRECT work
that closes in its turn, which follows `framework/direct-eligibility.md`
§The DIRECT run): read and follow `skills/_protocols/mca-dispatch.md` (brief
and report files in the work unit's records, the five-part dispatch, the
short return and its persistence).

**Skill-invocation fallback (no CC wrapper / stale mirror):** when a
canonical or utility skill is the required path but is NOT invocable
via the `Skill` tool (absent from the available-skills reminder — no
wrapper yet generated, or the consumer session runs against a mirror
the wrapper hasn't been release-synced to), Buddy MUST read the
neutral SoT `skills/<name>/SKILL.md` and execute its methodology
directly. Do NOT substitute a different skill because it happens to be
discoverable (e.g. never reach for `task_creation` because
`task_status_update` is the required path but unwrapped). Wrappers are
a generated artifact (`generate_skill_wrappers.py`), so this is rare —
but it stays the behavioural net for new or not-yet-propagated skills.
The substitution error is the failure mode; the SoT is always the
ground truth.
