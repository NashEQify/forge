#!/usr/bin/env bash
# state-write-block.sh — PreToolUse(Write/Edit) Hook for BuddyAI Workflow Engine
#
# Blocks direct Write/Edit operations on .workflow-state/ files.
# The LLM must use workflow_engine.py CLI to modify state.
#
# stdin:  JSON payload from CC with tool_input.file_path
# stdout: JSON with permissionDecision "deny" if blocked
# Exit 0 ALWAYS — graceful degradation on any error.

INPUT=$(cat 2>/dev/null) || exit 0
FILE=$(echo "$INPUT" | jq -r '.tool_input.file_path // empty' 2>/dev/null) || exit 0

if echo "$FILE" | grep -qF '.workflow-state/'; then
  cat <<ENDJSON
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "deny",
    "permissionDecisionReason": "Write to .workflow-state/ blocked. Use workflow_engine.py CLI."
  }
}
ENDJSON
fi
exit 0
