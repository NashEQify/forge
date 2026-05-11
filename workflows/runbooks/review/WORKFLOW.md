# Workflow: review

Review or validate spec(s). No code — only spec quality.

## Trigger

- User requests a spec review.
- Milestone gate check (every spec in the milestone must be reviewed).
- Post-change trigger (spec changed, re-review needed).
- Build workflow specify phase delegates a board review.

## NOT for

- Code review after implementation → verify phase in **build** or **fix**.
- Architecture decisions → **solve** (with council).
- Investigation / root cause → **fix** or **solve**.
- Implementation → **build**.

## Review routing

```
1 spec, standard size                    → spec_board (standard or deep)
1 spec, >1000 lines, foundation          → sectional_deep_review
2+ specs, shared contracts               → architecture_coherence_review
UI spec after a functional PASS          → spec_board (mode=ux)
```

## Named gates

The review workflow has **5 named gates**. Phase-status transitions
are engine-internal. Depth scales over the routing decision (above),
not over workflow variants.

| # | Gate | Skill | Conditional |
|---|------|-------|-------------|
| 1 | routing | classification | route: standard / sectional / architecture |
| 2 | board-dispatch | `spec_board/SKILL.md` (or sectional / architecture per route) | chief consolidates findings; Buddy reads only chief signal |
| 3 | convergence-loop | `convergence_loop/SKILL.md` | only on NEEDS-WORK; max 3 passes |
| 4 | close-bookkeeping | `task_creation/SKILL.md` | risk follow-up: only when verdict has non-empty `remaining_findings:` |
| 5 | commit | git pre-commit hooks | — |

## State file

`docs/review/YYYY-MM-DD-<slug>.md` per review run. Commit per phase.

**Proportionality:**
- **With task ref:** mandatory, full state file.
- **Without task ref (ad-hoc / milestone gate check):** state file
  optional; the engine tracks workflow_phase regardless.

Frontmatter, body content per phase, drift notes: `REFERENCE.md`.

## Detail per gate

**1. routing** — pick the review skill based on the spec set (table
above). Pick mid-flow via `--complete routing --route <key>`.

**2. board-dispatch** — dispatch the routed skill. Output paths:
- spec_board               → `docs/reviews/board/{spec_name}-consolidated-pass1.md`
- sectional_deep_review    → `docs/reviews/sectional/{spec_name}-deep.md`
- architecture_coherence_review → `docs/reviews/architecture/{spec_name}-coherence.md`

Chief consolidates findings into the verdict file. Buddy reads ONLY
the chief signal (CLAUDE.md §1).

**3. convergence-loop** — on NEEDS-WORK: fix-loop via `convergence_loop`,
max 3 passes, rising severity threshold. PASS at 0C+0H. Skip-eligible
when the first pass was already PASS.

**4. close-bookkeeping** — for every verdict file written this run,
check the top-level YAML block `remaining_findings:`. Non-empty →
file ONE follow-up task via `task_creation`. No remaining findings:
skip with one-line rationale.

**5. commit** — `git commit + push`. Updates `board_result` and
`readiness` in the task YAML.

## References

| Topic | Detail SoT |
|-------|------------|
| Spec board | `skills/spec_board/SKILL.md` |
| Sectional deep review | `skills/sectional_deep_review/SKILL.md` |
| Architecture coherence | `skills/architecture_coherence_review/SKILL.md` |
| Convergence loop | `skills/convergence_loop/SKILL.md` |
| Workflow engine CLI | `framework/workflow-engine-cookbook.md` |
