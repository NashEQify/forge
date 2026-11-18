#!/usr/bin/env python3
"""Trusted standalone indexed evaluation, policy and buffered publication."""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType
from typing import cast


@dataclass(frozen=True)
class StandaloneReport:
    record: str
    lines: tuple[str, ...]
    blocking: bool


@dataclass(frozen=True)
class Evaluation:
    skill_status: str
    skill_detail: str
    checked_skills: tuple[str, ...]
    skipped: tuple[tuple[str, str], ...]
    skill_skipped: tuple[tuple[str, str], ...]
    blocks: tuple[tuple[str, str], ...]
    warnings: tuple[str, ...]


def unavailable(
    repo: Path,
    skill: ModuleType | None,
    detail: str,
    *,
    driver_missing: bool = False,
    related: ModuleType | None = None,
    framework_root: Path | None = None,
) -> StandaloneReport:
    if skill is None or driver_missing:
        status, reason = "SKIP", "availability: trusted validator program missing"
    elif skill.yaml is None:
        status, reason = "SKIP", "dependency: PyYAML missing"
    else:
        status, reason = "BLOCK", "input unavailable: " + detail
    payload = _base(repo)
    payload.update(
        skill_status=status,
        skill_detail=reason,
        detail=detail,
    )
    result = (
        None if related is None else related.unavailable_result(framework_root, detail)
    )
    return _report(payload, (), (), result, framework_root)


def _base(repo: Path) -> dict:
    return dict(
        version=1,
        mode="indexed",
        consumer=str(repo),
        git_dir=None,
        index=None,
        input_available=False,
        input_identity=None,
        detail="",
        checked_skills=[],
        skipped_paths=[],
        skill_skipped_paths=[],
        defect_paths=[],
        definitive=[],
        worktree_fallback_paths=[],
        related_file_mode="mixed",
        fully_indexed_related_files=False,
        limitations="Plan/evidence resolution retains working-tree or mixed inputs. "
        "Currentness is observed before publication; a subsequent commit is not transactional.",
    )


_RELATED_LIMITATIONS = (
    "Validator programs and framework/task-schema.yaml are trusted framework inputs, "
    "not candidate data. Plan gate paths escaping the project root resolve outside the "
    "candidate tree. Temporary space and time scale with candidate size. "
    "Currentness is observed before publication; a subsequent commit is not transactional."
)


_WORKTREE_LIMITATION = (
    " Framework root and consumer are the same repository: CLAUDE.md, AGENTS.md, "
    "framework/agent-autonomy.md (autonomy consistency) and framework/task-schema.yaml "
    "are read by the plan engine from the worktree, not from the candidate."
)


def _same_repository(payload: dict, framework_root: Path | None) -> bool:
    if framework_root is None:
        return False
    try:
        return Path(payload["consumer"]).resolve() == Path(framework_root).resolve()
    except OSError:
        return False


def _apply_related(payload: dict, related, framework_root: Path | None) -> None:
    """Record the related-file part of the report."""
    worktree_inputs = _same_repository(payload, framework_root)
    evaluated = related.plan_evaluated and related.evidence_evaluated
    payload.update(
        plan_status=related.plan_status,
        plan_detail=related.plan_detail,
        evidence_status=related.evidence_status,
        evidence_detail=related.evidence_detail,
        crossref_status=related.crossref_status,
        crossref_detail=related.crossref_detail,
        crossref_overflow=related.crossref_overflow,
        crossref_unresolved=list(related.crossref_unresolved),
        checked_reports=list(related.checked_reports),
        unresolved_links=list(related.unresolved_links),
        gitlink_paths=list(related.gitlinks),
        related_file_mode="indexed" if evaluated else "not-evaluated",
        fully_indexed_related_files=evaluated and not worktree_inputs,
        framework_inputs="worktree" if worktree_inputs else "framework",
        limitations=_RELATED_LIMITATIONS
        + (_WORKTREE_LIMITATION if worktree_inputs else ""),
    )
    if payload["definitive"]:
        if related.plan_evaluated:
            payload["definitive"].append(dict(check="plan", status=related.plan_status))
        if related.evidence_evaluated:
            payload["definitive"].append(
                dict(check="evidence", status=related.evidence_status)
            )
        if related.crossref_status in ("PASS", "WARN"):
            payload["definitive"].append(
                dict(check="crossref", status=related.crossref_status)
            )


def _report(
    payload: dict,
    warnings: tuple[str, ...],
    diagnostics: tuple[str, ...],
    related=None,
    framework_root: Path | None = None,
) -> StandaloneReport:
    lines = [] if related is None else list(related.plan_lines)
    lines.append(
        f"SKILL-FM-VALIDATE {payload['skill_status']} — {payload['skill_detail']}"
    )
    lines.extend("SKILL-FM-WARN: " + warning for warning in warnings)
    lines.extend(diagnostics)
    if related is not None:
        _apply_related(payload, related, framework_root)
        lines.extend(related.evidence_lines)
        lines.extend(related.crossref_lines)
    return StandaloneReport(
        json.dumps(payload, ensure_ascii=True, sort_keys=True),
        tuple(lines),
        payload["skill_status"] == "BLOCK"
        or (related is not None and related.plan_status == "BLOCK"),
    )


