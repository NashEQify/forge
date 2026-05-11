# Spec Board — 5 Dimensions Review Mode

Optional dispatch mode for `spec_board` that structures the review explicitly
along **5 quality dimensions**. Complementary to the role-based standard
dispatch — the 5 dimensions are a grid that runs orthogonal to roles.

**When to use this dispatch:**
- Pre-launch review of a whole spec corpus
- After a `spec_update` skill run (for dim-coverage validation)
- When in doubt after a standard dispatch: "which dim has the standard
  pass not covered?"

**When NOT:**
- Single-spec delta verify after a fix (too heavy for small changes)
- Runbook/template/skill reviews (there, implementability =
  executability, not code-implementability — different semantics)

---

## The 5 dimensions

Every finding MUST be assigned to one of these dimensions (DIM tag in
the finding ID):

| # | Dimension | What it should check |
|---|---|---|
| **COMP** | Completeness | Are scenarios missing? Error cases? Edge cases? Migration paths? What is NOT in the spec that should be? |
| **CONS** | Consistency | Do parts of the spec contradict each other? Are terms used uniformly? Do internal references match (section numbers, links)? |
| **IMPL** | Implementability | Can a developer build this 1:1 without follow-up questions? Are magic numbers explained? Are mechanisms described in full (not "see code")? |
| **INTF** | Interface contracts | Are all inputs/outputs specified exactly? Types, formats, bounds? Event payloads? State enums? API signatures? |
| **DEPS** | Dependencies | What must exist for this to work? Are external libraries, browser APIs, services named explicitly? Are version requirements clear? |

---

## Role focus (who checks which dim primarily)

Every agent checks all 5 dimensions, but with one primary perspective:

| Role | Primary focus | Secondary |
|---|---|---|
| `board-adversary` | **COMP** + **CONS** (smart-but-wrong, contradictions, edge cases) | IMPL, INTF |
| `board-adversary-2` (Deep) | **COMP** (first-principles check — what is fundamentally missing?) | CONS, DEPS |
| `board-adversary` (Deep, sonnet variant, prefix F-A3-) | **CONS** + **COMP** (E2E scenarios, cross-section consistency) | INTF |
| `board-implementer` | **IMPL** + **INTF** (buildability, API check, interface contracts) | DEPS |
| `board-impact` | **DEPS** + **CONS** (cross-spec blast radius, dependency chains) | COMP |
| `board-consumer` | **IMPL** (readability-as-implementability for new readers) | COMP |
| `board-chief` | Consolidates all 5, produces per-dim verdict | — |

**Standard pass** (4 agents): Chief + Adversary + Implementer + Impact —
covers all 5 dimensions primarily (COMP+CONS via Adv, IMPL+INTF via Impl,
DEPS via Impact, Chief consolidates).

**Deep pass** (7 agents): adds Adv-2, Adv-3, Consumer — redundant
coverage of the heavy dimensions (COMP, CONS, IMPL).

---

## Dispatch prompt template

This prompt is given to every review agent as an **additional block** in
the dispatch, after the standard reviewer-base.md context:

```
=== 5 DIMENSIONS REVIEW MODE ===

You review this spec along 5 quality dimensions. As {ROLE}, your primary
focus is: {PRIMARY_DIMS}. You may produce findings in all 5 dimensions,
but your main contribution is {PRIMARY_DIMS}.

**The 5 dimensions:**

1. **COMP — Completeness**
   - Missing scenarios, error cases, edge cases, migration paths
   - What is NOT in the spec that SHOULD be there to fully describe
     the behaviour
   - "as needed" / "if applicable" / "later" / "see code" are warning
     signs — each one is a COMP finding

2. **CONS — Consistency**
   - Contradiction between sections of the spec
   - Inconsistent terms (the same concept under different names)
   - Broken internal references (section X points to section Y that
     does not exist or has been renamed)

3. **IMPL — Implementability**
   - Can a developer build this 1:1 without follow-up questions?
   - Magic numbers without justification (e.g., "500ms delay" without
     a reason)
   - Mechanisms referenced as "see code" or "as in the implementation"
     instead of being fully described
   - Implementation blockers: a line that sounds correct but is not
     buildable without making an implicit decision

4. **INTF — Interface contracts**
   - API signatures, event payloads, state enums, config schemas
   - Types, formats, bounds (min/max/default)
   - Error responses explicit (not "throws Error" but "throws X with
     payload Y")
   - Cross-spec interfaces: who calls what with which parameters

5. **DEPS — Dependencies**
   - Which external libraries/services/APIs MUST exist
   - Browser API versions, library versions when critical
   - Runtime dependencies: what must be running/started
   - Documented? Or implicit?

**Finding format:**

Every finding MUST carry a dimension. Finding-ID format:
`{ROLE_SHORT}-{DIM}-{NUM}` — e.g., `ADV-COMP-001`, `IMP-INTF-003`.

Each finding:
- **ID**: `{ROLE_SHORT}-{DIM}-{NUM}`
- **Severity**: CRITICAL / HIGH / MEDIUM / LOW
- **Location**: section, approximate line
- **Problem**: 1-2 sentences, concrete
- **Remediation**: what the spec should say (concrete text or structure)

**Constraint**: if you find ten COMP findings and none in the other
dimensions, you are not a review regular — use all 5 dimensions
deliberately. A spec that has problems in only one dimension almost
certainly has problems in others; you simply did not look for them.

**Output ordering**: findings grouped by dimension, within a group by
severity descending. Finish with a one-line summary per dimension:

```
## Findings by Dimension

