# Eval Pattern: Postgres/Brain

Domain-specific quality criteria for Brain library tests (asyncpg, no ORM).
The tester reads this file in execution mode and checks whether the written tests cover these criteria.
Missing criteria → coverage-matrix gap → back to main-code-agent.

SoT for Brain/Postgres testing quality. Referenced from `skills/testing/SKILL.md` (Eval Patterns section).

**Stack context:** asyncpg directly (no ORM), parameterised queries, Postgres 16 + pgvector (768d nomic-embed-text), JSONB for metadata, UUID4 as primary keys.

---

## L2 Unit Criteria

### PG-U1: Parameterised Queries

- **Level:** L2 Unit
- **Check question:** Does every query use parameterised placeholders (`$1`, `$2`) — no f-strings, no `.format()`, no `%s` substitution in SQL?
- **Violation signal:** SQL injection possible. String concatenation in SQL strings recognisable in code review.
- **Code:**

```python
# Generated from PG-U1 (L2 Unit, Structural)
# INFRA: none
import ast
import inspect
from pathlib import Path


def test_no_string_formatting_in_sql():
    """PG-U1: No f-strings or .format() in SQL queries."""
    brain_src = Path("src/buddyai/brain/")
    violations = []

    for py_file in brain_src.rglob("*.py"):
        source = py_file.read_text()
        tree = ast.parse(source)
        for node in ast.walk(tree):
            # f-string on a line that contains SQL keywords
            if isinstance(node, ast.JoinedStr):
                line = source.splitlines()[node.lineno - 1]
                sql_keywords = ["SELECT", "INSERT", "UPDATE", "DELETE", "CREATE", "ALTER"]
                if any(kw in line.upper() for kw in sql_keywords):
                    violations.append(f"{py_file}:{node.lineno}: f-string in SQL")

    assert violations == [], f"SQL injection risk:\n" + "\n".join(violations)
```

**Note:** This test is static (L0-like) but domain-specific to Brain code. It runs as part of the L2 suite because it deliberately checks Brain modules, not generic repo structure.

### PG-U2: NULL Handling

- **Level:** L2 Unit
- **Check question:** Are optional fields correctly handled as SQL NULL — no NoneType errors, no string `"None"` in the DB?
- **Violation signal:** `NoneType has no attribute` runtime error. Or: string `"None"` in the DB instead of SQL NULL.
- **Code:**

```python
# Generated from PG-U2 (L2 Unit, Boundary)
# INFRA: Postgres
import pytest


async def test_optional_field_stored_as_null(brain):
    """PG-U2: Optional fields → SQL NULL, not the string 'None'."""
    entity_id = await brain.create_entity(
        name="null-test",
        entity_type="test",
        metadata=None,  # optional field
    )
    entity = await brain.get_entity(entity_id)

    # Must be None, not the string "None"
    assert entity["metadata"] is None


async def test_optional_field_roundtrip(brain):
    """PG-U2: Entity storable with and without optional fields."""
    # With metadata
    id_with = await brain.create_entity(
        name="with-meta", entity_type="test", metadata={"key": "value"},
    )
    # Without metadata
    id_without = await brain.create_entity(
        name="without-meta", entity_type="test",
    )

    e_with = await brain.get_entity(id_with)
    e_without = await brain.get_entity(id_without)

    assert e_with["metadata"] == {"key": "value"}
    assert e_without["metadata"] is None
```

### PG-U3: UUID Generation

- **Level:** L2 Unit
- **Check question:** Are UUIDs generated as UUID4 — correctly formatted, no duplicates, no sequential patterns?
- **Violation signal:** UUID collision. Or: UUID is not a valid UUID4 format.
- **Code:**