def _skill_path(path: str) -> bool:
    return (
        path.startswith("skills/")
        and path.endswith("/SKILL.md")
        and "/_archived/" not in path
    )


def evaluate_candidate(candidate, skill: ModuleType | None) -> Evaluation:
    from lib.indexed_candidate import InputUnavailable, read_blob

    paths = tuple(os.fsdecode(entry.path) for entry in candidate.entries)
    known = frozenset(
        path.split("/")[1][:-3]
        for path in paths
        if path.startswith("agents/")
        and path.count("/") == 1
        and path.endswith(".md")
        and path.split("/")[1][:-3] not in ("README", "navigation")
    )
    if skill is None:
        skill_status, skill_detail = (
            "SKIP",
            "availability: trusted skill validator missing",
        )
    elif skill.yaml is None:
        skill_status, skill_detail = "SKIP", "dependency: PyYAML missing"
    elif not any(path.startswith("skills/") for path in paths):
        skill_status, skill_detail = "SKIP", "no skills/ candidate membership"
    else:
        skill_status, skill_detail = "PASS", "indexed candidate; explicit empty scope"
    checked_skills, skipped, skill_skipped = [], [], []
    blocks, warnings = [], []
    cache: dict[bytes, str | Exception] = {}
    for entry in candidate.changed:
        path = os.fsdecode(entry.path)
        do_skill = skill_status != "SKIP" and _skill_path(path)
        if not _skill_path(path) and (
            path.endswith("/SKILL.md") or path.endswith("\\SKILL.md")
        ):
            skill_skipped.append((path, "outside skill scope or archived"))
        if not do_skill:
            skipped.append((path, "outside available standalone scope"))
            continue
        checked_skills.append(path)
        try:
            if entry.mode not in (b"100644", b"100755"):
                raise InputUnavailable(
                    "unsupported relevant mode " + os.fsdecode(entry.mode)
                )
            if entry.oid not in cache:
                try:
                    cache[entry.oid] = read_blob(
                        candidate.selection, os.fsdecode(entry.oid)
                    ).decode("utf-8")
                except (InputUnavailable, UnicodeError, OSError) as exc:
                    cache[entry.oid] = exc
            text = cache[entry.oid]
            if isinstance(text, Exception):
                raise InputUnavailable(str(text))
        except InputUnavailable as exc:
            blocks.append((path, "input unavailable: " + str(exc)))
            continue
        try:
            result = cast(ModuleType, skill).evaluate_skill(path, text, known)
            blocks.extend((path, block) for block in result.blocks)
            warnings.extend(result.warnings)
        except Exception as exc:
            blocks.append((path, f"input unavailable: skill evaluator {exc}"))
    skipped.extend((os.fsdecode(path), reason) for path, reason in candidate.skipped)
    if blocks:
        skill_status, skill_detail = "BLOCK", "indexed content invalid/unavailable"
    elif checked_skills:
        skill_detail = "indexed candidate content"
    return Evaluation(
        skill_status,
        skill_detail,
        tuple(checked_skills),
        tuple(skipped),
        tuple(skill_skipped),
        tuple(blocks),
        tuple(warnings),
    )


def run(
    repo: Path,
    skill: ModuleType | None,
    related: ModuleType | None = None,
    framework_root: Path | None = None,
) -> StandaloneReport:
    """Without ``related`` this is the plain standalone run."""
    from lib.indexed_candidate import capture_candidate, compare_candidate

    if related is not None and framework_root is None:
        framework_root = Path(__file__).resolve().parent.parent
    try:
        candidate = capture_candidate(repo)
        evaluated = evaluate_candidate(candidate, skill)
        related_result = (
            None if related is None else related.evaluate(candidate, framework_root)
        )
        compare_candidate(candidate)
    except Exception as exc:
        return unavailable(
            repo, skill, str(exc), related=related, framework_root=framework_root
        )
    observation = candidate.observation
    payload = _base(repo)
    payload.update(
        input_available=True,
        consumer=observation.consumer,
        git_dir=observation.git_dir,
        index=observation.index,
        input_identity=dict(
            head=observation.head,
            raw_index=observation.raw_index.digest,
            index_stat=observation.raw_index.stat,
            mapping=hashlib.sha256(
                repr(observation.stages).encode("ascii")
            ).hexdigest(),
            delta=hashlib.sha256(observation.delta).hexdigest(),
        ),
        detail="stable captured input; final comparison matched",
        skill_status=evaluated.skill_status,
        skill_detail=evaluated.skill_detail,
        checked_skills=evaluated.checked_skills,
        skipped_paths=evaluated.skipped,
        skill_skipped_paths=evaluated.skill_skipped,
        defect_paths=sorted({path for path, _ in evaluated.blocks}),
        definitive=[dict(check="skill", status=evaluated.skill_status)],
    )
    diagnostics = tuple(
        f"  {json.dumps(path, ensure_ascii=True)}: {message}"
        for path, message in evaluated.blocks
    )
    return _report(
        payload, evaluated.warnings, diagnostics, related_result, framework_root
    )
