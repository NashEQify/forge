"""Find old project-local Forge skill files that conflict with plugin migration, and remove approved ones.

Rows carry sha256 (of the SKILL.md bytes); an uninspected skill root makes the migration `unavailable`, never
`clear`. Both removal commands of forge_setup.py share remove_skill_wrappers; parse_approval states the --wrapper form.
"""

from __future__ import annotations

import errno
import hashlib
import json
import os
import re
import stat
from contextlib import contextmanager
from pathlib import Path

SKILL_ROOTS = (Path(".claude/skills"), Path(".agents/skills"), Path(".opencode/skills"))
MARKER = "<!-- generated-by: scripts/generate_skill_wrappers.py (do not hand-edit) -->"
FRAMEWORK = Path(__file__).resolve().parents[1]


def _open_directory(root: Path, parts: tuple[str, ...] = ()) -> int:
    """An fd of root/parts; no component below root may be a symlink."""
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    fd = os.open(root, flags)
    try:
        for part in parts:
            child = os.open(part, flags, dir_fd=fd)
            os.close(fd)
            fd = child
    except BaseException:
        os.close(fd)
        raise
    return fd


@contextmanager
def _directory(root: Path, parts: tuple[str, ...] = ()):
    fd = _open_directory(root, parts)
    try:
        yield fd
    finally:
        os.close(fd)


def _read_skill(fd: int) -> tuple[bytes, os.stat_result]:
    flags = os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK
    with os.fdopen(os.open("SKILL.md", flags, dir_fd=fd), "rb") as stream:
        info = os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode):
            raise ValueError("expected a regular SKILL.md")
        return stream.read(), info


def _wrapper_target(path: Path, contents: str) -> Path | None:
    lines = contents.splitlines()
    if not lines or lines[0] != "---":
        return None
    try:
        end = lines.index("---", 1)
    except ValueError:
        return None
    name = path.parent.name
    if f"name: {name}" not in lines[1:end]:
        return None
    body = [line.strip() for line in lines[end + 1:] if line.strip()]
    if not body:
        return None

    if MARKER in body:
        links = [line for line in body if line.startswith("**SoT:**")]
        if len(links) != 1:
            return None
        match = re.fullmatch(r"\*\*SoT:\*\* `(/[^\x00`]+)`", links[0])
    else:
        # Legacy project wrappers put this directive immediately after the frontmatter.
        match = re.fullmatch(r"(?:Lade und befolge|Load and follow) (/[^\x00]+)", body[0])
    if not match:
        return None
    target = Path(match[1])
    if target.name != "SKILL.md" or target.parent.parent.name != "skills":
        return None
    source = target.parent.name
    if source.replace("_", "-") != name or not (FRAMEWORK / "skills" / source / "SKILL.md").is_file():
        return None
    if MARKER not in body and target.parent.parent.parent.name != "framework":
        return None
    return target


def _conflict(path: Path, data: bytes, exports: frozenset[str]) -> dict[str, str] | None:
    """The conflict row of one SKILL.md; an OSError other than ENOENT/ENOTDIR on its target propagates."""
    target = _wrapper_target(path, data.decode("utf-8", "replace"))
    if target is None:
        return None
    try:
        target.stat()
    except (FileNotFoundError, NotADirectoryError):
        state = "missing"
    else:
        if target.parent.name not in exports:
            return None
        state = "reachable"
    return {"path": str(path), "target": str(target), "target_state": state,
            "sha256": hashlib.sha256(data).hexdigest()}


def _reason(path: object, exc: BaseException, project: Path | None = None) -> str:
    """Why `path` (relative to project) went uninspected; names the first symlinked component when there is one."""
    if project is not None and isinstance(exc, OSError):
        parts = Path(str(path)).parts
        for end in range(1, len(parts) + 1):
            try:
                if stat.S_ISLNK(os.lstat(project.joinpath(*parts[:end])).st_mode):
                    return f"{Path(*parts[:end])}: a symlink, not inspected"
            except OSError:
                break
    if isinstance(exc, OSError) and exc.errno == errno.ELOOP:
        return f"{path}: a symlink, not inspected"
    detail = exc.strerror if isinstance(exc, OSError) and exc.strerror else str(exc)
    return f"{path}: could not be inspected ({detail})"


def _scan(project: Path, exports: frozenset[str]) -> tuple[list[dict[str, str]], list[str]]:
    """Conflict rows and the paths the scan could not inspect; only a missing skill root counts as absent."""
    found: list[dict[str, str]] = []
    problems: list[str] = []
    project = Path(os.path.realpath(project))
    try:
        with _directory(project):
            pass
    except OSError as exc:
        return found, [_reason(project, exc)]
    for root in SKILL_ROOTS:
        try:
            with _directory(project, root.parts) as directory:
                names = sorted(os.listdir(directory))
                kinds = {name: os.stat(name, dir_fd=directory, follow_symlinks=False).st_mode for name in names}
        except FileNotFoundError:
            continue
        except OSError as exc:
            problems.append(_reason(root, exc, project))
            continue
        for name in names:
            path = root / name / "SKILL.md"
            if stat.S_ISLNK(kinds[name]):
                problems.append(f"{root / name}: a symlink, not inspected")
                continue
            if not stat.S_ISDIR(kinds[name]):
                continue
            try:
                with _directory(project, path.parent.parts) as fd:
                    data, _ = _read_skill(fd)
                conflict = _conflict(path, data, exports)
            except FileNotFoundError:
                continue  # a skill folder without SKILL.md
            except (OSError, ValueError) as exc:
                problems.append(_reason(path, exc, project))
                continue
            if conflict:
                found.append(conflict)
    return found, problems


