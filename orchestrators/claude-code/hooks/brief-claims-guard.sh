#!/usr/bin/env bash
# brief-claims-guard.sh — PreToolUse Hook for L-044 Brief-Claims-Verification gate.
#
# Detects trigger formulations in writes to task/spec/brief files:
#   supersedes | reuses existing | already implemented | wraps existing |
#   delivered in Task | existing-code verifications confirm
#
# If a trigger is present in the new content:
#   - No C-VERIFY/verification table found → WARN (allow, with reason)
#   - C-VERIFY present + grep command extractable → re-run the command and
#     compare against the stored Output field. Mismatch → BLOCK (deny).
#
# Anti-hallucination floor: the hook runs the grep itself, so the agent
# cannot fabricate "(no output)" or "5 hits" — the hook's re-run is the
# evidence, not the agent's stored text.
#
# Matcher: Edit | Write | NotebookEdit
#
# Dual-mode invocation:
#   1. CC PreToolUse: JSON on stdin (tool_name + tool_input).
#   2. Standalone test: env CLAUDE_TOOL_NAME + CLAUDE_TOOL_INPUT_JSON.
#
# Exit codes (standalone):
#   0 — PASS (no trigger, or trigger+verification verified, or graceful skip)
#   1 — WARN (trigger present, no C-VERIFY block — agent gets reminder)
#   2 — BLOCK (C-VERIFY re-run mismatched the stored output)

set -uo pipefail

# ---------- Input resolution ----------

TOOL_NAME=""
TOOL_INPUT_JSON=""
STDIN_MODE=0

if [ ! -t 0 ]; then
  STDIN_CONTENT=$(cat 2>/dev/null || true)
  if [ -n "$STDIN_CONTENT" ] && command -v jq &>/dev/null; then
    PARSED_TOOL=$(echo "$STDIN_CONTENT" | jq -r '.tool_name // empty' 2>/dev/null || true)
    if [ -n "$PARSED_TOOL" ]; then
      TOOL_NAME="$PARSED_TOOL"
      TOOL_INPUT_JSON=$(echo "$STDIN_CONTENT" | jq -c '.tool_input // {}' 2>/dev/null || echo "{}")
      STDIN_MODE=1
    fi
  fi
fi

if [ -z "$TOOL_NAME" ]; then
  TOOL_NAME="${CLAUDE_TOOL_NAME:-}"
  TOOL_INPUT_JSON="${CLAUDE_TOOL_INPUT_JSON:-{}}"
fi

[ -z "$TOOL_NAME" ] && exit 0

case "$TOOL_NAME" in
  Edit|Write|NotebookEdit) ;;
  *) exit 0 ;;
esac

command -v jq &>/dev/null || exit 0

FILE_PATH=$(echo "$TOOL_INPUT_JSON" | jq -r '.file_path // empty' 2>/dev/null || true)
[ -z "$FILE_PATH" ] && exit 0

# Scope: only files where claims live
case "$FILE_PATH" in
  */docs/tasks/*.yaml|*/docs/tasks/*.md|\
*/docs/specs/*.md|*/docs/specs/**/*.md|\
*/docs/build/*.md|\
*/.workflow-state/build-*.json) ;;
  *) exit 0 ;;
esac

# Extract new content. Write tool: .content; Edit: .new_string; NotebookEdit: .new_source
NEW_CONTENT=$(echo "$TOOL_INPUT_JSON" | jq -r '.new_string // .content // .new_source // empty' 2>/dev/null || true)
[ -z "$NEW_CONTENT" ] && exit 0

# ---------- Trigger detect ----------

TRIGGERS='supersedes|reuses existing|already implemented|wraps existing|delivered in Task|existing-code verifications confirm'
if ! echo "$NEW_CONTENT" | grep -iqE "$TRIGGERS"; then
  exit 0
fi

# ---------- C-VERIFY block presence ----------