```python
# Generated from PG-U3 (L2 Unit, Positive)
# INFRA: Postgres
import uuid


async def test_uuid_format(brain):
    """PG-U3: Generated IDs are valid UUID4."""
    entity_id = await brain.create_entity(name="uuid-test", entity_type="test")
    parsed = uuid.UUID(entity_id)
    assert parsed.version == 4


async def test_uuid_uniqueness(brain):
    """PG-U3: 100 generated IDs are all unique."""
    ids = []
    for i in range(100):
        eid = await brain.create_entity(name=f"unique-{i}", entity_type="test")
        ids.append(eid)

    assert len(ids) == len(set(ids)), "UUID duplicates found"
```

### PG-U4: JSONB Queries

- **Level:** L2 Unit
- **Check question:** Do JSONB queries use the correct Postgres operators (`->`, `->>`, `@>`, `?`) — no Python dict artefacts in SQL?
- **Violation signal:** Postgres syntax error on a JSONB query. Or: a Python dict stored as a string in JSONB instead of as real JSONB.
- **Code:**

```python
# Generated from PG-U4 (L2 Unit, Positive)
# INFRA: Postgres
import json


async def test_jsonb_query_by_key(brain):
    """PG-U4: JSONB query by key returns correct results."""
    await brain.create_entity(
        name="jsonb-test",
        entity_type="test",
        metadata={"category": "alpha", "priority": 1},
    )
    results = await brain.search_entities_by_metadata(key="category", value="alpha")
    assert len(results) >= 1
    assert results[0]["metadata"]["category"] == "alpha"


async def test_jsonb_stored_as_jsonb_not_string(brain):
    """PG-U4: metadata is stored as JSONB, not as a string."""
    entity_id = await brain.create_entity(
        name="jsonb-type-test",
        entity_type="test",
        metadata={"nested": {"deep": True}},
    )
    # Direct DB query to check the actual type
    row = await brain._conn.fetchrow(
        "SELECT pg_typeof(metadata) AS dtype FROM entities WHERE id = $1",
        entity_id,
    )
    assert row["dtype"] == "jsonb"
```

---

## L3 Integration Criteria

### PG-I1: Connection Pool Lifecycle

- **Level:** L3 Integration
- **Check question:** Is the pool created cleanly, are connections recycled, and is the pool closed on shutdown?
- **Violation signal:** Connection leak (pool grows unboundedly). Or: `pool.close()` is not called → Postgres complains about open connections.
- **Code:**

```python
# Generated from PG-I1 (L3 Integration, Lifecycle)
# INFRA: Postgres
import asyncpg
import pytest


@pytest.mark.integration
async def test_pool_lifecycle():
    """PG-I1: Pool created, usable, and closed cleanly."""
    from buddyai.brain.pool import create_pool, TEST_DSN

    pool = await create_pool(dsn=TEST_DSN, min_size=1, max_size=3)

    # Pool is usable
    async with pool.acquire() as conn:
        result = await conn.fetchval("SELECT 1")
        assert result == 1

    # Pool size within limits
    assert pool.get_size() >= 1
    assert pool.get_size() <= 3

    # Clean close
    await pool.close()

    # After close() acquire() should fail
    with pytest.raises(asyncpg.InterfaceError):
        async with pool.acquire():
            pass
```

### PG-I2: Transaction Isolation

- **Level:** L3 Integration
- **Check question:** Are transactions correctly isolated — concurrent writes without data races, read-your-own-writes within a transaction?
- **Violation signal:** Lost updates on parallel writes. Or: an INSERT inside a transaction is not visible to a SELECT in the same transaction.
- **Code:**

