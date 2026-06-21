"""_plan_engine.compute — DAG, critical-path, milestone status, next actions.

Pure computation over loaded models. Reads no project globals directly; the
plan-data needed for the critical-path lookup is passed in by the caller.

Split out of the former monolithic scripts/plan_engine.py.
"""

from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass


from _plan_engine.core import (
    Milestone,
    PhaseProgress,
    Task,
    _emit_warn,
)
from _plan_engine.loading import (
    _archived_task_status,
    _milestone_archived_credit,
)


def compute_milestone_dependents(milestones: dict[str, Milestone]) -> None:
    """Invert requires-graph. Sets milestone.dependents for each milestone."""
    for m in milestones.values():
        m.dependents = []
    for m in milestones.values():
        for req in m.requires:
            if req in milestones:
                milestones[req].dependents.append(m.key)


def compute_phase_progress(
    phase_key: str,
    milestones: dict[str, Milestone],
    tasks: dict[int, Task],
) -> PhaseProgress:
    """Aggregate progress over all milestones belonging to a phase."""
    phase_milestones = [m for m in milestones.values() if phase_key in m.phases]
    tasks_done = 0
    tasks_total = 0
    remaining_effort = 0
    for m in phase_milestones:
        for tid in m.tasks:
            t = tasks.get(tid)
            if not t or (t.is_terminal and t.status != "done"):
                continue
            tasks_total += 1
            # is_terminal is the canonical completion semantic across the
            # milestone surfaces (fmt_boot / fmt_status / fmt_dashboard_json).
            # Here it is EQUIVALENT to is_done by construction: the filter above
            # already skipped every terminal-not-done task, so a task reaching
            # this point is either non-terminal (both False) or done (both True).
            # Spelled is_terminal for uniformity; not a behaviour change here.
            if t.is_terminal:
                tasks_done += 1
            else:
                remaining_effort += t.effort_weight
        # Archive-Awareness: tasks done+MOVED to docs/tasks/archive/ left m.tasks
        # (loader is non-recursive). Credit them with done_only=True, so non-done
        # archived terminals (superseded / wontfix / absorbed) are skipped
        # exactly as the loaded-task branch above skips them (is_terminal and
        # status != "done" -> continue). Additive (not already loaded).
        # Single-repo only — phases are not merged in aggregate, so no aggregate
        # guard is needed here. no-archive -> +0.
        credit = _milestone_archived_credit(m, tasks, done_only=True)
        tasks_done += credit
        tasks_total += credit
    pct = int(tasks_done / tasks_total * 100) if tasks_total > 0 else 0
    return PhaseProgress(
        pct=pct, tasks_done=tasks_done,
        tasks_total=tasks_total, remaining_effort=remaining_effort,
    )


def assign_tasks_to_milestones(tasks: dict, milestones: dict[str, Milestone]):
    """Populate milestone.tasks lists.

    Uses t.key (namespaced in aggregate mode, int in single-repo).
    m.tasks entries are therefore dict keys valid against the tasks dict.
    """
    for m in milestones.values():
        m.tasks = []
    for t in tasks.values():
        if t.milestone in milestones:
            milestones[t.milestone].tasks.append(t.key)


def compute_milestone_status(milestones: dict[str, Milestone], tasks: dict[int, Task]):
    """Compute status for all milestones. Bottom-up via topo sort on requires DAG."""
    # Topological sort of milestones
    in_degree = dict.fromkeys(milestones, 0)
    children = defaultdict(list)  # parent → children that require it
    for k, m in milestones.items():
        for req in m.requires:
            if req in milestones:
                in_degree[k] += 1
                children[req].append(k)

    queue = deque(k for k, d in in_degree.items() if d == 0)
    order = []
    while queue:
        k = queue.popleft()
        order.append(k)
        for child in children[k]:
            in_degree[child] -= 1
            if in_degree[child] == 0:
                queue.append(child)

    # Compute status in topological order
    for key in order:
        m = milestones[key]
        milestone_tasks = [tasks[tid] for tid in m.tasks if tid in tasks]

        # Priority chain (spec §1)
        # 1. Group → always active
        if m.is_group:
            m.status = "active"
            continue

        # 2. Check requires FIRST — a milestone can't be done if its requires aren't done.
        # This must come before the done-check to prevent meta-milestones (no tasks, no gate)
        # from being vacuously "done" while their requires are still pending.
        requires_issues = False
        requires_deep_block = False
        for req_key in m.requires:
            req_m = milestones.get(req_key)
            if req_m and req_m.status != "done":
                requires_issues = True
                if req_m.status in ("blocked", "future"):
                    requires_deep_block = True

        if requires_deep_block:
            m.status = "future"
            continue
        if requires_issues:
            m.status = "blocked"
            continue

        # 3. Done check: gate (if any) must PASS *and* all tasks must be terminal
        #    (done, superseded, absorbed, wontfix all count as "completed").
        all_tasks_done = milestone_tasks and all(t.is_terminal for t in milestone_tasks)
        no_tasks = not milestone_tasks

        if m.gate:
            all_gate_pass = all(g.check(tasks)[0] for g in m.gate)
            if all_gate_pass and (all_tasks_done or no_tasks):
                m.status = "done"
                continue
        else:
            if all_tasks_done or no_tasks:
                m.status = "done"
                continue

        # 6. Active if any task in_progress
        if any(t.status == "in_progress" for t in milestone_tasks):
            m.status = "active"
            continue

        # 7. Ready
        m.status = "ready"


