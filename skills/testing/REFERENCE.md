# testing — REFERENCE

Detail mechanics. The Buddy-facing `SKILL.md` carries the 6-level
pyramid, test-case design, coverage matrix, and run strategy.
This file is reference material for format details, eval
methodology, and the retest gate.

## Test-plan format

Fields per TC: level, type (positive / negative / boundary + AC
ref), input, expectation, verification.

```markdown
# Test plan: <task / spec title>
Derived from: <spec ref> | Level coverage: L0, L1, L2

### TC-001: <description>
- Level: L2 (unit) | Type: positive (AC-1)
- Input: <concrete> | Expectation: <concrete> | Verification: <how>
```

## Skeleton format

```python
# TC-001 (AC-1, L2 unit, positive) | INFRA: none
def test_crud_roundtrip():
    """AC-1: CRUD create → get → update → delete roundtrip."""
    pytest.skip("SKELETON — implementation pending")
```

**INFRA values:** `none`, `Postgres`, `Ollama`, `NATS`, `Neo4j`,
`Redis`, `Docker`.

## Execution order

**MUST on >5 TCs:** cluster by sub-task dependency. Red → green
→ refactor per cluster.

## Eval methodology

Gate inside the spec process (step 3e). Tests spec assumptions
with code against real infra, before implementation.

**Hypothesis types:** API behaviour · schema compatibility ·
performance (with a threshold!) · infra capability · config
behaviour · interop.

### Eval-script format

Path: `tests/eval/<task-id>/test_eval_<slug>.py`. Marker:
`@pytest.mark.eval`. Docstring: hypothesis, task ID,
`spec_version`. INFRA header. Minimal — only check the
hypothesis.

```python
# INFRA: Postgres, Ollama
"""Hypothesis: add() accepts custom DataPoint subclasses. Task: 050 | v1"""
@pytest.mark.eval
async def test_cognee_accepts_custom_datapoint():
    assert result.status == "success"
```

### Eval classification

- **GO** — hypothesis confirmed.
- **ADAPT** — partly confirmed; new constraints / ACs / failure
  modes go into the spec.
- **NO-GO** — refuted; architecture change or drop.

**Aggregate:** all GO → GO. ≥1 ADAPT → ADAPT. ≥1 NO-GO → NO-GO.

Eval scripts stay persistent in `tests/eval/` — an assumption
regression suite.

## Test-first detail

Skeletons BEFORE implementation as a delegation-ready artifact.
`skip("SKELETON")` → assertions (RED) → implement (GREEN) →
refactor.
Green right away = finding (the test isn't testing what the spec
requires).

## Retest gate (required after every fix)

| Fix type | Retest scope |
|---------|--------------|
| Code fix without spec impact | L0 + affected L1 |
| Spec change | L0 + L1 + matrix TCs for the changed AC |
| Framework change | L0 + L1 + L2 smoke |

After retest: update the matrix — eval status, AC quality if
anything shifted.

## Eval-patterns lookup

Domain-specific patterns live in
`skills/testing/eval_patterns/<domain>.md`.
Flow: read the criteria, mark gaps in the matrix, use the
pattern where it fits. No pattern for a domain → skip + note
("No eval pattern for <domain>").

## Infrastructure

Cross-project discipline for test infrastructure: when to mock, when
to lift, when to spin up containers, how to isolate. The principles
here are project-neutral — project-specific concretions (DSN, image
tags, port numbers, marker vocabulary, custom fixtures) live in the
**project-side** `docs/test-conventions/<topic>.md`. Cross-link
example: a consumer's `docs/test-conventions/postgres-fixtures.md`
documenting its concrete DSN, fixture name, and transaction wrapper.

### Fixture-availability preflight (the L-025 discipline)

**Trap:** the skeleton-writer (or any test author) writes
`pytest.skip("STUB — needs <fixture>")` while a canonical
implementation of that fixture already exists in the repo, then a
follow-up agent rebuilds parallel infrastructure instead of lifting
the existing one. The skip-comment is asserting absence without
having checked. Pattern class: **cycle-symptom-as-cause /
rebuild-vs-reuse**.

**Preflight (MUST before declaring STUB):**

1. `grep -rn '<fixture-name>\|<canonical-pattern>' tests/**/conftest.py tests/**/test_*.py`
   — does the fixture or an equivalent pattern (e.g. `real_pg_pool`,
   `pgvector`, `testcontainer`, `httpx_mock`) already exist?
2. Repo-root: `ls docker-compose.test*.yml` — is there a
   testcontainer stack the existing fixtures rely on?
3. Project-side: read `docs/test-conventions/` if present — do the
   conventions declare canonical lift-sources?

**Result handling:**

- **Found** → skeleton writes `pytest.skip("STUB — LIFT <fixture> from <path>:<line>")`. The next agent sees a clear lift-source; no parallel infra is invented.
- **Genuinely absent** → flag in the RED-phase return summary with
  grep-evidence (commands run, zero hits). **Do not invent new
  fixture infrastructure unilaterally** — escalate so a human or
  Buddy decides whether to spec the new fixture or lift from a
  related repo.

**Complementary producer-side discipline:** see §INFRA-Header
convention below — every skeleton declares the services it expects.
The preflight is the *consumer*-side check; the INFRA-Header is the
*producer*-side declaration. Both together close the rebuild-vs-reuse
loop.

### INFRA-Header convention

Every test skeleton declares its infrastructure requirements via a
comment header on the test (or module) so the tester (execution mode)
and MCA can choose fixtures or skip without guessing:

