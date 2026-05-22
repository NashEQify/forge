#!/usr/bin/env bash
# smoke-shim.sh — verifies the CC-shaped JSON-on-stdin contract that the
# OpenCode forge-hooks plugin depends on. Runs each PreToolUse / PostToolUse
# bash hook with a sample CC payload, asserts the expected outcome (exit
# code, BLOCK envelope, stderr keyword).
#
# This is NOT a full integration test — there's no headless OpenCode harness
# for the plugin event loop. What this DOES verify is the SoT contract: the
# bash hooks accept the JSON shape the plugin emits, and emit the BLOCK
# signals the plugin interprets. If this passes, the plugin's translator
# layer is the only remaining failure surface.
#
# Usage: bash orchestrators/opencode/tests/smoke-shim.sh
# Exit:  0 = all assertions passed, 1 = one or more failed.

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "$(readlink -f "$0")")" && pwd)"
FRAMEWORK_DIR="$(cd "$SCRIPT_DIR/../../.." && pwd)"
export CLAUDE_PROJECT_DIR="$FRAMEWORK_DIR"
HOOKS_DIR="$FRAMEWORK_DIR/orchestrators/claude-code/hooks"

PASS=0
FAIL=0

ok() { echo "  ✓ $1"; PASS=$((PASS + 1)); }
ko() { echo "  ✗ $1" >&2; FAIL=$((FAIL + 1)); }

# Run a hook with a JSON payload on stdin. Captures stdout, stderr, exit code
# into the named output variables. Times out at 5s to match the plugin.
#
# Args: <hook-name> <payload-json> <out-var> <err-var> <code-var>
run_hook() {
  # Locals use a `_` prefix so they don't shadow the caller's var names
  # (we accept caller names like `out`, `err`, `code` as args).
  local _hook="$1" _payload="$2" _outvar="$3" _errvar="$4" _codevar="$5"
  local _script="$HOOKS_DIR/$_hook"
  local _stdout_file _stderr_file
  _stdout_file=$(mktemp)
  _stderr_file=$(mktemp)

  local _exit=0
  echo "$_payload" | timeout 5 bash "$_script" >"$_stdout_file" 2>"$_stderr_file" || _exit=$?

  printf -v "$_outvar" '%s' "$(cat "$_stdout_file")"
  printf -v "$_errvar" '%s' "$(cat "$_stderr_file")"
  printf -v "$_codevar" '%s' "$_exit"
  rm -f "$_stdout_file" "$_stderr_file"
}

# ── path-whitelist-guard ──────────────────────────────────────────────────

echo "path-whitelist-guard"

# (1) Whitelisted Edit → PASS (exit 0, no deny envelope).
WL_OK_PAYLOAD=$(cat <<JSON
{"hook_event_name":"PreToolUse","tool_name":"Edit","tool_input":{"file_path":"$FRAMEWORK_DIR/docs/test.md"}}
JSON
)
run_hook path-whitelist-guard.sh "$WL_OK_PAYLOAD" out err code
if [ "$code" = "0" ] && ! echo "$out" | grep -q '"permissionDecision": *"deny"'; then
  ok "whitelisted Edit → exit 0, no deny envelope"
else
  ko "whitelisted Edit expected exit 0 + no deny; got exit=$code, stdout=${out:0:120}"
fi

# (2) Non-whitelisted Edit → BLOCK (stdin mode: exit 0 + deny envelope).
WL_BAD_PAYLOAD=$(cat <<'JSON'
{"hook_event_name":"PreToolUse","tool_name":"Edit","tool_input":{"file_path":"/etc/passwd"}}
JSON
)
run_hook path-whitelist-guard.sh "$WL_BAD_PAYLOAD" out err code
if [ "$code" = "0" ] && echo "$out" | grep -q '"permissionDecision": *"deny"'; then
  ok "non-whitelisted Edit → deny envelope"
else
  ko "non-whitelisted Edit expected deny envelope; got exit=$code, stdout=${out:0:120}"
