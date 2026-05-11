#!/usr/bin/env bash
# mca-return-stop-condition.sh — PostToolUse(Task) hook [Item 2 post-388]
#
# Re-interpretation of dogfooding §7.6 (Stop-Condition mechanic enforcement)
# as a *warn-only* heuristic on tool_response when subagent_type=main-code-agent.
#
# Pattern-Lesson 388 F-CR-004: MCA reported "Stop-Condition 4 (Architecture-
# Konflikt-Eskalation)" in Return-Summary. Buddy autonom-resolved instead of
# escalating to User. Cost: Welle-2 verification work.
#
# This hook parses MCA's Return-Summary for Stop-Condition keywords and
# emits stderr WARN if detected — Buddy sees it in next turn-context and
# is forced to acknowledge before proceeding.
#
# Matcher: Task (filtered to subagent_type=main-code-agent inside)
#
# Core Logic:
#   1. Parse tool_input.subagent_type — only main-code-agent triggers this.
#   2. Parse tool_response (MCA's return text).
#   3. Grep for Stop-Condition keywords (case-insensitive):
#      - "Stop-Condition" / "STOP-CONDITION"
#      - "ESCALATE" / "ESCALATED" / "ESCALATION"
#      - "ARCH-CONFLICT" / "ARCHITECTURE-CONFLICT"
#      - "AUTO-FIXED" (special — needs Buddy retest, not autonom-pass)
#   4. If detected: extract surrounding context line(s), emit WARN to stderr.
#
# Exit codes:
#   0 — always (graceful, never blocks; Buddy-discipline + visible WARN)
#
# CC-hook output: WARN via stderr. Buddy's next-turn context includes hook
# stderr via cc's standard hook-output mechanism.

set -uo pipefail

# ---------- Input resolution ----------

TOOL_INPUT_JSON=""
TOOL_RESPONSE_JSON=""
STDIN_MODE=0

if [ ! -t 0 ]; then
  STDIN_CONTENT=$(cat 2>/dev/null || true)
  if [ -n "$STDIN_CONTENT" ] && command -v jq &>/dev/null; then
    PARSED_TOOL=$(echo "$STDIN_CONTENT" | jq -r '.tool_name // empty' 2>/dev/null || true)
    if [ "$PARSED_TOOL" = "Task" ]; then
      TOOL_INPUT_JSON=$(echo "$STDIN_CONTENT" | jq -c '.tool_input // {}' 2>/dev/null || echo "{}")
      TOOL_RESPONSE_JSON=$(echo "$STDIN_CONTENT" | jq -c '.tool_response // {}' 2>/dev/null || echo "{}")
      STDIN_MODE=1
    fi
  fi
fi

# Fallback: env-vars (standalone test)
if [ -z "$TOOL_INPUT_JSON" ] && [ -n "${CLAUDE_TOOL_INPUT_JSON:-}" ]; then
  TOOL_INPUT_JSON="$CLAUDE_TOOL_INPUT_JSON"
  TOOL_RESPONSE_JSON="${CLAUDE_TOOL_RESPONSE_JSON:-{}}"
fi

# Nothing to parse → graceful exit
if [ -z "$TOOL_INPUT_JSON" ]; then
  exit 0
fi

if ! command -v jq &>/dev/null; then
  exit 0
fi

# ---------- Filter: only main-code-agent ----------

SUBAGENT=$(echo "$TOOL_INPUT_JSON" | jq -r '.subagent_type // empty' 2>/dev/null || true)
if [ "$SUBAGENT" != "main-code-agent" ]; then
  exit 0
fi

# ---------- Extract MCA-Return text ----------

# tool_response varies by harness — try multiple shapes
RESPONSE=$(echo "$TOOL_RESPONSE_JSON" | jq -r '
  if type == "object" then
    (.text // .content // .return // .summary // (. | tostring))
  else (. | tostring) end
' 2>/dev/null || true)

if [ -z "$RESPONSE" ] || [ "$RESPONSE" = "null" ]; then
  exit 0
fi

# ---------- Detect Stop-Condition keywords ----------

# Patterns (case-insensitive). Each pattern triggers a distinct WARN-class.
declare -A PATTERNS=(
  ["Stop-Condition"]="STOP-CONDITION"
  ["ESCALATE"]="ESCALATION"
  ["ESCALATED"]="ESCALATION"
  ["ARCH-CONFLICT"]="ARCHITECTURE-CONFLICT"
  ["ARCHITECTURE-CONFLICT"]="ARCHITECTURE-CONFLICT"
  ["AUTO-FIXED"]="AUTO-FIX"
)

DETECTED=()
for pattern in "${!PATTERNS[@]}"; do
  if echo "$RESPONSE" | grep -qiE "\b${pattern}\b"; then
    klasse="${PATTERNS[$pattern]}"
    # Extract line containing pattern (max 200 chars)
    context=$(echo "$RESPONSE" | grep -iE "\b${pattern}\b" | head -1 | cut -c1-200)
    DETECTED+=("[$klasse] $context")
  fi
done

# Dedup (some patterns map to same Klasse)
if [ ${#DETECTED[@]} -gt 0 ]; then
  # Build unique-by-klasse list
  declare -A SEEN
  UNIQUE=()
  for entry in "${DETECTED[@]}"; do
    klasse=$(echo "$entry" | grep -oE '^\[[A-Z-]+\]' | head -1)
    if [ -z "${SEEN[$klasse]:-}" ]; then
      SEEN[$klasse]=1
      UNIQUE+=("$entry")
    fi
  done

  echo "" >&2
  echo "============================================================" >&2
  echo "mca-return-stop-condition: WARN — MCA-Return enthaelt Stop-/Escalate-Marker." >&2
  echo "Pattern-Lesson 388 F-CR-004: MCA reported Stop-Condition, Buddy autonom-resolved" >&2
  echo "instead of escalating. Buddy MUSS acknowledge BEVOR --complete:" >&2
  echo "" >&2
  for entry in "${UNIQUE[@]}"; do
    echo "  - $entry" >&2
  done
  echo "" >&2
  echo "Action: lese MCA-Return vollstaendig, eskaliere zu User WENN architektur-" >&2
  echo "decision noetig, sonst dokumentiere autonom-resolve mit explicit-Begruendung." >&2
  echo "============================================================" >&2
fi

exit 0
