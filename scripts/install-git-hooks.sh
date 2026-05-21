#!/usr/bin/env bash
# install-git-hooks.sh — Idempotent git-hook install for the forge framework.
#
# Symlinks .git/hooks/{pre-commit,commit-msg} into the framework's
# orchestrators/claude-code/hooks/pre-commit.sh. The hook script self-
# detects the invocation mode via $0 basename (F-102 fix), so the same
# file serves both hook events.
#
# Usage:
#   bash $FRAMEWORK_DIR/scripts/install-git-hooks.sh            # uses $PWD as target repo
#   bash $FRAMEWORK_DIR/scripts/install-git-hooks.sh <repo-dir>  # explicit target
#   bash $FRAMEWORK_DIR/scripts/install-git-hooks.sh --check     # probe only, no writes
#   bash $FRAMEWORK_DIR/scripts/install-git-hooks.sh --uninstall # remove symlinks
#
# Worktrees: handled via `git rev-parse --git-dir`, so consumer repos
# created with `git worktree add` work without special-casing.
#
# Idempotent: re-running is a no-op with OK output. Broken symlinks
# (target missing) and wrong-target symlinks are auto-corrected.
# Existing non-symlink files at the hook path produce a WARNUNG and
# are NOT overwritten — operator must inspect and remove manually.
#
# Self-probe (post-install, skipped on --check / --uninstall):
#   - probe-1: validator rejects bad input (exit != 0 on --validate -1).
#   - probe-2: hook script executes via symlink (exec OK; exit code is
#              informational only — a non-zero exit on the current state
#              just means there are real BLOCK conditions staged, which
#              is the *correct* behaviour, not an install failure).

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$(readlink -f "$0")")" && pwd)"
FRAMEWORK_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
HOOK_SCRIPT="$FRAMEWORK_DIR/orchestrators/claude-code/hooks/pre-commit.sh"

# --- Args ---
MODE="install"           # install | check | uninstall
TARGET_REPO=""
for arg in "$@"; do
  case "$arg" in
    --check)     MODE="check" ;;
    --uninstall) MODE="uninstall" ;;
    -h|--help)
      grep -E "^# (install-git-hooks|Usage|Worktrees|Idempotent|Self-probe|  )" "$0" | sed 's/^# //; s/^#$//'
      exit 0 ;;
    -*)
      echo "Unknown flag: $arg" >&2
      echo "Try: $0 --help" >&2
      exit 2 ;;
    *)
      if [ -n "$TARGET_REPO" ]; then
        echo "FEHLER: mehrere Repo-Argumente ('$TARGET_REPO' + '$arg')." >&2
        exit 2
      fi
      TARGET_REPO="$arg" ;;
  esac
done
TARGET_REPO="${TARGET_REPO:-$PWD}"

# --- Resolve target ---
if [ ! -d "$TARGET_REPO" ]; then
  echo "FEHLER: $TARGET_REPO existiert nicht." >&2
  exit 1
fi
TARGET_REPO="$(cd "$TARGET_REPO" && pwd)"

GIT_DIR="$(cd "$TARGET_REPO" && git rev-parse --git-dir 2>/dev/null || true)"
if [ -z "$GIT_DIR" ]; then
  echo "FEHLER: $TARGET_REPO ist kein git-checkout (rev-parse --git-dir)." >&2
  exit 1
