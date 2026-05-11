# Workflow: docs-rewrite

Rewrite architecture documentation from scratch.
Reader-journey-first: structure follows the audience, not
the system.

## Trigger

- Framework refactoring that makes existing docs stale.
- New audience or changed information goal.
- User imperative ("docs rewrite").

## Input

| Parameter | Required | Description |
|-----------|----------|-------------|
| scope | yes | What is rewritten (e.g. "Framework site /dev/") |
| reason | yes | Why stale (e.g. "Task 273 fundamentally reworked the framework") |
| content_goal | yes | What the docs should convey (e.g. "Workflows, architectures, design decisions — no file listings") |
| personas | no | Path to persona definitions. Default: derive from existing docs / task. |
| existing_docs | no | Path to existing pages being rewritten |

---

### Phase: Research
- **Agent:** CC subagent_type `Explore`
  (thoroughness: very thorough). Not a framework agent —
  native CC mechanism for repo exploration. No prompt
  assembly, no persona file.
- **Input:** repo access + focus instructions from
  content_goal.
- **Output:** research document (~1500–2500 words):
  design decisions, workflows, architecture principles,
  technology stack, key interconnections — extracted
  from source files, not paraphrased.
- **Gate:** Buddy checks the research against a
  content_goal checklist: every item from content_goal
  must be covered by at least one substantiated
  statement. Missing items → follow-up.
- **Failure:** gaps → Buddy adds specific follow-up
  reads (max 2).
- **Autonomy:** agent-autonomous (reads what it needs).

Entry points (Buddy fills these in before dispatch from
context):
- Always: intent.md (vision), CLAUDE.md (invariants),
  process-map.md (workflows).
- Framework rewrite: 273.md (design decisions),
  agentic-design-principles.md, workflow runbooks.
- Product rewrite: ARCHITECTURE.md, specs, container
  atlas.
- Buddy derives entry points from scope + reason. No
  heuristic — from known context.

**Prompt core for the research agent:** see
`prompts.md` §research-agent prompt.

---

### Phase: Structure
- **Agent:** Buddy direct (orchestrator work: docs/ is
  Buddy scope).
- **Input:** research document + personas + existing
  pages (to understand what was there).
- **Output:** page plan — for each page: title, file
  name, core question it answers, 3–5 content points
  (from research), estimated length, dependencies on
  other pages.
- **Gate:** every persona finds its entry. Every
  research point is mapped to a page. No research point
  orphaned. Gate check: mapping table (research point →
  page) without gaps.
- **Failure:** gap in the mapping → research follow-up
  or add a page.
- **Autonomy:** Buddy decides; the user can intervene.

Page-plan logic:
1. Define reader journeys (1 per persona).
2. Per journey: which pages in which order.
3. Pages that appear in multiple journeys = core pages
   (written first).
4. Distribute research points across pages — each point
   exactly once.
5. Index page: entry points per journey (like the
   existing index.md).
6. How-to pages: derive from the page plan (operational
   guides as their own category).
7. Stale-cleanup plan: list of existing pages to be
   removed / replaced.

---

### Phase: Write
- **Agent:** CC subagent_type `general-purpose` (1
  spawn per page, parallel where possible). NOT MCA —
  doc pages aren't code; MCA expects delegation
  artifacts (intent_chain, spec, test plan) that don't
  exist here.
- **Input:** per agent: page-plan entry + relevant
  research excerpt + persona context + writing
  guidelines + neighbour-page titles (for boundary).
- **Output:** finished markdown page as a file in
  `docs/architecture/framework/`.
- **Gate:** the page answers its core question. Length
  in the estimated range. No file listings as a goal in
  themselves.
- **Failure:** page misses the core question → Buddy
  gives specific feedback, new agent spawn (max 2).
- **Autonomy:** agent writes autonomously within the
  page-plan scope.

**Prompt core for the writer agent:** see `prompts.md`
§writer-agent prompt.

Parallelisation: pages without dependencies spawn in
parallel. Pages WITH a dependency are sequential.

---

