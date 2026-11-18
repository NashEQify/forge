"""Additional meaningful boundary checks for protected publication."""

import json
import os
import subprocess
import sys

from conftest import ROOT


def test_personal_content_relative_scope_is_distinct(continuity):
    cli = continuity
    snapshot = cli.snapshot(["preferences.md"], scope="personal")
    assert snapshot["scope"]["content_root"] == str(cli.project / "context/user")
    cli.publish(snapshot, {"preferences.md": "Personal preference."}, scope="personal")
    assert (
        cli.project / "context/user/preferences.md"
    ).read_text() == "Personal preference."
    assert not (cli.project / "preferences.md").exists()
    rejected = cli.call(
        "snapshot", {"paths": ["../session-handover.md"]}, scope="personal", expected=2
    )
    assert rejected["status"] == "not_persisted"
    assert (cli.project / "context/.continuity-project.lock").exists() is False


def test_noop_preserves_content_metadata_and_absence(continuity):
    cli = continuity
    path = cli.project / "context/topic.md"
    path.write_bytes(b"line1\r\nline2\r\n")
    before = path.stat().st_mtime_ns
    snapshot = cli.snapshot(["context/topic.md", "context/missing.md"])
    cli.publish(snapshot, {p: f["text"] for p, f in snapshot["files"].items()})
    assert path.read_bytes() == b"line1\r\nline2\r\n"
    assert path.stat().st_mtime_ns == before
    assert not (cli.project / "context/maintenance-pending.md").exists()
    assert not (cli.project / "context/missing.md").exists()


def test_unwritable_pending_prevents_content_publication(continuity):
    cli = continuity
    for p in ("a.md", "b.md"):
        (cli.project / "context" / p).write_text("old")
    snapshot = cli.snapshot(["context/a.md", "context/b.md"])
    directory = cli.project / "context"
    directory.chmod(0o500)
    try:
        result = cli.publish(
            snapshot, {"context/a.md": "new", "context/b.md": "new"}, expected=2
        )
        assert result["status"] == "not_persisted"
    finally:
        directory.chmod(0o700)
    assert (directory / "a.md").read_text() == (directory / "b.md").read_text() == "old"


def test_locking_unavailable_never_falls_back(continuity):
    cli = continuity
    script = "import sys,runpy;sys.modules['fcntl']=None;sys.path.insert(0,sys.argv[1]);sys.argv=sys.argv[2:];runpy.run_path(sys.argv[0],run_name='__main__')"
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            script,
            str(ROOT / "scripts"),
            str(ROOT / "scripts/continuity.py"),
            "snapshot",
            "--scope",
            "project",
            "--project-root",
            str(cli.project),
        ],
        input=json.dumps({"paths": ["context/topic.md"]}),
        capture_output=True,
        text=True,
        env=cli.env,
    )
    assert result.returncode == 4
    assert json.loads(result.stdout)["reason"] == "locking_unavailable"
    assert not (cli.project / "context/topic.md").exists()


def test_stale_absence_and_dependent_read_reject_publish(continuity):
    cli = continuity
    snap = cli.snapshot(["context/missing.md", "context/owner.md"])
    (cli.project / "context/missing.md").write_text("concurrent creation")
    cli.publish(snap, {"context/owner.md": "based on absence"}, expected=3)
    assert not (cli.project / "context/owner.md").exists()


def test_hardlinked_and_reserved_targets_are_rejected(continuity):
    cli = continuity
    original = cli.project / "context/first.md"
    original.write_text("do not alias")
    os.link(original, cli.project / "context/second.md")
    for path in (
        "context/first.md",
        ".workflow-state/test.json",
        "context/maintenance-pending.md",
    ):
        assert (
            cli.call("snapshot", {"paths": [path]}, expected=2)["status"]
            == "not_persisted"
        )
