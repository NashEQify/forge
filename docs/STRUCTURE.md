# docs/ folder taxonomy

Rule doc for the `docs/` hierarchy. SoT for "where does
what go".

## Tracked (in the OSS repo)

| Path | Purpose | Content |
|------|---------|---------|
| `docs/plan.yaml` | Programme SoT | north_star, operational_intent, phases, milestones |
| `docs/STRUCTURE.md` | This file | Folder-taxonomy rule |
| `docs/tasks/<NNN>.{md,yaml}` | Active tasks | Task spec + YAML metadata |
| `docs/tasks/archive/<NNN>.{md,yaml}` | Done tasks | Auto-moved by `task_status_update` step 5. WORM (frozen zone). |
| `docs/decisions/ADR-<NNN>.md` | ADRs | Architecture decision records — status, context, decision, alternatives, consequences |
| `docs/architecture/` | Architecture notes | Hand-written architecture reflections (e.g. `build-workflow-structural-gap.md`) |

## Gitignored (local-only, no OSS trace)

| Path | Purpose |
|------|---------|
| `docs/build/` | Build workflow state files (`YYYY-MM-DD-task-NNN-slug.md`) |
| `docs/solve/` | Solve workflow state files |
| `docs/fix/` | Fix workflow state files |
| `docs/review/` | Review workflow state files (singular per workflow convention) |
| `docs/research/` | Research workflow state files |
| `docs/audit/` | Audit workflow state files (singular per workflow convention) |
| `docs/audit/handovers/` | Audit dogfooding docs as a sub-folder |
| `docs/docs-rewrite/` | Docs-rewrite workflow state files |
| `docs/reviews/` | Review-persona output (sub-folders `board/` + `council/`) — cross-workflow, hence plural |
| `docs/specs/` | Intermediate spec drafts (edit plans, transient specs from solve / build) |
| `docs/handovers/` | Cross-repo handover bundles, dogfooding reports |
| `docs/discoveries/` | Cross-repo discovery logs |
| `docs/tasks/<NNN>-{gates,delegation,test-plan}.*` | Per-task audit trail files |

## Drift aliases (DO NOT use)

The following paths exist historically in some skill /
workflow texts but are drift and should be removed
progressively:

- `docs/spec/` (singular) → canonical `docs/specs/`
  (plural, gitignored).
- `docs/plan/` / `docs/plans/` → canonical
  `docs/plan.yaml` (file, not directory).
- `docs/adr/` → canonical `docs/decisions/`.
- `docs/audits/` (plural) → canonical `docs/audit/`
  (singular).

Note: `docs/review/` (singular) is NOT a drift alias —
it is the canonical review-workflow state-file path form
(analogous to `docs/build/`, `docs/solve/`, etc.).
`docs/reviews/` (plural) is semantically separate
(board / council output, cross-workflow).

`consistency_check` check 9 (folder-taxonomy drift)
warns on new paths outside this table.

## Override for consumer repos

Consumers (BuddyAI, Huddle, personal, infra) may have
their own `docs/STRUCTURE.md` extending or adapting this
convention. Skills that write (e.g.
`documentation_and_adrs` ADR path override) respect a
project-local `STRUCTURE.md` with higher priority than
the framework default.

## Rationale

- **Minimal-tracked:** the OSS repo shows framework
  content, not internal operational state.
- **Auto-discoverable:** `docs/STRUCTURE.md` is the only
  lookup for "where does what go".
- **Drift-robust:** consistency_check check 9 catches
  new drift paths on the next structural commit.
