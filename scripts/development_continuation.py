#!/usr/bin/env python3
"""Explicit development bindings in an existing continuity handoff.

No development import occurs in continuity. State inspection belongs to the
engine; this adapter publishes references only and never advances a workflow.
"""

from __future__ import annotations

import argparse
from collections.abc import Hashable
import copy
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import uuid
from typing import Any

try:
    from . import continuity
    from .user_scope import resolve_continuity_scope
    from .workflow_engine import export_selected_states, continuation_compatible, _utcnow
    from ._plan_engine.core import KNOWN_TASK_STATUSES, TERMINAL_STATUSES
except ImportError:
    import continuity
    from user_scope import resolve_continuity_scope
    # Same standalone-script fallback as above; mypy resolves the package branch.
    from workflow_engine import (  # type: ignore[import-not-found,no-redef]
        export_selected_states, continuation_compatible, _utcnow,
    )
    from _plan_engine.core import KNOWN_TASK_STATUSES, TERMINAL_STATUSES

FENCE = re.compile(r"(?m)^```forge-development\n(.*?)\n```[ \t]*(?:\n|$)", re.S)
# A line opening a forge-development fence in any spelling, outside FENCE:
# after any non-word lead-in (BOM, NBSP, quote or list marker, list number).
OPENER = re.compile(
    r"(?m)^[^\w\n`~]*(?:\d{1,9}[.)])?[^\w\n`~]*(?:`{3,}|~{3,})[ \t]*forge-development"
)
FRAMEWORK = Path(__file__).resolve().parents[1]


def _envelope(text: str) -> dict:
    matches = list(FENCE.finditer(text))
    if not matches:
        if OPENER.search(text):
            raise ValueError("malformed development envelope")
        return {"schema_version": 1, "bindings": []}
    if OPENER.search(FENCE.sub("", text)):
        raise ValueError("malformed development envelope")
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
    # Older envelopes may carry check_observations and observation references; they pass through unread.
    return data


def _render(text: str, envelope: dict) -> str:
    match = FENCE.search(text)
    if not envelope["bindings"]:
        # The last binding left: the owned region goes with it. As the file's tail it
        # also takes the one separator newline added on creation; nothing else.
        if not match:
            return text
        before, after = text[: match.start()], text[match.end() :]
        if not after and before.endswith("\n"):
            before = before[:-1]
        return before + after
    block = (
        "```forge-development\n"
        + json.dumps(envelope, ensure_ascii=False, indent=2)
        + "\n```\n"
    )
    if match:
        return FENCE.sub(lambda _: block, text)
    # Exactly one separator newline, so removal takes back exactly what was added.
    return text + ("\n" if text else "") + block


def _valid_selection(workflow_ids: object, references: object) -> bool:
    """Workflow IDs are a list of hashable values; state references are a mapping."""
    return (
        isinstance(workflow_ids, list)
        and all(isinstance(wid, Hashable) for wid in workflow_ids)
        and isinstance(references, dict)
    )


