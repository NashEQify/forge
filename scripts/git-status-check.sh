#!/usr/bin/env bash
# git-status-check.sh — Parallel fetch + status-check for FRAMEWORK_DIR + CWD,
# and (--boot) the boot probe: every boot fact a script can gather in one call.
# A pull that changes this file is applied by the next session start (Task467 AC-13).
#
# Used by the boot STATUS-CHECK step (agents/buddy/boot-status.md). Fetches
# origin (quiet) and reports repos that are behind, ahead or divergent, or
# carry uncommitted entries. Output is parsed by Buddy and surfaced in GREET if
# any repo is non-clean.
#
# Usage:
#   bash $FRAMEWORK_DIR/scripts/git-status-check.sh
#   bash <framework root>/scripts/git-status-check.sh --boot [--no-network]
#
# Output format without --boot (one line per non-clean repo; only present
# groups, in this order, separated by one space):
#   <path> [ahead N | behind M | ahead N, behind M]
#          [uncommitted: S staged, M modified, U untracked]
#   - uncommitted: porcelain entries (an untracked directory is one entry; an
#     entry can count as staged and modified); all three numbers always shown.
# Targets: the framework checkout when CWD is inside it, plus CWD's own Git
# root when that differs (e.g. a linked worktree nested in the framework).
# Or, if nothing to report:
#   (empty stdout)
# Fetch/status failures are reported on stderr, never as a clean stdout claim; empty stdout alone does
# not establish successful remote freshness. The caller owns tool approval.
#
# --boot (the boot probe): the framework root is the directory above this
# script unless FRAMEWORK_DIR is set (an explicit FRAMEWORK_DIR wins). Targets:
# the framework always, CWD's Git root, and the configured user repo (resolved
# by `user_scope.py --json`) when its canonical Git root differs from both.
# Only the active project (CWD's Git root) gets the full status line; every
# other target (the framework from a consumer, the user repo) is reported
# only as `<path> [behind N]` when it is behind: its own unpublished work
# (ahead, uncommitted) belongs to that repository's sessions.
# Prints, in this order:
#   orient: <YYYY-MM-DD HH:MM TZ> <hostname> <pwd>
#   <the status lines above for every non-clean target, reduced to behind for
#    the other targets; after a line with uncommitted entries:
#    `  entries: <path>, … (+N more)`, the first five porcelain paths as Git
#    prints them>
#   intent: <absolute path of the nearest intent.md walking up from CWD | none>
#   mode-line: <software | on-demand | none>   (only an explicit
#              `Forge workflows: …` line under the intent's `## Context`)
#   context-dir: <present | absent>             (<CWD>/context/)
#   backlog: <present | absent>                 (<CWD>/docs/backlog.md)
#   handoff: <context/session-handoff.md | context/session-handover.md | absent>
#   session-buffer: <pending N | none | absent> (<CWD>/docs/session-buffer.md;
#              N = lines starting with PENDING, `status: PENDING` lines, and
#              the list items, indented or not, under a `PENDING` heading)
#   pending-project: <present | absent>         (<CWD>/context/maintenance-pending.md)
#   pending-personal: <present | absent | no-user-scope>
#              (<user repo>/context/user/maintenance-pending.md, presence only)
#   plan: <present | absent>                    (<CWD>/docs/plan.yaml)
#   tasks-in-progress: <N>  (<CWD>/docs/tasks/*.yaml, archive/ excluded, whose
#              top-level status is in_progress)
#   binding: <present | absent>  (the handoff carries an opening marker of
#              the development-continuation envelope, as development_continuation.py
#              recognizes it, malformed ones included)
#   chub: <installed | the advisory line of chub-status-check.sh | not installed>
#              (not installed: the helper is not part of this installation)
# then six lines derived only from the facts above and the per-target fetch
# and status outcome (targets in target order):
#   mode: <software | on-demand | unknown | from-intent | none>
#              (the mode-line; from-intent: an intent without one; none: no intent)
#   remote: <fetched | unchecked <path>[, <path>…] | not checked (no network) | none>
#              (unchecked: a target whose fetch failed, timed out or was skipped,
#              or whose branch's upstream is not on origin;
#              none: no Git target)
#   pull-question: <none | <path> behind N[; <path> behind M…]>
#              (behind after a successful fetch only; cached counts never)
#   read-list: <none | absolute paths joined by `, `>  (the intent; the mode's
#              boot units; the handoff; the pending session buffer; the backlog;
#              continuous-maintenance.md with a configured user scope)
#   profile-read: <the personal snapshot command with its stdin request,
#              runnable as printed | no-user-scope | unknown>
#   greet: <none | findings joined by `; `>  (remote unchecked; uncommitted
#              <own path> (N entries); pending recovery: project | personal;
#              user profile missing; user soul missing)
# A fact that cannot be determined prints `unknown` and a stderr diagnostic.
# The facts are file facts, not content; a pull invalidates them (re-probe).
#
# --boot --no-network: no fetch and no Git metadata write.
# Each target runs only `git --no-optional-locks status --porcelain`; its
# entries are counted into the uncommitted group as above (no ahead/behind).
# A line `freshness: not checked (no network)` follows the orient line; the
# fact lines are printed as with --boot.
#
# --boot without a temporary directory: the status lines are computed one by
# one without fetch, with one stderr diagnostic.
#
# Exit codes:
#   0 — always (graceful — never blocks boot)

