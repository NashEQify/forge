#!/usr/bin/env bash
# deploy-docs.sh — Build mkdocs site(s) + dashboard, rsync to user-config'd host.
#
# Usage: ./scripts/deploy-docs.sh [--dry-run]
#
# Three-site build: Product (/) + Framework (/dev/) + Dashboard (/dashboard/).
# All three are optional — if mkdocs.yml/mkdocs-framework.yml are missing,
# those steps skip gracefully. Dashboard generation runs if generate-dashboard.py
# is present and DASHBOARD_PROJECTS is set.
#
# Env (no user-specific defaults — configure per host):
#   DEPLOY_REMOTE         — SSH alias / hostname for deploy target (REQUIRED)
#   DEPLOY_REMOTE_PATH    — Remote site directory (REQUIRED, e.g. "~/sites/repo/")
#   DASHBOARD_PROJECTS    — comma-separated repo slugs (REQUIRED for dashboard)
#   DASHBOARD_HOST_REPO   — repo-slug for Top-Panel; default: first project
#   DASHBOARD_TITLE       — HTML <title>; default: "<host-repo> Dev Dashboard"
#
# Example (export from ~/.bashrc or sourced from ~/.config/forge/deploy.env):
#   export DEPLOY_REMOTE="my-server"
#   export DEPLOY_REMOTE_PATH="~/sites/myproject/"
#   export DASHBOARD_PROJECTS="myrepo,framework"
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
VENV="$REPO_ROOT/.venv-docs"
SITE_DIR="$REPO_ROOT/_site"
FRAMEWORK_SITE_DIR="$REPO_ROOT/_site-framework"
DASHBOARD_OUT="$SITE_DIR/dashboard"

