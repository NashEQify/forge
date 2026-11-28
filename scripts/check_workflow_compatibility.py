#!/usr/bin/env python3
"""Guard Forge's local main ref using committed workflow compatibility edges."""

from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

MAIN = "refs/heads/main"
MANIFEST = "framework/workflow-compatibility.yaml"
REVIEW = "framework/workflow-compatibility-review-gates.md"
RUNBOOKS = "workflows/runbooks/"
SKILLS = "skills/"
OID = re.compile(r"(?:[0-9a-f]{40}|[0-9a-f]{64})")
FINGERPRINT = re.compile(r"[0-9a-f]{64}")


class CheckError(Exception):
    """The pending ref update could not be verified."""


def git_result(*args, cwd=None, env=None, errors="strict"):
    result = subprocess.run(
        ["git", "--no-replace-objects", *args],
        cwd=cwd, env=env, capture_output=True, check=False,
    )
    return subprocess.CompletedProcess(
        result.args, result.returncode,
        result.stdout.decode("utf-8", errors), result.stderr.decode("utf-8", errors),
    )


def git(*args, cwd=None, env=None, errors="strict"):
    result = git_result(*args, cwd=cwd, env=env, errors=errors)
    if result.returncode:
        raise CheckError(f"git {' '.join(args)} failed: {result.stderr.strip()}")
    return result.stdout


def same_repository(source):
    if not ((source / ".git").is_dir() or (source / ".git").is_file()):
        return False
    source_env = os.environ.copy()
    for key in git("rev-parse", "--local-env-vars").splitlines():
        source_env.pop(key, None)
    args = ("rev-parse", "--path-format=absolute", "--git-common-dir")
    trusted = git(*args, cwd=source, env=source_env).strip()
    return Path(trusted).resolve() == Path(git(*args).strip()).resolve()


def existing_main():
    result = git_result("for-each-ref", "--format=%(refname) %(objectname)", MAIN)
    if result.returncode or result.stderr:
        raise CheckError(f"cannot determine whether {MAIN} exists: {result.stderr.strip()}")
    current = None
    for record in result.stdout.splitlines():
        ref, separator, oid = record.partition(" ")
        if (not separator or not OID.fullmatch(oid) or not oid.strip("0")
                or (ref != MAIN and not ref.startswith(f"{MAIN}/"))):
            raise CheckError(f"invalid ref lookup output for {MAIN}: {record!r}")
        if ref == MAIN:
            if current is not None:
                raise CheckError(f"duplicate ref lookup output for {MAIN}")
            current = oid
    return current


def inputs(commit):
    if git("cat-file", "-t", commit).strip() != "commit":
        raise CheckError(f"{commit} is not a commit")
    discovery_roots = (RUNBOOKS.rstrip("/"), SKILLS.rstrip("/"))
    roots = {"workflows", *discovery_roots}
    entries = git("ls-tree", "-z", commit, "--", "workflows")
    entries += git("ls-tree", "-rzt", commit, "--", *discovery_roots, MANIFEST,
                   errors="surrogateescape")
    candidates: dict[str, dict[str, tuple[str, str, str]]] = {RUNBOOKS: {}, SKILLS: {}}
    manifest = None
    for entry in entries.rstrip("\0").split("\0") if entries else ():
        metadata, path = entry.split("\t", 1)
        mode, kind, oid = metadata.split()
        if path == MANIFEST:
            manifest = (path, mode, oid)
            continue
        if path in roots and kind != "tree":
            raise CheckError(f"{commit}:{path} must be a directory for workflow discovery")
        for prefix in candidates:
            if not path.startswith(prefix):
                continue
            parts = path.removeprefix(prefix).split("/")
            if len(parts) == 1 and mode in {"120000", "160000"}:
                candidates[prefix][parts[0]] = (path, mode, oid)
            elif len(parts) == 2 and parts[1] == "workflow.yaml":
                candidates[prefix][parts[0]] = (path, mode, oid)

    return candidates[SKILLS] | candidates[RUNBOOKS], manifest


def loadable_workflows(commit, entries, *, previous=None):
    workflows = {}
    for key, entry in entries.items():
        path, mode, _ = entry
        if path in {f"{RUNBOOKS}{key}", f"{SKILLS}{key}"}:
            raise CheckError(f"{commit}:{path} must be a directory for workflow discovery")
        # A selected directory could not start a run. Preserve precedence
        # and allow recovery without inventing a predecessor from its fallback.
        if mode == "040000" and (previous is None or previous.get(key) == entry):
            continue
        if mode not in {"100644", "100755"}:
            raise CheckError(f"{commit}:{path} must be a regular workflow YAML file")
        workflows[key] = entry
    return workflows


def read_yaml(commit, entry, *, yaml):
    path, mode, oid = entry
    if mode not in {"100644", "100755"}:
        raise CheckError(f"{commit}:{path} must be a regular file")
    try:
        return yaml.safe_load(git("cat-file", "blob", oid))
    except (CheckError, UnicodeError, yaml.YAMLError) as error:
        raise CheckError(f"cannot read {commit}:{path}: {error}") from error


