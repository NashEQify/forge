---
name: get-api-docs
description: >
  Fetch current API documentation for external libraries before
  coding against them. Prevents hallucinated parameters and stale
  interfaces.
status: active
relevant_for: ["main-code-agent"]
invocation:
  primary: workflow-step
  secondary: [user-facing, sub-skill]
disable-model-invocation: false
uses: []
---

# Skill: get-api-docs

## Purpose

Fetch current, curated API documentation for external libraries
before coding against them. Prevents hallucinated parameters and
stale interfaces.

## When to call

- Before the first API call against an external library in a
  task.
- On uncertainty whether a parameter / method is still current.
- When a reviewer reports an "API currency" finding.

## Prerequisite

```bash
chub --version 2>/dev/null || echo "MISSING: npm install -g @aisuite/chub"
```

## Workflow

### 1. Search

```bash
chub search "<library-name>"
```

Returns available doc IDs (format: `author/entry-name`).

### 2. Fetch the docs

```bash
chub get <id>                    # default (Python)
chub get <id> --lang js          # JavaScript variant
chub get <id> --version 2.0.0    # specific version
chub get <id> --full             # main + every reference
chub get <id> --file advanced    # specific reference file
```

Markdown is printed directly. Read it, then code.

### 3. Annotate (on discoveries)

```bash
chub annotate <id> "<precise note>"
```

Annotations show up on the next `chub get` automatically.
Cross-session persistent.

## Common doc IDs for the BuddyAI stack

```bash
chub search "fastapi"
chub search "nats"
chub search "pydantic"
chub search "postgres asyncpg"
chub search "litellm"
chub search "ollama"
chub search "apscheduler"
chub search "pgvector"
chub search "neo4j"
```

## Behaviour rule

Default: always run `chub get` before the first API call against
a new library inside a task. Exception: the library is trivial
(stdlib, well-known APIs like `os.path`, `json`).

Existing annotations are appended automatically — watch for
`[ANNOTATION]` blocks.

## Boundary

- No research workflow → research/WORKFLOW.md (`get_api_docs` is
  only API lookup, not domain research).
- No code generation — MCA writes the code; `get_api_docs` only
  delivers the docs.
- No library comparison — research workflow on alternatives
  evaluation.

## Anti-patterns

- **NOT** write code against a library without `chub get` when
  the library is new. INSTEAD always lookup before the first
  API call in a new lib. Because: API assumptions from memory
  are often stale.
- **NOT** ignore ANNOTATION blocks. INSTEAD read them; they
  contain BuddyAI-specific conventions. Because: annotations
  are the gap between lib defaults and our stack.
- **NOT** drop the docs on a "well-known" lib when the last
  check is >6 months old. INSTEAD lookup when uncertain.
  Because: APIs change.
