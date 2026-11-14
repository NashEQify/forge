#!/usr/bin/env python3
"""select_tests.py — choose the pytest files that exercise a set of changed paths.

Agents run the set this prints for a change. The broad suite runs when the
result is ``broad``, or when the change touches a safety floor (the testing
skill, ``skills/testing/run-strategy.md`` §Test selection, decides that). The
selector reads the repository statically (``ast`` and ``git`` only): it never
imports project code, never runs tests and never writes files. A missing
exercising test is the failure that matters; over-selection only costs time.
When a rule is ambiguous the selector therefore keeps the edge.

Usage:
    python3 scripts/select_tests.py [--root DIR]
        (--staged | --diff RANGE | --worktree | --paths-from FILE | PATH...)
        [--format text|json|args] [--explain PATH] [--map]

Inputs (paths are repo-relative to --root, default the working directory):
    --staged          ``git diff --cached --name-status -M`` (both sides of a
                      rename, deleted paths included)
    --diff RANGE      ``git diff --name-status -M RANGE``
    --worktree        ``git status --porcelain`` (staged, unstaged, untracked)
    --paths-from FILE one path per line; ``-`` reads stdin
    PATH...           paths given directly; a directory expands to its files
An input that yields no changed paths (nothing staged, a clean tree, an empty
range or list) is an error, not an empty selection; for committed work use
``--diff <base>..HEAD``. ``--explain`` and ``--map`` also run without an input.

Text result (the contract agents read):
    result: targeted | result: broad      always the first line
    reason: <why>                         broad only, one line per reason
    tests/test_x.py                       selected test files, one per line
    light-path: <path>                    Markdown no test reads: no pytest
    no tests: <path>                      unmapped paths inside a no-test zone
    removed test: <path>                  deleted test files (they select nothing)

Markdown (``.md``) outside the test paths selects only the tests whose own
code reads it: depth-0 code (the test file, its conftest ancestry, support
files under the test paths) that reaches it over a direct edge or lists it
with ``glob``/``rglob``. Reach through module code or a copied tree does not
count. Markdown no test reads selects nothing and never makes the result
broad: outside the no-test zones it is a ``light-path`` line, verified by the
light-path checks (``framework/installation-activation.md`` §Light path)
instead of pytest; inside them it is ``no tests``. Code (``.py``, ``.sh`` or a
script by its shebang, not a test file) selects only the tests that reach it
over direct edges (see the edges below); with none it is unmapped outside the
zones: a test that only copies the tree holding it does not exercise it.
Every other path (data files, templates, test files, Markdown under the test
paths) selects each test that reaches it over any edge. Shared test
infrastructure, cross-cutting entries and absent test files keep their own
rules, below.
``broad`` means a targeted run is not enough: a changed path is shared test
infrastructure, is on the cross-cutting list, or maps to no test outside the
no-test zones. The targeted union is still listed; it may run first for an
early signal, and the broad run is still due.
A deleted test file adds no test and never makes the result broad; tests that
still reference it are selected as usual. A test-file path (it matches
pytest's test-file patterns under the test paths) counts as deleted when it is
absent from the tree and the input mode reported it deleted or renamed away
(``--staged``, ``--diff``, ``--worktree``) or Git's ``HEAD`` contains it. Any
other absent test-file path (a typo, say) is unmapped.
Test paths are pytest's ``testpaths``; without them pytest searches the
repository root, and so does the selector (``norecursedirs`` and
``python_files`` still apply).
No-test zones: the record trees ``docs/``, ``context/``, ``workspace/``,
``architecture-documentation/`` and ``assets/``, root-level community files
(``README*``, ``LICENSE*``, ...), and documentation: ``references/`` at the
repository root and ``README*`` files at any depth. Only unmapped paths are
affected; a zone path a test reaches (for Markdown: reads, for code:
directly) still selects that test (for module code see Known limits).
``--format args`` prints pytest targets on one line: the selected files, the
test paths for ``broad``, and nothing (with a stderr note) for an empty
targeted set — a bare ``pytest $(...)`` would then run the whole suite. With
light-path lines the note says to run the light-path checks instead.
``--format json`` carries ``result``, ``tests``, ``reasons``, ``unmapped``,
``no_tests``, ``light_path``, ``removed_tests``, ``by_path`` (each changed
path's selected tests) and ``test_paths`` (the test paths, ``.`` for the
repository root; the targets ``args`` prints for ``broad``). ``--explain
PATH`` prints the reference chain of each test that reaches PATH over any
edge (for Markdown and code that includes tests the rules above do not
select); ``--map`` dumps every test's dependencies.

Each edge is direct or tree. A tree edge stands for a family of files: a repo
directory used as a tree (``copytree``/``glob``/``rglob``/``iterdir``/``walk``
or a call argument), a directory entry of a copy-loop tuple, a by-name load
below a directory, a wildcard that matches more than one file. Every other
edge is direct: imports, exact paths and path suffixes, shell tokens naming a
file, basenames, a narrowed variable file name, a wildcard matching one file.
The direct closure is the same search over direct edges only. For Markdown,
a ``glob``/``rglob`` in test code also counts as reading the files it matches.

How a test reaches a path (edges):
  * Imports, followed transitively through repo modules: absolute against the
    importing file's directory, the root, the test paths and directories test
    code puts on ``sys.path``, pytest's ``pythonpath`` and a root ``src/``, and,
    for an import that resolved nowhere else, the parent of each non-zone
    package directory named like its first segment; relative by package; ``importlib.import_module``
    and ``__import__`` with a constant name too.
  * File references, collected only at depth 0 (the test, its ``conftest.py``
    ancestry and support files under the configured test paths, or under
    ``tests/`` without a configuration) and depth 1 (repo
    modules and scripts depth-0 code uses directly). A path is repo-rooted
    when it derives from ``__file__`` or from a name matching ROOT, FRAMEWORK,
    REPO or CHECKOUT in any case: lowercase ``root``, ``repo``, ``framework``
    and ``checkout`` count too (see Known limits). Path text is carried through names per file
    (``D = ROOT / "a"`` then ``D / "b"`` is ``a/b``); a variable segment after
    a constant repo prefix matches one segment. A variable file name
    (``ROOT / "scripts" / script``) matches only the ``.py``/``.sh`` basenames
    the file names as string constants when all of these hold: the variable
    is a plain name, attribute or subscript (not a composed expression such as
    ``name + ".py"``); the path is not used as a directory (not an argument of
    ``copytree``/``walk``/``listdir``/``scandir``/``glob``, not the receiver of
    ``glob``/``rglob``/``iterdir``/``walk``/``listdir``/``scandir``) and is not
    followed by ``with_suffix``/``with_name``; and at least one named script
    exists under the constant prefix. Otherwise, and for a name-table value,
    it stays a one-segment wildcard. A repo directory used by
    ``copytree``/``glob``/``rglob``/``iterdir``/``walk`` or passed as a call
    argument stands for every file below it. Test code also maps constants
    containing '/', f-strings anchored at a top-level directory, copy-loop
    tuples of top-level entries, tuples of .py/.sh basenames, and a standalone
    .py/.sh basename constant that names exactly one repository file outside
    the no-test zones (a helper in another test module may run it). Module
    code maps repo-rooted paths, constants naming a file outside the zones, and
    anything resolving to a script; module f-strings are not edges.
  * Loading by name, at any depth: a repo directory and a literal basename in
    the same module map every file with that basename below that directory.
  * Shell scripts reached at depth <= 1: tokens naming ``.py``/``.sh`` files.

Known limits. They are covered where a path then maps to no test (``broad``),
by the commit hooks (plan validation's inputs) and by the broad run a
safety-floor change takes; a replay that shows another such miss adds a
cross-cutting entry:
  * Code a test reaches only through a tree edge (it copies the tree and
    runs the copy) does not select that test when another test reaches the
    code directly. Markdown a test reads only through module code, a copied
    tree or a wildcard path that is not a glob (a parametrized f-string, say)
    does not select that test.
  * Paths and module names computed from runtime values, including targets
    read from data files such as YAML, are not followed.
  * Files read by code two or more imports below a test are not followed (the
    depth limit), nor are inputs read only inside isolated subprocesses
    (``python3 -I`` or ``-E``). Plan validation's inputs (``CLAUDE.md``,
    ``AGENTS.md`` and other framework files) are missed both ways.
  * Narrowing a variable file name to the script names its file states can
    miss a test that passes other values through such a path: non-script
    parametrized values, a helper called from another file with a basename
    that is not unique, a path that a wrapper function uses as a directory.
  * Repo-rooted reads into the no-test zones from module code are not mapped:
    module code addresses the consumer project's documents.
  * A lowercase root-like name bound to a temporary directory over-selects, and
    it can also make an otherwise unmapped path look mapped (``targeted``
    where ``broad`` was due).
  * Import roots set only at runtime (``PYTHONPATH``, ``.pth`` files, packages
    installed outside the repository) are not followed. A module reached only
    that way is unmapped (``broad``), but it is missed when another test
    reaches it by another edge. Namespace packages (no ``__init__.py``) under
    a root that is neither ``src/`` nor a ``pythonpath`` entry are not followed
    either.
  * A package named like a standard-library module that sits directly on a
    primary base (the root, ``src/``, a ``pythonpath`` entry) picks up the
    stdlib imports of that name (over-selection). One on a fallback-only root
    is not reached by its importers: Python shadows it with the stdlib module.
Paths built on temporary or fixture bases in test code are not edges.

Exit codes: 0 result printed (also when the reader closes stdout early, as
``| head`` does); 2, with one stderr line, for an unreadable root, a Git
failure or unusable input (no changed paths, a path list that is not UTF-8, a
``pytest.ini`` that ``configparser`` rejects).
"""
from __future__ import annotations

import argparse
import ast
import configparser
import fnmatch
import json
import os
import posixpath
import re
import subprocess
import sys
import tomllib
from collections import deque
from collections.abc import Callable, Iterable, Iterator, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import NamedTuple

# ---------------------------------------------------------------------------
# Repository knowledge (the only forge-specific constants)
# ---------------------------------------------------------------------------

