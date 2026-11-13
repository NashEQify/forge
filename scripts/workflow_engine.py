#!/usr/bin/env python3
"""
workflow_engine.py — Workflow Engine for forge.

YAML-driven workflow orchestration: reads definitions, tracks state,
tells the LLM what step comes next.

Engine shape SoT: framework/workflow-engine-cookbook.md

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

Exit Codes: 0=success, 1=validation-fail, 2=not-found, 3=schema-error,
            4=corrupt-state, 5=ambiguous (>=2 active workflows, no --id/--task),
            6=guard-evaluation-error, 7=stale-state (reload and retry)
"""

from __future__ import annotations

import argparse
import contextlib
import copy
import fnmatch
import hashlib
import json
import os
import re
import subprocess  # noqa: F401 — retained interception seam for observational regression tests
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from uuid import uuid4

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
    VALID_COMPLETION_TYPES,
    VALID_GUARD_TYPES,
    discover_workflow_yaml,
    list_available_workflows,
    load_workflow_yaml,
    resolve_task_id,
)


from scripts.lib.evidence_pointers import _FENCE_RE  # noqa: E402
from scripts.lib.review_adoption import (  # noqa: E402
    OPTION_FIELDS, POLICIES, ReviewEvaluationError, ReviewRefusal,
    capture_subject, check_adoption, check_exclusion_prefixes, qualify_decision, validate_adoption_options,
)


# ---------------------------------------------------------------------------
# Path resolution
# ---------------------------------------------------------------------------
#
# PROJECT_ROOT   → where the active project's data lives: .workflow-state/,
#                  docs/tasks/, docs/<workflow>/ (solve/build/fix/review/
#                  research/docs-rewrite — see STATE_FILE_DIRS), and any
#                  workflow-step artefacts referenced by completion checks /
#                  guards. Derived from BUDDY_PROJECT_ROOT env-var,
#                  --project-root flag, or Path.cwd() (e.g.
#                  ~/projects/<consumer>).
#
# FRAMEWORK_ROOT → where workflow_engine.py itself lives. Reserved for
#                  framework-internal reads (currently none directly —
#                  workflow YAML discovery is delegated to
#                  scripts.lib.yaml_loader which resolves against its own
#                  FRAMEWORK_ROOT constant).
#
# REPO_ROOT      → back-compat alias mirroring PROJECT_ROOT. Kept so existing
#                  callers / tests that reference `scripts.workflow_engine
#                  .REPO_ROOT` keep working.
#
# When PROJECT_ROOT and FRAMEWORK_ROOT coincide (session running directly
# inside the framework repo without BUDDY_PROJECT_ROOT set), state files
# land under the framework's own docs/ tree.

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
EXIT_AMBIGUOUS = 5  # >=2 active workflows match and no --id/--task narrows to one
EXIT_GUARD_ERROR = 6
EXIT_STALE_STATE = 7


class GuardEvaluationError(Exception):
    """A guard could not be evaluated; the step must not advance."""


class CompletionEvaluationError(Exception):
    """A completion check could not run; on_fail does not apply."""


class StaleStateError(RuntimeError):
    """A transition used an outdated snapshot; reload before retrying."""

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

# Default iteration-cap per step (Item 7 + Item 13); workflow.yaml top-level
# `iteration_cap: <int>` changes it. The cap counts review rounds: every --retry
# counts except a `capture-correction:` retry before any producer output was
# adopted. Crossing it takes `override:` / `override-rationale:`; on the code
# board step it takes `at-the-cap: <verdict path>` instead, a record with a
# non-empty `remaining_findings` list (skills/convergence_loop/at-the-cap.md).
DEFAULT_ITERATION_CAP = 3
CODE_REVIEW_BOARD_SKILL = "skills/code_review_board/SKILL.md"
_CAPTURE_CORRECTION_RE = re.compile(r"^capture-correction:\s*\S", re.IGNORECASE)
_AT_THE_CAP_RE = re.compile(r"at-the-cap:\s*(\S+)", re.IGNORECASE)


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


def _parse_utc_safe(ts: Any) -> datetime | None:
    """Parse a UTC timestamp, returning None on missing/malformed (no raise)."""
    if not isinstance(ts, str):
        return None
    try:
        return _parse_utc(ts)
    except ValueError:
        return None


def _last_activity(state: dict[str, Any]) -> datetime | None:
    """Most recent timestamp across `started` + every step's started_at /
    completed_at — the last recorded step *transition* (for --reap staleness).

    NOT a liveness heartbeat: a step merely sitting `in_progress` refreshes
    nothing, so a workflow parked on one long step ages like an abandoned one.
    --reap therefore only ARCHIVES (reversible), never deletes.
    """
    stamps: list[datetime] = []
    t = _parse_utc_safe(state.get("started"))
    if t:
        stamps.append(t)
    for ss in state.get("steps", {}).values():
        if not isinstance(ss, dict):
            continue
        for key in ("started_at", "completed_at"):
            t = _parse_utc_safe(ss.get(key))
            if t:
                stamps.append(t)
    return max(stamps) if stamps else None


def _generate_workflow_id(workflow_name: str, task_id: int | None) -> str:
    """Keep a readable prefix while giving every run an independent identity."""
    ts = datetime.now(UTC).strftime("%Y%m%dT%H%M")
    parts = [workflow_name]
    if task_id is not None:
        parts.append(str(task_id))
    parts.append(ts)
    parts.append(uuid4().hex)
    return "-".join(parts)


def _state_path(workflow_id: str) -> Path:
    return STATE_DIR / f"{workflow_id}.json"


def _capture_check_view(path, details, *, errors="replace"):
    raw = path.read_bytes()
    details.setdefault('checked_input', []).append({'kind': 'file', 'path': str(path.relative_to(PROJECT_ROOT)), 'identity': {'sha256': hashlib.sha256(raw).hexdigest()}})
    return raw.decode('utf-8', errors=errors)


def _record_component(checks, comp, path, result, reason, *, details=None, producer=None, executed=True):
    """Append one receipt check to the caller's local list; ``None`` records nothing."""
    if checks is None:
        return
    details = details or {}
    ctype = comp.get('type', 'manual')
    entry = {'check': path, 'type': ctype, 'result': result,
             'producer': producer or ('agent' if ctype == 'manual' else 'checker'),
             'input': copy.deepcopy(details.get('checked_input', [])),
             'detail': str(reason or result)[:300]}
    if executed and (details.get('limits') or not details.get('checked_input')):
        entry['partial'] = True
    checks.append(entry)


def _unevaluated(checks, comp, path, producer='checker'):
    if comp.get('type') == 'compound':
        for i, sub in enumerate(comp['checks']):
            _unevaluated(checks, sub, path + '.' + str(i), producer)
    else:
        reason = 'Not evaluated: permitted force' if producer == 'forced' else 'Not evaluated'
        _record_component(checks, comp, path, 'not_evaluated', reason, producer=producer, executed=False)


def _evaluate_completion(comp, state, step_state, checks=None, path='completion', validated=False):
    """Evaluate a completion tree; ``checks`` collects receipt entries named by ``path``."""
    raw = comp
    resolved = _resolve_completion_vars(comp, state.get('variables', {}))
    if not validated:
        try:
            _validate_completion_inputs(resolved, _path=path)
        except (CompletionEvaluationError, OSError, ValueError, TypeError) as exc:
            origin = getattr(exc, '_completion_input', {})
            failing = origin.get('definition', resolved)
            failing_path = origin.get('path', path)
            _record_component(checks, failing, failing_path + '.input', 'unknown', str(exc))
            _unevaluated(checks, resolved, path)
            raise
    ctype = resolved.get('type', 'manual')
    if ctype == 'compound':
        messages = []
        for i, child in enumerate(raw['checks']):
            try:
                ok, msg = _evaluate_completion(child, state, step_state, checks, path + '.' + str(i), True)
            except BaseException:
                for j, later in enumerate(raw['checks'][i+1:], i+1):
                    _unevaluated(checks, _resolve_completion_vars(later, state.get('variables', {})), path + '.' + str(j))
                raise
            messages.append(msg)
            if not ok:
                for j, later in enumerate(raw['checks'][i+1:], i+1):
                    _unevaluated(checks, _resolve_completion_vars(later, state.get('variables', {})), path + '.' + str(j))
                return False, f'compound check [{i}] failed: {msg}'
        return True, 'all compound checks passed (' + '; '.join(messages) + ')'
    details = {}
    try:
        ok, msg = _evaluate_leaf(resolved, state, step_state, details)
    except BaseException as exc:
        _record_component(checks, resolved, path, 'unknown', str(exc), details=details)
        raise
    producer = details.pop('producer', None)
    result = 'not_evaluated' if producer == 'legacy' else 'passed' if ok else 'failed'
    _record_component(checks, resolved, path, result, msg, details=details, producer=producer)
    return ok, msg


def _typed_completion_method(checks, force=False):
    if force:
        return 'forced'
    producers = {c['producer'] for c in checks}
    if 'agent' in producers:
        return 'agent-confirmed'
    if 'legacy' in producers:
        return 'legacy-unverified'
    return 'verified'


def _receipt(operation, step_state, checks):
    """One plain run receipt for a transition, written in the same save."""
    return {'operation': operation, 'at': _utcnow(), 'iteration': step_state.get('iterations', 1),
            'checks': checks}


def _receipt_summary(checks):
    return ', '.join(f"{c['check']}={c['result']}/{c['producer']}" for c in checks)


def _refusal_checks(checks):
    evaluated = [c for c in checks if c['result'] != 'not_evaluated']
    return '; checks: ' + _receipt_summary(evaluated) if evaluated else ''


def _review_owner(workflow_id: str, step_id: str, *, mutate: bool = False) -> tuple[dict[str, Any], dict[str, Any]]:
    """Read one exact owner, including retained archives only for observation."""
    if not isinstance(workflow_id, str) or not re.fullmatch(r"[A-Za-z0-9_-]+", workflow_id):
        raise CompletionEvaluationError("Review operation requires an exact --id workflow")
    if not isinstance(step_id, str) or not step_id.strip():
        raise CompletionEvaluationError("Review operation requires an exact owner step")
    paths = [path for path in (_state_path(workflow_id), ARCHIVE_DIR / f"{workflow_id}.json") if path.exists()]
    if not paths:
        raise CompletionEvaluationError("Review owner state missing")
    records = []
    for path in paths:
        try:
            records.append(json.loads(path.read_text(encoding="utf-8")))
        except (OSError, ValueError) as exc:
            raise CompletionEvaluationError(f"Unreadable review owner state: {exc}") from exc
    if any(record != records[0] for record in records[1:]):
        raise CompletionEvaluationError("Conflicting active/archive review owner state")
    state = records[0]
    if not isinstance(state, dict) or state.get("workflow_id") != workflow_id:
        raise CompletionEvaluationError("Invalid review owner identity")
    step = state.get("steps", {}).get(step_id)
    if not isinstance(step, dict):
        raise CompletionEvaluationError("Exact review owner step missing")
    if mutate and (any(path.parent == ARCHIVE_DIR for path in paths) or state.get("paused") or state.get("aborted") or state.get("completed")):
        raise CompletionEvaluationError("Review owner workflow is not live/mutable")
    iteration = step.get("iterations", 1)
    if type(iteration) is not int or iteration < 1:
        raise CompletionEvaluationError("Invalid existing owner iteration")
    return state, step


def _review_capture_record(state: dict[str, Any], step: dict[str, Any], step_id: str) -> dict[str, Any]:
    record = step.get("review")
    if not isinstance(record, dict):
        raise ReviewRefusal("No captured review on exact owner")
    if (record.get("owner") != {"workflow_id": state["workflow_id"], "step_id": step_id}
            or record.get("iteration") != step.get("iterations", 1)):
        raise ReviewRefusal("Review owner/iteration mismatch; retry and capture")
    if not all(key in record for key in ("request", "subject", "review_run_id", "review_subject_digest")):
        raise CompletionEvaluationError("Malformed retained review capture")
    return record


def _review_input(record: dict[str, Any], policy: str) -> dict[str, Any]:
    """Identity of the retained review a check read: run, subject and decision bytes.

    Also how much its adoption verified (quotes and the diagnostics count), when retained.
    """
    adoption = record.get("adoption")
    entry: dict[str, Any] = {"kind": "review", "owner": copy.deepcopy(record.get("owner"))}
    if isinstance(adoption, dict):
        diagnostics = adoption.get("diagnostics")
        entry.update(iteration=record.get("iteration"), review_run_id=record.get("review_run_id"),
                     review_subject_digest=record.get("review_subject_digest"),
                     decision=adoption.get("decision"), decision_sha256=adoption.get("sha256"),
                     quotes_verified=adoption.get("quotes_verified"),
                     diagnostics=len(diagnostics) if isinstance(diagnostics, list) else None)
    else:
        entry["review_run_id"] = record.get("review_run_id")
    entry["policy"] = policy
    return {key: value for key, value in entry.items() if value is not None}


def _review_current(workflow_id: str, step_id: str, policy: str, *, source: str | None = None, observed=None, owner=None) -> tuple[bool, str]:
    state, step = owner if owner is not None else _review_owner(workflow_id, step_id)
    try:
        record = _review_capture_record(state, step, step_id)
        if observed is not None:
            observed['checked_input'] = [_review_input(record, policy)]
            observed['limits'] = ['Review requalification reads transitive subject/report inputs; identity coverage is partial']
        result = check_adoption(PROJECT_ROOT, record, record.get("adoption"), policy, configured_source=source)
        return result.permitted, result.message
    except ReviewRefusal as exc:
        return False, str(exc)
    except (ReviewEvaluationError, KeyError) as exc:
        raise CompletionEvaluationError(f"Review evaluation error: {exc}") from exc


