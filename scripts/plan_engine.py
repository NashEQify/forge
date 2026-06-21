#!/usr/bin/env python3
"""
plan_engine.py — Computed planning layer for forge consumers.

Reads docs/tasks/*.yaml + docs/plan.yaml, builds DAGs,
computes milestone status, critical path, next actions.

Spec: docs/specs/planning-system.md v0.2

Usage:
    python3 scripts/plan_engine.py --boot
    python3 scripts/plan_engine.py --status
    python3 scripts/plan_engine.py --next [--limit N]
    python3 scripts/plan_engine.py --critical-path
    python3 scripts/plan_engine.py --check [MILESTONE]
    python3 scripts/plan_engine.py --after TASK_ID
    python3 scripts/plan_engine.py --dashboard-json
    python3 scripts/plan_engine.py --validate
    python3 scripts/plan_engine.py --spec-pipeline

Structure: this file is the thin CLI entry + public re-export shim. The engine
bodies live in the sibling ``_plan_engine`` package (core / loading / compute /
validation / rendering). ``import plan_engine`` and
``python3 scripts/plan_engine.py`` both resolve to THIS module, so the public
library surface and every mechanical CLI caller stay byte-identical.
"""

from __future__ import annotations

import argparse
import os
import sys
from types import ModuleType as _ModuleType

# Ensure the engine's own directory (scripts/) is importable so the sibling
# ``_plan_engine`` package resolves whether we are run as a script
# (python3 scripts/plan_engine.py) or imported as a library (import plan_engine
# after sys.path.insert(scripts_dir), as generate-dashboard.py does).
_SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
if _SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, _SCRIPTS_DIR)

try:
    import yaml
except ImportError:
    # Auto-relaunch via framework venv if available — handles PEP-668-protected
    # system Python (brew etc.) where pip install needs --break-system-packages.
    # Discriminator: sys.prefix points into .venv when running under venv python.
    _framework_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    _venv_prefix = os.path.join(_framework_root, ".venv")
    _venv_python = os.path.join(_venv_prefix, "bin", "python3")
    if os.path.exists(_venv_python) and not sys.prefix.startswith(_venv_prefix):
        os.execv(_venv_python, [_venv_python] + sys.argv)
    print("ERROR: PyYAML required. Install via:", file=sys.stderr)
    print(f"  python3 -m venv {_venv_prefix} && {_venv_prefix}/bin/pip install pyyaml", file=sys.stderr)
    sys.exit(1)

from glob import glob  # noqa: E402,F401  (re-export: legacy callers)
from pathlib import Path  # noqa: E402

# loading is used by the rebind seam below; compute / rendering / validation are
# re-exported as namespaced submodules (plan_engine.compute.X) for parity with
# the flat function re-exports — part of the public surface, not dead imports.
from _plan_engine import compute, loading, rendering, validation  # noqa: E402,F401
from _plan_engine.core import (  # noqa: E402,F401
    FRAMEWORK_ROOT,
    DEFAULT_EFFORT_WEIGHT,
    EFFORT_WEIGHTS,
    KNOWN_TASK_STATUSES,
    NONTERMINAL_STATUSES,
    SPEC_PHASE_ENUM,
    SPEC_PHASE_TRANSITIONS,
    TERMINAL_STATUSES,
    Milestone,
    Phase,
    PhaseProgress,
    PlanResult,
    Task,
    ValidationIssue,
    _emit_warn,
)

# ---------------------------------------------------------------------------
# Public re-export surface: the functions + 4 project globals consumed by the
# library callers (generate-dashboard.py is the principal one). The 4 globals
# are re-exported as late-bound module attributes via the rebind seam below;
# functions are bound here so ``plan_engine.<fn>`` keeps resolving.
# ---------------------------------------------------------------------------
from _plan_engine.loading import (  # noqa: E402,F401
    AggregateResult,
    GateCondition,
    discover_projects,
    load_aggregated,
    load_archived_task_ids,
    load_archived_tasks,
    load_plan,
    load_tasks,
)
from _plan_engine.compute import (  # noqa: E402,F401
    assign_tasks_to_milestones,
    compute_active_milestone_task_chain,
    compute_blocking_score,
    compute_critical_path,
    compute_milestone_dependents,
    compute_milestone_status,
    compute_next_actions,
    compute_phase_progress,
)
from _plan_engine.validation import (  # noqa: E402,F401
    validate,
    validate_task_schema_conformance,
)
from _plan_engine.rendering import (  # noqa: E402,F401
    fmt_after,
    fmt_boot,
    fmt_check,
    fmt_critical_path,
    fmt_dashboard_json,
    fmt_next,
    fmt_spec_pipeline,
    fmt_status,
    fmt_validate,
)

