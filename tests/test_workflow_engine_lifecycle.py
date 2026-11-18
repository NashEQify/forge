"""Local closure witnesses through revisioned persistence and explicit consumers."""

from __future__ import annotations

import copy
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from scripts import workflow_engine as we  # noqa: E402
from scripts.lib import yaml_loader  # noqa: E402

# Only workflow discovery is redirected; real command parsing, checks, state
# writes, exact export and continuation publication execute unchanged.
RUNNER = """
import os, runpy, sys
from pathlib import Path
from scripts.lib import yaml_loader
yaml_loader.WORKFLOW_SEARCH_PATHS = [Path(sys.argv.pop(1))]
script = sys.argv.pop(1)
sys.argv[0] = script
sys.path.insert(0, str(Path(script).parent))
if os.environ.get('LIFECYCLE_FAIL_ARCHIVE'):
    real_replace = os.replace
    def replace(src, dst):
        if Path(dst).parent.name == 'archive':
            raise PermissionError('synthetic archive replacement denied')
        return real_replace(src, dst)
    os.replace = replace
if os.environ.get('LIFECYCLE_FORBID_CHECKS'):
    def profile(frame, event, arg):
        if event == 'call' and frame.f_code.co_name in {'check_completion', '_check_completion'}:
            raise RuntimeError('Reconciliation replayed a completion check')
    sys.setprofile(profile)
runpy.run_path(script, run_name='__main__')
"""


class LocalRun:
    def __init__(self, root, definitions, env):
        self.root, self.definitions, self.env = root, definitions, env
        self.trace = root / "commands.jsonl"

    def command(self, script, *args, request=None):
        argv = [
            sys.executable,
            "-c",
            RUNNER,
            str(self.definitions),
            str(ROOT / "scripts" / script),
            "--project-root",
            str(self.root),
            *args,
        ]
        result = subprocess.run(
            argv,
            cwd=ROOT,
            env=self.env,
            input=json.dumps(request or {}),
            text=True,
            capture_output=True,
            timeout=15,
        )
        with self.trace.open("a") as stream:
            stream.write(
                json.dumps(
                    {
                        "argv": argv,
                        "request": request,
                        "code": result.returncode,
                        "stdout": result.stdout,
                        "stderr": result.stderr,
                    }
                )
                + "\n"
            )
        return result

    def engine(self, *args):
        return self.command("workflow_engine.py", *args)

    def adapter(self, command, request=None):
        result = self.command(
            "development_continuation.py",
            command,
            "--handoff",
            "context/session-handover.md",
            request=request,
        )
        return result, json.loads(result.stdout)

    def define(self, **fields):
        step = {
            "id": "publication",
            "name": "Publication",
            "category": "content",
            "instruction": "Publish only when selected",
            "required": False,
            "completion": {"type": "manual"},
            **fields,
        }
        definition = {"name": "local-close", "steps": [step]}
        folder = self.definitions / "local-close"
        folder.mkdir(exist_ok=True)
        (folder / "workflow.yaml").write_text(yaml.safe_dump(definition))
        self.definition = definition
        return definition

    def create(self, **fields):
        self.define(**fields)
        self.state = we.create_state("local-close", self.definition)
        self.wid = self.state["workflow_id"]
        return self.state

    @property
    def active(self):
        return self.root / ".workflow-state" / f"{self.wid}.json"

    @property
    def archived(self):
        return self.root / ".workflow-state/archive" / f"{self.wid}.json"

    def export(self):
        result = we.export_selected_states(self.root, [self.wid])
        with (self.root / "exact-exports.jsonl").open("a") as stream:
            stream.write(json.dumps(result) + "\n")
        assert not result["blockers"], result
        return result["states"][0]

    def bind(self):
        result, payload = self.adapter(
            "bind",
            {
                "binding_id": "selected",
                "selection_basis": {
                    "kind": "explicit",
                    "evidence": "Synthetic user selection",
                },
                "workflow_ids": [self.wid],
                "required_checks": [],
            },
        )
        assert result.returncode == 0, payload

    def close(self):
        return self.adapter(
            "close",
            {
                "binding_id": "selected",
                "reason": "Local work delivered",
                "evidence": "Exact selected engine lifecycle",
            },
        )


