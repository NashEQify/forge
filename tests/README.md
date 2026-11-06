# Public checks

These tests run from a fresh checkout of the public repository, with no credentials, private files or network
access. They need Linux or macOS, Python 3, pytest, pytest-xdist and PyYAML:

    python3 -m pip install pytest pytest-xdist pyyaml
    python3 -m pytest tests

`pytest.ini` runs them in parallel; `-n 0` runs them serially.

| Test | What it checks |
|---|---|
| `capabilities/test_continuity.py`, `capabilities/test_continuity_contract.py` | Continuity publication: a stale or foreign write is refused, an interrupted publication is recovered without losing later corrections, and private content stays out of shared output |
| `test_workflow_engine_lifecycle.py` | Workflow lifecycle: an escalation or a failed archive never counts as success, a paused or aborted workflow does not progress, and a finished workflow archives, exports and closes |

## What they establish, and what they do not

- They check Forge's deterministic helpers in temporary directories. They do not run a model or an agent host.
- They come from end-to-end runs in which agent sessions resumed interrupted work and handled failed checks:
  - the workflow-control runs used Codex CLI 0.163.0-alpha.11.1, launched with `gpt-6.1-sol` at medium reasoning
    effort requested; the host did not report the model or effort that actually ran;
  - the resume runs used Claude Code 2.1.302 with `claude-opus-5-5`, in throwaway project and user scopes.
- Each run was a single sample. It shows that the behaviour occurred, not how reliably. These tests pin the helper
  behaviour those sessions depended on; they do not reproduce the sessions.
- To check a session outcome yourself, use your own agent host and report it as described in
  [CONTRIBUTING.md](../CONTRIBUTING.md#reports-and-proposals).
- The maintainers' full regression suite is not part of the public repository.