#: Record and scratch trees: unmapped paths there select nothing, and the copies
#: they hold never decide how a reference resolves.
ZONE_DIRS: tuple[str, ...] = (
    "docs/",
    "context/",
    "workspace/",
    "architecture-documentation/",
    "assets/",
)
#: Root-level community files that select nothing when unmapped.
ZONE_ROOT_FILES: tuple[str, ...] = (
    "README*",
    "LICENSE*",
    "CONTRIBUTING*",
    "CODE_OF_CONDUCT*",
    "SECURITY*",
)
#: Documentation that selects nothing when unmapped but resolves like any other
#: file, so a test that reaches it (a copied tree, a named constant) still maps it.
DOC_ZONE_DIRS: tuple[str, ...] = ("references/",)
#: Documentation file names, at any depth.
DOC_ZONE_FILES: tuple[str, ...] = ("README*",)
#: Root-level pytest configuration files: a change makes the result broad.
INFRA_CONFIG_FILES = frozenset({"pytest.ini", "pyproject.toml", "setup.cfg", "tox.ini"})
#: Paths the scan cannot follow: fnmatch pattern -> one-line reason.
#: Add an entry only when a replay or a test shows a by-name load no rule reaches.
CROSS_CUTTING: dict[str, str] = {}

# ---------------------------------------------------------------------------
# Scan vocabulary
# ---------------------------------------------------------------------------

#: Names treated as the repository root when no assignment tells otherwise.
ROOTISH = re.compile(r"(^|_)(ROOT|FRAMEWORK|REPO|CHECKOUT)(_|$)|^HERE$", re.IGNORECASE)
#: Path methods whose receiver stands for a directory tree.
TREE_METHODS = frozenset({"rglob", "glob", "iterdir", "walk"})
#: Directory use that keeps a variable file name a wildcard: the receiver of
#: these methods and the arguments of these calls (``shutil.copytree``,
#: ``os.walk``, ``os.listdir``, ``os.scandir``, ``glob.glob``) are trees or patterns.
DIR_USE_METHODS = TREE_METHODS | {"listdir", "scandir"}
DIR_USE_CALLS = frozenset({"copytree", "walk", "listdir", "scandir", "glob", "iglob"})
#: Path methods that append to or replace the last segment of their receiver.
REWRITE_METHODS = frozenset({"joinpath", "with_name", "with_suffix"})
#: Calls that build or wrap a path value (their arguments are part of the path).
PATH_BUILDERS = frozenset({
    "Path", "PurePath", "PosixPath", "PurePosixPath",
    "pathlib.Path", "pathlib.PurePath", "pathlib.PosixPath", "pathlib.PurePosixPath",
    "str", "os.fspath", "os.path.join", "posixpath.join", "os.path.dirname",
    "os.path.abspath", "os.path.realpath", "os.path.normpath", "os.path.expanduser",
})
#: Path methods that keep (or extend) the receiver's location.
PATH_METHODS = frozenset({
    "resolve", "absolute", "expanduser", "as_posix", "__fspath__",
    "joinpath", "with_name", "with_suffix",
})
#: Calls whose arguments are sys.path entries, never file references.
SYS_PATH_CALLS = frozenset({
    "sys.path.insert", "sys.path.append", "sys.path.extend", "sys.path.remove",
    "site.addsitedir",
})
DYNAMIC_IMPORTS = frozenset({"importlib.import_module", "import_module", "__import__"})
SCRIPT_SUFFIXES = (".py", ".sh")
#: A string constant that names a script file without a directory part.
SCRIPT_BASENAME = re.compile(r"[\w.-]+\.(?:py|sh)")
SHELL_TOKEN = re.compile(r"[A-Za-z0-9_./-]+\.(?:py|sh)(?![A-Za-z0-9_])")
SHELL_VARIABLE = re.compile(r"\$\{[^}]*\}|\$[A-Za-z_][A-Za-z0-9_]*")
#: Without ``testpaths`` pytest searches the rootdir recursively: '' is the root.
DEFAULT_TESTPATHS = ("",)
#: Without ``testpaths``, support files count as test code only under tests/;
#: the root would make every module test code and drop the module-code rules.
DEFAULT_SUPPORT_PATHS = ("tests",)
DEFAULT_PYTHON_FILES = ("test_*.py", "*_test.py")
DEFAULT_NORECURSE = ("*.egg", ".*", "_darcs", "build", "CVS", "dist", "node_modules", "venv", "{arch}")
WALK_SKIP_DIRS = frozenset({
    ".git", "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache",
    ".tox", ".venv", "venv", "node_modules",
})
_MAX_VARIANTS = 64
_FAR = 1 << 30


class SelectorError(Exception):
    """An input or Git problem: reported on stderr with exit code 2."""


def is_zone(path: str) -> bool:
    """True for a path inside a record zone (a directory gets a trailing '/').

    Record zones decide reference resolution as well as selection; see
    ``is_no_test_zone`` for the wider set that only decides selection.
    """
    if path.startswith(ZONE_DIRS):
        return True
    return "/" not in path and any(fnmatch.fnmatchcase(path, p) for p in ZONE_ROOT_FILES)


def is_no_test_zone(path: str) -> bool:
    """True when an unmapped path selects nothing: record zones and documentation."""
    if is_zone(path) or path.startswith(DOC_ZONE_DIRS):
        return True
    return any(fnmatch.fnmatchcase(posixpath.basename(path), p) for p in DOC_ZONE_FILES)


def _zone_dir(path: str) -> bool:
    """True when a file or directory text lies in (or is) a no-test zone."""
    return is_zone(path) or is_zone(path + "/")


def _has_wildcard(text: str) -> bool:
    return "*" in text or "?" in text


def _has_constant_segment(text: str) -> bool:
    """A pattern needs one segment that is not pure wildcard ('*' alone matches anything)."""
    return any(seg and seg.strip("*?") for seg in text.split("/"))


def _literal_prefix(text: str) -> str:
    """The segments before the first wildcard segment."""
    out: list[str] = []
    for seg in text.split("/"):
        if _has_wildcard(seg):
            break
        out.append(seg)
    return "/".join(out)


def _normalize(text: str) -> str | None:
    """Collapse '.', '..' and empty segments; None when the text climbs above the root."""
    out: list[str] = []
    for seg in text.split("/"):
        if seg in ("", "."):
            continue
        if seg == "..":
            if not out:
                return None
            out.pop()
            continue
        out.append(seg)
    return "/".join(out)


def _glob_regex(pattern: str, dir_ctx: bool) -> re.Pattern[str]:
    """Translate a repo glob ('*' one segment part, '**' any depth) to a regex."""
    parts = pattern.split("/")
    out: list[str] = []
    for i, seg in enumerate(parts):
        last = i == len(parts) - 1
        if seg == "**":
            out.append(".*" if last else "(?:[^/]+/)*")
            continue
        out.append("".join("[^/]*" if c == "*" else "[^/]" if c == "?" else re.escape(c) for c in seg))
        if not last:
            out.append("/")
    tail = "(?:/.*)?" if dir_ctx else ""
    return re.compile("".join(out) + tail + r"\Z")


def _plausible_path(text: str) -> bool:
    """Cheap filter: constants that cannot be repository paths are skipped."""
    if not text or len(text) > 240 or "://" in text:
        return False
    if text[0] in "/~-" or any(c.isspace() for c in text):
        return False
    return not any(c in text for c in "\0{}$%<>|\\")


def _dotted(node: ast.AST) -> str | None:
    """'os.path.join' for an attribute chain over a name; None otherwise."""
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        inner = _dotted(node.value)
        return f"{inner}.{node.attr}" if inner else None
    return None


def _const_str(node: ast.AST | None) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


def _fstring_text(values: Sequence[ast.AST]) -> str:
    """Constant parts of an f-string; each placeholder becomes '*'."""
    return "".join(c if (c := _const_str(v)) is not None else "*" for v in values)


def _call_name(call: ast.Call) -> str:
    """Last component of a call's dotted name ('copytree' for shutil.copytree)."""
    return (_dotted(call.func) or "").rsplit(".", 1)[-1]


# ---------------------------------------------------------------------------
# Pytest configuration
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PytestConfig:
    """The pytest settings that decide which files are tests.

    ``testpaths`` is where pytest collects (the root when none is configured).
    ``support_paths`` is where the selector treats every Python file as test
    code at depth 0: the configured ``testpaths``, else ``tests/``. Collected
    test files and conftest files are test code wherever they are.
    """

    testpaths: tuple[str, ...] = DEFAULT_TESTPATHS
    python_files: tuple[str, ...] = DEFAULT_PYTHON_FILES
    norecursedirs: tuple[str, ...] = DEFAULT_NORECURSE
    support_paths: tuple[str, ...] = DEFAULT_SUPPORT_PATHS
    pythonpath: tuple[str, ...] = ()

    @classmethod
    def read(cls, root: Path) -> PytestConfig:
        """Read the first pytest config in pytest's own order; defaults otherwise."""
        section = _pytest_section(root)
        if section is None:
            return cls()

        def words(key: str) -> tuple[str, ...] | None:
            value = section.get(key)
            if value is None:
                return None
            items = value if isinstance(value, list) else str(value).split()
            return tuple(str(v) for v in items)

        testpaths = tuple(
            "" if n == "." else n
            for n in (_normalize(p) for p in (words("testpaths") or ()))
            if n is not None
        )
        return cls(
            testpaths=testpaths or DEFAULT_TESTPATHS,
            python_files=words("python_files") or DEFAULT_PYTHON_FILES,
            norecursedirs=words("norecursedirs") or DEFAULT_NORECURSE,
            support_paths=testpaths or DEFAULT_SUPPORT_PATHS,
            pythonpath=tuple(
                "" if n == "." else n
                for n in (_normalize(p) for p in (words("pythonpath") or ()))
                if n is not None
            ),
        )

    @staticmethod
    def _path_of(rel: str, paths: tuple[str, ...]) -> str | None:
        """The entry of paths containing rel (glob entries allowed; '' is the root)."""
        for tp in paths:
            if tp == "":
                return ""
            if _has_wildcard(tp):
                parts = rel.split("/")
                for i in range(1, len(parts)):
                    if fnmatch.fnmatchcase("/".join(parts[:i]), tp):
                        return "/".join(parts[:i])
            elif rel.startswith(tp + "/"):
                return tp
        return None

    def testpath_of(self, rel: str) -> str | None:
        """The test path containing rel."""
        return self._path_of(rel, self.testpaths)

    def in_testpaths(self, rel: str) -> bool:
        return self.testpath_of(rel) is not None

    def in_support_paths(self, rel: str) -> bool:
        """Under the configured test paths, or under tests/ without them."""
        return self._path_of(rel, self.support_paths) is not None

    def is_test_code(self, rel: str) -> bool:
        """Depth-0 code: under the support paths, a collected test file or a conftest."""
        if self._path_of(rel, self.support_paths) is not None or self.is_test_file(rel):
            return True
        return posixpath.basename(rel) == "conftest.py" and self.in_testpaths(rel)

    def is_test_file(self, rel: str) -> bool:
        """Collected by pytest: under a test path, matching name, no skipped directory."""
        tp = self.testpath_of(rel)
        if tp is None:
            return False
        name = posixpath.basename(rel)
        if not any(fnmatch.fnmatchcase(name, p) for p in self.python_files):
            return False
        inner = rel[len(tp) + 1 if tp else 0:].split("/")[:-1]
        return not any(
            d == "__pycache__" or any(fnmatch.fnmatchcase(d, p) for p in self.norecursedirs)
            for d in inner
        )


