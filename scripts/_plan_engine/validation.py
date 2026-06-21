"""_plan_engine.validation — schema + governance validation.

``validate`` (DAG/cycle/dep checks) and ``validate_task_schema_conformance``
(machine-readable task-schema). Both return ``list[ValidationIssue]``. Reads the
project globals late via ``loading.PROJECT_ROOT`` / ``loading.TASKS_DIR`` so the
--project-root override and dashboard rebind are honoured.

Split out of the former monolithic scripts/plan_engine.py.
"""

from __future__ import annotations

from collections import defaultdict, deque
from pathlib import Path

import yaml

from _plan_engine import loading
from _plan_engine.core import (
    FRAMEWORK_ROOT,
    KNOWN_TASK_STATUSES,
    SPEC_PHASE_ENUM,
    TERMINAL_STATUSES,
    Milestone,
    ValidationIssue,
)
from _plan_engine.loading import (
    load_archived_task_ids,
)

# machine-readable task-schema SoT. The validator parses THIS file — field
# names, required-sets, value vocab, filename grammar and calibration switches
# are read FROM the parsed dict, never re-encoded in Python. Framework-internal.
TASK_SCHEMA_PATH = FRAMEWORK_ROOT / "framework" / "task-schema.yaml"


def validate(
    tasks: dict,
    milestones: dict[str, Milestone],
    archived_ids: set | None = None,
) -> list[ValidationIssue]:
    """Validate tasks + milestones.

    uses t.key (namespaced in aggregate).
    archived_ids -> Silent-Pass fuer
    BROKEN_DEP wenn target_id in archived_ids set. Wenn archived_ids=None:
    auto-load aus PROJECT_ROOT (explicit project_root via module-global).

    archived_ids ist ein set[int] in
    Single-Repo-Mode UND set[str] in Aggregate-Mode (namespaced
    "<repo>#<id:03d>"). Membership-Check via direktem `dep in archived_ids` —
    set-Lookup ist type-safe (Bool-Werte werden in load_archived_task_ids
    bereits gerejected, also keine Pythonic 0==False/1==True-Kollision moeglich).
    """
    if archived_ids is None:
        # Auto-load: muss automatisch greifen — caller ohne explicit
        # archived_ids bekommt trotzdem Silent-Pass-Verhalten (CLI-Pfade,
        # Test-direkt-Aufrufe). PROJECT_ROOT-relativ.
        archived_ids = load_archived_task_ids(loading.PROJECT_ROOT)
    issues = []
    task_keys = set(tasks.keys())

    # ID_REUSED_FROM_ARCHIVE: an active task id must not also exist in
    # docs/tasks/archive/. Archived IDs are retired, never recycled — a live id
    # colliding with an archived one breaks the WORM archive move at close (the
    # `git mv -> archive/<id>.yaml` hits an existing path) and silently
    # duplicates an id across the active+archive sets. task_keys and
    # archived_ids share one identity space by construction (int in single-repo,
    # "<repo>#<id:03d>" in aggregate — the same space the BROKEN_DEP silent-pass
    # below relies on), so the intersection is collision-exact in both modes.
    for reused in sorted(task_keys & archived_ids, key=str):
        issues.append(ValidationIssue(
            "ID_REUSED_FROM_ARCHIVE", "ERROR", task_id=reused,
            detail="active task id also present in docs/tasks/archive/ — "
                   "archived ids are retired; pick the next free id "
                   "(max over docs/tasks/ + docs/tasks/archive/, + 1)"))

    for t in tasks.values():
        tid_for_issue = t.key  # namespaced in aggregate mode
        # NO_MILESTONE (terminal tasks may have null milestone — they're completed)
        if not t.milestone and not t.is_terminal:
            issues.append(ValidationIssue("NO_MILESTONE", "ERROR", task_id=tid_for_issue,
                                          detail="task has no milestone field"))
        elif not t.milestone and t.is_terminal:
            pass  # terminal tasks without milestone are fine
        elif t.milestone not in milestones and not t.is_terminal:
            # Terminal tasks (done/superseded) get a free pass — symmetric with the
            # NO_MILESTONE branch above. Archived/done tasks may point at retired
            # milestone keys after a reorg; that is audit-trail, not a defect.
            issues.append(ValidationIssue("UNKNOWN_MILESTONE", "ERROR", task_id=tid_for_issue,
                                          detail=f"milestone '{t.milestone}' not in plan.yaml"))
        # BROKEN_DEP (Silent-Pass: archived Tasks skipped)
        for dep in t.blocked_by:
            if dep not in task_keys:
                # Silent-Pass: archived id -> kein ERR.
                # archived_ids ist set[int] (single-repo)
                # ODER set[str] (aggregate, "<repo>#<id:03d>"). Direkter
                # set-Membership-Check funktioniert in beiden Modi.
                if dep in archived_ids:
                    continue
                issues.append(ValidationIssue("BROKEN_DEP", "ERROR", task_id=tid_for_issue,
                                              detail=f"blocked_by {dep} not found"))
        # DEAD_DEP
        for dep in t.blocked_by:
            dep_t = tasks.get(dep)
            if dep_t and dep_t.status in TERMINAL_STATUSES - {"done"}:
                issues.append(ValidationIssue("DEAD_DEP", "ERROR", task_id=tid_for_issue,
                                              detail=f"blocked_by {dep} is {dep_t.status}"))
        # INVALID_STATUS: a status outside the sanctioned enum is silently
        # mis-handled — the pending-keyed critical-path / next-actions logic
        # excludes it, so a rogue/typo'd status (e.g. `open`) drops the task off
        # the live frontier with no signal. Flag it loudly so it can't corrupt
        # the plan view unseen. (Terminal tasks are validated the same way.)
        if t.status not in KNOWN_TASK_STATUSES:
            issues.append(ValidationIssue("INVALID_STATUS", "WARN", task_id=tid_for_issue,
                                          detail=f"status {t.status!r} not in sanctioned enum "
                                                 f"{sorted(KNOWN_TASK_STATUSES)} — excluded from "
                                                 f"critical-path/next-actions (treated as non-pending)"))
        # NO_EFFORT
        if t.status in ("pending", "in_progress") and not t.effort:
            issues.append(ValidationIssue("NO_EFFORT", "ERROR", task_id=tid_for_issue,
                                          detail="pending/in_progress without effort"))
        # STALE_BLOCKED
        if t.status == "blocked":
            done_keys = {tk for tk, tt in tasks.items() if tt.is_done}
            if all(d in done_keys for d in t.blocked_by):
                issues.append(ValidationIssue("STALE_BLOCKED", "WARN", task_id=tid_for_issue,
                                              detail="status=blocked but all deps done"))
        # EXTERNAL_DEP
        if t.has_external_deps:
            issues.append(ValidationIssue("EXTERNAL_DEP", "WARN", task_id=tid_for_issue,
                                          detail="has blocked_by_external"))
        # DECOMPOSE — XL tasks should be broken into sub-tasks
        if t.effort == "XL" and t.status in ("pending", "in_progress"):
            issues.append(ValidationIssue("DECOMPOSE", "WARN", task_id=tid_for_issue,
                                          detail="effort=XL — consider decomposing into sub-tasks"))

        # SPEC_STATES validation
        if t.spec_states:
            if not isinstance(t.spec_states, dict):
                issues.append(ValidationIssue(
                    "SPEC_STATES_TYPE", "ERROR", task_id=tid_for_issue,
                    detail="spec_states is not a dict",
                ))
                continue
            for spec_name, state in t.spec_states.items():
                if not isinstance(state, dict):
                    issues.append(ValidationIssue(
                        "SPEC_STATE_TYPE", "ERROR", task_id=tid_for_issue,
                        detail=f"spec_states[{spec_name}] is not a dict",
                    ))
                    continue
                phase = state.get("current_phase", "")
                if phase not in SPEC_PHASE_ENUM:
                    issues.append(ValidationIssue(
                        "SPEC_PHASE_ENUM", "ERROR", task_id=tid_for_issue,
                        detail=f"spec_states[{spec_name}].current_phase "
                               f"'{phase}' not in {sorted(SPEC_PHASE_ENUM)}",
                    ))
                rp = state.get("review_passes", 0)
                fp = state.get("fix_passes", 0)
                if not isinstance(rp, int) or rp < 0:
                    issues.append(ValidationIssue(
                        "SPEC_PASSES_TYPE", "ERROR", task_id=tid_for_issue,
                        detail=f"spec_states[{spec_name}].review_passes "
                               f"must be int >= 0, got {rp!r}",
                    ))
                if not isinstance(fp, int) or fp < 0:
                    issues.append(ValidationIssue(
                        "SPEC_PASSES_TYPE", "ERROR", task_id=tid_for_issue,
                        detail=f"spec_states[{spec_name}].fix_passes "
                               f"must be int >= 0, got {fp!r}",
                    ))
                # Transition consistency: reviewing/fixing/ready require review_passes > 0
                if (phase in ("reviewing", "fixing", "ready")
                        and isinstance(rp, int) and rp <= 0):
                    issues.append(ValidationIssue(
                        "SPEC_PHASE_CONSISTENCY", "ERROR", task_id=tid_for_issue,
                        detail=f"spec_states[{spec_name}].current_phase={phase} "
                               f"but review_passes={rp} (must be > 0)",
                    ))

    # Spec duplicate check: same spec in spec_states of 2+ active tasks
    spec_owners: dict[str, list] = defaultdict(list)
    for t in tasks.values():
        if t.status in {"superseded", "absorbed"}:
            continue
        for spec_name in t.spec_states:
            spec_owners[spec_name].append(t.key)
    for spec_name, owner_keys in spec_owners.items():
        if len(owner_keys) > 1:
            ids_str = ", ".join(str(tk) for tk in sorted(owner_keys, key=str))
            issues.append(ValidationIssue(
                "SPEC_DUPLICATE", "WARN",
                detail=f"spec '{spec_name}' tracked in multiple active tasks: {ids_str}",
            ))

    # Cycle detection (simplified — check if topo sort covers all).
    # iterate via t.key (polymorphic int/str).
    in_deg = dict.fromkeys(tasks, 0)
    for t in tasks.values():
        # set(): count each DISTINCT dependency once. The drain loop below
        # uses a membership test (`if tk in t2.blocked_by`) which fires once
        # per dependent, so the build loop must be dedup-symmetric — otherwise
        # a duplicate blocked_by entry (e.g. [1, 1], not a real cycle) inflates
        # the in-degree, the node never reaches 0, and a phantom CYCLE fires.
        for dep in set(t.blocked_by):
            if dep in in_deg:
                in_deg[t.key] += 1
    queue = deque(tk for tk, d in in_deg.items() if d == 0)
    visited = set()
    while queue:
        tk = queue.popleft()
        visited.add(tk)
        for t2 in tasks.values():
            if tk in t2.blocked_by:
                in_deg[t2.key] -= 1
                if in_deg[t2.key] == 0:
                    queue.append(t2.key)
    unvisited = set(tasks.keys()) - visited
    if unvisited:
        issues.append(ValidationIssue("CYCLE", "ERROR",
                                      detail=f"cycle involving tasks: {sorted(unvisited, key=str)}"))

    # Milestone checks
    for m in milestones.values():
        if not m.is_group and not m.tasks and m.status in ("ready", "active"):
            issues.append(ValidationIssue("ORPHAN_MILESTONE", "WARN",
                                          milestone_key=m.key,
                                          detail=f"0 tasks, status={m.status}"))
        open_count = sum(1 for tid in m.tasks
                        if tid in tasks and not tasks[tid].is_terminal)
        if not m.is_group and open_count > 15 and m.status not in ("future", "done"):
            issues.append(ValidationIssue("LARGE_MILESTONE", "WARN",
                                          milestone_key=m.key,
                                          detail=f"{open_count} open tasks (of {len(m.tasks)} total)"))
        # GATE_TASK_DRIFT: gate passes but tasks still pending AND none in progress
        # (if tasks are in_progress, gate PASS is expected — prerequisites met).
        # Skip when the milestone has no "hard" gates — preliminary + manual gates
        # don't encode prerequisites, so their PASS state carries no implication
        # about whether member tasks should be done. A manual gate explicitly
        # delegates closure to human judgement; firing DRIFT against it is
        # structurally noise.
        if m.gate and not m.is_group:
            hard_gates = [g for g in m.gate
                          if not g.preliminary and g.type != "manual"]
            if hard_gates:
                all_gate_pass = all(g.check(tasks)[0] for g in m.gate)
                non_done = [tid for tid in m.tasks
                            if tid in tasks and not tasks[tid].is_terminal and not tasks[tid].is_done]
                has_active = any(tasks[tid].status == "in_progress"
                                 for tid in m.tasks if tid in tasks)
                if all_gate_pass and non_done and not has_active:
                    ids = ", ".join(str(t) for t in non_done[:5])
                    issues.append(ValidationIssue("GATE_TASK_DRIFT", "WARN",
                                                  milestone_key=m.key,
                                                  detail=f"gate PASS but {len(non_done)} tasks pending: {ids}"))
        # Gate scripts
        for g in m.gate:
            if g.type == "script" and not (loading.PROJECT_ROOT / g.path).exists():
                issues.append(ValidationIssue("SCRIPT_MISSING", "WARN",
                                              milestone_key=m.key,
                                              detail=f"gate script not found: {g.path}"))

        # Requires reference check
        # feature_milestones requires-Eintraege
        # koennen sein: milestone-key (str) ODER task-id (int oder digit-str).
        # Task-ID-Refs werden NICHT als UNKNOWN_REQUIRES gewertet wenn die
        # Task existiert (im tasks-dict oder in archived_ids).
        for req in m.requires:
            if isinstance(req, str) and req in milestones:
                continue
            # Namespaced task-ref (aggregate mode): "<repo>#<id:03d>" matches
            # the task / archived_ids key format directly.
            if isinstance(req, str) and (req in tasks or req in archived_ids):
                continue
            # Numerischer String: als Task-Id behandeln
            if isinstance(req, str) and req.isdigit():
                tid_int = int(req)
                if tid_int in tasks or tid_int in archived_ids:
                    continue
            if isinstance(req, int) and (req in tasks or req in archived_ids):
                continue
            issues.append(ValidationIssue("UNKNOWN_REQUIRES", "ERROR",
                                          milestone_key=m.key,
                                          detail=f"requires '{req}' not in plan.yaml"))

    return issues



