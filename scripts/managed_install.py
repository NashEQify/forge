"""Hash-owned installation: whole files, marker-delimited text blocks and JSON fragments.

Preflight the entire operation. Never follow destination symlinks, overwrite
custom edits, or recursively remove directories containing user content.
Whole files are owned through a per-folder manifest (managed_files); a text
block inside a file the user also edits through its block hash (plan_block with
a state file, plan_text_block with the hash kept by the caller); keys and list
items inside a JSON file the host also writes through a fragment hash
(plan_json_fragment).
"""

from __future__ import annotations

import hashlib
import itertools
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

    def apply(self, *, first: tuple[Path, ...] = ()) -> None:
        # Recheck every snapshot before the first write, including manifests.
        for path, (old, _) in self.files.items():
            if read_file(path) != old:
                raise InstallConflict(f"destination changed during preflight: {path}")
        # `first` (such as a Git exclude block) is written before any content. Ownership/state files
        # (.forge-*) are written after all content: an interrupted apply leaves the old ownership in place,
        # so a re-run still proves ownership of every half-written file and converges.
        early = {safe_path(path) for path in first}
        ordered = sorted(
            self.files.items(),
            key=lambda item: 0 if item[0] in early else 1 + item[0].name.startswith(".forge-"),
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


def unmanage_root(
    plan: InstallPlan, root: Path, *, keep: frozenset[str] = frozenset(), pending: dict[str, str] | None = None
) -> None:
    """Plan removal of every owned file under `root` and of its manifest.

    A file whose bytes no longer match the recorded hash is a conflict;
    `keep` names owned files another planner takes over (left in place);
    `pending` maps a name to the hash an interrupted write recorded before
    the manifest (those bytes count as owned too).
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
        if current is not None and digest(current) not in {previous[name], (pending or {}).get(name)}:
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
    pending: dict[str, str] | None = None,
    hold: frozenset[str] = frozenset(),
) -> None:
    """Adopt exact desired/explicit legacy bytes, then track content hashes.

    `pending` maps a name to the hash an interrupted write recorded before the
    manifest: those bytes count as owned. `hold` names files left exactly as
    they are (a diverged or colliding file a refresh skips): an owned one keeps
    its manifest hash, an unowned one stays out of the manifest.

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
    for name in sorted((set(desired) | set(previous)) - set(release) - hold):
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
        owned = current is not None and digest(current) in {previous.get(name), (pending or {}).get(name)}
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
                    **{name: digest(content.encode()) for name, content in desired.items() if name not in hold},
                    **{name: previous[name] for name in hold if name in previous},
                },
            }
        ),
        expected=raw,
    )


# Person-specific legacy text outside a managed block (an old per-person soul
# block or the retired session-resume entry) is never edited by forge.
LEGACY_TEXT = re.compile(r"<!--\s*[\w.-]*-SOUL:START|session-resume")
HASH = re.compile(r"[a-f0-9]{64}")


def _block_span(text: str, path: Path, start: str, end: str) -> tuple[int, int] | None:
    """(first, last) of the one marker-delimited block in text, None without markers."""
    if start not in text and end not in text:
        return None
    if text.count(start) != 1 or text.count(end) != 1 or text.index(start) > text.index(end):
        raise InstallConflict(f"malformed managed boot block: {path}")
    return text.index(start), text.index(end) + len(end)


