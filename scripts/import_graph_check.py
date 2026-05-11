#!/usr/bin/env python3
"""import_graph_check.py — AST-based transitive import-graph cycle check.

Walks the import graph statically (via `ast.parse`, never `import`)
from a starting module and reports any transitive path that reaches a
target module. Used as a pre-lock check for structural-refactor briefs
per `skills/_protocols/mca-brief-template.md` §Structural-refactor
pre-lock checklist.

The runtime alternative (`importlib.import_module`) is unsuitable
because the very cycle we are checking would itself trigger an
ImportError when the check runs. AST traversal sees the imports
without executing the module bodies.

Usage:
    python3 scripts/import_graph_check.py --from <module> --to <module> \
        [--root <package-root>]
    python3 scripts/import_graph_check.py --from <module> --detect-cycles \
        [--root <package-root>]

Examples:
    # "Does chat.state transitively reach audit.contracts.audit?"
    python3 scripts/import_graph_check.py \
        --from buddyai.chat.state \
        --to buddyai.audit.contracts.audit \
        --root src/

    # "Are there any cycles starting from chat.state?"
    python3 scripts/import_graph_check.py \
        --from buddyai.chat.state \
        --detect-cycles \
        --root src/

Exit codes:
    0 = no cycle / target unreachable
    1 = cycle found (or target reachable when --to given)
    2 = invalid arguments / module not found
"""
from __future__ import annotations

import argparse
import ast
import sys
from pathlib import Path


def _module_to_path(module: str, root: Path) -> Path | None:
    """Resolve a dotted module name to a .py file under root.

    Tries both `<module>.py` and `<module>/__init__.py`. Returns the
    first match or None.
    """
    parts = module.split(".")
    file_candidate = root.joinpath(*parts).with_suffix(".py")
    if file_candidate.is_file():
        return file_candidate
    pkg_candidate = root.joinpath(*parts, "__init__.py")
    if pkg_candidate.is_file():
        return pkg_candidate
    return None


def _imports_from_file(path: Path) -> list[str]:
    """Return the dotted module names imported by the given .py file.

    Best-effort — unparseable files yield an empty list (not an error;
    the consumer reports unresolved nodes separately). Both `import X`
    and `from X import Y` produce the dotted module name `X`. Relative
    imports (`from . import ...`) are skipped — they require the
    importing module's package context, which the caller passes via
    `_resolve_relative` below.
    """
    try:
        source = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return []
    try:
        tree = ast.parse(source, filename=str(path))
    except SyntaxError:
        return []

    imports: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.level and node.level > 0:
                # Relative import — caller must resolve against package.
                # Encode as a sentinel so _resolve_relative can rewrite it.
                imports.append(f"__relative__:{node.level}:{node.module or ''}")
            elif node.module:
                imports.append(node.module)
    return imports


def _resolve_relative(rel: str, importing_module: str) -> str | None:
    """Resolve a `__relative__:<level>:<module>` sentinel against the
    importing module's package path."""
    _, level_str, mod = rel.split(":", 2)
    level = int(level_str)
    parts = importing_module.split(".")
    if level > len(parts):
        return None
    base = parts[: len(parts) - level]
    if mod:
        base.extend(mod.split("."))
    return ".".join(base) if base else None


def _build_graph(
    start: str, root: Path
) -> tuple[dict[str, list[str]], set[str]]:
    """BFS the import graph from `start` (dotted module). Returns
    (edges, unresolved). Edges are direct imports per module; unresolved
    is the set of dotted names whose source file was not found under
    root."""
    edges: dict[str, list[str]] = {}
    unresolved: set[str] = set()
    queue: list[str] = [start]
    while queue:
        mod = queue.pop()
        if mod in edges:
            continue
        path = _module_to_path(mod, root)
        if path is None:
            unresolved.add(mod)
            edges[mod] = []
            continue
        raw = _imports_from_file(path)
        resolved: list[str] = []
        for imp in raw:
            if imp.startswith("__relative__:"):
                full = _resolve_relative(imp, mod)
                if full:
                    resolved.append(full)
            else:
                resolved.append(imp)
        edges[mod] = resolved
        for r in resolved:
            if r not in edges:
                queue.append(r)
    return edges, unresolved