# Required-env validation
missing=()
[ -z "${DEPLOY_REMOTE:-}" ]      && missing+=("DEPLOY_REMOTE")
[ -z "${DEPLOY_REMOTE_PATH:-}" ] && missing+=("DEPLOY_REMOTE_PATH")
[ -z "${DASHBOARD_PROJECTS:-}" ] && missing+=("DASHBOARD_PROJECTS")
if [ ${#missing[@]} -gt 0 ]; then
    echo "ERROR: deploy-docs needs config — set: ${missing[*]}" >&2
    echo "Example (export or source ~/.config/forge/deploy.env):" >&2
    echo "  export DEPLOY_REMOTE=\"my-server\"" >&2
    echo "  export DEPLOY_REMOTE_PATH=\"~/sites/myproject/\"" >&2
    echo "  export DASHBOARD_PROJECTS=\"repo1,repo2\"" >&2
    exit 2
fi

REMOTE="$DEPLOY_REMOTE"
REMOTE_PATH="$DEPLOY_REMOTE_PATH"

# Default host-repo to first project if not set.
if [ -z "${DASHBOARD_HOST_REPO:-}" ]; then
    DASHBOARD_HOST_REPO="${DASHBOARD_PROJECTS%%,*}"
fi
# Colors
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
NC='\033[0m'

# --- Dry-run flag ---
DRY_RUN=0
for arg in "$@"; do
  case "$arg" in
    --dry-run|-n) DRY_RUN=1 ;;
  esac
done

# --- Step 1: Generate (both sites) ---
echo -e "${YELLOW}[1/7] Regenerating status overlay (Product)...${NC}"
python3 "$REPO_ROOT/scripts/generate-status.py" 2>/dev/null || echo "  (status script skipped)"

echo -e "${YELLOW}[2/7] Regenerating architecture registry (Framework)...${NC}"
# Default output: docs/architecture/generated/ (canonical, single location).
# Override-parameter previously pointed at docs/framework/generated/ — created
# a second copy that drifted silently. Unified post-3b fix.
python3 "$REPO_ROOT/scripts/generate-architecture.py" \
  2>/dev/null || echo "  (architecture script skipped)"

# --- Step 1b: Dashboard static HTML ---
# Multi-repo dashboard: generate-dashboard.py loads plan.yaml from each
# --projects entry via plan_engine library import. --host-repo drives the
# Top-Panel (Target, Bottleneck, Next Action, Critical Path, Warnings).
echo -e "${YELLOW}[3/7] Regenerating dashboard (multi-repo, host=$DASHBOARD_HOST_REPO)...${NC}"
gen_args=(--host-repo "$DASHBOARD_HOST_REPO"
          --projects  "$DASHBOARD_PROJECTS"
          --output    "$DASHBOARD_OUT/index.html")
[ -n "${DASHBOARD_TITLE:-}" ] && gen_args+=(--title "$DASHBOARD_TITLE")
python3 "$REPO_ROOT/scripts/generate-dashboard.py" "${gen_args[@]}" \
  || {
    echo "  WARNING: dashboard generation failed — continuing without dashboard update" >&2
  }

# In --dry-run we stop right after the dashboard step so the test loop
# exercises the new A5b/A5c changes without running the (slow) mkdocs build
# or the actual rsync. Remove this early-exit if you need dry-run to also
# validate the mkdocs build.
if [ "$DRY_RUN" -eq 1 ]; then
  echo -e "${GREEN}Dry-run: dashboard generate step complete; skipping mkdocs build + rsync.${NC}"
  echo "  Dashboard output: $DASHBOARD_OUT/"
  ls -la "$DASHBOARD_OUT/" 2>/dev/null | head -5 || echo "  (dashboard dir missing)"
  exit 0
fi

# --- Step 2: Sync framework source files ---
# Legacy migration step: source dir docs/architecture/framework/ existed in
# pre-split state. In framework-native repo, framework docs live directly
# under docs/framework/ — no sync needed. Graceful skip if legacy source
# absent.
echo -e "${YELLOW}[4/7] Syncing framework source files...${NC}"
FW_LEGACY_SRC="$REPO_ROOT/docs/architecture/framework"
if [ -d "$FW_LEGACY_SRC" ]; then
  rsync -a --delete \
    --exclude generated/ \
    --exclude .gitkeep \
    --exclude stylesheets/ \
    --exclude javascripts/ \
    --exclude howto/ \
    "$FW_LEGACY_SRC/" "$REPO_ROOT/docs/framework/"
  echo "  Synced docs/architecture/framework/ -> docs/framework/"
else
  echo "  SKIP: $FW_LEGACY_SRC absent — framework docs are already native"
  echo "        in docs/framework/ (post-split; Task-011 Phase 2b migration)"
fi

# --- Step 3: Build both sites ---
# mkdocs.yml + mkdocs-framework.yml are optional. Each consumer/host repo
# may have its own; if missing, builds skip gracefully and only the
# dashboard rsyncs (or nothing if no mkdocs and no dashboard config).
MKDOCS_READY=1
if [ ! -f "$REPO_ROOT/mkdocs.yml" ] || [ ! -f "$REPO_ROOT/mkdocs-framework.yml" ]; then
  MKDOCS_READY=0
fi

if [ "$MKDOCS_READY" -eq 1 ]; then
  echo -e "${YELLOW}[5/7] Building Product site (mkdocs.yml)...${NC}"
  if [ ! -d "$VENV" ]; then
      echo "  Creating venv..."
      python3 -m venv "$VENV"
  fi
  "$VENV/bin/pip" install -q -r "$REPO_ROOT/requirements-docs.txt"
  "$VENV/bin/mkdocs" build --strict -f "$REPO_ROOT/mkdocs.yml"

  echo -e "${YELLOW}[6/7] Building Framework site (mkdocs-framework.yml)...${NC}"
  "$VENV/bin/mkdocs" build --strict -f "$REPO_ROOT/mkdocs-framework.yml"

  # Merge: Framework site goes into Product site at /dev/
  cp -r "$FRAMEWORK_SITE_DIR/." "$SITE_DIR/dev/"
  echo "  Merged framework into $SITE_DIR/dev/"

  # Note: mkdocs build --strict strips the dashboard from _site/ because it's
  # not part of the mkdocs nav. We regenerate it here so the rsync in Step 7
  # picks up the fresh static HTML alongside the product/framework content.
  if [ ! -f "$DASHBOARD_OUT/index.html" ]; then
    echo "  (redashboard) regenerating after mkdocs build"
    python3 "$REPO_ROOT/scripts/generate-dashboard.py" "${gen_args[@]}" \
      || echo "  WARNING: dashboard re-generation failed" >&2
  fi
else
  echo -e "${YELLOW}[5/7] Building Product site (mkdocs.yml)...${NC}"
  echo "  SKIP: mkdocs.yml missing in framework repo."
  echo "        mkdocs config migration pending (Task-011 Phase 4)."
  echo -e "${YELLOW}[6/7] Building Framework site (mkdocs-framework.yml)...${NC}"
  echo "  SKIP: mkdocs-framework.yml missing — same as above."
fi

# --- Step 4: Deploy ---
echo -e "${YELLOW}[7/7] Deploying...${NC}"
if [ "$DRY_RUN" -eq 1 ]; then
  echo "  DRY-RUN: would rsync $SITE_DIR/ -> $REMOTE:$REMOTE_PATH"
  echo "  DRY-RUN: dashboard output at $DASHBOARD_OUT/"
  ls -la "$DASHBOARD_OUT/" 2>/dev/null || echo "  (dashboard dir missing)"
  echo -e "${GREEN}Dry-run complete.${NC}"
  exit 0
fi

if [ "$MKDOCS_READY" -eq 0 ]; then
  echo "  SKIP: deploy bypassed because mkdocs build did not run."
  echo "        (rsync with --delete on a partial _site/ would strip live"
  echo "        deployment. Restore deploy by migrating mkdocs configs.)"
  echo -e "${GREEN}Partial run: local generation steps 1-3 complete.${NC}"
  echo "  Dashboard output (local): $DASHBOARD_OUT/"
  exit 0
fi

rsync -avz --delete --quiet "$SITE_DIR/" "$REMOTE:$REMOTE_PATH"

# Dashboard: pure static HTML lives under $REMOTE_PATH/dashboard/ via the
# rsync above. No remote services / containers required.

echo -e "${GREEN}Done!${NC}"
echo -e "${GREEN}Deployed: $SITE_DIR/ -> $REMOTE:$REMOTE_PATH${NC}"
[ -f "$DASHBOARD_OUT/index.html" ] && echo -e "${GREEN}Dashboard: $REMOTE:$REMOTE_PATH/dashboard/${NC}"
