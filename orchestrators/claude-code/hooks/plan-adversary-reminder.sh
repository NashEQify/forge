#!/usr/bin/env bash
# plan-adversary-reminder.sh — PreToolUse Hook (Defekt E post-comm-82657bc)
#
# WARN when Buddy is about to Edit/Write/MultiEdit a Tier-1 file as part of
# a non-trivial-edit-cluster, with no plan-adversary spawn marker in last 60min.
#
# Non-trivial = either:
#   - N>2 distinct Tier-1 files already modified/staged in repo, OR
#   - large single-file delta (proposed write content >= 80 lines vs file size)
#
# Per F-PA-007: byte-delta dimension catches single-file Tier-1 rewrites
# (highest-leverage non-trivial work) that pure file-count threshold misses.
#
# Override syntax (in CLAUDE.md scratch):
#   # allow:no-plan-adversary <one-sentence-reason>
#
# Marker: written under .session/plan-adversary/<timestamp>.marker by Buddy
# after spawning plan-adversary agent. Marker mtime >60min = stale.
#
# Note: WARN-only via stderr — does not block. plan-adversary skip is
# recoverable post-fact via separate adversary-pass.

set -uo pipefail

FRAMEWORK_ROOT="${CLAUDE_PROJECT_DIR:-$HOME/projects/forge}"

INPUT=$(cat 2>/dev/null || true)
[ -z "$INPUT" ] && exit 0
command -v jq &>/dev/null || exit 0

TOOL_NAME=$(echo "$INPUT" | jq -r '.tool_name // empty' 2>/dev/null)
case "$TOOL_NAME" in
  Edit|Write|MultiEdit|NotebookEdit) ;;
  *) exit 0 ;;
esac

TARGET=$(echo "$INPUT" | jq -r '.tool_input.file_path // empty' 2>/dev/null)
[ -z "$TARGET" ] && exit 0

# Repo-relative
case "$TARGET" in
  "$FRAMEWORK_ROOT"/*) REL="${TARGET#$FRAMEWORK_ROOT/}" ;;
  /*) exit 0 ;;
  *) REL="$TARGET" ;;
esac

# Tier-1 path check
is_tier_1() {
  case "$1" in
    architecture-documentation/*) return 0 ;;
    framework/*) return 0 ;;
    agents/*) return 0 ;;
    skills/*) return 0 ;;
    workflows/*) return 0 ;;
    scripts/*) return 0 ;;
    orchestrators/*) return 0 ;;
    README.md|CLAUDE.md|AGENTS.md) return 0 ;;
    *) return 1 ;;
  esac
}

is_tier_1 "$REL" || exit 0

# Override token
if [ -f "$FRAMEWORK_ROOT/CLAUDE.md" ]; then
  if grep -qE '^# *allow:no-plan-adversary' "$FRAMEWORK_ROOT/CLAUDE.md" 2>/dev/null; then
    exit 0
  fi
fi

# --- non-trivial-edit-cluster ---
cd "$FRAMEWORK_ROOT" 2>/dev/null || exit 0

# Dimension 1: file count (Tier-1)
TIER1_COUNT=$(git status --porcelain 2>/dev/null \
  | awk '{print $NF}' \
  | while read -r f; do
      case "$f" in
        architecture-documentation/*|framework/*|agents/*|skills/*|workflows/*|scripts/*|orchestrators/*|README.md|CLAUDE.md|AGENTS.md) echo "$f" ;;
      esac
    done \
  | wc -l)

# Dimension 2: byte-delta (Write tool only — Edit doesn't expose full content)
DELTA_LINES=0
if [ "$TOOL_NAME" = "Write" ] && [ -f "$TARGET" ]; then
  CONTENT=$(echo "$INPUT" | jq -r '.tool_input.content // empty' 2>/dev/null)
  if [ -n "$CONTENT" ]; then
    NEW_LINES=$(printf '%s' "$CONTENT" | wc -l)
    OLD_LINES=$(wc -l < "$TARGET" 2>/dev/null || echo 0)
    if [ "$NEW_LINES" -gt "$OLD_LINES" ]; then
      DELTA_LINES=$((NEW_LINES - OLD_LINES))
    else
      DELTA_LINES=$((OLD_LINES - NEW_LINES))
    fi
  fi
fi

# Trigger if either dimension exceeds threshold
NON_TRIVIAL=0
if [ "$TIER1_COUNT" -gt 2 ]; then NON_TRIVIAL=1; fi
if [ "$DELTA_LINES" -ge 80 ]; then NON_TRIVIAL=1; fi

# Skip if total diff is trivial (typo-fix floor)
if [ "$TIER1_COUNT" -le 1 ] && [ "$DELTA_LINES" -lt 80 ]; then
  exit 0
fi

[ "$NON_TRIVIAL" -eq 0 ] && exit 0

# --- plan-adversary marker check ---
MARKER_DIR="$FRAMEWORK_ROOT/.session/plan-adversary"
HAS_RECENT=0
if [ -d "$MARKER_DIR" ]; then
  RECENT=$(find "$MARKER_DIR" -name "*.marker" -mmin -60 2>/dev/null | head -1)
  [ -n "$RECENT" ] && HAS_RECENT=1
fi

if [ "$HAS_RECENT" -eq 0 ]; then
  echo "WARN: plan-adversary-reminder — Non-trivial Tier-1 edit (${TIER1_COUNT} files modified, target=${REL}) without plan-adversary in last 60min. Required next action: spawn plan-adversary on current plan-block, OR add '# allow:no-plan-adversary <reason>' to CLAUDE.md scratch." >&2
fi

exit 0
