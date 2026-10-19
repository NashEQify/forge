---
name: knowledge-processor
description: >
  The context-write mechanism — reconcile new information against existing
  knowledge so `context/` and the user's own repo stay accurate. Triggers when
  new information must be folded in: a fact, decision, correction or changed
  state in the conversation (same response cycle under continuous
  maintenance), a task status change, save, or an agent return; NOT a
  standalone workflow — it is cross-cutting infrastructure.
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
routing). Project with its own `context/` → project path.
Without `context/` → user scope only. All paths relative to
the active context path. **Exception — always global:**
user-scope facts go to the resolved user repo
(`<user_repo>/context/user/`, `framework/user-scope.md`) regardless of
the active project path. No user scope configured → do not write; report
the fact as unroutable.

## Inputs

- **information:** what was observed / changed / experienced
  (raw input or summary).
- **mode:** `process` | `wrap-up` | `user-signal`.

**Close-phase input (build / fix / solve, when `close_retro` fired):** the
`information` is the retro's **§Patterns-Emerged** section
(`docs/<workflow>/<slug>-retro.md`) — already distilled — consumed via
`mode=process` rather than re-extracting from raw artifacts. Other
invocations (standalone, save, agent-return) are unchanged. (spec 374 §6.)

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

## Continuous maintenance

Applies to the user scope whenever one is configured
(`framework/user-scope.md` — configuring it is the person's consent), and to
a project's context when the project's rules require ongoing maintenance. Runtime-neutral and
instruction-level: no hook, no background agent. Project rules may add
specifics (provenance, sensitive data, storage places); they do not need to
restate these rules.

- **Same response cycle.** Fold a new relevant fact, decision, correction,
  confirmed goal/preference or changed state into its responsible file
  before sending the final answer — do not wait for `save` or session end.
  Delta check first; write NEW/CHANGED only; uncertain → ask, or keep it as
  a marked open question, never as fact. Honor "do not save". Tentative
  thinking, AI interpretations and third-party claims are not user facts.
- **Keep the scope.** An instruction for one task or topic is filed with
  that task/topic, not promoted to repository-wide rules. Judge profile
  content and execution rules of one source separately.
- **New leading file.** When a new leading version of a result appears
  (draft, deck, document), switch the responsible navigation and the
  handoff to it in the same cycle — a new session must land on the newest
  version.
- **Task-scoped working rules** (e.g. where drafts of an assignment go) are
  recorded in the handoff or the topic's local notes, not only in a tool's
  memory; other sessions and runtimes cannot see tool memory.
- **Checkpoint.** In long sessions, after a substantive interim result and
  before a topic switch: knowledge to its leading place; assignment,
  decisions and open work to the handoff. Do not accumulate over many turns
  in chat only.
- **Before each write** re-read the target file: parallel sessions write
  to the same user files.
- **After compaction or resume:** re-read the project rules, the user boot
  set and the complete handoff, then the affected topic files; catch up
  pending maintenance before dependent work. Never claim from memory that
  maintenance was done — check the files.
- **Write blocked:** for project context, note a concrete pending item
  (target file, missing information) in that project's handoff; if that is
  blocked too, report the missing persistence explicitly. For **user-scope**
  facts, never park them in another repository's files — report them as
  `deferred:` in the FACTS line and catch up when the user repo is
  writable (`framework/user-scope.md` §4).
- **Supersede, don't append.** Replace outdated statements in current
  knowledge and align affected summaries and links; historical evidence
  stays unchanged.

**FACTS line** — proof of the check, as the last line of an answer:

`FACTS: keine | {Fakt} → {Ziel} [geschrieben|deferred:{Grund}]`

Every answer carries the line while continuous maintenance is active;
`FACTS: keine` when nothing qualified. "pending" is not a value — write now, or defer with a reason. A `deferred:` item is
resolved or carried into the handoff before the next commit or save.

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
