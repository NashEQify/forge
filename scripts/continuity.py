#!/usr/bin/env python3
"""Coherent scoped snapshots and recoverable publication for cooperating writers.

JSON requests use stdin, responses stdout. Semantic reconciliation belongs to KP.
The advisory lock does not protect against nonparticipating external writers.
"""

from __future__ import annotations

import argparse
import base64
import contextlib
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import sys
import tempfile
from typing import Any

try:
    import fcntl
except ImportError:
    fcntl = None

try:
    from .user_scope import (
        ContinuityScope,
        config_path,
        from_config,
        load_config,
        resolve_continuity_scope,
    )
except ImportError:
    from user_scope import (
        ContinuityScope,
        config_path,
        from_config,
        load_config,
        resolve_continuity_scope,
    )

SCHEMA_VERSION = 1
FENCE = re.compile(
    r"\A# Pending continuity reconciliation\n\n```forge-continuity\n(.*?)\n```\n\Z",
    re.S,
)
MAX_METADATA = 64 * 1024


class ContinuityError(ValueError):
    """A precise failure which never includes request payload text."""

    def __init__(
        self, reason: str, code: int = 2, *, affected: list[str] | None = None
    ):
        super().__init__(reason)
        self.reason, self.code, self.affected = reason, code, affected or []


def _hash(text: str | None) -> str | None:
    return (
        hashlib.sha256(text.encode("utf-8")).hexdigest() if text is not None else None
    )


def _identity(scope: ContinuityScope) -> dict[str, str]:
    return {
        "kind": scope.kind,
        "owner_root": str(scope.owner_root),
        "content_root": str(scope.content_root),
    }


def _safe_path(
    scope: ContinuityScope, relative: str, *, internal: bool = False
) -> Path:
    if not isinstance(relative, str) or not relative or "\\" in relative:
        raise ContinuityError("invalid_path")
    rel = PurePosixPath(relative)
    if rel.is_absolute() or any(p in {"", ".", ".."} for p in relative.split("/")):
        raise ContinuityError("invalid_path")
    path = (
        scope.owner_root if internal or scope.kind == "project" else scope.content_root
    ) / relative
    if not path.is_relative_to(scope.content_root):
        raise ContinuityError("path_outside_scope")
    if scope.kind == "project" and path.is_relative_to(
        scope.owner_root / "context/user"
    ):
        raise ContinuityError("personal_path_in_project_scope")
    if not internal and (
        path in {scope.pending_path, scope.lock_path}
        or any(
            p in {".git", ".workflow-state", ".codex", ".agents", ".claude"}
            or p.startswith(".continuity-")
            for p in rel.parts
        )
    ):
        raise ContinuityError("reserved_control_path")
    for item in (path, *path.parents):
        if item == scope.owner_root:
            break
        try:
            info = item.lstat()
        except FileNotFoundError:
            continue
        if stat.S_ISLNK(info.st_mode):
            raise ContinuityError("symlink_path")
        if item == path:
            if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
                raise ContinuityError("unsafe_file_type")
        elif not stat.S_ISDIR(info.st_mode):
            raise ContinuityError("unsafe_parent_type")
    return path


def _rel(scope: ContinuityScope, path: Path) -> str:
    return path.relative_to(scope.owner_root).as_posix()


def _read(
    scope: ContinuityScope, relative: str, *, internal: bool = False
) -> str | None:
    path = _safe_path(scope, relative, internal=internal)
    try:
        with path.open(encoding="utf-8", newline="") as stream:
            return stream.read()
    except FileNotFoundError:
        return None


def _fsync_dir(path: Path) -> None:
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _mkdir_durable(path: Path) -> None:
    missing = []
    current = path
    while not current.exists():
        missing.append(current)
        current = current.parent
    for directory in reversed(missing):
        directory.mkdir(mode=0o700, exist_ok=True)
        _fsync_dir(directory.parent)