def _pytest_section(root: Path) -> dict[str, object] | None:
    """pytest.ini [pytest], pyproject [tool.pytest.ini_options], tox.ini, setup.cfg."""
    ini = root / "pytest.ini"
    if ini.is_file():
        parser = configparser.ConfigParser(interpolation=None)
        try:
            parser.read(ini, encoding="utf-8")
        except configparser.Error as exc:
            # pytest reads this file first, so a guess from another file would mislead.
            raise SelectorError(f"malformed pytest.ini: {' '.join(str(exc).split())}") from exc
        return dict(parser["pytest"]) if parser.has_section("pytest") else {}
    pyproject = root / "pyproject.toml"
    if pyproject.is_file():
        try:
            data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
        except (OSError, tomllib.TOMLDecodeError):
            data = {}
        options = data.get("tool", {}).get("pytest", {}).get("ini_options")
        if isinstance(options, dict):
            return options
    for name, sect in (("tox.ini", "pytest"), ("setup.cfg", "tool:pytest")):
        path = root / name
        if path.is_file():
            parser = configparser.ConfigParser(interpolation=None)
            try:
                parser.read(path, encoding="utf-8")
            except configparser.Error:
                continue
            if parser.has_section(sect):
                return dict(parser[sect])
    return None


# ---------------------------------------------------------------------------
# Repository index
# ---------------------------------------------------------------------------


def _git(root: Path, *args: str) -> str:
    """Run a read-only git command in root; SelectorError on failure."""
    cmd = ["git", "--no-optional-locks", "-C", str(root), *args]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    except OSError as exc:
        raise SelectorError(f"cannot run git: {exc}") from exc
    if proc.returncode != 0:
        first = (proc.stderr.strip().splitlines() or ["no output"])[0]
        raise SelectorError(f"git {' '.join(args[:2])} failed: {first}")
    return proc.stdout


def _list_files(root: Path) -> list[str]:
    """Tracked and untracked, non-ignored files; a plain walk without Git."""
    try:
        out = _git(root, "ls-files", "-co", "--exclude-standard", "-z")
        return sorted(f for f in set(out.split("\0")) if f and (root / f).is_file())
    except SelectorError:
        pass
    found: list[str] = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in WALK_SKIP_DIRS and not d.startswith(".venv")]
        rel_dir = Path(dirpath).relative_to(root).as_posix()
        for name in filenames:
            found.append(name if rel_dir == "." else f"{rel_dir}/{name}")
    return sorted(found)


class RepoIndex:
    """Every repository file plus the changed paths, with the lookups the rules use.

    Record files are indexed too: a test's explicit reference into a zone maps.
    Suffix and basename lookups only see files outside the zones, so copies kept
    as evidence never decide whether a reference resolves.
    """

    def __init__(self, root: Path, extra: Iterable[str] = ()) -> None:
        self.root = root
        self.existing: list[str] = _list_files(root)
        self.files: set[str] = set(self.existing) | set(extra)
        self.dirs: set[str] = set()
        self.top_dirs: set[str] = set()
        self._below: dict[str, list[str]] = {}
        self._by_base: dict[str, list[str]] = {}
        self._dirs_by_base: dict[str, list[str]] = {}
        for rel in sorted(self.files):
            parts = rel.split("/")
            if len(parts) > 1:
                self.top_dirs.add(parts[0])
            for i in range(1, len(parts)):
                d = "/".join(parts[:i])
                if d not in self.dirs:
                    self.dirs.add(d)
                    if not is_zone(d + "/"):
                        self._dirs_by_base.setdefault(parts[i - 1], []).append(d)
                self._below.setdefault(d, []).append(rel)
            if not is_zone(rel):
                self._by_base.setdefault(parts[-1], []).append(rel)

    def below(self, directory: str) -> list[str]:
        return self._below.get(directory, [])

    def by_base(self, name: str) -> list[str]:
        """Files outside the zones with this basename."""
        return self._by_base.get(name, [])

    def zone_filter(self, hits: Iterable[str], prefix: str, zone_ok: bool) -> list[str]:
        """Keep zone hits only when the reference itself names a zone path."""
        if zone_ok and _zone_dir(prefix):
            return list(hits)
        return [h for h in hits if not is_zone(h)]

    def suffix(self, text: str, dir_ctx: bool) -> list[str]:
        """Non-zone files (or, for directory use, files below dirs) ending in /text."""
        base = text.rsplit("/", 1)[-1]
        tail = "/" + text
        hits = [f for f in self.by_base(base) if f.endswith(tail)]
        if dir_ctx:
            for d in self._dirs_by_base.get(base, []):
                if d.endswith(tail):
                    hits.extend(f for f in self.below(d) if not is_zone(f))
        return hits

    def glob(self, pattern: str, dir_ctx: bool) -> list[str]:
        """Files matching a repo-anchored pattern (directory use includes files below)."""
        rx = _glob_regex(pattern, dir_ctx)
        first = pattern.split("/", 1)[0]
        if not _has_wildcard(first) and first in self.dirs:
            pool: Iterable[str] = self.below(first)
        else:
            pool = self.files
        return sorted(f for f in pool if rx.match(f))

    def resolve_path(self, text: str, dir_ctx: bool, zone_ok: bool) -> list[str]:
        """Exact file, directory (for directory use), pattern, else path suffix."""
        if _has_wildcard(text):
            if not _has_constant_segment(text):
                return []
            prefix = _literal_prefix(text)
            return self.zone_filter(self.glob(text, dir_ctx), prefix, zone_ok)
        if text in self.files:
            return self.zone_filter([text], text, zone_ok)
        if text in self.dirs:
            return self.zone_filter(self.below(text), text, zone_ok) if dir_ctx else []
        if "/" in text:
            return self.suffix(text, dir_ctx)
        return []


# ---------------------------------------------------------------------------
# Per-file facts (one parse per file)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ImportSpec:
    """One import statement or constant dynamic import."""

    module: str
    names: tuple[str, ...]
    level: int
    line: int

    def label(self) -> str:
        dots = "." * self.level
        if self.names:
            return f"from {dots}{self.module} import {', '.join(self.names)}"
        return f"import {dots}{self.module}"


@dataclass(frozen=True)
class Ref:
    """One file reference and the policy that decides how it resolves.

    Policies: ``test-repo`` (repo-rooted path in test code), ``test-const``
    (constant in test code), ``module-repo`` (repo-rooted path in a module),
    ``module-const`` (constant with '/' in a module), ``module-tail`` (constant
    tail of a path on an unknown base in a module), ``shell`` (token in a shell
    script), ``tuple`` (literal tuple/list in test code). ``enumerates``: the
    path is the receiver of ``glob``/``rglob``, which lists the files it matches.
    """

    policy: str
    text: str
    line: int
    dir_ctx: bool = False
    items: tuple[str, ...] = ()
    enumerates: bool = False

    def key(self) -> tuple[str, str, bool, tuple[str, ...], bool]:
        return (self.policy, self.text, self.dir_ctx, self.items, self.enumerates)


@dataclass(frozen=True)
class FileFacts:
    """Everything the rules need from one Python file."""

    imports: tuple[ImportSpec, ...] = ()
    refs: tuple[Ref, ...] = ()
    syspath_dirs: tuple[str, ...] = ()
    channel_dirs: tuple[str, ...] = ()
    literals: frozenset[str] = frozenset()


@dataclass(frozen=True)
class _Val:
    """A path value: 'repo' texts are relative to the repository root, 'const'
    texts are constant strings with no known base. '*' marks a variable segment.
    """

    anchor: str
    texts: frozenset[str]


