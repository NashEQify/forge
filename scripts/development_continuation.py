#!/usr/bin/env python3
"""Explicit development bindings in an existing continuity handoff.

No development import occurs in continuity. State inspection belongs to the
engine; this adapter publishes references only and never advances a workflow.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import subprocess
import sys
import uuid

try:
    from . import continuity
    from .user_scope import resolve_continuity_scope
    from .workflow_engine import export_selected_states, continuation_compatible
    from ._plan_engine.core import KNOWN_TASK_STATUSES, TERMINAL_STATUSES
except ImportError:
    import continuity
    from user_scope import resolve_continuity_scope
    from workflow_engine import export_selected_states, continuation_compatible
    from _plan_engine.core import KNOWN_TASK_STATUSES, TERMINAL_STATUSES

FENCE = re.compile(r"(?m)^```forge-development\n(.*?)\n```[ \t]*(?:\n|$)", re.S)
FRAMEWORK = Path(__file__).resolve().parents[1]


def _envelope(text: str) -> dict:
    matches = list(FENCE.finditer(text))
    if not matches:
        if "```forge-development" in text:
            raise ValueError("malformed development envelope")
        return {"schema_version": 1, "bindings": []}
    if len(matches) != 1:
        raise ValueError("ambiguous development envelopes")
    data = json.loads(matches[0][1])
    if (
        not isinstance(data, dict)
        or data.get("schema_version") != 1
        or not isinstance(data.get("bindings"), list)
    ):
        raise ValueError("unsupported development envelope")
    identities = set()
    for binding in data["bindings"]:
        if not isinstance(binding, dict) or not isinstance(
            binding.get("binding_id"), str
        ):
            raise ValueError("invalid development binding")
        if binding["binding_id"] in identities:
            raise ValueError("duplicate binding identity")
        identities.add(binding["binding_id"])
    return data


def _render(text: str, envelope: dict) -> str:
    block = (
        "```forge-development\n"
        + json.dumps(envelope, ensure_ascii=False, indent=2)
        + "\n```\n"
    )
    if FENCE.search(text):
        return FENCE.sub(lambda _: block, text)
    return (
        text
        + ("\n" if text and not text.endswith("\n") else "")
        + ("\n" if text else "")
        + block
    )


def _validate_binding(binding: dict, root: Path) -> None:
    if binding.get("project_root") != str(root):
        raise ValueError("binding belongs to another project")
    basis = binding.get("selection_basis")
    if (
        not isinstance(basis, dict)
        or basis.get("kind") not in {"intent", "explicit"}
        or not basis.get("evidence")
    ):
        raise ValueError("explicit development selection evidence required")
    if not isinstance(binding.get("workflow_ids"), list) or not isinstance(
        binding.get("state_references", {}), dict
    ):
        raise ValueError("invalid bound workflow selection")
    checks = binding.get("required_checks", [])
    if not isinstance(checks, list):
        raise ValueError("required checks must be a list")
    seen_checks = {}
    for check in checks:
        if not isinstance(check, dict) or check.get("kind") not in {"task", "plan"}:
            raise ValueError("unknown required development check")
        path = check.get("path")
        if (
            not isinstance(path, str)
            or Path(path).is_absolute()
            or ".." in Path(path).parts
        ):
            raise ValueError("invalid required-check path")
        resolved = root / path
        if not resolved.resolve().is_relative_to(root) or resolved.is_symlink():
            raise ValueError("required-check path escapes project")
        if check["kind"] == "plan" and path != "docs/plan.yaml":
            raise ValueError("plan check must use the plan engine's authoritative path")
        if check["kind"] == "task" and not re.fullmatch(
            r"docs/tasks/(?:archive/)?[0-9]+(?:-[^/]+)?\.yaml", path
        ):
            raise ValueError("task check must name an authoritative task file")
        identity = _check_id(check)
        if identity in seen_checks and seen_checks[identity] != check:
            raise ValueError("conflicting expectations require explicit reconciliation")
        seen_checks[identity] = check
    if "closed" in binding:
        receipt = binding["closed"]
        if (
            not isinstance(receipt, dict)
            or not receipt.get("reason")
            or not receipt.get("evidence")
            or not isinstance(receipt.get("verified_states"), list)
            or not isinstance(receipt.get("verified_checks"), list)
            or not (receipt["verified_states"] or receipt["verified_checks"])
        ):
            raise ValueError("invalid verified closure receipt")
        if (
            {state.get("workflow_id") for state in receipt["verified_states"]}
            != set(binding["workflow_ids"])
            or any(
                not state.get("lifecycle", {}).get("terminal")
                for state in receipt["verified_states"]
            )
            or any(
                check.get("status") != "complete"
                or (
                    check.get("check", {}).get("kind") == "task"
                    and check.get("observed_status") not in TERMINAL_STATUSES
                )
                for check in receipt["verified_checks"]
            )
            or {_check_id(check["check"]) for check in receipt["verified_checks"]}
            != {_check_id(check) for check in checks}
        ):
            raise ValueError("closure receipt does not cover terminal obligations")


def _check(root: Path, check: dict) -> dict:
    """Read-only validation. Status changes remain the task-status skill's job."""
    import yaml

    path = root / check["path"]
    if not path.is_file():
        return {"check": check, "status": "blocked", "reason": "required file missing"}
    if check["kind"] == "plan":
        result = subprocess.run(
            [
                sys.executable,
                str(FRAMEWORK / "scripts/plan_engine.py"),
                "--validate",
                "--project-root",
                str(root),
            ],
            cwd=root,
            capture_output=True,
            text=True,
            check=False,
        )
        return {
            "check": check,
            "status": "complete" if result.returncode == 0 else "blocked",
            "reason": "" if result.returncode == 0 else "plan validation failed",
            "exit_code": result.returncode,
        }
    try:
        data = yaml.safe_load(path.read_text())
        if not isinstance(data, dict) or data.get("status") not in KNOWN_TASK_STATUSES:
            raise ValueError("unknown task status")
        if str(data.get("id")) != _check_id(check).split(":", 1)[1]:
            raise ValueError("task identity disagrees with reference")
        expected = check.get("expected_status")
        if expected is not None and data["status"] != expected:
            raise ValueError("task status requires reconciliation")
        return {"check": check, "status": "complete", "observed_status": data["status"]}
    except (OSError, ValueError, yaml.YAMLError) as exc:
        return {"check": check, "status": "blocked", "reason": str(exc)}