### COMP (Completeness) — 4 findings
- ADV-COMP-001 CRITICAL: ...
- ADV-COMP-002 HIGH: ...

### CONS (Consistency) — 2 findings
...

### IMPL, INTF, DEPS: (see above)

## Summary per Dimension

| Dim | Findings | Severity |
|---|---|---|
| COMP | 4 | 1C 1H 2M |
| CONS | 2 | 2M |
| IMPL | 3 | 1H 2M |
| INTF | 1 | 1M |
| DEPS | 0 | clean |
```

=== END 5 DIMENSIONS REVIEW MODE ===
```

The variable `{ROLE}` is replaced at dispatch (`Adversary`, `Implementer`,
`Impact`, `Consumer`). `{PRIMARY_DIMS}` is replaced with the role's
primary dimensions (see table above). `{ROLE_SHORT}` is replaced with
`ADV`, `IMP`, `IMPACT`, `CON`, `ADV2`, `ADV3`.

---

## Chief consolidation (5-dim mode)

The Chief receives, in addition to the standard consolidation prompt:

```
=== 5 DIMENSIONS CONSOLIDATION MODE ===

Consolidate the findings of all reviewers along the 5 dimensions:
COMP, CONS, IMPL, INTF, DEPS.

**Structure of the consolidated report:**

1. **Executive summary** (3-4 sentences): overall verdict + which dims
   are clean, which have work to do.

2. **Per-dimension verdict** (one paragraph each):
   - COMP: PASS / NEEDS-WORK (with severity distribution)
   - CONS: PASS / NEEDS-WORK
   - IMPL: PASS / NEEDS-WORK
   - INTF: PASS / NEEDS-WORK
   - DEPS: PASS / NEEDS-WORK

3. **Consolidated findings table** (sorted: severity desc, then dim):
   | Finding-ID | Dim | Severity | Location | Problem | Remediation | Status |

4. **Merge spot-check**: show at least 2-3 MERGED findings explicitly —
   were they merged correctly? Same root cause?

5. **Minority re-check**: scan REMOVED low-severity findings briefly —
   anything surprising in there?

6. **Post-convergence check**:
   - The weakest point in PASS — which dim could flip on closer
     inspection?
   - Which single-agent finding was downweighted the most — rightly so?

7. **Overall verdict**:
   - **PASS**: all 5 dimensions PASS (0 CRITICAL + 0 HIGH)
   - **NEEDS-WORK**: at least one dimension NEEDS-WORK
     -> name which dim(s), which severity, fix-scope estimate

=== END 5 DIMENSIONS CONSOLIDATION MODE ===
```

---

## Verdict criterion

- **PASS**: 0 CRITICAL + 0 HIGH in **all** 5 dimensions
- **NEEDS-WORK**: at least 1 CRITICAL **OR** 1 HIGH in **at least one**
  dimension
- Standard -> Deep escalation: ≥1 CRITICAL **OR** ≥3 HIGH in a single
  dimension (signals a systematic gap)

---

## Anti-patterns

- **DO NOT** produce findings without a dimension tag. INSTEAD every
  finding must be assigned to one of the 5 dimensions. Why: without a
  tag the Chief cannot validate coverage, and the DIM map from
  `spec_update` phase 3 cannot be cross-checked.

- **DO NOT** cluster all findings in **one** dimension. INSTEAD check
  all 5 deliberately. Why: a reviewer who only finds COMP has likely
  overlooked IMPL, not confirmed IMPL as clean.

- **DO NOT** reduce the Chief to role-based consolidation when the
  dispatch ran in 5-dim mode. INSTEAD a per-dim verdict in the Chief
  output. Why: the 5-dim grid is the entire point of this mode;
  without a per-dim verdict you only have the standard dispatch with
  extra tags.
