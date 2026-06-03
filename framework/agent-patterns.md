# Agent patterns forge hardens against

The typical ways a coding agent — or the orchestrator driving it — goes
wrong, and how forge is wired to catch each. These are tendencies
observed dogfooding forge on real work, generalized: the *tendency*
first, then *forge:* the control. The controls live in skills, personas,
and runbooks — this page is the map, not the mechanism. They are
tendencies, not certainties; a capable agent avoids many of them most of
the time. forge's bet is structural — turn each "the user caught it at
the gate" into a control that catches it by default — and where a control
is convention rather than a mechanical gate, it says so.

## Framing & anchoring

- **Inherited framing** — an agent adopts the framing it's handed and
  amplifies it, so a wrong premise propagates instead of getting caught.
  *forge:* reviewers start cold, with no shared brief colouring their
  findings.
- **Plausible-but-wrong premise** — the frame sounds right, so nobody
  challenges it. *forge:* an adversary whose whole job is to attack the
  premise, run first so its challenge isn't diluted by within-frame
  agreement.
- **Smart-but-wrong** — every check is green and the result is still
  wrong. *forge:* the adversary simulates how the spec could be satisfied
  to the letter and still miss the intent.
- **Dispatcher bias** — the orchestrator's own hypothesis leaks into the
  brief and steers every reviewer. *forge:* a dispatch carries only scope
  and the artifact, never the orchestrator's analysis.
- **Warm re-review** — a second look inherits the first look's frame and
  re-confirms it. *forge:* re-review derives cold from the diff first,
  then reconciles against prior findings — it never starts from them.
- **Depth mistaken for cleanliness** — more reviewers feel like more
  rigor, but if they share one frame they share one blind spot. *forge:*
  context cleanliness over apparatus depth — one cold outside read can
  beat a large warm board.

## Belief over reality

- **Belief over disk** — the agent trusts its memory of the code over
  what's actually there. *forge:* mechanical claims are checked against
  the live tree before they're stated.
- **Unverified "already exists"** — "reuses X / supersedes Y / already
  handled" is asserted and built on without a check. *forge:* such claims
  carry a grep result (confirmed or falsified) before work proceeds.
- **Spec prose over code** — a brief's code claims are sourced from the
  spec, in the very task where the code has drifted from that spec.
  *forge:* the brief author is context-isolated and read-only, so it has
  to read the code to write anything.
- **Decision treated as fact** — a premise from a prior decision or
  council is built on without checking what the code actually produces.
  *forge:* collision / reconcile claims are verified against real emitted
  output, not the stated policy.
- **Cited but unverified** — a spec citation is copied forward across
  revisions without re-opening the line. *forge:* the author cites with a
  grep; an independent pass re-verifies the citation.
- **Live state as decoration** — deploy evidence that contradicts a claim
  (zero rows vs "the write path works") is read as context, not
  authority. *forge:* a live observation that contradicts a claim is a
  finding, not a footnote.
- **Prose over engine truth** — trusting a spec's prose about how
  something behaves instead of the code that implements it. *forge:* a
  mechanical claim must point at the consuming engine, not the prose that
  asserts it.

## False confidence & honest enforcement

- **Hand-waving** — findings asserted without evidence. *forge:* every
  finding cites a file and line, with a verbatim quote.
- **Format as verification** — "well-formatted, therefore correct."
  *forge:* review weighs substance over presentation; a claim with no
  code quote is rejected.
- **Single-layer "done"** — "closed" claimed from the helper layer while
  the boundary and consumer sides go untraced. *forge:* a closure claim
  traces producer → boundary → consumer, with a test that fails if the
  boundary drops the signal.
- **Proving a negative** — "I grepped the name, zero hits, all clean" over
  an open form-space where the thing survives as a label, a spaced form, a
  paraphrase. *forge:* prove completeness by flipping to a pinned
  inventory of what exists and walking claims against it — with a verifier
  lens different from the one that did the removal.
- **Phantom enforcement** — docs claim a check "blocks" when no runnable
  artifact exists. *forge:* enforcement is registered with honest class
  tags; a doc may not bind a live-enforcement verb to a mechanism that
  isn't there.
- **Test-green ≠ wired** — components ship unit-green but never wired into
  the running system, and skipped or stubbed tests count as "green."
  *forge:* an integration claim needs a green, non-skipped wire-proving
  test; a new consumer with no instantiation outside tests is the
  tripwire.

## System-level blindness

- **Local optimisation** — fixes the local spot and misses the system
  break (a producer wired up with no consumer on the other end). *forge:*
  a coherence check at the milestone / architecture layer, not just
  per-file.
- **Cross-boundary acceptance** — an outcome ("user types → it appears")
  needs two subsystems live, but they're owned by different tasks.
  *forge:* a cross-subsystem acceptance criterion is split to its owning
  tasks, never marked closeable in one.
