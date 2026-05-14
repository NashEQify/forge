# 06 — Usage + Workflows

How to use the framework in practice: quickstart, typical workflows,
patterns, anti-patterns, best practices.

## Quickstart

```bash
$ cc framework
Buddy: Boot complete. What's up?

User: I want to apply the fix workflow to a bug I just spotted in
src/foo.py.

Buddy: <intake gate ACTIONABLE>
       <plan-block: scope = src/foo.py, agent = main-code-agent,
        artefact = Fix + Test, route = fix workflow Phase Specify>
       <starts workflow_engine.py --start fix --task NNN>
       <Phase Specify with root_cause_fix skill>
       ...
```

Buddy is the only agent the user talks to directly. Everything else goes through Buddy.

### How the user triggers workflows (engine layer)

The user NEVER calls the engine directly — Buddy translates natural-language
intent into engine commands. Trigger phrases:

| You say | Buddy starts |
|---|---|
| `build task <id>` / `feature X for task <id>` | `workflow_engine.py --start build --task <id>` |
| `build task <id> as sub-build` (parent has an existing locked spec) | `--start build --task <id> --route sub-build` (skips interview/spec-write/board) |
| `fix bug <description>` / `fix task <id>` | `--start fix --task <id>` |
| `fix task <id> nested in build` | `--start fix --task <id> --route sub-fix` (parent owns task-status) |
| `review spec <path>` | `--start review --task <id>` |
| `solve <problem>` | `--start solve --task <id>` |
| `research <topic>` | `--start research --task <id>` |
| `docs rewrite` | `--start docs-rewrite` |
| `save` (end-of-session) | `--start save` (or DIRECT short-path) |
| `retry step <id>` | `--retry <step-id> --reason "<why>"` (iteration cap default 3) |

**Path routing:** `build` and `fix` have top-level `routes:` in workflow.yaml.
The default route is `standard` without `--route`. For nested iteration
(sub-build/sub-fix) `--route` MUST be set explicitly — otherwise item 1's
task-status-done fires and incorrectly marks the parent task as done.

What you see as a user:

- **Boot:** resume line `WORKFLOWS: build [task <id>] step 7/15 (since 2h)`
  — at session start you immediately know where you left off
- **Every turn:** `WORKFLOW-ENGINE: NEXT: build [task <id>] > <step-name>:
  <instruction>` as a header in Buddy's response
- **Pre-commit:** workflow with unfinished `commit_gate: true` steps blocks
  the commit (workflow-commit-gate.sh hook)
- **Cross-session resume:** if you close the session mid-flow and reopen
  later — the engine puts you on the same step. State lives in
  `.workflow-state/<id>.json` (git-tracked content since 2026-05-14 —
  syncs across machines via push/pull; `_lock` mutex stays local)

Skip list (engine NOT active):

- DIRECT path build/fix (≤3 files, no spec, no new behaviour) —
  executed inline
- save/quicksave/checkpoint/wakeup/sleep — no multi-step state
- context_housekeeping — maintenance with no pause points
- frame/bedrock_drill standalone — sub-skills
- think! — open discussion

Mechanical fallback: pre-commit Check 8 (`ENGINE-USE`) WARNS when a
`feat|fix|refactor` commit with a `[Task-NNN]` ref has no active workflow
— catching the case where Buddy mentally forgot `--start`.

## Deploy lifecycle (optional)

The framework can generate a dashboard (HTML from tasks + plan +
workflows). Default mode: **generate locally, view locally**. Server
push is optional.

**Local mode** (default, no server setup needed):

```bash
# Generate the dashboard once
python3 $FRAMEWORK_DIR/scripts/generate-dashboard.py \
    --output $FRAMEWORK_DIR/_site/dashboard/index.html \
    --projects forge
xdg-open $FRAMEWORK_DIR/_site/dashboard/index.html
```

**Server mode** (optional, for multi-device / sharing): config in
`~/.config/forge/deploy.env` with `DEPLOY_REMOTE`,
`DEPLOY_REMOTE_PATH`, `DASHBOARD_PROJECTS`, `DASHBOARD_HOST_REPO`. Then:

```bash
bash $FRAMEWORK_DIR/scripts/deploy-docs.sh
```

The script sources deploy.env automatically (`deploy-dashboard-lite.sh`) or
expects the variables exported (`deploy-docs.sh` does not yet have an
auto-source block — drift note, ACTIONABLE spawn).

**OBLIGATIONS reminder:** pre-commit Check 3 WARNS when `docs/dashboard/`
or plan files have changed — *"Deploy via deploy-docs.sh required"*.
For pure local mode the WARN is ignorable. For server mode: deploy
before the next push.

