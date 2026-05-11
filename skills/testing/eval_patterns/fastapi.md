# Eval Pattern: FastAPI Endpoints

Domain-specific quality criteria for FastAPI endpoint tests.
The tester reads this file in execution mode and checks whether the written tests cover these criteria.
Missing criteria → coverage-matrix gap → back to main-code-agent.

SoT for FastAPI testing quality. Referenced from `skills/testing/SKILL.md` (Eval Patterns section).

---

## L2 Unit Criteria

### FA-U1: Request Validation

- **Level:** L2 Unit
- **Check question:** Does the endpoint return 422 with the correct Pydantic detail format on invalid input?
- **Violation signal:** 500 instead of 422, or 422 without a `detail` array carrying `loc`/`msg`/`type` structure.
- **Code:**

```python
# Generated from FA-U1 (L2 Unit, Negative)
# INFRA: none
import pytest
from httpx import AsyncClient


async def test_invalid_request_returns_422(client: AsyncClient):
    """FA-U1: Invalid request body → 422 with Pydantic detail format."""
    resp = await client.post("/api/brain/entities", json={"name": 123})  # name expects str
    assert resp.status_code == 422
    detail = resp.json()["detail"]
    assert isinstance(detail, list)
    assert len(detail) > 0
    error = detail[0]
    assert "loc" in error
    assert "msg" in error
    assert "type" in error
```

### FA-U2: Response Serialisation

- **Level:** L2 Unit
- **Check question:** Does the response match the declared Pydantic response model exactly — no extra fields, correct types?
- **Violation signal:** Fields that are not defined in the response model appear in the response, or fields are missing.
- **Code:**

```python
# Generated from FA-U2 (L2 Unit, Positive)
# INFRA: Postgres
from pydantic import ValidationError
from buddyai.gateway.models import BrainEntryResponse


async def test_response_matches_model(client: AsyncClient):
    """FA-U2: Response is exactly the declared response model."""
    resp = await client.get("/api/brain/entities/some-uuid")
    assert resp.status_code == 200

    try:
        BrainEntryResponse.model_validate(resp.json())
    except ValidationError as e:
        pytest.fail(f"Response deviates from model: {e}")

    response_keys = set(resp.json().keys())
    model_keys = set(BrainEntryResponse.model_fields.keys())
    extra = response_keys - model_keys
    assert extra == set(), f"Extra fields in response: {extra}"
```

### FA-U3: Dependency Injection

- **Level:** L2 Unit
- **Check question:** Can dependencies (Brain, NATS client, etc.) be cleanly substituted in tests without changing app logic?
- **Violation signal:** Test requires a real DB connection even though only endpoint logic is being tested. Or: `app.dependency_overrides` has no effect.
- **Code:**

```python
# Generated from FA-U3 (L2 Unit, Positive)
# INFRA: none
from unittest.mock import AsyncMock
from buddyai.gateway.app import create_app
from buddyai.gateway.deps import get_brain
from httpx import AsyncClient, ASGITransport


async def test_dependency_override():
    """FA-U3: Dependencies can be replaced via dependency_overrides."""
    mock_brain = AsyncMock()
    mock_brain.get_entity.return_value = {"id": "test", "name": "Mock Entity"}

    app = create_app()
    app.dependency_overrides[get_brain] = lambda: mock_brain

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        resp = await c.get("/api/brain/entities/test")

    assert resp.status_code == 200
    mock_brain.get_entity.assert_called_once_with("test")
    app.dependency_overrides.clear()
```

### FA-U4: Error Handling

- **Level:** L2 Unit
- **Check question:** Are HTTPExceptions raised with the correct status code and a human-readable `detail` — no leaking of internal stack traces?
- **Violation signal:** 500 with a traceback instead of a defined 404/409/etc. Or: `detail` is a Python repr instead of a message.
- **Code:**

```python
# Generated from FA-U4 (L2 Unit, Negative)
# INFRA: none
async def test_not_found_returns_404(client: AsyncClient):
    """FA-U4: Non-existent entity → 404 with readable detail."""
    resp = await client.get("/api/brain/entities/nonexistent-uuid")
    assert resp.status_code == 404
    body = resp.json()
    assert "detail" in body
    assert isinstance(body["detail"], str)
    assert "Traceback" not in body["detail"]
    assert "asyncpg" not in body["detail"]
```

### FA-U5: Auth Guards

- **Level:** L2 Unit
- **Check question:** Do protected endpoints return 401 or 403 without/with an invalid auth token?
- **Violation signal:** Endpoint returns 200 without an auth header. Or: 500 instead of 401/403.
- **Code:**

