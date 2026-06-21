"""_plan_engine.loading — task/plan loading, gate model, multi-repo aggregation.

Owns the project-scoped path globals (PROJECT_ROOT / TASKS_DIR / PLAN_PATH /
REPO_ROOT) as the single source of truth. Consumers MUST read them via
attribute access (``loading.PROJECT_ROOT``), never ``from .loading import
PROJECT_ROOT`` — the latter captures the value at import time and would not see
the late ``--project-root`` / dashboard rebind. ``GateCondition`` lives here
(not in the pure-data core leaf) because its ``.check()`` runs subprocess +
filesystem IO.

Split out of the former monolithic scripts/plan_engine.py.
"""

from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass, field
from glob import glob
from pathlib import Path

import yaml

from _plan_engine.core import (
    Milestone,
    Phase,
    PlanResult,
    Task,
    _emit_warn,
    _parse_external_entry,
)

# Project-scoped path globals — the rebind seam. PROJECT_ROOT is derived from
# BUDDY_PROJECT_ROOT / cwd at import; the CLI --project-root override and the
# generate-dashboard.py consumer rebind these four attributes on this module
# object, and every reader resolves them late via ``loading.<NAME>``.
PROJECT_ROOT = Path(os.environ.get("BUDDY_PROJECT_ROOT", Path.cwd())).resolve()

# Back-compat alias: older code-paths still reference REPO_ROOT. It mirrors
# PROJECT_ROOT (the "data" side) which is where task/plan/gate-scripts live.
REPO_ROOT = PROJECT_ROOT

TASKS_DIR = PROJECT_ROOT / "docs" / "tasks"
PLAN_PATH = PROJECT_ROOT / "docs" / "plan.yaml"


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
# Per-PROJECT_ROOT keyed; der Key ist das Modul-Global PROJECT_ROOT, das nur vom
# `--project-root` CLI-Override in main() (oder von einem Out-of-Process-Consumer
# via plan_engine.PROJECT_ROOT-Rebind — generate-dashboard.py macht das pro Repo)
# umgehaengt wird, daher kein manuelles Invalidate noetig.
_archived_ids_cache: dict[Path, set[int]] = {}


def _get_archived_ids_cached() -> set[int]:
    """Lazy + cached access to archived task IDs for current PROJECT_ROOT.

    Used by GateCondition.check (task-type) so that an archived gate-task
    (e.g., M0-cross-cutting gate id=417 after M0-Welle-Closeout) is treated
    as done. Without this, every Milestone whose gate-tasks become archived
    would misreport as ORPHAN.

    Cache invalidation: implicit per PROJECT_ROOT — the cache key is the
    module-global PROJECT_ROOT, rebound only by the `--project-root` CLI override
    in main() (or by an out-of-process consumer rebinding plan_engine.PROJECT_ROOT,
    as generate-dashboard.py does per repo). plan_engine's own --aggregate path
    does NOT rebind PROJECT_ROOT in-process.
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


# Module-level Cache fuer die VOLLEN archived Task-Objekte (single-repo
# dict[int, Task]). Used by (a) the render-time milestone done/total counters
# (fmt_boot / fmt_status / fmt_dashboard_json / compute_phase_progress) so a
# milestone whose terminal tasks were MOVED to docs/tasks/archive/ is still
# credited, and (b) the critical-path renderer (_render_cp_item) so an archived
# dep is labelled with its ACTUAL terminal status (done / superseded / wontfix /
# absorbed), not a hardcoded "done".
#
# Per-PROJECT_ROOT keyed. Invalidation is implicit: the key is the module-global
# PROJECT_ROOT, which is rebound only by the `--project-root` CLI override in
# main() (or by an out-of-process consumer rebinding plan_engine.PROJECT_ROOT —
# generate-dashboard.py does this per repo). plan_engine's OWN aggregate path
# (load_aggregated) never rebinds PROJECT_ROOT in-process, which is exactly why
# the milestone credit is a deterministic no-op under --aggregate (see
# _milestone_archived_credit). Single read of the archive per root.
_archived_tasks_cache: dict[Path, dict] = {}

# Sentinel for "no prior cache entry" — used by the self-test save/restore so a
# genuinely-absent key is distinguished from a cached empty dict.
_ARCH_MISS = object()


def _get_archived_tasks_cached() -> dict:
    """Lazy + cached full archived-Task map for current PROJECT_ROOT.

    Built from load_archived_tasks (non-recursive, mirrors load_archived_task_ids
    — NO recursive globbing added). Single-repo keyed by bare int task id. On any
    load failure -> empty dict (archive-awareness degrades to the pre-fix
    behaviour, never crashes the boot-critical render path).
    """
    if PROJECT_ROOT not in _archived_tasks_cache:
        try:
            _archived_tasks_cache[PROJECT_ROOT] = load_archived_tasks(PROJECT_ROOT)
        except (OSError, AttributeError):
            _archived_tasks_cache[PROJECT_ROOT] = {}
    return _archived_tasks_cache[PROJECT_ROOT]


def _archived_task_status(item: int) -> str | None:
    """ACTUAL terminal status of an archived task id, or None if not archived.

    The archive holds EVERY terminal status (done / superseded / wontfix /
    absorbed), so a label that hardcodes "done" is wrong (e.g. archive/161.yaml
    is wontfix). Returns the real status string for an accurate
    `(<status>, archived)` label; None means "not in the archive" -> the caller
    keeps its genuinely-unresolvable `(missing)` signal intact.
    """
    t = _get_archived_tasks_cached().get(item)
    if t is None:
        return None
    return getattr(t, "status", "") or ""


def _milestone_archived_credit(m, tasks: dict, *, aggregate: bool = False,
                               done_only: bool = False) -> int:
    """Extra done/total count for milestone `m` from archived tasks.

    Counts archived tasks belonging to `m` whose key is NOT already present in
    the loaded `tasks` dict. The not-in-`tasks` guard keeps the credit strictly
    ADDITIVE over what the existing counter already sees and prevents
    double-counting a task that is both loaded AND archived (the
    ID_REUSED_FROM_ARCHIVE collision case — already an ERROR, counted once here).

    Semantic-match to the calling surface (the pre-existing is_terminal-vs-is_done
    split is preserved, NOT unified):
      - done_only=False -> credit archived *terminal* tasks (the is_terminal
        surfaces: fmt_boot / fmt_status / fmt_dashboard_json).
      - done_only=True  -> credit archived *done* tasks only (compute_phase_progress,
        which skips non-done terminals).

    Aggregate mode (aggregate=True) -> guaranteed clean no-op (return 0, the
    archive cache is never consulted). The cache is single-repo, bare-keyed off
    PROJECT_ROOT, and load_aggregated does NOT rebind PROJECT_ROOT per repo — so
    crediting here would be both inert (namespaced m.key never matches a bare key)
    AND a cross-repo contamination hazard. The no-op is explicit, not accidental.
    Aggregate milestone fractions therefore stay archive-naive (documented scope
    limit), but never wrong.

    Common case (single-repo, nothing archived) -> 0, so counters stay
    byte-identical to the pre-fix render.
    """
    if aggregate:
        return 0
    archived = _get_archived_tasks_cached()
    count = 0
    for t in archived.values():
        if (getattr(t, "milestone", "") or "") != m.key:
            continue
        if done_only:
            if not getattr(t, "is_done", False):
                continue
        elif not getattr(t, "is_terminal", False):
            continue
        if t.key not in tasks:
            count += 1
    return count


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


