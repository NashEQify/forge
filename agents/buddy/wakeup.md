# Buddy — Wakeup

Session continuity: full context after a fresh boot.
Trigger: user says `wakeup`.

## What wakeup does

Boot loaded the minimum (the profile and the session handoff).
Wakeup expands to a full overview:

1. **Deepen plan state:** run
   `python3 $FRAMEWORK_DIR/scripts/plan_engine.py --status` for the
   full milestone overview.
   `python3 $FRAMEWORK_DIR/scripts/plan_engine.py --critical-path`
   for the detailed path.
2. **History:** the last 5 entries from `context/history/`.
3. **On-demand reload:** whatever is listed in the Context field
   under "On-demand" — filtered by relevance: in-progress tasks →
   load their task YAML + MD. History points to active areas → load
   their overview.md. Not blind everything.
4. **Task resume:** in-progress tasks from the --boot output →
   offer to resume. For active tasks: task YAML → spec_ref → load
   the spec when needed.
5. **Confirmation:** 3-5 sentences: what's known, what happened
   last, what's relevant now.

## Proactive spec readiness

On wakeup: read `$FRAMEWORK_DIR/scripts/plan_engine.py --next`.
At most one offer per wakeup: "Task X is ready and has
blocking_score Y — start it?"