def plan_text_block(
    plan: InstallPlan,
    path: Path,
    start: str,
    end: str,
    body: str,
    *,
    old_hash: str | None,
    replace_whole: bool = False,
    adopt_absent: bool = False,
) -> str:
    """Own exactly one marker-delimited block in `path`; text outside it is kept.

    old_hash: the block hash the caller recorded at the last install (None: not
    installed). Returns the new block's hash for the caller to record.
    replace_whole: the caller proved the entire current file is owned (legacy
    whole-file ownership); the new content is the block only.
    adopt_absent: a block that is gone (its file deleted or the block cut out)
    counts as not installed and is written again, instead of a conflict.
    """
    path = safe_path(path)
    original = read_file(path)
    text = original.decode() if original is not None else ""
    block = start + "\n" + body + end
    span = None if replace_whole else _block_span(text, path, start, end)
    if replace_whole:
        updated = block + "\n"
    elif span is not None:
        first, last = span
        current = text[first:last]
        if current != block and digest(current.encode()) != old_hash:
            raise InstallConflict(f"modified or unowned boot block: {path}")
        updated = text[:first] + block + text[last:]
    else:
        if old_hash is not None and original is not None and not adopt_absent:
            raise InstallConflict(f"managed boot block removed: {path}")
        updated = text + ("\n\n" if text else "") + block + "\n"
    plan.add(path, updated.encode(), expected=original)
    return digest(block.encode())


def plan_text_block_removal(
    plan: InstallPlan, path: Path, start: str, end: str, old_hash: str, *, keep_file: bool = False
) -> None:
    """Remove the block whose hash is old_hash; delete the file if nothing else remains (keep_file: the
    file was there before Forge, so what remains is written back even when empty).

    A block whose bytes differ from old_hash (a user edit) is a conflict; an
    already absent block is nothing to remove.
    """
    path = safe_path(path)
    original = read_file(path)
    text = original.decode() if original is not None else ""
    span = _block_span(text, path, start, end)
    if span is None:
        return
    first, last = span
    if digest(text[first:last].encode()) != old_hash:
        raise InstallConflict(f"modified or unowned boot block: {path}")
    before, after = text[:first], text[last:]
    if after.startswith("\n"):
        after = after[1:]
    if before.endswith("\n\n"):  # separator plan_text_block added after outer text
        before = before[:-2]
        # Outer text without a final newline: keep the following line apart.
        if before and not before.endswith("\n") and after[:1] not in ("", "\n", "\r"):
            before += "\n"
    remaining = before + after
    plan.add(path, remaining.encode() if remaining.strip() or keep_file else None, expected=original)


def _block_state(state_path: Path) -> tuple[bytes | None, str | None]:
    raw_state = read_file(state_path)
    if raw_state is None:
        return None, None
    try:
        state = json.loads(raw_state)
        if set(state) != {"version", "sha256"} or state["version"] != 1:
            raise ValueError("unsupported boot state")
        old_hash = state["sha256"]
        if not isinstance(old_hash, str) or not HASH.fullmatch(old_hash):
            raise ValueError("invalid boot hash")
    except (ValueError, TypeError) as exc:
        raise InstallConflict(f"invalid boot ownership: {state_path}") from exc
    return raw_state, old_hash


def plan_block(
    plan: InstallPlan,
    path: Path,
    state_path: Path,
    start: str,
    end: str,
    body: str,
    *,
    replace_whole: bool = False,
) -> None:
    """plan_text_block with the block hash kept in its own state file."""
    raw_state, old_hash = _block_state(state_path)
    new_hash = plan_text_block(
        plan, path, start, end, body, old_hash=old_hash, replace_whole=replace_whole, adopt_absent=True
    )
    plan.add(state_path, json_bytes({"version": 1, "sha256": new_hash}), expected=raw_state)


def plan_block_removal(
    plan: InstallPlan, path: Path, state_path: Path, start: str, end: str, *, keep_file: bool = False
) -> None:
    """Remove a hash-owned block (and its state); delete the file if nothing else remains."""
    raw_state = read_file(state_path)
    if raw_state is None:
        return
    try:
        old_hash = json.loads(raw_state)["sha256"]
    except (ValueError, TypeError, KeyError) as exc:
        raise InstallConflict(f"invalid boot ownership: {state_path}") from exc
    plan_text_block_removal(plan, path, start, end, old_hash, keep_file=keep_file)
    plan.add(state_path, None, expected=raw_state)