class _Scanner:
    """Collect imports, sys.path entries and file references from one parsed file.

    ``test_code`` selects the depth-0 rules (files under the test paths); other
    files get the module rules. Path text flows through a per-file name table so
    ``D = ROOT / "a"`` followed by ``D / "b"`` yields ``a/b``.

    A variable operand is one ``*`` segment. When it is the file name of a path
    with a constant prefix (``ROOT / "scripts" / script``), it matches only the
    ``.py``/``.sh`` basenames the file names as string constants, provided the
    premise of that narrowing holds (see ``_names_file`` and ``_narrows``).
    Name-table values keep the wildcard, because a later ``/`` may extend them.
    ``exists`` answers whether a path text resolves to a repository file.
    """

    def __init__(self, rel: str, tree: ast.Module, test_code: bool,
                 exists: Callable[[str], bool] | None = None) -> None:
        self.rel = rel
        self.tree = tree
        self.test_code = test_code
        self._exists: Callable[[str], bool] = exists or (lambda _text: False)
        self.parent: dict[ast.AST, ast.AST] = {}
        script_names: set[str] = set()
        for node in ast.walk(tree):
            for child in ast.iter_child_nodes(node):
                self.parent[child] = node
            const = _const_str(node)
            if const is not None and SCRIPT_BASENAME.fullmatch(const):
                script_names.add(const)
        self.script_names = frozenset(script_names)
        self.path_names: dict[str, set[str]] = {}
        self.const_names: dict[str, set[str]] = {}
        self.syspath_nodes: set[ast.AST] = set()
        self.syspath_dirs: set[str] = set()
        self._narrow = False
        self._build_name_tables()
        self._mark_syspath()
        self._narrow = True

    # -- name tables --------------------------------------------------------

    def _build_name_tables(self) -> None:
        """Fixpoint over assignments and loop targets: name -> repo paths / constants."""
        bindings: list[tuple[str, ast.AST, bool]] = []
        for node in ast.walk(self.tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    self._bind(target, node.value, False, bindings)
            elif isinstance(node, (ast.AnnAssign, ast.NamedExpr)) and node.value is not None:
                self._bind(node.target, node.value, False, bindings)
            elif isinstance(node, (ast.For, ast.AsyncFor, ast.comprehension)):
                self._bind(node.target, node.iter, True, bindings)
        for _ in range(4):
            changed = False
            for name, value, iterating in bindings:
                for item in self._iter_items(value) if iterating else [value]:
                    val = self.eval_path(item)
                    # Only a path with a constant leading segment (or the root) names
                    # a repo location; '*' or '*/x' as a base would match anything.
                    texts = {t for t in val.texts if not _has_wildcard(t.split("/", 1)[0])} if val else set()
                    if val is not None and val.anchor == "repo" and texts:
                        known = self.path_names.setdefault(name, set())
                        if not texts <= known:
                            known |= texts
                            changed = True
                    const = _const_str(item)
                    if const is not None:
                        known = self.const_names.setdefault(name, set())
                        if const not in known:
                            known.add(const)
                            changed = True
            if not changed:
                break

    @staticmethod
    def _bind(target: ast.AST, value: ast.AST, iterating: bool,
              out: list[tuple[str, ast.AST, bool]]) -> None:
        if isinstance(target, ast.Name):
            out.append((target.id, value, iterating))
        elif (not iterating and isinstance(target, (ast.Tuple, ast.List))
              and isinstance(value, (ast.Tuple, ast.List)) and len(target.elts) == len(value.elts)):
            for t, v in zip(target.elts, value.elts, strict=True):
                _Scanner._bind(t, v, False, out)

    def _iter_items(self, node: ast.AST) -> list[ast.AST]:
        """The elements a loop over node yields, as far as they are literal."""
        if isinstance(node, (ast.Tuple, ast.List, ast.Set)):
            return list(node.elts)
        if isinstance(node, ast.Call) and _dotted(node.func) in ("sorted", "list", "tuple", "reversed") and node.args:
            return self._iter_items(node.args[0])
        return [node]

    # -- sys.path -----------------------------------------------------------

    def _mark_syspath(self) -> None:
        """sys.path entries extend import resolution and are never file references."""
        for node in ast.walk(self.tree):
            entries: list[ast.AST] = []
            if isinstance(node, ast.Call):
                name = _dotted(node.func) or ""
                if name in SYS_PATH_CALLS or name.endswith(".syspath_prepend"):
                    entries = [*node.args, *(k.value for k in node.keywords)]
            elif isinstance(node, ast.Compare):
                if any(_dotted(c) == "sys.path" for c in [node.left, *node.comparators]):
                    entries = [node]
            elif isinstance(node, (ast.Assign, ast.AugAssign)):
                targets = node.targets if isinstance(node, ast.Assign) else [node.target]
                for t in targets:
                    if _dotted(t) == "sys.path" or (isinstance(t, ast.Subscript) and _dotted(t.value) == "sys.path"):
                        entries = [node.value]
            for entry in entries:
                for sub in ast.walk(entry):
                    self.syspath_nodes.add(sub)
                for item in self._iter_items(entry):
                    val = self.eval_path(item)
                    if val is not None and val.anchor == "repo":
                        self.syspath_dirs |= {t for t in val.texts if not _has_wildcard(t)}

    # -- path evaluation ----------------------------------------------------

    def eval_path(self, node: ast.AST) -> _Val | None:
        """The path value of an expression, or None when it is no repo/constant path.

        A call the evaluator does not model counts as the repository root when a
        direct argument is a repo path (``Path(os.environ.get("X", ROOT))``,
        ``make_copy(ROOT)``): its constant tail still maps. Nothing else falls
        back, so unrelated names never inherit repo-rootedness.
        """
        if isinstance(node, ast.Constant):
            return _Val("const", frozenset({node.value})) if isinstance(node.value, str) else None
        if isinstance(node, ast.JoinedStr):
            return self._eval_fstring(node)
        if isinstance(node, ast.Name):
            if node.id == "__file__":
                return _Val("repo", frozenset({self.rel}))
            if node.id in self.path_names:
                return _Val("repo", frozenset(self.path_names[node.id]))
            if ROOTISH.search(node.id):
                return _Val("repo", frozenset({""}))
            if node.id in self.const_names:
                return _Val("const", frozenset(self.const_names[node.id]))
            return None
        if isinstance(node, ast.Attribute):
            if node.attr == "parent":
                return self._up(self.eval_path(node.value), 1)
            if ROOTISH.search(node.attr):
                return _Val("repo", frozenset({""}))
        elif isinstance(node, ast.Subscript):
            value, index = node.value, node.slice
            if (isinstance(value, ast.Attribute) and value.attr == "parents"
                    and isinstance(index, ast.Constant) and isinstance(index.value, int)):
                return self._up(self.eval_path(value.value), index.value + 1)
            if isinstance(value, ast.Name) and value.id in self.path_names:
                return _Val("repo", frozenset(self.path_names[value.id]))  # element of a path list
        elif isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div):
            return self._join(self.eval_path(node.left), [node.right], self._names_file(node))
        elif isinstance(node, ast.Call):
            return self._eval_call(node) or self._call_on_repo_path(node)
        elif isinstance(node, (ast.ListComp, ast.SetComp, ast.GeneratorExp)):
            return self.eval_path(node.elt)
        elif isinstance(node, ast.IfExp):
            return self._union([node.body, node.orelse])
        elif isinstance(node, ast.BoolOp):
            return self._union(node.values)
        return None

    def _call_on_repo_path(self, node: ast.Call) -> _Val | None:
        """An unmodelled call with a repo path as a direct argument: the root."""
        for arg in [*node.args, *(k.value for k in node.keywords)]:
            val = self.eval_path(arg)
            if val is not None and val.anchor == "repo":
                return _Val("repo", frozenset({""}))
        return None

    def _eval_call(self, node: ast.Call) -> _Val | None:
        name = _dotted(node.func)
        if name in PATH_BUILDERS:
            if not node.args:
                return None
            if name == "os.path.dirname":
                return self._up(self.eval_path(node.args[0]), 1)
            return self._join(self.eval_path(node.args[0]), node.args[1:], self._names_file(node))
        if isinstance(node.func, ast.Attribute) and node.func.attr in PATH_METHODS:
            receiver = self.eval_path(node.func.value)
            method = node.func.attr
            if method == "joinpath":
                return self._join(receiver, node.args, self._names_file(node))
            if method == "with_name" and node.args:
                return self._join(self._up(receiver, 1), node.args[:1], self._names_file(node))
            if method == "with_suffix" and node.args and receiver is not None:
                suffix = _const_str(node.args[0])
                if suffix is None:
                    return receiver
                texts = {posixpath.splitext(t)[0] + suffix for t in receiver.texts if t}
                return _Val(receiver.anchor, frozenset(texts)) if texts else receiver
            return receiver
        return None

    def _eval_fstring(self, node: ast.JoinedStr) -> _Val | None:
        """Test code: f"{ROOT}/a/{x}" -> repo 'a/*'. Otherwise const text with '*'."""
        parts = list(node.values)
        head: frozenset[str] | None = None
        if self.test_code and len(parts) > 1 and isinstance(parts[0], ast.FormattedValue):
            val = self.eval_path(parts[0].value)
            if val is not None and val.anchor == "repo" and _fstring_text(parts[1:]).startswith("/"):
                head, parts = val.texts, parts[1:]
        rest = _fstring_text(parts)
        if head is None:
            return _Val("const", frozenset({rest}))
        texts = {_normalize((h + rest if h else rest).lstrip("/")) for h in head}
        return _Val("repo", frozenset(t if t is not None else "" for t in texts))

    def _union(self, nodes: Sequence[ast.AST]) -> _Val | None:
        vals = [v for v in (self.eval_path(n) for n in nodes) if v is not None]
        if not vals:
            return None
        anchor = "repo" if any(v.anchor == "repo" for v in vals) else "const"
        return _Val(anchor, frozenset().union(*(v.texts for v in vals if v.anchor == anchor)))

    @staticmethod
    def _up(val: _Val | None, levels: int) -> _Val | None:
        """Parent directory, `levels` times; above the root counts as the root."""
        if val is None:
            return None
        texts: set[str] = set()
        for text in val.texts:
            segs = text.split("/") if text else []
            if levels <= len(segs):
                texts.add("/".join(segs[: len(segs) - levels]))
            elif val.anchor == "repo":
                texts.add("")
        return _Val(val.anchor, frozenset(texts)) if texts else None

    def _names_file(self, node: ast.AST) -> bool:
        """True when node's path value ends in a file name that narrowing may restrict.

        Wrappers that keep the location (``str()``, ``Path()``, ``.resolve()``)
        are looked through. False when a later operation may change the last
        segment (a further ``/``, ``joinpath`` or path-builder argument, string
        arithmetic, an f-string, ``with_name``, ``with_suffix``) or uses the
        path as a directory (the receiver of a tree method, ``listdir`` or
        ``scandir``; an argument of ``copytree``, ``walk``, ``listdir``,
        ``scandir`` or ``glob``): a variable there need not be a script name.
        Always False while the name tables are built.
        """
        if not self._narrow:
            return False
        cur = node
        while True:
            p = self.parent.get(cur)
            if isinstance(p, (ast.BinOp, ast.FormattedValue, ast.JoinedStr)):
                return False
            if isinstance(p, ast.Attribute) and p.value is cur:
                if p.attr in DIR_USE_METHODS or p.attr in REWRITE_METHODS:
                    return False
                call = self.parent.get(p)
                if p.attr in PATH_METHODS and isinstance(call, ast.Call) and call.func is p:
                    cur = call
                    continue
                return True
            if isinstance(p, ast.keyword):
                call = self.parent.get(p)
                return not (isinstance(call, ast.Call) and _call_name(call) in DIR_USE_CALLS)
            if isinstance(p, ast.Call) and cur is not p.func:
                if _call_name(p) in DIR_USE_CALLS:
                    return False
                if _dotted(p.func) in PATH_BUILDERS:
                    if p.args and p.args[0] is cur and len(p.args) > 1:
                        return False
                    cur = p
                    continue
            return True

    def _narrows(self, node: ast.AST, heads: set[str]) -> bool:
        """The rest of the narrowing premise for a file-name operand after heads.

        The operand is a plain name, attribute or subscript (a composed
        expression such as ``name + ".py"`` can build any name), and at least
        one script basename the file names exists under one of the prefixes
        that is constant (a prefix with a wildcard segment does not qualify).
        """
        if not self.script_names or not isinstance(node, (ast.Name, ast.Attribute, ast.Subscript)):
            return False
        return any(self._exists(f"{h}/{n}") for h in heads if not _has_wildcard(h) for n in self.script_names)

    def _piece(self, node: ast.AST, file_heads: set[str]) -> set[str]:
        """The texts one path operand can take; a variable is one '*' segment.

        ``file_heads``: the constant prefixes when the operand is the path's
        file name (empty otherwise); a variable there matches only the script
        basenames the file names when ``_narrows`` holds.
        """
        const = _const_str(node)
        if const is not None:
            return {const}
        if isinstance(node, ast.JoinedStr):
            return {_fstring_text(node.values)}
        if isinstance(node, ast.Name) and node.id in self.const_names:
            return set(self.const_names[node.id]) | {"*"}
        if file_heads and self._narrows(node, file_heads):
            return set(self.script_names)
        return {"*"}

    def _join(self, base: _Val | None, operands: Sequence[ast.AST], ends: bool = False) -> _Val | None:
        """Append operands to base; ``ends``: the last operand is the file name."""
        if base is None:
            return None
        texts = set(base.texts)
        for i, operand in enumerate(operands):
            last = ends and i == len(operands) - 1
            joined: set[str] = set()
            for prefixed in (False, True):
                heads = {t for t in texts if bool(t) is prefixed}
                if not heads:
                    continue
                alts = self._piece(operand, heads if last and prefixed else set())
                if len(texts) * len(alts) > _MAX_VARIANTS:
                    alts = {"*"}
                joined |= {f"{t}/{a.strip('/')}" if t else a.strip("/") for t in heads for a in alts}
            texts = joined
        out: set[str] = set()
        for text in texts:
            norm = _normalize(text)
            if norm is not None:
                out.add(norm)
            elif base.anchor == "repo":
                out.add("")
        return _Val(base.anchor, frozenset(out)) if out else None

    # -- reference collection ----------------------------------------------

    def _path_shaped(self, node: ast.AST) -> bool:
        if isinstance(node, ast.Name):
            return isinstance(node.ctx, ast.Load)
        if isinstance(node, ast.Constant):
            return isinstance(node.value, str)
        if isinstance(node, ast.JoinedStr):
            return True
        if isinstance(node, ast.BinOp):
            return isinstance(node.op, ast.Div)
        if isinstance(node, ast.Attribute):
            return node.attr == "parent" or bool(ROOTISH.search(node.attr))
        if isinstance(node, ast.Subscript):
            return isinstance(node.value, ast.Attribute) and node.value.attr == "parents"
        if isinstance(node, ast.Call):
            if _dotted(node.func) in PATH_BUILDERS:
                return True
            return isinstance(node.func, ast.Attribute) and node.func.attr in PATH_METHODS
        return False

    def _consumed(self, node: ast.AST) -> bool:
        """True when node is an operand of a larger path expression (evaluated there)."""
        p = self.parent.get(node)
        if p is None:
            return False
        if isinstance(p, ast.BinOp) and isinstance(p.op, ast.Div):
            return True
        if isinstance(p, (ast.JoinedStr, ast.FormattedValue)):
            return True
        if isinstance(p, ast.Call):
            return node is p.func or (_dotted(p.func) in PATH_BUILDERS and node in p.args)
        if isinstance(p, ast.keyword):
            call = self.parent.get(p)
            return isinstance(call, ast.Call) and _dotted(call.func) in PATH_BUILDERS
        if isinstance(p, ast.Attribute) and p.value is node:
            return p.attr in PATH_METHODS or p.attr in ("parent", "parents")
        if isinstance(p, ast.Subscript) and p.value is node:
            return isinstance(node, ast.Attribute) and node.attr == "parents"
        return False

    def _context(self, node: ast.AST) -> tuple[bool, str | None, bool]:
        """(used as a directory, glob pattern of a tree method, enumerated by
        ``glob``/``rglob``) for a maximal path."""
        p = self.parent.get(node)
        if isinstance(p, ast.Attribute) and p.value is node and p.attr in TREE_METHODS:
            call = self.parent.get(p)
            if isinstance(call, ast.Call) and call.func is p:
                pattern = _const_str(call.args[0]) if call.args else None
                enumerates = p.attr in ("glob", "rglob")
                if p.attr == "rglob" and pattern is not None:
                    return True, "**/" + pattern, enumerates
                if p.attr == "glob" and pattern is not None:
                    return True, pattern, enumerates
                return True, None, enumerates
        child = node
        while isinstance(p, (ast.List, ast.Tuple, ast.Set, ast.Starred)):
            child, p = p, self.parent.get(p)
        if isinstance(p, ast.Call) and child is not p.func:
            return True, None, False
        return isinstance(p, ast.keyword), None, False

    def _module_tail(self, node: ast.BinOp) -> str | None:
        """Constant tail of `base / "a" / "b.py"` on an unknown base (module code)."""
        ops: list[ast.AST] = []
        cur: ast.AST = node
        while isinstance(cur, ast.BinOp) and isinstance(cur.op, ast.Div):
            ops.append(cur.right)
            cur = cur.left
        consts = [_const_str(o) for o in reversed(ops)]
        if not consts or any(c is None for c in consts):
            return None
        return _normalize("/".join(c.strip("/") for c in consts if c is not None))

    def _refs_for(self, node: ast.AST, val: _Val, out: list[Ref]) -> None:
        dir_ctx, pattern, enumerates = self._context(node)
        line = getattr(node, "lineno", 0)
        for raw in sorted(val.texts):
            if val.anchor == "repo":
                text = f"{raw}/{pattern}" if raw and pattern else (pattern or raw)
                if not text:
                    continue
                out.append(Ref("test-repo" if self.test_code else "module-repo", text, line, dir_ctx,
                               enumerates=enumerates))
                continue
            text = raw.split("::", 1)[0]
            while text.startswith("./"):
                text = text[2:]
            text = text.rstrip("/")
            if not _plausible_path(text):
                continue
            if self.test_code:
                out.append(Ref("test-const", text, line, dir_ctx and "/" in text))
            elif "/" in text:
                out.append(Ref("module-const", text, line))

    def collect(self) -> FileFacts:
        imports: list[ImportSpec] = []
        refs: list[Ref] = []
        channel_dirs: set[str] = set()
        literals: set[str] = set()
        for node in ast.walk(self.tree):
            if isinstance(node, ast.Import):
                imports.extend(ImportSpec(a.name, (), 0, node.lineno) for a in node.names)
                continue
            if isinstance(node, ast.ImportFrom):
                names = tuple(a.name for a in node.names if a.name != "*")
                imports.append(ImportSpec(node.module or "", names, node.level, node.lineno))
                continue
            if isinstance(node, ast.Call):
                spec = self._dynamic_import(node)
                if spec is not None:
                    imports.append(spec)
            if node in self.syspath_nodes:
                continue
            const = _const_str(node)
            if const is not None and "/" not in const and _plausible_path(const) and len(const) <= 128:
                literals.add(const)
            if (self.test_code and isinstance(node, (ast.Tuple, ast.List, ast.Set))
                    and not isinstance(getattr(node, "ctx", None), ast.Store)):
                items = [_const_str(e) for e in node.elts]
                if len(items) >= 2 and all(i is not None for i in items):
                    refs.append(Ref("tuple", "", node.lineno, items=tuple(i for i in items if i is not None)))
            if not self._path_shaped(node) or self._consumed(node):
                continue
            if isinstance(node, ast.JoinedStr) and not self.test_code:
                continue  # module f-strings address the consumer project, not the repo
            val = self.eval_path(node)
            if val is None:
                if not self.test_code and isinstance(node, ast.BinOp):
                    tail = self._module_tail(node)
                    if tail:
                        refs.append(Ref("module-tail", tail, node.lineno))
                continue
            self._refs_for(node, val, refs)
            if val.anchor == "repo":
                channel_dirs |= {p for p in (_literal_prefix(t) for t in val.texts) if p}
        for texts in self.path_names.values():
            channel_dirs |= {p for p in (_literal_prefix(t) for t in texts) if p}
        unique: dict[tuple[str, str, bool, tuple[str, ...], bool], Ref] = {}
        for ref in refs:
            unique.setdefault(ref.key(), ref)
        return FileFacts(
            imports=tuple(imports),
            refs=tuple(unique.values()),
            syspath_dirs=tuple(sorted(self.syspath_dirs)),
            channel_dirs=tuple(sorted(channel_dirs)),
            literals=frozenset(literals),
        )

    @staticmethod
    def _dynamic_import(node: ast.Call) -> ImportSpec | None:
        """importlib.import_module("a.b") / __import__("a") with a constant name."""
        if _dotted(node.func) not in DYNAMIC_IMPORTS or not node.args:
            return None
        name = _const_str(node.args[0])
        if not name:
            return None
        level = len(name) - len(name.lstrip("."))
        if level:
            package = next((_const_str(k.value) for k in node.keywords if k.arg == "package"), None)
            if package is None and len(node.args) > 1:
                package = _const_str(node.args[1])
            if not package:
                return None
            parts = package.split(".")
            keep = parts[: len(parts) - (level - 1)] if level > 1 else parts
            name = ".".join(keep + ([name[level:]] if name[level:] else []))
        return ImportSpec(name, (), 0, node.lineno)


