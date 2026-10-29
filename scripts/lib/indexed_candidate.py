"""Read-only coherent indexed data for standalone commit checks.

No rule policy, candidate execution or mutable capture lifecycle lives here.
"""

from __future__ import annotations

import hashlib
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path


class InputUnavailable(Exception):
    """The bounded indexed input cannot be established."""


@dataclass(frozen=True)
class GitSelection:
    cwd: str
    environment: tuple[tuple[str, str], ...]


@dataclass(frozen=True, order=True)
class Entry:
    path: bytes
    mode: bytes
    oid: bytes


@dataclass(frozen=True)
class RawIndex:
    absent: bool
    digest: str
    stat: tuple[int, ...]


@dataclass(frozen=True)
class Observation:
    consumer: str
    git_dir: str
    index: str
    head: tuple[str, str, str]
    raw_index: RawIndex
    baseline: tuple[Entry, ...]
    stages: tuple[Entry, ...]
    delta: bytes
    shared_index: bytes


@dataclass(frozen=True)
class Candidate:
    selection: GitSelection
    observation: Observation
    entries: tuple[Entry, ...]
    changed: tuple[Entry, ...]
    skipped: tuple[tuple[bytes, str], ...]


def git(
    selection: GitSelection, *args: str, allow_failure: bool = False
) -> subprocess.CompletedProcess:
    try:
        result = subprocess.run(
            ["git", "--no-replace-objects", *args],
            cwd=selection.cwd,
            env=dict(selection.environment),
            capture_output=True,
            check=False,
        )
    except OSError as exc:
        raise InputUnavailable(f"Git unavailable: {exc}") from exc
    if result.returncode and not allow_failure:
        raise InputUnavailable(
            f"Git {args[0]} input unavailable: {os.fsdecode(result.stderr).strip()}"
        )
    return result


def _line(selection: GitSelection, *args: str) -> str:
    return os.fsdecode(git(selection, *args).stdout).removesuffix("\n")


def observe_head(selection: GitSelection) -> tuple[str, str, str]:
    symbolic = git(
        selection, "symbolic-ref", "--quiet", "--no-recurse", "HEAD", allow_failure=True
    )
    if symbolic.returncode not in (0, 1):
        raise InputUnavailable("invalid HEAD symbolic resolution")
    spelling = (
        os.fsdecode(symbolic.stdout).removesuffix("\n")
        if symbolic.returncode == 0
        else ""
    )
    commit = git(
        selection, "rev-parse", "--verify", "HEAD^{commit}", allow_failure=True
    )
    if commit.returncode:
        if (
            not spelling
            or git(
                selection, "check-ref-format", spelling, allow_failure=True
            ).returncode
        ):
            raise InputUnavailable("invalid HEAD resolution")
        target = git(
            selection, "show-ref", "--verify", "--quiet", spelling, allow_failure=True
        )
        if target.returncode != 1:
            raise InputUnavailable("invalid HEAD target; cannot establish unborn input")
        return spelling, "", ""
    tree = _line(selection, "rev-parse", "--verify", "HEAD^{tree}")
    return spelling, os.fsdecode(commit.stdout).strip(), tree


def read_index_bytes(path: Path) -> bytes:
    """Named raw read boundary; never writes or replaces the index."""
    return path.read_bytes()


def _stat_identity(path: Path) -> tuple[int, ...]:
    value = path.stat()
    return (
        value.st_dev,
        value.st_ino,
        value.st_size,
        value.st_mtime_ns,
        value.st_ctime_ns,
    )


def read_index_identity(path: Path) -> RawIndex:
    try:
        before = _stat_identity(path)
    except FileNotFoundError:
        # A fresh existence check distinguishes stable absence from creation.
        try:
            _stat_identity(path)
        except FileNotFoundError:
            return RawIndex(True, "", ())
        except OSError as exc:
            raise InputUnavailable(f"index input unavailable: {exc}") from exc
        raise InputUnavailable("changed index: created during observation")
    except OSError as exc:
        raise InputUnavailable(f"index input unavailable: {exc}") from exc
    try:
        first = read_index_bytes(path)
        middle = _stat_identity(path)
        second = read_index_bytes(path)
        after = _stat_identity(path)
    except OSError as exc:
        raise InputUnavailable(f"index input unavailable: {exc}") from exc
    if before != middle or middle != after or first != second:
        raise InputUnavailable("changed index: unstable bytes/stat observation")
    return RawIndex(False, hashlib.sha256(first).hexdigest(), before)


def _tree_entries(raw: bytes) -> tuple[Entry, ...]:
    entries = []
    for record in raw.split(b"\0"):
        if not record:
            continue
        try:
            metadata, path = record.split(b"\t", 1)
            mode, _kind, oid = metadata.split(b" ")
        except ValueError as exc:
            raise InputUnavailable("invalid baseline entry") from exc
        entries.append(Entry(path, mode, oid))
    return tuple(sorted(entries))