@pytest.fixture
def local(tmp_path, monkeypatch):
    root, definitions = tmp_path / "project", tmp_path / "definitions"
    root.mkdir()
    definitions.mkdir()
    (root / "context").mkdir()
    monkeypatch.setattr(we, "PROJECT_ROOT", root)
    monkeypatch.setattr(we, "REPO_ROOT", root)
    monkeypatch.setattr(we, "STATE_DIR", root / ".workflow-state")
    monkeypatch.setattr(we, "ARCHIVE_DIR", root / ".workflow-state/archive")
    monkeypatch.setattr(yaml_loader, "WORKFLOW_SEARCH_PATHS", [definitions])
    config = tmp_path / "user.json"
    config.write_text(
        json.dumps({"version": 1, "user_repo": str(root), "profile": "daily"})
    )
    env = dict(os.environ, FORGE_USER_CONFIG=str(config), PYTHONDONTWRITEBYTECODE="1")
    env.pop("BUDDY_PROJECT_ROOT", None)
    return LocalRun(root, definitions, env)


def assert_archived(local, status):
    exported = local.export()
    assert exported["state"]["steps"]["publication"]["status"] == status
    assert exported["lifecycle"] == {"status": "completed", "terminal": True}, exported
    assert local.archived.is_file() and not local.active.exists()
    assert exported["state"]["current_step"] is None


def test_final_optional_skip_cli_archives_exports_and_closes(local):
    local.define()
    result = local.engine("--start", "local-close")
    assert result.returncode == 0, result.stderr
    local.active_dir = local.root / ".workflow-state"
    local.state = json.loads(next(local.active_dir.glob("*.json")).read_text())
    local.wid = local.state["workflow_id"]
    local.bind()
    result = local.engine(
        "--skip",
        "publication",
        "--reason",
        "Publication not selected",
        "--id",
        local.wid,
    )
    exported = local.export()
    closed, payload = local.close()
    assert result.returncode == 0, result.stderr
    assert exported["state"]["steps"]["publication"]["status"] == "skipped"
    assert exported["lifecycle"]["terminal"] and closed.returncode == 0, (
        exported,
        payload,
    )
    assert_archived(local, "skipped")
    before = local.archived.read_bytes()
    assert local.engine("--next", "--id", local.wid).returncode == 0
    assert local.archived.read_bytes() == before


@pytest.mark.parametrize(
    "marker", [False, True], ids=["all-terminal", "retained-completion"]
)
def test_explicit_next_reconciles_without_replaying_evidence(local, marker):
    state = local.create()
    state["steps"]["publication"].update(
        status="skipped",
        evidence="Retained skip evidence",
        completed_at="2026-01-01T00:00:00+00:00",
    )
    if marker:
        state["completed"] = "2026-01-01T01:00:00+00:00"
    we.save_state(state)
    steps = copy.deepcopy(state["steps"])
    local.env["LIFECYCLE_FORBID_CHECKS"] = "1"
    result = local.engine("--next", "--id", local.wid)
    assert result.returncode == 0, result.stderr
    assert_archived(local, "skipped")
    archived = json.loads(local.archived.read_text())
    assert archived["steps"] == steps
    if marker:
        assert archived["completed"] == state["completed"]
    before = local.archived.read_bytes()
    assert local.engine("--next", "--id", local.wid).returncode == 0
    assert local.archived.read_bytes() == before


