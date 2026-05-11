"""Regression tests for workflow_engine drift-tolerance fixes.

Covers Task-340 items:
  - FW-001: find_next_step KeyError on workflow.yaml-drift (new step in spec,
            absent from existing state-file).
  - F-100 : {state_file} variable unresolved post-creation (state-file
            created mid-workflow, --start could not discover it).
  - FW-007: completion-check pre-fulfilled idempotency (deterministic step
            with file-based check that already passes should auto-complete
            instead of demanding manual --complete).

Each test patches workflow_engine.PROJECT_ROOT + STATE_DIR onto a tmp_path
so production state-files are not touched.
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

import pytest

# Make the framework checkout importable regardless of pytest cwd.
_FRAMEWORK_ROOT = Path(__file__).resolve().parent.parent
if str(_FRAMEWORK_ROOT) not in sys.path:
    sys.path.insert(0, str(_FRAMEWORK_ROOT))

from scripts import workflow_engine as we  # noqa: E402


@pytest.fixture
def isolated_project(tmp_path, monkeypatch):
    """Redirect PROJECT_ROOT and STATE_DIR onto tmp_path for each test."""
    state_dir = tmp_path / ".workflow-state"
    state_dir.mkdir()
    archive_dir = state_dir / "archive"
    archive_dir.mkdir()

    monkeypatch.setattr(we, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(we, "STATE_DIR", state_dir)
    monkeypatch.setattr(we, "ARCHIVE_DIR", archive_dir)
    monkeypatch.setattr(we, "REPO_ROOT", tmp_path)
    return tmp_path


def _make_workflow_def(steps):
    """Build a minimal workflow_def dict with the given step specs.

    Each entry of `steps` is a dict that becomes one step. The id is the
    `id` key. Other keys (category, completion, depends_on, ...) pass
    through verbatim.
    """
    return {"name": "test-workflow", "version": "1", "steps": list(steps)}


# ---------------------------------------------------------------------------
# FW-001: drift-tolerance — workflow.yaml grew a step, state did not.
# ---------------------------------------------------------------------------


def test_fw_001_find_next_step_tolerates_workflow_drift(isolated_project):
    """State has a, b complete + c pending. workflow_def adds d.

    find_next_step must NOT KeyError on 'd' (was line 726 pre-fix). It
    should return 'c' (first non-terminal) and leave 'd' as PENDING in the
    merged state.
    """
    workflow_def = _make_workflow_def(
        [
            {"id": "a", "category": "manual"},
            {"id": "b", "category": "manual"},
            {"id": "c", "category": "manual"},
            {"id": "d", "category": "manual"},  # NEW — absent from state
        ]
    )

    state = {
        "schema_version": "2",
        "workflow": "test-workflow",
        "workflow_id": "test-wf-001",
        "task_id": None,
        "started": we._utcnow(),
        "current_step": "c",
        "variables": {},
        "steps": {
            "a": {"status": we.STATUS_COMPLETE},
            "b": {"status": we.STATUS_COMPLETE},
            "c": {"status": we.STATUS_PENDING},
            # 'd' deliberately missing
        },
        "force_count": 0,
    }

    next_step = we.find_next_step(state, workflow_def)

    assert next_step == "c", f"expected 'c' as next actionable step, got {next_step!r}"
    assert "d" in state["steps"], "drift-merge did not add 'd' to state"
    assert state["steps"]["d"]["status"] == we.STATUS_PENDING, (
        f"expected merged 'd' to be PENDING, got {state['steps']['d']!r}"
    )
    # Sanity: 'c' became in_progress (activation succeeded without KeyError).
    assert state["steps"]["c"]["status"] == we.STATUS_IN_PROGRESS


# ---------------------------------------------------------------------------
# F-100: lazy state_file re-discovery.
# ---------------------------------------------------------------------------


def test_f_100_lazy_state_file_rediscovery(isolated_project):
    """state_file is empty at --start; mid-workflow a docs/solve/*.md is
    created. find_next_step must re-discover and populate variables.
    """
    tmp_path = isolated_project
    task_id = 999

    # Pre-create the workflow_def with a single manual step so find_next_step
    # has something to iterate. The lazy-discovery branch runs unconditionally
    # at the top of find_next_step (before the activation loop).
    workflow_def = _make_workflow_def(
        [
            {"id": "specify", "category": "manual"},
        ]
    )

    state = {
        "schema_version": "2",
        "workflow": "build-standard",
        "workflow_id": "test-wf-100",
        "task_id": task_id,
        "started": we._utcnow(),
        "current_step": "specify",
        "variables": {"task_id": str(task_id), "state_file": ""},
        "steps": {"specify": {"status": we.STATUS_PENDING}},
        "force_count": 0,
    }

    # NOW (post-state-init) the state file appears on disk.
    solve_dir = tmp_path / "docs" / "solve"
    solve_dir.mkdir(parents=True)
    state_md = solve_dir / "2026-05-03-task-999-test.md"
    state_md.write_text("# Task 999 state\n", encoding="utf-8")

    we.find_next_step(state, workflow_def)

    discovered = state["variables"].get("state_file")
    assert discovered, "lazy re-discovery did not populate state_file"
    assert discovered.endswith("2026-05-03-task-999-test.md"), (
        f"unexpected discovered state_file path: {discovered!r}"
    )


def test_f_100_lazy_rediscovery_noop_when_already_set(isolated_project):
    """If variables['state_file'] is already set, lazy discovery must NOT
    overwrite it — protects against fixed-up paths being clobbered.
    """
    workflow_def = _make_workflow_def(
        [
            {"id": "specify", "category": "manual"},
        ]
    )
    preexisting = "docs/solve/preset-path.md"
    state = {
        "schema_version": "2",
        "workflow": "build-standard",
        "workflow_id": "test-wf-100b",
        "task_id": 999,
        "started": we._utcnow(),
        "current_step": "specify",
        "variables": {"task_id": "999", "state_file": preexisting},
        "steps": {"specify": {"status": we.STATUS_PENDING}},
        "force_count": 0,
    }

    we.find_next_step(state, workflow_def)

    assert state["variables"]["state_file"] == preexisting, (
        "lazy re-discovery clobbered an already-set state_file"
    )


# ---------------------------------------------------------------------------
# FW-007: deterministic step pre-fulfilled → auto-complete.
# ---------------------------------------------------------------------------


def test_fw_007_pre_fulfilled_deterministic_step_auto_completes(isolated_project):
    """Step 'gate-file' has completion `test -f docs/tasks/999-gates.yaml`.

    The file is pre-created. find_next_step must mark the step COMPLETE
    (auto) and advance to the next step instead of activating it.
    """
    tmp_path = isolated_project

    # Pre-create the artefact that satisfies the completion check.
    tasks_dir = tmp_path / "docs" / "tasks"
    tasks_dir.mkdir(parents=True)
    (tasks_dir / "999-gates.yaml").write_text("gates: []\n", encoding="utf-8")

    workflow_def = _make_workflow_def(
        [
            {
                "id": "gate-file",
                "category": "deterministic",
                "completion": {
                    "type": "exit_code",
                    "command": "test -f docs/tasks/{task_id}-gates.yaml",
                },
            },
            {
                "id": "next-step",
                "category": "manual",
            },
        ]
    )

    state = {
        "schema_version": "2",
        "workflow": "build-standard",
        "workflow_id": "test-wf-007",
        "task_id": 999,
        "started": we._utcnow(),
        "current_step": "gate-file",
        "variables": {"task_id": "999"},
        "steps": {
            "gate-file": {"status": we.STATUS_PENDING},
            "next-step": {"status": we.STATUS_PENDING},
        },
        "force_count": 0,
    }

    next_step = we.find_next_step(state, workflow_def)

    assert state["steps"]["gate-file"]["status"] == we.STATUS_COMPLETE, (
        f"expected 'gate-file' to be auto-completed, got "
        f"{state['steps']['gate-file']!r}"
    )
    evidence = state["steps"]["gate-file"].get("evidence", "")
    assert "auto-complete" in evidence, (
        f"expected auto-complete evidence marker, got: {evidence!r}"
    )
    assert next_step == "next-step", (
        f"expected engine to advance to 'next-step', got {next_step!r}"
    )
    assert state["steps"]["next-step"]["status"] == we.STATUS_IN_PROGRESS


def test_fw_007_manual_step_never_auto_completes(isolated_project):
    """A manual-category step must not be auto-completed even if some
    accidental file matches — manual is by definition not auto-checkable.
    """
    workflow_def = _make_workflow_def(
        [
            {
                "id": "manual-step",
                "category": "manual",
                "completion": {"type": "manual"},
            },
        ]
    )
    state = {
        "schema_version": "2",
        "workflow": "test",
        "workflow_id": "test-wf-007b",
        "task_id": None,
        "started": we._utcnow(),
        "current_step": "manual-step",
        "variables": {},
        "steps": {"manual-step": {"status": we.STATUS_PENDING}},
        "force_count": 0,
    }

    next_step = we.find_next_step(state, workflow_def)

    # Manual step still requires explicit --complete; engine activates it
    # rather than skipping it via auto-complete.
    assert next_step == "manual-step"
    assert state["steps"]["manual-step"]["status"] == we.STATUS_IN_PROGRESS


def test_fw_007_failing_check_falls_through_to_activation(isolated_project):
    """Deterministic step whose check does NOT pre-fulfil must fall through
    to normal activation (in_progress) — auto-complete is opportunistic.
    """
    workflow_def = _make_workflow_def(
        [
            {
                "id": "gate-file",
                "category": "deterministic",
                "completion": {
                    "type": "exit_code",
                    "command": "test -f does/not/exist.yaml",
                },
            },
        ]
    )
    state = {
        "schema_version": "2",
        "workflow": "test",
        "workflow_id": "test-wf-007c",
        "task_id": 999,
        "started": we._utcnow(),
        "current_step": "gate-file",
        "variables": {"task_id": "999"},
        "steps": {"gate-file": {"status": we.STATUS_PENDING}},
        "force_count": 0,
    }

    next_step = we.find_next_step(state, workflow_def)

    assert next_step == "gate-file"
    assert state["steps"]["gate-file"]["status"] == we.STATUS_IN_PROGRESS
    # speculative started_at must be replaced by the real activation timestamp,
    # not be the leftover value from the auto-complete probe.
    assert "started_at" in state["steps"]["gate-file"]


# ---------------------------------------------------------------------------
# Task 459 fix: _discover_state_file multi-dir + dual-key (task_ref primary,
# parent_task legacy fallback). Pre-fix searched docs/solve/ only and matched
# parent_task only — Task 459's docs/build/...task_ref:459 fell through.
# ---------------------------------------------------------------------------


def _seed_state_file(
    base: Path, subdir: str, filename: str, frontmatter: dict | None = None
) -> Path:
    wf_dir = base / "docs" / subdir
    wf_dir.mkdir(parents=True, exist_ok=True)
    fp = wf_dir / filename
    body = ""
    if frontmatter is not None:
        fm_lines = "\n".join(f"{k}: {v}" for k, v in frontmatter.items())
        body = f"---\n{fm_lines}\n---\n\n# {filename}\n"
    else:
        body = f"# {filename}\n"
    fp.write_text(body, encoding="utf-8")
    return fp


def test_discover_state_file_finds_build_dir_via_task_ref(isolated_project):
    """Task 459 surface: state-file in docs/build/ with `task_ref: 459` in
    frontmatter. Pre-fix this returned None (Strategy 1 looked for parent_task
    only AND only in docs/solve/). Post-fix: returns the build/ path.
    """
    tmp = isolated_project
    fp = _seed_state_file(
        tmp,
        "build",
        "2026-05-08-task-459-cooperation-hooks-fix.md",
        frontmatter={"workflow": "build", "task_ref": 459},
    )

    discovered = we._discover_state_file(459)

    assert discovered is not None, "expected discover to find build/ state-file"
    assert discovered == str(fp.relative_to(tmp))


def test_discover_state_file_legacy_parent_task_still_works(isolated_project):
    """Backward-compat: pre-Task-459 state-files written with `parent_task:`
    must keep resolving so existing live workflows do not break.
    """
    tmp = isolated_project
    fp = _seed_state_file(
        tmp,
        "solve",
        "2026-05-01-task-300-legacy.md",
        frontmatter={"workflow": "solve", "parent_task": 300},
    )

    discovered = we._discover_state_file(300)

    assert discovered == str(fp.relative_to(tmp))


def test_discover_state_file_task_ref_wins_over_legacy(isolated_project):
    """If two files exist — one with task_ref, one with parent_task pointing
    to a DIFFERENT task — the task_ref match must win for the matching id.
    """
    tmp = isolated_project
    fp_canonical = _seed_state_file(
        tmp,
        "build",
        "2026-05-08-task-700-canonical.md",
        frontmatter={"workflow": "build", "task_ref": 700},
    )
    _seed_state_file(
        tmp,
        "solve",
        "2026-05-01-task-300-other.md",
        frontmatter={"workflow": "solve", "parent_task": 300},
    )

    assert we._discover_state_file(700) == str(fp_canonical.relative_to(tmp))


def test_discover_state_file_searches_multiple_workflow_dirs(isolated_project):
    """Filename Strategy 2 must hit any registered workflow-state directory.
    Seeds a fix/ state-file with no frontmatter — only the filename anchors.
    """
    tmp = isolated_project
    fp = _seed_state_file(tmp, "fix", "2026-05-08-task-555-bug.md")

    discovered = we._discover_state_file(555)

    assert discovered == str(fp.relative_to(tmp))


def test_discover_state_file_returns_none_when_no_match(isolated_project, capsys):
    """No match across all dirs → None + WARNING with the new multi-dir
    diagnostic so users can see Strategy-1+2 both missed.
    """
    tmp = isolated_project
    # Seed an unrelated file so directories exist but task-id does not match.
    _seed_state_file(
        tmp,
        "build",
        "2026-05-08-task-1-other.md",
        frontmatter={"workflow": "build", "task_ref": 1},
    )

    discovered = we._discover_state_file(9999)

    assert discovered is None
    err = capsys.readouterr().err
    assert "WARNING: no state-file found for task 9999" in err
    # New diagnostic should mention the multi-dir search to make the failure
    # mode obvious instead of "looked in solve/ only".
    assert "task_ref" in err
    assert "parent_task" in err


def test_discover_state_file_filename_strategy_avoids_date_collision(isolated_project):
    """Regression: pre-existing fix narrowed Strategy 2 to literal `task-<N>`
    so date components like 2026-05-01 don't false-positive task_id=1.
    Multi-dir change must not regress this guarantee.
    """
    tmp = isolated_project
    # File named with date component but NOT a task-1 file.
    _seed_state_file(tmp, "build", "2026-05-01-feature.md")

    discovered = we._discover_state_file(1)

    assert discovered is None, (
        "Strategy 2 must not match date components — only literal task-<N>"
    )


# ---------------------------------------------------------------------------
# Module import sanity (catches syntax/regression in workflow_engine.py).
# ---------------------------------------------------------------------------


def test_module_imports_cleanly():
    """Re-importing workflow_engine must not raise — guards against
    accidental top-level breakage from the merge.
    """
    importlib.reload(we)
