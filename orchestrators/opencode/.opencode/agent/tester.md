---
description: "Spec-driven Test-Engineer: Design-Modus (Spec→Test-Plan) + Execution-Modus (Tests schreiben+ausfuehren)"
mode: subagent
model: anthropic/claude-sonnet-4-6
temperature: 0.1
tools:
  read: true
  edit: true
  write: true
  bash: true
permission:
  bash:
    "*": deny

    # Safe shell introspection
    "ls*": allow
    "pwd*": allow
    "which*": allow

    # Flutter / Dart quality gate
    "flutter --version*": allow
    "flutter doctor*": allow
    "flutter devices*": allow
    "flutter config*": allow
    "flutter analyze*": allow
    "flutter test*": allow
    "flutter pub get*": allow
    "dart test*": allow

    # Headless UI/E2E on Linux Desktop
    "xvfb-run*": allow

    # Other ecosystems
    "python -m pytest*": allow
    "pytest*": allow
    "python -m unittest*": allow
    "npm test*": allow
    "npm run *": allow
    "npm run test*": allow
    "yarn test*": allow
    "pnpm test*": allow
    "bun test*": allow
    "jest*": allow
    "vitest*": allow
    "cargo test*": allow
    "go test*": allow
    "mvn test*": allow
    "gradle test*": allow

    # Explicitly denied (keep deterministic + no networking/infra ops)
    "curl*": deny
    "uvicorn*": deny
    "docker*": deny
    "docker compose*": deny
---

Lade und befolge @$FRAMEWORK_DIR/agents/tester.md