def cmd_review(args: argparse.Namespace) -> None:
    step_id = args.review_capture or args.review_adopt or args.review_check
    mutate = bool(args.review_capture or args.review_adopt)
    state, step = _review_owner(args.wf_id, step_id, mutate=mutate)
    try:
        if not mutate:
            if args.review_policy not in POLICIES:
                raise CompletionEvaluationError("--review-check requires --review-policy")
            details: dict[str, Any] = {}
            try:
                ok, message = _review_current(args.wf_id, step_id, args.review_policy, observed=details, owner=(state, step))
                outcome = 'passed' if ok else 'failed'
            except CompletionEvaluationError as exc:
                ok, message, outcome = False, str(exc), 'unknown'
            payload = {'retention': 'not_persisted', 'owner': {'workflow_id': args.wf_id, 'step_id': step_id},
                       'policy': args.review_policy, 'result': outcome, 'reason': message,
                       'input': details.get('checked_input', [])}
            if getattr(args, 'fmt', None) == 'json':
                print(json.dumps(payload))
            else:
                print(message + '; retention: not_persisted; receipt=' + json.dumps(payload))
            if not ok:
                raise ReviewRefusal(message)
            return
        if step.get("status") not in {STATUS_IN_PROGRESS, STATUS_COMPLETE}:
            raise ReviewRefusal("Review owner must be in_progress or retained complete")
        if args.review_capture:
            request = json.load(sys.stdin)
            normalized, subject, digest = capture_subject(PROJECT_ROOT, request)
            # Capture only, before any state is written: an exclusion prefix must name a directory.
            check_exclusion_prefixes(PROJECT_ROOT, request)
            if step.get("review") is None:
                if step.get("status") != STATUS_IN_PROGRESS:
                    raise ReviewRefusal("Initial capture requires in_progress owner; cannot backfill completed dispatch")
                record = {"schema_version": 1, "owner": {"workflow_id": args.wf_id, "step_id": step_id},
                          "iteration": step.get("iterations", 1), "review_run_id": uuid4().hex,
                          "review_subject_digest": digest, "request": normalized, "subject": subject,
                          "adoption_history": []}
            else:
                # Same subject keeps run and iteration; a changed request replaces the old one
                # and retires the current adoption into history.
                record = copy.deepcopy(_review_capture_record(state, step, step_id))
                if record["subject"] != subject or record["review_subject_digest"] != digest:
                    raise ReviewRefusal("Subject changed; retry before fresh capture")
                if record["request"] != normalized:
                    if adoption := record.pop("adoption", None):
                        record.setdefault("adoption_history", []).append(adoption)
                    record["request"] = normalized
            if step.get("review") != record:
                step["review"] = record
                save_state(state)
            envelope = {key: record[key] for key in ("schema_version", "owner", "iteration", "review_run_id", "review_subject_digest")}
            print(json.dumps(envelope))
            return
        if not args.verdict:
            raise CompletionEvaluationError("--review-adopt requires --verdict")
        record = _review_capture_record(state, step, step_id)
        adoption = qualify_decision(PROJECT_ROOT, record, args.verdict)
        previous = record.get("adoption")
        if previous == adoption:
            print(f"Review adoption unchanged: {adoption['decision']} sha256={adoption['sha256']} (identical decision already adopted)")
            return
        if previous:
            record.setdefault("adoption_history", []).append(previous)
        record["adoption"] = adoption
        save_state(state)
        if previous:
            print(f"Review adoption replaced: {previous.get('decision')} sha256={previous.get('sha256')} moved to adoption_history")
        print(f"Review adopted: {adoption['decision']} sha256={adoption['sha256']} (current evidence; success policy checked separately); "
              f"quotes verified: {adoption['quotes_verified']}")
        for diagnostic in adoption["diagnostics"]:
            print(f"diagnostic: {diagnostic}")
    except (ReviewRefusal, ReviewEvaluationError, KeyError) as exc:
        raise CompletionEvaluationError(f"Review {'refused' if isinstance(exc, ReviewRefusal) else 'evaluation error'}: {exc}") from exc


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


def _load_state_quiet(workflow_id: str) -> dict[str, Any] | None:
    """Load a state file, returning None on missing/corrupt (never exits/raises).

    Used by --reap to re-read a candidate fresh before archiving, without the
    sys.exit semantics of load_state.
    """
    path = _state_path(workflow_id)
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


@contextlib.contextmanager
def _state_lock(directory: Path | None = None):
    """Acquire an exclusive flock on STATE_DIR/_lock for atomic state ops.

    Prevents race conditions when boot-context, --next, --complete run
    concurrently against the same .workflow-state/ (e.g. UserPromptSubmit
    hook firing while boot is still parallelising). Unix-only (fcntl).
    """
    if directory is None:
        _ensure_state_dir()
    lock_path = (directory or STATE_DIR) / "_lock"
    fd = os.open(str(lock_path), os.O_CREAT | os.O_RDWR, 0o644)
    try:
        if fcntl is not None:
            fcntl.flock(fd, fcntl.LOCK_EX)
        yield
    finally:
        if fcntl is not None:
            fcntl.flock(fd, fcntl.LOCK_UN)
        os.close(fd)