# Read-only audit layer. It re-reads each docs/tasks/*.yaml via
# yaml.safe_load — it MUST NOT consume the constructed Task (lossy:
# status→pending, effort→M defaults, non-int blocked_by filtered,
# priority not a Task field). Every field name / required-set / value
# vocabulary / filename rule / calibration switch is dereferenced from
# the parsed schema dict; zero schema knowledge is hardcoded here.
#
# Trust boundary. `_load_task_schema` returns
# `dict | None`; "is a dict" is NOT "is a valid schema". Every `.get()`
# after the load is otherwise an unenforced trust assumption. Rather
# than scattering per-site isinstance guards (which provably recurse one
# nesting level deeper every pass), the document transitions from
# *untrusted bytes* to *validated structure* at exactly ONE seam:
# `_validate_schema_structure`, called first thing in
# `validate_task_schema_conformance` (after the None-check, before any
# consumer / re.compile). The expected shape is DECLARATIVE DATA
# (`_TASK_SCHEMA_SHAPE`); a single generic walker interprets it. Adding
# schema DEPTH later (a deeper node of an already-expressible kind) =
# adding a data node, no new code branches.
#
# Scope of the guarantee — read this before trusting it. This boundary
# closes exactly ONE class: the structural WRONG-TYPE class, i.e. a
# key that IS PRESENT but whose value has the wrong Python type, at
# any nesting depth. It does NOT express CONDITIONAL-REQUIREDNESS: a
# key that is required only given a sibling's value (e.g. a field-def
# with `type: enum` but the `values:` key entirely ABSENT) is
# type-valid by this grammar and passes — the consumer then silently
# drops that field's vocab. That is a KNOWN, owner-ACCEPTED residual
# (MEDIUM, accepted): the descriptor grammar
# below has no "required-because-of-a-sibling" construct, and adding
# one WOULD be a new code branch. The accepted trigger is human
# damage to the LOCKED framework/task-schema.yaml, not a code path.
# Do not "fix" this in a comment pass and do not overstate the
# guarantee in either direction.