# Autonomy-table consistency check: relocated out of the plan engine to the
# consistency tooling (it validates framework governance docs, not plan-DAG
# state). Re-exported here so assemble() / --validate keep calling it and the
# pre-commit PLAN-VALIDATE BLOCK still exercises it via the unchanged path.
from consistency_check import validate_autonomy_consistency  # noqa: E402,F401


# ---------------------------------------------------------------------------
# Global-rebind seam.
#
# Four project-scoped globals (PROJECT_ROOT / TASKS_DIR / PLAN_PATH / REPO_ROOT)
# live canonically on the loading module; every engine routine reads them via
# attribute access (loading.PROJECT_ROOT, late-bound) so a --project-root or a
# per-repo swap takes effect for all of them.
#
# A plain module object cannot intercept ``plan_engine.PROJECT_ROOT = x``
# (assignment always sets a real attribute and a later read returns that stale
# copy, NOT loading's). generate-dashboard.py rebinds and reads back exactly
# this way (_swap_plan_engine_globals, then library calls that read loading.*),
# so we must keep the two in lockstep. The robust mechanism is to give this
# module a custom type whose __setattr__ mirrors the four names into loading and
# whose __getattr__ reads them back from loading. Reads and writes of the seam
# then ALWAYS resolve through loading — single source of truth, no stale copy.
# ---------------------------------------------------------------------------
_REBIND_GLOBALS = ("PROJECT_ROOT", "TASKS_DIR", "PLAN_PATH", "REPO_ROOT")


class _PlanEngineModule(_ModuleType):
    """Module type mirroring the four rebindable globals to ``loading``."""

    def __getattr__(self, name):  # only consulted for names not in __dict__
        if name in _REBIND_GLOBALS:
            return getattr(loading, name)
        raise AttributeError(f"module {self.__name__!r} has no attribute {name!r}")

    def __setattr__(self, name, value):
        if name in _REBIND_GLOBALS:
            setattr(loading, name, value)
        else:
            super().__setattr__(name, value)


sys.modules[__name__].__class__ = _PlanEngineModule


def _configure_stdio_for_windows() -> None:
    """Avoid UnicodeEncodeError on Windows consoles (e.g. cp1252)."""
    if os.name != "nt":
        return
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            try:
                reconfigure(errors="replace")
            except OSError:
                # Keep default stream config if runtime forbids reconfigure.
                pass


