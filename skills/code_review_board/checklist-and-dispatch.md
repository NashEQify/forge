# Code review board — checklist and dispatch

Step-loaded unit of `skills/code_review_board/SKILL.md`. Read it when assembling prompts and dispatching reviewers of a board review (a same-turn DIRECT check is not one:
`SKILL.md` §Same-turn DIRECT check),
when running the L2 pre-board frame check, and before a fix pass or re-verify. Section numbers are skill-wide: §1 and §6–§10 in `SKILL.md`, §2–§3 in `brief-and-team.md`, §4–§4a in
`checklist-and-dispatch.md`, §5–§5a in `verdict.md`, §11 in `review-package.md`.

## 4. Buddy checklist

1. Write brief (5 steps).
2. Decide level (§1) and, on L1, the trigger lenses (§3).
3. Check L0 from MCA return (ruff 0, mypy 0).
4. Assemble prompts: `reviewer-base` + `code-reviewer-protocol` +
   `reviewer-reasoning-trace` + `first-principles-check` + persona;
   dispatch with brief + review package (§11) + L0 + spec.
   **L2 brief content (per §4a):** persona-prompt + scope + diff +
   spec links + code paths ONLY. NO prior cycle findings, NO prior
   chief verdict, NO lens framing as autonomous authority, NO
   brief-author rationale.
5. Dispatch.
   - **L1:** core + trigger lenses, parallel, context-isolated,
     cold-start. Buddy works the §3 L1 checklist alongside.
   - **L2 with three or fewer reviewers:** parallel cold-start like L1;
     Buddy consolidates (§1.3).
   - **L2 with four or more:** pre-board frame check + board dispatch per §4a — Buddy
     runs adversary + architect-roots cold-start
     first, persists their returns verbatim as the frame-check
     artifact (`docs/reviews/code/<date>-<task-id|slug>-frame-check.md`,
     slug fallback when no task), distills the substantive findings
     (severity-preserving) into the board brief as scope/context
     content, then dispatches the rest of the sized §3 roster parallel
     cold-start.
6. **L1:** Apply §1.3 to the actual reviewer count (≤ 3: Buddy
   consolidates, no chief). Buddy owns the verdict and verifies pivotal
   source claims; inspect individual findings when needed, without
   routinely redoing the reviews. Write the checklist result into the
   verdict.
7. **L2 with ≥ 4 reviewers** (and L1 with ≥ 4, without the frame-check audit):
   Chief consolidates (F-C-DRILL-MISSING / F-C-TRACE-MISSING
   enforced; chain-of-custody audit per `agents/code-chief.md`
   §CHIEF-1.0 — chief reads frame-check artifact and audits board
   coverage of its substantive concerns; pre-consolidation gates
   §CHIEF-1.1, 1.2; reject every claim without ≥1 verbatim
   `file:line` code-quote) → discourse → Buddy's decision and pivotal-claim
   verification. Chiefs recommend; they do not take over the decision.
8. SAVE.

**Fix-pass dispatch (post-FAIL):** before briefing any fix pass, apply
`agents/buddy/delegation.md` §Delegation hygiene (cumulative effort) and
`agents/buddy/architecture-comprehension.md` §B (machinery reassessment); the fix brief records
the choice. It carries each fix-now finding's verified row (`skills/_protocols/finding-verification.md`
§What follows), and the `§Complexity-Tracking` rows the fix
adds: no public surface and no guard for undemonstrated state without one
(`_protocols/mca-brief-template.md` §Complexity-Tracking). The fix pass and its re-verify run the selected set for the fix's
changes and L0 on touched files; whether a broad run is due, and when,
follows `skills/testing/run-strategy.md` §Test selection.
**Re-verify** — three
cases, decided from the fix diff (the fix-range package, §11):

