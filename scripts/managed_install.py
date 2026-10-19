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
        self.written = 0  # files changed by apply(), also when it fails midway

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
        # Ownership/state files (.forge-*) are written after all content: an
        # interrupted apply leaves the old ownership in place, so a re-run
        # still proves ownership of every half-written file and converges.
        ordered = sorted(
            self.files.items(), key=lambda item: item[0].name.startswith(".forge-")
        )
        for path, (old, new) in ordered:
            if old == new:
                continue
            if read_file(path) != old:
                raise InstallConflict(f"destination changed during install: {path}")
            if new is None:
                path.unlink()
                self.written += 1
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
                self.written += 1
            finally:
                if os.path.exists(temp):
                    os.unlink(temp)


def read_manifest(root: Path) -> tuple[Path, bytes | None, dict[str, str]]:
    """Return (manifest path, raw bytes or None, owned name -> sha256)."""
    manifest = safe_path(root) / ".forge-managed.json"
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
    return manifest, raw, previous


def unmanage_root(plan: InstallPlan, root: Path, *, keep: frozenset[str] = frozenset()) -> None:
    """Plan removal of every owned file under `root` and of its manifest.

    A file whose bytes no longer match the recorded hash is a conflict;
    `keep` names owned files another planner takes over (left in place).
    """
    manifest, raw, previous = read_manifest(root)
    if raw is None:
        return
    for name in sorted(previous):
        if (
            not name
            or Path(name).is_absolute()
            or ".." in Path(name).parts
            or str(Path(name)) != name
        ):
            raise InstallConflict(f"invalid managed filename: {name!r}")
        target = manifest.parent / name
        current = read_file(target)
        if current is not None and digest(current) != previous[name]:
            raise InstallConflict(f"custom or modified file: {target}")
        if name not in keep:
            plan.add(target, None, expected=current)
    plan.add(manifest, None, expected=raw)


def managed_files(
    plan: InstallPlan,
    root: Path,
    desired: dict[str, str],
    *,
    legacy: dict[str, str] | None = None,
    legacy_hashes: dict[str, set[str]] | None = None,
    release: frozenset[str] = frozenset(),
    release_completed: dict[str, bytes] | None = None,
) -> None:
    """Adopt exact desired/explicit legacy bytes, then track content hashes.

    `release` names currently owned files that leave the manifest without
    being deleted (another planner takes them over); releasing a file that is
    not owned with a matching hash, or that is also desired, is a conflict.
    `release_completed` maps a released name to the exact bytes its new
    planner writes: a file already holding them (an interrupted earlier run
    wrote it before the manifest) is released too.
    """
    root = safe_path(root)
    manifest, raw, previous = read_manifest(root)
    completed = release_completed or {}
    for name in sorted(release):
        target = root / name
        current = read_file(target) if name in previous else None
        if (
            name in desired
            or current is None
            or (
                previous.get(name) != digest(current)
                and completed.get(name) != current
            )
        ):
            raise InstallConflict(f"cannot release unowned or modified file: {target}")
    for name in sorted((set(desired) | set(previous)) - set(release)):
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