def fingerprint(commit, entry, *, yaml, validate, compute):
    definition = read_yaml(commit, entry, yaml=yaml)
    try:
        if not isinstance(definition, dict):
            raise ValueError("expected a mapping")
        errors = validate(definition)
        if errors:
            raise ValueError(", ".join(errors))
        return compute(definition)
    except (ValueError, TypeError) as error:
        raise CheckError(f"invalid workflow {commit}:{entry[0]}: {error}") from error


def manifest_edges(commit, entry, *, yaml):
    if entry is None:
        return set()
    data = read_yaml(commit, entry, yaml=yaml)
    if not isinstance(data, dict) or type(data.get("version")) is not int or data["version"] != 1:
        raise CheckError(f"{commit}:{MANIFEST} must be a version-1 mapping")
    rows = data.get("mappings", [])
    if not isinstance(rows, list):
        raise CheckError(f"{commit}:{MANIFEST} mappings must be a list")
    for number, row in enumerate(rows, start=1):
        if not isinstance(row, dict):
            raise CheckError(f"{commit}:{MANIFEST} row {number} must be a mapping")
        directions = row.get("allowed_directions", [])
        if not isinstance(directions, list) or any(
            direction not in ("upgrade", "rollback") for direction in directions
        ):
            raise CheckError(f"{commit}:{MANIFEST} row {number} has invalid allowed_directions")

    edges = set()
    for row in rows:
        if row.get("review_status") != "accepted" or "upgrade" not in row.get("allowed_directions", []):
            continue
        pointer = row.get("preserved_obligations")
        workflow, prior, current = (row.get(key) for key in ("workflow", "prior", "current"))
        if (isinstance(pointer, str) and pointer.strip()
                and isinstance(workflow, str) and workflow
                and all(isinstance(value, str) and FINGERPRINT.fullmatch(value)
                        for value in (prior, current))):
            edges.add((workflow, prior, current))
    return edges


def require_edge(edge, *, restore=False):
    workflow, prior, current = edge
    action = "Restore" if restore else "Add"
    raise CheckError(
        f"{action} an accepted upgrade edge for {workflow}: {prior} → {current} "
        f"in {MANIFEST} in the same change, with a preservation pointer. "
        f"Pair review: {REVIEW}"
    )


def check_landing(old, new, source):
    old_inputs, old_manifest = inputs(old)
    new_inputs, new_manifest = inputs(new)
    old_workflows = loadable_workflows(old, old_inputs)
    new_workflows = loadable_workflows(new, new_inputs, previous=old_inputs)
    manifest_changed = old_manifest != new_manifest
    keys = old_workflows.keys() & new_workflows.keys()
    relevant = sorted(key for key in keys if manifest_changed or old_workflows[key] != new_workflows[key])
    if not relevant and not manifest_changed:
        return

    # Import only from the trusted installation. Candidate YAML is data.
    sys.dont_write_bytecode = True
    sys.path.insert(0, str(source))
    import yaml
    from scripts.lib.yaml_loader import validate_workflow_schema
    from scripts.workflow_engine import definition_fingerprint

    fingerprint_tools = {"yaml": yaml, "validate": validate_workflow_schema,
                         "compute": definition_fingerprint}

    changes = {}
    for key in relevant:
        before = fingerprint(old, old_workflows[key], **fingerprint_tools)
        after = before
        if old_workflows[key] != new_workflows[key]:
            after = fingerprint(new, new_workflows[key], **fingerprint_tools)
        changes[key] = (before, after)
    if not manifest_changed and all(before == after for before, after in changes.values()):
        return

    old_edges = manifest_edges(old, old_manifest, yaml=yaml)
    new_edges = manifest_edges(new, new_manifest, yaml=yaml)
    for key, (before, after) in changes.items():
        if before != after and (key, before, after) not in new_edges - old_edges:
            require_edge((key, before, after))
    for edge in sorted(old_edges - new_edges):
        key, _, current = edge
        if changes.get(key) == (current, current):
            require_edge(edge, restore=True)


def packing_refs():
    """True when the git process running this hook is `git pack-refs`.

    pack-refs moves a loose ref into packed-refs: one transaction creates the packed entry, a second deletes the
    loose file, and the ref keeps its value throughout. Without /proc the answer is False and the deletion is refused
    as before.
    """
    try:
        argv = Path(f"/proc/{os.getppid()}/cmdline").read_bytes().split(b"\0")
    except OSError:
        return False
    return b"pack-refs" in argv[1:3]


def check_transaction(source):
    for record in sys.stdin:
        old, new, ref = record.split()
        if ref != MAIN or not same_repository(source):
            continue
        if not OID.fullmatch(old) or not OID.fullmatch(new):
            raise CheckError(f"cannot interpret object IDs for {MAIN}")
        if not old.strip("0"):
            old = existing_main()
        if old is None:
            continue
        if not new.strip("0"):
            if packing_refs():
                continue
            raise CheckError(f"cannot delete established {MAIN}; it anchors workflow compatibility")
        if old != new:
            check_landing(old, new, source)


if __name__ == "__main__" and sys.argv[1:] == ["prepared"]:
    try:
        check_transaction(Path(__file__).resolve().parents[1])
    except (CheckError, OSError, ValueError, ImportError) as error:
        print(f"workflow compatibility: {error}", file=sys.stderr)
        sys.exit(1)
