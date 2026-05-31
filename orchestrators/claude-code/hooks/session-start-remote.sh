#!/usr/bin/env bash
# session-start-remote.sh — SessionStart hook for Claude Code remote/web sessions.
#
# Web/desktop CC containers are ephemeral: pre-commit hooks + path-whitelist
# + ~/.claude/{agents,skills} symlinks are NOT installed by default. This
# hook runs setup-cc.sh idempotently so the full forge hook stack is
# available in web sessions too.
#
# Gated on $CLAUDE_CODE_REMOTE=true — terminal sessions install via the
# cc launcher's own setup flow and don't need this.
#
# Smoke-test status (2026-05-28): first iteration, sync mode. Marker
# lines [session-start-remote] are intentional so the next session can
# verify in the transcript that the hook actually fired.

set -euo pipefail

# Read JSON from stdin (SessionStart hook input includes session_id +
# source: startup|resume|clear|compact). Capture for logging — we want
# persistent evidence of which trigger actually fires in remote sessions.
HOOK_INPUT="$(cat)"
HOOK_SOURCE="$(echo "$HOOK_INPUT" | grep -oE '"source"[[:space:]]*:[[:space:]]*"[^"]*"' | head -1 | sed 's/.*:[[:space:]]*"\([^"]*\)".*/\1/')"
HOOK_SOURCE="${HOOK_SOURCE:-unknown}"

# Skip in non-remote (terminal) sessions — terminal users run cc / setup-cc.sh manually.
if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

# Persistent log so the next session has retroactive evidence of past triggers.
# Container is ephemeral — this only survives within ONE container's lifetime,
# which is exactly what we need to verify "did SessionStart fire at startup
# in this container?"
LOG_DIR="${CLAUDE_PROJECT_DIR:-/tmp}/.workflow-state"
mkdir -p "$LOG_DIR" 2>/dev/null || true
LOG_FILE="$LOG_DIR/session-start.log"
echo "$(date -Iseconds) source=$HOOK_SOURCE pid=$$ session_id=$(echo "$HOOK_INPUT" | grep -oE '"session_id"[[:space:]]*:[[:space:]]*"[^"]*"' | sed 's/.*:[[:space:]]*"\([^"]*\)".*/\1/')" >> "$LOG_FILE" 2>/dev/null || true

echo "[session-start-remote] start (source=$HOOK_SOURCE)"

if [ -z "${CLAUDE_PROJECT_DIR:-}" ]; then
  echo "[session-start-remote] FAIL: \$CLAUDE_PROJECT_DIR unset" >&2
  exit 0  # don't kill the session
fi