set -uo pipefail

BOOT=0
NO_NETWORK=0
for arg in "$@"; do
  case "$arg" in
    --boot) BOOT=1 ;;
    --no-network) NO_NETWORK=1 ;;
  esac
done
if [ "$NO_NETWORK" = "1" ] && [ "$BOOT" = "0" ]; then
  echo "git-status-check: --no-network applies only with --boot; nothing checked" >&2
  exit 0
fi

# Targets: framework + active CWD (canonical-deduped via realpath).
# String-compare alone misses symlink<->target equivalence.
if [ "$BOOT" = "1" ] && [ -z "${FRAMEWORK_DIR:-}" ]; then
  # The boot probe resolves the framework root from its own location.
  FRAMEWORK_DIR_RAW="$(cd "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")/.." 2>/dev/null && pwd)"
else
  FRAMEWORK_DIR_RAW="${FRAMEWORK_DIR:-$HOME/projects/forge}"
fi
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
# The framework is a Git target only when it is itself a checkout's root: a
# plugin's copy inside another repository (a Git-tracked HOME) is not that
# repository's framework.
framework_git_root() {
  local root
  root=$(git_root "$FRAMEWORK_DIR") || return 1
  [ "$root" = "$FRAMEWORK_DIR" ] || return 1
  printf '%s\n' "$root"
}
add_framework_target() {
  framework_git_root >/dev/null && add_target "$FRAMEWORK_DIR"
  return 0
}

# Boot probe: the configured user repo, resolved the way user_scope.py --json
# reports it. USER_SCOPE_STATE: configured | none | unknown.
USER_SCOPE_STATE="none"
USER_REPO=""
resolve_user_scope() {
  local resolver="$FRAMEWORK_DIR/scripts/user_scope.py" json parsed
  if [ ! -f "$resolver" ]; then
    echo "git-status-check: user scope resolver missing ($resolver); personal facts unknown" >&2
    USER_SCOPE_STATE="unknown"
    return 0
  fi
  if ! json=$(timeout 5 python3 -B "$resolver" --framework-root "$FRAMEWORK_DIR" --json 2>/dev/null); then
    echo "git-status-check: user scope resolver failed; personal facts unknown" >&2
    USER_SCOPE_STATE="unknown"
    return 0
  fi
  if ! parsed=$(python3 -I -c '
import json, sys
try:
    data = json.load(sys.stdin)
except ValueError:
    data = None
if not isinstance(data, dict):
    print("unknown"); print("unparsable resolver output"); sys.exit(0)
repo = data.get("user_repo")
if data.get("configured") is True and isinstance(repo, str) and repo and "\n" not in repo:
    print("configured"); print(repo); sys.exit(0)
warnings = data.get("warnings") if isinstance(data.get("warnings"), list) else []
warnings = [w for w in warnings if isinstance(w, str)]
unresolved = [w for w in warnings if "not resolved" in w]
if data.get("config_path"):  # a machine setting exists but yields no scope: unusable, not absent
    unresolved += [w for w in warnings if w.startswith(("user_repo ", "user context directory", "machine setting"))
                   and not w.startswith("user_repo missing in machine setting")]
if unresolved:
    print("unknown"); print(unresolved[0].splitlines()[0][:200]); sys.exit(0)
print("none"); print("")
' 2>/dev/null <<< "$json"); then
    echo "git-status-check: user scope resolver output unparsable; personal facts unknown" >&2
    USER_SCOPE_STATE="unknown"
    return 0
  fi
  { IFS= read -r USER_SCOPE_STATE; IFS= read -r USER_REPO; } <<< "$parsed" || true
  case "$USER_SCOPE_STATE" in
    configured) ;;
    unknown)
      echo "git-status-check: user scope not resolved (${USER_REPO:-no reason given}); personal facts unknown" >&2
      USER_REPO="" ;;
    *) USER_SCOPE_STATE="none"; USER_REPO="" ;;
  esac
}

