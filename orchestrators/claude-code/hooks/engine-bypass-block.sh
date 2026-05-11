#!/usr/bin/env bash
# engine-bypass-block.sh — PreToolUse Hook (Defekt A post-comm-82657bc)
#
# BLOCKS Edit/Write/MultiEdit/NotebookEdit on reader-facing Tier-1 paths when:
#   - target file matches explicit reader-facing-allowlist (Pattern 7)
#   - 2+ reader-facing files already modified or staged in repo
#   - no active workflow in .workflow-state/
#   - no override token in CLAUDE.md scratch
#
# Override syntax (in CLAUDE.md scratch):
#   # allow:engine-bypass <one-sentence-reason>
#
# Per F-PA-003: explicit allowlist (default OUT bei Doubt), NOT
# default-reader-facing-bei-Doubt (would False-Positive-Sturm).
#
# Per F-PA-005: BLOCK at PreToolUse — moment-of-bypass intervention.
# WARN-only mode is the failure-mode being fixed (workflow-reminder
# became background noise in commit 82657bc incident).

set -uo pipefail

FRAMEWORK_ROOT="${CLAUDE_PROJECT_DIR:-$HOME/projects/forge}"

INPUT=$(cat 2>/dev/null || true)
[ -z "$INPUT" ] && exit 0

if ! command -v jq &>/dev/null; then
  exit 0
fi

TOOL_NAME=$(echo "$INPUT" | jq -r '.tool_name // empty' 2>/dev/null)
case "$TOOL_NAME" in
  Edit|Write|MultiEdit|NotebookEdit) ;;
  *) exit 0 ;;
esac

TARGET=$(echo "$INPUT" | jq -r '.tool_input.file_path // empty' 2>/dev/null)
[ -z "$TARGET" ] && exit 0

# Repo-relative path
case "$TARGET" in
  "$FRAMEWORK_ROOT"/*) REL="${TARGET#$FRAMEWORK_ROOT/}" ;;
  /*) exit 0 ;;
  *) REL="$TARGET" ;;
esac

# --- is_reader_facing(path): explicit allowlist (Pattern 7) ---
is_reader_facing() {
  case "$1" in
    README.md) return 0 ;;
    architecture-documentation/*.md) return 0 ;;
    architecture-documentation/*/*.md) return 0 ;;
    docs/getting-started.md) return 0 ;;
    docs/CONTRIBUTING.md) return 0 ;;
    *) return 1 ;;
  esac
}

is_reader_facing "$REL" || exit 0

# --- Override-Token check ---
if [ -f "$FRAMEWORK_ROOT/CLAUDE.md" ]; then
  if grep -qE '^# *allow:engine-bypass' "$FRAMEWORK_ROOT/CLAUDE.md" 2>/dev/null; then
    exit 0
  fi
fi

# --- Active workflow check ---
HAS_ACTIVE=$(timeout 1 python3 "$FRAMEWORK_ROOT/scripts/workflow_engine.py" --list --format json 2>/dev/null \
  | jq -e '.active | length > 0' 2>/dev/null)
[ "$HAS_ACTIVE" = "true" ] && exit 0

# --- Count modified+staged reader-facing files ---
cd "$FRAMEWORK_ROOT" 2>/dev/null || exit 0
MOD_COUNT=$(git status --porcelain 2>/dev/null \
  | awk '{print $NF}' \
  | while read -r f; do
      case "$f" in
        README.md|architecture-documentation/*.md|architecture-documentation/*/*.md|docs/getting-started.md|docs/CONTRIBUTING.md) echo "$f" ;;
      esac
    done \
  | wc -l)

# Threshold: 2 OR more already modified means this Edit would be the 3rd+ file
if [ "$MOD_COUNT" -ge 2 ]; then
  MSG="BLOCK: Multi-file reader-facing edit (currently ${MOD_COUNT} files modified/staged in repo) without active workflow. Pattern 7 (Reader-Facing-Surface Detection): doc-rollouts must be engine-tracked. Required next action: python3 scripts/workflow_engine.py --start solve --task <id>. Override: add '# allow:engine-bypass <one-sentence-reason>' line to CLAUDE.md scratch."
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
fi

exit 0
