#!/usr/bin/env bash
# deploy-dashboard-lite.sh — Dashboard-Regen + Rsync zu user-konfiguriertem Host.
#
# Gemeinsamer Kern fuer zwei Aufrufer:
#   1. post-commit Hook in Consumer-Repos (Background, /tmp/dashboard-hook.log)
#   2. save-Workflow Step 10 (Foreground, Exit-Status ausgewertet)
#
# Trigger-Filter: der AUFRUFER prueft ob Regen noetig ist (docs/tasks/*.yaml
# oder docs/plan.yaml geaendert). Dieses Script macht immer regen — Filter
# ist Caller-Responsibility.
#
# Env (alle ohne user-spezifische Defaults — must be configured):
#   FRAMEWORK_DIR        — forge root
#                          (auto-detected via dirname falls nicht gesetzt)
#   DASHBOARD_HOST       — SSH-Alias / hostname fuer Deploy-Target (PFLICHT)
#   DASHBOARD_TARGET     — Remote-Pfad fuer index.html (PFLICHT)
#   DASHBOARD_PROJECTS   — comma-separated repo-slugs (PFLICHT)
#   DASHBOARD_HOST_REPO  — repo-slug der den Top-Panel treibt
#                          (default: erster Eintrag aus DASHBOARD_PROJECTS)
#   DASHBOARD_TITLE      — HTML <title> (default: "<host-repo> Dev Dashboard")
#
# Beispiel (in ~/.bashrc oder ~/.config/forge/deploy.env):
#   export DASHBOARD_HOST="my-server"
#   export DASHBOARD_TARGET="~/sites/dashboard/index.html"
#   export DASHBOARD_PROJECTS="myrepo,framework,sideproject"
#   export DASHBOARD_HOST_REPO="myrepo"

set -euo pipefail

# Auto-detect FRAMEWORK_DIR if not set (script lives at $FRAMEWORK_DIR/scripts/).
if [ -z "${FRAMEWORK_DIR:-}" ]; then
    FRAMEWORK_DIR="$(cd "$(dirname "$(readlink -f "$0")")/.." && pwd)"
fi

# Auto-source user-local deploy.env if it exists. This makes the documented
# convention (~/.config/forge/deploy.env) actually work for both
# manual invocation AND the post-commit-dashboard.sh hook (which runs in a
# subshell that does not inherit interactive-shell exports).
DEPLOY_ENV_FILE="${HOME}/.config/forge/deploy.env"
if [ -f "$DEPLOY_ENV_FILE" ]; then
    set -a
    # shellcheck disable=SC1090
    . "$DEPLOY_ENV_FILE"
    set +a
fi

# Required-env validation — fail fast with a clear message.
missing=()
[ -z "${DASHBOARD_HOST:-}" ]      && missing+=("DASHBOARD_HOST")
[ -z "${DASHBOARD_TARGET:-}" ]    && missing+=("DASHBOARD_TARGET")
[ -z "${DASHBOARD_PROJECTS:-}" ]  && missing+=("DASHBOARD_PROJECTS")
if [ ${#missing[@]} -gt 0 ]; then
    echo "ERROR: deploy-dashboard-lite needs config — set: ${missing[*]}" >&2
    echo "Example (export or in ~/.config/forge/deploy.env):" >&2
    echo "  export DASHBOARD_HOST=\"my-server\"" >&2
    echo "  export DASHBOARD_TARGET=\"~/sites/dashboard/index.html\"" >&2
    echo "  export DASHBOARD_PROJECTS=\"repo1,repo2\"" >&2
    exit 2
fi

# Default host-repo to first entry of projects if not set.
if [ -z "${DASHBOARD_HOST_REPO:-}" ]; then
    DASHBOARD_HOST_REPO="${DASHBOARD_PROJECTS%%,*}"
fi

OUTPUT="/tmp/dashboard-lite-$$.html"
trap 'rm -f "$OUTPUT"' EXIT

VENV_PY="$FRAMEWORK_DIR/.venv/bin/python3"
GEN_SCRIPT="$FRAMEWORK_DIR/scripts/generate-dashboard.py"

# Fall back to system python3 if framework venv not bootstrapped.
if [ ! -x "$VENV_PY" ]; then
    if command -v python3 &>/dev/null; then
        VENV_PY="python3"
    else
        echo "ERROR: weder $FRAMEWORK_DIR/.venv/bin/python3 noch system python3 verfuegbar." >&2
        exit 2
    fi
fi

if [ ! -f "$GEN_SCRIPT" ]; then
    echo "ERROR: $GEN_SCRIPT nicht gefunden." >&2
    exit 2
fi

echo "[deploy-dashboard-lite] regen ..."
gen_args=(--host-repo "$DASHBOARD_HOST_REPO"
          --projects  "$DASHBOARD_PROJECTS"
          --output    "$OUTPUT")
if [ -n "${DASHBOARD_TITLE:-}" ]; then
    gen_args+=(--title "$DASHBOARD_TITLE")
fi
if ! "$VENV_PY" "$GEN_SCRIPT" "${gen_args[@]}" 2>&1 | tail -4; then
    echo "ERROR: Dashboard-Regen fehlgeschlagen." >&2
    exit 3
fi

if [ ! -s "$OUTPUT" ]; then
    echo "ERROR: Output leer." >&2
    exit 3
fi

echo "[deploy-dashboard-lite] rsync $DASHBOARD_HOST ..."
if ! rsync -az --timeout=30 "$OUTPUT" "$DASHBOARD_HOST:$DASHBOARD_TARGET" 2>&1 | tail -4; then
    echo "ERROR: Rsync fehlgeschlagen (Host offline?)." >&2
    exit 4
fi

SIZE_KB=$(( $(stat -c '%s' "$OUTPUT") / 1024 ))
echo "[deploy-dashboard-lite] OK — ${SIZE_KB} KB deployed to $DASHBOARD_HOST:$DASHBOARD_TARGET"