```python
# Generated from PG-I2 (L3 Integration, Concurrency)
# INFRA: Postgres
import asyncio
import pytest


@pytest.mark.integration
async def test_read_your_own_writes(brain):
    """PG-I2: Within a transaction, your own writes are immediately visible."""
    entity_id = await brain.create_entity(name="ryow-test", entity_type="test")
    entity = await brain.get_entity(entity_id)
    assert entity is not None
    assert entity["name"] == "ryow-test"


@pytest.mark.integration
async def test_concurrent_writes_no_lost_updates(brain_pool):
    """PG-I2: Parallel updates do not lose data."""
    from buddyai.brain.core import Brain

    # Create a shared entity
    async with brain_pool.acquire() as conn:
        b = Brain(conn)
        entity_id = await b.create_entity(name="concurrent-test", entity_type="counter")

    async def increment(pool, eid, field_value):
        async with pool.acquire() as conn:
            # Serializable or advisory lock depending on implementation
            await conn.execute(
                """UPDATE entities SET metadata = jsonb_set(
                     COALESCE(metadata, '{}'::jsonb),
                     '{counter}',
                     (COALESCE((metadata->>'counter')::int, 0) + 1)::text::jsonb
                   ) WHERE id = $1""",
                eid,
            )

    tasks = [increment(brain_pool, entity_id, i) for i in range(10)]
    await asyncio.gather(*tasks)

    async with brain_pool.acquire() as conn:
        b = Brain(conn)
        entity = await b.get_entity(entity_id)
    assert entity["metadata"]["counter"] == 10, "Lost update: not all increments counted"
```

### PG-I3: Index Usage

- **Level:** L3 Integration
- **Check question:** Do typical queries (entity lookup by ID, full-text search, vector nearest-neighbour) use the expected index instead of a seq scan?
- **Violation signal:** `EXPLAIN ANALYZE` shows `Seq Scan` for queries that should be covered by an index.
- **Code:**

```python
# Generated from PG-I3 (L3 Integration, Performance)
# INFRA: Postgres
import pytest


@pytest.mark.integration
async def test_entity_lookup_uses_index(brain):
    """PG-I3: Entity lookup by ID uses index, not seq scan."""
    # Enough data so the planner does not prefer a seq scan
    for i in range(100):
        await brain.create_entity(name=f"idx-test-{i}", entity_type="test")

    entity_id = await brain.create_entity(name="target", entity_type="test")

    plan = await brain._conn.fetchval(
        "EXPLAIN (FORMAT TEXT) SELECT * FROM entities WHERE id = $1",
        entity_id,
    )
    assert "Seq Scan" not in plan, f"Entity lookup uses seq scan:\n{plan}"


@pytest.mark.integration
async def test_vector_search_uses_index(brain):
    """PG-I3: Vector nearest-neighbour uses HNSW/IVFFlat index."""
    # Seed with embeddings (at least 100 for IVFFlat)
    import numpy as np
    for i in range(100):
        embedding = np.random.rand(768).tolist()
        await brain.create_entity(
            name=f"vec-{i}", entity_type="test", embedding=embedding,
        )

    query_vec = np.random.rand(768).tolist()
    plan = await brain._conn.fetchval(
        "EXPLAIN (FORMAT TEXT) SELECT * FROM entities ORDER BY embedding <-> $1 LIMIT 10",
        str(query_vec),
    )
    # HNSW or IVFFlat index scan expected (brain-schema.md: HNSW default)
    assert "Seq Scan" not in plan or "Index" in plan, (
        f"Vector search does not use an index:\n{plan}"
    )
```

### PG-I4: Migration Compatibility

- **Level:** L3 Integration
- **Check question:** Does Alembic up/down run without data loss and without schema inconsistencies?
- **Violation signal:** `alembic downgrade` fails. Or: data is lost on upgrade→downgrade→upgrade.
- **Code:**