def _build_milestone_order(milestones: dict[str, Milestone], target: str) -> list[str]:
    """Return milestones in requires-chain of target, topologically sorted (deps first)."""
    relevant = set()
    queue = deque([target])
    while queue:
        mk = queue.popleft()
        if mk in relevant:
            continue
        relevant.add(mk)
        m = milestones.get(mk)
        if m:
            for req in m.requires:
                queue.append(req)

    # Topo sort: deps before dependents
    in_deg = dict.fromkeys(relevant, 0)
    children = defaultdict(list)
    for k in relevant:
        m = milestones.get(k)
        if m:
            for req in m.requires:
                if req in relevant:
                    in_deg[k] += 1
                    children[req].append(k)
    q = deque(k for k, d in in_deg.items() if d == 0)
    order = []
    while q:
        k = q.popleft()
        order.append(k)
        for c in children[k]:
            in_deg[c] -= 1
            if in_deg[c] == 0:
                q.append(c)
    return order


# Mixed-Item-Render-Helper fuer Critical-Path-Items.
# Items koennen sein:
#   - int task-id (legacy + post-1980-mode)
#   - str milestone-key (z.B. "M1", "M1.5", "POST-MVP")
#   - list[str] parallel-Liste (z.B. ["M1", "M1.5"])
#   - str post-MVP-Beschreibung
def _render_cp_item(item, tasks: dict) -> str:
    """Render Critical-Path-Item zu String fuer fmt_boot/fmt_status/fmt_critical_path.

    explicit None-Branch (yaml-null wuerde 'None'-string).
    """
    # warnings via _emit_warn
    if item is None:
        return "(none)"
    if isinstance(item, bool):
        # bool ist subtype of int — explicit vor int-Branch
        return str(item)
    if isinstance(item, int):
        t = tasks.get(item)
        if t is None:
            # Archive-Awareness (mirror of GateCondition.check, ~L369): a dep
            # MOVED to docs/tasks/archive/ on reaching a terminal status is not
            # dangling. task_status_update §Step-4 deliberately KEEPS a terminal
            # id in other tasks' blocked_by, so an archived id legitimately
            # surfaces here as a satisfied gate dep. Render it distinctly with
            # its ACTUAL terminal status — the archive holds every terminal
            # status (done / superseded / wontfix / absorbed), so a hardcoded
            # "done" mislabels e.g. a wontfix id (archive/161.yaml).
            arch_status = _archived_task_status(item)
            if arch_status is not None:
                return f"[{item}] ({arch_status}, archived)"
            # neither loaded nor archived -> genuinely-unresolvable ref. The
            # "(missing)" signal is preserved EXACTLY for this case (real
            # dangling-ref detection).
            return f"[{item}] (missing)"
        title = getattr(t, "title", "") or ""
        return f"[{item}] {title}"
    if isinstance(item, list):
        # Items zu str kasten (TypeError-Schutz)
        return "[" + " || ".join(str(x) for x in item) + "]"
    if isinstance(item, str):
        return item
    if isinstance(item, dict):
        # dict-Item -> WARN UNKNOWN_CP_ITEM_TYPE,
        # rendern via str(item) (raw repr).
        _emit_warn(f"UNKNOWN_CP_ITEM_TYPE: dict {item!r}")
        return str(item)
    return str(item)


