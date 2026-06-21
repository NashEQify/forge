"""_plan_engine.rendering — output formatters (the 9 fmt_* functions).

Renders the loaded + computed model into the CLI surfaces (--boot / --status /
--next / --critical-path / --check / --after / --spec-pipeline / --validate /
--dashboard-json). Output strings are load-bearing: the pre-commit PLAN-VALIDATE
BLOCK greps fmt_validate's "Summary: 0 errors" / "CLEAN:" lines.

Split out of the former monolithic scripts/plan_engine.py.
"""

from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime, timedelta, timezone


from _plan_engine.core import (
    EFFORT_WEIGHTS,
    ValidationIssue,
    _format_tid,
)
from _plan_engine.compute import (
    _hashable_cp_set,
    _render_cp_item,
    compute_active_milestone_task_chain,
    compute_phase_progress,
)
from _plan_engine.loading import _milestone_archived_credit


def fmt_boot(tasks, milestones, target, north_star, op_intent, critical_path,
             blocking_scores, next_actions, issues, aggregate=False):
    lines = []
    lines.append(f"TARGET: {target} ({milestones[target].title})" if target in milestones else f"TARGET: {target}")
    lines.append("")

    # Critical path (Mixed-Items via _render_cp_item)
    if critical_path:
        cp_labels = [_render_cp_item(item, tasks) for item in critical_path]
        total_effort = 0
        has_effort_item = False  # any int task-id item that carries effort.
        for item in critical_path:
            if isinstance(item, int) and not isinstance(item, bool):
                t = tasks.get(item)
                if t is not None:
                    total_effort += t.effort_weight
                    has_effort_item = True
        lines.append(f"CRITICAL PATH -> {target}:")
        lines.append(f"  {' -> '.join(cp_labels)}")
        # suppress the effort line for a milestone-key (string)
        # spine — a structural 0 reads as a real metric when it is not one.
        if has_effort_item:
            lines.append(f"  Effort-weighted length: {total_effort}")
        # Bottleneck: first non-done task on path (only int items count)
        for item in critical_path:
            if isinstance(item, int) and not isinstance(item, bool):
                t = tasks.get(item)
                if t is not None and not t.is_done:
                    lines.append(f"  Bottleneck: Task {_format_tid(t)} ({t.title[:40]})")
                    break
        # nest the live active-milestone task chain under the
        # milestone spine so a boot read answers "what's the next critical-path
        # task" without a manual plan.yaml read.
        lines.extend(_fmt_active_chain_block(tasks, milestones, target))
    lines.append("")

    # In progress
    in_progress = sorted([t for t in tasks.values() if t.status == "in_progress"],
                         key=lambda t: (t._repo, t.id))
    lines.append(f"IN PROGRESS ({len(in_progress)}):")
    for t in in_progress:
        summary = f" — {t.summary[:60]}" if t.summary else ""
        lines.append(f"  [{_format_tid(t)}] {t.title[:40]} ({t.milestone}){summary}")
    lines.append("")

    # Next actions
    lines.append("NEXT ACTIONS:")
    for i, tid in enumerate(next_actions, 1):
        t = tasks[tid]
        cp_flag = "  CRITICAL_PATH" if tid in _hashable_cp_set(critical_path) else ""
        bs = blocking_scores.get(tid, 0)
        lines.append(
            f"  {i}. [{_format_tid(t)}] {t.title[:45]} ({t.milestone}) "
            f"effort:{t.effort}  blocking:{bs}{cp_flag}"
        )
    lines.append("")

    # Milestones
    lines.append("MILESTONES:")
    status_order = {"done": 0, "active": 1, "ready": 2, "blocked": 3, "future": 4}
    sorted_ms = sorted(milestones.values(), key=lambda m: status_order.get(m.status, 9))
    # Dynamic width for aggregate mode (milestone keys get longer with "<repo>:" prefix)
    ms_width = max((len(m.key) for m in sorted_ms), default=25)
    ms_width = max(ms_width, 25)
    for m in sorted_ms:
        # Archive-Awareness: terminal tasks MOVED to docs/tasks/archive/ leave
        # m.tasks (loader is non-recursive), so credit them additively here.
        # archived terminal -> +1 done AND +1 total (no-archive / aggregate ->
        # +0). is_terminal surface, so done_only=False.
        archived_credit = _milestone_archived_credit(m, tasks, aggregate=aggregate)
        task_count = len(m.tasks) + archived_credit
        done_count = sum(1 for tid in m.tasks if tid in tasks and tasks[tid].is_terminal) + archived_credit
        detail = ""
        if m.status == "blocked":
            blockers = [r for r in m.requires if milestones.get(r) and milestones[r].status != "done"]
            detail = f"  by: {', '.join(str(b) for b in blockers)}"
        elif m.status == "active" and m.gate:
            failed_gates = [str(g) for g in m.gate if not g.check(tasks)[0]]
            if failed_gates:
                detail = f"  (gate: {', '.join(g[:30] for g in failed_gates)})"
        status_sym = {"done": "done", "active": "active", "ready": "ready",
                      "blocked": "BLOCKED", "future": "future"}.get(m.status, m.status)
        lines.append(f"  {status_sym:8s} {m.key:{ms_width}s} {done_count}/{task_count}{detail}")
        # feature_milestones-spezifische Sub-Zeilen
        if getattr(m, "feature", ""):
            lines.append(f"             feature: {m.feature[:80]}")
        if getattr(m, "app_status_post_milestone", ""):
            lines.append(f"             app_status: {m.app_status_post_milestone[:80]}")
    lines.append("")

    # Warnings
    errors = [i for i in issues if i.severity == "ERROR"]
    warns = [i for i in issues if i.severity == "WARN"]
    if errors or warns:
        lines.append("WARNINGS:")
        for issue in (errors + warns)[:10]:
            loc = _fmt_issue_loc(issue)  # shared helper handles global issues
            prefix = f"{loc} — " if loc else ""
            lines.append(f"  {issue.check}: {prefix}{issue.detail}")
        remaining = len(errors) + len(warns) - 10
        if remaining > 0:
            lines.append(f"  ... and {remaining} more")

    return "\n".join(lines)