def _path_to(
    edges: dict[str, list[str]], start: str, target: str
) -> list[str] | None:
    """DFS for a path from start to target. Returns the path as a list
    of module names, or None if unreachable."""
    visited: set[str] = set()
    stack: list[tuple[str, list[str]]] = [(start, [start])]
    while stack:
        mod, path = stack.pop()
        if mod == target and len(path) > 1:
            return path
        if mod in visited:
            continue
        visited.add(mod)
        for nxt in edges.get(mod, []):
            if nxt == target:
                return path + [nxt]
            if nxt not in visited:
                stack.append((nxt, path + [nxt]))
    return None


def _detect_cycles(edges: dict[str, list[str]], start: str) -> list[list[str]]:
    """Detect cycles reachable from start. Returns one path per cycle
    (the path from start that closes back on a previously-visited node).
    """
    cycles: list[list[str]] = []
    seen_cycles: set[tuple[str, ...]] = set()

    def dfs(mod: str, path: list[str], on_path: set[str]) -> None:
        for nxt in edges.get(mod, []):
            if nxt in on_path:
                idx = path.index(nxt)
                cycle = tuple(path[idx:] + [nxt])
                if cycle not in seen_cycles:
                    seen_cycles.add(cycle)
                    cycles.append(list(cycle))
                continue
            if nxt not in edges:
                continue
            dfs(nxt, path + [nxt], on_path | {nxt})

    dfs(start, [start], {start})
    return cycles


def main() -> int:
    parser = argparse.ArgumentParser(
        description="AST-based transitive import-graph cycle / reachability check."
    )
    parser.add_argument(
        "--from",
        dest="from_module",
        required=True,
        help="dotted module name to start from (e.g. buddyai.chat.state)",
    )
    parser.add_argument(
        "--to",
        dest="to_module",
        default=None,
        help="dotted module name to test reachability against",
    )
    parser.add_argument(
        "--detect-cycles",
        action="store_true",
        help="report any cycle reachable from --from (instead of a single --to target)",
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=Path.cwd(),
        help="package source root to resolve modules under (default: cwd)",
    )
    parser.add_argument(
        "--show-unresolved",
        action="store_true",
        help="list dotted names that did not resolve to a .py file under --root",
    )
    args = parser.parse_args()

    if not args.to_module and not args.detect_cycles:
        parser.error("either --to <module> or --detect-cycles is required")

    if not args.root.is_dir():
        print(f"ERROR: --root not a directory: {args.root}", file=sys.stderr)
        return 2

    edges, unresolved = _build_graph(args.from_module, args.root)

    if args.from_module in unresolved:
        print(
            f"ERROR: --from module {args.from_module!r} not found under {args.root}",
            file=sys.stderr,
        )
        return 2

    print(f"Walked {len(edges)} module(s) from {args.from_module} under {args.root}")
    if args.show_unresolved and unresolved:
        print(f"Unresolved (likely stdlib / external / wrong --root): {len(unresolved)}")
        for u in sorted(unresolved):
            print(f"  {u}")

    if args.to_module:
        path = _path_to(edges, args.from_module, args.to_module)
        if path is None:
            print(f"OK: {args.from_module} does NOT transitively reach {args.to_module}.")
            return 0
        print(f"CYCLE-CANDIDATE: {args.from_module} reaches {args.to_module} via:")
        for i, m in enumerate(path):
            print(f"  {'  ' * i}{m}")
        return 1

    cycles = _detect_cycles(edges, args.from_module)
    if not cycles:
        print(f"OK: no cycles reachable from {args.from_module}.")
        return 0
    print(f"FOUND {len(cycles)} cycle(s) reachable from {args.from_module}:")
    for i, cyc in enumerate(cycles, 1):
        print(f"  cycle {i}: {' -> '.join(cyc)}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