def _explicit_order_violations(explicit: list, milestones: dict) -> list:
    """Real `requires`-edge violations in the explicit critical_path order.

    A violation = a milestone whose `requires` predecessor — itself a milestone
    present in the explicit list — appears AFTER it. Topologically-parallel
    milestones (no requires-path between them) impose no order, so their relative
    position is free; only a real edge inversion is flagged. Returns a list of
    `(predecessor, dependent)` pairs (the predecessor that must precede but
    follows), or [] when the order is a valid topological ordering.

    This replaces a positional compare against ONE arbitrary topo-sort, which
    false-flagged the tie-break order of parallel milestones (e.g. M1/M1.5, both
    gating M2 with no edge between them) as drift even though every order of two
    independent milestones is valid. Ignored, because they impose no milestone
    ordering: non-milestone entries on the path (task ids, POST-MVP strings) and
    task-id `requires`. Nested parallel groups ([M1, M1.5]) share one position.
    """
    pos: dict[str, int] = {}
    for idx, item in enumerate(explicit):
        members = item if isinstance(item, list) else [item]
        for m in members:
            key = str(m) if m is not None else ""
            if key not in pos:
                pos[key] = idx

    violations: list = []
    for key, p in pos.items():
        m = milestones.get(key)
        if m is None:
            continue  # not a milestone (task id / POST-MVP string) -> no edge
        for req in m.requires:
            rkey = str(req)
            if rkey in pos and pos[rkey] > p:
                violations.append((rkey, key))  # rkey must precede key but follows
    return violations


def _topo_sort_legacy(
    tasks: dict,
    milestones: dict[str, Milestone],
    target: str,
) -> list:
    """Wrapper fuer die existierende Task-DAG-Topo-Sort-Logik (umbenannt).
    4-stufiger-Lookup-Stufe-4 Last-Resort.

    Wraps die ehemalige Body-Logik von compute_critical_path. Bei target leer
    oder tasks empty: returnt []."""
    return _compute_critical_path_dag(tasks, milestones, target)


def _hashable_cp_set(critical_path: list) -> set:
    """build set fuer 'in cp' Lookup ohne TypeError
    auf Mixed-Items. parallel-Listen werden zu frozenset, dict-items zu repr,
    None wird ignoriert."""
    out: set = set()
    for item in critical_path or []:
        if item is None:
            continue
        if isinstance(item, list):
            try:
                out.add(frozenset(item))
            except TypeError:
                # nested unhashables -> repr-fallback
                out.add(repr(item))
            # plus jedes individuelle Item (fuer task-id-Lookup auf parallel-content)
            for sub in item:
                if isinstance(sub, (str, int)) and not isinstance(sub, bool):
                    out.add(sub)
            continue
        if isinstance(item, dict):
            out.add(repr(item))
            continue
        try:
            out.add(item)
        except TypeError:
            out.add(repr(item))
    return out


def compute_critical_path(
    tasks: dict,
    milestones: dict[str, Milestone],
    target: str,
    plan_data: dict | None = None,
) -> list:
    """4-stufiger Lookup mit Konsistenz-Validation.

    Stufen:
      1. plan_data["critical_path"] (Greenfield-Authority) -> 1:1 als Authority
      2. plan_data["critical_path_feature_view"] (pre-Greenfield)
      3. plan_data["legacy_critical_path_sequence"] (legacy)
      4. DAG-Topological-Sort (Last-Resort)

    Konsistenz-Validation: prueft ob explicit eine gueltige topologische
    Reihenfolge der Milestone-`requires`-Kanten ist; WARN CRITICAL_PATH_MISMATCH
    nur bei echter Kanten-Verletzung (Tie-Break paralleler Milestones ist frei).

    Skip-Conditions:
      - target leer -> skip Drift-Detection
      - tasks empty -> skip
      - DAG-Sort empty -> skip
      - target unknown -> WARN UNKNOWN_TARGET + skip Drift
    """
    # warnings via _emit_warn

    if plan_data is None:
        plan_data = {}

    # Stufe 1-3: explicit Top-Level-Keys.
    # Edge-Case: leere Liste critical_path: [] is legitim.
    # Wir nutzen `if "key" in dict` Pattern statt `or`-Fallthrough fuer Stufe 1.
    explicit: list | None = None
    if "critical_path" in plan_data:
        v = plan_data["critical_path"]
        if isinstance(v, list):
            explicit = v
    if explicit is None and plan_data.get("critical_path_feature_view"):
        v = plan_data["critical_path_feature_view"]
        if isinstance(v, list):
            explicit = v
    if explicit is None and plan_data.get("legacy_critical_path_sequence"):
        v = plan_data["legacy_critical_path_sequence"]
        if isinstance(v, list):
            explicit = v

    if explicit is not None:
        # Konsistenz-Validation skip-Conditions
        skip_drift = False

        # target leer -> skip
        if not target:
            skip_drift = True

        # UNKNOWN_TARGET: target ist weder Milestone-Key
        # noch Task-Id im scope -> WARN, skip Drift.
        target_known = (
            (target in milestones)
            or (
                isinstance(target, str)
                and target.isdigit()
                and int(target) in tasks
            )
        )
        if target and not target_known:
            _emit_warn(f"UNKNOWN_TARGET: target {target!r} not in milestones/tasks")
            skip_drift = True

        # tasks empty + milestones empty -> skip
        if not tasks and not milestones:
            skip_drift = True

        if not skip_drift:
            # Validate the explicit order against the requires-DAG itself, not
            # against one arbitrary topo-sort: only a REAL requires-edge inversion
            # is a mismatch. Topologically-parallel milestones (no requires-path
            # between them — e.g. M1/M1.5, both gating M2) impose no order, so any
            # relative position is valid; the old positional compare false-flagged
            # that tie-break as drift.
            violations = _explicit_order_violations(explicit, milestones)
            if violations:
                edges = ", ".join(f"{dep} -> {m}" for dep, m in violations)
                _emit_warn(
                    f"CRITICAL_PATH_MISMATCH: explicit critical_path violates "
                    f"requires-edges (must hold: {edges}); explicit={explicit}"
                )
        return explicit

    # Stufe 4: DAG-Topological-Sort (Last-Resort)
    return _topo_sort_legacy(tasks, milestones, target)


