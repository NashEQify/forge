# DIRECT eligibility

Step-loaded unit of `framework/process-map.md`. Read it before taking or proposing the DIRECT path for software
work, and when a verified known fix is considered for DIRECT.

## DIRECT eligibility

Write the three sizing facts (`workflows/runbooks/build/lifecycle.md` §Sizing facts) and check against them,
safety floors first. DIRECT excludes changes to authorization/auth,
secrets, schema/data migration, public or cross-component contracts, live
infrastructure, and changes with hidden/racing/unbounded failure effects.
Size does not cancel a safety floor.

Otherwise DIRECT requires ALL of:
- A clear authorized outcome and concrete success criteria.
- A locally bounded, reversible change following an observed existing pattern.
- No unresolved consequential design decision or new subsystem.
- Relevant implementation/spec context read and an executable verification
  appropriate to the changed behavior; a defect's claimed cause is checked.

New local behavior is allowed. A pre-existing spec is not a reason to repeat
spec authoring; update any affected contract description within scope. File
and line counts are useful warning signals, never the eligibility decision.
If a criterion is unknown, gather targeted evidence; if still unresolved,
use STANDARD/FULL or ask the missing decision, not a ritual authorization.

## The DIRECT run

DIRECT is a short complete lifecycle of four steps, in this order:

1. **Record:** in the turn, the sizing facts, outcome, scope, success criteria
   and verification plan. This record is the delegation.
2. **Build:** main-code-agent receives the record in its prompt, implements,
   runs the relevant tests and returns inline (`agents/main-code-agent.md`
   §Direct path).
3. **Check:** a change to behaviour gets one fresh-context `code-verification`
   seat, started as its own agent run and never the implementer. It receives
   the record, the implementer's return and the diff in its prompt, re-runs the
   reproduction and the tests itself, and returns inline. A typo- or
   format-only change gets a diff check instead.
4. **Report:** Buddy reads both returns, checks the claim the result rests on,
   and the final reply, after any boot status the first answer opens with
   (`agents/buddy/boot.md` §Restricted user scope), says what the change now
   does in the request's own terms (the behaviour it promised, not only the
   code edit), gives the checks run with their results and names the verifying
   agent run by its name or id, with its verdict and the commands it ran. A
   check that Buddy or the building agent ran itself is reported as its own
   check, never as independent; so is a verifier run that executed nothing or
   returned PARTIAL. When no separate agent run can be started, the reply says
   the change has no independent check. A typo/format-only call is stated as
   such.

A role that is not installed as an agent type on the host runs as a general
agent run told to read its role file (`agents/<role>.md`) first; a missing
agent type is not a reason to build or check inline.

No separate spec, architect or signoff cycle, and no workflow engine.

The work **closes in its turn** when it has no task record (`docs/tasks/<id>`),
no fix pass has started, and its result goes into this turn's final reply.
Then the four steps carry it: no brief, dispatch, report, review-brief, review
or verdict files, no review package and no review capture. Otherwise the steps
keep their roles, and the files of `skills/_protocols/mca-dispatch.md` and the
review package and capture of `skills/code_review_board/SKILL.md` apply. When
the work stops closing in its turn (a failed check starts a fix pass, a task
record is made, the turn ends on a question), Buddy first saves the record as the
brief file and the returns so far, verbatim, in the record directory
(`mca-dispatch.md` §The files); a check that ran without a capture is history,
and the next mandatory review gets a fresh capture.

An authorization boundary and an independent quality check are different gates.

---