# warn_skipped and skipped close through the same terminal-status set; skipped runs via "guard".
@pytest.mark.parametrize("path", ["guard", "deterministic", "recovery", "warn"])
def test_final_transition_uses_local_closure(local, path):
    fields = {}
    if path == "guard":
        fields["guard"] = {"type": "file_exists", "path": "not-selected"}
    elif path in {"deterministic", "recovery"}:
        fields["completion"] = {
            "type": "file_content_check",
            "path": "ready",
            "pattern": "ready",
            "condition": "has_match",
        }
        if path == "deterministic":
            fields["category"] = "deterministic"
        (local.root / "ready").write_text("ready")
    else:
        fields.update(
            on_fail=path,
            completion={
                "type": "file_content_check",
                "path": "missing",
                "pattern": "ready",
                "condition": "has_match",
            },
        )
    state = local.create(**fields)
    if path == "deterministic":
        state["steps"]["publication"]["status"] = "pending"
        we.save_state(state)
    command = (
        ["--next"]
        if path in {"guard", "deterministic"}
        else ["--recover"]
        if path == "recovery"
        else ["--complete", "publication"]
    )
    result = local.engine(*command, "--id", local.wid)
    assert result.returncode == 0, result.stderr
    expected = (
        "warn_skipped"
        if path == "warn"
        else "skipped"
        if path in {"guard", "skip"}
        else "complete"
    )
    assert_archived(local, expected)


@pytest.mark.parametrize("policy", ["block", "escalate"])
def test_failed_check_and_escalation_remain_nonterminal(local, policy):
    local.create(
        on_fail=policy,
        completion={
            "type": "file_content_check",
            "path": "missing",
            "pattern": "ready",
            "condition": "has_match",
        },
    )
    result = local.engine("--complete", "publication", "--id", local.wid)
    assert result.returncode == (1 if policy == "block" else 0), result.stderr
    exported = local.export()
    assert not exported["lifecycle"]["terminal"]
    assert exported["state"]["steps"]["publication"]["status"] == (
        "in_progress" if policy == "block" else "escalated"
    )
    assert not local.archived.exists()


# Every terminal status takes the same refusal; escalated is the one a skip would hide.
@pytest.mark.parametrize("terminal", ["escalated"])
def test_skip_preserves_terminal_transition_evidence(local, terminal):
    state = local.create()
    state["steps"]["publication"].update(
        status=terminal, evidence="Keep original evidence", completed_at="original"
    )
    we.save_state(state)
    before = local.active.read_bytes()
    result = local.engine(
        "--skip", "publication", "--reason", "Do not rewrite", "--id", local.wid
    )
    assert result.returncode != 0, result.stdout
    assert local.active.read_bytes() == before


# Each consumer runs paused; aborted takes the same refusal and runs once.
@pytest.mark.parametrize("isolation, operation", [
    *(("paused", op) for op in ("complete", "skip", "next", "recover", "retry")),
    ("aborted", "complete"),
])
def test_pause_and_abort_consumers_do_not_progress(local, isolation, operation):
    state = local.create(
        completion={
            "type": "file_content_check",
            "path": "ready",
            "pattern": "ready",
            "condition": "has_match",
        }
    )
    (local.root / "ready").write_text("ready")
    state[isolation] = True if isolation == "paused" else "2026-01-01T00:00:00+00:00"
    if operation == "next":
        state["steps"]["publication"]["status"] = "pending"
        state["current_step"] = None
    we.save_state(state)
    assert local.export()["lifecycle"] == {
        "status": isolation,
        "terminal": isolation == "aborted",
    }
    before = local.active.read_bytes()
    args = ["--" + operation]
    if operation in {"complete", "skip", "retry"}:
        args += ["publication"]
    if operation in {"skip", "retry"}:
        args += ["--reason", "Explicit test request"]
    result = local.engine(*args, "--id", local.wid)
    assert local.active.exists() and local.active.read_bytes() == before, (
        operation,
        isolation,
        result.stdout,
        result.stderr,
    )
    assert not local.archived.exists()
    if operation in {"complete", "skip", "retry"}:
        assert result.returncode != 0
    assert local.export()["lifecycle"] == {
        "status": isolation,
        "terminal": isolation == "aborted",
    }


def test_escalation_cannot_be_archived_as_success_by_later_completion(local):
    local.define()
    definition = copy.deepcopy(local.definition)
    definition["steps"].insert(0, {**definition["steps"][0], "id": "attention"})
    (local.definitions / "local-close/workflow.yaml").write_text(
        yaml.safe_dump(definition)
    )
    state = we.create_state("local-close", definition)
    local.wid = state["workflow_id"]
    state["steps"]["attention"].update(
        status="escalated", evidence="User action required"
    )
    state["steps"]["publication"]["status"] = "in_progress"
    state["current_step"] = "publication"
    we.save_state(state)
    result = local.engine("--complete", "publication", "--id", local.wid)
    assert result.returncode == 0, result.stderr
    assert not local.export()["lifecycle"]["terminal"]
    assert local.active.exists()


