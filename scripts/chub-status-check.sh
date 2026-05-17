#!/usr/bin/env bash
# chub-status-check.sh — boot-time presence check for the chub CLI.
#
# Used by boot.md STATUS-CHECK step in parallel with git-status-check.sh.
# Emits a single advisory line if chub is missing; emits nothing when
# present. Output is parsed by Buddy and surfaced in GREET when non-empty.
#
# Usage:
#   bash $FRAMEWORK_DIR/scripts/chub-status-check.sh
#
# Output format:
#   non-empty line  → chub missing, install hint
#   empty stdout    → chub installed
#
# Exit codes:
#   0 — always (graceful — never blocks boot)
#
# Background: build-468 L-007 — chub is a get_api_docs prerequisite
# but not installed by default; mid-build install adds turn-cost.
# Boot-time check converts the runtime surprise into a boot-time nudge.

set -uo pipefail

if ! command -v chub >/dev/null 2>&1; then
  echo "chub not installed — get_api_docs falls back to WebFetch. Install: npm install -g @aisuite/chub"
fi

exit 0
