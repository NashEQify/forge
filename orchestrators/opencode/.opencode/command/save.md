---
description: Buddy speichert – Session-Persistenz (mid + end of session)
agent: buddy
---
Fuehre /save aus: Durchlaufe den kanonischen save-Workflow (`workflows/runbooks/save/WORKFLOW.md`) – das eine adaptive Save-Kommando fuer mid- und end-of-session. Schritte: Dispatcher (session-buffer triage) → Reconciliation (gap-check + task-status + `plan_engine --validate`) → Handoff-Merge (`.bak` + merge-default) → History-Eintrag (bei Task-Closeout) → Commit + Push → Buffer-Cleanup. Kein separates quicksave – der Footprint passt sich an.
