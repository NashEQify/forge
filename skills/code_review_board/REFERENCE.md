# Code Review Board — Reference

Detail mechanics. Buddy loads SKILL.md for dispatch. This file holds
the long-form detail moved out of SKILL.md to keep attention on the
contract (proportionality gate + hard floors + level choice).

## L2 phases (detail)

1. SCOPE + REVIEW BRIEF (Buddy).
2. L0 static analysis (MCA already ran it; Buddy checks the
   return).
3. PARALLEL agent reviews (context-isolated).
4. CHIEF-1 consolidation (L2 only) — dedup, severity ranking,
   noise filtering.
5. DISCOURSE (L2 only, optional).
6. CHIEF-2 synthesis (L2 only) — confidence adjustment.
7. VERDICT.

## Content preservation on fixes

→ `skills/_protocols/content-preservation.md` (SoT).
Defensive code (timeout guards, fallback paths) is not removed
just because the happy path doesn't exercise it.

## Extended output paths

| Artifact | Path |
|----------|------|
| Agent reviews | `docs/reviews/code/{task-id}-{role}.md` |
| Consolidated | `docs/reviews/code/{task-id}-consolidated.md` |
| Discourse | `docs/reviews/code/{task-id}-discourse-{role}.md` |
| Verdict | `docs/reviews/code/{task-id}-verdict.md` |

## Agent overview

| Agent | Focus | L1 | L2 |
|-------|-------|----|-----|
| code-review | Correctness + architecture + performance (3 axes) | ✓ | ✓ |
| code-adversary | Smart-but-wrong, race conditions | ✓ | ✓ |
| code-security | Auth, injection, validation | — | ✓ |
| code-domain-logic | State machines, business rules | — | ✓ |
| code-reliability | Observability, failure recovery | — | ✓ |
| code-data | Schema, queries, migrations | — | ✓ |
| code-api-contract | REST, schema pipeline, SSE | — | ✓ |
| code-ai-llm | Prompt, model, token budget | — | ✓ |
| code-docs-consumer | Code docs + spec readability | — | ✓ |
| code-chief | Consolidation, discourse synthesis | — | ✓ |
| code-spec-fit | Spec conformance + sole test-coverage owner | — | ✓ + spec_ref |
| code-spec-drift | Retroactive spec drift | — | ✓ + retroactive |
| code-architect-roots | Pattern-purity (post-build) — gated trigger | — | ✓ + new-contract |

**Multi-axis persona:** code-quality + code-architecture +
code-performance were absorbed into code-review as a 3-axis
persona. Axis marker in findings:
`Axis: Correctness | Architecture | Performance`. Drill+Trace per
axis is required.

## NEW MODULE vs NEW SUBSYSTEM (level-choice detail)

"NEW MODULE" alone is no longer sufficient for L2 escalation. A
new file in an existing directory tree is NEW MODULE (stays at
L1). Only NEW SUBSYSTEM (first instance of a top-level service /
domain at the same depth as existing subsystems) escalates to L2.
The distinction is mechanical: a new file in an existing directory
tree is NEW MODULE; a new top-level directory at the same depth as
existing subsystems is NEW SUBSYSTEM.

Aligned with WORKFLOW.md gate 8: L2 triggers on **new exported
behavior** (new public API surface, new state machine, new schema),
not on file-creation. Shape-preserving extractions stay at L1.

## Optional L1+ mid-tier

