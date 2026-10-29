"""INFRA: none — real temporary files and cooperating CLI processes.

Only the JSON adapter names are assumptions; assertions concern observable data.
No production implementation is imported or replaced by a fake publisher.
"""
import json

import pytest

pytestmark = [pytest.mark.integration, pytest.mark.property]
OWNER = 'context/topic.md'
REF = 'context/session-handover.md'
PENDING = 'context/maintenance-pending.md'


def seed(cli, owner='old', reference='old'):
    (cli.project / OWNER).write_text(owner)
    (cli.project / REF).write_text(reference)


def texts(snapshot):
    return {path: item['text'] for path, item in snapshot['files'].items()}


# TC-004 | INFRA: none
@pytest.mark.parametrize('attack', ['personal-target', 'traversal', 'escaping-symlink'])
def test_scope_leakage(continuity, attack):
    cli = continuity
    seed(cli)
    private = cli.project / 'context/user/maintenance-pending.md'
    private.write_text('PRIVATE-CANARY-42')
    before = private.read_bytes()
    snap = cli.snapshot([OWNER, REF])
    assert 'PRIVATE-CANARY-42' not in json.dumps(snap)
    cli.publish(snap, {OWNER: 'project defect', REF: 'project defect'})
    snap = cli.snapshot([OWNER])
    target = {'personal-target': 'context/user/preferences.md',
              'traversal': '../outside.md', 'escaping-symlink': 'context/escape/fact.md'}[attack]
    outside = cli.cwd / 'outside'
    outside.mkdir()
    if attack == 'escaping-symlink':
        (cli.project / 'context/escape').symlink_to(outside, target_is_directory=True)
    request = cli.request(snap, {target: 'PRIVATE-CANARY-42'}, operation='private-attempt')
    request['affected_paths'].append(target)
    code, answer, error = cli.start('publish', request).result()
    assert code == 2
    assert answer['status'] == 'not_persisted'
    assert 'PRIVATE-CANARY-42' not in json.dumps(answer) + error
    assert private.read_bytes() == before
    assert not (cli.project / 'context/user/preferences.md').exists()
    assert list(outside.iterdir()) == []
    assert (cli.project / OWNER).read_text() == 'project defect'
    pending = cli.project / PENDING
    assert not pending.exists() or 'PRIVATE-CANARY-42' not in pending.read_text()
    # Project-only inspection must remain possible with no user configuration.
    cli.env['FORGE_USER_CONFIG'] = str(cli.cwd / 'absent-config')
    recovered = cli.call('recover', {'paths': [OWNER, REF]})
    assert 'PRIVATE-CANARY-42' not in json.dumps(recovered)


# TC-009 | INFRA: none
@pytest.mark.parametrize('variant', ['ordinary', 'migration', 'compare-replace-barrier'])
def test_concurrent_overwrite(continuity, variant):
    cli = continuity
    seed(cli)
    a = cli.snapshot([OWNER, REF])
    b = cli.snapshot([OWNER, REF])
    changes_a = {OWNER: 'stale prepared A', REF: 'stale prepared A'}
    changes_b = {OWNER: 'new B qualifier', REF: 'new B qualifier'}
    if variant == 'compare-replace-barrier':
        paused = cli.start('publish', cli.request(a, changes_a, 'A'), fault={
            'target': str(cli.project / OWNER), 'when': 'before', 'action': 'pause'})
        paused.reached()
        writer_b = cli.start('publish', cli.request(b, changes_b, 'B'))
        paused.release()
        assert paused.result()[0] == 0
        code, _, _ = writer_b.result()
        assert code == 3, 'B must reject its baseline made stale by A, not overwrite silently'
        cli.publish(cli.snapshot([OWNER, REF]), changes_b, 'B-reconciled')
    else:
        cli.publish(b, changes_b, 'B')
        reply = cli.publish(a, changes_a, f'A-{variant}', expected=3)
        assert reply['status'] == 'not_persisted'
    assert texts(cli.snapshot([OWNER, REF])) == changes_b


# TC-010 + ADV-TC-002 | INFRA: none
@pytest.mark.parametrize('variant', ['multi-file', 'two-single-file-no-pending'])
def test_incoherent_dependent_observation(continuity, variant):
    cli = continuity
    seed(cli)
    first = cli.snapshot([OWNER])
    assert texts(first) == {OWNER: 'old'}
    # Each call is a separate process; writer completing before extension proves
    # snapshot did not retain a lock across reasoning.
    if variant == 'multi-file':
        cli.publish(cli.snapshot([OWNER, REF]), {OWNER: 'new', REF: 'new'}, 'writer')
    else:
        cli.publish(cli.snapshot([OWNER]), {OWNER: 'new'}, 'owner')
        cli.publish(cli.snapshot([REF]), {REF: 'new'}, 'reference')
    extended = cli.snapshot([REF], previous=first)
    assert texts(extended) == {OWNER: 'new', REF: 'new'}
    assert OWNER in extended['invalidated_paths']
    assert extended['snapshot_token'] != first['snapshot_token']
    assert not extended['pending_operations']


# TC-013 + ADV-TC-001 | INFRA: none
@pytest.mark.parametrize('variant', ['before-pending', 'after-pending', 'after-owner',
                                    'before-final-clear', 'concurrent-recovery'])
