"""Current software-review qualification (public evidence-pointer protocol §9).

The engine owns workflow selection and persistence. This module owns subjects,
selected payloads and policy; it neither discovers nor mutates workflow state.
"""

from __future__ import annotations

import hashlib
import json
import re
import stat
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from scripts.lib.evidence_pointers import _FENCE_RE, review_evidence

POLICIES = frozenset({"evidence", "spec_success", "code_success"})
OPTION_FIELDS = frozenset(
    {"review_owner_workflow", "review_owner_step", "review_policy"}
)
DECISIONS = {
    "spec": {"PASS", "NEEDS-WORK"},
    "code": {"PASS", "PASS_WITH_RISKS", "FAIL", "PARTIAL"},
}
REPORT_FIELDS = ("slot", "path", "sha256", "actor")
MEDIATOR_MARKER = "[mediator-audit-pending]"
MARKDOWN_SUFFIXES = (".md", ".markdown")


class ReviewRefusal(ValueError):
    """Supported input or evidence does not qualify for this operation."""


class ReviewEvaluationError(RuntimeError):
    """Required source data could not be read or interpreted."""


@dataclass(frozen=True)
class ReviewCheck:
    current: bool
    permitted: bool
    decision: str | None
    message: str


def validate_adoption_options(comp: dict[str, Any]) -> list[str]:
    """The shared structural contract for the new pointer-check extension only."""
    present = OPTION_FIELDS.intersection(comp)
    if not present:
        return []
    errors = []
    if present != OPTION_FIELDS:
        errors.append(
            "mandatory review requires review_owner_workflow, review_owner_step and review_policy together"
        )
    for field in present:
        if not isinstance(comp[field], str) or not comp[field].strip():
            errors.append(f"{field} requires a nonblank string")
    if "review_policy" in present and (
        not isinstance(comp["review_policy"], str)
        or comp["review_policy"] not in POLICIES
    ):
        errors.append("review_policy must be evidence, spec_success or code_success")
    return errors


def _require(ok: bool, message: str) -> None:
    if not ok:
        raise ReviewRefusal(message)