**When server push is worth it:** multiple devices, sharing use case,
Hetzner / own-server setup. Otherwise local is enough.

## 5-phase model (producer class)

Producer-class workflows (`build`, `fix`, `review`, `solve`) follow the
5-phase model:

```
SPECIFY ─▶ PREPARE ─▶ EXECUTE ─▶ VERIFY ─▶ CLOSE
   │           │          │          │        │
 frame      delegation   MCA       boards   commit
 spec_board test-design  inline    L1/L2    +deploy
 council    artefact              convergence
```

`research` is a 5-phase producer with different phase names (Research-Plan →
Discover → Synthesize → Validate → Close). `docs-rewrite` is 7-phase
documentation. `save` is 3-group (Pre-Write, Content-Writes parallel,
Post-Write). `context_housekeeping` is 2-group.

## Workflow matrix

`framework/process-map.md` is the canonical routing table:

| I want to... | Workflow | Runbook |
|---|---|---|
| Tackle a problem with an open solution shape | `solve` | `workflows/runbooks/solve/WORKFLOW.md` |
| Decompose an objective into L0-L3 | `solve` (scoping mode) | `skills/scoping/SKILL.md` |
| Implement a feature/task | `build` | `workflows/runbooks/build/WORKFLOW.md` |
| Write / design a spec | `build` (Specify phase) | (same runbook) |
| Review spec(s) | `review` | `workflows/runbooks/review/WORKFLOW.md` |
| Fix a bug / handle an incident | `fix` | `workflows/runbooks/fix/WORKFLOW.md` |
| Research / spike | `research` | `workflows/runbooks/research/WORKFLOW.md` |
| Rewrite docs | `docs-rewrite` | `workflows/runbooks/docs-rewrite/WORKFLOW.md` |
| End the session | `save` | `workflows/runbooks/save/WORKFLOW.md` |

## Typical workflows

### A. Fix a bug — `fix`

**Trigger:** user reports an error, or a test failure in the verify
phase, or a sub-agent ESCALATED, or a monitoring alert.

**Path:**

```
Phase Specify
  → root_cause_fix Phase A (symptoms → hypotheses → root-cause drill)
  → Test plan (failing test reproducing the bug)
Phase Prepare
  → Fix plan, conditional
Phase Execute
  → main-code-agent inline (fix + test green)
  → root_cause_fix Phase B (implementation)
Phase Verify
  → code_review_board (L1) for effort S-M, L2 for larger diffs
  → retest green
Phase Close
  → Lessons learned (knowledge_processor mode=process)
  → task_status_update → done
  → Commit (pre-commit hook runs)
```

**Anti-pattern:** patching the symptom without root cause. `fix` forces a
drill in Phase A — if the hypothesis was wrong, that surfaces when writing the test.

### B. Implement a feature — `build`

**Trigger:** user defines feature/task. Spec approved and ready.

**Path determination** (`workflows/runbooks/build/WORKFLOW.md` §Path-Determination):

```
ALL three? (a) ≤3 files (b) no spec (c) no new behaviour → DIRECT
At least ONE? (a) >1 subsystem (b) new subsystem (c) new pattern
  (d) schema change (e) >10 ACs → FULL
Otherwise → STANDARD
```

**STANDARD path:**

```
Specify  → frame interview (8 sub-steps) → SPEC → spec_board → Test plan
Prepare  → testing(Design) + delegation artefact with board findings
Execute  → main-code-agent inline (Plan → Plan-Review → Implement → L0)
Verify   → code_review_board (L1/L2) → conditional spec_amendment_verification
Close    → task_status_update → done + commit guard + deploy
```

**FULL path:** spec is built up in 3 levels (E1 → Board → E2 → Board → E3 → Board Deep + DR).
Test design additive (L4/L5 after E1, L3 after E2, L2 after E3).

**DIRECT path:** inline delegation → MCA → L0 → return. No board, no
state file. The pre-commit hook stays (NON-NEGOTIABLE).

### C. Open-shaped problem — `solve`

**Trigger:** the problem is clear, but the solution shape (feature? spec?
code? process?) is not. Typical for meta-problems, structural questions,
methodology decisions.

**Path (full):**

```
Phase 1 — Frame
  frame skill (8 sub-steps): reformulate problem → first-principles drill →
  plan + review → repo check → constraints → SOTA research conditional →
  solution space (idea lenses, at least 3 approaches) → evaluate + recommend
Phase 2 — Refine
  user dialogue, council conditional when >1 path + irreversible
Phase 3 — Artifact
  Write artefact (runbook/skill/spec/ADR/plan)
Phase 4 — Validate
  Board appropriate to artefact type
Phase 5 — Execute
  state-file done + handoff to matching workflow or self-apply + commit
```