# Version this descriptor was authored against. MUST equal
# `schema_version` in framework/task-schema.yaml. The positive-anchor
# self-test asserts the real locked schema passes the walker; this pin
# additionally forces a CONSCIOUS descriptor revisit on any intentional
# schema evolution (mismatch -> _schema_defect ESCALATE, never silent
# under-validation).
_TASK_SCHEMA_VERSION = 1

# Declarative structural mirror of framework/task-schema.yaml — the
# closed set of nodes validate_task_schema_conformance dereferences
# (mechanically equal to the `schema.get(...)` / nested-deref set; a
# reviewer confirms via grep over the schema-consumer functions, not by
# trusting this comment). Node grammar (all keys optional unless noted):
#   type      : expected Python type (or tuple) for the value
#   what      : human label for `type` (defect message)
#   required  : True -> key MUST be present (default False; absent
#               optional key != malformed -> no over-fire)
#   elem_type : list-element expected type (only for type==list)
#   elem_what : human label for elem_type
#   children  : {child_key: node} — fixed-key sub-mapping
#   each_value: node applied to EVERY value of a mapping
#               (mapping-of-mappings, e.g. fields.<name>)
#   when      : (sibling_key, sibling_value) — sibling-LOCALITY only:
#               the node is type-checked ONLY when the sibling key
#               equals that value (e.g. enum `values`).
#               `when` does NOT make the key conditionally REQUIRED —
#               if the gated key is ABSENT it is simply skipped, never
#               flagged. Conditional requiredness is not expressible
#               in this grammar (see residual note below).
#
# Provenance + scope (accepted residual). _TASK_SCHEMA_SHAPE
# (and _FIELD_DEF_SHAPE) is the structural MIRROR of
# framework/task-schema.yaml — a SECOND structural description of the
# schema in Python that MUST NOT silently drift from the YAML SoT. It
# validates structural TYPE ONLY (a present key whose value is the
# wrong type, at any depth); it deliberately does NOT validate
# conditional-requiredness (a sibling-gated key being entirely
# absent). That gap is the owner-accepted residual (MEDIUM):
# extreme edge case, trigger is human damage to the LOCKED schema, no
# behavioural fix. A `schema_version` bump REQUIRES revisiting this
# constant (the version pin enforces it); the self-test positive
# anchor asserts the real schema passes here.
_FIELD_DEF_SHAPE: dict = {
    "type": dict,
    "what": "a mapping",
    "children": {
        "type": {"type": str, "what": "a string"},
        # enum vocab: a list ONLY when this field-def declares
        # type==enum. A scalar here pre-fix silently disabled that
        # field's vocab enforcement — now ESCALATE. NOTE
        # (accepted): `when` gates only the TYPE check. If
        # `values` is entirely ABSENT under type==enum this descriptor
        # does NOT flag it (no conditional-requiredness construct); the
        # consumer then silently drops that field's vocab. Accepted
        # residual — trigger is human damage to the LOCKED schema.
        "values": {
            "type": list,
            "what": "a list",
            "when": ("type", "enum"),
        },
        "read_aliases": {"type": dict, "what": "a mapping"},
    },
}

