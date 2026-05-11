#!/usr/bin/env bash
# path-whitelist-guard.sh — PreToolUse Hook [Task-010 Phase 6 Stream B3]
#
# Enforces Buddy's write path whitelist (CLAUDE.md Invariante 5 + SE/INV-5).
# Canonical Spec: docs/specs/phase-6-hook-specs.md §Hook 2
#
# Matcher: Edit | Write | NotebookEdit | Bash
#
# Behavior:
#   Edit/Write/NotebookEdit: blocks (exit 2) if target path not in whitelist
#   Bash:                    warns (exit 1) if write-op heuristic detects
#                            non-whitelisted path — heuristic is intentionally
#                            partial (CM1 F5 Bash-Shell-Redirect-Vielfalt).
#
# Dual-mode invocation:
#   1. CC PreToolUse hook: JSON payload on stdin with tool_name and tool_input
#   2. Standalone test:    env vars CLAUDE_TOOL_NAME + CLAUDE_TOOL_INPUT_JSON
#
# When called as a CC hook with a block decision, emits JSON "deny" payload
# on stdout (exit 0) as CC expects. In standalone mode, emits plain text
# and uses exit codes 0/1/2 as documented in the spec.
#
# Exit codes (standalone mode):
#   0 — PASS (path in whitelist, or Bash without write-op, or skip)
#   1 — WARN (Bash write-op heuristic on non-whitelisted path)
#   2 — BLOCK (Edit/Write/NotebookEdit on non-whitelisted path)

set -uo pipefail

WHITELIST_FILE="${CLAUDE_PROJECT_DIR:-$HOME/projects/forge}/.claude/path-whitelist.txt"

if [ ! -f "$WHITELIST_FILE" ]; then
  # Graceful degradation: no whitelist file → allow all
  echo "path-whitelist-guard: SKIP (no whitelist file at $WHITELIST_FILE)" >&2
  exit 0
fi

# ---------- Input resolution: stdin JSON or env vars ----------

TOOL_NAME=""
TOOL_INPUT_JSON=""
STDIN_MODE=0

# Try stdin JSON first (CC PreToolUse API)
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

# Fallback to env vars (standalone test mode)
if [ -z "$TOOL_NAME" ]; then
  TOOL_NAME="${CLAUDE_TOOL_NAME:-}"
  TOOL_INPUT_JSON="${CLAUDE_TOOL_INPUT_JSON:-{}}"
fi

if [ -z "$TOOL_NAME" ]; then
  # Nothing to check
  exit 0
fi

if ! command -v jq &>/dev/null; then
  # jq missing → cannot parse, graceful pass
  exit 0
fi

# ---------- Target path extraction ----------

TARGET_PATH=""
case "$TOOL_NAME" in
  Edit|Write|NotebookEdit)
    TARGET_PATH=$(echo "$TOOL_INPUT_JSON" | jq -r '.file_path // empty' 2>/dev/null || true)
    ;;
  Bash)
    CMD=$(echo "$TOOL_INPUT_JSON" | jq -r '.command // empty' 2>/dev/null || true)
    if [ -z "$CMD" ]; then
      exit 0
    fi
    # Heuristic write-op detection (intentionally partial per CM1 F5)
    # Covers: > file, >> file, tee file, sed -i file, cat > file, vim file,
    #         nano file, vi file, touch file, mkdir -p path, rm file,
    #         mv src dst, cp src dst.
    # Python/awk/other interpreters doing I/O are NOT caught → known risk.
    WRITE_REGEX='(>>?[[:space:]]*|tee[[:space:]]+|sed[[:space:]]+-i[[:space:]]+|vim[[:space:]]+|vi[[:space:]]+|nano[[:space:]]+|touch[[:space:]]+|rm[[:space:]]+(-[rf]+[[:space:]]+)?|mv[[:space:]]+[^[:space:]]+[[:space:]]+|cp[[:space:]]+[^[:space:]]+[[:space:]]+)'
    if ! echo "$CMD" | grep -qE "$WRITE_REGEX"; then
      # No write-op detected → pass
      exit 0
    fi
    # Best-effort target extraction: strip the operator keyword, take next token.
    TARGET_PATH=$(echo "$CMD" | grep -oE "$WRITE_REGEX[^[:space:]]+" | head -1 | awk '{print $NF}')
    # Strip leading > / >> / operator residue
    TARGET_PATH="${TARGET_PATH##*>}"
    TARGET_PATH="${TARGET_PATH##*>>}"
    ;;
  *)
    # Unknown/irrelevant tool → pass
    exit 0
    ;;
esac

if [ -z "$TARGET_PATH" ]; then
  exit 0
fi

# ---------- Symlink resolution (fallback on failure) ----------

REAL_PATH=$(realpath "$TARGET_PATH" 2>/dev/null || echo "$TARGET_PATH")

# ---------- Whitelist match ----------

match_pattern() {
  local path="$1"
  local pattern="$2"

  # Convert gitignore-style glob to regex.
  # Escape regex metachars except * and /.
  # Then: **  → .*
  #       *   → [^/]*
  local escaped
  escaped=$(printf '%s' "$pattern" | sed -e 's/[][\.|$(){}?+^]/\\&/g')
  # Placeholder __DBLSTAR__ avoids bash interpretation issues with \x00
  escaped="${escaped//\*\*/__DBLSTAR__}"
  escaped="${escaped//\*/[^/]*}"
  escaped="${escaped//__DBLSTAR__/.*}"

  [[ "$path" =~ ^${escaped}$ ]]
}

MATCH_FOUND=0
while IFS= read -r pattern || [ -n "$pattern" ]; do
  # Skip comments and empty
  [[ "$pattern" =~ ^[[:space:]]*# ]] && continue
  [[ -z "${pattern// /}" ]] && continue
  # Trim trailing whitespace/CR
  pattern=$(echo "$pattern" | tr -d '\r' | sed 's/[[:space:]]*$//')
  [[ -z "$pattern" ]] && continue

  if match_pattern "$REAL_PATH" "$pattern"; then
    MATCH_FOUND=1
    break
  fi
  # Also try against the raw target path (in case realpath resolved
  # into a different tree but the raw path was whitelisted).
  if [ "$REAL_PATH" != "$TARGET_PATH" ]; then
    if match_pattern "$TARGET_PATH" "$pattern"; then
      MATCH_FOUND=1
      break
    fi
  fi
done < "$WHITELIST_FILE"

# ---------- Decision ----------

if [ "$MATCH_FOUND" -eq 1 ]; then
  # Pass — nothing to do for CC hook, standalone emits info
  if [ "$STDIN_MODE" -eq 0 ]; then
    echo "path-whitelist-guard: PASS — $REAL_PATH matches whitelist"
  fi
  exit 0
fi

# No match → decide based on tool
case "$TOOL_NAME" in
  Edit|Write|NotebookEdit)
    MSG="path-whitelist-guard: BLOCK — $REAL_PATH not in whitelist. Delegate to main-code-agent or adjust whitelist at $WHITELIST_FILE."
    if [ "$STDIN_MODE" -eq 1 ]; then
      # CC JSON deny output
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
    ;;
  Bash)
    MSG="path-whitelist-guard: WARN — Bash write-op may target non-whitelisted path: $REAL_PATH"
    if [ "$STDIN_MODE" -eq 1 ]; then
      # CC: warning output via stderr — does not block, but visible to user
      echo "$MSG" >&2
      exit 0
    else
      echo "$MSG" >&2
      exit 1
    fi
    ;;
esac

exit 0
