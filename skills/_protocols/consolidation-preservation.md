# Protocol: Consolidation Preservation

Prevents silent loss in multi-agent review consolidation.
Loaded by: spec_board (chief dispatch, incl. mode=ux),
code_review_board (code-chief dispatch), sectional_deep_review,
architecture_coherence_review.

## The problem this protocol solves

Chief consolidation loses findings, especially single-agent
findings. The word "consolidate" triggers a compression mode.
Without an explicit preservation rule, findings without a
chief-internal tracking mechanism get "forgotten". Demonstrated on
solve-framing pass 1 (session 98): 4 of 34 raw findings silently
lost, all single-agent.

## Preservation contract (NON-NEGOTIABLE)

**Every finding from every sub-review MUST appear in the
consolidated output.** Allowed end-states (anything else is silent
loss):

1. **KEPT** — the finding appears as a standalone F-C-NNN in the
   consolidated output. Required: co-finder list when >1 agent
   raised it.
   **Divergent marker:** when ONLY 1 agent has the finding (no
   co-finder), tag `[SINGLE-SOURCE]` in the consolidated output.
   Single-source findings are NOT automatically less important —
   they may be the most valuable (only one sees it; the rest are
   blind). Severity is NOT downgraded just because the finding is
   single-source. Chief justifies in the post-convergence check
   why kept / downweighted.
2. **MERGED** — the finding is folded into another F-C-NNN.
   Required: name the original ID under "co-finder" in the merged
   finding.
   **Merge rule:** MERGE only when the ROOT CAUSE is identical
   (same problem, same mechanism). If symptoms overlap but root
   causes COULD differ → **RELATED** instead of MERGED: keep both
   as separate F-C-NNN, cross-reference ("Related: F-C-NNN")
   instead of absorbing. When in doubt: RELATED (preserve
   information > compactness).
3. **REMOVED** — the finding is explicitly removed.
   Required: a dedicated section "Noise filter — removals" with
   rationale per ID.

**Forbidden:**
- mentioning a finding without an end-state (= silent loss);
- REMOVED without rationale;
- MERGED without a co-finder entry in the target finding;
- summary phrasing like "rest is noise" without IDs.

## Mandatory tracking table

Before writing the consolidated review output: **build the tracking
table** and persist it inside the consolidated file.

Format:

```
| Raw ID | Agent | Severity | Status | Target |
|--------|-------|----------|--------|--------|
| F-A-001 | Adv   | high     | MERGED | F-C-002 (co-finder, identical root cause) |
| F-A-004 | Adv   | medium   | RELATED| F-C-005 (similar symptom, different root cause) |
| F-A-002 | Adv   | medium   | KEPT   | F-C-003 |
| F-A-003 | Adv   | low      | REMOVED| (Reason: style preference, no semantic impact) |
| F-I-001 | Impl  | critical | MERGED | F-C-001 (co-finder Impact) |
| ...    |       |          |        |        |
```

**Required final row of the table:**

```
Total Raw: N  |  Kept: K  |  Merged: G  |  Related: L  |  Removed: R
Verification: N = K + G + L + R ?  (must hold; otherwise silent loss)
```

If the verification equation does not hold, the chief MUST find the
missing IDs and either assign them a target or declare them REMOVED
with rationale before the consolidated review is finalized.

## What's Working Well (consumer obligation)

Reviewers deliver "What's Working Well" (1-3 positive observations,
reviewer-base.md). The chief MUST collect these into a dedicated
section `## What's Working Well` in the consolidated output — not
mixed into findings, not omitted. Good patterns become visible and
reinforceable. Without this section: the consolidated output is
incomplete.

## Self-check before closing

Before the chief writes "PASS" or "FAIL" as the overall verdict:

1. Tracking table is present and complete.
2. N = K + G + L + R is verified (numbers at the end of the table).
3. Every MERGED ID is listed under co-finder in the target finding.
4. Every REMOVED ID has a rationale in the noise-filter section.
5. No raw ID without a status.

A consolidated review without this tracking table is not finished.

## Why a table (not prose)?

The table is mechanically checkable. Prose like "I considered all
relevant findings" cannot be checked and produces exactly the
silent-loss bug. Table + verification equation = machine-readable
hard gate, not a soft target.

## Relation to convergence_loop

`convergence_loop` MUST signal PASS only when this preservation
check is complete. A missing tracking-table entry = automatic
NEEDS-WORK, not PASS.