def fmt_status(tasks, milestones, aggregate=False):
    """Milestone-Overview. zeigt
    feature_milestones-spezifische Felder (feature, app_status_post_milestone)
    inline wenn vorhanden."""
    lines = []
    status_order = {"done": 0, "active": 1, "ready": 2, "blocked": 3, "future": 4}
    sorted_ms = sorted(milestones.values(), key=lambda m: status_order.get(m.status, 9))
    ms_width = max((len(m.key) for m in sorted_ms), default=25)
    ms_width = max(ms_width, 25)
    # Running sum of the per-milestone archived credit, reused for the Total
    # below so the Total's archived contribution == the sum of the lines'.
    total_archived_credit = 0
    for m in sorted_ms:
        # Archive-Awareness: see fmt_boot — credit archived terminal tasks that
        # left m.tasks on archival (no-archive / aggregate -> +0, byte-identical).
        archived_credit = _milestone_archived_credit(m, tasks, aggregate=aggregate)
        total_archived_credit += archived_credit
        task_count = len(m.tasks) + archived_credit
        done_count = sum(1 for tid in m.tasks if tid in tasks and tasks[tid].is_terminal) + archived_credit
        lines.append(f"  {m.status:8s} {m.key:{ms_width}s} {m.title:30s} {done_count}/{task_count}")
        # feature_milestones-spezifische Sub-Zeilen
        if getattr(m, "feature", ""):
            lines.append(f"           feature: {m.feature}")
        if getattr(m, "app_status_post_milestone", ""):
            lines.append(f"           app_status: {m.app_status_post_milestone}")
        if getattr(m, "parallel_to", []):
            lines.append(f"           parallel_to: {', '.join(m.parallel_to)}")
        # Pre-Set-Gates mit preliminary-Marker
        if any(getattr(g, "preliminary", False) for g in m.gate):
            preliminary_count = sum(1 for g in m.gate if getattr(g, "preliminary", False))
            lines.append(f"           gates: {preliminary_count} preliminary")
    # Archived credit on the Total is the SUM of the per-milestone archived
    # credits accumulated above. Each per-milestone line adds its
    # _milestone_archived_credit to BOTH its numerator and denominator, so the
    # Total mirrors that exactly: total_archived_credit -> +numerator AND
    # +denominator. This guarantees, in any single --status render, that the
    # Total's archived contribution == the sum of the lines' archived
    # contributions — an orphan-milestone archived task (milestone not a
    # plan.yaml key) is credited in NEITHER, instead of the old unfiltered sweep
    # that credited it in the Total but in no line. Aggregate -> +0 (the per-
    # milestone credit is already a no-op there), byte-identical no-archive.
    #
    # The Total numerator counts is_terminal (done + superseded + wontfix +
    # absorbed) — the SAME completion semantic as the per-milestone lines above
    # (done_count uses is_terminal) and as compute_milestone_status /
    # compute_phase_progress. Previously the Total counted is_done (strict),
    # which made it disagree with the lines it summarises: per-milestone lines
    # summed to N done while the Total read a smaller N' (the gap = loaded
    # terminal-not-done tasks: superseded/wontfix/absorbed). is_terminal is the
    # milestone-completion authority, so it is canonical here.
    #
    # One PRE-EXISTING difference is deliberately LEFT: a loaded task with an
    # orphan milestone (milestone not a plan.yaml key) is in the Total
    # denominator (len(tasks)) but in no per-milestone bucket. That is a
    # denominator/orphan concern, separate from this numerator-semantic fix.
    total = len(tasks) + total_archived_credit
    total_done = sum(1 for t in tasks.values() if t.is_terminal) + total_archived_credit
    lines.append(f"\nTotal: {total_done}/{total} tasks done")
    return "\n".join(lines)


