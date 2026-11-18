# Buddy — Delegation

On-demand unit (`agents/buddy/navigation.md` §Moments). Read it when
taking up work of more than one task, when the selected step leaves its executor
undecided, before dispatching another actor or commissioning a further round.
The core's Applicability holds for software. On demand, follow
the project's working rules.

Routing lookup:

| Topic | Agent |
|-------|-------|
| Code / implementation | main-code-agent |
| Architecture / framework choice | solution-expert |
| Security | security |
| Sysadmin, orchestrator work | Buddy direct |

Permission depth per artifact: `framework/agent-autonomy.md` (SoT).

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
What must stay exact in a brief travels as a copy or a pointer
(`skills/return_summary/SKILL.md` §Accuracy at handovers).
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

**Vehicle choice.** Choose where each piece runs before its first act.
When the remainder becomes a task with its own result, would fill this
chat, or needs an independent view, choose again before acting on it,
including drafting its repair or state artifact. The lookup's choice
cannot cover that remainder. Once a bounded check establishes a separate
repair, do not read its implementation or run its diagnostics before
choosing and writing any due entry. Discovery to establish whether a
separate repair exists and reading the vehicle rules can precede the choice.
- **Inline** — Buddy holds the context, needs the result this turn and needs
  no independent view. Product code stays with main-code-agent except the
  quick path (Inv 4).
- **Isolated agent** — a bounded question, a code piece (main-code-agent,
  Inv 4) or a required independent view for Buddy's next decision.
- **Persistent session** — a task of its own (it outlives the turn and has
  its own result), work that would fill this chat, or work the user wants
  in a session or wants to see or steer. Buddy starts it within host and
  role limits, without first asking or offering a card. Follow the user's
  direction about where work runs. On a refused or unavailable start, use
  the supported fallback in `agents/buddy/coordinating-sessions.md`
  §Coordinator and report it in one line. Without a session route, work
  inline and with isolated agents within role, authority and review limits.
  A start grants no new authority (`agents/buddy/coordinating-sessions.md`
  §Programme order, `agents/buddy/concurrent-writers.md`,
  `framework/process-map.md` §Authorization).
  A session costs a full boot and rebuilt context. A bounded check for the
  next decision stays inline or with an agent, including for a coordinator.
  Coordinators send out their task work. Send a further brief when a running session holds the context, including
  for a different task. Keep one writer per file set
  (`agents/buddy/concurrent-writers.md`). For replacement see
  `agents/buddy/coordinating-sessions.md` §Buddy-to-Buddy.
**The vehicle entry.** Before a piece's first act Buddy appends its entry to `.forge/decisions.jsonl` in the project
root: before an agent call (one for a batch of one decision), a session start or a further brief, and before
inline work he expects to take more than ten own tool calls, a check included, at the latest before the
eleventh (intent: past ten, inline work fills the chat unseen). Inline work of ten or fewer writes none,
nor a session for its brief's work. Purpose: writing the reason makes the choice.
```
mkdir -p .forge && echo '*' >.forge/.gitignore && printf '{"kind":"vehicle","v":1,"ts":"%s","session":"%s","what":"…","where":"inline|agent|session","rests_on":"…","why":"…","est":N}\n' "$(date -Is)" "${CLAUDE_CODE_SESSION_ID:-$PWD}" >>.forge/decisions.jsonl
```
`rests_on`: `context-held`; `bounded-question`, `code-piece`, `independent-view`; `own-task`, `fills-chat`,
`user-steers`, `running-session`; `host-limit`; `step` (a step or brief names it); `user-word` (`why` quotes the user;
nothing more is asked). `why`: name the fact about this piece or remainder that meets the chosen condition and
check that the next act follows from it. `est`: tool calls for that work if done in this chat.
No `%` or `"` in texts. Readers skip other kinds, unknown fields.
Multi-agent work pays on parallelizable, high-value work and costs on
sequential work; a spawn needs an isolation or independence gain. Host
vehicles and fallbacks: `architecture-documentation/07-tool-integrations.md`
§Delegation vehicles; how a role is called, as an agent type or a general agent reading its role file:
`skills/_protocols/role-dispatch.md`. The MCA questions below are the code case of this choice.

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
  review, except a small fix on a live path that meets
  `skills/code_review_board/live-path.md` §1.0a; which floors need L2 is named
  in its §1.1, the rest run L1 + lens).

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