# Resolve forge framework dir from hook location (canonical, independent
# of CLAUDE_PROJECT_DIR). Used to scope framework-only operations
# (main-sync, VALIDATION) to forge_dev sessions so consumer projects
# that load forge as adapter don't get framework-targeted behaviour
# misapplied to their own working tree.
HOOK_FRAMEWORK="$(cd "$(dirname "$(readlink -f "$0")")/../../.." 2>/dev/null && pwd || echo "")"
PROJECT_REAL="$(realpath "$CLAUDE_PROJECT_DIR" 2>/dev/null || echo "$CLAUDE_PROJECT_DIR")"
IN_FRAMEWORK=0
if [ -n "$HOOK_FRAMEWORK" ] && { [ "$PROJECT_REAL" = "$HOOK_FRAMEWORK" ] || [[ "$PROJECT_REAL" == "$HOOK_FRAMEWORK"/* ]]; }; then
  IN_FRAMEWORK=1
fi

SETUP="$CLAUDE_PROJECT_DIR/scripts/setup-cc.sh"
if [ ! -x "$SETUP" ]; then
  echo "[session-start-remote] FAIL: $SETUP missing or not executable" >&2
  exit 0
fi

if bash "$SETUP" 2>&1 | sed 's/^/[session-start-remote] setup: /'; then
  echo "[session-start-remote] done (setup-cc.sh ok)"
else
  echo "[session-start-remote] done (setup-cc.sh exit=$?)"
fi

# --- Harness branch override (no-branching policy per CLAUDE.md) ---
# Framework-scoped: only fires when this session IS forge_dev. Consumer
# projects that use forge as adapter have their own pull cadence — do
# not auto-pull their main.
if [ "$IN_FRAMEWORK" -ne 1 ]; then
  echo "[session-start-remote] scope: consumer session ($PROJECT_REAL outside $HOOK_FRAMEWORK) — skipping framework-only main-sync and VALIDATION"
  exit 0
fi

# The web/desktop harness puts each session on a claude/<name>-<hash>
# branch by default. Per CLAUDE.md Invariant: "No branching ceremony —
# single-dev workflow, commit directly to main when authorised." Auto-
# switch to main HEAD if (a) on harness-default branch, (b) tree clean.
# Skip otherwise — never destroy WIP.
cd "$CLAUDE_PROJECT_DIR" 2>/dev/null || exit 0

CURRENT_BRANCH="$(git symbolic-ref --short HEAD 2>/dev/null || true)"
case "$CURRENT_BRANCH" in
  claude/*)
    if [ -z "$(git status --porcelain 2>/dev/null)" ]; then
      echo "[session-start-remote] branch-override: on $CURRENT_BRANCH, tree clean — switching to main"
      if git fetch origin main 2>&1 | sed 's/^/[session-start-remote] fetch: /' \
         && git checkout main 2>&1 | sed 's/^/[session-start-remote] checkout: /' \
         && git pull --ff-only origin main 2>&1 | sed 's/^/[session-start-remote] pull: /'; then
        echo "[session-start-remote] branch-override: now on main at $(git rev-parse --short HEAD)"
        echo "$(date -Iseconds) branch-override src=$CURRENT_BRANCH dst=main commit=$(git rev-parse --short HEAD)" >> "$LOG_FILE" 2>/dev/null || true
      else
        echo "[session-start-remote] branch-override: FAILED — staying on $CURRENT_BRANCH"
      fi
    else
      echo "[session-start-remote] branch-override: on $CURRENT_BRANCH but tree dirty — skipped (preserve WIP)"
    fi
    ;;
  main)
    # Already on main — just pull latest if possible
    if [ -z "$(git status --porcelain 2>/dev/null)" ]; then
      if git fetch origin main 2>&1 | sed 's/^/[session-start-remote] fetch: /' \
         && git pull --ff-only origin main 2>&1 | sed 's/^/[session-start-remote] pull: /'; then
        echo "[session-start-remote] main-sync: at $(git rev-parse --short HEAD)"
      fi
    fi
    ;;
  *)
    echo "[session-start-remote] branch-override: on $CURRENT_BRANCH (non-harness, non-main) — no action"
    ;;
esac

# --- VALIDATION block (next-session self-check) ---
# Prints PASS/FAIL per shipped component so the user sees the state in
# the first system-reminder without having to run anything. Update the
# checks when shipping new components.
echo "[session-start-remote] === VALIDATION ==="

if [ -L .git/hooks/pre-commit ]; then
  echo "[session-start-remote] PASS git pre-commit hook wired"
else
  echo "[session-start-remote] FAIL git pre-commit hook MISSING — setup-cc.sh did not install symlinks"
fi

if grep -q '"SessionStart"' .claude/settings.json 2>/dev/null; then
  echo "[session-start-remote] PASS SessionStart hook registered in settings.json"
else
  echo "[session-start-remote] FAIL SessionStart not in settings.json"
fi

if [ -x orchestrators/claude-code/hooks/buddy-boot-inject.sh ]; then
  echo "[session-start-remote] PASS buddy-boot-inject.sh present (SessionStart owns boot for claude-desktop/web)"
else
  echo "[session-start-remote] FAIL buddy-boot-inject.sh missing or not executable"
fi

BRANCH_NOW="$(git symbolic-ref --short HEAD 2>/dev/null || echo unknown)"
if [ "$BRANCH_NOW" = "main" ]; then
  echo "[session-start-remote] PASS on main branch (no-branching override effective)"
else
  echo "[session-start-remote] FAIL on $BRANCH_NOW (expected main — branch-override did not switch)"
fi

echo "[session-start-remote] === END VALIDATION ==="

exit 0
