#!/usr/bin/env python3
"""
Regenerate the Claude-Code skill-wrapper set under .claude/skills/.

A wrapper (`.claude/skills/<kebab-name>/SKILL.md`) is the thin,
CC-discoverable proxy for an orchestrator-neutral skill SoT
(`skills/<dir>/SKILL.md`). Wrappers exist solely so Claude Code can
inject the skill into the available-skills system-reminder for
proactive discovery; they carry no methodology.

The wrapper is a DERIVED artifact: this script is the sole generator,
`consistency_check` (check 10) is the validator. Mirrors the
`scripts/generate_skill_map.py` generator + validator split.

Inclusion contract (framework/skill-anatomy.md §Frontmatter schema,
locked decision Option C). A skill is wrapper-eligible iff:

  status not in {archived, deprecated}
  AND disable-model-invocation != true
  AND ( invocation.primary in {user-facing, cross-cutting}
        OR cc_wrapper == true )
  AND cc_wrapper != false

`cc_wrapper` is a NEW optional bool frontmatter field, override-only
(absent ⇒ the implicit rule decides).

Failure modes:
  - malformed/missing frontmatter ⇒ skip skill + stderr warning,
    continue (no crash);
  - two eligible skills normalizing to the same kebab name ⇒ hard
    error, non-zero exit, NO partial write;
  - `cc_wrapper` present but non-bool ⇒ hard error, non-zero exit.

CLI mirrors generate_skill_map.py:
  default     write the wrapper set (idempotent, byte-identical on
              re-run; orphan wrappers removed)
  --check     verify-only; non-zero exit on any drift vs a fresh
              generation; no write.

Standalone script: reads skills/*/SKILL.md, writes only under
.claude/skills/. No framework-runtime import, no release-sync call.
"""
from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    yaml = None  # type: ignore

ELIGIBLE_PRIMARY = {"user-facing", "cross-cutting"}
EXCLUDED_STATUS = {"archived", "deprecated"}

# Stable body sentinel. Every wrapper this generator emits carries
# this exact line. The orphan-sweep only `rmtree`s a directory whose
# SKILL.md contains this marker (= provably generator-authored). A
# directory without it (hand-authored CC-plugin wrapper, asset dir,
# anything else) is LEFT in place + WARNed, never deleted. Changing
# this string is a breaking change: every previously generated
# wrapper would stop being recognized as managed.
GENERATED_MARKER = (
    "<!-- generated-by: scripts/generate_skill_wrappers.py "
    "(do not hand-edit) -->"
)

WRAPPER_BODY_TEMPLATE = """# Skill: {name} (Wrapper)

{marker}

This is the Claude-Code-discoverable wrapper. The full
orchestrator-neutral protocol — methodology, contract, modes,
red flags — lives in the SoT:

**SoT:** `skills/{src_dir}/SKILL.md`

Read the SoT and follow it. This wrapper is a generated derived
artifact (`scripts/generate_skill_wrappers.py`); it exists only so
Claude Code can inject the skill into the available-skills
system-reminder for proactive discovery. Do not hand-edit — edits
are reverted on the next generator run and flagged by
`consistency_check`.
"""


def is_generated_wrapper(wdir: Path) -> bool:
    """
    True iff `wdir` is provably a wrapper this generator authored:
    it contains a SKILL.md AND that file carries GENERATED_MARKER.

    This is the ownership proof gating the destructive orphan-sweep.
    A directory without the marker (hand-authored CC-plugin wrapper,
    asset dir, anything non-generated) returns False and is never
    removed.

    A symlink is rejected up front, before any `is_dir()` (which
    follows symlinks): the generator never emits symlinked wrappers,
    so a symlinked path under .claude/skills/ is by definition not
    generator-authored. Without this guard a symlinked dir would be
    classified as a generated wrapper and `shutil.rmtree` would raise
    an unhandled OSError (it refuses to recurse a symlink). Treating
    it as unmanaged gives parity with the leave-and-WARN path.
    """
    if wdir.is_symlink():
        return False
    if not wdir.is_dir():
        return False
    sf = wdir / "SKILL.md"
    if not sf.is_file():
        return False
    try:
        return GENERATED_MARKER in sf.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return False


class RepoRootError(RuntimeError):
    """No `framework/` ancestor — refuse to guess the repo root."""