def _resolve_active_milestone(
    milestones: dict[str, Milestone], target: str
) -> Milestone | None:
    """pick the milestone whose live task chain to surface — the
    FRONTIER, i.e. the earliest non-`done` milestone on the target's
    requires-spine.

    The `target` is the program north-star (e.g. M8 Distribution); the milestone
    the user actually works at is the nearest unfinished prerequisite (e.g. M3),
    not the far target. So the active milestone is the live frontier: walk the
    spine deps-first and return the first milestone that is not yet `done`. When
    the target IS the frontier (all predecessors done), this returns the target.
    When every spine milestone is done, returns None -> renderers degrade to the
    milestone-spine-only view (graceful degradation).

    (Earlier this returned the target itself whenever non-done, which mislabels
    a far north-star target as the active milestone — surfacing M8's gate chain
    while the work is at M3. Frontier-resolution makes the label and chain follow
    the live frontier regardless of how distant the target is set.)

    Status vocab from `compute_milestone_status` (done/future/blocked/ready/
    active); only `done` is skipped — every non-done state can be the frontier.
    """
    # _build_milestone_order is deps-first, so the first non-done milestone is
    # the earliest unfinished prerequisite = the live frontier.
    for k in _build_milestone_order(milestones, target):
        m = milestones.get(k)
        if m is not None and m.status != "done":
            return m
    return None


def _resolve_gate_task_keys(m: Milestone, tasks: dict) -> list:
    """resolve ALL `type: task` gate dict-keys for milestone `m`.

    A `type: task` gate carries the gate task id as a raw int (GateCondition.id).
    The tasks dict is keyed by task.key — int in single-repo, '<repo>#<id>' in
    aggregate mode. m.tasks holds those same keys, so we match the
    gate id against the milestone's own task keys to stay mode-agnostic. Falls
    back to a direct int-key lookup for milestones whose tasks list is empty.

    a milestone can carry multiple `type: task` gates (Milestone.gate is a
    list, gate task(s)). All of them block closure, so all of their
    chains must be surfaced — returning only the first silently under-reports.
    Returns the resolved keys in gate-declaration order (deduped), or [].
    """
    gate_ids = [g.id for g in m.gate if getattr(g, "type", "") == "task"]
    keys: list = []
    seen: set = set()
    for gid in gate_ids:
        resolved = None
        # Aggregate + single-repo: m.tasks entries are valid dict keys; match by
        # the underlying task id so we never assume the key shape.
        for key in m.tasks:
            t = tasks.get(key)
            if t is not None and t.id == gid:
                resolved = key
                break
        # Single-repo direct lookup (gate task id == int key) for the case where
        # the gate task is present in `tasks` but not listed in m.tasks.
        if resolved is None and gid in tasks:
            resolved = gid
        if resolved is not None and resolved not in seen:
            seen.add(resolved)
            keys.append(resolved)
    return keys


@dataclass(frozen=True)
class ActiveChain:
    """the full render-ready result of one active-milestone
    chain computation. The renderer needs all three from a SINGLE call so the
    production path == the tested path (no re-implemented orchestration twin):

      - milestone: the resolved active Milestone (for the header label `m.key`),
        or None when nothing gating resolves (spine-only degrade).
      - chain: ordered task keys (roots-first, gate last), or [] on degrade.
      - cycle_seen: True iff the blocked_by walk hit a real back-edge (the WARN
        was already emitted by compute_active_milestone_task_chain — the
        orchestration owner — so a consumer must NOT re-emit it).
    """
    milestone: Milestone | None
    chain: list
    cycle_seen: bool