def fmt_next(tasks, next_actions, critical_path, blocking_scores):
    lines = [f"NEXT ACTIONS ({len(next_actions)}):"]
    cp_set = _hashable_cp_set(critical_path)
    for i, tid in enumerate(next_actions, 1):
        t = tasks[tid]
        cp = " CRITICAL_PATH" if tid in cp_set else ""
        bs = blocking_scores.get(tid, 0)
        lines.append(f"  {i}. [{_format_tid(t)}] {t.title[:50]} ({t.milestone}) effort:{t.effort} blocking:{bs}{cp}")
    return "\n".join(lines)


_VALID_EFFORTS = frozenset(EFFORT_WEIGHTS)  # {"S","M","L","XL"}


def _fmt_active_chain_block(tasks, milestones, target, indent="  "):
    """render the active-milestone task chain as nested lines.

    Returns a list of rendered lines (possibly empty when no chain resolves —
    degrade). Shared by fmt_critical_path + fmt_boot.

    the data comes from a SINGLE compute_active_milestone_task_chain
    call — the same function the 13 self-test TCs exercise. This renderer does
    NOT re-implement the resolve -> gate -> topo orchestration, so the shipped
    path is exactly the tested path (no divergence twin). The header label
    (`m.key`), the chain content, and the cycle flag all come from that one
    result.

    the active milestone is resolved exactly ONCE — inside the public
    function — and reused here via `result.milestone` for the header. This
    renderer does NOT resolve again, so the label and the content can never
    point at different milestones, AND the resolve (a BFS+topo over the
    requires-graph) runs once per render, not twice. The cycle WARN is emitted
    by the public function (orchestration owner); this renderer must not
    re-emit it.
    """
    result = compute_active_milestone_task_chain(tasks, milestones, target)
    m = result.milestone
    chain = result.chain
    if m is None or not chain:
        return []
    lines = [f"{indent}ACTIVE-MILESTONE TASK PATH ({m.key}):"]
    # Known limitation: in aggregate mode
    # _render_cp_item's str-branch returns the bare '<repo>#<id>' key (no title);
    # the status mark below is appended outside the renderer. Single-repo int
    # keys render '[id] title' inside _render_cp_item. Cosmetic only — the id is
    # present and `Next on chain:` still renders the title. Not widened here.
    labels = []
    chain_effort = 0
    unset_effort = 0  # tasks with no explicit {S,M,L,XL} effort.
    for key in chain:
        t = tasks.get(key)
        if t is not None:
            chain_effort += t.effort_weight
            if t.effort not in _VALID_EFFORTS:
                unset_effort += 1
            status_mark = "done" if t.is_done else t.status
            labels.append(f"{_render_cp_item(key, tasks)} [{status_mark}]")
        else:
            labels.append(_render_cp_item(key, tasks))
    lines.append(f"{indent}  {' -> '.join(labels)}")
    # the chain-effort metric must be honest. A task with no
    # explicit {S,M,L,XL} effort silently contributes the default weight (3);
    # presenting that as an exact number is the same misleading-metric class as
    # the zero placeholder. Mark it estimated and name the unset count so the
    # reader never reads a defaulted weight as a measured estimate.
    if unset_effort:
        plural = "s" if unset_effort != 1 else ""
        lines.append(
            f"{indent}  Chain effort-weighted length: ~{chain_effort} "
            f"({unset_effort} task{plural} effort-unset, counted as M)"
        )
    else:
        lines.append(f"{indent}  Chain effort-weighted length: {chain_effort}")
    # Bottleneck: first non-done task on the chain.
    for key in chain:
        t = tasks.get(key)
        if t is not None and not t.is_done:
            lines.append(f"{indent}  Next on chain: [{_format_tid(t)}] {t.title[:40]}")
            break
    return lines


