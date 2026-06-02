"""Regression tests for plan_engine cycle detection (Kahn's algorithm).

Guards two properties of `plan_engine.validate()`'s CYCLE check:

1. A DUPLICATE `blocked_by` entry (e.g. `blocked_by: [1, 1]`) is NOT a
   real cycle and must NOT raise a phantom CYCLE issue. The original bug:
   the in-degree BUILD loop counted every `blocked_by` occurrence, but the
   DRAIN loop decremented only once per dependent (membership test). The
   asymmetry left the node's in-degree above zero, so it never entered the
   topo-sort queue and was reported as an unvisited "cycle".

2. A REAL cycle (A blocked_by B, B blocked_by A) MUST still raise CYCLE —
   the dedup fix must not mask genuine cycles.

These call the validate() API directly with in-memory Task objects (the
single-repo path keys tasks by int id). We assert only on CYCLE-coded
issues; unrelated milestone/dependency WARN/ERRORs are out of scope.
"""
from __future__ import annotations

import sys
from pathlib import Path

_FRAMEWORK_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_FRAMEWORK_ROOT) not in sys.path:
    sys.path.insert(0, str(_FRAMEWORK_ROOT))

from scripts.plan_engine import Task, validate  # noqa: E402


def _make_task(tid: int, blocked_by: list[int]) -> Task:
    """Schema-complete, terminal-free Task in a real milestone.

    status='pending' (non-terminal) so it participates in the topo sort;
    milestone='' would trip NO_MILESTONE but that's an unrelated ERROR — we
    only ever assert on CYCLE issues, so the milestone value is irrelevant
    to these tests. We still give it one for realism.
    """
    return Task.from_dict({
        "id": tid,
        "title": f"task {tid}",
        "status": "pending",
        "milestone": "m1",
        "blocked_by": blocked_by,
    })


def _cycle_issues(issues) -> list:
    return [i for i in issues if i.check == "CYCLE"]


def test_duplicate_blocked_by_is_not_a_phantom_cycle():
    """RED-first: task 2 blocked_by [1, 1] (duplicate, NO cycle).

    With the build/drain asymmetry, in_deg[2] inflates to 2, the drain
    decrements it once to 1, node 2 never reaches 0 -> phantom CYCLE.
    After the `set()` dedup fix: no CYCLE issue.
    """
    tasks = {
        1: _make_task(1, blocked_by=[]),
        2: _make_task(2, blocked_by=[1, 1]),  # duplicate dep, not a cycle
    }
    issues = validate(tasks, milestones={})
    cycles = _cycle_issues(issues)
    assert cycles == [], (
        "duplicate blocked_by must NOT produce a phantom CYCLE; "
        f"got: {[i.detail for i in cycles]}"
    )


def test_real_cycle_still_detected():
    """Guard: A blocked_by B, B blocked_by A -> CYCLE must still fire."""
    tasks = {
        1: _make_task(1, blocked_by=[2]),
        2: _make_task(2, blocked_by=[1]),
    }
    issues = validate(tasks, milestones={})
    cycles = _cycle_issues(issues)
    assert len(cycles) == 1, (
        "a real 2-node cycle must still be detected as exactly one CYCLE issue; "
        f"got: {[i.detail for i in cycles]}"
    )
    assert cycles[0].severity == "ERROR"
