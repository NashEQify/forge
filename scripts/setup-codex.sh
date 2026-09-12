#!/usr/bin/env bash
# Install generated Codex roles, skills and explicit AGENTS boot entries.
# Usage: setup-codex.sh [--check] [--migrate-legacy] [project-dir ...]
# CODEX_HOME and AGENTS_HOME select isolated/staged destinations when provided.
# --check never writes; unknown/edited files and symlinks are conflicts.
# --migrate-legacy adopts only byte-identical known legacy roles/skill wrappers.
# No Codex config.toml, credentials, or Git hooks are changed by this installer.
# Install shared Git hooks separately with scripts/install-git-hooks.sh.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$(readlink -f "$0")")" && pwd)"
FRAMEWORK_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

if [ ! -f "$FRAMEWORK_DIR/agents/buddy/boot.md" ] || [ ! -f "$FRAMEWORK_DIR/framework/boot-navigation.md" ]; then
  echo "ERROR: missing Forge boot/navigation under $FRAMEWORK_DIR" >&2
  exit 1
fi

exec python3 -B "$FRAMEWORK_DIR/scripts/generate_codex_agents.py" \
  --repo "$FRAMEWORK_DIR" --install "$@"