fi

# (3) Unknown tool → PASS (exit 0, silent).
UNK_PAYLOAD='{"hook_event_name":"PreToolUse","tool_name":"Read","tool_input":{"file_path":"/etc/passwd"}}'
run_hook path-whitelist-guard.sh "$UNK_PAYLOAD" out err code
if [ "$code" = "0" ] && [ -z "$out" ]; then
  ok "unknown tool → exit 0, silent"
else
  ko "unknown tool expected exit 0 + silent; got exit=$code, stdout=${out:0:120}"
fi

# ── frozen-zone-guard ─────────────────────────────────────────────────────

echo "frozen-zone-guard"

# Frozen path → BLOCK. Use an existing history file so we hit the BLOCK
# path; frozen-zone-guard has a Create-exception for non-existing dated
# files (knowledge-processor + save-workflow need to create new entries).
FZ_EXISTING=$(ls "$FRAMEWORK_DIR/context/history/"*.md 2>/dev/null | head -1)
FZ_BAD_PAYLOAD=$(cat <<JSON
{"hook_event_name":"PreToolUse","tool_name":"Edit","tool_input":{"file_path":"$FZ_EXISTING"}}
JSON
)
run_hook frozen-zone-guard.sh "$FZ_BAD_PAYLOAD" out err code
# frozen-zone-guard returns exit 2 OR exit 0 + deny envelope on BLOCK.
# Both paths honored; the hook also accepts relative-from-project-dir
# matching so the relative patterns in frozen-zones.txt match the
# absolute file_path that CC sends.
if { [ "$code" = "2" ] || echo "$out" | grep -q '"permissionDecision": *"deny"'; }; then
  ok "frozen Edit → BLOCK (exit=$code)"
else
  ko "frozen Edit expected BLOCK; got exit=$code, stdout=${out:0:120}, stderr=${err:0:120}"
fi

# Non-frozen path → PASS.
FZ_OK_PAYLOAD=$(cat <<JSON
{"hook_event_name":"PreToolUse","tool_name":"Edit","tool_input":{"file_path":"$FRAMEWORK_DIR/docs/test.md"}}
JSON
)
run_hook frozen-zone-guard.sh "$FZ_OK_PAYLOAD" out err code
if [ "$code" = "0" ] && ! echo "$out" | grep -q '"permissionDecision": *"deny"'; then
  ok "non-frozen Edit → exit 0"
else
  ko "non-frozen Edit expected exit 0; got exit=$code"
fi

# ── state-write-block ─────────────────────────────────────────────────────

echo "state-write-block"

# Workflow state file → BLOCK.
ST_BAD_PAYLOAD=$(cat <<JSON
{"hook_event_name":"PreToolUse","tool_name":"Write","tool_input":{"file_path":"$FRAMEWORK_DIR/.workflow-state/build-298.json"}}
JSON
)
run_hook state-write-block.sh "$ST_BAD_PAYLOAD" out err code
if { [ "$code" = "2" ] || echo "$out" | grep -q '"permissionDecision": *"deny"'; }; then
  ok "workflow-state Write → BLOCK (exit=$code)"
else
  ko "workflow-state Write expected BLOCK; got exit=$code, stdout=${out:0:120}"
fi

# ── engine-bypass-block (informational — may not BLOCK without runbook ctx) ─

echo "engine-bypass-block"
EB_PAYLOAD=$(cat <<JSON
{"hook_event_name":"PreToolUse","tool_name":"Edit","tool_input":{"file_path":"$FRAMEWORK_DIR/docs/test.md"}}
JSON
)
run_hook engine-bypass-block.sh "$EB_PAYLOAD" out err code
if [ "$code" = "0" ] || [ "$code" = "2" ]; then
  ok "engine-bypass-block accepts CC JSON shape (exit=$code)"
else
  ko "engine-bypass-block crashed on CC JSON shape; got exit=$code, stderr=${err:0:120}"
