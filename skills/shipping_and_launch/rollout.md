# Shipping and launch — rollout, monitoring and post-launch verification

Step-loaded unit of `skills/shipping_and_launch/SKILL.md`. Read it when a release uses a feature flag, before the
first deploy stage of a rollout and at each advance, hold or rollback decision, when setting up monitoring before
launch, and in the first hour after the launch. Phases 1.5 (deploy-discipline invariants) and 6 (rollback plan) are
in `SKILL.md`, phase 1 in `pre-launch-checklist.md`.

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
   └── The broad run in the staging environment, unless it already
       ran on these bytes (skills/testing/run-strategy.md: no rerun after a hash-checked transfer)
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
├── DB connection-pool usage (pool exhaustion)
├── Disk space
├── Network latency
└── Queue depth (broker / job queue, when relevant)

Client (when frontend):
├── Core Web Vitals (LCP, INP, CLS)
├── JS errors
├── API error rates from the client perspective
└── Page-load time
```

#### Error-reporting pattern (Python / FastAPI)

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
        # AppError instead of HTTPException
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
