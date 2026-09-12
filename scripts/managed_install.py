"""Hash-owned file installation for Codex roles and skills.

Preflight the entire operation. Never follow destination symlinks, overwrite
custom edits, or recursively remove directories containing user content.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import stat
import tempfile
from pathlib import Path


class InstallConflict(ValueError):
    """The destination cannot be proven safe to change."""


def digest(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def safe_path(path: Path) -> Path:
    path = Path(os.path.abspath(path.expanduser()))
    for part in [*reversed(path.parents), path]:
        if part.is_symlink():
            raise InstallConflict(f"symlink destination: {part}")
        if part != path and part.exists() and not part.is_dir():
            raise InstallConflict(f"non-directory destination parent: {part}")
    return path


def read_file(path: Path) -> bytes | None:
    safe_path(path)
    if not path.exists():
        return None
    info = path.stat()
    if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
        raise InstallConflict(f"destination is not a single regular file: {path}")
    return path.read_bytes()


def json_bytes(value: dict) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode()


class InstallPlan:
    def __init__(self) -> None:
        self.files: dict[Path, tuple[bytes | None, bytes | None]] = {}

    def add(self, path: Path, content: bytes | None, *, expected: bytes | None) -> None:
        path = safe_path(path)
        snapshot = (expected, content)
        if path in self.files and self.files[path] != snapshot:
            raise InstallConflict(
                f"overlapping install target or changed snapshot: {path}"
            )
        if read_file(path) != expected:
            raise InstallConflict(f"destination changed since validation: {path}")
        self.files.setdefault(path, snapshot)

    def changes(self) -> list[Path]:
        return [path for path, (old, new) in self.files.items() if old != new]

    def apply(self) -> None:
        # Recheck every snapshot before the first write, including manifests.
        for path, (old, _) in self.files.items():
            if read_file(path) != old:
                raise InstallConflict(f"destination changed during preflight: {path}")
        for path, (old, new) in self.files.items():
            if old == new:
                continue
            if read_file(path) != old:
                raise InstallConflict(f"destination changed during install: {path}")
            if new is None:
                path.unlink()
                continue
            path.parent.mkdir(parents=True, exist_ok=True)
            safe_path(path)
            mode = stat.S_IMODE(path.stat().st_mode) if old is not None else 0o644
            fd, temp = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
            try:
                with os.fdopen(fd, "wb") as stream:
                    os.fchmod(stream.fileno(), mode)
                    stream.write(new)
                os.replace(temp, path)
            finally:
                if os.path.exists(temp):
                    os.unlink(temp)


def managed_files(
    plan: InstallPlan,
    root: Path,
    desired: dict[str, str],
    *,
    legacy: dict[str, str] | None = None,
    legacy_hashes: dict[str, set[str]] | None = None,
) -> None:
    """Adopt exact desired/explicit legacy bytes, then track content hashes."""
    root = safe_path(root)
    manifest = root / ".forge-managed.json"
    raw = read_file(manifest)
    previous: dict[str, str] = {}
    if raw is not None:
        try:
            data = json.loads(raw)
            if set(data) != {"version", "files"} or data["version"] != 1:
                raise ValueError("unsupported manifest")
            previous = data["files"]
            if not isinstance(previous, dict) or not all(
                isinstance(key, str)
                and isinstance(value, str)
                and re.fullmatch(r"[a-f0-9]{64}", value)
                for key, value in previous.items()
            ):
                raise ValueError("invalid file hashes")
        except (ValueError, TypeError) as exc:
            raise InstallConflict(
                f"invalid ownership manifest: {manifest}: {exc}"
            ) from exc
    for name in sorted(set(desired) | set(previous)):
        if (
            not name
            or Path(name).is_absolute()
            or ".." in Path(name).parts
            or str(Path(name)) != name
            or name == manifest.name
        ):
            raise InstallConflict(f"invalid managed filename: {name!r}")
        target = root / name
        current = read_file(target)
        wanted = desired[name].encode() if name in desired else None
        owned = current is not None and previous.get(name) == digest(current)
        exact_legacy = (
            name not in previous
            and current is not None
            and (
                (
                    legacy is not None
                    and name in legacy
                    and current == legacy[name].encode()
                )
                or (
                    legacy_hashes is not None
                    and digest(current) in legacy_hashes.get(name, set())
                )
            )
        )
        if current is not None and current != wanted and not owned and not exact_legacy:
            raise InstallConflict(f"custom or modified file: {target}")
        plan.add(target, wanted, expected=current)
    plan.add(
        manifest,
        json_bytes(
            {
                "version": 1,
                "files": {
                    name: digest(content.encode()) for name, content in desired.items()
                },
            }
        ),
        expected=raw,
    )
