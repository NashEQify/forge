"""Find old project-local Forge skill files that conflict with plugin migration."""

from __future__ import annotations

import json
import os
import re
import stat
from contextlib import contextmanager
from pathlib import Path

SKILL_ROOTS = (Path(".claude/skills"), Path(".agents/skills"), Path(".opencode/skills"))
MARKER = "<!-- generated-by: scripts/generate_skill_wrappers.py (do not hand-edit) -->"
FRAMEWORK = Path(__file__).resolve().parents[1]


@contextmanager
def _directory(root: Path, parts: tuple[str, ...] = ()):
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    fd = os.open(root, flags)
    try:
        for part in parts:
            child = os.open(part, flags, dir_fd=fd)
            os.close(fd)
            fd = child
        yield fd
    finally:
        os.close(fd)


def _read_skill(fd: int) -> tuple[str, os.stat_result]:
    flags = os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK
    with os.fdopen(os.open("SKILL.md", flags, dir_fd=fd), encoding="utf-8") as stream:
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


def _conflict(path: Path, contents: str, exports: frozenset[str]) -> dict[str, str] | None:
    target = _wrapper_target(path, contents)
    if target is None:
        return None
    try:
        target.stat()
    except (FileNotFoundError, NotADirectoryError):
        state = "missing"
    except OSError:
        return None
    else:
        if target.parent.name not in exports:
            return None
        state = "reachable"
    return {"path": str(path), "target": str(target), "target_state": state}


def _scan(project: Path, exports: frozenset[str]) -> list[dict[str, str]]:
    found = []
    for root in SKILL_ROOTS:
        try:
            with _directory(project, root.parts) as directory:
                names = sorted(os.listdir(directory))
        except OSError:
            continue
        for name in names:
            path = root / name / "SKILL.md"
            try:
                with _directory(project, path.parent.parts) as fd:
                    contents, _ = _read_skill(fd)
            except (OSError, ValueError):
                continue
            if conflict := _conflict(path, contents, exports):
                found.append(conflict)
    return found


def stale_skill_wrappers(project: Path) -> list[dict[str, str]]:
    return missing_wrapper_paths(_scan(project, frozenset()))


def missing_wrapper_paths(conflicts: list[dict[str, str]]) -> list[dict[str, str]]:
    return [{"path": row["path"], "target": row["target"]}
            for row in conflicts if row["target_state"] == "missing"]


def _exported_skills() -> frozenset[str]:
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
    try:
        exports = _exported_skills()
    except (OSError, ValueError) as exc:
        return {"status": "unavailable", "conflicts": _scan(project, frozenset()),
                "reason": f"Cannot verify the Forge plugin skill list: {exc}"}
    conflicts = _scan(project, exports)
    return {"status": "pending" if conflicts else "clear", "conflicts": conflicts}


def remove_skill_wrapper(project: Path, selected: dict[str, str]) -> None:
    """Remove a selected wrapper only while its reported migration conflict holds."""
    path = Path(selected["path"])
    if path.parent.parent not in SKILL_ROOTS or path.name != "SKILL.md" or ".." in path.parts:
        raise ValueError(f"{path}: not a project-local skill file")
    exports = _exported_skills() if selected["target_state"] == "reachable" else frozenset()
    with _directory(project, path.parent.parts) as fd:
        contents, original = _read_skill(fd)
        if _conflict(path, contents, exports) != selected:
            raise ValueError(f"{path}: no longer matches the reported wrapper conflict")
        current = os.stat(path.name, dir_fd=fd, follow_symlinks=False)
        if not os.path.samestat(current, original) or current.st_ctime_ns != original.st_ctime_ns:
            raise ValueError(f"{path}: changed while checking the wrapper")
        os.unlink(path.name, dir_fd=fd)
