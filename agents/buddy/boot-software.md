# Buddy — Software start

Step-loaded unit of `agents/buddy/boot.md`. Read it at boot step 3 when the
workflow selection is software: it holds steps 4–7 of boot.md's boot sequence
(ROUTE, LOAD, RESUME, GREET); step numbers continue that sequence. boot.md's
§Boot rules apply to these steps.

4. **ROUTE:** decide context routing (read and write paths for the
   session). CWD comes from ORIENT.
   - Run `ls <CWD>/context/` (MUST — filesystem check, don't infer
     from intent.md).
     Found → context write path = `<CWD>/context/`.
     Not found → auto-create `<CWD>/context/` with `history/` +
     `overview.md`, then write project-local (see `boot-routing.md` §Context routing).
   - **Project docs:** if RESOLVE found an intent.md, run
     `ls <CWD>/docs/backlog.md` (MUST).
     Found → the project has a local docs/ (backlog, tasks, specs)
     for the session.
     Not found → no local backlog.
   The result holds for the entire session. Rules: `boot-routing.md`
   §Context routing.
5. **LOAD:** first follow `framework/continuity.md` for scoped recovery checks
   and coherent snapshots of required profile/project context. Pending work blocks
   dependent use until reconciled or explicitly qualified. Then load context. Two categories: always-load (Buddy
   infrastructure, scope-independent) + intent-load (from the
   Context field of the active intent.md).
   - **always-load** (Buddy tier, every session):
     - **User profile** — `<user_repo>/context/user/profile.md`
       (`boot.md` §User scope: who the user is, including values and priorities), CWD-independent (who the user is —
       minimal context). No user scope → nothing to load.
     - `bash $FRAMEWORK_DIR/scripts/chub-status-check.sh` — presence
       check for the `chub` CLI (get_api_docs prerequisite). Empty
       output = installed; non-empty = one advisory line for GREET.
     - `$FRAMEWORK_DIR/framework/boot-navigation.md` — skill index
       (25 skills + 10 workflows). Without it, Buddy boots without
       the skill landscape in mind. Explicit-absolute (consumer-CWD
       convention).
   - **intent-load** (project-specific):
     - Whatever the Context field lists under "Boot". That, and
       nothing else.
     - Local backlog: if ROUTE (step 4) found one → load it.
     - Context field missing in intent.md: derive from Vision +
       Non-Goals; ask if uncertain.
   - No intent.md found: only always-load, then create intent.md
     together.
6. **RESUME:** load session state.
   - `session-buffer.md`: `<CWD>/docs/session-buffer.md` (repo-
     local). PENDING → dispatcher, PROCESSED → remove. Not found →
     skip.
   - **Root session:** run
     `python3 $FRAMEWORK_DIR/scripts/plan_engine.py --boot`. The
     output gives in-progress tasks, critical path, next actions,
     milestone status, warnings. NEXT ACTIONS ranks graph readiness;
     where the project keeps a programme agreement, its order decides
     the next task.
   - **Selected development continuation:** load the existing handoff through
     `framework/continuity.md` with pending status, then use
     `framework/development-continuation.md` to restore explicit bindings without
     advancing or unpausing. Software intent binds task/plan-only checks even with
     no workflow IDs. Legacy selected work requires explicit session evidence;
     ambiguous selection blocks exact continuation, never binds every active run.
   - **Session handoff:** `<CWD>/context/session-handoff.md`. The
     handoff carries the discussion context from the last session
     (open goals/state, leading files and next steps/blockers, with necessary decisions, approvals and failed attempts). Not
     found → fresh start. Approvals recorded there keep their stated scope and
     duration: do not renew an old host or session approval or carry it to
     other targets.
   - After the applicable freshness and recovery sequence, read and follow
     `framework/context-and-loading.md` §Buddy coordination refresh before
     continuing resumed coordination.
7. **GREET:** short greeting (style: soul.md).

   Report the boot findings (STATUS-CHECK, held-back work, user-scope warnings,
   workflow resume) per `agents/buddy/boot-status.md` §Greeting findings.