def _check_id(check: dict) -> str:
    if check["kind"] == "task":
        return "task:" + str(int(Path(check["path"]).stem.split("-", 1)[0]))
    return "plan:" + check["path"]


def _merge_checks(
    prior: list[dict], changes: list[dict], *, reconcile: bool = False
) -> list[dict]:
    merged = {}
    replacements = {_check_id(check) for check in changes} if reconcile else set()
    for check in prior:
        identity = _check_id(check)
        if (
            identity in merged
            and merged[identity] != check
            and identity not in replacements
        ):
            raise ValueError(
                "conflicting prior checks require explicit identity reconciliation"
            )
        merged[identity] = check
    for check in changes:
        key = _check_id(check)
        if reconcile and key not in merged:
            raise ValueError("reconciliation cannot introduce an unbound obligation")
        if (
            reconcile
            and "expected_status" in merged[key]
            and "expected_status" not in check
        ):
            raise ValueError("reconciliation cannot discard an expected status")
        if not reconcile and key in merged and merged[key] != check:
            raise ValueError(
                "changed check expectation requires explicit reconciliation"
            )
        merged[key] = check
    return list(merged.values())


def _inspect(root: Path, envelope: dict) -> dict:
    bindings = envelope["bindings"]
    ids: list[str] = []
    refs: dict[str, str] = {}
    checks: dict[str, dict] = {}
    for binding in bindings:
        _validate_binding(binding, root)
        if binding.get("closed"):
            continue
        for wid in binding["workflow_ids"]:
            if wid not in ids:
                ids.append(wid)
            reference = binding.get("state_references", {}).get(wid)
            if reference:
                if wid in refs and refs[wid] != reference:
                    raise ValueError("conflicting authoritative state references")
                refs[wid] = reference
        for check in binding.get("required_checks", []):
            checks[json.dumps(check, sort_keys=True)] = check
    exact = export_selected_states(root, ids, refs)
    observed = {state["workflow_id"]: state for state in exact["states"]}
    check_results = {key: _check(root, check) for key, check in checks.items()}
    updated, blockers = [], []
    for binding in bindings:
        if binding.get("closed"):
            updated.append(
                dict(binding, status="complete", unfinished=False, blockers=[])
            )
            continue
        problems = [
            p for p in exact["blockers"] if p["workflow_id"] in binding["workflow_ids"]
        ]
        states = [observed[wid] for wid in binding["workflow_ids"] if wid in observed]
        for state in states:
            prior = binding.get("observed_states", {}).get(state["workflow_id"])
            if prior:
                if state["revision"] < prior["revision"]:
                    problems.append(
                        {
                            "workflow_id": state["workflow_id"],
                            "reason": "state revision regressed",
                        }
                    )
                if not continuation_compatible(
                    state["state"]["workflow"],
                    prior.get("definition_fingerprint"),
                    state["definition_fingerprint"],
                ):
                    problems.append(
                        {
                            "workflow_id": state["workflow_id"],
                            "reason": "workflow interpretation changed",
                        }
                    )
                if (
                    state["revision"] == prior["revision"]
                    and state["sha256"] != prior["sha256"]
                ):
                    problems.append(
                        {
                            "workflow_id": state["workflow_id"],
                            "reason": "state changed without revision",
                        }
                    )
        for check in binding.get("required_checks", []):
            result = check_results[json.dumps(check, sort_keys=True)]
            if result["status"] != "complete":
                problems.append(result)
        binding = dict(binding)
        # A failed observation cannot overwrite the last accepted compatibility baseline.
        if not problems:
            binding["state_references"] = {
                state["workflow_id"]: state["state_file"] for state in states
            }
            binding["observed_states"] = {
                state["workflow_id"]: {
                    key: state[key]
                    for key in ("revision", "sha256", "definition_fingerprint")
                }
                for state in states
            }
        binding["status"] = "blocked" if problems else "complete"
        binding["blockers"] = problems
        binding["unfinished"] = (
            bool(problems)
            or any(not state["lifecycle"]["terminal"] for state in states)
            or any(
                result.get("observed_status") not in TERMINAL_STATUSES
                for result in (
                    check_results[json.dumps(c, sort_keys=True)]
                    for c in binding.get("required_checks", [])
                    if c["kind"] == "task"
                )
            )
            or not binding["workflow_ids"]
        )
        blockers.extend(
            {"binding_id": binding["binding_id"], **problem} for problem in problems
        )
        updated.append(binding)
    status = (
        "partial"
        if blockers and any(b["status"] == "complete" for b in updated)
        else "blocked"
        if blockers
        else "complete"
    )
    return {
        "schema_version": 1,
        "status": status,
        "bindings": updated,
        "blockers": blockers,
        "states": exact["states"],
        "checks": list(check_results.values()),
    }