L1 + 1 risk-specialist (drawn from L2 specialist set per the
brief's risk-assessment top-1 entry) is a precision-escalation
option when effort=S/M but a single risk-class dominates (e.g.
error path with security implications → core + 1× security).

## State-vocabulary-property trigger (architect-roots required)

When the brief's §Implicit-Decisions-Surfaced contains a
`structural_invariants` LD with pattern-class "state-vocab" OR
"smell-transfer" OR "cycle-symptom-cause" for ANY LD,
`code-architect-roots` is REQUIRED on the specialist-set, not
optional. The state-vocab half-coverage concern is structurally
invisible to the other specialists.

Note: post-build architect-roots is now gated to "new exported
contract or replicable-downstream pattern" per `agents/code-architect-roots.md`.
Shape-preserving extractions do NOT fire post-build architect-roots
even when this trigger nominally applies — the pre-implementation
lens (`agents/code-architect-lens.md`, task 372) handles those.

## Specialist-name registry-check (NON-NEGOTIABLE)

Every specialist name in a brief's pre-arranged specialist-set OR
in Buddy's dispatch list MUST resolve to a real file in
`agents/code-*.md`. Hallucinated labels (e.g. `code-async`,
`code-concurrency`) silently fall through at dispatch-time and
cause specialist-set drift — the risk-area they were meant to
cover ships unreviewed. Run `ls agents/code-*.md` at dispatch-prep
to verify; if a name does not match, substitute from the canonical
table in SKILL §3 (Infra/worker → `code-reliability`, async/race →
`code-adversary` + `code-architect-roots`). Log substitutions in
the dispatch transparency-header.

## code-architect-roots vs code-review Architecture-Axis

`code-architect-roots` is **property-shaped** (smell-transfer,
cycle-symptom-cause, state-vocab-half), distinct from `code-review`
Architecture-Axis 2 which is **module-graph-shaped** (dependency
direction, coupling, layer violations). Both run in parallel on
substantial L2 when architect-roots is triggered.

## Migration note (2026-04-30)

Before 2026-04-30 the L2 table had separate entries for
`code-architecture` (dependency / cross-package) and `code-performance`
(hot path / N+1 / memory). Both are absorbed into `code-review`
since the hybrid migration. The risk areas dependency / architecture
and hot path / performance are covered by `code-review` — no
separate specialist dispatch needed.

## Fix-pass dispatch (post-FAIL detail)

When dispatching MCA after FAIL, the brief MUST explicitly state:

- **Test scope:** scope-focused on touched files
  (`uv run pytest <scope-files> -x --tb=short`), NOT
  `uv run pytest tests/`. Per `skills/convergence_loop/SKILL.md`
  §"Test scope between passes".
- **L0 scope:** `ruff check <touched-files>` +
  `mypy <touched-files>` only. NOT the full repo.
- **Full-suite sweep:** ONCE at convergence-end, not per
  fix-phase.
- **Re-review composition:** single reviewer per cluster (see
  Re-review composition below), not full-board redo.

Don't rely on MCA picking the right default — the test-driven
mindset baked into prompts and skills defaults to full-suite.
Make scope-focused testing explicit in the brief.

## Risk carry-forward — full YAML schema

The `remaining_findings:` block schema (referenced from SKILL §5
Verdict):

```yaml
remaining_findings:
  - id: C2-003                                 # cluster / finding ID
    target: new_task                           # routing target — see enum table below
    severity: high                             # critical | high | medium | low
    locator: src/foo.py:47-52                  # file:lines or spec §
    title: "Validator regex rejects v1 forms"
    rationale_for_carry_over: >
      PASS_WITH_RISKS — H-finding, within 2H budget, documented per
      re-review-limit hit without severity drop
    proposed_action: "Tighten regex per C2-004 — ~10 LOC"
  - id: C2-006
    target: spec_text                          # batch-patched, no task
    severity: low
    locator: docs/specs/<spec>:651
    title: "Example block shows v1 syntax; should be v2"
    proposed_action: "Replace `foo_v1(...)` with `foo_v2(...)` at line 651"
  - id: C2-005
    target: absorb_next                        # logged, no immediate action
    severity: low
    locator: tests/foo/test_bar.py:123
    ...
  - id: C2-009
    target: accept                             # known limitation — no fix, no task
    severity: medium
    locator: src/stream.py:88-94
    title: "Narrow late-release race on the slot pool"
    rationale_for_carry_over: >
      Non-blocking — backstopped by the reaper; does not block the
      reported defect. Default accept per §5 proportionality triage.
```

## 7-value `target:` enum (full detail)

| `target` | Action | When to use |
|---|---|---|
| `spec_text` | batch-patched in same commit by `agents/spec-text-drift-batch.md` (per spec 306 §4.8) — no task | spec wording, example blocks, cross-ref drift, mirror-line inconsistency |
| `new_task` | `task_creation` skill dispatched per entry | real follow-up work (MEDIUM+ severity only, ≥M effort, new behaviour). **LOW is forbidden — see SKILL §5 hard floor.** |
| `watch_item` | appended to `context/risk-watch.md` per `skills/_protocols/risk-watch-template.md` | forward-looking risk that fires only on a future trigger |
| `accept` | recorded in the verdict as a known accepted limitation — no fix, no task, no trigger | non-blocking finding that is narrow + backstopped, latent, or introduced by a prior fix-pass in this chain and narrower than the original defect — the DEFAULT disposition for any non-blocking finding, MANDATORY for any standalone LOW |
| `absorb_next` | logged to chief-verdict-archive only — no immediate action | LOW finding the next code-touch on the same file will trivially close |
| `closes_with: <id>` | no action — references another finding's fix | duplicate / convergence — same root, two angles |
| `re_review: <reviewer>` | dispatch the named reviewer with the finding cluster as scoped focus | chief uncertain, contradiction across reviewers, second specialist look |

Chief MUST annotate every entry. Empty `target:` fails chief
output validation (per `skills/risk_followup_routing/SKILL.md`).
Distribution check: if all entries have the same `target:`,
chief surfaces as anti-pattern (likely missed triage).

The workflow step `risk-followup-routing` (build / review / fix
workflow.yaml) reads this block and mechanically files a follow-up
task via `task_creation` — empty/absent block: skip. A verdict
file without the block on PASS_WITH_RISKS is an invalid verdict
(chief re-synth mandatory).

## PASS_WITH_RISKS history (rationale)

PASS_WITH_RISKS was historically "≤2H documented" with "documented"
as an unspecified string — findings ended up in the verdict prose
and never became follow-up tasks. Structured `remaining_findings:`
block + workflow step makes carry-forward mechanically enforced,
not bookkeeping-dependent.

## Self-introduced findings

A finding introduced by a prior fix-pass in the same chain, narrower
than the original defect, is `accept` by default — chasing it ratchets
the next pass's scope upward (the fix-pass-manufactures-the-next-pass's-finding
spiral).

