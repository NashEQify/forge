#!/usr/bin/env bash
# chub-status-check.sh — presence check for the chub CLI.
#
# Called by the boot probe (git-status-check.sh --boot), which prints its
# output as the `chub:` fact line (`chub: installed` when the output is empty).
# It is not a boot step of its own. Emits a single advisory line if chub is
# missing; emits nothing when present.
#
# Usage:
#   bash $FRAMEWORK_DIR/scripts/chub-status-check.sh   (normally via the probe)
#
# Output format:
#   non-empty line  → chub missing, install hint
#   empty stdout    → chub installed
#
# Exit codes:
#   0 — always (graceful — never blocks boot)
#
# Background: chub is a get_api_docs prerequisite
# but not installed by default; mid-build install adds turn-cost.
# Boot-time check converts the runtime surprise into a boot-time nudge.

set -uo pipefail

if ! command -v chub >/dev/null 2>&1; then
  echo "chub not installed — get_api_docs falls back to WebFetch. Install: npm install -g @aisuite/chub"
fi

exit 0
