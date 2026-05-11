# BuddyAI System Testcases

Standardised testcases for the repo logic, workflows and Buddy behaviour.
Run periodically — manually (Buddy walks through them) or after larger refactors.

Each testcase has: ID, Precondition, Steps, Expected result, Status (pass/fail/untested).
PASS tests additionally have `expected_behavior` — a behavioural description as preparation for Langfuse golden datasets (ADR OBS-001). UNTESTED tests get the field on first PASS.

---

## T01: Boot in BuddyAI (intent.md in WD)

**Precondition:** `cd ~/BuddyAI && cc` (fresh session)
**Steps:**
1. Buddy starts, reads soul.md + operational.md + boot.md
2. Recognise intent: BuddyAI/intent.md found (in WD)
3. Load context: Context field says "coding project" → plan_engine --boot + values.md
4. Check session-buffer for PENDING
5. Hook resume or standby
6. Entropy audit (one sentence)
7. Greeting (style: soul.md)

**Expected result:**
- Buddy knows the user (name, machines, working style — from plan_engine --boot output)
- Buddy knows the backlog (current phase, next task — from plan_engine --boot output)
- Buddy knows the current situation (hook, handoff — from plan_engine --boot output)
- Greeting is short and context-aware

**expected_behavior:** Buddy reads soul.md + operational.md + boot.md, finds BuddyAI/intent.md, reads Context field ("coding project"), loads plan_engine --boot + values.md. Checks session-buffer for PENDING. Gives a short context-aware greeting. No on-the-fly loading of individual files during boot — details on wakeup on-demand.

**Last tested:** 2026-03-08 (boot before framework review: soul+operational+boot read, boot-context+values read, session-buffer PROCESSED cleared, entropy audit, short greeting)
**Status:** PASS
**DR coverage:** DR-4, DR-8

---

## T02: Boot in external project (intent.md in project WD)

**Precondition:** `cd ~/GamingHangout && cc` (project with intent.md)
**Steps:**
1. Buddy starts, finds GamingHangout/intent.md (in WD)
2. Load context: values.md (global) + derived from the Context field of the project intent.md
3. Greeting with project context

**Expected result:**
- Only values.md is guaranteed. Everything else is derived from the Context field of the project intent.md
- Buddy knows the project intent AND user defaults
- Project rules (CLAUDE.md) apply on top of BuddyAI rules
- Context routing: history + backlog in the project, user context global

**expected_behavior:** Buddy finds intent.md in the project WD, loads values.md (global) + derives context from intent.md (CLAUDE.md, backlog, tech-spec). Greeting with project context. Context routing: history goes to BuddyAI (no context/ in the project), user context global.

**Last tested:** 2026-03-17 (boot in ~/projects/GamingHangout: intent.md found, values.md loaded, CLAUDE.md+backlog+tech-spec loaded, greeting with project context, history written to BuddyAI)
**Status:** PASS
**DR coverage:** DR-4, DR-8

---

---

## T04: Context update after commit (mode=process, brain logic)

**Precondition:** Agent has made a commit
**Steps:**
1. Agent recognises commit trigger
2. Checks: structural commit? (files moved/renamed/deleted)
3. If yes: knowledge-processor + consistency-check
4. If no: knowledge-processor only
5. Checks whether context changes are required

**Expected result:**
- For a structural commit: consistency check runs, dead references are reported
- For a normal commit: context check only
- No stale references remain

**Check points:**
- [ ] Trigger fires reliably
- [ ] Structural vs. normal is correctly distinguished
- [ ] Consistency check finds real errors
- [ ] Context update writes to the correct path

**expected_behavior:** Agent recognises commit trigger, distinguishes structural vs. normal. For a structural commit: knowledge-processor + consistency-check both run. For a normal commit: knowledge-processor only. No stale references remain. Context write goes to the active context path.

**Update (ARCH-018):** main-code-agent no longer runs a commit gate. Context updates after commits are Buddy's responsibility via return summary. T04 now applies only to Buddy's own commits and sysadmin work.

**Last tested:** 2026-03-05 (5 commits checked, 2 context updates, navigation consistent)
**Status:** PASS
**DR coverage:** DR-3, DR-4

---

## T05: save command (mode=wrap-up)

