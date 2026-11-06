#!/usr/bin/env python3
"""Stopped-session installation transactions; no consumer knowledge is written.

The lock domain is deliberately independent of HOME and checkout. Test callers
may replace LOCK_ROOT in Python; the production CLI has no lock-domain override.
"""
from __future__ import annotations

import base64
from contextlib import contextmanager
import contextvars
import fcntl
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess
import tempfile
import uuid

try:
    from .managed_install import merge_owned_part, owned_part
except ImportError:
    from managed_install import merge_owned_part, owned_part

LOCK_ROOT = Path(f'/tmp/forge-install-{os.geteuid()}')
_HELD = contextvars.ContextVar('forge_install_lock', default=None)
TERMINAL = {'complete', 'rolled_back'}
# Phases whose operation is still open for its owner to continue. ``applying``
# is excluded: apply holds the exclusive lock, so a reader only ever observes it
# after an interrupted writer.
OPERATION_OPEN = {'prepared', 'validation_pending'}


def _safe_parents(path):
    path = Path(os.path.abspath(path))
    for parent in reversed(path.parents):
        if parent.is_symlink():
            raise ValueError(f'symlink parent: {parent}')
    return path


def identity(path):
    path = _safe_parents(path)
    try:
        info = path.lstat()
    except FileNotFoundError:
        return {'kind': 'absent'}
    if info.st_uid != os.geteuid():
        raise ValueError(f'resource belongs to another OS owner: {path}')
    mode = stat.S_IMODE(info.st_mode)
    if stat.S_ISLNK(info.st_mode):
        return {'kind': 'link', 'target': os.readlink(path)}
    if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
        raise ValueError(f'not a single regular file: {path}')
    data = path.read_bytes()
    return {'kind': 'file', 'mode': mode, 'sha256': hashlib.sha256(data).hexdigest(),
            'bytes': base64.b64encode(data).decode('ascii')}


def file_identity(data, mode=0o644):
    return {'kind': 'file', 'mode': mode, 'sha256': hashlib.sha256(data).hexdigest(),
            'bytes': base64.b64encode(data).decode('ascii')}


def instruction_path(root, path):
    """True iff a recorded source key is instruction Markdown under ``root``.

    Classification uses only the recorded key and the live identity kind: a
    symlink, directory or other non-regular entry is never instruction.
    """
    path = Path(os.path.abspath(path))
    if path.suffix != '.md' or not path.is_relative_to(Path(root).resolve()):
        return False
    try:
        return identity(path)['kind'] in {'file', 'absent'}
    except ValueError:
        return False


_GIT_SELECTION = {'GIT_DIR', 'GIT_WORK_TREE', 'GIT_INDEX_FILE', 'GIT_COMMON_DIR'}


def _git_query(root, *args):
    # ``-C root`` selects the repository; an inherited GIT_DIR (e.g. inside a
    # hook) must not redirect it. No optional index refresh is ever written.
    env = {k: v for k, v in os.environ.items() if k not in _GIT_SELECTION}
    env['GIT_OPTIONAL_LOCKS'] = '0'
    return subprocess.run(['git', '-C', str(root), *args], env=env, stdin=subprocess.DEVNULL,
                          capture_output=True, timeout=30)


def _first_line(raw):
    lines = os.fsdecode(raw).strip().splitlines()
    return lines[0][:200] if lines else 'no detail'


def _canonical(path):
    # Resolve directories only: a recorded source may itself be a symlink.
    path = Path(os.path.abspath(path))
    return Path(os.path.realpath(path.parent)) / path.name


def uncommitted_sources(root, paths, *, tracked_only=False):
    """Which ``paths`` Git reports as not committed in HEAD: ``(head, uncommitted, reason)``.

    Staged, modified, deleted and untracked paths count (``tracked_only``:
    untracked paths do not); ignored paths and nested repositories or
    worktrees (not this checkout's sources) never appear. ``uncommitted``
    holds sorted ``root``-relative paths (absolute outside ``root``); ``head``
    is the HEAD commit or ``None`` before the first commit. Read-only. Git
    missing, no work tree or a failed query yield ``(None, None, reason)``;
    never raises.
    """
    try:
        top = _git_query(root, 'rev-parse', '--show-toplevel')
        if top.returncode:
            return None, None, 'not a Git work tree: ' + _first_line(top.stderr)
        toplevel = Path(os.path.realpath(os.fsdecode(top.stdout).strip()))
        head = _git_query(root, 'rev-parse', '--verify', '-q', 'HEAD')
        commit = os.fsdecode(head.stdout).strip() if head.returncode == 0 else None
        untracked = '--untracked-files=no' if tracked_only else '--untracked-files=all'
        status = _git_query(root, 'status', '--porcelain=v1', '-z', untracked,
                            '--no-renames', '--ignored=no')
        if status.returncode:
            return None, None, f'git status failed (exit {status.returncode}): ' + _first_line(status.stderr)
        listed = set()
        fields = iter(status.stdout.split(b'\0'))
        for entry in fields:
            if len(entry) < 4:
                continue
            names = [entry[3:]]
            if entry[:1] in b'RC' or entry[1:2] in b'RC':
                names.append(next(fields, b''))  # rename/copy origin (not with --no-renames)
            for name in filter(None, names):
                path = toplevel / os.fsdecode(name)
                # With --untracked-files=all the only directory entry is a
                # nested repository or worktree: not this checkout's source.
                if name.endswith(b'/') and os.path.lexists(path / '.git'):
                    continue
                listed.add(path)
        base = Path(os.path.realpath(root))
        uncommitted = set()
        for item in paths:
            path = _canonical(item)
            if path in listed:
                uncommitted.add(str(path.relative_to(base)) if path.is_relative_to(base) else str(path))
        return commit, sorted(uncommitted), None
    except FileNotFoundError as exc:
        return None, None, f'git unavailable: {exc}'
    except subprocess.TimeoutExpired:
        return None, None, 'git query timed out'
    except Exception as exc:  # observation only: never fail the caller
        return None, None, f'{type(exc).__name__}: {exc}'


