# Security and hardening — input validation and rate limiting

Step-loaded unit of `skills/security_and_hardening/SKILL.md`. Read it when code accepts external input or file
uploads, or exposes an endpoint that needs rate limiting.

## Input-validation patterns

### Schema validation at boundaries

```typescript
import { z } from 'zod';

// IMPORTANT: Zod chain order. Transforms (.trim()) MUST come BEFORE
// validations (.min/.max), otherwise "   " (3 spaces) validates as
// valid (length=3 passes min(1)) -> trim empties -> empty title in DB.
const CreateTaskSchema = z.object({
  title: z.string().trim().min(1).max(200),  // trim FIRST, then length check
  description: z.string().trim().max(2000).optional(),
  priority: z.enum(['low', 'medium', 'high']).default('medium'),
  dueDate: z.string().datetime().optional(),
});

app.post('/api/tasks', async (req, res) => {
  const result = CreateTaskSchema.safeParse(req.body);
  if (!result.success) {
    return res.status(422).json({
      error: { code: 'VALIDATION_ERROR', details: result.error.flatten() },
    });
  }
  const task = await taskService.create(result.data);
  return res.status(201).json(task);
});
```

```python
# Pydantic equivalent (Python stack)
from pydantic import BaseModel, Field, field_validator

class CreateTaskRequest(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=2000)
    priority: Literal["low", "medium", "high"] = "medium"
    due_date: datetime | None = None

# Required validation at the FastAPI / Starlette boundary, not in the business logic
```

### File-upload safety

**Threat model:** `file.mimetype` comes from a
client-controlled Content-Type header. `evil.php.png` with
`Content-Type: image/png` blocks nothing. Mimetype trust is
**the problem**, not an edge case. A magic-bytes check is
required; mimetype as an additional sanity check.

```typescript
import { fileTypeFromBuffer } from 'file-type';

const ALLOWED_TYPES = ['image/jpeg', 'image/png', 'image/webp'];
const MAX_SIZE = 5 * 1024 * 1024;

async function validateUpload(file: UploadedFile) {
  // 1. Size check first (cheap)
  if (file.size > MAX_SIZE) throw new ValidationError('File too large (max 5MB)');

  // 2. Magic-bytes check (REQUIRED — mimetype header is client-controlled)
  const detected = await fileTypeFromBuffer(file.buffer);
  if (!detected || !ALLOWED_TYPES.includes(detected.mime)) {
    throw new ValidationError('File type not allowed (magic-bytes mismatch)');
  }

  // 3. Mimetype header as a sanity check (defence in depth)
  if (file.mimetype !== detected.mime) {
    throw new ValidationError('Mimetype header mismatch with file content');
  }

  // 4. SVG is dangerous (XSS via embedded <script>) — either exclude
  //    or DOMPurify strict, plus serve with Content-Disposition: attachment.
  // 5. Re-encode server-side (sharp / jimp for images) -> strips EXIF +
  //    makes embedded payloads harmless.
}
```

## Rate limiting

**IMPORTANT (multi-instance + proxy):**
- The `express-rate-limit` default store is **in-memory
  per-process**. K8s with 5 replicas → effective limit
  max*5. Multi-instance needs a **shared store** (Redis /
  Memcached).
- Without `app.set('trust proxy')` the counter key is the
  proxy IP → shared-counter DoS (everyone behind one load
  balancer shares the limit).

```typescript
import rateLimit from 'express-rate-limit';
import RedisStore from 'rate-limit-redis';
import { createClient } from 'redis';

// Required behind a reverse proxy / load balancer
app.set('trust proxy', 1);

const redis = createClient({ url: process.env.REDIS_URL });
await redis.connect();

app.use('/api/', rateLimit({
  windowMs: 15 * 60 * 1000,
  max: 100,
  standardHeaders: true,
  legacyHeaders: false,
  store: new RedisStore({ sendCommand: (...args) => redis.sendCommand(args) }),
}));

app.use('/api/auth/', rateLimit({
  windowMs: 15 * 60 * 1000,
  max: 10,  // stricter limit for auth endpoints
  store: new RedisStore({ sendCommand: (...args) => redis.sendCommand(args) }),
}));
```
