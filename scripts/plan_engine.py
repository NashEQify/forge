#!/usr/bin/env python3
"""
plan_engine.py — Computed planning layer for BuddyAI.

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
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import warnings
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from glob import glob
from pathlib import Path


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


def _emit_warn(msg: str, stacklevel: int = 3) -> None:
    """Task 435: zentraler Wrapper fuer warnings.warn mit konsistentem
    stacklevel (B028 ruff-clean). Caller ruft mit stacklevel=2 wenn er
    direkt aus User-Code-Pfad warnt; default 3 reflektiert Aufrufer-Stack."""
    warnings.warn(msg, stacklevel=stacklevel)

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

# Path resolution (Task 010 Part L0 — Pre-Split Refactor)
#
# PROJECT_ROOT   → where the user's docs/tasks/*.yaml and docs/plan.yaml live.
#                  Derived from BUDDY_PROJECT_ROOT env-var, or --project-root
#                  flag, or current working directory. Post-split this is the
#                  product repo (e.g. ~/projects/buddyai).
#
# FRAMEWORK_ROOT → where plan_engine.py itself lives. Framework-internal files
#                  (CLAUDE.md, AGENTS.md, framework/agent-autonomy.md,
#                  agents/buddy/operational.md, etc.) are resolved against
#                  this root. Post-split this is the framework repo
#                  (e.g. ~/projects/forge).
#
# Pre-Split Invariant: when invoked from the BuddyAI monolith root without
# BUDDY_PROJECT_ROOT set, PROJECT_ROOT == FRAMEWORK_ROOT == BuddyAI root,
# so existing behaviour is preserved (regression-free).
PROJECT_ROOT = Path(os.environ.get("BUDDY_PROJECT_ROOT", Path.cwd())).resolve()
FRAMEWORK_ROOT = Path(__file__).resolve().parent.parent

# Back-compat alias: older code-paths still reference REPO_ROOT. It mirrors
# PROJECT_ROOT (the "data" side) which is where task/plan/gate-scripts live.
# Framework-internal reads should use FRAMEWORK_ROOT explicitly.
REPO_ROOT = PROJECT_ROOT

TASKS_DIR = PROJECT_ROOT / "docs" / "tasks"
PLAN_PATH = PROJECT_ROOT / "docs" / "plan.yaml"

EFFORT_WEIGHTS = {"S": 1, "M": 3, "L": 8, "XL": 20}
DEFAULT_EFFORT_WEIGHT = 3  # M equivalent

TERMINAL_STATUSES = {"done", "superseded", "wontfix", "absorbed"}

SPEC_PHASE_ENUM = {"raw", "reviewing", "fixing", "ready"}
SPEC_PHASE_TRANSITIONS: dict[str, set[str]] = {
    "raw": {"reviewing"},
    "reviewing": {"fixing", "ready"},
    "fixing": {"reviewing"},
    "ready": set(),
}


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------

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
    # Task 367: Namespace marker for aggregate-mode. Empty string in single-repo.
    _repo: str = ""
    # Task 367: Tracks unresolved blocked_by_external entries that couldn't be
    # resolved in aggregate-mode (repo missing or task not found). Used as an
    # additional "permanently blocked" signal alongside legacy simple-list entries.
    _unresolved_external: list = field(default_factory=list)
    # Task 435 (F-C-014, AC-A.9): Sub-Tags fuer POST-MVP Mass-Migration.
    # legacy_milestone_key: Pre-Greenfield-Key, behalten zur Re-Klassifizierung.
    # migration_note: Menschenlesbarer Migrations-Audit-Trail.
    legacy_milestone_key: str = ""
    migration_note: str = ""

    @classmethod
    def from_dict(cls, data: dict) -> Task:
        """Build Task from yaml-loaded dict. Type-Coercion-disziplin (F-CA-003):
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
        """Task 367: True if task has unresolved external deps that block it.

        In single-repo mode: any non-empty blocked_by_external entry blocks
        (unchanged from pre-367 behaviour — both legacy simple-list and new
        dict-form entries are treated as unresolved).

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
        """Task 367: Canonical dict key. Int in single-repo, str '<repo>#<id>' in aggregate."""
        if self._repo:
            return f"{self._repo}#{self.id:03d}"
        return self.id


# Task 367: TaskKey = int | str (single-repo uses int, aggregate uses '<repo>#<id>').
# Keeping as type alias for readability; Python's dicts handle mixed transparently.
TaskKey = object  # documentation alias only


def _format_tid(t: Task) -> str:
    """Task 367: Render task ID. Prefixes with '<repo>#' in aggregate mode."""
    if t._repo:
        return f"{t._repo}#{t.id:03d}"
    return f"{t.id:03d}"


def _parse_external_entry(entry) -> tuple[str, int] | None:
    """Task 367: Parse a blocked_by_external entry.

    Returns (repo, id) tuple if entry is a dict with 'repo' + 'id' keys
    (new schema), None if it's legacy simple-list form (string/placeholder).
    """
    if isinstance(entry, dict) and "repo" in entry and "id" in entry:
        try:
            return (str(entry["repo"]), int(entry["id"]))
        except (TypeError, ValueError):
            return None
    return None


# Task 435 (B-2 Lock, F-C-006, Amendment-003):
# Type-Whitelist fuer GateCondition. Bekannte Types werden in check() geroutet,
# unbekannte werfen WARN UNKNOWN_GATE_TYPE in check() (kein Crash).
GATE_TYPE_WHITELIST = {"task", "validate", "coverage", "spec_review", "file", "script"}


@dataclass
class GateCondition:
    type: str
    path: str = ""
    id: int = 0
    want: str = ""
    # Task 435 (Amendment-003): additive Felder fuer Pre-Set-Gates pro feature_milestone.
    # ref:         Beschreibungs-/Reference-String (z.B. "plan_engine clean")
    # preliminary: True -> Gate gibt (True, "preliminary") zurueck (blockiert nicht)
    # desc:        Menschenlesbare Beschreibung
    ref: str = ""
    preliminary: bool = False
    desc: str = ""

    def __post_init__(self) -> None:
        # F-CA-003: explicit Type-Coercion fuer preliminary (yaml liefert bool ODER
        # string). String 'true'/'false' soll zu bool kasten + WARN ausloesen.
        # `True is True` Disziplin verhindert truthy-string-Fallthrough.
        # warnings via _emit_warn
        if not isinstance(self.preliminary, bool):
            raw = self.preliminary
            if isinstance(raw, str):
                if raw.strip().lower() == "true":
                    self.preliminary = True
                else:
                    # 'false', '', anything-else -> False (explicit, not truthy)
                    self.preliminary = False
                _emit_warn(
                    f"GATE_TYPE_MISMATCH: preliminary=string '{raw}' coerced to bool"
                )
            else:
                self.preliminary = bool(raw)
                _emit_warn(
                    f"GATE_TYPE_MISMATCH: preliminary={raw!r} ({type(raw).__name__}) coerced to bool"
                )
        # type must be string (yaml could deliver list)
        if not isinstance(self.type, str):
            _emit_warn(
                f"GATE_TYPE_MUST_BE_STR: type={self.type!r} ({type(self.type).__name__})"
            )
            try:
                self.type = str(self.type)
            except Exception:
                self.type = ""

    def check(self, tasks: dict, milestones: dict | None = None) -> tuple[bool, str]:  # noqa: ARG002
        # Backward-compat: accept (tasks) or (tasks, milestones). milestones-Parameter
        # ist Reserve fuer zukuenftige Cross-Milestone-Gate-Checks.
        # Task 435 (B-2 Lock): preliminary-Gates pass (blockieren Status-Compute nicht).
        if self.preliminary:
            return True, "preliminary"

        if self.type == "task":
            # 2026-05-07: Archive-Awareness. Archivierte Tasks sind per
            # archive-Semantik terminal-done (Frozen Zone WORM-Pattern).
            # Wenn gate `want: done` (default) UND task-id ist archiviert →
            # pass. Konsistent mit Dashboard-archive_done-Set in
            # generate-dashboard.py:1378+. Ohne dieses Verhalten wird jeder
            # Milestone mit archiviertem Gate-Task als ORPHAN klassifiziert.
            want = self.want or "done"
            if want == "done":
                archived_ids = _get_archived_ids_cached()
                if self.id in archived_ids:
                    return True, f"task {self.id} archived (terminal-done)"
            t = tasks.get(self.id)
            if not t:
                return False, f"task {self.id} not found"
            actual = t.status
            # Default-want: 'done' (post-Greenfield Pre-Set-Gates haben kein 'want',
            # nur id+desc — Implementation-Task done == gate pass).
            ok = actual == want
            return ok, f"want={want} have={actual}"
        if self.type == "file":
            matches = glob(str(PROJECT_ROOT / self.path))
            count = len(matches)
            return count > 0, f"{count} match(es)"
        if self.type == "script":
            # Recursion guard: script gates can call plan_engine.py which
            # evaluates all gates again → infinite process spawning.
            # Parent sets _PLAN_ENGINE_ACTIVE in child env; nested calls skip.
            if os.environ.get("_PLAN_ENGINE_ACTIVE"):
                return False, "skipped (recursion guard)"
            script_path = PROJECT_ROOT / self.path
            if not script_path.exists():
                return False, f"script not found: {self.path}"
            try:
                env = os.environ.copy()
                env["_PLAN_ENGINE_ACTIVE"] = "1"
                result = subprocess.run(
                    [str(script_path)], capture_output=True, timeout=30,
                    cwd=str(PROJECT_ROOT), env=env
                )
                return result.returncode == 0, f"exit {result.returncode}"
            except (OSError, subprocess.SubprocessError) as e:
                return False, str(e)
        elif self.type in ("validate", "coverage", "spec_review"):
            # Task 435 (B-2 Lock): non-preliminary Pflicht-Gates dieser Types
            # haben aktuell keine Default-Logik; sie sind nur als preliminary
            # spezifiziert. Nicht-preliminary => no-op pass mit Hinweis-Detail.
            return True, f"{self.type}: noop (non-preliminary fallback)"
        else:
            # Unknown type: WARN UNKNOWN_GATE_TYPE, return fail
            # warnings via _emit_warn
            _emit_warn(f"UNKNOWN_GATE_TYPE: {self.type!r}")
            return False, f"unknown gate type: {self.type}"

    def __str__(self) -> str:
        if self.preliminary:
            return f"{self.type}:{self.ref or self.desc} (preliminary)"
        if self.type == "task":
            return f"task:{self.id} = {self.want or 'done'}"
        if self.type == "file":
            return f"file:{self.path}"
        if self.type == "script":
            return f"script:{self.path}"
        if self.type in ("validate", "coverage", "spec_review"):
            return f"{self.type}:{self.ref or self.desc}"
        return f"{self.type}:?"


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
    # Task 435 (B-3 Lock Strategy A flat, F-C-007):
    # 13 Optional-Felder direkt typisiert in Dataclass mit Default-Werten.
    # KEIN extra-dict, KEIN Hybrid (User-Override 2026-05-03).
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
    buddyai_infra_audit: str = ""                 # M1.5-only
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


# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------

# Task 435 (F-C-P2-001 User-Lock 2026-05-03 Variante c):
# Synthetic-IDs fuer Feature-Milestones M1-M7+M1.5 (Schema-File §1, B-1 Lock).
# 8 IDs, KEIN 2090, KEIN M0-cross-cutting in feature_milestones-Block.
FEATURE_MILESTONE_SYNTHETIC_IDS: dict[str, int] = {
    "M1": 2100,
    "M1.5": 2150,
    "M2": 2110,
    "M3": 2120,
    "M4": 2130,
    "M5": 2140,
    "M6": 2160,
    "M7": 2170,
}

# Task 435 (Schema-File §1, F-C-014):
# Whitelist erlaubter Feldnamen pro feature_milestone-Eintrag. Unbekannte
# Felder loesen WARN UNKNOWN_FIELD aus, kein ERR. Pflicht-Felder sind
# implizit (Schema-File §1) — fehlende Pflicht-Felder werden tolerant
# behandelt (Default-Werte).
_FEATURE_MILESTONE_KNOWN_FIELDS = {
    # Pflicht-Felder per Schema-File §1
    "name", "feature", "capabilities", "specs", "fallback_strategy",
    "requires", "blocked_by", "gate", "app_status_post_milestone",
    # Optional-Felder
    "cross_cutting", "parallel_to", "frontend_components",
    "backend_refactor_components", "sysadmin_methodology_import",
    "buddyai_infra_audit", "gap_ownership_anchor_task",
    # Doku-only (akzeptiert ohne WARN)
    "title", "desc",
}


def load_archived_task_ids(project_root: Path) -> set[int]:
    """Task 435 (F-C-P2-001 User-Lock 2026-05-03 Variante c, F-CA-001 Mitigation):

    Liest IDs aus <project_root>/docs/tasks/archive/*.yaml (NICHT recursive,
    NICHT legacy_milestones_archive.yaml). Reine ID-Sammlung, kein Stub-Read.
    Used by validate-Loop fuer Silent-Pass von BROKEN_DEP wenn Target archived.

    PROJECT_ROOT-relativ (F-CA-001): project_root MUSS explicit uebergeben
    werden — kein implicit cwd-Resolve. Verhindert Cycle-Entry-Point-Sensitivity.

    Anti-Pattern-9-Disambiguation: docs/tasks/archive/*.yaml ist NICHT
    docs/plan/legacy-milestones-archive.yaml — letzteres bleibt unread.
    """
    # warnings via _emit_warn

    archived_ids: set[int] = set()
    archive_dir = project_root / "docs" / "tasks" / "archive"
    if not archive_dir.is_dir():
        # frischer Repo / kein archive — leeres set OK (kein WARN, legitim)
        return archived_ids

    for path in sorted(archive_dir.glob("*.yaml")):
        try:
            with open(path, encoding="utf-8") as f:
                data = yaml.safe_load(f)
        except (FileNotFoundError, yaml.YAMLError, OSError) as e:
            # F-CA-002 Mitigation: explizite Exception-Klassen, NICHT silent except.
            # WARN ARCHIVED_ID_PARSE_FAIL emittiert (sichtbar im Test-Output).
            _emit_warn(f"ARCHIVED_ID_PARSE_FAIL: {path}: {e}")
            continue

        if not isinstance(data, dict):
            continue
        raw_id = data.get("id")
        if raw_id is None:
            # Old-Format-File ohne id — Skip (legitim, kein WARN noetig)
            continue
        # CA-001 Iteration 2: yaml-bool-id explizit reject VOR Coercion.
        # Python int(True)=1 / int(False)=0 -> ohne Reject wuerde Task #1
        # bzw. #0 stumm als archiviert markiert.
        if isinstance(raw_id, bool):
            _emit_warn(
                f"ARCHIVED_ID_BOOL_REJECTED: {path}: id={raw_id!r} "
                "(yaml-bool ist nie valide id)"
            )
            continue
        # F-CA-003 Type-Coercion-Disziplin: _coerce_int_or_none statt raw int().
        coerced = _coerce_int_or_none(raw_id, f"archive[{path.name}].id")
        if coerced is None:
            # WARN bereits emittiert von _coerce_int_or_none (oder bool-reject oben)
            _emit_warn(f"ARCHIVED_ID_TYPE_INVALID: {path}: id={raw_id!r}")
            continue
        archived_ids.add(coerced)
    return archived_ids


# 2026-05-07: Module-level Cache fuer archived task IDs, used by
# GateCondition.check zur Archive-Awareness (archived gate-task = terminal-done).
# Per-PROJECT_ROOT keyed; _swap_plan_engine_globals (aggregate-mode) wechselt
# PROJECT_ROOT und damit den Cache-Key, daher kein manuelles Invalidate noetig.
_archived_ids_cache: dict[Path, set[int]] = {}


def _get_archived_ids_cached() -> set[int]:
    """Lazy + cached access to archived task IDs for current PROJECT_ROOT.

    Used by GateCondition.check (task-type) so that an archived gate-task
    (e.g., M0-cross-cutting gate id=417 after M0-Welle-Closeout) is treated
    as done. Without this, every Milestone whose gate-tasks become archived
    would misreport as ORPHAN.

    Cache invalidation: implicit per PROJECT_ROOT — when aggregate-mode swaps
    PROJECT_ROOT via _swap_plan_engine_globals, the cache key changes too.
    """
    if PROJECT_ROOT not in _archived_ids_cache:
        try:
            _archived_ids_cache[PROJECT_ROOT] = load_archived_task_ids(PROJECT_ROOT)
        except (OSError, AttributeError):
            _archived_ids_cache[PROJECT_ROOT] = set()
    return _archived_ids_cache[PROJECT_ROOT]


def _coerce_str(raw, field_name: str = "") -> str:  # noqa: ARG001
    """F-CA-003 Helper: yaml-Field zu str mit None-Default. Kein Crash auf None."""
    if raw is None:
        return ""
    return str(raw)


def _coerce_str_list(raw, field_name: str = "") -> list[str]:
    """F-CA-003 Helper: yaml-Field zu list[str]. Bei string-statt-list:
    explicit None|empty -> [] ohne WARN; non-empty string -> [string] (auto-wrap)
    + WARN SCHEMA_TYPE_MISMATCH (yaml-Tippfehler-Detection)."""
    # warnings via _emit_warn

    if raw is None:
        return []
    if isinstance(raw, list):
        # Items zu str kasten falls noetig (Schema akzeptiert string + dict-with-quotes)
        return [str(x) for x in raw if x is not None]
    if isinstance(raw, str):
        if not raw:
            return []
        _emit_warn(
            f"SCHEMA_TYPE_MISMATCH: field {field_name!r} expected list, got str: "
            f"auto-wrapped to [{raw!r}]"
        )
        return [raw]
    # int/dict/anything-else: WARN, fallback []
    _emit_warn(
        f"SCHEMA_TYPE_MISMATCH: field {field_name!r} expected list, got "
        f"{type(raw).__name__}: {raw!r} -> []"
    )
    return []


def _coerce_int_or_none(raw, field_name: str = "") -> int | None:
    """F-CA-003 Helper: yaml-Field zu int|None. String 'abc' -> None + WARN.

    Iteration 2 (CA-001 + CA-004 Fix): yaml-bool wird explizit REJECTED.
    Python-Quirk: bool ist int-Subtyp -> int(True)=1, int(False)=0.
    Ohne expliziten bool-Reject wuerde 'id: true' silent als id=1 archiviert
    bzw. als Gate-Target gerendert. Wir emittieren WARN
    SCHEMA_TYPE_MISMATCH_BOOL und returnen None damit der Caller
    skip-and-continue macht.
    """
    # warnings via _emit_warn

    if raw is None:
        return None
    if isinstance(raw, bool):
        # CA-001/CA-004 Mitigation: yaml-bool ist NIE eine valide id.
        # MUST be checked BEFORE isinstance(raw, int) (bool ist int-Subtyp).
        _emit_warn(
            f"SCHEMA_TYPE_MISMATCH: field {field_name!r} expected int|None, got "
            f"bool: {raw!r} -> None (yaml-bool als id ist nie valide)"
        )
        return None
    if isinstance(raw, int):
        return raw
    try:
        return int(raw)
    except (TypeError, ValueError):
        _emit_warn(
            f"SCHEMA_TYPE_MISMATCH: field {field_name!r} expected int|None, got "
            f"{type(raw).__name__}: {raw!r} -> None"
        )
        return None


def _construct_task_from_dict(
    data: object, repo_name: str = ""
) -> tuple[int | None, "Task | None"]:
    """Build Task from already-parsed yaml dict.

    Returns (tid, Task) on success, (None, None) when data is invalid (not a
    dict, missing id). Used by load_tasks AND load_archived_tasks to avoid
    schema-parse-drift between active and archived task IO.
    """
    if not isinstance(data, dict):
        return None, None
    raw_id = data.get("id")
    if raw_id is None:
        return None, None
    # F-CA-003 Type-Coercion-Disziplin: _coerce_int_or_none statt raw int().
    # Aggregate-Mode (`{tid:03d}`) erwartet int — str-ids in YAML (z.B.
    # `id: "098"`) wuerden sonst beim f-string crashen.
    if isinstance(raw_id, bool):
        # yaml-bool ist nie valide id (Python int(True)=1)
        return None, None
    tid = _coerce_int_or_none(raw_id, "task.id")
    if tid is None:
        return None, None

    bb = data.get("blocked_by") or []
    if isinstance(bb, int):
        bb = [bb]
    if not isinstance(bb, list):
        bb = []
    bb = [int(x) if isinstance(x, str) and x.isdigit() else x
          for x in bb if x is not None]
    # Filter non-int entries
    bb = [x for x in bb if isinstance(x, int)]

    bbe = data.get("blocked_by_external") or []

    task = Task(
        id=tid,
        title=data.get("title", ""),
        status=data.get("status", "pending"),
        milestone=data.get("milestone", ""),
        blocked_by=bb,
        effort=data.get("effort", "M"),
        area=data.get("area", ""),
        assignee=data.get("assignee", ""),
        spec_ref=data.get("spec_ref", "") or "",
        board_result=str(data.get("board_result", "") or ""),
        readiness=data.get("readiness", ""),
        summary=data.get("summary", "") or "",
        blocked_by_external=bbe,
        created=str(data.get("created", "")),
        updated=str(data.get("updated", "")),
        intent_chain=data.get("intent_chain") or {},
        notes=str(data.get("notes", "") or ""),
        note=str(data.get("note", "") or ""),
        blocking_note=str(data.get("blocking_note", "") or ""),
        sub_tasks=data.get("sub_tasks") or [],
        parent_task=data.get("parent_task") or 0,
        deploy_gate=str(data.get("deploy_gate", "") or ""),
        closed=str(data.get("closed", "") or ""),
        workflow_template=str(data.get("workflow_template", "") or ""),
        ac_schema_validation=str(data.get("ac_schema_validation", "") or ""),
        spec_version=str(data.get("spec_version", "") or ""),
        spec_states=data.get("spec_states") if isinstance(data.get("spec_states"), dict) else {},  # type: ignore[arg-type]
        _repo=repo_name,
        # Task 435 (F-C-014, AC-A.9): Sub-Tags-Propagation in Task-Dataclass.
        legacy_milestone_key=_coerce_str(data.get("legacy_milestone_key"), "legacy_milestone_key"),
        migration_note=_coerce_str(data.get("migration_note"), "migration_note"),
    )
    return tid, task


def load_tasks(project_root: Path | None = None, repo_name: str = "") -> dict:
    """Load tasks from a single project root.

    Task 367: project_root parameter allows loading tasks from arbitrary
    directories (used by aggregate mode). When None, falls back to the
    module-level TASKS_DIR (current PROJECT_ROOT). repo_name, when set,
    marks each Task with _repo for namespacing — used only by aggregate mode.

    Return type depends on mode:
      - Single-repo (repo_name=""): dict[int, Task] keyed by integer task id
      - Aggregate (repo_name set): dict[str, Task] keyed by "<repo>#<id:03d>"
    """
    # Task 435 (F-C-010a): non-recursive Path-Filter via tasks_dir.glob("*.yaml").
    # Explizit NICHT rglob, NICHT docs/tasks/archive/**.
    # Archived tasks live in docs/tasks/archive/ — read via load_archived_tasks().
    # Path-Flexibilitaet: project_root kann sein:
    #   - None: nutzt module-level TASKS_DIR
    #   - Pfad zu <root>/docs/tasks/ direkt (Test-Use-Case): nutzt as-is
    #   - Pfad zu <root>/ (Standard): nutzt <root>/docs/tasks
    if project_root is None:
        tasks_dir = TASKS_DIR
    elif project_root.name == "tasks" and project_root.is_dir():
        tasks_dir = project_root
    else:
        tasks_dir = project_root / "docs" / "tasks"
    tasks: dict = {}
    for yaml_path in sorted(tasks_dir.glob("*.yaml")):
        if yaml_path.name.endswith("-gates.yaml"):
            continue
        try:
            data = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
        except (yaml.YAMLError, OSError):
            continue
        tid, task = _construct_task_from_dict(data, repo_name)
        if task is None:
            continue
        if repo_name:
            # Aggregate mode: key by namespaced string "<repo>#<id:03d>".
            # blocked_by stays integer here — it will be rewritten to
            # namespaced keys during the merge step in load_aggregated().
            tasks[f"{repo_name}#{tid:03d}"] = task
        else:
            tasks[tid] = task
    return tasks


def load_archived_tasks(
    project_root: Path | None = None, repo_name: str = ""
) -> dict:
    """Load full Task objects from <project_root>/docs/tasks/archive/*.yaml.

    Komplementaer zu load_archived_task_ids (das nur IDs fuer blocked_by-
    Resolution liefert). Diese Funktion gibt komplette Task-Objekte zurueck
    — used by Dashboard fuer done-collapsed-Stack-Render der archivierten
    Tasks (sonst waeren sie post-Archive unsichtbar im Dashboard).

    Path-Resolution analog zu load_tasks:
      - None: TASKS_DIR / archive
      - Pfad zu <root>/docs/tasks/: project_root / archive
      - Pfad zu <root>/: project_root / docs / tasks / archive

    Return type analog zu load_tasks (single-repo dict[int, Task] oder
    aggregate dict[str, Task] bei nicht-leerem repo_name).

    NICHT recursive (analog zu load_archived_task_ids). -gates.yaml wird
    geskippt (Konsistenz mit load_tasks).
    """
    if project_root is None:
        archive_dir = TASKS_DIR / "archive"
    elif project_root.name == "tasks" and project_root.is_dir():
        archive_dir = project_root / "archive"
    else:
        archive_dir = project_root / "docs" / "tasks" / "archive"

    tasks: dict = {}
    if not archive_dir.is_dir():
        # frischer Repo / kein archive — leeres dict OK (kein WARN, legitim)
        return tasks

    for yaml_path in sorted(archive_dir.glob("*.yaml")):
        if yaml_path.name.endswith("-gates.yaml"):
            continue
        try:
            data = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
        except (yaml.YAMLError, OSError) as e:
            _emit_warn(f"ARCHIVED_TASK_PARSE_FAIL: {yaml_path}: {e}")
            continue
        tid, task = _construct_task_from_dict(data, repo_name)
        if task is None:
            continue
        if repo_name:
            tasks[f"{repo_name}#{tid:03d}"] = task
        else:
            tasks[tid] = task
    return tasks


def _build_gate_from_dict(g: dict) -> GateCondition:
    """Build GateCondition from yaml-loaded dict. Type-Coercion-disziplin (F-CA-003).

    Schema-File §3 Pre-Set-Gate-Format:
      {type: task, id: <int>, desc: <str>}
      {type: validate|coverage|spec_review, ref: <str>, preliminary: true|false}
    """
    if not isinstance(g, dict):
        # Defensive: list-statt-dict (yaml-Tippfehler) -> empty Gate
        # warnings via _emit_warn
        _emit_warn(f"GATE_TYPE_MISMATCH: gate-entry expected dict, got {type(g).__name__}: {g!r}")
        return GateCondition(type="")
    # CA-004 Iteration 2: yaml-bool-id explizit reject VOR int()-Coercion
    # (gleiche Bug-Class wie CA-001 in load_archived_task_ids, anderer Pfad).
    raw_id = g.get("id", 0)
    if isinstance(raw_id, bool):
        _emit_warn(
            f"GATE_ID_BOOL_REJECTED: gate-entry id={raw_id!r} "
            "(yaml-bool ist nie valide Task-id) -> 0"
        )
        gid = 0
    elif raw_id is None:
        gid = 0
    else:
        coerced = _coerce_int_or_none(raw_id, "gate.id")
        gid = coerced if coerced is not None else 0
    return GateCondition(
        type=g.get("type", "") or "",
        path=_coerce_str(g.get("path"), "path"),
        id=gid,
        want=_coerce_str(g.get("want"), "want"),
        ref=_coerce_str(g.get("ref"), "ref"),
        preliminary=g.get("preliminary", False),  # __post_init__ macht Coercion
        desc=_coerce_str(g.get("desc"), "desc"),
    )


def load_plan(project_root: Path | None = None) -> PlanResult:
    """Returns PlanResult (backward-compatible with tuple unpacking).

    Task 367: project_root parameter allows loading plan from arbitrary
    directories (used by aggregate mode). When None, falls back to the
    module-level PLAN_PATH.

    Task 435 (F-C-007, F-C-010a, B-1, F-CA-003): liest zusaetzlich
    `feature_milestones:`-Block und erzeugt Synthetic-Milestones mit IDs
    2100/2150/2110/2120/2130/2140/2160/2170. Bei Key-Kollision mit
    `milestones:`-Pointern: feature_milestones gewinnt (B-1 Lock).

    Path-Flexibilitaet: project_root kann sein:
      - None: nutzt module-level PLAN_PATH
      - Path zu Verzeichnis: liest <root>/docs/plan.yaml
      - Path zu yaml-File: liest direkt diese Datei (Test-Fixture-Use-Case)

    Graceful degradation (Task 010 Part L0 + Task 435 F-C-010a):
    Bei fehlendem feature_milestones-Block: kein Crash, kein WARN.
    """
    # warnings via _emit_warn

    if project_root is None:
        plan_path = PLAN_PATH
    else:
        # Path-Flexibilitaet: File oder Dir
        plan_path = project_root if project_root.is_file() else project_root / "docs" / "plan.yaml"

    if not plan_path.exists():
        return PlanResult(
            milestones={},
            target="",
            north_star="",
            operational_intent={},
            phases=[],
        )
    try:
        data = yaml.safe_load(plan_path.read_text(encoding="utf-8"))
    except (yaml.YAMLError, OSError) as e:
        _emit_warn(f"PLAN_PARSE_FAIL: {plan_path}: {e}")
        return PlanResult(
            milestones={},
            target="",
            north_star="",
            operational_intent={},
            phases=[],
        )

    if not isinstance(data, dict):
        return PlanResult(
            milestones={},
            target="",
            north_star="",
            operational_intent={},
            phases=[],
        )

    target = _coerce_str(data.get("target"), "target")
    north_star = _coerce_str(data.get("north_star"), "north_star").strip()
    op_intent_raw = data.get("operational_intent")
    op_intent: dict = op_intent_raw if isinstance(op_intent_raw, dict) else {}

    # Parse phases section
    phases_raw = data.get("phases", {})
    phases = []
    if isinstance(phases_raw, dict):
        for order, (key, pdata) in enumerate(phases_raw.items()):
            if not isinstance(pdata, dict):
                continue
            phases.append(Phase(
                key=str(key),
                title=str(pdata.get("title", key) or key),
                desc=str(pdata.get("desc", "") or ""),
                investor_desc=str(pdata.get("investor_desc", "") or ""),
                order=order,
            ))

    milestones: dict[str, Milestone] = {}

    # Step 1: Legacy `milestones:`-Liste (Pointer-Format).
    # Wird zuerst geladen — feature_milestones gewinnt bei Kollision (B-1 Lock).
    for entry in data.get("milestones", []) or []:
        if not isinstance(entry, dict):
            continue
        key = entry.get("key", "")
        if not key:
            continue
        gates = [_build_gate_from_dict(g) for g in entry.get("gate", []) or []]
        # Pre-Greenfield Pointer-Eintraege koennen 'id' haben (Synthetic 2090-2170).
        # CA-004 Iteration 2: yaml-bool-id explizit reject VOR int()-Coercion.
        raw_id = entry.get("id", 0)
        if isinstance(raw_id, bool):
            _emit_warn(
                f"MILESTONE_ID_BOOL_REJECTED: milestones[{key!r}] id={raw_id!r} "
                "(yaml-bool ist nie valide Synthetic-id) -> 0"
            )
            mid = 0
        elif raw_id is None:
            mid = 0
        else:
            coerced = _coerce_int_or_none(raw_id, f"milestones[{key}].id")
            mid = coerced if coerced is not None else 0
        milestones[key] = Milestone(
            key=key,
            title=str(entry.get("title", key) or key),
            desc=str(entry.get("desc", "") or ""),
            type=str(entry.get("type", "milestone") or "milestone"),
            gate=gates,
            requires=entry.get("requires", []) or [],
            phases=entry.get("phases", []) or [],
            id=mid,
        )

    # Step 2 (Task 435, B-1 Lock): feature_milestones-Block native lesen.
    # Bei Key-Kollision mit milestones:-Liste: feature_milestones gewinnt (overwrite).
    feature_block = data.get("feature_milestones", {})
    if not isinstance(feature_block, dict):
        feature_block = {}

    for fkey, fdata in feature_block.items():
        if not isinstance(fdata, dict):
            _emit_warn(
                f"SCHEMA_TYPE_MISMATCH: feature_milestones[{fkey!r}] expected dict, "
                f"got {type(fdata).__name__}: {fdata!r} -> skipped"
            )
            continue

        # Synthetic-ID Lookup (8 IDs, kein 2090).
        synthetic_id = FEATURE_MILESTONE_SYNTHETIC_IDS.get(fkey, 0)

        # Type-Whitelist: unbekannte Felder triggern WARN UNKNOWN_FIELD.
        # F-CA-003 Anti-Pattern: yaml-Felder mit Python-Reservierten-Namen
        # (__class__, __init__) NICHT via setattr propagieren.
        unknown_fields = set(fdata.keys()) - _FEATURE_MILESTONE_KNOWN_FIELDS
        for ufield in sorted(unknown_fields):
            if ufield.startswith("__") and ufield.endswith("__"):
                # Python-reserved -> WARN, NICHT setattr
                _emit_warn(
                    f"UNKNOWN_FIELD: feature_milestones[{fkey!r}] has reserved "
                    f"name {ufield!r} (skipped, state-corruption-Schutz)"
                )
            else:
                _emit_warn(
                    f"UNKNOWN_FIELD: feature_milestones[{fkey!r}] hat unbekanntes "
                    f"Feld {ufield!r}"
                )

        # Default-Regel F-C-016: requires := requires_field or blocked_by_field or [].
        # Beide duerfen co-existieren; bei Konflikt gewinnt requires.
        requires_raw = fdata.get("requires")
        blocked_by_raw = fdata.get("blocked_by")
        if requires_raw:
            requires = _coerce_str_list(requires_raw, f"feature_milestones[{fkey}].requires")
        elif blocked_by_raw:
            requires = _coerce_str_list(blocked_by_raw, f"feature_milestones[{fkey}].blocked_by")
        else:
            requires = []

        # Gate parsen (Pre-Set-Gates Schema-File §3)
        gate_raw = fdata.get("gate", []) or []
        feature_gates: list[GateCondition] = []
        if isinstance(gate_raw, list):
            if "gate" in fdata and not gate_raw:
                # TC-ADV-024: Schema sagt 'Pflicht-Felder: gate'. Leere Liste WARN.
                _emit_warn(
                    f"MILESTONE_NO_GATE: feature_milestones[{fkey!r}] hat leeres gate"
                )
            for g in gate_raw:
                feature_gates.append(_build_gate_from_dict(g))
        else:
            _emit_warn(
                f"SCHEMA_TYPE_MISMATCH: feature_milestones[{fkey!r}].gate expected "
                f"list, got {type(gate_raw).__name__}"
            )

        # Capabilities/Specs etc. mit Type-Coercion-Disziplin lesen.
        capabilities = _coerce_str_list(
            fdata.get("capabilities"), f"feature_milestones[{fkey}].capabilities"
        )
        specs = _coerce_str_list(
            fdata.get("specs"), f"feature_milestones[{fkey}].specs"
        )
        fallback_strategy = _coerce_str_list(
            fdata.get("fallback_strategy"), f"feature_milestones[{fkey}].fallback_strategy"
        )
        cross_cutting = _coerce_str_list(
            fdata.get("cross_cutting"), f"feature_milestones[{fkey}].cross_cutting"
        )
        parallel_to = _coerce_str_list(
            fdata.get("parallel_to"), f"feature_milestones[{fkey}].parallel_to"
        )
        frontend_components = _coerce_str_list(
            fdata.get("frontend_components"), f"feature_milestones[{fkey}].frontend_components"
        )
        backend_refactor_components = _coerce_str_list(
            fdata.get("backend_refactor_components"),
            f"feature_milestones[{fkey}].backend_refactor_components",
        )
        gap_anchor = _coerce_int_or_none(
            fdata.get("gap_ownership_anchor_task"),
            f"feature_milestones[{fkey}].gap_ownership_anchor_task",
        )

        m = Milestone(
            key=fkey,
            title=_coerce_str(fdata.get("name"), "name") or fkey,
            desc=_coerce_str(fdata.get("desc"), "desc"),
            type="milestone",
            gate=feature_gates,
            requires=requires,
            phases=[],
            id=synthetic_id,
            name=_coerce_str(fdata.get("name"), "name"),
            feature=_coerce_str(fdata.get("feature"), "feature"),
            capabilities=capabilities,
            specs=specs,
            fallback_strategy=fallback_strategy,
            cross_cutting=cross_cutting,
            parallel_to=parallel_to,
            frontend_components=frontend_components,
            backend_refactor_components=backend_refactor_components,
            app_status_post_milestone=_coerce_str(
                fdata.get("app_status_post_milestone"), "app_status_post_milestone"
            ),
            sysadmin_methodology_import=_coerce_str(
                fdata.get("sysadmin_methodology_import"), "sysadmin_methodology_import"
            ),
            buddyai_infra_audit=_coerce_str(
                fdata.get("buddyai_infra_audit"), "buddyai_infra_audit"
            ),
            gap_ownership_anchor_task=gap_anchor,
        )
        # B-1 Lock: feature_milestones gewinnt bei Key-Kollision (overwrite).
        milestones[fkey] = m

    return PlanResult(
        milestones=milestones,
        target=target,
        north_star=north_star,
        operational_intent=op_intent,
        phases=phases,
    )


# ---------------------------------------------------------------------------
# Task 367: Multi-Repo Aggregation
# ---------------------------------------------------------------------------

def discover_projects(projects_arg: str | None = None) -> list[tuple[str, Path]]:
    """Task 367: Discover project repos for aggregate mode.

    Returns a list of (repo_name, project_root) tuples.

    Resolution:
      1. If projects_arg is set: comma-separated list. Each entry can be
         either a bare repo name (resolved against $PROJECTS_DIR) or an
         absolute/relative path to a project root. repo_name is derived from
         the final path component.
      2. Otherwise: scan $PROJECTS_DIR (default ~/projects) for subdirectories
         that contain BOTH intent.md AND docs/tasks/ — each such subdirectory
         becomes a candidate repo.

    Invalid entries (missing intent.md or docs/tasks/) are silently skipped.
    Caller can emit warnings via validate() if expected repos are missing.
    """
    projects_dir = Path(os.environ.get("PROJECTS_DIR", Path.home() / "projects"))

    candidates: list[tuple[str, Path]] = []

    if projects_arg:
        for raw in projects_arg.split(","):
            name_or_path = raw.strip()
            if not name_or_path:
                continue
            candidate_path = Path(name_or_path)
            if not candidate_path.is_absolute():
                # Try projects_dir first, then CWD-relative
                cand = projects_dir / name_or_path
                candidate_path = cand if cand.exists() else candidate_path.resolve()
            else:
                candidate_path = candidate_path.resolve()
            repo_name = candidate_path.name
            candidates.append((repo_name, candidate_path))
    else:
        # Auto-discovery
        if not projects_dir.exists():
            return []
        for entry in sorted(projects_dir.iterdir()):
            if not entry.is_dir():
                continue
            intent_md = entry / "intent.md"
            tasks_dir = entry / "docs" / "tasks"
            if intent_md.exists() and tasks_dir.exists():
                candidates.append((entry.name, entry.resolve()))

    # Validate: drop entries that don't look like project repos.
    validated: list[tuple[str, Path]] = []
    for repo_name, root in candidates:
        if not root.exists():
            continue
        # Auto-discovered entries have already been validated. For explicit
        # --projects entries, also require at least docs/tasks/ to exist —
        # intent.md is optional for explicit list (user knows what they pass).
        tasks_dir = root / "docs" / "tasks"
        if not tasks_dir.exists():
            continue
        validated.append((repo_name, root))

    return validated


@dataclass
class AggregateResult:
    """Task 367: Result of load_aggregated.

    Contains merged tasks, merged milestones, and metadata about the aggregate
    scope. Unlike PlanResult (single-repo), this does not expose a single
    "target" — each repo has its own target, and aggregate views show them all.
    """
    tasks: dict
    milestones: dict[str, Milestone]
    # Per-repo metadata: repo_name -> PlanResult (original single-repo plan)
    per_repo: dict[str, PlanResult] = field(default_factory=dict)
    # Set of (repo_name, project_root) that were loaded
    projects: list[tuple[str, Path]] = field(default_factory=list)
    # Warnings discovered during aggregation (e.g. stale external refs)
    warnings: list[str] = field(default_factory=list)
    # Primary target for critical-path etc. — taken from the FIRST repo that
    # defines a non-empty target. In aggregate mode this is namespaced as
    # "<repo>:<milestone_key>" to avoid collisions.
    target: str = ""
    north_star: str = ""
    operational_intent: dict = field(default_factory=dict)
    # Task 435 Iteration 2 (CA-002 Fix): Union der per-repo archived task-IDs,
    # namespaced als "<repo>#<id:03d>" damit validate-Loop direkt match macht.
    archived_ids: set[str] = field(default_factory=set)


def load_aggregated(projects_arg: str | None = None) -> AggregateResult:
    """Task 367: Load multiple project repos and merge into unified tasks/milestones.

    Keying:
      - Tasks: dict key is "<repo>#<id:03d>" string (e.g. "buddyai#358").
      - Milestones: dict key is "<repo>:<milestone_key>" (colon separator to
        distinguish from task keys). Inter-milestone requires references are
        rewritten to the namespaced form when the referenced milestone belongs
        to the same repo; cross-repo milestone requires are NOT supported.

    blocked_by rewriting:
      - Intra-repo: int ids are rewritten to "<repo>#<id:03d>" keys.
      - Cross-repo (via blocked_by_external dict entries): resolved to
        "<target_repo>#<id:03d>" and appended to blocked_by. Unresolved
        entries are stashed in _unresolved_external and count as blockers
        via has_external_deps.

    Task 435 Iteration 2 (CA-002 Fix): per-repo archived_ids gesammelt + zu
    einem namespaced set ("<repo>#<id:03d>") gemerged. Variante c Silent-Pass
    funktioniert damit auch im Aggregate-Pfad — cross-repo blocked_by-Refs
    auf in einem Repo archivierte Tasks erzeugen kein BROKEN_DEP mehr.
    Ergebnis liegt in result.archived_ids (set[str]).
    """
    projects = discover_projects(projects_arg)
    if not projects:
        return AggregateResult(tasks={}, milestones={})

    result = AggregateResult(tasks={}, milestones={}, projects=projects)

    # Phase 1: load each repo individually, namespace keys
    for repo_name, root in projects:
        repo_tasks = load_tasks(project_root=root, repo_name=repo_name)
        repo_plan = load_plan(project_root=root)
        result.per_repo[repo_name] = repo_plan

        # CA-002 Iteration 2: per-repo archived_ids sammeln + namespacen.
        # Format identisch zur blocked_by-Rewrite ("<repo>#<id:03d>") damit
        # validate-Loop direkt matched.
        repo_archived = load_archived_task_ids(root)
        for aid in repo_archived:
            result.archived_ids.add(f"{repo_name}#{aid:03d}")

        # Record first non-empty target/north_star as the aggregate's primary
        if not result.target and repo_plan.target:
            result.target = f"{repo_name}:{repo_plan.target}"
            result.north_star = repo_plan.north_star
            result.operational_intent = repo_plan.operational_intent

        # Namespace milestones: key becomes "<repo>:<key>"; requires rewritten
        # to same-repo namespaced keys.
        for mkey, m in repo_plan.milestones.items():
            namespaced_key = f"{repo_name}:{mkey}"
            namespaced_requires = [f"{repo_name}:{r}" for r in m.requires]
            new_m = Milestone(
                key=namespaced_key,
                title=m.title,
                desc=m.desc,
                type=m.type,
                gate=list(m.gate),
                requires=namespaced_requires,
                phases=list(m.phases),
                status=m.status,
                tasks=[],  # repopulated below from namespaced tasks
                dependents=[],
            )
            result.milestones[namespaced_key] = new_m

        # Namespace each task's milestone field + rewrite blocked_by from int
        # to namespaced string keys.
        for task_key, task in repo_tasks.items():
            if task.milestone:
                task.milestone = f"{repo_name}:{task.milestone}"
            task.blocked_by = [
                f"{repo_name}#{int(dep):03d}" for dep in task.blocked_by
                if isinstance(dep, int)
            ]
            result.tasks[task_key] = task

    # Phase 2: resolve blocked_by_external entries across the aggregate scope.
    known_repos = {name for name, _ in projects}
    for task_key, task in result.tasks.items():
        if not task.blocked_by_external:
            continue
        unresolved = []
        for entry in task.blocked_by_external:
            parsed = _parse_external_entry(entry)
            if parsed is None:
                # Legacy simple-list form: can't resolve without schema, keep
                # as unresolved (preserves pre-367 semantics: always blocks).
                unresolved.append(entry)
                continue
            ext_repo, ext_id = parsed
            if ext_repo not in known_repos:
                # Stale/missing repo: WARN + treat as unresolved
                result.warnings.append(
                    f"task {task_key}: blocked_by_external references repo "
                    f"'{ext_repo}' which is not in the aggregate scope — "
                    f"treated as unresolved"
                )
                unresolved.append(entry)
                continue
            target_key = f"{ext_repo}#{ext_id:03d}"
            if target_key not in result.tasks:
                result.warnings.append(
                    f"task {task_key}: blocked_by_external references "
                    f"{target_key} which does not exist in repo '{ext_repo}' "
                    f"— treated as unresolved"
                )
                unresolved.append(entry)
                continue
            # Resolved — append to blocked_by as a cross-repo dep
            if target_key not in task.blocked_by:
                task.blocked_by.append(target_key)
        task._unresolved_external = unresolved

    return result


# ---------------------------------------------------------------------------
# DAG + Computation
# ---------------------------------------------------------------------------

def compute_milestone_dependents(milestones: dict[str, Milestone]) -> None:
    """Invert requires-graph. Sets milestone.dependents for each milestone."""
    for m in milestones.values():
        m.dependents = []
    for m in milestones.values():
        for req in m.requires:
            if req in milestones:
                milestones[req].dependents.append(m.key)


def compute_phase_progress(
    phase_key: str,
    milestones: dict[str, Milestone],
    tasks: dict[int, Task],
) -> PhaseProgress:
    """Aggregate progress over all milestones belonging to a phase."""
    phase_milestones = [m for m in milestones.values() if phase_key in m.phases]
    tasks_done = 0
    tasks_total = 0
    remaining_effort = 0
    for m in phase_milestones:
        for tid in m.tasks:
            t = tasks.get(tid)
            if not t or (t.is_terminal and t.status != "done"):
                continue
            tasks_total += 1
            if t.is_done:
                tasks_done += 1
            else:
                remaining_effort += t.effort_weight
    pct = int(tasks_done / tasks_total * 100) if tasks_total > 0 else 0
    return PhaseProgress(
        pct=pct, tasks_done=tasks_done,
        tasks_total=tasks_total, remaining_effort=remaining_effort,
    )


def assign_tasks_to_milestones(tasks: dict, milestones: dict[str, Milestone]):
    """Populate milestone.tasks lists.

    Task 367: Uses t.key (namespaced in aggregate mode, int in single-repo).
    m.tasks entries are therefore dict keys valid against the tasks dict.
    """
    for m in milestones.values():
        m.tasks = []
    for t in tasks.values():
        if t.milestone in milestones:
            milestones[t.milestone].tasks.append(t.key)


def compute_milestone_status(milestones: dict[str, Milestone], tasks: dict[int, Task]):
    """Compute status for all milestones. Bottom-up via topo sort on requires DAG."""
    # Topological sort of milestones
    in_degree = dict.fromkeys(milestones, 0)
    children = defaultdict(list)  # parent → children that require it
    for k, m in milestones.items():
        for req in m.requires:
            if req in milestones:
                in_degree[k] += 1
                children[req].append(k)

    queue = deque(k for k, d in in_degree.items() if d == 0)
    order = []
    while queue:
        k = queue.popleft()
        order.append(k)
        for child in children[k]:
            in_degree[child] -= 1
            if in_degree[child] == 0:
                queue.append(child)

    # Compute status in topological order
    for key in order:
        m = milestones[key]
        milestone_tasks = [tasks[tid] for tid in m.tasks if tid in tasks]

        # Priority chain (spec §1)
        # 1. Group → always active
        if m.is_group:
            m.status = "active"
            continue

        # 2. Check requires FIRST — a milestone can't be done if its requires aren't done.
        # This must come before the done-check to prevent meta-milestones (no tasks, no gate)
        # from being vacuously "done" while their requires are still pending.
        requires_issues = False
        requires_deep_block = False
        for req_key in m.requires:
            req_m = milestones.get(req_key)
            if req_m and req_m.status != "done":
                requires_issues = True
                if req_m.status in ("blocked", "future"):
                    requires_deep_block = True

        if requires_deep_block:
            m.status = "future"
            continue
        if requires_issues:
            m.status = "blocked"
            continue

        # 3. Done check: gate (if any) must PASS *and* all tasks must be terminal
        #    (done, superseded, absorbed, wontfix all count as "completed").
        all_tasks_done = milestone_tasks and all(t.is_terminal for t in milestone_tasks)
        no_tasks = not milestone_tasks

        if m.gate:
            all_gate_pass = all(g.check(tasks)[0] for g in m.gate)
            if all_gate_pass and (all_tasks_done or no_tasks):
                m.status = "done"
                continue
        else:
            if all_tasks_done or no_tasks:
                m.status = "done"
                continue

        # 6. Active if any task in_progress
        if any(t.status == "in_progress" for t in milestone_tasks):
            m.status = "active"
            continue

        # 7. Ready
        m.status = "ready"


def _build_milestone_order(milestones: dict[str, Milestone], target: str) -> list[str]:
    """Return milestones in requires-chain of target, topologically sorted (deps first)."""
    relevant = set()
    queue = deque([target])
    while queue:
        mk = queue.popleft()
        if mk in relevant:
            continue
        relevant.add(mk)
        m = milestones.get(mk)
        if m:
            for req in m.requires:
                queue.append(req)

    # Topo sort: deps before dependents
    in_deg = dict.fromkeys(relevant, 0)
    children = defaultdict(list)
    for k in relevant:
        m = milestones.get(k)
        if m:
            for req in m.requires:
                if req in relevant:
                    in_deg[k] += 1
                    children[req].append(k)
    q = deque(k for k, d in in_deg.items() if d == 0)
    order = []
    while q:
        k = q.popleft()
        order.append(k)
        for c in children[k]:
            in_deg[c] -= 1
            if in_deg[c] == 0:
                q.append(c)
    return order


# Task 435 (F-C-P2-003): Mixed-Item-Render-Helper fuer Critical-Path-Items.
# Items koennen sein:
#   - int task-id (legacy + post-1980-mode)
#   - str milestone-key (z.B. "M1", "M1.5", "POST-MVP")
#   - list[str] parallel-Liste (z.B. ["M1", "M1.5"])
#   - str post-MVP-Beschreibung
def _render_cp_item(item, tasks: dict) -> str:
    """Render Critical-Path-Item zu String fuer fmt_boot/fmt_status/fmt_critical_path.

    F-C-P2-003 (Mixed-Items) + F-CA-005 (Subset/Superset-Behavior).
    F-CA-001 Mitigation: explicit None-Branch (yaml-null wuerde 'None'-string).
    """
    # warnings via _emit_warn
    if item is None:
        return "(none)"
    if isinstance(item, bool):
        # bool ist subtype of int — explicit vor int-Branch
        return str(item)
    if isinstance(item, int):
        t = tasks.get(item)
        if t is None:
            # weder in tasks noch sonst etwas: nutzen wir "(missing)"
            return f"[{item}] (missing)"
        title = getattr(t, "title", "") or ""
        return f"[{item}] {title}"
    if isinstance(item, list):
        # Items zu str kasten (TypeError-Schutz F-CA-005 / TC-ADV-018)
        return "[" + " || ".join(str(x) for x in item) + "]"
    if isinstance(item, str):
        return item
    if isinstance(item, dict):
        # F-CA-005 / TC-ADV-016: dict-Item -> WARN UNKNOWN_CP_ITEM_TYPE,
        # rendern via str(item) (raw repr).
        _emit_warn(f"UNKNOWN_CP_ITEM_TYPE: dict {item!r}")
        return str(item)
    return str(item)


def _sequences_consistent(explicit: list, dag_sort: list) -> tuple[bool, list]:
    """Vergleicht explicit (YAML-deklarierte critical_path) mit dag_sort
    (DAG-Topo-Sort). Returns (is_consistent: bool, mismatch_items: list).

    F-CA-005 Subset/Superset/Reihenfolge-Inversion-Logic:
    - Items in BEIDEN Listen muessen in gleicher Reihenfolge sein (gemeinsame Subsequenz).
    - Items NUR in explicit (z.B. POST-MVP-strings) -> kein Mismatch.
    - Items NUR in dag_sort (z.B. Tasks die explicit auslaesst) -> kein Mismatch.
    - Reihenfolge-Inversion in gemeinsamen Items -> mismatch_items + WARN.
    - Parallel-Listen [M1, M1.5] in explicit werden als Set behandelt
      (Reihenfolge innerhalb parallel egal).
    """
    if not explicit or not dag_sort:
        return True, []

    # Normalisiere explicit: parallel-Listen werden zu Sets (frozenset fuer hashability)
    def _flat_items(seq):
        """Flatten parallel-Listen aber merken welche Items parallel sind."""
        flat = []
        for item in seq:
            if isinstance(item, list):
                # Parallel-Liste: alle items zaehlen einzeln, aber als gemeinsamer Set-Marker
                for sub in item:
                    flat.append(("parallel", str(sub)))
            else:
                flat.append(("seq", str(item) if item is not None else ""))
        return flat

    flat_explicit = _flat_items(explicit)
    flat_dag = _flat_items(dag_sort)

    # Common items (str-key): die gemeinsame Subsequenz
    explicit_keys = [key for _, key in flat_explicit]
    dag_keys = [key for _, key in flat_dag]
    common = set(explicit_keys) & set(dag_keys)
    if not common:
        return True, []  # keine Ueberschneidung -> kein Drift

    # Reihenfolge-Vergleich der gemeinsamen Items
    # Filter: nur common-Items aus beiden Sequenzen
    explicit_common = [k for k in explicit_keys if k in common]
    dag_common = [k for k in dag_keys if k in common]

    # Parallel-Items in explicit: setze sie als "frei rotierbar".
    # Vereinfachung: wenn explicit_common != dag_common in Reihenfolge UND
    # nicht via parallel-Slot erklaert: mismatch.
    parallel_keys = {key for kind, key in flat_explicit if kind == "parallel"}

    mismatch = []
    # Brute-force: walk parallel beide Sequenzen, sammle mismatching Positionen.
    # Wenn beide gleich -> consistent.
    if explicit_common == dag_common:
        return True, []

    # Bevor wir mismatch melden: wenn alle "abweichende" Positionen reine
    # parallel-Slot-Permutationen sind, akzeptieren wir.
    # Heuristik: wenn nach Entfernen aller parallel_keys aus beiden Sequenzen
    # die Reste gleich sind -> consistent.
    e_seq_only = [k for k in explicit_common if k not in parallel_keys]
    d_seq_only = [k for k in dag_common if k not in parallel_keys]
    if e_seq_only == d_seq_only:
        return True, []

    # Mismatch: liste die divergierenden Items
    for pos, (e, d) in enumerate(zip(explicit_common, dag_common, strict=False)):
        if e != d:
            mismatch.append({"pos": pos, "explicit": e, "dag": d})
    if len(explicit_common) != len(dag_common):
        mismatch.append({"length_diff": len(explicit_common) - len(dag_common)})
    return False, mismatch


def _topo_sort_legacy(
    tasks: dict,
    milestones: dict[str, Milestone],
    target: str,
) -> list:
    """Wrapper fuer die existierende Task-DAG-Topo-Sort-Logik (umbenannt).
    4-stufiger-Lookup-Stufe-4 Last-Resort.

    Wraps die ehemalige Body-Logik von compute_critical_path. Bei target leer
    oder tasks empty: returnt []."""
    return _compute_critical_path_dag(tasks, milestones, target)


def _hashable_cp_set(critical_path: list) -> set:
    """Task 435 (F-C-P2-003): build set fuer 'in cp' Lookup ohne TypeError
    auf Mixed-Items. parallel-Listen werden zu frozenset, dict-items zu repr,
    None wird ignoriert."""
    out: set = set()
    for item in critical_path or []:
        if item is None:
            continue
        if isinstance(item, list):
            try:
                out.add(frozenset(item))
            except TypeError:
                # nested unhashables -> repr-fallback
                out.add(repr(item))
            # plus jedes individuelle Item (fuer task-id-Lookup auf parallel-content)
            for sub in item:
                if isinstance(sub, (str, int)) and not isinstance(sub, bool):
                    out.add(sub)
            continue
        if isinstance(item, dict):
            out.add(repr(item))
            continue
        try:
            out.add(item)
        except TypeError:
            out.add(repr(item))
    return out


def compute_critical_path(
    tasks: dict,
    milestones: dict[str, Milestone],
    target: str,
    plan_data: dict | None = None,
) -> list:
    """Task 435 (F-C-003 Option 1, Amendment-001):
    4-stufiger Lookup mit Konsistenz-Validation.

    Stufen:
      1. plan_data["critical_path"] (Greenfield-Authority) -> 1:1 als Authority
      2. plan_data["critical_path_feature_view"] (pre-Greenfield)
      3. plan_data["legacy_critical_path_sequence"] (legacy)
      4. DAG-Topological-Sort (Last-Resort)

    Konsistenz-Validation: vergleicht explicit mit DAG-Sort,
    WARN CRITICAL_PATH_MISMATCH bei Drift.

    Skip-Conditions (F-C-P2-004 + F-CA-005 Mitigation):
      - target leer -> skip Drift-Detection
      - tasks empty -> skip
      - DAG-Sort empty -> skip
      - target unknown -> WARN UNKNOWN_TARGET + skip Drift
    """
    # warnings via _emit_warn

    if plan_data is None:
        plan_data = {}

    # Stufe 1-3: explicit Top-Level-Keys.
    # F-CA-005 Edge-Case TC-ADV-007: leere Liste critical_path: [] is legitim.
    # Wir nutzen `if "key" in dict` Pattern statt `or`-Fallthrough fuer Stufe 1.
    explicit: list | None = None
    if "critical_path" in plan_data:
        v = plan_data["critical_path"]
        if isinstance(v, list):
            explicit = v
    if explicit is None and plan_data.get("critical_path_feature_view"):
        v = plan_data["critical_path_feature_view"]
        if isinstance(v, list):
            explicit = v
    if explicit is None and plan_data.get("legacy_critical_path_sequence"):
        v = plan_data["legacy_critical_path_sequence"]
        if isinstance(v, list):
            explicit = v

    if explicit is not None:
        # Konsistenz-Validation skip-Conditions
        skip_drift = False

        # F-C-P2-004: target leer -> skip
        if not target:
            skip_drift = True

        # F-CA-005 / TC-ADV-019 UNKNOWN_TARGET: target ist weder Milestone-Key
        # noch Task-Id im scope -> WARN, skip Drift.
        target_known = (
            (target in milestones)
            or (
                isinstance(target, str)
                and target.isdigit()
                and int(target) in tasks
            )
        )
        if target and not target_known:
            _emit_warn(f"UNKNOWN_TARGET: target {target!r} not in milestones/tasks")
            skip_drift = True

        # tasks empty + milestones empty -> skip
        if not tasks and not milestones:
            skip_drift = True

        if not skip_drift:
            # Milestone-DAG-Sort: nutzt requires-Felder der Milestones zur
            # Reihenfolge-Drift-Detection auf Milestone-Key-Ebene.
            # Faellt auf Task-DAG zurueck wenn Milestone-Drift-Sort leer.
            dag_sort: list = []
            if target in milestones:
                try:
                    dag_sort = _build_milestone_order(milestones, target)
                except Exception:
                    dag_sort = []
            if not dag_sort and tasks:
                try:
                    dag_sort = _topo_sort_legacy(tasks, milestones, target)
                except Exception:
                    dag_sort = []
            if dag_sort:
                consistent, mismatch = _sequences_consistent(explicit, dag_sort)
                if not consistent:
                    _emit_warn(
                        f"CRITICAL_PATH_MISMATCH: YAML={explicit} DAG={dag_sort} "
                        f"mismatch_items={mismatch}"
                    )
        return explicit

    # Stufe 4: DAG-Topological-Sort (Last-Resort)
    return _topo_sort_legacy(tasks, milestones, target)


def _compute_critical_path_dag(
    tasks: dict,
    milestones: dict[str, Milestone],
    target: str,
) -> list:
    """Original Body von compute_critical_path (DAG-Topo-Sort).
    Renamed fuer 4-stufigen-Lookup-Stufe-4. Keine Verhaltensaenderung.

    Cross-milestone dependencies: milestones are processed in requires-order.
    For each milestone M that requires R, entry tasks of M (tasks with no
    in-scope blocked_by) get a virtual dependency on the exit task of R
    (task with highest dist in R).

    Task 367: In aggregate mode, blocked_by entries can cross repo boundaries.
    """
    if not target:
        return []
    if not tasks:
        return []
    if target not in milestones:
        return []
    ms_order = _build_milestone_order(milestones, target)
    relevant_milestones = set(ms_order)

    # Scope: non-terminal tasks in relevant milestones
    scope = {
        tid: t for tid, t in tasks.items()
        if not t.is_terminal and t.milestone in relevant_milestones
    }
    if not scope:
        return []

    # Task 367: In aggregate mode ONLY, expand scope via backward-walk on
    # blocked_by to include cross-repo predecessor milestones. Single-repo
    # mode keeps its original semantics (critical path scoped strictly to
    # milestones on target's requires-chain) to preserve regression.
    # Aggregate mode is detected by any task having a non-empty _repo marker.
    is_aggregate = any(t._repo for t in tasks.values())
    if is_aggregate:
        changed = True
        while changed:
            changed = False
            extra_ms: set[str] = set()
            for t in scope.values():
                for dep in t.blocked_by:
                    dep_t = tasks.get(dep)
                    if dep_t is None or dep_t.is_terminal:
                        continue
                    if dep_t.milestone and dep_t.milestone not in relevant_milestones:
                        extra_ms.add(dep_t.milestone)
            if extra_ms:
                relevant_milestones |= extra_ms
                # Rebuild scope to include tasks from the newly-added milestones.
                scope = {
                    tid: t for tid, t in tasks.items()
                    if not t.is_terminal and t.milestone in relevant_milestones
                }
                changed = True

        # Rebuild ms_order with a topo-sort that accounts for both (a) milestone
        # requires and (b) inter-milestone task-level blocked_by edges. This
        # ensures DP processes prerequisite milestones first even when they
        # come from a different repo.
        if relevant_milestones != set(ms_order):
            ms_deps: dict[str, set[str]] = {mk: set() for mk in relevant_milestones}
            for mk in relevant_milestones:
                m = milestones.get(mk)
                if not m:
                    continue
                for req in m.requires or []:
                    if req in relevant_milestones:
                        ms_deps[mk].add(req)
            for t in scope.values():
                for dep in t.blocked_by:
                    dep_t = tasks.get(dep)
                    if dep_t is None or dep_t.is_terminal:
                        continue
                    if dep_t.milestone and dep_t.milestone != t.milestone \
                            and dep_t.milestone in relevant_milestones:
                        ms_deps[t.milestone].add(dep_t.milestone)
            in_deg = {mk: len(ms_deps[mk]) for mk in relevant_milestones}
            q_ms = deque(mk for mk, d in in_deg.items() if d == 0)
            new_order: list[str] = []
            while q_ms:
                mk = q_ms.popleft()
                new_order.append(mk)
                for other, deps in ms_deps.items():
                    if mk in deps:
                        deps.discard(mk)
                        in_deg[other] -= 1
                        if in_deg[other] == 0:
                            q_ms.append(other)
            remaining = [mk for mk in relevant_milestones if mk not in new_order]
            ms_order = new_order + remaining

    scope_ids = set(scope.keys())

    # Group tasks by milestone
    ms_tasks: dict[str, list[int]] = defaultdict(list)
    for tid, t in scope.items():
        ms_tasks[t.milestone].append(tid)

    # Global dist and prev (accumulated across milestones)
    dist: dict[int, int] = {}
    prev: dict[int, int | None] = {}
    milestone_exit_task: dict[str, int] = {}

    # Process milestones in topological order (prereqs first)
    for mk in ms_order:
        m = milestones.get(mk)
        if not m:
            continue

        m_tids = ms_tasks.get(mk, [])
        if not m_tids:
            continue

        # Collect virtual predecessors from prerequisite milestones
        virtual_pred_dist = 0
        virtual_pred_tid = None
        for req_key in (m.requires or []):
            exit_tid = milestone_exit_task.get(req_key)
            if exit_tid is not None and exit_tid in dist:
                if dist[exit_tid] > virtual_pred_dist:
                    virtual_pred_dist = dist[exit_tid]
                    virtual_pred_tid = exit_tid

        # Topo sort tasks within this milestone (using blocked_by within scope)
        local_in_deg = dict.fromkeys(m_tids, 0)
        local_successors: dict[int, list[int]] = defaultdict(list)
        m_tids_set = set(m_tids)

        for tid in m_tids:
            for dep in scope[tid].blocked_by:
                if dep in m_tids_set:
                    local_in_deg[tid] += 1
                    local_successors[dep].append(tid)

        topo_queue = deque(tid for tid in m_tids if local_in_deg[tid] == 0)
        topo_order = []
        while topo_queue:
            tid = topo_queue.popleft()
            topo_order.append(tid)
            for succ in local_successors[tid]:
                local_in_deg[succ] -= 1
                if local_in_deg[succ] == 0:
                    topo_queue.append(succ)

        # DP: longest path for tasks in this milestone
        for tid in topo_order:
            t = scope[tid]
            best_pred_d = 0
            best_pred = None

            # Check explicit blocked_by (within scope, including cross-milestone)
            for dep in t.blocked_by:
                if dep in dist and dist[dep] > best_pred_d:
                    best_pred_d = dist[dep]
                    best_pred = dep

            # Check virtual predecessor (from requires chain)
            # Only applies to entry tasks (no in-scope blocked_by within this milestone)
            is_entry = not any(dep in m_tids_set for dep in t.blocked_by)
            if is_entry and virtual_pred_tid is not None:
                if virtual_pred_dist > best_pred_d:
                    best_pred_d = virtual_pred_dist
                    best_pred = virtual_pred_tid

            dist[tid] = t.effort_weight + best_pred_d
            prev[tid] = best_pred

        # Exit task: highest dist in this milestone
        if m_tids:
            computed_tids = [tid for tid in m_tids if tid in dist]
            if computed_tids:
                milestone_exit_task[mk] = max(computed_tids, key=lambda x: dist[x])

    if not dist:
        return []

    # Find endpoint: prefer tasks in the target milestone
    target_tids = [tid for tid in ms_tasks.get(target, []) if tid in dist]
    if target_tids:
        end_tid = max(target_tids, key=lambda x: dist[x])
    else:
        end_tid = max(dist, key=lambda x: dist[x])

    # Reconstruct path
    path = []
    cur: int | None = end_tid
    while cur is not None:
        path.append(cur)
        cur = prev.get(cur)
    path.reverse()
    return path


def compute_blocking_score(
    tasks: dict,
    milestones: dict[str, Milestone],
) -> dict:
    """For each task, count how many non-done tasks would be transitively unblocked.

    Includes cross-milestone effects: if completing task X causes milestone M
    to become done, then tasks in milestones that require M become unblocked.

    Task 367: Uses t.key (namespaced string in aggregate mode, int in single-
    repo) so the same graph code works for both modes.
    """
    # Build reverse graph: task → tasks that are blocked by it
    dependents = defaultdict(list)
    for t in tasks.values():
        for dep in t.blocked_by:
            dependents[dep].append(t.key)

    # Build milestone → tasks mapping and reverse requires
    ms_tasks = defaultdict(list)
    for t in tasks.values():
        ms_tasks[t.milestone].append(t.key)
    # milestone → milestones that require it
    ms_dependents = defaultdict(list)
    for m in milestones.values():
        for req in m.requires:
            ms_dependents[req].append(m.key)

    actually_done = {t.key for t in tasks.values() if t.is_done}

    # Precompute gate results ONCE — avoids re-evaluating script gates
    # inside the per-task loop (which would spawn 139× subprocesses)
    gate_cache: dict[str, bool] = {}
    for m in milestones.values():
        if m.is_group:
            continue
        gate_cache[m.key] = all(g.check(tasks)[0] for g in m.gate) if m.gate else True

    scores = {}
    for tid in tasks:
        if tasks[tid].is_terminal:
            scores[tid] = 0
            continue

        # Simulate: what if tid becomes done?
        sim_done = actually_done | {tid}
        unblocked = set()

        # Phase 1: direct task-level unblocking (BFS)
        check_queue = deque(dependents.get(tid, []))
        while check_queue:
            candidate = check_queue.popleft()
            if candidate in unblocked or candidate in sim_done:
                continue
            ct = tasks.get(candidate)
            if not ct or ct.is_terminal:
                continue
            if all(d in sim_done for d in ct.blocked_by):
                unblocked.add(candidate)
                sim_done.add(candidate)
                for further in dependents.get(candidate, []):
                    check_queue.append(further)

        # Phase 2: check if any milestone becomes done, unlocking downstream milestones
        # Recompute which milestones would be done with sim_done
        sim_done_milestones = set()
        for m in milestones.values():
            if m.is_group:
                continue
            m_tids = ms_tasks.get(m.key, [])
            all_m_tasks_done = all(
                tid_m in sim_done for tid_m in m_tids
                if tid_m in tasks and not tasks[tid_m].is_terminal
            ) if m_tids else True
            gate_pass = gate_cache.get(m.key, True)
            if all_m_tasks_done and gate_pass:
                sim_done_milestones.add(m.key)

        # Original done milestones (before simulation)
        orig_done_milestones = set()
        for m in milestones.values():
            if m.status == "done":
                orig_done_milestones.add(m.key)

        # Newly done milestones
        newly_done_ms = sim_done_milestones - orig_done_milestones

        # For each newly done milestone, find downstream milestones that become unblocked
        if newly_done_ms:
            # Find tasks in milestones that were blocked by the now-done milestones
            for new_ms_key in newly_done_ms:
                for dependent_ms_key in ms_dependents.get(new_ms_key, []):
                    dep_m = milestones.get(dependent_ms_key)
                    if not dep_m:
                        continue
                    # Check if ALL requires of this dependent milestone are now done
                    all_reqs_done = all(
                        r in sim_done_milestones or r in orig_done_milestones
                        for r in dep_m.requires
                    )
                    if all_reqs_done:
                        # Tasks in this milestone become unblocked (milestone-level)
                        for m_tid in ms_tasks.get(dependent_ms_key, []):
                            if m_tid in sim_done or m_tid in unblocked:
                                continue
                            mt = tasks.get(m_tid)
                            if not mt or mt.is_terminal:
                                continue
                            # Still check task-level deps
                            if all(d in sim_done for d in mt.blocked_by):
                                unblocked.add(m_tid)

        scores[tid] = len(unblocked)
    return scores


def compute_next_actions(
    tasks: dict,
    milestones: dict[str, Milestone],
    critical_path: list,
    blocking_scores: dict,
    target: str,
    limit: int = 10,
) -> list:
    """Tasks that are ready to start, sorted by priority.

    Sort order: (1) on critical path, (2) on target path (milestone is target
    or in requires-chain of target), (3) blocking score desc, (4) effort asc.
    This ensures MVP-path tasks rank above non-MVP tasks even when milestones
    like intelligence/life-os are technically unblocked.

    Task 367: Uses t.key throughout so the same logic applies to aggregate mode.
    """
    cp_set = _hashable_cp_set(critical_path)
    done_keys = {t.key for t in tasks.values() if t.is_done}

    # Compute target path: milestones in the requires-chain of the target
    target_path_ms = set()
    queue = deque([target])
    while queue:
        mk = queue.popleft()
        if mk in target_path_ms:
            continue
        target_path_ms.add(mk)
        m = milestones.get(mk)
        if m:
            for req in m.requires:
                queue.append(req)

    ready = []
    for t in tasks.values():
        if t.status != "pending":
            continue
        if t.has_external_deps:
            continue
        # All blocked_by must be done
        if not all(d in done_keys for d in t.blocked_by):
            continue
        # Milestone must not be blocked/future
        m = milestones.get(t.milestone)
        if m and m.status in ("blocked", "future"):
            continue
        ready.append(t.key)

    # Sort: critical path > target path > blocking score > effort
    ready.sort(key=lambda tk: (
        0 if tk in cp_set else 1,                            # critical path first
        0 if tasks[tk].milestone in target_path_ms else 1,   # target-path milestones next
        -blocking_scores.get(tk, 0),                         # higher blocking score first
        tasks[tk].effort_weight,                             # smaller effort first
        str(tk),                                             # stable fallback (str works for both modes)
    ))
    return ready[:limit]


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def validate(
    tasks: dict,
    milestones: dict[str, Milestone],
    archived_ids: set | None = None,
) -> list[ValidationIssue]:
    """Validate tasks + milestones.

    Task 367: uses t.key (namespaced in aggregate).
    Task 435 (F-C-P2-001 Variante c): archived_ids -> Silent-Pass fuer
    BROKEN_DEP wenn target_id in archived_ids set. Wenn archived_ids=None:
    auto-load aus PROJECT_ROOT (F-CA-001 explicit project_root via module-global).

    Task 435 Iteration 2 (CA-002 Fix): archived_ids ist ein set[int] in
    Single-Repo-Mode UND set[str] in Aggregate-Mode (namespaced
    "<repo>#<id:03d>"). Membership-Check via direktem `dep in archived_ids` —
    set-Lookup ist type-safe (Bool-Werte werden in load_archived_task_ids
    bereits gerejected, also keine Pythonic 0==False/1==True-Kollision moeglich).
    """
    if archived_ids is None:
        # Auto-load: Variante c muss automatisch greifen — caller ohne explicit
        # archived_ids bekommt trotzdem Silent-Pass-Verhalten (CLI-Pfade,
        # Test-direkt-Aufrufe wie ADV_029). PROJECT_ROOT-relativ (F-CA-001).
        archived_ids = load_archived_task_ids(PROJECT_ROOT)
    issues = []
    task_keys = set(tasks.keys())

    for t in tasks.values():
        tid_for_issue = t.key  # Task 367: namespaced in aggregate mode
        # NO_MILESTONE (terminal tasks may have null milestone — they're completed)
        if not t.milestone and not t.is_terminal:
            issues.append(ValidationIssue("NO_MILESTONE", "ERROR", task_id=tid_for_issue,
                                          detail="task has no milestone field"))
        elif not t.milestone and t.is_terminal:
            pass  # terminal tasks without milestone are fine
        elif t.milestone not in milestones:
            severity = "WARN" if t.is_terminal else "ERROR"
            issues.append(ValidationIssue("UNKNOWN_MILESTONE", severity, task_id=tid_for_issue,
                                          detail=f"milestone '{t.milestone}' not in plan.yaml"))
        # BROKEN_DEP (Task 435 Variante c Silent-Pass: archived Tasks skipped)
        for dep in t.blocked_by:
            if dep not in task_keys:
                # F-C-P2-001 Silent-Pass: archived id -> kein ERR.
                # CA-002 Iteration 2: archived_ids ist set[int] (single-repo)
                # ODER set[str] (aggregate, "<repo>#<id:03d>"). Direkter
                # set-Membership-Check funktioniert in beiden Modi.
                if dep in archived_ids:
                    continue
                issues.append(ValidationIssue("BROKEN_DEP", "ERROR", task_id=tid_for_issue,
                                              detail=f"blocked_by {dep} not found"))
        # DEAD_DEP
        for dep in t.blocked_by:
            dep_t = tasks.get(dep)
            if dep_t and dep_t.status in TERMINAL_STATUSES - {"done"}:
                issues.append(ValidationIssue("DEAD_DEP", "ERROR", task_id=tid_for_issue,
                                              detail=f"blocked_by {dep} is {dep_t.status}"))
        # NO_EFFORT
        if t.status in ("pending", "in_progress") and not t.effort:
            issues.append(ValidationIssue("NO_EFFORT", "ERROR", task_id=tid_for_issue,
                                          detail="pending/in_progress without effort"))
        # STALE_BLOCKED
        if t.status == "blocked":
            done_keys = {tk for tk, tt in tasks.items() if tt.is_done}
            if all(d in done_keys for d in t.blocked_by):
                issues.append(ValidationIssue("STALE_BLOCKED", "WARN", task_id=tid_for_issue,
                                              detail="status=blocked but all deps done"))
        # EXTERNAL_DEP
        if t.has_external_deps:
            issues.append(ValidationIssue("EXTERNAL_DEP", "WARN", task_id=tid_for_issue,
                                          detail="has blocked_by_external"))
        # DECOMPOSE — XL tasks should be broken into sub-tasks
        if t.effort == "XL" and t.status in ("pending", "in_progress"):
            issues.append(ValidationIssue("DECOMPOSE", "WARN", task_id=tid_for_issue,
                                          detail="effort=XL — consider decomposing into sub-tasks"))

        # SPEC_STATES validation
        if t.spec_states:
            if not isinstance(t.spec_states, dict):
                issues.append(ValidationIssue(
                    "SPEC_STATES_TYPE", "ERROR", task_id=tid_for_issue,
                    detail="spec_states is not a dict",
                ))
                continue
            for spec_name, state in t.spec_states.items():
                if not isinstance(state, dict):
                    issues.append(ValidationIssue(
                        "SPEC_STATE_TYPE", "ERROR", task_id=tid_for_issue,
                        detail=f"spec_states[{spec_name}] is not a dict",
                    ))
                    continue
                phase = state.get("current_phase", "")
                if phase not in SPEC_PHASE_ENUM:
                    issues.append(ValidationIssue(
                        "SPEC_PHASE_ENUM", "ERROR", task_id=tid_for_issue,
                        detail=f"spec_states[{spec_name}].current_phase "
                               f"'{phase}' not in {sorted(SPEC_PHASE_ENUM)}",
                    ))
                rp = state.get("review_passes", 0)
                fp = state.get("fix_passes", 0)
                if not isinstance(rp, int) or rp < 0:
                    issues.append(ValidationIssue(
                        "SPEC_PASSES_TYPE", "ERROR", task_id=tid_for_issue,
                        detail=f"spec_states[{spec_name}].review_passes "
                               f"must be int >= 0, got {rp!r}",
                    ))
                if not isinstance(fp, int) or fp < 0:
                    issues.append(ValidationIssue(
                        "SPEC_PASSES_TYPE", "ERROR", task_id=tid_for_issue,
                        detail=f"spec_states[{spec_name}].fix_passes "
                               f"must be int >= 0, got {fp!r}",
                    ))
                # Transition consistency: reviewing/fixing/ready require review_passes > 0
                if (phase in ("reviewing", "fixing", "ready")
                        and isinstance(rp, int) and rp <= 0):
                    issues.append(ValidationIssue(
                        "SPEC_PHASE_CONSISTENCY", "ERROR", task_id=tid_for_issue,
                        detail=f"spec_states[{spec_name}].current_phase={phase} "
                               f"but review_passes={rp} (must be > 0)",
                    ))

    # Spec duplicate check: same spec in spec_states of 2+ active tasks
    spec_owners: dict[str, list] = defaultdict(list)
    for t in tasks.values():
        if t.status in {"superseded", "absorbed"}:
            continue
        for spec_name in t.spec_states:
            spec_owners[spec_name].append(t.key)
    for spec_name, owner_keys in spec_owners.items():
        if len(owner_keys) > 1:
            ids_str = ", ".join(str(tk) for tk in sorted(owner_keys, key=str))
            issues.append(ValidationIssue(
                "SPEC_DUPLICATE", "WARN",
                detail=f"spec '{spec_name}' tracked in multiple active tasks: {ids_str}",
            ))

    # Cycle detection (simplified — check if topo sort covers all).
    # Task 367: iterate via t.key (polymorphic int/str).
    in_deg = dict.fromkeys(tasks, 0)
    for t in tasks.values():
        for dep in t.blocked_by:
            if dep in in_deg:
                in_deg[t.key] += 1
    queue = deque(tk for tk, d in in_deg.items() if d == 0)
    visited = set()
    while queue:
        tk = queue.popleft()
        visited.add(tk)
        for t2 in tasks.values():
            if tk in t2.blocked_by:
                in_deg[t2.key] -= 1
                if in_deg[t2.key] == 0:
                    queue.append(t2.key)
    unvisited = set(tasks.keys()) - visited
    if unvisited:
        issues.append(ValidationIssue("CYCLE", "ERROR",
                                      detail=f"cycle involving tasks: {sorted(unvisited, key=str)}"))

    # Milestone checks
    for m in milestones.values():
        if not m.is_group and not m.tasks and m.status in ("ready", "active"):
            issues.append(ValidationIssue("ORPHAN_MILESTONE", "WARN",
                                          milestone_key=m.key,
                                          detail=f"0 tasks, status={m.status}"))
        open_count = sum(1 for tid in m.tasks
                        if tid in tasks and not tasks[tid].is_terminal)
        if not m.is_group and open_count > 15 and m.status not in ("future", "done"):
            issues.append(ValidationIssue("LARGE_MILESTONE", "WARN",
                                          milestone_key=m.key,
                                          detail=f"{open_count} open tasks (of {len(m.tasks)} total)"))
        # GATE_TASK_DRIFT: gate passes but tasks still pending AND none in progress
        # (if tasks are in_progress, gate PASS is expected — prerequisites met)
        if m.gate and not m.is_group:
            all_gate_pass = all(g.check(tasks)[0] for g in m.gate)
            non_done = [tid for tid in m.tasks
                        if tid in tasks and not tasks[tid].is_terminal and not tasks[tid].is_done]
            has_active = any(tasks[tid].status == "in_progress"
                             for tid in m.tasks if tid in tasks)
            if all_gate_pass and non_done and not has_active:
                ids = ", ".join(str(t) for t in non_done[:5])
                issues.append(ValidationIssue("GATE_TASK_DRIFT", "WARN",
                                              milestone_key=m.key,
                                              detail=f"gate PASS but {len(non_done)} tasks pending: {ids}"))
        # Gate scripts
        for g in m.gate:
            if g.type == "script" and not (PROJECT_ROOT / g.path).exists():
                issues.append(ValidationIssue("SCRIPT_MISSING", "WARN",
                                              milestone_key=m.key,
                                              detail=f"gate script not found: {g.path}"))

        # Requires reference check
        # Task 435 (B-1, F-CA-005): feature_milestones requires-Eintraege
        # koennen sein: milestone-key (str) ODER task-id (int oder digit-str).
        # Task-ID-Refs werden NICHT als UNKNOWN_REQUIRES gewertet wenn die
        # Task existiert (im tasks-dict oder in archived_ids).
        for req in m.requires:
            if isinstance(req, str) and req in milestones:
                continue
            # Numerischer String: als Task-Id behandeln
            if isinstance(req, str) and req.isdigit():
                tid_int = int(req)
                if tid_int in tasks or tid_int in archived_ids:
                    continue
            if isinstance(req, int) and (req in tasks or req in archived_ids):
                continue
            issues.append(ValidationIssue("UNKNOWN_REQUIRES", "ERROR",
                                          milestone_key=m.key,
                                          detail=f"requires '{req}' not in plan.yaml"))

    return issues


# ---------------------------------------------------------------------------
# Autonomy Consistency (framework/agent-autonomy.md SoT)
# ---------------------------------------------------------------------------

# SoT-Datei der Autonomy-Regeln. Mirror-Check, Existenz-Check, Referenz-
# Integritaet und Drift-Warnung werden gegen dieses Dokument gefahren.
# Framework-intern → FRAMEWORK_ROOT (Task 010 Part L0).
AUTONOMY_SOT_PATH = FRAMEWORK_ROOT / "framework" / "agent-autonomy.md"

# Dateien, in denen der Verweis auf framework/agent-autonomy.md existieren
# MUSS (Check 3, Referenz-Integritaet). Relativ zu FRAMEWORK_ROOT.
AUTONOMY_REFERENCE_FILES = [
    "CLAUDE.md",
    "AGENTS.md",
    "agents/buddy/operational.md",
    "workflows/runbooks/solve/WORKFLOW.md",
]


def _extract_section(text: str, header_pattern: str) -> str | None:
    """Extrahiere Inhalt einer Markdown-Sektion.

    header_pattern: Regex, der auf den Sektions-Header matched (inkl. ### Prefix).
    Gibt den Block inkl. Header bis zum naechsten Header gleicher oder
    hoeherer Ebene (###) zurueck. None wenn nicht gefunden.
    """
    import re
    lines = text.split("\n")
    start = None
    for i, line in enumerate(lines):
        if re.match(header_pattern, line):
            start = i
            break
    if start is None:
        return None
    end = len(lines)
    for j in range(start + 1, len(lines)):
        # Naechster Header gleicher Ebene (###) oder hoeher (##, #)
        if lines[j].startswith("### ") or lines[j].startswith("## ") or lines[j].startswith("# "):
            end = j
            break
    return "\n".join(lines[start:end])


def _extract_sections_containing(text: str, needle: str) -> dict[str, str]:
    """Extrahiere alle `###`-Sektionen, deren Inhalt `needle` enthaelt.

    Rueckgabe: dict mapping `title_key → section_text` (inkl. Header-Zeile bis
    zum naechsten gleich- oder hoeherrangigen Header). Der `title_key` ist der
    Header-Text ohne Prefix-`### ` und ohne fuehrende Sektions-Nummer
    (`5. `, `5.1 `, etc.) — das erlaubt robustes Matching zwischen zwei
    Dateien, auch wenn die Nummerierung auseinanderlaeuft.

    Hintergrund (F-C-014): Der Mirror-Check darf nicht mehr an die feste
    Header-Nummer `### 5. Code-Delegation` gebunden sein. Stattdessen werden
    alle Sektionen gespiegelt, die den SoT-Pfad `framework/agent-autonomy.md`
    erwaehnen.
    """
    import re
    lines = text.split("\n")
    # Indizes der `###`-Header (und Ende bei `##` oder `#`).
    header_indices: list[int] = []
    for i, line in enumerate(lines):
        if line.startswith("### "):
            header_indices.append(i)
        elif line.startswith(("## ", "# ")):
            header_indices.append(i)  # Sentinel als Grenze
    # Fuer jeden `###`-Header die Sektion bis zum naechsten Header extrahieren.
    num_prefix_re = re.compile(r"^\d+(?:\.\d+)*\.?\s+")
    result: dict[str, str] = {}
    for idx, start in enumerate(header_indices):
        if not lines[start].startswith("### "):
            continue
        # Ende = naechster Header-Index (egal welche Ebene)
        end = len(lines)
        if idx + 1 < len(header_indices):
            end = header_indices[idx + 1]
        section = "\n".join(lines[start:end])
        if needle not in section:
            continue
        # Title-Key normalisieren: `### 5. Code-Delegation / Autonomy` →
        # `code-delegation / autonomy`
        header_line = lines[start][4:].strip()  # strip "### "
        title_key = num_prefix_re.sub("", header_line).strip().lower()
        # Kollisionen: bei Duplicate-Headern vermeiden wir Overwrite indem
        # wir nur den ersten behalten — Duplicate-Warnung ist out-of-scope.
        if title_key not in result:
            result[title_key] = section
    return result


def _extract_autonomy_table_routing(text: str) -> list[str]:
    """Extrahiere die Routing-Spalte der Haupttabelle aus agent-autonomy.md.

    Die Tabelle hat Spalten: # | Artefakt-Typ | Pfad-Muster | Permission | Gate | Routing
    Routing ist Spalte 6 (Index 5). Wir sammeln alle rohen Routing-Zellen.
    """
    import re
    lines = text.split("\n")
    in_table = False
    routing_values = []
    for line in lines:
        stripped = line.strip()
        if not stripped.startswith("|"):
            if in_table:
                # Tabelle zu Ende
                break
            continue
        # Tabellen-Zeile
        cells = [c.strip() for c in stripped.strip("|").split("|")]
        if not in_table:
            # Header-Zeile? Pruefe auf "Routing" in Zellen
            if any("Routing" in c for c in cells) and any("Permission" in c for c in cells):
                in_table = True
            continue
        # Separator-Zeile (---|---|...) ueberspringen
        if all(re.match(r"^-+$", c) for c in cells if c):
            continue
        # Daten-Zeile — Routing ist die letzte Spalte (bei 6 Spalten Index 5)
        if len(cells) >= 6:
            routing_values.append(cells[5])
    return routing_values


def _extract_autonomy_table_gate_peers(text: str) -> list[str]:
    """Extrahiere `peer:<agent>` Targets aus der Gate-Spalte der Haupttabelle.

    Hintergrund (F-C-002): Die Gate-Polymorphie in agent-autonomy.md erlaubt
    Merger-Faelle, bei denen ein Peer-Konsultations-Gate gleichzeitig die
    Routing-Antwort traegt (z.B. `peer:council`, `peer:solution-expert`).
    Ein Drift-Check, der nur die Routing-Spalte liest, meldet diese Agenten
    faelschlich als "in operational.md aber nicht in agent-autonomy.md".

    Diese Funktion scannt die Gate-Spalte (Index 4) und gibt alle Tokens
    nach einem `peer:`-Prefix zurueck. `review:*` Gates werden bewusst
    ignoriert (das sind Skill-Gates, keine Agenten).
    """
    import re
    lines = text.split("\n")
    in_table = False
    peers: list[str] = []
    peer_re = re.compile(r"peer:([A-Za-z0-9_-]+)")
    for line in lines:
        stripped = line.strip()
        if not stripped.startswith("|"):
            if in_table:
                break
            continue
        cells = [c.strip() for c in stripped.strip("|").split("|")]
        if not in_table:
            if any("Routing" in c for c in cells) and any("Permission" in c for c in cells):
                in_table = True
            continue
        if all(re.match(r"^-+$", c) for c in cells if c):
            continue
        # Daten-Zeile — Gate ist Index 4 (bei 6 Spalten: 0=#, 1=Typ, 2=Pfad,
        # 3=Permission, 4=Gate, 5=Routing).
        if len(cells) >= 6:
            gate_cell = cells[4]
            for match in peer_re.finditer(gate_cell):
                peers.append(match.group(1))
    return peers


def _extract_operational_routing_agents(text: str) -> list[str]:
    """Extrahiere die Agent-Spalte aus der Delegation-Routing-Tabelle in operational.md.

    Die Tabelle hat Spalten: | Thema | Agent |
    """
    import re
    lines = text.split("\n")
    in_table = False
    agents = []
    for line in lines:
        stripped = line.strip()
        if not stripped.startswith("|"):
            if in_table:
                break
            continue
        cells = [c.strip() for c in stripped.strip("|").split("|")]
        if not in_table:
            if any("Agent" in c for c in cells) and any("Thema" in c for c in cells):
                in_table = True
            continue
        if all(re.match(r"^-+$", c) for c in cells if c):
            continue
        if len(cells) >= 2:
            agents.append(cells[1])
    return agents


def validate_autonomy_consistency() -> list[ValidationIssue]:
    """Autonomy-Consistency-Checks (framework-ambiguity-audit Fund 1, Phase 3).

    Prueffaelle:
      Check 1 — Mirror-Check CLAUDE.md §5 ↔ AGENTS.md §5 (ERROR bei Abweichung)
      Check 2 — Existenz-Check framework/agent-autonomy.md (ERROR bei Fehlern)
      Check 3 — Referenz-Integritaet in Konsumenten-Dateien (ERROR pro fehlendem Verweis)
      Check 4 — Cross-Reference Drift-Warnung operational.md ↔ agent-autonomy.md (WARN)
    """
    import re
    issues: list[ValidationIssue] = []

    # Check 1: Mirror-Check CLAUDE.md ↔ AGENTS.md
    # F-C-014: Scope ist nicht mehr die feste Sektion "### 5. Code-Delegation",
    # sondern alle `###`-Sektionen, die den SoT-Pfad `framework/agent-autonomy.md`
    # erwaehnen. Matching der korrespondierenden Sektionen erfolgt ueber den
    # normalisierten Header-Text (Nummer entfernt), damit Nummer-Aenderungen
    # nicht still den Check umgehen koennen.
    claude_path = FRAMEWORK_ROOT / "CLAUDE.md"
    agents_path = FRAMEWORK_ROOT / "AGENTS.md"

    if not claude_path.exists():
        issues.append(ValidationIssue(
            "AUTONOMY_MIRROR", "ERROR",
            detail="CLAUDE.md fehlt — Mirror-Check nicht moeglich"))
    elif not agents_path.exists():
        issues.append(ValidationIssue(
            "AUTONOMY_MIRROR", "ERROR",
            detail="AGENTS.md fehlt — Mirror-Check nicht moeglich"))
    else:
        claude_text = claude_path.read_text(encoding="utf-8")
        agents_text = agents_path.read_text(encoding="utf-8")
        claude_sections = _extract_sections_containing(
            claude_text, "framework/agent-autonomy.md")
        agents_sections = _extract_sections_containing(
            agents_text, "framework/agent-autonomy.md")

        if not claude_sections:
            issues.append(ValidationIssue(
                "AUTONOMY_MIRROR", "ERROR",
                detail=("CLAUDE.md: keine '###'-Sektion gefunden, die "
                        "'framework/agent-autonomy.md' erwaehnt — Mirror-"
                        "Anker fehlt")))
        if not agents_sections:
            issues.append(ValidationIssue(
                "AUTONOMY_MIRROR", "ERROR",
                detail=("AGENTS.md: keine '###'-Sektion gefunden, die "
                        "'framework/agent-autonomy.md' erwaehnt — Mirror-"
                        "Anker fehlt")))

        if claude_sections and agents_sections:
            # Symmetrischer Satz-Vergleich: jeder Title-Key muss in beiden
            # Dateien existieren.
            only_in_claude = set(claude_sections) - set(agents_sections)
            only_in_agents = set(agents_sections) - set(claude_sections)
            for tk in sorted(only_in_claude):
                issues.append(ValidationIssue(
                    "AUTONOMY_MIRROR", "ERROR",
                    detail=(f"CLAUDE.md hat Sektion '{tk}' (erwaehnt "
                            f"agent-autonomy.md), die in AGENTS.md fehlt — "
                            f"Sync noetig")))
            for tk in sorted(only_in_agents):
                issues.append(ValidationIssue(
                    "AUTONOMY_MIRROR", "ERROR",
                    detail=(f"AGENTS.md hat Sektion '{tk}' (erwaehnt "
                            f"agent-autonomy.md), die in CLAUDE.md fehlt — "
                            f"Sync noetig")))

            # Fuer Sektionen die in beiden Dateien existieren: Text-Gleichheit.
            # Body ohne die erste Zeile (Header) vergleichen, damit eine
            # unterschiedliche Sektions-Nummer im Header die Sektion nicht
            # faelschlich als "Mismatch" meldet. Der Title-Key-Match oben
            # stellt bereits sicher, dass die Header textlich identisch sind
            # (modulo Nummer-Prefix).
            common = set(claude_sections) & set(agents_sections)
            for tk in sorted(common):
                claude_body = "\n".join(
                    claude_sections[tk].rstrip().split("\n")[1:])
                agents_body = "\n".join(
                    agents_sections[tk].rstrip().split("\n")[1:])
                if claude_body.rstrip() == agents_body.rstrip():
                    continue
                # Diff-Darstellung: erste abweichende Zeile. Zeilennummer
                # ist sektion-relativ (Header = Zeile 1, erste Body-Zeile = 2).
                claude_lines = claude_body.rstrip().split("\n")
                agents_lines = agents_body.rstrip().split("\n")
                diff_line = None
                max_len = max(len(claude_lines), len(agents_lines))
                for i in range(max_len):
                    cl = claude_lines[i] if i < len(claude_lines) else "<EOF>"
                    al = agents_lines[i] if i < len(agents_lines) else "<EOF>"
                    if cl != al:
                        diff_line = (i + 2, cl, al)
                        break
                if diff_line:
                    ln, cl, al = diff_line
                    issues.append(ValidationIssue(
                        "AUTONOMY_MIRROR", "ERROR",
                        detail=(f"CLAUDE.md Sektion '{tk}' != AGENTS.md "
                                f"ab Zeile {ln}: CLAUDE='{cl[:60]}' vs "
                                f"AGENTS='{al[:60]}' — Sync via Edit "
                                f"beider Dateien noetig")))
                else:
                    issues.append(ValidationIssue(
                        "AUTONOMY_MIRROR", "ERROR",
                        detail=(f"CLAUDE.md Sektion '{tk}' != AGENTS.md "
                                f"(Laengenunterschied)")))

    # Check 2: Existenz-Check framework/agent-autonomy.md
    autonomy_text = ""
    if not AUTONOMY_SOT_PATH.exists():
        issues.append(ValidationIssue(
            "AUTONOMY_EXISTS", "ERROR",
            detail=f"{AUTONOMY_SOT_PATH.relative_to(FRAMEWORK_ROOT)} fehlt — "
                   "SoT fuer Permission/Gate/Routing nicht vorhanden"))
    else:
        autonomy_text = AUTONOMY_SOT_PATH.read_text(encoding="utf-8")
        # Header "# Agent Autonomy"
        if not re.search(r"^# Agent Autonomy\s*$", autonomy_text, re.MULTILINE):
            issues.append(ValidationIssue(
                "AUTONOMY_EXISTS", "ERROR",
                detail=f"{AUTONOMY_SOT_PATH.relative_to(FRAMEWORK_ROOT)}: "
                       "Header '# Agent Autonomy' fehlt"))
        # Section "## Tabelle — Artefakt-Typ → Autonomy" (DE) or
        # "## Table — artifact type -> autonomy" (EN, post Task-300 translation).
        # Match either German or English header form.
        table_header_found = False
        for line in autonomy_text.split("\n"):
            if not line.startswith("## "):
                continue
            line_lower = line.lower()
            de_match = ("tabelle" in line_lower and "artefakt-typ" in line_lower)
            en_match = ("table" in line_lower and "artifact" in line_lower
                        and "type" in line_lower)
            if de_match or en_match:
                table_header_found = True
                break
        if not table_header_found:
            issues.append(ValidationIssue(
                "AUTONOMY_EXISTS", "ERROR",
                detail=f"{AUTONOMY_SOT_PATH.relative_to(FRAMEWORK_ROOT)}: "
                       "section header with 'Tabelle'+'Artefakt-Typ' (DE) or "
                       "'Table'+'artifact'+'type' (EN) missing"))

    # Check 3: Referenz-Integritaet in Konsumenten-Dateien
    for rel_path in AUTONOMY_REFERENCE_FILES:
        file_path = FRAMEWORK_ROOT / rel_path
        if not file_path.exists():
            issues.append(ValidationIssue(
                "AUTONOMY_REF", "ERROR",
                detail=f"{rel_path}: Datei fehlt, Referenz-Check nicht moeglich"))
            continue
        content = file_path.read_text(encoding="utf-8")
        # Als Pfad-String oder Markdown-Link. Suche nach dem Pfad-Fragment.
        if "framework/agent-autonomy.md" not in content:
            issues.append(ValidationIssue(
                "AUTONOMY_REF", "ERROR",
                detail=f"{rel_path}: kein Verweis auf "
                       "'framework/agent-autonomy.md' gefunden — Konsument "
                       "muss auf SoT verweisen"))

    # Check 4: Cross-Reference Drift-Warnung (operational.md ↔ agent-autonomy.md)
    # Weicher Check: wenn Agenten in einer Tabelle stehen aber nicht in der
    # anderen, Warning mit Drift-Hinweis. Kein Blocker (unterschiedlicher Scope
    # ist legitim moeglich).
    operational_path = FRAMEWORK_ROOT / "agents" / "buddy" / "operational.md"
    if operational_path.exists() and autonomy_text:
        operational_text = operational_path.read_text(encoding="utf-8")
        op_section = _extract_section(operational_text, r"^### Delegation-Routing")
        if op_section is not None:
            op_agents_raw = _extract_operational_routing_agents(op_section)
            autonomy_routing_raw = _extract_autonomy_table_routing(autonomy_text)
            # F-C-002: Merger-Faelle mitzaehlen — Agenten, die in der
            # Gate-Spalte als `peer:X` auftauchen, sind ebenfalls "bekannt".
            autonomy_gate_peers = _extract_autonomy_table_gate_peers(autonomy_text)

            # Bekannte Rollen-Tokens. Wenn die normalisierte Form eines davon
            # als Wort enthaelt, nehmen wir den Token (grobe Matching-Heuristik).
            known_roles = (
                "main-code-agent", "solution-expert", "buddy", "security",
                # council: Merger-Fall (peer:council in Gate-Spalte = Routing,
                # intentionally NOT in operational.md Delegation-Routing).
                # review-agent: entfernt (existiert nicht, war Phantom).
            )

            def _normalize_agent(s: str) -> str:
                s = s.strip().lower()
                s = s.replace("`", "").replace("*", "")
                # Prefix-Strip fuer agent-autonomy.md Routing-Zellen
                for prefix in ("handoff:", "peer:", "review:"):
                    if s.startswith(prefix):
                        s = s[len(prefix):]
                # Klammer-Suffixe droppen
                if "(" in s:
                    s = s.split("(", 1)[0]
                # Phrase-Tails droppen (" weil ...", " mit ...", " direkt" ...)
                for sep in (" weil ", " mit ", " via ", " direkt",
                            " dispatcht", " schreibt"):
                    if sep in s:
                        s = s.split(sep, 1)[0]
                s = s.strip().strip(",;.:")
                # Wenn ein bekannter Rollen-Token als Wort enthalten ist,
                # nehmen wir den als normalisierte Form (robuster gegen Prosa).
                tokens = re.split(r"\s+", s)
                for role in known_roles:
                    if role in tokens:
                        return role
                return s

            # Agent-Filter: nur Token, die plausibel ein Agent-Name sind
            # (in known_roles oder hyphen-basiert). Alles andere (z.B.
            # "mirror", "plan_engine") ist Mechanismus-Beiwerk und wird
            # als Rauschen verworfen.
            def _looks_like_agent(token: str) -> bool:
                if not token:
                    return False
                if token in known_roles:
                    return True
                # Workflow/Runbook/Skill-Suffixe sind keine Agenten
                # (F-C-003): Zellen wie `handoff:build-workflow oder
                # fix-workflow` koennen `fix-workflow` als hyphen-Token
                # produzieren, das faelschlich als Agent durchrutscht.
                for suffix in ("-workflow", "-runbook", "-skill"):
                    if token.endswith(suffix):
                        return False
                # hyphen-basierte Agent-Namen (z.B. "foo-agent", "bar-expert")
                return bool(re.match(r"^[a-z]+(-[a-z]+)+$", token))

            op_agents_norm = {
                _normalize_agent(a) for a in op_agents_raw if a.strip()
            }
            op_agents_norm = {a for a in op_agents_norm if _looks_like_agent(a)}

            # Aus agent-autonomy.md nehmen wir nur Zellen ohne Workflow-Handoff
            # (diese routen per Workflow, nicht an einen Agent), und zerlegen
            # an "oder"/"/" sowie Kommas fuer multi-agent-Zellen.
            autonomy_agents_norm = set()
            for cell in autonomy_routing_raw:
                cell_l = cell.lower()
                if "handoff:" in cell_l:
                    continue
                parts = re.split(r"\bor\b|\boder\b|/|,", cell, flags=re.IGNORECASE)
                for p in parts:
                    norm = _normalize_agent(p)
                    if norm:
                        autonomy_agents_norm.add(norm)

            # F-C-002: Gate-Peer-Targets als bekannte Agenten mitfuehren
            # (Merger-Fall Gate = Routing). Peers durchlaufen dieselbe
            # Normalisierung wie Routing-Zellen.
            for peer in autonomy_gate_peers:
                norm = _normalize_agent(peer)
                if norm:
                    autonomy_agents_norm.add(norm)

            autonomy_agents_norm = {
                a for a in autonomy_agents_norm if _looks_like_agent(a)
            }

            # Leere Strings aussortieren
            op_agents_norm.discard("")
            autonomy_agents_norm.discard("")

            only_in_op = op_agents_norm - autonomy_agents_norm
            only_in_autonomy = autonomy_agents_norm - op_agents_norm

            if only_in_op:
                issues.append(ValidationIssue(
                    "AUTONOMY_DRIFT", "WARN",
                    detail=(f"operational.md Delegation-Routing listet Agenten, "
                            f"die in agent-autonomy.md Routing-Spalte fehlen: "
                            f"{sorted(only_in_op)} — Drift-Risiko, ggf. "
                            f"agent-autonomy.md erweitern")))
            if only_in_autonomy:
                issues.append(ValidationIssue(
                    "AUTONOMY_DRIFT", "WARN",
                    detail=(f"agent-autonomy.md Routing-Spalte nennt Agenten, "
                            f"die in operational.md Delegation-Routing fehlen: "
                            f"{sorted(only_in_autonomy)} — Drift-Risiko, ggf. "
                            f"operational.md-Tabelle ergaenzen")))

    return issues


# ---------------------------------------------------------------------------
# Output Formatters
# ---------------------------------------------------------------------------

def fmt_boot(tasks, milestones, target, north_star, op_intent, critical_path,
             blocking_scores, next_actions, issues):
    lines = []
    lines.append(f"TARGET: {target} ({milestones[target].title})" if target in milestones else f"TARGET: {target}")
    lines.append("")

    # Critical path (Task 435 F-C-P2-003: Mixed-Items via _render_cp_item)
    if critical_path:
        cp_labels = [_render_cp_item(item, tasks) for item in critical_path]
        total_effort = 0
        for item in critical_path:
            if isinstance(item, int) and not isinstance(item, bool):
                t = tasks.get(item)
                if t is not None:
                    total_effort += t.effort_weight
        lines.append(f"CRITICAL PATH -> {target}:")
        lines.append(f"  {' -> '.join(cp_labels)}")
        lines.append(f"  Effort-weighted length: {total_effort}")
        # Bottleneck: first non-done task on path (only int items count)
        for item in critical_path:
            if isinstance(item, int) and not isinstance(item, bool):
                t = tasks.get(item)
                if t is not None and not t.is_done:
                    lines.append(f"  Bottleneck: Task {_format_tid(t)} ({t.title[:40]})")
                    break
    lines.append("")

    # In progress
    in_progress = sorted([t for t in tasks.values() if t.status == "in_progress"],
                         key=lambda t: (t._repo, t.id))
    lines.append(f"IN PROGRESS ({len(in_progress)}):")
    for t in in_progress:
        summary = f" — {t.summary[:60]}" if t.summary else ""
        lines.append(f"  [{_format_tid(t)}] {t.title[:40]} ({t.milestone}){summary}")
    lines.append("")

    # Next actions
    lines.append("NEXT ACTIONS:")
    for i, tid in enumerate(next_actions, 1):
        t = tasks[tid]
        cp_flag = "  CRITICAL_PATH" if tid in _hashable_cp_set(critical_path) else ""
        bs = blocking_scores.get(tid, 0)
        lines.append(
            f"  {i}. [{_format_tid(t)}] {t.title[:45]} ({t.milestone}) "
            f"effort:{t.effort}  blocking:{bs}{cp_flag}"
        )
    lines.append("")

    # Milestones
    lines.append("MILESTONES:")
    status_order = {"done": 0, "active": 1, "ready": 2, "blocked": 3, "future": 4}
    sorted_ms = sorted(milestones.values(), key=lambda m: status_order.get(m.status, 9))
    # Dynamic width for aggregate mode (milestone keys get longer with "<repo>:" prefix)
    ms_width = max((len(m.key) for m in sorted_ms), default=25)
    ms_width = max(ms_width, 25)
    for m in sorted_ms:
        task_count = len(m.tasks)
        done_count = sum(1 for tid in m.tasks if tid in tasks and tasks[tid].is_terminal)
        detail = ""
        if m.status == "blocked":
            blockers = [r for r in m.requires if milestones.get(r) and milestones[r].status != "done"]
            detail = f"  by: {', '.join(str(b) for b in blockers)}"
        elif m.status == "active" and m.gate:
            failed_gates = [str(g) for g in m.gate if not g.check(tasks)[0]]
            if failed_gates:
                detail = f"  (gate: {', '.join(g[:30] for g in failed_gates)})"
        status_sym = {"done": "done", "active": "active", "ready": "ready",
                      "blocked": "BLOCKED", "future": "future"}.get(m.status, m.status)
        lines.append(f"  {status_sym:8s} {m.key:{ms_width}s} {done_count}/{task_count}{detail}")
        # Task 435 (B-3 flat, AC-A.7c): feature_milestones-spezifische Sub-Zeilen
        if getattr(m, "feature", ""):
            lines.append(f"             feature: {m.feature[:80]}")
        if getattr(m, "app_status_post_milestone", ""):
            lines.append(f"             app_status: {m.app_status_post_milestone[:80]}")
    lines.append("")

    # Warnings
    errors = [i for i in issues if i.severity == "ERROR"]
    warns = [i for i in issues if i.severity == "WARN"]
    if errors or warns:
        lines.append("WARNINGS:")
        for issue in (errors + warns)[:10]:
            loc = _fmt_issue_loc(issue)  # Task 367: shared helper handles global issues
            prefix = f"{loc} — " if loc else ""
            lines.append(f"  {issue.check}: {prefix}{issue.detail}")
        remaining = len(errors) + len(warns) - 10
        if remaining > 0:
            lines.append(f"  ... and {remaining} more")

    return "\n".join(lines)


def fmt_status(tasks, milestones):
    """Milestone-Overview. Task 435 (F-C-008, AC-A.7c): zeigt
    feature_milestones-spezifische Felder (feature, app_status_post_milestone)
    inline wenn vorhanden."""
    lines = []
    status_order = {"done": 0, "active": 1, "ready": 2, "blocked": 3, "future": 4}
    sorted_ms = sorted(milestones.values(), key=lambda m: status_order.get(m.status, 9))
    ms_width = max((len(m.key) for m in sorted_ms), default=25)
    ms_width = max(ms_width, 25)
    for m in sorted_ms:
        task_count = len(m.tasks)
        done_count = sum(1 for tid in m.tasks if tid in tasks and tasks[tid].is_terminal)
        lines.append(f"  {m.status:8s} {m.key:{ms_width}s} {m.title:30s} {done_count}/{task_count}")
        # Task 435 (B-3 flat): feature_milestones-spezifische Sub-Zeilen
        if getattr(m, "feature", ""):
            lines.append(f"           feature: {m.feature}")
        if getattr(m, "app_status_post_milestone", ""):
            lines.append(f"           app_status: {m.app_status_post_milestone}")
        if getattr(m, "parallel_to", []):
            lines.append(f"           parallel_to: {', '.join(m.parallel_to)}")
        # Pre-Set-Gates mit preliminary-Marker (B-2 Lock)
        if any(getattr(g, "preliminary", False) for g in m.gate):
            preliminary_count = sum(1 for g in m.gate if getattr(g, "preliminary", False))
            lines.append(f"           gates: {preliminary_count} preliminary")
    total = len(tasks)
    total_done = sum(1 for t in tasks.values() if t.is_done)
    lines.append(f"\nTotal: {total_done}/{total} tasks done")
    return "\n".join(lines)


def fmt_next(tasks, next_actions, critical_path, blocking_scores):
    lines = [f"NEXT ACTIONS ({len(next_actions)}):"]
    cp_set = _hashable_cp_set(critical_path)
    for i, tid in enumerate(next_actions, 1):
        t = tasks[tid]
        cp = " CRITICAL_PATH" if tid in cp_set else ""
        bs = blocking_scores.get(tid, 0)
        lines.append(f"  {i}. [{_format_tid(t)}] {t.title[:50]} ({t.milestone}) effort:{t.effort} blocking:{bs}{cp}")
    return "\n".join(lines)


def fmt_critical_path(tasks, critical_path, target):
    """Task 435 (F-C-P2-003): Mixed-Item-Render via _render_cp_item.
    Items koennen sein: int task-id, str milestone-key, list[str] parallel,
    str post-MVP-Beschreibung.
    """
    if not critical_path:
        return f"No critical path to {target} (no pending tasks in scope)"
    lines = [f"CRITICAL PATH -> {target}:"]
    total = 0
    for item in critical_path:
        rendered = _render_cp_item(item, tasks)
        if isinstance(item, int) and not isinstance(item, bool):
            t = tasks.get(item)
            if t is not None:
                total += t.effort_weight
                done_mark = "done" if t.is_done else t.status
                lines.append(f"  {rendered} ({t.milestone}) effort:{t.effort} [{done_mark}]")
            else:
                lines.append(f"  {rendered} (archived)")
        elif isinstance(item, list):
            # Parallel-Liste: explizit als parallel-Marker rendern (TC-L1-003)
            lines.append(f"  {rendered}  [parallel]")
        else:
            lines.append(f"  {rendered}")
    lines.append(f"\nTotal effort-weighted length: {total}")
    return "\n".join(lines)


def fmt_check(milestones, tasks, milestone_key=None):
    lines = []
    targets = [milestone_key] if milestone_key else list(milestones.keys())
    all_pass = True
    for key in targets:
        m = milestones.get(key)
        if not m:
            lines.append(f"MILESTONE: {key}  [NOT FOUND]")
            all_pass = False
            continue
        if not m.gate:
            lines.append(f"MILESTONE: {key}  [NO GATE]  status={m.status}")
            continue
        gate_pass = True
        lines.append(f"MILESTONE: {key}  [{m.status.upper()}]")
        for g in m.gate:
            ok, detail = g.check(tasks)
            sym = "✓" if ok else "✗"
            lines.append(f"  {sym} {g}  ({detail})")
            if not ok:
                gate_pass = False
        passed = sum(1 for g in m.gate if g.check(tasks)[0])
        lines.append(f"RESULT: {passed}/{len(m.gate)} conditions passed")
        if not gate_pass:
            all_pass = False
        lines.append("")
    return "\n".join(lines), all_pass


def fmt_after(tasks, milestones, task_id, blocking_scores):
    # Task 367: task_id may be int (single-repo) or str "repo#id" (aggregate).
    t = tasks.get(task_id)
    if not t:
        return f"Task {task_id} not found"

    lines = [f"COMPLETING Task {_format_tid(t)} ({t.title}):"]
    lines.append("")

    # Find directly unblocked tasks
    done_keys = {tk for tk, tt in tasks.items() if tt.is_done}
    simulated_done = done_keys | {task_id}

    directly_unblocked = []
    for other in tasks.values():
        if other.key == task_id or other.is_terminal:
            continue
        if task_id not in other.blocked_by:
            continue
        if all(d in simulated_done for d in other.blocked_by):
            directly_unblocked.append(other)

    if directly_unblocked:
        lines.append("DIRECTLY UNBLOCKED:")
        for u in directly_unblocked:
            lines.append(f"  [{_format_tid(u)}] {u.title[:50]} -> becomes READY")
    else:
        lines.append("DIRECTLY UNBLOCKED: none")
    lines.append("")

    # Milestone impact
    m = milestones.get(t.milestone)
    if m and m.gate:
        lines.append("MILESTONE IMPACT:")
        for g in m.gate:
            ok, detail = g.check(tasks)
            sym = "✓" if ok else "pending"
            lines.append(f"  {m.key}: {g} ({sym}: {detail})")
    lines.append("")

    # Chain effect (blocking score)
    bs = blocking_scores.get(task_id, 0)
    lines.append(f"TOTAL CHAIN EFFECT: {bs} tasks transitively unblocked")

    return "\n".join(lines)


def fmt_spec_pipeline(tasks: dict) -> str:
    """Format spec pipeline report showing per-spec review progress.

    Only includes tasks with non-empty spec_states and non-terminal status
    (excluding superseded/absorbed). Detects duplicate spec ownership.

    Task 367: uses t.key (namespaced in aggregate mode) for task references.
    """
    # Collect specs from active tasks
    spec_entries: list = []  # (spec_name, state, task_key)
    seen_specs: dict[str, list] = defaultdict(list)  # spec → task_keys
    duplicates: list[str] = []

    for t in sorted(tasks.values(), key=lambda x: (x._repo, x.id)):
        if t.status in {"superseded", "absorbed"}:
            continue
        if not t.spec_states or not isinstance(t.spec_states, dict):
            continue
        for spec_name, state in t.spec_states.items():
            spec_entries.append((spec_name, state, t.key))
            seen_specs[spec_name].append(t.key)

    # Detect duplicates
    for spec_name, task_keys in seen_specs.items():
        if len(task_keys) > 1:
            ids_str = " and ".join(str(tk) for tk in task_keys)
            duplicates.append(f"DUPLICATE: {spec_name} in Task {ids_str}")

    if not spec_entries and not duplicates:
        return "SPEC PIPELINE:\n  (no specs tracked)"

    lines = ["SPEC PIPELINE:"]

    # Duplicate warnings first
    for dup in duplicates:
        lines.append(f"  {dup}")
    if duplicates:
        lines.append("")

    # Spec lines
    for spec_name, state, task_key in spec_entries:
        phase = state.get("current_phase", "?")
        review_passes = state.get("review_passes", 0)
        fix_passes = state.get("fix_passes", 0)

        # Truncate spec name to 30 chars
        display_name = spec_name[:27] + "..." if len(spec_name) > 30 else spec_name

        # Build pass/fix info (omit if 0)
        pass_info = f"Pass {review_passes}" if review_passes else ""
        fix_info = f"Fix {fix_passes}" if fix_passes else ""
        detail_parts = [p for p in [pass_info, fix_info] if p]
        detail = "  ".join(detail_parts)

        lines.append(
            f"  {display_name:30s} {phase:10s} {detail:16s} [Task {task_key}]"
        )

    # Aggregate
    lines.append("")
    phase_counts: dict[str, int] = defaultdict(int)
    total_specs = 0
    task_set: set = set()
    seen_agg: set[str] = set()
    for _spec_name, state, task_key in spec_entries:
        if _spec_name in seen_agg:
            continue
        seen_agg.add(_spec_name)
        phase = state.get("current_phase", "unknown")
        phase_counts[phase] += 1
        total_specs += 1
        task_set.add(task_key)

    ready_count = phase_counts.get("ready", 0)
    non_ready = total_specs - ready_count
    lines.append("AGGREGATE:")
    lines.append(
        f"  spec-readiness:  {ready_count}/{total_specs} ready"
        f" ({non_ready} raw/reviewing/fixing)"
    )
    lines.append(
        f"  Total tracked:   {total_specs} specs across {len(task_set)} tasks"
    )

    return "\n".join(lines)


def _fmt_issue_loc(i: ValidationIssue) -> str:
    """Location-Prefix fuer Validate-Ausgabe. Globale Checks (ohne task/milestone)
    bekommen keinen Prefix, nur den Check-Namen + detail."""
    if i.task_id:
        return f"Task {i.task_id}"
    if i.milestone_key:
        return f"Milestone {i.milestone_key}"
    return ""  # global issue (z.B. AUTONOMY_*)


def fmt_validate(issues):
    errors = [i for i in issues if i.severity == "ERROR"]
    warns = [i for i in issues if i.severity == "WARN"]
    lines = []
    if errors:
        lines.append(f"ERRORS ({len(errors)}):")
        for i in errors:
            loc = _fmt_issue_loc(i)
            if loc:
                lines.append(f"  {i.check}: {loc} — {i.detail}")
            else:
                lines.append(f"  {i.check}: {i.detail}")
    if warns:
        lines.append(f"\nWARNINGS ({len(warns)}):")
        for i in warns:
            loc = _fmt_issue_loc(i)
            if loc:
                lines.append(f"  {i.check}: {loc} — {i.detail}")
            else:
                lines.append(f"  {i.check}: {i.detail}")
    if not errors and not warns:
        lines.append("CLEAN: no issues found")
    else:
        lines.append(f"\nSummary: {len(errors)} errors, {len(warns)} warnings")
    return "\n".join(lines), len(errors) == 0


def fmt_dashboard_json(tasks, milestones, target, north_star, op_intent,
                       critical_path, blocking_scores, next_actions, issues,
                       phases=None):
    now = datetime.now(timezone(timedelta(hours=2)))  # CEST

    ms_list = []
    for m in milestones.values():
        gate_results = []
        for g in m.gate:
            ok, detail = g.check(tasks)
            gate_results.append({
                "type": g.type, "spec": str(g), "pass": ok, "detail": detail
            })
        milestone_tasks = [tid for tid in m.tasks if tid in tasks]
        done_count = sum(1 for tid in milestone_tasks if tasks[tid].is_terminal)
        in_progress_count = sum(1 for tid in milestone_tasks if tasks[tid].status == "in_progress")
        pending_count = len(milestone_tasks) - done_count - in_progress_count

        blocking_ms = [r for r in m.requires
                       if milestones.get(r) and milestones[r].status != "done"]

        ms_list.append({
            "key": m.key, "title": m.title, "desc": m.desc, "type": m.type,
            "status": m.status,
            "progress": {"done": done_count, "in_progress": in_progress_count,
                         "pending": pending_count, "total": len(milestone_tasks)},
            "gate_results": gate_results,
            "requires": m.requires,
            "dependents": m.dependents,
            "phases": m.phases,
            "blocking_milestones": blocking_ms,
            "tasks": sorted(milestone_tasks, key=str),  # Task 367: str-sort handles both modes
        })

    cp_set = _hashable_cp_set(critical_path)
    task_list = []
    # Task 367: sort by (repo, id) so aggregate mode groups by namespace
    for t in sorted(tasks.values(), key=lambda x: (x._repo, x.id)):
        task_list.append({
            "id": t.id, "title": t.title, "status": t.status,
            "milestone": t.milestone, "effort": t.effort, "area": t.area,
            "assignee": t.assignee, "on_critical_path": t.key in cp_set,
            "blocking_score": blocking_scores.get(t.key, 0),
            "blocked_by": t.blocked_by, "spec_ref": t.spec_ref,
            "board_result": t.board_result, "readiness": t.readiness,
            "summary": t.summary,
            "repo": t._repo,  # Task 367: namespace (empty in single-repo)
            "namespaced_id": _format_tid(t),  # Task 367: full rendered ID
        })

    na_list = []
    for tid in next_actions:
        t = tasks[tid]
        na_list.append({
            "id": t.id, "title": t.title, "milestone": t.milestone,
            "effort": t.effort, "blocking_score": blocking_scores.get(t.key, 0),
            "on_critical_path": t.key in cp_set,
            "repo": t._repo,
            "namespaced_id": _format_tid(t),
        })

    cp_effort = sum(
        tasks[item].effort_weight
        for item in (critical_path or [])
        if isinstance(item, int) and not isinstance(item, bool) and item in tasks
    ) if critical_path else 0

    validation = {
        "errors": [{"check": i.check, "task": i.task_id, "milestone": i.milestone_key,
                     "detail": i.detail}
                    for i in issues if i.severity == "ERROR"],
        "warnings": [{"check": i.check, "task": i.task_id, "milestone": i.milestone_key,
                       "detail": i.detail}
                      for i in issues if i.severity == "WARN"],
    }

    # Phase data
    phases_list = []
    phase_progress_dict = {}
    if phases:
        for p in phases:
            phases_list.append({
                "key": p.key, "title": p.title, "desc": p.desc,
                "investor_desc": p.investor_desc or p.desc,
                "order": p.order,
            })
            pp = compute_phase_progress(p.key, milestones, tasks)
            phase_progress_dict[p.key] = {
                "pct": pp.pct, "tasks_done": pp.tasks_done,
                "tasks_total": pp.tasks_total, "remaining_effort": pp.remaining_effort,
            }

    return json.dumps({
        "generated_at": now.isoformat(),
        "north_star": north_star,
        "target": target,
        "operational_intent": op_intent,
        "phases": phases_list,
        "phase_progress": phase_progress_dict,
        "milestones": ms_list,
        "tasks": task_list,
        "critical_path": {"target": target, "path": critical_path, "effort_total": cp_effort},
        "next_actions": na_list,
        "validation": validation,
    }, indent=2, ensure_ascii=False)


# ---------------------------------------------------------------------------
# Self-Test (Task 435 B-5 Lock — Inline Smoke-Tests)
# ---------------------------------------------------------------------------

def _run_self_test() -> int:
    """Task 435 (B-5 Lock): inline Smoke-Tests fuer feature_milestones-Schema.

    Laeuft 5-7 Smoke-TCs gegen tests/fixtures/feature_milestones_minimal.yaml.
    Kein pytest-Setup im framework-Repo Pflicht (B-5 Lock). Returnt exit-code 0
    bei Pass, 1 bei Fail.
    """
    fixtures_dir = FRAMEWORK_ROOT / "tests" / "fixtures"
    minimal = fixtures_dir / "feature_milestones_minimal.yaml"
    empty = fixtures_dir / "feature_milestones_empty.yaml"
    drift = fixtures_dir / "critical_path_drift.yaml"
    dual = fixtures_dir / "dual_critical_path.yaml"

    failures: list[str] = []

    def _ok(msg: str) -> None:
        print(f"  [PASS] {msg}")

    def _fail(msg: str) -> None:
        print(f"  [FAIL] {msg}")
        failures.append(msg)

    print("plan_engine --self-test (Task 435 B-5 Lock)")

    # Smoke-1: load_plan reads feature_milestones
    if not minimal.exists():
        _fail(f"Fixture missing: {minimal}")
    else:
        plan = load_plan(minimal)
        expected = {"M1": 2100, "M1.5": 2150, "M2": 2110, "M3": 2120,
                    "M4": 2130, "M5": 2140, "M6": 2160, "M7": 2170}
        for k, eid in expected.items():
            if k not in plan.milestones:
                _fail(f"Smoke-1: Milestone {k} missing")
                break
            if plan.milestones[k].id != eid:
                _fail(f"Smoke-1: {k} id={plan.milestones[k].id} expected {eid}")
                break
        else:
            _ok("Smoke-1: 8 Synthetic-IDs (B-1 Lock, kein 2090)")

    # Smoke-2: graceful degradation
    if empty.exists():
        plan = load_plan(empty)
        if "tier2-harness" in plan.milestones:
            _ok("Smoke-2: graceful degradation (no feature_milestones-Block)")
        else:
            _fail("Smoke-2: legacy milestone tier2-harness not loaded")
    else:
        _fail(f"Fixture missing: {empty}")

    # Smoke-3: 4-stufiger Lookup explicit gewinnt
    if dual.exists():
        plan = load_plan(dual)
        plan_data = yaml.safe_load(dual.read_text(encoding="utf-8"))
        cp = compute_critical_path({}, plan.milestones, plan_data.get("target", "M1"), plan_data)
        if 999 in cp or 998 in cp:
            _fail(f"Smoke-3: critical_path_feature_view/legacy gewann statt critical_path: cp={cp}")
        elif 1 in cp or "M1" in cp:
            _ok("Smoke-3: 4-stufiger Lookup Stufe-1 critical_path: gewinnt")
        else:
            _fail(f"Smoke-3: Stufe-1 nicht gewaehlt: cp={cp}")
    else:
        _fail(f"Fixture missing: {dual}")

    # Smoke-4: Drift-Detection
    if drift.exists():
        plan = load_plan(drift)
        plan_data = yaml.safe_load(drift.read_text(encoding="utf-8"))
        # warnings via _emit_warn
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            compute_critical_path({}, plan.milestones, "M2", plan_data)
        mismatch = [w for w in caught if "CRITICAL_PATH_MISMATCH" in str(w.message)]
        if mismatch:
            _ok("Smoke-4: Drift-Detection WARN CRITICAL_PATH_MISMATCH")
        else:
            _fail("Smoke-4: kein CRITICAL_PATH_MISMATCH bei drift-Fixture")
    else:
        _fail(f"Fixture missing: {drift}")

    # Smoke-5: GateCondition preliminary returns (True, "preliminary")
    g = GateCondition(type="validate", ref="x", preliminary=True)
    ok, reason = g.check({}, {})
    if ok is True and reason == "preliminary":
        _ok("Smoke-5: GateCondition preliminary returns (True, 'preliminary')")
    else:
        _fail(f"Smoke-5: preliminary check returned ({ok!r}, {reason!r})")

    # Smoke-6: load_archived_task_ids robust auf fehlendem dir
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        archived = load_archived_task_ids(Path(tmp))
        if archived == set():
            _ok("Smoke-6: load_archived_task_ids leeres set bei fehlendem archive/")
        else:
            _fail(f"Smoke-6: archived={archived}")

    # Smoke-7: _render_cp_item alle 4 Item-Types
    out_int = _render_cp_item(425, {})
    out_str = _render_cp_item("M1", {})
    out_list = _render_cp_item(["M1", "M1.5"], {})
    out_post = _render_cp_item("POST-MVP", {})
    if "425" in out_int and out_str == "M1" and "||" in out_list and "POST-MVP" in out_post:
        _ok("Smoke-7: _render_cp_item alle 4 Item-Types")
    else:
        _fail(f"Smoke-7: out_int={out_int!r} out_str={out_str!r} out_list={out_list!r} out_post={out_post!r}")

    if failures:
        print(f"\n{len(failures)} self-test failure(s).")
        return 1
    print("\nAll smoke-tests passed.")
    return 0


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    _configure_stdio_for_windows()

    parser = argparse.ArgumentParser(description="BuddyAI Plan Engine")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--boot", action="store_true", help="Full boot hook")
    group.add_argument("--status", action="store_true", help="Milestone overview")
    group.add_argument("--next", action="store_true", help="Next actions")
    group.add_argument("--critical-path", action="store_true", help="Critical path")
    group.add_argument("--check", nargs="?", const="__all__", help="Gate check")
    group.add_argument("--after", type=str, help="What unblocks after task ID? "
                       "(int in single-repo, 'repo#id' in aggregate mode)")
    group.add_argument("--dashboard-json", action="store_true", help="JSON for dashboard")
    group.add_argument("--validate", action="store_true", help="Consistency check")
    group.add_argument("--spec-pipeline", action="store_true",
                       help="Spec review pipeline status")
    group.add_argument("--self-test", action="store_true",
                       help="Task 435 B-5 Lock: inline smoke-tests fuer "
                            "feature_milestones-Schema-Erweiterung")
    parser.add_argument("--limit", type=int, default=10, help="Limit for --next")
    parser.add_argument(
        "--project-root",
        type=str,
        default=None,
        help="Override PROJECT_ROOT (where docs/tasks + docs/plan.yaml live). "
             "Takes precedence over BUDDY_PROJECT_ROOT env-var.",
    )
    # Task 367: Multi-Repo Aggregation
    parser.add_argument(
        "--aggregate",
        action="store_true",
        help="Task 367: Multi-repo aggregate mode. Scans multiple project repos "
             "and builds a unified view with namespaced IDs <repo>#<id>.",
    )
    parser.add_argument(
        "--projects",
        type=str,
        default=None,
        help="Task 367: Comma-separated list of project repos for --aggregate "
             "mode. Each entry can be a repo name (resolved against $PROJECTS_DIR) "
             "or an absolute/relative path. Default: auto-discovery in "
             "$PROJECTS_DIR (~/projects by default).",
    )
    args = parser.parse_args()

    # Task 010 Part L0: explicit --project-root override. Rebinds the three
    # project-scoped module globals so that load_tasks/load_plan + all
    # GateCondition.check calls resolve against the new root.
    if args.project_root:
        global PROJECT_ROOT, TASKS_DIR, PLAN_PATH, REPO_ROOT
        PROJECT_ROOT = Path(args.project_root).resolve()
        TASKS_DIR = PROJECT_ROOT / "docs" / "tasks"
        PLAN_PATH = PROJECT_ROOT / "docs" / "plan.yaml"
        REPO_ROOT = PROJECT_ROOT  # keep back-compat alias in sync

    # Task 435 (B-5 Lock): --self-test entry-point.
    if getattr(args, "self_test", False):
        rc = _run_self_test()
        sys.exit(rc)

    # Load
    if args.aggregate:
        # Task 367: Multi-Repo Aggregate Mode
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

    # Task 435 (F-C-P2-001 User-Lock 2026-05-03 Variante c):
    # Load archived task IDs fuer Silent-Pass von BROKEN_DEP.
    # Iteration 2 (CA-002 Fix): Aggregate-Mode sammelt per-repo archived_ids
    # in load_aggregated und stellt sie als namespaced set[str] bereit.
    archived_ids: set
    if args.aggregate:
        archived_ids = aggregate.archived_ids
    else:
        archived_ids = load_archived_task_ids(PROJECT_ROOT)

    # Task 435 (F-C-003 Option 1, Amendment-001):
    # Pass plan_data fuer 4-stufigen Critical-Path-Lookup.
    plan_data_for_cp: dict = {}
    if not args.aggregate and PLAN_PATH.exists():
        try:
            plan_data_for_cp = yaml.safe_load(PLAN_PATH.read_text(encoding="utf-8")) or {}
        except (yaml.YAMLError, OSError):
            plan_data_for_cp = {}
        if not isinstance(plan_data_for_cp, dict):
            plan_data_for_cp = {}

    # Compute
    critical_path = compute_critical_path(tasks, milestones, target, plan_data_for_cp)
    blocking_scores = compute_blocking_score(tasks, milestones)
    issues = validate(tasks, milestones, archived_ids=archived_ids)
    # Autonomy-Consistency-Checks (framework-ambiguity-audit Fund 1, Phase 3).
    # Additiv — keine Beeinflussung bestehender Task/Milestone-Checks.
    # Skipped in aggregate mode (operates on FRAMEWORK_ROOT, not per-repo).
    if not args.aggregate:
        issues.extend(validate_autonomy_consistency())
    else:
        # Task 367: surface aggregate-mode warnings (stale external refs, etc.)
        for w in aggregate.warnings:
            issues.append(ValidationIssue(
                "AGGREGATE_WARN", "WARN", detail=w))
    next_actions = compute_next_actions(tasks, milestones, critical_path, blocking_scores,
                                        target=target, limit=args.limit)

    # Output
    if args.boot:
        print(fmt_boot(tasks, milestones, target, north_star, op_intent,
                        critical_path, blocking_scores, next_actions, issues))
    elif args.status:
        print(fmt_status(tasks, milestones))
    elif args.next:
        print(fmt_next(tasks, next_actions, critical_path, blocking_scores))
    elif args.critical_path:
        print(fmt_critical_path(tasks, critical_path, target))
    elif args.check is not None:
        key = None if args.check == "__all__" else args.check
        output, all_pass = fmt_check(milestones, tasks, key)
        print(output)
        sys.exit(0 if all_pass else 1)
    elif args.after is not None:
        # Task 367: accept int or "repo#id" for --after
        after_key: object = args.after
        import contextlib
        with contextlib.suppress(TypeError, ValueError):
            after_key = int(args.after)
        print(fmt_after(tasks, milestones, after_key, blocking_scores))
    elif args.dashboard_json:
        print(fmt_dashboard_json(tasks, milestones, target, north_star, op_intent,
                                  critical_path, blocking_scores, next_actions, issues,
                                  phases=phases_for_json))
    elif args.validate:
        output, clean = fmt_validate(issues)
        print(output)
        sys.exit(0 if clean else 1)
    elif args.spec_pipeline:
        print(fmt_spec_pipeline(tasks))


if __name__ == "__main__":
    main()