**Precondition:** Buddy in active session, work has been done
**Steps:**
1. User says "save"
2. Buddy reads knowledge_processor SKILL.md
3. Summary of the session
4. Check context files and update if necessary
5. Write history entry
6. Open points in the history entry → captured as tasks in the backlog

**Expected result:**
- History entry under context/history/ in the active context path
- Open points that require concrete actions → in the backlog
- History entry has "Backlog: <task IDs>" or "Backlog: no action required"
- Context files updated where necessary

**expected_behavior:** Buddy reads knowledge_processor SKILL.md, summarises the session, checks context files, writes a history entry in the active context path. Open points with a concrete action are captured as tasks in the backlog. History entry references backlog IDs or explicitly states "no action required". Hook + handoff are written.

**Last tested:** 2026-03-08 (save after framework-review prompt: dispatcher (empty) → Validate → History → boot-context refresh → Hook → Handoff → TC → Convoy (skip, no objective) → Cleanup (already clean). 9 steps complete.)
**Status:** PASS
**DR coverage:** DR-3, DR-8

---

## T06: Delegation to main-code-agent (full pipeline loop)

**Precondition:** Buddy has spec + task, delegates to main-code-agent
**Steps:**
1. Buddy creates Delegation-Ready artefact (from spec-authoring.md template)
2. Buddy emits transparency header
3. main-code-agent receives with intent_chain
4. main-code-agent emits its own transparency header
5. Plan → Spec Baseline (code-spec-fit, conditional on spec_ref) → Implement → Review (code-review / code-adversary / code-* via Code-Review-Board) → Test (tester) → Spec Validation → Iterate
6. Tester derives testcases from the spec, writes tests, executes them
7. main-code-agent reports: "Tester: SIGNED OFF (N tests, M new)"
8. Return summary (Changes, Spec-Assumption-Diff, Discoveries, Incidents)

**Expected result:**
- Full loop is traversed
- No "done" without tester sign-off
- Transparency header at every point
- Return summary complete (Changes, Discoveries, Incidents)

**expected_behavior:** Buddy creates a Delegation-Ready artefact, emits the transparency header. main-code-agent emits its own header + Intent Alignment block. Full pipeline loop: Plan → Spec Baseline → Implement → Review → Test → Spec Validation → return summary to Buddy. Buddy runs knowledge_processor after the return (ARCH-018). Closing message "Tester: SIGNED OFF" as the final line. No skipping of steps.

**Last tested:** 2026-03-05 (this session, Task 075)
**Status:** PARTIAL PASS — task execution correct, closing message MISSING, sub-agent delegation not observable (CC Agent tool limitation). Fix: closing message turned into a hard gate.
**DR coverage:** DR-1, DR-2, DR-5, DR-10

---

## T07: Consistency check (structural + methodological)

**Precondition:** User says "consistency-check" or a structural/methodological commit
**Steps (structural):**
1. Scan all *.md files for dead path references (except archive/, history/)
2. Check Adapter SoT sync (CC + OC against agents/README.md)
3. Check navigation tree against disk
4. Walk through refactoring checklist (if category recognisable)

**Steps (methodological — on process/workflow/agent-behaviour change):**
5. Impact analysis: which files/processes reference or implement the changed concept?
6. Semantically check all affected places (logic, assumptions, flows)
7. Fix inconsistencies immediately

**Expected result:**
- Structural: output in defined format (ERRORS / WARNINGS / CHECKLIST)
- Methodological: all affected places read and confirmed consistent or fixed
- No false positives on example paths in documentation

**expected_behavior:** Structural: scan all *.md for dead references, check Adapter SoT sync, navigation tree against disk. Output in the format ERRORS/WARNINGS/CHECKLIST. No false positives on example paths. Methodological: semantically check all affected places, fix inconsistencies immediately. Structural commits trigger the check as a blocking gate (CLEAN = continue, ERRORS = fix loop). Check detects when its own path patterns are stale (new directories not covered) and reports that as ERRORS.

**Last tested:** 2026-04-02 (retroactive: consistency_check Skill actively used, §6 Stale Cleanup in sessions 73-80, plan_engine --validate as the structural check)
**Status:** PASS
**DR coverage:** DR-4, DR-7