fi

# ── workflow-commit-gate (Bash matcher) ───────────────────────────────────

echo "workflow-commit-gate"
WCG_PAYLOAD='{"hook_event_name":"PreToolUse","tool_name":"Bash","tool_input":{"command":"git status"}}'
run_hook workflow-commit-gate.sh "$WCG_PAYLOAD" out err code
if [ "$code" = "0" ] || [ "$code" = "2" ]; then
  ok "workflow-commit-gate accepts CC JSON shape (exit=$code)"
else
  ko "workflow-commit-gate crashed on CC JSON shape; got exit=$code, stderr=${err:0:120}"
fi

# ── delegation-prompt-quality (Task matcher) ──────────────────────────────

echo "delegation-prompt-quality"
DPQ_PAYLOAD='{"hook_event_name":"PreToolUse","tool_name":"Task","tool_input":{"subagent_type":"main-code-agent","prompt":"build a small fix"}}'
run_hook delegation-prompt-quality.sh "$DPQ_PAYLOAD" out err code
if [ "$code" = "0" ] || [ "$code" = "1" ]; then
  ok "delegation-prompt-quality accepts CC JSON shape (exit=$code, warn=$code)"
else
  ko "delegation-prompt-quality crashed; got exit=$code, stderr=${err:0:120}"
fi

# ── plan-adversary-reminder ───────────────────────────────────────────────

echo "plan-adversary-reminder"
PAR_PAYLOAD=$(cat <<JSON
{"hook_event_name":"PreToolUse","tool_name":"Write","tool_input":{"file_path":"$FRAMEWORK_DIR/docs/test.md","content":"hello"}}
JSON
)
run_hook plan-adversary-reminder.sh "$PAR_PAYLOAD" out err code
if [ "$code" = "0" ] || [ "$code" = "1" ]; then
  ok "plan-adversary-reminder accepts CC JSON shape (exit=$code)"
else
  ko "plan-adversary-reminder crashed; got exit=$code, stderr=${err:0:120}"
fi

# ── PostToolUse hooks ─────────────────────────────────────────────────────

echo "mca-return-stop-condition"
MCA_PAYLOAD='{"hook_event_name":"PostToolUse","tool_name":"Task","tool_input":{"subagent_type":"main-code-agent"},"tool_response":{"result":"AUTO-FIXED 3 issues"}}'
run_hook mca-return-stop-condition.sh "$MCA_PAYLOAD" out err code
if [ "$code" = "0" ]; then
  ok "mca-return-stop-condition accepts CC JSON shape (exit=$code)"
else
  ko "mca-return-stop-condition crashed; got exit=$code, stderr=${err:0:120}"
fi

echo "board-output-check"
BOC_PAYLOAD='{"hook_event_name":"PostToolUse","tool_name":"Task","tool_input":{"subagent_type":"code-review","prompt":"review"},"tool_response":{}}'
run_hook board-output-check.sh "$BOC_PAYLOAD" out err code
if [ "$code" = "0" ]; then
  ok "board-output-check accepts CC JSON shape (exit=$code)"
else
  ko "board-output-check crashed; got exit=$code, stderr=${err:0:120}"
fi

echo "evidence-pointer-check"
EPC_PAYLOAD='{"hook_event_name":"PostToolUse","tool_name":"Task","tool_input":{"subagent_type":"code-review"},"tool_response":{"result":"done"}}'
run_hook evidence-pointer-check.sh "$EPC_PAYLOAD" out err code
if [ "$code" = "0" ]; then
  ok "evidence-pointer-check accepts CC JSON shape (exit=$code)"
else
  ko "evidence-pointer-check crashed; got exit=$code, stderr=${err:0:120}"
fi

# ── Summary ───────────────────────────────────────────────────────────────

echo ""
echo "passed: $PASS"
echo "failed: $FAIL"

[ "$FAIL" = "0" ] && exit 0 || exit 1
