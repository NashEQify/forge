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

# --- Buddy boot reminder ---
# Each ephemeral container starts without persona-load. CLAUDE.md says
# "Load and follow: agents/buddy/{soul,operational,boot}.md" — but the
# default Claude Code agent does not act on that statement until it
# actually reads those files. The marker .workflow-state/buddy-boot-ack
# is set after the agent boots. Container is fresh → marker absent →
# we inject a BOOT instruction so the next turn must do the read.
BOOT_ACK="${CLAUDE_PROJECT_DIR:-$FRAMEWORK_ROOT}/.workflow-state/buddy-boot-ack"
BOOT_PREFIX=""
if [ ! -f "$BOOT_ACK" ]; then
  BOOT_PREFIX="BUDDY-BOOT REQUIRED: read agents/buddy/soul.md + operational.md + boot.md NOW and follow them as the buddy persona. After reading, run: mkdir -p .workflow-state && touch .workflow-state/buddy-boot-ack — this suppresses the reminder for the rest of the session. "
fi

# Query engine for next step. Hard cap 2s — stays within CC's 3s hook
# budget even if engine is slow (e.g. yaml-load latency on power-user
# repos). Engine guard-evaluation (subprocess up to 30s) is NOT in --brief
# fast-path — that's evaluation-time at --complete/--start, not here.
NEXT=$(timeout 2 python3 "${FRAMEWORK_ROOT}/scripts/workflow_engine.py" --next --brief 2>/dev/null) || NEXT=""

# Hard-cap WORKFLOW segment at 200 chars to prevent token-spam from
# verbose context_refs / instruction strings. Boot prefix is exempt
# from the cap — it's a one-time critical instruction per container.
WORKFLOW_SEGMENT=""
if [ -n "$NEXT" ]; then
  SAFE_NEXT=$(echo "$NEXT" | tr '\n' ' ' | sed 's/"/\\"/g')
  if [ ${#SAFE_NEXT} -gt 200 ]; then
    SAFE_NEXT="${SAFE_NEXT:0:197}..."
  fi
  WORKFLOW_SEGMENT="WORKFLOW-ENGINE: ${SAFE_NEXT}"
fi

CONTEXT="${BOOT_PREFIX}${WORKFLOW_SEGMENT}"

cat <<ENDJSON
{
  "hookSpecificOutput": {
    "hookEventName": "UserPromptSubmit",
    "additionalContext": "${CONTEXT}"
  }
}
ENDJSON

exit 0
