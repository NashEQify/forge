---
name: api-and-interface-design
description: >
  API and interface design discipline. Hyrum's law +
  one-version rule + contract-first + validate-at-boundaries
  + prefer-addition-over-modification + predictable-naming.
  Use when designing new APIs, module boundaries, type
  contracts between modules, REST / SSE endpoints, schema
  pipeline boundaries.
status: active
invocation:
  primary: user-facing
  secondary: [workflow-step, sub-skill]
  trigger_patterns:
    - "design API"
    - "interface design"
    - "module boundary"
    - "API contract"
    - "endpoint design"
    - "schema pipeline"
disable-model-invocation: false
---

# Skill: api-and-interface-design

## Purpose

Design stable, well-documented interfaces that are
hard-to-misuse. Good interfaces make the right thing easy and
the wrong thing hard. Applies to REST APIs, SSE streams,
module boundaries, Pydantic models, component props, and any
surface where one piece of code talks to another.

Complementary to `agents/code-api-contract.md` (persona
reviewer for existing APIs) — this skill is the **authoring
discipline** for new interfaces; the persona is the review
counterpart.

Absorbs the existing schema-pipeline reality (Pydantic →
OpenAPI → Zod) as a concrete pattern.

## Source

Lifted from `github.com/addyosmani/agent-skills`
(`skills/api-and-interface-design/SKILL.md`, 2026-04-30).
**Adapted** to the BuddyAI / forge reality:
- TypeScript examples translated to Pydantic + FastAPI.
- JSON-body validation: Pydantic `extra="forbid"` +
  `model_validate()`.
- Error handling: AppError + ErrorResponse (Task 265).
- SSE as the streaming counterpart to REST
  (BuddyResponseChunk / DoneEvent / ErrorEvent).
- Schema pipeline: Pydantic → OpenAPI → Zod (frontend sync).

## Standalone

Distinct from:
- `agents/code-api-contract.md` (persona) — review role for
  existing APIs in code_review_board L2. This skill is the
  authoring stage.
- `skills/spec_authoring/SKILL.md` — general spec writing.
  This skill specializes in interface design within the
  spec.
- `skills/code_review_board/SKILL.md` — the whole code
  review board. This skill feeds the board with consistently
  designed APIs.

What only this skill delivers:
- Hyrum's law as an explicit authoring requirement (hidden
  behaviour as a de-facto contract).
- One-version rule (diamond-dependency avoidance).
- 5 authoring requirements (contract-first / consistent
  errors / validate-at-boundaries / prefer-addition /
  predictable-naming).
- REST + SSE patterns specifically.
- Discriminated unions / input-output separation /
  branded types for Pydantic.

## When to call

- Designing new API endpoints (REST or SSE).
- Defining module boundaries or contracts between teams.
- Creating Pydantic model schemas.
- Designing a database schema that informs the API shape.
- Changing existing public interfaces (Hyrum's-law
  obligation).

### Do not call for

- Internal function signatures that are not a public API →
  `code-quality` (naming axis).
- DB schema without API implication →
  `agents/code-data.md` persona.
- Pre-existing endpoint bug fix → `fix` workflow + L1
  review.
- General spec writing → `spec_authoring`.

## Process

### Phase 1: internalize Hyrum's law (mandatory mindset)

> "With a sufficient number of users of an API, all
> observable behaviours of your system will be depended on
> by somebody, regardless of what you promise in the
> contract."

**Consequence for authoring:**
- **Be intentional about what you expose.** Every observable
  behaviour is a potential commitment.
- **Don't leak implementation details.** When users can
  observe it, they will depend on it.
- **Plan for deprecation at design time.** Cross-ref
  `deprecation_and_migration`.
- **Tests aren't enough.** Even with perfect contract tests
  Hyrum's-law reality breaks: "safe" changes break users
  who consume undocumented behaviour.

### Phase 2: one-version rule

Avoid forcing consumers into a multi-version choice. Diamond
dependencies arise when different consumers need different
versions.

**Authoring discipline:** design for a world where only **one
version** exists at a time. **Extend** instead of **fork**.
Cross-ref `deprecation_and_migration` for the sunset path on
incompatibilities.

### Phase 3: contract-first (authoring obligation)

Define the interface BEFORE the implementation. The contract
IS the spec — implementation follows.