def fmt_critical_path(tasks, critical_path, target, milestones=None):
    """Mixed-Item-Render via _render_cp_item.
    Items koennen sein: int task-id, str milestone-key, list[str] parallel,
    str post-MVP-Beschreibung.

    when `milestones` is supplied, the live active-milestone task
    chain (gate -> blocked_by) is nested under the milestone spine.
    """
    if not critical_path:
        return f"No critical path to {target} (no pending tasks in scope)"
    lines = [f"CRITICAL PATH -> {target}:"]
    total = 0
    has_effort_item = False  # any int task-id item that carries effort.
    for item in critical_path:
        rendered = _render_cp_item(item, tasks)
        if isinstance(item, int) and not isinstance(item, bool):
            t = tasks.get(item)
            if t is not None:
                total += t.effort_weight
                has_effort_item = True
                done_mark = "done" if t.is_done else t.status
                lines.append(f"  {rendered} ({t.milestone}) effort:{t.effort} [{done_mark}]")
            else:
                lines.append(f"  {rendered} (archived)")
        elif isinstance(item, list):
            # Parallel-Liste: explizit als parallel-Marker rendern
            lines.append(f"  {rendered}  [parallel]")
        else:
            lines.append(f"  {rendered}")
    # a milestone-key (string) spine has no effort-bearing items,
    # so the sum is a structural 0 — a rendered "0" reads as a real metric when
    # it is not one. Only show the effort line when the spine actually carries
    # effort-bearing task items.
    if has_effort_item:
        lines.append(f"\nTotal effort-weighted length: {total}")
    # nest the active-milestone task chain under the spine.
    if milestones is not None:
        chain_lines = _fmt_active_chain_block(tasks, milestones, target)
        if chain_lines:
            lines.append("")
            lines.extend(chain_lines)
    return "\n".join(lines)


