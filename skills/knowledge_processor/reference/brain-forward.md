# Forward compatibility (Brain)

Documents how this skill changes once the Brain is built (ARCH-009). No code — design intent.

## Forward-compatibility table

| Step | Pre-Brain (now) | Post-Brain |
|------|-----------------|------------|
| EXTRACT | LLM reads raw information | LLM + entity extraction pipeline (assertion-titled) |
| LOCATE | Navigation-guided file reading + grep | Graph traversal (SQL) + embedding search (pgvector) |
| ASSESS | LLM compares text against text | LLM compares against structured entities |
| ACT | Edit context files | Graph update (create/update/historicise) + context files |
| RECURSE | LLM traverses impact tree recursively over files | Graph traversal + LLM reasoning |
| Maturity | Implicit via position (history=seed, detail=sprout, overview=evergreen) | Explicit field `maturity: seed/sprout/evergreen`, promotion trigger |
| Entropy Audit | Boot cross-check, manual heuristic | Heartbeat + temporal queries (valid_until) |

## What changes

**IMPACT CHAIN → Brain invalidation mechanism:**
- LOCATE uses brain.search() (graph traversal + semantic search) instead of file grep
- ASSESS compares against structured Neo4j entities instead of free text
- ACT sets valid_until on existing relations on CONTRADICTS/OBSOLETES, creates new ones with valid_from
- RECURSE traverses the Neo4j graph instead of recursively reading files

**Dual write:** Brain first (SoT), then MD (cache). Dynamic MDs are kept fresh by the background curator (ARCH-010).

**SOURCE_REF dispatch → Cognee ECL:** the dispatcher routes to the Cognee ECL pipeline. Custom DataPoints control the ontology. Document pointer in Postgres is still written.

**LOCATE uses brain.search():** hybrid search (semantic + graph + fulltext) replaces navigation-guided file reading + grep. Graph traversal finds indirect impacts (2+ hops).

**mode=user-signal Post-Brain:** the pipeline is taken over by the user-model worker (`src/buddyai/workers/user_model_worker.py`). The dispatcher routes `user.signal` events to NATS, the worker processes asynchronously.

## Hybrid sync/async IMPACT CHAIN (Post-Brain)

Design decision: option C — critical path sync, RECURSE async.

| Step | Execution | Latency budget |
|------|-----------|----------------|
| EXTRACT | Synchronous (LLM call) | ~500ms-2s |
| LOCATE | Synchronous (brain.search()) | ~20-50ms |
| ASSESS | Synchronous (LLM call, produces narrative_fragment) | ~500ms-2s |
| ACT | Synchronous (Neo4j MERGE + Postgres embedding) | ~10-30ms |
| RECURSE | **Asynchronous** via NATS `brain.impact.indirect.{relation_id}` | unbounded, eventual consistency |

**Rationale:** direct impact (entity/relation + narrative_fragment) is persistent immediately (~50ms DB time). RECURSE (indirect impacts, 2+ hop graph traversal, potential further LLM calls) is the only unbounded-expensive part. Indirect impacts are by definition not immediately critical — eventual consistency is acceptable.

**Concurrency protection on rapid user inputs:**
- `narrative_fragments` is List<Map> instead of String — append semantics, no last-write-wins
- Atomic Cypher: `coalesce(r.narrative_fragments, []) + $new_fragment`
- NATS consumer with `max_ack_pending=1`: forces serial processing, guarantees ordering
- Day-N if throughput becomes a problem: migrate to application-level ordering (worker buffers per relation ID)
- Sync ACT + async RECURSE on the same relation: both append safely (no data loss)

**Day-N: fragment compaction:**
A periodic background job (APScheduler) condenses accumulated fragments via LLM into a consolidated fragment. Trigger: relation has > N fragments (e.g. 10). Analogous to the Entropy Audit, but at fragment level. No information loss — compaction only replaces the text list, episode references are preserved.

What changes:
- LOCATE uses Neo4j + pgvector instead of file grep
- IMPACT CHAIN uses spreading activation (edge decay) instead of 1-hop
- CONNECT uses embedding search + LLM assessment
- CONTRADICTS escalates to Buddy via NATS (`user.model.escalation`)
- Immediate-stable is Python code (`pre_classify()`), not an LLM prompt
- Intensity is computed mathematically (ACT-R), no LLM

What stays identical:
- Facet classification (identical taxonomy)
- Immediate-stable rule (identical logic, different implementation)
- Decay thresholds (identical matrix)
- CONTRADICTS: Buddy always asks (T1: synchronous, T2: via escalation)

Reference: `docs/specs/user-model-t2.md`

## What does not change

- **EXTRACT → IMPACT CHAIN → SIGNAL CHECK pipeline** — same process, different data basis
- **Dispatcher integration** — knowledge_processor is still invoked for FACT, USER, CONNECTION
- **Proportionality** — still applies
- **MUST NOT: dispatcher never writes directly into context/** — always via knowledge_processor (exception: decisions.md)
- **Maturity promotion** — becomes an explicit field instead of implicit position, same logic
- **Delta check** — before every write, whether MD or Brain entity

Overall model: `docs/specs/knowledge-architecture.md`. Schema: `docs/specs/brain-schema.md`.
