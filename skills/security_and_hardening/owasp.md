# Security and hardening — OWASP Top 10 prevention

Step-loaded unit of `skills/security_and_hardening/SKILL.md`. Read it when writing or reviewing code that touches
queries or commands, authentication or password storage, rendered user content, access control, security
configuration or sensitive data.

## OWASP Top 10 prevention

### 1. Injection (SQL, NoSQL, OS command, LDAP, Cypher)

```typescript
// BAD — string concat
const query = `SELECT * FROM users WHERE id = '${userId}'`;

// GOOD — parameterized
const user = await db.query('SELECT * FROM users WHERE id = $1', [userId]);

// GOOD — ORM with parameterized
const user = await prisma.user.findUnique({ where: { id: userId } });
```

```python
# Python equivalent
# BAD
cursor.execute(f"SELECT * FROM users WHERE id = '{user_id}'")

# GOOD
cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
```

### 2. Broken authentication

#### Password-hashing thresholds (algorithm-specific, 2026 floor)

| Algorithm | Parameter | 2026 minimum | Note |
|---|---|---|---|
| **argon2id** *(preferred)* | `m=64MiB t=3 p=4` | OWASP recommended | Memory-hard, side-channel resistant. Default for new code. |
| argon2id (low-mem) | `m=19MiB t=2 p=1` | OWASP min (constrained envs) | Mobile / edge. |
| bcrypt | `cost=12` | 2026 floor (was 2018) | 72-byte limit (longer passwords get truncated). Re-tune obligation every 2 years. |
| scrypt | `N=2^17 r=8 p=1` | OWASP min | Memory-hard. |

**IMPORTANT:** "salt rounds" is **bcrypt-specific**. argon2
has `memory / iterations / parallelism`; scrypt has
`N / r / p`. Algorithm switch without parameter translation
= weaker than the default. Re-tune at least every 2 years
against current hardware (CPU / GPU / ASIC availability).

```typescript
// Preferred 2026 — argon2id
import { hash, verify, argon2id } from 'argon2';
const hashed = await hash(plaintext, {
  type: argon2id,
  memoryCost: 65536,   // 64 MiB
  timeCost: 3,
  parallelism: 4,
});
const isValid = await verify(hashed, plaintext);

// Legacy / interoperability — bcrypt
import { hash as bcryptHash, compare } from 'bcrypt';
const COST = 12;  // 2026 floor; re-tune every 2 years
// Note: bcrypt truncates passwords > 72 bytes silently.
// Pre-hash with SHA-256 if long passwords are allowed.
const hashed2 = await bcryptHash(plaintext, COST);
const isValid2 = await compare(plaintext, hashed2);

// Sessions
app.use(session({
  secret: process.env.SESSION_SECRET,
  resave: false,
  saveUninitialized: false,
  cookie: {
    httpOnly: true,
    secure: true,
    sameSite: 'lax',  // closes cross-site CSRF (different origin) but NOT
                      // sub-domain CSRF (a.example.com -> b.example.com).
                      // For multiple sub-domains: also CSRF token (below).
    maxAge: 24 * 60 * 60 * 1000,
  },
}));

// CSRF token for state-mutating routes (POST/PUT/PATCH/DELETE)
// — required when sub-domain architecture OR sameSite: 'none'.
import csurf from 'csurf';
app.use(csurf({ cookie: { httpOnly: true, secure: true, sameSite: 'lax' } }));

// Per mutating route: req.csrfToken() in the form field _csrf or header X-CSRF-Token,
// the csurf middleware verifies. On mismatch -> 403.
//
// SameSite=Lax alone prevents classic cross-site CSRF, but:
// (a) GET requests are not protected (should be read-only, but apps
//     misuse GET for state changes — anti-pattern itself).
// (b) Sub-domains share cookies with sameSite=Lax — XSS on one sub-domain
//     leaks the session to all. On a multi-sub-domain setup: token-based.
```

### 3. Cross-site scripting (XSS)

```typescript
// BAD
element.innerHTML = userInput;

// GOOD — React auto-escaping
return <div>{userInput}</div>;

// GOOD — sanitize when HTML is needed
import DOMPurify from 'dompurify';
const clean = DOMPurify.sanitize(userInput);
```

### 4. Broken access control