---

## T08: Incident detection

**Precondition:** Buddy reads a spec/reference that looks stale
**Steps:**
1. Buddy detects inconsistency (path exists but should not be there, or structure does not match the documentation)
2. STOP — do not continue
3. Report to user
4. Analyse root cause
5. Capture as a task if systemic

**Expected result:**
- Buddy does not accept "technically works but structurally wrong" states
- User is informed before something is executed blindly

**expected_behavior:** Buddy detects inconsistency proactively while reading specs/references. STOP — do not continue. User is informed. Root cause is analysed. For systemic problems: capture a task. Do not accept "technically works but structurally wrong".

**Last tested:** 2026-03-05 (orphaned command/coding.md discovered, root cause analysed, checklist extended)
**Status:** PASS
**DR coverage:** DR-1, DR-2

---

## T09: think! command

**Precondition:** Buddy in active session
**Steps:**
1. User says "think!" or Buddy detects the need
2. Buddy emits a context dump (situation, open question, relevant context, current state)
3. User pastes the dump into a buddy-thinking session

**Expected result:**
- Context dump is self-contained and complete
- buddy-thinking can work with it without follow-up questions

**expected_behavior:** Buddy emits a context dump with situation, open question, relevant context and current state. The dump is self-contained — buddy-thinking can work with it without follow-up questions. No code output, only a structured context block.

**Last tested:** 2026-03-05 (this session, simulated)
**Status:** PASS
**DR coverage:** DR-8

---

## T10: Solution Expert delegation

**Precondition:** Architectural decision with trade-offs that is hard to reverse
**Steps:**
1. Buddy detects trigger (>1 valid path, hard to reverse, or own uncertainty)
2. Buddy delegates to solution-expert
3. solution-expert runs a Council (3 phases, situational perspectives)
4. Result returned to Buddy

**Expected result:**
- Buddy does NOT delegate voluntarily but MUST do so on trigger
- Decision is recorded in decisions.md

**Last tested:** never
**Status:** UNTESTED
**DR coverage:** DR-1, DR-6

---

## T11: Open points tracking (history → backlog)

**Precondition:** A history entry with open points is being written
**Steps:**
1. Context-update Skill writes the history entry
2. Skill checks the "Open points" section
3. Concrete actions → captured as tasks in the backlog or assigned to existing tasks
4. History entry receives "Backlog: <task IDs>"

**Expected result:**
- No open point with a concrete action remains only in the history
- Backlog reference at the end of the history entry

**expected_behavior:** Context-update Skill writes the history entry, checks "Open points". Concrete actions are captured as tasks in the backlog or assigned to existing tasks. History entry receives "Backlog: <task IDs>" or "no action required". No open point with a concrete action remains only in history.

**Last tested:** 2026-03-05 (as part of T05 save — open points checked, all in existing tasks)
**Status:** PASS
**DR coverage:** DR-3

---

## T12: New project setup (project-setup Skill)

**Precondition:** Empty folder or repo without intent.md
**Steps:**
1. Boot detects case 4
2. Buddy offers project-setup
3. Interview mode: what is the project? Status?
4. Create intent.md, CLAUDE.md, context/
5. Git init if needed

**Expected result:**
- Project has intent.md, CLAUDE.md, context/overview.md
- Global rules apply on top
- Buddy can start working in the project immediately

**Last tested:** never
**Status:** UNTESTED
**DR coverage:** DR-10

---

## Test-run log

| Date | Tested | Result | Notes |
|------|--------|--------|-------|
| 2026-03-05 | T01, T07 | PASS (after fixes) | Navigation tree, consistency check |
| 2026-03-05 | T06 | PARTIAL PASS | Delegation OK, closing message missing → gate added |
| 2026-03-05 | T09 | PASS | think! context dump correct, self-contained |
| 2026-03-05 | T04 | PASS | 5 commits, context update correct, navigation consistent |
| 2026-03-05 | T07 | PASS (methodological) | Consistency cascade applied to itself |
| 2026-03-05 | T08 | PASS | Orphaned command/coding.md discovered, root cause → checklist extended |
| 2026-03-05 | T05 | PASS | Full save flow: context, history, open points |
| 2026-03-05 | T11 | PASS | Open points → backlog checked, all in existing tasks |
| 2026-03-22 | T24 | FAIL | Intake gate did not fire on a casual turn. Steffi fact skipped. Fix: operational.md Intake-Gate-Clarification. Re-test required. |
| 2026-03-22 | T27 | PASS | Root-Cause-Fix with user gate. Steffi incident: Phase A → user "yes" → Phase B. |