def _validate_binding(binding: dict, root: Path) -> None:
    # Tuples, not sets, for the membership tests: a JSON list or object there is bad
    # input to refuse, not an unhashable-type crash.
    if binding.get("project_root") != str(root):
        raise ValueError("binding belongs to another project")
    basis = binding.get("selection_basis")
    if (
        not isinstance(basis, dict)
        or basis.get("kind") not in ("intent", "explicit")
        or not basis.get("evidence")
    ):
        raise ValueError("explicit development selection evidence required")
    if not _valid_selection(binding.get("workflow_ids"), binding.get("state_references", {})):
        raise ValueError("invalid bound workflow selection")
    observed = binding.get("observed_states", {})
    if not isinstance(observed, dict) or not all(
        isinstance(record, dict)
        and isinstance(record.get("revision"), int)
        and isinstance(record.get("sha256"), str)
        for record in observed.values()
    ):
        raise ValueError("invalid observed development state")
    checks = binding.get("required_checks", [])
    if not isinstance(checks, list):
        raise ValueError("required checks must be a list")
    seen_checks = {}
    for check in checks:
        if not isinstance(check, dict) or check.get("kind") not in ("task", "plan"):
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
            or not all(
                isinstance(state, dict) and isinstance(state.get("workflow_id"), Hashable)
                for state in receipt["verified_states"]
            )
            or not all(
                isinstance(check, dict)
                and isinstance(check.get("check"), dict)
                and isinstance(check.get("observed_status", ""), str)
                for check in receipt["verified_checks"]
            )
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
    """Evaluate once; the result carries its receipt entry: what was read and decided."""
    import yaml
    path = root / check['path']
    item: dict[str, Any] = {'kind': 'file', 'path': check['path'], 'exists': path.is_file()}
    entry: dict[str, Any] = {'check': _check_id(check), 'type': check['kind'], 'result': 'failed',
                             'producer': 'checker', 'input': [item]}
    result: dict[str, Any] = {'check': check, 'status': 'blocked', 'reason': 'required file missing'}
    detail = None
    if path.is_file():
        try:
            if check['kind'] == 'plan':
                cmd = [sys.executable, str(FRAMEWORK / 'scripts/plan_engine.py'), '--validate', '--project-root', str(root)]
                # The validator reads more than docs/plan.yaml, so the recorded input is partial.
                entry.update(partial=True, command=cmd)
                ran = subprocess.run(cmd, cwd=root, capture_output=True, text=True, check=False)
                entry['exit_code'] = ran.returncode
                passed = ran.returncode == 0
                result.update(status='complete' if passed else 'blocked', reason='' if passed else 'plan validation failed', exit_code=ran.returncode)
                entry['result'] = 'passed' if passed else 'failed'
                output = (ran.stdout + ran.stderr).strip()[:300]
                if not passed and output:
                    detail = 'plan validation failed: ' + output
            else:
                raw = path.read_bytes()
                del item['exists']
                item['identity'] = {'sha256': hashlib.sha256(raw).hexdigest()}
                data = yaml.safe_load(raw.decode('utf-8'))
                if (not isinstance(data, dict) or not isinstance(data.get('status'), str)
                        or data['status'] not in KNOWN_TASK_STATUSES):
                    raise ValueError('unknown task status')
                if str(data.get('id')) != _check_id(check).split(':', 1)[1]:
                    raise ValueError('task identity disagrees with reference')
                result['observed_status'] = data['status']
                expected = check.get('expected_status')
                if expected is not None and data['status'] != expected:
                    result['reason'] = 'task status requires reconciliation'
                else:
                    result.update(status='complete', reason='')
                    entry['result'] = 'passed'
        except (OSError, ValueError, yaml.YAMLError) as exc:
            result['reason'] = str(exc)
            entry['result'] = 'unknown'
    entry['detail'] = detail or result['reason'] or 'passed'
    result['receipt'] = entry
    return result


def _check_id(check: dict) -> str:
    # A request or stored check reaches this before full validation: a malformed one
    # raises the contract's ValueError, in _validate_binding's order (kind, then path).
    if not isinstance(check, dict) or "kind" not in check:
        raise ValueError("unknown required development check")
    if not isinstance(check.get("path"), str):
        if check["kind"] in ("task", "plan"):
            raise ValueError("invalid required-check path")
        raise ValueError("unknown required development check")
    if check["kind"] == "task":
        return "task:" + str(int(Path(check["path"]).stem.split("-", 1)[0]))
    return "plan:" + check["path"]


def _merge_checks(
    prior: list[dict], changes: list[dict], *, reconcile: bool = False
) -> list[dict]:
    if not isinstance(prior, list) or not isinstance(changes, list):
        raise ValueError("required checks must be a list")
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