def save_state(state: dict[str, Any], is_new: bool = False) -> None:
    """Compare revisions and atomically replace state under the same lock.

    Legacy states without a revision start at zero. A successful write updates
    the caller's revision; a stale or archived snapshot raises StaleStateError
    so its caller cannot continue a transition that was never persisted.
    New runs recheck active workflow/task uniqueness under this same lock.
    """
    with _state_lock():
        path = _state_path(state["workflow_id"])
        expected = state.get("revision", 0)
        if type(expected) is not int or expected < 0:
            raise StaleStateError("Invalid state revision; reload and retry")
        if path.exists():
            current = _persisted_revision(path)
            if is_new or current != expected:
                raise StaleStateError(
                    f"Stale workflow '{state['workflow_id']}' (expected revision {expected}, "
                    f"found {current}); reload and retry"
                )
        elif not is_new and (expected != 0 or (ARCHIVE_DIR / path.name).exists()):
            raise StaleStateError(
                f"Stale workflow '{state['workflow_id']}' was removed or archived; reload and retry"
            )
        if is_new and state.get("workflow") is not None:
            # Scan directly: list_active_states would acquire a nested flock.
            for active_path in sorted(STATE_DIR.glob("*.json")):
                try:
                    active = json.loads(active_path.read_text(encoding="utf-8"))
                except (json.JSONDecodeError, OSError) as exc:
                    raise StaleStateError(f"Cannot check active workflow uniqueness: {exc}; reload and retry") from exc
                if not isinstance(active, dict):
                    raise StaleStateError("Invalid active workflow state; repair, reload and retry")
                if (active.get("workflow"), active.get("task_id")) == (state["workflow"], state.get("task_id")):
                    print(
                        f"ERROR: Workflow '{state['workflow']}' with task {state.get('task_id')} "
                        f"already active (id: {active.get('workflow_id')})",
                        file=sys.stderr,
                    )
                    sys.exit(EXIT_VALIDATION_FAIL)
        updated = {**state, "revision": expected + 1}
        tmp_path = path.with_suffix(path.suffix + ".tmp")
        tmp_path.write_text(
            json.dumps(updated, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        os.replace(str(tmp_path), str(path))
        state["revision"] = updated["revision"]


def _persisted_revision(path: Path) -> int:
    """Read a revision while the caller holds the state lock."""
    try:
        stored = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise StaleStateError("Cannot update corrupt state; repair, reload and retry") from exc
    revision = stored.get("revision", 0) if isinstance(stored, dict) else None
    if type(revision) is not int or revision < 0:
        raise StaleStateError("Invalid persisted state revision; repair, reload and retry")
    return revision


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


def archive_state(workflow_id: str, *, expected_revision: int | None = None) -> None:
    """Move state file to archive atomically (os.replace, single-step).

    Legacy IDs may already have an archive entry. A second entry receives a
    timestamp suffix so the prior archived record survives.
    """
    with _state_lock():
        src = _state_path(workflow_id)
        if not src.exists():
            if expected_revision is not None:
                raise StaleStateError(f"Stale workflow '{workflow_id}' is no longer active; reload and retry")
            return
        if expected_revision is not None and _persisted_revision(src) != expected_revision:
            raise StaleStateError(f"Stale workflow '{workflow_id}' changed before archiving; reload and retry")
        dst = ARCHIVE_DIR / src.name
        if dst.exists():
            stamp = _utcnow().replace(":", "").replace("-", "")
            dst = ARCHIVE_DIR / f"{src.stem}.{stamp}{src.suffix}"
        os.replace(str(src), str(dst))


# ---------------------------------------------------------------------------
# Template Variable Resolution
# ---------------------------------------------------------------------------

def _resolve_vars(text: str, variables: dict[str, Any]) -> str:
    """Replace {var_name} placeholders with values from variables dict.

    empty-string-Resolution wird wie None/missing
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
        # empty-string wird wie missing behandelt
        if s == "":
            return m.group(0)
        return s
    return re.sub(r"\{([A-Za-z_]\w*)\}", replacer, text)


def _has_unresolved_vars(text: str) -> list[str]:
    """Return list of unresolved {var_name} placeholders in text.

    variables-Dict-Lookup
    geschieht via `_resolve_completion_vars()` VOR diesem Aufruf, das die
    Variablen im Text ersetzt. Diese Funktion ist die Restpruefung —
    findet die Placeholder die nach Resolution noch im Text stehen.

    Pre-fix hatte ein optional `variables` Argument das im Hot-Path nirgends
    genutzt wurde (dead-code im Hot-Path); ueber 1 Pass entfernt.
    Whitelist-Erweiterung ist semantisch via variables-Dict in
    _resolve_completion_vars (Spec §2.1).
    """
    return re.findall(r"\{([A-Za-z_]\w*)\}", text)


def _ensure_state_variables_resolved(state: dict[str, Any]) -> bool:
    """Lazy-resolve `spec_name` + `state_file` in state["variables"].

    pre-fix war diese Resolution NUR
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

    # lazy spec_name lookup
    if not variables.get("spec_name"):
        try:
            spec_name = _resolve_spec_name(int(task_id))
        except (TypeError, ValueError):
            spec_name = None
        if spec_name:
            variables["spec_name"] = spec_name
            changed = True

    # lazy state_file re-discovery
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


# Spec-slug shape gate for {spec_name}. A `spec_ref` is supposed to be
# a spec PATH (`docs/specs/299-fabrication-mitigation.md`) whose stem is a clean
# slug. But some tasks carry PROSE in `spec_ref` (e.g. "Implements
# PostgresStore at src/.../postgres_store.py:195.") — `Path(prose).stem`
# then yields garbage like `postgres_store.py:195.`. That garbage flowed into
# {spec_name} and the board-spec compound pointer_check globbed a non-existent
# `docs/reviews/board/postgres_store.py:195.-consolidated-pass1.md`, blocking
# the step with a confusing "file not found". Validating the stem here and
# returning None on garbage is the SAFE direction: an unset {spec_name} leaves
# the placeholder literal, and the compound HARD-policy (see `check_completion`,
# ctype=="compound") converts that into a clean "unresolved variable" block. It
# can never cause a false auto-complete.
_SPEC_SLUG_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
# Prose / code-path tells on a RAW `spec_ref` (whitespace/colon/semicolon/comma/
# parens/section-sign). Deliberately EXCLUDES `.` `/` `-` `_` — those are legit
# in spec paths and slugs. Prose detection belongs on the raw string
# (which still carries these tells), not on the post-`Path.stem` slug.
_PROSE_TELL_RE = re.compile(r"[\s:;,()§]")


def _is_spec_slug(stem: str) -> bool:
    """True iff `stem` has a clean spec-slug SHAPE.

    Accepts hyphen/underscore/dot slugs such as '299-fabrication-mitigation',
    '597-memory-search', and the date-prefixed council form
    '2026-06-02-l061-verdict-pointer-fix-decision'. Rejects an empty stem and
    any stem with a char outside the slug charset (whitespace, ':', path
    separators). Prose / code-path rejection lives UPSTREAM on the raw
    `spec_ref` (`_resolve_spec_name`'s `_PROSE_TELL_RE` pre-gate), so a bare
    dotted token like 'postgres_store.py' is a valid slug SHAPE here.
    """
    if not stem:
        return False
    if not _SPEC_SLUG_RE.match(stem):
        return False
    return True


def _task_yaml_candidates(task_id: int) -> list[Path]:
    """Candidate task-file paths for `task_id` under the active PROJECT_ROOT.

    Single source of truth for the `docs/tasks/{id}.yaml` AND
    `docs/tasks/{id:03d}.yaml` lookup shape, shared by `_resolve_spec_name` and
    the at-start cwd-task guard (`_assert_task_in_cwd`) so they stay in lock-step.
    """
    return [
        PROJECT_ROOT / "docs" / "tasks" / f"{task_id}.yaml",
        PROJECT_ROOT / "docs" / "tasks" / f"{task_id:03d}.yaml",
    ]


def _assert_task_in_cwd(task_id: int) -> None:
    """Refuse (exit) if `task_id` has no task file under the active PROJECT_ROOT.

    A `--start build --task <id>` run right after `cd <other-repo>` started
    a stray `build-<id>` workflow in the wrong repo (no such task there) and
    polluted boot-context. A warning still lets the stray workflow through, so
    this REFUSES — `create_state` calls it before any state is written. Only
    fires when `--task` was given (`task_id is not None`); a task-less `--start`
    is legitimate for some workflows and is left untouched by the caller.
    """
    if any(c.is_file() for c in _task_yaml_candidates(task_id)):
        return
    tasks_dir = PROJECT_ROOT / "docs" / "tasks"
    print(
        f"ERROR: task {task_id} not found in {tasks_dir}/ — wrong working "
        f"directory? (refusing to start a stray workflow)",
        file=sys.stderr,
    )
    sys.exit(EXIT_NOT_FOUND)


def _spec_ref_text(task: dict[str, Any]) -> str | None:
    """The task's `spec_ref` when it is a non-blank string; any other value means no spec_ref."""
    spec_ref = task.get("spec_ref")
    return spec_ref if isinstance(spec_ref, str) and spec_ref.strip() else None


def _resolve_spec_name(task_id: int) -> str | None:
    """resolve {spec_name} variable.

    Liest docs/tasks/<task_id>.yaml + extrahiert spec_ref-Field, returnt
    Basename ohne Extension (z.B. 'docs/specs/299-fabrication-mitigation.md'
    -> '299-fabrication-mitigation').

    Conditional: Task ohne spec_ref ODER spec_ref=null → return None.
    Ein spec_ref der PROSE ist (kein Spec-Pfad) → stem ist Garbage →
    return None (statt Garbage in {spec_name} zu leiten). Engine setzt
    spec_name nur wenn None nicht ist (kein Override mit None).
    """
    task_yaml = next((c for c in _task_yaml_candidates(task_id) if c.is_file()), None)
    if task_yaml is None:
        return None

    try:
        import yaml as _yaml
    except ImportError:
        return None

    try:
        data = _yaml.safe_load(task_yaml.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return None
    if not isinstance(data, dict):
        return None

    spec_ref = _spec_ref_text(data)
    if spec_ref is None:
        return None
    # Reject prose / code-path refs on the RAW string before stemming —
    # a section-prose ref like 'SKILL.md §1 (...)' stems to a clean-looking
    # 'SKILL' that the slug gate would wrongly accept.
    if _PROSE_TELL_RE.search(spec_ref):
        return None
    # Basename ohne Extension — nur zurueckgeben wenn es ein sauberer Slug ist
    # (Code-Pfad-spec_ref → None statt Garbage-Glob).
    stem = Path(spec_ref).stem
    if not _is_spec_slug(stem):
        return None
    return stem


def _task_without_spec_ref(task_id: int) -> bool:
    """True iff the task file is a mapping without a spec_ref (`_spec_ref_text`).

    Picks the default build route. An unreadable task file (OS or YAML error,
    not a mapping, no PyYAML) prints a NOTE naming it and gives False, so the
    start keeps the route with the spec phase.
    """
    task_yaml = next((c for c in _task_yaml_candidates(task_id) if c.is_file()), None)
    if task_yaml is None:
        return False
    try:
        import yaml as _yaml
    except ImportError:
        data = None
    else:
        try:
            data = _yaml.safe_load(task_yaml.read_text(encoding="utf-8"))
        except (OSError, ValueError, _yaml.YAMLError):
            data = None
    if not isinstance(data, dict):
        print(
            f"NOTE: task file {task_yaml} could not be read as a mapping; "
            f"route defaults to 'standard'",
            file=sys.stderr,
        )
        return False
    return _spec_ref_text(data) is None


def _existing_spec_ref_path(task_id: int) -> Path | None:
    """Return the task's `spec_ref` as a Path iff it resolves to an existing
    file under PROJECT_ROOT, else None (advisory route-hint).

    Distinct from `_resolve_spec_name`: that gates on stem SHAPE; this gates on
    the referenced file EXISTING. A prose `spec_ref` never names an existing
    file, so the hint only fires for a real spec/path that is already authored.
    """
    task_yaml = next((c for c in _task_yaml_candidates(task_id) if c.is_file()), None)
    if task_yaml is None:
        return None
    try:
        import yaml as _yaml
    except ImportError:
        return None
    try:
        data = _yaml.safe_load(task_yaml.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return None
    if not isinstance(data, dict):
        return None
    spec_ref = _spec_ref_text(data)
    if spec_ref is None:
        return None
    ref_path = (PROJECT_ROOT / spec_ref).resolve()
    return ref_path if ref_path.is_file() else None


# Workflow state-file directories searched by `_discover_state_file`. State-files
# live per workflow type (docs/<workflow>/...). List sourced from
# `workflows/runbooks/<workflow>/REFERENCE.md` Frontmatter-Schema sections —
# extend when a new workflow defines its state-file dir.
#
# Pre-Fix war diese Liste hardcoded auf `docs/solve/`:
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


def _discover_state_file(task_id: int, *, strict: bool = False) -> str | None:
    """Discover workflow state file for a given task ID.

    Searches all known workflow-state directories (`docs/<workflow>/`) for:
    1. Files with `task_ref: <task_id>` in YAML frontmatter (canonical key per
       `workflows/workflow-template.md` line 159 + 4 workflow REFERENCE.md).
       Legacy `parent_task: <task_id>` is ALSO accepted as fallback so existing
       state-files written before the convention-fix keep resolving.
    2. Most recent file with literal `task-<N>` or `task_<N>` prefix in the
       filename (across all workflow dirs).

    Returns relative path (from project root) or None. With strict=True,
    propagate I/O failures so named guards cannot mistake them for absence.

    Convention note: `parent_task:` is the task-yaml field for sub-task
    hierarchy (`framework/task-format.md` line 45). It is NOT a state-file
    field. Strategy-1 fallback exists purely for backward-compat with files
    written before the convention was clarified.
    """
    candidate_files: list[Path] = []
    for sub in STATE_FILE_DIRS:
        wf_dir = PROJECT_ROOT / "docs" / sub
        if strict:
            candidate_files.extend(_glob_paths_strict(f"docs/{sub}/*.md"))
            continue
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
            if strict:
                raise
            continue
        fm_match = re.match(r"^---\s*\n(.*?)\n---", content, re.DOTALL)
        if not fm_match:
            continue
        frontmatter = fm_match.group(1)
        # Primary: task_ref (canonical state-file convention)
        tr_match = re.search(r"^\s*task_ref:\s*(\d+)\s*$", frontmatter, re.MULTILINE)
        if tr_match and int(tr_match.group(1)) == task_id:
            return str(md_file.relative_to(PROJECT_ROOT))
        # Legacy fallback: parent_task (pre-fix convention)
        pt_match = re.search(r"^\s*parent_task:\s*(\d+)\s*$", frontmatter, re.MULTILINE)
        if pt_match and int(pt_match.group(1)) == task_id:
            return str(md_file.relative_to(PROJECT_ROOT))

    # Strategy 2: explicit `task-<N>` prefix (e.g., <date>-task-<N>-<slug>.md).
    # Previous regex `(?:^|[-_])0*N(?:[-_]|$)` had false-positives on date
    # components (e.g., task_id=1 matched "...-01-..." via the "01" digits).
    # Now we require the literal "task-" or "task_" prefix to anchor the match.
    task_str = str(task_id)
    for md_file in md_files:
        name = md_file.stem  # without extension
        # Match "task-<N>" or "task_<N>" with word-boundary after N
        if re.search(rf"task[-_]0*{re.escape(task_str)}(?:[-_]|$)", name):
            return str(md_file.relative_to(PROJECT_ROOT))

    # Keep missing-input diagnostics visible to callers that retry discovery.
    print(
        f"WARNING: no state-file found for task {task_id}. "
        f"Strategy 1 (frontmatter task_ref or legacy parent_task across "
        f"docs/{{{','.join(STATE_FILE_DIRS)}}}/) + Strategy 2 (task-N filename) "
        f"both missed. Completion checks using {{state_file}} remain blocked until resolved.",
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
    """Read evidence_layout from skill-frontmatter.

    Lookup-Pfad: state["current_step"]["skill_ref"] ODER step_state["skill_ref"].
    Bei fehlendem skill_ref ODER File nicht lesbar: Default 'auto'.
    Bei Skill-Frontmatter ohne evidence_layout: Default 'per_finding' (Spec §1.5).

    Snapshot-Pattern. Wenn step_state
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
                f"snapshot.",
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


def _unresolved_outside(value: Any, available: set[str] | frozenset[str] = frozenset()) -> list[str]:
    """Unresolved `{var}` names in a string value, minus prior producer outputs."""
    if not isinstance(value, str):
        return []
    return [name for name in _has_unresolved_vars(value) if name not in available]


def _pointer_source_field(
    comp: dict[str, Any], available: set[str] | frozenset[str] = frozenset(),
) -> str:
    """Which field a pointer_check reads its path from (L1, review 2026-10-23).

    `source_file` is primary. When it still carries unresolved variables after
    resolution (e.g. `{task_id}` unset because the workflow was started without
    `--task`) and `source_file_fallback` resolves fully, the fallback is used.
    In every other case the primary stays selected, so a fully unresolved pair
    keeps the clean unresolved-variable block on `source_file`.
    """
    if comp.get("type") != "pointer_check":
        return "source_file"
    primary = comp.get("source_file")
    fallback = comp.get("source_file_fallback")
    if (
        isinstance(primary, str)
        and _unresolved_outside(primary, available)
        and isinstance(fallback, str)
        and fallback
        and not _unresolved_outside(fallback, available)
    ):
        return "source_file_fallback"
    return "source_file"


def _check_pointer(
    comp: dict[str, Any], state: dict[str, Any], step_state: dict[str, Any],
    observed=None,
) -> tuple[bool, str]:
    """pointer_check Completion-Type — Spec §2.1 Schicht-2.

    1. source_file must be resolved before evaluation.
    2. Layout via Skill-Frontmatter (default per_finding).
    3. Capture report once and call the evidence_pointers content API:
       - schema_version: 0 OR missing → return (True, "legacy, skipped")
       - schema_version: 1 + leeres/missing evidence → return (False, "non-empty...")
       - pro Pointer Mechanik (existence + grep -F + range etc.)
    4. Exit 0 passes, exit 1 is a valid negative, other exits raise evaluation errors.
    5. An unavailable validator is an evaluation error, never manual success.
    6. Optional `source_file_fallback` replaces an unresolved `source_file`
       (see `_pointer_source_field`); the repo-boundary check applies to
       whichever path is used.
    7. Optional `min_schema_version` (int): a source whose schema_version is
       missing, 0 or below the minimum is a valid negative instead of the
       legacy skip.
    """
    observed = observed if observed is not None else {}
    source_field = _pointer_source_field(comp)
    source_file = comp.get(source_field)
    if not source_file:
        return False, "pointer_check: 'source_file' required"
    min_sv = comp.get("min_schema_version")

    # Resolve relativ zu PROJECT_ROOT
    abs_source = (PROJECT_ROOT / str(source_file)).resolve()
    # asymmetric-boundary-check — Validator hatte
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

    if OPTION_FIELDS.intersection(comp):
        if min_sv is not None and min_sv > 1:
            return False, f"pointer_check requires schema_version >= {min_sv}; mandatory current schema is 1"
        owner = comp["review_owner_workflow"]
        if owner == "self":
            owner = state.get("workflow_id")
        if (state.get("workflow") in {"spec_board", "spec-board"} and state.get("parent_workflow_id")
                and owner != state["parent_workflow_id"]):
            raise CompletionEvaluationError("Nested spec-board owner conflicts with explicit parent")
        return _review_current(owner, comp["review_owner_step"], comp["review_policy"], source=str(source_file), observed=observed)

    layout = _resolve_evidence_layout(state, step_state)

    try:
        from scripts.lib.evidence_pointers import (
            EvidenceParseError as _EvParseErr,
            EvidenceValidationError as _EvValErr,
            validate_content,
        )
    except ImportError as exc:
        raise CompletionEvaluationError(
            f"evidence pointer validator unavailable ({exc})"
        ) from exc

    try:
        content = _capture_check_view(abs_source, observed)
        result = validate_content(content, layout=layout, repo_root=str(PROJECT_ROOT))
        sv, exit_code, messages = result.schema_version, result.exit_code, result.messages
        observed.update(schema_version=sv, layout=layout, limits=["Pointer dependency targets are not a complete atomic input snapshot"])
    except (_EvParseErr, _EvValErr) as exc:
        raise CompletionEvaluationError(f"pointer_check evaluation error: {exc}") from exc
    except Exception as exc:  # noqa: BLE001
        raise CompletionEvaluationError(f"pointer_check internal error: {exc}") from exc

    if exit_code not in (0, 1):
        raise CompletionEvaluationError(
            f"pointer_check evaluation failed (exit {exit_code}): {'; '.join(messages)}"
        )
    if min_sv is not None and (sv is None or sv < min_sv):
        got = "missing" if sv is None else str(sv)
        return False, (
            f"pointer_check fail: schema_version >= {min_sv} required, "
            f"got {got} ({source_file})"
        )

    # separate WARN-Channel von errors. Validator-Library appended
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
            observed["producer"] = "legacy"
            return True, "legacy, skipped (schema_version 0 or missing)"
        return True, f"pointer_check ok: {detail}" if detail else "pointer_check ok"
    if exit_code == 1:
        return False, f"pointer_check fail: {detail}"
    raise CompletionEvaluationError(f"pointer_check evaluation failed (exit {exit_code}): {detail}")


def check_completion(comp: dict[str, Any], state: dict[str, Any], step_state: dict[str, Any]) -> tuple[bool, str]:
    """Evaluate a completion condition. Returns (passed, message)."""
    try:
        return _check_completion(comp, state, step_state)
    except (CompletionEvaluationError, OSError, ValueError, TypeError, re.error) as exc:
        return False, f"completion evaluation error: {exc}"


def _validate_completion_inputs(
    comp: dict[str, Any], available_outputs: set[str] | None = None, *, _path: str = 'completion',
) -> set[str]:
    try:
        return _validate_completion_inputs_impl(comp, available_outputs, _path=_path)
    except (CompletionEvaluationError, OSError, ValueError, TypeError) as exc:
        if not hasattr(exc, '_completion_input'):
            setattr(exc, '_completion_input', {'definition': copy.deepcopy(comp), 'path': _path})
        raise


def _validate_completion_inputs_impl(
    comp: dict[str, Any], available_outputs: set[str] | None = None, *, _path: str = 'completion',
) -> set[str]:
    """Validate external inputs up front; defer only prior producer outputs."""
    _preflight_completion(comp)
    available = set(available_outputs or ())
    source_field = _pointer_source_field(comp, available)
    for field in ("path", "command", "pattern", source_field, "review_owner_workflow", "review_owner_step"):
        val = comp.get(field)
        for item in val if isinstance(val, list) else [val]:
            unresolved = _unresolved_outside(item, available)
            if unresolved:
                raise CompletionEvaluationError(
                    f"unresolved variable(s) {{{', '.join(unresolved)}}} "
                    f"in completion field '{field}' (value: {item})"
                )
    ctype = comp.get("type", "manual")
    if ctype not in VALID_COMPLETION_TYPES:
        raise CompletionEvaluationError(f"unknown completion type: {ctype}")
    if ctype == "pointer_check":
        min_sv = comp.get("min_schema_version")
        if min_sv is not None and (
            isinstance(min_sv, bool) or not isinstance(min_sv, int) or min_sv < 0
        ):
            raise CompletionEvaluationError(
                f"pointer_check min_schema_version must be a non-negative integer "
                f"(value: {min_sv!r})"
            )
    if ctype == "compound":
        checks = comp.get("checks")
        if not isinstance(checks, list) or not checks:
            raise CompletionEvaluationError("compound requires non-empty checks")
        for i, sub in enumerate(checks):
            if not isinstance(sub, dict):
                raise CompletionEvaluationError(f"compound check [{i}] must be a mapping")
            available = _validate_completion_inputs(sub, available, _path=_path + "." + str(i))
    elif ctype == "file_created_matching":
        available.add("artifact_path")
    return available


def _check_brief(path: str, workflow_id: str, observed=None) -> tuple[bool, str]:
    """Check one captured brief; local structure does not certify judgment."""
    import yaml

    class UniqueLoader(yaml.SafeLoader):
        def construct_mapping(self, node, deep=False):
            self.flatten_mapping(node)
            result = {}
            for key_node, value_node in node.value:
                key = self.construct_object(key_node, deep=deep)
                if key in result:
                    raise ValueError(f"duplicate YAML key: {key}")
                result[key] = self.construct_object(value_node, deep=deep)
            return result

    def parse(text):
        return yaml.load(text, Loader=UniqueLoader)

    def nonblank(value):
        return isinstance(value, str) and bool(value.strip())

    def require(condition, message):
        if not condition:
            raise CompletionEvaluationError(f"brief: {message}")

    require(nonblank(path), "required path is blank")
    relative = Path(path)
    require(not relative.is_absolute(), "path must be project-relative")
    try:
        target = (PROJECT_ROOT / relative).resolve()
        require(target.is_relative_to(PROJECT_ROOT.resolve()), "path escapes active project")
        require(target.is_file(), "path must resolve to a readable regular file")
        content = _capture_check_view(target, observed if observed is not None else {}, errors="strict")
        require(nonblank(content), "content is empty")
        lines = content.splitlines()
        require(lines[0] == "---", "missing frontmatter contract")
        end = next((i for i in range(1, len(lines)) if lines[i] == "---"), None)
        require(end is not None, "unterminated frontmatter")
        metadata = parse("\n".join(lines[1:end]))
        require(isinstance(metadata, dict), "frontmatter must be a mapping")
        contract = metadata.get("brief_contract")
        obligations = {"implicit_decisions", "mechanism_cells"}
        require(isinstance(contract, dict) and set(contract) == obligations | {"workflow_id"},
                "brief_contract requires exactly workflow_id, implicit_decisions and mechanism_cells")
        require(nonblank(contract["workflow_id"]) and contract["workflow_id"] == workflow_id,
                "workflow owner does not match selected run")
        for name in obligations:
            declaration = contract[name]
            require(isinstance(declaration, dict) and "status" in declaration
                    and set(declaration) <= {"status", "reason"}, f"unsupported {name} declaration")
            require(declaration["status"] in ("applicable", "exempt"), f"{name} applicability is unresolved")
            if declaration["status"] == "exempt":
                require(nonblank(declaration.get("reason")), f"{name} exemption requires a reason")

        # Recognize only real section headings, outside Markdown fenced examples.
        sections = {}
        current = None
        fence = None
        for line in lines[end + 1:]:
            marker = re.match(r"^ {0,3}(`{3,}|~{3,})(.*)$", line)
            if fence:
                if current is not None:
                    sections[current].append(line)
                if re.fullmatch(rf" {{0,3}}{re.escape(fence[0])}{{{fence[1]},}}\s*", line):
                    fence = None
                continue
            if marker:
                fence = (marker[1][0], len(marker[1]))
            else:
                heading = re.match(r"^ {0,3}(#{1,6})\s+(.+?)\s*#*\s*$", line)
                if heading and len(heading[1]) <= 2:
                    current = None
                    title = heading[2].removeprefix("§").strip()
                    name = {"Implicit-Decisions-Surfaced": "implicit_decisions",
                            "Mechanism-cells": "mechanism_cells"}.get(title)
                    if len(heading[1]) == 2 and name:
                        require(name not in sections, f"duplicate {title} section")
                        current = name
                        sections[name] = []
                    continue
            if current is not None:
                sections[current].append(line)

        for name in obligations:
            body = sections.get(name, [])
            if name in sections:
                require(any(line.strip() and not re.match(r"^\s*(`{3,}|~{3,})", line) for line in body),
                        f"empty {name} section")
            if contract[name]["status"] == "exempt":
                continue
            require(name in sections, f"missing {name} section")
            payloads = []
            block = None
            fence = None
            for line in body:
                if fence:
                    if re.fullmatch(rf" {{0,3}}{re.escape(fence[0])}{{{fence[1]},}}\s*", line):
                        if block is not None:
                            payloads.append(parse("\n".join(block)))
                        fence, block = None, None
                    elif block is not None:
                        block.append(line)
                    continue
                marker = re.match(r"^ {0,3}(`{3,}|~{3,})(.*)$", line)
                if marker:
                    fence = (marker[1][0], len(marker[1]))
                    block = [] if marker[2].strip().lower() in {"yaml", "yml"} else None
            require(fence is None, f"unterminated fence in {name}")
            require(len(payloads) == 1, f"{name} requires one unambiguous YAML payload")
            root = "implicit_decisions_surfaced" if name == "implicit_decisions" else name
            payload = payloads[0]
            require(isinstance(payload, dict) and isinstance(payload.get(root), dict), f"missing {root} mapping")
            values = payload[root]
            if name == "implicit_decisions":
                for key in ("schema_and_contract", "error_and_stop", "layer_discipline",
                            "structural_invariants", "vision_alignment"):
                    decision = values.get(key)
                    require(isinstance(decision, dict) and nonblank(decision.get("locked"))
                            and nonblank(decision.get("value")), f"{key} requires nonblank locked and value")
            else:
                require(nonblank(values.get("section")), "mechanism_cells requires section")
                for key in ("in_scope", "placed", "forbidden_adjacent"):
                    cells = values.get(key)
                    require(isinstance(cells, list) and all(nonblank(cell) for cell in cells),
                            f"mechanism_cells {key} requires a list of nonblank strings")
                    if key == "in_scope":
                        require(bool(cells), "mechanism_cells in_scope must not be empty")
    except (OSError, UnicodeError, ValueError, TypeError, yaml.YAMLError) as exc:
        raise CompletionEvaluationError(f"brief: invalid required input: {exc}") from exc
    return True, "brief structure checked; judgment and authorization remain manual"


def _mandatory_review_checks(comp: dict[str, Any] | None) -> list[dict[str, Any]]:
    if comp is None:
        return []
    if comp.get("type") == "pointer_check" and OPTION_FIELDS.intersection(comp):
        return [comp]
    if comp.get("type") == "compound":
        return [item for child in comp.get("checks", []) for item in _mandatory_review_checks(child)]
    return []


def _contains_brief_check(comp: dict[str, Any] | None) -> bool:
    if comp is None:
        return False
    return comp.get("type") == "brief_check" or (
        comp.get("type") == "compound" and any(_contains_brief_check(child) for child in comp["checks"])
    )


def _check_completion(comp: dict[str, Any], state: dict[str, Any], step_state: dict[str, Any]) -> tuple[bool, str]:
    return _evaluate_completion(comp, state, step_state)


def _evaluate_leaf(comp, state, step_state, details):
    """Distinguish failed evaluation from a valid negative completion check."""
    ctype = comp.get("type", "manual")

    if ctype == "brief_check":
        return _check_brief(comp["path"], state.get("workflow_id", ""), details)

    if ctype == "manual":
        return True, "manual: agent-confirmed (not verified)"

    if ctype == "file_modified_after":
        target_path = comp.get("path", "")
        abs_path = PROJECT_ROOT / target_path
        if not abs_path.exists():
            return False, f"file not found: {target_path}"
        started_at = step_state.get("started_at", state.get("started"))
        if not started_at:
            raise CompletionEvaluationError("no started_at to compare")
        start_ts = _parse_utc(started_at).timestamp()
        mtime = abs_path.stat().st_mtime
        details["checked_input"] = [{"kind": "metadata", "path": target_path, "mtime": mtime, "baseline": started_at}]
        if mtime >= start_ts:
            return True, "file modified after step start"
        return False, f"file not modified since step start ({target_path})"

    if ctype == "file_created_matching":
        patterns = comp.get("pattern", [])
        if isinstance(patterns, str):
            patterns = [patterns]
        workflow_start = state.get("started", "")
        start_ts = 0.0 if not workflow_start else _parse_utc(workflow_start).timestamp()
        details["checked_input"] = [{"kind": "matching", "patterns": patterns, "baseline": workflow_start, "matches": []}]
        for pat in patterns:
            for match_path in _glob_paths_strict(pat):
                if not match_path.exists():
                    continue
                mtime = match_path.stat().st_mtime
                if mtime >= start_ts:
                    rel = str(match_path.relative_to(PROJECT_ROOT))
                    details["checked_input"][0]["matches"].append({"path": rel, "mtime": mtime})
                    state.setdefault("variables", {})["artifact_path"] = rel
                    return True, f"found matching file: {rel}"
        return False, f"no matching files for patterns: {patterns}"

    if ctype == "file_content_check":
        target_path = comp.get("path", "")
        abs_path = PROJECT_ROOT / target_path
        if not abs_path.exists():
            return False, f"file not found: {target_path}"
        content = _capture_check_view(abs_path, details)
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

    if ctype == "named_predicate":
        return _named_predicate(comp, state, observed=details)

    if ctype == "pointer_check":
        result = _check_pointer(comp, state, step_state, details)
        if OPTION_FIELDS.intersection(comp) and not result[0]:
            raise CompletionEvaluationError("Mandatory review adoption refused: " + result[1])
        return result

    raise CompletionEvaluationError(f"unknown completion type: {ctype}")


# ---------------------------------------------------------------------------
# Guard Evaluation
# ---------------------------------------------------------------------------

def _glob_paths_strict(pattern: str) -> list[Path]:
    """Glob with scandir so unreadable directories cannot become no matches.

    Like Path.glob, include hidden names and do not recurse through symlinked
    directories for **. Missing paths are legitimate negatives.
    """
    path = Path(pattern)
    if not pattern or path.is_absolute() or ".." in path.parts:
        raise ValueError(f"glob path must be non-empty and repo-relative: {pattern}")
    if any("**" in part and part != "**" for part in path.parts):
        raise ValueError("** must be an entire path component")

    def walk(base: Path, parts: tuple[str, ...]) -> list[Path]:
        if not parts:
            base.stat()
            return [base]
        part, rest = parts[0], parts[1:]
        try:
            with os.scandir(base) as scan:
                entries = list(scan)
        except FileNotFoundError:
            return []
        matches = walk(base, rest) if part == "**" else []
        for entry in entries:
            child = Path(entry.path)
            if part == "**":
                if entry.is_dir(follow_symlinks=False):
                    matches.extend(walk(child, parts))
            elif fnmatch.fnmatchcase(entry.name, part):
                if not rest:
                    if not pattern.endswith("/") or entry.is_dir():
                        matches.append(child)
                elif entry.is_dir():
                    matches.extend(walk(child, rest))
        return matches

    return walk(PROJECT_ROOT, path.parts)


def evaluate_guard(guard: dict[str, Any], state: dict[str, Any], variables: dict[str, Any]) -> tuple[bool | None, str]:
    """Return (applicable, reason): True=proceed, False=skip, None=error."""
    try:
        return _evaluate_guard(guard, state, variables)
    except (OSError, ValueError, TypeError) as exc:
        return None, f"guard evaluation error: {exc}"


def _evaluate_guard(guard: dict[str, Any], state: dict[str, Any], variables: dict[str, Any]) -> tuple[bool | None, str]:
    if not isinstance(guard, dict):
        return None, "guard must be a mapping"
    guard = _resolve_completion_vars(guard, variables)
    for field, value in guard.items():
        if isinstance(value, str) and (unresolved := _has_unresolved_vars(value)):
            return None, f"guard field '{field}' has unresolved variable(s): {', '.join(unresolved)}"
    gtype = guard.get("type", "")

    if gtype == "always_skip":
        return False, "always_skip guard"

    if gtype == "file_exists":
        resolved = guard.get("path", "")
        matches = _glob_paths_strict(resolved)
        if matches:
            return True, f"file exists: {resolved}"
        return False, f"file not found: {resolved}"

    if gtype == "step_status":
        step_id = guard.get("step_id", "")
        expected = guard.get("expected", "complete")
        steps = state.get("steps", {})
        if step_id not in steps:
            return None, f"guard references unknown step: {step_id}"
        if expected not in TERMINAL_STEP_STATUSES | {STATUS_PENDING, STATUS_IN_PROGRESS}:
            return None, f"guard references unknown status: {expected}"
        step_state = steps.get(step_id, {})
        actual = step_state.get("status", STATUS_PENDING)
        if actual == expected:
            return True, f"step '{step_id}' is {actual}"
        return False, f"step '{step_id}' is {actual}, expected {expected}"

    if gtype == "route_active":
        step_id = guard.get("step_id", "")
        route = guard.get("route", "")
        steps = state.get("steps", {})
        if step_id not in steps or not route:
            return None, f"guard requires a known step and non-empty route: {step_id}"
        step_state = steps.get(step_id, {})
        selected = step_state.get("selected_route")
        if selected == route:
            return True, f"route '{route}' is active on step '{step_id}'"
        return False, f"route '{route}' not active on step '{step_id}' (selected: {selected})"

    if gtype == "named_predicate":
        try:
            return _named_predicate(guard, {**state, "variables": variables}, guard=True)
        except (CompletionEvaluationError, OSError, ValueError, TypeError) as exc:
            return None, f"named predicate evaluation error: {exc}"

    if gtype == "script":
        return None, "unsupported script guard: inspection never executes commands"

    return None, f"unknown guard type: {gtype}"


def _completion_method(comp: dict[str, Any] | None, message: str = "") -> str:
    """Add provenance without changing the legacy step status vocabulary."""
    if not comp or comp.get("type", "manual") == "manual":
        return "agent-confirmed"
    if comp.get("type") == "compound" and any(
        _completion_method(check) == "agent-confirmed" for check in comp.get("checks", [])
    ):
        return "agent-confirmed"
    if "legacy, skipped" in message:
        return "legacy-unverified"
    return "verified"


def _format_completion_method(method: str) -> str:
    if method in {"agent-confirmed", "forced", "legacy-unverified"}:
        return f"{method} (not verified)"
    return method


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
    not given, default to "standard-implementation-only" when both it and
    "standard" are declared and the task has no spec_ref; otherwise to
    "standard" if declared, else error with valid list.
    """
    _ensure_state_dir()

    # Refuse a stray workflow when `--task` points at a task that does
    # not exist under the active PROJECT_ROOT (wrong working directory). Runs
    # before id-generation / duplicate-check / state-write so nothing leaks.
    if task_id is not None:
        _assert_task_in_cwd(task_id)

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
    route_defaulted_to_standard = False
    if wf_routes is not None:
        if not isinstance(wf_routes, dict) or not wf_routes:
            print(
                f"ERROR: Workflow '{workflow_name}' has 'routes' but not a "
                f"non-empty dict (got {type(wf_routes).__name__})",
                file=sys.stderr,
            )
            sys.exit(EXIT_SCHEMA_ERROR)
        if route is None:
            if (
                task_id is not None
                and {"standard", "standard-implementation-only"} <= wf_routes.keys()
                and _task_without_spec_ref(task_id)
            ):
                route = "standard-implementation-only"
                print(
                    f"NOTE: task {task_id} has no spec_ref; route defaults to "
                    f"'standard-implementation-only' (--route standard authors a spec)"
                )
            elif "standard" in wf_routes:
                route = "standard"
                route_defaulted_to_standard = True
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

    # Advisory-only route-hint. When the route defaulted to `standard`
    # (the full spec-authoring path) AND the task's spec_ref points at an
    # already-existing spec, the operator likely wanted an implementation-only
    # route. Pure non-blocking stderr hint — never changes/blocks/auto-switches.
    if route_defaulted_to_standard and task_id is not None:
        existing_spec = _existing_spec_ref_path(task_id)
        if existing_spec is not None:
            impl_routes = [
                r for r in ("standard-implementation-only", "sub-build")
                if r in (wf_routes or {})
            ]
            suffix = f" — did you mean --route {' / '.join(impl_routes)}?" if impl_routes else ""
            print(
                f"HINT: task {task_id} has a spec_ref to an existing spec "
                f"({existing_spec.name}) but route defaulted to 'standard' "
                f"(full spec-authoring path){suffix}",
                file=sys.stderr,
            )

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

        # befuelle spec_name aus
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
        "definition_fingerprint": definition_fingerprint(workflow_def),
    }

    save_state(state, is_new=True)
    return state


def find_next_step(state: dict[str, Any], workflow_def: dict[str, Any]) -> str | None:
    """Find the next actionable step. Returns step_id or None if all done/paused."""
    if _progress_refusal(state):
        return None
    _preflight_workflow(state, workflow_def)

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

    # lazy state_file re-discovery + lazy
    # spec_name lookup. Konsolidiert in `_ensure_state_variables_resolved`
    # damit `--complete` (cmd_complete) denselben Resolution-State sieht
    # (pre-fix war Resolution NUR hier; `--complete`
    # mit pointer_check + `{spec_name}` blockierte ohne `--force`).
    variables = state.get("variables", {})

    # FW-007 auto-complete is restricted to deterministic completion-types
    # whose evaluation is side-effect-free / file-based. Manual & compound
    # are excluded by spec (manual cannot be auto-checked, compound may
    # contain manual sub-checks).
    # pointer_check als top-level type ist per
    # Spec §2.2 schema-permissiv mit auto-complete-on-pass — wenn Pointer
    # mechanisch valid sind, passiert der Step ohne expliziten manual-step.
    # Aufgenommen ins Set damit die Spec-Zusage tatsaechlich greift.
    _AUTO_COMPLETE_TYPES = {
        "file_content_check",
        "file_created_matching",
        "file_modified_after",
        "pointer_check",
    }

    for sid in step_ids:
        ss = steps.get(sid, {})
        status = ss.get("status", STATUS_PENDING)

        # Skip terminal statuses
        if status in TERMINAL_STEP_STATUSES:
            continue

        # Pending: check depends_on
        step_def = _get_step_def(workflow_def, sid)
        if not step_def:
            continue

        deps = step_def.get("depends_on", [])
        if status != STATUS_IN_PROGRESS and isinstance(deps, list):
            deps_met = all(
                steps.get(d, {}).get("status") in TERMINAL_STEP_STATUSES
                for d in deps
            )
            if not deps_met:
                continue

        # Check guard
        guard = step_def.get("guard")
        if "guard" in step_def:
            proceed, reason = evaluate_guard(guard, state, variables)
            if proceed is None:
                raise GuardEvaluationError(f"Step '{sid}': {reason}")
            if proceed is False:
                steps[sid] = {
                    "status": STATUS_SKIPPED,
                    "skipped_reason": f"guard: {reason}",
                    "completed_at": _utcnow(),
                }
                save_state(state)
                continue

        # Active steps (including the first step) still need a valid guard.
        if status == STATUS_IN_PROGRESS:
            if _ensure_state_variables_resolved(state):
                save_state(state)
            return sid

        # FW-007 (pre-fulfilled idempotency): if a deterministic step's
        # completion-check already passes BEFORE activation (typical when
        # an artefact from a previous run still exists), auto-complete it
        # and continue to the next step instead of forcing a manual
        # --complete round-trip.
        cat = step_def.get("category", "content")
        comp = step_def.get("completion")
        if (
            cat == "deterministic"
            and not step_def.get("evidence_required", False)
            and isinstance(comp, dict)
            and comp.get("type") in _AUTO_COMPLETE_TYPES
        ):
            # Evaluate in memory; only a pass is a transition, saved once with its receipt.
            proposed = copy.deepcopy(state)
            checks: list[dict[str, Any]] = []
            working = proposed['steps'][sid]
            working.setdefault('started_at', _utcnow())
            try:
                _ensure_state_variables_resolved(proposed)
                success, msg = _evaluate_completion(comp, proposed, working, checks, sid + ':completion')
            except (CompletionEvaluationError, OSError, ValueError, TypeError, re.error):
                success = False
            if success:
                working.update(status=STATUS_COMPLETE, completion_method=_typed_completion_method(checks),
                               completed_at=_utcnow(), evidence='auto-complete: ' + msg,
                               receipt=_receipt('auto_complete', working, checks))
                save_state(proposed)
                state.clear()
                state.update(proposed)
                steps = state['steps']
                variables = state.get('variables', {})
                continue

        _ensure_state_variables_resolved(state)

        # Activate this step
        steps[sid]["status"] = STATUS_IN_PROGRESS
        steps[sid]["started_at"] = _utcnow()
        # snapshot evidence_layout fuer pointer_check
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


def _require_invocation_evidence(step: dict[str, Any] | None, evidence: str | None) -> None:
    if step and step.get("evidence_required", False):
        if not isinstance(evidence, str) or not evidence.strip():
            raise CompletionEvaluationError(
                "Fresh --evidence is required for this completion invocation, including force; "
                "retained evidence is insufficient"
            )


def _progress_refusal(state: dict[str, Any]) -> str | None:
    """Pause and abort isolation applies before evaluation or incidental writes."""
    if state.get("aborted"):
        return "Workflow is aborted; progression is refused"
    if state.get("paused"):
        return "Workflow is paused; resume explicitly before progressing"
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
    """Complete explicitly; flagged steps require evidence from this invocation."""
    if refusal := _progress_refusal(state):
        return False, refusal
    try:
        _preflight_workflow(state, workflow_def)
        _require_invocation_evidence(_get_step_def(workflow_def, step_id), evidence)
    except (CompletionEvaluationError, GuardEvaluationError) as exc:
        return False, f"Completion evaluation error: {exc}"
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

    if "guard" in step_def:
        guard_vars = {**state.get("variables", {}), **(set_vars or {})}
        applicable, reason = evaluate_guard(step_def["guard"], state, guard_vars)
        if applicable is not True:
            return False, f"Cannot complete step '{step_id}': guard: {reason}. Run --next after resolving it."

    if force and _contains_brief_check(step_def.get("completion", {})):
        return False, "brief_check refuses force; resolve required input and complete ordinarily"

    # Force guardrails: soft warning threshold + hard stop.
    if force:
        force_count = state.get("force_count", 0)
        if force_count >= MAX_FORCE_PER_WORKFLOW:
            return False, (
                f"Force limit reached ({MAX_FORCE_PER_WORKFLOW}/{MAX_FORCE_PER_WORKFLOW}). "
                "Cannot force-complete more steps in this workflow. "
                "Fix the completion check or --abort and restart."
            )

    cat = step_def.get('category', 'content')
    if cat == 'classification':
        if not route or route not in step_def.get('routes', {}):
            return False, f"Classification step '{step_id}' requires a valid --route"
    if state.get('workflow') in {'spec_board', 'spec-board'} and state.get('parent_workflow_id'):
        for review in _mandatory_review_checks(step_def.get('completion')):
            owner = _resolve_vars(review['review_owner_workflow'], {**state.get('variables', {}), **(set_vars or {})})
            if owner == 'self':
                owner = state['workflow_id']
            if not _has_unresolved_vars(owner) and owner != state['parent_workflow_id']:
                return False, 'Nested spec-board owner conflicts with explicit parent'
    # Evaluate into a local list; a transition and its receipt are saved once, a refusal saves nothing.
    proposed = copy.deepcopy(state)
    ss = proposed['steps'][step_id]
    checks: list[dict[str, Any]] = []
    comp = step_def.get('completion') or {'type': 'manual'}
    forced = force and bool(step_def.get('completion'))
    try:
        if set_vars:
            proposed.setdefault('variables', {}).update(set_vars)
        _ensure_state_variables_resolved(proposed)
        def mandatory(node, path='completion'):
            if node.get('type') == 'compound':
                for i, child in enumerate(node['checks']):
                    yield from mandatory(child, path + '.' + str(i))
            elif OPTION_FIELDS.intersection(node):
                yield node, path
        for check, path in mandatory(comp):
            prechecks: list[dict[str, Any]] = []
            try:
                _evaluate_completion(check, proposed, ss, prechecks, step_id + ':' + path)
            finally:
                checks.extend({**c, 'precheck': True} for c in prechecks)
        if forced:
            _unevaluated(checks, _resolve_completion_vars(comp, proposed.get('variables', {})), step_id + ':completion', 'forced')
            passed, detail = True, 'permitted force'
        else:
            passed, detail = _evaluate_completion(comp, proposed, ss, checks, step_id + ':completion')
    except (CompletionEvaluationError, OSError, ValueError, TypeError, re.error) as exc:
        return False, 'Completion evaluation error: ' + str(exc) + _refusal_checks(checks)
    if not passed:
        policy = step_def.get('on_fail', 'block')
        if policy == 'block':
            return False, 'Completion check failed: ' + detail + _refusal_checks(checks)
        candidate = copy.deepcopy(state)
        ss = candidate['steps'][step_id]
        ss['status'] = {'warn': STATUS_WARN_SKIPPED, 'skip': STATUS_SKIPPED, 'escalate': STATUS_ESCALATED}[policy]
        ss['completed_at'] = _utcnow()
        if policy == 'warn':
            ss['warn_reason'] = detail
        if evidence:
            ss['evidence'] = evidence
        message = {'warn': 'WARNING: ', 'skip': 'Skipped: ', 'escalate': 'ESCALATE: '}[policy] + step_id + ': ' + detail
    else:
        method = _typed_completion_method(checks, forced)
        ss.update(status=STATUS_COMPLETE, completion_method=method, completed_at=_utcnow())
        if evidence:
            ss['evidence'] = evidence
        if forced:
            proposed['force_count'] = proposed.get('force_count', 0) + 1
            ss['force_completed'] = True
        if route:
            ss['selected_route'] = route
            if cat == 'classification':
                _activate_route(proposed, workflow_def, step_id, route)
        candidate = proposed
        message = f"Step '{step_id}' completed: {_format_completion_method(method)}"
        if forced:
            message += f" (forced {proposed['force_count']}/{MAX_FORCE_PER_WORKFLOW})"
            if proposed['force_count'] > FORCE_WARN_THRESHOLD:
                message += ' WARNING: high force usage'
    ss['receipt'] = _receipt('complete', ss, checks)
    save_state(candidate)
    state.clear()
    state.update(candidate)
    if state['steps'][step_id]['status'] != STATUS_ESCALATED:
        _check_workflow_completion(state, workflow_def, propagate_parent=state['steps'][step_id]['status'] == STATUS_COMPLETE)
    return True, message + '; receipt: ' + _receipt_summary(checks)


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


def _check_workflow_completion(
    state: dict[str, Any], workflow_def: dict[str, Any], *, propagate_parent: bool = False,
) -> None:
    """Archive eligible local closure; retained completion records retry archive only."""
    if _progress_refusal(state):
        return
    _preflight_workflow(state, workflow_def)
    steps = state.get("steps", {})
    if set(steps) != set(_ordered_step_ids(workflow_def)) or any(
        step.get("status") not in TERMINAL_STEP_STATUSES - {STATUS_ESCALATED}
        for step in steps.values()
    ):
        return

    parent_id = state.get("parent_workflow_id")
    if parent_id and not propagate_parent:
        raise CompletionEvaluationError(
            "Local closure unresolved: parent-linked finalization is unsupported for this operation; "
            "the parent is unchanged. Only the existing ordinary explicit-completion path propagates."
        )

    needs_save = not state.get("completed") or state.get("current_step") is not None
    if not state.get("completed"):
        state["completed"] = _utcnow()
    state["current_step"] = None
    if needs_save:
        save_state(state)
    archive_state(state["workflow_id"], expected_revision=state.get("revision", 0))

    # Preserve the legacy boundary; newly added closure paths cannot propagate.
    if parent_id:
        _propagate_child_completion(state, parent_id)


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
    if refusal := _progress_refusal(state):
        return False, refusal
    _preflight_workflow(state, workflow_def)
    steps = state.get("steps", {})
    if step_id not in steps:
        return False, f"Step '{step_id}' not found"

    step_def = _get_step_def(workflow_def, step_id)
    if not step_def:
        return False, f"Step '{step_id}' not in definition"

    if steps[step_id].get("status") in TERMINAL_STEP_STATUSES:
        return False, f"Step '{step_id}' already terminal; use --next --id to reconcile closure"

    required = step_def.get("required", True)
    if required:
        # Check if guard would skip
        guard = step_def.get("guard")
        if "guard" in step_def:
            proceed, guard_reason = evaluate_guard(guard, state, state.get("variables", {}))
            if proceed is None:
                return False, f"Cannot skip required step '{step_id}': {guard_reason}"
            if proceed is True:
                return False, f"Cannot skip required step '{step_id}' (guard passed)"
        else:
            return False, f"Cannot skip required step '{step_id}'"

    steps[step_id]["status"] = STATUS_SKIPPED
    steps[step_id]["completed_at"] = _utcnow()
    steps[step_id]["skipped_reason"] = reason
    save_state(state)
    _check_workflow_completion(state, workflow_def)
    return True, f"Step '{step_id}' skipped: {reason}"


def _capture_correction_refusal(step_state: dict[str, Any], current_status: str) -> str | None:
    """Why the record contradicts a capture-correction claim; None when it does not.

    The engine cannot observe dispatch: the claim is Buddy's, refused where the
    step is not in_progress or its review record holds adopted producer output.
    """
    if current_status != STATUS_IN_PROGRESS:
        return f"the step is {current_status}, not in_progress"
    record = step_state.get("review")
    if isinstance(record, dict) and ("adoption" in record or record.get("adoption_history")):
        return "its review record holds an adopted decision over producer reports"
    return None


def _at_the_cap_record(reason: str) -> tuple[dict[str, str] | None, str]:
    """Qualify the `at-the-cap: <path>` ruling record a code-board crossing names.

    Returns ({path, sha256}, "") or (None, failed condition).
    """
    import yaml

    match = _AT_THE_CAP_RE.search(reason)
    if not match:
        return None, "no at-the-cap reference"
    written = match.group(1)
    root = PROJECT_ROOT.resolve()
    target = (root / written).resolve()
    if Path(written).is_absolute() or not target.is_relative_to(root):
        return None, f"path outside the project: {written}"
    if not target.is_file():
        return None, f"missing file: {written}"
    data = target.read_bytes()
    lines = data.decode("utf-8", errors="replace").splitlines()
    blocks: list[str] = []
    if lines and lines[0].strip() == "---":
        end = next((i for i in range(1, len(lines)) if lines[i].strip() == "---"), None)
        if end is not None:
            blocks.append("\n".join(lines[1:end]))
    fence: tuple[str, bool] | None = None  # (opening marker, is yaml) while inside a fence
    body: list[str] = []
    for line in lines:
        match = _FENCE_RE.match(line)
        if fence is None:
            if match:
                info = match.group(2).split()
                fence, body = (match.group(1), bool(info) and info[0].lower() in {"yaml", "yml"}), []
        elif (match and match.group(1)[0] == fence[0][0] and len(match.group(1)) >= len(fence[0])
              and not match.group(2).strip()):
            if fence[1]:
                blocks.append("\n".join(body))
            fence = None
        else:
            body.append(line)
    for block in blocks:
        try:
            parsed = yaml.safe_load(block)
        except yaml.YAMLError:
            continue
        findings = parsed.get("remaining_findings") if isinstance(parsed, dict) else None
        if isinstance(findings, list) and findings:
            return {"path": written, "sha256": hashlib.sha256(data).hexdigest()}, ""
    return None, f"no non-empty remaining_findings in {written}"


def retry_step(
    state: dict[str, Any],
    workflow_def: dict[str, Any],
    step_id: str,
    reason: str,
) -> tuple[bool, str]:
    """Reopen an in-progress or terminal step using its existing iteration.

    Preserve prior review evidence in retry history; pending steps need no retry.
    The cap counts review rounds: a `capture-correction:` retry (no producer
    output adopted yet) keeps the iteration and skips the cap. A counted retry
    at the cap needs a structured override; on the code board step, the
    at-the-cap ruling record instead of free text.
    """
    if refusal := _progress_refusal(state):
        return False, refusal
    _require_interpretation(state, workflow_def, reopening_step=step_id)
    _preflight_workflow(state, workflow_def)
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
    counted = not _CAPTURE_CORRECTION_RE.match(reason.strip())
    at_the_cap: dict[str, str] | None = None
    step_def = _get_step_def(workflow_def, step_id)
    if not counted:
        if refusal := _capture_correction_refusal(step_state, current_status):
            return False, (
                f"Step '{step_id}' retry refused as capture correction: {refusal}. "
                f"A counted retry is needed instead."
            )
    elif iterations >= iteration_cap and step_def and step_def.get("skill_ref") == CODE_REVIEW_BOARD_SKILL:
        # Code board: the skill's per-mechanism limit ends the loop; crossing
        # the engine cap names the at-the-cap ruling record, not free text.
        at_the_cap, failed = _at_the_cap_record(reason)
        if at_the_cap is None:
            return False, (
                f"Step '{step_id}' has iterated {iterations}/{iteration_cap} "
                f"times (cap reached). On the code board step, crossing the cap "
                f"requires the ruling record of skills/convergence_loop/at-the-cap.md: "
                f"--reason must contain 'at-the-cap: <project-relative verdict path>' "
                f"naming a file with a non-empty remaining_findings list. Failed: {failed}."
            )
    elif iterations >= iteration_cap:
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

    # Reopened work invalidates a retained completion awaiting archival.
    state.pop("completed", None)

    # Reset state for retry, preserve audit-trail
    retry_history = step_state.get("retry_history", [])
    prior_review = step_state.pop("review", None)
    prior_receipt = step_state.pop("receipt", None)
    retry_history.append({
        **({"review": copy.deepcopy(prior_review)} if prior_review is not None else {}),
        **({"receipt": copy.deepcopy(prior_receipt)} if prior_receipt is not None else {}),
        "from_status": current_status,
        "reason": reason,
        "when": _utcnow(),
        "iteration_before": iterations,
        "counted": counted,
        **({"at_the_cap": at_the_cap} if at_the_cap is not None else {}),
    })

    step_state["status"] = STATUS_IN_PROGRESS
    step_state["started_at"] = _utcnow()
    step_state["iterations"] = iterations + 1 if counted else iterations
    step_state["retry_history"] = retry_history
    # Capture the prior route selection BEFORE clearing it — the classification
    # re-pristine below needs it.
    prior_route = step_state.get("selected_route")
    # Clear terminal-state fields so retry is clean
    for field in ("completed_at", "evidence", "warn_reason", "skipped_reason",
                  "force_completed", "selected_route", "completion_method"):
        step_state.pop(field, None)

    # Classification retry: re-pristine the route-children whose state is a
    # CONSEQUENCE of the prior route selection, so a re-route re-activates
    # cleanly. Reset set =
    #   (a) children currently ROUTE_SKIPPED — the prior route excluded them;
    #       _apply_route_skip only marks PENDING, so on re-selection they would
    #       stay skipped → the newly-selected route silently does not run + the
    #       workflow wedges (the original CRITICAL); PLUS
    #   (b) children EXCLUSIVE to the prior selected route — abandoned work on
    #       the path being left; otherwise they linger non-terminal.
    # Steps SHARED with other routes are left untouched: a re-route may still
    # need them, and resetting a completed shared step would wipe its evidence +
    # audit trail. Correct for every FLAT (leaf-classification) route topology —
    # disjoint (build `board`), fully-shared (review/research), and 3+-route
    # partial-overlap. NOT recursive: were a reset child itself a classification
    # step, its own route-children would not be re-pristined. No current
    # workflow.yaml nests a classification inside a route (all are leaf), so
    # this is latent, not live; a nested classification would need this reset
    # made recursive (or a validate_runbook_consistency rule forbidding nesting).
    if step_def and step_def.get("category") == "classification":
        routes = {
            k: set(v) for k, v in (step_def.get("routes") or {}).items()
            if isinstance(v, list)
        }
        if routes:
            all_children: set[str] = set().union(*routes.values())
            others: set[str] = set().union(
                *[v for k, v in routes.items() if k != prior_route]
            )
            prior_exclusive = routes.get(prior_route, set()) - others
            route_skipped = {
                cid for cid in all_children
                if steps.get(cid, {}).get("status") == STATUS_ROUTE_SKIPPED
            }
            for child_id in prior_exclusive | route_skipped:
                child = steps.get(child_id)
                if not child or child.get("status") == STATUS_PENDING:
                    continue
                child["status"] = STATUS_PENDING
                for f in ("completed_at", "started_at", "evidence", "warn_reason",
                          "skipped_reason", "force_completed", "selected_route", "completion_method",
                          "receipt"):
                    child.pop(f, None)

    # Update current_step pointer
    state["current_step"] = step_id

    save_state(state)
    iteration_note = (f"Iteration {iterations + 1}/{iteration_cap}" if counted
                      else f"Iteration {iterations}/{iteration_cap} (not counted: capture correction)")
    return True, (
        f"Step '{step_id}' reset to in_progress. {iteration_note}. "
        f"Reason: {reason}. Re-execute + --complete when done."
    )


# ---------------------------------------------------------------------------
# Recovery
# ---------------------------------------------------------------------------

def recover_workflow(state: dict[str, Any], workflow_def: dict[str, Any]) -> list[str]:
    if _progress_refusal(state):
        return []
    _preflight_workflow(state, workflow_def)
    selected = []
    for sid, ss in state.get('steps', {}).items():
        if ss.get('status') != STATUS_IN_PROGRESS:
            continue
        node = _get_step_def(workflow_def, sid)
        if not node:
            continue
        if 'guard' in node:
            applies, reason = evaluate_guard(node['guard'], state, state.get('variables', {}))
            if applies is None:
                raise GuardEvaluationError(reason)
            if not applies:
                continue
        comp = node.get('completion')
        if not comp or node.get('evidence_required') or _completion_method(comp) == 'agent-confirmed':
            continue
        selected.append((sid, comp))
    if not selected:
        _check_workflow_completion(state, workflow_def)
        return []
    # Evaluate in memory; earlier recoveries stay promoted when a later step errors. One save.
    candidate = copy.deepcopy(state)
    recovered: list[str] = []
    failure: tuple[str, Exception] | None = None
    for sid, comp in selected:
        # Only a successful obligation promotes its proposed control state.
        proposed = copy.deepcopy(candidate)
        checks: list[dict[str, Any]] = []
        try:
            passed, detail = _evaluate_completion(comp, proposed, proposed['steps'][sid], checks, sid + ':completion')
        except (CompletionEvaluationError, OSError, ValueError, TypeError, re.error) as exc:
            failure = (sid, exc)
            break
        if passed:
            method = _typed_completion_method(checks)
            working = proposed['steps'][sid]
            working.update(status=STATUS_COMPLETE, completed_at=_utcnow(), completion_method=method,
                           evidence='recovered: ' + _format_completion_method(method) + '; ' + detail)
            working['receipt'] = _receipt('recover', working, checks)
            candidate = proposed
            recovered.append(sid)
    if recovered:
        save_state(candidate)
        state.clear()
        state.update(candidate)
    if failure is not None:
        failed_sid, error = failure
        raise CompletionEvaluationError(f"Step '{failed_sid}': {error}") from error
    _check_workflow_completion(state, workflow_def)
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


def _active_siblings(
    state: dict[str, Any], all_states: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """Other workflows live in the same checkout (all active minus self)."""
    wf_id = state.get("workflow_id", "")
    pool = all_states if all_states is not None else list_active_states()
    return [s for s in pool if s.get("workflow_id") != wf_id]


def _scope_lines(state: dict[str, Any], siblings: list[dict[str, Any]]) -> list[str]:
    """SCOPE (this instance's own files) + NOT-YOURS (sibling live workflows).

    C1 of the task-awareness design: a dispatched agent is TOLD its files so it
    never reconstructs "which files are mine" by browsing the shared
    `docs/<workflow>/` + `.workflow-state/`, which is how the solve-593 agent
    tripped over solve-594. Emitted only when a sibling is actually live.
    """
    wf_id = state.get("workflow_id", "")
    task_id = state.get("task_id")
    own: list[str] = []
    sf = state.get("variables", {}).get("state_file")
    if sf:
        own.append(sf)
    if task_id is not None:
        own.append(f"docs/tasks/{task_id}.yaml")
    own_str = ", ".join(own) if own else "(your state file only)"
    locs = [
        s.get("variables", {}).get("state_file")
        or f"workflow {s.get('workflow_id')}"
        for s in siblings
    ]
    return [
        f"SCOPE: you are in workflow {wf_id} (task {task_id}). Your files: {own_str}.",
        f"NOT-YOURS: {len(siblings)} other workflow(s) live in this checkout — do NOT "
        f"read or act on their files: {'; '.join(locs)}.",
    ]


def fmt_next(state: dict[str, Any], workflow_def: dict[str, Any], brief: bool = False) -> str:
    """Format the --next output."""
    _preflight_workflow(state, workflow_def)
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
    siblings = _active_siblings(state)
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

        # C1: warn when sibling workflows are live — pass --id to disambiguate
        if siblings:
            parts.append(f"NOT-YOURS: {len(siblings)} other workflow(s) live — pass --id")

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

    # C1: instance scope — own files + sibling NOT-YOURS, so a dispatched agent
    # never reconstructs "which files are mine" by browsing shared dirs.
    if siblings:
        lines.extend(_scope_lines(state, siblings))

    lines.append(f"PROGRESS: {done}/{total} done | {total - done} remaining")

    return "\n".join(lines)


def _format_completion(comp: dict[str, Any], variables: dict[str, Any]) -> str:
    """Human-readable completion description."""
    ctype = comp.get("type", "manual")
    if ctype == "manual":
        return "manual: agent-confirmed (not verified)"
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
    if ctype == "brief_check":
        return f"brief_check({_resolve_vars(comp.get('path', ''), variables)})"
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
        if ss.get("completion_method"):
            extra = f" [{_format_completion_method(ss['completion_method'])}]"
        if ss.get("evidence"):
            extra += f" [{ss['evidence'][:50]}]"
        if ss.get("selected_route"):
            extra += f" [route: {ss['selected_route']}]"
        lines.append(f"  {status:15s} {sid}{extra}")
        receipt = ss.get("receipt")
        if status in TERMINAL_STEP_STATUSES and isinstance(receipt, dict):
            lines.append(_format_receipt(receipt, PROJECT_ROOT))

    if "check_observations" in state:
        block = state["check_observations"]
        attempts = block.get("attempts") if isinstance(block, dict) else None
        count = len(attempts) if isinstance(attempts, list) else "unreadable"
        lines.append(f"Legacy check_observations: {count} attempts retained (not interpreted)")
    return "\n".join(lines)


def _format_receipt(receipt: dict[str, Any], root: Path) -> str:
    """One status line per receipt: each check's result, producer and first input identity.

    A recorded file input whose current bytes under ``root`` differ is marked ``stale``, an absent one ``missing``.
    """
    parts = []
    for check in receipt.get("checks", []):
        if not isinstance(check, dict):
            continue
        part = f"{check.get('check')}={check.get('result')}/{check.get('producer')}"
        inputs = check.get("input")
        first = inputs[0] if isinstance(inputs, list) and inputs and isinstance(inputs[0], dict) else {}
        identity = first.get("identity")
        digest = identity.get("sha256") if isinstance(identity, dict) else None
        if first.get("path") and isinstance(digest, str):
            part += f" {first['path']}@{digest[:12]}"
        if check.get("partial"):
            part += " partial"
        recorded = _recorded_file_input(check)
        if recorded:
            part += _file_input_drift(root, *recorded)
        parts.append(part)
    return f"      receipt {receipt.get('operation')} {receipt.get('at')}: " + ", ".join(parts)


def _recorded_file_input(check: dict[str, Any]) -> tuple[str, str] | None:
    """A check's first recorded input as (path, sha256) when it is a file identity with a non-empty path."""
    inputs = check.get("input")
    first = inputs[0] if isinstance(inputs, list) and inputs and isinstance(inputs[0], dict) else {}
    identity = first.get("identity")
    digest = identity.get("sha256") if isinstance(identity, dict) else None
    path = first.get("path")
    if first.get("kind") == "file" and isinstance(path, str) and path and isinstance(digest, str):
        return path, digest
    return None


def _file_input_drift(root: Path, path: str, digest: str) -> str:
    """Read-only freshness of a recorded file input: '' if the bytes match, else ' stale' or ' missing'.

    ``root`` is the project root the path was recorded against (``_capture_check_view``). Only a regular
    file is read, in chunks; anything else, or any read error, is ' missing', so a FIFO or device cannot
    hang or break a status read.
    """
    try:
        target = root / path
        if not target.is_file():
            return " missing"
        with target.open("rb") as handle:
            current = hashlib.file_digest(handle, "sha256").hexdigest()
    except (OSError, ValueError):
        return " missing"
    return "" if current == digest else " stale"


def _stale_inputs(state: dict[str, Any], root: Path) -> list[dict[str, Any]]:
    """Read-only: the recorded file inputs of terminal steps' receipts that --status marks stale or missing."""
    entries: list[dict[str, Any]] = []
    steps = state.get("steps")
    for sid, step in steps.items() if isinstance(steps, dict) else ():
        receipt = step.get("receipt") if isinstance(step, dict) else None
        if not isinstance(receipt, dict) or step.get("status") not in TERMINAL_STEP_STATUSES:
            continue
        checks = receipt.get("checks")
        for check in checks if isinstance(checks, list) else ():
            recorded = _recorded_file_input(check) if isinstance(check, dict) else None
            marker = _file_input_drift(root, *recorded).strip() if recorded else ""
            if marker:
                entries.append({"step": sid, "check": check.get("check"), "path": recorded[0], "marker": marker})
    return entries


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

        # state-file path (if known): Buddy runs --boot-context on demand when
        # returning to an in-flight workflow (boot itself does not run it; see
        # framework/workflow-engine-cookbook.md §Boot integration) and reads the
        # content state from this path without searching docs/<workflow>/
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
# Instance resolution — refuse-on-ambiguity (no silent wrong-instance guess)
# ---------------------------------------------------------------------------

class AmbiguousWorkflowError(Exception):
    """Raised when a command cannot resolve to a single workflow instance.

    >=2 candidate workflows are active and the caller gave neither --id nor a
    --task that narrows to one. The engine REFUSES rather than silently picking
    first-match / most-recent-leaf — the silent wrong-instance bug
    (solve-593 vs solve-594, both `solve`, sharing step ids in one checkout).
    Carries the candidate list for a copy-paste `--id` hint.
    """

    def __init__(self, candidates: list[dict[str, Any]], context: str = ""):
        self.candidates = candidates
        self.context = context
        super().__init__(
            f"ambiguous workflow resolution: {len(candidates)} candidates"
        )


def _resolve_unique(
    candidates: list[dict[str, Any]],
    wf_id: str | None,
    task_id: int | None,
    context: str = "",
) -> dict[str, Any] | None:
    """Resolve a candidate workflow list to exactly one instance, or refuse.

    Order: explicit `wf_id` wins; else `task_id` filters; else the N==1
    fast-path (single active candidate = the common single-workflow session,
    frictionless); else REFUSE (AmbiguousWorkflowError). Returns None only when
    nothing matches (not-found), never a silent guess among >=2.
    """
    if wf_id:
        for s in candidates:
            if s.get("workflow_id") == wf_id:
                return s
        return None
    if task_id is not None:
        matches = [s for s in candidates if _task_matches(s.get("task_id"), task_id)]
        if len(matches) == 1:
            return matches[0]
        if not matches:
            return None
        raise AmbiguousWorkflowError(matches, context)
    if len(candidates) == 1:
        return candidates[0]
    if not candidates:
        return None
    raise AmbiguousWorkflowError(candidates, context)


def _format_ambiguous(exc: AmbiguousWorkflowError) -> str:
    """Copy-paste-ready candidate list for an ambiguous-resolution refusal."""
    head = (
        f"ambiguous: {len(exc.candidates)} active workflows"
        + (f" contain step '{exc.context}'" if exc.context else " match")
        + " and no --id/--task narrows to one. Re-run with one of:"
    )
    lines = [head]
    for s in sorted(exc.candidates, key=lambda s: s.get("started", "")):
        wf = s.get("workflow", "?")
        tid = s.get("task_id")
        tid_str = f", task {tid}" if tid is not None else ""
        lines.append(f"  --id {s.get('workflow_id')}   ({wf}{tid_str})")
    return "\n".join(lines)


def _task_matches(state_task: Any, want: int) -> bool:
    """True if a state's task_id equals `want`, tolerant of int/str storage."""
    try:
        return int(state_task) == want
    except (TypeError, ValueError):
        return False


def _task_id_from_args(args: argparse.Namespace) -> int | None:
    """Resolve --task to an int, or EXIT on a malformed value.

    Distinguishes "no --task" (None -> no filter) from "--task given but
    unparseable" (error + exit) so a typo'd narrowing never silently degrades to
    the fast-path / refuse with the user believing they scoped.
    """
    if args.task is None:
        return None
    tid = resolve_task_id(args.task)
    if tid is None:
        print(f"ERROR: invalid --task value: {args.task!r}", file=sys.stderr)
        sys.exit(EXIT_VALIDATION_FAIL)
    return tid


# ---------------------------------------------------------------------------
# Finding the right active workflow for --next / --pause
# ---------------------------------------------------------------------------

def find_active_workflow_for_next(
    workflow_id: str | None,
    task_id: int | None = None,
) -> dict[str, Any] | None:
    """Find the right workflow state for --next / --pause. Prefers child workflows.

    Refuses (AmbiguousWorkflowError) when neither `workflow_id` nor `task_id` is
    given and >=2 independent (leaf) workflows are active, instead of the old
    silent most-recent-leaf guess. A child workflow (its parent spawned it) is
    the active leaf under nesting — that is resolution, not ambiguity. N==1
    stays frictionless.
    """
    states = list_active_states()
    if not states:
        return None

    if workflow_id:
        for s in states:
            if s.get("workflow_id") == workflow_id:
                return s
        return None

    # Reduce to leaves: workflows that are NOT the parent of any other active
    # workflow. Nesting is unambiguous (the innermost child is the active one);
    # ambiguity is >=2 independent leaves.
    parent_ids = {s.get("parent_workflow_id") for s in states if s.get("parent_workflow_id")}
    leaves = [s for s in states if s.get("workflow_id") not in parent_ids]
    pool = leaves if leaves else states
    return _resolve_unique(pool, None, task_id)


# Pure observational checks and creation-bound interpretation.

def _definition_projection(definition: dict[str, Any]) -> dict[str, Any]:
    """Pure semantic projection shared by creation, import and continuation."""
    projection = {k: v for k, v in definition.items()
                  if k not in {"description", "need_phrase", "trigger", "derived_from"}}
    projection.setdefault("iteration_cap", DEFAULT_ITERATION_CAP)
    projection.setdefault("routes", {})
    projection["steps"] = []
    defaults = {"required": True, "commit_gate": False, "depends_on": [],
                "on_fail": "block", "skill_ref": "", "context_refs": [], "routes": {}}
    for step in definition["steps"]:
        normalized = {k: v for k, v in step.items() if k != "name"}
        for key, value in defaults.items():
            normalized.setdefault(key, value)
        projection["steps"].append(normalized)
    return projection


def definition_fingerprint(definition: dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(_definition_projection(definition), sort_keys=True).encode()).hexdigest()


_AFFECTED_CHECKS = {"save": {"commit-push"}, "solve": {"refine", "commit-deploy"},
                    "spec_board": {"task-yaml-update", "push-board", "deploy-board"}}


def _require_interpretation(state: dict[str, Any], definition: dict[str, Any], *, reopening_step: str | None = None) -> None:
    affected = _AFFECTED_CHECKS.get(state.get("workflow"), set())
    unfinished = any(state.get("steps", {}).get(sid, {}).get("status", STATUS_PENDING)
                     not in TERMINAL_STEP_STATUSES for sid in affected)
    if not unfinished and reopening_step not in affected:
        return
    if state.get("definition_fingerprint") != definition_fingerprint(definition):
        raise CompletionEvaluationError(
            "Affected unfinished checks lack matching creation-bound definition interpretation. "
            "Preserve the run and its history; reconcile unfinished obligations explicitly before progress. "
            "The installed definition cannot establish an old run's creation provenance."
        )


def _preflight_workflow(state: dict[str, Any], definition: dict[str, Any]) -> None:
    """Run before lazy writes and mutations; terminal evidence stays historical."""
    _require_interpretation(state, definition)
    for step in definition.get("steps", []):
        if state.get("steps", {}).get(step["id"], {}).get("status") in TERMINAL_STEP_STATUSES:
            continue
        if "evidence_required" in step and type(step["evidence_required"]) is not bool:
            raise CompletionEvaluationError("evidence_required must be a boolean")
        if "guard" in step:
            guard = step["guard"]
            if not isinstance(guard, dict) or guard.get("type") not in VALID_GUARD_TYPES or guard.get("type") == "script":
                raise GuardEvaluationError("Unsupported or malformed guard; inspection cannot execute scripts")
            required_fields = {"file_exists": ("path",), "step_status": ("step_id", "expected"),
                               "route_active": ("step_id", "route")}.get(guard["type"], ())
            if any(not isinstance(guard.get(key), str) or not guard[key].strip() for key in required_fields):
                raise GuardEvaluationError("Malformed guard fields")
            if guard["type"] == "named_predicate" and (guard.get("name") not in {"council-needed", "task-yaml-ok"} or
                    isinstance(guard.get("task_id"), bool) or not isinstance(guard.get("task_id"), (str, int))):
                raise GuardEvaluationError("Malformed named predicate guard")
        if step.get("completion") is not None:
            _preflight_completion(step["completion"])


def _preflight_completion(comp: Any) -> None:
    """Structure-only recursive validation, independent of variables/force."""
    if not isinstance(comp, dict) or "type" not in comp:
        raise CompletionEvaluationError("Completion must be a mapping with type")
    ctype = comp["type"]
    if ctype not in VALID_COMPLETION_TYPES or ctype == "exit_code":
        raise CompletionEvaluationError(f"Unsupported completion type: {ctype}; inspection never executes commands")
    if ctype == "compound":
        checks = comp.get("checks")
        if not isinstance(checks, list) or not checks:
            raise CompletionEvaluationError("compound requires nonempty checks")
        for sub in checks:
            _preflight_completion(sub)
    if ctype in {"file_modified_after", "file_content_check", "brief_check"}:
        if not isinstance(comp.get("path"), str) or not comp["path"].strip():
            raise CompletionEvaluationError("File completion requires a nonempty path")
    if ctype == "file_content_check":
        if not isinstance(comp.get("pattern"), str) or not comp["pattern"]:
            raise CompletionEvaluationError("File content completion requires a pattern")
        if comp.get("condition", "has_match") not in {"has_match", "no_match"}:
            raise CompletionEvaluationError("Invalid file content condition")
    if ctype == "file_created_matching":
        patterns = comp.get("pattern")
        if not isinstance(patterns, (str, list)) or not patterns or (isinstance(patterns, list) and any(not isinstance(v, str) or not v for v in patterns)):
            raise CompletionEvaluationError("File-created completion requires nonempty patterns")
    if ctype == "pointer_check":
        if errors := validate_adoption_options(comp):
            raise CompletionEvaluationError("; ".join(errors))
        source = comp.get("source_file", comp.get("source"))
        if not isinstance(source, str) or not source:
            raise CompletionEvaluationError("Pointer completion requires source_file")
        minimum = comp.get("min_schema_version")
        if minimum is not None and (type(minimum) is not int or minimum < 0):
            raise CompletionEvaluationError("pointer_check min_schema_version must be a non-negative integer")
        fallback = comp.get("source_file_fallback")
        if fallback is not None and (not isinstance(fallback, str) or not fallback.strip()):
            raise CompletionEvaluationError("Pointer source_file_fallback requires a nonempty string")
    if ctype == "named_predicate":
        task = comp.get("task_id")
        if isinstance(task, bool) or not isinstance(task, (str, int)) or not re.fullmatch(r"(?:[0-9]+|\{[A-Za-z_][A-Za-z0-9_]*\})", str(task)):
            raise CompletionEvaluationError("named_predicate requires numeric task_id or a variable")
        if comp.get("name") not in {"council-needed", "task-yaml-ok", "task-status-done"} or not comp.get("task_id"):
            raise CompletionEvaluationError("Malformed named_predicate")


def _named_predicate(node: dict[str, Any], state: dict[str, Any], *, guard: bool = False, observed=None) -> tuple[bool, str]:
    resolved = _resolve_completion_vars(node, state.get("variables", {}))
    name = resolved.get("name")
    allowed = {"council-needed", "task-yaml-ok"}
    if not guard:
        allowed.add("task-status-done")
    if name not in allowed:
        raise CompletionEvaluationError("Unsupported named predicate")
    task_id = resolved.get("task_id")
    if isinstance(task_id, bool) or not str(task_id).isdigit():
        raise CompletionEvaluationError("named_predicate requires numeric task_id")
    task_id = int(task_id)
    if name != "task-status-done":
        passed = _named_guard_applies(name, task_id)
    else:
        import yaml
        records = []
        candidates = set(_task_yaml_candidates(task_id))
        candidates.update(path.parent / "archive" / path.name for path in list(candidates))
        for path in sorted(candidates):
            try:
                data = yaml.safe_load(_capture_check_view(path, observed if observed is not None else {}))
            except FileNotFoundError:
                continue
            except yaml.YAMLError as exc:
                raise CompletionEvaluationError(f"Malformed task record: {path}") from exc
            if not isinstance(data, dict) or type(data.get("id")) is not int or data["id"] != task_id or not isinstance(data.get("status"), str):
                raise CompletionEvaluationError(f"Malformed task identity/status: {path}")
            records.append(data)
        if len(records) > 1 and any(item != records[0] for item in records[1:]):
            raise CompletionEvaluationError("Conflicting active/archive task records")
        passed = bool(records) and records[0]["status"] == "done"
    if observed is not None:
        observed.update(predicate=name, task_id=task_id, predicate_result=passed)
        if not observed.get('checked_input'):
            observed['checked_input'] = [{'kind': 'predicate', 'name': name, 'task_id': task_id, 'result': passed}]
            observed['limits'] = ['Predicate helper dependency identity is partial']
    return passed, f"named predicate {name}: {'passed' if passed else 'negative'}"


def _continuation_definition(state: dict[str, Any]) -> dict[str, Any]:
    """Validate interpretation without evaluating guards or transitioning steps."""
    if state.get("schema_version") not in ("1", "2", 1, 2):
        raise ValueError("unsupported state schema")
    if type(state.get("revision", 0)) is not int or state.get("revision", 0) < 0:
        raise ValueError("invalid state revision")
    if not isinstance(state.get("variables"), dict) or not isinstance(state.get("steps"), dict):
        raise ValueError("invalid state variables or steps")
    if "paused" in state and type(state["paused"]) is not bool:
        raise ValueError("invalid paused state")
    definition_path = discover_workflow_yaml(state.get("workflow", ""))
    if not definition_path:
        raise ValueError("workflow definition unavailable")
    definition = load_workflow_yaml(definition_path)
    declared = {step["id"]: step for step in definition["steps"]}
    if set(state["steps"]) != set(declared):
        raise ValueError("workflow step vocabulary changed")
    if state.get("current_step") is not None and state["current_step"] not in declared:
        raise ValueError("unknown current step")
    route = state.get("selected_route")
    if route is not None and route not in definition.get("routes", {}):
        raise ValueError("unknown selected route")
    valid = TERMINAL_STEP_STATUSES | {STATUS_PENDING, STATUS_IN_PROGRESS}
    for step_id, step in state["steps"].items():
        if not isinstance(step, dict) or step.get("status") not in valid:
            raise ValueError("unknown step status")
        if step.get("route") is not None and step["route"] not in declared[step_id].get("routes", {}):
            raise ValueError("unknown classification route")
    return _definition_projection(definition)



def _maintenance_definition(state: dict[str, Any], *, archived: bool) -> dict[str, Any]:
    """Observe retained history without authorizing historical execution.

    Validate the carrier before considering terminality. Only acknowledged archived
    completion or abort can outlive current definition vocabulary. The deterministic
    history projection is private to maintenance; ordinary continuation stays strict.
    """
    if not isinstance(state, dict):
        raise ValueError("invalid retained state")
    if type(state.get("schema_version")) not in (str, int) or state["schema_version"] not in ("1", "2", 1, 2):
        raise ValueError("unsupported state schema")
    for key in ("workflow_id", "workflow"):
        if not isinstance(state.get(key), str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", state[key]):
            raise ValueError("invalid retained state identity")
    if type(state.get("revision", 0)) is not int or state.get("revision", 0) < 0:
        raise ValueError("invalid state revision")
    if not isinstance(state.get("variables"), dict) or not isinstance(state.get("steps"), dict) or not state["steps"]:
        raise ValueError("invalid state variables or steps")
    if "paused" in state and type(state["paused"]) is not bool:
        raise ValueError("invalid paused state")
    valid = TERMINAL_STEP_STATUSES | {STATUS_PENDING, STATUS_IN_PROGRESS}
    for step_id, step in state["steps"].items():
        if not isinstance(step_id, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", step_id):
            raise ValueError("invalid retained step identity")
        if not isinstance(step, dict) or not isinstance(step.get("status"), str) or step["status"] not in valid:
            raise ValueError("unknown step status")
        route = step.get("route")
        if route is not None and (not isinstance(route, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", route)):
            raise ValueError("invalid retained classification route")
    current = state.get("current_step")
    if current is not None and (not isinstance(current, str) or current not in state["steps"]):
        raise ValueError("unknown current step")
    route = state.get("selected_route")
    if route is not None and (not isinstance(route, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", route)):
        raise ValueError("invalid retained selected route")
    for marker in ("completed", "aborted"):
        if marker in state:
            value = state[marker]
            if not isinstance(value, str) or not value.strip():
                raise ValueError("invalid retained lifecycle marker")
            try:
                timestamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
                if "T" not in value or timestamp.tzinfo is None:
                    raise ValueError("lifecycle marker requires a timestamp with timezone")
            except ValueError as exc:
                raise ValueError("invalid retained lifecycle marker") from exc
    if "completed" in state and "aborted" in state:
        raise ValueError("contradictory retained lifecycle markers")
    completed = "completed" in state and not state.get("paused") and all(
        step["status"] in TERMINAL_STEP_STATUSES - {STATUS_ESCALATED} for step in state["steps"].values())
    if archived and ("aborted" in state or completed):
        # Includes all retained meaning, independent of either generation's loader.
        # Never returned by the public continuation/export APIs.
        return {"terminal_history": state}
    return _continuation_definition(state)


def continuation_compatible(workflow: str, observed_fingerprint: str,
                            current_fingerprint: str, *, direction: str | None = None) -> bool:
    """Accept identity or an exact, reviewed directional definition transition."""
    if direction not in (None, "upgrade", "rollback"):
        raise ValueError("unknown compatibility direction")
    if any(not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{64}", value)
           for value in (observed_fingerprint, current_fingerprint)):
        return False
    if observed_fingerprint == current_fingerprint:
        return True
    import yaml
    manifest = FRAMEWORK_ROOT / "framework/workflow-compatibility.yaml"
    try:
        data = yaml.safe_load(manifest.read_text())
        if not isinstance(data, dict) or data.get("version") != 1:
            return False
        for mapping in data.get("mappings", []):
            if (mapping.get("workflow") != workflow or mapping.get("review_status") != "accepted"
                    or not mapping.get("preserved_obligations")):
                continue
            for selected in ("upgrade", "rollback") if direction is None else (direction,):
                if selected not in mapping.get("allowed_directions", []):
                    continue
                pair = (mapping.get("prior"), mapping.get("current"))
                if selected == "rollback":
                    pair = pair[::-1]
                if pair == (observed_fingerprint, current_fingerprint):
                    return True
    except (OSError, ValueError, TypeError, AttributeError, yaml.YAMLError):
        return False
    return False


def continuation_lifecycle(state: dict[str, Any], *, archived: bool = False) -> dict[str, Any]:
    """Successful closure requires acknowledged archive placement; abort stays distinct."""
    if state.get("aborted"):
        return {"status": "aborted", "terminal": True}
    if archived and not state.get("paused") and state.get("completed") and all(
            step["status"] in TERMINAL_STEP_STATUSES - {STATUS_ESCALATED} for step in state["steps"].values()):
        return {"status": "completed", "terminal": True}
    return {"status": "paused" if state.get("paused") else "active", "terminal": False}


def export_selected_states(
    project_root: Path, workflow_ids: list[str], references: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Engine-owned exact snapshot. Never selects by presence or changes state.

    All selected runs are observed under the engine's existing lock. An archived
    run must have exactly one matching identity; ambiguity is always a blocker.
    """
    if not isinstance(workflow_ids, list) or any(
        not isinstance(wid, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", wid)
        for wid in workflow_ids
    ) or len(workflow_ids) != len(set(workflow_ids)):
        raise ValueError("explicit unique workflow IDs required")
    references = references or {}
    if not isinstance(references, dict) or set(references) - set(workflow_ids):
        raise ValueError("invalid state references")
    result: dict[str, Any] = {"schema_version": 1, "states": [], "blockers": []}
    if not workflow_ids:
        return result
    root = project_root.resolve(strict=True)
    directory = root / ".workflow-state"
    if not directory.is_dir():
        result["blockers"] = [{"workflow_id": wid, "reason": "state_missing"} for wid in workflow_ids]
        return result
    if fcntl is None:
        raise ValueError("state locking unavailable")
    if directory.is_symlink() or (directory / "_lock").is_symlink():
        raise ValueError("unsafe state directory")
    with _state_lock(directory):
        for wid in workflow_ids:
            try:
                reference = references.get(wid, f".workflow-state/{wid}.json")
                if not isinstance(reference, str):
                    raise ValueError("invalid state reference")
                given = Path(reference)
                source = given if given.is_absolute() else root / given
                if ".." in given.parts or not source.is_relative_to(directory):
                    raise ValueError("state reference outside owner")
                candidates = []
                # Identity uniqueness is global even after a reference relocates.
                # Inspect identity only for unrelated runs; never export their contents.
                paths = sorted(directory.glob("*.json"))
                if (directory / "archive").is_dir():
                    paths += sorted((directory / "archive").glob("*.json"))
                if source.exists() and source not in paths:
                    raise ValueError("state reference outside allowed owner paths")
                for path in paths:
                    if path.is_symlink() or not path.resolve().is_relative_to(directory):
                        raise ValueError("unsafe state reference")
                    try:
                        raw = path.read_bytes()
                        state = json.loads(raw)
                    except (OSError, ValueError):
                        if path == source:
                            raise
                        continue
                    if path == source and (not isinstance(state, dict) or state.get("workflow_id") != wid):
                        raise ValueError("state reference identity mismatch")
                    if isinstance(state, dict) and state.get("workflow_id") == wid:
                        candidates.append((path, raw, state))
                if len(candidates) != 1:
                    raise ValueError("state missing or ambiguous")
                path, raw, state = candidates[0]
                interpretation = _continuation_definition(state)
                result["states"].append({"workflow_id": wid, "state_file": str(path.relative_to(root)),
                    "revision": state.get("revision", 0), "sha256": hashlib.sha256(raw).hexdigest(),
                    "definition_fingerprint": hashlib.sha256(json.dumps(interpretation, sort_keys=True).encode()).hexdigest(),
                    "state": state, "lifecycle": continuation_lifecycle(state, archived=path.parent == directory / "archive"),
                    # Read-only freshness against this root, never PROJECT_ROOT; information, not a blocker.
                    "stale_inputs": _stale_inputs(state, root)})
            except (OSError, ValueError, TypeError, KeyError, SchemaError) as exc:
                result["blockers"].append({"workflow_id": wid, "reason": str(exc)})
    return result

# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="forge Workflow Engine",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--review-capture", metavar="STEP", help="Capture current review subject from JSON stdin; explicit --id required (evidence-pointer protocol §9)")
    group.add_argument("--review-adopt", metavar="STEP", help="Retain qualified explicit decision; --id and --verdict required")
    group.add_argument("--review-check", metavar="STEP", help="Read-only exact current review check; --id and --review-policy required")
    group.add_argument("--export-selected", action="store_true", help="Read exact explicitly selected state; JSON request on stdin")
    group.add_argument("--start", metavar="WORKFLOW", help="Start a new workflow")
    group.add_argument("--next", action="store_true", help="Show next step")
    group.add_argument("--complete", metavar="STEP_ID", help="Complete a step")
    group.add_argument("--skip", metavar="STEP_ID", help="Skip a step")
    group.add_argument("--retry", metavar="STEP_ID",
                        help="Reopen in-progress or terminal step, preserve review history and increment iteration")
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
    group.add_argument("--reap", action="store_true",
                        help="Archive stale (long-idle) active workflows")

    # Shared options
    parser.add_argument("--verdict", help="Project-relative retained Buddy decision path for --review-adopt")
    parser.add_argument("--review-policy", help="evidence | spec_success | code_success for --review-check")
    parser.add_argument("--task", type=str, default=None, help="Task ID")
    parser.add_argument("--id", type=str, default=None, dest="wf_id", help="Workflow ID")
    parser.add_argument("--parent", type=str, default=None, help="Parent workflow ID")
    parser.add_argument("--brief", action="store_true", help="Brief output for hooks")
    parser.add_argument("--route", type=str, default=None, help="Route key for classification")
    parser.add_argument("--evidence", type=str, default=None, help="Evidence text")
    parser.add_argument("--force", action="store_true", help="Force complete ordinary checks; mandatory review and brief checks cannot be bypassed")
    parser.add_argument("--set", nargs=2, action="append", metavar=("KEY", "VALUE"),
                        default=None, help="Set state variable")
    parser.add_argument("--reason", type=str, default=None, help="Reason for skip/abort")
    parser.add_argument("--format", type=str, default=None, dest="fmt", help="Output format")
    parser.add_argument("--available", action="store_true", help="Include available definitions")
    parser.add_argument("--before-commit", action="store_true", help="Check commit gates")
    parser.add_argument("--max-age-hours", type=int, default=None, dest="max_age_hours",
                        help="--reap staleness threshold in hours (default 168 = 7d)")
    parser.add_argument("--dry-run", action="store_true", dest="dry_run",
                        help="--reap: list what would be archived, change nothing")
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

    # explicit --project-root override. Rebinds the
    # project-scoped module globals so that state discovery + completion
    # checks resolve against the new root.
    if args.project_root:
        global PROJECT_ROOT, STATE_DIR, ARCHIVE_DIR, REPO_ROOT
        PROJECT_ROOT = Path(args.project_root).resolve()
        STATE_DIR = PROJECT_ROOT / ".workflow-state"
        ARCHIVE_DIR = STATE_DIR / "archive"
        REPO_ROOT = PROJECT_ROOT  # keep back-compat alias in sync

    # Dispatch. Any resolver that cannot narrow to one workflow raises
    # AmbiguousWorkflowError — caught here and rendered as a LOUD refusal with
    # a copy-paste --id list + EXIT_AMBIGUOUS, never a silent wrong-instance guess.
    try:
        if args.review_capture or args.review_adopt or args.review_check:
            cmd_review(args)
        elif args.export_selected:
            try:
                request = json.load(sys.stdin)
                result = export_selected_states(PROJECT_ROOT, request.get("workflow_ids"), request.get("references"))
                print(json.dumps(result))
                sys.exit(4 if result["blockers"] else 0)
            except (ValueError, TypeError, OSError) as exc:
                print(json.dumps({"schema_version": 1, "states": [], "blockers": [str(exc)]}))
                sys.exit(4)
        elif args.start:
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
        elif args.reap:
            cmd_reap(args)
    except AmbiguousWorkflowError as exc:
        print(f"ERROR: {_format_ambiguous(exc)}", file=sys.stderr)
        sys.exit(EXIT_AMBIGUOUS)
    except GuardEvaluationError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(EXIT_GUARD_ERROR)
    except CompletionEvaluationError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(EXIT_VALIDATION_FAIL)
    except StaleStateError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(EXIT_STALE_STATE)
    except (ValueError, TypeError, OSError, SchemaError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(EXIT_VALIDATION_FAIL)


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

    # Validate even the first step's guard before presenting work to execute.
    next_id = find_next_step(state, workflow_def)
    if not next_id:
        _check_workflow_completion(state, workflow_def)
    output = fmt_next(state, workflow_def) if next_id else ""
    if output:
        print(output)
    else:
        print(f"Workflow '{workflow_name}' started (id: {state['workflow_id']}) — no steps.")


def cmd_next(args: argparse.Namespace) -> None:
    state = find_active_workflow_for_next(args.wf_id, _task_id_from_args(args))
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

    next_id = find_next_step(state, workflow_def)
    if not next_id:
        _check_workflow_completion(state, workflow_def)
        return
    if state.get("current_step") != next_id:
        state["current_step"] = next_id
        save_state(state)

    output = fmt_next(state, workflow_def, brief=args.brief)
    if output:
        print(output)


def cmd_complete(args: argparse.Namespace) -> None:
    step_id = args.complete
    wf_id = args.wf_id

    # Find the workflow that contains this step
    state = _find_state_for_step(step_id, wf_id, _task_id_from_args(args))
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

    if refusal := _progress_refusal(state):
        raise CompletionEvaluationError(refusal)
    _preflight_workflow(state, workflow_def)
    _require_invocation_evidence(_get_step_def(workflow_def, step_id), args.evidence)

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

    state = _find_state_for_step(step_id, args.wf_id, _task_id_from_args(args))
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
    if not reason or not reason.strip():
        print("ERROR: --skip requires --reason", file=sys.stderr)
        sys.exit(EXIT_VALIDATION_FAIL)

    state = _find_state_for_step(step_id, args.wf_id, _task_id_from_args(args))
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
        states = [load_state(args.wf_id)]
    elif args.task is not None:
        # Scope to the named task — recover must NOT silently sweep + mutate
        # every instance when the caller asked for one. Refuse if
        # the task itself is ambiguous (same task id across >1 live workflow).
        tid = _task_id_from_args(args)
        states = [s for s in list_active_states() if _task_matches(s.get("task_id"), tid)]
        if len(states) > 1:
            raise AmbiguousWorkflowError(states)
    else:
        states = list_active_states()  # explicit sweep-all (maintenance use)

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
            method = state["steps"][sid]["completion_method"]
            total_recovered.append(f"{state.get('workflow_id')}: {sid} ({_format_completion_method(method)})")

    if total_recovered:
        print(f"Recovered {len(total_recovered)} step(s):")
        for r in total_recovered:
            print(f"  {r}")
    else:
        print("No steps recovered.")


def cmd_reap(args: argparse.Namespace) -> None:
    """Archive active workflows idle longer than the staleness threshold.

    Stale = no `started` / step activity within --max-age-hours (default 168 =
    7d). Paused workflows are never reaped. --dry-run lists candidates without
    changing anything. Clears the abandonment litter that pollutes
    list_active_states() + a dispatched agent's perception of "which workflows
    are live" (the deferred reaper).
    """
    max_age_hours = args.max_age_hours if args.max_age_hours is not None else 168
    if max_age_hours < 1:
        print(
            f"ERROR: --max-age-hours must be >= 1 (got {max_age_hours}); refusing "
            f"to reap recently-active workflows.",
            file=sys.stderr,
        )
        sys.exit(EXIT_VALIDATION_FAIL)
    now = datetime.now(UTC)
    cutoff = now - timedelta(hours=max_age_hours)

    # Scan: ids whose last recorded activity is older than the cutoff. Skip
    # paused + malformed (no workflow_id) states.
    candidate_ids: list[str] = []
    for state in list_active_states():
        if not isinstance(state, dict) or state.get("paused"):
            continue
        wid = state.get("workflow_id")
        last = _last_activity(state)
        if wid and last is not None and last < cutoff:
            candidate_ids.append(wid)

    if not candidate_ids:
        print(f"No stale workflows (idle > {max_age_hours}h).")
        return

    reaped = 0
    for wid in candidate_ids:
        # Re-read fresh + re-verify immediately before acting. The scan snapshot
        # may be stale (another session advanced the workflow); writing it back
        # would overwrite live content with dead state. If it
        # advanced past the cutoff since the scan, leave it.
        fresh = _load_state_quiet(wid)
        if fresh is None:
            continue  # archived / removed concurrently
        last = _last_activity(fresh)
        if last is None or last >= cutoff:
            continue
        idle_h = (now - last).total_seconds() / 3600
        if args.dry_run:
            print(f"WOULD REAP: {wid} (idle {idle_h:.0f}h, last {last.isoformat()})")
            reaped += 1
            continue
        try:
            # Normalize dangling in_progress steps (parity with --abort closeout).
            for ss in fresh.get("steps", {}).values():
                if isinstance(ss, dict) and ss.get("status") == STATUS_IN_PROGRESS:
                    ss["status"] = STATUS_SKIPPED
                    ss["skipped_reason"] = "reaped: stale"
                    ss["completed_at"] = _utcnow()
            fresh["aborted"] = _utcnow()
            fresh["abort_reason"] = f"reaped: stale, idle {idle_h:.0f}h (> {max_age_hours}h)"
            save_state(fresh)
            archive_state(wid, expected_revision=fresh["revision"])
            print(f"REAPED: {wid} (idle {idle_h:.0f}h, last {last.isoformat()})")
            reaped += 1
        except Exception as exc:  # noqa: BLE001 — one bad state must not abort the sweep
            print(f"WARNING: could not reap {wid}: {exc}", file=sys.stderr)

    if args.dry_run:
        print(f"\n{reaped} stale — re-run without --dry-run to archive.")
    else:
        print(f"\nReaped {reaped} stale workflow(s).")


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
    archive_state(wf_id, expected_revision=state["revision"])
    touched_info = f" (closeout: {len(touched_steps)} step(s))" if touched_steps else ""
    print(f"Workflow '{wf_id}' aborted: {reason}{touched_info}")


def cmd_pause(args: argparse.Namespace) -> None:
    """Pause the active workflow (F4)."""
    state = find_active_workflow_for_next(args.wf_id, _task_id_from_args(args))
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
    which prefers leaf workflows regardless of paused status.
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

    if guard_name not in {"council-needed", "task-yaml-ok"}:
        print(f"Unknown guard: {guard_name}", file=sys.stderr)
        sys.exit(EXIT_GUARD_ERROR)
    tid = resolve_task_id(task_id)
    if tid is None or tid <= 0:
        print(f"ERROR: Guard '{guard_name}' requires a valid positive task ID", file=sys.stderr)
        sys.exit(EXIT_GUARD_ERROR)

    try:
        applicable = _named_guard_applies(guard_name, tid)
    except (OSError, ValueError) as exc:
        print(f"ERROR: Guard '{guard_name}' evaluation failed: {exc}", file=sys.stderr)
        sys.exit(EXIT_GUARD_ERROR)
    sys.exit(EXIT_SUCCESS if applicable else EXIT_VALIDATION_FAIL)


def _named_guard_applies(guard_name: str, task_id: int) -> bool:
    """Only a successfully evaluated negative may produce guard exit 1."""
    if guard_name == "council-needed":
        # Council is Buddy-judgmental (skills/council/SKILL.md §1.0
        # proportionality gate is the SoT, not an engine heuristic).
        # Opt-in mechanism: Buddy writes `council-required: true` in the
        # state file (frontmatter or body marker) when frame report's
        # >1-path + hard-to-reverse criteria fire. Guard greps for it.
        # Default = skip; council fires when Buddy explicitly marks it.
        rel = _discover_state_file(task_id, strict=True)
        if not rel:
            return False
        content = (PROJECT_ROOT / rel).read_text(errors="replace")
        return "council-required: true" in content or "council_required: true" in content

    task_path = PROJECT_ROOT / "docs" / "tasks" / f"{task_id:03d}.yaml"
    try:
        task_path.stat()
    except FileNotFoundError:
        return False
    return True


def _find_state_for_step(
    step_id: str, wf_id: str | None = None, task_id: int | None = None,
) -> dict[str, Any] | None:
    """Find the active state containing the given step, resolving to exactly one.

    Refuses (AmbiguousWorkflowError) when neither `wf_id` nor `task_id` resolves
    and >=2 active workflows contain the step — the silent first-match bug
    (--complete/--skip/--retry <step> hitting the wrong instance). N==1 stays
    frictionless.
    """
    if wf_id:
        state = load_state(wf_id)
        if step_id in state.get("steps", {}):
            return state
        return None

    candidates = [
        s for s in list_active_states() if step_id in s.get("steps", {})
    ]
    return _resolve_unique(candidates, None, task_id, context=step_id)


if __name__ == "__main__":
    main()
