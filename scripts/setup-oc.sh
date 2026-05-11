#!/usr/bin/env bash
# setup-oc.sh — Generates orchestrators/opencode/opencode.jsonc from the
# .example template by substituting ${FRAMEWORK_DIR} and ${HOME} with the
# detected absolute paths.
#
# Idempotent. Safe to re-run.
#
# Usage: bash $FRAMEWORK_DIR/scripts/setup-oc.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$(readlink -f "$0")")" && pwd)"
FRAMEWORK_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
TEMPLATE="$FRAMEWORK_DIR/orchestrators/opencode/opencode.jsonc.example"
TARGET="$FRAMEWORK_DIR/orchestrators/opencode/opencode.jsonc"

if [ ! -f "$TEMPLATE" ]; then
  echo "setup-oc: ERROR — template not found at $TEMPLATE" >&2
  exit 1
fi

# Substitute ${FRAMEWORK_DIR} and ${HOME} via simple sed (paths shouldn't
# contain | so it's safe as the sed delimiter).
sed -e "s|\${FRAMEWORK_DIR}|$FRAMEWORK_DIR|g" \
    -e "s|\${HOME}|$HOME|g" \
    "$TEMPLATE" > "$TARGET"

echo "setup-oc: wrote $TARGET"
echo "  FRAMEWORK_DIR = $FRAMEWORK_DIR"
echo "  HOME          = $HOME"

if ! command -v opencode &>/dev/null; then
  echo ""
  echo "WARNUNG: 'opencode' nicht im PATH. Install: https://opencode.ai" >&2
fi

echo ""
echo "Verwendung:"
echo "  $FRAMEWORK_DIR/orchestrators/opencode/bin/oc"