# ---------------------------------------------------------------------------
# Reference map: test -> dependencies
# ---------------------------------------------------------------------------


class Edge(NamedTuple):
    """How a dependency was first reached (for --explain)."""

    parent: str | None
    detail: str


@dataclass
class ReferenceMap:
    """Static dependency closure of every test file in a repository."""

    root: Path
    extra: Iterable[str] = ()
    index: RepoIndex = field(init=False)
    config: PytestConfig = field(init=False)
    tests: list[str] = field(init=False)

    def __post_init__(self) -> None:
        self.index = RepoIndex(self.root, self.extra)
        self.config = PytestConfig.read(self.root)
        self.tests = [f for f in self.index.existing if self.config.is_test_file(f)]
        self._facts: dict[str, FileFacts | None] = {}
        self._kinds: dict[str, str | None] = {}
        self._resolved: dict[tuple[str, str, bool, tuple[str, ...], bool], tuple[tuple[str, bool], ...]] = {}
        self._out: dict[tuple[str, bool], tuple[tuple[str, str, bool, bool], ...]] = {}
        self._closures: dict[str, dict[str, Edge]] = {}
        self._direct_closures: dict[str, frozenset[str]] = {}
        self._own_reads: dict[str, frozenset[str]] = {}
        self._inverse: dict[str, set[str]] | None = None
        self._direct_inverse: dict[str, set[str]] | None = None
        self._reads_inverse: dict[str, set[str]] | None = None
        bases: set[str] = set()
        for rel in self.index.existing:
            if rel.endswith(".py") and self.config.is_test_code(rel):
                facts = self.facts(rel)
                if facts is not None:
                    bases.update(facts.syspath_dirs)
        self._test_syspath = sorted(d for d in bases if d in self.index.dirs or d == "")
        self._pkg_roots: dict[str, list[str]] | None = None

    # -- files --------------------------------------------------------------

    def kind(self, rel: str) -> str | None:
        """'python', 'shell' or None; extensionless scripts by their shebang."""
        if rel not in self._kinds:
            kind: str | None = None
            if rel.endswith(".py"):
                kind = "python"
            elif rel.endswith(".sh"):
                kind = "shell"
            elif "." not in posixpath.basename(rel):
                try:
                    with (self.root / rel).open("rb") as fh:
                        first = fh.readline(200)
                except OSError:
                    first = b""
                if first.startswith(b"#!"):
                    kind = "python" if b"python" in first else "shell" if b"sh" in first else None
            self._kinds[rel] = kind
        return self._kinds[rel]

    def facts(self, rel: str) -> FileFacts | None:
        """Parse a Python file once; unparsable files warn and contribute nothing."""
        if rel not in self._facts:
            path = self.root / rel
            facts: FileFacts | None = None
            if path.is_file():
                try:
                    tree = ast.parse(path.read_bytes(), filename=rel)
                    facts = _Scanner(rel, tree, self.config.is_test_code(rel), self._exists).collect()
                except (SyntaxError, ValueError, OSError, RecursionError) as exc:
                    print(f"select_tests: warning: cannot parse {rel}: {exc.__class__.__name__}; skipped",
                          file=sys.stderr)
            self._facts[rel] = facts
        return self._facts[rel]

    # -- resolution ---------------------------------------------------------

    def _exists(self, text: str) -> bool:
        """True when a path text names at least one repository file."""
        return bool(self.index.resolve_path(text, False, zone_ok=True))

    def _unique_script(self, name: str) -> list[str]:
        """A bare .py/.sh basename that names exactly one file outside the no-test
        zones: a helper in another test module may run that script by name."""
        if not SCRIPT_BASENAME.fullmatch(name):
            return []
        hits = [h for h in self.index.by_base(name) if not is_no_test_zone(h)]
        return hits if len(hits) == 1 else []

    def resolve(self, ref: Ref) -> tuple[tuple[str, bool], ...]:
        """(file, direct) pairs a reference reaches; a file reached both ways is direct."""
        key = ref.key()
        if key not in self._resolved:
            merged: dict[str, bool] = {}
            for hit, direct in self._resolve(ref):
                merged[hit] = merged.get(hit, False) or direct
            self._resolved[key] = tuple(merged.items())
        return self._resolved[key]

    def _scripts(self, hits: Iterable[str]) -> list[str]:
        return [h for h in hits if self.kind(h) is not None]

    @staticmethod
    def _classify(text: str, hits: list[str]) -> list[tuple[str, bool]]:
        """Mark each hit of a path text direct or tree.

        Direct: the text names the file itself (the exact path, a path suffix,
        a basename) or is a wildcard that matches exactly one file. Tree: a file
        below a directory the text names, or one of several wildcard matches.
        """
        if _has_wildcard(text):
            return [(h, len(hits) == 1) for h in hits]
        return [(h, h == text or h.endswith("/" + text)) for h in hits]

    def _resolve(self, ref: Ref) -> list[tuple[str, bool]]:
        idx = self.index
        text = ref.text
        if ref.policy == "test-repo":
            return self._classify(text, idx.resolve_path(text, ref.dir_ctx, zone_ok=True))
        if ref.policy == "module-repo":
            return self._classify(text, idx.resolve_path(text, ref.dir_ctx, zone_ok=False))
        if ref.policy == "test-const":
            if _has_wildcard(text):
                first = text.split("/", 1)[0]
                if "/" not in text or _has_wildcard(first) or first not in idx.top_dirs:
                    return []
            elif "/" not in text:
                return self._classify(text, [text] if text in idx.files else self._unique_script(text))
            return self._classify(text, idx.resolve_path(text, ref.dir_ctx, zone_ok=True))
        if ref.policy == "module-const":
            if text in idx.files:
                return [] if is_zone(text) else [(text, True)]
            return self._classify(text, self._scripts(idx.resolve_path(text, False, zone_ok=False)))
        if ref.policy == "module-tail":
            return self._classify(text, self._scripts(idx.resolve_path(text, False, zone_ok=False)))
        if ref.policy == "shell":
            if "/" in text:
                return self._classify(text, self._scripts(idx.resolve_path(text, False, zone_ok=False)))
            hits = idx.by_base(text)
            return [(hits[0], True)] if len(hits) == 1 else []
        if ref.policy == "tuple":
            return self._resolve_tuple(ref.items)
        return []

    def _resolve_tuple(self, items: tuple[str, ...]) -> list[tuple[str, bool]]:
        """Copy loops name >=2 top-level entries; otherwise .py/.sh basename lists.

        A directory entry of a copy loop stands for its tree; a file entry and a
        basename name their files directly.
        """
        idx = self.index
        if all(i in idx.top_dirs or i in idx.files for i in items):
            out: list[tuple[str, bool]] = []
            for item in items:
                if item in idx.dirs:
                    out.extend((h, False) for h in idx.below(item))
                else:
                    out.append((item, True))
            return out
        return [(h, True) for i in items if i.endswith(SCRIPT_SUFFIXES) and "/" not in i for h in idx.by_base(i)]

    def _resolve_import(self, rel: str, facts: FileFacts, spec: ImportSpec) -> list[str]:
        """Repo files an import executes, including enclosing package __init__ files."""
        targets = ([spec.module] if spec.module else []) + [
            f"{spec.module}.{n}" if spec.module else n for n in spec.names
        ]
        if spec.level:
            pkg = posixpath.dirname(rel)
            for _ in range(spec.level - 1):
                pkg = posixpath.dirname(pkg)
            bases = [pkg]
        else:
            bases = list(dict.fromkeys(
                [posixpath.dirname(rel), "", *self.config.testpaths, *self.config.support_paths,
                 *self._test_syspath,
                 *(d for d in facts.syspath_dirs if d in self.index.dirs),
                 *(d for d in (*self.config.pythonpath, "src") if d == "" or d in self.index.dirs)]
            ))
        hits = self._import_hits(bases, targets, spec.level)
        first = targets[0].split(".")[0] if targets else ""
        if not spec.level and first not in sys.stdlib_module_names:
            hits = list(dict.fromkeys([*hits, *self._import_hits(self._package_roots(first), targets, 0)]))
        return hits

    def _import_hits(self, bases: list[str], targets: list[str], level: int) -> list[str]:
        files = self.index.files
        hits: list[str] = []
        for base in bases:
            pre = f"{base}/" if base else ""
            if level and f"{pre}__init__.py" in files:
                hits.append(f"{pre}__init__.py")
            for target in targets:
                parts = target.split(".")
                path = pre + "/".join(parts)
                found = [c for c in (f"{path}.py", f"{path}/__init__.py") if c in files]
                if found:
                    hits.extend(found)
                    hits.extend(
                        init for i in range(1, len(parts))
                        if (init := pre + "/".join(parts[:i]) + "/__init__.py") in files
                    )
        return hits

    def _package_roots(self, name: str) -> list[str]:
        """Parents of the top-level packages called name (``<parent>/<name>/__init__.py``) outside the zones."""
        if self._pkg_roots is None:
            roots: dict[str, list[str]] = {}
            for d in sorted(self.index.dirs):
                parent = posixpath.dirname(d)
                if (d and not is_zone(d + "/") and f"{d}/__init__.py" in self.index.files
                        and f"{parent}/__init__.py" not in self.index.files):
                    roots.setdefault(posixpath.basename(d), []).append(posixpath.dirname(d))
            self._pkg_roots = roots
        return self._pkg_roots.get(name, [])

    def _channel(self, rel: str, facts: FileFacts) -> Iterator[tuple[str, str, bool, bool]]:
        """By-name loading: a repo directory plus a literal basename in one module (tree edges)."""
        dirs = [d for d in facts.channel_dirs if d in self.index.dirs and not is_zone(d + "/")]
        if not dirs:
            return
        for literal in sorted(facts.literals):
            for hit in self.index.by_base(literal):
                for d in dirs:
                    if hit.startswith(d + "/"):
                        yield hit, f"{rel} loads {literal!r} by name below {d}/", False, False
                        break

    def _shell_refs(self, rel: str) -> list[Ref]:
        try:
            text = (self.root / rel).read_text(encoding="utf-8", errors="replace")
        except OSError:
            return []
        refs: dict[str, Ref] = {}
        here = posixpath.dirname(rel)
        for lineno, line in enumerate(text.splitlines(), 1):
            # "$DIR/../x.py" and "${ROOT}/x.py": the variable is the unknown base.
            for token in SHELL_TOKEN.findall(SHELL_VARIABLE.sub("", line)):
                token = token.lstrip("/")
                while token.startswith("./"):
                    token = token[2:]
                if ".." in token.split("/"):
                    norm = _normalize(posixpath.join(here, token))
                    if norm is None:
                        continue
                    token = norm
                elif "/" not in token and posixpath.join(here, token) in self.index.files:
                    token = posixpath.join(here, token)
                if token and token not in refs:
                    refs[token] = Ref("shell", token, lineno)
        return list(refs.values())

    # -- closure ------------------------------------------------------------

    def outgoing(self, rel: str, with_refs: bool) -> tuple[tuple[str, str, bool, bool], ...]:
        """(target, how, direct, reads) edges leaving one file; file references only at depth <= 1.

        ``direct`` is False for a tree edge: a reference that stands for a family
        of files (a directory used as a tree, a copy-loop directory entry, a
        by-name load below a directory, a wildcard matching several files).
        ``reads`` is ``direct`` or a ``glob``/``rglob`` enumeration: the files
        test code reads over it (the Markdown rule).
        """
        key = (rel, with_refs)
        if key in self._out:
            return self._out[key]
        out: list[tuple[str, str, bool, bool]] = []
        kind = self.kind(rel)
        if kind == "python":
            facts = self.facts(rel)
            if facts is not None:
                if with_refs:
                    for ref in facts.refs:
                        label = "|".join(ref.items) if ref.policy == "tuple" else ref.text
                        out.extend((hit, f"{rel}:{ref.line} {ref.policy} {label!r}", direct,
                                    direct or ref.enumerates)
                                   for hit, direct in self.resolve(ref))
                for spec in facts.imports:
                    out.extend((hit, f"{rel}:{spec.line} {spec.label()}", True, True)
                               for hit in self._resolve_import(rel, facts, spec))
                out.extend(self._channel(rel, facts))
        elif kind == "shell" and with_refs:
            for ref in self._shell_refs(rel):
                out.extend((hit, f"{rel}:{ref.line} runs {ref.text!r}", direct, direct)
                           for hit, direct in self.resolve(ref))
        result = tuple(out)
        self._out[key] = result
        return result

    def conftests(self, test: str) -> list[str]:
        """conftest.py files from the test's directory up to its test path."""
        top = self.config.testpath_of(test) or ""
        out: list[str] = []
        d = posixpath.dirname(test)
        while True:
            candidate = f"{d}/conftest.py" if d else "conftest.py"
            if candidate in self.index.files and candidate != test:
                out.append(candidate)
            if d == top or not d:
                break
            d = posixpath.dirname(d)
        return out

    def closure(self, test: str) -> dict[str, Edge]:
        """Every path the test reaches, each with the edge that reached it first.

        0-1 breadth-first search: test code (``PytestConfig.is_test_code``) keeps the
        depth of the code that reaches it; other files are one level deeper.
        """
        if test not in self._closures:
            self._closures[test] = self._search(test, direct_only=False)[0]
        return self._closures[test]

    def direct_closure(self, test: str) -> frozenset[str]:
        """The paths the test reaches over direct edges only (the same search)."""
        self._direct_search(test)
        return self._direct_closures[test]

    def own_reads(self, test: str) -> frozenset[str]:
        """The paths the test's own code reads: depth-0 code (the test file, its
        conftest ancestry, support files under the test paths, as far as direct
        edges reach them) over a direct edge or a ``glob``/``rglob`` enumeration."""
        self._direct_search(test)
        return self._own_reads[test]

    def _direct_search(self, test: str) -> None:
        if test not in self._direct_closures:
            deps, reads = self._search(test, direct_only=True)
            self._direct_closures[test] = frozenset(deps)
            self._own_reads[test] = frozenset(reads)

    def _search(self, test: str, direct_only: bool) -> tuple[dict[str, Edge], set[str]]:
        """The 0-1 search; returns the reached paths and what depth-0 code reads."""
        reads: set[str] = set()
        deps: dict[str, Edge] = {test: Edge(None, "the test file itself")}
        queue: deque[tuple[str, int]] = deque([(test, 0)])
        for conftest in self.conftests(test):
            deps.setdefault(conftest, Edge(test, f"{test} conftest ancestry"))
            queue.append((conftest, 0))
        best: dict[str, int] = {}
        while queue:
            rel, depth = queue.popleft()
            if best.get(rel, _FAR) <= depth:
                continue
            best[rel] = depth
            for hit, how, direct, read in self.outgoing(rel, depth <= 1):
                if depth == 0 and read:
                    reads.add(hit)
                if direct_only and not direct:
                    continue
                if hit not in deps:
                    deps[hit] = Edge(rel, how)
                hit_depth = depth if self.config.is_test_code(hit) else depth + 1
                if best.get(hit, _FAR) > hit_depth and self.kind(hit) is not None:
                    if hit_depth == depth:
                        queue.appendleft((hit, hit_depth))
                    else:
                        queue.append((hit, hit_depth))
        return deps, reads

    def inverse(self) -> dict[str, set[str]]:
        """path -> tests whose closure contains it."""
        if self._inverse is None:
            inv: dict[str, set[str]] = {}
            for test in self.tests:
                for dep in self.closure(test):
                    inv.setdefault(dep, set()).add(test)
            self._inverse = inv
        return self._inverse

    def direct_inverse(self) -> dict[str, set[str]]:
        """path -> tests whose direct closure contains it (the path's direct hits)."""
        if self._direct_inverse is None:
            inv: dict[str, set[str]] = {}
            for test in self.tests:
                for dep in self.direct_closure(test):
                    inv.setdefault(dep, set()).add(test)
            self._direct_inverse = inv
        return self._direct_inverse

    def reads_inverse(self) -> dict[str, set[str]]:
        """path -> tests whose own code reads it (``own_reads``)."""
        if self._reads_inverse is None:
            inv: dict[str, set[str]] = {}
            for test in self.tests:
                for dep in self.own_reads(test):
                    inv.setdefault(dep, set()).add(test)
            self._reads_inverse = inv
        return self._reads_inverse

    def chain(self, test: str, path: str) -> list[str]:
        """The reference chain from test to path, one step per line."""
        deps = self.closure(test)
        steps: list[str] = []
        cur: str | None = path
        seen: set[str] = set()
        while cur is not None and cur != test and cur not in seen:
            seen.add(cur)
            edge = deps[cur]
            steps.append(f"{edge.detail} -> {cur}")
            cur = edge.parent
        return list(reversed(steps)) or ["the test file itself"]