def check_legacy_text(path: Path, start: str, end: str) -> None:
    """Refuse when person-specific legacy text sits outside the managed block;
    the rollout removes it by hand first."""
    raw = read_file(path)
    if raw is None:
        return
    text = raw.decode("utf-8", errors="replace")
    outside = text
    if start in text and end in text and text.index(start) < text.index(end):
        outside = text[: text.index(start)] + text[text.index(end) + len(end):]
    if LEGACY_TEXT.search(outside):
        raise InstallConflict(f"legacy text outside managed block: {path}")


def prune_empty_dirs(removed: list[Path], roots: list[Path]) -> None:
    """rmdir (non-recursive) directories emptied by owned-file removals, below a root, never a root. Paths and
    roots are normalized first; a root that is a symlink is a conflict."""
    roots = [Path(os.path.abspath(root)) for root in roots]
    if any(root.is_symlink() for root in roots):
        raise InstallConflict("a removal root is a symlink: " + ", ".join(map(str, roots)))
    for path in removed:
        directory = Path(os.path.abspath(path)).parent
        while (
            any(directory != root and directory.is_relative_to(root) for root in roots)
            and directory.is_dir()
            and not directory.is_symlink()
            and not any(directory.iterdir())
        ):
            directory.rmdir()
            directory = directory.parent


# --- JSON fragments: keys and list items Forge owns inside a JSON object another writer also edits ---
#
# A fragment is a set of top-level keys with their values plus, per list (named by its dotted key path,
# such as "hooks.SessionStart"), one item Forge appended. Its hash covers exactly those values, so keys
# and items a host adds next to them never count as a change; an edit to an owned value does.


def _canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def fragment_hash(keys: dict[str, object], items: dict[str, object]) -> str:
    return digest(_canonical({"keys": keys, "items": items}))


def _json_object(path: Path) -> tuple[bytes | None, dict]:
    raw = read_file(path)
    if raw is None:
        return None, {}
    try:
        data = json.loads(raw)
    except ValueError as exc:
        raise InstallConflict(f"not valid JSON: {path}") from exc
    if not isinstance(data, dict):
        raise InstallConflict(f"not a JSON object: {path}")
    return raw, data


def _list_at(data: dict, dotted: str, path: Path, *, create: bool) -> list | None:
    node = data
    *parents, leaf = dotted.split(".")
    for part in parents:
        child = node.get(part)
        if child is None:
            if not create:
                return None
            child = node[part] = {}
        if not isinstance(child, dict):
            raise InstallConflict(f"{path}: {part} is not a JSON object")
        node = child
    value = node.get(leaf)
    if value is None:
        if not create:
            return None
        value = node[leaf] = []
    if not isinstance(value, list):
        raise InstallConflict(f"{path}: {dotted} is not a JSON list")
    return value


def _owned_items(
    data: dict, key_names: list[str], item_paths: list[str], old_hash: str, path: Path
) -> dict[str, int] | None:
    """The index of each owned list item such that the owned keys and items hash to old_hash, else None."""
    keys = {name: data[name] for name in key_names if name in data}
    lists = [_list_at(data, dotted, path, create=False) or [] for dotted in item_paths]
    for combination in itertools.product(*(range(len(items)) for items in lists)):
        chosen = {dotted: items[i] for dotted, items, i in zip(item_paths, lists, combination)}
        if fragment_hash(keys, chosen) == old_hash:
            return dict(zip(item_paths, combination))
    return None


