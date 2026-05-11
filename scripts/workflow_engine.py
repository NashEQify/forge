#!/usr/bin/env python3
"""
workflow_engine.py — Workflow Engine for BuddyAI.

YAML-driven workflow orchestration: reads definitions, tracks state,
tells the LLM what step comes next.

Spec: docs/specs/workflow-engine.md v0.2.2

Usage:
    python3 scripts/workflow_engine.py --start <workflow> [--task <id>]
    python3 scripts/workflow_engine.py --next [--id <workflow-id>] [--brief]
    python3 scripts/workflow_engine.py --complete <step-id> [--route <key>] [--evidence <text>]
                                                           [--force] [--set <key> <value>]
    python3 scripts/workflow_engine.py --skip <step-id> --reason "<text>"
    python3 scripts/workflow_engine.py --retry <step-id> --reason "<text>"
    python3 scripts/workflow_engine.py --status [--id <workflow-id>]
    python3 scripts/workflow_engine.py --list [--format json] [--available]
    python3 scripts/workflow_engine.py --validate [--before-commit]
    python3 scripts/workflow_engine.py --recover [--id <workflow-id>]
    python3 scripts/workflow_engine.py --abort <workflow-id> --reason "<text>"
    python3 scripts/workflow_engine.py --pause [--id <workflow-id>]
    python3 scripts/workflow_engine.py --resume [--id <workflow-id>]
    python3 scripts/workflow_engine.py --handoff-context
    python3 scripts/workflow_engine.py --boot-context
    python3 scripts/workflow_engine.py --find --task <id>
    python3 scripts/workflow_engine.py --guard <guard-name> [<task-id>]

Exit Codes: 0=success, 1=validation-fail, 2=not-found, 3=schema-error, 4=corrupt-state
"""

from __future__ import annotations

import argparse
import contextlib
import json
import os
import re
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

try:
    import fcntl  # type: ignore
except ImportError:  # Windows
    fcntl = None  # type: ignore

# Allow running both as `python3 scripts/workflow_engine.py` (cwd=repo root)
# and from tests that import the module. This sys.path insertion targets the
# framework checkout (where scripts/ lives), not the active project root.
_SCRIPT_DIR = Path(__file__).resolve().parent
_FRAMEWORK_ROOT = _SCRIPT_DIR.parent
if str(_FRAMEWORK_ROOT) not in sys.path:
    sys.path.insert(0, str(_FRAMEWORK_ROOT))

from scripts.lib.yaml_loader import (  # noqa: E402
    SchemaError,
    discover_workflow_yaml,
    list_available_workflows,
    load_workflow_yaml,
    resolve_task_id,
)

# ---------------------------------------------------------------------------
# Path resolution (Task 010 Part L0b — Pre-Split Refactor)
# ---------------------------------------------------------------------------
#
# PROJECT_ROOT   → where the active project's data lives: .workflow-state/,
#                  docs/tasks/, docs/<workflow>/ (solve/build/fix/review/
#                  research/docs-rewrite — see STATE_FILE_DIRS), and any
#                  workflow-step artefacts
#                  referenced by completion checks / guards. Derived from
#                  BUDDY_PROJECT_ROOT env-var, --project-root flag, or
#                  Path.cwd(). Post-split this is the product repo (e.g.
#                  ~/projects/buddyai), while workflow_engine.py itself has
#                  moved to the framework repo.
#
# FRAMEWORK_ROOT → where workflow_engine.py itself lives. Reserved for
#                  framework-internal reads (currently none directly —
#                  workflow YAML discovery is delegated to
#                  scripts.lib.yaml_loader which resolves against its own
#                  FRAMEWORK_ROOT constant).
#
# REPO_ROOT      → back-compat alias mirroring PROJECT_ROOT. Kept so existing
#                  callers / tests that reference `scripts.workflow_engine
#                  .REPO_ROOT` keep working during the transition.
#
# Pre-Split Invariant: when invoked from the BuddyAI monolith root without
# BUDDY_PROJECT_ROOT set, PROJECT_ROOT == FRAMEWORK_ROOT == BuddyAI root,
# so existing behaviour (and the 140-test regression suite) is preserved.

PROJECT_ROOT = Path(os.environ.get("BUDDY_PROJECT_ROOT", Path.cwd())).resolve()
FRAMEWORK_ROOT = _FRAMEWORK_ROOT
REPO_ROOT = PROJECT_ROOT

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

EXIT_SUCCESS = 0
EXIT_VALIDATION_FAIL = 1
EXIT_NOT_FOUND = 2
EXIT_SCHEMA_ERROR = 3
EXIT_CORRUPT_STATE = 4

STATE_DIR = PROJECT_ROOT / ".workflow-state"
ARCHIVE_DIR = STATE_DIR / "archive"

# Step statuses
STATUS_PENDING = "pending"
STATUS_IN_PROGRESS = "in_progress"
STATUS_COMPLETE = "complete"
STATUS_SKIPPED = "skipped"
STATUS_ROUTE_SKIPPED = "route_skipped"
STATUS_WARN_SKIPPED = "warn_skipped"
STATUS_ESCALATED = "escalated"

TERMINAL_STEP_STATUSES = {
    STATUS_COMPLETE, STATUS_SKIPPED, STATUS_ROUTE_SKIPPED,
    STATUS_WARN_SKIPPED, STATUS_ESCALATED,
}

# Force guardrails per workflow instance.
# - FORCE_WARN_THRESHOLD: emit warning once exceeded (soft limit)
# - MAX_FORCE_PER_WORKFLOW: hard stop
FORCE_WARN_THRESHOLD = 2
MAX_FORCE_PER_WORKFLOW = 10

# Default iteration-cap per step (Item 7 + Item 13). Override via workflow.yaml
# top-level `iteration_cap: <int>` OR --retry --reason "override-rationale".
DEFAULT_ITERATION_CAP = 3


# ---------------------------------------------------------------------------
# State Management
# ---------------------------------------------------------------------------

def _utcnow() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _parse_utc(ts: str) -> datetime:
    """Parse a UTC timestamp string."""
    for fmt in ("%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S.%fZ"):
        try:
            return datetime.strptime(ts, fmt).replace(tzinfo=UTC)
        except ValueError:
            continue
    raise ValueError(f"Cannot parse timestamp: {ts}")


def _generate_workflow_id(workflow_name: str, task_id: int | None) -> str:
    ts = datetime.now(UTC).strftime("%Y%m%dT%H%M")
    parts = [workflow_name]
    if task_id is not None:
        parts.append(str(task_id))
    parts.append(ts)
    return "-".join(parts)


def _state_path(workflow_id: str) -> Path:
    return STATE_DIR / f"{workflow_id}.json"


def _ensure_state_dir() -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)


def load_state(workflow_id: str) -> dict[str, Any]:
    """Load state file. Raises SystemExit on corruption."""
    path = _state_path(workflow_id)
    if not path.exists():
        print(f"ERROR: State file not found: {path}", file=sys.stderr)
        sys.exit(EXIT_NOT_FOUND)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        print(f"ERROR: Corrupt state file {path}: {e}", file=sys.stderr)
        sys.exit(EXIT_CORRUPT_STATE)
    return data


@contextlib.contextmanager
def _state_lock():
    """Acquire an exclusive flock on STATE_DIR/_lock for atomic state ops.

    Prevents race conditions when boot-context, --next, --complete run
    concurrently against the same .workflow-state/ (e.g. UserPromptSubmit
    hook firing while boot is still parallelising). Unix-only (fcntl).
    """
    _ensure_state_dir()
    lock_path = STATE_DIR / "_lock"
    fd = os.open(str(lock_path), os.O_CREAT | os.O_RDWR, 0o644)
    try:
        if fcntl is not None:
            fcntl.flock(fd, fcntl.LOCK_EX)
        yield
    finally:
        if fcntl is not None:
            fcntl.flock(fd, fcntl.LOCK_UN)
        os.close(fd)


