"""scripts.lib — Shared utilities for BuddyAI CLI tools.

Task 010 Part L0b: FRAMEWORK_ROOT replaces REPO_ROOT.

This module lives inside the framework (scripts/lib/) and only reads framework-
internal files (workflows/, skills/). The root derived from
`__file__` therefore represents the framework repo, not the project repo. Post
repo-split (Task 010) this will point to ~/projects/forge.

Consumers that need PROJECT_ROOT semantics (per-project data like docs/tasks/,
.workflow-state/) must derive their own project root from BUDDY_PROJECT_ROOT
/ Path.cwd() — they must not import a "REPO_ROOT" from scripts.lib.
"""

from __future__ import annotations

from pathlib import Path

FRAMEWORK_ROOT = Path(__file__).resolve().parent.parent.parent
