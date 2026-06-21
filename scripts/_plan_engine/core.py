"""_plan_engine.core — dependency-free data leaf.

Pure data model + shared constants for the plan engine. Imports nothing from
the rest of the package, so compute / validation / rendering / loading can all
depend on it one-directionally without an import cycle.

Split out of the former monolithic scripts/plan_engine.py; the public surface
is re-exported from scripts/plan_engine.py.
"""

from __future__ import annotations

import warnings
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    # GateCondition carries subprocess/file IO (.check) and therefore lives in
    # loading, not this pure-data leaf. Milestone.gate is annotated with it, but
    # `from __future__ import annotations` keeps that annotation a lazy string,
    # so no runtime import (and no cycle) is created — the import is for static
    # checkers only.
    from _plan_engine.loading import GateCondition


# FRAMEWORK_ROOT — where the framework checkout lives. This module sits at
# scripts/_plan_engine/core.py, so the framework root is THREE parents up
# (core.py -> _plan_engine -> scripts -> <framework-root>), one deeper than the
# former top-level scripts/plan_engine.py which used .parent.parent.
FRAMEWORK_ROOT = Path(__file__).resolve().parent.parent.parent


def _emit_warn(msg: str, stacklevel: int = 3) -> None:
    """zentraler Wrapper fuer warnings.warn mit konsistentem
    stacklevel (B028 ruff-clean). Caller ruft mit stacklevel=2 wenn er
    direkt aus User-Code-Pfad warnt; default 3 reflektiert Aufrufer-Stack."""
    warnings.warn(msg, stacklevel=stacklevel)


EFFORT_WEIGHTS = {"S": 1, "M": 3, "L": 8, "XL": 20}
DEFAULT_EFFORT_WEIGHT = 3  # M equivalent

TERMINAL_STATUSES = {"done", "superseded", "wontfix", "absorbed"}
# The full sanctioned task-status vocabulary (task_status_update SKILL §enum).
# The critical-path / next-actions core keys on the literal `pending`, so a
# status outside this set is silently treated as non-pending and drops off the
# live frontier with no signal — KNOWN_TASK_STATUSES lets validate() flag it.
NONTERMINAL_STATUSES = {"pending", "in_progress", "blocked"}
KNOWN_TASK_STATUSES = TERMINAL_STATUSES | NONTERMINAL_STATUSES

SPEC_PHASE_ENUM = {"raw", "reviewing", "fixing", "ready"}
SPEC_PHASE_TRANSITIONS: dict[str, set[str]] = {
    "raw": {"reviewing"},
    "reviewing": {"fixing", "ready"},
    "fixing": {"reviewing"},
    "ready": set(),
}