def save_state(state: dict[str, Any]) -> None:
    """Write state to disk atomically (tmp + os.replace) under flock.

    Atomicity prevents kill-9-mid-write corruption. Concurrent --next /
    --complete / --boot-context calls serialise via _state_lock.
    """
    with _state_lock():
        path = _state_path(state["workflow_id"])
        tmp_path = path.with_suffix(path.suffix + ".tmp")
        tmp_path.write_text(
            json.dumps(state, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        os.replace(str(tmp_path), str(path))


def list_active_states() -> list[dict[str, Any]]:
    """List all active (non-archived) workflow states.

    Corrupt JSON files are reported to stderr (not silently skipped) so
    the user discovers state-file corruption instead of "workflow vanished".
    Locking via _state_lock to guard against concurrent writes during scan.
    """
    if not STATE_DIR.exists():
        return []
    states = []
    with _state_lock():
        for p in sorted(STATE_DIR.glob("*.json")):
            if p.name == "_lock":
                continue
            try:
                states.append(json.loads(p.read_text(encoding="utf-8")))
            except json.JSONDecodeError as e:
                print(
                    f"WARNING: corrupt workflow-state file {p}: {e}. "
                    f"Run --recover or manually inspect.",
                    file=sys.stderr,
                )
                continue
            except OSError as e:
                print(f"WARNING: cannot read {p}: {e}", file=sys.stderr)
                continue
    return states


def archive_state(workflow_id: str) -> None:
    """Move state file to archive atomically (os.replace, single-step)."""
    with _state_lock():
        src = _state_path(workflow_id)
        if src.exists():
            dst = ARCHIVE_DIR / src.name
            os.replace(str(src), str(dst))


# ---------------------------------------------------------------------------
# Template Variable Resolution
# ---------------------------------------------------------------------------

def _resolve_vars(text: str, variables: dict[str, Any]) -> str:
    """Replace {var_name} placeholders with values from variables dict.

    Task 301 C2-003 Fix: empty-string-Resolution wird wie None/missing
    behandelt — Placeholder bleibt unaufgeloest. Pre-fix: empty-string
    `{spec_name}` resolved zu "" → Pfad wurde `docs/reviews/board/-foo.md`
    → `_has_unresolved_vars` fand nichts → pointer_check produzierte
    "file not found" statt "unresolved variable" (Diagnostic-Reibung).
    Per Spec §2.1 sollte source_file nie empty resolven; legitime empty
    Use-Cases existieren nicht in den whitelisted Resolution-Targets
    (path/command/pattern/source_file).
    """
    def replacer(m: re.Match) -> str:
        key = m.group(1)
        val = variables.get(key)
        if val is None:
            return m.group(0)
        s = str(val)
        # C2-003: empty-string wird wie missing behandelt
        if s == "":
            return m.group(0)
        return s
    return re.sub(r"\{(\w+)\}", replacer, text)


def _has_unresolved_vars(text: str) -> list[str]:
    """Return list of unresolved {var_name} placeholders in text.

    Spec 299 Phase C2 + CC-014/CC-016 Pass-1-Fix: variables-Dict-Lookup
    geschieht via `_resolve_completion_vars()` VOR diesem Aufruf, das die
    Variablen im Text ersetzt. Diese Funktion ist die Restpruefung —
    findet die Placeholder die nach Resolution noch im Text stehen.

    Pre-fix hatte ein optional `variables` Argument das im Hot-Path nirgends
    genutzt wurde (CC-016 dead-code im Hot-Path); ueber 1 Pass entfernt.
    Whitelist-Erweiterung ist semantisch via variables-Dict in
    _resolve_completion_vars (Spec §2.1).
    """
    return re.findall(r"\{(\w+)\}", text)


def _ensure_state_variables_resolved(state: dict[str, Any]) -> bool:
    """Lazy-resolve `spec_name` + `state_file` in state["variables"].

    Spec 299 Task 301 F-ENGINE-001 Fix: pre-fix war diese Resolution NUR
    in `find_next_step()`. `cmd_complete` ruft direkt `complete_step()`
    auf — wenn der Schritt-Completion-Check `pointer_check` mit
    `{spec_name}` enthaelt, blockiert HARD-policy weil die Variable
    noch nicht resolved wurde. Helper konsolidiert beide Lazy-Resolutions
    so dass Engine-Entry-Points (`--next`, `--complete`, `--status`) den
    selben Resolution-State sehen.

    Returns True wenn variables veraendert wurden (caller kann save_state
    auf Wunsch aufrufen).
    """
    task_id = state.get("task_id")
    if task_id is None:
        return False
    variables = state.setdefault("variables", {})
    changed = False

    # Spec 299 Phase C2 (F-I-013) — lazy spec_name lookup
    if not variables.get("spec_name"):
        try:
            spec_name = _resolve_spec_name(int(task_id))
        except (TypeError, ValueError):
            spec_name = None
        if spec_name:
            variables["spec_name"] = spec_name
            changed = True

    # F-100 lazy state_file re-discovery
    if not variables.get("state_file"):
        try:
            discovered = _discover_state_file(int(task_id))
        except (TypeError, ValueError):
            discovered = None
        if discovered:
            variables["state_file"] = discovered
            changed = True

    if changed:
        state["variables"] = variables
    return changed


def _resolve_spec_name(task_id: int) -> str | None:
    """Spec 299 Phase C2 (F-I-013) — resolve {spec_name} variable.

    Liest docs/tasks/<task_id>.yaml + extrahiert spec_ref-Field, returnt
    Basename ohne Extension (z.B. 'docs/specs/299-fabrication-mitigation.md'
    -> '299-fabrication-mitigation').

    Conditional: Task ohne spec_ref ODER spec_ref=null → return None.
    Engine setzt spec_name nur wenn None nicht ist (kein Override mit None).
    """
    candidates = [
        PROJECT_ROOT / "docs" / "tasks" / f"{task_id}.yaml",
        PROJECT_ROOT / "docs" / "tasks" / f"{task_id:03d}.yaml",
    ]
    task_yaml = next((c for c in candidates if c.is_file()), None)
    if task_yaml is None:
        return None

    try:
        import yaml as _yaml
    except ImportError:
        return None

    try:
        data = _yaml.safe_load(task_yaml.read_text(encoding="utf-8"))
    except (OSError, Exception):  # noqa: BLE001
        return None
    if not isinstance(data, dict):
        return None

    spec_ref = data.get("spec_ref")
    if not spec_ref or not isinstance(spec_ref, str):
        return None
    # Basename ohne Extension
    return Path(spec_ref).stem


# Workflow state-file directories searched by `_discover_state_file`. State-files
# live per workflow type (docs/<workflow>/...). List sourced from
# `workflows/runbooks/<workflow>/REFERENCE.md` Frontmatter-Schema sections —
# extend when a new workflow defines its state-file dir.
#
# Pre-Fix war diese Liste hardcoded auf `docs/solve/` (Task 459 surface):
# build/fix/review/research/docs-rewrite-State-Files wurden nie gefunden,
# Strategy 2 fired im falschen Dir. Multi-Dir-Search behebt das.
STATE_FILE_DIRS = (
    "solve",
    "build",
    "fix",
    "review",
    "research",
    "docs-rewrite",
)


def _discover_state_file(task_id: int) -> str | None:
    """Discover workflow state file for a given task ID.

    Searches all known workflow-state directories (`docs/<workflow>/`) for:
    1. Files with `task_ref: <task_id>` in YAML frontmatter (canonical key per
       `workflows/workflow-template.md` line 159 + 4 workflow REFERENCE.md).
       Legacy `parent_task: <task_id>` is ALSO accepted as fallback so existing
       state-files written before Task 459's convention-fix keep resolving.
    2. Most recent file with literal `task-<N>` or `task_<N>` prefix in the
       filename (across all workflow dirs).

    Returns relative path (from project root) or None.

    Convention note: `parent_task:` is the task-yaml field for sub-task
    hierarchy (`framework/task-format.md` line 45). It is NOT a state-file
    field. Strategy-1 fallback exists purely for backward-compat with files
    written before the convention was clarified.
    """
    candidate_files: list[Path] = []
    for sub in STATE_FILE_DIRS:
        wf_dir = PROJECT_ROOT / "docs" / sub
        if not wf_dir.is_dir():
            continue
        candidate_files.extend(wf_dir.glob("*.md"))

    if not candidate_files:
        return None

    # Sort by mtime DESC so most-recent wins on ambiguous filename match.
    md_files = sorted(candidate_files, key=lambda p: p.stat().st_mtime, reverse=True)

    # Strategy 1: YAML frontmatter with `task_ref:` (primary) or
    # `parent_task:` (legacy fallback for pre-fix state-files).
    for md_file in md_files:
        try:
            content = md_file.read_text(errors="replace")
        except OSError:
            continue
        fm_match = re.match(r"^---\s*\n(.*?)\n---", content, re.DOTALL)
        if not fm_match:
            continue
        frontmatter = fm_match.group(1)
        # Primary: task_ref (canonical state-file convention)
        tr_match = re.search(r"^\s*task_ref:\s*(\d+)\s*$", frontmatter, re.MULTILINE)
        if tr_match and int(tr_match.group(1)) == task_id:
            return str(md_file.relative_to(PROJECT_ROOT))
        # Legacy fallback: parent_task (pre-Task-459 convention)
        pt_match = re.search(r"^\s*parent_task:\s*(\d+)\s*$", frontmatter, re.MULTILINE)
        if pt_match and int(pt_match.group(1)) == task_id:
            return str(md_file.relative_to(PROJECT_ROOT))

    # Strategy 2: explicit `task-<N>` prefix (e.g., 2026-04-07-task-331-foo.md).
    # Previous regex `(?:^|[-_])0*N(?:[-_]|$)` had false-positives on date
    # components (e.g., task_id=1 matched "2026-05-01-..." via the "01" digits).
    # Now we require the literal "task-" or "task_" prefix to anchor the match.
    task_str = str(task_id)
    for md_file in md_files:
        name = md_file.stem  # without extension
        # Match "task-<N>" or "task_<N>" with word-boundary after N
        if re.search(rf"task[-_]0*{re.escape(task_str)}(?:[-_]|$)", name):
            return str(md_file.relative_to(PROJECT_ROOT))

    # No match: warn so user knows state-file lookup failed (vs silent
    # degradation to "manual" completion-checks)
    print(
        f"WARNING: no state-file found for task {task_id}. "
        f"Strategy 1 (frontmatter task_ref or legacy parent_task across "
        f"docs/{{{','.join(STATE_FILE_DIRS)}}}/) + Strategy 2 (task-N filename) "
        f"both missed. Workflow steps using {{state_file}} will degrade to manual.",
        file=sys.stderr,
    )

    return None


def _resolve_completion_vars(comp: dict[str, Any], variables: dict[str, Any]) -> dict[str, Any]:
    """Deep-resolve template vars in completion definitions."""
    resolved: dict[str, Any] = {}
    for k, v in comp.items():
        if isinstance(v, str):
            resolved[k] = _resolve_vars(v, variables)
        elif isinstance(v, list) and k == "checks":
            resolved[k] = [_resolve_completion_vars(c, variables) if isinstance(c, dict) else c for c in v]
        elif isinstance(v, list):
            resolved[k] = [_resolve_vars(item, variables) if isinstance(item, str) else item for item in v]
        else:
            resolved[k] = v
    return resolved


# ---------------------------------------------------------------------------
# Completion Checks
# ---------------------------------------------------------------------------

def _resolve_evidence_layout(
    state: dict[str, Any], step_state: dict[str, Any],
) -> str:
    """Read evidence_layout from skill-frontmatter (F-I-014).

    Lookup-Pfad: state["current_step"]["skill_ref"] ODER step_state["skill_ref"].
    Bei fehlendem skill_ref ODER File nicht lesbar: Default 'auto'.
    Bei Skill-Frontmatter ohne evidence_layout: Default 'per_finding' (Spec §1.5).

    CC-021 (F-CA-011) Pass-1-Fix: Snapshot-Pattern. Wenn step_state
    "evidence_layout_snapshot" enthaelt (geschrieben bei --start), nutze den
    Snapshot statt fresh-read — Mid-Flight-Layout-Mutation wird so abgefangen
    UND geloggt.
    """
    snapshot = step_state.get("evidence_layout_snapshot")
    if isinstance(snapshot, str) and snapshot in (
        "per_finding", "top_level", "auto",
    ):
        # Use snapshot but compute fresh value too, log if drift detected.
        fresh = _detect_evidence_layout_now(state, step_state)
        if fresh != snapshot:
            print(
                f"WARNING: evidence_layout drift mid-flight — snapshot was "
                f"{snapshot!r}, current Skill-FM says {fresh!r}. Honoring "
                f"snapshot (CC-021 Pass-1-Fix).",
                file=sys.stderr,
            )
        return snapshot
    return _detect_evidence_layout_now(state, step_state)


def _detect_evidence_layout_now(
    state: dict[str, Any], step_state: dict[str, Any],
) -> str:
    """Inner helper — re-read Skill-Frontmatter at call-time (no snapshot)."""
    skill_ref = None
    cur = state.get("current_step")
    if isinstance(cur, dict):
        skill_ref = cur.get("skill_ref")
    if not skill_ref:
        skill_ref = step_state.get("skill_ref")
    if not skill_ref:
        return "auto"

    # skill_ref kann unter PROJECT_ROOT oder FRAMEWORK_ROOT liegen
    candidates = [
        PROJECT_ROOT / str(skill_ref),
        FRAMEWORK_ROOT / str(skill_ref),
    ]
    skill_path = next((c for c in candidates if c.is_file()), None)
    if skill_path is None:
        return "auto"

    try:
        text = skill_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return "auto"

    fm_match = re.match(r"^---\s*\n(.*?)\n---", text, re.DOTALL)
    if not fm_match:
        return "per_finding"
    fm_text = fm_match.group(1)
    layout_match = re.search(
        r"(?m)^\s*evidence_layout:\s*(per_finding|top_level)\s*$", fm_text
    )
    if layout_match:
        return layout_match.group(1)
    return "per_finding"


def _check_pointer(
    comp: dict[str, Any], state: dict[str, Any], step_state: dict[str, Any],
) -> tuple[bool, str]:
    """pointer_check Completion-Type — Spec 299 §2.1 Schicht-2.

    1. source_file resolved (mit unresolved-vars-graceful — siehe loop oben).
    2. Layout via Skill-Frontmatter (default per_finding).
    3. validate_evidence_pointers Library-Import:
       - schema_version: 0 OR missing → return (True, "legacy, skipped")
       - schema_version: 1 + leeres/missing evidence → return (False, "non-empty...")
       - pro Pointer Mechanik (existence + grep -F + range etc.)
    4. exit-code Mapping: 0 → (True, msg), 1 → (False, msg), 2 → (False, parse-error).
    5. NIE crash — bei ImportError silent-degrade auf manual.
    """
    source_file = comp.get("source_file")
    if not source_file:
        return False, "pointer_check: 'source_file' required"

    # Resolve relativ zu PROJECT_ROOT
    abs_source = (PROJECT_ROOT / str(source_file)).resolve()
    # CC-003 (F-CA-002) fix: asymmetric-boundary-check — Validator hatte
    # _resolve_within_repo, Engine source_file aber nicht. Symlink-Drop in
    # docs/reviews/board/ konnte source_file auf /etc/passwd zeigen lassen.
    # Spec §1.3 sagt "Path-Format: repo-relativ" generell, nicht
    # selektiv per Validator-Pfad.
    try:
        abs_source.relative_to(PROJECT_ROOT.resolve())
    except ValueError:
        return False, (
            f"pointer_check: source_file resolves outside repo: "
            f"{source_file} -> {abs_source}"
        )
    if not abs_source.is_file():
        return False, f"pointer_check: file not found: {source_file}"

    layout = _resolve_evidence_layout(state, step_state)

    try:
        from scripts.validate_evidence_pointers import (
            EvidenceParseError as _EvParseErr,
            EvidenceValidationError as _EvValErr,
            validate_file,
        )
    except ImportError as exc:
        # Silent-degrade: validator-lib unavailable → manual
        return True, f"manual: validate_evidence_pointers unavailable ({exc})"

    # Legacy-Detection vor validate_file (validator returnt empty messages
    # bei legacy was wir nicht von "valid mit 0 pointers" unterscheiden
    # koennen — Engine muss das semantisch erkennen)
    try:
        from scripts.validate_evidence_pointers import get_schema_version
        sv = get_schema_version(str(abs_source))
    except Exception:  # noqa: BLE001
        sv = None

    try:
        exit_code, messages = validate_file(
            str(abs_source), layout=layout, repo_root=str(PROJECT_ROOT),
        )
    except (_EvParseErr, _EvValErr) as exc:
        return False, f"pointer_check parse-error: {exc}"
    except Exception as exc:  # noqa: BLE001
        # Engine NIE crash — return (False, msg) per Spec §5.2 error_handling
        return False, f"pointer_check internal error: {exc}"

    # CC-007 fix: separate WARN-Channel von errors. Validator-Library appended
    # WARN-Strings ans messages-Array; engine-Pfad sollte sie NICHT als Teil
    # des Success-Detail propagieren (sonst log-greps nach `WARN` produzieren
    # false-positives, User sieht "ok: WARN..." was kontraintuitiv ist).
    warn_msgs = [m for m in messages if m.startswith("WARN")]
    ok_msgs = [m for m in messages if not m.startswith("WARN")]
    detail = "; ".join(ok_msgs) if ok_msgs else ""
    # Emit WARNs auf stderr — Discipline-Channel parallel zur Engine-Logging.
    for w in warn_msgs:
        print(f"INFO pointer_check {step_state.get('id', '?')}: {w}",
              file=sys.stderr)

    if exit_code == 0:
        if sv is None or sv == 0:
            return True, "legacy, skipped (schema_version 0 or missing)"
        return True, f"pointer_check ok: {detail}" if detail else "pointer_check ok"
    if exit_code == 1:
        return False, f"pointer_check fail: {detail}"
    # exit_code == 2
    return False, f"pointer_check parse-error: {detail}"


def check_completion(comp: dict[str, Any], state: dict[str, Any], step_state: dict[str, Any]) -> tuple[bool, str]:
    """Evaluate a completion condition. Returns (passed, message)."""
    variables = state.get("variables", {})
    comp = _resolve_completion_vars(comp, variables)
    ctype = comp.get("type", "manual")

    # Check for unresolved variables in path/command/pattern/source_file fields
    # — graceful degradation. Spec 299 Phase C2 erweitert die Whitelist um
    # source_file (pointer_check Pflichtfeld).
    for field in ("path", "command", "pattern", "source_file"):
        val = comp.get(field)
        if isinstance(val, str):
            unresolved = _has_unresolved_vars(val)
            if unresolved:
                var_names = ", ".join(unresolved)
                print(
                    f"WARNING: Unresolved variable(s) {{{var_names}}} in completion check "
                    f"field '{field}' (value: {val}). Treating as manual.",
                    file=sys.stderr,
                )
                return True, f"manual: unresolved variable(s) {{{var_names}}} — skipped check"
        elif isinstance(val, list):
            for item in val:
                if isinstance(item, str):
                    unresolved = _has_unresolved_vars(item)
                    if unresolved:
                        var_names = ", ".join(unresolved)
                        print(
                            f"WARNING: Unresolved variable(s) {{{var_names}}} in completion check "
                            f"field '{field}' (value: {item}). Treating as manual.",
                            file=sys.stderr,
                        )
                        return True, f"manual: unresolved variable(s) {{{var_names}}} — skipped check"

    if ctype == "manual":
        return True, "manual: always passes"

    if ctype == "file_modified_after":
        target_path = comp.get("path", "")
        abs_path = PROJECT_ROOT / target_path
        if not abs_path.exists():
            return False, f"file not found: {target_path}"
        started_at = step_state.get("started_at", state.get("started"))
        if not started_at:
            return True, "no started_at to compare"
        start_ts = _parse_utc(started_at).timestamp()
        mtime = abs_path.stat().st_mtime
        if mtime >= start_ts:
            return True, "file modified after step start"
        return False, f"file not modified since step start ({target_path})"

    if ctype == "file_created_matching":
        patterns = comp.get("pattern", [])
        if isinstance(patterns, str):
            patterns = [patterns]
        workflow_start = state.get("started", "")
        start_ts = 0.0 if not workflow_start else _parse_utc(workflow_start).timestamp()
        for pat in patterns:
            for match_path in Path(PROJECT_ROOT / pat).parent.glob(Path(pat).name):
                if match_path.exists() and match_path.stat().st_mtime >= start_ts:
                    rel = str(match_path.relative_to(PROJECT_ROOT))
                    state.setdefault("variables", {})["artifact_path"] = rel
                    return True, f"found matching file: {rel}"
        return False, f"no matching files for patterns: {patterns}"

    if ctype == "file_content_check":
        target_path = comp.get("path", "")
        abs_path = PROJECT_ROOT / target_path
        if not abs_path.exists():
            return False, f"file not found: {target_path}"
        content = abs_path.read_text(errors="replace")
        pattern = comp.get("pattern", "")
        condition = comp.get("condition", "has_match")
        has = bool(re.search(pattern, content))
        if condition == "has_match":
            if has:
                return True, f"pattern found in {target_path}"
            return False, f"pattern not found in {target_path}"
        # no_match
        if not has:
            return True, f"pattern correctly absent from {target_path}"
        return False, f"pattern unexpectedly found in {target_path}"

    if ctype == "exit_code":
        command = comp.get("command", "")
        try:
            result = subprocess.run(  # noqa: S602
                command, shell=True, capture_output=True, timeout=30,
                cwd=str(PROJECT_ROOT),
            )
            if result.returncode == 0:
                return True, "command succeeded (exit 0)"
            return False, f"command failed (exit {result.returncode})"
        except subprocess.TimeoutExpired:
            return False, "command timed out"
        except Exception as e:  # noqa: BLE001
            return False, f"command error: {e}"

    if ctype == "pointer_check":
        # Spec 299 Phase C2 — Schicht-2 Engine-Check fuer Evidence-Pointer.
        # Library-Import von scripts.validate_evidence_pointers (Spec §6.5
        # Library-bevorzugt). Bei ImportError: silent-degrade auf manual
        # damit Engine NIE crasht.
        return _check_pointer(comp, state, step_state)

    if ctype == "compound":
        # CC-004 (F-CA-003) fix: graceful-degradation-Konflikt mit
        # spec-§2.2-Race-Mitigation. Pre-fix: pointer_check mit unresolved
        # `{spec_name}` returnt (True, "manual: unresolved...") → manual
        # passt → compound passes silent. Konsequenz: jeder Task ohne
        # spec_ref durchlief Tier-1-Steps OHNE pointer_check Enforcement.
        # Generic-Defense-vs-Specific-Enforcement-Drift.
        checks = comp.get("checks", [])
        for i, sub in enumerate(checks):
            if not isinstance(sub, dict):
                continue
            ok, msg = check_completion(sub, state, step_state)
            # HARD policy fuer pointer_check innerhalb compound: unresolved
            # variables blockieren — pointer_check-Defense darf NICHT
            # via graceful-degradation umgangen werden.
            if (
                sub.get("type") == "pointer_check"
                and ok
                and "unresolved variable" in msg
            ):
                return False, (
                    f"compound check [{i}] pointer_check requires "
                    f"resolved source_file (Spec 299 §2.2): {msg}"
                )
            if not ok:
                return False, f"compound check [{i}] failed: {msg}"
        return True, "all compound checks passed"

    return False, f"unknown completion type: {ctype}"


# ---------------------------------------------------------------------------
# Guard Evaluation
# ---------------------------------------------------------------------------

def evaluate_guard(guard: dict[str, Any], state: dict[str, Any], variables: dict[str, Any]) -> tuple[bool, str]:
    """Evaluate a guard. Returns (proceed, reason). proceed=False means skip."""
    gtype = guard.get("type", "")

    if gtype == "always_skip":
        return False, "always_skip guard"

    if gtype == "file_exists":
        path_pattern = guard.get("path", "")
        resolved = _resolve_vars(path_pattern, variables)
        matches = list(Path(PROJECT_ROOT / resolved).parent.glob(Path(resolved).name))
        if matches:
            return True, f"file exists: {resolved}"
        return False, f"file not found: {resolved}"

    if gtype == "step_status":
        step_id = guard.get("step_id", "")
        expected = guard.get("expected", "complete")
        steps = state.get("steps", {})
        step_state = steps.get(step_id, {})
        actual = step_state.get("status", STATUS_PENDING)
        if actual == expected:
            return True, f"step '{step_id}' is {actual}"
        return False, f"step '{step_id}' is {actual}, expected {expected}"

    if gtype == "route_active":
        step_id = guard.get("step_id", "")
        route = guard.get("route", "")
        steps = state.get("steps", {})
        step_state = steps.get(step_id, {})
        selected = step_state.get("selected_route")
        if selected == route:
            return True, f"route '{route}' is active on step '{step_id}'"
        return False, f"route '{route}' not active on step '{step_id}' (selected: {selected})"

    if gtype == "script":
        command = guard.get("command", "")
        resolved = _resolve_vars(command, variables)
        try:
            result = subprocess.run(  # noqa: S602
                resolved, shell=True, capture_output=True, timeout=30,
                cwd=str(PROJECT_ROOT),
            )
            if result.returncode == 0:
                return True, "script guard: proceed"
            return False, f"script guard: skip (exit {result.returncode})"
        except subprocess.TimeoutExpired:
            return False, "script guard: timeout"
        except Exception as e:  # noqa: BLE001
            return False, f"script guard error: {e}"

    return False, f"unknown guard type: {gtype}"


# ---------------------------------------------------------------------------
# Workflow Definition Helpers
# ---------------------------------------------------------------------------

def _get_step_def(workflow_def: dict[str, Any], step_id: str) -> dict[str, Any] | None:
    """Find step definition by id."""
    for s in workflow_def.get("steps", []):
        if isinstance(s, dict) and s.get("id") == step_id:
            return s
    return None


def _ordered_step_ids(workflow_def: dict[str, Any]) -> list[str]:
    """Return step IDs in definition order."""
    return [s["id"] for s in workflow_def.get("steps", []) if isinstance(s, dict) and "id" in s]


def _get_all_route_step_ids(workflow_def: dict[str, Any]) -> dict[str, set[str]]:
    """Map: classification_step_id -> set of all step IDs referenced in its routes."""
    result: dict[str, set[str]] = {}
    for step in workflow_def.get("steps", []):
        if not isinstance(step, dict):
            continue
        if step.get("category") == "classification" and step.get("routes"):
            all_ids: set[str] = set()
            for route_steps in step["routes"].values():
                if isinstance(route_steps, list):
                    all_ids.update(route_steps)
            result[step["id"]] = all_ids
    return result


# ---------------------------------------------------------------------------
# Core Workflow Logic
# ---------------------------------------------------------------------------

def create_state(
    workflow_name: str,
    workflow_def: dict[str, Any],
    task_id: int | None = None,
    parent_workflow_id: str | None = None,
    set_vars: dict[str, str] | None = None,
    route: str | None = None,
) -> dict[str, Any]:
    """Create initial workflow state.

    Workflow-level routes (top-level `routes:` block in yaml): if present
    AND `route` arg given, validate + apply `_apply_route_skip` immediately
    so non-route steps are marked STATUS_ROUTE_SKIPPED before first-step
    activation. Distinct from mid-workflow classification-step routes.

    Default route resolution: if workflow has top-level routes but `route`
    not given, default to "standard" if declared, else error with valid list.
    """
    _ensure_state_dir()
    wid = _generate_workflow_id(workflow_name, task_id)

    # Check for duplicate active workflow (same type + same task)
    for existing in list_active_states():
        if existing.get("workflow") == workflow_name and existing.get("task_id") == task_id:
            print(
                f"ERROR: Workflow '{workflow_name}' with task {task_id} already active "
                f"(id: {existing['workflow_id']})",
                file=sys.stderr,
            )
            sys.exit(EXIT_VALIDATION_FAIL)

    # Validate top-level routes (if declared) + resolve route
    wf_routes = workflow_def.get("routes")
    if wf_routes is not None:
        if not isinstance(wf_routes, dict) or not wf_routes:
            print(
                f"ERROR: Workflow '{workflow_name}' has 'routes' but not a "
                f"non-empty dict (got {type(wf_routes).__name__})",
                file=sys.stderr,
            )
            sys.exit(EXIT_SCHEMA_ERROR)
        if route is None:
            if "standard" in wf_routes:
                route = "standard"
            else:
                valid = ", ".join(sorted(wf_routes.keys()))
                print(
                    f"ERROR: workflow '{workflow_name}' declares routes but no "
                    f"--route given and no 'standard' default. Valid: {valid}",
                    file=sys.stderr,
                )
                sys.exit(EXIT_VALIDATION_FAIL)
        if route not in wf_routes:
            valid = ", ".join(sorted(wf_routes.keys()))
            print(
                f"ERROR: route '{route}' not declared in workflow '{workflow_name}'. "
                f"Valid: {valid}",
                file=sys.stderr,
            )
            sys.exit(EXIT_VALIDATION_FAIL)
    elif route is not None:
        print(
            f"ERROR: --route '{route}' given but workflow '{workflow_name}' "
            f"has no top-level 'routes:' block",
            file=sys.stderr,
        )
        sys.exit(EXIT_VALIDATION_FAIL)

    step_ids = _ordered_step_ids(workflow_def)
    now = _utcnow()

    steps_state: dict[str, dict[str, Any]] = {}
    for sid in step_ids:
        steps_state[sid] = {"status": STATUS_PENDING}

    # Apply route-filtering BEFORE first-step activation (eager).
    # Steps in OTHER routes but not selected → STATUS_ROUTE_SKIPPED.
    if wf_routes and route:
        _apply_route_skip(steps_state, wf_routes, route)

    # Activate first NON-SKIPPED step (route-skipped steps were eager-marked)
    first_step = None
    for sid in step_ids:
        if steps_state[sid].get("status") == STATUS_PENDING:
            first_step = sid
            break

    if first_step:
        steps_state[first_step]["status"] = STATUS_IN_PROGRESS
        steps_state[first_step]["started_at"] = now

    variables: dict[str, Any] = {
        "task_id": str(task_id) if task_id is not None else None,
        "artifact_path": None,
    }

    # Auto-discover state_file across all workflow types (solve/build/fix/...)
    if task_id is not None:
        discovered = _discover_state_file(task_id)
        if discovered:
            variables["state_file"] = discovered

        # Spec 299 Phase C2 (F-I-013) — befuelle spec_name aus
        # task.spec_ref Basename ohne Extension. Conditional damit Tasks
        # ohne spec_ref keine KeyError/None-Probleme produzieren.
        spec_name = _resolve_spec_name(task_id)
        if spec_name:
            variables["spec_name"] = spec_name

    # Apply explicit --set variables (override auto-discovered values)
    if set_vars:
        variables.update(set_vars)

    state: dict[str, Any] = {
        "schema_version": "2",  # bumped: top-level route support added
        "workflow": workflow_name,
        "workflow_id": wid,
        "task_id": task_id,
        "parent_workflow_id": parent_workflow_id,
        "started": now,
        "current_step": first_step,
        "selected_route": route,  # workflow-level route (None if no top-level routes)
        "variables": variables,
        "steps": steps_state,
        "force_count": 0,
    }

    save_state(state)
    return state


def find_next_step(state: dict[str, Any], workflow_def: dict[str, Any]) -> str | None:
    """Find the next actionable step. Returns step_id or None if all done/paused."""
    if state.get("paused"):
        return None

    step_ids = _ordered_step_ids(workflow_def)
    steps = state.get("steps", {})
    variables = state.get("variables", {})

    # FW-001 (drift-tolerance): workflow.yaml may have grown step-additions
    # AFTER state-file creation (spec evolved between sessions). Merge any
    # missing step_ids from workflow_def into state["steps"] as PENDING so
    # later activation does not KeyError on `steps[sid]["status"] = ...`.
    for sid in step_ids:
        if sid not in steps:
            steps[sid] = {"status": STATUS_PENDING}
    state["steps"] = steps

    # F-100 (lazy state_file re-discovery) + Spec 299 Phase C2 (F-I-013) lazy
    # spec_name lookup. Konsolidiert in `_ensure_state_variables_resolved`
    # damit `--complete` (cmd_complete) denselben Resolution-State sieht
    # (Task 301 F-ENGINE-001 Fix: pre-fix war Resolution NUR hier; `--complete`
    # mit pointer_check + `{spec_name}` blockierte ohne `--force`).
    if _ensure_state_variables_resolved(state):
        # Persist immediately so downstream callers and concurrent reads
        # see the discovered path even if no step gets activated this pass.
        try:
            save_state(state)
        except OSError as exc:
            print(
                f"WARNING: save_state failed after lazy variable "
                f"resolution: {exc}",
                file=sys.stderr,
            )
    variables = state.get("variables", {})

    # FW-007 auto-complete is restricted to deterministic completion-types
    # whose evaluation is side-effect-free / file-based. Manual & compound
    # are excluded by spec (manual cannot be auto-checked, compound may
    # contain manual sub-checks).
    # CC-023 (F-CF-003) Pass-1-Fix: pointer_check als top-level type ist per
    # Spec §2.2 schema-permissiv mit auto-complete-on-pass — wenn Pointer
    # mechanisch valid sind, passiert der Step ohne expliziten manual-step.
    # Aufgenommen ins Set damit die Spec-Zusage tatsaechlich greift.
    _AUTO_COMPLETE_TYPES = {
        "exit_code",
        "file_content_check",
        "file_created_matching",
        "file_modified_after",
        "pointer_check",
    }

    for sid in step_ids:
        ss = steps.get(sid, {})
        status = ss.get("status", STATUS_PENDING)

        # Already in progress — this IS the next step
        if status == STATUS_IN_PROGRESS:
            return sid

        # Skip terminal statuses
        if status in TERMINAL_STEP_STATUSES:
            continue

        # Pending: check depends_on
        step_def = _get_step_def(workflow_def, sid)
        if not step_def:
            continue

        deps = step_def.get("depends_on", [])
        if isinstance(deps, list):
            deps_met = all(
                steps.get(d, {}).get("status") in TERMINAL_STEP_STATUSES
                for d in deps
            )
            if not deps_met:
                continue

        # Check guard
        guard = step_def.get("guard")
        if guard and isinstance(guard, dict):
            proceed, reason = evaluate_guard(guard, state, variables)
            if not proceed:
                steps[sid] = {
                    "status": STATUS_SKIPPED,
                    "skipped_reason": f"guard: {reason}",
                    "completed_at": _utcnow(),
                }
                try:
                    save_state(state)
                except OSError as exc:
                    print(
                        f"WARNING: save_state failed after guard-skip "
                        f"of '{sid}': {exc}",
                        file=sys.stderr,
                    )
                continue

        # FW-007 (pre-fulfilled idempotency): if a deterministic step's
        # completion-check already passes BEFORE activation (typical when
        # an artefact from a previous run still exists), auto-complete it
        # and continue to the next step instead of forcing a manual
        # --complete round-trip.
        cat = step_def.get("category", "content")
        comp = step_def.get("completion")
        if (
            cat == "deterministic"
            and isinstance(comp, dict)
            and comp.get("type") in _AUTO_COMPLETE_TYPES
        ):
            # check_completion reads step_state["started_at"] for
            # file_modified_after; seed it so the check has a baseline.
            now = _utcnow()
            if "started_at" not in steps[sid]:
                steps[sid]["started_at"] = now
            try:
                success, msg = check_completion(comp, state, steps[sid])
            except Exception as exc:  # noqa: BLE001
                # Auto-complete is opportunistic — never let an evaluator
                # crash break the regular activation path.
                success, msg = False, f"auto-complete eval error: {exc}"
            if success:
                steps[sid]["status"] = STATUS_COMPLETE
                steps[sid]["completed_at"] = _utcnow()
                steps[sid]["evidence"] = (
                    f"auto-complete: pre-fulfilled completion-check ({msg})"
                )
                try:
                    save_state(state)
                except OSError as exc:
                    print(
                        f"WARNING: save_state failed after auto-complete "
                        f"of '{sid}': {exc}",
                        file=sys.stderr,
                    )
                continue
            # Did not pre-fulfil — drop the speculative started_at so the
            # real activation below sets a fresh timestamp.
            if steps[sid].get("started_at") == now:
                del steps[sid]["started_at"]

        # Activate this step
        steps[sid]["status"] = STATUS_IN_PROGRESS
        steps[sid]["started_at"] = _utcnow()
        # CC-021 Pass-1-Fix: snapshot evidence_layout fuer pointer_check
        # Steps damit Mid-Flight-Skill-FM-Mutation nicht das Layout flippen
        # kann. Snapshot wird in _resolve_evidence_layout konsultiert.
        try:
            steps[sid]["skill_ref"] = step_def.get("skill_ref", "")
            snap = _detect_evidence_layout_now(
                {"current_step": {"skill_ref": step_def.get("skill_ref", "")}},
                steps[sid],
            )
            steps[sid]["evidence_layout_snapshot"] = snap
        except Exception:  # noqa: BLE001
            pass  # never let snapshot-error break activation
        state["current_step"] = sid
        try:
            save_state(state)
        except OSError as exc:
            print(
                f"WARNING: save_state failed after activating "
                f"'{sid}': {exc}",
                file=sys.stderr,
            )
        return sid

    return None


def complete_step(
    state: dict[str, Any],
    workflow_def: dict[str, Any],
    step_id: str,
    route: str | None = None,
    evidence: str | None = None,
    force: bool = False,
    set_vars: dict[str, str] | None = None,
) -> tuple[bool, str]:
    """Complete a step. Returns (success, message)."""
    steps = state.get("steps", {})
    if step_id not in steps:
        return False, f"Step '{step_id}' not found in workflow"

    step_state = steps[step_id]
    step_def = _get_step_def(workflow_def, step_id)
    if not step_def:
        return False, f"Step '{step_id}' not in workflow definition"

    current_status = step_state.get("status", STATUS_PENDING)
    if current_status in TERMINAL_STEP_STATUSES:
        return False, f"Step '{step_id}' already in terminal state: {current_status}"

    # Fix 1: Sequenz-Enforcement — step MUST be in_progress before completion.
    # This check is FORCE-IMMUN: --force cannot bypass it.
    if current_status != STATUS_IN_PROGRESS:
        return False, f"Step '{step_id}' is {current_status}, must be in_progress first. Run --next to advance."

    # Force guardrails: soft warning threshold + hard stop.
    if force:
        force_count = state.get("force_count", 0)
        if force_count >= MAX_FORCE_PER_WORKFLOW:
            return False, (
                f"Force limit reached ({MAX_FORCE_PER_WORKFLOW}/{MAX_FORCE_PER_WORKFLOW}). "
                "Cannot force-complete more steps in this workflow. "
                "Fix the completion check or --abort and restart."
            )

    # Set variables
    if set_vars:
        state.setdefault("variables", {}).update(set_vars)

    cat = step_def.get("category", "content")
    if cat == "classification":
        if not route:
            return False, f"Classification step '{step_id}' requires --route"
        routes = step_def.get("routes", {})
        if route not in routes:
            valid = ", ".join(sorted(routes.keys()))
            return False, f"Unknown route '{route}' for step '{step_id}'. Valid: {valid}"

    comp = step_def.get("completion")
    if comp and isinstance(comp, dict) and not force:
        passed, msg = check_completion(comp, state, step_state)
        if not passed:
            on_fail = step_def.get("on_fail", "block")
            if on_fail == "block":
                return False, f"Completion check failed: {msg}"
            if on_fail == "warn":
                step_state["status"] = STATUS_WARN_SKIPPED
                step_state["completed_at"] = _utcnow()
                step_state["warn_reason"] = msg
                if evidence:
                    step_state["evidence"] = evidence
                save_state(state)
                return True, f"WARNING: {step_id} failed: {msg}. Continuing."
            if on_fail == "skip":
                step_state["status"] = STATUS_SKIPPED
                step_state["completed_at"] = _utcnow()
                if evidence:
                    step_state["evidence"] = evidence
                save_state(state)
                return True, f"Skipped: {step_id}"
            if on_fail == "escalate":
                step_state["status"] = STATUS_ESCALATED
                step_state["completed_at"] = _utcnow()
                if evidence:
                    step_state["evidence"] = evidence
                save_state(state)
                return True, f"ESCALATE: {step_id} failed: {msg}. User action needed."

    force_count_after: int | None = None
    force_warning = ""

    # Force: increment counter and mark.
    if force and comp and isinstance(comp, dict):
        state["force_count"] = state.get("force_count", 0) + 1
        force_count_after = int(state["force_count"])
        step_state["force_completed"] = True
        if force_count_after > FORCE_WARN_THRESHOLD:
            force_warning = (
                f" WARNING: high force usage ({force_count_after}/{MAX_FORCE_PER_WORKFLOW}). "
                "Consider route selection, optional steps, or abort-closeout if this repeats."
            )

    # Mark complete
    step_state["status"] = STATUS_COMPLETE
    step_state["completed_at"] = _utcnow()
    if evidence:
        step_state["evidence"] = evidence

    # Route activation
    if route:
        step_state["selected_route"] = route
        if cat == "classification":
            _activate_route(state, workflow_def, step_id, route)

    save_state(state)

    # Check if workflow is done
    _check_workflow_completion(state, workflow_def)

    msg = f"Step '{step_id}' completed"
    if force_count_after is not None:
        msg += f" (forced {force_count_after}/{MAX_FORCE_PER_WORKFLOW})"
    if force_warning:
        msg += force_warning
    return True, msg


def _apply_route_skip(
    steps_state: dict[str, Any],
    routes: dict[str, Any],
    selected_route: str,
) -> None:
    """Mark steps not in selected_route (but in any other route) as ROUTE_SKIPPED.

    Reusable core for both:
    - `_activate_route` (mid-workflow at classification step) — routes live on step
    - `create_state` (at --start with --route) — routes live at workflow top-level

    Operates directly on the steps dict (state["steps"] or fresh init).
    """
    active_step_ids = set(routes.get(selected_route, []))
    all_route_step_ids: set[str] = set()
    for route_steps in routes.values():
        if isinstance(route_steps, list):
            all_route_step_ids.update(route_steps)

    # Steps that are in OTHER routes but NOT in selected route
    to_skip = all_route_step_ids - active_step_ids
    now = _utcnow()
    for sid in to_skip:
        if sid in steps_state and steps_state[sid].get("status") == STATUS_PENDING:
            steps_state[sid]["status"] = STATUS_ROUTE_SKIPPED
            steps_state[sid]["completed_at"] = now


def _activate_route(
    state: dict[str, Any],
    workflow_def: dict[str, Any],
    classification_step_id: str,
    selected_route: str,
) -> None:
    """After route selection at classification step: skip non-route steps.

    Mid-workflow variant — reads routes from the classification step itself.
    For at-start route activation, see `create_state` which calls
    `_apply_route_skip` directly with workflow top-level routes.
    """
    step_def = _get_step_def(workflow_def, classification_step_id)
    if not step_def:
        return
    routes = step_def.get("routes", {})
    _apply_route_skip(state.get("steps", {}), routes, selected_route)


def _check_workflow_completion(state: dict[str, Any], _workflow_def: dict[str, Any]) -> None:
    """Check if all steps are done. If so, archive state."""
    steps = state.get("steps", {})
    all_done = all(
        s.get("status") in TERMINAL_STEP_STATUSES
        for s in steps.values()
    )
    if not all_done:
        return

    state["completed"] = _utcnow()

    # If this is a child workflow, propagate completion to parent
    parent_id = state.get("parent_workflow_id")
    if parent_id:
        _propagate_child_completion(state, parent_id)

    save_state(state)
    archive_state(state["workflow_id"])


def _propagate_child_completion(child_state: dict[str, Any], parent_id: str) -> None:
    """When a child workflow completes, mark the parent step that spawned it."""
    parent_path = _state_path(parent_id)
    if not parent_path.exists():
        return
    try:
        parent_state = json.loads(parent_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return

    # Find parent workflow definition
    parent_wf_name = parent_state.get("workflow", "")
    parent_yaml_path = discover_workflow_yaml(parent_wf_name)
    if not parent_yaml_path:
        return
    try:
        parent_def = load_workflow_yaml(parent_yaml_path)
    except SchemaError:
        return

    # Find step with child_workflow matching child's workflow name
    child_wf_name = child_state.get("workflow", "")
    for step in parent_def.get("steps", []):
        if isinstance(step, dict) and step.get("child_workflow") == child_wf_name:
            sid = step["id"]
            parent_steps = parent_state.get("steps", {})
            if sid in parent_steps:
                parent_steps[sid]["status"] = STATUS_COMPLETE
                parent_steps[sid]["completed_at"] = _utcnow()
                parent_steps[sid]["evidence"] = f"child workflow {child_state.get('workflow_id')} completed"
                save_state(parent_state)
            break


def skip_step(
    state: dict[str, Any],
    workflow_def: dict[str, Any],
    step_id: str,
    reason: str,
) -> tuple[bool, str]:
    """Skip a step. Returns (success, message)."""
    steps = state.get("steps", {})
    if step_id not in steps:
        return False, f"Step '{step_id}' not found"

    step_def = _get_step_def(workflow_def, step_id)
    if not step_def:
        return False, f"Step '{step_id}' not in definition"

    required = step_def.get("required", True)
    if required:
        # Check if guard would skip
        guard = step_def.get("guard")
        if guard and isinstance(guard, dict):
            proceed, _ = evaluate_guard(guard, state, state.get("variables", {}))
            if not proceed:
                pass  # Guard fail allows skip even if required
            else:
                return False, f"Cannot skip required step '{step_id}' (guard passed)"
        else:
            return False, f"Cannot skip required step '{step_id}'"

    steps[step_id]["status"] = STATUS_SKIPPED
    steps[step_id]["completed_at"] = _utcnow()
    steps[step_id]["skipped_reason"] = reason
    save_state(state)
    return True, f"Step '{step_id}' skipped: {reason}"


def retry_step(
    state: dict[str, Any],
    workflow_def: dict[str, Any],
    step_id: str,
    reason: str,
) -> tuple[bool, str]:
    """Reset a terminal step back to pending so it can be re-executed.

    Item 7 (post-388 dogfooding): re-iteration-block was opaque-zur-Engine.
    `--retry` makes iteration mechanical-trackable. State-File records
    iteration-count per step + retry-history (audit-trail).

    Iteration-Cap (Item 13): default 3 per step. Workflow-level override
    via top-level `iteration_cap: <int>` in workflow.yaml. Beyond cap:
    --reason MUST contain explicit override-rationale (engine logs but
    accepts — Buddy-discipline + audit-trail catches abuse).

    Allowed source statuses: any TERMINAL_STEP_STATUSES (complete /
    skipped / warn_skipped / escalated). Not allowed for STATUS_PENDING
    (already retryable) or STATUS_IN_PROGRESS (use --complete first).
    """
    steps = state.get("steps", {})
    if step_id not in steps:
        return False, f"Step '{step_id}' not found"

    step_state = steps[step_id]
    current_status = step_state.get("status", STATUS_PENDING)

    if current_status == STATUS_PENDING:
        return False, (
            f"Step '{step_id}' is already pending — no retry needed. "
            f"Use --next to advance to it."
        )
    # in_progress + terminal both retry-able. in_progress = mid-execution-restart
    # (user discovered wrong direction). terminal = redo-after-completion (e.g.,
    # code-review-board FAIL after re-fix).

    # Iteration-cap check (workflow-level override allowed)
    iteration_cap = workflow_def.get("iteration_cap", DEFAULT_ITERATION_CAP)
    iterations = step_state.get("iterations", 1)  # 1 = initial run
    if iterations >= iteration_cap:
        # Override allowed via structured reason ("override:" or
        # "override-rationale:" prefix) — log but accept. Audit-trail in
        # retry_history catches abuse. Loose substring "override" rejected
        # to avoid false-positives ("no override here" etc.).
        reason_lower = reason.lower().strip()
        is_override = (
            reason_lower.startswith("override:")
            or reason_lower.startswith("override-rationale:")
            or " override:" in reason_lower
            or " override-rationale:" in reason_lower
        )
        if not is_override:
            return False, (
                f"Step '{step_id}' has iterated {iterations}/{iteration_cap} "
                f"times (cap reached). For legitimate override, --reason MUST "
                f"start with 'override:' or 'override-rationale:' followed by "
                f"explicit explanation. Iteration-Cap-Override-Discipline "
                f"(Item 13)."
            )

    # Reset state for retry, preserve audit-trail
    retry_history = step_state.get("retry_history", [])
    retry_history.append({
        "from_status": current_status,
        "reason": reason,
        "when": _utcnow(),
        "iteration_before": iterations,
    })

    step_state["status"] = STATUS_IN_PROGRESS
    step_state["started_at"] = _utcnow()
    step_state["iterations"] = iterations + 1
    step_state["retry_history"] = retry_history
    # Clear terminal-state fields so retry is clean
    for field in ("completed_at", "evidence", "warn_reason", "skipped_reason",
                  "force_completed", "selected_route"):
        step_state.pop(field, None)

    # Update current_step pointer
    state["current_step"] = step_id

    save_state(state)
    return True, (
        f"Step '{step_id}' reset to in_progress. Iteration {iterations + 1}/"
        f"{iteration_cap}. Reason: {reason}. Re-execute + --complete when done."
    )


# ---------------------------------------------------------------------------
# Recovery
# ---------------------------------------------------------------------------

def recover_workflow(state: dict[str, Any], workflow_def: dict[str, Any]) -> list[str]:
    """Re-evaluate completion conditions for in_progress steps. Returns list of recovered step IDs."""
    recovered: list[str] = []
    steps = state.get("steps", {})

    for sid, ss in steps.items():
        if ss.get("status") != STATUS_IN_PROGRESS:
            continue
        step_def = _get_step_def(workflow_def, sid)
        if not step_def:
            continue
        comp = step_def.get("completion")
        if not comp or not isinstance(comp, dict):
            continue
        passed, _msg = check_completion(comp, state, ss)
        if passed:
            ss["status"] = STATUS_COMPLETE
            ss["completed_at"] = _utcnow()
            ss["evidence"] = "recovered: completion check passed retroactively"
            recovered.append(sid)

    if recovered:
        save_state(state)
    return recovered


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def validate_commit_gates(states: list[dict[str, Any]]) -> list[str]:
    """Check commit_gate steps in active workflows up to current step.
    Only checks gates that have been REACHED (before or at current step).
    Future gates are not checked. Returns list of error strings (empty = PASS)."""
    errors: list[str] = []

    for state in states:
        wf_name = state.get("workflow", "")
        yaml_path = discover_workflow_yaml(wf_name)
        if not yaml_path:
            continue
        try:
            wf_def = load_workflow_yaml(yaml_path)
        except SchemaError:
            continue

        steps_state = state.get("steps", {})
        current_step = state.get("current_step", "")

        # Walk steps in YAML order, only check gates up to current step
        for step in wf_def.get("steps", []):
            if not isinstance(step, dict):
                continue
            sid = step["id"]

            # Check commit_gate if we've reached this step
            if step.get("commit_gate", False):
                ss = steps_state.get(sid, {})
                status = ss.get("status", STATUS_PENDING)
                if (
                    status != STATUS_COMPLETE
                    and status not in {STATUS_SKIPPED, STATUS_ROUTE_SKIPPED, STATUS_WARN_SKIPPED}
                    and status != STATUS_PENDING
                ):
                    errors.append(
                        f"[{state['workflow_id']}] commit_gate step '{sid}' is {status}, must be complete"
                    )

            # Stop checking after current step — everything after is future
            if sid == current_step:
                break

    return errors


# ---------------------------------------------------------------------------
# Formatting
# ---------------------------------------------------------------------------

def _last_step_evidence(steps: dict[str, dict[str, Any]]) -> str:
    """Return the evidence string from the most recently completed step (by completed_at)."""
    best_ts = ""
    best_ev = ""
    for ss in steps.values():
        ev = ss.get("evidence", "")
        ts = ss.get("completed_at", "")
        if ev and ts and ts > best_ts:
            best_ts = ts
            best_ev = ev
    return best_ev


def fmt_next(state: dict[str, Any], workflow_def: dict[str, Any], brief: bool = False) -> str:
    """Format the --next output."""
    step_id = state.get("current_step")
    if not step_id:
        step_id = find_next_step(state, workflow_def)
    if not step_id:
        return ""

    step_def = _get_step_def(workflow_def, step_id)
    if not step_def:
        return ""

    variables = state.get("variables", {})
    wf_name = state.get("workflow", "")
    task_id = state.get("task_id")
    started = state.get("started", "")

    # Count progress
    steps = state.get("steps", {})
    total = len(steps)
    done = sum(1 for s in steps.values() if s.get("status") in TERMINAL_STEP_STATUSES)

    # Resolve instruction
    instruction = _resolve_vars(step_def.get("instruction", ""), variables)
    category = step_def.get("category", "content")
    skill = step_def.get("skill_ref", "")
    comp = step_def.get("completion", {})
    if brief:
        task_str = f" [Task {task_id}]" if task_id else ""
        wf_id = state.get("workflow_id", "")
        parts = [f"NEXT: {wf_name}{task_str} > {step_id} ({category}): {instruction[:80]}"]

        # Context refs from step definition (F10)
        ctx_refs = step_def.get("context_refs", [])
        if ctx_refs:
            parts.append(f"CONTEXT: {', '.join(ctx_refs)}")

        # F10: last completed step evidence
        last_evidence = _last_step_evidence(steps)
        if last_evidence:
            parts.append(f"LAST: {last_evidence[:120]}")

        # F12: workflow_id for CLI usage
        parts.append(f"ID: {wf_id}")

        return " | ".join(parts)

    task_part = f" [Task {task_id}]" if task_id else ""
    time_part = f" (active since {started[:16]})" if started else ""
    lines = [
        f"WORKFLOW: {wf_name}{task_part}{time_part}",
        f"STEP: {step_id} ({category}) [{done + 1}/{total}]",
        f"INSTRUCTION: {instruction}",
    ]
    if skill:
        lines.append(f"SKILL: {skill}")

    # Context refs
    ctx_refs = step_def.get("context_refs", [])
    if ctx_refs:
        lines.append(f"CONTEXT: {', '.join(ctx_refs)}")

    # Completion expectation
    if isinstance(comp, dict):
        lines.append(f"COMPLETION: {_format_completion(comp, variables)}")

    lines.append(f"PROGRESS: {done}/{total} done | {total - done} remaining")

    return "\n".join(lines)


def _format_completion(comp: dict[str, Any], variables: dict[str, Any]) -> str:
    """Human-readable completion description."""
    ctype = comp.get("type", "manual")
    if ctype == "manual":
        return "manual"
    if ctype == "file_modified_after":
        return f"file_modified_after({_resolve_vars(comp.get('path', ''), variables)})"
    if ctype == "file_created_matching":
        patterns = comp.get("pattern", [])
        if isinstance(patterns, str):
            patterns = [patterns]
        resolved = [_resolve_vars(p, variables) for p in patterns]
        return f"file_created_matching({', '.join(resolved)})"
    if ctype == "file_content_check":
        path = _resolve_vars(comp.get("path", ""), variables)
        cond = comp.get("condition", "has_match")
        pat = comp.get("pattern", "")
        return f'file_content_check({path}, {cond}, "{pat}")'
    if ctype == "exit_code":
        return f"exit_code({comp.get('command', '')})"
    if ctype == "compound":
        checks = comp.get("checks", [])
        parts = [_format_completion(c, variables) if isinstance(c, dict) else str(c) for c in checks]
        return f"compound [{' + '.join(parts)}]"
    return ctype


def fmt_status(state: dict[str, Any]) -> str:
    """Format --status output."""
    wf_name = state.get("workflow", "")
    wid = state.get("workflow_id", "")
    task_id = state.get("task_id")
    started = state.get("started", "")
    current = state.get("current_step", "")
    steps = state.get("steps", {})

    total = len(steps)
    done = sum(1 for s in steps.values() if s.get("status") in TERMINAL_STEP_STATUSES)

    paused = state.get("paused", False)
    paused_str = " [PAUSED]" if paused else ""

    lines = [
        f"Workflow: {wf_name} (id: {wid}){paused_str}",
        f"Task: {task_id}" if task_id else "Task: none",
        f"Started: {started}",
        f"Current: {current}",
        f"Progress: {done}/{total} steps done",
        "",
        "Steps:",
    ]
    for sid, ss in steps.items():
        status = ss.get("status", STATUS_PENDING)
        extra = ""
        if ss.get("evidence"):
            extra = f" [{ss['evidence'][:50]}]"
        if ss.get("selected_route"):
            extra += f" [route: {ss['selected_route']}]"
        lines.append(f"  {status:15s} {sid}{extra}")

    return "\n".join(lines)


def fmt_list(states: list[dict[str, Any]], available: list[str] | None = None, as_json: bool = False) -> str:
    """Format --list output."""
    if as_json:
        data = {
            "active": [
                {
                    "workflow_id": s.get("workflow_id"),
                    "workflow": s.get("workflow"),
                    "task_id": s.get("task_id"),
                    "started": s.get("started"),
                    "current_step": s.get("current_step"),
                    "paused": s.get("paused", False),
                }
                for s in states
            ],
        }
        if available is not None:
            data["available"] = available
        return json.dumps(data, indent=2)

    lines: list[str] = []
    if states:
        lines.append("Active workflows:")
        for s in states:
            task_str = f" [Task {s.get('task_id')}]" if s.get("task_id") else ""
            current = s.get("current_step", "none")
            paused_str = " [PAUSED]" if s.get("paused") else ""
            lines.append(f"  {s.get('workflow_id')} -- {s.get('workflow')}{task_str} (current: {current}){paused_str}")
    else:
        lines.append("No active workflows.")

    if available is not None:
        lines.append("")
        lines.append("Available definitions:")
        for name in available:
            lines.append(f"  {name}")

    return "\n".join(lines)


def fmt_handoff_context(states: list[dict[str, Any]]) -> str:
    """Format workflow state as text block for session handoff (F9)."""
    if not states:
        return ""

    blocks: list[str] = []
    for state in states:
        wf_name = state.get("workflow", "")
        wf_id = state.get("workflow_id", "")
        task_id = state.get("task_id")
        current = state.get("current_step", "none")
        steps = state.get("steps", {})
        paused = state.get("paused", False)

        total = len(steps)
        done = sum(1 for s in steps.values() if s.get("status") in TERMINAL_STEP_STATUSES)

        task_str = f" [Task {task_id}]" if task_id else ""
        paused_str = " [PAUSED]" if paused else ""

        # Find current step instruction from def (best-effort)
        current_instruction = ""
        yaml_path = discover_workflow_yaml(wf_name)
        if yaml_path:
            try:
                wf_def = load_workflow_yaml(yaml_path)
                step_def = _get_step_def(wf_def, current)
                if step_def:
                    variables = state.get("variables", {})
                    current_instruction = _resolve_vars(step_def.get("instruction", ""), variables)
            except SchemaError:
                pass

        lines = [
            f"WORKFLOW: {wf_name}{task_str} (id: {wf_id}){paused_str}",
            f"PROGRESS: {done}/{total} steps done",
            f"CURRENT STEP: {current}",
        ]
        if current_instruction:
            lines.append(f"INSTRUCTION: {current_instruction}")

        # Last 3 step evidences
        evidences: list[tuple[str, str, str]] = []
        for sid, ss in steps.items():
            ev = ss.get("evidence", "")
            ts = ss.get("completed_at", "")
            if ev and ts:
                evidences.append((ts, sid, ev))
        evidences.sort(key=lambda x: x[0], reverse=True)
        if evidences:
            lines.append("RECENT EVIDENCE:")
            for _ts, sid, ev in evidences[:3]:
                lines.append(f"  {sid}: {ev[:120]}")

        blocks.append("\n".join(lines))

    return "\n---\n".join(blocks)


def fmt_boot_context(states: list[dict[str, Any]]) -> str:
    """Format compact resume block for all active workflows at boot (F11)."""
    if not states:
        return ""

    blocks: list[str] = []
    for state in states:
        wf_name = state.get("workflow", "")
        wf_id = state.get("workflow_id", "")
        task_id = state.get("task_id")
        current = state.get("current_step", "none")
        started = state.get("started", "")
        steps = state.get("steps", {})
        paused = state.get("paused", False)

        total = len(steps)
        done = sum(1 for s in steps.values() if s.get("status") in TERMINAL_STEP_STATUSES)

        task_str = f" [Task {task_id}]" if task_id else ""
        paused_str = " [PAUSED]" if paused else ""

        # Resolve current step instruction
        current_instruction = ""
        yaml_path = discover_workflow_yaml(wf_name)
        if yaml_path:
            try:
                wf_def = load_workflow_yaml(yaml_path)
                step_def = _get_step_def(wf_def, current)
                if step_def:
                    variables = state.get("variables", {})
                    current_instruction = _resolve_vars(step_def.get("instruction", ""), variables)
            except SchemaError:
                pass

        # state-file path (if known) — boot.md WORKFLOW-RESUME uses this
        # to read the inhaltliche Stand without searching docs/<workflow>/
        variables = state.get("variables", {})
        state_file = variables.get("state_file", "")
        state_file_str = f" | state_file: {state_file}" if state_file else ""

        # workflow-level route (top-level routes activated at --start)
        # Distinct from per-step selected_route (mid-flow classification).
        wf_route = state.get("selected_route", "")
        route_str = f" | route: {wf_route}" if wf_route else ""

        line = (
            f"WF: {wf_name}{task_str} | step: {current} ({done}/{total})"
            f"{route_str}"
            f" | {current_instruction[:80]}"
            f"{state_file_str}"
            f" | since: {started[:16]}"
            f" | id: {wf_id}{paused_str}"
        )
        blocks.append(line)

    return "\n".join(blocks)


# ---------------------------------------------------------------------------
# Finding the right active workflow for --next
# ---------------------------------------------------------------------------

def find_active_workflow_for_next(
    workflow_id: str | None,
) -> dict[str, Any] | None:
    """Find the right workflow state for --next. Prefers child workflows."""
    states = list_active_states()
    if not states:
        return None

    if workflow_id:
        for s in states:
            if s.get("workflow_id") == workflow_id:
                return s
        return None

    # Find innermost child (no other workflow has this as parent)
    parent_ids = {s.get("parent_workflow_id") for s in states if s.get("parent_workflow_id")}
    # Workflows that are NOT parents of any other workflow
    leaves = [s for s in states if s.get("workflow_id") not in parent_ids]
    if leaves:
        # Prefer most recently started
        leaves.sort(key=lambda s: s.get("started", ""), reverse=True)
        return leaves[0]
    # Fallback: most recent
    states.sort(key=lambda s: s.get("started", ""), reverse=True)
    return states[0]


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="BuddyAI Workflow Engine",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--start", metavar="WORKFLOW", help="Start a new workflow")
    group.add_argument("--next", action="store_true", help="Show next step")
    group.add_argument("--complete", metavar="STEP_ID", help="Complete a step")
    group.add_argument("--skip", metavar="STEP_ID", help="Skip a step")
    group.add_argument("--retry", metavar="STEP_ID",
                        help="Reset a terminal step back to pending (Item 7 — re-iteration-block)")
    group.add_argument("--status", action="store_true", help="Show workflow status")
    group.add_argument("--list", action="store_true", dest="list_cmd", help="List workflows")
    group.add_argument("--validate", action="store_true", help="Validate consistency")
    group.add_argument("--recover", action="store_true", help="Recover in-progress steps")
    group.add_argument("--abort", metavar="WORKFLOW_ID", help="Abort a workflow")
    group.add_argument("--pause", action="store_true", help="Pause active workflow")
    group.add_argument("--resume", action="store_true", help="Resume paused workflow")
    group.add_argument("--handoff-context", action="store_true", dest="handoff_context",
                        help="Output workflow state for session handoff")
    group.add_argument("--boot-context", action="store_true", dest="boot_context",
                        help="Output compact resume block for boot")
    group.add_argument("--find", action="store_true", help="Find workflow ID by task")
    group.add_argument("--guard", metavar="GUARD_NAME", help="Evaluate a named guard")

    # Shared options
    parser.add_argument("--task", type=str, default=None, help="Task ID")
    parser.add_argument("--id", type=str, default=None, dest="wf_id", help="Workflow ID")
    parser.add_argument("--parent", type=str, default=None, help="Parent workflow ID")
    parser.add_argument("--brief", action="store_true", help="Brief output for hooks")
    parser.add_argument("--route", type=str, default=None, help="Route key for classification")
    parser.add_argument("--evidence", type=str, default=None, help="Evidence text")
    parser.add_argument("--force", action="store_true", help="Force complete (skip checks)")
    parser.add_argument("--set", nargs=2, action="append", metavar=("KEY", "VALUE"),
                        default=None, help="Set state variable")
    parser.add_argument("--reason", type=str, default=None, help="Reason for skip/abort")
    parser.add_argument("--format", type=str, default=None, dest="fmt", help="Output format")
    parser.add_argument("--available", action="store_true", help="Include available definitions")
    parser.add_argument("--before-commit", action="store_true", help="Check commit gates")
    parser.add_argument(
        "--project-root",
        type=str,
        default=None,
        help="Override PROJECT_ROOT (where .workflow-state/ + docs/solve/ + "
             "docs/tasks/ live). Takes precedence over BUDDY_PROJECT_ROOT env-var.",
    )
    # Positional for --guard
    parser.add_argument("guard_args", nargs="*", help=argparse.SUPPRESS)

    args = parser.parse_args()

    # Task 010 Part L0b: explicit --project-root override. Rebinds the
    # project-scoped module globals so that state discovery + completion
    # checks resolve against the new root.
    if args.project_root:
        global PROJECT_ROOT, STATE_DIR, ARCHIVE_DIR, REPO_ROOT
        PROJECT_ROOT = Path(args.project_root).resolve()
        STATE_DIR = PROJECT_ROOT / ".workflow-state"
        ARCHIVE_DIR = STATE_DIR / "archive"
        REPO_ROOT = PROJECT_ROOT  # keep back-compat alias in sync

    # --start
    if args.start:
        cmd_start(args)
    elif args.next:
        cmd_next(args)
    elif args.complete:
        cmd_complete(args)
    elif args.skip:
        cmd_skip(args)
    elif args.retry:
        cmd_retry(args)
    elif args.status:
        cmd_status(args)
    elif args.list_cmd:
        cmd_list(args)
    elif args.validate:
        cmd_validate(args)
    elif args.recover:
        cmd_recover(args)
    elif args.abort:
        cmd_abort(args)
    elif args.pause:
        cmd_pause(args)
    elif args.resume:
        cmd_resume(args)
    elif args.handoff_context:
        cmd_handoff_context(args)
    elif args.boot_context:
        cmd_boot_context(args)
    elif args.find:
        cmd_find(args)
    elif args.guard:
        cmd_guard(args)


def cmd_start(args: argparse.Namespace) -> None:
    workflow_name = args.start
    task_id = resolve_task_id(args.task)

    yaml_path = discover_workflow_yaml(workflow_name)
    if not yaml_path:
        avail = list_available_workflows()
        avail_str = ", ".join(avail) if avail else "none"
        print(f"ERROR: Workflow '{workflow_name}' not found. Available: [{avail_str}]", file=sys.stderr)
        sys.exit(EXIT_NOT_FOUND)

    try:
        workflow_def = load_workflow_yaml(yaml_path)
    except SchemaError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(EXIT_SCHEMA_ERROR)

    set_vars = dict(args.set) if args.set else None

    state = create_state(
        workflow_name, workflow_def,
        task_id=task_id,
        parent_workflow_id=args.parent,
        set_vars=set_vars,
        route=args.route,
    )

    # Show first step
    output = fmt_next(state, workflow_def)
    if output:
        print(output)
    else:
        print(f"Workflow '{workflow_name}' started (id: {state['workflow_id']}) — no steps.")


def cmd_next(args: argparse.Namespace) -> None:
    state = find_active_workflow_for_next(args.wf_id)
    if not state:
        # Exit 0 with empty output = no active workflow (spec)
        sys.exit(EXIT_SUCCESS)

    wf_name = state.get("workflow", "")
    yaml_path = discover_workflow_yaml(wf_name)
    if not yaml_path:
        print(f"ERROR: Workflow definition '{wf_name}' not found", file=sys.stderr)
        sys.exit(EXIT_NOT_FOUND)

    try:
        workflow_def = load_workflow_yaml(yaml_path)
    except SchemaError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(EXIT_SCHEMA_ERROR)

    # Advance to next if current is done
    current = state.get("current_step")
    steps = state.get("steps", {})
    if current and steps.get(current, {}).get("status") in TERMINAL_STEP_STATUSES:
        next_id = find_next_step(state, workflow_def)
        if next_id:
            state["current_step"] = next_id
            save_state(state)

    output = fmt_next(state, workflow_def, brief=args.brief)
    if output:
        print(output)


def cmd_complete(args: argparse.Namespace) -> None:
    step_id = args.complete
    wf_id = args.wf_id

    # Find the workflow that contains this step
    state = _find_state_for_step(step_id, wf_id)
    if not state:
        print(f"ERROR: No active workflow contains step '{step_id}'", file=sys.stderr)
        sys.exit(EXIT_NOT_FOUND)

    wf_name = state.get("workflow", "")
    yaml_path = discover_workflow_yaml(wf_name)
    if not yaml_path:
        print(f"ERROR: Workflow definition '{wf_name}' not found", file=sys.stderr)
        sys.exit(EXIT_NOT_FOUND)

    try:
        workflow_def = load_workflow_yaml(yaml_path)
    except SchemaError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(EXIT_SCHEMA_ERROR)

    set_vars = dict(args.set) if args.set else None

    # Task 301 F-ENGINE-001 Fix: lazy-resolve spec_name + state_file VOR
    # complete_step damit pointer_check-Steps mit `{spec_name}` nicht
    # mit "Unresolved variable(s)" blockieren wenn der Workflow ohne
    # vorheriges --next/--status auf --complete gestartet wurde.
    if _ensure_state_variables_resolved(state):
        try:
            save_state(state)
        except OSError as exc:
            print(
                f"WARNING: save_state failed after lazy variable "
                f"resolution: {exc}",
                file=sys.stderr,
            )

    ok, msg = complete_step(
        state, workflow_def, step_id,
        route=args.route,
        evidence=args.evidence,
        force=args.force,
        set_vars=set_vars,
    )
    if ok:
        print(msg)
    else:
        print(f"ERROR: {msg}", file=sys.stderr)
        sys.exit(EXIT_VALIDATION_FAIL)


def cmd_retry(args: argparse.Namespace) -> None:
    step_id = args.retry
    reason = args.reason
    if not reason:
        print("ERROR: --retry requires --reason", file=sys.stderr)
        sys.exit(EXIT_VALIDATION_FAIL)

    state = _find_state_for_step(step_id, args.wf_id)
    if not state:
        print(f"ERROR: No active workflow contains step '{step_id}'", file=sys.stderr)
        sys.exit(EXIT_NOT_FOUND)

    wf_name = state.get("workflow", "")
    yaml_path = discover_workflow_yaml(wf_name)
    if not yaml_path:
        print(f"ERROR: Workflow definition '{wf_name}' not found", file=sys.stderr)
        sys.exit(EXIT_NOT_FOUND)

    try:
        workflow_def = load_workflow_yaml(yaml_path)
    except SchemaError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(EXIT_SCHEMA_ERROR)

    ok, msg = retry_step(state, workflow_def, step_id, reason)
    if ok:
        print(msg)
    else:
        print(f"ERROR: {msg}", file=sys.stderr)
        sys.exit(EXIT_VALIDATION_FAIL)


def cmd_skip(args: argparse.Namespace) -> None:
    step_id = args.skip
    reason = args.reason
    if not reason:
        print("ERROR: --skip requires --reason", file=sys.stderr)
        sys.exit(EXIT_VALIDATION_FAIL)

    state = _find_state_for_step(step_id, args.wf_id)
    if not state:
        print(f"ERROR: No active workflow contains step '{step_id}'", file=sys.stderr)
        sys.exit(EXIT_NOT_FOUND)

    wf_name = state.get("workflow", "")
    yaml_path = discover_workflow_yaml(wf_name)
    if not yaml_path:
        print(f"ERROR: Workflow definition '{wf_name}' not found", file=sys.stderr)
        sys.exit(EXIT_NOT_FOUND)

    try:
        workflow_def = load_workflow_yaml(yaml_path)
    except SchemaError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(EXIT_SCHEMA_ERROR)

    ok, msg = skip_step(state, workflow_def, step_id, reason)
    if ok:
        print(msg)
    else:
        print(f"ERROR: {msg}", file=sys.stderr)
        sys.exit(EXIT_VALIDATION_FAIL)


def cmd_status(args: argparse.Namespace) -> None:
    if args.wf_id:
        state = load_state(args.wf_id)
        print(fmt_status(state))
    else:
        states = list_active_states()
        if not states:
            print("No active workflows.")
            return
        for s in states:
            print(fmt_status(s))
            print()


def cmd_list(args: argparse.Namespace) -> None:
    states = list_active_states()
    available = list_available_workflows() if args.available else None
    as_json = args.fmt == "json"
    print(fmt_list(states, available=available, as_json=as_json))


def cmd_validate(args: argparse.Namespace) -> None:
    states = list_active_states()

    if args.before_commit:
        errors = validate_commit_gates(states)
        if errors:
            for e in errors:
                print(f"FAIL: {e}", file=sys.stderr)
            sys.exit(EXIT_VALIDATION_FAIL)
        print("PASS: All commit gates satisfied.")
        sys.exit(EXIT_SUCCESS)

    # General validation: check all active workflows
    if not states:
        print("No active workflows.")
        sys.exit(EXIT_SUCCESS)

    all_ok = True
    for state in states:
        wf_name = state.get("workflow", "")
        yaml_path = discover_workflow_yaml(wf_name)
        if not yaml_path:
            print(f"WARN: Definition for '{wf_name}' not found", file=sys.stderr)
            continue
        try:
            load_workflow_yaml(yaml_path)
        except SchemaError as e:
            print(f"FAIL: {e}", file=sys.stderr)
            all_ok = False

    if all_ok:
        print("PASS: All workflows valid.")
    sys.exit(EXIT_SUCCESS if all_ok else EXIT_VALIDATION_FAIL)


def cmd_recover(args: argparse.Namespace) -> None:
    if args.wf_id:
        state = load_state(args.wf_id)
        states = [state]
    else:
        states = list_active_states()

    if not states:
        print("No active workflows to recover.")
        return

    total_recovered: list[str] = []
    for state in states:
        wf_name = state.get("workflow", "")
        yaml_path = discover_workflow_yaml(wf_name)
        if not yaml_path:
            continue
        try:
            workflow_def = load_workflow_yaml(yaml_path)
        except SchemaError:
            continue
        recovered = recover_workflow(state, workflow_def)
        for sid in recovered:
            total_recovered.append(f"{state.get('workflow_id')}: {sid}")

    if total_recovered:
        print(f"Recovered {len(total_recovered)} step(s):")
        for r in total_recovered:
            print(f"  {r}")
    else:
        print("No steps recovered.")


def cmd_abort(args: argparse.Namespace) -> None:
    def _abort_closeout_best_effort(state: dict[str, Any], reason: str) -> list[str]:
        """Best-effort closeout before abort archive.

        Keeps abort pragmatic and non-blocking: normalize any in-progress steps
        to skipped, and finalize common closeout markers when present.
        """
        steps = state.get("steps", {})
        if not isinstance(steps, dict):
            return []

        now = _utcnow()
        touched: list[str] = []

        # Never leave in-progress steps dangling in an archived abort-state.
        for sid, ss in steps.items():
            if not isinstance(ss, dict):
                continue
            if ss.get("status") == STATUS_IN_PROGRESS:
                ss["status"] = STATUS_SKIPPED
                ss["skipped_reason"] = f"abort: {reason}"
                ss["completed_at"] = now
                touched.append(sid)

        # Minimal closeout marker to reduce engine/task drift during abort flows.
        phase_done = steps.get("phase-done")
        if isinstance(phase_done, dict) and phase_done.get("status") == STATUS_PENDING:
            phase_done["status"] = STATUS_COMPLETE
            phase_done["completed_at"] = now
            phase_done["evidence"] = "abort-closeout"
            touched.append("phase-done")

        # Abort must not implicitly mark task done.
        task_done = steps.get("task-status-done")
        if isinstance(task_done, dict) and task_done.get("status") == STATUS_PENDING:
            task_done["status"] = STATUS_SKIPPED
            task_done["skipped_reason"] = "abort-closeout: task status not finalized"
            task_done["completed_at"] = now
            touched.append("task-status-done")

        state["current_step"] = None
        state["closeout_on_abort"] = {
            "completed_at": now,
            "touched_steps": touched,
        }
        return touched

    wf_id = args.abort
    reason = args.reason
    if not reason:
        print("ERROR: --abort requires --reason", file=sys.stderr)
        sys.exit(EXIT_VALIDATION_FAIL)

    state = load_state(wf_id)
    touched_steps = _abort_closeout_best_effort(state, reason)
    state["aborted"] = _utcnow()
    state["abort_reason"] = reason
    save_state(state)
    archive_state(wf_id)
    touched_info = f" (closeout: {len(touched_steps)} step(s))" if touched_steps else ""
    print(f"Workflow '{wf_id}' aborted: {reason}{touched_info}")


def cmd_pause(args: argparse.Namespace) -> None:
    """Pause the active workflow (F4)."""
    state = find_active_workflow_for_next(args.wf_id)
    if not state:
        print("ERROR: No active workflow to pause.", file=sys.stderr)
        sys.exit(EXIT_NOT_FOUND)

    if state.get("paused"):
        print(f"Workflow '{state['workflow_id']}' is already paused.")
        return

    state["paused"] = True
    state["paused_at"] = _utcnow()
    save_state(state)
    print(f"Workflow '{state['workflow_id']}' paused.")


def cmd_resume(args: argparse.Namespace) -> None:
    """Resume a paused workflow (F4).

    Uses dedicated paused-workflow lookup instead of find_active_workflow_for_next,
    which prefers leaf workflows regardless of paused status (F-CQ-001 fix).
    """
    if args.wf_id:
        # Explicit --id: load directly and check paused flag
        state = load_state(args.wf_id)
        if not state.get("paused"):
            print(f"Workflow '{state['workflow_id']}' is not paused.")
            return
    else:
        # No --id: find all paused workflows among active states
        states = list_active_states()
        paused_states = [s for s in states if s.get("paused")]
        if len(paused_states) == 0:
            print("ERROR: No paused workflow to resume.", file=sys.stderr)
            sys.exit(EXIT_NOT_FOUND)
        if len(paused_states) > 1:
            ids = ", ".join(s["workflow_id"] for s in paused_states)
            print(
                f"ERROR: Multiple paused workflows: {ids}. Use --resume --id <workflow-id>.",
                file=sys.stderr,
            )
            sys.exit(EXIT_VALIDATION_FAIL)
        state = paused_states[0]

    state["paused"] = False
    state.pop("paused_at", None)
    save_state(state)
    print(f"Workflow '{state['workflow_id']}' resumed.")


def cmd_handoff_context(_args: argparse.Namespace) -> None:
    """Output workflow state for session handoff (F9)."""
    states = list_active_states()
    output = fmt_handoff_context(states)
    if output:
        print(output)


def cmd_boot_context(_args: argparse.Namespace) -> None:
    """Output compact resume block for boot (F11)."""
    states = list_active_states()
    output = fmt_boot_context(states)
    if output:
        print(output)


def cmd_find(args: argparse.Namespace) -> None:
    """Find workflow ID by task (F12)."""
    if not args.task:
        print("ERROR: --find requires --task", file=sys.stderr)
        sys.exit(EXIT_VALIDATION_FAIL)

    task_id = resolve_task_id(args.task)
    if task_id is None:
        print(f"ERROR: Invalid task ID: {args.task}", file=sys.stderr)
        sys.exit(EXIT_VALIDATION_FAIL)

    states = list_active_states()
    for state in states:
        if state.get("task_id") == task_id:
            print(state["workflow_id"])
            return

    print(f"ERROR: No active workflow for task {task_id}", file=sys.stderr)
    sys.exit(EXIT_NOT_FOUND)


def cmd_guard(args: argparse.Namespace) -> None:
    guard_name = args.guard
    # guard_args may contain task_id
    task_id = args.guard_args[0] if args.guard_args else args.task

    # Named guards — extend as needed
    # For now, exit 1 (skip) for unknown guards
    if guard_name == "council-needed":
        # Heuristic: skip council for now (no implementation yet)
        sys.exit(1)
    elif guard_name == "delta-needed":
        sys.exit(1)
    elif guard_name == "task-yaml-ok":
        # Check if task YAML exists
        if task_id:
            tid = resolve_task_id(task_id)
            if tid:
                task_path = PROJECT_ROOT / "docs" / "tasks" / f"{tid:03d}.yaml"
                if task_path.exists():
                    sys.exit(EXIT_SUCCESS)
        sys.exit(EXIT_VALIDATION_FAIL)
    else:
        print(f"Unknown guard: {guard_name}", file=sys.stderr)
        sys.exit(EXIT_VALIDATION_FAIL)


def _find_state_for_step(step_id: str, wf_id: str | None = None) -> dict[str, Any] | None:
    """Find active state containing the given step."""
    if wf_id:
        state = load_state(wf_id)
        if step_id in state.get("steps", {}):
            return state
        return None

    for state in list_active_states():
        if step_id in state.get("steps", {}):
            return state
    return None


if __name__ == "__main__":
    main()