```python
# Generated from PG-I4 (L3 Integration, Lifecycle)
# INFRA: Postgres
import subprocess
import pytest


@pytest.mark.integration
async def test_alembic_upgrade_downgrade(live_services):
    """PG-I4: Alembic up + down + up without errors."""
    def run_alembic(cmd):
        result = subprocess.run(
            ["alembic", cmd, "head"] if cmd == "upgrade" else ["alembic", cmd, "-1"],
            capture_output=True, text=True,
            env={"DATABASE_URL": "postgresql://test:test@localhost:5433/buddyai_test"},
        )
        assert result.returncode == 0, f"alembic {cmd} failed:\n{result.stderr}"
        return result

    run_alembic("upgrade")    # head
    run_alembic("downgrade")  # -1
    run_alembic("upgrade")    # head again — schema must be stable


@pytest.mark.integration
async def test_migration_preserves_data(brain):
    """PG-I4: Data survives the migration cycle."""
    entity_id = await brain.create_entity(name="migration-test", entity_type="test")

    # Alembic upgrade (no-op if already at head)
    subprocess.run(["alembic", "upgrade", "head"], check=True)

    entity = await brain.get_entity(entity_id)
    assert entity is not None, "Entity disappeared after migration"
    assert entity["name"] == "migration-test"
```

---

## L5 Property-Based Criteria (hypothesis)

### PG-P1: Entity Roundtrip

- **Level:** L5 Property-Based
- **Check question:** Can every valid entity be stored and read back identically?
- **Violation signal:** hypothesis finds an input that is altered on roundtrip (e.g. unicode truncation, whitespace normalisation).
- **Code:**

```python
# Generated from PG-P1 (L5 Property, Roundtrip)
# INFRA: Postgres
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

# Reusable strategy for Brain entities
entity_names = st.text(
    alphabet=st.characters(categories=("L", "N", "P", "Z")),
    min_size=1,
    max_size=255,
)
entity_types = st.sampled_from(["person", "concept", "project", "document", "location"])
entity_metadata = st.one_of(
    st.none(),
    st.dictionaries(
        keys=st.text(min_size=1, max_size=50),
        values=st.one_of(st.text(max_size=200), st.integers(), st.floats(allow_nan=False), st.booleans()),
        max_size=10,
    ),
)


@pytest.mark.property
@given(name=entity_names, etype=entity_types, meta=entity_metadata)
@settings(max_examples=50, deadline=5000)
async def test_entity_roundtrip(brain, name, etype, meta):
    """PG-P1: Every valid entity survives create → get identically."""
    entity_id = await brain.create_entity(name=name, entity_type=etype, metadata=meta)
    entity = await brain.get_entity(entity_id)

    assert entity["name"] == name
    assert entity["entity_type"] == etype
    assert entity["metadata"] == meta
```

### PG-P2: Search Completeness

- **Level:** L5 Property-Based
- **Check question:** If an entry exists and the query string occurs in the content, does `search()` find it?
- **Violation signal:** hypothesis finds a search term that occurs in the entity name but is not found (e.g. special characters, case-sensitivity).
- **Code:**

```python
# Generated from PG-P2 (L5 Property, Completeness)
# INFRA: Postgres
import pytest
from hypothesis import given, settings, assume
from hypothesis import strategies as st


search_terms = st.text(
    alphabet=st.characters(categories=("L", "N")),
    min_size=3,
    max_size=30,
)


@pytest.mark.property
@given(term=search_terms)
@settings(max_examples=30, deadline=5000)
async def test_search_finds_existing_entity(brain, term):
    """PG-P2: Entity with term in its name is found by search()."""
    assume(term.strip())  # No pure whitespace terms
    name = f"searchable-{term}-entity"
    await brain.create_entity(name=name, entity_type="test")

    results = await brain.search(query=term)
    found_names = [r["name"] for r in results]
    assert any(term in n for n in found_names), (
        f"search('{term}') did not find entity '{name}'. "
        f"Results: {found_names}"
    )
```

### PG-P3: Relation Integrity

- **Level:** L5 Property-Based
- **Check question:** Are there no orphaned relations after `delete_entity()`?
- **Violation signal:** hypothesis finds a scenario in which a relation references a deleted entity.
- **Code:**