def plan_json_fragment(
    plan: InstallPlan,
    path: Path,
    keys: dict[str, object],
    items: dict[str, object],
    *,
    old_hash: str | None,
) -> str:
    """Own `keys` and one item per list in the JSON object at `path`; everything else is kept.

    old_hash: the fragment hash recorded at the last install (None: not installed). An owned
    value whose bytes no longer match it (a user edit) is a conflict. Not installed, an owned
    key holding another value is a conflict; one already holding the owned value (an
    interrupted earlier install) and an equal list item are adopted. A fragment that is gone
    (the file deleted, or none of the owned keys left) counts as not installed; its old item,
    found by the hash with the owned keys at their values, is replaced in place. Returns the
    new hash.
    """
    path = safe_path(path)
    raw, data = _json_object(path)
    original = json.loads(raw) if raw is not None else None
    if old_hash is not None:
        owned = _owned_items(data, list(keys), list(items), old_hash, path)
        if owned is None and not any(name in data for name in keys):
            owned = _owned_items({**data, **keys}, list(keys), list(items), old_hash, path)
            if owned is None:
                old_hash = None  # gone: planned as a fresh install below
    if old_hash is not None:
        if owned is None:
            raise InstallConflict(f"modified Forge settings in {path} (changed since the install; "
                                  "restore or remove them by hand)")
        for dotted, item in items.items():
            target = _list_at(data, dotted, path, create=True)
            assert target is not None
            target[owned[dotted]] = item
    else:
        for name, value in keys.items():
            if name in data and data[name] != value:
                raise InstallConflict(f"{path}: {name} is {data[name]!r}, not {value!r}")
        for dotted, item in items.items():
            target = _list_at(data, dotted, path, create=True)
            assert target is not None
            if item not in target:
                target.append(item)
    data.update(keys)
    if data != original:
        plan.add(path, (json.dumps(data, indent=2, ensure_ascii=False) + "\n").encode(), expected=raw)
    return fragment_hash(keys, items)


def plan_json_fragment_removal(
    plan: InstallPlan, path: Path, key_names: list[str], item_paths: list[str], old_hash: str
) -> None:
    """Remove the fragment whose hash is old_hash; delete the file when nothing else remains.

    A list or object left empty by the removal is removed with it. An owned value that
    changed since the install is a conflict, and nothing is removed.
    """
    path = safe_path(path)
    raw, data = _json_object(path)
    if raw is None or not any(name in data for name in key_names):
        return  # gone already (the file, or every owned key): counts as removed
    owned = _owned_items(data, key_names, item_paths, old_hash, path)
    if owned is None:
        raise InstallConflict(f"modified Forge settings in {path} (changed since the install; "
                              "restore or remove them by hand)")
    for name in key_names:
        data.pop(name, None)
    for dotted, index in owned.items():
        *parents, leaf = dotted.split(".")
        nodes = [data]
        for part in parents:
            nodes.append(nodes[-1][part])
        target = nodes[-1][leaf]
        del target[index]
        if not target:
            del nodes[-1][leaf]
            for parent, part in zip(reversed(nodes[:-1]), reversed(parents)):
                if parent[part]:
                    break
                del parent[part]
    content = (json.dumps(data, indent=2, ensure_ascii=False) + "\n").encode() if data else None
    plan.add(path, content, expected=raw)


# --- Owned-part identity: what of a shared integration target Forge owns (the installation journal's drift
# check, scripts/install_activation.py). A file another writer also edits (the host, the user) is compared by
# Forge's part only; every other file keeps whole-file identity (owned_part returns None for it).

# No installer writes the next two any more (Claude Code and Codex take Forge as a plugin). They stay so an
# installation journal from before the retirement still compares those targets by Forge's part.
# ~/.claude/settings.json: the top-level keys the retired machine install set (its hooks).
CLAUDE_SETTINGS_KEYS = ("hooks",)
# The marker-delimited text blocks the retired installers wrote into an instruction file a user also edits: the
# Codex boot block (generate_codex_agents.START/END) in ~/.codex/AGENTS.md and a consumer project's AGENTS.md,
# and the Claude boot block of ~/.claude/CLAUDE.md.
SHARED_BLOCKS = {
    "AGENTS.md": ("<!-- FORGE-CODEX-BOOT:START -->", "<!-- FORGE-CODEX-BOOT:END -->"),
    "CLAUDE.md": ("<!-- FORGE-CLAUDE-BOOT:START -->", "<!-- FORGE-CLAUDE-BOOT:END -->"),
}
# The machine setting (~/.config/forge/user.yaml): the keys the installer computes. `maintenance` is the
# person's choice of path (kept, never computed), comments and other keys are theirs.
SETTING_KEYS = ("version", "user_repo", "profile", "skill_links")