def repo_root(start: Path) -> Path:
    """
    Resolve the repo root as the nearest ancestor containing a
    `framework/` dir. No such ancestor → hard error (RepoRootError),
    never a `start.resolve()` fallback: a silent fallback lets the
    generator materialize a fresh `.claude/skills/` tree in the wrong
    location.
    """
    cur = start.resolve()
    for parent in [cur] + list(cur.parents):
        if (parent / "framework").is_dir():
            return parent
    raise RepoRootError(
        f"no `framework/` ancestor of {cur} — cannot locate the repo "
        f"root; refusing to write `.claude/skills/` into an unknown "
        f"tree (pass --repo <repo-root>)"
    )


def extract_frontmatter(text: str, src_dir: str = "?") -> dict | None:
    """
    Parse the YAML frontmatter block.

    The fence is detected LINE-WISE on the first two ``^---$`` lines
    (the YAML document delimiters), never a bare substring split — a
    literal ``---`` inside a description value must NOT mis-split and
    silently un-discover an otherwise-eligible skill (Task 326's whole
    purpose).

    A fence line is the literal ``---`` at column 0 (only trailing
    whitespace / ``\\r`` tolerated). An *indented* ``---`` — e.g. a
    divider line inside a ``|`` block scalar — is content, not a
    fence, exactly as YAML itself resolves it via indentation.

    Three distinct outcomes:
      - no opening fence            → not a frontmatter doc, quiet None
      - opening fence but no close  → fence detection failed on a doc
                                      that *starts* like frontmatter →
                                      loud WARN, None (must not vanish)
      - fence found, YAML fails     → genuine YAML error, soft WARN,
                                      None
    """
    def _is_fence(line: str) -> bool:
        # Column-0 `---`, only trailing whitespace/CR tolerated.
        # Indented `---` (block-scalar content) is NOT a fence.
        return line.rstrip() == "---"

    # Accept UTF-8 BOM-prefixed markdown files.
    text = text.lstrip("﻿")
    lines = text.splitlines()
    if not lines or not _is_fence(lines[0]):
        return None

    close_idx = None
    for i in range(1, len(lines)):
        if _is_fence(lines[i]):
            close_idx = i
            break
    if close_idx is None:
        print(
            f"generate_skill_wrappers: WARN {src_dir} — opening `---` "
            f"fence but no closing `^---$` line; frontmatter not parsed "
            f"(possible literal `---` mis-handling), skill NOT wrapped",
            file=sys.stderr,
        )
        return None

    if yaml is None:
        return None

    block = "\n".join(lines[1:close_idx])
    try:
        data = yaml.safe_load(block)
    except yaml.YAMLError as exc:
        print(
            f"generate_skill_wrappers: WARN {src_dir} — frontmatter "
            f"present but YAML failed to parse ({exc.__class__.__name__}), "
            f"skipped",
            file=sys.stderr,
        )
        return None
    return data if isinstance(data, dict) else None


def kebab_normalize(name: str) -> str:
    """Harmonize `-`/`_` to kebab (framework/skill-anatomy.md §name)."""
    return name.strip().replace("_", "-")


def normalize_description(desc: str) -> str:
    """
    Collapse YAML folded-scalar whitespace to single spaces.

    The trigger string ("Triggers when ..." / "Use when ...") is
    load-bearing for P(invoked) and is preserved verbatim — only
    inter-token whitespace (newlines/runs of spaces introduced by the
    `>` folded scalar) is normalized. Used for both wrapper rendering
    and the source-fidelity gate, so they compare apples to apples.
    """
    return " ".join(str(desc).split())


class CollisionError(RuntimeError):
    """Two eligible skills normalize to the same kebab wrapper name."""


class FrontmatterValueError(RuntimeError):
    """A frontmatter field has an invalid type (e.g. cc_wrapper non-bool)."""


def is_eligible(data: dict | None) -> tuple[bool, str | None]:
    """
    Apply the locked Option-C inclusion predicate.

    Returns (eligible, hard_error). `hard_error` is non-None only for
    a `cc_wrapper` type violation (caller must abort non-zero). A
    None `data` (malformed frontmatter) is a soft skip, not a hard
    error.
    """
    if not data:
        return (False, None)

    cc = data.get("cc_wrapper")
    if cc is not None and not isinstance(cc, bool):
        return (False, f"cc_wrapper must be a bool, got {cc!r}")

    if cc is False:
        return (False, None)

    status = data.get("status")
    if status in EXCLUDED_STATUS:
        return (False, None)

    if data.get("disable-model-invocation") is True:
        return (False, None)

    prim = None
    inv = data.get("invocation")
    if isinstance(inv, dict):
        prim = inv.get("primary")

    if cc is True:
        return (True, None)

    if prim in ELIGIBLE_PRIMARY:
        return (True, None)

    return (False, None)