def test_interrupted_publication_loss(continuity, variant):
    cli = continuity
    seed(cli)
    initial = cli.snapshot([OWNER, REF])
    boundary = PENDING if variant in {'before-pending', 'after-pending', 'before-final-clear'} else OWNER
    phase = 'before' if variant in {'before-pending', 'before-final-clear'} else 'after'
    crashed = cli.start('publish', cli.request(initial, {OWNER: 'new', REF: 'new'}, 'P'), fault={
        'target': str(cli.project / boundary), 'when': phase, 'action': 'crash',
        'syscall': 'unlink' if variant == 'before-final-clear' else 'replace'})
    crashed.reached()
    assert crashed.result()[0] == 91
    if variant == 'before-pending':
        assert (cli.project / OWNER).read_text() == 'old'
        assert (cli.project / REF).read_text() == 'old'
        assert not (cli.project / PENDING).exists()
        return
    assert (cli.project / PENDING).is_file()
    disk_before = {p: (cli.project / p).read_bytes() for p in [OWNER, REF, PENDING]}
    if variant == 'concurrent-recovery':
        # Produce unrelated Q through the same real writer, not a fabricated record.
        q_paths = ['context/q-owner.md', 'context/q-ref.md']
        for path in q_paths:
            (cli.project / path).write_text('Q old')
        q = cli.snapshot(q_paths)
        interrupted_q = cli.start('publish', cli.request(q, dict.fromkeys(q_paths, 'Q new'), 'Q'), fault={
            'target': str(cli.project / q_paths[0]), 'when': 'after', 'action': 'crash'})
        interrupted_q.reached()
        assert interrupted_q.result()[0] == 91
        disk_before[PENDING] = (cli.project / PENDING).read_bytes()
    r1 = cli.call('recover', {'paths': [OWNER, REF]})
    assert {p: (cli.project / p).read_bytes() for p in disk_before} == disk_before, 'recover is inspection, not replay'
    if variant == 'concurrent-recovery':
        # Real caller R1 has returned a snapshot and is paused at semantic reasoning.
        # R2 recovers independently and finishes before R1 attempts publication.
        r2 = cli.call('recover', {'paths': [OWNER, REF]})
        cli.publish(r2['snapshot'], {OWNER: 'new', REF: 'new'}, 'P', recovery='P')
        cli.publish(cli.snapshot([OWNER, REF]), {OWNER: 'later correction', REF: 'later correction'}, 'V2')
        rejected = cli.publish(r1['snapshot'], {OWNER: 'new', REF: 'new'}, 'P', recovery='P', expected=3)
        assert rejected['status'] == 'not_persisted'
        assert texts(cli.snapshot([OWNER, REF])) == {OWNER: 'later correction', REF: 'later correction'}
    else:
        # A later external edit must be observed during recovery, never replayed away.
        (cli.project / OWNER).write_text('later correction')
        fresh = cli.call('recover', {'paths': [OWNER, REF]})
        assert texts(fresh['snapshot'])[OWNER] == 'later correction'
        cli.publish(fresh['snapshot'], {OWNER: 'later correction', REF: 'later correction'}, 'P', recovery='P')
    clean = cli.call('recover', {'paths': [OWNER, REF]})
    after = {p: (cli.project / p).read_bytes() for p in [OWNER, REF]}
    repeated = cli.call('recover', {'paths': [OWNER, REF]})
    assert clean['operations'] == repeated['operations']
    remaining = {op['operation_id'] for op in clean['operations']}
    assert remaining == ({'Q'} if variant == 'concurrent-recovery' else set())
    assert after == {p: (cli.project / p).read_bytes() for p in after}


# Publication interrupted after the pending record | INFRA: none
def test_failure_after_pending_record_reports_interrupted(continuity):
    cli = continuity
    seed(cli)
    decoy = cli.cwd / 'decoy.md'
    decoy.write_text('outside')
    initial = cli.snapshot([OWNER, REF])
    # Pause after the owner replacement: the record exists, the second path is unwritten.
    paused = cli.start('publish', cli.request(initial, {OWNER: 'new', REF: 'new'}, 'P'), fault={
        'target': str(cli.project / OWNER), 'when': 'after', 'action': 'pause'})
    paused.reached()
    assert (cli.project / PENDING).is_file()
    # A nonparticipating writer swaps the second path for a symlink.
    (cli.project / REF).unlink()
    (cli.project / REF).symlink_to(decoy)
    paused.release()
    code, answer, error = paused.result()
    assert code == 4, (answer, error)
    assert answer['reason'] == 'publication_interrupted'
    assert answer['status'] == 'owner_updated_reconciliation_pending'
    assert set(answer['affected_paths']) == {OWNER, REF}
    assert decoy.read_text() == 'outside'
    assert (cli.project / PENDING).is_file()
    # The operator removes the unsafe link; recovery then lists the operation.
    (cli.project / REF).unlink()
    (cli.project / REF).write_text('old')
    recovered = cli.call('recover', {'paths': [OWNER, REF]})
    assert recovered['status'] == 'reconciliation_pending'
    [op] = recovered['operations']
    assert op['operation_id'] == 'P'
    assert (op['completed'], op['remaining']) == ([OWNER], [REF])
    assert op['classifications'] == {OWNER: 'proposed', REF: 'original'}

