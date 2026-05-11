#!/usr/bin/env bash
# board-output-check.sh — PostToolUse(Task) hook [Item 8 post-388]
#
# Mechanical enforcement of dispatch-template.md File-Output-OVERRIDE.
#
# 388 Welle-1 + 421-Adversary: sub-agents (Board-Reviewer / Council-Member)
# ignorieren File-Output-OVERRIDE und returnen findings inline statt in Datei.
# Buddy Pass-Through-Fallback in operational.md ist Recovery, nicht Prevention.
#
# This hook checks: when dispatch-prompt contained "Schreibe dein Review in:
# <pfad>" OR "Output-Pfad: <pfad>" pattern, AND task completed: does the
# expected file exist? If not, emit WARN with pass-through-suggestion.
#
# Matcher: Task (any subagent_type with file-output-pattern in prompt).
#
# Exit codes:
#   0 — always (graceful, never blocks)
#
# CC-hook output: WARN via stderr.

set -uo pipefail

# ---------- Input resolution ----------

TOOL_INPUT_JSON=""
STDIN_MODE=0

if [ ! -t 0 ]; then
  STDIN_CONTENT=$(cat 2>/dev/null || true)
  if [ -n "$STDIN_CONTENT" ] && command -v jq &>/dev/null; then
    PARSED_TOOL=$(echo "$STDIN_CONTENT" | jq -r '.tool_name // empty' 2>/dev/null || true)
    if [ "$PARSED_TOOL" = "Task" ]; then
      TOOL_INPUT_JSON=$(echo "$STDIN_CONTENT" | jq -c '.tool_input // {}' 2>/dev/null || echo "{}")
      STDIN_MODE=1
    fi
  fi
fi

if [ -z "$TOOL_INPUT_JSON" ] && [ -n "${CLAUDE_TOOL_INPUT_JSON:-}" ]; then
  TOOL_INPUT_JSON="$CLAUDE_TOOL_INPUT_JSON"
fi

if [ -z "$TOOL_INPUT_JSON" ]; then
  exit 0
fi

if ! command -v jq &>/dev/null; then
  exit 0
fi

# ---------- Extract prompt + subagent_type ----------

PROMPT=$(echo "$TOOL_INPUT_JSON" | jq -r '.prompt // empty' 2>/dev/null || true)
SUBAGENT=$(echo "$TOOL_INPUT_JSON" | jq -r '.subagent_type // empty' 2>/dev/null || true)

# ---------- UX-Board marker ----------
#
# Write timestamped marker when the sub-agent is a UX-Board reviewer.
# Reader-facing-edit guards (engine-bypass-block.sh, Pattern 7) consult
# the marker to confirm a UX-Board ran in the last 24h before allowing
# a reader-facing artefact commit.

if [[ "$SUBAGENT" =~ ^board-ux- ]]; then
  PROJECT_ROOT_M="${CLAUDE_PROJECT_DIR:-$(pwd)}"
  MARKER_DIR="$PROJECT_ROOT_M/.session/board-runs"
  mkdir -p "$MARKER_DIR" 2>/dev/null
  if [ -d "$MARKER_DIR" ]; then
    touch "$MARKER_DIR/ux-$(date +%s)-${SUBAGENT}.marker" 2>/dev/null || true
  fi
fi

if [ -z "$PROMPT" ]; then
  exit 0
fi

# ---------- Detect file-output-Pattern in dispatch-prompt ----------

# Patterns (German + English):
#   "Schreibe dein Review in: <pfad>"
#   "Output-Pfad: <pfad>"
#   "WRITE the review file at the path specified above"
#   "Output: <path>"
#
# Extract paths matching docs/reviews/board/, docs/reviews/council/,
# docs/reviews/code/, etc. — file-system paths to .md files.

EXPECTED_PATHS=()

# Pattern 1: explicit "in: <path>"
while IFS= read -r line; do
  [ -z "$line" ] && continue
  EXPECTED_PATHS+=("$line")
done < <(echo "$PROMPT" | grep -oE "(Schreibe.{0,30}in|Output-Pfad|WRITE.{0,30}at|Output[[:space:]]*[Pp]ath):[[:space:]]+[a-zA-Z0-9_./-]+\.md" 2>/dev/null | grep -oE "[a-zA-Z0-9_./-]+\.md$" || true)

# Pattern 2: backtick-quoted paths in dispatch-prompt
# (`docs/reviews/.../<file>.md`)
while IFS= read -r line; do
  [ -z "$line" ] && continue
  # Skip if already in EXPECTED_PATHS
  found=0
  for ep in "${EXPECTED_PATHS[@]}"; do
    [ "$ep" = "$line" ] && found=1 && break
  done
  [ $found -eq 0 ] && EXPECTED_PATHS+=("$line")
done < <(echo "$PROMPT" | grep -oE '`[^`]*docs/reviews/[^`]+\.md`' 2>/dev/null | tr -d '`' || true)

# Nothing to check → graceful exit
if [ ${#EXPECTED_PATHS[@]} -eq 0 ]; then
  exit 0
fi

# ---------- Verify each expected path exists ----------

# Resolve paths relative to project root
PROJECT_ROOT="${CLAUDE_PROJECT_DIR:-$(pwd)}"

MISSING_PATHS=()
for path in "${EXPECTED_PATHS[@]}"; do
  full_path="$PROJECT_ROOT/$path"
  if [ ! -f "$full_path" ]; then
    MISSING_PATHS+=("$path")
  fi
done

# ---------- WARN ----------

if [ ${#MISSING_PATHS[@]} -gt 0 ]; then
  echo "" >&2
  echo "============================================================" >&2
  echo "board-output-check: WARN — Sub-Agent dispatch erwartete File-Output," >&2
  echo "aber File(s) fehlen post-Task. Pattern-Lesson 388 Welle-1: Sub-Agents" >&2
  echo "ignorieren File-Output-OVERRIDE und returnen inline. dispatch-template.md" >&2
  echo "Buddy-Pass-Through-Fallback ist Recovery — schreibe Sub-Agent-Return-" >&2
  echo "Content mechanisch in erwarteten Pfad mit Banner-Note:" >&2
  echo "" >&2
  echo "> Pass-through note: <agent> returned this content inline rather than" >&2
  echo "> writing the file directly. Buddy wrote it here verbatim per dispatcher-" >&2
  echo "> mechanics. No content modified." >&2
  echo "" >&2
  echo "Erwartete Files (missing):" >&2
  for path in "${MISSING_PATHS[@]}"; do
    echo "  - $path" >&2
  done
  echo "============================================================" >&2
fi

exit 0