```typescript
// Authorization check IN ADDITION to authentication.
// Plus: NULL check + 404-instead-of-403 for anti-enumeration.
app.patch('/api/tasks/:id', authenticate, async (req, res) => {
  const task = await taskService.findById(req.params.id);

  // not-found: 404 (no reveal that the ID exists)
  if (!task) {
    return res.status(404).json({
      error: { code: 'NOT_FOUND', message: 'Resource not found' }
    });
  }

  // not-yours: ALSO 404 (anti-enumeration: 403 reveals "exists, belongs to someone else")
  if (task.ownerId !== req.user.id) {
    return res.status(404).json({
      error: { code: 'NOT_FOUND', message: 'Resource not found' }
    });
  }

  return res.json(await taskService.update(req.params.id, req.body));
});
```

**Anti-enumeration:** 403 for "exists but not yours" reveals
that the resource ID is valid — an attacker can enumerate
the ID space via the 403 / 404 response diff. 404 for both
closes that vector.

### 5. Security misconfiguration

```typescript
import helmet from 'helmet';
app.use(helmet());

app.use(helmet.contentSecurityPolicy({
  directives: {
    defaultSrc: ["'self'"],
    scriptSrc: ["'self'"],
    styleSrc: ["'self'", "'unsafe-inline'"],
    imgSrc: ["'self'", 'data:', 'https:'],
    connectSrc: ["'self'"],
  },
}));

// CORS — fail-closed (consistent with the STRIPE_API_KEY pattern below).
// Env-var miss in prod (typo, manifest drift) OTHERWISE silently falls back
// to localhost -> sidecar/pod localhost gets authenticated.
const allowedOrigins = process.env.ALLOWED_ORIGINS?.split(',').filter(Boolean);
if (!allowedOrigins || allowedOrigins.length === 0) {
  throw new Error('ALLOWED_ORIGINS not configured (fail-closed)');
}
app.use(cors({
  origin: allowedOrigins,
  credentials: true,
}));
```

### 7-10. Other OWASP Top 10 (short form)

- **A04 Insecure design** — threat model BEFORE
  implementation. "Who is the attacker, what are we
  protecting, what are the trust boundaries?" Pre-build,
  not post-hoc.
- **A08 Software and data integrity failures** —
  dependencies pinned (lockfile committed),
  Subresource-Integrity (SRI) on external scripts, signed
  releases on critical software (sigstore / cosign), CI
  pipeline integrity (no untrusted actions).
- **A09 Security logging failures** — security-relevant
  events (login success / failure, privilege escalation,
  auth-token rotation, admin actions) MUST be logged.
  Plus: logs centralized + tamper-resistant (append-only
  sink). Plus: alert triggers for abnormal patterns.
- **A10 Server-side request forgery (SSRF)** — don't fetch
  user-controlled URLs directly. Allowlist permitted hosts;
  block internal IP ranges (10.x, 192.168.x, 127.x,
  169.254.x metadata); follow + re-validate redirects
  manually.

These four are less code-pattern-heavy (more architectural /
operational discipline) — execution context-dependent; the
threat model has to clarify the relevance per project.

### 6. Sensitive data exposure

```typescript
// BAD — denylist via spread-omit. Day X+90 someone adds mfaSecret or
// apiToken to UserRecord -> automatically exposed via spread to client.
// No compile error, no test fail.
function sanitizeUserBAD(user: UserRecord): PublicUser {
  const { passwordHash, resetToken, ...publicFields } = user;
  return publicFields;
}

// GOOD — allowlist via Pick. New UserRecord fields are by default
// NOT exposed. The schema stays explicit + compile-checked when adding.
type PublicUser = Pick<UserRecord, 'id' | 'email' | 'displayName' | 'createdAt'>;
function sanitizeUser(user: UserRecord): PublicUser {
  return {
    id: user.id,
    email: user.email,
    displayName: user.displayName,
    createdAt: user.createdAt,
  };
}

// Plus: snapshot test for the API response field set:
// "API response contains EXACT { id, email, displayName, createdAt };
//  a new field in UserRecord -> test failure until explicitly added or excluded."

const API_KEY = process.env.STRIPE_API_KEY;
if (!API_KEY) throw new Error('STRIPE_API_KEY not configured');  // fail-closed
```