def fmt_check(milestones, tasks, milestone_key=None):
    lines = []
    targets = [milestone_key] if milestone_key else list(milestones.keys())
    all_pass = True
    for key in targets:
        m = milestones.get(key)
        if not m:
            lines.append(f"MILESTONE: {key}  [NOT FOUND]")
            all_pass = False
            continue
        if not m.gate:
            lines.append(f"MILESTONE: {key}  [NO GATE]  status={m.status}")
            continue
        gate_pass = True
        lines.append(f"MILESTONE: {key}  [{m.status.upper()}]")
        for g in m.gate:
            ok, detail = g.check(tasks)
            sym = "✓" if ok else "✗"
            lines.append(f"  {sym} {g}  ({detail})")
            if not ok:
                gate_pass = False
        passed = sum(1 for g in m.gate if g.check(tasks)[0])
        lines.append(f"RESULT: {passed}/{len(m.gate)} conditions passed")
        if not gate_pass:
            all_pass = False
        lines.append("")
    return "\n".join(lines), all_pass


def fmt_after(tasks, milestones, task_id, blocking_scores):
    # task_id may be int (single-repo) or str "repo#id" (aggregate).
    t = tasks.get(task_id)
    if not t:
        return f"Task {task_id} not found"

    lines = [f"COMPLETING Task {_format_tid(t)} ({t.title}):"]
    lines.append("")

    # Find directly unblocked tasks
    done_keys = {tk for tk, tt in tasks.items() if tt.is_done}
    simulated_done = done_keys | {task_id}

    directly_unblocked = []
    for other in tasks.values():
        if other.key == task_id or other.is_terminal:
            continue
        if task_id not in other.blocked_by:
            continue
        if all(d in simulated_done for d in other.blocked_by):
            directly_unblocked.append(other)

    if directly_unblocked:
        lines.append("DIRECTLY UNBLOCKED:")
        for u in directly_unblocked:
            lines.append(f"  [{_format_tid(u)}] {u.title[:50]} -> becomes READY")
    else:
        lines.append("DIRECTLY UNBLOCKED: none")
    lines.append("")

    # Milestone impact
    m = milestones.get(t.milestone)
    if m and m.gate:
        lines.append("MILESTONE IMPACT:")
        for g in m.gate:
            ok, detail = g.check(tasks)
            sym = "✓" if ok else "pending"
            lines.append(f"  {m.key}: {g} ({sym}: {detail})")
    lines.append("")

    # Chain effect (blocking score)
    bs = blocking_scores.get(task_id, 0)
    lines.append(f"TOTAL CHAIN EFFECT: {bs} tasks transitively unblocked")

    return "\n".join(lines)


