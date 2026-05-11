# Verification Workflow Guide

Step-by-step guide for executing the L3+ Verification Suite.
Referenced from `workflows/templates/verification.yaml`.

The tester reads this document when running the Verification Workflow. Each step describes WHAT to do, WHICH tools/commands are needed, and HOW the result is evaluated.

**Prerequisite:** Test infrastructure is up (`make test-infra-up`). See `skills/test_infrastructure/SKILL.md`.

---

## Step 1: Contract Tests

**Goal:** Ensure that all API endpoints comply with their declared OpenAPI schema.

### 1.1 Check prerequisites

```bash
# schemathesis installed?
python -c "import schemathesis; print(schemathesis.__version__)"

# deepdiff installed for schema stability?
python -c "import deepdiff; print(deepdiff.__version__)"
```

If not: `pip install schemathesis deepdiff --break-system-packages`

### 1.2 Schema compliance via schemathesis (FA-C1)

**Option A: CLI (quick check)**

```bash
# Start the app (if needed) or use the ASGI transport
# CLI against running app (schemathesis 4.x):
schemathesis run http://localhost:8000/openapi.json

# With a limited number of examples (via schemathesis.toml or CLI):
# schemathesis run http://localhost:8000/openapi.json --generation.max-examples=50
# For current CLI options: schemathesis run --help
```

**Option B: Programmatic (integrated into the test suite)**

```python
# tests/gateway/test_contracts.py
import pytest
import schemathesis
from buddyai.gateway.app import create_app

schema = schemathesis.openapi.from_asgi("/openapi.json", app=create_app())


@schema.parametrize()
@pytest.mark.contract
def test_openapi_contract(case):
    """Every endpoint satisfies its OpenAPI schema."""
    response = case.call_and_validate()
```

**Run:**

```bash
make test-contract
# Or directly:
pytest tests/ -m "contract" -v
```

### 1.3 Check schema stability (FA-C2)

```bash
# First run: creates the snapshot
pytest tests/gateway/test_contracts.py::test_schema_no_breaking_changes -v

# Subsequent runs: compare against the snapshot
# FAIL = breaking change -> intentional? -> update the snapshot
# FAIL = unintentional? -> fix the code
```

Snapshot update on intentional changes:

```bash
cp tests/snapshots/openapi_schema.json tests/snapshots/openapi_schema.json.bak
pytest tests/gateway/test_contracts.py::test_schema_no_breaking_changes -v
# Test creates a new snapshot on the first run after deletion
```

### 1.4 Response-model validation (FA-U2)

```python
# For every endpoint in scope:
from buddyai.gateway.models import BrainEntryResponse  # matching model

resp = client.get("/api/brain/entities/some-id")
BrainEntryResponse.model_validate(resp.json())  # raises on schema mismatch
```

### 1.5 Evaluation

| Result | Meaning | Next step |
|--------|---------|-----------|
| All tests PASS | Schema is stable, endpoints conformant | Continue to Step 2 |
| schemathesis FAIL | Endpoint deviates from schema | Fix -> retest |
| Schema-stability FAIL | Breaking change detected | Deliberate decision: intentional -> update snapshot, unintentional -> fix |

---

## Step 2: API End-to-End Tests

**Goal:** Verify full request/response cycles against real services (DB, NATS).

### 2.1 Start test infrastructure

```bash
# Start the Docker Compose test stack
make test-infra-up

# Verify services are running:
docker compose -f docker-compose.test.yml ps
# Expectation: postgres-test (healthy), nats-test (healthy)

# Postgres reachable?
psql "postgresql://buddyai_test:test@localhost:5433/buddyai_test" -c "SELECT 1"

# NATS reachable?
curl -s http://localhost:8223/healthz
```

### 2.2 Run migrations

```bash
DATABASE_URL="postgresql://buddyai_test:test@localhost:5433/buddyai_test" alembic upgrade head
```

### 2.3 Run tests

