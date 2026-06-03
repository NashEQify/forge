#!/usr/bin/env python3
"""
Regenerate the workflow-router skill SoT from the workflow set.

`skills/workflow_router/SKILL.md` is the single injected wrapper that
makes forge's workflows *discoverable* — the harness scans a directory
of `SKILL.md` descriptions and injects each `description` into the
available-skills system-reminder, so a workflow can be reached for at
the moment of need instead of only via a pull-consult of
`framework/process-map.md`. The router is ONE user-facing utility skill
that points TO the workflows; it carries no workflow methodology.

The whole file is generated (frontmatter + thin body), byte-identical
on re-run, carrying the standard generated-by marker. This is the
`generate_skill_wrappers.py` whole-file precedent (not the
marker-region precedent), so there is no hand-region to preserve and
idempotence is trivial.

Source of the catalogue: each `workflows/runbooks/*/workflow.yaml`
gains a one-line `need_phrase:` field — a curated, need-shaped clause.
The generator reads `need_phrase:` verbatim (byte-deterministic
source). A missing / empty `need_phrase:` in any workflow.yaml is a
HARD error (non-zero exit, NO partial write) — parity with
`generate_skill_wrappers.py` collision handling. A runbook directory
with no `workflow.yaml` is skipped + WARNed (a known
`validate_runbook_consistency` gap, not this generator's to gate).

CHAINED-RUN ORDERING ([DISCIPLINE], not mechanically enforced):
regenerate this SoT BEFORE running `generate_skill_wrappers.py`. The
wrapper reads this SoT, so against a STALE router SoT it regenerates
cleanly and its `--check` passes GREEN on stale content. No automated
seam sequences the two — the net is `--check`: run
`generate_workflow_router.py --check` (or `consistency_check`) before
commit to catch router drift, exactly as for wrapper drift. Same
WARN-class generator-drift discipline as every other generated
artifact, not a stronger guarantee.

CLI mirrors generate_skill_wrappers.py / generate_skill_map.py:
  default     write skills/workflow_router/SKILL.md (idempotent,
              byte-identical on re-run)
  --check     verify-only; non-zero exit on any drift vs a fresh
              generation; no write.

Standalone script: reads workflows/runbooks/*/workflow.yaml, writes
only skills/workflow_router/SKILL.md. No framework-runtime import.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    yaml = None  # type: ignore

# Stable body sentinel — the SKILL.md is fully generated; nothing in it
# is hand-maintained. Mirrors generate_skill_wrappers.py's marker shape.
GENERATED_MARKER = (
    "<!-- generated-by: scripts/generate_workflow_router.py "
    "(do not hand-edit) -->"
)

ROUTER_DIR = "workflow_router"
ROUTER_NAME = "workflow-router"

DESC_PREFIX = "forge workflow router — Use when you need to: "
DESC_SUFFIX = "; → open process-map.md and start via workflow_engine."

INSTRUCTION = (
    "Match a need → open `framework/process-map.md` → start it: "
    "`python3 scripts/workflow_engine.py --start <name> --task <id>`"
)


class RepoRootError(RuntimeError):
    """No `framework/` ancestor — refuse to guess the repo root."""


class WorkflowSourceError(RuntimeError):
    """A workflow.yaml is missing a usable `need_phrase:` field."""


def repo_root(start: Path) -> Path:
    """
    Resolve the repo root as the nearest ancestor containing a
    `framework/` dir. No such ancestor → hard error (RepoRootError),
    never a `start.resolve()` fallback — parity with
    generate_skill_wrappers.py: a silent fallback would let the
    generator materialize the router SoT in the wrong tree.
    """
    cur = start.resolve()
    for parent in [cur] + list(cur.parents):
        if (parent / "framework").is_dir():
            return parent
    raise RepoRootError(
        f"no `framework/` ancestor of {cur} — cannot locate the repo "
        f"root; refusing to write skills/{ROUTER_DIR}/SKILL.md into an "
        f"unknown tree (pass --repo <repo-root>)"
    )


def iter_workflows(runbooks_root: Path) -> list[tuple[str, dict]]:
    """
    Walk workflows/runbooks/*/workflow.yaml (sorted by dir name for
    determinism). A runbook dir with no workflow.yaml is skipped +
    WARNed (known validate_runbook_consistency gap, not gated here).
    A workflow.yaml that fails to parse is a HARD error.
    """
    out: list[tuple[str, dict]] = []
    if not runbooks_root.is_dir():
        return out
    for child in sorted(runbooks_root.iterdir()):
        if not child.is_dir():
            continue
        if child.name.startswith("_"):
            continue
        yf = child / "workflow.yaml"
        if not yf.is_file():
            print(
                f"generate_workflow_router: WARN {child.name} — no "
                f"workflow.yaml; skipped",
                file=sys.stderr,
            )
            continue
        text = yf.read_text(encoding="utf-8")
        try:
            data = yaml.safe_load(text)
        except yaml.YAMLError as exc:
            raise WorkflowSourceError(
                f"{child.name}/workflow.yaml — YAML failed to parse "
                f"({exc.__class__.__name__}); no router written"
            ) from exc
        if not isinstance(data, dict):
            raise WorkflowSourceError(
                f"{child.name}/workflow.yaml — not a YAML mapping; "
                f"no router written"
            )
        out.append((child.name, data))
    return out


def need_phrases(
    workflows: list[tuple[str, dict]],
) -> list[tuple[str, str]]:
    """
    Extract (dir_name, need_phrase) for every workflow. A missing /
    empty / non-str `need_phrase:` is a HARD error (non-zero, no
    write) — the field is the byte-deterministic catalogue source.
    """
    out: list[tuple[str, str]] = []
    for dir_name, data in workflows:
        phrase = data.get("need_phrase")
        if not isinstance(phrase, str) or not phrase.strip():
            raise WorkflowSourceError(
                f"{dir_name}/workflow.yaml — missing / empty "
                f"`need_phrase:` (required catalogue source); "
                f"no router written"
            )
        out.append((dir_name, phrase.strip()))
    return out


def render_description(phrases: list[tuple[str, str]]) -> str:
    """
    Build the §4.2 catalogue description (folded, one line after
    safe_dump): prefix + the need_phrases joined "; " + suffix.
    """
    catalog = "; ".join(phrase for _, phrase in phrases)
    return DESC_PREFIX + catalog + DESC_SUFFIX


def render_body(phrases: list[tuple[str, str]]) -> str:
    """
    Thin generated body: one sign-post sentence, the generated-by
    marker, a workflow → use-case → runbook table built from the
    workflow set, and the single start-instruction line.
    """
    lines = [
        "# Skill: workflow-router",
        "",
        GENERATED_MARKER,
        "",
        "This is forge's workflow discovery router — one injected "
        "sign-post that points to the workflow runbooks. It carries no "
        "workflow methodology; the runbooks (`workflows/runbooks/"
        "<name>/WORKFLOW.md`) and `framework/process-map.md` are the "
        "SoT.",
        "",
        "| Workflow | Use case | Runbook |",
        "|---|---|---|",
    ]
    for dir_name, phrase in phrases:
        runbook = f"`workflows/runbooks/{dir_name}/WORKFLOW.md`"
        lines.append(f"| `{dir_name}` | {phrase} | {runbook} |")
    lines += [
        "",
        INSTRUCTION,
        "",
    ]
    return "\n".join(lines)


def render_skill(phrases: list[tuple[str, str]]) -> str:
    """
    Render the whole SKILL.md (frontmatter + thin body).

    The frontmatter block is serialized via ``yaml.safe_dump`` with the
    same call shape as generate_skill_wrappers.py's render_wrapper
    (`sort_keys=False`, `allow_unicode=True`, `width=10**9`), so the
    description scalar never line-wraps and output is byte-identical
    run-vs-run.
    """
    description = render_description(phrases)
    front_block = yaml.safe_dump(
        {
            "name": ROUTER_NAME,
            "description": description,
            "status": "active",
            "invocation": {"primary": "user-facing"},
            "disable-model-invocation": False,
        },
        sort_keys=False,
        allow_unicode=True,
        default_flow_style=False,
        width=10**9,  # never line-wrap the description scalar
    )
    front = f"---\n{front_block}---\n\n"
    return front + render_body(phrases)


def build_skill(repo: Path) -> str:
    """Build the router SKILL.md content from the workflow set."""
    runbooks_root = repo / "workflows" / "runbooks"
    workflows = iter_workflows(runbooks_root)
    if not workflows:
        raise WorkflowSourceError(
            f"no workflow.yaml found under {runbooks_root}; "
            f"no router written"
        )
    phrases = need_phrases(workflows)
    return render_skill(phrases)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", type=Path, default=None)
    ap.add_argument(
        "--check",
        action="store_true",
        help="fail (non-zero) if the router SKILL.md would change; no write",
    )
    args = ap.parse_args(argv)

    try:
        root = repo_root(args.repo or Path.cwd())
    except RepoRootError as exc:
        print(f"generate_workflow_router: ERROR {exc}", file=sys.stderr)
        return 1

    if yaml is None:
        print(
            "generate_workflow_router: SKIP — PyYAML missing",
            file=sys.stderr,
        )
        return 0

    out_path = root / "skills" / ROUTER_DIR / "SKILL.md"

    try:
        content = build_skill(root)
    except WorkflowSourceError as exc:
        print(f"generate_workflow_router: ERROR {exc}", file=sys.stderr)
        return 1

    current = (
        out_path.read_text(encoding="utf-8") if out_path.is_file() else None
    )

    if args.check:
        if current != content:
            print(
                "generate_workflow_router: drift detected "
                "(run without --check)"
            )
            if current is None:
                print(f"  + missing router SKILL.md: {out_path}")
            else:
                print(f"  ~ stale router SKILL.md: {out_path}")
            return 1
        print("generate_workflow_router: OK (no drift)")
        return 0

    if current == content:
        print("generate_workflow_router: router SKILL.md up to date")
        return 0

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(content, encoding="utf-8")
    print(f"generate_workflow_router: wrote {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