```python
# Pydantic contract first
from pydantic import BaseModel, Field
from datetime import datetime

class CreateTaskInput(BaseModel):
    """User-supplied input for task creation."""
    model_config = {"extra": "forbid"}  # MUST: no silent pass-through

    title: str = Field(..., min_length=1, max_length=200)
    description: str | None = Field(None, max_length=2000)


class Task(BaseModel):
    """Output: server-generated + user-supplied combined."""
    id: str
    title: str
    description: str | None
    created_at: datetime
    updated_at: datetime
    created_by: str  # UserId


class ListTasksParams(BaseModel):
    page: int = Field(1, ge=1)
    page_size: int = Field(20, ge=1, le=100)
    sort_by: str = Field("created_at", pattern="^(created_at|updated_at|title)$")


class PaginatedResult(BaseModel):
    data: list[Task]
    pagination: dict  # page / pageSize / totalItems / totalPages
```

### Phase 4: consistent error semantics

**One error strategy for every endpoint.** Mixed patterns
break consumer predictability.

BuddyAI pattern (Task 265):

```python
# AppError + ErrorResponse — one form for every error
class AppError(Exception):
    """Base app error with code + message + details."""
    def __init__(self, code: str, message: str, details: dict | None = None,
                 status_code: int = 500):
        self.code = code
        self.message = message
        self.details = details
        self.status_code = status_code


class ErrorResponse(BaseModel):
    error: dict  # {code, message, details}


# FastAPI error handler — uniform error shape
@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError):
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(error={
            "code": exc.code,
            "message": exc.message,
            "details": exc.details,
        }).model_dump(),
    )
```

**HTTP-status-code mapping:**

| Code | Meaning |
|---|---|
| 400 | Client sent invalid data (before validation) |
| 401 | Not authenticated |
| 403 | Authenticated but not authorized |
| 404 | Resource not found |
| 409 | Conflict (duplicate, version mismatch) |
| 422 | Validation failed (semantically invalid) |
| 500 | Server error (NEVER expose internals) |

**MUST NOT mix patterns:** when some endpoints
`raise HTTPException`, others `return None`, others
`return {"error": ...}` → consumers cannot predict. One
strategy + everywhere.

### Phase 5: validate-at-boundaries

Trust internal code. Validate **at system edges** where
external input enters:

```python
# BuddyAI pattern: Pydantic validation at the API boundary
@app.post("/api/tasks", response_model=Task, status_code=201)
async def create_task(
    input: CreateTaskInput,  # Pydantic validates AUTOMATICALLY
    user: User = Depends(resolve_user),  # auth boundary
) -> Task:
    # After validation: internal code trusts types
    return await task_service.create(input, user.id)
```

**Where validation belongs:**
- API route handler (user input).
- Form-submission handler (user input).
- External-service response parsing (third-party data —
  **always treat as untrusted**).
- Environment-variable loading (configuration).

**Where validation does NOT belong:**
- Between internal functions that share type contracts.
- In utility functions called by already-validated code.
- On data that just came out of your own DB (Pydantic models
  in the brain facade are fine).

> **Third-party API responses are untrusted data.** Validate
> shape + content before any logic / rendering / decision-
> making. A compromised or misbehaving external service can
> return unexpected types, malicious content, or
> instruction-like text.

### Phase 6: prefer-addition-over-modification

Extend interfaces without breaking existing consumers:

```python
# Good: add optional fields
class CreateTaskInput(BaseModel):
    model_config = {"extra": "forbid"}
    title: str
    description: str | None = None
    priority: Literal["low", "medium", "high"] | None = None  # added later, optional
    labels: list[str] | None = None  # added later, optional


# Bad: change existing field types or remove fields
class CreateTaskInput(BaseModel):
    title: str
    # description: str | None  # REMOVED — breaks existing consumers
    priority: int  # CHANGED from string — breaks existing consumers
```

**Removal / change path:** when actually needed → cross-ref
`deprecation_and_migration` for an orderly sunset.

### Phase 7: predictable naming