---

## T13: Context invariants (structural, mechanically checkable)

**Precondition:** Repo in current state
**Steps:**

1. **Line length:** Every `.md` file under `context/` has ≤200 lines (exceptions: `detailed-overview.md`, `agentic-design-principles.md`)
   ```bash
   find ~/BuddyAI/context -name '*.md' ! -name 'detailed-overview.md' -exec awk 'END{if(NR>200) print FILENAME": "NR" lines"}' {} \;
   ```

2. **Navigation completeness:** Every file/folder under `context/` (except `history/`) is listed in the corresponding `navigation.md`. No dead entries in `navigation.md`.
   ```bash
   # For each area: compare disk content with navigation.md entries
   ```

3. **Area structure:** Every area under `context/` (except `history/`) has at least `overview.md`. Areas with subfolders have `navigation.md`.

4. **History naming convention:** All files under `context/history/` follow the pattern `YYYY-MM-DD-HHMM-*.md`.

5. **No secrets:** No file under `context/` contains patterns indicating secrets (`password:`, `secret:`, `token:`, `-----BEGIN`).

**Expected result:**
- All 5 checks pass
- On violation: concrete file + reason is reported

**Check points:**
- [ ] Line length: all ≤200 (except exceptions)
- [ ] Navigation: complete, no dead links
- [ ] Area structure: overview.md present
- [ ] History: naming convention adhered to
- [ ] Secrets: none found

**expected_behavior:** 5 mechanical checks run: line length ≤200 (with exceptions), navigation completeness against disk, area structure (overview.md present), history naming convention, no secrets. On violation: concrete file + reason. All 5 PASS = context invariants intact.

**Last tested:** 2026-03-05 (5 checks, 2 violations found and fixed: agentic-design-principles.md added to navigation.md + as line-length exception)
**Status:** PASS
**DR coverage:** DR-1, DR-4

