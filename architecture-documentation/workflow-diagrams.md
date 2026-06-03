# Workflow diagrams — one per workflow

The README shows the *shared shape* every workflow follows. This page
draws each of the eight workflows in full: its real phases (boxed), the
steps inside them, where a board / council / agent is spawned, the loops,
and where the result leaves the workflow.

## The shared shape

A **workflow is the home** — the container the work lives in, with its
place persisted per step (`.workflow-state/<id>.json`) so a paused run
resumes exactly where it stopped, even across sessions and machines.

Inside the home are **phases** (the boxes); inside phases are **steps**
(listed to the right). A step is where a **skill** runs — and some skills
spawn a **cold sub-routine**: a board, a council, or the code-agent, each
running context-isolated (reviewers never see the orchestrator's framing)
and returning only one consolidated **chief signal** back into the step.
When a check fails the flow **loops** — fix and re-review, bounded to a
fixed number of passes, then it escalates. The **result** leaves the
container at the bottom — it is the output of the whole workflow, not of
any single board pass.

```
legend
  ┌─────────┐
  │  phase  │  steps run inside the phase (listed right) — a step runs a skill
  └────┬────┘
       ▼            phases run top → bottom
  ◄ ≤N              a bounded loop: N passes, then escalate to the user
  cold → 1 signal   context-isolated spawn (board / council / agent); only
                    the chief's consolidated signal returns
  RESULT            leaves the container at the bottom — the workflow's output
```

The path (or route) is chosen *before* the phases run and sets the depth:
the lightest path skips the apparatus entirely, the heaviest runs every
gate. Effort scales to the stakes.

---

## Producers — `build` · `fix` · `review` · `research` · `solve`

### build — implement a feature or task

```
┌─ build · implement a feature or task ─────────────────────────────────────────────┐
│  paths: DIRECT · STANDARD · FULL · SUB-BUILD · STD-IMPL-ONLY · AUTHORITY-ONLY     │
│                                                                                   │
│  ┌─────────┐                                                                      │
│  │ Specify │  interview (frame) · spec-write · board ─► spec-board | council      │
│  └────┬────┘                                                                      │
│  ┌────▼────┐                                                                      │
│  │ Prepare │  test-design (+adversary) · architect-lens · brief-author · sign-off │
│  └────┬────┘                                                                      │
│  ┌────▼────┐                                                                      │
│  │ Execute │  main-code-agent:  plan → impl-plan-review → implement → L0          │
│  └────┬────┘                                                                      │
│  ┌────▼────┐                                                                      │
│  │ Verify  │  code-review-board (L1 / L2) · spec-drift    ◄ review → re-fix ≤3    │
│  └────┬────┘                                                                      │
│  ┌────▼────┐                                                                      │
│  │ Close   │  bookkeeping (ADR · risk · knowledge) · commit + deploy              │
│  └────┬────┘                                                                      │
│       │  FULL: spec in levels  E1 ─► board ─► E2 ─► board ─► E3 ─► board (deep)   │
└───────┼───────────────────────────────────────────────────────────────────────────┘
        ▼
     RESULT — committed, deployed
```

### fix — root-cause a bug, no symptom-patching

```
┌─ fix · root-cause a bug, no symptom-patching ─────────────────────────────────────┐
│  paths: STANDARD · SUB-FIX · (FULL reserved)                                      │
│                                                                                   │
│  ┌─────────┐                                                                      │
│  │ Specify │  root-cause (symptoms → hypotheses → drill ◄ ≤3) · RED test first    │
│  └────┬────┘                                                                      │
│  ┌────▼────┐                                                                      │
│  │ Prepare │  fix-brief (architect, on substantial fixes) · sign-off              │
│  └────┬────┘                                                                      │
│  ┌────▼────┐                                                                      │
│  │ Execute │  make the RED test green ◄ ≤3 · regression suite green               │
│  └────┬────┘                                                                      │
│  ┌────▼────┐                                                                      │
│  │ Verify  │  code-review-board (light / L1 / L2) · spec-drift   ◄ re-fix ≤2      │
│  └────┬────┘                                                                      │
│  ┌────▼────┐                                                                      │
│  │ Close   │  lessons (knowledge) · risk follow-up · commit + deploy              │
│  └────┬────┘                                                                      │
│       │  SUB-FIX (nested in a parent build) skips Close — parent owns task status │
└───────┼───────────────────────────────────────────────────────────────────────────┘
        ▼
     RESULT — committed, deployed
```

### review — validate a spec, no code

```
┌─ review · validate a spec, no code ────────────────────────────────────────────────┐
│                                                                                    │
│  ┌──────────┐                                                                      │
│  │ routing  │  classify ─► spec-board (std/deep) | sectional | arch-coherence | ux │
│  └────┬─────┘                                                                      │
│  ┌────▼─────┐                                                                      │
│  │ board    │  spawn the routed board, cold → chief consolidates → 1 signal        │
│  └────┬─────┘                                                                      │
│  ┌────▼─────┐                                                                      │
│  │ converge │  NEEDS-WORK → fix → re-board   ◄ ≤3, PASS at 0 crit + 0 high         │
│  └────┬─────┘                                                                      │
│  ┌────▼─────┐                                                                      │
│  │ close    │  remaining findings → follow-up task                                 │
│  └────┬─────┘                                                                      │
│  ┌────▼─────┐                                                                      │
│  │ commit   │  update board_result + readiness                                     │
│  └────┬─────┘                                                                      │
│       │                                                                            │
└───────┼────────────────────────────────────────────────────────────────────────────┘
        ▼
     RESULT — validated spec
```

### research — close a knowledge gap, output is knowledge not code

```
┌─ research · close a knowledge gap — output is knowledge, not code ──────┐
│  quality: standard · high (≥3 sources + adversary)                      │
│                                                                         │
│  ┌──────────┐                                                           │
│  │ scope    │  read prior research · pick the quality level   ◄ ≤2      │
│  └────┬─────┘                                                           │
│  ┌────▼─────┐                                                           │
│  │ research │  web search · web fetch · API docs              ◄ ≤3      │
│  └────┬─────┘                                                           │
│  ┌────▼─────┐                                                           │
│  │ synth    │  consensus · matrix · position  (high: + adversary)  ◄ ≤2 │
│  └────┬─────┘                                                           │
│  ┌────▼─────┐                                                           │
│  │ capture  │  persist findings · close context gaps · flag impact      │
│  └────┬─────┘                                                           │
│  ┌────▼─────┐                                                           │
│  │ commit   │  git pre-commit hooks                                     │
│  └────┬─────┘                                                           │
│       │                                                                 │
└───────┼─────────────────────────────────────────────────────────────────┘
        ▼
     RESULT — knowledge artifact
```

### solve — a problem whose solution shape is still open

```
┌─ solve · a problem whose solution shape is still open ────────────────────────────┐
│  single path · frame depth: quick · focused · deep                                │
│                                                                                   │
│  ┌──────────┐                                                                     │
│  │ frame    │  frame (8 sub-steps): reformulate → first-principles → recommend    │
│  └────┬─────┘                                                                     │
│  ┌────▼─────┐                                                                     │
│  │ refine   │  user dialog · council (only if >1 path AND hard-to-reverse)        │
│  └────┬─────┘                                                                     │
│  ┌────▼─────┐                                                                     │
│  │ artifact │  author the artifact (spec / runbook / protocol / plan)             │
│  └────┬─────┘                                                                     │
│  ┌────▼─────┐                                                                     │
│  │ validate │  classify → routed board → convergence ◄ ≤3 → delta-verify          │
│  └────┬─────┘                                                                     │
│  ┌────▼─────┐                                                                     │
│  │ apply    │  direct | hand off to build | hand off to docs-rewrite | self-apply │
│  └────┬─────┘                                                                     │
│  ┌────▼─────┐                                                                     │
│  │ close    │  ADR (when the decision meets the triple) · knowledge wrap-up       │
│  └────┬─────┘                                                                     │
│  ┌────▼─────┐                                                                     │
│  │ commit   │  git commit + push · deploy                                         │
│  └────┬─────┘                                                                     │
│       │                                                                           │
└───────┼───────────────────────────────────────────────────────────────────────────┘
        ▼
     RESULT — reproducible solution artifact
```

---

## Other shapes — `docs-rewrite` · `save` · `context_housekeeping`

### docs-rewrite — rewrite reader-facing docs, reader-journey-first

```
┌─ docs-rewrite · rewrite reader-facing docs, reader-journey-first ────────────┐
│                                                                              │
│  ┌───────────┐                                                               │
│  │ Research  │  Explore agent → research doc        ◄ follow-ups ≤2          │
│  └─────┬─────┘                                                               │
│  ┌─────▼─────┐                                                               │
│  │ Structure │  page plan + reader journeys  (every persona finds an entry)  │
│  └─────┬─────┘                                                               │
│  ┌─────▼─────┐                                                               │
│  │ Write     │  one writer agent per page, parallel   ◄ rewrites ≤2          │
│  └─────┬─────┘                                                               │
│  ┌─────▼─────┐                                                               │
│  │ Coherence │  uniform terms · transitions · no redundancy                  │
│  └─────┬─────┘                                                               │
│  ┌─────▼─────┐                                                               │
│  │ Assemble  │  index · nav · cross-links · stale cleanup  (mkdocs --strict) │
│  └─────┬─────┘                                                               │
│  ┌─────▼─────┐                                                               │
│  │ Review    │  spec-board (ux): 3 UX personas       ◄ re-review ≤1          │
│  └─────┬─────┘                                                               │
│  ┌─────▼─────┐                                                               │
│  │ Close     │  task update · build-test · commit · deploy · verify          │
│  └─────┬─────┘                                                               │
│        │                                                                     │
└────────┼─────────────────────────────────────────────────────────────────────┘
         ▼
      RESULT — live site
```

### save — persist the session so the next one boots warm

```
┌─ save · persist the session so the next one boots warm ───────────────────────────┐
│  3 groups · mid-session vs end-of-session footprint auto-adapts                   │
│                                                                                   │
│  ┌────────────┐                                                                   │
│  │ Pre-write  │  dispatcher · reconcile gaps/task-status · workflow-state handoff │
│  └─────┬──────┘                                                                   │
│  ┌─────▼──────┐                                                                   │
│  │ Writes     │  PARALLEL: session-handoff.md (9-pt merge)  ‖  history/ entry     │
│  └─────┬──────┘                                                                   │
│  ┌─────▼──────┐                                                                   │
│  │ Post-write │  commit + push · buffer cleanup                                   │
│  └─────┬──────┘                                                                   │
│        │                                                                          │
└────────┼──────────────────────────────────────────────────────────────────────────┘
         ▼
      RESULT — next session reads the handoff on boot
```

### context_housekeeping — periodic upkeep of the context system

```
┌─ context_housekeeping · periodic upkeep of the context system ────────────────┐
│  2 groups                                                                     │
│                                                                               │
│  ┌──────────┐                                                                 │
│  │ analysis │  read-only: line-counts · nav · orphans · dead-links · currency │
│  └────┬─────┘                                                                 │
│  ┌────▼─────┐                                                                 │
│  │ curation │  per area: resize · update/remove stale · split/merge  ◄ resume │
│  └────┬─────┘                                                                 │
│       │                                                                       │
└───────┼───────────────────────────────────────────────────────────────────────┘
        ▼
     RESULT — context system curated
```

---

## How they relate

All eight share one backbone — engine-tracked state per step, boards and
council spawned cold inside steps, bounded loops that escalate on
overshoot, a terminal phase whose output leaves the container. They differ
in their phases and in which sub-routines each step reaches for. Workflows
also hand off to one another: a `solve` can hand its artifact to `build`; a
`build` interview can spawn a `research` sub-workflow; `research` can feed
back into `solve` or `build`.

For the model behind the diagrams — the tier stack, the engine, and how
boards stay context-isolated — see
[`02-architecture.md`](02-architecture.md) and
[`06-usage-workflows.md`](06-usage-workflows.md). Routing (which workflow
for which intent) lives in
[`../framework/process-map.md`](../framework/process-map.md).
