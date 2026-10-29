#!/usr/bin/env bash
# git-status-check.sh — Parallel fetch + status-check for FRAMEWORK_DIR + CWD.
#
# Used by the boot STATUS-CHECK step (agents/buddy/boot-status.md). Fetches
# origin (quiet) and reports repos that are behind, ahead or divergent, carry
# uncommitted entries, or (framework only) have installed Forge sources not
# committed in HEAD. Output is parsed by Buddy and surfaced in GREET if any
# repo is non-clean.
#
# Usage:
#   bash $FRAMEWORK_DIR/scripts/git-status-check.sh
#
# Output format (one line per non-clean repo; only present groups, in this
# order, separated by one space):
#   <path> [ahead N | behind M | ahead N, behind M]
#          [uncommitted: S staged, M modified, U untracked]
#          [installed-not-committed: K]
#          [installer: <phase>] | [installer: <phase>, operation open]
#   - uncommitted: porcelain entries (an untracked directory is one entry; an
#     entry can count as staged and modified); all three numbers always shown.
#   - installed groups: only for the target that is the Git root of
#     FRAMEWORK_DIR and only when $FRAMEWORK_DIR/scripts/forge_install.py
#     exists, from `forge_install.py --maintenance status`, printed verbatim:
#     installed-not-committed when K > 0 (installed sources Git reports as not
#     committed in HEAD); installer for every phase other than complete,
#     rolled_back or unprepared, whatever K is, with ", operation open" when
#     the installer reports `operation_open`.
# Targets: the framework checkout when CWD is inside it, plus CWD's own Git
# root when that differs (e.g. a linked worktree nested in the framework).
# Or, if nothing to report:
#   (empty stdout)
# Fetch/status failures and an unavailable installed-vs-HEAD comparison are
# reported on stderr, never as a clean stdout claim; empty stdout alone does
# not establish successful remote freshness. The caller owns tool approval.
#
# Exit codes:
#   0 — always (graceful — never blocks boot)

set -uo pipefail

# Targets: framework + active CWD (canonical-deduped via realpath).
# String-compare alone misses symlink<->target equivalence.
FRAMEWORK_DIR_RAW="${FRAMEWORK_DIR:-$HOME/projects/forge}"
FRAMEWORK_DIR="$(realpath "$FRAMEWORK_DIR_RAW" 2>/dev/null || echo "$FRAMEWORK_DIR_RAW")"
CWD="$(realpath "$(pwd)" 2>/dev/null || pwd)"

# Scope policy:
#   - CWD INSIDE FRAMEWORK_DIR (or equal) → framework is the active repo,
#     check it. CWD is a separate target only when its Git root differs (a
#     nested linked worktree); the canonical-root dedup keeps one otherwise.
#   - CWD OUTSIDE FRAMEWORK_DIR → consumer / project session. The user
#     does not want framework status spam in unrelated sessions. Check
#     ONLY the CWD's own repo if it is one. Framework is silenced.
#   Override: explicit GIT_STATUS_CHECK_INCLUDE_FRAMEWORK=1 forces the
#   framework target back in (legacy / power-user path).
declare -a TARGETS=()
git_root() {
  local root
  # Git resolves both .git directories and linked-worktree pointer files.
  root=$(GIT_OPTIONAL_LOCKS=0 git -C "$1" rev-parse --show-toplevel 2>/dev/null) || return 1
  realpath "$root" 2>/dev/null || echo "$root"
}
add_target() {
  local root existing
  root=$(git_root "$1") || return 0
  for existing in "${TARGETS[@]}"; do
    [ "$existing" = "$root" ] && return 0
  done
  TARGETS+=("$root")
}