def _inspect(root: Path, envelope: dict, operation: str) -> dict:
    bindings = envelope["bindings"]
    at = _utcnow()
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
    check_results = {}
    for key, definition in checks.items():
        check_results[key] = _check(root, definition)
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
        # A failed check cannot overwrite the last accepted compatibility baseline or receipt.
        if not problems:
            binding.pop("check_observation_refs", None)
            if binding.get("required_checks"):
                binding["check_receipt"] = {
                    "operation": operation,
                    "at": at,
                    "checks": [
                        check_results[json.dumps(c, sort_keys=True)]["receipt"]
                        for c in binding["required_checks"]
                    ],
                }
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
    scope = resolve_continuity_scope('project', root)
    snap = continuity.snapshot(scope, {'paths': [handoff]})
    if any(handoff in op['affected_paths'] for op in snap['pending_operations']):
        raise continuity.ContinuityError('handoff_reconciliation_pending', 4)
    text = snap['files'][handoff]['text'] or ''
    accepted = _envelope(text)
    envelope = copy.deepcopy(accepted)
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
            # The request meets the stored binding here, before the merged one is validated.
            if not _valid_selection(binding["workflow_ids"], binding["state_references"]):
                raise ValueError("invalid bound workflow selection")
            binding["workflow_ids"] = list(
                dict.fromkeys(existing["workflow_ids"] + binding["workflow_ids"])
            )
            binding["state_references"] = {
                **existing.get("state_references", {}),
                **binding["state_references"],
            }
            binding["check_observation_refs"] = copy.deepcopy(existing.get("check_observation_refs", []))
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
    for binding in envelope['bindings']:
        _validate_binding(binding, root)
    # A new proposed binding's identity is reserved even before it is accepted.
    ids = [request['binding_id']] if command in {'bind', 'reconcile', 'close'} and request.get('binding_id') else [b['binding_id'] for b in envelope['bindings'] if not b.get('closed')]
    if command == 'bind' and not request.get('binding_id'):
        ids = [identifier]
    result = _inspect(root, envelope, command)
    if command == 'close':
        selected = next(b for b in result['bindings'] if b['binding_id'] == request['binding_id'])
        selected_states = [x for x in result['states'] if x['workflow_id'] in selected['workflow_ids']]
        selected_checks = [x for x in result['checks'] if x['check'] in selected.get('required_checks', [])]
        tasks = [x for x in selected_checks if x['check']['kind'] == 'task']
        verified = (not selected['blockers'] and bool(selected_states or tasks)
            and all(x['lifecycle']['terminal'] for x in selected_states)
            and all(x['status'] == 'complete' for x in selected_checks)
            and all(x.get('observed_status') in TERMINAL_STATUSES for x in tasks))
        if verified:
            selected.update(closed={'reason': request['reason'], 'evidence': request['evidence'],
                'verified_states': [{k: v for k, v in x.items() if k not in ('state', 'stale_inputs')} for x in selected_states],
                'verified_checks': selected_checks}, unfinished=False)
        else:
            problem = {'binding_id': selected['binding_id'], 'reason': 'selected obligations are not terminal'}
            selected.update(status='blocked', unfinished=True, blockers=[*selected['blockers'], problem])
            result['blockers'].append(problem)
            result['status'] = 'blocked'
    # Failed proposals publish nothing: accepted expectations, references, baselines and receipts stay.
    final_bindings = None
    if command in {'bind', 'reconcile', 'close'}:
        selected_result = next(b for b in result['bindings'] if b['binding_id'] == ids[0])
        if not selected_result['blockers']:
            final_bindings = [copy.deepcopy(selected_result if b['binding_id'] == ids[0] else b) for b in accepted['bindings']]
            if not any(b['binding_id'] == ids[0] for b in final_bindings):
                final_bindings.append(copy.deepcopy(selected_result))
            if command == 'close':
                # A verified close removes the binding; the output keeps its closed record.
                final_bindings = [b for b in final_bindings if b['binding_id'] != ids[0]]
    elif command == 'export':
        final_bindings = copy.deepcopy(result['bindings'])
    if final_bindings is not None and envelope['bindings']:
        # One publish with the accepted binding changes and their receipts; legacy top-level data passes through.
        owner = copy.deepcopy(accepted)
        owner['bindings'] = final_bindings
        try:
            continuity.publish(scope, {'snapshot_token': snap['snapshot_token'], 'operation_id': 'development-' + uuid.uuid4().hex,
                'intended_change': 'Persist permitted development binding changes and their check receipts',
                'source_references': ['development adapter'],
                'affected_paths': [handoff], 'replacements': {handoff: _render(text, owner)}})
        except continuity.ContinuityError as exc:
            if command == 'close':
                # The handoff may already lack the binding; the caller must still receive its closed record.
                exc.closed_binding = {'binding_id': selected['binding_id'], 'closed': selected['closed']}  # type: ignore[attr-defined]
            raise
    if command == 'restore':
        result['retention'] = 'not_persisted'
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
    except (ValueError, OSError) as exc:
        # The contract's errors only (ContinuityError is a ValueError); a
        # programming error propagates instead of reading as "blocked".
        reason = exc.reason if isinstance(exc, continuity.ContinuityError) else str(exc)
        payload = {
            "schema_version": 1,
            "status": "blocked",
            "blockers": [{"reason": reason}],
        }
        closed_binding = getattr(exc, "closed_binding", None)
        if closed_binding:
            payload.update(closed_binding)
        print(json.dumps(payload))
        return exc.code if isinstance(exc, continuity.ContinuityError) else 2


if __name__ == "__main__":
    sys.exit(main())