def contribute(command: str, root: Path, handoff: str, request: dict) -> dict:
    root = root.resolve(strict=True)
    scope = resolve_continuity_scope("project", root)
    snap = continuity.snapshot(scope, {"paths": [handoff]})
    if any(handoff in op["affected_paths"] for op in snap["pending_operations"]):
        raise continuity.ContinuityError("handoff_reconciliation_pending", 4)
    text = snap["files"][handoff]["text"] or ""
    envelope = _envelope(text)
    if command == "bind":
        identifier = request.get("binding_id") or str(uuid.uuid4())
        if not isinstance(identifier, str) or not re.fullmatch(
            r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}", identifier
        ):
            raise ValueError("invalid binding identity")
        existing = next(
            (b for b in envelope["bindings"] if b["binding_id"] == identifier), None
        )
        binding = {
            "binding_id": identifier,
            "project_root": str(root),
            "selection_basis": request.get("selection_basis"),
            "workflow_ids": request.get("workflow_ids", []),
            "state_references": request.get("state_references", {}),
            "required_checks": request.get("required_checks", []),
        }
        if existing:
            _validate_binding(existing, root)
            binding["workflow_ids"] = list(
                dict.fromkeys(existing["workflow_ids"] + binding["workflow_ids"])
            )
            binding["state_references"] = {
                **existing.get("state_references", {}),
                **binding["state_references"],
            }
            binding["observed_states"] = existing.get("observed_states", {})
            binding["reconciliations"] = existing.get("reconciliations", [])
            if existing.get("closed"):
                raise ValueError(
                    "closed binding cannot reopen; select a new binding identity"
                )
            binding["required_checks"] = _merge_checks(
                existing.get("required_checks", []), binding["required_checks"]
            )
            envelope["bindings"] = [
                binding if b is existing else b for b in envelope["bindings"]
            ]
        else:
            envelope["bindings"].append(binding)
    elif command in {"reconcile", "close"}:
        if not request.get("reason") or not request.get("evidence"):
            raise ValueError("explicit lifecycle reason and evidence required")
        target = next(
            (
                b
                for b in envelope["bindings"]
                if b["binding_id"] == request.get("binding_id")
            ),
            None,
        )
        if target is None or target.get("closed"):
            raise ValueError("open binding identity required")
        if command == "reconcile":
            before_checks = target.get("required_checks", [])
            target["required_checks"] = _merge_checks(
                before_checks, request.get("required_checks", []), reconcile=True
            )
            target.setdefault("reconciliations", []).append(
                {
                    "reason": request["reason"],
                    "evidence": request["evidence"],
                    "prior_checks": before_checks,
                    "reconciled_checks": target["required_checks"],
                }
            )
    elif command not in {"export", "restore"}:
        raise ValueError("unknown contribution command")
    # No bindings means no development selected, even with task/plan/state files.
    result = _inspect(root, envelope)
    if command in {"reconcile", "close"}:
        selected = next(
            b for b in result["bindings"] if b["binding_id"] == request["binding_id"]
        )
        if selected["blockers"]:
            return result
        if command == "close":
            selected_states = [
                state
                for state in result["states"]
                if state["workflow_id"] in selected["workflow_ids"]
            ]
            selected_checks = [
                _check(root, check) for check in selected.get("required_checks", [])
            ]
            tasks = [
                check for check in selected_checks if check["check"]["kind"] == "task"
            ]
            verified = (
                bool(selected_states or tasks)
                and all(state["lifecycle"]["terminal"] for state in selected_states)
                and all(
                    check.get("observed_status") in TERMINAL_STATUSES for check in tasks
                )
            )
            if not verified:
                problem = {
                    "binding_id": selected["binding_id"],
                    "reason": "selected obligations are not terminal",
                }
                selected.update(status="blocked", unfinished=True, blockers=[problem])
                result["blockers"].append(problem)
                result["status"] = "blocked"
                return result
            selected.update(
                closed={
                    "reason": request["reason"],
                    "evidence": request["evidence"],
                    "verified_states": [
                        {k: v for k, v in state.items() if k != "state"}
                        for state in selected_states
                    ],
                    "verified_checks": selected_checks,
                },
                unfinished=False,
            )
    if command != "restore" and envelope["bindings"]:
        replacement = _render(
            text, {"schema_version": 1, "bindings": result["bindings"]}
        )
        continuity.publish(
            scope,
            {
                "snapshot_token": snap["snapshot_token"],
                "operation_id": "development-" + uuid.uuid4().hex,
                "intended_change": "Persist explicit development continuation references",
                "source_references": ["development adapter"],
                "affected_paths": [handoff],
                "replacements": {handoff: replacement},
            },
        )
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "command", choices=("bind", "export", "restore", "reconcile", "close")
    )
    parser.add_argument("--project-root", type=Path, required=True)
    parser.add_argument("--handoff", required=True)
    args = parser.parse_args(argv)
    try:
        request = json.load(sys.stdin)
        if not isinstance(request, dict) or request.get("schema_version", 1) != 1:
            raise ValueError("unsupported request")
        result = contribute(args.command, args.project_root, args.handoff, request)
        print(json.dumps(result, ensure_ascii=False))
        return 4 if result["blockers"] else 0
    except (ValueError, OSError, TypeError, KeyError) as exc:
        reason = exc.reason if isinstance(exc, continuity.ContinuityError) else str(exc)
        print(
            json.dumps(
                {
                    "schema_version": 1,
                    "status": "blocked",
                    "blockers": [{"reason": reason}],
                }
            )
        )
        return exc.code if isinstance(exc, continuity.ContinuityError) else 2


if __name__ == "__main__":
    sys.exit(main())
