# Security and hardening — review

Step-loaded unit of `skills/security_and_hardening/SKILL.md`. Read it when reviewing a change for security and before
calling security-relevant work done.

## Security review checklist

```markdown
### Authentication
- [ ] Passwords hashed with bcrypt / scrypt / argon2 (salt rounds >= 12)
- [ ] Session tokens httpOnly + secure + sameSite
- [ ] Login with rate limiting
- [ ] Password reset tokens expire

### Authorization
- [ ] Every endpoint checks user permissions
- [ ] Users access only their own resources
- [ ] Admin actions verify the admin role

### Input
- [ ] All user input validated at the boundary
- [ ] SQL / Cypher queries parameterized
- [ ] HTML output encoded / escaped

### Data
- [ ] No secrets in code or VCS
- [ ] Sensitive fields excluded from API responses
- [ ] PII encrypted at rest (when applicable)

### Infrastructure
- [ ] Security headers configured (CSP, HSTS, etc.)
- [ ] CORS restricted to known origins
- [ ] Dependencies checked for vulnerabilities
- [ ] Error messages don't expose internals
```

This section IS the required checklist. (A separate
`references/security-checklist.md` doesn't currently exist
— if the checklist's growth here gets unwieldy, it gets
extracted to `references/`. Until then: here.)

## Red flags

- Auth bypass defaults in local / dev mode
  (`if (process.env.NODE_ENV === 'development') skipAuth()`).
- Plaintext secret imports
  (`import { API_KEY } from './secrets'`) instead of
  env-var load.
- POST / PUT / PATCH endpoints without a CSRF token on
  cookie sessions.
- Wildcard CORS (`origin: '*'`) with `credentials: true`.
- Session tokens / auth tokens in `localStorage` /
  `sessionStorage`.
- Stack traces / internal errors in HTTP response body.
- Dependencies with `audit` HIGH / CRITICAL without a
  review date.
- Authorization derived implicitly from authentication
  (`if (req.user) ...` instead of
  `if (resource.ownerId === req.user.id)`).
- Spread- / rest-based "sanitization" (denylist omit)
  instead of allowlist pick.
- File uploads that only check the `mimetype` header, no
  magic-bytes check.

## Common rationalizations

| Rationalization | Reality |
|---|---|
| "Internal tool, security doesn't matter" | Internal tools get compromised. Attackers aim at the weakest link. |
| "Security later" | Retrofitting is 10x harder. Bake it in now. |
| "Nobody would exploit that" | Automated scanners find it. Security by obscurity != security. |
| "The framework handles that" | Frameworks are tools, not guarantees — you must use them correctly. |
| "Just a prototype" | Prototypes become production. Security habits from day 1. |

## Anti-patterns

- **NOT** trust client-side validation as a security
  boundary. **INSTEAD** the server boundary always
  validates too; client validation is UX convenience.
  Because: client code can be modified arbitrarily.
- **NOT** store plaintext passwords or hash with MD5 /
  SHA-1. **INSTEAD** bcrypt / scrypt / argon2 with salt
  rounds >= 12. Because: GPU cracking makes weak hashes
  breakable in hours.
- **NOT** auth tokens in localStorage / sessionStorage.
  **INSTEAD** httpOnly cookies. Because: XSS attacks read
  localStorage trivially; httpOnly closes that vector.
- **NOT** expose stack traces or internal errors to users.
  **INSTEAD** generic error message + internal logs.
  Because: stack traces leak the tech stack, library
  versions, internal paths — recon material for
  attackers.
- **NOT** wildcard CORS (`*`) in production. **INSTEAD**
  explicit origin allowlist via env var. Because: a
  wildcard allows any foreign origin to make requests
  with cookies.
- **NOT** secrets in code, history, or logs. **INSTEAD**
  `.env` files (gitignored) + pre-commit check + a
  secret-scanning tool. Because: once in git history =
  forever public; force-push and rotation needed.
- **NOT** derive authorization implicitly from
  authentication. **INSTEAD** explicit
  `if (resource.ownerId !== req.user.id) return 403`.
  Because: an authenticated user != an authorized user;
  cross-user access bugs are classic broken-access-
  control findings.
- **NOT** ignore dependency-audit findings because
  "noisy". **INSTEAD** decision tree (`secrets-and-supply-chain.md`), explicitly
  deferred with a review date. Because: accumulated
  unaddressed findings = a known attack path with a
  roadmap.
