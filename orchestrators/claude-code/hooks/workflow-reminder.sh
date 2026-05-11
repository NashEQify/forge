#!/usr/bin/env bash
set -euo pipefail

# workflow-reminder.sh — UserPromptSubmit Hook for BuddyAI Workflow Engine
#
# Called by Claude Code when the user submits a prompt — BEFORE the LLM responds.
# Injects current workflow step as additionalContext into the LLM's context.
# This is the ONLY hook type that can inject context the LLM actually sees.
#
# Stop hooks only show systemMessage to the user (UI), NOT to the LLM.
# UserPromptSubmit hooks inject additionalContext into model context (required field).
#
# stdin:  JSON payload from CC
# stdout: JSON with hookSpecificOutput.additionalContext
# Exit 0 ALWAYS — graceful degradation on any error.

FRAMEWORK_ROOT="$(cd "$(dirname "$(readlink -f "$0")")/../../.." && pwd)"

# Consume stdin
cat > /dev/null 2>&1 || true

# Query engine for next step. Hard cap 2s — stays within CC's 3s hook
# budget even if engine is slow (e.g. yaml-load latency on power-user
# repos). Engine guard-evaluation (subprocess up to 30s) is NOT in --brief
# fast-path — that's evaluation-time at --complete/--start, not here.
NEXT=$(timeout 2 python3 "${FRAMEWORK_ROOT}/scripts/workflow_engine.py" --next --brief 2>/dev/null) || exit 0

# Hard-cap additionalContext at 200 chars to prevent token-spam from
# verbose context_refs / instruction strings.
if [ -n "$NEXT" ]; then
  SAFE_NEXT=$(echo "$NEXT" | tr '\n' ' ' | sed 's/"/\\"/g')
  if [ ${#SAFE_NEXT} -gt 200 ]; then
    SAFE_NEXT="${SAFE_NEXT:0:197}..."
  fi
  cat <<ENDJSON
{
  "hookSpecificOutput": {
    "hookEventName": "UserPromptSubmit",
    "additionalContext": "WORKFLOW-ENGINE: ${SAFE_NEXT}"
  }
}
ENDJSON
else
  # additionalContext is required for UserPromptSubmit — send empty if no workflow
  cat <<ENDJSON
{
  "hookSpecificOutput": {
    "hookEventName": "UserPromptSubmit",
    "additionalContext": ""
  }
}
ENDJSON
fi

exit 0
