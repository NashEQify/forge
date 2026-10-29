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

# Resolved boot entry: soul + user scope per framework/user-scope.md,
# rendered as complete JSON by the resolver (json.dumps). The resolver never
# fails on user data; if python3 itself fails (missing, crash, timeout) the
# static forge-soul entry below is emitted instead. Never exit non-zero
# because of the resolver — a missing boot is worse than the forge soul.
RESOLVER=(python3 "$FRAMEWORK_DIR/scripts/user_scope.py" --framework-root "$FRAMEWORK_DIR" --hook-json)
if command -v timeout >/dev/null 2>&1; then
  RESOLVER=(timeout -k 0.5 1.5 "${RESOLVER[@]}")
fi
if out="$("${RESOLVER[@]}" 2>/dev/null)" && [ -n "$out" ]; then
  printf '%s\n' "$out"
  exit 0
fi

# Static fallback. JSON-escape FRAMEWORK_DIR (path is typically safe, but defensive).
# The scope-rule and reread lines restate user_scope.SCOPE_RULE and
# user_scope.reread_line(FRAMEWORK_DIR, "full") as text (this path cannot
# import them); tests/test_boot_injectors.py keeps both equal.
FW_ESC="$(printf '%s' "$FRAMEWORK_DIR" | sed 's/\\/\\\\/g; s/"/\\"/g')"

cat <<JSON
{"hookSpecificOutput":{"hookEventName":"SessionStart","additionalContext":"BUDDY-BOOT REQUIRED before answering.\n\nRead by absolute path: ${FW_ESC}/agents/buddy/soul.md, ${FW_ESC}/agents/buddy/operational.md, ${FW_ESC}/agents/buddy/boot.md, ${FW_ESC}/framework/invariants.md.\nA quick question or a small fix does not shorten the boot; 'it is only a lookup' is no exception: run boot.md's sequence before reading anything for the request. Instruction source: the framework root is this session's instruction source. Reading its files and the files this entry names loads instructions; it is not work outside the project, and a user scope that limits writes, network or installs does not forbid it. Under such a scope, skip only the boot steps it forbids (the freshness fetch needs the network and writes Git metadata; creating context files needs a write) and report each as an unavailable check. If the boot is skipped or cut short for any reason, say so at the start of your first answer and name what did not load.\nUser scope warning: resolver failed\nAfter compaction, reread before continuing: the soul named above; under the framework root ${FW_ESC} (every framework path in this line is relative to it, not to the project): agents/buddy/boot.md, framework/work-principle.md, framework/invariants.md; for software development agents/buddy/operational.md, framework/boot-navigation.md and agents/buddy/boot-software.md; for on-demand use agents/buddy/boot-on-demand.md; on Codex agents/buddy/codex-execution.md; then the user profile (when a user scope is configured), the knowledge_processor continuous-maintenance rules (skills/knowledge_processor/continuous-maintenance.md, under that root), the project rules, intent.md and the session handoff; then, for any Forge step in progress (skill, protocol, framework or workflow step), its core and the unit its stub or engine step text names for that step.\n\nFollow boot.md in order before the first answer: orientation, freshness gate, intent and workflow selection, then the selected mode's boot procedure and greeting. Resolve any remote-update decision before loading intent or context. Do not run plan/workflow probes or load the full skill index ahead of workflow selection. For on-demand use, follow the project's local boot and working rules.\n\nKeep the consumer CWD active. The project's CLAUDE.md and local authorization rules apply. FRAMEWORK_DIR=${FW_ESC}."}}
JSON