# ---------------------------------------------------------------------------
# Selection
# ---------------------------------------------------------------------------


@dataclass
class Selection:
    """The selector's answer for one set of changed paths."""

    result: str
    tests: list[str]
    reasons: list[str]
    unmapped: list[str]
    no_tests: list[str]
    removed_tests: list[str]
    by_path: dict[str, list[str]]
    test_paths: list[str]
    light_path: list[str] = field(default_factory=list)


def is_markdown(path: str) -> bool:
    return path.endswith(".md")


def is_infrastructure(path: str, config: PytestConfig) -> bool:
    """Shared test infrastructure: any conftest.py under the test paths, pytest config files."""
    if path in INFRA_CONFIG_FILES:
        return True
    return posixpath.basename(path) == "conftest.py" and config.in_testpaths(path)


def cross_cutting_reason(path: str) -> str | None:
    for pattern, reason in CROSS_CUTTING.items():
        if fnmatch.fnmatchcase(path, pattern):
            return reason
    return None


def is_missing_test(path: str, refmap: ReferenceMap) -> bool:
    """A test-file path pytest would collect that is absent from the tree."""
    return refmap.config.is_test_file(path) and not (refmap.root / path).exists()


def _known_at_head(root: Path, paths: Sequence[str]) -> set[str]:
    """The paths Git's HEAD commit contains; none without Git or a commit."""
    if not paths:
        return set()
    try:
        out = _git(root, "ls-tree", "-r", "--name-only", "-z", "HEAD", "--", *paths)
    except SelectorError:
        return set()
    return {p for p in out.split("\0") if p}