def compute_active_milestone_task_chain(
    tasks: dict,
    milestones: dict[str, Milestone],
    target: str,
) -> ActiveChain:
    """ordered task-level path through the ACTIVE milestone.

    Resolves the active milestone's gate task and walks its blocked_by chain
    transitively back to the nearest unblocked root(s), returning an
    `ActiveChain(milestone, chain, cycle_seen)`: the resolved milestone (for the
    header label), the ordered list of task keys (roots-first, gate last —
    e.g. 550->551->552->553->429), and the cycle flag.

    this is the SINGLE source of the resolve -> gate -> topo -> WARN
    sequence. `_fmt_active_chain_block` (the production render path that
    `--critical-path`/`--boot` execute) consumes this one call instead of
    re-implementing the orchestration — so the self-test TCs that exercise this
    function exercise exactly what ships. The cycle WARN is emitted HERE (the
    orchestration owner); consumers read `cycle_seen` and must not re-emit.

    This is a SEPARATE computed view from compute_critical_path: it does NOT
    feed _hashable_cp_set / _explicit_order_violations / NEXT-ACTIONS cp_flag /
    dashboard_json. The milestone spine stays the critical-path authority; this
    only adds the live next-actions task chain nested under the active milestone.

    when the milestone has multiple `type: task` gates, every gate's
    chain is surfaced (the union of their predecessor sets, topo-ordered) — a
    single milestone with two blocking gates is not silently truncated to one.

    the active milestone is resolved exactly ONCE (here). Consumers reuse
    the returned `.milestone` for the label rather than resolving again — a
    second resolve is the latent label/content divergence trap.

    Edge handling:
      - no active milestone resolvable -> milestone=None, chain=[] (degrade)
      - no gate task resolves -> chain=[] (spine-only degrade)
      - gate task has empty blocked_by -> chain=[gate-task-key] (gate alone)
      - cycle in blocked_by -> break the walk + WARN, never loop

    Mode-agnostic: resolves keys via m.tasks / task.key, so it works
    in single-repo (int keys) and aggregate ('<repo>#<id>' keys) alike.
    """
    m = _resolve_active_milestone(milestones, target)
    if m is None:
        return ActiveChain(None, [], False)
    gate_keys = _resolve_gate_task_keys(m, tasks)
    if not gate_keys:
        return ActiveChain(m, [], False)

    chain, cycle_seen = _topo_blocked_by_chain(gate_keys, tasks)
    if cycle_seen:
        _emit_warn(
            f"ACTIVE_CHAIN_CYCLE: blocked_by cycle in milestone {m.key!r} "
            f"gate-task chain — walk truncated at {len(chain)} task(s)"
        )
    return ActiveChain(m, chain, cycle_seen)


def _topo_blocked_by_chain(gate_keys: list, tasks: dict) -> tuple[list, bool]:
    """reverse-topo over `blocked_by` from the gate task(s).

    Returns (ordered_keys, cycle_seen). For the acyclic portion the order is
    roots-first — every dependency precedes its dependents (550 -> 551 ->
    ... -> gate). A diamond / shared blocker (in-degree > 1, acyclic) is ordered
    correctly and does NOT report a cycle; a real back-edge DOES (keeps the
    WARN).

    caveat: when cycle_seen is True, the nodes on the cycle never drain
    from the Kahn queue, so they CANNOT be topo-ordered. They are appended as a
    deterministic residue (sorted by str) AFTER the drained prefix — within that
    residue the "dependency precedes dependent" guarantee does NOT hold. This is
    bounded: the residue only appears alongside an always-emitted
    ACTIVE_CHAIN_CYCLE WARN (the caller emits it whenever cycle_seen is True), so
    a mis-ordered tail is never presented silently as a valid topo order.

    Two-phase, mirroring the DAG pattern in _compute_critical_path_dag:
      1. Collect the reachable predecessor subgraph from the gate(s) via BFS on
         blocked_by, recording the dependency edges (dep -> dependent).
      2. Kahn topological sort over those edges. Nodes that never drain (still
         have unmet predecessors when the queue empties) are exactly the nodes
         on a cycle — that, and only that, sets cycle_seen. This distinguishes a
         re-convergence (DAG, legal) from a back-edge (true cycle); the old
         single black `visited` set could not.
    """
    # Phase 1: reachable predecessor subgraph (nodes + dep->dependent edges).
    reachable: set = set()
    # children[dep] = dependents that list `dep` in their blocked_by.
    children: dict = defaultdict(list)
    in_deg: dict = {}
    queue: deque = deque()
    for gk in gate_keys:
        if gk not in reachable:
            reachable.add(gk)
            in_deg[gk] = 0
            queue.append(gk)
    while queue:
        key = queue.popleft()
        t = tasks.get(key)
        if t is None:
            continue
        # blocked_by entries are valid task keys in both modes (int single-repo,
        # '<repo>#<id>' aggregate after rewrite).
        for dep in t.blocked_by:
            children[dep].append(key)
            in_deg[key] = in_deg.get(key, 0) + 1
            if dep not in reachable:
                reachable.add(dep)
                in_deg.setdefault(dep, 0)
                queue.append(dep)

    # Phase 2: Kahn topo sort (roots-first). Tie-break popped roots by a stable
    # key so the order is deterministic across runs.
    ready: list = sorted((k for k in reachable if in_deg.get(k, 0) == 0), key=str)
    ordered: list = []
    while ready:
        key = ready.pop(0)
        ordered.append(key)
        newly_ready = []
        for child in children.get(key, []):
            in_deg[child] -= 1
            if in_deg[child] == 0:
                newly_ready.append(child)
        # Keep deterministic order as nodes free up.
        for nk in sorted(newly_ready, key=str):
            ready.append(nk)

    # Any node not emitted is on a cycle (its predecessors never all drained).
    cycle_seen = len(ordered) < len(reachable)
    if cycle_seen:
        # Append the cycle residue (deterministic) so the gate(s) still surface
        # rather than vanishing — the walk is truncated, not dropped.
        residue = sorted((k for k in reachable if k not in set(ordered)), key=str)
        ordered.extend(residue)
    return ordered, cycle_seen