def assemble(args):
    """Run the load -> compute -> validate pipeline. Returns everything the
    render dispatch consumes. The --validate <id> short-circuit and the
    --project-root override stay in main() (they run before / instead of this
    pipeline)."""
    # Load
    if args.aggregate:
        # Multi-Repo Aggregate Mode
        aggregate = load_aggregated(projects_arg=args.projects)
        tasks = aggregate.tasks
        milestones = aggregate.milestones
        target = aggregate.target
        north_star = aggregate.north_star
        op_intent = aggregate.operational_intent
        phases_for_json = []  # phases are per-repo; aggregate doesn't merge them
    else:
        tasks = load_tasks()
        plan = load_plan()
        milestones, target, north_star, op_intent = plan
        phases_for_json = plan.phases

    assign_tasks_to_milestones(tasks, milestones)
    compute_milestone_dependents(milestones)
    compute_milestone_status(milestones, tasks)

    # Load archived task IDs fuer Silent-Pass von BROKEN_DEP.
    # Aggregate-Mode sammelt per-repo archived_ids
    # in load_aggregated und stellt sie als namespaced set[str] bereit.
    archived_ids: set
    if args.aggregate:
        archived_ids = aggregate.archived_ids
    else:
        archived_ids = load_archived_task_ids(loading.PROJECT_ROOT)

    # Pass plan_data fuer 4-stufigen Critical-Path-Lookup.
    plan_data_for_cp: dict = {}
    if not args.aggregate and loading.PLAN_PATH.exists():
        try:
            plan_data_for_cp = yaml.safe_load(loading.PLAN_PATH.read_text(encoding="utf-8")) or {}
        except (yaml.YAMLError, OSError, ValueError):
            plan_data_for_cp = {}
        if not isinstance(plan_data_for_cp, dict):
            plan_data_for_cp = {}

    # Compute
    critical_path = compute_critical_path(tasks, milestones, target, plan_data_for_cp)
    blocking_scores = compute_blocking_score(tasks, milestones)
    issues = validate(tasks, milestones, archived_ids=archived_ids)
    # Autonomy-Consistency-Checks.
    # Additiv — keine Beeinflussung bestehender Task/Milestone-Checks.
    # Skipped in aggregate mode (operates on FRAMEWORK_ROOT, not per-repo).
    if not args.aggregate:
        issues.extend(validate_autonomy_consistency())
    else:
        # surface aggregate-mode warnings (stale external refs, etc.)
        for w in aggregate.warnings:
            issues.append(ValidationIssue(
                "AGGREGATE_WARN", "WARN", detail=w))

    # full-tree task-schema conformance. Additive and scoped
    # to the --validate full path ONLY. It is intentionally NOT fed into
    # the shared issue stream that --boot / --dashboard-json render: the
    # forge_dev + consumer trees are pre-backfill, so schema WARNs
    # would otherwise inject a WARNINGS block into the boot-critical path
    # before strict_after_backfill is flipped — exactly the repo-brick
    # the strict-after-backfill ordering exists to prevent. WARN-first
    # calibration keeps exit-code 0 on --validate (PASS) while still
    # surfacing the drift. Per-repo in aggregate mode.
    if args.validate == "__full__":
        if args.aggregate:
            for repo_name, repo_root in discover_projects(args.projects):
                for si in validate_task_schema_conformance(
                        project_root=repo_root):
                    si.detail = f"[{repo_name}] {si.detail}"
                    issues.append(si)
        else:
            issues.extend(validate_task_schema_conformance())
    next_actions = compute_next_actions(tasks, milestones, critical_path, blocking_scores,
                                        target=target, limit=args.limit)
    return (tasks, milestones, target, north_star, op_intent, critical_path,
            blocking_scores, next_actions, issues, phases_for_json)