_TASK_SCHEMA_SHAPE: dict = {
    "type": dict,
    "what": "a mapping",
    "children": {
        # Version pin (see _TASK_SCHEMA_VERSION + the exact-match
        # check in _validate_schema_structure).
        "schema_version": {"type": int, "what": "an int"},
        "filename": {
            "type": dict,
            "what": "a mapping",
            "children": {
                # task_basename feeds re.compile() — a non-str pre-fix
                # raised an uncaught TypeError (crash class).
                "task_basename": {"type": str, "what": "a string"},
                "id_matches_basename": {"type": bool, "what": "a bool"},
            },
        },
        "required_always": {
            "type": list, "what": "a list",
            "elem_type": str, "elem_what": "a string",
        },
        "required_when_open": {
            "type": list, "what": "a list",
            "elem_type": str, "elem_what": "a string",
        },
        "required_when_terminal": {
            "type": list, "what": "a list",
            "elem_type": str, "elem_what": "a string",
        },
        "terminal_status": {
            "type": list, "what": "a list",
            "elem_type": str, "elem_what": "a string",
        },
        "fields": {
            "type": dict,
            "what": "a mapping",
            "each_value": _FIELD_DEF_SHAPE,
        },
        "validator": {
            "type": dict,
            "what": "a mapping",
            "children": {
                # locked: non-bool present -> defect/ESCALATE,
                # NEVER bool()/string-literal coercion.
                "strict_after_backfill": {"type": bool, "what": "a bool"},
            },
        },
    },
}


