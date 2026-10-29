"""INFRA: none. Temporary roots only; no inherited user configuration.

The fixture creates only the continuity inputs it needs, without installing a
host or importing project code.
"""
import json
import os
from pathlib import Path
import select
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]


def pytest_configure(config):
    for marker in ('integration', 'property'):
        config.addinivalue_line('markers', f'{marker}: capabilities test selection')


# Interpose only at real atomic replacements; never emulate publication.
# Barrier acknowledges the exact syscall boundary, with timeout only as deadlock guard.
INJECTOR = r'''
import json, os, runpy, sys
cfg = json.loads(os.environ['CAPABILITIES_FAULT'])
real_replace, real_rename = os.replace, os.rename
fired = False
def wrap(real):
    def call(src, dst, *a, **kw):
        global fired
        matches = cfg.get('syscall', 'replace') == 'replace' and not fired and os.path.abspath(os.fsdecode(dst)) == cfg['target']
        if matches and cfg['when'] == 'before':
            fired = True
            signal()
        result = real(src, dst, *a, **kw)
        if matches and cfg['when'] == 'after':
            fired = True
            signal()
        return result
    return call
def signal():
    os.write(cfg['signal_fd'], b'R')
    if cfg['action'] == 'crash':
        os._exit(91)
    assert os.read(cfg['release_fd'], 1) == b'G'
real_unlink = os.unlink
def unlink(path, *a, **kw):
    global fired
    if cfg.get('syscall') == 'unlink' and not fired and os.path.abspath(os.fsdecode(path)) == cfg['target']:
        fired = True
        signal()
    return real_unlink(path, *a, **kw)
os.unlink = unlink
os.replace = wrap(real_replace)
os.rename = wrap(real_rename)
sys.argv = sys.argv[1:]
sys.path.insert(0, os.path.dirname(sys.argv[0]))
runpy.run_path(sys.argv[0], run_name='__main__')
'''


class Invocation:
    def __init__(self, process, signal_fd=None, release_fd=None):
        self.process, self.signal_fd, self.release_fd = process, signal_fd, release_fd

    def reached(self):
        ready, _, _ = select.select([self.signal_fd], [], [], 10)
        assert ready and os.read(self.signal_fd, 1) == b'R', 'Production replacement fault boundary was not reached'

    def release(self):
        os.write(self.release_fd, b'G')

    def result(self):
        out, err = self.process.communicate(timeout=15)
        payload = json.loads(out) if out.strip() else {}
        return self.process.returncode, payload, err

    def close(self):
        if self.process.poll() is None:
            self.process.kill()
            self.process.wait()
        for fd in (self.signal_fd, self.release_fd):
            if fd is not None:
                os.close(fd)


class Continuity:
    def __init__(self, project, env, cwd):
        self.project, self.env, self.cwd, self.children = project, env, cwd, []

    def available(self):
        assert (ROOT / 'scripts/continuity.py').is_file(), 'Missing production scripts/continuity.py (RED boundary)'

    def start(self, command, request, scope='project', fault=None):
        self.available()
        argv = [sys.executable, str(ROOT / 'scripts/continuity.py'), command,
                '--scope', scope, '--project-root', str(self.project)]
        env, pass_fds = dict(self.env), ()
        signal_read = release_write = None
        if fault:
            signal_read, signal_write = os.pipe()
            release_read, release_write = os.pipe()
            config = dict(fault, signal_fd=signal_write, release_fd=release_read)
            env['CAPABILITIES_FAULT'] = json.dumps(config)
            pass_fds = (signal_write, release_read)
            argv = [sys.executable, '-c', INJECTOR, *argv[1:]]
        process = subprocess.Popen(argv, cwd=self.cwd, env=env, text=True,
                                   stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE, pass_fds=pass_fds)
        process.stdin.write(json.dumps(request))
        process.stdin.close()
        process.stdin = None
        if fault:
            os.close(signal_write)
            os.close(release_read)
        invocation = Invocation(process, signal_read, release_write)
        self.children.append(invocation)
        return invocation

    def call(self, command, request, scope='project', expected=0):
        code, result, err = self.start(command, request, scope).result()
        assert code == expected, (command, code, result, err)
        assert isinstance(result, dict)
        return result

    def snapshot(self, paths, previous=None, scope='project'):
        request = {'paths': paths}
        if previous is not None:
            request['previous'] = previous
        return self.call('snapshot', request, scope)

    def request(self, snapshot, replacements, operation='update', recovery=None):
        data = {'snapshot_token': snapshot['snapshot_token'], 'operation_id': operation,
                'intended_change': 'Synthetic scoped correction', 'source_references': ['synthetic:user'],
                'affected_paths': list(snapshot['files']), 'replacements': replacements}
        if recovery:
            data['recovery_operation_id'] = recovery
        return data

    def publish(self, snapshot, replacements, operation='update', recovery=None, expected=0, scope='project'):
        return self.call('publish', self.request(snapshot, replacements, operation, recovery), scope, expected)


@pytest.fixture
def continuity(tmp_path):
    project = tmp_path / 'project with spaces'
    (project / 'context/user').mkdir(parents=True)
    (project / 'context/user/profile.md').write_text('Synthetic user profile.\n')
    foreign = tmp_path / 'external artifacts'
    foreign.mkdir()
    home = tmp_path / 'isolated home'
    home.mkdir()
    config = home / 'user.json'
    config.write_text(json.dumps({'version': 1, 'user_repo': str(project), 'profile': 'daily'}))
    env = {k: v for k, v in os.environ.items() if k not in
           {'HOME', 'XDG_CONFIG_HOME', 'CODEX_HOME', 'AGENTS_HOME', 'FORGE_USER_CONFIG'}}
    env.update(HOME=str(home), FORGE_USER_CONFIG=str(config), PYTHONDONTWRITEBYTECODE='1')
    cli = Continuity(project, env, foreign)
    yield cli
    for child in cli.children:
        child.close()

