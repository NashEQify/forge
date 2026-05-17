# docs/ folder taxonomy

Rule doc for the `docs/` hierarchy. SoT for "where does
what go".

## Repo topology (read first)

Two repos, one-way sync. **`forge_dev`** = private dev SoT (this
table describes its `docs/`). **`forge`** = public OSS mirror,
produced solely by `scripts/release-sync.sh`. The sync's exclude
list is the enforcement mechanism for "no internal operational
state in public" — it is not advisory.

What the **public mirror** carries from `docs/`: framework content
only (`docs/STRUCTURE.md`, `docs/decisions/`, `docs/architecture/`),
plus `docs/tasks/.gitkeep` and a hand-maintained `docs/plan.yaml`
**north_star stub** (no live milestones/tasks). Everything else
below is forge_dev-only — excluded by the sync.

## Tracked (in forge_dev — the dev SoT)

| Path | Purpose | Content | Public mirror |
|------|---------|---------|---------------|
| `docs/plan.yaml` | Programme SoT | north_star, operational_intent, phases, milestones | north_star **stub** only |
| `docs/STRUCTURE.md` | This file | Folder-taxonomy rule | yes (framework content) |
| `docs/tasks/<NNN>.{md,yaml}` | Active tasks | Task spec + YAML metadata | no — excluded |
| `docs/tasks/archive/<NNN>.{md,yaml}` | Done tasks | Auto-moved by `task_status_update` step 5. WORM (frozen zone). | no — excluded |
| `docs/tasks/.gitkeep` | Convention marker | keeps the dir + convention visible | yes |
| `docs/decisions/ADR-<NNN>.md` | ADRs | Architecture decision records — status, context, decision, alternatives, consequences | yes (framework content) |
| `docs/architecture/` | Architecture notes | Hand-written architecture reflections (e.g. `build-workflow-structural-gap.md`) | yes (framework content) |

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

- **Minimal-tracked:** the public OSS mirror shows
  framework content, not internal operational state.
  This is enforced, not aspirational: the exclude list
  in `scripts/release-sync.sh` is the mechanism
  (`context/`, `docs/tasks/*.{yaml,md}`,
  `docs/tasks/archive/`, `docs/plan.yaml`). Public
  keeps only `docs/tasks/.gitkeep` + a `docs/plan.yaml`
  north_star stub. Topology: `CLAUDE.md` Invariant 8.
- **Auto-discoverable:** `docs/STRUCTURE.md` is the only
  lookup for "where does what go".
- **Drift-robust:** consistency_check check 9 catches
  new drift paths on the next structural commit.
