---
name: shipping-and-launch
description: >
  Production-launch discipline with pre-launch checklist +
  feature-flag strategy + staged rollout + rollback plan +
  monitoring. Use when deploying to production, preparing a
  release, migrating data / infra, opening beta, or any
  deployment that carries risk.
status: active
invocation:
  primary: user-facing
  secondary: [workflow-step]
  trigger_patterns:
    - "deploy to production"
    - "ship to prod"
    - "production launch"
    - "rollout"
    - "release"
disable-model-invocation: false
---

# Skill: shipping-and-launch

## Purpose

Production-launch discipline. The goal is not just deploying —
it's **deploying safely** with active monitoring, a tested
rollback plan, and a clear definition of success. Every launch
should be reversible, observable, and incremental.

Absorbs the `[INVARIANT]` from
`~/projects/personal/context/user/profile.md` §Deploy-Discipline
(pg_dump pre-DB-deploy + mount-verify pre-recreate) as formal
skill obligations, not just a user convention.

## Source

Lifted from `github.com/addyosmani/agent-skills`
(`skills/shipping-and-launch/SKILL.md`, 2026-04-30).
**Adapted** to the forge reality:
- npm audit → pip-audit + ruff (Python stack).
- Core Web Vitals → relevant for the React frontend, not
  backend-only.
- Production / edge / mesh-topology reality.
- DEPLOY-DISCIPLINE-INVARIANT absorbed as the ops
  companion.

## Standalone

Distinct from:
- `skills/code_review_board/` — code-quality review before
  deploy, not deploy discipline. shipping-and-launch is the
  post-code-review gate.
- `skills/testing/` — test methodology, not production
  rollout.
- `workflows/runbooks/save/WORKFLOW.md` step 10 (dashboard
  deploy in background) — minimal docs deploy.
  shipping-and-launch is a production-service deploy with
  risk management.

What only this skill delivers:
- Pre-launch checklist (6 categories) as a required gate.
- Feature-flag lifecycle discipline (owner + expiration +
  2-week cleanup).
- Staged-rollout sequence with a threshold table (advance /
  hold / rollback).
- Rollback-plan obligation **before deploy** (not ad-hoc
  post-incident).
- Post-launch verification in the first hour.
- BuddyAI-specific deploy discipline (pg_dump obligation,
  mount verify).

## When to call

- Before the first production deploy of a feature.
- On every significant release for users.
- On data or infrastructure migration.
- On beta or early-access opening.
- On every deploy that carries risk (every deploy).

### Do not call for

- Docs-only deploy via `deploy-docs.sh` — minimal risk; the
  save workflow step 10 is enough.
- Internal-tooling updates without user impact — use
  code_review_board L1.
- Pure bug fixes with clear reproduction — fix workflow + L1
  review is enough (except: a fix that touches the DB →
  deploy discipline active).

## Process

### Phase 1: pre-launch checklist (MUST before deploy)

Six required categories. Every box ticked before deploy
starts.

#### Code quality
- [ ] All tests run (L0 ruff / mypy + test suite).
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
- [ ] Tailscale auth (`resolve_user`) on every protected
  endpoint.

#### Performance (cross-ref `code-review` performance axis)
- [ ] Hot paths: no N+1 queries (cross-check asyncpg
  logging).
- [ ] DB indexes for common query patterns.
- [ ] Token budget for LLM calls respected.
- [ ] Connection-pool config (asyncpg pool_size,
  acquire_timeout).
- [ ] **Frontend (React Huddle / Dashboard, when
  relevant):** Core Web Vitals within "good" thresholds
  (LCP <2.5s, INP <200ms, CLS <0.1).

#### Accessibility (cross-ref `skills/spec_board/` mode=ux when UI)
- [ ] Keyboard navigation for every interactive element.
- [ ] Screen-reader compatibility.
- [ ] Color contrast WCAG 2.1 AA (4.5:1 for text).
- [ ] Focus management on modals + dynamic content.
- [ ] Error messages descriptive and associated with the
  form field.
