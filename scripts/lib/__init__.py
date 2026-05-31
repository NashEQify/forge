"""scripts.lib — Shared utilities for forge CLI tools.

This module lives inside the framework (scripts/lib/) and only reads
framework-internal files (workflows/, skills/). The root derived from
`__file__` therefore represents the framework repo, not the project repo —
it points to the forge framework checkout.

Consumers that need PROJECT_ROOT semantics (per-project data like
docs/tasks/, .workflow-state/) must derive their own project root from
BUDDY_PROJECT_ROOT / Path.cwd() — they must not import a "REPO_ROOT" from
scripts.lib.
"""

from __future__ import annotations

from pathlib import Path

FRAMEWORK_ROOT = Path(__file__).resolve().parent.parent.parent