- **Delegating understanding** — the orchestrator reads an artifact's text
  (an acceptance criterion, a return summary) as if it were comprehension,
  and propagates a framing nothing supports. *forge:* milestone-level
  coherence is reconstructed from the topology before a cross-component
  framing is authored.

## Structural & architectural shortcuts

- **Smell-transfer** — a refactor moves the root problem into a new
  vehicle (a new type, enum, model) instead of fixing it. *forge:* a
  structural-purity pass replays the original failure condition against
  the new code.
- **Cycle-symptom-as-cause** — `Any` / `dict` typing to dodge an import
  cycle, when the cycle is the symptom of wrong module placement. *forge:*
  the architecture lens flags the workaround and names the real seam.
- **State-vocabulary half-coverage** — an uninitialized state crammed into
  a working one ("degraded", "ready") because the vocabulary is too thin
  to name every lifecycle phase. *forge:* completeness of the state
  vocabulary is its own review check.
- **Shallow module / leaky seam** — a pass-through layer that pushes
  complexity onto its callers; a seam justified by a single hypothetical
  adapter. *forge:* a deep-modules lens at plan time — one adapter is
  hypothetical, two is a real seam.
- **Boiling-frog growth** — reviewers see 50-line diffs, not the
  2000-line file they sum to. *forge:* cumulative file totals are
  surfaced, not just the diff.

## Proportionality & scope drift

- **Trigger counts surface, not risk** — a heavy board fires for a trivial
  fix because test files and bookkeeping inflate the count. *forge:* a
  proportionality gate weighs stakes over counts; hard floors (security,
  schema, public API) stay regardless.
- **Scope-ratchet** — a fix-pass treats every minor finding as blocking,
  and its own new findings inflate the next pass. *forge:* per-finding
  triage with *accept* as the default for anything non-blocking.
- **Follow-up without a floor** — "add tests for future-edit safety" filed
  as work with no named cost or consumer. *forge:* a follow-up needs a
  named operational cost and a named consumer, or it's dropped.
- **Severity-laundering** — mixed-severity findings bundled under one low
  tag to slip the floor. *forge:* a bundle inherits its maximum severity
  and is unbundled at disposition.
- **Hardening an accepted finding** — re-opening a contained issue "for
  symmetry" and manufacturing a new defect. *forge:* an accepted finding
  gets no new mechanism without a stated new failure mode.
- **The brief outweighs the fix** — more time spent writing the delegation
  than the change would take. *forge:* delegation is a proportionality
  judgment, not an absolute trigger — trivial work stays inline.

## Bypass, over-escalation & mechanism misuse

- **Bypass by relabelling** — substantial work framed as "spec-only" or
  "trivial" to skip the process. *forge:* the trigger keys on the
  substance class, not the label.
- **Over-escalation** — convening a council for a contradiction the
  current scope can already decide. *forge:* a scope-check precedes
  escalation; cross-scope is not the same as undecidable-here.
- **Reinventing a primitive** — adding a new field / flag / step without
  checking whether the mechanism already exists. *forge:* a short survey
  of existing primitives is required before new mechanism.
- **Instance, not class** — handling the one triggering case and leaving
  its siblings inconsistent. *forge:* when a change creates a type, all
  instances in scope are found.

## Silent loss in consolidation & handoff

- **Consolidation compression** — "consolidate" becomes "compress," and
  single-source findings quietly vanish. *forge:* every finding ends as
  kept / merged / related / removed, tracked by a counting equation.
- **Over-merge** — two findings with similar symptoms but different roots
  collapsed into one. *forge:* merge only on identical root cause;
  otherwise cross-reference.
- **Defensive-content deletion** — "dead code" removed that was actually a
  guard or fallback. *forge:* before removal, standalone and defensive
  purpose is checked, and the check is recorded.

## Mechanical mode

- **Classify without understanding** — jumping straight to bucketing
  findings without reconstructing intent or simulating effect. *forge:* a
  proof of intent + effect + model precedes any classification, and a
  finding must reference it.
- **Theatre compliance** — the gate section is present but empty ("Intent:
  the goal is clarity"). *forge:* bind rules — a required section that
  nothing references is filler, and rejected.

## Brief quality & implementation drift

- **Decision pushed to the implementer** — a sketchy brief leaves
  architecture calls to whoever writes the code. *forge:* implicit
  decisions (schema, error / stop, layering, invariants) are enumerated
  and locked in the brief.
- **Loose phrasing expands scope** — "clean up all references" turns a
  one-file fix into twenty. *forge:* recommendations are narrow-quoted and
  scope-bound (file list, line cap, stop condition).
- **Terse prompt, shallow work** — a command-style prompt produces generic
  output. *forge:* delegate like briefing a colleague who just walked in —
  the goal, the context, the exact change.

## Context loss across sessions

- **Cold restart** — an ephemeral session loses its exact place, and the
  next one re-derives it from the transcript. *forge:* a structured
  handoff plus per-step engine state, read on boot, so a paused multi-day
  build resumes where it stopped.
