---
name: retroactive-spec-update
description: >
  Retroactively update existing specs to match the as-is code state.
  Git commits give SCOPE, source code is the EVIDENCE. Walk through the
  spec section by section, read the relevant source files completely,
  compare, update. Prevents feature creep by never asking "what could be
  added" — only "what does the code already do that the spec does not
  describe".
status: active
invocation:
  primary: workflow-step
  secondary: [user-facing]
disable-model-invocation: false
uses: [spec_amendment_verification, spec_board]
---

# Skill: retroactive-spec-update

## Guiding principle (keep in mind before every run)

**The spec defines the product. Incidents are fixed in the spec,
not in the code.**

This skill exists because in practice it often runs the other way
round: code evolves, specs lag behind. That is technical debt
which this skill pays off. Every run is a **reversal** of that
order — the spec reclaims what is hers by describing the code
that already exists.

**What this skill does NOT do:** invent new features, suggest
features, ask "what else could be there". The skill operates
strictly retroactively — the source of truth is the existing
source code, not the reviewer's imagination.

**Guiding question per section:** *"What does the code do that
the spec does not fully describe?"* — NOT *"What is missing from
the product?"*.

---

## When to call

- Pre-launch sweep: bring the spec corpus to as-is code state
  before public release.
- Post-incident: the bug fix changed behaviour; the spec must
  reflect it.
- Feature drift: a feature shipped without a spec update
  (technical debt).
- Periodic catch-up: N weeks / months without a spec sync; code
  is ahead.

## Do not call for

- **Writing new specs** → `spec_authoring` (interview-based).
- **New sections for new features in existing specs** →
  `spec_authoring` (because an interview is needed to clarify
  user intent, even on section additions).
- **Read-only cross-spec verification** →
  `spec_amendment_verification` (post-amendment).
- **Spec-quality review** → `spec_board` (rebuild-readiness
  check).

---

## Input

Buddy identifies and passes:

- **`target_specs`:** list of spec files that potentially have
  drift.
- **Optional `last_sync_ref`:** git ref of the last confirmed
  spec-sync commit. When present, it forms the scope entry.
  Otherwise: Buddy searches the git log for the last "sync all
  specs" or similar commit, or falls back to "all commits in N
  weeks".
- **Optional `scope_hints`:** additional source-file patterns
  that are relevant (when the spec doesn't reference code
  explicitly).

---

## Default dispatch path (per spec 306 §14.5)

Phase 1 (git scope) and Phases 3-5 (DIM check, cross-spec verify,
commit-bookkeeping) are Buddy-direct. **Phase 2 (spec walkthrough)
is dispatched to `brief-architect` in `mode=retro_spec_update`** —
the architect reads each relevant source file completely in fresh
context, classifies findings (MATCH / SPEC-GAP / SPEC-DRIFT /
CODE-BUG), and returns proposed prose + DIM-map per section
**inline**. Buddy integrates the architect's findings into the spec
file (architect has no Write target per spec 306 §14.4), bumps
`spec_version`, and continues to Phase 4.

The architect dispatch is the default. The skip path
(`--skip retroactive-spec-update --reason "buddy-context-already-loaded"`)
exists for the rare case where Buddy just finished writing the code
in scope and the read-cost has already been paid; in that case
Buddy executes Phase 2 inline. The default-architect choice
preserves fresh-context discipline on the typical retro run, which
is code-read-heavy by construction.

CODE-BUG escalations from the architect's findings list trigger the
phase 4b ledger flow (Buddy-direct, user-decision-required). The
architect identifies CODE-BUG candidates per the four-classification
model; Buddy owns the user-decision loop.

---

## Phase 1 — GIT SCOPE (structural, the entry door)

**Goal:** identify the relevant source files. Commits are hints,
not ground truth.

Steps:

1. **Find the last sync point:**
   - Read the spec header for `Board-Reviews` / `Last Update` /
     `spec_version`.
   - Or git log grep:
     `git log --grep="sync all specs\|spec sync" --oneline -5`.
   - Or passed in by the user.

2. **List commits since the last sync:**
   ```
   git log <last_sync>..HEAD --oneline
   ```
   Filter roughly for behaviour-relevant commits (feat, fix,
   refactor with behaviour impact). Infra / docs / release
   commits are irrelevant.

3. **Aggregate relevant source files** from two sources:
   - **From git log:** which files were changed in the relevant
     commits?
     `git log <last_sync>..HEAD --name-only --format=""`.
   - **From spec self-declaration:** grep the spec for
     file-path patterns, component names, class names. The
     spec often mentions `CallProvider`, `VideoGrid`,
     `AudioVideoSettings`, etc. — those are the entry points.

4. **Cross-reference:** files that appear in both lists are
   high-confidence. Files that appear in only one list are
   coverage warnings (either code was changed but the spec
   ignores the area, or the spec describes something that has
   no current code).

