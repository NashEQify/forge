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
import tempfile
import uuid

LOCK_ROOT = Path(f'/tmp/forge-install-{os.geteuid()}')
_HELD = contextvars.ContextVar('forge_install_lock', default=None)
TERMINAL = {'complete', 'rolled_back'}


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


@contextmanager
def machine_lock(*, shared=False):
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
    info = root.lstat()
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.geteuid() or stat.S_IMODE(info.st_mode) != 0o700:
        raise ValueError(f'installation lock directory must be private, owned, mode 0700: {root}')
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
        fcntl.flock(fd, fcntl.LOCK_SH if shared else fcntl.LOCK_EX)
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


class Activation:
    def __init__(self, source_root, journal=None):
        self.root = Path(source_root).resolve()
        self.journal = _safe_parents(journal or journal_path())

    def _load(self):
        data = _read_json(self.journal)
        if LOCK_ROOT.exists():
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
            lease = _read_json(LOCK_ROOT / 'active.json')
            if lease and lease.get('journal') == str(self.journal) and lease.get('snapshot'):
                result['phase'] = 'recovery_required'
                result['journal_transition_pending'] = True
                return result
            if data['phase'] in TERMINAL:
                direction = 'before' if data['phase'] == 'rolled_back' else 'after'
                for inventory in (data['sources'], data['actions']):
                    for path, item in inventory.items():
                        if identity(path) != item.get(direction, item['before']):
                            result['phase'] = 'recovery_required'
                            result['reason'] = 'source/integration drift without prepared baseline: ' + path
                            return result
            return result

    def prepare(self, sources, targets, *, consumer_roots=(), closure=()):
        with machine_lock():
            previous = self._load()
            self._lease(previous)
            if previous and previous['phase'] not in TERMINAL:
                raise ValueError('unfinished maintenance; retry or rollback the existing operation')
            if previous and previous['phase'] == 'complete':
                self._check(previous, integration=False, source=True)
            paths = {str(Path(p).absolute()) for p in sources}
            if previous:
                paths.update(previous['sources'])
            source_values = {p: {'before': identity(p)} for p in sorted(paths)}
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
            self._save(data)
            return self.status()

    def seal_updated_sources(self, source_paths=()):
        """Record the candidate generation before its dependency preflight.

        A failed closure check can then restore the matched prepared baseline.
        Calling this again cannot adopt subsequent edits to an already sealed
        candidate generation.
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
                data['sources'].setdefault(str(Path(path).absolute()), {'before': {'kind': 'absent'}})
            for path, item in data['sources'].items():
                item['after'] = identity(path)
            data['sources_sealed'] = True
            self._save(data)

    def _check(self, data, *, integration, source):
        for inventory in ([data['sources']] if source else []) + ([data['actions']] if integration else []):
            for path, item in inventory.items():
                current = identity(path)
                allowed = [item['before']]
                if 'after' in item:
                    allowed.append(item['after'])
                if current not in allowed:
                    raise ValueError(f'installation conflict: resource changed after snapshot: {path}')

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
                    data['sources'][key] = {'before': {'kind': 'absent'}}
            for path, item in data['sources'].items():
                current = identity(path)
                if data.get('sources_sealed') and current != item.get('after', current):
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
            inventories = [data['sources'], data['actions']] if rollback else [data['actions']]
            for inventory in inventories:
                for path, item in inventory.items():
                    wanted = item.get(direction, item['before'])
                    if identity(path) != wanted:
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
            data['phase'] = 'rolled_back' if rollback else 'validation_pending'
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
                data['compatibility'] = compatibility(data, rollback=rollback)
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
                data['compatibility'] = compatibility(data, rollback=True)
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
            for inventory in (data['sources'], data['actions']):
                for path, item in inventory.items():
                    if identity(path) != item['after']:
                        raise ValueError(f'activation incomplete: {path}')
            if compatibility:
                compatibility(data, rollback=False)
            status['validation_session'] = True
            return status

    def validate(self, operation_id, evidence):
        with machine_lock():
            data = self._load()
            self._lease(data)
            if not data or data['phase'] != 'validation_pending' or operation_id != data['operation_id']:
                raise ValueError('validation requires the exact pending operation ID')
            self._check(data, integration=True, source=True)
            for inventory in (data['sources'], data['actions']):
                for path, item in inventory.items():
                    if identity(path) != item['after']:
                        raise ValueError(f'activation incomplete: {path}')
            observed = identity(evidence)
            if observed['kind'] != 'file' or not base64.b64decode(observed['bytes']).strip():
                raise ValueError('fresh-session validation evidence is required')
            data['validation'] = {'path': str(Path(evidence).absolute()), 'sha256': observed['sha256']}
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
                validator = inspect.getsource(engine_owner._continuation_definition)
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
        definition = engine._continuation_definition(state)
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