- [ ] No A11y warnings in axe-core / Lighthouse.

#### Infrastructure (BuddyAI-specific)
- [ ] Environment variables set in production
  (.env.production).
- [ ] **DB-touching deploy:** `pg_dump` run as the FIRST
  command (see phase 1.5 below — INVARIANT).
- [ ] **Container recreate:** mount sources verified
  (`docker inspect`) BEFORE `docker compose up -d` (see
  phase 1.5 below — INVARIANT).
- [ ] DNS + SSL configured for changed endpoints.
- [ ] Logging + error reporting configured (structlog →
  where?).
- [ ] Health-check endpoint exists + answers 200.
- [ ] Tailscale mesh: production host (Hetzner) + edge
  (Odroid / local) reachable.

#### Documentation
- [ ] README + setup guide updated.
- [ ] API documentation current (FastAPI auto-generated
  OpenAPI).
- [ ] ADRs for architecture decisions (cross-ref
  `documentation_and_adrs`).
- [ ] Changelog updated.
- [ ] User-facing docs updated (when relevant).

### Phase 1.5: DEPLOY-DISCIPLINE-INVARIANT (BuddyAI, NON-NEGOTIABLE)

Absorbed from
`~/projects/personal/context/user/profile.md` §Deploy-Discipline.
These two INVARIANTS are **mechanical obligations** before
every production deploy that touches the DB or recreates
containers:

#### INVARIANT-1: pg_dump pre-DB-deploy

> On EVERY DB-touching deploy: `pg_dump` as the FIRST command
> before the recreate. No exception, even on "trivial
> migrations" (CHECK constraint add, column rename, etc).

**Required command format:**

```bash
docker compose exec -T <service-name>-db pg_dump -U <user> <dbname> | \
  gzip > ~/backups/<service-name>-pre-deploy-$(date +%Y%m%d-%H%M).sql.gz
```

**Rationale** (lessons learned 2026-04-19, Juliane DB total
loss on deploy v2.6.5→v2.7): 30s pg_dump versus hours of
recovery via re-ingest (when an external source exists) or
total data loss (when not). Lost data is not reproducible.

**When to skip:** **never.** Not even on a nominal
"read-only change". DB touch is DB touch.

#### INVARIANT-2: mount-verify pre-container-recreate

> On a docker-compose recreate after a location / machine
> change: verify the mount sources BEFORE `up -d`.

**Required steps:**
1. `docker inspect <container>` on the running container —
   which bind mounts, which volumes?
2. Check whether `--env-file` or other flags are needed for
   the same mount state.
3. Only then `up -d`.

