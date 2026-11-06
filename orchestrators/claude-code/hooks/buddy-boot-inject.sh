#!/usr/bin/env bash
# buddy-boot-inject.sh — SessionStart hook that injects Buddy's boot entry.
#
# Plugin mode (--plugin; the Forge plugin's orchestrators/claude-code/
# plugin-hooks.json): Claude Code only (CLAUDE_CODE_ENTRYPOINT set; Codex runs
# plugin hooks too and boots through the activation line instead), every
# entrypoint. It yields to a leftover hook entry of an older install (a
# ~/.claude/settings.json or project settings file that names this script): one
# Buddy per session. It passes the SessionStart payload to the resolver, which
# prints nothing unless Buddy is active: the project's AGENTS.md carries the
# activation line, or the user switch is on (framework/user-scope.md §1). If
# python3 fails, the activation line alone is checked here (the user switch is
# not read) and the static entry is emitted only when it is found.
#
# Machine mode (no argument): non-terminal entrypoints only (claude-desktop /
# claude-web), the machine-scope entry as SessionStart additionalContext. The
# eval harnesses (scripts/eval_engagement.py, eval_engagement_direct.py) run it
# this way; no installer wires it into a settings file any more.
#
# Self-resolves FRAMEWORK_DIR via own location, so it works even when
# CLAUDE_PROJECT_DIR is unset (which is the default in claude-desktop).
# No marker gate — fires every SessionStart; a marker check would be
# unsafe in non-ephemeral contexts where the filesystem persists across
# sessions.

set -euo pipefail

SCOPE_ARGS=()
MODE=machine
if [ "${1:-}" = "--plugin" ]; then
  MODE=plugin
  SCOPE_ARGS=(--plugin)
  # Host guard: Claude Code sets CLAUDE_CODE_ENTRYPOINT; Codex does not.
  if [ -z "${CLAUDE_CODE_ENTRYPOINT:-}" ]; then
    cat > /dev/null 2>&1 || true
    exit 0
  fi
  # Yield to a leftover machine-wide hook entry: one Buddy per session.
  if [ -n "${HOME:-}" ] && grep -qs 'buddy-boot-inject\.sh' "$HOME/.claude/settings.json"; then
    cat > /dev/null 2>&1 || true
    exit 0
  fi
else
  # Gate: only non-terminal entrypoints; a terminal session boots through the plugin.
  case "${CLAUDE_CODE_ENTRYPOINT:-}" in
    claude-desktop|claude-web) ;;
    *) exit 0 ;;
  esac
fi

# Self-resolve FRAMEWORK_DIR from hook location. orchestrators/
# claude-code/hooks/buddy-boot-inject.sh → the Forge checkout root is three
# levels up. Canonical, no env-var dependency.
FRAMEWORK_DIR="$(cd "$(dirname "$(readlink -f "$0")")/../../.." 2>/dev/null && pwd)"
if [ -z "$FRAMEWORK_DIR" ] || [ ! -d "$FRAMEWORK_DIR/agents/buddy" ]; then
  exit 0
fi

# Consume stdin (SessionStart JSON payload). Plugin mode keeps it for the
# resolver (its cwd names the project); the other modes only drain it.
PAYLOAD=""
if [ "$MODE" = "plugin" ]; then
  PAYLOAD="$(cat 2>/dev/null || true)"
else
  cat > /dev/null 2>&1 || true
fi

