# Workflow: research

Research, evaluate, spike. Result: knowledge, not code.

## Trigger

- User asks for SOTA, alternatives, patterns.
- Build workflow `interview` step (research after a board pass) — as
  a sub-workflow.
- Spike before an architecture decision.
- Tool / library evaluation.

## NOT for

Architecture decision → **solve**. Implementation → **build**.
Bug → **fix**. Spec validation → **review**.

## Path determination

Quality level set in `scope` step:
- **Standard** — synthesis suffices, 1 agent, web research.
- **High** — evidence required, ≥3 sources, adversary check.

## Named gates

The research workflow has **5 named gates**. Phase-status transitions
are engine-internal.

| # | Gate | Skill | Conditional |
|---|------|-------|-------------|
| 1 | scope | classification | route: standard / high |
| 2 | research | `get_api_docs/SKILL.md` + WebSearch / WebFetch | — |
| 3 | synthesis | — (Buddy or general-purpose agent) | High mode adds adversary check |
| 4 | knowledge-capture | `knowledge_capture/SKILL.md` | each of (persist, context-gap-check, impact) skip-eligible with one-line rationale |
| 5 | commit | git pre-commit hooks | — |

## State tracking

State file `docs/research/YYYY-MM-DD-slug.md` only on a standalone task.
Sub-workflow persists into the parent state file.

Frontmatter:
`workflow: research | problem: "1 line" | started | phase | status | task_ref | artefacts: []`.

## Detail per gate

**1. scope** — read existing research artefacts under
`<active-context>/research/sota-*.md` and `docs/research/` (max ~5
files, judgment-based — more loads cognitive cost without information
gain). Decide quality level: standard or high. Pick mid-flow via
`--complete scope --route <key>`.

**2. research** — web research per quality level. WebSearch, WebFetch,
`get_api_docs` for library docs.

**3. synthesis** — consensus + matrix + position. On high quality:
adversary check via `board-adversary` on weaknesses of the research.

**4. knowledge-capture** — three skip-eligible sub-checks:
(a) persist findings via `knowledge_capture` (SOTA maps to
`<active-context>/research/` or `docs/research/`);
(b) context-gap check — do findings close documented gaps? If yes,
update context files;
(c) impact — does the research affect open tasks / specs? If yes, add
to session-buffer PENDING.

**5. commit** — `git commit + push`. Sub-workflow: COMMIT must come
before HANDOFF — on a crash between these steps the parent would
otherwise consume non-persisted results.

## Iteration bounds

| Phase | Max | On overshoot |
|-------|-----|--------------|
| scope | 2 sharpening rounds | user decides scope or aborts |
| research | 3 iterations | accept + document gaps |
| synthesis | 2 quality rounds | accept Standard, document caveats |

## Cross-workflow handoffs

| Parent | Sub / target | Trigger |
|--------|--------------|---------|
| build | research (sub-workflow) | deeper research needed during interview |
| solve | research (sub-workflow) | frame phase: SOTA trigger |
| research | solve / build | architecture question → solve, impl-ready → build |

## References

| Topic | Detail SoT |
|-------|------------|
| WebSearch / WebFetch | built-in tools |
| Knowledge capture | `skills/knowledge_capture/SKILL.md` |
| Knowledge processor | `skills/knowledge_processor/SKILL.md` |
| Task status update | `skills/task_status_update/SKILL.md` |
| Workflow engine CLI | `framework/workflow-engine-cookbook.md` |