## No "leanest fix" for non-fix-now findings

A minimal fix is a flavour of fix-now for when a fix IS warranted —
never a disposition for a finding that did not clear the fix-now gate.
`accept` means closed: no fix, no task, no follow-up investigation.

## Buddy MUST NOT offer paths A/B/C

"Only CRITICALs now, the rest later" — phased scope negotiation
undermines the board verdict. The proportionality triage is the chief's
principled per-finding disposition, not a severity menu offered to the
user.

## Re-review limit (foundation override)

Default: **max 2 re-reviews → ESCALATE**. But:

- **Foundation tasks** (intake-mvp, brain-foundation, brain-schema,
  schema-foundation, harness-runtime-patterns, other tier-1 builds):
  Buddy may override the limit if convergence / severity drop per
  re-review is measurable (e.g. pass 1 FAIL 3C+16H → pass 2 FAIL
  0C+4H → pass 3 FAIL 0C+1H → pass 4 PASS). Foundation work needs
  to settle — better 4 reviews than permanent architecture drift.
- **Buddy decision per pass:** if severity does NOT drop from
  pass N to pass N+1 (e.g. the same convergence cluster shows up
  again) → ESCALATE instead of continuing. The limit override
  applies only on measurable progress.
- **User-override pattern:** the user may say "re-review more than
  2x if needed — your call", which explicitly empowers Buddy without
  pre-escalation.

Non-foundation tasks: max 2 re-reviews stays strict.

## Re-review composition (full table)

Default re-review on FAIL = **single-reviewer pass-1.5**: the SAME
reviewer that flagged the finding cluster reads the fix. Not full
L1 / L2 redo.

| Re-review type | Composition | When |
|----------------|-------------|------|
| Fix verification (default) | Single reviewer per cluster, scope = the finding's `affected_scope` | After every MCA fix-pass on FAIL |
| Bundled fix verification | Convergence-axis grouping — ~3 reviewers covering the systemic patterns in the bundle (correctness/architecture via `code-review`; concurrency/state-machine via `code-domain-logic` or `code-adversary`; cross-spec amendment fitness via `code-spec-fit` if relevant). Buddy may add a 4th for an axis the brief's risk-assessment names dominant (e.g. `code-security` on an auth-fix-pass). | Fix-pass with >5 clusters OR >5 files OR cross-spec amendments touched |
| Fresh angle (exception) | Full board (L1 / L2 per the original level) | Only if pass-1.5 surfaces an architecture concern OR Buddy explicitly wants a fresh take |

Rationale: the verdict file documents `file:line` per finding; the
fix touches that scope, nothing else can change. A 5-reviewer redo
of unaffected modules is risk-theater + 2-3× wallclock / token cost
without new signal. Full-board re-runs are reserved for fresh
analysis at a new convergence-pass scope, not for "did the fix
land?" verification.

**Bundled-fix-pass rationale (mid-row):** single-reviewer-per-cluster
is silly at >5 clusters (10× dispatch overhead, sequential bottleneck);
full-board redo is risk-theater on bundled scope. Convergence-axis
grouping covers the systemic patterns the bundle risks regressing
without the dispatch explosion. The 3-reviewer default is a starting
point — Buddy adapts the axis-set to the brief's risk-assessment
top entries.

**F-AR (architect-roots) re-review exception:** pattern-class fixes
touch multiple files by definition (smell-transfer fix = pattern
moved out of every site). Default re-review for F-AR findings =
pass-1.5 with **extended scope** (all files affected by the pattern,
not just one finding-locator). Fresh-angle exception fires when the
fix introduces a DIFFERENT pattern-class than the one flagged
(pattern-class-mismatch in fix) — then full-board redo on the new
class.

## Extended anti-patterns

- **NOT** FAIL → MCA fix → immediate re-review without a new L0.
  INSTEAD run L0 (ruff + mypy) after every fix. Because: a fix can
  break linting; re-review otherwise sees it later.
- **NOT** accept a chief signal without a tracking table (L2).
  INSTEAD run the preservation check (consolidation-preservation).
  Because: silent loss happens in the code board too.
- **NOT** re-run the full L1 / L2 board for fix verification post-FAIL.
  INSTEAD single-reviewer pass-1.5 of the finding cluster (Re-review
  composition above). Because: 5 reviewers re-doing unaffected scope
  = risk-theater + 2-3× wallclock / token cost without new signal.
- **NOT** brief MCA with `pytest tests/` as DoD on fix-pass dispatch.
  INSTEAD scope-files explicit. Because: re-running untouched modules
  is signal-noise; test-driven mindset baked into MCA prompts defaults
  to full-suite — must be overridden in the brief.
