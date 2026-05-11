# testing — REFERENCE

Detail mechanics. The Buddy-facing `SKILL.md` carries the 6-level
pyramid, test-case design, coverage matrix, and run strategy.
This file is reference material for format details, eval
methodology, and the retest gate.

## Test-plan format

Fields per TC: level, type (positive / negative / boundary + AC
ref), input, expectation, verification.

```markdown
# Test plan: <task / spec title>
Derived from: <spec ref> | Level coverage: L0, L1, L2

### TC-001: <description>
- Level: L2 (unit) | Type: positive (AC-1)
- Input: <concrete> | Expectation: <concrete> | Verification: <how>
```

## Skeleton format

```python
# TC-001 (AC-1, L2 unit, positive) | INFRA: none
def test_crud_roundtrip():
    """AC-1: CRUD create → get → update → delete roundtrip."""
    pytest.skip("SKELETON — implementation pending")
```

**INFRA values:** `none`, `Postgres`, `Ollama`, `NATS`, `Neo4j`,
`Redis`, `Docker`.

## Execution order

**MUST on >5 TCs:** cluster by sub-task dependency. Red → green
→ refactor per cluster.

## Eval methodology

Gate inside the spec process (step 3e). Tests spec assumptions
with code against real infra, before implementation.

**Hypothesis types:** API behaviour · schema compatibility ·
performance (with a threshold!) · infra capability · config
behaviour · interop.

### Eval-script format

Path: `tests/eval/<task-id>/test_eval_<slug>.py`. Marker:
`@pytest.mark.eval`. Docstring: hypothesis, task ID,
`spec_version`. INFRA header. Minimal — only check the
hypothesis.

```python
# INFRA: Postgres, Ollama
"""Hypothesis: add() accepts custom DataPoint subclasses. Task: 050 | v1"""
@pytest.mark.eval
async def test_cognee_accepts_custom_datapoint():
    assert result.status == "success"
```

### Eval classification

- **GO** — hypothesis confirmed.
- **ADAPT** — partly confirmed; new constraints / ACs / failure
  modes go into the spec.
- **NO-GO** — refuted; architecture change or drop.

**Aggregate:** all GO → GO. ≥1 ADAPT → ADAPT. ≥1 NO-GO → NO-GO.

Eval scripts stay persistent in `tests/eval/` — an assumption
regression suite.

## Test-first detail

Skeletons BEFORE implementation as a delegation-ready artifact.
`skip("SKELETON")` → assertions (RED) → implement (GREEN) →
refactor.
Green right away = finding (the test isn't testing what the spec
requires).

## Retest gate (required after every fix)

| Fix type | Retest scope |
|---------|--------------|
| Code fix without spec impact | L0 + affected L1 |
| Spec change | L0 + L1 + matrix TCs for the changed AC |
| Framework change | L0 + L1 + L2 smoke |

After retest: update the matrix — eval status, AC quality if
anything shifted.

## Eval-patterns lookup

Domain-specific patterns live in
`skills/testing/eval_patterns/<domain>.md`.
Flow: read the criteria, mark gaps in the matrix, use the
pattern where it fits. No pattern for a domain → skip + note
("No eval pattern for <domain>").

## L4 TESTCASES reference

Full L4 E2E test cases: `tests/TESTCASES.md`. Run on workflow
changes and milestone checks.

## L1 findings store

L1 logic / semantic findings from spec-review passes:
`docs/tasks/l1-testing-pass-findings.md`. Historical collection
for regression verification on process changes.
