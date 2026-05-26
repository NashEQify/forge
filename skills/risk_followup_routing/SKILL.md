---
name: risk-followup-routing
description: >
  Routes chief-verdict `remaining_findings:` entries per their
  `target:` annotation (7-value enum: spec_text / new_task /
  watch_item / accept / absorb_next / closes_with / re_review). Replaces
  the legacy `risk-followup-task` step which mechanically created
  one task per finding regardless of finding type.
  Triggers when a chief verdict carries remaining_findings: entries to route by their target: annotation; NOT for creating tasks directly (use task_creation).
status: active
invocation:
  primary: workflow-step
  secondary: []
disable-model-invocation: false
spec_ref: docs/specs/306-brief-architect.md
uses: [task_creation]
---

# Skill: risk-followup-routing

## Purpose

Dispatch each `remaining_findings:` entry from a chief verdict to
the correct downstream destination based on its `target:` field.
Replaces the legacy `risk-followup-task` step which created one
task per finding (wrong granularity for the actual mix of finding
types).

## When to call

- Build workflow `close-bookkeeping` gate, after chief verdict.
- Fix workflow analogous gate, after chief verdict.
- Review workflow analogous gate, after chief verdict.

The chief is responsible for annotating every entry with `target:`
per the 7-value enum (spec 306 §4.7 + `code_review_board/SKILL.md` §5).
This skill assumes that annotation exists; if any entry has empty
`target:`, the skill fails with a clear error and surfaces back to
the chief for re-emit.

## Input

- Path to chief verdict file (e.g.
  `docs/reviews/board/<id>-consolidated.md`).
- Path to consumer's `context/risk-watch.md` (created if absent
  per `skills/_protocols/risk-watch-template.md`).

## Process

1. Parse the chief verdict's `remaining_findings:` block. Validate
   that every entry has a `target:` field. On missing field: FAIL
   with `target_missing_on_<id>`.

1a. **Mechanical anti-goldplating gates (NON-NEGOTIABLE).** For every
    entry with `target: new_task`, run these gates BEFORE dispatch.
    The dispatcher does not negotiate and does not ask the chief to
    re-emit — the gate IS the answer. A failing gate rewrites the
    entry's target in-memory; the original chief annotation is logged
    as `chief-emit: new_task → <new-target> per Gate <X>`.

    Intent: ask explicitly *"is this gold plating? if yes — out."*
    once, mechanically, at the only place where new_task creation
    happens. Chief-side prose ("standalone LOW → accept") proved
    permissive in practice (bundling, value-floor erosion, dormant
    consumers); the gate makes the answer non-permissive.

    Run in order L → G → C. The first gate that fires routes the
    entry; subsequent gates do not re-fire on the same entry.

    - **Gate L — LOW floor (bundle-proof).** If `severity` ∈
      {low, LOW} → reroute. `bundle_with:` or `bundle:` does NOT
      promote severity; a bundle of N LOWs is still LOW. Severity
      lives per-entry, not per-bundle.
      Target rewrite:
      - `value_class: real-impact` → `absorb_next` (next file-touch
        closes; locator carries the anchor)
      - `value_class: nice-to-have` or missing → `accept`
      Log: `<id> reroute LOW→<target> per Gate L`.

    - **Gate G — Goldplating self-admission.** If `value_class:
      nice-to-have` regardless of severity → reroute to `accept`.
      The label itself is the gold-plating answer; no second check.
      "Nice-to-have" as a follow-up task is a contradiction in terms:
      either it has a measurable cost (then upgrade `value_class` to
      `real-impact` with named cost) or it does not (then `accept`).
      Log: `<id> reroute nice-to-have→accept per Gate G`.

    - **Gate C — Critical-path consumer (lens at closeout).** If
      `consumers:` is missing OR empty OR contains zero entries
      referencing an in-flight task in an active milestone:
        - Cross-ref `python3 $FRAMEWORK_DIR/scripts/plan_engine.py
          --boot` IN_PROGRESS + NEXT ACTIONS + active-milestone
          `ready` set.
        - Consumer string of shape `Task-NNN-...` (or `task-NNN`,
          `NNN`, etc.) is "in-flight" iff NNN appears in IN_PROGRESS
          or NEXT ACTIONS or active-milestone ready set.
        - Consumer string of shape `future-...`, `<role>-when-X`,
          any non-Task-NNN string, or a Task-NNN that lives in a
          dormant milestone (POST-MVP, future, BLOCKED) is by
          definition not in-flight (it is a future event or a
          generic user-role or a parked task).
      → reroute to `watch_item`. Derive `trigger:` from the consumer
      string:
        - `Task-NNN-<slug>` → `trigger: "Task NNN picked up"`
        - `future-<event>` → `trigger: "<event>"`
        - `<role>-on-<surface>` → `trigger: "<role> reports
          regression on <surface>"`
      If the consumer string is too vague to derive a trigger, FAIL
      with `consumer_vague_on_<id>` (chief must re-emit with a
      named trigger or change disposition).
      Log: `<id> reroute new_task→watch_item per Gate C (no active
      consumer; trigger: <derived>)`.

    After Gate processing, the dispatch report includes a summary
    line: `<N> chief-emit new_tasks → <M> survived gates → <N-M>
    rerouted (<by-gate breakdown>)`. The user sees what was caught.

    **Override:** the user (not the chief, not Buddy) may explicitly
    re-route a gated entry back to `new_task` with the phrase
    `override Gate <X> on <id>: <one-sentence reason>`. The override
    is logged verbatim into the verdict-archive and into the spawned
    task's `notes:`. No silent override.

