#!/usr/bin/env bash
# test-delegation-prompt-quality.sh — Tests for H1 (Task-011 Phase 3b)
#
# Test cases from docs/specs/011-harness-refactor.md §H1 Minimal-Tests:
#   1. Positive long: 500-char prose → exit 0
#   2. Positive keyword: short prompt with "Ziel:/Scope:" → exit 0
#   3. Positive filter: subagent_type=general-purpose + short prompt → exit 0
#   4. Negative: subagent_type=main-code-agent + "do the thing" → exit 1
#   5. Edge: prompt missing → exit 0 (graceful)
#
# Usage: bash tests/hooks/test-delegation-prompt-quality.sh
# Exit 0 if all pass, exit 1 on any failure.

set -uo pipefail

FRAMEWORK_ROOT="$(cd "$(dirname "$(readlink -f "$0")")/../../.." && pwd)"
HOOK="$FRAMEWORK_ROOT/orchestrators/claude-code/hooks/delegation-prompt-quality.sh"

if [ ! -x "$HOOK" ]; then
  echo "FAIL: hook not executable at $HOOK"
  exit 1
fi

PASS=0
FAIL=0
FAILED_TESTS=()

run_case() {
  local name="$1"
  local expected_exit="$2"
  local json_input="$3"

  local actual_exit
  echo "$json_input" | bash "$HOOK" >/dev/null 2>&1
  actual_exit=$?

  if [ "$actual_exit" -eq "$expected_exit" ]; then
    echo "  PASS: $name (exit=$actual_exit)"
    PASS=$((PASS + 1))
  else
    echo "  FAIL: $name (expected exit=$expected_exit, got=$actual_exit)"
    FAIL=$((FAIL + 1))
    FAILED_TESTS+=("$name")
  fi
}

# Build a 500-char prose prompt
LONG_PROMPT=$(printf 'abcdefghij%.0s' {1..50})  # 500 chars

# Case 1: Positive long (>=200 chars)
run_case "1-positive-long" 0 \
  "$(jq -nc --arg p "$LONG_PROMPT" '{tool_name:"Task", tool_input:{prompt:$p, subagent_type:"main-code-agent"}}')"

# Case 2: Positive keyword (short but has Ziel:)
run_case "2-positive-keyword" 0 \
  '{"tool_name":"Task","tool_input":{"prompt":"Ziel: X. Scope: Y.","subagent_type":"main-code-agent"}}'

# Case 3: Positive filter (short, no keyword, but subagent_type filtered)
run_case "3-positive-filter-gp" 0 \
  '{"tool_name":"Task","tool_input":{"prompt":"quick","subagent_type":"general-purpose"}}'

run_case "3b-positive-filter-explore" 0 \
  '{"tool_name":"Task","tool_input":{"prompt":"look","subagent_type":"Explore"}}'

run_case "3c-positive-filter-guide" 0 \
  '{"tool_name":"Task","tool_input":{"prompt":"help","subagent_type":"claude-code-guide"}}'

# Case 4: Negative (short, no keyword, non-filtered subagent)
# In STDIN mode the hook exits 0 (CC surface via stderr, no block).
# Test the intent via env-var (standalone) mode which uses exit 1.
ACTUAL=$(CLAUDE_TOOL_NAME=Task \
  CLAUDE_TOOL_INPUT_JSON='{"prompt":"do the thing","subagent_type":"main-code-agent"}' \
  bash "$HOOK" 2>/dev/null; echo $?)
ACTUAL_EXIT="${ACTUAL##*$'\n'}"
if [ "$ACTUAL_EXIT" = "1" ]; then
  echo "  PASS: 4-negative-short-no-keyword (standalone exit=1)"
  PASS=$((PASS + 1))
else
  echo "  FAIL: 4-negative-short-no-keyword (expected standalone exit=1, got=$ACTUAL_EXIT)"
  FAIL=$((FAIL + 1))
  FAILED_TESTS+=("4-negative-short-no-keyword")
fi

# Case 5: Edge — prompt missing (graceful pass)
run_case "5-edge-no-prompt" 0 \
  '{"tool_name":"Task","tool_input":{"subagent_type":"main-code-agent"}}'

# Case 6: Edge — empty stdin (graceful pass)
actual_exit=0
echo "" | bash "$HOOK" >/dev/null 2>&1 || actual_exit=$?
if [ "$actual_exit" -eq 0 ]; then
  echo "  PASS: 6-edge-empty-stdin"
  PASS=$((PASS + 1))
else
  echo "  FAIL: 6-edge-empty-stdin (exit=$actual_exit)"
  FAIL=$((FAIL + 1))
  FAILED_TESTS+=("6-edge-empty-stdin")
fi

# Case 7: Edge — non-Task tool (should skip)
run_case "7-edge-wrong-tool" 0 \
  '{"tool_name":"Bash","tool_input":{"prompt":"x"}}'

echo ""
echo "test-delegation-prompt-quality: $PASS pass, $FAIL fail"
if [ "$FAIL" -gt 0 ]; then
  echo "Failed: ${FAILED_TESTS[*]}"
  exit 1
fi
exit 0
