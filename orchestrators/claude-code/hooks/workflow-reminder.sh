#!/usr/bin/env bash
set -euo pipefail

# workflow-reminder.sh — UserPromptSubmit Hook for the forge Workflow Engine.
#
# Called by Claude Code when the user submits a prompt — BEFORE the LLM
# responds. Injects the current workflow step as additionalContext into
# the LLM's context. UserPromptSubmit is the only hook type that can
# inject context the LLM actually sees.
#
# Buddy boot is NOT this hook's job. Boot is owned by SessionStart:
#   - cc (terminal launcher) injects via --agent buddy + system-prompt
#   - claude --agent buddy (Quick CLI) loads persona via --agent flag
#   - claude-desktop / claude-web: orchestrators/claude-code/hooks/
#     buddy-boot-inject.sh (SessionStart hook) emits the boot instruction
# Per-host trigger; deterministic; no UserPromptSubmit fallback needed.
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
NEXT=$(timeout 2 python3 "${FRAMEWORK_ROOT}/scripts/workflow_engine.py" --next --brief 2>/dev/null) || NEXT=""

# Hard-cap WORKFLOW segment at 200 chars to prevent token-spam from
# verbose context_refs / instruction strings.
CONTEXT=""
if [ -n "$NEXT" ]; then
  SAFE_NEXT=$(echo "$NEXT" | tr '\n' ' ' | sed 's/"/\\"/g')
  if [ ${#SAFE_NEXT} -gt 200 ]; then
    SAFE_NEXT="${SAFE_NEXT:0:197}..."
  fi
  CONTEXT="WORKFLOW-ENGINE: ${SAFE_NEXT}"
fi

cat <<ENDJSON
{
  "hookSpecificOutput": {
    "hookEventName": "UserPromptSubmit",
    "additionalContext": "${CONTEXT}"
  }
}
ENDJSON

exit 0