### D. Review a spec — `review`

**Trigger:** spec exists, needs to be checked for rebuild fitness.

**Routing** (`workflows/runbooks/review/WORKFLOW.md` §Review-Routing):

```
1 spec, standard size            → spec_board (Standard or Deep)
1 spec, >1000 lines, foundation  → sectional_deep_review
2+ specs, shared contracts       → architecture_coherence_review
UI spec after functional PASS    → spec_board (mode=ux)
```

`spec_board` modes:
- **Standard** (4 reviewers: Chief + Adversary + Implementer + Impact)
- **Deep Pass 1** (7 reviewers: + Adversary-2 + a Sonnet-instance Adversary + Consumer)
- **Deep Pass 2+** (4 reviewers)
- **Deep Final** (2 reviewers)
- **mode=ux** (UX board: ux-heuristic + ux-ia + ux-interaction)

Convergence: `convergence_loop` (max 3 passes), decreasing severity threshold.

### E. Research / spike — `research`

**Trigger:** knowledge gap, SOTA question, library evaluation.

**Modes:**
- **Standard** (synthesis is enough, 1 agent, web)
- **High** (evidence required, min 3 sources, adversary check)

When `research` is invoked as a sub-workflow from `solve` step 6 or
`build` step 9: no own state file, findings returned via
`knowledge_processor` into the parent state.

### F. End the session — `save`

**Trigger:** user says `save` or `quicksave`.

**Three groups** (group order is mandatory; group B in parallel):

```
A. Pre-Write (sequential)
   1. Dispatcher (Buddy inline: triage PENDING from session-buffer.md)
   2. Reconciliation (gap check + task status)
   3. Workflow state (workflow_engine --handoff-context)

B. Content writes (PARALLEL — one batch)
   4. Session handoff (merge default, never overwrite blindly)
   5. Session log (decision/error notes)
   6. Context updates (overview.md + history entries)

C. Post-Write
   7. Commit (pre-commit hooks run, incl. PERSIST-GATE)
```

`quicksave` is the same path with reduced depth.

## Patterns

### Pattern 1 — Plan block before non-trivial action

`skills/_protocols/plan-review.md` is mandatory mechanics. For
non-trivial actions (delegation, build, refactor):

```markdown
**Plan block**
- Scope: <what is touched, what is not>
- Tool/Agent: <which sub-agent, with which constraints>
- Alternatives: <at least 2 alternatives with reasoning why not>
- Expected artefacts: <what should come out>

**Self-review**
- Scope check: does scope cover user intent? Too narrow / too broad?
- Instance-vs-class: is this a concrete instance or a pattern?
- Rationalisation reflex: why is the rationalisation "it's small, it's quick" wrong here?
```

For genuinely non-trivial actions also use the `plan-adversary` persona
dispatch (inline-only, defined in `_protocols/plan-review.md`).

### Pattern 2 — Source-grounding discipline

Before `str_replace` on spec/code: **read if last read >5 turns old.**
Before consistency assertion across 2+ artefacts: **read both, mandatory.**
Summaries are heuristic, not ground truth.

Source: `agents/buddy/operational.md §Source-Grounding`.

### Pattern 3 — Board dispatch without Buddy bias

`skills/_protocols/dispatch-template.md` + `skills/_protocols/context-isolation.md`:

- Buddy writes NO own analysis into the board dispatch prompt.
- Board reviewers receive spec + brief; their own analysis is their job.
- After the board: Buddy reads ONLY `chief-signal.md`, no individual reviews.

Violation: board reviewers get colored by Buddy's hypothesis, the
multi-perspective guarantee is gone.

### Pattern 4 — Cross-loading via uses

In SKILL frontmatter:
```yaml
uses: [_protocols/plan-review, _protocols/dispatch-template, convergence_loop]
```

When the skill is invoked the referenced protocols are assembled inline.
Cross-loading replaces inline duplication.

### Pattern 5 — Idempotent generators

```bash
python3 scripts/generate_skill_map.py
python3 scripts/generate_navigation.py
git diff --name-only        # → empty if nothing drifted
```

If the second run produces a diff the first wasn't idempotent —
generator bug. The validator hook (`consistency_check` Check 6/8) catches that.

### Pattern 6 — Hook + handoff (session continuity)

`framework/agent-patterns.md §Pattern: Hook + Handoff`:

- **Hook (computed):** `plan_engine --boot` returns a machine-readable session state.
- **Handoff (narrative):** `session-handoff.md` contains a 9-point structure with
  user decisions, errors, open topics.