| Fix diff | Re-verify |
|---|---|
| **Line-local:** touches only the finding's lines AND adds no guard, branch or rule to a mechanism that drew a HIGH | **light:** one `code-verification` re-runs every fix-now reproduction (red→green) |
| **Otherwise** (new guard / branch / rule on a HIGH mechanism, or edits beyond the finding's lines, or oracle hunks present) | **light + mechanism-scoped `code-adversary`:** cold-start with the owning spec's `§Mechanism-Lifecycle` matrix and the fix diff; mandate "attack the **mechanism**, with the whole matrix as context, not the fix"; returns a coverage table over the invariants and the matrix rows / columns the fix touches (cell · probe · result); two-phase per §5a |
| **Mechanism replaced** by the Simplify-before-patch gate | matrix updated first; then `code-adversary` + `code-domain-logic` on the **whole updated matrix** (`code-architect-roots` only if structure changed beyond it), two-phase per §5a |

No chief in any case. Reproductions alone prove only that the reported
routes are closed; a re-verify scoped to the fix diff finds only the
next side of the same mechanism (observed three times in a row on one
build). The adversary's unit is therefore the mechanism: it reads the
whole matrix, probes the invariants and the rows / columns the fix
touches, and reports which it reached, which held and which failed —
that table is the evidence the Simplify-before-patch gate reads. A
missing section follows the retro-model trigger
(`_protocols/mechanism-model.md` §Trigger). Detail: REFERENCE.md.

**Oracle edits on a fix pass (MUST):** a change to a differential
oracle (reference implementation, golden, property) goes in a separate
hunk citing the ruling it implements and is reviewed by the scoped
`code-adversary` of the re-verify (oracle hunks always select that case),
never only by the implementer
(`skills/testing/test-design.md` §Oracle discipline). Ruling-driven fix values
and validators cite the contract-owner spec and are checked against
every spec that produces or consumes the field
(`skills/spec_board/checklist-and-dispatch.md` §4b).

**Simplify-before-patch gate (MUST before fix pass ≥ 2, counted across
the task's spec and code passes on the mechanism):** record the check
per `skills/convergence_loop/simplify-before-patch.md` §Simplify-before-patch gate in
the build log before briefing the fix — `model` row first (the
`§Mechanism-Lifecycle` section present or written now), then same class
/ simpler mechanism / spec at fault answered against the matrix. Same
class + simpler mechanism or spec at fault → propose the simplification
to the caller instead of patching routes, showing the whole updated
matrix. A simplification that removes the class counts as fixing its
HIGHs. A `patch` names every cell it changes (fix brief
`§Mechanism-cells`).

**Disposition-respect + guarantee-carrier rigor on the fix-pass (MUST).**
Two guards, the first unconditional:

1. **Guarantee-carrier rigor (any fix, any disposition — even a mid-fix
   observation with no prior finding).** Before a fix adds a gate /
   claim / lock to a path that carries a delivery guarantee (always-emit,
   at-least-once, exactly-once), it MUST inherit the guarantee's
   failure-model — an explicit failure / redelivery / timeout (e.g. TTL)
   trace showing the added mechanism cannot strand the guaranteed item
   (a claim that out-lives its redelivery budget → silent permanent
   loss). Identify a carrier by consulting the spec's invariant /
   guarantee section (e.g. a §"always-publish" clause), NOT by recall.
   Name the carrier paths + the spec clause in the fix-pass brief prose.
2. **Disposition-respect (the narrower case).** A finding already
   dispositioned `accept` / `watch` (contained, non-blocking) defaults
   to **no new mechanism** on the fix-pass; re-opening it to "harden it
   while we're here" requires a stated NEW failure mode. "Symmetry
   between two paths" / "defense-in-depth" is an aesthetic pull, not a
   correctness argument — the asymmetry is often load-bearing (a
   deterministic path genuinely needs no claim; only the expensive /
   uncertain path does). The respect lasts only while its basis holds
   (`skills/convergence_loop/simplify-before-patch.md` §Record).

Root: Inv 9 proportionality + anti-goldplating (hand-wavy "symmetry" /
"defense-in-depth" re-routes, same family as the Inv-9 "follows
convention" reject). DIFFERENT root from §Claim-Verifications: that
verifies whether a *claim* is true; these guard whether a *change*
should exist at all.

## 4a. L2 dispatch — pre-board frame check + board

The board itself is one cold-start parallel dispatch (no internal
"layers" the reviewers need to know about). Buddy's pre-board work
incorporates an adversarial frame-check so the board brief reflects
substantive scope/parity/spec-citation concerns before reviewers
read it. The frame-check returns are persisted so chief can audit
the chain at consolidation.

**Cold-start brief (board reviewers):** persona + scope + diff +
spec links (locked) + code paths. NO prior cycle findings, NO chief
verdict, NO lens framing as autonomous authority, NO brief-author
rationale. Exception: narrow verify-single-fix gates (NOT board
iterations).

*Lens framing as autonomous authority defined.* Lens-produced
`## Claim-Verifications` rows (mechanical evidence: `file:line` +
grep command + grep output + disposition) ARE allowed in the brief
— the reviewer can independently re-verify each row with one grep.
What's NOT allowed: lens-produced depth/seam/responsibility-purity
JUDGMENTS presented as conclusions the reviewer must accept. The
distinction is mechanical-evidence (allowed) vs persona-judgment
(blocked).

**Pre-board frame check** (Buddy runs before assembling the board
brief, cold-start):
- Adversary — FULL review per `agents/code-adversary.md`
  §Cold-start pre-mission + persona Check focus. One pass. When the
  owning spec has a `§Mechanism-Lifecycle` section, its brief also
  carries that matrix and the mandate of the §4 re-verify table:
  attack the **mechanism**, with the whole matrix as context, not only
  the routes the diff adds; return the coverage table over the
  invariants and the matrix rows / columns the diff touches (cell ·
  probe · result). Same seat, same level.
- Architect-roots (when §1.2 trigger fires) — pattern-purity review
  per `agents/code-architect-roots.md` §Pre-board frame check role.

**Frame-check artifact (chain-of-custody, MANDATORY).** Buddy
persists both returns verbatim to
`docs/reviews/code/<date>-<task-id|slug>-frame-check.md` BEFORE
assembling the board brief. `<slug>` is a Buddy-derived short
identifier when no task-id exists (e.g. ad-hoc review). The
artifact is the raw evidence chain — chief reads it at consolidation
alongside the board reviews per
`agents/code-chief.md` §Chain-of-custody audit.

**Buddy intermezzo (substantive distillation, brief stays clean).**
Read both returns. Distill the substantive concerns into the board
brief as scope clarifications + named open verifications + code-path
emphasis. The brief contains SUBSTANCE, NOT findings-with-severity
or other finding-shaped framing. Severity stays in the frame-check
artifact for chief audit. Adding `[severity:CRITICAL]` or other
finding-shaped framing into brief content would re-create the
brief-contagion the cold-start rule prevents (reviewer reads
against the brief's framing, not against spec → code).

The anti-dilution mechanism is the **chief audit at consolidation**:
chief reads frame-check artifact AND board reviews, cross-references
by substance + severity (per `agents/code-chief.md` §CHIEF-1.0 audit),
surfaces unaddressed artifact concerns at original severity. Reviewers
receive the enriched brief and do normal persona Check focus on it — no
"frame-challenge" framing (special framing invites special handling); they
do NOT read the frame-check artifact (chief-audit surface, not reviewer
input).

**Board dispatch** (parallel, cold-start): the rest of the sized §3
L2 roster, without the frame-check seats: the coverage owner, each
fired trigger's perspective and the candidates the brief's open
questions select.

**Code-quote mandate (all reviewers):** every finding AND every
"verified X" non-finding carries ≥1 verbatim `file:line` quote
(1-3 lines). Chief rejects claim-without-quote and re-dispatches.