if ! echo "$NEW_CONTENT" | grep -qE 'C-VERIFY|Existing-Impl-Verifications|Claim-Verifications'; then
  MSG="brief-claims-guard: WARN — write to ${FILE_PATH} uses a trigger formulation (supersedes / reuses existing / already implemented / wraps existing / delivered in Task / existing-code verifications confirm) but contains no C-VERIFY block or Existing-Impl-Verifications table. Per L-044, claims about existing code MUST be grep-verified. Add a C-VERIFY block: verbatim grep command + verbatim output + CONFIRMED|FALSIFIED disposition. Hook re-runs the grep to detect hallucinated outputs."
  if [ "$STDIN_MODE" -eq 1 ]; then
    SAFE_MSG=$(printf '%s' "$MSG" | sed 's/"/\\"/g' | tr '\n' ' ')
    cat <<ENDJSON
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "allow",
    "permissionDecisionReason": "${SAFE_MSG}"
  }
}
ENDJSON
    exit 0
  else
    echo "$MSG" >&2
    exit 1
  fi
fi

# ---------- C-VERIFY present: extract grep commands + compare ----------

# Best-effort extraction: lines that LOOK like `grep -rn "..." path` (in
# code-fence, backticks, or plain). One command per line.
GREP_CMDS=$(echo "$NEW_CONTENT" \
  | grep -oE 'grep -[rnEHciow]+[[:space:]]+"[^"]+"[[:space:]]+[^[:space:]`|]+' \
  | sort -u)

if [ -z "$GREP_CMDS" ]; then
  # Block declared but no parseable commands — pass (agent provided a block
  # in some non-shell format; can't verify, but absence is not the failure).
  exit 0
fi

PROJECT_ROOT="${CLAUDE_PROJECT_DIR:-$(pwd)}"
cd "$PROJECT_ROOT" 2>/dev/null || exit 0

MISMATCHES=""
while IFS= read -r cmd; do
  [ -z "$cmd" ] && continue

  ACTUAL=$(timeout 5 bash -c "$cmd" 2>/dev/null || true)

  # Find the stored Output for this command. Search for the command line +
  # next ~5 lines and look for "(no output)" / "zero hits" / numeric hint.
  CTX=$(echo "$NEW_CONTENT" | grep -F -A 6 -- "$cmd" 2>/dev/null | head -8)

  STORED_EMPTY=0
  if echo "$CTX" | grep -qiE '\(no output\)|zero hits|0 hits'; then
    STORED_EMPTY=1
  fi

  ACTUAL_EMPTY=0
  [ -z "$ACTUAL" ] && ACTUAL_EMPTY=1

  # Mismatch: stored empty but actual non-empty, OR stored non-empty but actual empty.
  if [ "$STORED_EMPTY" -eq 1 ] && [ "$ACTUAL_EMPTY" -eq 0 ]; then
    FIRST=$(echo "$ACTUAL" | head -1)
    MISMATCHES="${MISMATCHES}stored=(no output) but re-run yields hits — first: ${FIRST}; cmd: ${cmd} | "
  elif [ "$STORED_EMPTY" -eq 0 ] && [ "$ACTUAL_EMPTY" -eq 1 ] && echo "$CTX" | grep -qE '[a-z]+\.[a-z]+:[0-9]+'; then
    # Stored shows file:line hints but actual is empty → mismatch
    MISMATCHES="${MISMATCHES}stored shows hits but re-run yields zero — cmd: ${cmd} | "
  fi
done <<<"$GREP_CMDS"

if [ -n "$MISMATCHES" ]; then
  MSG="brief-claims-guard: BLOCK — C-VERIFY re-run mismatch in ${FILE_PATH}. L-044 anti-hallucination floor. ${MISMATCHES}"
  if [ "$STDIN_MODE" -eq 1 ]; then
    SAFE_MSG=$(printf '%s' "$MSG" | sed 's/"/\\"/g' | tr '\n' ' ')
    cat <<ENDJSON
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "deny",
    "permissionDecisionReason": "${SAFE_MSG}"
  }
}
ENDJSON
    exit 0
  else
    echo "$MSG" >&2
    exit 2
  fi
fi

exit 0
