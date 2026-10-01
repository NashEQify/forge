#!/usr/bin/env bash
# buddy-boot-inject.sh — SessionStart hook for non-terminal entrypoints.
#
# Terminal cc launcher injects buddy-boot via --agent buddy +
# --append-system-prompt FRAMEWORK_INJECT. claude-desktop / claude-web
# run plain `claude` without those flags, so the persona-load never
# fires. This hook recreates the inject as SessionStart additionalContext
# for those entrypoints. Generic so any forge-consuming repo can wire
# it from the canonical framework location.
#
# Self-resolves FRAMEWORK_DIR via own location, so it works even when
# CLAUDE_PROJECT_DIR is unset (which is the default in claude-desktop).
# No marker gate — fires every SessionStart; a marker check would be
# unsafe in non-ephemeral contexts where the filesystem persists across
# sessions.

set -euo pipefail

# Gate: only non-terminal entrypoints. cc-terminal already boots via
# --agent buddy; firing this would double-inject.
case "${CLAUDE_CODE_ENTRYPOINT:-}" in
  claude-desktop|claude-web) ;;
  *) exit 0 ;;
esac

# Self-resolve FRAMEWORK_DIR from hook location. orchestrators/
# claude-code/hooks/buddy-boot-inject.sh → forge_dev root is three
# levels up. Canonical, no env-var dependency.
FRAMEWORK_DIR="$(cd "$(dirname "$(readlink -f "$0")")/../../.." 2>/dev/null && pwd)"
if [ -z "$FRAMEWORK_DIR" ] || [ ! -d "$FRAMEWORK_DIR/agents/buddy" ]; then
  exit 0
fi

# Consume stdin (SessionStart JSON payload — we don't need it but CC
# expects the hook to drain it).
cat > /dev/null 2>&1 || true

# JSON-escape FRAMEWORK_DIR (path is typically safe, but defensive).
FW_ESC="$(printf '%s' "$FRAMEWORK_DIR" | sed 's/\\/\\\\/g; s/"/\\"/g')"

cat <<JSON
{"hookSpecificOutput":{"hookEventName":"SessionStart","additionalContext":"BUDDY-BOOT REQUIRED before answering.\n\nRead by absolute path: ${FW_ESC}/agents/buddy/soul.md, ${FW_ESC}/agents/buddy/operational.md, ${FW_ESC}/agents/buddy/boot.md.\n\nFollow boot.md in order: orientation, freshness gate, intent and workflow selection, then the selected mode's boot procedure and greeting. Resolve any remote-update decision before loading intent or context. Do not run plan/workflow probes or load the full skill index ahead of workflow selection. For on-demand use, follow the project's local boot and working rules.\n\nKeep the consumer CWD active. CLAUDE.md and local authorization rules apply. FRAMEWORK_DIR=${FW_ESC}."}}
JSON