if [ "$CWD" = "$FRAMEWORK_DIR" ] || [[ "$CWD" == "$FRAMEWORK_DIR"/* ]]; then
  add_target "$FRAMEWORK_DIR"
  add_target "$CWD"
else
  add_target "$CWD"
  if [ "${GIT_STATUS_CHECK_INCLUDE_FRAMEWORK:-0}" = "1" ]; then
    add_target "$FRAMEWORK_DIR"
  fi
fi

# Installed-vs-HEAD comparison: only the framework's own Git root, only when
# its installer exists (sparse/daily checkouts without it stay silent).
FRAMEWORK_ROOT=$(git_root "$FRAMEWORK_DIR") || FRAMEWORK_ROOT=""
INSTALLER="$FRAMEWORK_DIR/scripts/forge_install.py"

# Safety: require TMPDIR_BOOT mktemp succeeded (set -u would catch but
# explicit check is clearer for trap)
: "${TMPDIR_BOOT:=}"

# Fetch + status per target in parallel (background jobs)
TMPDIR_BOOT=$(mktemp -d -t git-status-check.XXXXXX) || {
  echo "git-status-check: cannot create temporary directory; freshness unknown" >&2
  exit 0
}
trap 'rm -rf "$TMPDIR_BOOT"' EXIT

for index in "${!TARGETS[@]}"; do
  repo=${TARGETS[$index]}
  (
    error_file="$TMPDIR_BOOT/$index.err"
    install_pid=""
    if [ -n "$FRAMEWORK_ROOT" ] && [ "$repo" = "$FRAMEWORK_ROOT" ] && [ -f "$INSTALLER" ]; then
      # Read-only status under the shared installation lock; it may wait on
      # an exclusive operation, hence the bound. Runs concurrently with fetch.
      GIT_OPTIONAL_LOCKS=0 timeout 5 python3 -B "$INSTALLER" --maintenance status \
        >"$TMPDIR_BOOT/$index.install" 2>"$TMPDIR_BOOT/$index.install-err" &
      install_pid=$!
    fi
    # Fetch with strict timeout — never block boot on network
    if timeout 5 git -C "$repo" fetch --quiet origin 2>"$TMPDIR_BOOT/$index.fetch"; then
      :
    else
      fetch_exit=$?
      if [ "$fetch_exit" = "124" ]; then
        printf '%s: fetch timed out after 5s; remote freshness unknown; status uses cached refs\n' "$repo" >> "$error_file"
      else
        printf '%s: fetch failed (exit %s); remote freshness unknown; status uses cached refs\n' "$repo" "$fetch_exit" >> "$error_file"
      fi
      cat "$TMPDIR_BOOT/$index.fetch" >> "$error_file"
    fi
    groups=""
    # Porcelain v1 with --branch gives branch + ahead/behind in one header
    # line; unlike -sb, its labels are stable and untranslated in any locale.
    # The explicit untracked mode keeps user config (status.showUntrackedFiles)
    # from hiding entries.
    if status=$(GIT_OPTIONAL_LOCKS=0 git -C "$repo" status --porcelain=v1 --branch --untracked-files=normal 2>"$TMPDIR_BOOT/$index.status"); then
      status_line=${status%%$'\n'*}
      # Extract ahead/behind. Patterns:
      #   ## main...origin/main                  → clean
      #   ## main...origin/main [behind 3]       → behind
      #   ## main...origin/main [ahead 2]        → ahead
      #   ## main...origin/main [ahead 1, behind 2]
      if [[ "$status_line" =~ \[(ahead\ [0-9]+(,\ behind\ [0-9]+)?|behind\ [0-9]+)\] ]]; then
        # Format: <repo> [<bracket>] — matches the GREET format in agents/buddy/boot-status.md
        groups="[${BASH_REMATCH[1]}]"
      fi
      # Entries after the header: XY <path>; X = index, Y = worktree column.
      staged=0 modified=0 untracked=0
      while IFS= read -r entry; do
        case "$entry" in
          '##'*|'') continue ;;
          '??'*) untracked=$((untracked + 1)); continue ;;
        esac
        case "${entry:0:1}" in ' '|'?'|'!') ;; *) staged=$((staged + 1)) ;; esac
        case "${entry:1:1}" in ' '|'?'|'!') ;; *) modified=$((modified + 1)) ;; esac
      done <<< "$status"
      if [ $((staged + modified + untracked)) -gt 0 ]; then
        groups="${groups:+$groups }[uncommitted: $staged staged, $modified modified, $untracked untracked]"
      fi
    else
      status_exit=$?
      printf '%s: status failed (exit %s); divergence and uncommitted counts unavailable\n' "$repo" "$status_exit" >> "$error_file"
      cat "$TMPDIR_BOOT/$index.status" >> "$error_file"
    fi
    if [ -n "$install_pid" ]; then
      wait "$install_pid"
      install_exit=$?
      unavailable=""
      if [ "$install_exit" = "124" ]; then
        unavailable="installer status timed out after 5s"
      elif [ "$install_exit" != "0" ]; then
        unavailable="installer status exit $install_exit"
        IFS= read -r first_error 2>/dev/null < "$TMPDIR_BOOT/$index.install-err" || true
        [ -n "${first_error:-}" ] && unavailable="$unavailable: ${first_error:0:200}"
      elif ! parsed=$(python3 -I -c '
import json, sys
def emit(groups="", diagnostic=""):
    print(groups)
    print(diagnostic)
    sys.exit(0)
try:
    data = json.load(sys.stdin)
except ValueError:
    data = None
if not isinstance(data, dict):
    emit(diagnostic="unparsable installer status")
phase = data.get("phase")
if not isinstance(phase, str) or not phase.isidentifier():
    emit(diagnostic="installer status with invalid phase")
if phase == "unprepared":
    emit()  # no journal: no installed generation to compare
operation_open = data.get("operation_open")
if not isinstance(operation_open, bool):
    emit(diagnostic="installer status with invalid operation_open")
groups, diagnostic = [], ""
sources = data.get("uncommitted_sources")
if "uncommitted_sources_unavailable" in data:
    lines = str(data["uncommitted_sources_unavailable"]).strip().splitlines() or ["no reason given"]
    diagnostic = lines[0][:200]
elif not isinstance(sources, list):
    diagnostic = "installer status without uncommitted_sources"
elif sources:
    groups.append("[installed-not-committed: %d]" % len(sources))
if phase not in {"complete", "rolled_back"}:
    groups.append("[installer: %s%s]" % (phase, ", operation open" if operation_open else ""))
emit(" ".join(groups), diagnostic)
' 2>/dev/null < "$TMPDIR_BOOT/$index.install"); then
        unavailable="unparsable installer status"
      fi
      installed_groups="" diagnostic="$unavailable"
      if [ -z "$unavailable" ]; then
        { IFS= read -r installed_groups; IFS= read -r diagnostic; } <<< "$parsed" || true
      fi
      if [ -n "$diagnostic" ]; then
        printf '%s: installed-vs-HEAD comparison unavailable (%s)\n' "$repo" "$diagnostic" >> "$error_file"
      fi
      if [ -n "$installed_groups" ]; then
        groups="${groups:+$groups }$installed_groups"
      fi
    fi
    if [ -n "$groups" ]; then
      printf '%s %s\n' "$repo" "$groups" > "$TMPDIR_BOOT/$index.out"
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
error_files=("$TMPDIR_BOOT"/*.err)
if [ ${#error_files[@]} -gt 0 ]; then
  cat "${error_files[@]}" >&2
fi
exit 0