def render_wrapper(name_kebab: str, description: str, src_dir: str) -> str:
    """
    Render the full wrapper SKILL.md (frontmatter + fixed body).

    The frontmatter block is serialized via ``yaml.safe_dump`` so any
    description — colons, quotes, unicode, the load-bearing trigger
    string — round-trips as valid, machine-parseable YAML. ``safe_dump``
    is deterministic for a fixed input (sorted keys disabled, fixed
    field order), so output stays byte-identical run-vs-run.
    """
    desc = normalize_description(description)
    front_block = yaml.safe_dump(
        {"name": name_kebab, "description": desc},
        sort_keys=False,
        allow_unicode=True,
        default_flow_style=False,
        width=10**9,  # never line-wrap the description scalar
    )
    front = f"---\n{front_block}---\n\n"
    body = WRAPPER_BODY_TEMPLATE.format(
        name=name_kebab, src_dir=src_dir, marker=GENERATED_MARKER
    )
    return front + body


def iter_skills(skills_root: Path) -> list[tuple[str, dict | None]]:
    """Walk skills/*/SKILL.md (skip `_`-prefixed and non-dirs)."""
    out: list[tuple[str, dict | None]] = []
    if not skills_root.is_dir():
        return out
    for child in sorted(skills_root.iterdir()):
        if not child.is_dir():
            continue
        if child.name.startswith("_"):
            continue
        sf = child / "SKILL.md"
        if not sf.is_file():
            continue
        text = sf.read_text(encoding="utf-8")
        data = extract_frontmatter(text, child.name)
        out.append((child.name, data))
    return out


def build_desired(skills_root: Path) -> dict[str, str]:
    """
    Map kebab wrapper name -> wrapper file content for every eligible
    skill.

    Raises FrontmatterValueError on a `cc_wrapper` type violation and
    CollisionError on a kebab-name collision between two eligible
    skills. Both abort BEFORE any write (no partial state).
    """
    desired: dict[str, str] = {}
    # Casefolded kebab -> (first kebab, first src_dir), for case-only
    # collision detection on case-insensitive filesystems (C-007).
    seen_fold: dict[str, tuple[str, str]] = {}

    for src_dir, data in iter_skills(skills_root):
        eligible, hard_err = is_eligible(data)
        if hard_err is not None:
            raise FrontmatterValueError(f"{src_dir}: {hard_err}")
        if not eligible:
            # C-004: an `invocation` present but not a mapping is a
            # malformed schema that silently makes the skill ineligible
            # (the implicit predicate can't read `primary`). WARN with
            # parity to the name/description skip paths below, instead
            # of vanishing the skill with no signal.
            if isinstance(data, dict):
                inv = data.get("invocation")
                if inv is not None and not isinstance(inv, dict):
                    print(
                        f"generate_skill_wrappers: WARN {src_dir} — "
                        f"`invocation` present but not a mapping "
                        f"({type(inv).__name__}); ineligible, skipped",
                        file=sys.stderr,
                    )
            continue

        assert data is not None  # eligible ⇒ frontmatter parsed
        raw_name = data.get("name")
        if not isinstance(raw_name, str) or not raw_name.strip():
            print(
                f"generate_skill_wrappers: WARN {src_dir} — eligible but "
                f"missing/invalid `name`, skipped",
                file=sys.stderr,
            )
            continue
        description = data.get("description")
        if not isinstance(description, str) or not description.strip():
            print(
                f"generate_skill_wrappers: WARN {src_dir} — eligible but "
                f"missing/invalid `description`, skipped",
                file=sys.stderr,
            )
            continue

        kebab = kebab_normalize(raw_name)
        # Collision key is casefolded: on a case-insensitive FS
        # (macOS APFS, Windows) `Foo` and `foo` resolve to the same
        # directory, so the second write would silently overwrite the
        # first. Casefolding makes the collision deterministic on
        # every platform (and still catches exact-kebab collisions —
        # casefold is idempotent on identical strings).
        fold = kebab.casefold()
        if fold in seen_fold:
            prior_kebab, prior_dir = seen_fold[fold]
            raise CollisionError(
                f"kebab-name collision (case-insensitive): `{kebab}` "
                f"from `{src_dir}` vs `{prior_kebab}` from "
                f"`{prior_dir}` — ambiguous discovery, no wrapper "
                f"written"
            )
        desired[kebab] = render_wrapper(kebab, description, src_dir)
        seen_fold[fold] = (kebab, src_dir)

    return desired