```bash
make test-e2e
# Or:
pytest tests/ -m "e2e" -v
```

### 2.4 What E2E tests cover

Full workflows that traverse multiple layers:

```python
@pytest.mark.e2e
async def test_entity_lifecycle(client: AsyncClient):
    """Full lifecycle: Create -> Get -> Update -> Search -> Delete."""
    # Create
    resp = await client.post("/api/brain/entities", json={
        "name": "e2e-test", "entity_type": "concept",
    })
    assert resp.status_code == 201
    entity_id = resp.json()["id"]

    # Get
    resp = await client.get(f"/api/brain/entities/{entity_id}")
    assert resp.status_code == 200
    assert resp.json()["name"] == "e2e-test"

    # Update
    resp = await client.patch(f"/api/brain/entities/{entity_id}", json={
        "name": "e2e-updated",
    })
    assert resp.status_code == 200

    # Search
    resp = await client.get("/api/brain/search?q=e2e-updated")
    assert resp.status_code == 200
    assert any(e["id"] == entity_id for e in resp.json()["items"])

    # Delete
    resp = await client.delete(f"/api/brain/entities/{entity_id}")
    assert resp.status_code == 204

    # Verify deleted
    resp = await client.get(f"/api/brain/entities/{entity_id}")
    assert resp.status_code == 404
```

### 2.5 Cleanup

```bash
make test-infra-down
# Or manually:
docker compose -f docker-compose.test.yml down -v
```

### 2.6 Evaluation

| Result | Meaning | Next step |
|--------|---------|-----------|
| All tests PASS | Full workflows work | Continue to Step 3 |
| FAIL with DB error | Schema problem or migration gap | Check PG-I4, fix migration |
| FAIL with NATS error | Event-system problem | Test FA-I2 in isolation |
| Timeout | Service-startup problem | Check docker-compose logs |

---

## Step 3: Browser E2E Tests (DEFERRED)

DEFERRED — only when a custom React UI exists. Open WebUI is interim and not under test. When the custom UI is built: create a dedicated Playwright skill, use the `e2e` marker, populate this step.

Note in the verification report: `Browser E2E: SKIPPED — no custom UI present.`

---

## Step 4: Property-Based Tests

**Goal:** Check invariants with generated inputs. hypothesis finds edge cases that manual tests miss.

### 4.1 Define hypothesis strategies

Reusable strategies live in `tests/brain/strategies.py`:

```python
# tests/brain/strategies.py
from hypothesis import strategies as st
import numpy as np

EMBEDDING_DIM = 768

entity_names = st.text(
    alphabet=st.characters(categories=("L", "N", "P", "Z")),
    min_size=1, max_size=255,
)
entity_types = st.sampled_from(["person", "concept", "project", "document", "location"])
entity_metadata = st.one_of(
    st.none(),
    st.dictionaries(
        keys=st.text(min_size=1, max_size=50),
        values=st.one_of(
            st.text(max_size=200),
            st.integers(),
            st.floats(allow_nan=False),
            st.booleans(),
        ),
        max_size=10,
    ),
)
embeddings = st.builds(lambda: np.random.rand(EMBEDDING_DIM).tolist())
relation_types = st.sampled_from(["depends_on", "related_to", "part_of", "derived_from"])
```

### 4.2 Formulate properties

Every property follows the pattern: **"For all valid inputs, X holds."**

| ID | Property | What hypothesis generates |
|----|----------|---------------------------|
| PG-P1 | Entity round-trip: create -> get returns identical data | name, type, metadata |
| PG-P2 | Search completeness: term in name -> search finds it | search terms |
| PG-P3 | Relation integrity: delete -> no orphaned relations | entity graphs |
| PG-P4 | Embedding dimension: only 768d accepted | random dimensions |

### 4.3 Run tests

```bash
make test-property
# Or:
pytest tests/ -m "property" -v

# With more examples (for thorough checking):
pytest tests/ -m "property" -v --hypothesis-seed=0 -s
```