@dataclass
class Task:
    id: int
    title: str
    status: str
    milestone: str
    blocked_by: list = field(default_factory=list)  # list[int] (single-repo) or list[TaskKey] (aggregate)
    effort: str = "M"
    area: str = ""
    assignee: str = ""
    spec_ref: str = ""
    board_result: str = ""
    readiness: str = ""
    summary: str = ""
    blocked_by_external: list = field(default_factory=list)
    created: str = ""
    updated: str = ""
    intent_chain: dict = field(default_factory=dict)
    notes: str = ""
    note: str = ""
    blocking_note: str = ""
    sub_tasks: list = field(default_factory=list)
    parent_task: int = 0
    deploy_gate: str = ""
    closed: str = ""
    workflow_template: str = ""
    ac_schema_validation: str = ""
    spec_version: str = ""
    spec_states: dict[str, dict] = field(default_factory=dict)
    # Namespace marker for aggregate-mode. Empty string in single-repo.
    _repo: str = ""
    # Tracks unresolved blocked_by_external entries that couldn't be
    # resolved in aggregate-mode (repo missing or task not found). Used as an
    # additional "permanently blocked" signal alongside legacy simple-list entries.
    _unresolved_external: list = field(default_factory=list)
    # Sub-Tags fuer POST-MVP Mass-Migration.
    # legacy_milestone_key: Pre-Greenfield-Key, behalten zur Re-Klassifizierung.
    # migration_note: Menschenlesbarer Migrations-Audit-Trail.
    legacy_milestone_key: str = ""
    migration_note: str = ""

    @classmethod
    def from_dict(cls, data: dict) -> Task:
        """Build Task from yaml-loaded dict. Type-Coercion-disziplin:
        - int-fields: int(raw) with ValueError-fallback
        - str-fields: explicit None-Check -> "" default
        - list-fields: isinstance-check, sonst [] default

        Used by tests + load_tasks-callers. Mirrors the inline construction
        in load_tasks but with explicit type-safety fuer Sub-Tags."""
        tid_raw = data.get("id")
        try:
            tid = int(tid_raw) if tid_raw is not None else 0
        except (TypeError, ValueError):
            tid = 0

        bb = data.get("blocked_by") or []
        if isinstance(bb, int):
            bb = [bb]
        if not isinstance(bb, list):
            bb = []
        bb = [int(x) if isinstance(x, str) and x.isdigit() else x
              for x in bb if x is not None]
        bb = [x for x in bb if isinstance(x, int)]

        bbe = data.get("blocked_by_external") or []
        if not isinstance(bbe, list):
            bbe = []

        spec_states = data.get("spec_states")
        if not isinstance(spec_states, dict):
            spec_states = {}

        def _str(key: str) -> str:
            v = data.get(key)
            return str(v) if v is not None else ""

        intent_chain_raw = data.get("intent_chain")
        intent_chain: dict = intent_chain_raw if isinstance(intent_chain_raw, dict) else {}
        sub_tasks_raw = data.get("sub_tasks")
        sub_tasks: list = sub_tasks_raw if isinstance(sub_tasks_raw, list) else []
        parent_task_raw = data.get("parent_task")
        parent_task: int = parent_task_raw if isinstance(parent_task_raw, int) else 0

        return cls(
            id=tid,
            title=_str("title"),
            status=_str("status") or "pending",
            milestone=_str("milestone"),
            blocked_by=bb,
            effort=_str("effort") or "M",
            area=_str("area"),
            assignee=_str("assignee"),
            spec_ref=_str("spec_ref"),
            board_result=_str("board_result"),
            readiness=_str("readiness"),
            summary=_str("summary"),
            blocked_by_external=bbe,
            created=_str("created"),
            updated=_str("updated"),
            intent_chain=intent_chain,
            notes=_str("notes"),
            note=_str("note"),
            blocking_note=_str("blocking_note"),
            sub_tasks=sub_tasks,
            parent_task=parent_task,
            deploy_gate=_str("deploy_gate"),
            closed=_str("closed"),
            workflow_template=_str("workflow_template"),
            ac_schema_validation=_str("ac_schema_validation"),
            spec_version=_str("spec_version"),
            spec_states=spec_states,
            legacy_milestone_key=_str("legacy_milestone_key"),
            migration_note=_str("migration_note"),
        )

    @property
    def effort_weight(self) -> int:
        return EFFORT_WEIGHTS.get(self.effort, DEFAULT_EFFORT_WEIGHT)

    @property
    def is_done(self) -> bool:
        return self.status == "done"

    @property
    def is_terminal(self) -> bool:
        return self.status in TERMINAL_STATUSES

    @property
    def has_external_deps(self) -> bool:
        """True if task has unresolved external deps that block it.

        In single-repo mode: any non-empty blocked_by_external entry blocks
        (both legacy simple-list and new dict-form entries are treated as
        unresolved).

        In aggregate mode: only entries that couldn't be resolved (stored in
        _unresolved_external) count as blockers. Resolved dict-form entries
        have been merged into blocked_by during load and are handled by the
        normal dep-resolution path.
        """
        if self._repo:
            # Aggregate mode: only unresolved externals still block. Legacy
            # simple-list entries are always unresolved (no resolution semantics
            # for strings), so they stay in _unresolved_external.
            return bool(self._unresolved_external)
        return bool(self.blocked_by_external)

    @property
    def key(self):
        """Canonical dict key. Int in single-repo, str '<repo>#<id>' in aggregate."""
        if self._repo:
            return f"{self._repo}#{self.id:03d}"
        return self.id


