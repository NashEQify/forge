# Buddy — Software start

Step-loaded unit of `agents/buddy/boot.md`. Read it at boot step 3 when the
workflow selection is software: it holds steps 4–7 of boot.md's boot sequence
(ROUTE, LOAD, RESUME, GREET); step numbers continue that sequence. boot.md's
§Boot rules apply to steps 4 and 5.

4. **ROUTE:** decide context routing (read and write paths for the
   session). CWD comes from ORIENT.
   - The boot probe's `context-dir:` line (a filesystem check; don't infer
     from intent.md).
     `present` → context write path = `<CWD>/context/`.
     `absent` → the write path is still `<CWD>/context/`, created at the first
     write there, not at boot (`boot-routing.md` §Context routing).
   - **Project docs:** if RESOLVE found an intent.md, the probe's `backlog:`
     line: `present` → the project has a local docs/ (backlog, tasks, specs)
     for the session; `absent` → no local backlog.
   The result holds for the entire session. Rules: `boot-routing.md`
   §Context routing.
5. **LOAD:** two categories: always-load (Buddy
   infrastructure, scope-independent) + intent-load (from the
   Context field of the active intent.md).
   - **always-load** (Buddy tier, every session):
     - **User profile** — `<user_repo>/context/user/profile.md`
       (`boot.md` §User scope: who the user is, including values and priorities), CWD-independent (who the user is —
       minimal context), read through one personal snapshot that also returns
       personal pending status:
       `python3 $FRAMEWORK_DIR/scripts/continuity.py snapshot --scope personal --project-root <CWD>`
       with `{"schema_version":1,"paths":["profile.md"]}` on stdin (the helper
       finds the user repo; personal paths are relative to its `context/user/`);
       read its JSON output directly, without writing it to a file.
       Non-empty `pending_operations` is pending recovery (`boot-status.md` §Greeting findings). No user scope
       → nothing to load.
     - The boot probe's `chub:` line — presence check for the `chub` CLI
       (get_api_docs prerequisite). `installed`, or exactly `not installed`
       (the check is not part of this installation): nothing to report; any
       other value is one advisory line for GREET.
     - Not at boot: the skill index `framework/boot-navigation.md`. Read it
       before choosing a workflow or skill for substantial work, when the user
       asks for a Forge skill, workflow, Council or board, and on Codex before
       choosing any skill or workflow: routing without it misses skills no
       workflow names.
   - **intent-load** (project-specific):
     - Whatever the Context field lists under "Boot". That, and
       nothing else.
     - Local backlog: if ROUTE (step 4) found one → load it.
     - Context field missing in intent.md: derive from Vision +
       Non-Goals; ask if uncertain.
   - No intent.md found: only always-load, then create intent.md
     together.
6. **RESUME:** a session handoff the probe found (`handoff:`) is read in
   Round 2, completely, with a pending session buffer (`session-buffer: pending
   N`). It carries the last session's context (open goals/state, leading files
   and next steps/blockers, with necessary decisions, approvals and failed
   attempts). Approvals recorded there keep their stated scope and duration:
   do not renew an old host or session approval or carry it to other targets.
   Every other unit loads at the step that uses it, through that step's own read
   trigger, not at boot. A request that takes up the handoff's work or an
   in-progress task binds it through `framework/development-continuation.md`
   before that work progresses; do not infer selection from task, plan or state
   files alone.
7. **GREET:** short greeting (style: soul.md).

   Report the boot findings (STATUS-CHECK, held-back work, user-scope warnings,
   workflow resume) per `agents/buddy/boot-status.md` §Greeting findings.
