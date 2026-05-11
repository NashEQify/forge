# Test Plan Format

SoT for test-plan structure. Referenced by
`workflows/runbooks/build/WORKFLOW.md` (Prepare phase TEST-DESIGN step)
and `skills/testing/SKILL.md`.

A test plan is created in tester design mode. It is persisted as a file
(`docs/tasks/{task_id}-test-plan.md`) and survives context rotation.
The tester in execution mode translates TCs 1:1 into test functions.

---

## YAML header (machine-readable)

```yaml
---
task_id: 115
spec: docs/specs/navigate-mode.md
spec_version: v1
test_plan_spec_ref: v1          # Freshness: must == spec_version
created: 2026-03-14
status: active                  # active | superseded
tc_count: 24                    # total TCs — mechanically verifiable
coverage_complete: true         # every AC + every FM has at least one TC
levels: [L2, L3, L4]            # included test levels (full path: grows)
---
```

**Freshness check (tester execution mode, required):**
`spec_version == test_plan_spec_ref`? yes -> fresh. no -> STOP, stale.

**tc_count check (mechanical):**
`tc_count == grep -c '^### TC-' test-plan.md`? yes -> continue.
no -> STOP, inconsistent.

---

## Coverage matrix (required)

Every AC and every failure mode MUST have at least one row.

```markdown
## Coverage Matrix

| Source | ID | TC-IDs | Level | Status |
|--------|-----|--------|-------|--------|
| AC-1 | Community overview | TC-001, TC-002 | L3 | pending |
| AC-8 | Graceful degradation | TC-010, TC-011 | L3 | pending |
| FM-1 | 0 seed entities | TC-015 | L2 | pending |
```

Status: `pending` -> `covered` -> `pass` | `fail` | `skipped`
(reason required for `skipped`).

---

## TC block schema

```markdown
### TC-{NNN}: {Short description}

- **Level:** L2 | L3 | L4 | L5
- **Type:** Positive | Negative | Degradation | Boundary | Regression
- **Source:** AC-{N} | FM-{N}
- **Setup:**
  - {DB/service}: {declarative — WHAT must exist, not HOW}
- **Input:** `{function call with concrete parameters}`
- **Assertions:**
  - `{executable Python code — isinstance, len, ==, raises}`
- **Teardown:** {testcontainers cleanup | None}
```

---

## Test file convention

Tests are stored in: `tests/{spec_name}/`
File names: `test_{tc_group}.py` (grouped by AC or function area).
Shared fixtures: `tests/{spec_name}/conftest.py`.

Example for task 040 (gateway):
```
tests/gateway/
  conftest.py            # shared fixtures (NATS mock, DB pool)
  test_auth.py           # TC-004 (G-4 auth)
  test_chat_endpoint.py  # TC-001, TC-002, TC-003 (G-1, G-2, G-3)
  test_health.py         # TC-006 (G-6)
  test_sessions.py       # TC-005, TC-010 (G-5, G-10)
```

---

## Implementation matrix (tester execution-mode report)

```markdown
## Implementation Matrix

| TC-ID | Test function | Status |
|-------|-------------|--------|
| TC-001 | test_tc_001_sse_stream | pass |
| TC-010 | test_tc_010_error_chunk | fail |
| TC-022 | SKIPPED: Neo4j unavailable | skipped |
```

**Rules:**
- Every TC in the plan MUST have one row
- `SKIPPED` only with a reason
- fewer rows than tc_count = FAIL
- SIGNED OFF only when: 0 fail, all skipped entries justified,
  row count == tc_count

---

## Accumulation (Full Path)

In Full Path, the test plan grows across 3 levels:
- Level 1: tester receives `target_levels=[L4,L5]`. Add new TCs.
- Level 2: tester receives `existing_plan={path}, target_levels=[L3]`.
  TCs are ADDITIVE.
- Level 3: tester receives
  `existing_plan={path}, l1={l1_path}, target_levels=[L2]`.
  TCs are ADDITIVE.

tc_count, coverage matrix, and `levels` in the header grow accordingly.
Existing TCs are NOT changed (regression rule:
`skills/testing/SKILL.md`).

---

## TC scope (for incremental execution)

MCA can pass a TC scope to tester execution mode:
- `tc_scope: all` — execute all TCs (default)
- `tc_scope: L4,L5` — only TCs with level L4 or L5
- `tc_scope: L3,L4,L5` — L3 + regression of previous levels

Tester filters TCs by level tag. Implementation matrix contains only
executed TCs, plus a note for active scope.

---

## Rules (7)

1. **Assertions are code, not prose.** `len(result) >= 1` — not
   "there should be results".
2. **Setup is declarative.** What must exist in which DB. Execution tester
   builds fixtures.
3. **1 TC = 1 test function.** No TC that checks "multiple things".
   Split when in doubt.
4. **Source is required.** Every TC references AC-N or FM-N.
5. **tc_count == number of TC blocks.** Mechanically verifiable.
   Mismatch = STOP.
6. **Every TC is implemented.** Implementation matrix proves completeness.
7. **Level tag is required.** Every TC has one level (L2/L3/L4/L5).

---

## Allowed adjustments by tester execution mode

**Allowed:**
- ADJUST assertions (field names, types aligned to actual implementation)
- TRANSLATE setup into testcontainers fixtures
- ADD fixture details

**Not allowed:**
- REMOVE TCs (without SKIPPED + reason)
- WEAKEN assertions
- ADD new TCs without matrix documentation