def owned_part(path: Path, content: bytes | None) -> str | None:
    """The identity of the part Forge owns in a shared integration target, or None for a file Forge writes
    whole. content None: the file is absent (it holds no Forge part). A file whose form cannot be read
    (invalid JSON or YAML, a malformed block) is identified whole, so any change to it counts."""
    path = Path(path)
    if path.name == "settings.json" and path.parent.name == ".claude":
        kind = "json"
    elif path.name in SHARED_BLOCKS:
        kind = "block"
    elif path.name == "user.yaml":
        kind = "setting"
    else:
        return None
    if content is None:
        content = b""
    try:
        if kind == "block":
            start, end = SHARED_BLOCKS[path.name]
            text = content.decode("utf-8")
            span = _block_span(text, path, start, end)
            return "block:" + (digest(text[span[0]:span[1]].encode()) if span else "none")
        names: tuple[str, ...]
        if kind == "json":
            data = json.loads(content) if content.strip() else {}
            names = CLAUDE_SETTINGS_KEYS
        else:
            data, names = _setting(content), SETTING_KEYS
        if not isinstance(data, dict):
            raise ValueError("not a mapping")
        return "keys:" + fragment_hash({name: data[name] for name in names if name in data}, {})
    except ValueError:  # an unreadable form (UnicodeDecodeError and JSONDecodeError included): whole file
        return "whole:" + digest(content)


def _setting(content: bytes) -> object:
    """The machine setting's mapping; ValueError when PyYAML is missing or the text is not YAML."""
    try:
        import yaml  # type: ignore[import-untyped]  # lazy: importing this module needs no PyYAML
    except ImportError as exc:
        raise ValueError("PyYAML missing") from exc
    try:
        return yaml.safe_load(content) if content.strip() else {}
    except yaml.YAMLError as exc:
        raise ValueError("not valid YAML") from exc


def merge_owned_part(path: Path, current: bytes | None, wanted: bytes | None) -> bytes | None:
    """`current` with Forge's part taken from `wanted` (a retry or rollback of a shared target): the JSON key,
    the text block or the setting's keys; every other byte of `current` stays. None: the file goes (`wanted`
    is no file and nothing else is left)."""
    path = Path(path)
    if current is None:
        return wanted
    if path.name in SHARED_BLOCKS:
        start, end = SHARED_BLOCKS[path.name]
        text, want = current.decode("utf-8"), (wanted or b"").decode("utf-8")
        span, found = _block_span(text, path, start, end), _block_span(want, path, start, end)
        block = want[found[0]:found[1]] if found else ""
        if span:
            text = text[:span[0]] + block + text[span[1]:]
        elif block:
            text = text + ("\n\n" if text else "") + block + "\n"
        rest: object = text.strip()
        merged = text.encode()
    else:
        settings = path.suffix == ".json"
        names = CLAUDE_SETTINGS_KEYS if settings else SETTING_KEYS
        load = (lambda raw: json.loads(raw) if raw and raw.strip() else {}) if settings else _setting
        data, source = load(current) or {}, (load(wanted) if wanted else {}) or {}
        if not isinstance(data, dict) or not isinstance(source, dict):
            raise ValueError(f"not a mapping: {path}")
        for name in names:
            if name in source:
                data[name] = source[name]
            else:
                data.pop(name, None)
        rest = data
        if settings:
            merged = (json.dumps(data, indent=2, ensure_ascii=False) + "\n").encode()
        else:
            import yaml  # type: ignore[import-untyped]

            merged = yaml.safe_dump(data, sort_keys=False, allow_unicode=True).encode()
    return None if wanted is None and not rest else merged