def fmt_spec_pipeline(tasks: dict) -> str:
    """Format spec pipeline report showing per-spec review progress.

    Only includes tasks with non-empty spec_states and non-terminal status
    (excluding superseded/absorbed). Detects duplicate spec ownership.

    uses t.key (namespaced in aggregate mode) for task references.
    """
    # Collect specs from active tasks
    spec_entries: list = []  # (spec_name, state, task_key)
    seen_specs: dict[str, list] = defaultdict(list)  # spec → task_keys
    duplicates: list[str] = []

    for t in sorted(tasks.values(), key=lambda x: (x._repo, x.id)):
        if t.status in {"superseded", "absorbed"}:
            continue
        if not t.spec_states or not isinstance(t.spec_states, dict):
            continue
        for spec_name, state in t.spec_states.items():
            spec_entries.append((spec_name, state, t.key))
            seen_specs[spec_name].append(t.key)

    # Detect duplicates
    for spec_name, task_keys in seen_specs.items():
        if len(task_keys) > 1:
            ids_str = " and ".join(str(tk) for tk in task_keys)
            duplicates.append(f"DUPLICATE: {spec_name} in Task {ids_str}")

    if not spec_entries and not duplicates:
        return "SPEC PIPELINE:\n  (no specs tracked)"

    lines = ["SPEC PIPELINE:"]

    # Duplicate warnings first
    for dup in duplicates:
        lines.append(f"  {dup}")
    if duplicates:
        lines.append("")

    # Spec lines
    for spec_name, state, task_key in spec_entries:
        phase = state.get("current_phase", "?")
        review_passes = state.get("review_passes", 0)
        fix_passes = state.get("fix_passes", 0)

        # Truncate spec name to 30 chars
        display_name = spec_name[:27] + "..." if len(spec_name) > 30 else spec_name

        # Build pass/fix info (omit if 0)
        pass_info = f"Pass {review_passes}" if review_passes else ""
        fix_info = f"Fix {fix_passes}" if fix_passes else ""
        detail_parts = [p for p in [pass_info, fix_info] if p]
        detail = "  ".join(detail_parts)

        lines.append(
            f"  {display_name:30s} {phase:10s} {detail:16s} [Task {task_key}]"
        )

    # Aggregate
    lines.append("")
    phase_counts: dict[str, int] = defaultdict(int)
    total_specs = 0
    task_set: set = set()
    seen_agg: set[str] = set()
    for _spec_name, state, task_key in spec_entries:
        if _spec_name in seen_agg:
            continue
        seen_agg.add(_spec_name)
        phase = state.get("current_phase", "unknown")
        phase_counts[phase] += 1
        total_specs += 1
        task_set.add(task_key)

    ready_count = phase_counts.get("ready", 0)
    non_ready = total_specs - ready_count
    lines.append("AGGREGATE:")
    lines.append(
        f"  spec-readiness:  {ready_count}/{total_specs} ready"
        f" ({non_ready} raw/reviewing/fixing)"
    )
    lines.append(
        f"  Total tracked:   {total_specs} specs across {len(task_set)} tasks"
    )

    return "\n".join(lines)


def _fmt_issue_loc(i: ValidationIssue) -> str:
    """Location-Prefix fuer Validate-Ausgabe. Globale Checks (ohne task/milestone)
    bekommen keinen Prefix, nur den Check-Namen + detail."""
    if i.task_id:
        return f"Task {i.task_id}"
    if i.milestone_key:
        return f"Milestone {i.milestone_key}"
    return ""  # global issue (z.B. AUTONOMY_*)


def fmt_validate(issues):
    errors = [i for i in issues if i.severity == "ERROR"]
    warns = [i for i in issues if i.severity == "WARN"]
    lines = []
    if errors:
        lines.append(f"ERRORS ({len(errors)}):")
        for i in errors:
            loc = _fmt_issue_loc(i)
            if loc:
                lines.append(f"  {i.check}: {loc} — {i.detail}")
            else:
                lines.append(f"  {i.check}: {i.detail}")
    if warns:
        lines.append(f"\nWARNINGS ({len(warns)}):")
        for i in warns:
            loc = _fmt_issue_loc(i)
            if loc:
                lines.append(f"  {i.check}: {loc} — {i.detail}")
            else:
                lines.append(f"  {i.check}: {i.detail}")
    if not errors and not warns:
        lines.append("CLEAN: no issues found")
    else:
        lines.append(f"\nSummary: {len(errors)} errors, {len(warns)} warnings")
    return "\n".join(lines), len(errors) == 0