fi
case "$GIT_DIR" in
  /*) ;;
  *)  GIT_DIR="$TARGET_REPO/$GIT_DIR" ;;
esac
HOOKS_DIR="$GIT_DIR/hooks"
mkdir -p "$HOOKS_DIR"

if [ ! -f "$HOOK_SCRIPT" ]; then
  echo "FEHLER: hook-script $HOOK_SCRIPT nicht gefunden." >&2
  exit 1
fi

echo "install-git-hooks: target = $TARGET_REPO"
echo "install-git-hooks: hooks-dir = $HOOKS_DIR"
echo "install-git-hooks: hook-script = $HOOK_SCRIPT"
echo "install-git-hooks: mode = $MODE"

# --- Helpers ---
HOOKS=(pre-commit commit-msg)

uninstall_one() {
  local hook="$1"
  local link="$HOOKS_DIR/$hook"
  if [ -L "$link" ]; then
    local current expected
    current="$(readlink -f "$link" 2>/dev/null || true)"
    expected="$(readlink -f "$HOOK_SCRIPT" 2>/dev/null || true)"
    if [ "$current" = "$expected" ]; then
      rm "$link"
      echo "  $hook: entfernt"
      return 0
    fi
    echo "  $hook: SKIP — symlink zeigt nicht auf framework-script (current → $current). Manuell pruefen."
    return 0
  elif [ -e "$link" ]; then
    echo "  $hook: SKIP — kein symlink (echter File). Manuell pruefen."
    return 0
  else
    echo "  $hook: bereits abwesend"
    return 0
  fi
}

install_or_check_one() {
  local hook="$1"
  local link="$HOOKS_DIR/$hook"
  if [ -L "$link" ]; then
    local current expected
    current="$(readlink -f "$link" 2>/dev/null || true)"
    expected="$(readlink -f "$HOOK_SCRIPT" 2>/dev/null || true)"
    if [ "$current" = "$expected" ]; then
      echo "  $hook: OK (already linked)"
      return 0
    fi
    if [ "$MODE" = "check" ]; then
      echo "  $hook: WRONG TARGET ($current → expected $expected)"
      return 1
    fi
    rm "$link"
    ln -s "$HOOK_SCRIPT" "$link"
    echo "  $hook: corrected (was → $current)"
    return 0
  elif [ -e "$link" ]; then
    echo "  $hook: WARNUNG — $link existiert und ist KEIN symlink." >&2
    echo "    Manuell pruefen + sichern, dann erneut. (Datei nicht ueberschrieben.)" >&2
    return 1
  else
    if [ "$MODE" = "check" ]; then
      echo "  $hook: NOT INSTALLED"
      return 1
    fi
    ln -s "$HOOK_SCRIPT" "$link"
    echo "  $hook: angelegt"
    return 0
  fi
}

# --- Dispatch ---
FAILED=0

if [ "$MODE" = "uninstall" ]; then
  for hook in "${HOOKS[@]}"; do
    uninstall_one "$hook" || FAILED=1
  done
  if [ "$FAILED" = "1" ]; then
    exit 1
  fi
  echo "install-git-hooks: uninstall complete."
  exit 0
fi

# install or check
for hook in "${HOOKS[@]}"; do
  install_or_check_one "$hook" || FAILED=1
done

if [ "$FAILED" = "1" ]; then
  if [ "$MODE" = "check" ]; then
    echo "install-git-hooks: CHECK FAIL — siehe Meldungen oben." >&2
  else
    echo "install-git-hooks: INSTALL FAIL — siehe Meldungen oben." >&2
  fi
  exit 1
fi

if [ "$MODE" = "check" ]; then
  echo "install-git-hooks: CHECK PASS"
  exit 0
fi

# --- Self-probe (install only) ---
echo ""
echo "install-git-hooks: self-probe..."

PROBE_FAILED=0
PLAN_ENGINE="$FRAMEWORK_DIR/scripts/plan_engine.py"
if [ -f "$PLAN_ENGINE" ]; then
  if python3 "$PLAN_ENGINE" --validate -1 >/dev/null 2>&1; then
    echo "  probe-1 (validator rejects --validate -1): FAIL — exit 0 expected != 0" >&2
    PROBE_FAILED=1
  else
    echo "  probe-1 (validator rejects --validate -1): PASS"
  fi
else
  echo "  probe-1: SKIP — plan_engine.py not found at $PLAN_ENGINE"
fi

# probe-2: hook executes via the freshly-installed symlink. Output to
# stderr/stdout drained — we only care that the script is reachable +
# executes. Exit code is informational (non-zero is valid; it means
# the current staged state has BLOCK conditions, which is the *correct*
# hook behaviour, not an install bug).
HOOK_EXIT=0
(cd "$TARGET_REPO" && "$HOOKS_DIR/pre-commit") >/dev/null 2>&1 || HOOK_EXIT=$?
if [ "$HOOK_EXIT" = "0" ]; then
  echo "  probe-2 (hook executes via symlink, clean exit on current state): PASS"
else
  echo "  probe-2 (hook executes via symlink): EXEC OK, exit=$HOOK_EXIT — current state has BLOCK conditions. Run \"$HOOKS_DIR/pre-commit\" manually for detail."
fi

if [ "$PROBE_FAILED" = "1" ]; then
  echo "install-git-hooks: INSTALL OK but self-probe FAILED (see above)." >&2
  exit 1
fi

echo ""
echo "install-git-hooks: OK — $HOOKS_DIR/{pre-commit,commit-msg} live."
echo ""
echo "Hint:"
echo "  Re-run any time (idempotent). --check probes without modifying."
echo "  --uninstall removes the symlinks (only if they still point at the framework)."
