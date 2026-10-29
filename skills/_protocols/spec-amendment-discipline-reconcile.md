# Spec-amendment discipline — sweep and same-commit reconciliation

Step-loaded unit of `skills/_protocols/spec-amendment-discipline.md`. Read it after the pre-edit gate's comparison
(step 3), before deciding what the amendment commit reconciles, and for a rename, mechanism or contract change or
another amendment with coordinated live impact: as author, as integrator before and after applying it, and as
verifier.

### Bounded amendment sweep

For a rename, mechanism or contract change, or another amendment with
coordinated live impact, use the existing edit-list to carry the following
context. Keep a local correction local; no separate inventory ceremony
or whole-corpus scan is required.

**Author.** Record the relevant input view actually read: target sections,
source contracts, dependency evidence and protected regions. Use content
identities or retained exact comparison views; paths or a moving HEAD
alone do not identify dirty working-file content.

Search named occurrences, then inspect actual producer → artifact →
consumer connections, including consumers that use different names.
Maps and supplied paths are discovery seeds, not scope whitelists.
The code-grounding cost ceiling limits initial symbol probes, not the
affected dependencies the sweep must account for.

Classify relevant occurrences or bounded groups as change, preserve or
unrelated, with a local or structural reason. Preserve historical
changelogs/version excerpts, frozen regions and concrete examples valid
in their stated context. An example claiming the current contract is a
live consumer; a valid labelled legacy example may retain old names.
Same spelling alone does not establish the same entity.

For each changed contract, name the expected consumer updates or retained
assumptions and the checks that establish them after application. Identify
protected text for comparison with its observed original.

Follow a demonstrated affected dependency until inspection establishes
that its downstream contract remains valid; record that stopping reason.
Conceptual adjacency alone does not extend the sweep, and absence of the
changed name alone does not end it. Reconcile related drift under the
same-commit rule. Unrelated drift remains outside this amendment; retain
any applicable obligation at its existing owner.

**Integrator.** Immediately before application, compare relevant current
inputs with the recorded input view. A changed input reopens affected
grounding, dependency reasoning, dispositions and edit expectations before
the affected edits are applied. Record the refreshed conclusion even if
the proposed prose remains valid. A clean patch does not establish
freshness; unaffected branches need not be reauthored.

After application, compare actual edits and consumer state with the
expected results and protected text with its observed original. Preserve
the edit-list and application observations for the existing verification
consumer. Unestablished required updates or checks remain explicit;
integration alone does not establish completion.

**Verifier.** Independently inspect actual affected producer/consumer
contracts using the same dependency boundary. Challenge the supplied
inventory rather than treating it as a whitelist. When sweep context is
supplied, check its expected results, preservation claims and freshness
observations against actual files and evidence. Report missed required
updates, unintended protected-text changes, unresolved stale grounding
or unavailable required comparisons in the existing result format.
PASS requires evidence for these applicable checks.

Existing MCA and retro callers remain valid without a sweep they did not
author. Sweep-specific comparisons are conditional on supplied context.
Existing read-only boundaries, authorization, issue routing and dispatch
thresholds remain unchanged.

This procedure uses existing artifacts and owners. It introduces no
machine schema, runtime enforcement, reference validator, effort estimator
or numerical efficiency guarantee.

### Same-commit reconciliation rule

If code state diverges from the §-section text (see §What counts as
divergence below), the divergence MUST be reconciled in the SAME
amendment commit (`framework/invariants.md` §Stale cleanup) — adding a
"spec-drift-fix" strand to the amendment cluster, not deferring to a
separate task. Cross-doc stale references to the same artifact are
swept by `spec_amendment_verification` post-amendment per `spec-amendment-discipline.md` §Dispatch
shape.

The same single-commit absorption applies to category (d)
module-boundary topics on L1+ specs via the §module-decomposition-add
strand — sister mechanism, different trigger.

**The amendment author writes the spec to match the code** — unless
the build is explicitly changing the code-shape, in which case the
spec leads.

### What counts as divergence

Three categories, with reconciliation triggers:

- **(a) Named-symbol mismatch** — the §-section names `FooBar` but
  the code now has `BarFoo`, OR the named class has been removed.
  → **ALWAYS reconcile** in same commit.