def _walk_schema_shape(node: dict, value: object, path: str) -> str | None:
    """Generic data-driven checker: walk `node` (a _TASK_SCHEMA_SHAPE
    descriptor) against `value`. Returns None when conforming, else a
    single human-readable defect string.

    Pure interpreter of the descriptor DATA — there is NO per-key
    isinstance ladder here. Adding a schema node = adding a data entry
    in _TASK_SCHEMA_SHAPE; this function never grows. Absent optional
    key != malformed (over-fire-safe): a child is only validated when
    PRESENT, unless its node sets required=True.
    """
    expected = node.get("type")
    if expected is not None and not isinstance(value, expected):
        # bool is an int subclass — guard would mis-accept True as int.
        # _TASK_SCHEMA_SHAPE has no int node that may receive a bool,
        # but be explicit so a future int node is not silently fooled.
        what = node.get("what", "the expected type")
        return (f"{path!r} must be {what}, got "
                f"{type(value).__name__}")
    if expected is int and isinstance(value, bool):
        what = node.get("what", "the expected type")
        return f"{path!r} must be {what}, got bool"

    elem_type = node.get("elem_type")
    if elem_type is not None and isinstance(value, list):
        for idx, elem in enumerate(value):
            if not isinstance(elem, elem_type):
                elem_what = node.get("elem_what", "the expected type")
                return (f"{path}[{idx}] must be {elem_what}, got "
                        f"{type(elem).__name__}")

    children = node.get("children")
    if children is not None and isinstance(value, dict):
        for child_key, child_node in children.items():
            present = child_key in value
            if not present:
                if child_node.get("required"):
                    return (f"{path}.{child_key!r} is required but "
                            "absent")
                continue
            when = child_node.get("when")
            if when is not None:
                sib_key, sib_val = when
                if value.get(sib_key) != sib_val:
                    continue
            child_val = value.get(child_key)
            # Absent optional key != malformed: a YAML null is treated
            # as absent (parity with the prior `is not None` predicate
            # the byte-identical bar depends on).
            if child_val is None and not child_node.get("required"):
                continue
            sub = _walk_schema_shape(
                child_node, child_val, f"{path}.{child_key}")
            if sub is not None:
                return sub

    each_value = node.get("each_value")
    if each_value is not None and isinstance(value, dict):
        for k, v in value.items():
            sub = _walk_schema_shape(each_value, v, f"{path}.{k}")
            if sub is not None:
                return sub

    return None


def _validate_schema_structure(schema: dict) -> str | None:
    """THE trust boundary. Transition the parsed schema from untrusted
    bytes to validated structure. Returns None on a conforming schema,
    else a single human-readable defect string (the caller routes it
    through `_schema_defect` -> SCHEMA_FILE ERROR + ESCALATE — no
    divergent error path).

    Two-part drift defense:
      1. Generic walk of _TASK_SCHEMA_SHAPE (the structural mirror).
      2. schema_version pin: the loaded version MUST equal the version
         the descriptor was authored against, so an intentional schema
         evolution FORCES a conscious descriptor update instead of
         silent under-validation.
    """
    defect = _walk_schema_shape(_TASK_SCHEMA_SHAPE, schema, "schema")
    if defect is not None:
        return defect
    sv = schema.get("schema_version")
    if sv is not None and sv != _TASK_SCHEMA_VERSION:
        return (f"schema_version {sv!r} != descriptor version "
                f"{_TASK_SCHEMA_VERSION} — the structural descriptor "
                "_TASK_SCHEMA_SHAPE is out of date relative to "
                "framework/task-schema.yaml; the descriptor MUST be "
                "revisited for this schema_version before validation "
                "can be trusted")
    return None