def main():
    _configure_stdio_for_windows()

    parser = argparse.ArgumentParser(description="forge Plan Engine")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--boot", action="store_true", help="Full boot hook")
    group.add_argument("--status", action="store_true", help="Milestone overview")
    group.add_argument("--next", action="store_true", help="Next actions")
    group.add_argument("--critical-path", action="store_true", help="Critical path")
    group.add_argument("--check", nargs="?", const="__all__", help="Gate check")
    group.add_argument("--after", type=str, help="What unblocks after task ID? "
                       "(int in single-repo, 'repo#id' in aggregate mode)")
    group.add_argument("--dashboard-json", action="store_true", help="JSON for dashboard")
    group.add_argument(
        "--validate", nargs="?", const="__full__", default=None,
        metavar="TASK_ID",
        help="Consistency check (no arg = full tree, unchanged exit-code "
             "contract). With <id>: single-task schema-only check of "
             "docs/tasks/<id>.yaml (no milestone/cycle/cross-repo), "
             "exit 0/1 on schema ERROR.")
    group.add_argument("--spec-pipeline", action="store_true",
                       help="Spec review pipeline status")
    parser.add_argument("--limit", type=int, default=10, help="Limit for --next")
    parser.add_argument(
        "--project-root",
        type=str,
        default=None,
        help="Override PROJECT_ROOT (where docs/tasks + docs/plan.yaml live). "
             "Takes precedence over BUDDY_PROJECT_ROOT env-var.",
    )
    # Multi-Repo Aggregation
    parser.add_argument(
        "--aggregate",
        action="store_true",
        help="Multi-repo aggregate mode. Scans multiple project repos "
             "and builds a unified view with namespaced IDs <repo>#<id>.",
    )
    parser.add_argument(
        "--projects",
        type=str,
        default=None,
        help="Comma-separated list of project repos for --aggregate "
             "mode. Each entry can be a repo name (resolved against $PROJECTS_DIR) "
             "or an absolute/relative path. Default: auto-discovery in "
             "$PROJECTS_DIR (~/projects by default).",
    )
    args = parser.parse_args()

    # explicit --project-root override. Rebinds the project-scoped globals on
    # the loading module (the single canonical home) so load_tasks/load_plan +
    # all GateCondition.check calls resolve against the new root.
    if args.project_root:
        loading.PROJECT_ROOT = Path(args.project_root).resolve()
        loading.TASKS_DIR = loading.PROJECT_ROOT / "docs" / "tasks"
        loading.PLAN_PATH = loading.PROJECT_ROOT / "docs" / "plan.yaml"
        loading.REPO_ROOT = loading.PROJECT_ROOT  # keep back-compat alias in sync

    # single-id schema-only mode. `--validate <id>` short-
    # circuits BEFORE the full load — no milestone / cycle / cross-repo.
    # Exit 0/1 strictly on schema ERROR (calibration applies: vocab /
    # missing-required are WARN while strict_after_backfill is false, so
    # exit 0). `--validate` without an id stays full-tree (unchanged).
    if args.validate is not None and args.validate != "__full__":
        try:
            single_id = int(args.validate)
        except (TypeError, ValueError):
            print(f"ERROR: --validate expects an integer task id, got "
                  f"{args.validate!r}", file=sys.stderr)
            sys.exit(2)
        # (locked): a task id is a positive int. <= 0 is an
        # argv error on the SAME path as a non-int value (exit 2) — never
        # a silent CLEAN exit 0 (the pre-fix false-PASS on `--validate -1`).
        if single_id <= 0:
            print(f"ERROR: --validate expects a positive integer task id, "
                  f"got {single_id}", file=sys.stderr)
            sys.exit(2)
        s_issues = validate_task_schema_conformance(single_id=single_id)
        output, clean = fmt_validate(s_issues)
        print(output)
        sys.exit(0 if clean else 1)

    (tasks, milestones, target, north_star, op_intent, critical_path,
     blocking_scores, next_actions, issues, phases_for_json) = assemble(args)
    # Output
    if args.boot:
        print(fmt_boot(tasks, milestones, target, north_star, op_intent,
                        critical_path, blocking_scores, next_actions, issues,
                        aggregate=args.aggregate))
    elif args.status:
        print(fmt_status(tasks, milestones, aggregate=args.aggregate))
    elif args.next:
        print(fmt_next(tasks, next_actions, critical_path, blocking_scores))
    elif args.critical_path:
        print(fmt_critical_path(tasks, critical_path, target, milestones))
    elif args.check is not None:
        key = None if args.check == "__all__" else args.check
        output, all_pass = fmt_check(milestones, tasks, key)
        print(output)
        sys.exit(0 if all_pass else 1)
    elif args.after is not None:
        # accept int or "repo#id" for --after
        after_key: object = args.after
        import contextlib
        with contextlib.suppress(TypeError, ValueError):
            after_key = int(args.after)
        print(fmt_after(tasks, milestones, after_key, blocking_scores))
    elif args.dashboard_json:
        print(fmt_dashboard_json(tasks, milestones, target, north_star, op_intent,
                                  critical_path, blocking_scores, next_actions, issues,
                                  phases=phases_for_json, aggregate=args.aggregate))
    elif args.validate:
        output, clean = fmt_validate(issues)
        print(output)
        sys.exit(0 if clean else 1)
    elif args.spec_pipeline:
        print(fmt_spec_pipeline(tasks))


if __name__ == "__main__":
    main()
