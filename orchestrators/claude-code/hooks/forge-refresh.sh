#!/usr/bin/env bash
# forge-refresh.sh — SessionStart hook, listed before the boot hook: brings the
# installed Forge entries up to the checkout's commit (forge_install.py
# --refresh), so `git pull` in the checkout is the whole update.
#
# Machine mode (no argument; the full-ai-integration installation's
# ~/.claude/settings.json) refreshes the machine installation. Project mode
# (--project; a project install's .claude/settings.local.json) refreshes the
# session's project and writes nothing outside it.
#
# A refresh never fails a start: stdin is drained, nothing reaches stdout (the
# host would read it as session context), and the exit status is always 0. The
# boot hook does not depend on this one: the host may run SessionStart hooks in
# parallel, and a description copied into a wrapper lags until this run lands.

cat > /dev/null 2>&1 || true
FRAMEWORK_DIR="$(cd "$(dirname "$(readlink -f "$0")")/../../.." 2>/dev/null && pwd)" || exit 0
[ -f "$FRAMEWORK_DIR/scripts/forge_install.py" ] || exit 0
ARGS=(--refresh)
if [ "${1:-}" = "--project" ]; then
  ARGS+=("${CLAUDE_PROJECT_DIR:-$PWD}")
fi
python3 -B "$FRAMEWORK_DIR/scripts/forge_install.py" "${ARGS[@]}" < /dev/null > /dev/null || true
exit 0