def failed_archive(local, *, create=True):
    if create:
        local.create()
    local.env["LIFECYCLE_FAIL_ARCHIVE"] = "1"
    try:
        result = local.engine(
            "--complete",
            "publication",
            "--id",
            local.wid,
            "--evidence",
            "Delivered once",
        )
    finally:
        local.env.pop("LIFECYCLE_FAIL_ARCHIVE")
    assert result.returncode == 1 and "archive replacement denied" in result.stderr
    assert local.active.exists() and not local.archived.exists()
    retained = json.loads(local.active.read_text())
    assert (
        retained["completed"]
        and retained["steps"]["publication"]["evidence"] == "Delivered once"
    )
    return retained


def test_archive_failure_export_and_close_remain_nonterminal(local):
    local.create()
    local.bind()
    failed_archive(local, create=False)
    exported = local.export()
    result, payload = local.close()
    assert not exported["lifecycle"]["terminal"] and result.returncode != 0, (
        exported,
        payload,
    )


def test_corrected_archive_failure_explicit_next_preserves_timestamp(local):
    retained = failed_archive(local)
    result = local.engine("--next", "--id", local.wid)
    assert result.returncode == 0, result.stderr
    assert_archived(local, "complete")
    archived = json.loads(local.archived.read_text())
    assert archived["steps"] == retained["steps"]
    assert archived["completed"] == retained["completed"]


def test_new_child_skip_finalization_is_explicitly_refused(local):
    state = local.create()
    parent = we.create_state(
        "parent",
        {
            "name": "parent",
            "steps": [
                {
                    "id": "child",
                    "name": "Child",
                    "category": "content",
                    "completion": {"type": "manual"},
                }
            ],
        },
    )
    parent_path = we._state_path(parent["workflow_id"])
    before = parent_path.read_bytes()
    state["parent_workflow_id"] = parent["workflow_id"]
    we.save_state(state)
    result = local.engine(
        "--skip", "publication", "--reason", "No publication", "--id", local.wid
    )
    assert parent_path.read_bytes() == before
    assert not local.archived.exists()
    assert result.returncode != 0 and "parent" in result.stderr.lower(), (
        result.stdout,
        result.stderr,
    )


def test_selected_next_preserves_unrelated_sibling_control(local):
    state = local.create()
    sibling = we.create_state("sibling", local.definition)
    sibling_path = we._state_path(sibling["workflow_id"])
    before = sibling_path.read_bytes()
    state["steps"]["publication"]["status"] = "skipped"
    we.save_state(state)
    assert local.engine("--next", "--id", local.wid).returncode == 0
    assert sibling_path.read_bytes() == before


def test_retry_invalidates_stale_completion_eligibility(local):
    state = local.create()
    state["steps"]["publication"]["status"] = "complete"
    state["completed"] = "2026-01-01T00:00:00+00:00"
    we.save_state(state)
    result = local.engine(
        "--retry", "publication", "--reason", "Reopen explicitly", "--id", local.wid
    )
    assert result.returncode == 0, result.stderr
    reopened = json.loads(local.active.read_text())
    assert reopened["steps"]["publication"]["status"] == "in_progress"
    assert not reopened.get("completed"), reopened
    assert not local.export()["lifecycle"]["terminal"]