def _compute_critical_path_dag(
    tasks: dict,
    milestones: dict[str, Milestone],
    target: str,
) -> list:
    """Original Body von compute_critical_path (DAG-Topo-Sort).
    Renamed fuer 4-stufigen-Lookup-Stufe-4. Keine Verhaltensaenderung.

    Cross-milestone dependencies: milestones are processed in requires-order.
    For each milestone M that requires R, entry tasks of M (tasks with no
    in-scope blocked_by) get a virtual dependency on the exit task of R
    (task with highest dist in R).

    In aggregate mode, blocked_by entries can cross repo boundaries.
    """
    if not target:
        return []
    if not tasks:
        return []
    if target not in milestones:
        return []
    ms_order = _build_milestone_order(milestones, target)
    relevant_milestones = set(ms_order)

    # Scope: non-terminal tasks in relevant milestones
    scope = {
        tid: t for tid, t in tasks.items()
        if not t.is_terminal and t.milestone in relevant_milestones
    }
    if not scope:
        return []

    # In aggregate mode ONLY, expand scope via backward-walk on
    # blocked_by to include cross-repo predecessor milestones. Single-repo
    # mode keeps its original semantics (critical path scoped strictly to
    # milestones on target's requires-chain) to preserve regression.
    # Aggregate mode is detected by any task having a non-empty _repo marker.
    is_aggregate = any(t._repo for t in tasks.values())
    if is_aggregate:
        changed = True
        while changed:
            changed = False
            extra_ms: set[str] = set()
            for t in scope.values():
                for dep in t.blocked_by:
                    dep_t = tasks.get(dep)
                    if dep_t is None or dep_t.is_terminal:
                        continue
                    if dep_t.milestone and dep_t.milestone not in relevant_milestones:
                        extra_ms.add(dep_t.milestone)
            if extra_ms:
                relevant_milestones |= extra_ms
                # Rebuild scope to include tasks from the newly-added milestones.
                scope = {
                    tid: t for tid, t in tasks.items()
                    if not t.is_terminal and t.milestone in relevant_milestones
                }
                changed = True

        # Rebuild ms_order with a topo-sort that accounts for both (a) milestone
        # requires and (b) inter-milestone task-level blocked_by edges. This
        # ensures DP processes prerequisite milestones first even when they
        # come from a different repo.
        if relevant_milestones != set(ms_order):
            ms_deps: dict[str, set[str]] = {mk: set() for mk in relevant_milestones}
            for mk in relevant_milestones:
                m = milestones.get(mk)
                if not m:
                    continue
                for req in m.requires or []:
                    if req in relevant_milestones:
                        ms_deps[mk].add(req)
            for t in scope.values():
                for dep in t.blocked_by:
                    dep_t = tasks.get(dep)
                    if dep_t is None or dep_t.is_terminal:
                        continue
                    if dep_t.milestone and dep_t.milestone != t.milestone \
                            and dep_t.milestone in relevant_milestones:
                        ms_deps[t.milestone].add(dep_t.milestone)
            in_deg = {mk: len(ms_deps[mk]) for mk in relevant_milestones}
            q_ms = deque(mk for mk, d in in_deg.items() if d == 0)
            new_order: list[str] = []
            while q_ms:
                mk = q_ms.popleft()
                new_order.append(mk)
                for other, deps in ms_deps.items():
                    if mk in deps:
                        deps.discard(mk)
                        in_deg[other] -= 1
                        if in_deg[other] == 0:
                            q_ms.append(other)
            remaining = [mk for mk in relevant_milestones if mk not in new_order]
            ms_order = new_order + remaining

    # Group tasks by milestone
    ms_tasks: dict[str, list[int]] = defaultdict(list)
    for tid, t in scope.items():
        ms_tasks[t.milestone].append(tid)

    # Global dist and prev (accumulated across milestones)
    dist: dict[int, int] = {}
    prev: dict[int, int | None] = {}
    milestone_exit_task: dict[str, int] = {}

    # Process milestones in topological order (prereqs first)
    for mk in ms_order:
        m = milestones.get(mk)
        if not m:
            continue

        m_tids = ms_tasks.get(mk, [])
        if not m_tids:
            continue

        # Collect virtual predecessors from prerequisite milestones
        virtual_pred_dist = 0
        virtual_pred_tid = None
        for req_key in (m.requires or []):
            exit_tid = milestone_exit_task.get(req_key)
            if exit_tid is not None and exit_tid in dist:
                if dist[exit_tid] > virtual_pred_dist:
                    virtual_pred_dist = dist[exit_tid]
                    virtual_pred_tid = exit_tid

        # Topo sort tasks within this milestone (using blocked_by within scope)
        local_in_deg = dict.fromkeys(m_tids, 0)
        local_successors: dict[int, list[int]] = defaultdict(list)
        m_tids_set = set(m_tids)

        for tid in m_tids:
            for dep in scope[tid].blocked_by:
                if dep in m_tids_set:
                    local_in_deg[tid] += 1
                    local_successors[dep].append(tid)

        topo_queue = deque(tid for tid in m_tids if local_in_deg[tid] == 0)
        topo_order = []
        while topo_queue:
            tid = topo_queue.popleft()
            topo_order.append(tid)
            for succ in local_successors[tid]:
                local_in_deg[succ] -= 1
                if local_in_deg[succ] == 0:
                    topo_queue.append(succ)

        # DP: longest path for tasks in this milestone
        for tid in topo_order:
            t = scope[tid]
            best_pred_d = 0
            best_pred = None

            # Check explicit blocked_by (within scope, including cross-milestone)
            for dep in t.blocked_by:
                if dep in dist and dist[dep] > best_pred_d:
                    best_pred_d = dist[dep]
                    best_pred = dep

            # Check virtual predecessor (from requires chain)
            # Only applies to entry tasks (no in-scope blocked_by within this milestone)
            is_entry = not any(dep in m_tids_set for dep in t.blocked_by)
            if is_entry and virtual_pred_tid is not None:
                if virtual_pred_dist > best_pred_d:
                    best_pred_d = virtual_pred_dist
                    best_pred = virtual_pred_tid

            dist[tid] = t.effort_weight + best_pred_d
            prev[tid] = best_pred

        # Exit task: highest dist in this milestone
        if m_tids:
            computed_tids = [tid for tid in m_tids if tid in dist]
            if computed_tids:
                milestone_exit_task[mk] = max(computed_tids, key=lambda x: dist[x])

    if not dist:
        return []

    # Find endpoint: prefer tasks in the target milestone
    target_tids = [tid for tid in ms_tasks.get(target, []) if tid in dist]
    if target_tids:
        end_tid = max(target_tids, key=lambda x: dist[x])
    else:
        end_tid = max(dist, key=lambda x: dist[x])

    # Reconstruct path
    path = []
    cur: int | None = end_tid
    while cur is not None:
        path.append(cur)
        cur = prev.get(cur)
    path.reverse()
    return path