### Phase: Coherence
- **Agent:** Buddy direct.
- **Input:** all written pages.
- **Output:** coherence report + fixes.
- **Gate:** uniform terms, consistent tone, no
  redundancies, no gaps between pages.
- **Failure:** inconsistencies → Buddy fixes directly
  (autonomy SoT: `framework/agent-autonomy.md`,
  docs-rewrite runbook mechanic is the Buddy zone).
- **Autonomy:** mechanical.

Check points:
1. Glossary consistency: same terms for same concepts
   (scan all pages).
2. Transitions: page A references page B → does the
   context exist there?
3. Redundancy: same information on 2+ pages → keep on
   one, link from the others.
4. Tone: technical-explanatory, not marketing, not a
   reference manual.

---

### Phase: Assemble
- **Agent:** Buddy direct.
- **Input:** all written pages + page plan +
  stale-cleanup plan.
- **Output:** index.md (updated), mkdocs-framework.yml
  nav (updated), cross-links, old pages removed /
  replaced.
- **Gate:** all pages in nav. `mkdocs build --strict`
  PASS. Each journey has an entry on index.md.
  Stale-cleanup complete (invariant 6).
- **Failure:** build error or missing links → fill in.
  Mechanical.
- **Autonomy:** mechanical.

Stale cleanup (invariant 6):
1. Old pages marked "replaced" in the page plan →
   remove.
2. mkdocs-framework.yml nav → remove old entries.
3. Cross-links in other files pointing to removed pages
   → update.
4. `grep -rn` on removed file names in docs/ and
   framework/ → clean up.

---

### Phase: Review
- **Agent:** spec_board (mode=ux, quick mode, 3 UX
  personas: board-ux-heuristic, board-ux-ia,
  board-ux-interaction).
- **Input:** page plan + 2–3 core pages + index.md.
  Context in the dispatch: "This is framework
  documentation (markdown / mkdocs), not a UI spec.
  Check navigability, comprehensibility, information
  architecture for the defined personas."
- **Output:** UX findings (navigation,
  comprehensibility, information architecture).
- **Gate:** 0 critical + 0 high.
- **Failure:** findings → Buddy fixes the affected
  pages (targeted, not everything) → optionally
  re-review.
- **Autonomy:** agents autonomous. Fixes: Buddy direct
  (autonomy SoT: `framework/agent-autonomy.md`).
- **Protocols:** context-isolation.

---

### Phase: Close
- **Agent:** Buddy direct.
- **Input:** all pages, review result.
- **Output:** deployed site.
- **Gate:** `mkdocs build --strict` PASS + deploy +
  visual check (or user request).
- **Failure:** build error → fix. Deploy error → fix.
  Mechanical.

Steps:
1. TASK-UPDATE — task_status_update if a task exists
   (BEFORE commit, so the YAML lands in the commit).
2. BUILD-TEST —
   `mkdocs build --strict -f mkdocs-framework.yml`
   locally.
3. COMMIT-GUARD — OBLIGATIONS, PERSIST, TASK-SYNC,
   PLAN-VALIDATE, FACTS.
4. COMMIT — `git commit + push`.
5. DEPLOY — `$FRAMEWORK_DIR/scripts/deploy-docs.sh`.
6. VERIFY — ask the user to check visually (Buddy has
   no browser).

---

## Iteration bounds

| Phase | Max | On overshoot |
|-------|-----|--------------|
| Research | 2 follow-ups | Buddy closes with the available material |
| Write (per page) | 2 rewrites | Buddy writes the page directly (autonomy SoT: `framework/agent-autonomy.md`) or user escalation |
| Review (UX Board) | 1 re-review | User decides on further iteration |

## References

| Step | Detail SoT |
|------|-----------|
| Research | CC subagent_type: Explore (native CC mechanism) |
| Write | CC subagent_type: general-purpose (no MCA) |
| Coherence | Buddy direct (autonomy SoT: `framework/agent-autonomy.md`) |
| UX review (mode=ux) | skills/spec_board/SKILL.md |
| Deploy | $FRAMEWORK_DIR/scripts/deploy-docs.sh |
| Personas | docs/specs/dashboard/dashboard-persona.md (reference format) |