def _load_task_schema(schema_path: Path | None = None) -> dict | None:
    """Parse the machine-readable task-schema SoT.

    Returns the parsed dict, or None when the file is missing or
    unparseable (the caller turns None into a SCHEMA_FILE ERROR and
    escalates — there is no invented default).
    """
    path = schema_path if schema_path is not None else TASK_SCHEMA_PATH
    try:
        raw = path.read_text(encoding="utf-8")
    except (OSError, ValueError):  # ValueError = UnicodeDecodeError (non-UTF-8)
        return None
    try:
        data = yaml.safe_load(raw)
    except yaml.YAMLError:
        return None
    if not isinstance(data, dict):
        return None
    return data


def _schema_terminal_statuses(schema: dict) -> set:
    val = schema.get("terminal_status")
    return set(val) if isinstance(val, list) else set()


def _schema_field_defs(schema: dict) -> dict:
    fields = schema.get("fields")
    return fields if isinstance(fields, dict) else {}


def _schema_known_field_names(schema: dict) -> set:
    """Every field name the schema knows: fields map + every required set."""
    names: set = set(_schema_field_defs(schema).keys())
    for key in ("required_always", "required_when_open", "required_when_terminal"):
        val = schema.get(key)
        if isinstance(val, list):
            names.update(val)
    return names


def _schema_enum_values(field_def: object) -> list | None:
    if isinstance(field_def, dict) and field_def.get("type") == "enum":
        vals = field_def.get("values")
        if isinstance(vals, list):
            return vals
    return None


def _load_repo_extension_fields(tasks_dir: Path) -> set:
    """Per-repo task-field extension allowlist.

    The schema (`task-schema.yaml`) is a lean, framework-universal core;
    a consumer repo declares its own domain field names in
    `<repo>/docs/task-schema-extensions.yaml` (`extension_fields:` — a
    list of names). Those names are treated as known for THAT repo only,
    so the shared schema stays clean and an unknown-field WARN means a
    genuine typo or an undeclared field, not a domain-vocabulary mismatch.

    Optional + fail-safe: absent, unparseable, or malformed → empty set
    (a broken extension file never bricks validation; it only loses its
    own allowances). Repo-local; excluded from the OSS mirror by
    release-sync.sh.
    """
    ext_path = tasks_dir.parent / "task-schema-extensions.yaml"
    try:
        raw = ext_path.read_text(encoding="utf-8")
    except (OSError, ValueError):
        # ValueError covers UnicodeDecodeError (non-UTF-8 bytes): the
        # extension file is optional + fail-safe; a malformed one must
        # never crash the validator (which is a pre-commit BLOCK gate).
        return set()
    try:
        data = yaml.safe_load(raw)
    except yaml.YAMLError:
        return set()
    if not isinstance(data, dict):
        return set()
    names = data.get("extension_fields")
    if not isinstance(names, list):
        return set()
    return {n for n in names if isinstance(n, str)}