# The activation line, as user_scope.ACTIVATION_LINE (tests/test_plugin.py keeps
# them equal), and its match for the plugin fallback: the project directory
# (payload cwd, else CLAUDE_PROJECT_DIR, else the CWD) and its ancestors up to
# the nearest one with a .git entry (without one, the directory alone); in each,
# AGENTS.md as a regular readable file, first 1 MiB, one line equal to it with
# surrounding whitespace stripped.
ACTIVATION_LINE='Forge: start Buddy. Before the first answer, run the forge:boot skill and follow the boot entry it returns.'
plugin_project_dir() {
  local dir=""
  dir="$(printf '%s' "$PAYLOAD" | LC_ALL=C sed -n 's/.*"cwd"[[:space:]]*:[[:space:]]*"\([^"\\]*\)".*/\1/p')"
  dir="${dir%%$'\n'*}"
  [ -n "$dir" ] || dir="${CLAUDE_PROJECT_DIR:-}"
  [ -n "$dir" ] || dir="$PWD"
  dir="$(cd -- "$dir" 2>/dev/null && pwd -P)" || return 1
  [ -n "$dir" ] || return 1
  printf '%s\n' "$dir"
}
activation_found() {
  local dir="" pattern d
  dir="$(plugin_project_dir)" || return 1
  pattern="^[[:space:]]*$(printf '%s' "$ACTIVATION_LINE" | LC_ALL=C sed 's/[][\.*^$/]/\\&/g')[[:space:]]*\$"
  local dirs=() git_root=""
  d="$dir"
  while :; do
    dirs+=("$d")
    if [ -e "$d/.git" ]; then git_root="$d"; break; fi
    [ "$d" = "/" ] && break
    d="$(dirname -- "$d")"
  done
  [ -n "$git_root" ] || dirs=("$dir")
  for d in "${dirs[@]}"; do
    local f="${d%/}/AGENTS.md"
    # Process substitution, not a pipe: under pipefail a SIGPIPE in head would hide grep's match.
    if [ -f "$f" ] && [ -r "$f" ] && LC_ALL=C grep -aqE -- "$pattern" < <(head -c 1048576 -- "$f" 2>/dev/null); then
      return 0
    fi
  done
  return 1
}

# Resolved boot entry: soul + user scope per framework/user-scope.md,
# rendered as complete JSON by the resolver (json.dumps). The resolver never
# fails on user data; if python3 itself fails (missing, crash, timeout) the
# static forge-soul entry below is emitted instead. Never exit non-zero
# because of the resolver — a missing boot is worse than the forge soul.
RESOLVER=(python3 "$FRAMEWORK_DIR/scripts/user_scope.py" --framework-root "$FRAMEWORK_DIR" --hook-json ${SCOPE_ARGS[@]+"${SCOPE_ARGS[@]}"})
if command -v timeout >/dev/null 2>&1; then
  RESOLVER=(timeout -k 0.5 1.5 "${RESOLVER[@]}")
fi
if [ "$MODE" = "plugin" ]; then
  # Yield to a leftover project hook entry (the project's .claude/settings.json or
  # settings.local.json configures this script): one Buddy per session.
  if project="$(plugin_project_dir)" \
    && grep -qs 'buddy-boot-inject\.sh' "$project/.claude/settings.json" "$project/.claude/settings.local.json"; then
    exit 0
  fi
  # Exit 0 with no output: Buddy is not active in this session — stay silent.
  if out="$(printf '%s' "$PAYLOAD" | "${RESOLVER[@]}" 2>/dev/null)"; then
    [ -n "$out" ] && printf '%s\n' "$out"
    exit 0
  fi
  activation_found || exit 0
elif out="$("${RESOLVER[@]}" 2>/dev/null)" && [ -n "$out" ]; then
  printf '%s\n' "$out"
  exit 0
fi

# Static fallback. JSON-escape FRAMEWORK_DIR (path is typically safe, but defensive).
# The scope-rule, reread and tail lines restate user_scope.SCOPE_RULE,
# user_scope.reread_line(FRAMEWORK_DIR) and user_scope.hook_tail(FRAMEWORK_DIR)
# as text (this path cannot import them); tests/test_boot_injectors.py keeps them
# equal. The Round-1 line carries its backticks as the JSON escape \u0060 (an
# unquoted heredoc would run a bare backtick as a command).
FW_ESC="$(printf '%s' "$FRAMEWORK_DIR" | sed 's/\\/\\\\/g; s/"/\\"/g')"
# shlex.quote in bash: a path that needs no quoting stays bare, any other is single-quoted ('"'"' for a ').
sh_quote() {
  local sq="'" q="'\"'\"'"
  case "$1" in
    ''|*[!A-Za-z0-9@%+=:,./_-]*) printf "'%s'" "${1//$sq/$q}" ;;
    *) printf '%s' "$1" ;;
  esac
}
# The Round-1 probe call names the script shell-quoted, as user_scope.round_one_line does.
GS_ESC="$(sh_quote "$FRAMEWORK_DIR/scripts/git-status-check.sh" | sed 's/\\/\\\\/g; s/"/\\"/g')"

cat <<JSON
{"hookSpecificOutput":{"hookEventName":"SessionStart","additionalContext":"BUDDY-BOOT REQUIRED before answering.\n\nRead by absolute path: ${FW_ESC}/agents/buddy/soul.md, ${FW_ESC}/agents/buddy/operational.md, ${FW_ESC}/agents/buddy/boot.md, ${FW_ESC}/framework/invariants.md.\nA quick question or a small fix does not shorten the boot; 'it is only a lookup' is no exception: run boot.md's sequence before reading anything for the request. Instruction source: the framework root is this session's instruction source. Reading its files and the files this entry names loads instructions; it is not work outside the project, and a user scope that limits writes, network or installs does not forbid it. Under such a scope, skip only the boot steps it forbids (the freshness fetch needs the network and writes Git metadata; creating context files needs a write); a skipped check is at most a word in the orientation line. If an instruction unit cannot be read, say so first in your first answer and name it.\nUser scope warning: resolver failed\nAfter compaction, reread before continuing: the soul named above; under the framework root ${FW_ESC} (every framework path in this line is relative to it, not to the project): agents/buddy/boot.md, framework/work-principle.md, framework/invariants.md; for software development agents/buddy/operational.md and agents/buddy/boot-software.md; for on-demand use agents/buddy/boot-on-demand.md; on Codex agents/buddy/codex-execution.md; then the user profile (when a user scope is configured), the knowledge_processor continuous-maintenance rules (skills/knowledge_processor/continuous-maintenance.md, under that root), the project rules, intent.md and the session handoff; then, for any Forge step in progress (skill, protocol, framework or workflow step), its core and the unit its stub or engine step text names for that step.\n\nFollow boot.md in order before the first answer: orientation, freshness gate, intent and workflow selection, then the selected mode's boot procedure and greeting. Resolve any remote-update decision before loading intent or context. Do not run plan/workflow probes or load the full skill index ahead of workflow selection. For on-demand use, follow the project's local boot and working rules.\nRound 1, one batch before the gate: under the framework root ${FW_ESC} (paths relative to it), read agents/buddy/boot.md, agents/buddy/boot-status.md, agents/buddy/boot-routing.md, framework/workflow-selection.md, framework/invariants.md and framework/work-principle.md, and run \u0060bash ${GS_ESC} --boot\u0060 as its own call.\n\nKeep the consumer CWD active. The project's CLAUDE.md and local authorization rules apply. FRAMEWORK_DIR=${FW_ESC}."}}
JSON