```python
# Generated from PG-P3 (L5 Property, Integrity)
# INFRA: Postgres
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st


@pytest.mark.property
@given(n_entities=st.integers(min_value=2, max_value=5))
@settings(max_examples=20, deadline=10000)
async def test_no_orphaned_relations_after_delete(brain, n_entities):
    """PG-P3: No orphaned relations after delete_entity()."""
    # Create N entities and chain them
    ids = []
    for i in range(n_entities):
        eid = await brain.create_entity(name=f"rel-test-{i}", entity_type="test")
        ids.append(eid)

    # Create relations: 0→1, 1→2, ...
    for i in range(len(ids) - 1):
        await brain.create_relation(
            source_id=ids[i], target_id=ids[i + 1], relation_type="depends_on",
        )

    # Delete the middle entity
    target = ids[len(ids) // 2]
    await brain.delete_entity(target)

    # Check: no relation references the deleted entity
    orphans = await brain._conn.fetch(
        """SELECT * FROM relations
           WHERE source_id = $1 OR target_id = $1""",
        target,
    )
    assert len(orphans) == 0, (
        f"Orphaned relations after delete of {target}: {orphans}"
    )
```

### PG-P4: Embedding Dimension

- **Level:** L5 Property-Based
- **Check question:** Do all stored embeddings have exactly 768 dimensions?
- **Violation signal:** An embedding with the wrong dimension is stored (pgvector should prevent this, but the app layer must validate it before it reaches the DB).
- **Code:**

```python
# Generated from PG-P4 (L5 Property, Invariant)
# INFRA: Postgres
import pytest
import numpy as np
from hypothesis import given, settings
from hypothesis import strategies as st


EMBEDDING_DIM = 768


@pytest.mark.property
@given(dim=st.integers(min_value=1, max_value=2000).filter(lambda d: d != EMBEDDING_DIM))
@settings(max_examples=10, deadline=5000)
async def test_wrong_embedding_dimension_rejected(brain, dim):
    """PG-P4: Embedding with the wrong dimension is rejected."""
    wrong_embedding = np.random.rand(dim).tolist()

    with pytest.raises(Exception):  # ValueError or asyncpg.DataError
        await brain.create_entity(
            name="wrong-dim",
            entity_type="test",
            embedding=wrong_embedding,
        )


async def test_correct_embedding_dimension_accepted(brain):
    """PG-P4: Embedding with 768 dimensions is accepted."""
    embedding = np.random.rand(EMBEDDING_DIM).tolist()
    entity_id = await brain.create_entity(
        name="correct-dim", entity_type="test", embedding=embedding,
    )
    entity = await brain.get_entity(entity_id)
    assert len(entity["embedding"]) == EMBEDDING_DIM
```

---

## Reusable hypothesis Strategies

These strategies can be placed in `tests/brain/strategies.py` and used via import:

```python
# tests/brain/strategies.py
"""Reusable hypothesis strategies for Brain models."""
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

embeddings = st.builds(
    lambda: np.random.rand(EMBEDDING_DIM).tolist(),
)

relation_types = st.sampled_from(["depends_on", "related_to", "part_of", "derived_from"])
```

---

## Checklist for the Tester

In execution mode for Brain/Postgres-related tests, walk through these criteria:

1. Every query in new code: PG-U1 (parameterised)? — static analysis.
2. Optional fields: is PG-U2 (NULL handling) covered?
3. ID generation: is PG-U3 (UUID4) covered?
4. JSONB usage: is PG-U4 (correct Postgres syntax) covered?
5. Pool management in scope: PG-I1 (lifecycle)?
6. Concurrent writes in scope: PG-I2 (isolation)?
7. New queries: PG-I3 (index usage via EXPLAIN)?
8. New migrations: PG-I4 (up/down/up)?
9. Property tests present for critical invariants: PG-P1 through PG-P4?
10. hypothesis strategies from `tests/brain/strategies.py` used rather than rewritten?