def current_wrappers(cc_skills_root: Path) -> dict[str, str]:
    """
    Map wrapper dir name -> current SKILL.md content on disk, scoped
    to directories this generator provably authored (SKILL.md +
    GENERATED_MARKER).

    Unmanaged directories (hand-authored CC-plugin wrappers, asset
    dirs) are deliberately invisible here: the orphan-sweep never
    touches them, so reporting them as drift would make `--check`
    perpetually red with no generator action that resolves it.
    Mirrors the leave-and-WARN behaviour of write_wrappers.
    """
    out: dict[str, str] = {}
    if not cc_skills_root.is_dir():
        return out
    for child in sorted(cc_skills_root.iterdir()):
        if not child.is_dir():
            continue
        sf = child / "SKILL.md"
        if not sf.is_file():
            continue
        if not is_generated_wrapper(child):
            continue
        out[child.name] = sf.read_text(encoding="utf-8")
    return out


def diff_report(
    desired: dict[str, str], current: dict[str, str]
) -> list[str]:
    """Human-readable drift lines (empty ⇒ in sync)."""
    report: list[str] = []
    for name in sorted(set(desired) | set(current)):
        if name not in current:
            report.append(f"  + missing wrapper: {name}")
        elif name not in desired:
            report.append(f"  - orphan wrapper: {name}")
        elif desired[name] != current[name]:
            report.append(f"  ~ stale wrapper: {name}")
    return report


def write_wrappers(cc_skills_root: Path, desired: dict[str, str]) -> None:
    """Write desired wrappers; remove orphan wrapper dirs."""
    cc_skills_root.mkdir(parents=True, exist_ok=True)
    for name, content in desired.items():
        wdir = cc_skills_root / name
        wdir.mkdir(parents=True, exist_ok=True)
        target = wdir / "SKILL.md"
        if not target.is_file() or target.read_text(encoding="utf-8") != content:
            target.write_text(content, encoding="utf-8")
    for child in sorted(cc_skills_root.iterdir()):
        if not child.is_dir():
            continue
        if child.name in desired:
            continue
        # Orphan candidate. Only remove it if it is provably a
        # wrapper THIS generator authored (SKILL.md + GENERATED_MARKER).
        # Anything else — a hand-authored CC-plugin wrapper, an asset
        # dir, a dir without a SKILL.md — is LEFT in place + WARNed.
        if is_generated_wrapper(child):
            shutil.rmtree(child)
        else:
            print(
                f"generate_skill_wrappers: WARN unmanaged dir under "
                f".claude/skills/, not removed: {child.name}",
                file=sys.stderr,
            )


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", type=Path, default=None)
    ap.add_argument(
        "--check",
        action="store_true",
        help="fail (non-zero) if wrappers would change; no write",
    )
    args = ap.parse_args(argv)
    try:
        root = repo_root(args.repo or Path.cwd())
    except RepoRootError as exc:
        print(f"generate_skill_wrappers: ERROR {exc}", file=sys.stderr)
        return 1
    skills_root = root / "skills"
    cc_skills_root = root / ".claude" / "skills"

    if yaml is None:
        print("generate_skill_wrappers: SKIP — PyYAML missing", file=sys.stderr)
        return 0

    if not skills_root.is_dir():
        print(
            f"generate_skill_wrappers: missing {skills_root}", file=sys.stderr
        )
        return 1

    try:
        desired = build_desired(skills_root)
    except FrontmatterValueError as exc:
        print(f"generate_skill_wrappers: ERROR {exc}", file=sys.stderr)
        return 1
    except CollisionError as exc:
        print(f"generate_skill_wrappers: ERROR {exc}", file=sys.stderr)
        return 1

    current = current_wrappers(cc_skills_root)
    report = diff_report(desired, current)

    if args.check:
        if report:
            print("generate_skill_wrappers: drift detected (run without --check)")
            for line in report:
                print(line)
            return 1
        print("generate_skill_wrappers: OK (no drift)")
        return 0

    write_wrappers(cc_skills_root, desired)
    if report:
        print(f"generate_skill_wrappers: wrote {len(desired)} wrappers")
        for line in report:
            print(line)
    else:
        print(
            f"generate_skill_wrappers: {len(desired)} wrappers up to date"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
