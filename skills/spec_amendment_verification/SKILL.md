---
name: spec-amendment-verification
description: >
  Read-only cross-spec verification after spec amendments.
  Checks whether the changes are consistent with the referenced
  specs.
status: active
verification_tier: 1
evidence_layout: per_finding
relevant_for: ["main-code-agent"]
invocation:
  primary: workflow-step
  secondary: [sub-skill]
disable-model-invocation: false
uses: [_protocols/evidence-pointer-schema]
---

# Skill: spec-amendment-verification

Read-only verification of spec amendments for cross-spec
consistency. Lightweight alternative to a board review. No fixes,
only findings.

---

## Trigger

Buddy spawns this skill when the MCA return contains
`SPEC_VERIFICATION: NEEDED`. Buddy does NOT spawn it on its own
judgment — the field in the return is the trigger.

## Input

Buddy passes:
- `changed_files`: list of changed spec files (from the MCA
  return).
- `change_summary`: per-item status from the MCA return (what was
  changed).
- `task_context`: task ID + wave / item reference (for
  traceability).

## Agent

Agent type: `reviewer` (read-only).

## Process

### 1. SCOPE (determined autonomously)

1. Read the SPEC-MAP (`docs/SPEC-MAP.md`).
2. For every changed spec: identify all consumers and producers
   from the SPEC-MAP.
3. Result: verification scope = changed specs + every directly
   referenced spec.

The agent determines scope ITSELF from the SPEC-MAP. Buddy / MCA
do not prescribe scope.

### 2. READ

Read all specs in the verification scope. For large specs: the
sections that contain cross-references (interface tables, import
lists, type definitions, NATS subject lists, consumer configs).

### 3. CHECK

For every changed spec, against every referenced spec:

| Check | What |
|-------|------|
| **Contract** | Signatures, return types, parameter lists consistent? |
| **Naming** | Same term = same spelling across all specs? |
| **Types** | Enum values, literal types, Pydantic models aligned? |
| **References** | Section numbers, line refs, version tags up to date? |
| **NATS** | Subject names, consumer configs, event payloads consistent? |
| **Locks** | Lock namespaces, advisory-lock signatures aligned? |

No completeness check on the spec itself — only cross-spec
consistency of the changed places.

### 4. RETURN

```
VERIFICATION-RESULT:
  Scope: [N changed specs, M cross-refs checked]
  Status: PASS | ISSUES_FOUND
  Issues:
    - [Spec-A §X ↔ Spec-B §Y]: description of the inconsistency
  Notes:
    - [observations that aren't issues but are relevant]
```

On `PASS`: Buddy logs and moves on.
On `ISSUES_FOUND`: Buddy escalates to the user with the issue
list. Buddy does NOT fix autonomously — the user decides whether
a fix is needed or acceptable.

## Contract

### INPUT
- **Required:** changed_files — list of changed spec files (from
  the MCA return).
- **Required:** change_summary — per-item status from the MCA
  return (what was changed).
- **Required:** task_context — task ID + wave / item reference
  (for traceability).
- **Required:** MCA return with `SPEC_VERIFICATION: NEEDED` —
  the only trigger.
- **Context:** `docs/specs/SPEC-MAP.md` — the agent determines
  the scope autonomously.

### OUTPUT
**DELIVERS:**
- Verification result: PASS or ISSUES_FOUND.
- Scope documentation (N changed specs, M cross-refs checked).
- On ISSUES_FOUND: issue list with spec references (Spec-A §X ↔
  Spec-B §Y).
- Notes: observations that are not issues but are relevant.

**DOES NOT DELIVER:**
- No fixes — read-only, only findings.
- No completeness check — only cross-spec consistency of the
  changed places.
- No pre-amendment review — this is POST-amendment.

**ENABLES:**
- Build verify: cross-spec consistency after spec amendments.
- User decision: issue list as a basis for the fix decision.
- Fix routing: issues show which consumer specs are affected.

### DONE
- SPEC-MAP read and the verification scope determined
  autonomously.
- All specs in scope read (interface points).
- 6 checks executed (contract, naming, types, references, NATS,
  locks).
- Verification result returned: PASS or ISSUES_FOUND.

### FAIL
- **Retry:** not foreseen — verification is a single pass.
- **Escalate:** ISSUES_FOUND → Buddy escalates to the user with
  the issue list (Buddy does NOT fix autonomously).
- **Abort:** not foreseen.

## Boundary

- No spec review → `spec_board` (amendment-verification is
  POST-amendment, not pre).
- No code review → `code_review_board`.
- No completeness check on a spec → `spec_board` §Completeness.
- No pre-amendment cross-spec coherence →
  `architecture_coherence_review`.
- Read-only: Buddy does not fix here, only verifies.

## Anti-patterns

- **NOT** run amendment verification without first listing all
  changed specs. INSTEAD: `git diff --stat` + an explicit scan
  for amendment markers. Because: missed amendments =
  unverified changes.
- **NOT** fix yourself when issues are found. INSTEAD escalate
  to the user with the issue list. Because: amendment
  verification is read-only — otherwise role conflict.
- **NOT** push cross-spec consistency off as "the board's job".
  INSTEAD check it here, that's the main purpose. Because: the
  board checks single-spec quality, not cross-spec effects of
  amendments.