def fmt_dashboard_json(tasks, milestones, target, north_star, op_intent,
                       critical_path, blocking_scores, next_actions, issues,
                       phases=None, aggregate=False):
    now = datetime.now(timezone(timedelta(hours=2)))  # CEST

    ms_list = []
    for m in milestones.values():
        gate_results = []
        for g in m.gate:
            ok, detail = g.check(tasks)
            gate_results.append({
                "type": g.type, "spec": str(g), "pass": ok, "detail": detail
            })
        milestone_tasks = [tid for tid in m.tasks if tid in tasks]
        done_count = sum(1 for tid in milestone_tasks if tasks[tid].is_terminal)
        in_progress_count = sum(1 for tid in milestone_tasks if tasks[tid].status == "in_progress")
        pending_count = len(milestone_tasks) - done_count - in_progress_count
        # Archive-Awareness: same is_terminal surface as fmt_boot / fmt_status —
        # archived terminal tasks that left m.tasks credit BOTH done and total
        # (they are terminal, so never in_progress / pending). no-archive /
        # aggregate -> +0, byte-identical. Keeps --dashboard-json's milestone
        # fraction in agreement with --boot / --status.
        archived_credit = _milestone_archived_credit(m, tasks, aggregate=aggregate)
        done_count += archived_credit
        total_count = len(milestone_tasks) + archived_credit

        blocking_ms = [r for r in m.requires
                       if milestones.get(r) and milestones[r].status != "done"]

        ms_list.append({
            "key": m.key, "title": m.title, "desc": m.desc, "type": m.type,
            "status": m.status,
            "progress": {"done": done_count, "in_progress": in_progress_count,
                         "pending": pending_count, "total": total_count},
            "gate_results": gate_results,
            "requires": m.requires,
            "dependents": m.dependents,
            "phases": m.phases,
            "blocking_milestones": blocking_ms,
            "tasks": sorted(milestone_tasks, key=str),  # str-sort handles both modes
        })

    cp_set = _hashable_cp_set(critical_path)
    task_list = []
    # sort by (repo, id) so aggregate mode groups by namespace
    for t in sorted(tasks.values(), key=lambda x: (x._repo, x.id)):
        task_list.append({
            "id": t.id, "title": t.title, "status": t.status,
            "milestone": t.milestone, "effort": t.effort, "area": t.area,
            "assignee": t.assignee, "on_critical_path": t.key in cp_set,
            "blocking_score": blocking_scores.get(t.key, 0),
            "blocked_by": t.blocked_by, "spec_ref": t.spec_ref,
            "board_result": t.board_result, "readiness": t.readiness,
            "summary": t.summary,
            "repo": t._repo,  # namespace (empty in single-repo)
            "namespaced_id": _format_tid(t),  # full rendered ID
        })

    na_list = []
    for tid in next_actions:
        t = tasks[tid]
        na_list.append({
            "id": t.id, "title": t.title, "milestone": t.milestone,
            "effort": t.effort, "blocking_score": blocking_scores.get(t.key, 0),
            "on_critical_path": t.key in cp_set,
            "repo": t._repo,
            "namespaced_id": _format_tid(t),
        })

    cp_effort = sum(
        tasks[item].effort_weight
        for item in (critical_path or [])
        if isinstance(item, int) and not isinstance(item, bool) and item in tasks
    ) if critical_path else 0

    validation = {
        "errors": [{"check": i.check, "task": i.task_id, "milestone": i.milestone_key,
                     "detail": i.detail}
                    for i in issues if i.severity == "ERROR"],
        "warnings": [{"check": i.check, "task": i.task_id, "milestone": i.milestone_key,
                       "detail": i.detail}
                      for i in issues if i.severity == "WARN"],
    }

    # Phase data
    phases_list = []
    phase_progress_dict = {}
    if phases:
        for p in phases:
            phases_list.append({
                "key": p.key, "title": p.title, "desc": p.desc,
                "investor_desc": p.investor_desc or p.desc,
                "order": p.order,
            })
            pp = compute_phase_progress(p.key, milestones, tasks)
            phase_progress_dict[p.key] = {
                "pct": pp.pct, "tasks_done": pp.tasks_done,
                "tasks_total": pp.tasks_total, "remaining_effort": pp.remaining_effort,
            }

    return json.dumps({
        "generated_at": now.isoformat(),
        "north_star": north_star,
        "target": target,
        "operational_intent": op_intent,
        "phases": phases_list,
        "phase_progress": phase_progress_dict,
        "milestones": ms_list,
        "tasks": task_list,
        "critical_path": {"target": target, "path": critical_path, "effort_total": cp_effort},
        "next_actions": na_list,
        "validation": validation,
    }, indent=2, ensure_ascii=False)