```python
# Generated from FA-U5 (L2 Unit, Negative)
# INFRA: none
async def test_protected_endpoint_without_auth(client: AsyncClient):
    """FA-U5: Protected endpoint without auth → 401."""
    resp = await client.post("/api/brain/entities", json={"name": "test"})
    assert resp.status_code in (401, 403)


async def test_protected_endpoint_with_invalid_token(client: AsyncClient):
    """FA-U5: Protected endpoint with invalid token → 401."""
    resp = await client.post(
        "/api/brain/entities",
        json={"name": "test"},
        headers={"Authorization": "Bearer invalid-token-xxx"},
    )
    assert resp.status_code in (401, 403)
```

---

## L3 Contract Criteria

### FA-C1: OpenAPI Schema Compliance

- **Level:** L3 Contract
- **Check question:** Do all endpoints pass against the auto-generated OpenAPI spec — including randomised inputs?
- **Violation signal:** schemathesis finds schema mismatches: undocumented status codes, missing fields, type mismatches.
- **Code:**

```python
# Generated from FA-C1 (L3 Contract, Property)
# INFRA: Postgres
import pytest
import schemathesis
from buddyai.gateway.app import create_app

schema = schemathesis.openapi.from_asgi("/openapi.json", app=create_app())


@schema.parametrize()
@pytest.mark.contract
def test_openapi_contract(case):
    """FA-C1: Every endpoint satisfies its OpenAPI schema."""
    response = case.call_and_validate()
```

**Note:** `call_and_validate()` automatically checks: status code is documented in the schema, response body matches the schema, content-type is correct. For endpoints with DB state, use the `from_fixture` variant (schemathesis 4.x):

```python
# Alternative: pytest-fixture-based (recommended when Brain is needed)
@pytest.fixture
def api_schema(brain):
    app = create_app(brain=brain)
    return schemathesis.openapi.from_asgi("/openapi.json", app)

schema = schemathesis.pytest.from_fixture("api_schema")

@schema.parametrize()
@pytest.mark.contract
def test_api_with_brain(case):
    case.call_and_validate()
```

### FA-C2: Schema Stability

- **Level:** L3 Contract
- **Check question:** Are breaking changes in request/response schemas detectable — missing required fields, type changes, removed endpoints?
- **Violation signal:** A consumer client breaks after an update because a field changed type or is missing.
- **Code:**

```python
# Generated from FA-C2 (L3 Contract, Regression)
# INFRA: none
import json
import pytest
from pathlib import Path
from deepdiff import DeepDiff
from httpx import AsyncClient, ASGITransport
from buddyai.gateway.app import create_app


SNAPSHOT_PATH = Path("tests/snapshots/openapi_schema.json")


@pytest.mark.contract
async def test_schema_no_breaking_changes():
    """FA-C2: OpenAPI schema has no unexpected breaking changes."""
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        resp = await c.get("/openapi.json")
    current = resp.json()

    if not SNAPSHOT_PATH.exists():
        SNAPSHOT_PATH.parent.mkdir(parents=True, exist_ok=True)
        SNAPSHOT_PATH.write_text(json.dumps(current, indent=2))
        pytest.skip("Snapshot created — first run")

    baseline = json.loads(SNAPSHOT_PATH.read_text())
    diff = DeepDiff(baseline, current, ignore_order=True)

    breaking_indicators = ["dictionary_item_removed", "type_changes"]
    for indicator in breaking_indicators:
        assert indicator not in diff, (
            f"Breaking change: {indicator}\n{diff[indicator]}"
        )
```

**Workflow:** Snapshot is created on the first run. For intentional changes: `pytest --update-snapshots` (custom flag) or copy manually. Unintentional changes → test FAIL.

### FA-C3: Content-Type Validation

- **Level:** L3 Contract
- **Check question:** Does the endpoint accept and return the correct content types?
- **Violation signal:** Endpoint accepts `text/plain` where JSON is expected, or returns HTML instead of JSON.
- **Code:**

```python
# Generated from FA-C3 (L3 Contract, Negative)
# INFRA: none
@pytest.mark.contract
async def test_wrong_content_type_rejected(client: AsyncClient):
    """FA-C3: Endpoint rejects the wrong content type."""
    resp = await client.post(
        "/api/brain/entities",
        content="name=test",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert resp.status_code == 422


@pytest.mark.contract
async def test_response_content_type_json(client: AsyncClient):
    """FA-C3: API responses have content-type application/json."""
    resp = await client.get("/api/brain/entities")
    assert resp.status_code == 200
    assert "application/json" in resp.headers.get("content-type", "")
```

### FA-C4: Pagination

- **Level:** L3 Contract
- **Check question:** Does pagination work correctly — cursor/offset, empty results, last page, no duplicates?
- **Violation signal:** Last page returns duplicates. Empty page returns 500 instead of an empty list. Cursor points to a non-existent offset.
- **Code:**