### 4.4 Failure analysis

On a hypothesis failure:

1. **Read the minimal counter-example** — hypothesis automatically shrinks to the smallest input that reproduces the error.
2. **Reproduce** — the seed is in the output: `pytest tests/brain/test_properties.py --hypothesis-seed=<SEED>`
3. **Identify root cause** — is it an app bug or an over-tight test?
4. **Fix + retest** — after the fix, run the same seed again.

### 4.5 Evaluation

| Result | Meaning | Next step |
|--------|---------|-----------|
| All properties PASS | Invariants hold for generated inputs | Continue to Step 5 |
| Shrunk example found | Edge case discovered | Root-cause fix, retest with the same seed |
| Deadline exceeded | Test too slow for hypothesis | Raise `@settings(deadline=...)` or optimise the DB fixture |

---

## Step 5: Smoke Tests

**Goal:** Are the critical endpoints reachable on the running instance and do they respond correctly?

### 5.1 Configuration

The production URL is set via an environment variable:

```bash
export PROD_URL="https://your-deployment.example.com"
# Or for a local instance:
export PROD_URL="http://localhost:8000"
```

### 5.2 Smoke-test pattern

```python
# tests/smoke/test_smoke.py
import os
import pytest
from httpx import AsyncClient

PROD_URL = os.environ.get("PROD_URL", "http://localhost:8000")


@pytest.mark.smoke
async def test_health_endpoint():
    """Smoke: /health reachable and returns 200."""
    async with AsyncClient(base_url=PROD_URL) as c:
        resp = await c.get("/health")
    assert resp.status_code == 200


@pytest.mark.smoke
async def test_openapi_schema_available():
    """Smoke: OpenAPI schema reachable."""
    async with AsyncClient(base_url=PROD_URL) as c:
        resp = await c.get("/openapi.json")
    assert resp.status_code == 200
    schema = resp.json()
    assert "paths" in schema
    assert len(schema["paths"]) > 0


@pytest.mark.smoke
async def test_brain_search_responds():
    """Smoke: brain search endpoint responds (may be empty)."""
    async with AsyncClient(base_url=PROD_URL) as c:
        resp = await c.get("/api/brain/search?q=test")
    assert resp.status_code == 200
    assert "items" in resp.json()


@pytest.mark.smoke
async def test_brain_entities_list():
    """Smoke: entity list responds."""
    async with AsyncClient(base_url=PROD_URL) as c:
        resp = await c.get("/api/brain/entities?limit=1")
    assert resp.status_code == 200
```

### 5.3 Run

```bash
PROD_URL=https://your-deployment.example.com make test-smoke
# Or:
PROD_URL=http://localhost:8000 pytest tests/ -m "smoke" -v
```

### 5.4 Evaluation

| Result | Meaning | Next step |
|--------|---------|-----------|
| All PASS | System is reachable and responsive | Verification suite complete |
| Health FAIL | Service down or network problem | Check ops (Portainer, systemctl, Cloudflare) |
| Endpoint FAIL | Specific endpoint broken | Debug in isolation, check logs |
| Timeout | Performance problem or DNS | Network + service logs |

---

## Verification Report Format

After all steps complete: document the report in the task file.

```markdown
## Verification Report

Date: YYYY-MM-DD
Runner: tester (execution mode)

| Step | Status | Details |
|------|--------|---------|
| Contract (schemathesis) | PASS | 12 endpoints, 0 schema violations |
| Contract (schema stability) | PASS | Snapshot current, no breaking changes |
| API E2E | PASS | 8 workflows, all green |
| Browser E2E | SKIPPED | No custom UI present |
| Property-based | PASS | 4 properties, 150 examples, 0 failures |
| Smoke | PASS | 4 endpoints reachable |

Result: VERIFICATION PASS
```

On FAIL in any step: `VERIFICATION FAIL — Step X: [details]`. Verification is a hard gate — no merge without PASS.