def _stage_entries(raw: bytes) -> tuple[Entry, ...]:
    entries = []
    for record in raw.split(b"\0"):
        if not record:
            continue
        try:
            metadata, path = record.split(b"\t", 1)
            mode, oid, stage = metadata.split(b" ")
        except ValueError as exc:
            raise InputUnavailable("invalid index entry") from exc
        if stage != b"0":
            raise InputUnavailable("unmerged index stages unsupported")
        if mode == b"040000":
            raise InputUnavailable("sparse-directory index unsupported")
        entries.append(Entry(path, mode, oid))
    if len({entry.path for entry in entries}) != len(entries):
        raise InputUnavailable("duplicate stage-zero entry")
    return tuple(sorted(entries))


def observe(selection: GitSelection) -> Observation:
    consumer = _line(selection, "rev-parse", "--show-toplevel")
    git_dir = _line(selection, "rev-parse", "--absolute-git-dir")
    index = _line(
        selection, "rev-parse", "--path-format=absolute", "--git-path", "index"
    )
    head = observe_head(selection)
    raw_index = read_index_identity(Path(index))
    shared = git(selection, "rev-parse", "--shared-index-path").stdout
    if shared.strip():
        raise InputUnavailable("split index unsupported")
    baseline = (
        _tree_entries(git(selection, "ls-tree", "-r", "-z", head[2]).stdout)
        if head[2]
        else ()
    )
    stages = _stage_entries(
        git(selection, "ls-files", "--stage", "--sparse", "-z").stdout
    )
    delta = git(
        selection,
        "diff",
        "--cached",
        "--raw",
        "-z",
        "--no-abbrev",
        "--no-renames",
        "--no-ext-diff",
        "--no-textconv",
        "--no-color",
        "--ita-invisible-in-index",
    ).stdout
    return Observation(
        consumer, git_dir, index, head, raw_index, baseline, stages, delta, shared
    )


def _candidate_entries(
    observation: Observation,
) -> tuple[tuple[Entry, ...], tuple[Entry, ...], tuple[tuple[bytes, str], ...]]:
    baseline = {entry.path: entry for entry in observation.baseline}
    stages = {entry.path: entry for entry in observation.stages}
    candidate = dict(baseline)
    skipped = []
    records = observation.delta.split(b"\0")
    if records[-1] != b"" or (len(records) - 1) % 2:
        raise InputUnavailable("invalid NUL staged delta")
    for offset in range(0, len(records) - 1, 2):
        metadata, path = records[offset : offset + 2]
        try:
            old_mode, new_mode, old_oid, new_oid, status = metadata.removeprefix(
                b":"
            ).split(b" ")
        except ValueError as exc:
            raise InputUnavailable("invalid raw staged delta") from exc
        if not metadata.startswith(b":") or status not in (b"A", b"D", b"M", b"T"):
            raise InputUnavailable("unsupported staged delta record")
        old = baseline.get(path)
        if old_mode == b"000000":
            if old is not None:
                raise InputUnavailable("changed baseline membership")
        elif old != Entry(path, old_mode, old_oid):
            raise InputUnavailable("changed baseline identity")
        if new_mode == b"000000":
            candidate.pop(path, None)
            skipped.append((path, "deleted"))
        else:
            entry = Entry(path, new_mode, new_oid)
            if stages.get(path) != entry:
                raise InputUnavailable("changed stage mapping")
            candidate[path] = entry
    if any(stages.get(path) != entry for path, entry in candidate.items()):
        raise InputUnavailable("changed candidate/stage mapping")
    # Stage-only records omitted by --ita-invisible-in-index are not additions.
    skipped.extend(
        (path, "intent-to-add, no staged content")
        for path in stages.keys() - candidate.keys()
    )
    changed = tuple(
        sorted(
            entry for path, entry in candidate.items() if baseline.get(path) != entry
        )
    )
    return tuple(sorted(candidate.values())), changed, tuple(sorted(skipped))


def capture_candidate(repo: Path) -> Candidate:
    environment = dict(os.environ)
    environment["GIT_OPTIONAL_LOCKS"] = "0"
    selection = GitSelection(str(repo), tuple(sorted(environment.items())))
    first = observe(selection)
    entries, changed, skipped = _candidate_entries(first)
    if observe(selection) != first:
        raise InputUnavailable("changed input during capture")
    return Candidate(selection, first, entries, changed, skipped)


def compare_candidate(candidate: Candidate) -> None:
    if observe(candidate.selection) != candidate.observation:
        raise InputUnavailable("changed input before publication")


def read_blob(selection: GitSelection, oid: str) -> bytes:
    if git(selection, "cat-file", "-t", oid).stdout != b"blob\n":
        raise InputUnavailable("required original object is not a blob")
    return git(selection, "cat-file", "blob", oid).stdout