def _atomic_write(path: Path, text: str | None) -> None:
    """Durably replace one file, retaining its mode. Also used for the journal."""
    if text is None:
        if path.exists():
            path.unlink()
            _fsync_dir(path.parent)
        return
    _mkdir_durable(path.parent)
    mode = stat.S_IMODE(path.stat().st_mode) if path.exists() else 0o600
    fd, name = tempfile.mkstemp(prefix=".continuity-", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as stream:
            os.fchmod(stream.fileno(), mode)
            stream.write(text)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(name, path)
        _fsync_dir(path.parent)
    finally:
        if os.path.exists(name):
            os.unlink(name)


@contextlib.contextmanager
def _scope_lock(scope: ContinuityScope):
    if fcntl is None:
        raise ContinuityError("locking_unavailable", 4)
    path = _safe_path(scope, _rel(scope, scope.lock_path), internal=True)
    _mkdir_durable(path.parent)
    fd = os.open(path, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
            raise ContinuityError("unsafe_lock")
        fcntl.flock(fd, fcntl.LOCK_EX)
        yield
    finally:
        os.close(fd)


def _pending(scope: ContinuityScope) -> tuple[str | None, list[dict[str, Any]]]:
    text = _read(scope, _rel(scope, scope.pending_path), internal=True)
    if text is None:
        return None, []
    match = FENCE.fullmatch(text)
    if not match:
        raise ContinuityError("unrecognized_pending_record", 4)
    try:
        payload = json.loads(match[1])
        if payload["schema_version"] != SCHEMA_VERSION or payload["scope"] != _identity(
            scope
        ):
            raise ValueError
        operations = payload["operations"]
        if not isinstance(operations, list):
            raise ValueError
        identities = set()
        for op in operations:
            if (
                not isinstance(op, dict)
                or not isinstance(op["operation_id"], str)
                or op["operation_id"] in identities
            ):
                raise ValueError
            identities.add(op["operation_id"])
            for path in _paths(op["affected_paths"]):
                _safe_path(scope, path)
                if path not in op["baselines"] or path not in op["proposed_hashes"]:
                    raise ValueError
        return text, operations
    except (KeyError, TypeError, ValueError) as exc:
        raise ContinuityError("invalid_pending_record", 4) from exc


def _write_pending(scope: ContinuityScope, operations: list[dict[str, Any]]) -> None:
    _safe_path(scope, _rel(scope, scope.pending_path), internal=True)
    text = None
    if operations:
        data = {
            "schema_version": SCHEMA_VERSION,
            "scope": _identity(scope),
            "operations": operations,
        }
        text = (
            "# Pending continuity reconciliation\n\n```forge-continuity\n"
            + json.dumps(data, ensure_ascii=False, indent=2)
            + "\n```\n"
        )
    _atomic_write(scope.pending_path, text)


def _paths(value: Any) -> list[str]:
    if not isinstance(value, list) or any(not isinstance(p, str) for p in value):
        raise ContinuityError("paths_must_be_strings")
    if len(value) != len(set(value)):
        raise ContinuityError("duplicate_paths")
    return value


def _decode(scope: ContinuityScope, token: Any) -> dict[str, Any]:
    if isinstance(token, dict):
        token = token.get("snapshot_token")
    try:
        data = json.loads(base64.urlsafe_b64decode(token.encode("ascii")))
        if data["schema_version"] != SCHEMA_VERSION or data["scope"] != _identity(
            scope
        ):
            raise ValueError
        if not isinstance(data["baselines"], dict) or "pending_hash" not in data:
            raise ValueError
        for path, value in data["baselines"].items():
            _safe_path(scope, path)
            if value is not None and (
                not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{64}", value)
            ):
                raise ValueError
        return data
    except (ValueError, TypeError, KeyError, AttributeError, UnicodeError) as exc:
        raise ContinuityError("invalid_snapshot_token") from exc


def _capture(
    scope: ContinuityScope, paths: list[str], previous: dict | None = None
) -> dict:
    pending_text, operations = _pending(scope)
    files = {}
    for path in sorted(paths):
        content = _read(scope, path)
        files[path] = {"text": content, "sha256": _hash(content)}
    baselines = {p: item["sha256"] for p, item in files.items()}
    payload = {
        "schema_version": SCHEMA_VERSION,
        "scope": _identity(scope),
        "baselines": baselines,
        "pending_hash": _hash(pending_text),
    }
    token = base64.urlsafe_b64encode(
        json.dumps(payload, sort_keys=True).encode()
    ).decode()
    invalid = [
        p
        for p, value in (previous or {}).get("baselines", {}).items()
        if baselines.get(p) != value
    ]
    return {
        "schema_version": SCHEMA_VERSION,
        "scope": _identity(scope),
        "status": "complete",
        "snapshot_token": token,
        "files": files,
        "pending_operations": operations,
        "invalidated_paths": sorted(invalid),
        "pending_changed": previous is not None
        and previous["pending_hash"] != payload["pending_hash"],
    }


def snapshot(scope: ContinuityScope, request: dict) -> dict:
    paths = set(_paths(request.get("paths", [])))
    previous = _decode(scope, request["previous"]) if request.get("previous") else None
    if previous:
        paths.update(previous["baselines"])
    with _scope_lock(scope):
        return _capture(scope, sorted(paths), previous)


def publish(scope: ContinuityScope, request: dict) -> dict:
    baseline = _decode(scope, request.get("snapshot_token"))
    affected = _paths(request.get("affected_paths"))
    replacements = request.get("replacements")
    if not isinstance(replacements, dict) or any(
        not isinstance(v, (str, type(None))) for v in replacements.values()
    ):
        raise ContinuityError("invalid_replacements")
    for path in set(affected) | set(replacements):
        _safe_path(scope, path)
    if not set(replacements) <= set(affected) <= set(baseline["baselines"]):
        raise ContinuityError("affected_paths_not_observed")
    operation_id = request.get("operation_id")
    if not isinstance(operation_id, str) or not re.fullmatch(
        r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}", operation_id
    ):
        raise ContinuityError("invalid_operation_id")
    intention, sources = (
        request.get("intended_change"),
        request.get("source_references"),
    )
    if (
        not isinstance(intention, str)
        or not isinstance(sources, list)
        or any(not isinstance(s, str) for s in sources)
    ):
        raise ContinuityError("invalid_recovery_metadata")
    if len(json.dumps([intention, sources]).encode()) > MAX_METADATA:
        raise ContinuityError("recovery_metadata_too_large")
    recovery = request.get("recovery_operation_id")
    with _scope_lock(scope):
        pending_text, operations = _pending(scope)
        current = {p: _read(scope, p) for p in baseline["baselines"]}
        stale = [
            p for p, text in current.items() if _hash(text) != baseline["baselines"][p]
        ]
        if stale or _hash(pending_text) != baseline["pending_hash"]:
            raise ContinuityError("stale_baseline", 3, affected=stale)
        target = next((op for op in operations if op["operation_id"] == recovery), None)
        if recovery and (not target or recovery != operation_id):
            raise ContinuityError("recovery_operation_missing", 4)
        if target and not set(target["affected_paths"]) <= set(affected):
            raise ContinuityError("incomplete_reconciliation", 4)
        for op in operations:
            if op is target:
                continue
            if op["operation_id"] == operation_id or set(op["affected_paths"]) & set(
                baseline["baselines"]
            ):
                raise ContinuityError("pending_operation_overlap", 4)
        changed = {p: text for p, text in replacements.items() if text != current[p]}
        if not changed and not target:
            return {
                "schema_version": 1,
                "status": "complete",
                "affected_paths": [],
                "pending_operations": operations,
            }
        durable = target is not None or len(affected) > 1
        completed = []
        if durable:
            result = {p: replacements.get(p, current[p]) for p in affected}
            record = {
                "operation_id": operation_id,
                "affected_paths": affected,
                "baselines": {p: baseline["baselines"][p] for p in affected},
                "intended_change": intention,
                "source_references": sources,
                "proposed_hashes": {p: _hash(text) for p, text in result.items()},
                "proposed_replacements": result,
                "completed": [],
                "remaining": list(affected),
            }
            operations = [record if op is target else op for op in operations]
            if not target:
                operations.append(record)
            _write_pending(scope, operations)
        try:
            for path, text in changed.items():
                _atomic_write(_safe_path(scope, path), text)
                completed.append(path)
                if durable:
                    record["completed"] = list(completed)
                    record["remaining"] = [p for p in affected if p not in completed]
                    _write_pending(scope, operations)
            if durable:
                operations = [
                    op for op in operations if op["operation_id"] != operation_id
                ]
                _write_pending(scope, operations)
        except OSError as exc:
            # Actual disk content is authoritative, including a failed fsync after replace.
            raise ContinuityError(
                "publication_interrupted", 4, affected=affected
            ) from exc
        return {
            "schema_version": 1,
            "status": "complete",
            "affected_paths": list(changed),
            "pending_operations": operations,
        }


def recover(scope: ContinuityScope, request: dict) -> dict:
    with _scope_lock(scope):
        _, operations = _pending(scope)
        requested = set(_paths(request.get("paths", [])))
        # Only relevant operations join the snapshot; unrelated records stay visible
        # but do not make their owners dependencies of this reconciliation.
        relevant = [
            op
            for op in operations
            if not requested or requested & set(op["affected_paths"])
        ]
        paths = requested | {p for op in relevant for p in op["affected_paths"]}
        captured = _capture(scope, sorted(paths))
        results = []
        for op in operations:
            classifications = {}
            if op in relevant:
                for path in op["affected_paths"]:
                    actual = captured["files"][path]["sha256"]
                    classifications[path] = (
                        "proposed"
                        if actual == op["proposed_hashes"][path]
                        else "original"
                        if actual == op["baselines"][path]
                        else "changed"
                    )
            results.append({**op, "classifications": classifications})
        return {
            "schema_version": 1,
            "status": "reconciliation_pending" if relevant else "complete",
            "snapshot": captured,
            "operations": results,
        }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("snapshot", "publish", "recover"))
    parser.add_argument("--scope", choices=("project", "personal"), required=True)
    parser.add_argument("--project-root", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        request = json.load(sys.stdin)
        if not isinstance(request, dict) or request.get("schema_version", 1) != 1:
            raise ContinuityError("unsupported_request")
        user = None
        if args.scope == "personal":
            cfg = config_path(os.environ)
            data, warnings = load_config(cfg) if cfg else (None, [])
            user = from_config(
                Path(__file__).resolve().parents[1], data, config=cfg, warnings=warnings
            )
        scope = resolve_continuity_scope(args.scope, args.project_root, user)
        response = {"snapshot": snapshot, "publish": publish, "recover": recover}[
            args.command
        ](scope, request)
        print(json.dumps(response, ensure_ascii=False))
        return 0
    except (ContinuityError, OSError, ValueError) as exc:
        code = exc.code if isinstance(exc, ContinuityError) else 2
        reason = (
            exc.reason
            if isinstance(exc, ContinuityError)
            else "invalid_request_or_access"
        )
        status = (
            "owner_updated_reconciliation_pending"
            if reason == "publication_interrupted"
            else "not_persisted"
        )
        print(
            json.dumps(
                {
                    "schema_version": 1,
                    "status": status,
                    "reason": reason,
                    "affected_paths": exc.affected
                    if isinstance(exc, ContinuityError)
                    else [],
                }
            )
        )
        return code


if __name__ == "__main__":
    sys.exit(main())
