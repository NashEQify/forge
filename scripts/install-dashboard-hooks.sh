#!/usr/bin/env bash
# install-dashboard-hooks.sh — Symlink post-commit Hook in Consumer-Repos.
#
# Idempotent. Läuft über die Consumer-Repo-Liste (BuddyAI, forge,
# personal, Huddle) und installiert den post-commit-Hook als Symlink nach
# <repo>/.git/hooks/post-commit. Bei bestehendem Non-Symlink: abort mit
# Warnung — User muss manuell entscheiden.
#
# Usage: ./scripts/install-dashboard-hooks.sh [--dry-run]

set -euo pipefail

FRAMEWORK_DIR="${FRAMEWORK_DIR:-$HOME/projects/forge}"
HOOK_SOURCE="$FRAMEWORK_DIR/orchestrators/claude-code/hooks/post-commit-dashboard.sh"

if [ ! -f "$HOOK_SOURCE" ]; then
    echo "ERROR: Hook source nicht gefunden: $HOOK_SOURCE" >&2
    exit 1
fi
chmod +x "$HOOK_SOURCE"
chmod +x "$FRAMEWORK_DIR/scripts/deploy-dashboard-lite.sh"

DRY_RUN=0
if [ "${1:-}" = "--dry-run" ]; then
    DRY_RUN=1
fi

# Candidate consumer repos — all with docs/tasks/ structure.
REPOS=(
    "$HOME/projects/BuddyAI"
    "$HOME/projects/forge"
    "$HOME/projects/personal"
    # Huddle: excluded bis docs/tasks/ existiert
)

for repo in "${REPOS[@]}"; do
    if [ ! -d "$repo/.git" ]; then
        echo "skip — $repo (not a git repo)"
        continue
    fi

    hook_path="$repo/.git/hooks/post-commit"
    if [ -L "$hook_path" ]; then
        current_target=$(readlink -f "$hook_path" 2>/dev/null || echo "")
        if [ "$current_target" = "$(readlink -f "$HOOK_SOURCE")" ]; then
            echo "ok   — $repo (hook already symlinked correctly)"
            continue
        else
            echo "WARN — $repo hook points to $current_target, expected $HOOK_SOURCE"
            echo "       überschreiben? manuell entscheiden."
            continue
        fi
    elif [ -f "$hook_path" ]; then
        echo "WARN — $repo hat bereits einen post-commit Hook (kein Symlink)."
        echo "       inhalt:"
        head -5 "$hook_path" | sed 's/^/         /'
        echo "       NICHT automatisch ersetzt — manuell entscheiden."
        continue
    fi

    if [ "$DRY_RUN" = "1" ]; then
        echo "DRY  — would ln -s $HOOK_SOURCE $hook_path"
    else
        ln -s "$HOOK_SOURCE" "$hook_path"
        echo "ok   — $repo (hook symlinked)"
    fi
done

if [ "$DRY_RUN" = "0" ]; then
    echo ""
    echo "Installation done. Test mit einem Status-Commit in einem Consumer-Repo:"
    echo "  tail -f /tmp/dashboard-hook.log"
fi