def _fsync_dir(path):
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def replace_identity(path, value):
    path = _safe_parents(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if value['kind'] == 'absent':
        path.unlink(missing_ok=True)
    elif value['kind'] == 'link':
        temp = path.parent / ('.forge-link-' + uuid.uuid4().hex)
        try:
            temp.symlink_to(value['target'])
            os.replace(temp, path)
        finally:
            temp.unlink(missing_ok=True)
    else:
        fd, name = tempfile.mkstemp(prefix='.forge-install-', dir=path.parent)
        try:
            with os.fdopen(fd, 'wb') as stream:
                os.fchmod(stream.fileno(), value['mode'])
                stream.write(base64.b64decode(value['bytes'], validate=True))
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(name, path)
        finally:
            Path(name).unlink(missing_ok=True)
    _fsync_dir(path.parent)


def _write_json(path, data):
    replace_identity(path, file_identity((json.dumps(data, sort_keys=True, indent=2) + '\n').encode(), 0o600))


def _private_lock_root(root):
    """The lock directory is this user's alone: a directory, owned, mode 0700 (else ValueError). Checked
    before the lease in it is read or the lock in it is taken."""
    info = root.lstat()
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.geteuid() or stat.S_IMODE(info.st_mode) != 0o700:
        raise ValueError(f'installation lock directory must be private, owned, mode 0700: {root}')


@contextmanager
def machine_lock(*, shared=False, blocking=True):
    """The machine's installation lock. ``blocking=False`` raises BlockingIOError when another process
    holds it (a session-start refresh must not wait)."""
    held = _HELD.get()
    if held is not None and held[2] == os.getpid():
        if held[1] and not shared:
            raise ValueError('cannot mutate under a read-only installation lock')
        yield held[0]
        return
    root = _safe_parents(LOCK_ROOT)
    if not root.exists():
        if shared:
            # No journal can exist until a writer creates the stable lock.
            yield None
            return
        try:
            root.mkdir(mode=0o700)
        except FileExistsError:
            pass
    _private_lock_root(root)
    path = root / 'mutation.lock'
    flags = os.O_RDWR | os.O_NOFOLLOW
    if not shared:
        flags |= os.O_CREAT
    try:
        fd = os.open(path, flags, 0o600)
    except FileNotFoundError:
        if shared:
            yield None
            return
        raise
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_uid != os.geteuid() or stat.S_IMODE(info.st_mode) != 0o600:
            raise ValueError('unsafe installation lock file')
        fcntl.flock(fd, (fcntl.LOCK_SH if shared else fcntl.LOCK_EX) | (0 if blocking else fcntl.LOCK_NB))
        token = _HELD.set((fd, shared, os.getpid()))
        try:
            yield fd
        finally:
            _HELD.reset(token)
            fcntl.flock(fd, fcntl.LOCK_UN)
    finally:
        os.close(fd)


def journal_path(home=None):
    base = Path(os.environ.get('XDG_STATE_HOME') or (Path(home or os.environ['HOME']) / '.local/state'))
    return base / 'forge/installation.json'


def _read_json(path):
    raw = identity(path)
    if raw['kind'] == 'absent':
        return None
    if raw['kind'] != 'file':
        raise ValueError(f'journal must be a regular file: {path}')
    return json.loads(base64.b64decode(raw['bytes']))


class SnapshotAuthority:
    """The byte snapshot of every installed source is the authority (the coordinated path).

    Between operations only instruction Markdown may drift; every other source must keep its recorded
    bytes, and every integration target its recorded identity (a shared target its Forge part). An
    operation ends in ``validation_pending`` and needs fresh-session evidence. This adapter adds no key: a
    journal without ``source_authority`` reads as snapshot on a coordinated machine.
    """

    name = 'snapshot'
    end_phase = 'validation_pending'
    records_bytes = True
    drift_prefix = 'source/integration drift without prepared baseline: '
    unrecorded_prefix = 'unrecorded source without prepared baseline: '

    def record(self, activation, data, head=None):
        """Keys this authority adds to a new journal: none."""

    def behind(self, activation, data, head=None):
        """A snapshot journal does not follow a commit."""
        return False

    def check_terminal(self, activation, previous):
        """Before a new prepare: may the terminal ``previous`` journal be continued?"""
        if previous['phase'] == 'complete':
            blocking, _ = self.terminal_drift(activation, previous, integration=False, snapshot=True)
            if blocking:
                raise ValueError(f'installation conflict: resource changed after snapshot: {blocking}')

    def check_baseline(self, activation, paths):
        """Before a new prepare: may ``paths`` be recorded as the new baseline? Any bytes may."""

    def check_sources(self, activation, data):
        """Inside an operation: every recorded source still holds its before or after bytes."""
        for path, item in data['sources'].items():
            allowed = [item['before']] + ([item['after']] if 'after' in item else [])
            if identity(path) not in allowed:
                raise ValueError(f'installation conflict: resource changed after snapshot: {path}')

    def install_drift(self, activation, data, inventory):
        """An install with nothing pending on a complete journal: the refusal message, or None."""
        blocking, _ = self.terminal_drift(activation, data, snapshot=True)
        if blocking:
            return f'installation conflict: resource changed after snapshot: {blocking}'
        blocking, _ = self.unrecorded_sources(activation, data, inventory)
        if blocking:
            return f'unrecorded source without prepared baseline: {blocking}'
        return None

    def terminal_drift(self, activation, data, *, integration=True, snapshot=False):
        direction = 'before' if data['phase'] == 'rolled_back' else 'after'
        accepted = []
        inventories = [('sources', data['sources'])] + ([('actions', data['actions'])] if integration else [])
        for name, inventory in inventories:
            for path, item in inventory.items():
                current = identity(path)
                if snapshot:
                    allowed = [item['before']] + ([item['after']] if 'after' in item else [])
                else:
                    allowed = [item.get(direction, item['before'])]
                if current in allowed or (name == 'actions' and target_unchanged(path, current, allowed)):
                    continue
                if name == 'sources' and instruction_path(activation.root, path):
                    accepted.append(path)
                    continue
                return path, accepted
        return None, accepted

    def unrecorded_sources(self, activation, data, inventory):
        accepted = []
        for path in sorted(str(Path(p).absolute()) for p in inventory):
            if path in data['sources']:
                continue
            if not instruction_path(activation.root, path):
                return path, accepted
            accepted.append(path)
        return None, accepted

    def drift(self, activation, data):
        """A terminal journal's readiness: ``(reason | None, instruction_paths)``."""
        blocking, accepted = self.terminal_drift(activation, data)
        return (self.drift_prefix + blocking if blocking else None), accepted

    def unrecorded(self, activation, data, inventory):
        """Sources the terminal journal never recorded: ``(reason | None, instruction_paths)``."""
        blocking, accepted = self.unrecorded_sources(activation, data, inventory)
        return (self.unrecorded_prefix + blocking if blocking else None), accepted

    def open_reason(self, activation, data, *, interrupted):
        """A prepared or interrupted operation is the developer's to continue: no reason of its own."""
        return None, False


def source_head(root):
    """The checkout's HEAD commit, or None (no Git work tree, no commit yet, Git missing). Read-only."""
    try:
        result = _git_query(root, 'rev-parse', '--verify', '-q', 'HEAD')
    except (OSError, subprocess.SubprocessError):
        return None
    head = os.fsdecode(result.stdout).strip()
    return head if result.returncode == 0 and head else None


def _content(value):
    """A recorded or live identity's file bytes; None when absent."""
    return None if value['kind'] == 'absent' else base64.b64decode(value.get('bytes', ''))


def target_unchanged(path, current, allowed, *, absent_ok=False):
    """Whether the integration target ``path`` (live identity ``current``) still is one of ``allowed``.

    A target another writer shares (managed_install.owned_part: ~/.claude/settings.json, the Forge block of
    an AGENTS.md or CLAUDE.md, the machine setting) is compared by the part Forge owns, so a host's or the
    user's write outside it never counts. Every other target keeps its whole identity (kind, mode, bytes).
    Used between operations and inside them (_check: retry and rollback merge Forge's part into the current
    file). ``absent_ok``: a shared target whose Forge part is gone (no block, no owned key, no file) is not
    installed rather than changed; the next write adds the part again.
    """
    if current in allowed:
        return True
    if current['kind'] == 'link':
        return False
    owned = owned_part(Path(path), _content(current))
    if owned is not None and absent_ok and owned == owned_part(Path(path), None):
        return True
    return owned is not None and any(
        item['kind'] != 'link' and owned_part(Path(path), _content(item)) == owned for item in allowed)


def absent_parts(data, served=None):
    """Shared targets whose recorded Forge part is gone now: not installed, so the next refresh writes them.
    ``served``: only these paths count (the targets the recorded selection still renders)."""
    direction = 'before' if data['phase'] == 'rolled_back' else 'after'
    found = []
    for path, item in data['actions'].items():
        if served is not None and path not in served:
            continue
        none = owned_part(Path(path), None)
        wanted = item.get(direction, item['before'])
        if none is not None and wanted['kind'] != 'link' and owned_part(Path(path), _content(wanted)) != none:
            current = identity(path)
            if current['kind'] != 'link' and owned_part(Path(path), _content(current)) == none:
                found.append(path)
    return found


def _byte_journal(data):
    """The journal records source bytes: every journal except a commit one (a journal without the key was
    written by a snapshot operation or before the key existed, and keeps its bytes)."""
    return data.get('source_authority') != 'commit'


def _action_drift(data, *, snapshot):
    direction = 'before' if data['phase'] == 'rolled_back' else 'after'
    for path, item in data['actions'].items():
        if snapshot:
            allowed = [item['before']] + ([item['after']] if 'after' in item else [])
        else:
            allowed = [item.get(direction, item['before'])]
        if not target_unchanged(path, identity(path), allowed, absent_ok=True):
            return path
    return None


class CommitAuthority:
    """The checkout's Git commit is the authority (the user path: ``git pull`` is the update).

    A commit counts as a released state: committed source changes never block, and an operation ends
    ``complete`` without a validation session. Git alone judges the sources, in every check (status, the
    check before a prepare, apply, retry, rollback): tracked non-Markdown sources that differ from HEAD (the
    half-applied case) block; untracked files and instruction Markdown do not. The journal records the
    source paths, ``source_authority: commit`` and the ``source_commit`` it was prepared from, no source
    bytes. Integration targets keep their recorded identity (a shared target its Forge part).
    """

    name = 'commit'
    end_phase = 'complete'
    records_bytes = False
    DIRTY = 'uncommitted source change: {}; commit or discard it (a developer checkout: --coordinated)'
    CHANGED = 'a Forge entry was changed outside Forge: {} (the Forge part of it); restore it'
    UNAVAILABLE = 'source commit unavailable: {}'
    PREPARED = 'an installation operation is prepared from committed sources; the next start completes it'
    INTERRUPTED = 'an installation operation was interrupted; the next start completes it'

    def record(self, activation, data, head=None):
        data['source_authority'] = self.name
        data['source_commit'] = head if head is not None else source_head(activation.root)

    def behind(self, activation, data, head=None):
        """The checkout's HEAD is not the commit the journal was prepared from (a journal without
        ``source_commit`` always is)."""
        return (head if head is not None else source_head(activation.root)) != data.get('source_commit')

    def dirty(self, activation, paths):
        """``(path, reason)``: the first tracked non-Markdown path among ``paths`` that differs from HEAD,
        or why that cannot be known; ``(None, None)`` when the sources are committed."""
        head, uncommitted, reason = uncommitted_sources(activation.root, list(paths), tracked_only=True)
        if reason is not None:
            return None, reason
        if head is None:
            return None, 'the source checkout has no commit'
        for relative in uncommitted:
            if Path(relative).suffix != '.md':
                path = Path(relative)
                return str(path if path.is_absolute() else activation.root / path), None
        return None, None

    def source_reason(self, activation, paths):
        """Why ``paths`` cannot count as a released state, or None when Git holds them committed."""
        path, reason = self.dirty(activation, paths)
        if reason is not None:
            return self.UNAVAILABLE.format(reason)
        return self.DIRTY.format(path) if path else None

    def check_terminal(self, activation, previous):
        """Committed changes never block; the new baseline is checked by its own authority."""

    def check_baseline(self, activation, paths):
        refusal = self.source_reason(activation, paths)
        if refusal:
            raise ValueError(refusal)

    def check_sources(self, activation, data):
        """Inside an operation (apply, retry, rollback, validate): Git judges the recorded sources, also
        after further pulls; recorded bytes, if any, are not compared."""
        self.check_baseline(activation, data['sources'])

    def install_drift(self, activation, data, inventory):
        paths = set(data['sources']) | {str(Path(p).absolute()) for p in inventory}
        refusal = self.source_reason(activation, sorted(paths))
        if refusal:
            return refusal
        changed = _action_drift(data, snapshot=True)
        return self.CHANGED.format(changed) if changed else None

    def drift(self, activation, data):
        reason = self.source_reason(activation, data['sources'])
        if reason is None:
            changed = _action_drift(data, snapshot=False)
            reason = self.CHANGED.format(changed) if changed else None
        return reason, []

    def unrecorded(self, activation, data, inventory):
        new = sorted({str(Path(p).absolute()) for p in inventory} - set(data['sources']))
        return (self.source_reason(activation, new) if new else None), []

    def open_reason(self, activation, data, *, interrupted):
        """A prepared or interrupted operation on committed sources: ``(reason, True)``, the next start (the
        refresh) completes it; on dirty sources the dirt, which it cannot complete."""
        reason = self.source_reason(activation, data['sources'])
        if reason:
            return reason, False
        return (self.INTERRUPTED if interrupted else self.PREPARED), True


SNAPSHOT = SnapshotAuthority()
COMMIT = CommitAuthority()
AUTHORITIES = {SNAPSHOT.name: SNAPSHOT, COMMIT.name: COMMIT}


class Activation:
    def __init__(self, source_root, journal=None, default_authority=None):
        self.root = Path(source_root).resolve()
        self.journal = _safe_parents(journal or journal_path())
        # The authority of a journal without ``source_authority`` and of a prepare that names none:
        # forge_install passes the machine setting's choice (commit unless maintenance: coordinated); an
        # Activation never reads the setting itself.
        self.default_authority = default_authority or SNAPSHOT

    def authority_of(self, data):
        """The source authority of ``data``: recorded, else the default (also for no journal)."""
        name = data.get('source_authority') if data else None
        if name is None:
            return self.default_authority
        if name not in AUTHORITIES:
            raise ValueError(f'unknown installation source authority: {name!r}')
        return AUTHORITIES[name]

    def _load(self):
        data = _read_json(self.journal)
        if LOCK_ROOT.exists():
            _private_lock_root(_safe_parents(LOCK_ROOT))  # before the lease in it is read
            lease = _read_json(LOCK_ROOT / 'active.json')
            if lease and lease.get('journal') == str(self.journal) and lease.get('snapshot'):
                # The stable lease is the write-ahead record for interrupted
                # replacement of an older journal, including another UUID.
                data = lease['snapshot']
        if data and (data.get('version') != 1 or data.get('source_root') != str(self.root)):
            raise ValueError('installation journal belongs to a different source checkout')
        return data

    def _lease(self, data=None):
        lease = _read_json(LOCK_ROOT / 'active.json')
        if lease and lease['phase'] not in TERMINAL:
            if not data or lease['operation_id'] != data['operation_id'] or lease['journal'] != str(self.journal):
                raise ValueError('unfinished installation maintenance lease; inspect the active journal: ' + lease['journal'])

    def _save(self, data):
        self.journal.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        lease = {'operation_id': data['operation_id'], 'journal': str(self.journal), 'phase': 'recovery_required', 'snapshot': data}
        _write_json(LOCK_ROOT / 'active.json', lease)
        _write_json(self.journal, data)
        lease['phase'] = data['phase']
        lease.pop('snapshot')
        _write_json(LOCK_ROOT / 'active.json', lease)

    def status(self):
        with machine_lock(shared=True):
            data = self._load()
            if not data:
                return {'version': 1, 'phase': 'unprepared'}
            result = {k: v for k, v in data.items() if k not in {'sources', 'actions', 'completed'}}
            result['completed_count'] = len(set(data['completed']))
            result['action_count'] = len(data['actions'])
            result['compatibility'] = [{'project_root': entry['project_root'], 'runs': [
                {key: value for key, value in state.items() if key != 'state'} for state in entry['states']
            ]} for entry in data.get('compatibility', [])]
            authority = self.authority_of(data)
            lease = _read_json(LOCK_ROOT / 'active.json')
            if lease and lease.get('journal') == str(self.journal) and lease.get('snapshot'):
                result['phase'] = 'recovery_required'
                result['journal_transition_pending'] = True
                self._open_reason(result, authority, data, interrupted=True)
                return result
            if data['phase'] in TERMINAL:
                reason, accepted = authority.drift(self, data)
                if reason:
                    result['phase'] = 'recovery_required'
                    result['reason'] = reason
                    return result
                if accepted:
                    result['instruction_drift'] = sorted(str(Path(p).relative_to(self.root)) for p in accepted)
            elif data['phase'] in {'prepared', 'applying', 'recovery_required'}:
                self._open_reason(result, authority, data, interrupted=data['phase'] != 'prepared')
            return result

    def _open_reason(self, result, authority, data, *, interrupted):
        """Status of an open operation: the reason, and whether the next start completes it
        (``next_start_completes``: the refresh and the implicit install continue it instead of refusing)."""
        reason, completes = authority.open_reason(self, data, interrupted=interrupted)
        changed = self._changed_action(data) if completes else None
        if changed:  # the next start would refuse it: name the file and the Forge part
            reason, completes = COMMIT.CHANGED.format(changed), False
        if reason:
            result['reason'] = reason
        if completes:
            result['next_start_completes'] = True

    def drift(self, data):
        """Readiness of a terminal journal by its authority: ``(reason | None, instruction_paths)``.

        Snapshot: only instruction Markdown in ``sources`` is accepted; any other source and every
        ``actions`` entry (a shared target by its Forge part) stays blocking. Commit: Git judges the
        sources, the actions as under snapshot. Never used inside an operation.
        """
        return self.authority_of(data).drift(self, data)

    def unrecorded(self, data, inventory):
        """Current source-inventory entries absent from a terminal journal: ``(reason | None,
        instruction_paths)`` by the journal's authority. Snapshot: unrecorded instruction Markdown is
        accepted, any other new source needs a prepared baseline; commit: only an uncommitted one blocks.
        Never used inside an operation.
        """
        return self.authority_of(data).unrecorded(self, data, inventory)

    def prepare(self, sources, targets, *, authority=None, consumer_roots=(), closure=(), source_commit=None):
        """Open a new operation under ``authority`` (the default authority when None), recorded once here;
        ``source_commit``: the HEAD the caller planned from (read here when None)."""
        authority = authority or self.default_authority
        with machine_lock():
            previous = self._load()
            self._lease(previous)
            if previous and previous['phase'] not in TERMINAL:
                raise ValueError('unfinished maintenance; retry or rollback the existing operation')
            if previous:
                self.authority_of(previous).check_terminal(self, previous)
            paths = {str(Path(p).absolute()) for p in sources}
            if previous:
                paths.update(previous['sources'])
            authority.check_baseline(self, sorted(paths))
            source_values = {p: ({'before': identity(p)} if authority.records_bytes else {}) for p in sorted(paths)}
            integrations = {str(Path(p).absolute()) for p in targets}
            if previous:
                for name, item in previous['actions'].items():
                    # A rolled-back absent link may become an ordinary parent
                    # directory in the next profile; children own its contents.
                    parent_only = (previous['phase'] == 'rolled_back' and item['before']['kind'] == 'absent'
                                   and any(Path(target).is_relative_to(Path(name)) and target != name for target in integrations))
                    if not parent_only:
                        integrations.add(name)
            data = {'version': 1, 'operation_id': str(uuid.uuid4()), 'source_root': str(self.root),
                    'phase': 'prepared', 'closure': list(closure), 'consumer_roots': [str(Path(p).resolve()) for p in consumer_roots],
                    'sources': source_values, 'actions': {p: {'before': identity(p)} for p in sorted(integrations)},
                    'completed': [], 'compatibility': []}
            authority.record(self, data, source_commit)
            self._save(data)
            return self.status()

    def seal_updated_sources(self, source_paths=()):
        """Record the candidate generation before its dependency preflight.

        A failed closure check can then restore the matched prepared baseline.
        Calling this again cannot adopt subsequent edits to an already sealed
        candidate generation. Under commit, Git judges the candidate instead.
        """
        with machine_lock():
            data = self._load()
            self._lease(data)
            if not data or data['phase'] != 'prepared':
                return
            if data.get('sources_sealed'):
                self._check(data, integration=True, source=True)
                return
            for path in source_paths:
                data['sources'].setdefault(str(Path(path).absolute()),
                                           {'before': {'kind': 'absent'}} if _byte_journal(data) else {})
            if self.authority_of(data) is COMMIT:
                COMMIT.check_sources(self, data)
            if _byte_journal(data):
                for path, item in data['sources'].items():
                    item['after'] = identity(path)
            data['sources_sealed'] = True
            self._save(data)

    def _check(self, data, *, integration, source):
        """Inside an operation: sources by the journal's authority, integration targets by target_unchanged
        (whole, or a shared target's Forge part)."""
        if source:
            self.authority_of(data).check_sources(self, data)
        changed = self._changed_action(data) if integration else None
        if changed:
            raise ValueError(f'installation conflict: resource changed after snapshot: {changed}')

    @staticmethod
    def _changed_action(data):
        for path, item in data['actions'].items():
            allowed = [item['before']] + ([item['after']] if 'after' in item else [])
            if not target_unchanged(path, identity(path), allowed, absent_ok=True):
                return path
        return None

    def _compatibility(self, data, compatibility, *, rollback):
        """Rollback restores source bytes only under snapshot; under commit the sources stay at HEAD."""
        return compatibility(data, rollback=rollback and self.authority_of(data) is SNAPSHOT)

    def apply(self, plan, links=(), *, source_paths=(), modes=None, compatibility=None, closure=None):
        with machine_lock():
            data = self._load()
            self._lease(data)
            if not data:
                self.prepare(source_paths, [*plan.files, *(p for p, _ in links)])
                data = self._load()
            if data['phase'] != 'prepared':
                raise ValueError('maintenance is not prepared; use retry, validate or rollback')
            self._check(data, integration=True, source=False)
            if closure is not None:
                data['closure'] = list(closure)
            for path in source_paths:
                key = str(Path(path).absolute())
                if key not in data['sources']:
                    data['sources'][key] = {'before': {'kind': 'absent'}} if _byte_journal(data) else {}
            snapshot = self.authority_of(data) is SNAPSHOT
            for path, item in data['sources'].items():
                if 'before' not in item:
                    continue  # a commit journal records no source bytes
                current = identity(path)
                if snapshot and data.get('sources_sealed') and current != item.get('after', current):
                    raise ValueError(f'candidate sources changed after preflight: {path}')
                item['after'] = current
            for path, (old, new) in plan.files.items():
                key = str(path)
                current = identity(path)
                expected = None if current['kind'] == 'absent' else base64.b64decode(current.get('bytes', ''))
                if current['kind'] not in {'file', 'absent'} or expected != old:
                    raise ValueError(f'installation conflict during preflight: {path}')
                if key not in data['actions']:
                    if current['kind'] != 'absent':
                        raise ValueError(f'target absent from prepared baseline: {path}')
                    data['actions'][key] = {'before': current}
                mode = (modes or {}).get(path, current.get('mode', 0o644))
                data['actions'][key]['after'] = {'kind': 'absent'} if new is None else file_identity(new, mode)
            for path, target in links:
                key = str(path)
                if key not in data['actions']:
                    current = identity(path)
                    if current['kind'] != 'absent':
                        raise ValueError(f'link absent from prepared baseline: {path}')
                    data['actions'][key] = {'before': current}
                data['actions'][key]['after'] = {'kind': 'absent'} if target is None else {'kind': 'link', 'target': str(target)}
            for item in data['actions'].values():
                item.setdefault('after', item['before'])
            if compatibility:
                data['compatibility'] = compatibility(data, rollback=False)
            data['phase'] = 'applying'
            self._save(data)
            self._run(data)
            return self.status()

    def _run(self, data, *, rollback=False):
        direction = 'before' if rollback else 'after'
        try:
            self._check(data, integration=True, source=True)
            # Under commit the sources are Git's: a rollback restores the integration targets only.
            sources = rollback and self.authority_of(data) is SNAPSHOT
            inventories = [data['sources'], data['actions']] if sources else [data['actions']]
            for inventory in inventories:
                for path, item in inventory.items():
                    wanted, current = item.get(direction, item['before']), identity(path)
                    shared = inventory is data['actions'] and owned_part(Path(path), None) is not None
                    recorded = current in (item['before'], item.get('after'))  # no host write: the plan's bytes
                    if shared and not recorded and current['kind'] == 'file' and wanted['kind'] != 'link':
                        # A shared target: Forge's part goes into the current file; the host's bytes stay.
                        if not target_unchanged(path, current, [wanted]):
                            merged = merge_owned_part(Path(path), _content(current), _content(wanted))
                            replace_identity(Path(path), {'kind': 'absent'} if merged is None
                                             else file_identity(merged, current['mode']))
                    elif current != wanted:
                        replace_identity(Path(path), wanted)
                    data['completed'].append(path)
            if not rollback:
                for name, item in data['actions'].items():
                    if item.get('after', {}).get('kind') != 'absent':
                        continue
                    path = Path(name)
                    skill_roots = [parent for parent in path.parents if parent.name in {'skills', 'agents'} and parent.parent.name in {'.claude', '.codex', '.agents'}]
                    if skill_roots:
                        boundary = skill_roots[0]
                        for parent in path.parents:
                            if parent == boundary:
                                break
                            try:
                                parent.rmdir()
                            except (FileNotFoundError, OSError):
                                break
            data['phase'] = 'rolled_back' if rollback else self.authority_of(data).end_phase
            self._save(data)
        except BaseException:
            data['phase'] = 'recovery_required'
            data['recovery_direction'] = direction
            self._save(data)
            raise

    def retry(self, *, compatibility=None):
        with machine_lock():
            data = self._load()
            self._lease(data)
            lease = _read_json(LOCK_ROOT / 'active.json')
            if data and lease and lease.get('snapshot') and lease.get('journal') == str(self.journal):
                self._check(data, integration=True, source=True)
                self._save(data)
                if data['phase'] in TERMINAL | {'prepared'}:
                    return self.status()
            if not data or data['phase'] not in {'applying', 'recovery_required', 'validation_pending'}:
                raise ValueError('no interrupted installation to retry')
            rollback = data.get('recovery_direction') == 'before'
            if compatibility:
                data['compatibility'] = self._compatibility(data, compatibility, rollback=rollback)
            self._run(data, rollback=rollback)
            return self.status()

    def rollback(self, *, compatibility=None):
        with machine_lock():
            data = self._load()
            self._lease(data)
            if not data or data['phase'] == 'rolled_back':
                raise ValueError('no installation to roll back')
            self._check(data, integration=True, source=True)
            if compatibility:
                data['compatibility'] = self._compatibility(data, compatibility, rollback=True)
            data.pop('completion_commit_state', None)  # describes a completion being undone
            data['phase'] = 'applying'
            data['recovery_direction'] = 'before'
            self._save(data)
            self._run(data, rollback=True)
            return self.status()

    def validation_status(self, operation_id, *, compatibility=None):
        """Read-only permission for one exact candidate's controlled acceptance run."""
        with machine_lock(shared=True):
            data = self._load()
            self._lease(data)
            status = self.status()
            if not data or status['phase'] != 'validation_pending' or operation_id != data['operation_id']:
                raise ValueError('validation session requires the exact pending operation ID')
            self._installed(data)
            if compatibility:
                compatibility(data, rollback=False)
            status['validation_session'] = True
            return status

    @staticmethod
    def _installed(data):
        """Every recorded identity is in place (a commit journal's sources have none)."""
        for name, inventory in (('sources', data['sources']), ('actions', data['actions'])):
            for path, item in inventory.items():
                current = identity(path)
                if 'after' in item and current != item['after'] and not (
                        name == 'actions' and target_unchanged(path, current, [item['after']])):
                    raise ValueError(f'activation incomplete: {path}')

    def validate(self, operation_id, evidence):
        with machine_lock():
            data = self._load()
            self._lease(data)
            if not data or data['phase'] != 'validation_pending' or operation_id != data['operation_id']:
                raise ValueError('validation requires the exact pending operation ID')
            self._check(data, integration=True, source=True)
            self._installed(data)
            observed = identity(evidence)
            if observed['kind'] != 'file' or not base64.b64decode(observed['bytes']).strip():
                raise ValueError('fresh-session validation evidence is required')
            data['validation'] = {'path': str(Path(evidence).absolute()), 'sha256': observed['sha256']}
            # Snapshot at completion: was the installed generation committed?
            # Observation only; optional key, older journals lack it, no
            # installer logic reads it, rollback removes it.
            head, uncommitted, reason = uncommitted_sources(self.root, list(data['sources']))
            commit_state = {'head': head,
                            'uncommitted_count_at_completion': None if uncommitted is None else len(uncommitted)}
            if reason is not None:
                commit_state['reason'] = reason
            data['completion_commit_state'] = commit_state
            data['phase'] = 'complete'
            self._save(data)
            return self.status()


def workflow_compatibility(data, *, rollback=False):
    """Ask each consuming engine to interpret exact, explicitly scoped runs.

    Materialize source before-images for rollback; never copy or rewrite states.
    Older engines without the exact export contract fail closed for retained runs.
    """
    import subprocess
    import sys
    roots = data.get('consumer_roots', [])
    source = Path(data['source_root'])
    records = []
    with tempfile.TemporaryDirectory(prefix='forge-compatibility-') as temp:
        baseline = Path(temp)
        if rollback:
            for name, item in data['sources'].items():
                path = Path(name)
                if path.is_relative_to(source) and item['before']['kind'] == 'file':
                    relative = path.relative_to(source)
                    if relative.parts[0] in {'scripts', 'workflows', 'framework'}:
                        replace_identity(baseline / relative, item['before'])
        for root in roots:
            project = Path(root)
            import re
            directory = project / '.workflow-state'
            if directory.is_symlink() or (directory / 'archive').is_symlink():
                raise ValueError('unsafe workflow state directory')
            ids = []
            references = {}
            paths = sorted(directory.glob('*.json')) + sorted((directory / 'archive').glob('*.json'))
            for path in paths:
                if path.is_symlink():
                    raise ValueError(f'unsafe workflow state path: {path}')
                value = json.loads(path.read_text())
                wid = value.get('workflow_id')
                if not isinstance(wid, str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]*', wid) or wid in references:
                    raise ValueError(f'unknown or ambiguous workflow state identity: {path}')
                ids.append(wid)
                references[wid] = str(path.relative_to(project))
            retained = {state['workflow_id'] for entry in data.get('compatibility', [])
                        if entry['project_root'] == root for state in entry['states']}
            if retained - set(ids):
                raise ValueError('retained workflow states missing: ' + ', '.join(sorted(retained - set(ids))))
            if not ids:
                continue
            def export(framework):
                # The compatibility policy is owned by the development engine;
                # execute it with the *consuming generation's* loader and state
                # vocabulary, including predecessor engines without a new CLI.
                import inspect
                import importlib
                module = (__package__ + '.workflow_engine') if __package__ else 'workflow_engine'
                try:
                    engine_owner = importlib.import_module(module)
                except ImportError as exc:
                    raise ValueError('selected development state requires its engine compatibility owner') from exc
                # The predecessor lacks the shared pure projection helper. Copy
                # the validator's existing closure, without changing its policy.
                validator = (inspect.getsource(engine_owner._definition_projection) + "\n" +
                             inspect.getsource(engine_owner._continuation_definition) + "\n" +
                             inspect.getsource(engine_owner._maintenance_definition))
                harness = """import hashlib,json,sys
from pathlib import Path
root, project = map(Path, sys.argv[1:])
sys.path.insert(0, str(root))
import scripts.workflow_engine as engine
request = json.load(sys.stdin)
engine.PROJECT_ROOT = project
engine.REPO_ROOT = project
engine.STATE_DIR = project / '.workflow-state'
engine.ARCHIVE_DIR = engine.STATE_DIR / 'archive'
exec(request['validator'], engine.__dict__)
result = []
with engine._state_lock():
    for wid in request['workflow_ids']:
        path = project / request['references'][wid]
        if path.is_symlink():
            raise ValueError('unsafe workflow state path')
        raw = path.read_bytes()
        state = json.loads(raw)
        if state.get('workflow_id') != wid:
            raise ValueError('workflow identity mismatch')
        definition = engine._maintenance_definition(
            state, archived=path.parent == engine.ARCHIVE_DIR)
        result.append({'workflow_id':wid,'state_file':str(path.relative_to(project)),
          'revision':state.get('revision',0),'sha256':hashlib.sha256(raw).hexdigest(),
          'definition_fingerprint':hashlib.sha256(json.dumps(definition,sort_keys=True).encode()).hexdigest(),
          'state':state})
print(json.dumps(result))
"""
                result = subprocess.run([sys.executable, '-B', '-c', harness, str(framework), str(project)],
                                        input=json.dumps({'workflow_ids': ids, 'references': references, 'validator': validator}), text=True,
                                        capture_output=True, cwd=framework, timeout=60)
                if result.returncode:
                    raise ValueError('workflow compatibility blocked by consuming engine: ' + str(framework) + ': ' + result.stderr.strip().splitlines()[-1])
                return json.loads(result.stdout)
            current = export(source)
            old_records = [record for record in data.get('compatibility', []) if record['project_root'] == root]
            old = export(baseline) if rollback else (old_records[0]['states'] if old_records else [])
            previous = {item['workflow_id']: item['definition_fingerprint'] for item in old}
            for item in current:
                if item['workflow_id'] in previous:
                    import importlib
                    module = (__package__ + '.workflow_engine') if __package__ else 'workflow_engine'
                    engine_owner = importlib.import_module(module)
                    before, after = previous[item['workflow_id']], item['definition_fingerprint']
                    if rollback:
                        before, after = after, before
                    if not engine_owner.continuation_compatible(item['state']['workflow'], before, after,
                                                               direction='rollback' if rollback else 'upgrade'):
                        raise ValueError('workflow meaning changed: ' + item['workflow_id'])
            records.append({'project_root': root, 'states': current})
    return records