- **(b) Structural change with semantic load** — signature change,
  file location moved with implications for consumers, contract shift.
  → **Reconcile when the §-section claims the structure.** If the
  §-section is identifier-only ("uses FooBar") without claiming
  shape, the move alone is not divergence.
- **(c) Abstraction-level mismatch** — the §-section uses paraphrase
  ("the cache layer"), the code uses literal names (`RedisCache`).
  → **NOT divergence.** Paraphrase ↔ literal is intentional
  abstraction.
- **(d) Module-boundary topic in an L1+ spec without §Module-Decomposition
  (touch-it-fix-it for the new-class L1+ discipline)** — when the
  amendment scope touches module-boundary topics (interface, dependency,
  layer, seam, responsibility-split) AND the host spec is L1+ AND the
  host spec does NOT yet have a §Module-Decomposition section, the
  amendment MUST add the §Module-Decomposition section in the SAME
  commit (per the schema in `framework/spec-engineering-l1-sections.md`
  §Convention: §Module-Decomposition for L1+ specs).
  → **Reconcile in same commit** as a §module-decomposition-add strand.
  Mirrors the §spec-drift-fix strand semantics from §Same-commit
  reconciliation rule above. Triggers only on amendment-into-topic;
  unrelated amendments to legacy L1+ specs (typo, §Changelog, cross-ref
  bump) do NOT trigger the absorption.
- **(e) AC-scope amendment in an L1+ spec without §Test-Strategy
  (touch-it-fix-it for the test-contract discipline)** — when the
  amendment scope touches **AC scope** (new AC, AC boundary shift, new
  behavior, new failure mode) AND the host spec is L1+ AND the host
  spec does NOT yet have a §Test-Strategy section, the amendment MUST
  add the §Test-Strategy section in the SAME commit (per the schema in
  `framework/spec-engineering-l1-sections.md` §Convention: §Test-Strategy for L1+
  specs), with bug-class rows **only for the AC(s) the amendment
  touches**. Pre-existing ACs without bug_class rows stay uncovered;
  the §Test-Strategy section is marked `partial: true` (header field)
  until a future amendment fills more rows or a dedicated migration
  task lands the full historic retrofit. Catalog grows organically
  per touch; the first AC-amendment does not carry the whole-spec
  retrofit weight.
  → **Reconcile in same commit** as a §test-strategy-add strand.
  Triggers only on AC-scope amendment; unrelated amendments (typo,
  §Changelog, cross-ref bump, internal example fix) do NOT trigger.

  **Full-historic-AC migration** (whole-spec retrofit) is a separate
  future topic — a dedicated migration task / sprint, not the
  per-amendment author's burden.

- **(f) §Test-Strategy bookkeeping append (adversary-mode discovery)** —
  when `skills/testing/SKILL.md` test-design surfaces a new
  `bug_class` (typically via adversary-mode), appending the row to
  §Test-Strategy is **bookkeeping-tier** (single section append, no
  contract change). No spec_board re-spin, no §Changelog ceremony
  per row; one §Changelog line summarising the batch is sufficient.
  The append happens inline during test-design (commit at end of
  adversary run or folded into a later commit). Test-design cannot
  invent bug_classes that are not derivable from an existing AC;
  if the bug_class belongs to no existing AC, that is category (e)
  territory (AC scope), not (f).

- **(g) State-carrier amendment without / outside §Mechanism-Lifecycle
  (touch-it-fix-it for the lifecycle discipline)** — when the amendment
  adds, removes or re-routes a state, an operation, a guard, an
  enforcement locus or an invariant of a mechanism (incl. a derived
  state or an "only via" rule) AND the owning spec has no
  `§Mechanism-Lifecycle` section for it, the amendment MUST add the
  section in the SAME commit (schema: `_protocols/mechanism-model.md`),
  with every cell filled. When the section exists, the amendment MUST
  edit the affected cells in the SAME commit — a ruling, simplification
  or user decision recorded only in a build log, verdict or changelog
  while the matrix stays stale is divergence of this category.
  → **Reconcile in same commit** as a §mechanism-lifecycle strand.
  Triggers only on amendment-into-mechanism; wording, cross-ref and
  §Changelog edits do NOT trigger.

**Strand-scope stop rule:** use the demonstrated-dependency boundary in
§Bounded amendment sweep. A related claim or affected consumer belongs
to the strand regardless of naming; unrelated divergence does not.
