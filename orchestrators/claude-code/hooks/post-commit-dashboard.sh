#!/usr/bin/env bash
# post-commit-dashboard.sh — Git post-commit Hook.
#
# Triggert Dashboard-Regen + Rsync im Background wenn der letzte Commit
# Task-Status oder Readiness geändert hat (oder docs/plan.yaml angefasst hat).
#
# Installation via scripts/install-dashboard-hooks.sh — Symlink nach
# <consumer-repo>/.git/hooks/post-commit.
#
# Nicht-blockend: Fehler gehen in Log, git commit ist schon durch. Das ist
# by design — post-commit kann Commit nicht cancellen, also führt Async-
# Regen zu keinem Terminal-Hang.
#
# Amend-Safety: git reflog-Action wird geprüft, bei `amend` wird der Hook
# einmal mehr getriggert. Wir deduplizieren via last-deployed-sha-File.

set -euo pipefail

FRAMEWORK_DIR="${FRAMEWORK_DIR:-$HOME/projects/forge}"
DEPLOY_SCRIPT="$FRAMEWORK_DIR/scripts/deploy-dashboard-lite.sh"
LAST_DEPLOYED_SHA_FILE="$HOME/.cache/dashboard-last-deployed-sha"
LOG_FILE="/tmp/dashboard-hook.log"

# --- Guard 1: deploy script must exist ---
if [ ! -x "$DEPLOY_SCRIPT" ]; then
    # Silent skip — hook is in every consumer repo, framework might be
    # missing on some machines. No noise in commit flow.
    exit 0
fi

# --- Guard 2: skip amends when the target SHA already deployed ---
CURRENT_SHA=$(git rev-parse HEAD 2>/dev/null || echo "")
if [ -z "$CURRENT_SHA" ]; then
    exit 0  # no HEAD yet (first commit race), skip
fi
mkdir -p "$(dirname "$LAST_DEPLOYED_SHA_FILE")"
if [ -f "$LAST_DEPLOYED_SHA_FILE" ] && [ "$(cat "$LAST_DEPLOYED_SHA_FILE")" = "$CURRENT_SHA" ]; then
    # Already deployed this SHA (e.g. post-amend re-trigger). Skip.
    exit 0
fi

# --- Guard 3: filter on paths the dashboard cares about ---
# Check what files the last commit touched. Match docs/tasks/*.yaml and
# docs/plan.yaml. For status-field granularity: grep the diff for
# +status:/-status:/+readiness:/-readiness: lines.
CHANGED_FILES=$(git diff --name-only "HEAD~1" "HEAD" 2>/dev/null || git show --name-only --format='' HEAD 2>/dev/null || echo "")
if [ -z "$CHANGED_FILES" ]; then
    exit 0
fi

RELEVANT=0
echo "$CHANGED_FILES" | grep -qE '^docs/tasks/[0-9]+\.yaml$|^docs/plan\.yaml$' && RELEVANT=1

if [ "$RELEVANT" = "0" ]; then
    # No task-yaml or plan.yaml changes — nothing to redeploy.
    exit 0
fi

# Refine: if only docs/tasks/*.yaml changed but no status/readiness field —
# it's a content-only edit (scope/notes/beschreibung) and dashboard render
# is identical. Skip to save the cycle.
if ! git diff "HEAD~1" "HEAD" -- 'docs/tasks/*.yaml' 'docs/plan.yaml' 2>/dev/null \
        | grep -qE '^[+-]\s*(status|readiness):'; then
    # plan.yaml changes without status field are still relevant (phases,
    # milestones, deps); keep a pass-through for them.
    if ! echo "$CHANGED_FILES" | grep -q '^docs/plan\.yaml$'; then
        exit 0
    fi
fi

# --- Run deploy in background, log all output ---
REPO=$(basename "$(git rev-parse --show-toplevel 2>/dev/null || pwd)")
{
    echo "---"
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] post-commit trigger from $REPO @ $CURRENT_SHA"
    if "$DEPLOY_SCRIPT"; then
        echo "$CURRENT_SHA" > "$LAST_DEPLOYED_SHA_FILE"
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] deploy OK (sha recorded)"
    else
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] deploy FAILED"
    fi
} >> "$LOG_FILE" 2>&1 &

disown 2>/dev/null || true
exit 0