```python
# Generated from FA-C4 (L3 Contract, Positive + Boundary)
# INFRA: Postgres
@pytest.mark.contract
async def test_pagination_empty_results(client: AsyncClient):
    """FA-C4: Empty result set → 200 with empty list, not 404."""
    resp = await client.get("/api/brain/entities?offset=99999&limit=10")
    assert resp.status_code == 200
    body = resp.json()
    assert body["items"] == []
    assert body["total"] >= 0


@pytest.mark.contract
async def test_pagination_no_duplicates(client: AsyncClient, brain):
    """FA-C4: Sequential pages contain no duplicates."""
    for i in range(15):
        await brain.create_entity(name=f"entity-{i}", entity_type="test")

    all_ids = []
    offset = 0
    limit = 5
    while True:
        resp = await client.get(f"/api/brain/entities?offset={offset}&limit={limit}")
        items = resp.json()["items"]
        if not items:
            break
        all_ids.extend(item["id"] for item in items)
        offset += limit

    assert len(all_ids) == len(set(all_ids)), "Duplicates in paginated results"
```

---

## L3 Integration Criteria

### FA-I1: DB Transaction Behaviour

- **Level:** L3 Integration
- **Check question:** On a failure after a partial DB write, is everything rolled back correctly — no partial state?
- **Violation signal:** Entity created but relation missing because the relation insertion failed.
- **Code:**

```python
# Generated from FA-I1 (L3 Integration, Negative)
# INFRA: Postgres
@pytest.mark.integration
async def test_transaction_rollback_on_error(client: AsyncClient, brain):
    """FA-I1: On error in a multi-step operation → no partial state."""
    count_before = await brain.count_entities()

    resp = await client.post("/api/brain/entities", json={
        "name": "test-entity",
        "entity_type": "test",
        "relations": [{"target_id": "nonexistent-uuid", "relation_type": "depends_on"}],
    })
    assert resp.status_code >= 400

    count_after = await brain.count_entities()
    assert count_after == count_before, "Partial state: entity created without relation"
```

### FA-I2: NATS Event Emission

- **Level:** L3 Integration
- **Check question:** Does the endpoint emit the correct NATS event after a successful operation?
- **Violation signal:** No event after a mutation. Event emitted on a failed operation. Payload deviates from the schema.
- **Code:**

```python
# Generated from FA-I2 (L3 Integration, Positive)
# INFRA: Postgres, NATS
import json
import asyncio
import pytest


@pytest.mark.integration
async def test_entity_created_event_emitted(client: AsyncClient, nats_client):
    """FA-I2: Entity create emits a brain.entity.created event."""
    sub = await nats_client.subscribe("brain.entity.created")

    resp = await client.post("/api/brain/entities", json={
        "name": "event-test",
        "entity_type": "test",
    })
    assert resp.status_code == 201
    entity_id = resp.json()["id"]

    try:
        msg = await asyncio.wait_for(sub.next_msg(), timeout=2.0)
    except asyncio.TimeoutError:
        pytest.fail("No NATS event received within 2s")

    payload = json.loads(msg.data)
    assert payload["entity_id"] == entity_id
    assert payload["event_type"] == "created"
    await sub.unsubscribe()


@pytest.mark.integration
async def test_no_event_on_failed_mutation(client: AsyncClient, nats_client):
    """FA-I2: No event on a failed operation."""
    sub = await nats_client.subscribe("brain.entity.>")

    resp = await client.post("/api/brain/entities", json={"invalid": True})
    assert resp.status_code >= 400

    with pytest.raises(asyncio.TimeoutError):
        await asyncio.wait_for(sub.next_msg(), timeout=0.5)
    await sub.unsubscribe()
```

### FA-I3: Connection Pool Behaviour

- **Level:** L3 Integration
- **Check question:** Does the app behave correctly on pool exhaustion — graceful error rather than hang?
- **Violation signal:** Request hangs indefinitely. Or: unhandled asyncpg exception leaks as a 500 with a traceback.
- **Code:**

```python
# Generated from FA-I3 (L3 Integration, Negative)
# INFRA: Postgres
import asyncio
import pytest


@pytest.mark.integration
async def test_pool_exhaustion_graceful(client: AsyncClient):
    """FA-I3: On pool exhaustion → defined error rather than hang."""
    tasks = [client.get("/api/brain/entities?limit=100") for _ in range(50)]
    responses = await asyncio.gather(*tasks, return_exceptions=True)

    status_codes = []
    for r in responses:
        if hasattr(r, "status_code"):
            status_codes.append(r.status_code)

    assert 200 in status_codes, "At least one request must succeed"
    non_200 = [s for s in status_codes if s != 200]
    for s in non_200:
        assert s in (503, 429), f"Expected 503/429 on pool exhaustion, got {s}"
```

---

## Checklist for the Tester

In execution mode for FastAPI-related tests, walk through these criteria:

1. For every endpoint in scope: are FA-U1 through FA-U5 covered?
2. Are there contract tests (FA-C1)? Schema-stability snapshot up to date (FA-C2)?
3. For endpoints with DB writes: are FA-I1 (transactions) and FA-I2 (events) covered?
4. For endpoints with pagination: is FA-C4 covered?
5. Missing criteria → gap in the coverage matrix → back to main-code-agent.
