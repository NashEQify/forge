# Shipping and launch — pre-launch checklist

Step-loaded unit of `skills/shipping_and_launch/SKILL.md`. Read it before a production deploy starts, to tick the six
required categories. Phases 1.5 (deploy-discipline invariants) and 6 (rollback plan) are in `SKILL.md`, phases 2–5
in `rollout.md`.

### Phase 1: pre-launch checklist (MUST before deploy)

Six required categories. Every box ticked before deploy
starts.

#### Code quality
- [ ] Tests per `skills/testing/run-strategy.md` §Test selection
  (L0 ruff / mypy + the broad run: a production launch touches live
  infrastructure, a safety floor).
- [ ] Build successful, no warnings.
- [ ] Code Review Board PASS (L1 or L2 by stage choice).
- [ ] No TODO comments that should be resolved before
  launch.
- [ ] No `print()` / `console.log()` debug statements in
  production code.
- [ ] Error handling covers expected failure modes.

#### Security (cross-ref `agents/security.md` + `agents/code-security.md`)
- [ ] No secrets in the code or repo
  (`grep -ri "secret\|api_key\|password"` pre-commit).
- [ ] `pip-audit` shows no critical / high vulnerabilities.
- [ ] Input validation on every user endpoint (Pydantic
  `extra="forbid"`).
- [ ] Auth + authorization on every state-changing
  endpoint.
- [ ] Security headers configured (CSP, HSTS,
  X-Frame-Options).
- [ ] Rate limiting on auth endpoints.
- [ ] CORS specifically configured (no wildcard `*`).
- [ ] Auth check on every protected endpoint (mesh auth /
  cookie / token, per project).

#### Performance (cross-ref `code-review` performance axis)
- [ ] Hot paths: no N+1 queries (cross-check asyncpg
  logging).
- [ ] DB indexes for common query patterns.
- [ ] Token budget for LLM calls respected.
- [ ] Connection-pool config (pool size, acquire timeout).
- [ ] **Frontend (when relevant):** Core Web Vitals within
  "good" thresholds (LCP <2.5s, INP <200ms, CLS <0.1).

#### Accessibility (cross-ref `skills/spec_board/` mode=ux when UI)
- [ ] Keyboard navigation for every interactive element.
- [ ] Screen-reader compatibility.
- [ ] Color contrast WCAG 2.1 AA (4.5:1 for text).
- [ ] Focus management on modals + dynamic content.
- [ ] Error messages descriptive and associated with the
  form field.
- [ ] No A11y warnings in axe-core / Lighthouse.

#### Infrastructure
- [ ] Environment variables set in production
  (`.env.production` or equivalent).
- [ ] **DB-touching deploy:** `pg_dump` run as the FIRST
  command (see phase 1.5 in `SKILL.md` — INVARIANT).
- [ ] **Container recreate:** mount sources verified
  (`docker inspect`) BEFORE `docker compose up -d` (see
  phase 1.5 in `SKILL.md` — INVARIANT).
- [ ] DNS + SSL configured for changed endpoints.
- [ ] Logging + error reporting configured (structured logs
  to a known sink).
- [ ] Health-check endpoint exists + answers 200.
- [ ] All target hosts (production + edge) reachable from
  the deploy host.

#### Documentation
- [ ] README + setup guide updated.
- [ ] API documentation current (FastAPI auto-generated
  OpenAPI).
- [ ] ADRs for architecture decisions (cross-ref
  `documentation_and_adrs`).
- [ ] Changelog updated.
- [ ] User-facing docs updated (when relevant).