**Phase 1 output** (working doc
`docs/spec/_update-notes/{spec}-scope.md` or inline in Buddy's
context):

```markdown
# {spec_file} — Retroactive Update Scope

**Last sync:** <commit hash + date>
**Commits since:** <count>

**Source files in scope:**
- src/path/to/fileA.ts
- src/path/to/fileB.tsx
- ...

**Commits as hints (not as the diff basis):**
- <hash> <subject>
- ...

**Spec-declared references:**
- Consumed: <list from header>
- Components mentioned: <from grep>
```

**Phase 1 is scope, not content.** No spec edits in phase 1.

---

## Phase 2 — SPEC WALKTHROUGH (code-driven, architect-dispatched)

**Goal:** compare each spec section with the relevant source
code.

**Dispatch:** Buddy spawns `brief-architect` via the `Agent` tool
with `mode: retro_spec_update`, passing `target_specs`, the
`last_sync_ref` and source-file shortlist from Phase 1, and
`intent_chain`. The architect executes the walkthrough below in
fresh context and returns the per-section findings list inline
(per `agents/brief-architect.md` Required Output for
`mode=retro_spec_update`). Buddy integrates the findings into the
target spec(s); the architect has no Write target.

The walkthrough definition below applies whether the architect
executes it (default) or Buddy executes it (skip path):

For every section of the spec (in order):

### 2a. Determine the section's scope

Which part of the code implements this section?
- Readable from the section itself (section 40.3 "Join Call
  Control" → CallControls.tsx + call.tsx joinCall function).
- From the phase-1 source-file shortlist → pick what's relevant.
- When unclear: grep the phase-1 files for terms from the
  section.

### 2b. Read the source code **completely**

**Not just the lines that appear in the git diff.** Read the
complete function / component / module. The lines that didn't
change often carry context the diff alone doesn't show (parent
handlers, state initialization, cleanup paths, error branches).

Recommended: **read the whole file** when <300 lines. **Read
the whole function** when the file is larger and the function
is clearly bounded.

### 2c. Describe what the code does

In your internal working memory (or as a working note):
- What is the function, what is the input, output, side
  effects?
- Which state transitions does it trigger?
- Which error paths exist?
- Which edge cases does it handle?
- Which browser APIs / library APIs / environment assumptions
  does it rely on?

This internal description is the **evidence** against which you
check the spec.

### 2d. Compare with the section

Four possible findings:

1. **MATCH:** spec and code agree. No change.

2. **SPEC-GAP:** code does more / more precisely than the spec
   describes.
   → Extend the spec with the missing description.
   Examples:
   - Code has a 500ms delay; the spec says nothing about timing.
   - Code handles `NotReadableError` with a retry button; the
     spec only has a generic "error shown".
   - Code has a `useEffect` with a cleanup flag; the spec
     doesn't mention that it is cancellable.

3. **SPEC-DRIFT:** spec describes old behaviour that no longer
   holds.
   → Update the spec; **replace** the old description (not just
   add to it).
   Examples:
   - Spec says `requestPermissions: true`; code has `false`.
   - Spec says "60-second ring timeout"; code has 30.
   - Spec says "webAudioMix: true"; code has removed it.

4. **CODE-BUG** (escalation): the code does something that
   **doesn't match intent** and looks like a bug — but it
   isn't obviously a bug, it could also be intentional.
   → **ESCALATE to the user.** Never silently encode it as
   "intended behaviour" in the spec. The guiding principle
   demands that the spec documents intent, not codify bugs.
   Examples:
   - Code has `if (user.isAdmin) { bypassValidation() }` — is
     that intentional or a security bug?
   - Code has the magic number `setTimeout(..., 3000)` without
     a comment — intentional or leftover debugging?

### 2e. Write the update (only on SPEC-GAP or SPEC-DRIFT)

Update along the 5 primitives (from `spec-engineering.md`):

- **P1 self-contained:** describe the new / corrected
  functionality so a re-implementer understands it without the
  code.
- **P2 acceptance criteria:** add AC(s) when the section has
  ACs.
- **P3 constraint architecture:** MUST / MUST NOT / PREFER /
  ESCALATE where relevant.
- **P4 failure modes:** required — which failure paths does
  the existing code have? Add them to the failure-modes table.
- **P5 interfaces & protocols:** exact API / event /
  state definitions when present.

---

## Phase 2b — LEFTOVER CHECK

After walking through every section:

1. **Source files that were in the phase-1 scope but were not
   assigned to any section in phase 2:** are there
   functionalities here that the spec doesn't mention at all?

