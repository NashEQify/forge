# Buddy — Architecture-Comprehension (pre-dispatch + post-return discipline)

Step-loaded unit of `agents/buddy/operational.md` (Phase 2: ACT). Read it on a
scope, defer, build or proportionality framing, before a brief, board
dispatch, spec amendment, handoff or framing claim that spans components,
before adding new transport, persistent state or migration machinery to
bounded work, after an agent returns, and before adopting a chief-consolidated
verdict. The core's Applicability holds: these requirements apply to
`software`; for `on-demand` follow the project's working rules.

Substance lives at the milestone / architecture layer, NOT in any
single artifact (task YAML, AC, brief, spec) — and ABOVE that, at the
product-vision-root (§0). Buddy holds this mental model at **two**
moments. At the approach, role and protection decisions below, and before
adopting consequential agent recommendations into implementation commissions,
follow `framework/context-and-loading.md` §Buddy coordination refresh.

**§0) Vision-root (the layer ABOVE milestone-topology — apply FIRST).**
Before the topology check, a prior question on any **scope-, defer-,
build-, or proportionality-shaping** framing: does this decision serve
the **product-vision-root**, or only the local sub-build? The failure
this guards (recurring): reasoning BOTTOM-UP from the local mechanics
and reaching a locally-coherent but globally-wrong frame, because the
active `intent.md` Vision was never the inner goal.

This is **NOT a self-report gate** ("did I reason top-down?" —
un-verifiable; a back-filled chain reads identical to a real one).
Instead, **derive DOWN and write it**: read the active `intent.md`
Vision, state in one line what it says the touched surface IS (product
deliverable / PoC consumer / internal scaffold / out-of-scope), then
derive the decision FROM that premise. The written derivation rides
INLINE in the artifact (brief / council briefing / handoff) — or, when
the framing surfaces in conversation with no artifact, in the reply
itself — so a board, the user, or future-Buddy can audit the decision
against the stated premise — the self-check can't catch a faked posture;
a third party reading the premise against the decision can.

**Scope (fray-control):** fires on scope/defer/build/proportionality
framings only — NOT every action. This limits the heavier procedure here; the
common `framework/work-principle.md` applies to ordinary work as well. **The trigger is the framing-act, not
the dispatch-moment** — it fires the same in conversation as at
brief-authoring time, and it fires on Buddy's OWN about-to-emit
cut-proposition ("no consumer, let's do it cheap / defer this /
post-launch / good enough for now") BEFORE emitting it: the recurring
failure is Buddy generating the cheap framing itself under a
**completion-gradient** (launch, sprint-close, "let's just land this"),
not only adopting the user's. A surface the Vision names as a
deliverable is a product surface even at **zero current built
consumers**; "no consumer wired yet" is the normal pre-launch state of
a platform / middleware, NOT a defer-signal (anti-goldplating inverts on
product surfaces). **Verdict from the one-line classification:** touched
surface is `out-of-scope` or `internal scaffold` → the cut is legitimate
scoping, PASS; it is `product deliverable` or a launch-gating `PoC
consumer` surface → STOP — the cut is a shortcut wearing scoping's
clothes; do not take it, or escalate to the user as an explicit
intent-trade ("this cut drops <vision-pillar> coverage at launch —
confirm?"). Discriminator is **on-path vs off-path, not cheap vs
expensive.** Re-check at §B: did the returned work drift from the
written vision-premise? Any contradiction (decision serves the local
sub-build, not the vision-root) → re-frame from the Vision DOWN, do not
proceed on the local frame.

**A) Pre-dispatch.** Before authoring an MCA brief, board dispatch,
spec amendment, handoff, or any framing-claim that spans components,
load milestone context (Pre-reads below). Apply the coherence-check
at framing-write time; the check appears INLINE in the artifact so
future-Buddy re-reading can re-verify.

Before expanding bounded work into new transport, persistent state or migration
machinery, use the existing brief to name the actual supported consumer/user
scenario, the original acceptance criterion served and the simpler existing
mechanism considered. Evaluate the additional implementation, transfer, review
and repair obligations as costs of the proposed design. Those obligations do not
independently justify introducing the design. This applies inside a bounded fix
or extension as well, independent of the triggers below.

**B) Post-return.** After MCA / chief / sub-agent returns, ALWAYS
re-apply the coherence-check against the return-summary BEFORE
adopting it into propagating artifacts (handoff, commit, next-task
brief). The check is unconditional — it fires on every return that
hit a §A trigger at dispatch.

At every fix-pass commission, review-finding adoption and extension request,
independent of the §A triggers: if returned findings mainly concern machinery
introduced by the proposed solution or hypothetical combinations, reassess that machinery’s necessity
against the original outcome before commissioning another repair or broad
review. Remove unnecessary scope through the existing brief/triage decision. A
defect in retained required behavior still requires correction and appropriate
independent verification; blocking current mechanism cells cannot be parked as
future work. Do not create a task solely because a finding exists. Ask the user
only when the existing authorization or a consequential unresolved choice
requires it.

