#!/usr/bin/env python3
"""
Pre-commit Check 7 — SKILL-FM-VALIDATE (Task 366 F.2).

Validates YAML frontmatter for staged skills/**/SKILL.md files
against framework/skill-anatomy.md rules (subset, mechanisch).

Exit codes:
  0 — PASS (warnings may be printed to stdout with prefix SKILL-FM-WARN:)
  1 — BLOCK (invalid YAML, new skill missing required fields, etc.)
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    yaml = None  # type: ignore

PRIMARY_ALLOW = frozenset(
    {"user-facing", "workflow-step", "sub-skill", "hook", "cross-cutting"}
)
SECONDARY_PATH_ALLOW = PRIMARY_ALLOW


def repo_root(start: Path) -> Path:
    cur = start.resolve()
    for parent in [cur] + list(cur.parents):
        if (parent / "framework").is_dir() and (parent / "scripts").is_dir():
            return parent
    return start.resolve()


def normalize_name_dir(name: str, dirname: str) -> bool:
    n = name.replace("-", "_").lower()
    d = dirname.replace("-", "_").lower()
    return n == d


def parse_frontmatter(text: str) -> tuple[dict | None, str | None]:
    # Be robust against UTF-8 BOM at file start.
    text = text.lstrip("\ufeff")
    if not text.startswith("---"):
        return None, "missing opening ---"
    parts = text.split("---", 2)
    if len(parts) < 3:
        return None, "unclosed frontmatter"
    raw = parts[1]
    if yaml is None:
        return None, "PyYAML not installed (SKIP validation)"
    try:
        data = yaml.safe_load(raw)
        if data is None:
            data = {}
        if not isinstance(data, dict):
            return None, "frontmatter must be a YAML mapping"
        return data, None
    except yaml.YAMLError as e:
        return None, f"YAML error: {e}"


def staged_skill_paths(root: Path) -> list[Path]:
    try:
        out = subprocess.run(
            ["git", "diff", "--cached", "--name-only", "-z"],
            cwd=root,
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError:
        return []
    if out.returncode != 0:
        return []
    names = [p for p in out.stdout.split("\0") if p]
    skills: list[Path] = []
    for name in names:
        p = root / name
        if not name.replace("\\", "/").startswith("skills/"):
            continue
        if "/_archived/" in name.replace("\\", "/"):
            continue
        if name.endswith("/SKILL.md") or name.endswith("\\SKILL.md"):
            skills.append(p)
    return skills


def added_skill_paths(root: Path) -> set[str]:
    try:
        out = subprocess.run(
            ["git", "diff", "--cached", "--name-only", "--diff-filter=A", "-z"],
            cwd=root,
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError:
        return set()
    if out.returncode != 0:
        return set()
    return {
        n.replace("\\", "/")
        for n in out.stdout.split("\0")
        if n and n.replace("\\", "/").startswith("skills/") and n.endswith("SKILL.md")
    }


def validate_file(path: Path, root: Path, is_new: bool) -> tuple[list[str], list[str]]:
    """Returns (blocks, warns)."""
    blocks: list[str] = []
    warns: list[str] = []

    rel = path.relative_to(root).as_posix()
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as e:
        return [f"{rel}: read error {e}"], []

    data, err = parse_frontmatter(text)
    if err:
        if "PyYAML not installed" in err:
            print(f"SKILL-FM-WARN: {rel}: {err}")
            return [], []
        return [f"{rel}: {err}"], []

    assert data is not None

    name_val = data.get("name")
    if name_val is not None and not isinstance(name_val, str):
        blocks.append(f"{rel}: name must be string")

    skill_dir = path.parent.name
    if isinstance(name_val, str) and not normalize_name_dir(name_val, skill_dir):
        blocks.append(
            f"{rel}: name '{name_val}' does not match directory '{skill_dir}' "
            "(normalized -/_)"
        )

    for fld in ("description", "status"):
        if fld not in data or data[fld] is None or data[fld] == "":
            blocks.append(f"{rel}: missing required field `{fld}`")

    inv = data.get("invocation")
    if not isinstance(inv, dict):
        blocks.append(f"{rel}: missing or invalid `invocation` mapping")
    else:
        prim = inv.get("primary")
        if prim is None:
            blocks.append(
                f"{rel}: invocation.primary must be one of {sorted(PRIMARY_ALLOW)}"
            )
        elif prim not in PRIMARY_ALLOW:
            blocks.append(
                f"{rel}: invocation.primary must be one of {sorted(PRIMARY_ALLOW)}"
            )

        sec = inv.get("secondary")
        if sec is not None and not isinstance(sec, list):
            warns.append(f"{rel}: invocation.secondary should be a list")
        elif isinstance(sec, list):
            for raw in sec:
                if not isinstance(raw, str) or not raw.strip():
                    warns.append(
                        f"{rel}: invocation.secondary element should be non-empty string, got {raw!r}"
                    )
                    continue
                token = raw.strip()
                path_name = token.split(":", 1)[0]
                if path_name not in SECONDARY_PATH_ALLOW:
                    warns.append(
                        f"{rel}: invocation.secondary unknown path '{path_name}' (from {token!r})"
                    )

    dmi = data.get("disable-model-invocation")
    if dmi is not None and not isinstance(dmi, bool):
        blocks.append(f"{rel}: disable-model-invocation must be boolean if present")

    modes = data.get("modes")
    if "modes" in data and data["modes"] is None:
        blocks.append(f"{rel}: modes must be omitted or a YAML list (not null)")
    elif modes is not None and not isinstance(modes, list):
        blocks.append(f"{rel}: modes must be a list")

    if isinstance(modes, list) and len(modes) > 3:
        warns.append(f"{rel}: more than 3 modes (Mega-Skill risk; Spec-Board)")

    # relevant_for: optional list of agent names or wildcard ["*"]
    rel_for = data.get("relevant_for")
    if rel_for is not None:
        if not isinstance(rel_for, list):
            blocks.append(
                f"{rel}: relevant_for must be a list (got {type(rel_for).__name__})"
            )
        else:
            agents_dir = root / "agents"
            known: set[str] = set()
            if agents_dir.is_dir():
                for md in agents_dir.glob("*.md"):
                    if md.stem not in ("README", "navigation"):
                        known.add(md.stem)
            for entry in rel_for:
                if not isinstance(entry, str) or not entry.strip():
                    blocks.append(
                        f"{rel}: relevant_for entries must be non-empty strings"
                    )
                    continue
                e = entry.strip()
                if e == "*":
                    continue
                if known and e not in known:
                    warns.append(
                        f"{rel}: relevant_for references unknown agent '{e}' "
                        f"(not found in agents/)"
                    )

    return blocks, warns


def main() -> int:
    ap = argparse.ArgumentParser(description="SKILL-FM-VALIDATE (Check 7)")
    ap.add_argument(
        "--repo",
        type=Path,
        default=None,
        help="Repository root (default: auto-detect)",
    )
    args = ap.parse_args()
    root = repo_root(args.repo or Path.cwd())
    skills_dir = root / "skills"
    if not skills_dir.is_dir():
        print("SKILL-FM-VALIDATE SKIP — skills/ not in this repo")
        return 0

    if yaml is None:
        print("SKILL-FM-VALIDATE SKIP — PyYAML missing")
        return 0

    staged = staged_skill_paths(root)
    if not staged:
        print("SKILL-FM-VALIDATE PASS - no staged SKILL.md under skills/")
        return 0

    added = added_skill_paths(root)
    blocks_all: list[str] = []
    warns_all: list[str] = []

    for path in staged:
        if not path.is_file():
            continue
        rel_posix = path.relative_to(root).as_posix()
        is_new = rel_posix in added
        b, w = validate_file(path, root, is_new=is_new)
        blocks_all.extend(b)
        warns_all.extend(w)

    for w in warns_all:
        print(f"SKILL-FM-WARN: {w}")

    if blocks_all:
        print("SKILL-FM-VALIDATE BLOCK", file=sys.stderr)
        for line in blocks_all:
            print(f"  {line}", file=sys.stderr)
        return 1

    print("SKILL-FM-VALIDATE PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