**Rationale:** implicit defaults ("compose reads .env
automatically") don't apply to `.env.production` — it has to
be passed explicitly, otherwise a different mount appears.

### Phase 2: feature-flag strategy (where applicable)

Decouple deployment from release via feature flags:

```python
# Pseudocode
flags = await get_feature_flags(user_id)
if flags.task_sharing:
    return TaskSharingPanel(task=task)
return None  # default: existing behavior
```

**Feature-flag lifecycle:**
1. **DEPLOY** with the flag OFF — code in production but
   inactive.
2. **ENABLE** for the team / beta — internal testing in
   production.
3. **GRADUAL ROLLOUT** — 5% → 25% → 50% → 100% of users.
4. **MONITOR** at every stage — error rates, performance,
   user feedback.
5. **CLEAN UP** — remove the flag + the dead code path
   after full rollout (max 2 weeks).

**Flag discipline:**
- Every feature flag has an owner + expiration date.
- Cleanup within 2 weeks of full rollout.
- No nested flags (exponential combination explosion).
- Both flag states (on + off) tested in CI.

### Phase 3: staged rollout

#### Rollout sequence

```
1. DEPLOY to staging
   └── Full test suite in the staging environment
   └── Manual smoke test of the critical flows

2. DEPLOY to production (feature flag OFF)
   └── Deploy verification (health-check 200)
   └── Error-monitoring check (no new errors)

3. ENABLE for the team (flag ON for internal users)
   └── Team uses the feature in production
   └── 24h monitoring window

4. CANARY (flag ON for 5% of users)
   └── Monitor error rates / latency / user behaviour
   └── Compare: canary vs baseline
   └── 24-48h window
   └── Advance ONLY if every threshold holds

5. GRADUAL (25% → 50% → 100%)
   └── Monitor at every stage
   └── Rollback capability to the previous percentage stage at any time

6. FULL rollout (flag ON for all)
   └── Monitor for 1 week
   └── Feature-flag cleanup
```

#### Rollout decision thresholds

| Metric | Advance (green) | Hold + investigate (yellow) | Rollback (red) |
|---|---|---|---|
| Error rate | <10% above baseline | 10-100% above baseline | >2x baseline |
| P95 latency | <20% above baseline | 20-50% above baseline | >50% above baseline |
| Client errors (frontend) | No new error types | <0.1% sessions | >0.1% sessions |
| Business metrics | Neutral or positive | Decline <5% | Decline >5% |

#### Immediate-rollback triggers

- Error rate >2x baseline.
- P95 latency >50% above baseline.
- User-report spike.
- Data-integrity issue detected.
- Security vulnerability discovered.

### Phase 4: monitoring + observability

#### What to monitor

```
Application:
├── Error rate (total + per endpoint)
├── Response time (p50, p95, p99)
├── Request volume
├── Active users
└── Business metrics (conversion, engagement)

Infrastructure:
├── CPU + memory
├── DB connection-pool usage (asyncpg pool exhaustion)
├── Disk space (Hetzner)
├── Network latency
└── Queue depth (NATS JetStream)

Client (when frontend):
├── Core Web Vitals (LCP, INP, CLS)
├── JS errors
├── API error rates from the client perspective
└── Page-load time
```

#### Error-reporting pattern (Python / asyncpg / FastAPI)

```python
# Server-side error reporting (FastAPI middleware)
@app.middleware("http")
async def error_middleware(request: Request, call_next):
    try:
        return await call_next(request)
    except Exception as exc:
        # Report via structlog
        logger.error(
            "request_error",
            method=request.method,
            url=str(request.url),
            user_id=getattr(request.state, "user_id", None),
            error_type=type(exc).__name__,
            error_message=str(exc),
        )
        # AppError instead of HTTPException (Task 265)
        raise AppError(
            code="INTERNAL_ERROR",
            message="Something went wrong",
        )
```

### Phase 5: post-launch verification (first hour)

```
1. Health-check endpoint /health → 200
2. Check the error-monitoring dashboard (no new error types)
3. Latency dashboard (no regression p95 / p99)
4. Manually test the critical user flow
5. Logs flowing + readable (`docker compose logs --tail=100 -f <service>`)
6. Rollback mechanism verified (dry run when possible)
```

### Phase 6: rollback plan (REQUIRED to write before deploy)

```markdown
## Rollback plan for [feature/release]

### Trigger conditions
- Error rate > 2x baseline
- P95 latency > [X]ms
- User reports of [specific issue]

### Rollback steps
1. Disable the feature flag (when applicable)
   OR
1. Deploy the previous version: `git revert <commit> && git push`
   PLUS on Hetzner: `docker compose pull && docker compose up -d`
2. Verify: health check + error monitoring
3. Communicate: notify the team

### Database considerations
- Migration [X] has rollback: `alembic downgrade -1`
- Data from the new feature: [preserved / cleaned up]

### Time to rollback
- Feature flag: <1 min
- Redeploy previous version: <5 min
- DB rollback: <15 min (when needed — pg_dump as the recovery source)
```

## Red flags

- Deployment without a rollback plan.
- No monitoring or error reporting in production.
- Big-bang releases (everything at once, no staging).
- Feature flags without expiration or owner.
- Nobody monitors the first hour post-deploy.
- Production config from memory instead of from code.
- "It's Friday afternoon, let's ship".
- DB-touching deploy without pg_dump (INVARIANT
  violation).
- Container recreate without mount verify (INVARIANT
  violation).

## Common rationalizations

| Rationalization | Reality |
|---|---|
| "It works in staging, so it works in production" | Production has different data, traffic patterns, edge cases. Monitor after deploy. |
| "We don't need a feature flag for that" | Every feature benefits from a kill switch. Even "simple" changes can break. |
| "Monitoring is overhead" | Without monitoring you discover problems through user complaints instead of dashboards. |
| "We add monitoring later" | Add it before launch. What you don't see, you can't debug. |
| "Rollback is admitting failure" | Rollback is responsible engineering. Shipping a broken feature is the failure. |
| "The migration is trivial — pg_dump is unnecessary" | Pattern session 2026-04-19 Juliane v2.6.5→v2.7: trivial migration, total DB loss. **Never.** |
| "Mount-verify is paranoia, compose reads .env anyway" | Pattern session 2026-04-19: `.env.production` was not read; a different mount appeared. **Verify.** |

## Contract

### INPUT
- **Required:** Code Review Board PASS
  (`code_review_board` L1 or L2 done) — BEFORE the
  pre-launch checklist.
- **Required:** test suite PASS (every level via the
  `testing` skill).
- **Required:** production-environment configuration in
  `.env.production` or equivalent.
- **Optional:** feature-flag definition (when phase 2
  applies).
- **Optional:** rollback-plan template (see phase 6).
- **Context:**
  `~/projects/personal/context/user/profile.md`
  §Deploy-Discipline (INVARIANTS),
  `skills/code_review_board/SKILL.md` (pre-deploy gate),
  `skills/security/SKILL.md` (cross-ref on
  security pre-launch).

### OUTPUT
**DELIVERS:**
- Pre-launch checklist ticked (6 categories +
  INVARIANT-1+2 when DB / container).
- Feature-flag configuration (when applicable).
- Rollback plan documented before deploy.
- Monitoring dashboards set up.
- Post-launch verification (first hour) executed.
- Backup file (pg_dump) on a DB-touching deploy.

**DOES NOT DELIVER:**
- No code changes — deploy skill, not a code skill.
- No code review — `code_review_board` is the
  precondition.
- No test run — `testing` is the precondition.
- No spec update — `retroactive_spec_update` is a separate
  lifecycle.

**ENABLES:**
- Production deploy with confidence (pre-launch gate
  satisfied).
- Fast rollback (plan + backup in place).
- Early issue detection (monitoring + verification).
- Step-by-step rollout (staged instead of big-bang).

### DONE
- Every pre-launch checklist box green.
- INVARIANT-1 (pg_dump) executed when DB touch.
- INVARIANT-2 (mount verify) executed when container
  recreate.
- Feature flag with owner + expiration configured (when
  relevant).
- Rollback plan documented.
- Post-launch verification (first hour) done; every check
  green.
- Cleanup date for the feature flag in the calendar.

### FAIL
- **Retry:** pre-launch checklist has issues → fix, then
  re-check (no deploy without 6/6 categories green). On
  DEPLOY-DISCIPLINE-INVARIANT violation: ABORT, no deploy.
- **Escalate:** the threshold table in phase 3 shows red
  values → immediate rollback per plan. Inform the user.
- **Abort:** INVARIANT violation (no pg_dump on DB touch
  / no mount verify on recreate) → ABORT before deploy.
  Risk too high.

## See also

- `skills/code_review_board/SKILL.md` — pre-deploy code
  gate.
- `skills/testing/SKILL.md` — test suite before deploy.
- `skills/deprecation_and_migration/SKILL.md` —
  deprecation workflow (complementary).
- `skills/_protocols/skill-guardrails.md` — skill
  anti-patterns.
- `~/projects/personal/context/user/profile.md`
  §Deploy-Discipline — INVARIANTS source.