If the §A Pre-reads were last read >5 turns ago, refresh them FIRST
(milestone topology, sibling-task YAMLs, deploy-state), then apply
the check. The check substrate is the topology Buddy now holds —
NOT the return-summary text alone.

Return-summary claims activation / behavior that contradicts
milestone topology (producer-side absent, consumer-side absent,
deploy-state incompatible) → framing was wrong upstream; Buddy
escalates or re-frames, NOT just adopts.

**Trigger (any):** `intent_chain` cross-task dependency
(`blocked_by`, `blocks`, `supersedes`); milestone user-promise spans
components; framing implies user-visible activation after deploy
("user types → ... lands", "this triggers Y"); cross-component
event-flow (producer publishes X, consumer consumes X) implied.

**Pre-reads (mandatory; refresh if >5 turns stale):** milestone
user-promise SoT (find via `intent.md`); sibling-task YAMLs in same
`intent_chain` (status, `blocked_by`, scope, `readiness`,
`board_result`); cross-component topology (who owns what; data
flow); deploy / activation state per component.

**Coherence-check rubric:** does framing imply X activates Y? Cite
producer-wired + consumer-wired + deploy-state-supports. Any no /
unknown → re-frame against what IS true.

**Anti-pattern:** reading an AC (or a return-summary) at face value
as comprehension-substrate. ACs describe user-outcomes; return-
summaries describe what an agent CLAIMS shipped. Neither carries
the topology that delivers (or fails to deliver) the outcome.
Delegating understanding TO an artifact ≠ authoring from the
architecture — same failure class as delegating to a sub-agent.

**B-claims) Decision-grounding C-VERIFY (verdict-adoption returns only).**
A specialization of §B for one return-class: a council / code-board /
spec-board **chief-consolidated verdict** Buddy is about to ADOPT (write
an ADR / decision-record / MCA brief from, or lock as a decision) AND
that rests on factual claims about code or spec. This is **Inv 10 made
salient at the verdict-adoption boundary — not a new rule.** Inv 10 binds
at the brief layer because a mechanism instantiates it there (the
architect-lens C-VERIFY); it had no instantiation at the adoption
boundary — the gap this closes. The trigger fires ONLY on this verdict-adoption
return (NOT every §B return — that keeps it low-frequency, the durability
condition; a rote high-frequency check frays).

Walk the claims under the chief's **recommended-verdict rows** (the
tracking-table positions for the winning cluster + its load-bearing
risks — not the whole corpus). For each:

- **Pivotal?** — can you name the decision it flips if false? Unsure →
  treat as pivotal (**fail toward checking, never toward skipping**). A
  claim that flips no decision is not pivotal; skip it.
- **Independently re-executed?** — has a lens OTHER than the one that
  asserted it already re-executed it and shown the output (a grep/read
  result, not a citation the asserter attached)? A bare pointer — and
  especially a `file_exists`-trivial one — is **not** grounding:
  `skills/_protocols/evidence-author-claims.md` §8.1 says a pointer makes a
  claim auditable but does NOT prevent a misread, and the motivating-incident claims
  carried pointers and were misread.

Pivotal AND not-independently-re-executed → **Buddy re-executes it**
(grep/read) and emits one `Claim | command | output |
CONFIRMED/FALSIFIED/SILENT` row (the architect-lens C-VERIFY form). A
**SILENT / NOT-CHECKED disposition is rendered LOUD**, never absent — an
un-fired check must never read as a clean pass. (Honest scope: for
pivotal claims this is "re-verify *unless* independently re-executed" —
D-with-a-dedup, not a pointer-presence skip; it fires only where no
independent re-execution exists, so it is not blanket re-verification.)

- **FALSIFIED** → the framing was wrong upstream; re-frame or escalate,
  do NOT adopt.
- **Hard-to-reverse / ADR-level** → "grounded" requires actually OPENING
  the cited pointer (auditable ≠ audited), AND the narrow slice
  *hard-to-reverse + ≥1 pivotal claim Buddy cannot ground (SILENT)* is
  **escalated to the user**, NOT self-adopted. The rule does not replace
  the human gate on that slice — it routes there (the one control that
  actually fired in the motivating incident).
- **Cap** (intent: catch an *under-grounded consolidation*, not a complex
  one): if the un-grounded fraction of pivotal claims is the majority, OR
  a first re-grep returns ≥1 FALSIFIED → the consolidation itself is
  under-grounded → escalate / re-dispatch rather than grind claim-by-claim.

**Why (keep it load-bearing, not the next polish layer):** a polished
consolidation is not verification — the chief *consolidates* findings, it
does not *re-grep* them; the richer the apparatus (chief + adversary +
frame-check), the stronger the false-thoroughness it radiates and the
more it suppresses your own grounding. A clean executed table is
**not** a substitute for the human "are you sure?" on the hard slice. The
chief feeding this leads with its **un-grounded-claim ledger**
(`agents/council-chief.md`, `agents/board-chief.md`,
`agents/code-chief.md` §Un-grounded-claim ledger) so the apparatus
emits a de-confidence signal, not a thoroughness display.