def compute_blocking_score(
    tasks: dict,
    milestones: dict[str, Milestone],
) -> dict:
    """For each task, count how many non-done tasks would be transitively unblocked.

    Includes cross-milestone effects: if completing task X causes milestone M
    to become done, then tasks in milestones that require M become unblocked.

    Uses t.key (namespaced string in aggregate mode, int in single-
    repo) so the same graph code works for both modes.
    """
    # Build reverse graph: task → tasks that are blocked by it
    dependents = defaultdict(list)
    for t in tasks.values():
        for dep in t.blocked_by:
            dependents[dep].append(t.key)

    # Build milestone → tasks mapping and reverse requires
    ms_tasks = defaultdict(list)
    for t in tasks.values():
        ms_tasks[t.milestone].append(t.key)
    # milestone → milestones that require it
    ms_dependents = defaultdict(list)
    for m in milestones.values():
        for req in m.requires:
            ms_dependents[req].append(m.key)

    actually_done = {t.key for t in tasks.values() if t.is_done}

    # Precompute gate results ONCE — avoids re-evaluating script gates
    # inside the per-task loop (which would spawn 139× subprocesses)
    gate_cache: dict[str, bool] = {}
    for m in milestones.values():
        if m.is_group:
            continue
        gate_cache[m.key] = all(g.check(tasks)[0] for g in m.gate) if m.gate else True

    scores = {}
    for tid in tasks:
        if tasks[tid].is_terminal:
            scores[tid] = 0
            continue

        # Simulate: what if tid becomes done?
        sim_done = actually_done | {tid}
        unblocked = set()

        # Phase 1: direct task-level unblocking (BFS)
        check_queue = deque(dependents.get(tid, []))
        while check_queue:
            candidate = check_queue.popleft()
            if candidate in unblocked or candidate in sim_done:
                continue
            ct = tasks.get(candidate)
            if not ct or ct.is_terminal:
                continue
            if all(d in sim_done for d in ct.blocked_by):
                unblocked.add(candidate)
                sim_done.add(candidate)
                for further in dependents.get(candidate, []):
                    check_queue.append(further)

        # Phase 2: check if any milestone becomes done, unlocking downstream milestones
        # Recompute which milestones would be done with sim_done
        sim_done_milestones = set()
        for m in milestones.values():
            if m.is_group:
                continue
            m_tids = ms_tasks.get(m.key, [])
            all_m_tasks_done = all(
                tid_m in sim_done for tid_m in m_tids
                if tid_m in tasks and not tasks[tid_m].is_terminal
            ) if m_tids else True
            gate_pass = gate_cache.get(m.key, True)
            if all_m_tasks_done and gate_pass:
                sim_done_milestones.add(m.key)

        # Original done milestones (before simulation)
        orig_done_milestones = set()
        for m in milestones.values():
            if m.status == "done":
                orig_done_milestones.add(m.key)

        # Newly done milestones
        newly_done_ms = sim_done_milestones - orig_done_milestones

        # For each newly done milestone, find downstream milestones that become unblocked
        if newly_done_ms:
            # Find tasks in milestones that were blocked by the now-done milestones
            for new_ms_key in newly_done_ms:
                for dependent_ms_key in ms_dependents.get(new_ms_key, []):
                    dep_m = milestones.get(dependent_ms_key)
                    if not dep_m:
                        continue
                    # Check if ALL requires of this dependent milestone are now done
                    all_reqs_done = all(
                        r in sim_done_milestones or r in orig_done_milestones
                        for r in dep_m.requires
                    )
                    if all_reqs_done:
                        # Tasks in this milestone become unblocked (milestone-level)
                        for m_tid in ms_tasks.get(dependent_ms_key, []):
                            if m_tid in sim_done or m_tid in unblocked:
                                continue
                            mt = tasks.get(m_tid)
                            if not mt or mt.is_terminal:
                                continue
                            # Still check task-level deps
                            if all(d in sim_done for d in mt.blocked_by):
                                unblocked.add(m_tid)

        scores[tid] = len(unblocked)
    return scores