Both are written on `save`, loaded on `wakeup`.

### Pattern 7 — Persist gate on status change

On task status change (e.g. `pending` → `in_progress` or `→ done`):
- 2 writes: `overview.md` + `history/`
- Pre-commit Check 6 (PERSIST-GATE) catches a status change without a context update

## Anti-patterns

### A1 — Buddy reads board reviews

CLAUDE.md §1: *On board/council, do not read review files, do not analyse
findings, do not write consolidations, do not verify fixes. Only:
spawn → read chief signal → SAVE → escalate.*

When Buddy does read along: his interpretation colours the findings,
the multi-perspective guarantee is lost, and the board was for nothing.

### A2 — Sub-agent call without delegation artefact

CLAUDE.md §3 / AGENTS.md §4: *No agent call without a delegation artefact.*

When Buddy calls the `Agent` tool ad-hoc without plan block or gate file:
constraints get forgotten, the sub-agent does "something other than meant",
refactoring later.

### A3 — Skill inflation

New capability → "I need a new skill". Wrong — first check whether an
existing skill with a `modes` extension covers the use case. Two or more
existing skills with high process disjunction: check consolidation
(`framework/skill-anatomy.md §Consolidation Mechanics`).

### A4 — Modelling a workflow as a skill

Workflows are routing trees, skills are methodology. If a "skill" mostly
composes other skills without its own methodology: that is a workflow,
belongs in `workflows/runbooks/`.

### A5 — Bypassing the generator

Editing the `framework/skill-map.md` AUTO block or `navigation.md`
manually leads to drift on the next generator run. **Edit only the sections
outside the AUTO markers.** For the AUTO block: source is disk
(SKILL frontmatter), index follows.

### A6 — Patching the symptom without root cause

`fix` workflow Phase A is not optional. Even for a "small bug" — if the
root-cause hypothesis was wrong, the bug comes back.

### A7 — Skipping the persist gate after status change

`task_status_update` sets the YAML status. Without the `overview.md` patch
and the `history` entry the status change is half. Pre-commit Check 6 warns
but does not block — discipline-discipline.

## Best practices

### BP1 — Frame before plan

For substantial problems: do `frame` (8-step analysis) first before writing
a plan. Step 1 (reformulate problem) plus Step 2 (first-principles drill)
plus Step 7 (solution space with idea lenses) prevents solution anchoring.

### BP2 — Standard skill frontmatter

Frontmatter with `name`, `description` (with "Use when"), `status`,
`invocation.primary`. 7 mandatory sections. `Standalone` block on
newly created skills.

### BP3 — Hooks symbolic, not copied inline

The pre-commit hook lives in every consumer repo via symlink, not via
copy. On hook update the consumer is automatically in sync.

### BP4 — Respect frozen zones

Never write actively into `context/history/**`. `frozen-zone-guard.sh`
blocks mechanically, but discipline shouldn't even attempt it.

### BP5 — Stale cleanup in the same commit

When a skill/workflow is archived: clean up all active refs in the same
commit. `grep -rn old_skill` + frozen-zone filter + fix the rest.
Pre-commit Check 5 warns; discipline closes the gap.

### BP6 — Mode discipline

Skills with `modes:` have **one axis** (depth / topic / phase / level / scope).
Mixing is forbidden. Hard convention: max 3 modes (exception: phase axis).

### BP7 — Check token budget up front

Before SKILL.md / WORKFLOW.md / persona edit: check the budget from
`skills/_protocols/piebald-budget.md`. On imminent overrun: extract to
REFERENCE.md or consolidate a mode.

## Who reads what?

### Human readers

- Read [`01-overview.md`](01-overview.md) and [`10-human-guide.md`](10-human-guide.md).
- Look at the diagrams in [`02-architecture.md`](02-architecture.md).
- Setup via [`05-installation.md`](05-installation.md).
- For trouble: [`12-troubleshooting.md`](12-troubleshooting.md).

### Coding agents

- Tier 0 (`CLAUDE.md` / `AGENTS.md`) is mandatory at boot.
- Tier 1 (`agents/buddy/`, `framework/`) on-load after boot.
- [`09-agent-guide.md`](09-agent-guide.md) has do/don't and invariants compactly.

### Maintainers

- Engine details + generator care in [`08-development-and-maintenance.md`](08-development-and-maintenance.md).
- Skill anatomy in [`04-core-concepts.md`](04-core-concepts.md) §Single-Class and
  [`../framework/skill-anatomy.md`](../framework/skill-anatomy.md).

## Next step

What this looks like concretely under Claude Code / OpenCode:
[`07-tool-integrations.md`](07-tool-integrations.md).