| Pattern | Convention | Example |
|---|---|---|
| REST endpoints | Plural nouns, no verbs | `GET /api/tasks`, `POST /api/tasks` |
| Query params | camelCase | `?sortBy=createdAt&pageSize=20` |
| Response fields | camelCase or snake_case (consistent in the API!) | `{ createdAt, updatedAt }` OR `{ created_at, updated_at }` |
| Boolean fields | `is_/has_/can_` prefix | `is_complete`, `has_attachments` |
| Enum values | UPPER_SNAKE | `"IN_PROGRESS"`, `"COMPLETED"` |

**BuddyAI convention:** response fields snake_case
(Python-consistent); the frontend Zod schema maps on
receipt. **Stay consistent inside the API.**

## REST API patterns

### Resource design

```
GET    /api/tasks              → list tasks (with query params for filtering)
POST   /api/tasks              → create task
GET    /api/tasks/{id}         → get a single task
PATCH  /api/tasks/{id}         → partial update (only provided fields)
DELETE /api/tasks/{id}         → idempotent delete

GET    /api/tasks/{id}/comments → list comments for a task (sub-resource)
POST   /api/tasks/{id}/comments → add a comment
```

### Pagination

Paginate list endpoints:

```python
class PaginatedResult(BaseModel, Generic[T]):
    data: list[T]
    pagination: PaginationMeta


class PaginationMeta(BaseModel):
    page: int
    page_size: int
    total_items: int
    total_pages: int
```

### Filtering via query params

```
GET /api/tasks?status=in_progress&assignee=user123&created_after=2026-01-01
```

### Partial updates (PATCH)

Accept partial objects — only update what's provided:

```python
class UpdateTaskInput(BaseModel):
    """All fields optional for a partial update."""
    model_config = {"extra": "forbid"}
    title: str | None = None
    description: str | None = None
    priority: Literal["low", "medium", "high"] | None = None
```

## SSE patterns (BuddyAI-specific)

Server-Sent-Events follow analogous discipline:

```python
# Event schema explicit (analogous to a REST response schema)
class BuddyResponseChunk(BaseModel):
    type: Literal["chunk"]
    content: str
    chunk_index: int


class DoneEvent(BaseModel):
    type: Literal["done"]
    total_chunks: int


class ErrorEvent(BaseModel):
    type: Literal["error"]
    code: str
    message: str


# The stream as a discriminated union
StreamEvent = BuddyResponseChunk | DoneEvent | ErrorEvent
```

**SSE obligations:**
- Each event type explicitly defined (no anonymous dict).
- ErrorEvent as a discriminated variant (don't raise after
  a StreamingResponse start — see code-adversary
  BuddyAI-specific).
- DoneEvent as the terminal sentinel.
- The client recognizes the event type via the `type` field
  discriminator.

## Pydantic patterns

### Discriminated unions for variants

```python
from typing import Literal, Annotated
from pydantic import BaseModel, Field

# Each variant is explicit
class PendingStatus(BaseModel):
    type: Literal["pending"]


class InProgressStatus(BaseModel):
    type: Literal["in_progress"]
    assignee: str
    started_at: datetime


class CompletedStatus(BaseModel):
    type: Literal["completed"]
    completed_at: datetime
    completed_by: str


TaskStatus = Annotated[
    PendingStatus | InProgressStatus | CompletedStatus,
    Field(discriminator="type"),
]


# Consumer gets type narrowing via match
def get_status_label(status: TaskStatus) -> str:
    match status:
        case PendingStatus():
            return "Pending"
        case InProgressStatus(assignee=name):
            return f"In progress ({name})"
        case CompletedStatus(completed_at=ts):
            return f"Done at {ts}"
```

### Input / output separation

```python
# Input: what the caller provides
class CreateTaskInput(BaseModel):
    model_config = {"extra": "forbid"}
    title: str
    description: str | None = None


# Output: what the system returns (incl. server-generated fields)
class Task(BaseModel):
    id: str
    title: str
    description: str | None
    created_at: datetime
    updated_at: datetime
    created_by: str
```

### Branded types for IDs (NewType pattern)

```python
from typing import NewType

TaskId = NewType("TaskId", str)
UserId = NewType("UserId", str)

# Prevents accidental mismatch
def get_task(id: TaskId) -> Task: ...
```

### Schema pipeline (BuddyAI-specific)

Pydantic models are SoT. Pipeline:

```
1. Pydantic models (backend SoT)
   ↓
2. FastAPI auto-generated OpenAPI schema
   ↓
3. zod schema (frontend, via openapi-zod-client or equivalent)
   ↓
4. TypeScript types for React code
```

