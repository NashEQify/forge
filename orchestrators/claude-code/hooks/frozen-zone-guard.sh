#!/usr/bin/env bash
# frozen-zone-guard.sh — PreToolUse Hook [Task-010 Phase 6 Stream B3]
#
# Enforces WORM (Write Once Read Many) on frozen zones.
# Canonical Spec: docs/specs/phase-6-hook-specs.md §Hook 3
# Frozen zones from: docs/STRUCTURE.md (declared Frozen Zones)
#
# Matcher: Edit | Write | NotebookEdit
#
# Behavior:
#   Blocks (exit 2) Edit/Write/NotebookEdit on paths inside a frozen zone.
#   Exceptions prefixed with ! (e.g. corrections-addendum.md) are allowed.
#
# TODO (known limitation): knowledge-processor MUST be able to create new
# files under context/history/. CC PreToolUse does not distinguish Create
# from Modify (Write tool covers both). Current workaround: only the
# corrections-addendum is exempt. Creating dated session files is currently
# blocked by this hook — future B2-continuation needs a separate agent-
# scoped whitelist for Create-operations. See phase-6-hook-specs.md §Hook 3
# Known Risks.
#
# Dual-mode invocation:
#   1. CC PreToolUse hook: JSON payload on stdin with tool_name and tool_input
#   2. Standalone test:    env vars CLAUDE_TOOL_NAME + CLAUDE_TOOL_INPUT_JSON
#
# Exit codes (standalone mode):
#   0 — PASS (not frozen, or explicit exception)
#   2 — BLOCK (inside frozen zone, no exception)

set -uo pipefail

FROZEN_FILE="${CLAUDE_PROJECT_DIR:-$HOME/projects/forge}/.claude/frozen-zones.txt"

if [ ! -f "$FROZEN_FILE" ]; then
  echo "frozen-zone-guard: SKIP (no frozen zones file at $FROZEN_FILE)" >&2
  exit 0
fi

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

if [ -z "$TOOL_NAME" ]; then
  exit 0
fi

# Only guard file-writing tools
case "$TOOL_NAME" in
  Edit|Write|NotebookEdit) ;;
  *) exit 0 ;;
esac

if ! command -v jq &>/dev/null; then
  exit 0
fi

TARGET_PATH=$(echo "$TOOL_INPUT_JSON" | jq -r '.file_path // empty' 2>/dev/null || true)
if [ -z "$TARGET_PATH" ]; then
  exit 0
fi

REAL_PATH=$(realpath "$TARGET_PATH" 2>/dev/null || echo "$TARGET_PATH")

# ---------- Special Case: context/history Create-Exception ----------
#
# context/history/ is frozen for modification (WORM) but knowledge-processor
# + save-Workflow MUST be able to CREATE new dated session files
# (YYYY-MM-DD-*.md). CC PreToolUse does not distinguish Create from Modify,
# so we check here: if the target matches the dated-file pattern AND the
# file does not exist yet, allow the write. Existing files stay blocked.
#
# Pattern: context/history/YYYY-MM-DD-*.md (4-digit year, 2-digit month/day)

if [[ "$REAL_PATH" =~ /context/history/[0-9]{4}-[0-9]{2}-[0-9]{2}[^/]*\.md$ ]] || \
   [[ "$TARGET_PATH" =~ /context/history/[0-9]{4}-[0-9]{2}-[0-9]{2}[^/]*\.md$ ]]; then
  # Check Create vs Modify
  if [ ! -f "$REAL_PATH" ] && [ ! -f "$TARGET_PATH" ]; then
    if [ "$STDIN_MODE" -eq 0 ]; then
      echo "frozen-zone-guard: PASS — $REAL_PATH is new dated history file (Create allowed)"
    fi
    exit 0
  fi
  # Existing dated history file → fall through to normal frozen-zone logic (BLOCK)
fi

# ---------- Glob-to-regex helper ----------

match_pattern() {
  local path="$1"
  local pattern="$2"

  local escaped
  escaped=$(printf '%s' "$pattern" | sed -e 's/[][\.|$(){}?+^]/\\&/g')
  escaped="${escaped//\*\*/__DBLSTAR__}"
  escaped="${escaped//\*/[^/]*}"
  escaped="${escaped//__DBLSTAR__/.*}"

  [[ "$path" =~ ^${escaped}$ ]]
}

# ---------- Pass 1: Exceptions (!-prefix) ----------

while IFS= read -r pattern || [ -n "$pattern" ]; do
  [[ "$pattern" =~ ^[[:space:]]*# ]] && continue
  [[ -z "${pattern// /}" ]] && continue
  pattern=$(echo "$pattern" | tr -d '\r' | sed 's/[[:space:]]*$//')
  [[ -z "$pattern" ]] && continue
  [[ ! "$pattern" =~ ^! ]] && continue

  ACTUAL_PATTERN="${pattern#!}"
  if match_pattern "$REAL_PATH" "$ACTUAL_PATTERN" || \
     { [ "$REAL_PATH" != "$TARGET_PATH" ] && match_pattern "$TARGET_PATH" "$ACTUAL_PATTERN"; }; then
    if [ "$STDIN_MODE" -eq 0 ]; then
      echo "frozen-zone-guard: PASS — $REAL_PATH is explicit exception ($ACTUAL_PATTERN)"
    fi
    exit 0
  fi
done < "$FROZEN_FILE"

# ---------- Pass 2: Frozen patterns ----------

while IFS= read -r pattern || [ -n "$pattern" ]; do
  [[ "$pattern" =~ ^[[:space:]]*# ]] && continue
  [[ -z "${pattern// /}" ]] && continue
  pattern=$(echo "$pattern" | tr -d '\r' | sed 's/[[:space:]]*$//')
  [[ -z "$pattern" ]] && continue
  [[ "$pattern" =~ ^! ]] && continue

  if match_pattern "$REAL_PATH" "$pattern" || \
     { [ "$REAL_PATH" != "$TARGET_PATH" ] && match_pattern "$TARGET_PATH" "$pattern"; }; then
    MSG="frozen-zone-guard: BLOCK — $REAL_PATH is in frozen zone ($pattern). WORM: no modification allowed. Use Corrections-Addendum pattern (context/history/corrections-addendum.md). See agents/buddy/context-rules.md §Frozen Zone Guard."
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
done < "$FROZEN_FILE"

# Not frozen → pass
exit 0
