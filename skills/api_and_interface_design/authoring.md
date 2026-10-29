# API and interface design — authoring process

Step-loaded unit of `skills/api_and_interface_design/SKILL.md`. Read it before designing a new interface or changing
an existing public one, and before writing its contract.

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

Example pattern (`AppError` + `ErrorResponse`):

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
# Pydantic validation at the API boundary
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

**Recommendation for Python-backed APIs:** response fields
snake_case (Python-consistent); the frontend Zod schema maps
on receipt. The cardinal rule is to **stay consistent inside
the API** — pick one form and apply it everywhere.