**Note:** This test implements ARCH-006 (Parse Don't Validate) in the pre-harness state. Post-harness this becomes a CI job with a custom linter.

---

## T14: Normal build task with intent-freshness check

**Precondition:** User gives a direct build instruction (e.g. "implement X"), backlog has a matching operational intent
**Steps:**

1. Buddy receives the instruction
2. Intake gate fires (INCIDENT/FACTS/ACTIONABLE/INTERPRETATION)
3. Agent Check Step 0: intent-freshness line with proof output
4. Pre-Delegation checklist before delegation
5. main-code-agent receives with intent_chain
6. main-code-agent emits Intent Alignment block before the first plan step
7. Tester design mode creates a coverage matrix with an AC-quality column

**Expected result:**
- Step 0 emits the intent-freshness line (not just checked, but proven)
- main-code-agent emits Intent Alignment block before the first plan step
- Pre-Delegation checklist contains an L1 simulation with at least 3 scenarios
- Coverage matrix has an AC-quality column

**Core assertions:**
- Step 0 proof output: `Intent-Freshness: "[...]" ↔ "[...]" → consistent/drift`
- main-code-agent Intent Alignment block present before the first code step

**Failure indicator:** Delegation without Pre-Delegation checklist / Intent Alignment without proof sentence

**Last tested:** 2026-04-02 (retroactive: sessions 72-80, tasks 242/256/258 went through the build pipeline with delegation, debug blocks, intent-freshness)
**Status:** PASS
**DR coverage:** DR-1, DR-2, DR-6

---

---

## T16: Save after a long session with checkpoints

**Precondition:** Session with 3+ delegations, light checkpoints after each return, then "save"
**Steps:**

1. 3+ sub-agent delegations, each followed by a light checkpoint
2. At least 1 checkpoint has a non-empty "Unwritten" field → context write occurs
3. User says "save"
4. save aggregates checkpoint deltas instead of reconstructing anew
5. Delta check prevents duplicate writes (anything already written is not written again)

**Expected result:**
- Each sub-agent return has a light-checkpoint output
- save emits delta-check output per file (NEW / CHANGED / EXISTING)
- History entry aggregates checkpoint deltas

**Core assertions:**
- Every sub-agent return: light checkpoint present
- save: delta-check output per affected file

**Failure indicator:** save without prior checkpoints / EXISTING entries are written anyway

**Last tested:** 2026-04-02 (retroactive: session 76 was a 10-commit session with saves, checkpoints, delta checks. Session 78 save with task closures.)
**Status:** PASS
**DR coverage:** DR-3, DR-9

---

---

## T19: Architectural decision — Council + ADR + structural change

**Precondition:** Buddy detects need for a new agent or fundamental architectural change
**Steps:**

1. Buddy detects Solution Expert trigger (>1 valid path, hard to reverse)
2. Solution Expert is delegated to
3. Entry check: read decisions.md + agentic-design-principles.md
4. Intent Alignment validation before Council
5. Council with situational perspectives (relevant DRs named in the Council)
6. Result: create an ADR in decisions.md
7. Refactoring checklist has a design-principles item

**Expected result:**
- Entry check explicitly names relevant ADRs
- If design-principles relevance: relevant DR named in the Council
- ADR is created (not just offered)
- Refactoring checklist runs

**Core assertions:**
- Entry check: decisions.md + agentic-design-principles.md read
- ADR is committed

**Failure indicator:** Council without decisions.md read / ADR remains optional

**Last tested:** 2026-04-02 (retroactive: session 72 milestone-redesign with Council, session 74 Dashboard Architecture Council. ADRs committed, decisions.md updated.)
**Status:** PASS
**DR coverage:** DR-1, DR-6, DR-7

---

---

## T21: Intent paraphrase instead of copy-paste (DR-5 reinforcement)

**Precondition:** Buddy delegates a build task to main-code-agent with intent_chain
**Steps:**

1. Buddy creates a Pre-Delegation checklist with intent_chain (vision, operational, action)
2. main-code-agent receives the Delegation-Ready artefact
3. main-code-agent emits the Intent Alignment block
4. Check: is the intent_chain in the Alignment block a paraphrase or copy-paste?
5. Check: does the paraphrase contain an inference ("for this task this means: ...")

**Expected result:**
- main-code-agent rephrases intent_chain in its own words
- Rephrasing contains at least one task-specific inference (not just synonym replacement)
- Agent demonstrates that it has understood WHAT the intent means for its concrete work

**Core assertions:**
- Intent Alignment block is NOT verbatim identical to the intent_chain from the delegation artefact
- At least 1 sentence of the form "For this task this means: [concrete derivation]"

**Failure indicator:** Verbatim copy of the intent_chain / rephrasing without task-specific inference (synonyms only)

**Last tested:** never
**Status:** UNTESTED
**DR coverage:** DR-5, DR-1

---

## T22: Absorption check after a new primitive (DR-7 reinforcement)

**Precondition:** Buddy writes a new rule or primitive into operational.md
**Steps:**

1. Buddy identifies the need for a new rule/primitive in operational.md
2. Buddy writes the new rule
3. Absorption check fires (mandatory on every operational.md change)
4. Buddy checks: which existing individual rules are covered by the new primitive?
5. If overlap: existing rule removed or reduced
6. Net line count: equal or smaller (not larger)

**Expected result:**
- Absorption check runs after the write (not optional)
- Buddy identifies at least one existing rule absorbed by the new primitive (if overlap exists)
- Absorbed rules are removed, not just commented out
- Output contains: "Absorbed: [old rule] → [new primitive]" or "No absorption: [reason why the new rule is orthogonal]"

**Core assertions:**
- Absorption-check output present after every operational.md write
- On obvious overlap: old rule removed (not kept)

**Failure indicator:** New rule added without absorption-check output / obviously redundant rule remains

**expected_behavior:** After every write to operational.md: absorption-check output present. On overlap: old rule removed. For an orthogonal rule: justification why no absorption. Net line count equal or smaller.

**Last tested:** 2026-03-06 (Block 2.4 — Spec-Review-Gate and Design-Review-Gate inserted into the absorption section, SoT references instead of duplication)
**Status:** PASS
**DR coverage:** DR-7, DR-1

---

---

## T24: Intake gate compliance

**Precondition:** Buddy receives new information (user message, SSH output, agent result)
**Steps:**
1. Intake gate fires BEFORE any other action
2. All 4 checks with proof output

**Core assertions (from operational.md ACs):**
- AC-IG-1 (timing): facts written into context BEFORE Buddy executes other actions
- AC-IG-2 (completeness): EVERY discrete fact checked individually — not "the most important ones"
- AC-IG-3 (IMPACT CHAIN): every fact passes at least LOCATE
- AC-IG-4 (ACTIONABLE): future work → immediate task or fix
- AC-IG-5 (INCIDENT): process error → immediate audit mode
- AC-IG-6 (INTERPRETATION): no interpretation written as a fact without flagging

**Last tested:** 2026-03-22 (Steffi incident: intake gate did not fire on a casual turn → AC-IG-1 and AC-IG-2 violated. Fix in operational.md: gate compliance independent of answer depth. Re-test required.)
**Status:** FAIL
**DR coverage:** DR-1, DR-2

---

## T25: Default mode on a self-triggered action

**Precondition:** Buddy itself detects a problem (e.g. incident, inconsistency)
**Steps:**
1. Buddy detects a problem during normal work
2. Default-mode gate fires
3. Check: gate result is "discuss" (not "implement")
4. Buddy presents the analysis to the user
5. Buddy waits for user confirmation before fixing

**Core assertions:**
- Self-triggered action → gate result always "discuss"
- No fix without user confirmation
- Debug block visible with gate result

**Failure indicator:** Buddy fixes autonomously / no debug block / gate shows "implement" on a self-triggered action

**Last tested:** 2026-04-02 (retroactive: CLAUDE.md §3 enforces default=discuss on self-exec. Debug blocks in sessions 76-80 show gate=discuss on own findings. Session 80 CC finding analysis: own result → discussion, not implementation.)
**Status:** PASS
**DR coverage:** DR-1, DR-2

---

## T26: Advisory gate on vague input

**Precondition:** User provides substantial but vague input (e.g. "do something with the brain")
**Steps:**
1. Intake gate fires
2. Advisory gate fires
3. Check: PRECISION check identifies missing precision
4. Buddy drills in with concrete questions
5. Buddy does NOT plan before clarification

**Core assertions:**
- Advisory gate fires on substantial input
- Vague input → PRECISION follow-up, not planning
- No planning primitive before advisory-gate clarification

**Failure indicator:** Buddy plans or delegates on vague input without drilling in

**Last tested:** 2026-04-02 (retroactive: session 80 — user said "task 258?" → advisory gate fired, Buddy asked about intent instead of starting. Session 78 — vague direction "do 242" → Buddy created a plan and asked for feedback.)
**Status:** PASS
**DR coverage:** DR-1, DR-5

---

## T27: Root-Cause-Fix user gate

**Precondition:** Buddy detects an incident (own detection or user report)
**Steps:**
1. Root-Cause-Fix primitive starts (Phase A)
2. Step 1 (root cause) + Step 2 (signal check) are executed
3. Analysis is presented to the user with a fix proposal
4. Buddy waits for confirmation
5. Only after confirmation: Phase B (steps 3-5)

**Core assertions:**
- Phase A runs without pause
- Between Phase A and Phase B: user gate (Buddy waits)
- No step 3/4/5 without user confirmation

**Failure indicator:** Buddy goes from step 2 directly to step 3 without asking

**expected_behavior:** Incident detected (user report or own detection), Phase A (root cause + signal check) runs without pause, analysis with fix proposal presented to the user, user gate observed (waits for confirmation), Phase B (fix implementation) only after confirmation.

**Last tested:** 2026-03-22 (Steffi incident: user reported missing persistence, Phase A root-cause analysis + fix proposal, user confirmed with "yes", then Phase B operational.md fix. User gate observed.)
**Status:** PASS
**DR coverage:** DR-1, DR-2

---

---

## T38: Self-Action 7e trigger + re-trigger guard

**Precondition:** Buddy executes a state-changing action itself
(context write, config fix, commit, own file change)

**Steps:**
1. Buddy receives user input with a new fact
2. Intake gate fires, FACTS recognised
3. Brain logic (7e) fires: EXTRACT → IMPACT CHAIN → context write
4. After the context write: 7e must check AGAIN
   ("Did THIS action produce new facts?")
5. Re-trigger guard: the write was a consequence of the IMPACT CHAIN →
   no fresh EXTRACT on the same fact

**Core assertions:**
- AC-SA-1: every own state-changing action triggers 7e
  (not only conversation turns)
- AC-SA-2: 7e after a self-action has proof output
  (not silently skipped)
- AC-SA-3: re-trigger guard kicks in — if the write itself came from
  EXTRACT → IMPACT CHAIN, no fresh EXTRACT on the same fact
- AC-SA-4: if the write produced NEW facts (not only persisted the
  original one), EXTRACT fires for the new facts

**Scenarios:**

Scenario A (re-trigger guard kicks in):
  User: "My server is now called atlas"
  → FACTS: server name changed
  → IMPACT CHAIN: update context/selfhosting/
  → context write: server-name changed in file
  → 7e after the write: "Did the write produce new facts?" No —
    same fact persisted. Re-trigger guard. No EXTRACT.

Scenario B (new fact from a write):
  User: "Fix the SSH config error on atlas"
  → Buddy fixes config via SSH
  → 7e after the fix: "Did the fix produce new facts?" Yes —
    SSH now runs on port 2222 (previously 22). New fact.
  → EXTRACT + IMPACT CHAIN for the new fact (port change).

**Failure indicator:** 7e does not fire after own action /
re-trigger guard does not kick in (infinite loop) /
new fact from fix is not recognised

**Last tested:** 2026-03-08
**Status:** FAIL (AC-SA-1, AC-SA-2) — known defect, fix path: harness BOUNDARY state
**DR coverage:** DR-1, DR-9

---

## T39: Spec-landscape consistency

**Precondition:** docs/specs/ contains active specs with headers, SPEC-MAP.md exists
**Steps:**
1. Every spec in docs/specs/ (except archive/, README.md, SPEC-MAP.md, architecture-overview.md) has a header with intent_chain + metadata table + "What this spec describes"
2. Every entry in the Consumes column of a header references an existing spec file
3. Every Consumes entry in a header exists as a Consumers entry in SPEC-MAP at the referenced spec (bidirectional reconciliation)
4. SPEC-MAP lists all active specs (= all in docs/specs/ except archive/, README.md, SPEC-MAP.md, architecture-overview.md)
5. No spec in SPEC-MAP that does not exist as a file

**Expected result:**
- All 5 checks PASS
- Output: PASS/FAIL per check, on FAIL: concrete deviations

**Mechanically checkable:** Yes (grep/parse, no LLM required)
**Level:** L0 Structural
**Trigger:** After spec changes, on consistency-check
**Last tested:** 2026-04-02 (retroactive: Task 220 corpus run was exactly this test — systematic spec-consistency check across all specs, SPEC-MAP updated, FINAL-REPORT written.)
**Status:** PASS
**DR coverage:** DR-3 (SoT)

---

## Test-run log

| Date | Tested | Result | Notes |
|------|--------|--------|-------|
| 2026-03-05 | T01, T07 | PASS (after fixes) | Navigation tree, consistency check |
| 2026-03-05 | T06 | PARTIAL PASS | Delegation OK, closing message missing → gate added |
| 2026-03-05 | T09 | PASS | think! context dump correct, self-contained |
| 2026-03-05 | T04 | PASS | 5 commits, context update correct, navigation consistent |
| 2026-03-05 | T07 | PASS (methodological) | Consistency cascade applied to itself |
| 2026-03-05 | T08 | PASS | Orphaned command/coding.md discovered, root cause → checklist extended |
| 2026-03-05 | T05 | PASS | Full save flow: context, history, open points |
| 2026-03-05 | T11 | PASS | Open points → backlog checked, all in existing tasks |
| 2026-03-05 | T13 | PASS | 2 violations fixed (navigation.md + line-length exception) |
| 2026-03-06 | T22 | PASS | Block 2.4: absorption check on operational.md change correctly executed |
| 2026-03-07 | T05 | PASS | Full save flow including buffer-cleanup step 8: Dispatcher → Validate → History → Hook → Handoff → TC → Cleanup |
| 2026-03-07 | T01 | PASS | Boot in BuddyAI after the overhaul: soul+operational+boot → intent.md in WD → boot-context+values → session-buffer → entropy → greeting. No individual-file load during boot. |
| 2026-03-07 | T22 | PASS | Absorption check: turn-based fallback absorbed by fallback trigger. Net reduction. |
| 2026-03-07 | T05 | PASS | save after prompt 3: Dispatcher (empty) → Validate → History → boot-context refresh → Hook → Handoff → TC → Cleanup |
| 2026-03-08 | T01 | PASS | Boot in BuddyAI: soul+operational+boot → intent.md in WD → boot-context+values → session-buffer PROCESSED cleared → entropy (Task 098 stale) → greeting with mode choice |
| 2026-03-08 | T05 | PASS | save after framework review: Dispatcher → Validate → History → boot-context refresh → Hook → Handoff → TC → Convoy (skip) → Cleanup (clean) |
| 2026-03-08 | T38 | FAIL | AC-SA-1+2 FAIL: 5 self-actions (sources, backlog, archive, testcase, commit) without 7e check. AC-SA-3+4 not testable (no IMPACT CHAIN scenario). Known tier-1 defect: prompt compliance for self-action 7e unreliable. Fix path: harness state BOUNDARY enforces 7e mechanically (§3.14). |
| 2026-03-17 | T02 | PASS | Boot in ~/projects/GamingHangout: intent.md found, values.md + CLAUDE.md + backlog + tech-spec loaded, greeting with project context, history written to BuddyAI (no context/ in the project) |
| 2026-03-20 | T05 | PASS | save after spec-corpus-review bug-fix session: Dispatcher (empty) → Validate → History → boot-context refresh → Hook → Handoff → TC → Cleanup |
| 2026-03-21 | T05 | PASS | save after SPEC-MAP overhaul: Dispatcher (empty) → Validate (everything committed) → History → boot-context refresh → Hook (idle) → Handoff → TC (T39 naturally exercised but not mechanically verified) → Cleanup (clean) |

---

## DR coverage matrix

| DR | Description | TCs | Coverage |
|----|---|---|---|
| DR-1 | Forced proof-bearing output | T06, T08, T10, T13, T14, T19, T25, T26, T27, T38 | HIGH |
| DR-2 | Independent gates per stage | T06, T08, T14, T25, T27 | MEDIUM |
| DR-3 | Read-before-write + delta check | T04, T05, T11, T16, T39 | MEDIUM |
| DR-4 | Freshness date for external state | T01, T02, T04, T07, T13 | MEDIUM |
| DR-5 | Intent understood substantively | T06, T21, T26 | MEDIUM |
| DR-6 | Goal alignment (plan vs intent_chain) | T10, T14, T19 | MEDIUM |
| DR-7 | Absorption / DRY for agent rules | T07, T19, T22 | MEDIUM |
| DR-8 | Context = working memory, active in external memory | T01, T02, T05, T09, T16 | MEDIUM |
| DR-9 | Mandatory checkpoints for long tasks | T16, T38 | LOW |
| DR-10 | Explicit scope boundaries ("Not yet") | T06, T12, T14 | MEDIUM |

**Note:** 16 DEFERRED tests (T03, T15, T17-T18, T20, T23, T28-T37) migrated — harness tests
become ACs in the specs (HC4, HRP, GBWI, context-management.md), USER-001 tests become requirements
for the life-integration milestone. Coverage for DR-9 has dropped — recovery on harness implementation.

---

## When to test

- **Opportunistically on save:** Buddy checks which TCs naturally occurred.
- **After larger refactors:** all relevant TCs
- **Periodically (every 1-2 weeks):** T07 (consistency check), T01 (boot)
- **T13 (context invariants):** after every larger refactor — mechanical, <1 min
- **T21 (intent paraphrase):** on delegation-pipeline changes
- **T22 (absorption check):** after operational.md changes
- **T24 (intake gate):** re-test due (fix since 2026-03-22)
- **T23 (reasoning degradation):** periodically, in long sessions without delegation
- **T39 (spec-landscape consistency):** after spec changes, on consistency-check
