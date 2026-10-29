"""Trusted related-file evaluation over one materialized indexed candidate.

PLAN-VALIDATE and SOURCE-VERIFICATION need a filesystem view (globs, path
containment, recursive grep). This module writes exactly the captured
candidate entries into a fresh private directory and runs the trusted
readers against it. Candidate bytes are only written as data; nothing here
touches the index, the worktree or the staging area, and no candidate
program is imported or executed. Not a CLI: the pre-commit hook drives it
through ``indexed_standalone.run``.
"""

from __future__ import annotations

import os
import posixpath
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import threading
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Generator, Iterator
from urllib.parse import unquote

from lib.indexed_candidate import Candidate, Entry, InputUnavailable

PLACEHOLDER = "<candidate>"
_REGULAR = (b"100644", b"100755")
_SYMLINK = b"120000"
_GITLINK = b"160000"
_REPORT_RE = re.compile(
    r"^docs/(reviews/(board|council|code|architecture|sectional|amendment)|specs)/"
)
# Same acceptance as the former shell grep filter:
#   ^schema_version:[[:space:]]*["']?1["']?[[:space:]]*(#.*)?$
_SCHEMA_LINE_RE = re.compile(
    r"schema_version:[ \t\r\f\v]*[\"']?1[\"']?[ \t\r\f\v]*(#.*)?"
)
_EVIDENCE_LINES = 20


@dataclass(frozen=True)
class CandidateTree:
    path: Path
    private_root: Path
    unresolved_links: tuple[str, ...]
    gitlinks: tuple[str, ...]


@dataclass(frozen=True)
class RelatedResult:
    plan_status: str
    plan_detail: str
    plan_lines: tuple[str, ...]
    plan_evaluated: bool
    evidence_status: str
    evidence_detail: str
    evidence_lines: tuple[str, ...]
    evidence_evaluated: bool
    checked_reports: tuple[str, ...]
    unresolved_links: tuple[str, ...]
    gitlinks: tuple[str, ...]
    crossref_status: str
    crossref_detail: str
    crossref_lines: tuple[str, ...]
    crossref_unresolved: tuple[dict, ...]
    crossref_overflow: int


# ---------------------------------------------------------------------------
# Materialization
# ---------------------------------------------------------------------------


def _components(path: bytes) -> tuple[bytes, ...]:
    if not path or path.startswith(b"/"):
        raise InputUnavailable(f"unsupported candidate path {os.fsdecode(path)!r}")
    parts = tuple(path.split(b"/"))
    for part in parts:
        if part in (b"", b".", b"..") or part.lower() == b".git":
            raise InputUnavailable(
                f"unsupported candidate path component in {os.fsdecode(path)!r}"
            )
    return parts


def _check_layout(entries: tuple[Entry, ...]) -> dict[bytes, tuple[bytes, ...]]:
    parts: dict[bytes, tuple[bytes, ...]] = {}
    directories: set[bytes] = set()
    for entry in entries:
        if entry.mode not in (*_REGULAR, _SYMLINK, _GITLINK):
            raise InputUnavailable(
                f"unsupported candidate mode {os.fsdecode(entry.mode)} for "
                f"{os.fsdecode(entry.path)!r}"
            )
        components = _components(entry.path)
        parts[entry.path] = components
        for depth in range(1, len(components)):
            directories.add(b"/".join(components[:depth]))
    collisions = directories & parts.keys()
    if collisions:
        raise InputUnavailable(
            "candidate file/directory collision at "
            + repr(os.fsdecode(sorted(collisions)[0]))
        )
    return parts


def _feed(stream, payload: bytes) -> None:
    try:
        stream.write(payload)
    except (BrokenPipeError, OSError):
        pass
    finally:
        try:
            stream.close()
        except OSError:
            pass


def _drain(stream, sink: list[bytes]) -> None:
    try:
        sink.append(stream.read())
    except OSError:
        pass


def _read_exact(stream, size: int) -> bytes:
    chunks, remaining = [], size
    while remaining:
        chunk = stream.read(remaining)
        if not chunk:
            raise InputUnavailable("truncated candidate object stream")
        chunks.append(chunk)
        remaining -= len(chunk)
    return b"".join(chunks)