2. Group entries by `target:` value (post-gate rewrite):
   - `spec_text`: collect all into a single batch.
   - `new_task`: each entry filed independently.
   - `watch_item`: collect for risk-watch append.
   - `accept`: collect for chief-verdict-archive log (accepted
     limitations — distinct from `absorb_next`: no future fix
     implied).
   - `absorb_next`: collect for chief-verdict-archive log.
   - `closes_with: <id>`: validate referenced finding exists in
     same verdict; collect for assertion log.
   - `re_review: <reviewer>`: collect for re-dispatch.
3. Dispatch per group:
   - **spec_text batch:** if non-empty, dispatch
     `agents/spec-text-drift-batch.md` once with the full list
     (per spec 306 §4.8). If chief verdict is FAIL and MCA
     fix-pass dispatches in parallel, fire both in one tool message
     (the parallel-dispatch invariant is in §4.8).
   - **new_task per entry:** dispatch `task_creation` skill per
     entry. When called from this routing, skip the
     duplicate-check step of `task_creation` (the chief verdict
     already deduped at finding-level).
   - **watch_item:** if `context/risk-watch.md` doesn't exist,
     create from `skills/_protocols/risk-watch-template.md`. Append
     each entry verbatim under `## Entries`.
   - **accept:** log to `docs/reviews/board/archive/<verdict-id>-accepted.md`
     (one file per verdict; append within file) as a known
     accepted limitation. No fix, no task, no trigger.
   - **absorb_next:** log to `docs/reviews/board/archive/<verdict-id>-absorbed.md`
     (one file per verdict; append within file). No further action.
   - **closes_with:** assert the referenced finding exists in the
     same verdict. On miss: FAIL with `closes_with_target_missing`.
     On hit: log assertion, no further action.
   - **re_review:** dispatch the named reviewer with the finding
     cluster as scoped focus. The re-review's verdict appends to
     the existing chief verdict (not a new pass). One-shot — if
     uncertainty persists, escalate to council per existing
     cross-layer-decision pattern.
4. Aggregate routing report: `<N> entries routed (<count> spec_text,
   <count> new_task, <count> watch_item, <count> accept,
   <count> absorb_next, <count> closes_with, <count> re_review)`.

## Output

DELIVERS:
- Spec-text patches applied (via spec-text-drift-batch sub-agent
  return, when spec_text entries exist).
- Tasks filed (via task_creation per entry).
- Risk-watch append (one or more entries).
- Archive log for accept and absorb_next entries.
- closes_with assertions logged.
- Re-review dispatched for re_review entries.

DOES NOT DELIVER:
- No semantic edit of finding content. The routing applies what
  the chief decided; it does not re-decide.
- No task duplicate-check (delegated to chief verdict's
  finding-level dedup; explicit skip-flag passed to task_creation).

ENABLES:
- Bulk-task-bloat avoidance (vs the legacy `risk-followup-task`
  which filed one task per finding regardless of type).
- Mechanical traceability (every finding ends up in a known
  location: applied diff / task / risk-watch / archive log).

## Failure modes

- **Missing `target:` field:** chief verdict didn't annotate all
  entries. FAIL — return to chief for re-emit.
- **`closes_with: <id>` references non-existent finding:** chief
  emit error. FAIL with locator.
- **`re_review: <reviewer>` references unknown reviewer:** the
  reviewer name is not in the framework's persona registry. FAIL
  with reviewer name + suggestion to use a known persona.
- **spec-text-drift-batch returns PARTIAL:** some entries skipped.
  Surface the skip reasons to user; the routing succeeds for the
  applied entries but flags partial-completion.
- **`consumer_vague_on_<id>` (Gate C):** chief routed `new_task`
  with consumers that can't be cross-referenced to plan_engine AND
  are too vague to derive a `watch_item` trigger from. FAIL — chief
  must re-emit with either (a) a named in-flight consumer task ID,
  (b) a named future trigger event, or (c) downgrade to `accept`.
  Do NOT default-route to `new_task` "to be safe" — that is exactly
  the goldplating path the gates exist to close.

## Anti-goldplating gates — why they exist

The 4-gate chain (target → Gate L → Gate G → Gate C → dispatch) is a
response to a recurring closeout failure mode: chief annotates
`target: new_task` per finding, dispatcher routes mechanically, the
user reviews the spawned tasks the next session and drops them as
goldplating. Three drop-classes observed (Task 520 closeout, 2026-05-26):

- **LOW bundled into "cleanup pass"** — chief escapes the standalone-
  LOW floor by bundling N LOWs into one task. Each item is still
  LOW; the task is still backlog noise. Gate L closes this.
- **`nice-to-have` routed as task** — chief self-admits "nice-to-have"
  AND routes new_task. The label IS the answer; Gate G closes this.
- **Dormant consumer** — chief names a consumer that is real but
  not in-flight (Task in POST-MVP milestone, future-event, future-
  feature-expansion). The right vehicle is a watch_item with the
  consumer-activation as trigger. Gate C closes this.

The gates are mechanical because the prose version of these rules
already exists in `code_review_board/SKILL.md` §5 and was demonstrably
permissive in practice. Hard mechanical rejection at the dispatch
gate replaces the chief-side discipline expectation.

## Replaces

- Legacy `risk-followup-task` step in build / fix / review
  WORKFLOW.md. The legacy step's name is preserved as a deprecated
  alias for one release cycle to avoid breaking in-flight runs;
  new dispatches use `risk-followup-routing`.