```python
# INFRA: none           — runs without external services (mock-based)
# INFRA: Postgres       — needs a Postgres testcontainer / pool fixture
# INFRA: NATS           — needs a NATS broker
# INFRA: Ollama         — needs a running LLM endpoint
# INFRA: Postgres,NATS  — needs both
```

The vocabulary is repo-local — projects extend it in their
`docs/test-conventions/`. The contract is **declarative, machine-
readable, lifted by tooling**: the tester reads the header and skips
when infra is unavailable instead of failing opaquely.

### Lift-vs-rebuild discipline

When the preflight finds an existing canonical fixture / pattern:
**lift it, don't rebuild.** Rebuilding produces:

- Two competing fixtures with subtly different lifecycle semantics
  (session vs function scope, cleanup strategy, lifecycle ordering).
- Maintenance debt — bug fixes go into only one of them.
- Test-author confusion — which is canonical?

The exception is when the existing fixture is wrong for the new test
(scope mismatch, missing setup) and *fixing* the existing one would
break its current consumers — then a parallel fixture is justified,
but call it out explicitly and create a follow-up task to converge.

### Anti-patterns

- **NOT** `pytest.skip("STUB — needs X")` without running the
  preflight. **INSTEAD** grep first, document evidence in the RED
  return summary. Because: an unchecked skip-comment asserts absence
  without checking and lets the next agent rebuild parallel
  infrastructure instead of lifting the existing one; pattern class
  is *cycle-symptom-as-cause*.
- **NOT** SQLite fallback for Postgres tests. **INSTEAD** real
  Postgres via testcontainer. Because: pgvector, JSONB operators,
  tsvector, NUMERIC — none of these translate to SQLite.
- **NOT** TRUNCATE-based isolation between tests. **INSTEAD**
  transaction-rollback (§Transaction-rollback isolation pattern
  below). Because: TRUNCATE is slow (no DDL caching, VACUUM after),
  prone to async leak, and order-sensitive on FK-bearing tables.
- **NOT** invent a parallel fixture when the preflight has not been
  run. **INSTEAD** preflight first, lift second, rebuild only with
  explicit justification.

### Marker-vs-directory selection

**Test selection is marker-driven, not directory-driven.** Verzeichnisse
(`tests/<area>/`) are *organization* — they group related tests by
domain. Selectors (`@pytest.mark.integration`, `.contract`, `.property`,
`.smoke`, `.e2e`, `.eval`) decide *which* tests a CI step runs.

Consequence: a test in `tests/brain/` can carry
`@pytest.mark.integration` and be picked up by
`make test-integration`. The directory is not the filter; the marker
is. This keeps the L0-L5 pyramid orthogonal to the directory
taxonomy.

### Transaction-rollback isolation pattern

For per-test isolation in DB-backed test suites, use **function-scoped
transaction rollback**, not TRUNCATE / DELETE FROM:

```python
@pytest.fixture
async def db_conn(pool):
    """Per-test DB connection with automatic rollback."""
    async with pool.acquire() as conn:
        tx = conn.transaction()
        await tx.start()
        yield conn
        await tx.rollback()
```

**Why:** faster (no DDL, no VACUUM), order-independent (no FK
sequencing), simpler (no per-table knowledge), naturally isolated
under parallel execution.

**Scope constraint:** function-scoped transactions cannot wrap
session-scoped fixtures. Typical split: connection pool / engine =
`scope=session`, per-test transaction = `scope=function`.
Session-scope is for **expensive setup that is read-only or
reset-between-tests by the transaction wrapper**, not for shared
mutable state.

### docker-compose.test.yml convention

Conventions for the testcontainer compose file (project-side; this
section documents the contract):

- **Separate ports from dev** — test stack uses ports distinct from
  the dev stack to avoid collision when both run on the same
  developer machine. The concrete port mapping is project-side; the
  *convention* (no port collision) is project-neutral.
- **Ephemeral storage** — mount data volumes as `tmpfs` so test
  state is RAM-resident. Tests run faster (no disk I/O for Postgres
  WAL / NATS JetStream); persistence is unwanted between runs
  anyway, so `tmpfs` aligns hardware to intent.
- **Healthcheck-gated startup** — every service declares a
  healthcheck; the suite waits for ready before exercising it. No
  "sleep 5 and hope".
- **Testcontainer-only for L3 / L4** — L0 / L1 / L2 should not need
  the compose stack; mock at the boundary. The compose stack
  enters scope at L3 (integration) and is mandatory at L4 (E2E).

Concrete compose YAML (image tags, env vars, port numbers, healthcheck
commands) lives in the project repo, not here.

### Cross-link: project-side conventions

The forge framework documents *what discipline applies*; the consumer
repo documents *what concrete fixtures and infra exist for this
project*. Convention:

```
<consumer-repo>/docs/test-conventions/
  postgres-fixtures.md      — DSN, pool fixture, transaction wrapper
  nats-fixtures.md          — broker URL, subscription cleanup
  mock-conventions.md       — Ollama / external API mock patterns
  README.md                 — index + cross-link back to forge §Infrastructure
```

Example: a Postgres-backed consumer maintains
`<consumer-repo>/docs/test-conventions/postgres-fixtures.md` with
the concrete `real_pg_pool` fixture (DSN, port, image tag,
transaction-rollback wrapper). Test-skeleton-writers running in
the consumer repo lift from there; the discipline that *makes them
check first* lives in this §Infrastructure section.
