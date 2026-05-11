#!/usr/bin/env bash
set -euo pipefail

# workflow-commit-gate.sh — PreToolUse(Bash) Hook for BuddyAI Workflow Engine (Task 321)
#
# Called by Claude Code on every Bash tool invocation. Checks if the command
# is a git commit and, if so, validates against the Workflow Engine.
# Non-commit commands pass through immediately (<50ms).
#
# F-CQ-003 fix (Task 324): Removed Task-NNN message parsing which failed on
# Heredoc commits (the primary commit style of Claude Code). Instead, always
# runs engine validation when any active workflow exists. The engine's
# validate_commit_gates only checks gates up to current_step, so future gates
# do not cause false blocks.
#
# stdin:  JSON payload from CC with tool_input.command
# stdout: JSON with permissionDecision "deny" if commit blocked
# Exit 0 ALWAYS — graceful degradation on any error.

FRAMEWORK_ROOT="$(cd "$(dirname "$(readlink -f "$0")")/../../.." && pwd)"

# Read stdin — CC sends hook payload on stdin
INPUT=$(cat 2>/dev/null) || exit 0

# Check jq availability — without it we cannot parse, so allow through
if ! command -v jq &>/dev/null; then
  exit 0
fi

# Extract command from payload
CMD=$(echo "$INPUT" | jq -r '.tool_input.command // empty' 2>/dev/null) || exit 0

# Fast path: not a git commit → allow immediately
if ! echo "$CMD" | grep -qE '^git commit|; *git commit|&& *git commit'; then
  exit 0
fi

# Check if any active workflow exists (fast check before calling engine)
ACTIVE_TASKS=$(python3 "${FRAMEWORK_ROOT}/scripts/workflow_engine.py" --list --format json 2>/dev/null) || exit 0

HAS_ACTIVE=$(echo "$ACTIVE_TASKS" | jq -e '.active | length > 0' 2>/dev/null) || exit 0

if [ "$HAS_ACTIVE" != "true" ]; then
  # No active workflows → nothing to gate
  exit 0
fi

# Active workflow exists → validate commit gates with Engine
# Engine only checks gates up to current_step — future gates are not checked.
RESULT=$(python3 "${FRAMEWORK_ROOT}/scripts/workflow_engine.py" --validate --before-commit 2>&1) || {
  EXIT_CODE=$?
  # Block only reaches here on non-zero exit (engine says FAIL)
  # Sanitize RESULT for JSON embedding (escape quotes and newlines)
  SAFE_RESULT=$(echo "$RESULT" | tr '\n' ' ' | sed 's/"/\\"/g')
  cat <<ENDJSON
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "deny",
    "permissionDecisionReason": "Workflow-Engine: ${SAFE_RESULT}"
  }
}
ENDJSON
  exit 0
}

# Engine PASS or no engine available → allow
exit 0