def validate_task_schema_conformance(
    project_root: Path | None = None,
    single_id: int | None = None,
    schema_path: Path | None = None,
) -> list[ValidationIssue]:
    """Schema-driven conformance pass over raw task YAML dicts.

    - project_root: repo root (or its docs/tasks dir). None → PROJECT_ROOT.
    - single_id: when set, only docs/tasks/<id>.yaml is checked (no
      milestone / cycle / cross-repo — pure schema check).
    - schema_path: override for the schema SoT (self-test injection).

    Severity is DATA-DRIVEN from validator.* in the schema:
      * structural (missing id, unparseable pure-numeric YAML,
        id != int(basename)) → ERROR regardless of calibration.
      * missing required_when_open / out-of-vocab → WARN while
        validator.strict_after_backfill is false, else ERROR.
      * unknown status value → tolerant, classified open, never error.
    """
    import re

    issues: list[ValidationIssue] = []

    schema = _load_task_schema(schema_path)
    if schema is None:
        target = schema_path if schema_path is not None else TASK_SCHEMA_PATH
        issues.append(ValidationIssue(
            "SCHEMA_FILE", "ERROR",
            detail=(f"task-schema SoT missing/unparseable: {target} — "
                    "ESCALATE: cannot validate task conformance without the "
                    "schema; tree NOT silently passed")))
        return issues

    def _schema_defect(detail: str) -> list[ValidationIssue]:
        return [ValidationIssue(
            "SCHEMA_FILE", "ERROR",
            detail=(f"task-schema SoT structurally invalid: {detail} — "
                    "ESCALATE: cannot validate task conformance with a "
                    "malformed schema; tree NOT silently passed"))]

    # THE trust boundary. Ordering is
    # load-bearing: None-check FIRST (above, unchanged), structural
    # check SECOND, both BEFORE any `_schema_*` consumer or re.compile.
    # The expected shape is declarative DATA (_TASK_SCHEMA_SHAPE) walked
    # by a single generic checker — there is no per-site isinstance
    # ladder here, so a deeper nesting level cannot recur the
    # defect class (it would be a missing DATA node, caught by
    # the §4 positive anchor self-test, not a missing code branch). A
    # present-but-wrong-type node (including filename.task_basename,
    # fields.<name>.values, validator.strict_after_backfill — the
    # keys) is fail-safe to the SAME contract as a missing
    # schema: SCHEMA_FILE ERROR + ESCALATE, never a traceback, never a
    # silent degrade. Absent optional key != malformed (over-fire-safe).
    if (d := _validate_schema_structure(schema)) is not None:
        return _schema_defect(d)

    # Past the boundary the schema is validated structure: `filename`
    # dict-or-absent, the four list keys lists, `fields` a mapping of
    # mappings, `validator` dict-or-absent, strict_after_backfill
    # bool-or-absent. These reads are now trusted (the `_schema_*`
    # accessors keep their defensive isinstance as a no-op on a
    # conformant schema — they are trusted-read accessors, NOT the
    # removed per-site schema guards).
    filename_raw = schema.get("filename")
    filename_rules = filename_raw if isinstance(filename_raw, dict) else {}
    task_basename_re = filename_rules.get("task_basename") or r"^[0-9]+$"
    id_matches_basename = bool(filename_rules.get("id_matches_basename"))

    field_defs = _schema_field_defs(schema)
    known_fields = _schema_known_field_names(schema)
    required_always = list(schema.get("required_always") or [])
    required_when_open = list(schema.get("required_when_open") or [])
    required_when_terminal = list(schema.get("required_when_terminal") or [])
    terminal_statuses = _schema_terminal_statuses(schema)

    validator_raw = schema.get("validator")
    validator_cfg = validator_raw if isinstance(validator_raw, dict) else {}
    # (locked): the calibration switch is a Python bool by
    # schema contract. The trust boundary already rejected a present
    # non-bool (-> SCHEMA_FILE ERROR + ESCALATE, NO bool()/string
    # coercion). Absent -> warn-first default (False).
    saf_raw = validator_cfg.get("strict_after_backfill")
    strict_after_backfill = saf_raw if isinstance(saf_raw, bool) else False
    # Calibration switch read in FULL — never assume strict. The
    # required/out-of-vocab severity is WARN until BOTH the backfill is
    # merged AND the switch is flipped (out_of_vocab/calibration are
    # advisory while strict_after_backfill is false).
    soft_severity = "ERROR" if strict_after_backfill else "WARN"

    name_re = re.compile(task_basename_re)

    # Resolve the tasks directory (mirror load_tasks path-resolution).
    if project_root is None:
        tasks_dir = loading.TASKS_DIR
    elif project_root.name == "tasks" and project_root.is_dir():
        tasks_dir = project_root
    else:
        tasks_dir = project_root / "docs" / "tasks"

    # Lean framework core (schema fields) + repo-local domain fields:
    # union the per-repo extension allowlist so a consumer's declared
    # vocabulary is known for its own tree without a framework-schema edit.
    known_fields = known_fields | _load_repo_extension_fields(tasks_dir)

    if single_id is not None:
        # (belt): a single-id target has an explicit name that
        # MUST resolve or error — it may never silently `continue`. The
        # negative/zero argv case is rejected at the dispatch boundary
        # (exit 2); this guard is defence-in-depth for direct callers.
        if not name_re.match(str(single_id)):
            issues.append(ValidationIssue(
                "SCHEMA_FILE", "ERROR", task_id=single_id,
                detail=(f"invalid single-id target {single_id!r}: fails "
                        f"task_basename grammar {task_basename_re!r} — "
                        "ESCALATE: single-id has an explicit target that "
                        "must resolve or error, never silently skipped")))
            return issues
        # archived terminal tasks live in
        # docs/tasks/archive/<id>.yaml. In single-id mode, fall back to
        # the archive when the primary path is absent — an archived task
        # is terminal (only id+status enforced), NOT a 'file not found'
        # ERROR.
        primary = tasks_dir / f"{single_id}.yaml"
        archived = tasks_dir / "archive" / f"{single_id}.yaml"
        if primary.exists():
            candidates = [primary]
        elif archived.exists():
            candidates = [archived]
        else:
            issues.append(ValidationIssue(
                "SCHEMA_FILE", "ERROR", task_id=single_id,
                detail=f"task file not found: {primary}"))
            return issues
    else:
        candidates = sorted(p for p in tasks_dir.glob("*.yaml"))

    # zero-pad duplicate-logical-id collision. `327.yaml` and
    # `0327.yaml` both map to int(basename)=327 — pre-fix BOTH were
    # silently validated as task 327. Detect as a duplicate-id ERROR
    # (calibration-independent structural defect).
    if single_id is None:
        by_logical: dict[int, list[str]] = {}
        for p in candidates:
            bn = p.stem
            if name_re.match(bn):
                by_logical.setdefault(int(bn), []).append(p.name)
        for lid, names in sorted(by_logical.items()):
            if len(names) > 1:
                issues.append(ValidationIssue(
                    "SCHEMA_ID_MISMATCH", "ERROR", task_id=lid,
                    detail=(f"duplicate logical task id {lid}: "
                            f"{sorted(names)} all resolve to "
                            f"int(basename)={lid}")))

    for yaml_path in candidates:
        basename = yaml_path.stem
        # Filename grammar: a *task* has a pure-numeric basename. Any
        # NNN-<suffix> aux file is never a task — never validated/errored.
        if not name_re.match(basename):
            continue

        basename_int = int(basename)
        tid_for_issue: int | None = basename_int

        try:
            data = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
        except (yaml.YAMLError, OSError, ValueError):
            # A pure-numeric file that won't parse is a structural ERROR
            # (calibration-independent) — it claims to be a task.
            issues.append(ValidationIssue(
                "SCHEMA_FILE", "ERROR", task_id=tid_for_issue,
                detail=f"unparseable task YAML: {yaml_path}"))
            continue

        if not isinstance(data, dict):
            issues.append(ValidationIssue(
                "SCHEMA_FILE", "ERROR", task_id=tid_for_issue,
                detail=f"task YAML is not a mapping: {yaml_path}"))
            continue

        raw_id = data.get("id")
        # Structural: missing id (ERROR regardless of calibration).
        if raw_id is None:
            issues.append(ValidationIssue(
                "SCHEMA_MISSING_REQUIRED", "ERROR", task_id=tid_for_issue,
                detail=f"required field 'id' missing in {yaml_path.name}"))
        else:
            try:
                id_int = int(raw_id) if not isinstance(raw_id, bool) else None
            except (TypeError, ValueError):
                id_int = None
            if id_int is None:
                issues.append(ValidationIssue(
                    "SCHEMA_ID_MISMATCH", "ERROR", task_id=tid_for_issue,
                    detail=f"'id' is not an int: {raw_id!r} in {yaml_path.name}"))
            elif id_matches_basename and id_int != basename_int:
                # Structural: id != int(basename) — ERROR regardless.
                issues.append(ValidationIssue(
                    "SCHEMA_ID_MISMATCH", "ERROR", task_id=tid_for_issue,
                    detail=(f"id {id_int} != int(basename) {basename_int} "
                            f"in {yaml_path.name}")))

        # Status classification. Unknown value → tolerant-read-as-open,
        # never silently terminal, never an error.
        raw_status = data.get("status")
        is_open = True
        if isinstance(raw_status, str) and raw_status in terminal_statuses:
            is_open = False
        # raw_status not in the schema status enum → unknown → stays open.

        # Required-set checks. Terminal tasks (done / superseded / wontfix /
        # absorbed) enforce ONLY required_when_terminal (id + status): history
        # is not rewritten, so a missing field on a closed task is not a defect
        # and cannot be meaningfully backfilled. Open tasks enforce
        # required_always (+ required_when_open below).
        base_required = required_always if is_open else required_when_terminal
        for fname in base_required:
            if data.get(fname) is None:
                # 'id' already handled structurally above.
                if fname == "id":
                    continue
                issues.append(ValidationIssue(
                    "SCHEMA_MISSING_REQUIRED", soft_severity,
                    task_id=tid_for_issue,
                    detail=(f"required field '{fname}' missing in "
                            f"{yaml_path.name}")))
        if is_open:
            for fname in required_when_open:
                if data.get(fname) is None:
                    issues.append(ValidationIssue(
                        "SCHEMA_MISSING_REQUIRED", soft_severity,
                        task_id=tid_for_issue,
                        detail=(f"required-when-open field '{fname}' missing "
                                f"in {yaml_path.name} (status="
                                f"{raw_status!r}, classified open)")))

        # Unknown field names (forward-compat: WARN, never blocks).
        for key in data:
            if key not in known_fields:
                issues.append(ValidationIssue(
                    "SCHEMA_UNKNOWN_FIELD", "WARN", task_id=tid_for_issue,
                    detail=(f"unknown field '{key}' in {yaml_path.name} "
                            "(not in task-schema.yaml fields/required sets "
                            "or the repo task-schema-extensions.yaml)")))

        # Value-vocabulary checks. Every enum field's vocab is read from
        # the schema. priority is write-strict: read_aliases are tolerant
        # on READ-classification only; an alias written into a YAML is
        # out-of-vocab here.
        for fname, fdef in field_defs.items():
            enum_vals = _schema_enum_values(fdef)
            if enum_vals is None:
                continue
            if fname not in data or data.get(fname) is None:
                continue
            value = data.get(fname)
            if value in enum_vals:
                continue
            if fname == "status":
                # Unknown status is tolerant (handled above) — not vocab err.
                continue
            issues.append(ValidationIssue(
                "SCHEMA_VOCAB", soft_severity, task_id=tid_for_issue,
                detail=(f"field '{fname}' value {value!r} not in schema "
                        f"vocab {enum_vals} ({yaml_path.name})")))

    return issues