2. Three options per unassigned file:
   - **(a) Add a new subsection** when the functionality
     belongs to the spec topic and is missing.
   - **(b) Cross-reference to another spec** when the
     functionality belongs elsewhere.
   - **(c) Escalate to the user** when unclear — **never pass
     silently**.

3. The decision goes into the working doc.

**Important:** phase 2b is **not** "what's missing as a feature".
It is "what does the code do that the spec ignores". That is the
fine but essential distinction.

---

## Phase 3 — DIM map per section (self-check)

For every section changed in phase 2: a **DIM map as an HTML
comment** in the spec or as a separate block in the working doc.

```html
<!-- DIM map §<section> <topic>
  Completeness:        ✓ / Partial / Open / Missing
  Consistency:         ✓ / Partial / Open / Missing
  Implementability:    ✓ / Partial / Open / Missing
  Interface contracts: ✓ / Partial / Open / Missing
  Dependencies:        ✓ / Partial / Open / Missing
-->
```

Status values:
- `✓` — dim fully addressed against code evidence.
- `Partial` — partial, with an explicit note on what is open.
- `Open` — deliberately left open with rationale (e.g. "feature
  handled in another spec").
- `Missing` — gap, MUST be addressed before phase 4.

**No section leaves phase 3 with `Missing`.**

**Important on completeness semantics:** here completeness is
*descriptive* ("what is there is described"), not *prescriptive*
("everything that should be there is there"). The difference is
the whole point of this skill.

---

## Phase 4 — Cross-spec verify

Dispatch the `spec_amendment_verification` skill:
- **Input:** `changed_specs` + `change_summary` from phase 2 +
  2b.
- **Output:** PASS or ISSUES_FOUND.
- **On ISSUES:** escalate to the user with the issue list.
  Buddy does NOT fix autonomously — the user decides whether
  the fix goes into the updated spec or into a neighbour spec.

---

## Phase 4b — Code Gap Ledger (NORMATIVE)

**In parallel with phase 4, ALWAYS when CODE-BUG findings came
out of phase 2.**

Every `CODE-BUG (ESCALATE)` finding is recorded in a persistent
**Code Gap Ledger**, **NOT fixed in code**.

### Why not fix in code

- The skill operates in retroactive mode — it assumes the app is
  currently stable and deployed. Code changes could break that.
- Whether a suspicious behaviour is a bug or intent can ONLY be
  decided by the user. The skill cannot make a silent decision.
- The ledger entry is a commitment device: the gap won't be
  forgotten, but it isn't fixed prematurely either.

### Ledger location

Project-specific. Convention:
- Projects with their own deploy path:
  `docs/<deploy-area>/code-gap-ledger.md` (gitignored).
- Other projects: `context/code-gap-ledger.md` or similar.
- The ledger MUST live in a gitignored path while user
  decisions are open — it carries working notes, not spec
  output.

### Ledger entry structure

Per CODE-BUG finding:

```markdown
### CGL-NNN {short title}
- **Source:** {spec section} → {finding ID from phase 2}
- **Severity:** CRITICAL / HIGH / MEDIUM / LOW
- **Code evidence:** {file:lines + short code quotes}
- **What the code does:** {1-3 sentences, concrete}
- **What the spec says:** {spec quote or "nothing"}
- **User decision needed:**
  - (a) {option 1 — fix the code: what would have to be done}
  - (b) {option 2 — update the spec: how the spec text would read}
- **Recommendation:** {Buddy's view, but no decision}
```

### Workflow

1. Buddy enters CODE-BUG findings from phase 2 into the ledger.
2. The app code is **NOT** changed.
3. The spec is **NOT** updated for this finding until the user
   has decided.
4. Other findings (SPEC-GAP, SPEC-DRIFT) flow into the spec
   updates as usual.
5. When the user later takes the decision: the ledger entry is
   marked "resolved" with date + action (code fix or spec
   update).

### Anti-pattern

**Silently writing a CODE-BUG as "intended behaviour" into the
spec.** That violates the guiding principle (the spec documents
intent, not implementation accidents) and smuggles technical
debt into the spec. **Ledger OR escalate — never silent
encoding.**

---

## Phase 5 — Commit

1. **Spec header update:**
   - Bump `spec_version` (minor on behaviour changes, patch on
     clarifications).
   - `Last Update` field: date + short summary.
2. Commit per spec or per logical group.
3. Commit message format:
   ```
   docs(spec): retroactive update {spec-name} to v{spec_version} — {summary}

   - Source files read: <list>
   - Findings: SPEC-GAP x N, SPEC-DRIFT x M, CODE-BUG x K (ledgered, not fixed)
   - DIM coverage: all sections cleared (see working doc)
   - spec_amendment_verification: PASS
   - Code Gap Ledger: {count} new entries

   Code-evidence as of <commit_hash>
   ```
4. After all updates: a consolidated change log in
   `context/history.md`.
5. The Code Gap Ledger is **NOT** committed (stays gitignored)
   — it is a working doc until user decisions are taken.

---

## Post-pass checklist (NON-NEGOTIABLE)

- [ ] Phase-1 scope doc exists (even if only in Buddy's
  context).
- [ ] Every section of the spec was actively compared (not
  skipped).
- [ ] All source files from the phase-1 scope are handled in
  phase 2 or 2b.
- [ ] No section with DIM-map status `Missing`.
- [ ] **All CODE-BUG findings are entered in the ledger
  (phase 4b) — NO code fix without an explicit user
  decision.**
- [ ] **No CODE-BUG was silently encoded as "intended
  behaviour" in the spec.**
- [ ] `spec_version` bumped on every updated spec.
- [ ] Failure-modes table updated (required per spec_update).
- [ ] `spec_amendment_verification` ran.
- [ ] CODE-BUG findings escalated to the user (when found).
- [ ] git commit(s) with conventional messages.
- [ ] `context/history.md` entry with change summary.

---

## Contract

### INPUT

- **Required:** `target_specs` — list of affected spec files.
- **Required:** access to the project's source code.
- **Required:** git log accessible (for phase 1).
- **Required:** `framework/spec-engineering.md` (5 primitives).
- **Optional:** `last_sync_ref`, or the skill finds it itself.
- **Optional:** `scope_hints` for additional source patterns.

### OUTPUT

**DELIVERS:**
- Updated spec files (with `spec_version` bumps).
- Scope working doc (can be committed or gitignored —
  project-specific).
- DIM map per changed section.
- `spec_amendment_verification` result.
- Commits with conventional messages.
- `context/history.md` entry.

**DOES NOT DELIVER:**
- No new features, no feature suggestions.
- No interview — the code is evidence; the user is not in the
  loop except on a CODE-BUG escalation.
- No board review — that is `spec_board`; can be requested
  afterwards.

**ENABLES:**
- Pre-launch sweep: as-is sync of every relevant spec.
- Post-incident update: the spec matches the new
  behaviour-fix.
- `spec_board` input: updated specs are review-ready.

### DONE

- All sections of `target_specs` were compared with the source
  code.
- The 5 primitives were applied per update.
- The 5 dimensions were self-checked via the DIM map (no
  `Missing`).
- `spec_amendment_verification` PASS or escalated issues.
- `spec_version` bumps, commits, history entry.

### FAIL

- **Retry:** cross-spec verify `ISSUES_FOUND` → fix →
  re-verify.
- **Escalate:**
  - CODE-BUG found, user decision needed.
  - Phase 2b unassigned source file, classification unclear.
  - Spec and code contradict each other and intent is unclear.
- **Abort:** not foreseen.

---

## Boundary

- **No interview authoring** → `spec_authoring` (for NEW specs
  or new sections that need an interview).
- **No read-only verify** → `spec_amendment_verification`.
- **No quality review** → `spec_board` (rebuild-readiness).
- **No code review** → `code_review_board`.

---

## Anti-patterns

- **NOT** treat git diffs as a substitute for code reading.
  INSTEAD: read the whole function / component. Because: diffs
  show delta, not context. The context contains the edge cases
  the spec has to describe.

- **NOT** ask "what's missing as a feature?". INSTEAD: "what
  does the code do that the spec doesn't describe?". Because:
  the first one is design review and leads to feature creep;
  the second is fidelity review and leads to accurate specs.

- **NOT** silently document bugs as intended behaviour. INSTEAD
  on suspicious code passages, escalate as CODE-BUG. Because:
  the guiding principle demands that the spec documents intent,
  not implementation accidents.

- **NOT** skip phase 2b (leftover check). INSTEAD actively
  triage unassigned source files. Because: "there's still
  something in the code" is often the real find of a
  retroactive run — a whole functionality the spec never
  mentioned.

- **NOT** walk multiple specs in parallel. INSTEAD one after
  the other, with a full walkthrough. Because: context
  switching between specs leads to shallow walkthroughs — the
  deep comparison needs dedicated focus.

- **NOT** treat the scope doc as a committed artifact. INSTEAD
  working doc (gitignored or ephemeral). Because: the scope
  doc is a process note, not spec output. Specs are the only
  committable artifact of the skill.

---

## Relation to other skills

```
spec_authoring             (NEW specs or new sections, interview-based)
     ↓
retroactive_spec_update    ← YOU ARE HERE (existing specs, code-as-evidence catch-up)
     ↓
spec_amendment_verification (phase 4, cross-spec consistency)
     ↓
spec_board                 (rebuild-readiness quality review)
```

The `retroactive_spec_update` skill is explicitly **retroactive**
— it compensates technical debt between code and spec. The name
says what it is and rules out the feature-creep route.
