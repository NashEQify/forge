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
# No marker gate — fires every SessionStart; the marker check in
# workflow-reminder.sh is unsafe in non-ephemeral contexts where the
# filesystem persists across sessions.

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
{"hookSpecificOutput":{"hookEventName":"SessionStart","additionalContext":"BUDDY-BOOT REQUIRED — mechanical execution, no reactive clustering.\n\nROUND 1 (single parallel tool block — Read tool, absolute paths):\n  1. ${FW_ESC}/agents/buddy/soul.md\n  2. ${FW_ESC}/agents/buddy/operational.md\n  3. ${FW_ESC}/agents/buddy/boot.md\n\nROUND 2 (single parallel tool block IMMEDIATELY after Round 1, NO thinking pause): execute boot.md §Parallelization exactly — ALL probes in one block: ORIENT (date+hostname+pwd), RESOLVE (ls intent.md, walk up if not found), STATUS-CHECK (bash ${FW_ESC}/scripts/git-status-check.sh AND bash ${FW_ESC}/scripts/chub-status-check.sh as separate calls), workflow_engine.py --boot-context, plan_engine.py --boot (root sessions only); PLUS ALL load-files in same block: always-load (values.md, profile.md, ${FW_ESC}/framework/boot-navigation.md), intent-load files derived from intent.md Context field (if Context field missing: derive from Vision + Non-Goals, ask if uncertain — do not silently skip), session-handoff.md per CWD-based path, project backlog if applicable. Probe-isolation MUST — each result-bearing Bash probe = own call, never ;-chained.\n\nGREET (per soul.md style) immediately after Round 2 — no thinking pause.\n\nCLAUDE.md applies. FRAMEWORK_DIR=${FW_ESC}. Under claude-desktop/web, CLAUDE_PROJECT_DIR is unset — use absolute paths above. This is a mechanical algorithm; do not interpret as guidance, do not reactive-cluster ('das brauche ich sofort'), do not insert a thinking pause between rounds. Round 1 → Round 2 (single parallel block) → GREET."}}
JSON
