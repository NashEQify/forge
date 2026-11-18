# Retroactive spec update — spec walkthrough and leftover check

Step-loaded unit of `skills/retroactive_spec_update/SKILL.md`. Read it when dispatching Phase 2 to `brief-architect`
(`mode=retro_spec_update`) and pass it to the architect, or before Buddy walks the spec inline on the skip path; the
architect or Buddy follows it through the Phase 2b leftover check.

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
