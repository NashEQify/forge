#!/usr/bin/env bash
# Public compatibility entry: every mutation belongs to the coordinator.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$(readlink -f "$0")")" && pwd)"
exec python3 -B "$SCRIPT_DIR/forge_install.py" "$@"
