# solve Workflow — REFERENCE

Detail mechanics. Reference for state-file format, slug convention,
first-run, problem decomposition, variant details. The Buddy-facing WORKFLOW.md is
the checklist.

## State file — detail format

One file per solve invocation: `docs/solve/YYYY-MM-DD-<slug>.md`.

**Frontmatter (mandatory):**
```yaml
---
workflow: solve
problem: short problem description (1 line)
started: YYYY-MM-DD
phase: frame | refine | artifact | validate | execute | done
status: active | paused | done | aborted
task_ref: NNN | null
artefacts: [list of produced files]
---
```

`workflow` identifies the workflow type (for workflow-agnostic tooling).
`task_ref` links to the task YAML (null if no task exists).
Both fields are mandatory. Existing state files are
not migrated — on resume, Buddy adds the fields inline.

**Body structure:** one `## Phase N: <name>` block per phase, append-only.
- Phase 1: frame report (8 sub-steps from frame)
- Phase 2: refinement notes (dialogue results, chosen approach)
- Phase 3: artefact refs + registration plan
- Phase 4: board result (consolidated with tracking table)
- Phase 5: execute result (applied actions, deploy, handoff)

**After every phase:** body extension + frontmatter `phase` update + commit.

## Slug convention

- `<kebab-case-short-topic>`
- At most 40 characters, lowercase, no special characters
- Derivation: first 3-5 significant words of the problem description
- Examples: `2026-04-05-solve-bootstrap.md`, `2026-04-12-dashboard-perf.md`
- On naming collision: counter suffix (`-2`, `-3`) or timestamp
  (`YYYY-MM-DD-HHMM-<slug>.md`)

## First run (new project)

`mkdir -p docs/solve` before the first state-file write (idempotent). For
clones/forks without prior solve invocations.

## Problem decomposition (exception)

If the problem is recognised as too large in Phase 1: **decompose inline in the
same state file**. The body then contains multiple Phase-1 sub-blocks:

```
## Phase 1: Frame (Sub-Problem A)
{8 sub-steps for A}

## Phase 1: Frame (Sub-Problem B)
{8 sub-steps for B}

## Phase 2: Refine
{operates on the combined understanding of all sub-problems}
```

**No scoping handoff** — scoping is for objectives with a known done,
not for unframed problem decomposition. See
`skills/frame/REFERENCE.md` §Edge Cases.

**Iteration-bound mechanics:** "Frame max 1" refers to one frame
pass per problem OR sub-problem. On decomposition: N sub-problems = N
frames, but each sub-frame runs only once. User feedback after frame =
Phase 2 Refine, not a new frame.

## Phase 5 Execute — variant details

### Variant 1: Direct (skill/runbook/protocol)
1. Artefact final-committed (from Phase 4)
2. Extend process-map.md (routing + skill taxonomy + composition map + maturity)
3. Stale cleanup: grep for replaced artefacts, fix all references
4. If docs/ is affected: deploy via `$FRAMEWORK_DIR/scripts/deploy-docs.sh`
5. Visual verification (CLAUDE.md §Deployment Verification) or ask the user
6. knowledge_processor wrap-up -> history entry
7. State file `status: done`, final commit

### Variant 2: Handoff Build
1. Artefact is a spec/plan for feature implementation
2. The build workflow Phase 1 Specify takes the artefact as input
3. solve Phase 5 = document handover + status: done
4. The build workflow continues independently
5. knowledge_processor wrap-up in solve close
6. State file `status: done`, final commit

### Variant 3: Handoff docs-rewrite
1. Artefact is a docs plan
2. docs-rewrite/WORKFLOW.md takes over
3. Analogous to Variant 2 (handover + solve close)

### Variant 4: Self-apply
1. Artefact is directly executable (e.g. a fix script, a configuration update)
2. Buddy executes it in the solve Phase 5 step
3. Verification + knowledge_processor wrap-up
4. State file `status: done`, final commit

## Status transitions

- `active` -> `paused`: user request or session end mid-phase
- `active` -> `done`: Phase 5 successfully completed
- `active` -> `aborted`: user abort or unrecoverable failure
- `paused` -> `active`: resume on a new session (boot finds via `ls docs/solve/`)

## ADR check in Phase 5 Execute

Optional `adr-check` step between `apply-artifact` and `knowledge-processor`.
Triggers `skills/documentation_and_adrs/SKILL.md` when the ADR-discipline triple
is satisfied:

- **Hard-to-reverse** — meaningful cost to switch later
- **Surprising-without-context** — future reader asks "why like this?"
- **Result-of-real-trade-off** — genuine alternatives with justification

Solve is by definition for **open solution shape** — the skip rate is lower
than for build. The frame report (Phase 1) has already documented trade-offs,
Phase 2 Refine has sharpened them, Phase 5 Apply has activated them. If the chosen
approach satisfies the triple: ADR with cross-reference to the frame report.

`required: false`, `on_fail: warn`. Anti-pattern: ADR inflation.

## Trigger validation (Phase 0 — at intake)

Before Phase 1 starts: trigger validation against the NOT-FOR list in
WORKFLOW.md. If the problem actually belongs to another workflow
(bug, knowledge question, clear feature): redispatch immediately, do not force it
through Phase 1. Document the redispatch decision in the state file
and close it with `status: aborted` (reason: "redispatched to <workflow>").