**Discipline:** when a backend Pydantic model changes →
regenerate OpenAPI → update Zod schema → frontend code
changes follow. **Single source of truth is Pydantic.**
Cross-ref `agents/code-api-contract.md` persona for the
review obligation across the whole pipeline.

## Red flags

- Endpoints that return different shapes depending on
  conditions.
- Inconsistent error formats across endpoints (some
  `raise HTTPException`, some AppError, some return None).
- Validation scattered in the internal code instead of at
  boundaries.
- Breaking changes to existing fields (type changes,
  removals).
- List endpoints without pagination.
- Verbs in REST URLs (`/api/createTask`, `/api/getUsers`).
- Third-party API responses without validation.
- `extra="ignore"` (default) instead of `extra="forbid"` on
  public request models.
- SSE events without an explicit event schema.
- StreamingResponse errors thrown as HTTPException (too
  late).

## Common rationalizations

| Rationalization | Reality |
|---|---|
| "We document the API later" | The Pydantic models ARE the documentation. Define them first. |
| "We don't need pagination yet" | As soon as someone has 100+ items you'll need it. Add it from the start. |
| "PATCH is complicated, let's use PUT" | PUT requires the full object every time. PATCH is what clients actually want. |
| "We version the API when needed" | Breaking changes without versioning break consumers. Design for extension from the start. |
| "Nobody uses the undocumented behaviour" | Hyrum's law: if it's observable, somebody depends on it. Treat every public behaviour as a commitment. |
| "We can just maintain two versions" | Multi-version maintenance multiplies cost and creates diamond dependencies. Cross-ref the one-version rule. |
| "Internal APIs don't need contracts" | Internal consumers are also consumers. Contracts prevent coupling and enable parallel work. |
| "extra=ignore is the default; that's fine" | Silent pass-through. Unknown fields are NOT recognized → drift. **extra=forbid** on public request models. |

## Contract

### INPUT
- **Required:** use case described (which resource, which
  operations).
- **Required:** consumer identified (frontend React,
  internal module, external API).
- **Optional:** existing schema-pipeline context (Pydantic
  models present?).
- **Context:** `framework/spec-engineering.md` 5 primitives,
  `agents/code-api-contract.md` persona,
  `skills/code_review_board/SKILL.md` (downstream review).

### OUTPUT
**DELIVERS:**
- Pydantic model schemas (input + output + error).
- REST / SSE endpoint definitions with status-code mapping.
- Pagination schema for list endpoints.
- Discriminated union for variants.
- Naming convention applied.
- Hyrum's-law considerations documented (which behaviours
  expose? which internal?).

**DOES NOT DELIVER:**
- No implementation logic — contract-first; implementation
  follows separately.
- No database schema — `agents/code-data.md` persona /
  spec authoring.
- No frontend code — the schema pipeline produces Zod;
  frontend code follows separately.

**ENABLES:**
- A stable public API with clear boundaries.
- A backward-compatible extension path.
- Schema-pipeline consistency (Pydantic → OpenAPI → Zod).
- code-api-contract persona can review consistently.

### DONE
- Every endpoint has typed input + output schemas.
- Error responses follow one consistent form (AppError +
  ErrorResponse).
- Validation only at system boundaries.
- List endpoints support pagination.
- New fields are additive + optional (backward compatible).
- Naming follows consistent conventions across every
  endpoint.
- API doc or types committed with the implementation.
- SSE events explicitly defined (when applicable).

### FAIL
- **Retry:** schema inconsistency detected → fix, then
  re-review.
- **Escalate:** Hyrum's-law consequence unclear →
  solution-expert or council for an architectural decision.
- **Abort:** replacement not designed but the old API
  should be deprecated → build the replacement first, then
  deprecate (cross-ref `deprecation_and_migration`).

## See also

- `agents/code-api-contract.md` — persona reviewer
  (counterpart to this skill).
- `skills/deprecation_and_migration/SKILL.md` — when a
  breaking change is needed.
- `skills/code_review_board/SKILL.md` — downstream review
  of the API implementation.
- `framework/spec-engineering.md` — 5 primitives (spec
  writing); applies to API specs.
- `skills/spec_authoring/SKILL.md` — when an API is part
  of a larger spec.
