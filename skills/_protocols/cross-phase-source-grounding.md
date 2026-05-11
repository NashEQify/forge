# Protocol: Cross-Phase Source Grounding

Finding-based source grounding for iterative solve runs. Prevents
silent loss of parked findings from predecessor runs.

**Scope (intentionally solve-only in this version):** only
`solve/WORKFLOW.md` phase 1 step 4a and `frame/SKILL.md` step 4.
Extension to fix / build / review is a **follow-up task** — not in
this run.

## Boundary against DR-12

DR-12 (`operational.md`, `agentic-design-principles.md`) =
**file-based** re-reading before edits. This protocol =
**finding-based** cross-pass grounding. Two separate classes.

## Problem

Session-99 pattern C: solve phases do not automatically pull parked
findings from past runs into the active scope. Concretely: 18
stage-2 parked findings from the framework-ambiguity-audit pilot
were not mapped at the start of phase 4 — only the user's
intervention "is that accounted for?" surfaced 2 real gaps.

## The rule

**Before phase transition 1→2 in predecessor-based solve runs: a
parked-findings mapping table is required.**

Predecessor-based when: the problem statement references an earlier
run, OR the state-file step 3 documents a source, OR the user gives
a continuity hint ("build on X"), OR a board run has parked
findings.

## SoT for parked findings (completeness anchor)

**Canonical source:**

1. **Primary:** consolidated review file of the predecessor run
   (`docs/reviews/board/{run-slug}-consolidated-pass{N}.md`) — if
   it exists. Every finding in the tracking table with status
   `parked`, `deferred`, or merge-target outside scope counts as a
   parked finding.
2. **Fallback:** state-file of the predecessor run — every section
   marked `parked`, `deferred`, `TBD`, `out-of-scope` counts as a
   parked finding.
3. **Failure path:** if none of these sources is reachable →
   **escalate to the user**, no silent skip.

## Mapping-table format (consumer)

```
## Cross-Phase Source Grounding (predecessor: <run slug or commit>)

| Finding ID | Short | Status | Rationale | target_run |
|------------|-------|--------|-----------|------------|
| F-X-003    | Process map cross-ref | addressed | DI-3 scope | - |
| F-X-005    | Spec-authoring gap | parked | out-of-scope | fund-5-run |
| F-A2-012   | Gate composition | refuted | new rule | - |
| F-I-007    | API assumption | potential gap | flag phase 3 | next-solve |
```

**Four status values:** `addressed` | `parked` | `refuted` |
`potential gap`. **Decision gate:** for `parked` AND `potential
gap`, the column `target_run` is **required** (slug of an existing
or explicitly planned run). An empty `target_run` = hard gate
failure. Verification is reviewer-side at phase transition (no
automated check — ephemeral gate via workflow step).

## Producer format (for the current run, as input for successors)

**Schema link to the consumer:** producer entries are matched by
the successor (consumer table above) via `Finding ID` + `target_run`.
The producer's columns `Short` / `Scope rationale` / `Proposal`
become the consumer's `Short` / `Rationale` of the status entry.

At the end of the state file, a section
`## Parked findings (for successor runs)` with the following schema:

```
## Parked findings (for successor runs)

| Finding ID | Short | Scope rationale | Proposal | target_run |
|------------|-------|-----------------|----------|------------|
| ...        | ...   | ...             | ...      | ...        |
```

Every `parked` or `potential gap` finding is persisted here. No
silent shifts — the finding remains traceable.

## Gate rule (phase transition)

Hard gate for solve phase 1 → phase 2 in predecessor-based runs.
Complete = every parked finding from the identified predecessor is
listed; each with status; `addressed` / `refuted` with rationale;
`parked` / `potential gap` with `target_run`.

## Anti-patterns + hard-gate rationale

- **NOT:** "reading is enough" — the table goes into the state file.
- **NOT:** empty `target_run` — slug or planned run.
- **NOT:** retroactive table — before phase transition.

Hard gate: session-99 tipping-point 9 (18 parked findings, 2 real
gaps silently lost without user intervention).