def _nonblank(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _path(value: Any, *, root: bool = False) -> str:
    _require(isinstance(value, str) and bool(value), "path must be a nonempty string")
    if root and value == ".":
        return value
    _require(
        not value.startswith("/")
        and "\\" not in value
        and not any(c in value for c in "\x00*?[]"),
        f"unsupported literal path: {value!r}",
    )
    _require(
        all(part not in {"", ".", ".."} for part in value.split("/")),
        f"path must be normalized and project-relative: {value!r}",
    )
    try:
        value.encode("utf-8")
    except UnicodeError as exc:
        raise ReviewRefusal("path must have valid Unicode spelling") from exc
    return value


def _paths(value: Any, *, roots: bool = False) -> list[str]:
    _require(isinstance(value, list), "path selectors must be arrays")
    result = [_path(item, root=roots) for item in value]
    _require(len(set(result)) == len(result), "duplicate path/selector declaration")
    return sorted(result)


def _under(path: str, prefix: str) -> bool:
    return prefix == "." or path == prefix or path.startswith(prefix + "/")


def _target(root: Path, relative: str) -> Path:
    path = root
    for part in _path(relative).split("/"):
        path = path / part
        _require(not path.is_symlink(), f"unsupported symlink: {relative}")
    _require(
        path.resolve().is_relative_to(root.resolve()),
        f"path escapes project: {relative}",
    )
    return path


def _read(root: Path, relative: str) -> bytes:
    target = _target(root, relative)
    try:
        _require(
            stat.S_ISREG(target.stat().st_mode), f"regular file required: {relative}"
        )
        return target.read_bytes()
    except OSError as exc:
        raise ReviewEvaluationError(f"cannot read {relative}: {exc}") from exc


def _endpoint(root: Path, relative: str, *, required: bool = False) -> dict[str, str]:
    target = _target(root, relative)
    try:
        info = target.stat()
    except FileNotFoundError:
        _require(not required, f"required file missing: {relative}")
        return {"type": "absent"}
    except OSError as exc:
        raise ReviewEvaluationError(f"cannot inspect {relative}: {exc}") from exc
    _require(stat.S_ISREG(info.st_mode), f"unsupported subject entry: {relative}")
    return {
        "type": "file",
        "sha256": _sha(_read(root, relative)),
        "mode": "100755" if info.st_mode & 0o111 else "100644",
    }


def _git(root: Path, *args: str) -> bytes:
    try:
        result = subprocess.run(
            ["git", "-C", str(root), *args], capture_output=True, check=False
        )
    except OSError as exc:
        raise ReviewEvaluationError(f"Git unavailable: {exc}") from exc
    if result.returncode:
        raise ReviewEvaluationError(
            f"Git {' '.join(args)} failed: {result.stderr.decode('utf-8', errors='replace').strip()}"
        )
    return result.stdout


def _decode(data: bytes) -> str:
    try:
        return data.decode("utf-8")
    except UnicodeError as exc:
        raise ReviewRefusal("unsupported path/text Unicode spelling") from exc


def _history(root: Path, value: Any) -> list[dict[str, str]]:
    _require(isinstance(value, list), "history must be an array")
    refs = []
    for ref in value:
        _require(
            isinstance(ref, dict) and set(ref) == {"path", "sha256"},
            "history requires exact path/sha256 references",
        )
        path = _path(ref["path"])
        _require(
            isinstance(ref["sha256"], str)
            and bool(re.fullmatch(r"[0-9a-f]{64}", ref["sha256"])),
            "invalid historical digest",
        )
        _require(
            _sha(_read(root, path)) == ref["sha256"],
            f"historical bytes changed: {path}",
        )
        refs.append({"path": path, "sha256": ref["sha256"]})
    _require(
        len({ref["path"] for ref in refs}) == len(refs), "duplicate history reference"
    )
    return sorted(refs, key=lambda item: item["path"])


def capture_subject(
    project_root: Path, request: dict[str, Any]
) -> tuple[dict[str, Any], dict[str, Any], str]:
    """Validate a capture request and observe its entire canonical subject."""
    root = project_root.resolve()
    _require(isinstance(request, dict), "capture request must be an object")
    family, extent = request.get("family"), request.get("extent")
    _require(
        isinstance(family, str) and family in DECISIONS, "family must be spec or code"
    )
    _require(extent in ("full", "scoped"), "extent must be full or scoped")
    focus: Any = request.get("focus")
    _require(
        isinstance(focus, list) and all(_nonblank(item) for item in focus),
        "focus must contain nonempty descriptions",
    )
    _require(extent != "scoped" or bool(focus), "scoped capture requires focus")
    files = _paths(request.get("files"))
    slots: Any = request.get("slots")
    _require(
        isinstance(slots, list) and bool(slots), "nonempty producer slots required"
    )
    for slot in slots:
        _require(
            isinstance(slot, dict) and set(slot) == {"slot", "role"},
            "slot requires identifier and role",
        )
        _require(
            _nonblank(slot["slot"])
            and slot["role"] in ("reviewer", "chief", "verification", "discourse"),
            "unsupported slot/role",
        )
    _require(
        len({slot["slot"] for slot in slots}) == len(slots), "duplicate producer slot"
    )
    history = _history(root, request.get("history", []))
    code: Any = request.get("code_diff")
    canonical_code: dict[str, Any] | None = None
    normalized_code = None
    if family == "spec":
        _require(code is None, "spec capture does not support code_diff")
    else:
        _require(isinstance(code, dict), "code family requires code_diff")
        roots = _paths(code.get("roots"), roots=True)
        _require(bool(roots), "code roots must not be empty")
        _require(
            not any(_under(b, a) for i, a in enumerate(roots) for b in roots[i + 1 :]),
            "overlapping code roots",
        )
        excludes = _paths(code.get("exclude_files"))
        prefixes = _paths(code.get("exclude_prefixes"))
        _require(
            not set(excludes).intersection(prefixes), "duplicate exclusion declaration"
        )

        def excluded(path: str) -> bool:
            return path in excludes or any(_under(path, p) for p in prefixes)

        _require(
            not any(excluded(path) for path in files),
            "required input conflicts with output exclusion",
        )
        base = code.get("base")
        _require(
            isinstance(base, str)
            and bool(re.fullmatch(r"[0-9a-fA-F]{40}|[0-9a-fA-F]{64}", base)),
            "base requires a full existing commit ID",
        )
        commit = _decode(
            _git(root, "rev-parse", "--verify", base + "^{commit}")
        ).strip()
        tree = _decode(_git(root, "rev-parse", "--verify", commit + "^{tree}")).strip()

        def selected_raw(raw: bytes) -> bool:
            def under_raw(prefix: str) -> bool:
                encoded = prefix.encode("utf-8")
                return prefix == "." or raw == encoded or raw.startswith(encoded + b"/")

            return (
                any(under_raw(prefix) for prefix in roots)
                and raw not in {path.encode("utf-8") for path in excludes}
                and not any(under_raw(prefix) for prefix in prefixes)
            )

        before: dict[str, dict[str, str]] = {}
        for row in _git(root, "ls-tree", "-r", "-z", commit).split(b"\0"):
            if not row:
                continue
            meta, rawpath = row.split(b"\t", 1)
            if selected_raw(rawpath):
                path = _path(_decode(rawpath))
                mode, kind, oid = meta.decode("ascii").split()
                _require(
                    kind == "blob" and mode in {"100644", "100755"},
                    f"unsupported baseline entry: {path}",
                )
                before[path] = {
                    "type": "file",
                    "mode": mode,
                    "sha256": _sha(_git(root, "cat-file", "blob", oid)),
                }
        current = set()
        for row in _git(root, "ls-files", "--stage", "-z").split(b"\0"):
            if not row:
                continue
            meta, rawpath = row.split(b"\t", 1)
            if selected_raw(rawpath):
                path = _path(_decode(rawpath))
                mode, _oid, stage = meta.decode("ascii").split()
                _require(stage == "0", f"unresolved merge: {path}")
                _require(
                    mode in {"100644", "100755"}, f"unsupported index entry: {path}"
                )
                current.add(path)
        for row in _git(root, "ls-files", "--others", "--exclude-standard", "-z").split(
            b"\0"
        ):
            if row:
                if selected_raw(row):
                    current.add(_path(_decode(row)))
        changes: list[dict[str, Any]] = []
        for path in sorted(set(before) | current):
            old = before.get(path, {"type": "absent"})
            new = _endpoint(root, path)
            if old != new:
                changes.append({"path": path, "before": old, "after": new})
        normalized_code = {
            "base": commit,
            "roots": roots,
            "exclude_files": excludes,
            "exclude_prefixes": prefixes,
        }
        canonical_code = {
            "base_commit": commit,
            "base_tree": tree,
            "roots": roots,
            "exclude_files": excludes,
            "exclude_prefixes": prefixes,
            "changes": changes,
        }
    entries = [
        {"path": path, "entry": _endpoint(root, path, required=True)} for path in files
    ]
    if canonical_code:
        current_entries = {
            item["path"]: item["after"] for item in canonical_code["changes"]
        }
        _require(
            all(
                item["entry"] == current_entries.get(item["path"], item["entry"])
                for item in entries
            ),
            "required input changed during subject capture",
        )
    subject = {"subject_version": 1, "files": entries, "code_diff": canonical_code}
    normalized = {
        "family": family,
        "extent": extent,
        "focus": list(focus),
        "files": files,
        "code_diff": normalized_code,
        "slots": sorted(slots, key=lambda item: item["slot"]),
        "history": history,
    }
    digest = _sha(
        json.dumps(
            subject, sort_keys=True, separators=(",", ":"), ensure_ascii=True
        ).encode("ascii")
    )
    return normalized, subject, digest


class _UniqueLoader(yaml.SafeLoader):
    """Identity metadata cannot have two competing values for the same key."""

    def construct_mapping(self, node: Any, deep: bool = False) -> dict[str, Any]:
        self.flatten_mapping(node)
        result = {}
        for key_node, value_node in node.value:
            key = self.construct_object(key_node, deep=deep)
            if key in result:
                raise ValueError(f"duplicate YAML key: {key}")
            result[key] = self.construct_object(value_node, deep=deep)
        return result


_METADATA_RE = re.compile(r"\A---\s*\n(.*?)\n---(?:\s*\n|\Z)", re.DOTALL)


def _metadata(text: str) -> dict[str, Any]:
    """Frontmatter mapping, read with unique keys; raises on anything unreadable."""
    match = _METADATA_RE.match(text)
    if match is None:
        raise ValueError("no frontmatter")
    metadata = yaml.load(match.group(1), Loader=_UniqueLoader)
    if not isinstance(metadata, dict):
        raise ValueError("frontmatter is not a mapping")
    return metadata


ECHO_FIELDS = ("review_run_id", "review_subject_digest", "review_slot")
_ECHO_RES = {
    field: re.compile(rf"^{field}:\s*[\"']?([^\"'\s#]+)") for field in ECHO_FIELDS
}


def _echo(text: str) -> dict[str, list[str]]:
    """Run echo values read line by line from the leading frontmatter block.

    The block starts at a first line ``---`` (after an optional BOM) and ends
    at the next ``---`` line; no block, no echo. Independent of whether the
    block parses as YAML, so a malformed line elsewhere cannot hide a value.
    """
    lines = text.removeprefix("\ufeff").splitlines()
    if not lines or lines[0].rstrip() != "---":
        return {}
    echo: dict[str, list[str]] = {}
    for line in lines[1:]:
        if line.rstrip() == "---":
            return echo
        for field, pattern in _ECHO_RES.items():
            match = pattern.match(line)
            if match:
                echo.setdefault(field, []).append(match.group(1))
    return {}


def _same_history(value: Any, history: list[dict[str, str]]) -> bool:
    if not isinstance(value, list) or not all(
        isinstance(ref, dict) and set(ref) == {"path", "sha256"} for ref in value
    ):
        return False
    return sorted(value, key=lambda ref: str(ref["path"])) == history


def _report(
    project_root: Path, capture: dict[str, Any], ref: dict[str, Any]
) -> tuple[int, list[str]]:
    """Pin one selected report and resolve its evidence; returns (verified, diagnostics).

    The report's run echo is its input binding: a run or subject echo that
    names another capture refuses, so does a slot echo that names another
    slot, and so does a report that names no run.
    """
    path = _path(ref["path"])
    raw = _read(project_root, path)
    _require(_sha(raw) == ref["sha256"], f"selected report bytes changed: {path}")
    diagnostics = []
    try:
        text = raw.decode("utf-8")
    except UnicodeError:
        text = raw.decode("utf-8", errors="replace")
        diagnostics.append("not UTF-8; read with replacement characters")
    echo = _echo(text)
    for field in ("review_run_id", "review_subject_digest"):
        _require(
            all(value == str(capture[field]) for value in echo.get(field, [])),
            f"foreign report: {path}",
        )
    _require(
        all(slot == ref["slot"] for slot in echo.get("review_slot", [])),
        f"report names another slot: {path}",
    )
    _require("review_run_id" in echo, f"report does not name the captured run: {path}")
    try:
        _metadata(text)  # YAML only for diagnostics; the echo above decides
    except (yaml.YAMLError, ValueError) as exc:
        diagnostics.append(f"report envelope unreadable: {exc}")
    missing = [field for field in ECHO_FIELDS[1:] if field not in echo]
    if missing:
        diagnostics.append("report envelope lacks " + ", ".join(missing))
    evidence = review_evidence(text, repo_root=str(project_root))
    _require(
        not evidence.failures,
        f"evidence does not resolve: {path}: " + "; ".join(evidence.failures),
    )
    diagnostics.extend(evidence.diagnostics)
    return evidence.verified, [f"{path}: {item}" for item in diagnostics]


def qualify_decision(
    project_root: Path,
    capture: dict[str, Any],
    verdict_path: str,
) -> dict[str, Any]:
    """Bind Buddy's decision to the capture, pin its reports and resolve their quotes.

    Form problems are returned as diagnostics; refusals are reserved for a
    noncurrent subject, a foreign or unsupported decision, an incomplete or
    changed report selection, two selected reports with identical bytes, a
    foreign report or one that names no run or another slot, and evidence
    that does not resolve.
    """
    normalized, subject, digest = capture_subject(project_root, capture["request"])
    _require(
        subject == capture["subject"] and digest == capture["review_subject_digest"],
        "review subject is noncurrent; retry and capture before review",
    )
    path = _path(verdict_path)
    raw = _read(project_root, path)
    try:
        text = raw.decode("utf-8")
        metadata = _metadata(text)
    except (UnicodeError, yaml.YAMLError, ValueError) as exc:
        raise ReviewRefusal(f"decision frontmatter unreadable: {path}: {exc}") from exc
    for field in ("review_run_id", "review_subject_digest"):
        _require(
            _nonblank(metadata.get(field)) and metadata[field] == capture[field],
            f"foreign/missing {field}",
        )
    decision = metadata.get("decision")
    _require(
        isinstance(decision, str) and decision in DECISIONS[normalized["family"]],
        "unsupported decision for captured family",
    )
    reports: Any = metadata.get("current_reports")
    _require(
        isinstance(reports, list) and bool(reports),
        "current_reports must be a nonempty list",
    )
    for ref in reports:
        _require(
            isinstance(ref, dict)
            and all(_nonblank(ref.get(key)) for key in ("slot", "path", "actor"))
            and isinstance(ref.get("sha256"), str)
            and bool(re.fullmatch(r"[0-9a-f]{64}", ref["sha256"])),
            "current report requires nonblank slot, path and actor and a 64-hex sha256",
        )
    selected = [{key: ref[key] for key in REPORT_FIELDS} for ref in reports]
    paths = [_path(ref["path"]) for ref in selected]
    slots = [ref["slot"] for ref in selected]
    _require(len(set(slots)) == len(slots), "duplicate report slot")
    _require(len(set(paths)) == len(paths), "duplicate report path")
    _require(
        len({ref["sha256"] for ref in selected}) == len(selected),
        "duplicate report bytes",
    )
    captured = [slot["slot"] for slot in normalized["slots"]]
    for slot in captured:
        _require(slot in slots, f"captured slot without report: {slot}")
    diagnostics = [f"report slot not captured: {slot}" for slot in slots if slot not in captured]
    verified = 0
    for ref in selected:
        count, notes = _report(project_root, capture, ref)
        verified += count
        diagnostics.extend(notes)
    history = normalized["history"]
    if "history" in metadata and not _same_history(metadata["history"], history):
        diagnostics.append("decision history differs from capture history")
    return {
        "verdict_path": path,
        "sha256": _sha(raw),
        "raw_decision": text,
        "decision": decision,
        "current_reports": sorted(selected, key=lambda ref: ref["path"]),
        "history": history,
        "qualification": "current",
        "quotes_verified": verified,
        "diagnostics": diagnostics,
    }


_BLOCK_QUOTE_RE = re.compile(r"^ {0,3}>")
# Word joiners of a near miss: "-", "_" and the Unicode hyphens U+2010–U+2015, U+2212.
_JOIN = "_\\-\u2010-\u2015\u2212"
_MARKER_LIKE_RE = re.compile(
    rf"\[\s*mediator[\s{_JOIN}]*audit[\s{_JOIN}]*pending"
    rf"|\bmediator[{_JOIN}]+audit[{_JOIN}]+pending\b",
    re.IGNORECASE,
)


def _outside_code_spans(line: str) -> tuple[str, bool]:
    """The line with each inline code span replaced by one space (CommonMark),
    and whether a backtick run on it found no closer on the line.

    A span opens at an unescaped backtick run and closes at the next run of
    the same length; a backslash-escaped backtick opens nothing, while inside
    a span backslashes are literal. A run without a closer stays text; it may
    be a span that the paragraph's next line closes.
    """
    out: list[str] = []
    unmatched = False
    i, n = 0, len(line)
    while i < n:
        if line[i] == "\\" and i + 1 < n:
            out.append(line[i : i + 2])
            i += 2
            continue
        if line[i] != "`":
            out.append(line[i])
            i += 1
            continue
        end = i
        while end < n and line[end] == "`":
            end += 1
        run, k, close = end - i, end, -1
        while k < n:
            if line[k] != "`":
                k += 1
                continue
            stop = k
            while stop < n and line[stop] == "`":
                stop += 1
            if stop - k == run:
                close = k
                break
            k = stop
        if close < 0:
            out.append(line[i:end])
            unmatched = True
            i = end
        else:
            out.append(" ")
            i = close + run
    return "".join(out), unmatched


def _fence_opener(line: str) -> re.Match[str] | None:
    """A fence opening line; a backtick fence's info string has no backtick (CommonMark)."""
    match = _FENCE_RE.match(line)
    if match and match.group(1)[0] == "`" and "`" in match.group(2):
        return None
    return match


def _indent(line: str) -> int:
    return len(line) - len(line.lstrip(" "))


def _fenced(lines: list[str]) -> list[bool]:
    """Lines inside a closed fence (both fence lines included).

    Fences follow the evidence scanner: same character, a closing run at least
    the opening length, no info string on the closing line. An opening fence
    that is never closed hides nothing; scanning continues after it. Unlike
    the shared scanner, a backtick line whose info string holds a backtick
    opens no fence.

    The scan does not model list items or other containers; it fails closed
    instead. A fence hides lines only if its closer has the opener's
    indentation and no non-blank line between them is indented less than the
    opener (a list item that ends there may already have closed it). Otherwise
    the opener counts as a fence whose end is unknown: it hides nothing, and
    neither does any later fence in the file, since the scan can no longer
    tell an opening fence line from a closing one.
    """
    hidden = [False] * len(lines)
    i = 0
    while i < len(lines):
        opening = _fence_opener(lines[i])
        if opening:
            char, length = opening.group(1)[0], len(opening.group(1))
            indent = _indent(lines[i])
            for j in range(i + 1, len(lines)):
                closing = _FENCE_RE.match(lines[j])
                if (
                    closing
                    and closing.group(1)[0] == char
                    and len(closing.group(1)) >= length
                    and not closing.group(2).strip()
                ):
                    if _indent(lines[j]) != indent or any(
                        line.strip() and _indent(line) < indent
                        for line in lines[i + 1 : j]
                    ):
                        return hidden
                    hidden[i : j + 1] = [True] * (j + 1 - i)
                    i = j
                    break
        i += 1
    return hidden


def _mediator_marker(project_root: Path, files: list[str]) -> str | None:
    """The first operative mediator-audit marker in captured Markdown.

    Code spans are found per line, which fails closed instead of modelling a
    span that wraps across lines: once a line of a paragraph (consecutive
    non-blank lines outside fences and block quotes) leaves a backtick run
    unclosed, the paragraph's following lines are scanned raw. A marker inside
    a span that wraps is therefore refused although it is code; that false
    refusal is the accepted cost.
    """
    for path in files:
        if not path.lower().endswith(MARKDOWN_SUFFIXES):
            continue
        try:
            text = _read(project_root, path).decode("utf-8")
        except (ReviewRefusal, ReviewEvaluationError, UnicodeError):
            return f"captured file unreadable: {path}"
        lines = text.splitlines()
        hidden = _fenced(lines)
        raw = False  # an earlier line of this paragraph left a code span open
        for number, line in enumerate(lines, start=1):
            if hidden[number - 1] or _BLOCK_QUOTE_RE.match(line) or not line.strip():
                raw = False  # a fence, a block quote or a blank line ends the paragraph
                continue
            if raw:
                visible = line
            else:
                visible, raw = _outside_code_spans(line)
            match = _MARKER_LIKE_RE.search(visible)
            if match:
                kind = (
                    "unresolved"
                    if visible.startswith(MEDIATOR_MARKER, match.start())
                    else "malformed"
                )
                return f"{kind} mediator audit marker: {path}:{number}"
    return None


def check_adoption(
    project_root: Path,
    capture: dict[str, Any],
    adoption: dict[str, Any] | None,
    policy: str,
    *,
    configured_source: str | None = None,
) -> ReviewCheck:
    """Read-only requalification of identity; evidence currentness is independent of policy.

    Quotes were resolved once, at adoption; this rechecks the subject and the
    pinned decision and report bytes (old-format adoptions alike).
    """
    _require(policy in POLICIES, "unknown review policy")
    if not adoption:
        return ReviewCheck(False, False, None, "no current adopted decision")
    try:
        _, subject, digest = capture_subject(project_root, capture["request"])
        _require(
            subject == capture["subject"] and digest == capture["review_subject_digest"],
            "review subject is noncurrent; retry and capture before review",
        )
        verdict = _path(adoption["verdict_path"])
        _require(
            _sha(_read(project_root, verdict)) == adoption["sha256"],
            f"adopted decision bytes changed: {verdict}",
        )
        for ref in adoption["current_reports"]:
            report = _path(ref["path"])
            _require(
                _sha(_read(project_root, report)) == ref["sha256"],
                f"selected report bytes changed: {report}",
            )
        if configured_source is not None:
            _require(
                _sha(_read(project_root, _path(configured_source)))
                == adoption["sha256"],
                "configured decision locator differs from retained decision bytes",
            )
    except ReviewRefusal as exc:
        return ReviewCheck(False, False, adoption.get("decision"), str(exc))
    family, decision = capture["request"]["family"], adoption["decision"]
    if family == "spec" and policy == "spec_success":
        marker = _mediator_marker(project_root, capture["request"]["files"])
        if marker:
            return ReviewCheck(
                True, False, decision, f"current {family} {decision}; {policy}: refused: {marker}"
            )
    permitted = (
        policy == "evidence"
        or (policy == "spec_success" and family == "spec" and decision == "PASS")
        or (
            policy == "code_success"
            and family == "code"
            and decision in {"PASS", "PASS_WITH_RISKS"}
        )
    )
    return ReviewCheck(
        True,
        permitted,
        decision,
        f"current {family} {decision}; {policy}: {'permitted' if permitted else 'refused'}",
    )
