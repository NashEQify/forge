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
    """zentraler Wrapper fuer warnings.warn mit konsistentem
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

# Path resolution
#
# PROJECT_ROOT   → where the consumer's docs/tasks/*.yaml and docs/plan.yaml
#                  live. Derived from BUDDY_PROJECT_ROOT env-var, or
#                  --project-root flag, or current working directory
#                  (e.g. ~/projects/<consumer>).
#
# FRAMEWORK_ROOT → where plan_engine.py itself lives. Framework-internal files
#                  (CLAUDE.md, AGENTS.md, framework/agent-autonomy.md,
#                  agents/buddy/operational.md, etc.) are resolved against
#                  this root (e.g. ~/projects/forge).
#
# When PROJECT_ROOT and FRAMEWORK_ROOT happen to coincide (a session running
# directly inside the framework repo), the same path is used for both —
# tasks + plan land in the framework's own docs/ tree.
PROJECT_ROOT = Path(os.environ.get("BUDDY_PROJECT_ROOT", Path.cwd())).resolve()
FRAMEWORK_ROOT = Path(__file__).resolve().parent.parent

# Back-compat alias: older code-paths still reference REPO_ROOT. It mirrors
# PROJECT_ROOT (the "data" side) which is where task/plan/gate-scripts live.
# Framework-internal reads should use FRAMEWORK_ROOT explicitly.
REPO_ROOT = PROJECT_ROOT

TASKS_DIR = PROJECT_ROOT / "docs" / "tasks"
PLAN_PATH = PROJECT_ROOT / "docs" / "plan.yaml"

# machine-readable task-schema SoT. The validator parses THIS
# file — field names, required-sets, value vocab, filename grammar and
# calibration switches are read FROM the parsed dict, never re-encoded
# in Python. Framework-internal → FRAMEWORK_ROOT (mirror AUTONOMY_SOT_PATH).
TASK_SCHEMA_PATH = FRAMEWORK_ROOT / "framework" / "task-schema.yaml"

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


# Type-Whitelist fuer GateCondition. Bekannte Types werden in check() geroutet,
# unbekannte werfen WARN UNKNOWN_GATE_TYPE in check() (kein Crash).
GATE_TYPE_WHITELIST = {"task", "validate", "coverage", "spec_review", "file", "script"}


@dataclass
class GateCondition:
    type: str
    path: str = ""
    id: int = 0
    want: str = ""
    # additive Felder fuer Pre-Set-Gates pro feature_milestone.
    # ref:         Beschreibungs-/Reference-String (z.B. "plan_engine clean")
    # preliminary: True -> Gate gibt (True, "preliminary") zurueck (blockiert nicht)
    # desc:        Menschenlesbare Beschreibung
    ref: str = ""
    preliminary: bool = False
    desc: str = ""

    def __post_init__(self) -> None:
        # explicit Type-Coercion fuer preliminary (yaml liefert bool ODER
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
        # preliminary-Gates pass (blockieren Status-Compute nicht).
        if self.preliminary:
            return True, "preliminary"

        if self.type == "task":
            # Archive-Awareness. Archivierte Tasks sind per
            # archive-Semantik terminal-done (Frozen Zone WORM-Pattern).
            # Wenn gate `want: done` (default) UND task-id ist archiviert →
            # pass. Ohne dieses Verhalten wird jeder Milestone mit
            # archiviertem Gate-Task als ORPHAN klassifiziert.
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
            # non-preliminary Pflicht-Gates dieser Types
            # haben aktuell keine Default-Logik; sie sind nur als preliminary
            # spezifiziert. Nicht-preliminary => no-op pass mit Hinweis-Detail.
            return True, f"{self.type}: noop (non-preliminary fallback)"
        elif self.type == "manual":
            # `manual` gates are soft markers — they signal human-judgement
            # bucket-closure rather than an auto-checkable condition. Engine
            # treats them as pass; the milestone closes when the listed
            # member-tasks reach done OR a human decides to fold the bucket.
            return True, "manual: soft marker (human-judgement)"
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
        if self.type == "manual":
            return f"manual:{self.desc or self.ref or '?'}"
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


# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------

# Synthetic-IDs fuer Feature-Milestones M1-M7+M1.5.
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

# Whitelist erlaubter Feldnamen pro feature_milestone-Eintrag. Unbekannte
# Felder loesen WARN UNKNOWN_FIELD aus, kein ERR. Pflicht-Felder sind
# implizit — fehlende Pflicht-Felder werden tolerant
# behandelt (Default-Werte).
_FEATURE_MILESTONE_KNOWN_FIELDS = {
    # Pflicht-Felder
    "name", "feature", "capabilities", "specs", "fallback_strategy",
    "requires", "blocked_by", "gate", "app_status_post_milestone",
    # Optional-Felder
    "cross_cutting", "parallel_to", "frontend_components",
    "backend_refactor_components", "sysadmin_methodology_import",
    "infra_audit", "gap_ownership_anchor_task",
    # Doku-only (akzeptiert ohne WARN)
    "title", "desc",
    # Dashboard-cluster assignment: allow phases on feature_milestones
    # entries so view-buckets like council-mod can opt out of the feature-milestones
    # pseudo-phase and cluster under a normal phase (e.g. post-mvp-backlog).
    "phases",
    # Plan-topology re-scope (INTENT-010): the 4 capability pillars as a
    # cross-cutting tag on milestone entries + the launch scope-freeze gate-doc.
    "pillars", "scope_freeze",
}


def load_archived_task_ids(project_root: Path) -> set[int]:
    """Liest IDs aus <project_root>/docs/tasks/archive/*.yaml (NICHT recursive,
    NICHT legacy_milestones_archive.yaml). Reine ID-Sammlung, kein Stub-Read.
    Used by validate-Loop fuer Silent-Pass von BROKEN_DEP wenn Target archived.

    PROJECT_ROOT-relativ: project_root MUSS explicit uebergeben
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
            # explizite Exception-Klassen, NICHT silent except.
            # WARN ARCHIVED_ID_PARSE_FAIL emittiert (sichtbar im Test-Output).
            _emit_warn(f"ARCHIVED_ID_PARSE_FAIL: {path}: {e}")
            continue

        if not isinstance(data, dict):
            continue
        raw_id = data.get("id")
        if raw_id is None:
            # Old-Format-File ohne id — Skip (legitim, kein WARN noetig)
            continue
        # yaml-bool-id explizit reject VOR Coercion.
        # Python int(True)=1 / int(False)=0 -> ohne Reject wuerde Task #1
        # bzw. #0 stumm als archiviert markiert.
        if isinstance(raw_id, bool):
            _emit_warn(
                f"ARCHIVED_ID_BOOL_REJECTED: {path}: id={raw_id!r} "
                "(yaml-bool ist nie valide id)"
            )
            continue
        # Type-Coercion-Disziplin: _coerce_int_or_none statt raw int().
        coerced = _coerce_int_or_none(raw_id, f"archive[{path.name}].id")
        if coerced is None:
            # WARN bereits emittiert von _coerce_int_or_none (oder bool-reject oben)
            _emit_warn(f"ARCHIVED_ID_TYPE_INVALID: {path}: id={raw_id!r}")
            continue
        archived_ids.add(coerced)
    return archived_ids


# Module-level Cache fuer archived task IDs, used by
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
    """yaml-Field zu str mit None-Default. Kein Crash auf None."""
    if raw is None:
        return ""
    return str(raw)


def _coerce_str_list(raw, field_name: str = "") -> list[str]:
    """yaml-Field zu list[str]. Bei string-statt-list:
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
    """yaml-Field zu int|None. String 'abc' -> None + WARN.

    yaml-bool wird explizit REJECTED.
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
        # yaml-bool ist NIE eine valide id.
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
    # Type-Coercion-Disziplin: _coerce_int_or_none statt raw int().
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
        # Sub-Tags-Propagation in Task-Dataclass.
        legacy_milestone_key=_coerce_str(data.get("legacy_milestone_key"), "legacy_milestone_key"),
        migration_note=_coerce_str(data.get("migration_note"), "migration_note"),
    )
    return tid, task


def load_tasks(project_root: Path | None = None, repo_name: str = "") -> dict:
    """Load tasks from a single project root.

    project_root parameter allows loading tasks from arbitrary
    directories (used by aggregate mode). When None, falls back to the
    module-level TASKS_DIR (current PROJECT_ROOT). repo_name, when set,
    marks each Task with _repo for namespacing — used only by aggregate mode.

    Return type depends on mode:
      - Single-repo (repo_name=""): dict[int, Task] keyed by integer task id
      - Aggregate (repo_name set): dict[str, Task] keyed by "<repo>#<id:03d>"
    """
    # non-recursive Path-Filter via tasks_dir.glob("*.yaml").
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
        except (yaml.YAMLError, OSError, ValueError):  # ValueError = UnicodeDecodeError
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
        except (yaml.YAMLError, OSError, ValueError) as e:
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
    """Build GateCondition from yaml-loaded dict. Type-Coercion-disziplin.

    Pre-Set-Gate-Format:
      {type: task, id: <int>, desc: <str>}
      {type: validate|coverage|spec_review, ref: <str>, preliminary: true|false}
    """
    if not isinstance(g, dict):
        # Defensive: list-statt-dict (yaml-Tippfehler) -> empty Gate
        # warnings via _emit_warn
        _emit_warn(f"GATE_TYPE_MISMATCH: gate-entry expected dict, got {type(g).__name__}: {g!r}")
        return GateCondition(type="")
    # yaml-bool-id explizit reject VOR int()-Coercion
    # (gleiche Bug-Class wie in load_archived_task_ids, anderer Pfad).
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

    project_root parameter allows loading plan from arbitrary
    directories (used by aggregate mode). When None, falls back to the
    module-level PLAN_PATH.

    liest zusaetzlich
    `feature_milestones:`-Block und erzeugt Synthetic-Milestones mit IDs
    2100/2150/2110/2120/2130/2140/2160/2170. Bei Key-Kollision mit
    `milestones:`-Pointern: feature_milestones gewinnt.

    Path-Flexibilitaet: project_root kann sein:
      - None: nutzt module-level PLAN_PATH
      - Path zu Verzeichnis: liest <root>/docs/plan.yaml
      - Path zu yaml-File: liest direkt diese Datei (Test-Fixture-Use-Case)

    Graceful degradation:
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
    except (yaml.YAMLError, OSError, ValueError) as e:
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
    # Wird zuerst geladen — feature_milestones gewinnt bei Kollision.
    for entry in data.get("milestones", []) or []:
        if not isinstance(entry, dict):
            continue
        key = entry.get("key", "")
        if not key:
            continue
        gates = [_build_gate_from_dict(g) for g in entry.get("gate", []) or []]
        # Pre-Greenfield Pointer-Eintraege koennen 'id' haben (Synthetic 2090-2170).
        # yaml-bool-id explizit reject VOR int()-Coercion.
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

    # Step 2: feature_milestones-Block native lesen.
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
        # Anti-Pattern: yaml-Felder mit Python-Reservierten-Namen
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

        # Default-Regel: requires := requires_field or blocked_by_field or [].
        # Beide duerfen co-existieren; bei Konflikt gewinnt requires.
        requires_raw = fdata.get("requires")
        blocked_by_raw = fdata.get("blocked_by")
        if requires_raw:
            requires = _coerce_str_list(requires_raw, f"feature_milestones[{fkey}].requires")
        elif blocked_by_raw:
            requires = _coerce_str_list(blocked_by_raw, f"feature_milestones[{fkey}].blocked_by")
        else:
            requires = []

        # Gate parsen (Pre-Set-Gates)
        gate_raw = fdata.get("gate", []) or []
        feature_gates: list[GateCondition] = []
        if isinstance(gate_raw, list):
            if "gate" in fdata and not gate_raw:
                # Schema sagt 'Pflicht-Felder: gate'. Leere Liste WARN.
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
            phases=_coerce_str_list(
                fdata.get("phases"), f"feature_milestones[{fkey}].phases"
            ),
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
            infra_audit=_coerce_str(
                fdata.get("infra_audit"), "infra_audit"
            ),
            gap_ownership_anchor_task=gap_anchor,
        )
        # feature_milestones gewinnt bei Key-Kollision (overwrite).
        milestones[fkey] = m

    return PlanResult(
        milestones=milestones,
        target=target,
        north_star=north_star,
        operational_intent=op_intent,
        phases=phases,
    )


# ---------------------------------------------------------------------------
# Multi-Repo Aggregation
# ---------------------------------------------------------------------------

def discover_projects(projects_arg: str | None = None) -> list[tuple[str, Path]]:
    """Discover project repos for aggregate mode.

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
            plan_yaml = entry / "docs" / "plan.yaml"
            # Aggregate is a PLAN view — only plan-managed repos qualify. A
            # repo with docs/tasks/ but no docs/plan.yaml (e.g. an analysis /
            # notes repo) has no milestones to validate against, so scanning it
            # only yields spurious NO_MILESTONE / UNKNOWN_REQUIRES errors.
            if intent_md.exists() and tasks_dir.exists() and plan_yaml.exists():
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
    """Result of load_aggregated.

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
    # Union der per-repo archived task-IDs,
    # namespaced als "<repo>#<id:03d>" damit validate-Loop direkt match macht.
    archived_ids: set[str] = field(default_factory=set)


def load_aggregated(projects_arg: str | None = None) -> AggregateResult:
    """Load multiple project repos and merge into unified tasks/milestones.

    Keying:
      - Tasks: dict key is "<repo>#<id:03d>" string (e.g. "<consumer>#358").
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

    per-repo archived_ids gesammelt + zu
    einem namespaced set ("<repo>#<id:03d>") gemerged. Silent-Pass
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

        # per-repo archived_ids sammeln + namespacen.
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
            # requires entries reference either a milestone (str key) or a task
            # (int / digit-str). Milestone refs namespace with ':'; task refs
            # MUST namespace as '<repo>#<id:03d>' to match the task /
            # archived_ids key format — else they never resolve (false
            # UNKNOWN_REQUIRES on a done+archived gate task). Branch order is
            # load-bearing: milestone-membership is tested BEFORE the digit
            # branch, so a digit-named milestone key is never taken for a task.
            namespaced_requires = []
            for r in m.requires:
                if isinstance(r, str) and r in repo_plan.milestones:
                    namespaced_requires.append(f"{repo_name}:{r}")
                elif isinstance(r, int) or (isinstance(r, str) and r.isdigit()):
                    namespaced_requires.append(f"{repo_name}#{int(r):03d}")
                else:
                    namespaced_requires.append(f"{repo_name}:{r}")
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
                # as unresolved (preserves semantics: always blocks).
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

    Uses t.key (namespaced in aggregate mode, int in single-repo).
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


# Mixed-Item-Render-Helper fuer Critical-Path-Items.
# Items koennen sein:
#   - int task-id (legacy + post-1980-mode)
#   - str milestone-key (z.B. "M1", "M1.5", "POST-MVP")
#   - list[str] parallel-Liste (z.B. ["M1", "M1.5"])
#   - str post-MVP-Beschreibung
def _render_cp_item(item, tasks: dict) -> str:
    """Render Critical-Path-Item zu String fuer fmt_boot/fmt_status/fmt_critical_path.

    explicit None-Branch (yaml-null wuerde 'None'-string).
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
        # Items zu str kasten (TypeError-Schutz)
        return "[" + " || ".join(str(x) for x in item) + "]"
    if isinstance(item, str):
        return item
    if isinstance(item, dict):
        # dict-Item -> WARN UNKNOWN_CP_ITEM_TYPE,
        # rendern via str(item) (raw repr).
        _emit_warn(f"UNKNOWN_CP_ITEM_TYPE: dict {item!r}")
        return str(item)
    return str(item)


def _explicit_order_violations(explicit: list, milestones: dict) -> list:
    """Real `requires`-edge violations in the explicit critical_path order.

    A violation = a milestone whose `requires` predecessor — itself a milestone
    present in the explicit list — appears AFTER it. Topologically-parallel
    milestones (no requires-path between them) impose no order, so their relative
    position is free; only a real edge inversion is flagged. Returns a list of
    `(predecessor, dependent)` pairs (the predecessor that must precede but
    follows), or [] when the order is a valid topological ordering.

    This replaces a positional compare against ONE arbitrary topo-sort, which
    false-flagged the tie-break order of parallel milestones (e.g. M1/M1.5, both
    gating M2 with no edge between them) as drift even though every order of two
    independent milestones is valid. Ignored, because they impose no milestone
    ordering: non-milestone entries on the path (task ids, POST-MVP strings) and
    task-id `requires`. Nested parallel groups ([M1, M1.5]) share one position.
    """
    pos: dict[str, int] = {}
    for idx, item in enumerate(explicit):
        members = item if isinstance(item, list) else [item]
        for m in members:
            key = str(m) if m is not None else ""
            if key not in pos:
                pos[key] = idx

    violations: list = []
    for key, p in pos.items():
        m = milestones.get(key)
        if m is None:
            continue  # not a milestone (task id / POST-MVP string) -> no edge
        for req in m.requires:
            rkey = str(req)
            if rkey in pos and pos[rkey] > p:
                violations.append((rkey, key))  # rkey must precede key but follows
    return violations


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
    """build set fuer 'in cp' Lookup ohne TypeError
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
    """4-stufiger Lookup mit Konsistenz-Validation.

    Stufen:
      1. plan_data["critical_path"] (Greenfield-Authority) -> 1:1 als Authority
      2. plan_data["critical_path_feature_view"] (pre-Greenfield)
      3. plan_data["legacy_critical_path_sequence"] (legacy)
      4. DAG-Topological-Sort (Last-Resort)

    Konsistenz-Validation: prueft ob explicit eine gueltige topologische
    Reihenfolge der Milestone-`requires`-Kanten ist; WARN CRITICAL_PATH_MISMATCH
    nur bei echter Kanten-Verletzung (Tie-Break paralleler Milestones ist frei).

    Skip-Conditions:
      - target leer -> skip Drift-Detection
      - tasks empty -> skip
      - DAG-Sort empty -> skip
      - target unknown -> WARN UNKNOWN_TARGET + skip Drift
    """
    # warnings via _emit_warn

    if plan_data is None:
        plan_data = {}

    # Stufe 1-3: explicit Top-Level-Keys.
    # Edge-Case: leere Liste critical_path: [] is legitim.
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

        # target leer -> skip
        if not target:
            skip_drift = True

        # UNKNOWN_TARGET: target ist weder Milestone-Key
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
            # Validate the explicit order against the requires-DAG itself, not
            # against one arbitrary topo-sort: only a REAL requires-edge inversion
            # is a mismatch. Topologically-parallel milestones (no requires-path
            # between them — e.g. M1/M1.5, both gating M2) impose no order, so any
            # relative position is valid; the old positional compare false-flagged
            # that tie-break as drift.
            violations = _explicit_order_violations(explicit, milestones)
            if violations:
                edges = ", ".join(f"{dep} -> {m}" for dep, m in violations)
                _emit_warn(
                    f"CRITICAL_PATH_MISMATCH: explicit critical_path violates "
                    f"requires-edges (must hold: {edges}); explicit={explicit}"
                )
        return explicit

    # Stufe 4: DAG-Topological-Sort (Last-Resort)
    return _topo_sort_legacy(tasks, milestones, target)


def _resolve_active_milestone(
    milestones: dict[str, Milestone], target: str
) -> Milestone | None:
    """pick the milestone whose live task chain to surface — the
    FRONTIER, i.e. the earliest non-`done` milestone on the target's
    requires-spine.

    The `target` is the program north-star (e.g. M8 Distribution); the milestone
    the user actually works at is the nearest unfinished prerequisite (e.g. M3),
    not the far target. So the active milestone is the live frontier: walk the
    spine deps-first and return the first milestone that is not yet `done`. When
    the target IS the frontier (all predecessors done), this returns the target.
    When every spine milestone is done, returns None -> renderers degrade to the
    milestone-spine-only view (graceful degradation).

    (Earlier this returned the target itself whenever non-done, which mislabels
    a far north-star target as the active milestone — surfacing M8's gate chain
    while the work is at M3. Frontier-resolution makes the label and chain follow
    the live frontier regardless of how distant the target is set.)

    Status vocab from `compute_milestone_status` (done/future/blocked/ready/
    active); only `done` is skipped — every non-done state can be the frontier.
    """
    # _build_milestone_order is deps-first, so the first non-done milestone is
    # the earliest unfinished prerequisite = the live frontier.
    for k in _build_milestone_order(milestones, target):
        m = milestones.get(k)
        if m is not None and m.status != "done":
            return m
    return None


def _resolve_gate_task_keys(m: Milestone, tasks: dict) -> list:
    """resolve ALL `type: task` gate dict-keys for milestone `m`.

    A `type: task` gate carries the gate task id as a raw int (GateCondition.id).
    The tasks dict is keyed by task.key — int in single-repo, '<repo>#<id>' in
    aggregate mode. m.tasks holds those same keys, so we match the
    gate id against the milestone's own task keys to stay mode-agnostic. Falls
    back to a direct int-key lookup for milestones whose tasks list is empty.

    a milestone can carry multiple `type: task` gates (Milestone.gate is a
    list, gate task(s)). All of them block closure, so all of their
    chains must be surfaced — returning only the first silently under-reports.
    Returns the resolved keys in gate-declaration order (deduped), or [].
    """
    gate_ids = [g.id for g in m.gate if getattr(g, "type", "") == "task"]
    keys: list = []
    seen: set = set()
    for gid in gate_ids:
        resolved = None
        # Aggregate + single-repo: m.tasks entries are valid dict keys; match by
        # the underlying task id so we never assume the key shape.
        for key in m.tasks:
            t = tasks.get(key)
            if t is not None and t.id == gid:
                resolved = key
                break
        # Single-repo direct lookup (gate task id == int key) for the case where
        # the gate task is present in `tasks` but not listed in m.tasks.
        if resolved is None and gid in tasks:
            resolved = gid
        if resolved is not None and resolved not in seen:
            seen.add(resolved)
            keys.append(resolved)
    return keys


@dataclass(frozen=True)
class ActiveChain:
    """the full render-ready result of one active-milestone
    chain computation. The renderer needs all three from a SINGLE call so the
    production path == the tested path (no re-implemented orchestration twin):

      - milestone: the resolved active Milestone (for the header label `m.key`),
        or None when nothing gating resolves (spine-only degrade).
      - chain: ordered task keys (roots-first, gate last), or [] on degrade.
      - cycle_seen: True iff the blocked_by walk hit a real back-edge (the WARN
        was already emitted by compute_active_milestone_task_chain — the
        orchestration owner — so a consumer must NOT re-emit it).
    """
    milestone: Milestone | None
    chain: list
    cycle_seen: bool


def compute_active_milestone_task_chain(
    tasks: dict,
    milestones: dict[str, Milestone],
    target: str,
) -> ActiveChain:
    """ordered task-level path through the ACTIVE milestone.

    Resolves the active milestone's gate task and walks its blocked_by chain
    transitively back to the nearest unblocked root(s), returning an
    `ActiveChain(milestone, chain, cycle_seen)`: the resolved milestone (for the
    header label), the ordered list of task keys (roots-first, gate last —
    e.g. 550->551->552->553->429), and the cycle flag.

    this is the SINGLE source of the resolve -> gate -> topo -> WARN
    sequence. `_fmt_active_chain_block` (the production render path that
    `--critical-path`/`--boot` execute) consumes this one call instead of
    re-implementing the orchestration — so the self-test TCs that exercise this
    function exercise exactly what ships. The cycle WARN is emitted HERE (the
    orchestration owner); consumers read `cycle_seen` and must not re-emit.

    This is a SEPARATE computed view from compute_critical_path: it does NOT
    feed _hashable_cp_set / _explicit_order_violations / NEXT-ACTIONS cp_flag /
    dashboard_json. The milestone spine stays the critical-path authority; this
    only adds the live next-actions task chain nested under the active milestone.

    when the milestone has multiple `type: task` gates, every gate's
    chain is surfaced (the union of their predecessor sets, topo-ordered) — a
    single milestone with two blocking gates is not silently truncated to one.

    the active milestone is resolved exactly ONCE (here). Consumers reuse
    the returned `.milestone` for the label rather than resolving again — a
    second resolve is the latent label/content divergence trap.

    Edge handling:
      - no active milestone resolvable -> milestone=None, chain=[] (degrade)
      - no gate task resolves -> chain=[] (spine-only degrade)
      - gate task has empty blocked_by -> chain=[gate-task-key] (gate alone)
      - cycle in blocked_by -> break the walk + WARN, never loop

    Mode-agnostic: resolves keys via m.tasks / task.key, so it works
    in single-repo (int keys) and aggregate ('<repo>#<id>' keys) alike.
    """
    m = _resolve_active_milestone(milestones, target)
    if m is None:
        return ActiveChain(None, [], False)
    gate_keys = _resolve_gate_task_keys(m, tasks)
    if not gate_keys:
        return ActiveChain(m, [], False)

    chain, cycle_seen = _topo_blocked_by_chain(gate_keys, tasks)
    if cycle_seen:
        _emit_warn(
            f"ACTIVE_CHAIN_CYCLE: blocked_by cycle in milestone {m.key!r} "
            f"gate-task chain — walk truncated at {len(chain)} task(s)"
        )
    return ActiveChain(m, chain, cycle_seen)


def _topo_blocked_by_chain(gate_keys: list, tasks: dict) -> tuple[list, bool]:
    """reverse-topo over `blocked_by` from the gate task(s).

    Returns (ordered_keys, cycle_seen). For the acyclic portion the order is
    roots-first — every dependency precedes its dependents (550 -> 551 ->
    ... -> gate). A diamond / shared blocker (in-degree > 1, acyclic) is ordered
    correctly and does NOT report a cycle; a real back-edge DOES (keeps the
    WARN).

    caveat: when cycle_seen is True, the nodes on the cycle never drain
    from the Kahn queue, so they CANNOT be topo-ordered. They are appended as a
    deterministic residue (sorted by str) AFTER the drained prefix — within that
    residue the "dependency precedes dependent" guarantee does NOT hold. This is
    bounded: the residue only appears alongside an always-emitted
    ACTIVE_CHAIN_CYCLE WARN (the caller emits it whenever cycle_seen is True), so
    a mis-ordered tail is never presented silently as a valid topo order.

    Two-phase, mirroring the DAG pattern in _compute_critical_path_dag:
      1. Collect the reachable predecessor subgraph from the gate(s) via BFS on
         blocked_by, recording the dependency edges (dep -> dependent).
      2. Kahn topological sort over those edges. Nodes that never drain (still
         have unmet predecessors when the queue empties) are exactly the nodes
         on a cycle — that, and only that, sets cycle_seen. This distinguishes a
         re-convergence (DAG, legal) from a back-edge (true cycle); the old
         single black `visited` set could not.
    """
    # Phase 1: reachable predecessor subgraph (nodes + dep->dependent edges).
    reachable: set = set()
    # children[dep] = dependents that list `dep` in their blocked_by.
    children: dict = defaultdict(list)
    in_deg: dict = {}
    queue: deque = deque()
    for gk in gate_keys:
        if gk not in reachable:
            reachable.add(gk)
            in_deg[gk] = 0
            queue.append(gk)
    while queue:
        key = queue.popleft()
        t = tasks.get(key)
        if t is None:
            continue
        # blocked_by entries are valid task keys in both modes (int single-repo,
        # '<repo>#<id>' aggregate after rewrite).
        for dep in t.blocked_by:
            children[dep].append(key)
            in_deg[key] = in_deg.get(key, 0) + 1
            if dep not in reachable:
                reachable.add(dep)
                in_deg.setdefault(dep, 0)
                queue.append(dep)

    # Phase 2: Kahn topo sort (roots-first). Tie-break popped roots by a stable
    # key so the order is deterministic across runs.
    ready: list = sorted((k for k in reachable if in_deg.get(k, 0) == 0), key=str)
    ordered: list = []
    while ready:
        key = ready.pop(0)
        ordered.append(key)
        newly_ready = []
        for child in children.get(key, []):
            in_deg[child] -= 1
            if in_deg[child] == 0:
                newly_ready.append(child)
        # Keep deterministic order as nodes free up.
        for nk in sorted(newly_ready, key=str):
            ready.append(nk)

    # Any node not emitted is on a cycle (its predecessors never all drained).
    cycle_seen = len(ordered) < len(reachable)
    if cycle_seen:
        # Append the cycle residue (deterministic) so the gate(s) still surface
        # rather than vanishing — the walk is truncated, not dropped.
        residue = sorted((k for k in reachable if k not in set(ordered)), key=str)
        ordered.extend(residue)
    return ordered, cycle_seen


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

    In aggregate mode, blocked_by entries can cross repo boundaries.
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

    # In aggregate mode ONLY, expand scope via backward-walk on
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

    Uses t.key (namespaced string in aggregate mode, int in single-
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

    Uses t.key throughout so the same logic applies to aggregate mode.
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

    uses t.key (namespaced in aggregate).
    archived_ids -> Silent-Pass fuer
    BROKEN_DEP wenn target_id in archived_ids set. Wenn archived_ids=None:
    auto-load aus PROJECT_ROOT (explicit project_root via module-global).

    archived_ids ist ein set[int] in
    Single-Repo-Mode UND set[str] in Aggregate-Mode (namespaced
    "<repo>#<id:03d>"). Membership-Check via direktem `dep in archived_ids` —
    set-Lookup ist type-safe (Bool-Werte werden in load_archived_task_ids
    bereits gerejected, also keine Pythonic 0==False/1==True-Kollision moeglich).
    """
    if archived_ids is None:
        # Auto-load: muss automatisch greifen — caller ohne explicit
        # archived_ids bekommt trotzdem Silent-Pass-Verhalten (CLI-Pfade,
        # Test-direkt-Aufrufe). PROJECT_ROOT-relativ.
        archived_ids = load_archived_task_ids(PROJECT_ROOT)
    issues = []
    task_keys = set(tasks.keys())

    # ID_REUSED_FROM_ARCHIVE: an active task id must not also exist in
    # docs/tasks/archive/. Archived IDs are retired, never recycled — a live id
    # colliding with an archived one breaks the WORM archive move at close (the
    # `git mv -> archive/<id>.yaml` hits an existing path) and silently
    # duplicates an id across the active+archive sets. task_keys and
    # archived_ids share one identity space by construction (int in single-repo,
    # "<repo>#<id:03d>" in aggregate — the same space the BROKEN_DEP silent-pass
    # below relies on), so the intersection is collision-exact in both modes.
    for reused in sorted(task_keys & archived_ids, key=str):
        issues.append(ValidationIssue(
            "ID_REUSED_FROM_ARCHIVE", "ERROR", task_id=reused,
            detail="active task id also present in docs/tasks/archive/ — "
                   "archived ids are retired; pick the next free id "
                   "(max over docs/tasks/ + docs/tasks/archive/, + 1)"))

    for t in tasks.values():
        tid_for_issue = t.key  # namespaced in aggregate mode
        # NO_MILESTONE (terminal tasks may have null milestone — they're completed)
        if not t.milestone and not t.is_terminal:
            issues.append(ValidationIssue("NO_MILESTONE", "ERROR", task_id=tid_for_issue,
                                          detail="task has no milestone field"))
        elif not t.milestone and t.is_terminal:
            pass  # terminal tasks without milestone are fine
        elif t.milestone not in milestones and not t.is_terminal:
            # Terminal tasks (done/superseded) get a free pass — symmetric with the
            # NO_MILESTONE branch above. Archived/done tasks may point at retired
            # milestone keys after a reorg; that is audit-trail, not a defect.
            issues.append(ValidationIssue("UNKNOWN_MILESTONE", "ERROR", task_id=tid_for_issue,
                                          detail=f"milestone '{t.milestone}' not in plan.yaml"))
        # BROKEN_DEP (Silent-Pass: archived Tasks skipped)
        for dep in t.blocked_by:
            if dep not in task_keys:
                # Silent-Pass: archived id -> kein ERR.
                # archived_ids ist set[int] (single-repo)
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
        # INVALID_STATUS: a status outside the sanctioned enum is silently
        # mis-handled — the pending-keyed critical-path / next-actions logic
        # excludes it, so a rogue/typo'd status (e.g. `open`) drops the task off
        # the live frontier with no signal. Flag it loudly so it can't corrupt
        # the plan view unseen. (Terminal tasks are validated the same way.)
        if t.status not in KNOWN_TASK_STATUSES:
            issues.append(ValidationIssue("INVALID_STATUS", "WARN", task_id=tid_for_issue,
                                          detail=f"status {t.status!r} not in sanctioned enum "
                                                 f"{sorted(KNOWN_TASK_STATUSES)} — excluded from "
                                                 f"critical-path/next-actions (treated as non-pending)"))
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
    # iterate via t.key (polymorphic int/str).
    in_deg = dict.fromkeys(tasks, 0)
    for t in tasks.values():
        # set(): count each DISTINCT dependency once. The drain loop below
        # uses a membership test (`if tk in t2.blocked_by`) which fires once
        # per dependent, so the build loop must be dedup-symmetric — otherwise
        # a duplicate blocked_by entry (e.g. [1, 1], not a real cycle) inflates
        # the in-degree, the node never reaches 0, and a phantom CYCLE fires.
        for dep in set(t.blocked_by):
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
        # (if tasks are in_progress, gate PASS is expected — prerequisites met).
        # Skip when the milestone has no "hard" gates — preliminary + manual gates
        # don't encode prerequisites, so their PASS state carries no implication
        # about whether member tasks should be done. A manual gate explicitly
        # delegates closure to human judgement; firing DRIFT against it is
        # structurally noise.
        if m.gate and not m.is_group:
            hard_gates = [g for g in m.gate
                          if not g.preliminary and g.type != "manual"]
            if hard_gates:
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
        # feature_milestones requires-Eintraege
        # koennen sein: milestone-key (str) ODER task-id (int oder digit-str).
        # Task-ID-Refs werden NICHT als UNKNOWN_REQUIRES gewertet wenn die
        # Task existiert (im tasks-dict oder in archived_ids).
        for req in m.requires:
            if isinstance(req, str) and req in milestones:
                continue
            # Namespaced task-ref (aggregate mode): "<repo>#<id:03d>" matches
            # the task / archived_ids key format directly.
            if isinstance(req, str) and (req in tasks or req in archived_ids):
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
# Task-schema conformance (framework/task-schema.yaml SoT)
# ---------------------------------------------------------------------------
#
# Read-only audit layer. It re-reads each docs/tasks/*.yaml via
# yaml.safe_load — it MUST NOT consume the constructed Task (lossy:
# status→pending, effort→M defaults, non-int blocked_by filtered,
# priority not a Task field). Every field name / required-set / value
# vocabulary / filename rule / calibration switch is dereferenced from
# the parsed schema dict; zero schema knowledge is hardcoded here.
#
# Trust boundary. `_load_task_schema` returns
# `dict | None`; "is a dict" is NOT "is a valid schema". Every `.get()`
# after the load is otherwise an unenforced trust assumption. Rather
# than scattering per-site isinstance guards (which provably recurse one
# nesting level deeper every pass), the document transitions from
# *untrusted bytes* to *validated structure* at exactly ONE seam:
# `_validate_schema_structure`, called first thing in
# `validate_task_schema_conformance` (after the None-check, before any
# consumer / re.compile). The expected shape is DECLARATIVE DATA
# (`_TASK_SCHEMA_SHAPE`); a single generic walker interprets it. Adding
# schema DEPTH later (a deeper node of an already-expressible kind) =
# adding a data node, no new code branches.
#
# Scope of the guarantee — read this before trusting it. This boundary
# closes exactly ONE class: the structural WRONG-TYPE class, i.e. a
# key that IS PRESENT but whose value has the wrong Python type, at
# any nesting depth. It does NOT express CONDITIONAL-REQUIREDNESS: a
# key that is required only given a sibling's value (e.g. a field-def
# with `type: enum` but the `values:` key entirely ABSENT) is
# type-valid by this grammar and passes — the consumer then silently
# drops that field's vocab. That is a KNOWN, owner-ACCEPTED residual
# (MEDIUM, accepted): the descriptor grammar
# below has no "required-because-of-a-sibling" construct, and adding
# one WOULD be a new code branch. The accepted trigger is human
# damage to the LOCKED framework/task-schema.yaml, not a code path.
# Do not "fix" this in a comment pass and do not overstate the
# guarantee in either direction.


# Version this descriptor was authored against. MUST equal
# `schema_version` in framework/task-schema.yaml. The positive-anchor
# self-test asserts the real locked schema passes the walker; this pin
# additionally forces a CONSCIOUS descriptor revisit on any intentional
# schema evolution (mismatch -> _schema_defect ESCALATE, never silent
# under-validation).
_TASK_SCHEMA_VERSION = 1

# Declarative structural mirror of framework/task-schema.yaml — the
# closed set of nodes validate_task_schema_conformance dereferences
# (mechanically equal to the `schema.get(...)` / nested-deref set; a
# reviewer confirms via grep over the schema-consumer functions, not by
# trusting this comment). Node grammar (all keys optional unless noted):
#   type      : expected Python type (or tuple) for the value
#   what      : human label for `type` (defect message)
#   required  : True -> key MUST be present (default False; absent
#               optional key != malformed -> no over-fire)
#   elem_type : list-element expected type (only for type==list)
#   elem_what : human label for elem_type
#   children  : {child_key: node} — fixed-key sub-mapping
#   each_value: node applied to EVERY value of a mapping
#               (mapping-of-mappings, e.g. fields.<name>)
#   when      : (sibling_key, sibling_value) — sibling-LOCALITY only:
#               the node is type-checked ONLY when the sibling key
#               equals that value (e.g. enum `values`).
#               `when` does NOT make the key conditionally REQUIRED —
#               if the gated key is ABSENT it is simply skipped, never
#               flagged. Conditional requiredness is not expressible
#               in this grammar (see residual note below).
#
# Provenance + scope (accepted residual). _TASK_SCHEMA_SHAPE
# (and _FIELD_DEF_SHAPE) is the structural MIRROR of
# framework/task-schema.yaml — a SECOND structural description of the
# schema in Python that MUST NOT silently drift from the YAML SoT. It
# validates structural TYPE ONLY (a present key whose value is the
# wrong type, at any depth); it deliberately does NOT validate
# conditional-requiredness (a sibling-gated key being entirely
# absent). That gap is the owner-accepted residual (MEDIUM):
# extreme edge case, trigger is human damage to the LOCKED schema, no
# behavioural fix. A `schema_version` bump REQUIRES revisiting this
# constant (the version pin enforces it); the self-test positive
# anchor asserts the real schema passes here.
_FIELD_DEF_SHAPE: dict = {
    "type": dict,
    "what": "a mapping",
    "children": {
        "type": {"type": str, "what": "a string"},
        # enum vocab: a list ONLY when this field-def declares
        # type==enum. A scalar here pre-fix silently disabled that
        # field's vocab enforcement — now ESCALATE. NOTE
        # (accepted): `when` gates only the TYPE check. If
        # `values` is entirely ABSENT under type==enum this descriptor
        # does NOT flag it (no conditional-requiredness construct); the
        # consumer then silently drops that field's vocab. Accepted
        # residual — trigger is human damage to the LOCKED schema.
        "values": {
            "type": list,
            "what": "a list",
            "when": ("type", "enum"),
        },
        "read_aliases": {"type": dict, "what": "a mapping"},
    },
}

_TASK_SCHEMA_SHAPE: dict = {
    "type": dict,
    "what": "a mapping",
    "children": {
        # Version pin (see _TASK_SCHEMA_VERSION + the exact-match
        # check in _validate_schema_structure).
        "schema_version": {"type": int, "what": "an int"},
        "filename": {
            "type": dict,
            "what": "a mapping",
            "children": {
                # task_basename feeds re.compile() — a non-str pre-fix
                # raised an uncaught TypeError (crash class).
                "task_basename": {"type": str, "what": "a string"},
                "id_matches_basename": {"type": bool, "what": "a bool"},
            },
        },
        "required_always": {
            "type": list, "what": "a list",
            "elem_type": str, "elem_what": "a string",
        },
        "required_when_open": {
            "type": list, "what": "a list",
            "elem_type": str, "elem_what": "a string",
        },
        "required_when_terminal": {
            "type": list, "what": "a list",
            "elem_type": str, "elem_what": "a string",
        },
        "terminal_status": {
            "type": list, "what": "a list",
            "elem_type": str, "elem_what": "a string",
        },
        "fields": {
            "type": dict,
            "what": "a mapping",
            "each_value": _FIELD_DEF_SHAPE,
        },
        "validator": {
            "type": dict,
            "what": "a mapping",
            "children": {
                # locked: non-bool present -> defect/ESCALATE,
                # NEVER bool()/string-literal coercion.
                "strict_after_backfill": {"type": bool, "what": "a bool"},
            },
        },
    },
}


def _walk_schema_shape(node: dict, value: object, path: str) -> str | None:
    """Generic data-driven checker: walk `node` (a _TASK_SCHEMA_SHAPE
    descriptor) against `value`. Returns None when conforming, else a
    single human-readable defect string.

    Pure interpreter of the descriptor DATA — there is NO per-key
    isinstance ladder here. Adding a schema node = adding a data entry
    in _TASK_SCHEMA_SHAPE; this function never grows. Absent optional
    key != malformed (over-fire-safe): a child is only validated when
    PRESENT, unless its node sets required=True.
    """
    expected = node.get("type")
    if expected is not None and not isinstance(value, expected):
        # bool is an int subclass — guard would mis-accept True as int.
        # _TASK_SCHEMA_SHAPE has no int node that may receive a bool,
        # but be explicit so a future int node is not silently fooled.
        what = node.get("what", "the expected type")
        return (f"{path!r} must be {what}, got "
                f"{type(value).__name__}")
    if expected is int and isinstance(value, bool):
        what = node.get("what", "the expected type")
        return f"{path!r} must be {what}, got bool"

    elem_type = node.get("elem_type")
    if elem_type is not None and isinstance(value, list):
        for idx, elem in enumerate(value):
            if not isinstance(elem, elem_type):
                elem_what = node.get("elem_what", "the expected type")
                return (f"{path}[{idx}] must be {elem_what}, got "
                        f"{type(elem).__name__}")

    children = node.get("children")
    if children is not None and isinstance(value, dict):
        for child_key, child_node in children.items():
            present = child_key in value
            if not present:
                if child_node.get("required"):
                    return (f"{path}.{child_key!r} is required but "
                            "absent")
                continue
            when = child_node.get("when")
            if when is not None:
                sib_key, sib_val = when
                if value.get(sib_key) != sib_val:
                    continue
            child_val = value.get(child_key)
            # Absent optional key != malformed: a YAML null is treated
            # as absent (parity with the prior `is not None` predicate
            # the byte-identical bar depends on).
            if child_val is None and not child_node.get("required"):
                continue
            sub = _walk_schema_shape(
                child_node, child_val, f"{path}.{child_key}")
            if sub is not None:
                return sub

    each_value = node.get("each_value")
    if each_value is not None and isinstance(value, dict):
        for k, v in value.items():
            sub = _walk_schema_shape(each_value, v, f"{path}.{k}")
            if sub is not None:
                return sub

    return None


def _validate_schema_structure(schema: dict) -> str | None:
    """THE trust boundary. Transition the parsed schema from untrusted
    bytes to validated structure. Returns None on a conforming schema,
    else a single human-readable defect string (the caller routes it
    through `_schema_defect` -> SCHEMA_FILE ERROR + ESCALATE — no
    divergent error path).

    Two-part drift defense:
      1. Generic walk of _TASK_SCHEMA_SHAPE (the structural mirror).
      2. schema_version pin: the loaded version MUST equal the version
         the descriptor was authored against, so an intentional schema
         evolution FORCES a conscious descriptor update instead of
         silent under-validation.
    """
    defect = _walk_schema_shape(_TASK_SCHEMA_SHAPE, schema, "schema")
    if defect is not None:
        return defect
    sv = schema.get("schema_version")
    if sv is not None and sv != _TASK_SCHEMA_VERSION:
        return (f"schema_version {sv!r} != descriptor version "
                f"{_TASK_SCHEMA_VERSION} — the structural descriptor "
                "_TASK_SCHEMA_SHAPE is out of date relative to "
                "framework/task-schema.yaml; the descriptor MUST be "
                "revisited for this schema_version before validation "
                "can be trusted")
    return None


def _load_task_schema(schema_path: Path | None = None) -> dict | None:
    """Parse the machine-readable task-schema SoT.

    Returns the parsed dict, or None when the file is missing or
    unparseable (the caller turns None into a SCHEMA_FILE ERROR and
    escalates — there is no invented default).
    """
    path = schema_path if schema_path is not None else TASK_SCHEMA_PATH
    try:
        raw = path.read_text(encoding="utf-8")
    except (OSError, ValueError):  # ValueError = UnicodeDecodeError (non-UTF-8)
        return None
    try:
        data = yaml.safe_load(raw)
    except yaml.YAMLError:
        return None
    if not isinstance(data, dict):
        return None
    return data


def _schema_terminal_statuses(schema: dict) -> set:
    val = schema.get("terminal_status")
    return set(val) if isinstance(val, list) else set()


def _schema_field_defs(schema: dict) -> dict:
    fields = schema.get("fields")
    return fields if isinstance(fields, dict) else {}


def _schema_known_field_names(schema: dict) -> set:
    """Every field name the schema knows: fields map + every required set."""
    names: set = set(_schema_field_defs(schema).keys())
    for key in ("required_always", "required_when_open", "required_when_terminal"):
        val = schema.get(key)
        if isinstance(val, list):
            names.update(val)
    return names


def _schema_enum_values(field_def: object) -> list | None:
    if isinstance(field_def, dict) and field_def.get("type") == "enum":
        vals = field_def.get("values")
        if isinstance(vals, list):
            return vals
    return None


def _load_repo_extension_fields(tasks_dir: Path) -> set:
    """Per-repo task-field extension allowlist.

    The schema (`task-schema.yaml`) is a lean, framework-universal core;
    a consumer repo declares its own domain field names in
    `<repo>/docs/task-schema-extensions.yaml` (`extension_fields:` — a
    list of names). Those names are treated as known for THAT repo only,
    so the shared schema stays clean and an unknown-field WARN means a
    genuine typo or an undeclared field, not a domain-vocabulary mismatch.

    Optional + fail-safe: absent, unparseable, or malformed → empty set
    (a broken extension file never bricks validation; it only loses its
    own allowances). Repo-local; excluded from the OSS mirror by
    release-sync.sh.
    """
    ext_path = tasks_dir.parent / "task-schema-extensions.yaml"
    try:
        raw = ext_path.read_text(encoding="utf-8")
    except (OSError, ValueError):
        # ValueError covers UnicodeDecodeError (non-UTF-8 bytes): the
        # extension file is optional + fail-safe; a malformed one must
        # never crash the validator (which is a pre-commit BLOCK gate).
        return set()
    try:
        data = yaml.safe_load(raw)
    except yaml.YAMLError:
        return set()
    if not isinstance(data, dict):
        return set()
    names = data.get("extension_fields")
    if not isinstance(names, list):
        return set()
    return {n for n in names if isinstance(n, str)}


def validate_task_schema_conformance(
    project_root: Path | None = None,
    single_id: int | None = None,
    schema_path: Path | None = None,
) -> list[ValidationIssue]:
    """Schema-driven conformance pass over raw task YAML dicts.

    - project_root: repo root (or its docs/tasks dir). None → PROJECT_ROOT.
    - single_id: when set, only docs/tasks/<id>.yaml is checked (no
      milestone / cycle / cross-repo — pure schema check).
    - schema_path: override for the schema SoT (self-test injection).

    Severity is DATA-DRIVEN from validator.* in the schema:
      * structural (missing id, unparseable pure-numeric YAML,
        id != int(basename)) → ERROR regardless of calibration.
      * missing required_when_open / out-of-vocab → WARN while
        validator.strict_after_backfill is false, else ERROR.
      * unknown status value → tolerant, classified open, never error.
    """
    import re

    issues: list[ValidationIssue] = []

    schema = _load_task_schema(schema_path)
    if schema is None:
        target = schema_path if schema_path is not None else TASK_SCHEMA_PATH
        issues.append(ValidationIssue(
            "SCHEMA_FILE", "ERROR",
            detail=(f"task-schema SoT missing/unparseable: {target} — "
                    "ESCALATE: cannot validate task conformance without the "
                    "schema; tree NOT silently passed")))
        return issues

    def _schema_defect(detail: str) -> list[ValidationIssue]:
        return [ValidationIssue(
            "SCHEMA_FILE", "ERROR",
            detail=(f"task-schema SoT structurally invalid: {detail} — "
                    "ESCALATE: cannot validate task conformance with a "
                    "malformed schema; tree NOT silently passed"))]

    # THE trust boundary. Ordering is
    # load-bearing: None-check FIRST (above, unchanged), structural
    # check SECOND, both BEFORE any `_schema_*` consumer or re.compile.
    # The expected shape is declarative DATA (_TASK_SCHEMA_SHAPE) walked
    # by a single generic checker — there is no per-site isinstance
    # ladder here, so a deeper nesting level cannot recur the
    # defect class (it would be a missing DATA node, caught by
    # the §4 positive anchor self-test, not a missing code branch). A
    # present-but-wrong-type node (including filename.task_basename,
    # fields.<name>.values, validator.strict_after_backfill — the
    # keys) is fail-safe to the SAME contract as a missing
    # schema: SCHEMA_FILE ERROR + ESCALATE, never a traceback, never a
    # silent degrade. Absent optional key != malformed (over-fire-safe).
    if (d := _validate_schema_structure(schema)) is not None:
        return _schema_defect(d)

    # Past the boundary the schema is validated structure: `filename`
    # dict-or-absent, the four list keys lists, `fields` a mapping of
    # mappings, `validator` dict-or-absent, strict_after_backfill
    # bool-or-absent. These reads are now trusted (the `_schema_*`
    # accessors keep their defensive isinstance as a no-op on a
    # conformant schema — they are trusted-read accessors, NOT the
    # removed per-site schema guards).
    filename_raw = schema.get("filename")
    filename_rules = filename_raw if isinstance(filename_raw, dict) else {}
    task_basename_re = filename_rules.get("task_basename") or r"^[0-9]+$"
    id_matches_basename = bool(filename_rules.get("id_matches_basename"))

    field_defs = _schema_field_defs(schema)
    known_fields = _schema_known_field_names(schema)
    required_always = list(schema.get("required_always") or [])
    required_when_open = list(schema.get("required_when_open") or [])
    required_when_terminal = list(schema.get("required_when_terminal") or [])
    terminal_statuses = _schema_terminal_statuses(schema)

    validator_raw = schema.get("validator")
    validator_cfg = validator_raw if isinstance(validator_raw, dict) else {}
    # (locked): the calibration switch is a Python bool by
    # schema contract. The trust boundary already rejected a present
    # non-bool (-> SCHEMA_FILE ERROR + ESCALATE, NO bool()/string
    # coercion). Absent -> warn-first default (False).
    saf_raw = validator_cfg.get("strict_after_backfill")
    strict_after_backfill = saf_raw if isinstance(saf_raw, bool) else False
    # Calibration switch read in FULL — never assume strict. The
    # required/out-of-vocab severity is WARN until BOTH the backfill is
    # merged AND the switch is flipped (out_of_vocab/calibration are
    # advisory while strict_after_backfill is false).
    soft_severity = "ERROR" if strict_after_backfill else "WARN"

    name_re = re.compile(task_basename_re)

    # Resolve the tasks directory (mirror load_tasks path-resolution).
    if project_root is None:
        tasks_dir = TASKS_DIR
    elif project_root.name == "tasks" and project_root.is_dir():
        tasks_dir = project_root
    else:
        tasks_dir = project_root / "docs" / "tasks"

    # Lean framework core (schema fields) + repo-local domain fields:
    # union the per-repo extension allowlist so a consumer's declared
    # vocabulary is known for its own tree without a framework-schema edit.
    known_fields = known_fields | _load_repo_extension_fields(tasks_dir)

    if single_id is not None:
        # (belt): a single-id target has an explicit name that
        # MUST resolve or error — it may never silently `continue`. The
        # negative/zero argv case is rejected at the dispatch boundary
        # (exit 2); this guard is defence-in-depth for direct callers.
        if not name_re.match(str(single_id)):
            issues.append(ValidationIssue(
                "SCHEMA_FILE", "ERROR", task_id=single_id,
                detail=(f"invalid single-id target {single_id!r}: fails "
                        f"task_basename grammar {task_basename_re!r} — "
                        "ESCALATE: single-id has an explicit target that "
                        "must resolve or error, never silently skipped")))
            return issues
        # archived terminal tasks live in
        # docs/tasks/archive/<id>.yaml. In single-id mode, fall back to
        # the archive when the primary path is absent — an archived task
        # is terminal (only id+status enforced), NOT a 'file not found'
        # ERROR.
        primary = tasks_dir / f"{single_id}.yaml"
        archived = tasks_dir / "archive" / f"{single_id}.yaml"
        if primary.exists():
            candidates = [primary]
        elif archived.exists():
            candidates = [archived]
        else:
            issues.append(ValidationIssue(
                "SCHEMA_FILE", "ERROR", task_id=single_id,
                detail=f"task file not found: {primary}"))
            return issues
    else:
        candidates = sorted(p for p in tasks_dir.glob("*.yaml"))

    # zero-pad duplicate-logical-id collision. `327.yaml` and
    # `0327.yaml` both map to int(basename)=327 — pre-fix BOTH were
    # silently validated as task 327. Detect as a duplicate-id ERROR
    # (calibration-independent structural defect).
    if single_id is None:
        by_logical: dict[int, list[str]] = {}
        for p in candidates:
            bn = p.stem
            if name_re.match(bn):
                by_logical.setdefault(int(bn), []).append(p.name)
        for lid, names in sorted(by_logical.items()):
            if len(names) > 1:
                issues.append(ValidationIssue(
                    "SCHEMA_ID_MISMATCH", "ERROR", task_id=lid,
                    detail=(f"duplicate logical task id {lid}: "
                            f"{sorted(names)} all resolve to "
                            f"int(basename)={lid}")))

    for yaml_path in candidates:
        basename = yaml_path.stem
        # Filename grammar: a *task* has a pure-numeric basename. Any
        # NNN-<suffix> aux file is never a task — never validated/errored.
        if not name_re.match(basename):
            continue

        basename_int = int(basename)
        tid_for_issue: int | None = basename_int

        try:
            data = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
        except (yaml.YAMLError, OSError, ValueError):
            # A pure-numeric file that won't parse is a structural ERROR
            # (calibration-independent) — it claims to be a task.
            issues.append(ValidationIssue(
                "SCHEMA_FILE", "ERROR", task_id=tid_for_issue,
                detail=f"unparseable task YAML: {yaml_path}"))
            continue

        if not isinstance(data, dict):
            issues.append(ValidationIssue(
                "SCHEMA_FILE", "ERROR", task_id=tid_for_issue,
                detail=f"task YAML is not a mapping: {yaml_path}"))
            continue

        raw_id = data.get("id")
        # Structural: missing id (ERROR regardless of calibration).
        if raw_id is None:
            issues.append(ValidationIssue(
                "SCHEMA_MISSING_REQUIRED", "ERROR", task_id=tid_for_issue,
                detail=f"required field 'id' missing in {yaml_path.name}"))
        else:
            try:
                id_int = int(raw_id) if not isinstance(raw_id, bool) else None
            except (TypeError, ValueError):
                id_int = None
            if id_int is None:
                issues.append(ValidationIssue(
                    "SCHEMA_ID_MISMATCH", "ERROR", task_id=tid_for_issue,
                    detail=f"'id' is not an int: {raw_id!r} in {yaml_path.name}"))
            elif id_matches_basename and id_int != basename_int:
                # Structural: id != int(basename) — ERROR regardless.
                issues.append(ValidationIssue(
                    "SCHEMA_ID_MISMATCH", "ERROR", task_id=tid_for_issue,
                    detail=(f"id {id_int} != int(basename) {basename_int} "
                            f"in {yaml_path.name}")))

        # Status classification. Unknown value → tolerant-read-as-open,
        # never silently terminal, never an error.
        raw_status = data.get("status")
        is_open = True
        if isinstance(raw_status, str) and raw_status in terminal_statuses:
            is_open = False
        # raw_status not in the schema status enum → unknown → stays open.

        # Required-set checks. Terminal tasks (done / superseded / wontfix /
        # absorbed) enforce ONLY required_when_terminal (id + status): history
        # is not rewritten, so a missing field on a closed task is not a defect
        # and cannot be meaningfully backfilled. Open tasks enforce
        # required_always (+ required_when_open below).
        base_required = required_always if is_open else required_when_terminal
        for fname in base_required:
            if data.get(fname) is None:
                # 'id' already handled structurally above.
                if fname == "id":
                    continue
                issues.append(ValidationIssue(
                    "SCHEMA_MISSING_REQUIRED", soft_severity,
                    task_id=tid_for_issue,
                    detail=(f"required field '{fname}' missing in "
                            f"{yaml_path.name}")))
        if is_open:
            for fname in required_when_open:
                if data.get(fname) is None:
                    issues.append(ValidationIssue(
                        "SCHEMA_MISSING_REQUIRED", soft_severity,
                        task_id=tid_for_issue,
                        detail=(f"required-when-open field '{fname}' missing "
                                f"in {yaml_path.name} (status="
                                f"{raw_status!r}, classified open)")))

        # Unknown field names (forward-compat: WARN, never blocks).
        for key in data:
            if key not in known_fields:
                issues.append(ValidationIssue(
                    "SCHEMA_UNKNOWN_FIELD", "WARN", task_id=tid_for_issue,
                    detail=(f"unknown field '{key}' in {yaml_path.name} "
                            "(not in task-schema.yaml fields/required sets "
                            "or the repo task-schema-extensions.yaml)")))

        # Value-vocabulary checks. Every enum field's vocab is read from
        # the schema. priority is write-strict: read_aliases are tolerant
        # on READ-classification only; an alias written into a YAML is
        # out-of-vocab here.
        for fname, fdef in field_defs.items():
            enum_vals = _schema_enum_values(fdef)
            if enum_vals is None:
                continue
            if fname not in data or data.get(fname) is None:
                continue
            value = data.get(fname)
            if value in enum_vals:
                continue
            if fname == "status":
                # Unknown status is tolerant (handled above) — not vocab err.
                continue
            issues.append(ValidationIssue(
                "SCHEMA_VOCAB", soft_severity, task_id=tid_for_issue,
                detail=(f"field '{fname}' value {value!r} not in schema "
                        f"vocab {enum_vals} ({yaml_path.name})")))

    return issues


# ---------------------------------------------------------------------------
# Autonomy Consistency (framework/agent-autonomy.md SoT)
# ---------------------------------------------------------------------------

# SoT-Datei der Autonomy-Regeln. Mirror-Check, Existenz-Check, Referenz-
# Integritaet und Drift-Warnung werden gegen dieses Dokument gefahren.
# Framework-intern → FRAMEWORK_ROOT.
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

    Hintergrund: Der Mirror-Check darf nicht mehr an die feste
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

    Hintergrund: Die Gate-Polymorphie in agent-autonomy.md erlaubt
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
    """Autonomy-Consistency-Checks.

    Prueffaelle:
      Check 1 — Mirror-Check CLAUDE.md §5 ↔ AGENTS.md §5 (ERROR bei Abweichung)
      Check 2 — Existenz-Check framework/agent-autonomy.md (ERROR bei Fehlern)
      Check 3 — Referenz-Integritaet in Konsumenten-Dateien (ERROR pro fehlendem Verweis)
      Check 4 — Cross-Reference Drift-Warnung operational.md ↔ agent-autonomy.md (WARN)
    """
    import re
    issues: list[ValidationIssue] = []

    # Check 1: Mirror-Check CLAUDE.md ↔ AGENTS.md
    # Scope ist nicht mehr die feste Sektion "### 5. Code-Delegation",
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
            # Merger-Faelle mitzaehlen — Agenten, die in der
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
                # Zellen wie `handoff:build-workflow oder
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

            # Gate-Peer-Targets als bekannte Agenten mitfuehren
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

    # Critical path (Mixed-Items via _render_cp_item)
    if critical_path:
        cp_labels = [_render_cp_item(item, tasks) for item in critical_path]
        total_effort = 0
        has_effort_item = False  # any int task-id item that carries effort.
        for item in critical_path:
            if isinstance(item, int) and not isinstance(item, bool):
                t = tasks.get(item)
                if t is not None:
                    total_effort += t.effort_weight
                    has_effort_item = True
        lines.append(f"CRITICAL PATH -> {target}:")
        lines.append(f"  {' -> '.join(cp_labels)}")
        # suppress the effort line for a milestone-key (string)
        # spine — a structural 0 reads as a real metric when it is not one.
        if has_effort_item:
            lines.append(f"  Effort-weighted length: {total_effort}")
        # Bottleneck: first non-done task on path (only int items count)
        for item in critical_path:
            if isinstance(item, int) and not isinstance(item, bool):
                t = tasks.get(item)
                if t is not None and not t.is_done:
                    lines.append(f"  Bottleneck: Task {_format_tid(t)} ({t.title[:40]})")
                    break
        # nest the live active-milestone task chain under the
        # milestone spine so a boot read answers "what's the next critical-path
        # task" without a manual plan.yaml read.
        lines.extend(_fmt_active_chain_block(tasks, milestones, target))
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
        # feature_milestones-spezifische Sub-Zeilen
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
            loc = _fmt_issue_loc(issue)  # shared helper handles global issues
            prefix = f"{loc} — " if loc else ""
            lines.append(f"  {issue.check}: {prefix}{issue.detail}")
        remaining = len(errors) + len(warns) - 10
        if remaining > 0:
            lines.append(f"  ... and {remaining} more")

    return "\n".join(lines)


def fmt_status(tasks, milestones):
    """Milestone-Overview. zeigt
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
        # feature_milestones-spezifische Sub-Zeilen
        if getattr(m, "feature", ""):
            lines.append(f"           feature: {m.feature}")
        if getattr(m, "app_status_post_milestone", ""):
            lines.append(f"           app_status: {m.app_status_post_milestone}")
        if getattr(m, "parallel_to", []):
            lines.append(f"           parallel_to: {', '.join(m.parallel_to)}")
        # Pre-Set-Gates mit preliminary-Marker
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


_VALID_EFFORTS = frozenset(EFFORT_WEIGHTS)  # {"S","M","L","XL"}


def _fmt_active_chain_block(tasks, milestones, target, indent="  "):
    """render the active-milestone task chain as nested lines.

    Returns a list of rendered lines (possibly empty when no chain resolves —
    degrade). Shared by fmt_critical_path + fmt_boot.

    the data comes from a SINGLE compute_active_milestone_task_chain
    call — the same function the 13 self-test TCs exercise. This renderer does
    NOT re-implement the resolve -> gate -> topo orchestration, so the shipped
    path is exactly the tested path (no divergence twin). The header label
    (`m.key`), the chain content, and the cycle flag all come from that one
    result.

    the active milestone is resolved exactly ONCE — inside the public
    function — and reused here via `result.milestone` for the header. This
    renderer does NOT resolve again, so the label and the content can never
    point at different milestones, AND the resolve (a BFS+topo over the
    requires-graph) runs once per render, not twice. The cycle WARN is emitted
    by the public function (orchestration owner); this renderer must not
    re-emit it.
    """
    result = compute_active_milestone_task_chain(tasks, milestones, target)
    m = result.milestone
    chain = result.chain
    if m is None or not chain:
        return []
    lines = [f"{indent}ACTIVE-MILESTONE TASK PATH ({m.key}):"]
    # Known limitation: in aggregate mode
    # _render_cp_item's str-branch returns the bare '<repo>#<id>' key (no title);
    # the status mark below is appended outside the renderer. Single-repo int
    # keys render '[id] title' inside _render_cp_item. Cosmetic only — the id is
    # present and `Next on chain:` still renders the title. Not widened here.
    labels = []
    chain_effort = 0
    unset_effort = 0  # tasks with no explicit {S,M,L,XL} effort.
    for key in chain:
        t = tasks.get(key)
        if t is not None:
            chain_effort += t.effort_weight
            if t.effort not in _VALID_EFFORTS:
                unset_effort += 1
            status_mark = "done" if t.is_done else t.status
            labels.append(f"{_render_cp_item(key, tasks)} [{status_mark}]")
        else:
            labels.append(_render_cp_item(key, tasks))
    lines.append(f"{indent}  {' -> '.join(labels)}")
    # the chain-effort metric must be honest. A task with no
    # explicit {S,M,L,XL} effort silently contributes the default weight (3);
    # presenting that as an exact number is the same misleading-metric class as
    # the zero placeholder. Mark it estimated and name the unset count so the
    # reader never reads a defaulted weight as a measured estimate.
    if unset_effort:
        plural = "s" if unset_effort != 1 else ""
        lines.append(
            f"{indent}  Chain effort-weighted length: ~{chain_effort} "
            f"({unset_effort} task{plural} effort-unset, counted as M)"
        )
    else:
        lines.append(f"{indent}  Chain effort-weighted length: {chain_effort}")
    # Bottleneck: first non-done task on the chain.
    for key in chain:
        t = tasks.get(key)
        if t is not None and not t.is_done:
            lines.append(f"{indent}  Next on chain: [{_format_tid(t)}] {t.title[:40]}")
            break
    return lines


def fmt_critical_path(tasks, critical_path, target, milestones=None):
    """Mixed-Item-Render via _render_cp_item.
    Items koennen sein: int task-id, str milestone-key, list[str] parallel,
    str post-MVP-Beschreibung.

    when `milestones` is supplied, the live active-milestone task
    chain (gate -> blocked_by) is nested under the milestone spine.
    """
    if not critical_path:
        return f"No critical path to {target} (no pending tasks in scope)"
    lines = [f"CRITICAL PATH -> {target}:"]
    total = 0
    has_effort_item = False  # any int task-id item that carries effort.
    for item in critical_path:
        rendered = _render_cp_item(item, tasks)
        if isinstance(item, int) and not isinstance(item, bool):
            t = tasks.get(item)
            if t is not None:
                total += t.effort_weight
                has_effort_item = True
                done_mark = "done" if t.is_done else t.status
                lines.append(f"  {rendered} ({t.milestone}) effort:{t.effort} [{done_mark}]")
            else:
                lines.append(f"  {rendered} (archived)")
        elif isinstance(item, list):
            # Parallel-Liste: explizit als parallel-Marker rendern
            lines.append(f"  {rendered}  [parallel]")
        else:
            lines.append(f"  {rendered}")
    # a milestone-key (string) spine has no effort-bearing items,
    # so the sum is a structural 0 — a rendered "0" reads as a real metric when
    # it is not one. Only show the effort line when the spine actually carries
    # effort-bearing task items.
    if has_effort_item:
        lines.append(f"\nTotal effort-weighted length: {total}")
    # nest the active-milestone task chain under the spine.
    if milestones is not None:
        chain_lines = _fmt_active_chain_block(tasks, milestones, target)
        if chain_lines:
            lines.append("")
            lines.extend(chain_lines)
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
    # task_id may be int (single-repo) or str "repo#id" (aggregate).
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

    uses t.key (namespaced in aggregate mode) for task references.
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
            "tasks": sorted(milestone_tasks, key=str),  # str-sort handles both modes
        })

    cp_set = _hashable_cp_set(critical_path)
    task_list = []
    # sort by (repo, id) so aggregate mode groups by namespace
    for t in sorted(tasks.values(), key=lambda x: (x._repo, x.id)):
        task_list.append({
            "id": t.id, "title": t.title, "status": t.status,
            "milestone": t.milestone, "effort": t.effort, "area": t.area,
            "assignee": t.assignee, "on_critical_path": t.key in cp_set,
            "blocking_score": blocking_scores.get(t.key, 0),
            "blocked_by": t.blocked_by, "spec_ref": t.spec_ref,
            "board_result": t.board_result, "readiness": t.readiness,
            "summary": t.summary,
            "repo": t._repo,  # namespace (empty in single-repo)
            "namespaced_id": _format_tid(t),  # full rendered ID
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
# Self-Test (Inline Smoke-Tests)
# ---------------------------------------------------------------------------

def _run_self_test() -> int:
    """inline Smoke-Tests fuer feature_milestones-Schema.

    Laeuft 5-7 Smoke-TCs gegen tests/fixtures/feature_milestones_minimal.yaml.
    Kein pytest-Setup im framework-Repo Pflicht. Returnt exit-code 0
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

    # Smoke-8: ID_REUSED_FROM_ARCHIVE — an active task id that also
    # exists in docs/tasks/archive/ is flagged ERROR. archived_ids passed
    # explicitly (no disk coupling). status=done -> terminal, so no unrelated
    # NO_MILESTONE / NO_EFFORT noise.
    reuse_issues = validate(
        {385: Task(id=385, title="t", status="done", milestone="")},
        {}, archived_ids={385})
    if any(i.check == "ID_REUSED_FROM_ARCHIVE" and i.severity == "ERROR"
           for i in reuse_issues):
        _ok("Smoke-8: active id colliding with archive/ -> ID_REUSED_FROM_ARCHIVE ERROR")
    else:
        _fail(f"Smoke-8: no ID_REUSED_FROM_ARCHIVE for 385: "
              f"{[(i.check, i.severity) for i in reuse_issues]}")
    clean_issues = validate(
        {386: Task(id=386, title="t", status="done", milestone="")},
        {}, archived_ids={385})
    if not any(i.check == "ID_REUSED_FROM_ARCHIVE" for i in clean_issues):
        _ok("Smoke-8: non-colliding id -> no ID_REUSED_FROM_ARCHIVE")
    else:
        _fail("Smoke-8: false ID_REUSED_FROM_ARCHIVE on non-colliding id")

    # active-milestone task-chain self-test suite (RED-first).
    # Synthetic in-memory fixture (Task/Milestone/GateCondition objects) — no
    # coupling to a consumer repo's live docs/tasks/ tree.
    chain_rc = _run_active_milestone_chain_self_test()
    if chain_rc != 0:
        failures.append("active-milestone-chain self-test suite")

    # task-schema conformance adversary suite (RED-first).
    schema_rc = _run_task_schema_self_test()
    if schema_rc != 0:
        failures.append("task-schema self-test suite")

    if failures:
        print(f"\n{len(failures)} self-test failure(s).")
        return 1
    print("\nAll smoke-tests passed.")
    return 0


def _run_active_milestone_chain_self_test() -> int:
    """adversary suite for compute_active_milestone_task_chain.

    Synthetic in-memory fixture (no plan.yaml / docs/tasks coupling):
    builds Task / Milestone / GateCondition objects directly and exercises
    the gate -> blocked_by walk plus its edge cases. Mirrors the inline
    object-construction style of Smoke-5. Returns 0 on all-PASS, 1 otherwise.
    """
    failures: list[str] = []

    def _ok(msg: str) -> None:
        print(f"  [PASS] {msg}")

    def _fail(msg: str) -> None:
        print(f"  [FAIL] {msg}")
        failures.append(msg)

    def _t(tid: int, status: str, blocked_by: list, *, effort: str = "M",
           milestone: str = "M3", repo: str = "") -> Task:
        return Task(id=tid, title=f"task {tid}", status=status,
                    milestone=milestone, blocked_by=list(blocked_by),
                    effort=effort, _repo=repo)

    def _ms(key: str, gate_task_ids, task_keys: list,
            requires: list | None = None) -> Milestone:
        """Build a Milestone WITHOUT a hand-set status.

        gate_task_ids: None | int | list[int] -> one or more `type: task` gates.
        Status is left "" so the caller MUST derive it via
        compute_milestone_status (the live-loader path). The old helper hand-set
        status="active" — a value the loader never emits for an all-`pending`
        gate chain.
        """
        if gate_task_ids is None:
            gate = []
        elif isinstance(gate_task_ids, int):
            gate = [GateCondition(type="task", id=gate_task_ids)]
        else:
            gate = [GateCondition(type="task", id=g) for g in gate_task_ids]
        m = Milestone(key=key, title=key, gate=gate,
                      requires=list(requires or []))
        m.tasks = list(task_keys)
        return m

    def _derive(tasks: dict, ms: dict) -> None:
        """Live-loader path: populate m.tasks + compute statuses the way the
        real pipeline does. NO hand-set status anywhere (kills the mask)."""
        assign_tasks_to_milestones(tasks, ms)
        compute_milestone_status(ms, tasks)

    print("\nplan_engine --self-test (Task 387 active-milestone task chain)")

    # TC-1 (frontier == target, LOADER-DRIVEN): M2 is done, so M3 is the live
    # frontier (ready) AND the target — the resolver returns M3 and surfaces its
    # gate chain 550(done)->551->552->553->429. Status is derived by
    # compute_milestone_status (emits "ready" for M3 — no member in_progress —
    # never "active"). TC-1b covers the far-target case where the frontier is an
    # EARLIER milestone than the target.
    tasks = {
        500: _t(500, "done", [], milestone="M2"),       # M2 done -> M3 is frontier
        550: _t(550, "done", [], milestone="M3"),
        551: _t(551, "pending", [550], milestone="M3"),
        552: _t(552, "pending", [551], milestone="M3"),
        553: _t(553, "pending", [552], milestone="M3"),
        429: _t(429, "pending", [553], milestone="M3"),
    }
    ms = {
        "M1": _ms("M1", None, [], requires=[]),
        "M2": _ms("M2", 500, [500], requires=["M1"]),
        "M3": _ms("M3", 429, [550, 551, 552, 553, 429], requires=["M2"]),
    }
    _derive(tasks, ms)
    # Precondition guard: loader emits "ready" for M3 (no member in_progress),
    # never "active" — the frontier walk keys on != "done", not == "active".
    if ms["M3"].status == "active":
        _fail("TC-1 precondition: loader emitted M3=active "
              "(expected ready) — fixture not loader-shaped")
    resolved = _resolve_active_milestone(ms, "M3")
    # take the full ActiveChain (the single-call result the renderer
    # consumes). the result's own `.milestone` must equal the milestone
    # the independent resolver returns — proving the public fn resolves the SAME
    # milestone the header will label with, so the renderer can reuse `.milestone`
    # without a second resolve.
    result = compute_active_milestone_task_chain(tasks, ms, "M3")
    chain = result.chain
    if resolved is not None and resolved.key == "M3" \
            and result.milestone is not None and result.milestone.key == "M3" \
            and chain == [550, 551, 552, 553, 429]:
        _ok(f"TC-1: loader-driven AC-1 tree resolves to gating M3 "
            f"(status={ms['M3'].status!r}), chain 550..429 roots-first; "
            f"single-call .milestone == resolved (C-006 single-resolve)")
    else:
        _fail(f"TC-1: resolved={resolved.key if resolved else None!r} "
              f"result.milestone={result.milestone.key if result.milestone else None!r} "
              f"chain={chain!r} (M3 status={ms['M3'].status!r}) "
              f"expected M3 + [550,551,552,553,429]")

    # TC-2 (honest effort): effort summed over the real task chain
    # (all int items carry effort_weight) — never a zero placeholder.
    effort = sum(tasks[k].effort_weight for k in chain)
    if effort == 5 * EFFORT_WEIGHTS["M"]:
        _ok(f"TC-2: chain effort summed over real tasks ({effort})")
    else:
        _fail(f"TC-2: effort={effort} expected {5 * EFFORT_WEIGHTS['M']}")

    # TC-3 (boot parity): fmt_boot renders the chain block; fmt_critical_path
    # renders the same chain. cp is the milestone spine (unchanged contract).
    spine = ["M3"]
    boot_out = fmt_boot(tasks, ms, "M3", "", "", spine, {}, [], [])
    cp_out = fmt_critical_path(tasks, spine, "M3", ms)
    if "[429]" in boot_out and "[550]" in boot_out and "[429]" in cp_out:
        _ok("TC-3: --boot and --critical-path both surface the task chain")
    else:
        _fail("TC-3: chain not surfaced in fmt_boot/fmt_critical_path output")

    # TC-3b: the milestone-key spine must NOT render a zero-valued
    # effort line (a structural 0 reads as a real metric). The honest per-chain
    # effort line still appears.
    if "Total effort-weighted length: 0" not in cp_out \
            and "Effort-weighted length: 0" not in boot_out \
            and "Chain effort-weighted length:" in cp_out:
        _ok("TC-3b: no misleading zero spine-effort line; honest chain metric present")
    else:
        _fail(f"TC-3b: misleading zero effort line rendered for a string spine\n"
              f"cp_out={cp_out!r}")

    # TC-1b (frontier-resolution, far-target case — pins the NEW semantics):
    # the TARGET is M3 but an EARLIER milestone on its spine is still open (M2
    # has a pending gate task), so the active milestone is the frontier M2 — the
    # earliest non-done milestone that must close next — NOT the target M3. This
    # is the user-facing scenario (target = far north-star, work at an earlier
    # milestone) the frontier semantics exist to deliver; the old target-preferring
    # resolver returned M3 here.
    far_tasks = {
        500: _t(500, "pending", [], milestone="M2"),    # M2 open -> M2 is frontier
        429: _t(429, "pending", [], milestone="M3"),
    }
    far_ms = {
        "M1": _ms("M1", None, [], requires=[]),
        "M2": _ms("M2", 500, [500], requires=["M1"]),
        "M3": _ms("M3", 429, [429], requires=["M2"]),
    }
    _derive(far_tasks, far_ms)
    far_resolved = _resolve_active_milestone(far_ms, "M3")
    far_result = compute_active_milestone_task_chain(far_tasks, far_ms, "M3")
    if far_resolved is not None and far_resolved.key == "M2" \
            and far_result.milestone is not None and far_result.milestone.key == "M2" \
            and far_result.chain == [500]:
        _ok("TC-1b: far target M3 with open earlier M2 resolves to frontier M2, chain [500]")
    else:
        _fail(f"TC-1b: resolved={far_resolved.key if far_resolved else None!r} "
              f"result.milestone={far_result.milestone.key if far_result.milestone else None!r} "
              f"chain={far_result.chain!r} (M2={far_ms['M2'].status!r} M3={far_ms['M3'].status!r}) "
              f"expected M2 + [500]")

    # TC-4 (cycle-guard, LOADER-DRIVEN): a real blocked_by back-edge
    # 553 -> 552 -> 553 must break + WARN. Status derived (no hand-set active).
    cyc = {
        429: _t(429, "pending", [553]),
        553: _t(553, "pending", [552]),
        552: _t(552, "pending", [553]),
    }
    cyc_ms = {"M3": _ms("M3", 429, [429, 553, 552], requires=[])}
    _derive(cyc, cyc_ms)
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        cyc_chain = compute_active_milestone_task_chain(cyc, cyc_ms, "M3").chain
    cyc_warn = [w for w in caught if "CYCLE" in str(w.message)]
    if 429 in cyc_chain and len(cyc_chain) == len(set(cyc_chain)) and cyc_warn:
        _ok("TC-4: real cycle in blocked_by breaks the walk + WARN, no loop")
    else:
        _fail(f"TC-4: chain={cyc_chain!r} warns={[str(w.message) for w in cyc_warn]}")

    # TC-5 (missing gate task): gate id points to a non-existent task ->
    # empty chain (degrade to spine-only), no crash.
    miss_tasks = {550: _t(550, "done", [])}
    miss_ms = {"M3": _ms("M3", 999, [550], requires=[])}
    _derive(miss_tasks, miss_ms)
    miss_chain = compute_active_milestone_task_chain(miss_tasks, miss_ms, "M3").chain
    if miss_chain == []:
        _ok("TC-5: missing gate task -> empty chain (spine-only degrade)")
    else:
        _fail(f"TC-5: chain={miss_chain!r} expected []")

    # TC-6 (empty blocked_by): gate task resolves but has no blocked_by ->
    # the gate task alone.
    solo = {429: _t(429, "pending", [])}
    solo_ms = {"M3": _ms("M3", 429, [429], requires=[])}
    _derive(solo, solo_ms)
    solo_chain = compute_active_milestone_task_chain(solo, solo_ms, "M3").chain
    if solo_chain == [429]:
        _ok("TC-6: empty blocked_by -> gate task alone")
    else:
        _fail(f"TC-6: chain={solo_chain!r} expected [429]")

    # TC-7 (no active milestone): the only milestone is done (no gating
    # frontier) -> empty chain, no crash (renderers fall back to spine-only).
    done_only = {"M0": _ms("M0", None, [], requires=[])}
    _derive({}, done_only)
    none_chain = compute_active_milestone_task_chain({}, done_only, "M0").chain
    if none_chain == [] and done_only["M0"].status == "done":
        _ok("TC-7: no gating milestone (M0 done) -> empty chain (no crash)")
    else:
        _fail(f"TC-7: chain={none_chain!r} (M0={done_only['M0'].status!r}) expected []")

    # TC-8 (done-target degrade, LOADER-DRIVEN — grounded on the status DAG):
    # a milestone is loader-"done" only when its gate passes AND all tasks are
    # terminal AND all `requires` are done. So a done TARGET implies every
    # predecessor on its requires-spine is also done — there is no open frontier
    # among its deps. The resolver must therefore return None (-> spine-only
    # degrade), never a stale or arbitrary milestone. This pins the actual
    # loader invariant rather than the old hand-set status="ready" fixture.
    fb_tasks = {
        700: _t(700, "done", [], milestone="M1"),
        701: _t(701, "done", [700], milestone="M2"),
    }
    fb_ms = {
        "M1": _ms("M1", 700, [700], requires=[]),
        "M2": _ms("M2", 701, [701], requires=["M1"]),
    }
    _derive(fb_tasks, fb_ms)
    fb_resolved = _resolve_active_milestone(fb_ms, "M2")  # target M2 is loader-done
    fb_chain = compute_active_milestone_task_chain(fb_tasks, fb_ms, "M2").chain
    if fb_ms["M2"].status == "done" and fb_resolved is None and fb_chain == []:
        _ok("TC-8: loader-done target (all spine deps done) -> None, spine-only degrade")
    else:
        _fail(f"TC-8: M2={fb_ms['M2'].status!r} "
              f"resolved={fb_resolved.key if fb_resolved else None!r} "
              f"chain={fb_chain!r} expected done+None+[]")

    # TC-9 (aggregate-mode keying): tasks keyed by '<repo>#<id>',
    # blocked_by rewritten to the same key form; gate id is still a raw int.
    # The walk must resolve via m.tasks keys, not by assuming int keys.
    agg = {
        "repoA#553": _t(553, "pending", ["repoA#552"], repo="repoA"),
        "repoA#552": _t(552, "done", [], repo="repoA"),
        "repoA#429": _t(429, "in_progress", ["repoA#553"], repo="repoA"),
    }
    agg_ms = {"repoA:M3": _ms("repoA:M3", 429,
                              ["repoA#552", "repoA#553", "repoA#429"], requires=[])}
    # compute_milestone_status' annotation is dict[int, Task]; in
    # aggregate mode the keys are '<repo>#<id>' strings at runtime, which the
    # function handles. Narrow ignore — the out-of-scope signature is unchanged.
    compute_milestone_status(agg_ms, agg)  # type: ignore[arg-type]
    agg_chain = compute_active_milestone_task_chain(agg, agg_ms, "repoA:M3").chain
    if agg_chain == ["repoA#552", "repoA#553", "repoA#429"]:
        _ok("TC-9: aggregate-mode str keys resolve gate + walk correctly")
    else:
        _fail(f"TC-9: chain={agg_chain!r} expected repoA#552->553->429")

    # TC-10 (stop at done root): the chain's first element is the done
    # root 550; the walk includes it but does not over-walk past its empty deps.
    if chain[0] == 550 and tasks[550].is_done:
        _ok("TC-10: walk terminates at done root (550) — bounded, no over-walk")
    else:
        _fail(f"TC-10: chain[0]={chain[0]!r} done={tasks[550].is_done}")

    # TC-11 (DIAMOND — RED-confirms the false-cycle + mis-order): a shared
    # blocker. gate 429 blocked_by [2,3]; 2,3 both blocked_by 1 (root). Acyclic.
    # MUST order roots-first (1 before 2 and 3, gate 429 last) and MUST NOT warn.
    diamond = {
        1: _t(1, "done", []),
        2: _t(2, "pending", [1]),
        3: _t(3, "pending", [1]),
        429: _t(429, "in_progress", [2, 3]),
    }
    dia_ms = {"M3": _ms("M3", 429, [1, 2, 3, 429], requires=[])}
    _derive(diamond, dia_ms)
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        dia_chain = compute_active_milestone_task_chain(diamond, dia_ms, "M3").chain
    dia_warn = [w for w in caught if "CYCLE" in str(w.message)]
    pos = {k: i for i, k in enumerate(dia_chain)}
    ordered_ok = (
        set(dia_chain) == {1, 2, 3, 429}
        and pos[1] < pos[2] and pos[1] < pos[3]
        and pos[2] < pos[429] and pos[3] < pos[429]
    )
    if ordered_ok and not dia_warn:
        _ok(f"TC-11: diamond ordered roots-first {dia_chain} + NO false cycle warn")
    else:
        _fail(f"TC-11: diamond chain={dia_chain!r} warns="
              f"{[str(w.message) for w in dia_warn]} (expected roots-first, no warn)")

    # TC-12 (MULTI-GATE — RED-confirms silent under-report): milestone M3
    # has TWO type:task gates 429 and 600, both fanning off a shared root 500.
    # BOTH gate chains must surface — not just the first.
    mg = {
        500: _t(500, "done", []),
        429: _t(429, "in_progress", [500]),
        600: _t(600, "pending", [500]),
    }
    mg_ms = {"M3": _ms("M3", [429, 600], [500, 429, 600], requires=[])}
    _derive(mg, mg_ms)
    mg_chain = compute_active_milestone_task_chain(mg, mg_ms, "M3").chain
    if set(mg_chain) == {500, 429, 600} and mg_chain.index(500) == 0:
        _ok(f"TC-12: multi-gate surfaces ALL gate chains {mg_chain} (no under-report)")
    else:
        _fail(f"TC-12: multi-gate chain={mg_chain!r} expected all of "
              f"{{500,429,600}} (gate 600 must not be dropped)")

    # TC-13 (invalid/blank effort must not silently inflate): gate task
    # has effort="" (non-{S,M,L,XL}). The rendered chain-effort line MUST mark it
    # estimated (~N + "effort-unset"), not present a clean exact number.
    be = {900: _t(900, "in_progress", [], effort="")}
    be_ms = {"M3": _ms("M3", 900, [900], requires=[])}
    _derive(be, be_ms)
    be_lines = _fmt_active_chain_block(be, be_ms, "M3")
    be_blob = "\n".join(be_lines)
    if "effort-unset" in be_blob and "~" in be_blob:
        _ok("TC-13: blank-effort task marks chain-effort estimated (no silent fabricated number)")
    else:
        _fail(f"TC-13: blank-effort not marked estimated\nlines={be_lines!r}")

    # TC-14 (RENDER-PATH parity for the guarantees):
    # TC-11/TC-12 prove diamond-order + multi-gate on compute_*; this drives the
    # ACTUAL shipped renderer (_fmt_active_chain_block, the path --critical-path/
    # --boot execute) on those two shapes and asserts the ORDERING (not mere
    # presence) shows up in the rendered text. After the collapse the renderer
    # routes through compute_active_milestone_task_chain, so a regression in the
    # tested fn now also breaks this — the proof is on what ships.
    #   Diamond: root 1 must render before both 2 and 3, gate 429 after both.
    dia_render = "\n".join(_fmt_active_chain_block(diamond, dia_ms, "M3"))
    chain_line = next((ln for ln in dia_render.splitlines() if " -> " in ln), "")
    p1, p2, p3, p429 = (chain_line.find(f"[{n}]") for n in (1, 2, 3, 429))
    diamond_render_ok = (
        "ACTIVE-MILESTONE TASK PATH (M3)" in dia_render
        and -1 not in (p1, p2, p3, p429)
        and p1 < p2 and p1 < p3 and p2 < p429 and p3 < p429
    )
    #   Multi-gate: BOTH gate chains (429 AND 600) must appear in the render,
    #   shared root 500 first — gate 600 must not be silently dropped.
    mg_render = "\n".join(_fmt_active_chain_block(mg, mg_ms, "M3"))
    mg_line = next((ln for ln in mg_render.splitlines() if " -> " in ln), "")
    m500, m429, m600 = (mg_line.find(f"[{n}]") for n in (500, 429, 600))
    multigate_render_ok = (
        -1 not in (m500, m429, m600) and m500 < m429 and m500 < m600
    )
    if diamond_render_ok and multigate_render_ok:
        _ok("TC-14: shipped renderer (_fmt_active_chain_block) preserves "
            "diamond roots-first + multi-gate fan-out (production==tested path)")
    else:
        _fail(f"TC-14: render-path order mismatch\n"
              f"diamond_line={chain_line!r} ok={diamond_render_ok}\n"
              f"multigate_line={mg_line!r} ok={multigate_render_ok}")

    if failures:
        print(f"\n{len(failures)} active-milestone-chain failure(s).")
        return 1
    return 0


def _run_task_schema_self_test() -> int:
    """adversary suite for the schema-driven task-conformance pass.

    Fixture-harness pattern (no pytest in framework repo).
    Exercises TC-1..TC-12 against
    tests/fixtures/task_schema/. Returns 0 on all-PASS, 1 otherwise.
    """
    base = FRAMEWORK_ROOT / "tests" / "fixtures" / "task_schema"
    conformant = base / "conformant"
    consumer = base / "consumer"
    single = base / "single"
    schema_path = FRAMEWORK_ROOT / "framework" / "task-schema.yaml"

    failures: list[str] = []

    def _ok(msg: str) -> None:
        print(f"  [PASS] {msg}")

    def _fail(msg: str) -> None:
        print(f"  [FAIL] {msg}")
        failures.append(msg)

    def _by_task(issues: list[ValidationIssue], tid: int) -> list[ValidationIssue]:
        return [i for i in issues if i.task_id == tid]

    def _checks(issues: list[ValidationIssue], tid: int) -> set[str]:
        return {i.check for i in _by_task(issues, tid)}

    print("\nplan_engine --self-test (Task 327 task-schema conformance)")

    # Conformant tree (TC-5 + TC-7): zero issues, aux files never tasks.
    conf_issues = validate_task_schema_conformance(
        project_root=conformant, schema_path=schema_path)
    if conf_issues:
        _fail(f"TC-5: conformant tree produced issues: "
              f"{[(i.check, i.task_id, i.detail) for i in conf_issues]}")
    else:
        _ok("TC-5: conformant tree -> 0 schema issues")
    aux_ids = {i.task_id for i in conf_issues}
    if 327 in aux_ids or 999 in aux_ids:
        _fail("TC-7: aux file (327-gates/-delegation/999-notes) raised a task issue")
    else:
        _ok("TC-7: aux NNN-<suffix> files classified non-task (0 task issues)")

    # Consumer adversary tree (TC-1..4, TC-6, TC-10, TC-11).
    cons = validate_task_schema_conformance(
        project_root=consumer, schema_path=schema_path)

    # TC-1: wrong field name 'prioritee' -> UNKNOWN_FIELD WARN + missing-priority WARN
    c200 = _checks(cons, 200)
    sev200 = {i.check: i.severity for i in _by_task(cons, 200)}
    if {"SCHEMA_UNKNOWN_FIELD", "SCHEMA_MISSING_REQUIRED"} <= c200 \
            and sev200.get("SCHEMA_UNKNOWN_FIELD") == "WARN" \
            and sev200.get("SCHEMA_MISSING_REQUIRED") == "WARN":
        _ok("TC-1: 'prioritee' -> UNKNOWN_FIELD WARN + MISSING_REQUIRED(priority) WARN")
    else:
        _fail(f"TC-1: task 200 checks={sev200}")

    # TC-2: missing priority on open task -> MISSING_REQUIRED WARN (calibration proof)
    i201 = _by_task(cons, 201)
    mr201 = [i for i in i201 if i.check == "SCHEMA_MISSING_REQUIRED"]
    if mr201 and all(i.severity == "WARN" for i in mr201) \
            and any("priority" in i.detail for i in mr201):
        _ok("TC-2: missing priority open -> MISSING_REQUIRED WARN (warn_first calibration)")
    else:
        _fail(f"TC-2: task 201 missing-required={[(i.severity, i.detail) for i in mr201]}")

    # TC-3: effort 'S-M' -> VOCAB WARN
    v202 = [i for i in _by_task(cons, 202) if i.check == "SCHEMA_VOCAB"]
    if v202 and all(i.severity == "WARN" for i in v202) \
            and any("effort" in i.detail for i in v202):
        _ok("TC-3: effort 'S-M' -> SCHEMA_VOCAB WARN")
    else:
        _fail(f"TC-3: task 202 vocab={[(i.severity, i.detail) for i in v202]}")

    # TC-4: priority 'mid' written -> VOCAB WARN (write-strict, alias not allowed on write)
    v203 = [i for i in _by_task(cons, 203) if i.check == "SCHEMA_VOCAB"]
    if v203 and all(i.severity == "WARN" for i in v203) \
            and any("priority" in i.detail for i in v203):
        _ok("TC-4: priority 'mid' written -> SCHEMA_VOCAB WARN (write-strict)")
    else:
        _fail(f"TC-4: task 203 vocab={[(i.severity, i.detail) for i in v203]}")

    # TC-6: cross-repo — issues located on the correct consumer task ids.
    cons_ids = {i.task_id for i in cons}
    if {200, 201, 202, 203} <= cons_ids and 206 not in cons_ids:
        _ok("TC-6: cross-repo consumer fixture -> issues located on offenders only")
    else:
        _fail(f"TC-6: consumer issue ids={sorted(x for x in cons_ids if x is not None)}")

    # TC-10: status 'deferred' (unknown) -> tolerant-read-as-open, NOT terminal.
    # Proof: open => required_when_open enforced => missing priority WARN raised.
    mr204 = [i for i in _by_task(cons, 204)
             if i.check == "SCHEMA_MISSING_REQUIRED" and "priority" in i.detail]
    if mr204:
        _ok("TC-10: status 'deferred' -> classified open (missing-priority raised)")
    else:
        _fail("TC-10: status 'deferred' was NOT treated as open")

    # TC-11: id:999 in 205.yaml -> SCHEMA_ID_MISMATCH ERROR (calibration-independent).
    idm = [i for i in _by_task(cons, 205) if i.check == "SCHEMA_ID_MISMATCH"]
    if not idm:
        # task_id may resolve to basename int (205) or yaml id (999) — check both
        idm = [i for i in cons if i.check == "SCHEMA_ID_MISMATCH"
               and i.task_id in (205, 999)]
    if idm and all(i.severity == "ERROR" for i in idm):
        _ok("TC-11: id:999 in 205.yaml -> SCHEMA_ID_MISMATCH ERROR")
    else:
        _fail(f"TC-11: id-mismatch issues={[(i.task_id, i.severity) for i in idm]}")

    # TC-8: single-id mode — --validate <id> reports only that task, exit 0/1.
    s327 = validate_task_schema_conformance(
        project_root=single, single_id=327, schema_path=schema_path)
    s327_ids = {i.task_id for i in s327}
    if s327_ids <= {327} and 328 not in s327_ids:
        _ok("TC-8: --validate 327 single-id -> only task 327, no 328 bleed")
    else:
        _fail(f"TC-8: single-id 327 reported ids={sorted(x for x in s327_ids if x is not None)}")
    # exit-code contract: structural ERROR on single id -> non-clean
    s329 = validate_task_schema_conformance(
        project_root=single, single_id=329, schema_path=schema_path)
    has_err_329 = any(i.severity == "ERROR" for i in s329)
    if has_err_329:
        _ok("TC-8: single-id structural ERROR -> non-clean (exit 1 path)")
    else:
        _fail(f"TC-8: single-id 329 produced no ERROR: {[(i.check, i.severity) for i in s329]}")
    # vocab-only single id (327, priority mid) is WARN -> clean exit-0 path
    if not any(i.severity == "ERROR" for i in s327):
        _ok("TC-8: single-id vocab-only -> WARN, clean (exit 0 path, warn_first)")
    else:
        _fail(f"TC-8: single-id 327 unexpectedly ERROR: {[(i.check, i.severity) for i in s327]}")

    # TC-12: schema file missing -> SCHEMA_FILE ERROR + escalation, no silent pass.
    missing = FRAMEWORK_ROOT / "tests" / "fixtures" / "task_schema" / "__no_such_schema__.yaml"
    tc12 = validate_task_schema_conformance(
        project_root=conformant, schema_path=missing)
    sf = [i for i in tc12 if i.check == "SCHEMA_FILE"]
    if sf and all(i.severity == "ERROR" for i in sf) \
            and any("ESCALATE" in i.detail for i in sf):
        _ok("TC-12: schema file missing -> SCHEMA_FILE ERROR + ESCALATE marker")
    else:
        _fail(f"TC-12: missing-schema issues={[(i.check, i.severity, i.detail) for i in sf]}")

    # -------------------------------------------------------------------
    # fix-pass RED-first cases.
    # Each was RED against pre-fix code and is GREEN after the
    # corresponding root-fix.
    # -------------------------------------------------------------------
    malformed = base / "malformed"

    def _schema_file_escalate(issues: list[ValidationIssue]) -> bool:
        sfx = [i for i in issues if i.check == "SCHEMA_FILE"]
        return (bool(sfx)
                and all(i.severity == "ERROR" for i in sfx)
                and any("ESCALATE" in i.detail for i in sfx))

    # `validator` is a scalar string (truthy non-dict). The
    # top-level doc is a valid mapping, so this is NOT the missing-file
    # path — it is the partial-corruption path that pre-fix crashed with
    # an uncaught AttributeError. Expect SCHEMA_FILE ERROR + ESCALATE.
    try:
        ca1a = validate_task_schema_conformance(
            project_root=conformant,
            schema_path=malformed / "schema-validator-scalar.yaml")
        if _schema_file_escalate(ca1a):
            _ok("F-CA-001a: validator-as-scalar -> SCHEMA_FILE ERROR + ESCALATE (no crash)")
        else:
            _fail(f"F-CA-001a: validator-scalar issues="
                  f"{[(i.check, i.severity) for i in ca1a]}")
    except Exception as exc:  # noqa: BLE001 — the bug IS an uncaught exc
        _fail(f"F-CA-001a: validator-as-scalar CRASHED ({exc!r}) — not fail-safe")

    # same class on `filename` (the second live instance).
    try:
        ca1b = validate_task_schema_conformance(
            project_root=conformant,
            schema_path=malformed / "schema-filename-scalar.yaml")
        if _schema_file_escalate(ca1b):
            _ok("F-CA-001b: filename-as-scalar -> SCHEMA_FILE ERROR + ESCALATE (no crash)")
        else:
            _fail(f"F-CA-001b: filename-scalar issues="
                  f"{[(i.check, i.severity) for i in ca1b]}")
    except Exception as exc:  # noqa: BLE001
        _fail(f"F-CA-001b: filename-as-scalar CRASHED ({exc!r}) — not fail-safe")

    # the root cause (no escalate on a malformed
    # trusted-config nested key) generalized to EVERY sibling
    # nested-structure key the SAME function reads. A present-but-wrong-
    # type key must fail-safe to SCHEMA_FILE ERROR + ESCALATE, never a
    # silent degrade to set()/[] (which reclassifies every terminal task
    # open / drops the real required-set with NO diagnostic). RED pre-fix
    # (silent WARN drift, no ESCALATE), GREEN post-fix.
    for ca7_fix, ca7_label in (
        ("schema-terminal-scalar.yaml",
         "terminal_status='done' (scalar) -> not silent set() drift"),
        ("schema-required-always-scalar.yaml",
         "required_always='id' (scalar) -> not silent list('id') drift"),
    ):
        try:
            ca7 = validate_task_schema_conformance(
                project_root=conformant,
                schema_path=malformed / ca7_fix)
            if _schema_file_escalate(ca7):
                _ok(f"F-CA-007: {ca7_label} -> SCHEMA_FILE ERROR + ESCALATE")
            else:
                _fail(f"F-CA-007: {ca7_fix} issues="
                      f"{[(i.check, i.severity) for i in ca7]}")
        except Exception as exc:  # noqa: BLE001
            _fail(f"F-CA-007: {ca7_fix} CRASHED ({exc!r}) — not fail-safe")

    # -------------------------------------------------------------------
    # STRUCTURAL trust-boundary. The per-site-guard
    # strategy failed convergence 3x (same class
    # one nesting level deeper each pass). The fix is ONE declarative
    # trust boundary: _validate_schema_structure walks the DATA constant
    # _TASK_SCHEMA_SHAPE. Coverage scales with the descriptor by
    # construction: one corrupt-node fixture PER node.
    # -------------------------------------------------------------------

    # THE single non-negotiable test (a reviewer checks this FIRST):
    # the REAL framework/task-schema.yaml must itself PASS the structural
    # walker. If the locked schema and the descriptor ever disagree this
    # fails loudly (closes the descriptor-DRIFT failure mode). NOTE: this
    # does NOT close (conditional-requiredness — a sibling-gated
    # key absent); that is an owner-accepted residual, not covered here.
    real_schema = _load_task_schema(schema_path)
    if real_schema is not None \
            and _validate_schema_structure(real_schema) is None:
        _ok("327-anchor: real framework/task-schema.yaml PASSES "
            "_validate_schema_structure (positive drift anchor)")
    else:
        _fail("327-anchor: real framework/task-schema.yaml does NOT pass "
              f"_validate_schema_structure: "
              f"{_validate_schema_structure(real_schema) if real_schema else 'unloadable'}")

    # Version pin: the loaded schema_version MUST equal the version the
    # descriptor was authored against, so an intentional schema evolution
    # FORCES a conscious descriptor revisit (not silent under-validation).
    if real_schema is not None \
            and real_schema.get("schema_version") == _TASK_SCHEMA_VERSION:
        _ok(f"327-pin: schema_version pin matches descriptor "
            f"(_TASK_SCHEMA_VERSION={_TASK_SCHEMA_VERSION})")
    else:
        _fail(f"327-pin: schema_version "
              f"{real_schema.get('schema_version') if real_schema else None} "
              f"!= _TASK_SCHEMA_VERSION {_TASK_SCHEMA_VERSION}")

    # One corrupt-node fixture PER node in _TASK_SCHEMA_SHAPE: each
    # corrupts exactly one descriptor node and MUST fail-safe to
    # SCHEMA_FILE ERROR + ESCALATE (no crash, no silent degrade). This
    # makes checker coverage proportional to the spec by construction —
    # adding a schema node = adding a data node = adding a fixture row.
    # Includes the two repros explicitly: schema-task-basename-
    # int (re.compile TypeError class) and schema-enum-values-scalar
    # (silent vocab-loss class). schema-version-mismatch exercises the
    # §4 version pin (well-formed, version != descriptor -> ESCALATE).
    for fx, node_label in (
        ("schema-version-nonint.yaml", "schema_version (non-int)"),
        ("schema-version-mismatch.yaml",
         "schema_version pin (version != descriptor)"),
        ("schema-task-basename-int.yaml",
         "filename.task_basename (F-CA-008: re.compile crash class)"),
        ("schema-id-matches-basename-str.yaml",
         "filename.id_matches_basename (non-bool)"),
        ("schema-required-when-open-scalar.yaml",
         "required_when_open (non-list)"),
        ("schema-required-when-terminal-scalar.yaml",
         "required_when_terminal (non-list)"),
        ("schema-required-always-elem-int.yaml",
         "required_always[] element (non-str)"),
        ("schema-fields-scalar.yaml", "fields (non-mapping)"),
        ("schema-field-def-scalar.yaml",
         "fields.<name> field-def (non-mapping)"),
        ("schema-field-type-int.yaml",
         "fields.<name>.type (non-str)"),
        ("schema-enum-values-scalar.yaml",
         "fields.<name>.values (F-CA-008: silent vocab-loss class)"),
        ("schema-read-aliases-scalar.yaml",
         "fields.<name>.read_aliases (non-mapping)"),
    ):
        try:
            r = validate_task_schema_conformance(
                project_root=conformant, schema_path=malformed / fx)
            if _schema_file_escalate(r):
                _ok(f"327-node: {node_label} -> SCHEMA_FILE ERROR + ESCALATE")
            else:
                _fail(f"327-node: {fx} ({node_label}) NOT fail-safe: "
                      f"{[(i.check, i.severity) for i in r]}")
        except Exception as exc:  # noqa: BLE001
            _fail(f"327-node: {fx} ({node_label}) CRASHED ({exc!r}) "
                  "— not fail-safe")

    # strict_after_backfill is the YAML *string* "false".
    # bool("false") is True -> pre-fix this silently inverted calibration
    # to strict. Locked decision: non-bool -> SCHEMA_FILE ERROR + ESCALATE
    # (NOT silent strict, NOT WARN-coerced, NOT bool()-coerced).
    try:
        ca2 = validate_task_schema_conformance(
            project_root=conformant,
            schema_path=malformed / "schema-strict-string.yaml")
        if _schema_file_escalate(ca2):
            _ok("F-CA-002: strict_after_backfill='false' (str) -> SCHEMA_FILE ERROR + ESCALATE")
        else:
            _fail(f"F-CA-002: non-bool calibration issues="
                  f"{[(i.check, i.severity, i.detail) for i in ca2]}")
    except Exception as exc:  # noqa: BLE001
        _fail(f"F-CA-002: non-bool calibration CRASHED ({exc!r})")

    # `--validate -1` / `--validate 0` at the argv/dispatch
    # boundary -> exit 2 (same path as a non-int value), NOT CLEAN exit 0.
    import subprocess
    engine = str(FRAMEWORK_ROOT / "scripts" / "plan_engine.py")
    for bad_id in ("-1", "0"):
        proc = subprocess.run(
            [sys.executable, engine, "--validate", bad_id],
            capture_output=True, text=True)
        if proc.returncode == 2 and "CLEAN" not in proc.stdout:
            _ok(f"F-CA-003a: --validate {bad_id} -> argv error exit 2 (not CLEAN)")
        else:
            _fail(f"F-CA-003a: --validate {bad_id} rc={proc.returncode} "
                  f"stdout={proc.stdout.strip()!r}")

    # (belt): single-id mode with a target that fails the name
    # grammar must NOT silently continue -> SCHEMA_FILE ERROR. Drive via
    # the function with a negative single_id (defence in depth below argv).
    ca3b = validate_task_schema_conformance(
        project_root=single, single_id=-1, schema_path=schema_path)
    if any(i.check == "SCHEMA_FILE" and i.severity == "ERROR" for i in ca3b):
        _ok("F-CA-003b: single-id grammar-miss -> SCHEMA_FILE ERROR (no silent continue)")
    else:
        _fail(f"F-CA-003b: single_id=-1 issues="
              f"{[(i.check, i.severity) for i in ca3b]}")

    # archived single-id. id resolves ONLY in
    # docs/tasks/archive/<id>.yaml -> clean terminal result, NOT a false
    # SCHEMA_FILE 'task file not found' ERROR.
    sa_root = base / "single_archived"
    ca4 = validate_task_schema_conformance(
        project_root=sa_root, single_id=299, schema_path=schema_path)
    if not any(i.severity == "ERROR" for i in ca4):
        _ok("F-CA-004: archived single-id 299 -> clean terminal (no false ERROR)")
    else:
        _fail(f"F-CA-004: archived id 299 issues="
              f"{[(i.check, i.severity, i.detail) for i in ca4]}")

    # zero-pad duplicate-logical-id collision. `327.yaml` and
    # `0327.yaml` both -> int(basename)=327. Chosen behaviour: detect as
    # a duplicate-id ERROR (SCHEMA_ID_MISMATCH, calibration-independent),
    # never silently validate both as task 327.
    dup_root = base / "dup_id"
    ca5e = validate_task_schema_conformance(
        project_root=dup_root, schema_path=schema_path)
    dup = [i for i in ca5e
           if i.check == "SCHEMA_ID_MISMATCH" and i.severity == "ERROR"
           and "duplicate" in i.detail.lower()]
    if dup:
        _ok("F-CA-005e: 327.yaml + 0327.yaml -> duplicate-id SCHEMA_ID_MISMATCH ERROR")
    else:
        _fail(f"F-CA-005e: dup-id issues="
              f"{[(i.check, i.severity, i.detail) for i in ca5e]}")

    # the dead full-tree not-exists guard must be gone.
    # Source-level assertion: the unreachable `if <none-check> ... :`
    # statement followed by `continue` no longer exists as code. The
    # needle is assembled at runtime so this comment cannot self-match.
    src = (FRAMEWORK_ROOT / "scripts" / "plan_engine.py").read_text(
        encoding="utf-8")
    dead_stmt = ("if single_id is None and not yaml_path."
                 + "exists():\n            continue")
    if dead_stmt not in src:
        _ok("F-CA-006: dead full-tree not-exists branch removed")
    else:
        _fail("F-CA-006: dead full-tree not-exists branch still present")

    if failures:
        print(f"\n{len(failures)} task-schema self-test failure(s).")
        return 1
    print("\nAll task-schema self-tests passed.")
    return 0


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

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
    group.add_argument("--self-test", action="store_true",
                       help="inline smoke-tests fuer "
                            "feature_milestones-Schema-Erweiterung")
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

    # explicit --project-root override. Rebinds the three
    # project-scoped module globals so that load_tasks/load_plan + all
    # GateCondition.check calls resolve against the new root.
    if args.project_root:
        global PROJECT_ROOT, TASKS_DIR, PLAN_PATH, REPO_ROOT
        PROJECT_ROOT = Path(args.project_root).resolve()
        TASKS_DIR = PROJECT_ROOT / "docs" / "tasks"
        PLAN_PATH = PROJECT_ROOT / "docs" / "plan.yaml"
        REPO_ROOT = PROJECT_ROOT  # keep back-compat alias in sync

    # --self-test entry-point.
    if getattr(args, "self_test", False):
        rc = _run_self_test()
        sys.exit(rc)

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
        archived_ids = load_archived_task_ids(PROJECT_ROOT)

    # Pass plan_data fuer 4-stufigen Critical-Path-Lookup.
    plan_data_for_cp: dict = {}
    if not args.aggregate and PLAN_PATH.exists():
        try:
            plan_data_for_cp = yaml.safe_load(PLAN_PATH.read_text(encoding="utf-8")) or {}
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

    # Output
    if args.boot:
        print(fmt_boot(tasks, milestones, target, north_star, op_intent,
                        critical_path, blocking_scores, next_actions, issues))
    elif args.status:
        print(fmt_status(tasks, milestones))
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
                                  phases=phases_for_json))
    elif args.validate:
        output, clean = fmt_validate(issues)
        print(output)
        sys.exit(0 if clean else 1)
    elif args.spec_pipeline:
        print(fmt_spec_pipeline(tasks))


if __name__ == "__main__":
    main()
