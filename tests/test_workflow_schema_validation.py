"""Schema validation across every workflow.yaml in the tree.

Catches the cross-file drift class where a workflow.yaml introduces a
step field/value that the engine validator does not yet accept (e.g. a
new `category:` value added without extending `VALID_CATEGORIES`). The
failure mode in production is an engine-side block at workflow start,
in a different repo from the framework — which is hard to root-cause
from the consumer side.

Two layers:
  - test_all_runbook_workflow_yaml_files_validate parameterises over
    every workflow.yaml in `workflows/runbooks/` and asserts the
    schema validator returns no errors.
  - test_valid_categories_set_is_complete asserts the registered
    category values cover every category actually used in the tree.
    Catches the drift even when the offending workflow.yaml is added
    to the tree but no integration run has happened yet.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
import yaml

_FRAMEWORK_ROOT = Path(__file__).resolve().parent.parent
if str(_FRAMEWORK_ROOT) not in sys.path:
    sys.path.insert(0, str(_FRAMEWORK_ROOT))

from scripts.lib.yaml_loader import (  # noqa: E402
    VALID_CATEGORIES,
    load_workflow_yaml,
    validate_workflow_schema,
)

_RUNBOOKS_DIR = _FRAMEWORK_ROOT / "workflows" / "runbooks"


def _all_workflow_yaml_files() -> list[Path]:
    return sorted(_RUNBOOKS_DIR.rglob("workflow.yaml"))


@pytest.mark.parametrize(
    "workflow_path",
    _all_workflow_yaml_files(),
    ids=lambda p: p.relative_to(_FRAMEWORK_ROOT).as_posix(),
)
def test_all_runbook_workflow_yaml_files_validate(workflow_path: Path) -> None:
    """Every runbook workflow.yaml must pass schema validation."""
    data = load_workflow_yaml(workflow_path)
    errors = validate_workflow_schema(data)
    assert not errors, (
        f"Schema errors in {workflow_path.relative_to(_FRAMEWORK_ROOT)}:\n  - "
        + "\n  - ".join(errors)
    )


def test_valid_categories_set_covers_all_used_categories() -> None:
    """Every `category:` value used in the tree must be in VALID_CATEGORIES.

    Drift detection: if a new category value is introduced in any
    workflow.yaml without extending VALID_CATEGORIES, this fails before
    a real workflow run hits the engine block in a consumer repo.
    """
    used: set[str] = set()
    for workflow_path in _all_workflow_yaml_files():
        with workflow_path.open() as fh:
            data = yaml.safe_load(fh) or {}
        for step in data.get("steps", []) or []:
            cat = step.get("category")
            if cat is not None:
                used.add(cat)

    unknown = used - VALID_CATEGORIES
    assert not unknown, (
        f"workflow.yaml uses category values not in VALID_CATEGORIES: "
        f"{sorted(unknown)}. Either extend VALID_CATEGORIES "
        f"({sorted(VALID_CATEGORIES)}) in scripts/lib/yaml_loader.py, "
        f"or change the workflow.yaml step(s) to a registered category."
    )


def test_gate_category_is_registered() -> None:
    """Regression: spec 306 introduced `category: gate` for brief-signoff.

    Keep this category registered so user-approval gate steps continue
    to load. The engine treats `gate` like `content` for completion
    purposes (manual completion only); see VALID_CATEGORIES comment.
    """
    assert "gate" in VALID_CATEGORIES