if [ "$BOOT" = "1" ]; then
  resolve_user_scope
  # The framework is always a target; the user repo when its root is distinct.
  if [ "$CWD" = "$FRAMEWORK_DIR" ] || [[ "$CWD" == "$FRAMEWORK_DIR"/* ]]; then
    add_framework_target
    add_target "$CWD"
  else
    add_target "$CWD"
    add_framework_target
  fi
  if [ -n "$USER_REPO" ]; then
    if git_root "$USER_REPO" >/dev/null; then
      add_target "$USER_REPO"
    else
      echo "git-status-check: user repo is not a Git repository ($USER_REPO); its freshness and personal facts unknown" >&2
      USER_SCOPE_STATE="unknown"
    fi
  fi
elif [ "$CWD" = "$FRAMEWORK_DIR" ] || [[ "$CWD" == "$FRAMEWORK_DIR"/* ]]; then
  add_framework_target
  add_target "$CWD"
else
  add_target "$CWD"
  if [ "${GIT_STATUS_CHECK_INCLUDE_FRAMEWORK:-0}" = "1" ]; then
    add_framework_target
  fi
fi

FRAMEWORK_ROOT=$(framework_git_root) || FRAMEWORK_ROOT=""

# Repository-local config that runs commands is neutralized on every target
# other than the framework checkout and the configured user repo (in practice
# the CWD project, whose .git/config the session did not choose): fsmonitor
# for status and fetch; for fetch also the ssh command and upload-pack program come from the
# global/system value or the default, and the ext:: transport is refused.
USER_ROOT=""
[ -n "$USER_REPO" ] && USER_ROOT=$(git_root "$USER_REPO" 2>/dev/null || true)
global_config() {  # <key> <default>: the global value, else the system value, else the default
  local value
  value=$(git config --global --includes --get "$1" 2>/dev/null) \
    || value=$(git config --system --includes --get "$1" 2>/dev/null) \
    || value=$2
  printf '%s' "$value"
}
STATUS_HARDENING=(-c core.fsmonitor=false)
FETCH_HARDENING=(-c core.fsmonitor=false -c protocol.ext.allow=never)
# The first remote.origin.uploadpack Git reads wins (the repository's before -c),
# so the program is passed as fetch's own option.
FETCH_UPLOAD_PACK="--upload-pack=$(global_config remote.origin.uploadpack git-upload-pack)"
if [ -z "${GIT_SSH_COMMAND:-}" ]; then  # GIT_SSH_COMMAND outranks any config
  FETCH_HARDENING+=(-c "core.sshCommand=$(global_config core.sshCommand "${GIT_SSH:-ssh}")")
fi
untrusted_target() {
  [ "$1" != "$FRAMEWORK_ROOT" ] && { [ -z "$USER_ROOT" ] || [ "$1" != "$USER_ROOT" ]; }
}

# The boot probe reports a repository's own work (ahead, uncommitted, entry
# paths) only for the active project, CWD's Git root. Every other target (the
# framework from a consumer, the user repo) is checked only for incoming
# updates (behind), which decide whether the instructions or the profile it
# loads are stale; another repository's unpublished work is not this session's.
OWN_ROOT=$(git_root "$CWD" 2>/dev/null || true)
own_target() {
  [ "$BOOT" = "0" ] || [ "$1" = "$OWN_ROOT" ]
}

# Counts a status output into globals, without printing (called directly, not
# in $(...), where the numbers must outlive the call): PC_STAGED, PC_MODIFIED,
# PC_UNTRACKED, PC_ENTRIES (porcelain entries; an entry can count as staged
# and modified), PC_PATHS (the entry paths as Git prints them), PC_BEHIND (N of
# the branch header's behind N, else empty) and PC_DIVERGENCE (the header's
# ahead/behind group, else empty).
porcelain_counts() {  # <status output> <with branch header: 0|1>
  local status=$1 status_line="" entry
  PC_STAGED=0 PC_MODIFIED=0 PC_UNTRACKED=0 PC_ENTRIES=0 PC_BEHIND="" PC_DIVERGENCE=""
  PC_PATHS=()
  [ "$2" = "1" ] && status_line=${status%%$'\n'*}
  if [[ "$status_line" =~ \[(ahead\ [0-9]+,\ )?behind\ ([0-9]+)\] ]]; then
    PC_BEHIND=${BASH_REMATCH[2]}
  fi
  # Extract ahead/behind. Patterns:
  #   ## main...origin/main                  → clean
  #   ## main...origin/main [behind 3]       → behind
  #   ## main...origin/main [ahead 2]        → ahead
  #   ## main...origin/main [ahead 1, behind 2]
  if [[ "$status_line" =~ \[(ahead\ [0-9]+(,\ behind\ [0-9]+)?|behind\ [0-9]+)\] ]]; then
    PC_DIVERGENCE=${BASH_REMATCH[1]}
  fi
  # Entries after the header: XY <path>; X = index, Y = worktree column.
  while IFS= read -r entry; do
    case "$entry" in
      '##'*|'') continue ;;
    esac
    PC_PATHS+=("${entry:3}")
    PC_ENTRIES=$((PC_ENTRIES + 1))
    case "$entry" in
      '??'*) PC_UNTRACKED=$((PC_UNTRACKED + 1)); continue ;;
    esac
    case "${entry:0:1}" in ' '|'?'|'!') ;; *) PC_STAGED=$((PC_STAGED + 1)) ;; esac
    case "${entry:1:1}" in ' '|'?'|'!') ;; *) PC_MODIFIED=$((PC_MODIFIED + 1)) ;; esac
  done <<< "$status"
}

# Renders the groups (line 1) from porcelain_counts. In --boot mode a second
# line names the first five entry paths as Git prints them (F-6). For a target
# that is not the own project (own: 0) only a behind count is kept.
porcelain_summary() {  # <status output> <with branch header: 0|1> [own: 1|0]
  local groups="" entry shown=""
  porcelain_counts "$1" "$2"
  if [ "${3:-1}" = "0" ]; then
    if [ -n "$PC_BEHIND" ]; then
      printf '%s\n' "[behind $PC_BEHIND]"
    else
      printf '\n'
    fi
    return 0
  fi
  # Format: <repo> [<bracket>] — matches the GREET format in agents/buddy/boot-status.md
  [ -n "$PC_DIVERGENCE" ] && groups="[$PC_DIVERGENCE]"
  if [ $((PC_STAGED + PC_MODIFIED + PC_UNTRACKED)) -gt 0 ]; then
    groups="${groups:+$groups }[uncommitted: $PC_STAGED staged, $PC_MODIFIED modified, $PC_UNTRACKED untracked]"
  fi
  printf '%s\n' "$groups"
  if [ "$BOOT" = "1" ] && [ "${#PC_PATHS[@]}" -gt 0 ]; then
    for entry in "${PC_PATHS[@]:0:5}"; do
      shown="${shown:+$shown, }$entry"
    done
    [ "${#PC_PATHS[@]}" -gt 5 ] && shown="$shown (+$(( ${#PC_PATHS[@]} - 5 )) more)"
    printf '  entries: %s\n' "$shown"
  fi
}

# Boot probe fact lines (--boot). Facts are presence checks and counts; no
# content is read beyond the intent's Context lines, the buffer's headings,
# PENDING line starts, status lines and list markers, the tasks' top-level
# status lines and the handoff's envelope marker lines.
# Paths are relative to CWD (the project, as boot-routing.md routes them).
# Each printed value is also kept in FACT_<key> (dashes as underscores) for
# boot_derived.
fact() {  # <key> <value>: prints `<key>: <value>` and keeps the value
  printf -v "FACT_${1//-/_}" '%s' "$2"
  printf '%s: %s\n' "$1" "$2"
}
fact_unknown() {  # <key> <reason>
  echo "git-status-check: $1 unknown ($2)" >&2
  fact "$1" "unknown"
}
fact_file() {  # <key> <path>: present | absent | unknown
  if [ -f "$2" ]; then
    fact "$1" "present"
  elif [ -e "$2" ]; then
    fact_unknown "$1" "not a regular file: $2"
  else
    fact "$1" "absent"
  fi
}
boot_facts() {
  local dir intent="" mode handoff="" count file chub_script chub_out
  dir="$CWD"
  while :; do
    if [ -f "${dir%/}/intent.md" ]; then
      intent="${dir%/}/intent.md"
      break
    fi
    [ "$dir" = "/" ] && break
    dir=$(dirname "$dir")
  done
  fact "intent" "${intent:-none}"

  if [ -z "$intent" ]; then
    fact "mode-line" "none"
  elif [ ! -r "$intent" ]; then
    fact_unknown "mode-line" "intent.md not readable: $intent"
  else
    # Only an explicit line under `## Context`, up to the next level-1/2 heading.
    mode=$(awk '
      { sub(/\r$/, "") }
      /^##[ \t]+Context[ \t]*$/ { ctx = 1; next }
      ctx && /^##?[ \t]/ { exit }
      ctx {
        line = $0
        sub(/^[ \t]+/, "", line); sub(/[ \t]+$/, "", line)
        if (line == "Forge workflows: software") { print "software"; exit }
        if (line == "Forge workflows: on-demand") { print "on-demand"; exit }
      }' "$intent" 2>/dev/null)
    fact "mode-line" "${mode:-none}"
  fi

  if [ -d "$CWD/context" ]; then
    fact "context-dir" "present"
  elif [ -e "$CWD/context" ]; then
    fact_unknown "context-dir" "not a directory: $CWD/context"
  else
    fact "context-dir" "absent"
  fi
  fact_file "backlog" "$CWD/docs/backlog.md"

  for file in context/session-handoff.md context/session-handover.md; do
    if [ -f "$CWD/$file" ]; then
      handoff="$file"
      break
    fi
  done
  fact "handoff" "${handoff:-absent}"

  file="$CWD/docs/session-buffer.md"
  if [ ! -e "$file" ]; then
    fact "session-buffer" "absent"
  elif [ ! -f "$file" ] || [ ! -r "$file" ]; then
    fact_unknown "session-buffer" "not a readable file: $file"
  else
    # PENDING entries: lines that start with PENDING; `status: PENDING` lines
    # (the block form the save workflow marks PROCESSED); and the list items
    # (`- `, `* `, `<n>. `, indented or not) under a heading whose text is
    # PENDING, up to the next heading. Under that heading a status line inside a
    # counted item belongs to it and is not counted again.
    if count=$(awk '
      { sub(/\r$/, "") }
      /^#+[ \t]/ {
        heading = $0
        sub(/^#+[ \t]+/, "", heading); sub(/[ \t#]+$/, "", heading)
        pending = (heading == "PENDING"); in_item = 0
        next
      }
      /^PENDING/ { n++; in_item = 0; next }
      { status = ($0 ~ /^[ \t]*([-*][ \t]+)?[Ss]tatus:[ \t]*PENDING[ \t]*$/) }
      pending {
        if (status) { if (!in_item) n++; next }
        if ($0 ~ /^[ \t]*([-*]|[0-9]+\.)[ \t]/) { n++; in_item = 1; next }
        if ($0 ~ /^[^ \t]/) in_item = 0
        next
      }
      status { n++ }
      END { print n + 0 }' "$file" 2>/dev/null); then
      if [ "$count" = "0" ]; then
        fact "session-buffer" "none"
      else
        fact "session-buffer" "pending $count"
      fi
    else
      fact_unknown "session-buffer" "cannot read $file"
    fi
  fi

  fact_file "pending-project" "$CWD/context/maintenance-pending.md"
  case "$USER_SCOPE_STATE" in
    configured) fact_file "pending-personal" "$USER_REPO/context/user/maintenance-pending.md" ;;
    unknown) fact "pending-personal" "unknown" ;;  # the resolver diagnostic is already on stderr
    *) fact "pending-personal" "no-user-scope" ;;
  esac

  fact_file "plan" "$CWD/docs/plan.yaml"
  count=0
  for file in "$CWD"/docs/tasks/*.yaml; do
    [ -f "$file" ] || continue
    if grep -Eq "^status:[[:space:]]*[\"']?in_progress[\"']?[[:space:]]*(#.*)?$" "$file" 2>/dev/null; then
      count=$((count + 1))
    fi
  done
  fact "tasks-in-progress" "$count"

  if [ -z "$handoff" ]; then
    fact "binding" "absent"
  elif [ ! -r "$CWD/$handoff" ]; then
    fact_unknown "binding" "handoff not readable: $CWD/$handoff"
  elif grep -Eq '^[^[:alnum:]_`~]*([0-9]{1,9}[.)])?[^[:alnum:]_`~]*(`{3,}|~{3,})[[:blank:]]*forge-development' \
      "$CWD/$handoff" 2>/dev/null; then
    # Any opening marker development_continuation.py (OPENER) treats as an
    # envelope, malformed ones included: the restore step reports those.
    fact "binding" "present"
  else
    fact "binding" "absent"
  fi

  chub_script="$FRAMEWORK_DIR/scripts/chub-status-check.sh"
  if [ ! -e "$chub_script" ]; then
    fact "chub" "not installed"  # the helper is not part of this installation
  elif chub_out=$(bash "$chub_script" 2>/dev/null); then
    chub_out=${chub_out%%$'\n'*}
    fact "chub" "${chub_out:-installed}"
  else
    fact_unknown "chub" "chub-status-check.sh failed (exit $?): $chub_script"
  fi
}

# Quotes one argument as Python's shlex.quote does: bare when it consists only
# of [A-Za-z0-9_@%+=:,./-], else in single quotes with each ' written as '"'"'.
# The letters are spelled out: a bracket range follows the locale's collation.
shell_quote() {  # <argument>
  local sq="'" escaped="'\"'\"'"
  case "$1" in
    '') printf "''" ;;
    *[!abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_@%+=:,./-]*)
      printf "'%s'" "${1//$sq/$escaped}" ;;
    *) printf '%s' "$1" ;;
  esac
}

# The derived lines (--boot), after the fact lines: computed only from the
# FACT_* values, the per-target record and the user scope state; the only
# reads of their own are the existence of the configured user repo's
# context/user/profile.md and soul.md.
boot_derived() {
  local mode remote="" pull="" reads="" greet="" index path arg command=""
  local -a units=()

  if [ "$FACT_intent" = "none" ]; then
    mode="none"
  else
    case "$FACT_mode_line" in
      software|on-demand|unknown) mode=$FACT_mode_line ;;
      *) mode="from-intent" ;;
    esac
  fi
  echo "mode: $mode"

  if [ "${#REC_PATHS[@]}" -eq 0 ]; then
    remote="none"
  elif [ "$NO_NETWORK" = "1" ]; then
    remote="not checked (no network)"
  else
    for index in "${!REC_PATHS[@]}"; do
      [ "${REC_REMOTE[$index]}" = "fetched" ] && continue
      remote="${remote:+$remote, }${REC_PATHS[$index]}"
    done
    if [ -z "$remote" ]; then
      remote="fetched"
    else
      remote="unchecked $remote"
    fi
  fi
  echo "remote: $remote"

  if [ "$NO_NETWORK" = "0" ] && [ "${#REC_PATHS[@]}" -gt 0 ]; then
    for index in "${!REC_PATHS[@]}"; do
      [ "${REC_REMOTE[$index]}" = "fetched" ] || continue
      [ -n "${REC_BEHIND[$index]}" ] && [ "${REC_BEHIND[$index]}" -gt 0 ] || continue
      pull="${pull:+$pull; }${REC_PATHS[$index]} behind ${REC_BEHIND[$index]}"
    done
  fi
  echo "pull-question: ${pull:-none}"

  [ "$FACT_intent" != "none" ] && reads=$FACT_intent
  case "$mode" in
    software) units=("agents/buddy/boot-software.md" "agents/buddy/operational.md") ;;
    on-demand) units=("agents/buddy/boot-on-demand.md") ;;
  esac
  if [ "${#units[@]}" -gt 0 ]; then
    for path in "${units[@]}"; do
      reads="${reads:+$reads, }$FRAMEWORK_DIR/$path"
    done
  fi
  [ "$FACT_handoff" != "absent" ] && reads="${reads:+$reads, }$CWD/$FACT_handoff"
  case "$FACT_session_buffer" in
    "pending "*) reads="${reads:+$reads, }$CWD/docs/session-buffer.md" ;;
  esac
  [ "$FACT_backlog" = "present" ] && reads="${reads:+$reads, }$CWD/docs/backlog.md"
  [ "$USER_SCOPE_STATE" = "configured" ] \
    && reads="${reads:+$reads, }$FRAMEWORK_DIR/skills/knowledge_processor/continuous-maintenance.md"
  echo "read-list: ${reads:-none}"

  case "$USER_SCOPE_STATE" in
    configured)
      for arg in python3 "$FRAMEWORK_DIR/scripts/continuity.py" snapshot --scope personal --project-root "$CWD"; do
        command="${command:+$command }$(shell_quote "$arg")"
      done
      echo "profile-read: printf '%s' '{\"schema_version\":1,\"paths\":[\"profile.md\"]}' | $command" ;;
    none) echo "profile-read: no-user-scope" ;;
    *) echo "profile-read: unknown" ;;
  esac

  case "$remote" in
    "unchecked "*|"not checked (no network)") greet="remote unchecked" ;;
  esac
  if [ -n "$OWN_UNCOMMITTED" ] && [ "$OWN_UNCOMMITTED" -gt 0 ]; then
    greet="${greet:+$greet; }uncommitted $OWN_ROOT ($OWN_UNCOMMITTED)"
  fi
  [ "$FACT_pending_project" = "present" ] && greet="${greet:+$greet; }pending recovery: project"
  [ "$FACT_pending_personal" = "present" ] && greet="${greet:+$greet; }pending recovery: personal"
  if [ "$USER_SCOPE_STATE" = "configured" ]; then
    [ -f "$USER_REPO/context/user/profile.md" ] || greet="${greet:+$greet; }user profile missing"
    [ -f "$USER_REPO/context/user/soul.md" ] || greet="${greet:+$greet; }user soul missing"
  fi
  echo "greet: ${greet:-none}"
}

# Safety: require TMPDIR_BOOT mktemp succeeded (set -u would catch but
# explicit check is clearer for trap)
: "${TMPDIR_BOOT:=}"

# The boot probe's per-target record, in TARGETS order (index i is target i):
# REC_PATHS, REC_REMOTE (fetched | unchecked | offline; empty: no record) and
# REC_BEHIND (N after a successful fetch and status, else empty). OWN_UNCOMMITTED
# is the own target's porcelain entry count after a successful status, else
# empty. Filled from the per-index facts files, or directly by the fallback.
REC_PATHS=()
REC_REMOTE=()
REC_BEHIND=()
OWN_UNCOMMITTED=""

if [ "$BOOT" = "1" ]; then
  orient_host=$(hostname 2>/dev/null || uname -n 2>/dev/null || echo unknown)
  printf 'orient: %s %s %s\n' "$(date '+%Y-%m-%d %H:%M %Z')" "$orient_host" "$(pwd)"
  if [ "$NO_NETWORK" = "1" ]; then
    echo "freshness: not checked (no network)"
  fi
fi

# Fetch + status per target in parallel (background jobs)
# The boot probe writes one diagnostic of its own when mktemp fails.
if [ "$BOOT" = "1" ]; then
  TMPDIR_BOOT=$(mktemp -d -t git-status-check.XXXXXX 2>/dev/null)
else
  TMPDIR_BOOT=$(mktemp -d -t git-status-check.XXXXXX)
fi || {
  if [ "$BOOT" = "0" ]; then
    echo "git-status-check: cannot create temporary directory; freshness unknown" >&2
    exit 0
  fi
  # The boot probe: sequential status lines without temp files and no fetch
  # (its diagnostics need the files).
  TMPDIR_BOOT=""
  if [ "$NO_NETWORK" = "1" ]; then
    echo "git-status-check: cannot create temporary directory; status lines computed one by one" >&2
  else
    echo "git-status-check: cannot create temporary directory; fetch skipped, status from cached refs" >&2
  fi
  for repo in "${TARGETS[@]}"; do
    # No fetch ran: the record says unchecked (offline under --no-network).
    REC_PATHS+=("$repo")
    if [ "$NO_NETWORK" = "1" ]; then REC_REMOTE+=("offline"); else REC_REMOTE+=("unchecked"); fi
    REC_BEHIND+=("")
    harden=()
    untrusted_target "$repo" && harden=("${STATUS_HARDENING[@]}")
    status_command=(git -C "$repo" ${harden[@]+"${harden[@]}"} status --porcelain=v1 --branch --untracked-files=normal)
    if [ "$NO_NETWORK" = "1" ]; then
      status_command=(git --no-optional-locks -C "$repo" ${harden[@]+"${harden[@]}"} status --porcelain --untracked-files=normal)
    fi
    if status=$(GIT_OPTIONAL_LOCKS=0 "${status_command[@]}" 2>/dev/null); then
      own=1
      own_target "$repo" || own=0
      if [ "$own" = "1" ]; then
        porcelain_counts "$status" "$((1 - NO_NETWORK))"
        OWN_UNCOMMITTED=$PC_ENTRIES
      fi
      summary=$(porcelain_summary "$status" "$((1 - NO_NETWORK))" "$own")
      if [ -n "${summary%%$'\n'*}" ]; then
        printf '%s %s\n' "$repo" "$summary"
      fi
    else
      printf '%s: status failed (exit %s); divergence and uncommitted counts unavailable\n' "$repo" "$?" >&2
    fi
  done
  TARGETS=()  # printed above; the fact lines follow
}
trap 'rm -rf "$TMPDIR_BOOT"' EXIT

for index in "${!TARGETS[@]}"; do
  repo=${TARGETS[$index]}
  (
    error_file="$TMPDIR_BOOT/$index.err"
    facts_file="$TMPDIR_BOOT/$index.facts"  # key=value lines for boot_derived
    remote=unchecked
    # Fetch with strict timeout — never block boot on network
    fetch_harden=()
    fetch_options=()
    if untrusted_target "$repo"; then
      fetch_harden=("${FETCH_HARDENING[@]}")
      fetch_options=("$FETCH_UPLOAD_PACK")
    fi
    if [ "$NO_NETWORK" = "1" ]; then
      remote=offline
    elif timeout 5 git -C "$repo" ${fetch_harden[@]+"${fetch_harden[@]}"} fetch --quiet ${fetch_options[@]+"${fetch_options[@]}"} origin 2>"$TMPDIR_BOOT/$index.fetch"; then
      remote=fetched
      # Only origin was fetched: an upstream on another remote (a local `.` is none)
      # was not, so its behind count is cached and the target unchecked.
      harden=()
      untrusted_target "$repo" && harden=("${STATUS_HARDENING[@]}")
      if [ "$BOOT" = "1" ] && branch=$(GIT_OPTIONAL_LOCKS=0 git -C "$repo" ${harden[@]+"${harden[@]}"} symbolic-ref -q HEAD 2>/dev/null) \
          && upstream=$(git -C "$repo" ${harden[@]+"${harden[@]}"} config "branch.${branch#refs/heads/}.remote" 2>/dev/null) \
          && [ "$upstream" != "origin" ] && [ "$upstream" != "." ]; then
        remote=unchecked
      fi
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
    entries_line=""
    # Porcelain v1 with --branch gives branch + ahead/behind in one header
    # line; unlike -sb, its labels are stable and untranslated in any locale.
    # The explicit untracked mode keeps user config (status.showUntrackedFiles)
    # from hiding entries.
    # --boot --no-network: plain porcelain, no branch header (no ahead/behind).
    harden=()
    untrusted_target "$repo" && harden=("${STATUS_HARDENING[@]}")
    status_command=(git -C "$repo" ${harden[@]+"${harden[@]}"} status --porcelain=v1 --branch --untracked-files=normal)
    if [ "$NO_NETWORK" = "1" ]; then
      status_command=(git --no-optional-locks -C "$repo" ${harden[@]+"${harden[@]}"} status --porcelain --untracked-files=normal)
    fi
    if status=$(GIT_OPTIONAL_LOCKS=0 "${status_command[@]}" 2>"$TMPDIR_BOOT/$index.status"); then
      own=1
      own_target "$repo" || own=0
      summary=$(porcelain_summary "$status" "$((1 - NO_NETWORK))" "$own")
      groups=${summary%%$'\n'*}
      [ "$summary" != "$groups" ] && entries_line=${summary#*$'\n'}
      if [ "$BOOT" = "1" ]; then
        porcelain_counts "$status" "$((1 - NO_NETWORK))"
        if [ "$remote" = "fetched" ] && [ -n "$PC_BEHIND" ] && [ "${upstream:-}" != "." ]; then
          printf 'behind=%s\n' "$PC_BEHIND" >> "$facts_file"
        fi
        [ "$own" = "1" ] && printf 'uncommitted=%s\n' "$PC_ENTRIES" >> "$facts_file"
      fi
    else
      status_exit=$?
      printf '%s: status failed (exit %s); divergence and uncommitted counts unavailable\n' "$repo" "$status_exit" >> "$error_file"
      cat "$TMPDIR_BOOT/$index.status" >> "$error_file"
    fi
    if [ -n "$groups" ]; then
      printf '%s %s\n' "$repo" "$groups" > "$TMPDIR_BOOT/$index.out"
      [ -n "$entries_line" ] && printf '%s\n' "$entries_line" >> "$TMPDIR_BOOT/$index.out"
    fi
    [ "$BOOT" = "1" ] && printf 'remote=%s\n' "$remote" >> "$facts_file"
  ) &
done
wait

# The boot probe reads each target's record in TARGETS order (a missing facts
# file leaves its remote empty: not fetched).
if [ "$BOOT" = "1" ] && [ -n "$TMPDIR_BOOT" ]; then
  for index in "${!TARGETS[@]}"; do
    rec_remote=""
    rec_behind=""
    if [ -f "$TMPDIR_BOOT/$index.facts" ]; then
      while IFS='=' read -r key value; do
        case "$key" in
          remote) rec_remote=$value ;;
          behind) rec_behind=$value ;;
          uncommitted) OWN_UNCOMMITTED=$value ;;
        esac
      done < "$TMPDIR_BOOT/$index.facts"
    fi
    REC_PATHS+=("${TARGETS[$index]}")
    REC_REMOTE+=("$rec_remote")
    REC_BEHIND+=("$rec_behind")
  done
fi

# Concatenate output (only non-clean repos).
# nullglob makes the *.out glob expand to nothing if no files match (all
# repos clean — the common case). Without it, the glob expands to a
# literal pattern and cat fails with exit 1, even though stderr is
# suppressed — the exit-code propagates and breaks boot-step 5.
# 421-Finding B-1.
shopt -s nullglob
out_files=()
error_files=()
if [ -n "$TMPDIR_BOOT" ]; then
  out_files=("$TMPDIR_BOOT"/*.out)
  error_files=("$TMPDIR_BOOT"/*.err)
fi
if [ ${#out_files[@]} -gt 0 ]; then
  cat "${out_files[@]}"
fi
if [ ${#error_files[@]} -gt 0 ]; then
  cat "${error_files[@]}" >&2
fi
if [ "$BOOT" = "1" ]; then
  boot_facts
  boot_derived
fi
exit 0
