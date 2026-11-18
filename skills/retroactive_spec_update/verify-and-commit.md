# Retroactive spec update — DIM map, cross-spec verify, Code Gap Ledger and commit

Step-loaded unit of `skills/retroactive_spec_update/SKILL.md`. Read it once the Phase 2 / 2b findings are integrated
into the spec, before the DIM self-check, and follow it through cross-spec verify, the Code Gap Ledger (whenever
Phase 2 produced a CODE-BUG finding), the commit and the post-pass checklist.

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
