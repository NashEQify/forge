#!/usr/bin/env bash
# git-status-check.sh — Parallel fetch + status-check for FRAMEWORK_DIR + CWD.
#
# Used by boot.md STATUS-CHECK step. Fetches origin (quiet) and reports
# repos that are behind, ahead, or divergent. Output is parsed by Buddy
# and surfaced in GREET if any repo is non-clean.
#
# Usage:
#   bash $FRAMEWORK_DIR/scripts/git-status-check.sh
#
# Output format (one line per non-clean repo):
#   <path> <ahead-N> <behind-N>
# Or, if all clean:
#   (empty stdout)
#
# Exit codes:
#   0 — always (graceful — never blocks boot)

set -uo pipefail

# Targets: framework + active CWD (canonical-deduped via realpath).
# String-compare alone misses symlink<->target equivalence — see F-H-008.
FRAMEWORK_DIR_RAW="${FRAMEWORK_DIR:-$HOME/projects/forge}"
FRAMEWORK_DIR="$(realpath "$FRAMEWORK_DIR_RAW" 2>/dev/null || echo "$FRAMEWORK_DIR_RAW")"
CWD="$(realpath "$(pwd)" 2>/dev/null || pwd)"

declare -a TARGETS=("$FRAMEWORK_DIR")
if [ "$CWD" != "$FRAMEWORK_DIR" ] && [ -d "$CWD/.git" ]; then
  TARGETS+=("$CWD")
fi

# Safety: require TMPDIR_BOOT mktemp succeeded (set -u would catch but
# explicit check is clearer for trap)
: "${TMPDIR_BOOT:=}"

# Fetch + status per target in parallel (background jobs)
TMPDIR_BOOT=$(mktemp -d -t git-status-check.XXXXXX)
trap 'rm -rf "$TMPDIR_BOOT"' EXIT

for repo in "${TARGETS[@]}"; do
  if [ ! -d "$repo/.git" ]; then
    continue
  fi
  (
    # Fetch with strict timeout — never block boot on network
    timeout 5 git -C "$repo" fetch --quiet origin 2>/dev/null || true
    # Status -sb gives branch + ahead/behind in one line
    status_line=$(git -C "$repo" status -sb 2>/dev/null | head -1)
    # Extract ahead/behind. Patterns:
    #   ## main...origin/main                  → clean
    #   ## main...origin/main [behind 3]       → behind
    #   ## main...origin/main [ahead 2]        → ahead
    #   ## main...origin/main [ahead 1, behind 2]
    if [[ "$status_line" =~ \[([^\]]+)\] ]]; then
      # Format: <repo> [<bracket>] — matches boot.md GREET-format spec
      bracket="${BASH_REMATCH[1]}"
      echo "$repo [$bracket]" > "$TMPDIR_BOOT/$(echo "$repo" | tr '/' '_').out"
    fi
  ) &
done
wait

# Concatenate output (only non-clean repos).
# nullglob makes the *.out glob expand to nothing if no files match (all
# repos clean — the common case). Without it, the glob expands to a
# literal pattern and cat fails with exit 1, even though stderr is
# suppressed — the exit-code propagates and breaks boot-step 5.
# 421-Finding B-1.
shopt -s nullglob
out_files=("$TMPDIR_BOOT"/*.out)
if [ ${#out_files[@]} -gt 0 ]; then
  cat "${out_files[@]}"
fi
exit 0