def select(refmap: ReferenceMap, changed: Iterable[str], deleted: Iterable[str] = ()) -> Selection:
    """Apply the result rules to changed paths.

    Shared test infrastructure, cross-cutting entries and absent test files
    keep the full closure. Otherwise Markdown outside the test support paths
    selects only the tests whose own code reads it (``own_reads``); with none
    it is a light path (a no-test zone path stays ``no tests``) and never makes
    the result broad. Code (``kind()`` python or shell, not a test file)
    selects only its direct hits; with none outside the no-test zones it is
    unmapped. Every other path, Markdown under the test paths included,
    selects its full closure.

    ``deleted``: paths the input mode reported deleted or renamed away. An
    absent test-file path counts as a removed test when it is one of them or
    Git's HEAD contains it; otherwise it is unmapped (a typo must not empty the
    selection).
    """
    inverse = refmap.inverse()
    direct = refmap.direct_inverse()
    reads = refmap.reads_inverse()
    paths = sorted(set(changed))
    gone = set(deleted)
    missing = {p for p in paths if is_missing_test(p, refmap)}
    gone |= _known_at_head(refmap.root, sorted(missing - gone))
    selected: set[str] = set()
    infra: list[str] = []
    cross: list[str] = []
    unmapped: list[str] = []
    no_tests: list[str] = []
    light: list[str] = []
    removed: list[str] = []
    by_path: dict[str, list[str]] = {}
    for path in paths:
        reason = cross_cutting_reason(path)
        special = is_infrastructure(path, refmap.config) or reason is not None or path in missing
        markdown = not special and is_markdown(path) and not refmap.config.in_support_paths(path)
        code = (not special and not is_markdown(path) and refmap.kind(path) in ("python", "shell")
                and not refmap.config.is_test_file(path))
        hits = set((reads if markdown else direct if code else inverse).get(path, ()))
        by_path[path] = sorted(hits)
        selected |= hits
        if is_infrastructure(path, refmap.config):
            infra.append(f"shared test infrastructure: {path}")
        elif reason is not None:
            cross.append(f"cross-cutting: {path} — {reason}")
        elif path in missing:
            (removed if path in gone else unmapped).append(path)
        elif not hits:
            if is_no_test_zone(path):
                no_tests.append(path)
            elif markdown:
                light.append(path)
            else:
                unmapped.append(path)
    reasons = infra + cross + [f"unmapped: {p}" for p in unmapped]
    return Selection(
        result="broad" if reasons else "targeted",
        tests=sorted(selected),
        reasons=reasons,
        unmapped=unmapped,
        no_tests=no_tests,
        removed_tests=removed,
        by_path=by_path,
        test_paths=[tp or "." for tp in refmap.config.testpaths],
        light_path=light,
    )