def _batch_blobs(
    candidate: Candidate, oids: list[bytes]
) -> Generator[tuple[bytes, bytes], None, None]:
    """Yield (oid, bytes) from one ``cat-file --batch`` over captured OIDs."""
    if not oids:
        return
    selection = candidate.selection
    try:
        process = subprocess.Popen(
            ["git", "--no-replace-objects", "cat-file", "--batch"],
            cwd=selection.cwd,
            env=dict(selection.environment),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    except OSError as exc:
        raise InputUnavailable(f"Git unavailable: {exc}") from exc
    assert process.stdin and process.stdout and process.stderr
    errors: list[bytes] = []
    writer = threading.Thread(
        target=_feed, args=(process.stdin, b"".join(oid + b"\n" for oid in oids))
    )
    reader = threading.Thread(target=_drain, args=(process.stderr, errors))
    writer.start()
    reader.start()
    completed = False
    try:
        for oid in oids:
            header = process.stdout.readline()
            fields = header.rstrip(b"\n").split(b" ")
            if not header.endswith(b"\n") or len(fields) != 3 or fields[0] != oid:
                raise InputUnavailable(
                    "candidate object unavailable: " + os.fsdecode(oid)
                )
            if fields[1] != b"blob" or not fields[2].isdigit():
                raise InputUnavailable(
                    "required candidate object is not a blob: " + os.fsdecode(oid)
                )
            data = _read_exact(process.stdout, int(fields[2]))
            if process.stdout.read(1) != b"\n":
                raise InputUnavailable("malformed candidate object stream")
            yield oid, data
        if process.stdout.read(1):
            raise InputUnavailable("unexpected candidate object stream data")
        completed = True
    finally:
        if not completed:
            process.kill()
        writer.join()
        process.stdout.close()
        returncode = process.wait()
        reader.join()
        process.stderr.close()
    if returncode:
        raise InputUnavailable(
            "Git cat-file input unavailable: " + os.fsdecode(b"".join(errors)).strip()
        )


def _inside(target: bytes, link_parts: tuple[bytes, ...]) -> bool:
    if not target or b"\0" in target or target.startswith(b"/"):
        return False
    stack = list(link_parts[:-1])
    for part in target.split(b"/"):
        if part in (b"", b"."):
            continue
        if part == b"..":
            if not stack:
                return False
            stack.pop()
        else:
            stack.append(part)
    return True


def _materialize(candidate: Candidate, root: bytes) -> tuple[list[str], list[str]]:
    parts = _check_layout(candidate.entries)
    made: set[bytes] = set()

    def ensure_parent(components: tuple[bytes, ...]) -> bytes:
        current = root
        for part in components[:-1]:
            current = os.path.join(current, part)
            if current not in made:
                try:
                    os.mkdir(current, 0o700)
                except FileExistsError:
                    if os.path.islink(current) or not os.path.isdir(current):
                        raise InputUnavailable("candidate path collision") from None
                made.add(current)
        return os.path.join(current, components[-1])

    by_oid: dict[bytes, list[Entry]] = {}
    gitlinks: list[str] = []
    for entry in candidate.entries:
        if entry.mode == _GITLINK:
            target = ensure_parent(parts[entry.path])
            try:
                os.mkdir(target, 0o700)
            except OSError as exc:
                raise InputUnavailable("candidate path collision") from exc
            gitlinks.append(os.fsdecode(entry.path))
        else:
            by_oid.setdefault(entry.oid, []).append(entry)

    links: list[tuple[Entry, bytes]] = []
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
    blobs = _batch_blobs(candidate, list(by_oid))
    try:
        for oid, data in blobs:
            for entry in by_oid[oid]:
                if entry.mode == _SYMLINK:
                    links.append((entry, data))
                    continue
                target = ensure_parent(parts[entry.path])
                try:
                    descriptor = os.open(target, flags, 0o600)
                except OSError as exc:
                    raise InputUnavailable("candidate path collision") from exc
                with os.fdopen(descriptor, "wb") as stream:
                    stream.write(data)
    finally:
        blobs.close()

    unresolved: list[str] = []
    created: list[bytes] = []
    for entry, target in sorted(links):
        if not _inside(target, parts[entry.path]):
            unresolved.append(os.fsdecode(entry.path))
            continue
        location = ensure_parent(parts[entry.path])
        try:
            os.symlink(target, location)
        except FileExistsError as exc:
            raise InputUnavailable("candidate path collision") from exc
        except OSError:
            unresolved.append(os.fsdecode(entry.path))
            continue
        created.append(location)
    # Defense in depth: lexical containment can still escape through another
    # in-tree link (`a -> ../..` then `b -> a/..`). Drop any created link
    # whose actual resolution leaves the tree; repeat until stable.
    real_root = os.path.realpath(root)
    changed = True
    while changed:
        changed = False
        for location in list(created):
            resolved = os.path.realpath(location)
            if resolved != real_root and not resolved.startswith(real_root + b"/"):
                os.unlink(location)
                created.remove(location)
                unresolved.append(os.fsdecode(os.path.relpath(location, root)))
                changed = True
    return sorted(unresolved), sorted(gitlinks)


@contextmanager
def candidate_tree(candidate: Candidate) -> Iterator[CandidateTree]:
    """Private materialized candidate (0700); always removed on exit."""
    private = tempfile.mkdtemp(prefix="forge-candidate-")
    try:
        os.chmod(private, 0o700)
        # The tree is one level down so `../` gate paths stay in private space.
        root = os.path.join(private, "tree")
        os.mkdir(root, 0o700)
        try:
            unresolved, gitlinks = _materialize(candidate, os.fsencode(root))
        except (InputUnavailable, OSError) as exc:
            # Failure details must not name the private path.
            scrub = _scrubber(CandidateTree(Path(root), Path(private), (), ()))
            raise InputUnavailable(scrub(str(exc))) from None
        yield CandidateTree(
            Path(root), Path(private), tuple(unresolved), tuple(gitlinks)
        )
    finally:
        shutil.rmtree(private, ignore_errors=True)


# ---------------------------------------------------------------------------
# Readers
# ---------------------------------------------------------------------------


def _scrubber(tree: CandidateTree):
    spellings = []
    for path in (tree.path, tree.private_root):
        for spelling in (str(path), os.path.realpath(path)):
            replacement = PLACEHOLDER if path == tree.path else PLACEHOLDER + "/.."
            spellings.append((spelling, replacement))
    spellings.sort(key=lambda item: len(item[0]), reverse=True)

    def scrub(text: str) -> str:
        for spelling, replacement in spellings:
            text = text.replace(spelling, replacement)
        return text

    return scrub


def plan_skip() -> tuple[str, str, tuple[str, ...]]:
    return (
        "SKIP",
        "plan_engine.py not found",
        (
            "pre-commit: PLAN-VALIDATE SKIP — plan_engine.py not found (graceful degradation)",
        ),
    )


_PLAN_INPUTS = ("docs/plan.yaml", "docs/task-schema-extensions.yaml", "docs/tasks")


def _plan_input(path: str) -> bool:
    """A dropped link/gitlink at (or above) a plan-engine input path."""
    return any(
        path == target or target.startswith(path + "/") or path.startswith(target + "/")
        for target in _PLAN_INPUTS
    )


def _plan(
    tree: CandidateTree, framework_root: Path, scrub
) -> tuple[str, str, tuple[str, ...], bool]:
    engine = framework_root / "scripts" / "plan_engine.py"
    if not engine.is_file():
        return (*plan_skip(), False)
    missing = [
        path for path in tree.unresolved_links + tree.gitlinks if _plan_input(path)
    ]
    if missing:
        detail = (
            "input unavailable: candidate plan input not materialized: "
            + ", ".join(sorted(missing))
        )
        return "BLOCK", detail, ("pre-commit: PLAN-VALIDATE BLOCK — " + detail,), False
    environment = dict(os.environ)
    environment.pop("BUDDY_PROJECT_ROOT", None)
    try:
        # -E: relative PYTHON* entries must not resolve inside candidate data.
        completed = subprocess.run(
            [
                sys.executable,
                "-E",
                str(engine),
                "--project-root",
                str(tree.path),
                "--validate",
            ],
            cwd=tree.path,
            env=environment,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
        )
    except OSError as exc:
        detail = "input unavailable: plan engine not runnable: " + str(exc)
        return "BLOCK", detail, ("pre-commit: PLAN-VALIDATE BLOCK — " + detail,), False
    output = scrub(completed.stdout.decode("utf-8", errors="replace")).rstrip("\n")
    lines = output.split("\n")
    # Only the engine's own final line counts, and only with exit 0: candidate
    # strings echoed in issue details must not forge a PASS.
    last = next((line for line in reversed(lines) if line.strip()), "")
    if completed.returncode == 0 and (
        re.match(r"Summary: 0 errors\b", last) or last.startswith("CLEAN:")
    ):
        return "PASS", "indexed candidate", ("pre-commit: PLAN-VALIDATE PASS",), True
    count = "\n".join(re.findall(r"(\d+) errors", output)) or "?"
    shown = [
        line for line in lines if line.startswith("ERRORS") or line.startswith("  ")
    ]
    return (
        "BLOCK",
        f"{count} error(s) found",
        (f"pre-commit: PLAN-VALIDATE BLOCK — {count} error(s) found", "", *shown, ""),
        True,
    )


def _reports(candidate: Candidate, tree: CandidateTree) -> list[tuple[str, str]]:
    selected = []
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    for entry in candidate.changed:
        path = os.fsdecode(entry.path)
        if entry.mode not in _REGULAR or not _REPORT_RE.match(path):
            continue
        descriptor = os.open(tree.path / path, flags)
        with os.fdopen(descriptor, "rb") as stream:
            content = stream.read().decode("utf-8", errors="replace")
        # Same newline translation as the former CLI's read_text.
        content = content.replace("\r\n", "\n").replace("\r", "\n")
        if any(_SCHEMA_LINE_RE.fullmatch(line) for line in content.split("\n")):
            selected.append((path, content))
    return selected


def _evidence(candidate: Candidate, tree: CandidateTree, framework_root: Path, scrub):
    if not (framework_root / "scripts" / "validate_evidence_pointers.py").is_file():
        return "SKIP", "availability: evidence validator missing", (), (), False
    try:
        reports = _reports(candidate, tree)
    except OSError as exc:
        detail = "candidate report unreadable: " + str(exc)
        return (
            "WARN/input unavailable",
            scrub(detail),
            (_evidence_unavailable_line(scrub(detail)),),
            (),
            False,
        )
    checked = tuple(path for path, _ in reports)
    if not reports:
        return "PASS", "no changed schema-1 reports in candidate", (), checked, True
    try:
        from lib import evidence_pointers
    except BaseException as exc:  # the module exits on missing PyYAML
        detail = f"evidence validator unavailable: {exc!r}"
        return (
            "WARN/input unavailable",
            detail,
            (_evidence_unavailable_line(detail),),
            checked,
            False,
        )
    errors: list[str] = []
    passed: list[str] = []
    overall = 0
    for path, content in reports:
        try:
            result = evidence_pointers.validate_content(
                content, repo_root=str(tree.path)
            )
            code, messages = result.exit_code, list(result.messages)
        except Exception as exc:
            code, messages = (
                evidence_pointers.EXIT_PARSE_ERROR,
                [f"validator failure: {exc}"],
            )
        # Former CLI shape under `2>&1`: unbuffered stderr (failures, WARN)
        # precedes block-buffered stdout.
        failing = code != evidence_pointers.EXIT_VALID
        if len(reports) > 1:
            (errors if failing else passed).append(f"=== {path} (exit {code}) ===")
        for message in messages:
            (errors if failing or message.startswith("WARN") else passed).append(
                message
            )
        overall = max(overall, code)
    if not overall:
        return "PASS", "indexed candidate", (), checked, True
    text = scrub("\n".join(errors + passed)).rstrip("\n")
    lines = (
        "",
        f"pre-commit: WARNING — SOURCE-VERIFICATION ({overall} fail across {len(reports)} file(s)):",
        *("    " + line for line in text.split("\n")[:_EVIDENCE_LINES]),
    )
    return "WARN", f"{overall} fail across {len(reports)} file(s)", lines, checked, True


def _evidence_unavailable_line(detail: str) -> str:
    return (
        "pre-commit: WARNING — SOURCE-VERIFICATION WARN/input unavailable — " + detail
    )


# ---------------------------------------------------------------------------
# Section cross-references: live Markdown of the candidate cites
# sections of other candidate Markdown files; each citation the commit
# touches must resolve in that same candidate. WARN-only, never BLOCK.
# ---------------------------------------------------------------------------

_CROSSREF_FROZEN = (
    "docs/tasks/archive",
    "context/history",
    "docs/build",
    "docs/fix",
    "docs/reviews",
    "docs/research",
    "docs/audit",
    "docs/audits",
    "docs/solve",
    "docs/handovers",
    "docs/review",
    "docs/docs-rewrite",
    "docs/discoveries",
    "docs/dogfood-learnings",
    "docs/decisions",
    "tests/fixtures",
    ".claude/skills/synced",
)
_CROSSREF_PREFIX = "pre-commit: WARNING — SOURCE-VERIFICATION cross-reference"
_CROSSREF_RECORDED = 200
_CROSSREF_LINE_LIMIT = 4000
_INTENT_TO_ADD = "intent-to-add, no staged content"
_MD_PATH = r"(?:[\w.-]+/)*[\w.-]+\.md"
# `path.md §…`, path bare or in one code span; `[text](path.md) §…`.
_SECTION_REF_RE = re.compile(r"(?<![\w./-])(`?)(" + _MD_PATH + r")\1[ \t]*§")
_LINK_SECTION_RE = re.compile(r"\[[^\]]*\]\([ \t]*<?([^()\s<>#]+\.md)>?[ \t]*\)[ \t]*§")
_ANCHOR_LINK_RE = re.compile(
    r"\[[^\]]*\]\([ \t]*<?([^()\s<>#]+\.md)#([^()\s<>]+?)>?"
    r"(?:[ \t]+\"[^\"]*\")?[ \t]*\)"
)
# Same fence rule as scripts/lib/evidence_pointers.py.
_FENCE_RE = re.compile(r"^ {0,3}(`{3,}|~{3,})(.*)$")
_NUMBER_RE = re.compile(r"[0-9]+[a-zA-Z]?(?:\.[0-9]+[a-zA-Z]?)*")
_NAME_END_RE = re.compile(r"[,;:)\]|`<]| [—–(+]|[.!?](?=\s|$)|$")
_PARENTHESES_RE = re.compile(r"\(([^()]*)\)")
_BLOCKQUOTE_RE = re.compile(r"^\s{0,3}>[ \t]?")
_HEADING_RE = re.compile(r"^ {0,3}#{1,6}(?:[ \t]+(.*?))?(?:[ \t]+#+)?[ \t]*$")
_LIST_ITEM_RE = re.compile(r"^[ \t]*([0-9]+)[.)](?:[ \t]+(.*)|$)")
_BOLD_LABEL_RE = re.compile(r"^[ \t]*(?:(?:[-*+]|[0-9]+[.)])[ \t]+)?(\*\*|__)(.+?)\1")
_HEADING_NUMBER_RE = re.compile(
    r"^(?:[0-9]+[a-zA-Z]?(?:\.[0-9]+[a-zA-Z]?)*)[.):]?[ \t]+"
)
_WORD_STRIP = "\"'“”‘’()[]{}.,;:!?*_§"


def _safe(text: str) -> str:
    """Surrogate-escaped path bytes as backslash escapes, so printing a line
    or writing the record can never raise."""
    return text.encode("utf-8", "backslashreplace").decode("utf-8")


def _crossref_unavailable_line(detail: str) -> str:
    return _CROSSREF_PREFIX + " WARN/input unavailable — " + _safe(detail)


def _number_at(text: str, position: int) -> str | None:
    """Numeric section token at ``position``: digits (dotted, optional letter
    suffix) not followed by a letter, digit or hyphen; a range ``N-M`` reads
    as N. Else None."""
    match = _NUMBER_RE.match(text, position)
    if not match:
        return None
    end = match.end()
    following = text[end : end + 1]
    if following.isalnum() or following == "_":
        return None
    if following == "-" and not text[end + 1 : end + 2].isdigit():
        return None
    return match.group(0).lower()


def _words(text: str) -> list[str]:
    words = (word.strip(_WORD_STRIP).lower() for word in text.replace("`", "").split())
    return [word for word in words if word]


def _code_spans(line: str) -> list[tuple[int, int]]:
    """Inline code spans on one line (a backtick run closes at the next run of
    the same length; an unmatched run is literal)."""
    runs = [(m.start(), m.end()) for m in re.finditer(r"`+", line)]
    spans, index = [], 0
    while index < len(runs):
        start, end = runs[index]
        close = next(
            (
                other
                for other in range(index + 1, len(runs))
                if runs[other][1] - runs[other][0] == end - start
            ),
            None,
        )
        if close is None:
            index += 1
            continue
        spans.append((start, runs[close][1]))
        index = close + 1
    return spans


def _fenced_lines(content: str) -> Iterator[tuple[int, str, bool]]:
    """(number, line, inside a fenced block); fence delimiter lines and lines
    longer than the line limit are omitted."""
    fence_char, fence_length = "", 0
    for number, line in enumerate(content.split("\n"), 1):
        fence = _FENCE_RE.match(line)
        if fence_char:
            if (
                fence
                and fence.group(1)[0] == fence_char
                and len(fence.group(1)) >= fence_length
                and not fence.group(2).strip()
            ):
                fence_char = ""
                continue
            fenced = True
        elif fence:
            fence_char, fence_length = fence.group(1)[0], len(fence.group(1))
            continue
        else:
            fenced = False
        if len(line) <= _CROSSREF_LINE_LIMIT:
            yield number, line, fenced


def _prose_lines(content: str) -> Iterator[tuple[int, str]]:
    """(number, line) outside fenced code blocks and block quotes."""
    for number, line, fenced in _fenced_lines(content):
        if not fenced and not _BLOCKQUOTE_RE.match(line):
            yield number, line


def _slug(title: str) -> str:
    """GitHub heading anchor: rendered text, lower case, punctuation dropped."""
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", title)
    text = re.sub(r"<[^>]+>", "", text).strip().lower()
    return re.sub(r"[^\w\- ]", "", text).replace(" ", "-")


@dataclass(frozen=True)
class _Sections:
    numbers: frozenset[str]
    headings: frozenset[tuple[str, ...]]  # name forms of headings
    labels: frozenset[tuple[str, ...]]  # name forms of bold labels and list items
    anchors: frozenset[str]


def _label(text: str) -> tuple[str, set[tuple[str, ...]]]:
    """Plain label text and its comparable name forms: as written, without
    leading `§`/numbering, and that cut at the first name terminator. Each
    form also yields its first two words hyphen-joined ("SOTA trigger" →
    "sota-trigger") so `§SOTA-Trigger` resolves."""
    plain = text.replace("*", "").replace("`", "").strip()
    unnumbered = _HEADING_NUMBER_RE.sub("", plain.lstrip("§ \t"), count=1)
    cut = unnumbered[: _NAME_END_RE.search(unnumbered).start()]
    forms: set[tuple[str, ...]] = set()
    for variant in (plain, unnumbered, cut):
        words = _words(variant)
        if words:
            forms.add(tuple(words))
            if len(words) >= 2:
                forms.add((words[0] + "-" + words[1], *words[2:]))
    return plain, forms


def _leading_number(plain: str) -> str | None:
    return _number_at(plain, len(plain) - len(plain.lstrip("§ \t")))


def _sections(content: str) -> _Sections:
    """Section labels of one target: headings, numbered list items and bold
    labels. Lines inside fenced blocks (output templates) and block quotes
    count for numbers and names; only unfenced headings are anchors."""
    numbers: set[str] = set()
    headings: set[tuple[str, ...]] = set()
    labels: set[tuple[str, ...]] = set()
    anchors: set[str] = set()
    seen: dict[str, int] = {}
    for _, raw, fenced in _fenced_lines(content):
        line = _BLOCKQUOTE_RE.sub("", raw, count=1)
        heading = _HEADING_RE.match(line)
        if heading:
            title = heading.group(1) or ""
            if not fenced:
                slug = _slug(title)
                count = seen.get(slug, 0)
                seen[slug] = count + 1
                anchors.add(slug if not count else f"{slug}-{count}")
            plain, forms = _label(title)
            headings.update(forms)
            # "Pattern: Fix-pass …" also answers to "Fix-pass …".
            if ": " in plain:
                headings.update(_label(plain.split(": ", 1)[1])[1])
            # "Consolidation (CHIEF-1)": a word with a digit in parentheses.
            for group in _PARENTHESES_RE.findall(plain):
                headings.update(
                    (word,)
                    for word in _words(group.replace(",", " "))
                    if any(char.isdigit() for char in word)
                )
            number = _leading_number(plain)  # "9.", "9.5 …", "§2.5 …"
            if number:
                numbers.add(number)
            continue
        listed = _LIST_ITEM_RE.match(line)
        if listed:
            numbers.add(listed.group(1))
            labels.update(_label(listed.group(2) or "")[1])
        label = _BOLD_LABEL_RE.match(line)
        if label:
            plain, forms = _label(label.group(2))
            labels.update(forms)
            number = _leading_number(plain)
            if number:
                numbers.add(number)
    return _Sections(
        frozenset(numbers), frozenset(headings), frozenset(labels), frozenset(anchors)
    )


def _same_word(cited: str, label: str) -> bool:
    return cited == label or cited.removesuffix("s") == label.removesuffix("s")


def _name_found(cited: list[str], sections: _Sections) -> bool:
    """A label starts with the cited name's first two words (its only word
    when it has one). A one-word heading also matches a name that runs on
    into the sentence ("§Authorization governs …"), unless the name's second
    word holds a digit ("§Invariant 7"); one-word bold labels and list items
    match one-word names only."""
    width = min(2, len(cited))
    run_on = width == 2 and not any(char.isdigit() for char in cited[1])
    for names, one_word in ((sections.headings, run_on), (sections.labels, False)):
        for name in names:
            if len(name) >= width:
                if all(_same_word(cited[i], name[i]) for i in range(width)):
                    return True
            elif one_word and _same_word(cited[0], name[0]):
                return True
    return False


def _section_ref(line: str, position: int) -> tuple[str, str] | None:
    """(kind, value) of the citation starting right after `§`."""
    number = _number_at(line, position)
    if number:
        return "number", number
    if position >= len(line) or not (line[position].isalnum() or line[position] == "_"):
        return None
    end = _NAME_END_RE.search(line, position).start()
    name = line[position:end].strip()
    return ("name", name) if _words(name) else None


def _references(line: str) -> Iterator[tuple[str, str, str, int]]:
    """(cited path, kind, value, column) for every supported reference."""
    spans = _code_spans(line)

    def quoted(column: int) -> bool:
        return any(start <= column < end for start, end in spans)

    for pattern, from_link in ((_SECTION_REF_RE, False), (_LINK_SECTION_RE, True)):
        for match in pattern.finditer(line):
            section = match.end() - 1
            if quoted(section):
                continue
            path = match.group(1 if from_link else 2)
            if from_link:
                if "://" in path or path.lower().startswith("mailto:"):
                    continue
                path = unquote(path)
            ref = _section_ref(line, match.end())
            if ref:
                yield path, ref[0], ref[1], match.start()
    for match in _ANCHOR_LINK_RE.finditer(line):
        path = match.group(1)
        if quoted(match.start()) or "://" in path or path.lower().startswith("mailto:"):
            continue
        yield unquote(path), "anchor", unquote(match.group(2)), match.start()


def _live_markdown(path: str) -> bool:
    return path.endswith(".md") and not any(
        path == prefix or path.startswith(prefix + "/") for prefix in _CROSSREF_FROZEN
    )


def _crossrefs(candidate: Candidate, tree: CandidateTree):
    """Resolve section cross-references of live candidate Markdown.

    Returns (status, detail, lines, unresolved, overflow). A reference is
    reported only when its referrer or its target is changed in the
    candidate. Any failure is WARN/input unavailable for this part only.
    """
    try:
        return _crossrefs_evaluate(candidate, tree)
    except Exception as exc:
        detail = _safe(f"cross-reference check failed: {exc}")
        return (
            "WARN/input unavailable",
            detail,
            (_crossref_unavailable_line(detail),),
            (),
            0,
        )


def _crossrefs_evaluate(candidate: Candidate, tree: CandidateTree):
    regular = {
        os.fsdecode(entry.path) for entry in candidate.entries if entry.mode in _REGULAR
    }
    # A cited path that is a symlink or gitlink, or runs through one, is not
    # checked.
    unchecked = {
        os.fsdecode(entry.path) for entry in candidate.entries if entry.mode == _SYMLINK
    } | set(tree.gitlinks)
    changed = {os.fsdecode(entry.path) for entry in candidate.changed}
    deleted, intent_to_add = set(), set()
    for path, reason in candidate.skipped:
        if reason == "deleted":
            deleted.add(os.fsdecode(path))
        elif reason == _INTENT_TO_ADD:
            intent_to_add.add(os.fsdecode(path))
    touched_names = {
        posixpath.basename(path) for path in changed | deleted if path.endswith(".md")
    }
    if not touched_names:
        return "PASS", "no changed Markdown in candidate", (), (), 0
    referrers = sorted(path for path in regular if _live_markdown(path))
    worktree = candidate.selection.cwd
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    # Suffix index, built once per run: basename → present and deleted live
    # Markdown paths. Frozen trees are left out (their snapshot copies would
    # make every common name ambiguous); the direct lookup still reaches them.
    by_name: dict[str, tuple[list[str], list[str]]] = {}
    for path in regular:
        if _live_markdown(path):
            by_name.setdefault(posixpath.basename(path), ([], []))[0].append(path)
    for path in deleted:
        if _live_markdown(path):
            by_name.setdefault(posixpath.basename(path), ([], []))[1].append(path)

    def read(path: str) -> str:
        descriptor = os.open(tree.path / path, flags)
        with os.fdopen(descriptor, "rb") as stream:
            content = stream.read().decode("utf-8", errors="replace")
        return content.replace("\r\n", "\n").replace("\r", "\n")

    def through_link(path: str) -> bool:
        parts = path.split("/")
        return any(
            "/".join(parts[:depth]) in unchecked for depth in range(1, len(parts) + 1)
        )

    def in_worktree(path: str) -> bool:
        """A regular working-tree file, reached without following a link.
        Existence only; its content is never read."""
        current, info = worktree, None
        for part in path.split("/"):
            current = os.path.join(current, part)
            try:
                info = os.lstat(current)
            except OSError:
                return False
            if stat.S_ISLNK(info.st_mode):
                return False
        return info is not None and stat.S_ISREG(info.st_mode)

    def locate(referrer: str, cited: str) -> tuple[str | None, str | None]:
        """(readable target, reason the target file is reported).

        Lookup order: referrer directory, repository root, then a unique
        path-suffix match among live candidate Markdown. A path deleted or
        renamed away in the candidate (direct, or the unique suffix match
        among deleted entries) is missing; for a changed referrer, a direct
        path that exists only in the working tree or as an intent-to-add entry
        is not staged. Several suffix matches or none are not checked.
        """
        if cited.startswith("/"):
            options = [cited.lstrip("/")]
        else:
            options = [posixpath.join(posixpath.dirname(referrer), cited), cited]
        paths: list[str] = []
        for option in options:
            path = posixpath.normpath(option)
            if path in ("", ".") or path == ".." or path.startswith(("../", "/")):
                continue
            if path not in paths:
                paths.append(path)
        for path in paths:
            if path in regular:
                return path, None
            if through_link(path):
                return None, None
        if any(path in deleted for path in paths):
            return None, "target file missing in candidate"
        if referrer in changed and any(
            path in intent_to_add or in_worktree(path) for path in paths
        ):
            return None, "target file not staged"
        tail = posixpath.normpath(cited.lstrip("/"))
        while tail.startswith("../"):
            tail = tail[3:]
        if tail in ("", ".", ".."):
            return None, None
        live, gone = by_name.get(posixpath.basename(tail), ([], []))
        live = [path for path in live if path == tail or path.endswith("/" + tail)]
        gone = [path for path in gone if path == tail or path.endswith("/" + tail)]
        if len(live) == 1 and not gone:
            return live[0], None
        if not live and len(gone) == 1:
            return None, "target file missing in candidate"
        return None, None

    cache: dict[str, _Sections] = {}
    seen: set[tuple[str, int, str, str, str]] = set()
    unresolved: list[dict] = []
    overflow = 0
    for referrer in referrers:
        content = read(referrer)
        if referrer not in changed and not any(
            name in content for name in touched_names
        ):
            continue
        for number, line in _prose_lines(content):
            for cited, kind, value, _ in _references(line):
                target, missing = locate(referrer, cited)
                if target is None and missing is None:
                    continue
                if target is not None:
                    if referrer not in changed and target not in changed:
                        continue
                    if target not in cache:
                        cache[target] = _sections(read(target))
                    sections = cache[target]
                    if kind == "number":
                        found = value in sections.numbers
                    elif kind == "name":
                        found = _name_found(_words(value), sections)
                    else:
                        found = value.lower() in sections.anchors
                    if found:
                        continue
                    missing = (
                        "no such anchor" if kind == "anchor" else "no such section"
                    )
                ref = ("#" if kind == "anchor" else "§") + value
                key = (referrer, number, target or cited, ref, missing)
                if key in seen:
                    continue
                seen.add(key)
                if len(unresolved) == _CROSSREF_RECORDED:
                    overflow += 1
                    continue
                unresolved.append(
                    dict(
                        referrer=_safe(referrer),
                        line=number,
                        target=_safe(target or cited),
                        ref=_safe(ref),
                        reason=missing,
                    )
                )
    if not unresolved:
        return "PASS", "indexed candidate", (), (), 0
    detail = f"{len(unresolved) + overflow} unresolved cross-reference(s)"
    if overflow:
        detail += f"; {overflow} beyond the first {_CROSSREF_RECORDED} not recorded"
    lines = [
        f"{_CROSSREF_PREFIX}: {item['referrer']}:{item['line']} → {item['target']}"
        + (item["ref"] if item["ref"].startswith("#") else " " + _shown(item["ref"]))
        + f": {item['reason']}"
        for item in unresolved[:_EVIDENCE_LINES]
    ]
    if len(unresolved) > _EVIDENCE_LINES:
        lines.append(
            f"{_CROSSREF_PREFIX}: … {len(unresolved) - _EVIDENCE_LINES} more in "
            "the INDEXED-STANDALONE record"
            + (f" ({overflow} more not recorded)" if overflow else "")
        )
    return "WARN", detail, tuple(lines), tuple(unresolved), overflow


def _shown(ref: str, limit: int = 60) -> str:
    return ref if len(ref) <= limit else ref[: limit - 1] + "…"


def evaluate_related(
    candidate: Candidate, tree: CandidateTree, framework_root: Path
) -> RelatedResult:
    scrub = _scrubber(tree)
    plan_status, plan_detail, plan_lines, plan_evaluated = _plan(
        tree, framework_root, scrub
    )
    (
        evidence_status,
        evidence_detail,
        evidence_lines,
        checked,
        evidence_evaluated,
    ) = _evidence(candidate, tree, framework_root, scrub)
    # The cross-reference part belongs to SOURCE-VERIFICATION and has the
    # same availability as its evidence part.
    if (framework_root / "scripts" / "validate_evidence_pointers.py").is_file():
        crossref = _crossrefs(candidate, tree)
    else:
        crossref = ("SKIP", "availability: evidence validator missing", (), (), 0)
    status, detail, lines, unresolved, overflow = crossref
    return RelatedResult(
        plan_status,
        scrub(plan_detail),
        tuple(plan_lines),
        plan_evaluated,
        evidence_status,
        scrub(evidence_detail),
        tuple(evidence_lines),
        evidence_evaluated,
        checked,
        tree.unresolved_links,
        tree.gitlinks,
        status,
        scrub(detail),
        tuple(scrub(line) for line in lines),
        tuple(unresolved),
        overflow,
    )


def unavailable_result(framework_root: Path | None, detail: str) -> RelatedResult:
    """Capture, tree or currentness failure: no definitive related result."""
    root = framework_root or Path("/nonexistent")
    plan: tuple[str, str, tuple[str, ...]]
    evidence: tuple[str, str, tuple[str, ...]]
    if (root / "scripts" / "plan_engine.py").is_file():
        plan = (
            "BLOCK",
            "input unavailable: " + detail,
            ("pre-commit: PLAN-VALIDATE BLOCK — input unavailable: " + detail,),
        )
    else:
        plan = plan_skip()
    if (root / "scripts" / "validate_evidence_pointers.py").is_file():
        evidence = (
            "WARN/input unavailable",
            detail,
            (_evidence_unavailable_line(detail),),
        )
        crossref = (
            "WARN/input unavailable",
            _safe(detail),
            (_crossref_unavailable_line(detail),),
        )
    else:
        evidence = ("SKIP", "availability: evidence validator missing", ())
        crossref = evidence
    return RelatedResult(
        plan[0],
        plan[1],
        plan[2],
        False,
        evidence[0],
        evidence[1],
        evidence[2],
        False,
        (),
        (),
        (),
        crossref[0],
        crossref[1],
        crossref[2],
        (),
        0,
    )


def evaluate(candidate: Candidate, framework_root: Path) -> RelatedResult:
    """Materialize, evaluate and remove; tree failures stay local to these checks."""
    try:
        with candidate_tree(candidate) as tree:
            return evaluate_related(candidate, tree, framework_root)
    except (InputUnavailable, OSError) as exc:
        return unavailable_result(framework_root, "candidate tree: " + str(exc))
