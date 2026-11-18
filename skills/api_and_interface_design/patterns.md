# API and interface design — REST, SSE and Pydantic patterns

Step-loaded unit of `skills/api_and_interface_design/SKILL.md`. Read it when defining REST endpoints, an SSE event
stream or Pydantic models, and before changing a model that feeds the schema pipeline.

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

## SSE patterns

Server-Sent-Events follow analogous discipline:

```python
# Event schema explicit (analogous to a REST response schema)
class ContentChunk(BaseModel):
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
StreamEvent = ContentChunk | DoneEvent | ErrorEvent
```

**SSE obligations:**
- Each event type explicitly defined (no anonymous dict).
- ErrorEvent as a discriminated variant (don't raise after
  a StreamingResponse start — errors past the
  StreamingResponse boundary belong to SSE, not HTTP).
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

### Schema pipeline (Pydantic → OpenAPI → Zod)

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