# ---------------------------------------------------------------------------
# Inputs
# ---------------------------------------------------------------------------


NO_CHANGED_PATHS = ("no changed paths (nothing staged, clean tree, empty range or empty list; "
                    "for committed work use --diff <base>..HEAD)")


class ChangeSet(NamedTuple):
    """Changed paths from one input, and those the input reported deleted or renamed away."""

    paths: list[str]
    deleted: frozenset[str] = frozenset()


def _parse_name_status(out: str) -> ChangeSet:
    """`git diff --name-status -z`: renames and copies carry two paths."""
    tokens = out.split("\0")
    paths: list[str] = []
    deleted: set[str] = set()
    i = 0
    while i < len(tokens):
        status = tokens[i]
        if not status:
            i += 1
            continue
        count = 2 if status[0] in "RC" else 1
        names = [t for t in tokens[i + 1: i + 1 + count] if t]
        paths.extend(names)
        if status[0] in "DR" and names:
            deleted.add(names[0])  # a deletion, or a rename's source
        i += 1 + count
    return ChangeSet(paths, frozenset(deleted))


def _parse_porcelain(out: str, prefix: str) -> ChangeSet:
    """`git status --porcelain -z`: 'XY path', a rename's source follows."""
    tokens = out.split("\0")
    paths: list[str] = []
    deleted: set[str] = set()
    i = 0
    while i < len(tokens):
        entry = tokens[i]
        i += 1
        if len(entry) < 4:
            continue
        paths.append(entry[3:])
        if "D" in entry[:2]:
            deleted.add(entry[3:])
        if entry[0] in "RC" or entry[1] in "RC":
            if i < len(tokens) and tokens[i]:
                paths.append(tokens[i])
                if "R" in entry[:2]:
                    deleted.add(tokens[i])
            i += 1
    return ChangeSet([p[len(prefix):] for p in paths if p.startswith(prefix)],
                     frozenset(p[len(prefix):] for p in deleted if p.startswith(prefix)))


def _relative(root: Path, raw: str) -> str:
    """A repo-relative path for one input path; SelectorError when unusable."""
    text = raw.strip()
    if not text:
        raise SelectorError("empty path in input")
    if os.path.isabs(text):
        try:
            text = Path(os.path.normpath(text)).relative_to(root).as_posix()
        except ValueError as exc:
            raise SelectorError(f"path outside the root: {raw}") from exc
    norm = _normalize(text.replace(os.sep, "/"))
    if not norm:
        raise SelectorError(f"not a repository path: {raw}")
    return norm


def changed_paths(args: argparse.Namespace, root: Path) -> ChangeSet | None:
    """The changed paths named by the input mode; None when no mode was given."""
    if args.staged:
        return _parse_name_status(_git(root, "diff", "--cached", "--name-status", "-M", "-z", "--relative"))
    if args.diff is not None:
        if args.diff.startswith("-"):
            raise SelectorError(f"invalid range: {args.diff}")
        return _parse_name_status(_git(root, "diff", "--name-status", "-M", "-z", "--relative", args.diff, "--"))
    if args.worktree:
        prefix = _git(root, "rev-parse", "--show-prefix").strip()
        return _parse_porcelain(_git(root, "status", "--porcelain=v1", "-z", "--untracked-files=all", "--", "."), prefix)
    if args.paths_from is not None:
        try:
            if args.paths_from == "-":
                lines = sys.stdin.read().splitlines()
            else:
                lines = Path(args.paths_from).read_text(encoding="utf-8").splitlines()
        except OSError as exc:
            raise SelectorError(f"cannot read {args.paths_from}: {exc.strerror}") from exc
        except UnicodeDecodeError as exc:
            raise SelectorError(f"cannot read {args.paths_from}: not UTF-8 text (byte {exc.start})") from exc
        return ChangeSet([_relative(root, line) for line in lines if line.strip()])
    if args.paths:
        return ChangeSet([_relative(root, p) for p in args.paths])
    return None


def _expand_dirs(paths: list[str], refmap: ReferenceMap) -> list[str]:
    """A directory given as input stands for the files below it."""
    out: list[str] = []
    for path in paths:
        if path in refmap.index.dirs and path not in refmap.index.files:
            out.extend(refmap.index.below(path))
        else:
            out.append(path)
    return out


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------


def _explain(refmap: ReferenceMap, path: str) -> dict[str, list[str]]:
    tests = sorted(refmap.inverse().get(path, ()))
    return {t: refmap.chain(t, path) for t in tests}


def _text_output(sel: Selection | None, explain: tuple[str, dict[str, list[str]]] | None,
                 mapping: dict[str, list[str]] | None) -> list[str]:
    lines: list[str] = []
    if sel is not None:
        lines.append(f"result: {sel.result}")
        lines.extend(f"reason: {r}" for r in sel.reasons)
        lines.extend(sel.tests)
        lines.extend(f"light-path: {p}" for p in sel.light_path)
        lines.extend(f"no tests: {p}" for p in sel.no_tests)
        lines.extend(f"removed test: {p}" for p in sel.removed_tests)
    if explain is not None:
        path, chains = explain
        if not chains:
            lines.append(f"explain: {path}: no test references it")
        else:
            lines.append(f"explain: {path}")
            for test, steps in chains.items():
                lines.append(f"  {test}")
                lines.extend(f"    {s}" for s in steps)
    if mapping is not None:
        for test, deps in mapping.items():
            lines.append(f"map: {test}")
            lines.extend(f"  {d}" for d in deps)
    return lines


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="select_tests.py",
        description="Select the pytest files that exercise changed paths (static scan).",
    )
    parser.add_argument("--root", default=".", help="repository root (default: working directory)")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--staged", action="store_true", help="paths staged in the Git index")
    mode.add_argument("--diff", metavar="RANGE", help="paths changed in a Git revision range")
    mode.add_argument("--worktree", action="store_true", help="staged, unstaged and untracked paths")
    mode.add_argument("--paths-from", metavar="FILE", help="one path per line; '-' reads stdin")
    parser.add_argument("paths", nargs="*", metavar="PATH", help="changed repo-relative paths")
    parser.add_argument("--format", choices=("text", "json", "args"), default="text")
    parser.add_argument("--explain", metavar="PATH", help="print each selecting test's chain to PATH")
    parser.add_argument("--map", action="store_true", help="dump test -> dependencies")
    args = parser.parse_args(argv)
    modes = sum(bool(x) for x in (args.staged, args.diff is not None, args.worktree,
                                  args.paths_from is not None, args.paths))
    if modes > 1:
        parser.error("give one input: --staged, --diff, --worktree, --paths-from or PATH...")
    if modes == 0 and not (args.explain or args.map):
        parser.error("no input: give --staged, --diff RANGE, --worktree, --paths-from FILE or PATH...")
    if args.format == "args" and (args.explain or args.map):
        parser.error("--format args cannot be combined with --explain or --map")
    return args


def _check_root(raw: str) -> Path:
    root = Path(raw).resolve()
    if not root.is_dir() or not os.access(root, os.R_OK | os.X_OK):
        raise SelectorError(f"root is not a readable directory: {raw}")
    return root


def _write_stdout(text: str) -> None:
    """Write the result; a reader that closes the pipe early (``| head``) is no error."""
    try:
        sys.stdout.write(text)
        sys.stdout.flush()
    except BrokenPipeError:
        # Point stdout at the null device so the interpreter's final flush stays quiet.
        devnull = os.open(os.devnull, os.O_WRONLY)
        os.dup2(devnull, sys.stdout.fileno())
        os.close(devnull)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        root = _check_root(args.root)
        changed = changed_paths(args, root)
        if changed is not None and not changed.paths:
            raise SelectorError(NO_CHANGED_PATHS)
        explain_path = _relative(root, args.explain) if args.explain else None
        extra = [p for p in changed.paths if not (root / p).is_dir()] if changed is not None else []
        refmap = ReferenceMap(root, extra)
        sel = (select(refmap, _expand_dirs(changed.paths, refmap), changed.deleted)
               if changed is not None else None)
    except SelectorError as exc:
        print(f"select_tests: error: {exc}", file=sys.stderr)
        return 2
    explain = (explain_path, _explain(refmap, explain_path)) if explain_path else None
    mapping = ({t: sorted(refmap.closure(t)) for t in refmap.tests} if args.map else None)
    if args.format == "args":
        if sel is None:
            return 2
        targets = sel.test_paths if sel.result == "broad" else sel.tests
        if not targets and sel.light_path:
            print("select_tests: no tests selected (result: targeted, empty set; light path); "
                  "run the light-path checks (framework/installation-activation.md §Light path) "
                  "instead of pytest", file=sys.stderr)
        elif not targets:
            print("select_tests: no tests selected (result: targeted, empty set); "
                  "a bare pytest call would run the whole suite", file=sys.stderr)
        _write_stdout(" ".join(targets) + "\n" if targets else "")
        return 0
    if args.format == "json":
        payload: dict[str, object] = {}
        if sel is not None:
            payload.update(
                result=sel.result, tests=sel.tests, reasons=sel.reasons, unmapped=sel.unmapped,
                no_tests=sel.no_tests, removed_tests=sel.removed_tests, by_path=sel.by_path,
                test_paths=sel.test_paths, light_path=sel.light_path,
            )
        if explain is not None:
            payload["explain"] = {explain[0]: explain[1]}
        if mapping is not None:
            payload["map"] = mapping
        _write_stdout(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
        return 0
    _write_stdout("".join(f"{line}\n" for line in _text_output(sel, explain, mapping)))
    return 0

if __name__ == "__main__":
    sys.exit(main())