def compute_next_actions(
    tasks: dict,
    milestones: dict[str, Milestone],
    critical_path: list,
    blocking_scores: dict,
    target: str,
    limit: int = 10,
) -> list:
    """Tasks that are ready to start, sorted by priority.

    Sort order: (1) on critical path, (2) on target path (milestone is target
    or in requires-chain of target), (3) blocking score desc, (4) effort asc.
    This ensures MVP-path tasks rank above non-MVP tasks even when milestones
    like intelligence/life-os are technically unblocked.

    Uses t.key throughout so the same logic applies to aggregate mode.
    """
    cp_set = _hashable_cp_set(critical_path)
    done_keys = {t.key for t in tasks.values() if t.is_done}

    # Compute target path: milestones in the requires-chain of the target
    target_path_ms = set()
    queue = deque([target])
    while queue:
        mk = queue.popleft()
        if mk in target_path_ms:
            continue
        target_path_ms.add(mk)
        m = milestones.get(mk)
        if m:
            for req in m.requires:
                queue.append(req)

    ready = []
    for t in tasks.values():
        if t.status != "pending":
            continue
        if t.has_external_deps:
            continue
        # All blocked_by must be done
        if not all(d in done_keys for d in t.blocked_by):
            continue
        # Milestone must not be blocked/future
        m = milestones.get(t.milestone)
        if m and m.status in ("blocked", "future"):
            continue
        ready.append(t.key)

    # Sort: critical path > target path > blocking score > effort
    ready.sort(key=lambda tk: (
        0 if tk in cp_set else 1,                            # critical path first
        0 if tasks[tk].milestone in target_path_ms else 1,   # target-path milestones next
        -blocking_scores.get(tk, 0),                         # higher blocking score first
        tasks[tk].effort_weight,                             # smaller effort first
        str(tk),                                             # stable fallback (str works for both modes)
    ))
    return ready[:limit]


