---
description: Solution Expert – architecture decisions, ADR-style thinking, Architecture Board
mode: subagent
model: anthropic/claude-opus-4-6
temperature: 0.2
tools:
  read: true
  bash: true
permission:
  edit: deny
  bash:
    "*": deny
    "ls*": allow
    "cat*": allow
    "head*": allow
    "tail*": allow
    "grep*": allow
    "rg*": allow
    "find*": allow
    "pwd*": allow
    "wc*": allow
    "file*": allow
    "stat*": allow
    "tree*": allow
    "jq*": allow
---

Lade und befolge @$FRAMEWORK_DIR/agents/solution-expert.md
