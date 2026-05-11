---
description: Buddy mit maximaler Denktiefe. Fuer tiefe Spec-Interviews, strategische
  Lebensfragen, komplexe offene Gespraeche. Trigger: "think!" oder Buddy-Vorschlag.
mode: primary
model: anthropic/claude-opus-4-6
temperature: 0.2
permission:
  # SoT: agents/buddy/permissions.md — buddy-thinking hat gleiche Rechte wie Buddy
  edit: allow
  bash:
    "*": allow
---

Lade und befolge @$FRAMEWORK_DIR/agents/buddy-thinking.md