class ScanIncomplete(Exception):
    """The scan could not inspect every skill root; `problems` names each uninspected path."""

    def __init__(self, problems: list[str]) -> None:
        super().__init__("wrapper scan incomplete: " + "; ".join(problems))
        self.problems = problems


def stale_skill_wrappers(project: Path) -> list[dict[str, str]]:
    """Dead-target wrappers (Task 532); raises ScanIncomplete instead of returning a partial list."""
    found, problems = _scan(project, frozenset())
    if problems:
        raise ScanIncomplete(problems)
    return missing_wrapper_paths(found)


def missing_wrapper_paths(conflicts: list[dict[str, str]]) -> list[dict[str, str]]:
    return [{"path": row["path"], "target": row["target"], "sha256": row["sha256"]}
            for row in conflicts if row["target_state"] == "missing"]


def exported_skills() -> frozenset[str]:
    manifest = FRAMEWORK / ".claude-plugin/plugin.json"
    with manifest.open(encoding="utf-8") as stream:
        data = json.load(stream)
    skills = data.get("skills") if isinstance(data, dict) and data.get("name") == "forge" else None
    if not isinstance(skills, list) or not skills:
        raise ValueError("plugin manifest has no explicit Forge skill list")
    exports = set()
    for entry in skills:
        match = re.fullmatch(r"\./skills/([a-z0-9][a-z0-9_-]*)", entry) if isinstance(entry, str) else None
        if match is None or not (FRAMEWORK / "skills" / match[1] / "SKILL.md").is_file():
            raise ValueError(f"invalid skill export: {entry!r}")
        exports.add(match[1])
    return frozenset(exports)


def wrapper_migration(project: Path) -> dict:
    """pending / clear / unavailable; never clear while the plugin list or any skill root went uninspected."""
    reasons = []
    try:
        exports = exported_skills()
    except (OSError, ValueError) as exc:
        exports = None
        reasons.append(f"Cannot verify the Forge plugin skill list: {exc}")
    conflicts, problems = _scan(project, exports or frozenset())
    if problems:
        reasons.append("Wrapper scan incomplete: " + "; ".join(problems))
    if reasons:
        return {"status": "unavailable", "conflicts": conflicts, "reason": " ".join(reasons)}
    return {"status": "pending" if conflicts else "clear", "conflicts": conflicts}


def parse_approval(value: str) -> tuple[str, str, str]:
    """`PATH=TARGET_STATE:SHA256` (split on the last `=`) -> (path, target_state, sha256); ValueError otherwise."""
    path, sep, token = value.rpartition("=")
    state, colon, digest = token.partition(":")
    if (not sep or not path or not colon or state not in ("missing", "reachable")
            or not re.fullmatch(r"[0-9a-f]{64}", digest)):
        raise ValueError(f"{value!r}: --wrapper takes PATH=TARGET_STATE:SHA256 from the listed row "
                         "(target_state missing or reachable, sha256 64 lowercase hex)")
    return path, state, digest


def _approved_path(name: str) -> Path:
    path = Path(name)
    if (path.is_absolute() or str(path) != name or ".." in path.parts or path.name != "SKILL.md"
            or path.parent.parent not in SKILL_ROOTS):
        raise ValueError(f"{name}: not a project-local skill file")
    return path


def _check(fd: int, approval: tuple[str, str, str], exports: frozenset[str]) -> os.stat_result:
    """Refuse unless the SKILL.md under fd hashes to the approved digest, the current conflict equals the approved
    row and its folder is writable; returns the stat of the file read."""
    name, state, digest = approval
    try:
        data, info = _read_skill(fd)
        if hashlib.sha256(data).hexdigest() != digest:
            raise ValueError(f"{name}: contents changed since listing (sha256 differs); file kept")
        current = _conflict(Path(name), data, exports)
        if current is None or current["target_state"] != state:
            raise ValueError(f"{name}: no longer matches the listed wrapper conflict; file kept")
        if not os.access(".", os.W_OK, dir_fd=fd):
            raise ValueError(f"{name}: its folder is not writable; nothing removed")
    except OSError as exc:
        raise ValueError(_reason(name, exc)) from exc
    return info


@contextmanager
def _wrapper_folder(project: Path, name: str):
    try:
        fd = _open_directory(project, _approved_path(name).parent.parts)
    except OSError as exc:
        raise ValueError(_reason(name, exc, project)) from exc
    try:
        yield fd
    finally:
        os.close(fd)


def remove_skill_wrappers(project: Path, approvals: list[tuple[str, str, str]], exports: frozenset[str],
                          states: tuple[str, ...], dry_run: bool, done: list[str]) -> None:
    """The one removal routine of both commands. Every approval is checked before the first unlink, then each is
    rechecked and unlinked; `done` collects the removed paths. Every refusal is a ValueError naming the wrapper."""
    project = Path(os.path.realpath(project))
    for name, state, _ in approvals:
        if state not in states:
            raise ValueError(f"{name}: a {state} wrapper is not removable by this command")
    for approval in approvals:
        with _wrapper_folder(project, approval[0]) as fd:
            _check(fd, approval, exports)
    if dry_run:
        return
    for approval in approvals:
        name = approval[0]
        with _wrapper_folder(project, name) as fd:
            original = _check(fd, approval, exports)
            try:
                current = os.stat("SKILL.md", dir_fd=fd, follow_symlinks=False)
                if not os.path.samestat(current, original) or current.st_ctime_ns != original.st_ctime_ns:
                    raise ValueError(f"{name}: changed while checking the wrapper; file kept")
                os.unlink("SKILL.md", dir_fd=fd)
            except OSError as exc:
                raise ValueError(f"{name}: not removed ({exc.strerror or exc})") from exc
        done.append(name)