def test_contending_lock_cannot_report_premature_success_control(local):
    local.create()
    argv = [
        sys.executable,
        "-c",
        RUNNER,
        str(local.definitions),
        str(ROOT / "scripts/workflow_engine.py"),
        "--project-root",
        str(local.root),
        "--complete",
        "publication",
        "--id",
        local.wid,
    ]
    before = local.active.read_bytes()
    child = None
    try:
        with we._state_lock():
            child = subprocess.Popen(
                argv,
                cwd=ROOT,
                env=local.env,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            with pytest.raises(subprocess.TimeoutExpired):
                child.communicate(timeout=0.25)
            assert local.active.read_bytes() == before
        out, err = child.communicate(timeout=15)
        assert child.returncode == 0, (out, err)
        assert_archived(local, "complete")
    finally:
        if child is not None and child.poll() is None:
            child.kill()
            child.communicate()


# The successful guard skip is covered by test_valid_negative_guards_still_skip.
@pytest.mark.parametrize("deny_save", [True], ids=["save-failure"])
def test_guard_skip_save_result_matches_durable_progress(local, deny_save):
    """Supported skip/retry positioning must not acknowledge an unsaved guard skip."""
    local.define()
    definition = {
        "name": "local-close",
        "steps": [
            {
                "id": "guarded",
                "name": "Guarded",
                "category": "content",
                "required": False,
                "instruction": "Guarded work",
                "guard": {"type": "file_exists", "path": "enabled"},
                "completion": {"type": "manual"},
            },
            {
                "id": "work",
                "name": "Work",
                "category": "content",
                "required": False,
                "instruction": "Later work",
                "completion": {"type": "manual"},
            },
        ],
    }
    (local.definitions / "local-close/workflow.yaml").write_text(
        yaml.safe_dump(definition)
    )
    enabled = local.root / "enabled"
    enabled.write_text("Selected guarded work")
    started = local.engine("--start", "local-close")
    assert started.returncode == 0, started.stderr
    state_path = next((local.root / ".workflow-state").glob("*.json"))
    local.wid = json.loads(state_path.read_text())["workflow_id"]
    assert (
        local.engine(
            "--skip", "work", "--reason", "Optional later work", "--id", local.wid
        ).returncode
        == 0
    )
    assert (
        local.engine(
            "--retry", "work", "--reason", "Reopen later work", "--id", local.wid
        ).returncode
        == 0
    )
    enabled.unlink()
    before = local.active.read_bytes()
    positioned = json.loads(before)
    assert positioned["current_step"] == "work"
    assert all(step["status"] == "in_progress" for step in positioned["steps"].values())
    (local.root / "durable-before.json").write_bytes(before)

    # Inject only at the real state replacement; discovery and command handling
    # remain identical to the other subprocess CLI witnesses.
    injection = """
if os.environ.get('LIFECYCLE_DENY_GUARD_SAVE'):
    real_replace = os.replace
    def deny_guard_save(src, dst):
        if str(Path(dst)) == os.environ['LIFECYCLE_DENY_GUARD_SAVE']:
            raise PermissionError('synthetic guard-skip write denied')
        return real_replace(src, dst)
    os.replace = deny_guard_save
runpy.run_path(script, run_name='__main__')
"""
    runner = RUNNER.replace("runpy.run_path(script, run_name='__main__')", injection)
    argv = [
        sys.executable,
        "-c",
        runner,
        str(local.definitions),
        str(ROOT / "scripts/workflow_engine.py"),
        "--project-root",
        str(local.root),
        "--next",
        "--id",
        local.wid,
    ]
    env = dict(local.env)
    if deny_save:
        env["LIFECYCLE_DENY_GUARD_SAVE"] = str(local.active)
    result = subprocess.run(
        argv, cwd=ROOT, env=env, text=True, capture_output=True, timeout=15
    )
    with local.trace.open("a") as stream:
        stream.write(
            json.dumps(
                {
                    "argv": argv,
                    "fault": deny_save,
                    "code": result.returncode,
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                }
            )
            + "\n"
        )
    after = local.active.read_bytes()
    (local.root / "durable-after.json").write_bytes(after)
    if deny_save:
        assert after == before
        assert result.returncode == 1, (result.stdout, result.stderr)
        assert "synthetic guard-skip write denied" in result.stderr
        assert "PROGRESS:" not in result.stdout
    else:
        assert result.returncode == 0, result.stderr
        persisted = json.loads(after)
        assert persisted["steps"]["guarded"]["status"] == "skipped"
        assert persisted["steps"]["work"]["status"] == "in_progress"
        assert "PROGRESS: 1/2 done" in result.stdout
