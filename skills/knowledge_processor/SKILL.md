---
name: knowledge-processor
description: >
  Brain logic as agent behaviour. Process new information against
  existing knowledge. Keeps `context/` accurate. Pre-brain: LLM on
  files; post-brain: queries.
status: active
relevant_for: ["solution-expert"]
invocation:
  primary: cross-cutting
  secondary: [workflow-step:close, user-facing]
disable-model-invocation: false
modes: [process, wrap-up, user-signal]
uses: []
---

# Skill: knowledge-processor

## Purpose

Brain logic as agent behaviour: process new information against
existing knowledge. Keeps the context system (`context/`)
accurate, not just current. Pre-brain as LLM reasoning on context
files, post-brain as structured queries — the logic stays.

## Context path

Operates on the **active context path** (set by boot.md context
routing). Project with its own `context/` → project path. In
BuddyAI → BuddyAI path. Without `context/` → user context only.
All paths relative to the active context path. **Exception —
always global:** `context/user/` is always written in BuddyAI.

## Inputs

- **information:** what was observed / changed / experienced
  (raw input or summary).
- **mode:** `process` | `wrap-up` | `user-signal`.

## Mode routing

| Mode | Loads | Pipeline |
|------|-------|----------|
| process | modes/process.md | EXTRACT → IMPACT CHAIN → SIGNAL CHECK |
| wrap-up | modes/wrap-up.md (calls process internally) | brain logic + history |
| user-signal | modes/user-signal.md | CLASSIFY → LOCATE → UPDATE/CREATE → IMPACT CHAIN → CONNECT → REPORT |

## Contract

### INPUT
- **Required:** information — what was observed / changed /
  experienced (raw input or summary).
- **Required:** mode — `process` | `wrap-up` | `user-signal`.
- **Context:** active context path (set by boot.md context
  routing). Mode-specific files: `modes/process.md`,
  `modes/wrap-up.md`, `modes/user-signal.md`.

### OUTPUT
**DELIVERS:**
- mode=process: context-file updates (delta-checked) + IMPACT
  CHAIN (LOCATE + ASSESS + ACT).
- mode=wrap-up: history entry + context updates as session
  closure.
- mode=user-signal: user-profile updates (CLASSIFY → LOCATE →
  UPDATE/CREATE → IMPACT CHAIN → CONNECT → REPORT).
- Delta-check proof: NEW / CHANGED / PRESENT classification per
  piece of information.

**DOES NOT DELIVER:**
- No uncertain information — only observed or derived (marked
  as `[Derived]`).
- No interpretation without a marker.

**ENABLES:**
- All workflows (close phase): persisting session knowledge.
- Boot: accurate context for the next session via
  `overview.md` + session handoff.
- All agents: current, delta-checked context files for routing
  and decisions.

### DONE
- Delta check per planned information: NEW / CHANGED / PRESENT
  classified.
- Only NEW and CHANGED written; PRESENT skipped.
- Write-quality gate: observed / derived / uncertain —
  uncertain is NOT written.
- IMPACT CHAIN executed (LOCATE + ASSESS + ACT).
- On wrap-up: history entry written.
- On user-signal: CLASSIFY → LOCATE → UPDATE/CREATE → IMPACT
  CHAIN → CONNECT → REPORT.

### FAIL
- **Retry:** not foreseen — the skill writes or skips
  (delta check).
- **Escalate:** uncertain information → ask the user instead
  of writing. Incident mode → ACT deferred until the fix is
  done.
- **Abort:** not foreseen — the skill is idempotent (the delta
  check prevents double writes).

## Entropy audit

No mode — triggered at boot and periodically. Logic and triggers:
`reference/concepts.md`.

## From coarse to fine

- `overview.md` = curated top-level summary (evergreen).
- Detail files = depth (sprout). More important content
  displaces less important content into detail files.
- `navigation.md` = index (quick routes to every file in the
  area).
- Max 200 lines per MD under `context/`.
- Maturity promotion (seed → sprout → evergreen):
  `reference/concepts.md`.

## Guardrails (apply to ALL modes)

### Delta check (MUST — before every context write)

For every planned context write:

**Step 1:** read the target file. MUST, no opt-out.

**Step 2:** classify per piece of information:

```
Delta check for [filename]:
  NEW:     [information not yet in the file]
  CHANGED: [information that exists but is stale / wrong → what gets replaced]
  PRESENT: [information already correctly in the file → not written again]
```

**Step 3:** only NEW and CHANGED are written. PRESENT is
skipped.

When everything is PRESENT: "Delta check: no new information —
write skipped."

### Write-quality gate (MUST — before every write commit)

```
Write quality: observed / derived / uncertain
```

- **observed:** directly from user input, commit, file, tool
  output — fact.
- **derived:** logical inference — mark as
  `[Derived: ...]` in the context text.
- **uncertain:** NOT written — ask the user or note as an open
  point.

### Unloading after a write

After every context write check whether the topic can be
unloaded. Criteria: `reference/concepts.md`.

### Incident mode (MUST — during an active root-cause-fix)

When a root-cause-fix is running (recognizable: Buddy is in the
`root_cause_fix` skill):

- **EXTRACT runs normally** — facts are identified and
  collected.
- **IMPACT CHAIN: LOCATE + ASSESS run normally** — impacts are
  recognized.
- **ACT phase is deferred** — no context writes until the fix
  is done.
  Reason: diagnostic facts describe a transient state. The fix
  changes that state. Context writes during diagnosis are
  stale after the fix.
- **After the fix is closed:** process the collected EXTRACT
  + ASSESS output in one pass. ACT on the end state, not on
  intermediate states.

Proof output during incident mode:

```
7e INCIDENT-MODE: [N] facts collected, ACT deferred until the fix is closed.
```

**Not affected:** SIGNAL CHECK. When a systemic signal is
recognized during diagnosis (e.g. "this error type is happening
the third time"), the signal is noted immediately —
independent of the fix status.

### Other

- No secrets in context files. Max 200 lines per MD (exception:
  `detailed-overview.md`). Keep navigation consistent after an
  update.

- **Patch over rewrite:** update existing context files via a
  targeted replace (single section / paragraph) instead of a
  full rewrite. Full rewrite only when >50% of the content
  changes.

Concepts, forward compatibility, session-buffer relationship:
`reference/`.