# TaskKey = int | str (single-repo uses int, aggregate uses '<repo>#<id>').
# Keeping as type alias for readability; Python's dicts handle mixed transparently.
TaskKey = object  # documentation alias only


def _format_tid(t: Task) -> str:
    """Render task ID. Prefixes with '<repo>#' in aggregate mode."""
    if t._repo:
        return f"{t._repo}#{t.id:03d}"
    return f"{t.id:03d}"


def _parse_external_entry(entry) -> tuple[str, int] | None:
    """Parse a blocked_by_external entry.

    Returns (repo, id) tuple if entry is a dict with 'repo' + 'id' keys
    (new schema), None if it's legacy simple-list form (string/placeholder).
    """
    if isinstance(entry, dict) and "repo" in entry and "id" in entry:
        try:
            return (str(entry["repo"]), int(entry["id"]))
        except (TypeError, ValueError):
            return None
    return None


@dataclass
class Phase:
    """A plan phase — grouping concept for milestones (view-only, no gates)."""
    key: str
    title: str
    desc: str = ""
    investor_desc: str = ""  # Fallback: desc
    order: int = 0


@dataclass
class PhaseProgress:
    """Aggregated progress over all milestones belonging to a phase."""
    pct: int                    # 0-100
    tasks_done: int
    tasks_total: int
    remaining_effort: int       # Sum of effort_weight for all non-done tasks


@dataclass
class Milestone:
    key: str
    title: str = ""
    desc: str = ""
    type: str = "milestone"  # milestone or group
    gate: list[GateCondition] = field(default_factory=list)
    requires: list[str] = field(default_factory=list)
    phases: list[str] = field(default_factory=list)       # from plan.yaml
    # Computed
    status: str = ""
    tasks: list = field(default_factory=list)
    dependents: list[str] = field(default_factory=list)    # inverted requires
    # 13 Optional-Felder direkt typisiert in Dataclass mit Default-Werten.
    # KEIN extra-dict, KEIN Hybrid.
    # Plus: id (Synthetic-IDs M1=2100 etc., Doku-only — kein Code-Konsument iteriert per id).
    id: int = 0
    name: str = ""
    feature: str = ""
    capabilities: list[str] = field(default_factory=list)
    specs: list[str] = field(default_factory=list)
    fallback_strategy: list[str] = field(default_factory=list)
    cross_cutting: list[str] = field(default_factory=list)
    parallel_to: list[str] = field(default_factory=list)
    frontend_components: list[str] = field(default_factory=list)
    backend_refactor_components: list[str] = field(default_factory=list)
    app_status_post_milestone: str = ""
    sysadmin_methodology_import: str = ""        # M1.5-only
    infra_audit: str = ""                 # M1.5-only
    gap_ownership_anchor_task: int | None = None  # M1.5-only

    @property
    def is_group(self) -> bool:
        return self.type == "group"


@dataclass
class ValidationIssue:
    check: str
    severity: str  # ERROR or WARN
    task_id: int | None = None
    milestone_key: str | None = None
    detail: str = ""


@dataclass
class PlanResult:
    """Return type for load_plan(). Backward-compatible with tuple unpacking."""
    milestones: dict[str, Milestone]
    target: str
    north_star: str
    operational_intent: dict
    phases: list[Phase] = field(default_factory=list)

    def __iter__(self):
        """Backward-compatible tuple unpacking for existing callers."""
        return iter((self.milestones, self.target, self.north_star, self.operational_intent))


