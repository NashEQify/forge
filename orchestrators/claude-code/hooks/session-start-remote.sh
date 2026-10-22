#!/usr/bin/env bash
# Session entry observes maintenance; it never updates sources or installs hosts.
set -euo pipefail
cat >/dev/null
if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then exit 0; fi
HERE="$(cd "$(dirname "$(readlink -f "$0")")" && pwd)"
if [ -f "$HERE/../../scripts/forge_install.py" ]; then
  FRAMEWORK="$(cd "$HERE/../.." && pwd)"
else
  FRAMEWORK="$(cd "$HERE/../../.." && pwd)"
fi
echo "[session-start-remote] coordinated maintenance status; no automatic source update"
python3 -B "$FRAMEWORK/scripts/forge_install.py" --maintenance status --require-ready
