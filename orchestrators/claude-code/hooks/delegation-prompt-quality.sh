#!/usr/bin/env bash
# delegation-prompt-quality.sh — PreToolUse Hook [Task-011 Phase 3b H1]
#
# Re-interpretation (DEC-K) of CLAUDE.md §3 Pre-Delegation as a *warn-only*
# heuristic on tool_input.prompt. Full plan-block verification is not
# feasible from PreToolUse context (no transcript access) — H1 covers the
# common fail-mode "prompt='do the thing'" without false-blocking
# well-formed short prompts.
#
# Canonical Spec: docs/specs/011-harness-refactor.md §Phase 3b H1
#
# Checks:
#   A — prompt length >= 200 (structural quality proxy)
#   B — keyword present (Scope/Ziel/Kontext/...)
#   C — MCA-Brief implicit_decisions_surfaced section + 4 standard
#       Decision-Klassen (when subagent=main-code-agent + length >= 600)
#
# Matcher: Task
#
# Core Logic:
#   1. Parse tool_input.prompt (string), tool_input.subagent_type (optional).
#   2. Filter: skip when subagent_type in {Explore, general-purpose,
#      claude-code-guide} — open-ended research agents.
#   3. PASS if prompt.length >= 200 characters.
#   4. PASS if prompt contains any of: Scope:, Ziel:, Kontext:, Aufgabe:,
#      Goal:, Task:, Context:, Intent:, Output: (case-insensitive).
#   5. WARN otherwise.
#
# Dual-mode invocation:
#   1. CC PreToolUse hook: JSON payload on stdin with tool_name and tool_input.
#   2. Standalone test:    env var CLAUDE_TOOL_INPUT_JSON (tool_name assumed Task).
#
# Exit codes:
#   0 — PASS (filtered OR length OK OR keyword present OR graceful skip)
#   1 — WARN (short + unstructured prompt, tool call proceeds)
#
# CC-hook output: warn is emitted via stderr (visible to user, no block).

set -uo pipefail

# ---------- Input resolution ----------

TOOL_NAME=""
TOOL_INPUT_JSON=""
STDIN_MODE=0

if [ ! -t 0 ]; then
  STDIN_CONTENT=$(cat 2>/dev/null || true)
  if [ -n "$STDIN_CONTENT" ] && command -v jq &>/dev/null; then
    PARSED_TOOL=$(echo "$STDIN_CONTENT" | jq -r '.tool_name // empty' 2>/dev/null || true)
    if [ -n "$PARSED_TOOL" ]; then
      TOOL_NAME="$PARSED_TOOL"
      TOOL_INPUT_JSON=$(echo "$STDIN_CONTENT" | jq -c '.tool_input // {}' 2>/dev/null || echo "{}")
      STDIN_MODE=1
    fi
  fi
fi

# Fallback: env-var (standalone test)
if [ -z "$TOOL_NAME" ] && [ -n "${CLAUDE_TOOL_INPUT_JSON:-}" ]; then
  TOOL_NAME="${CLAUDE_TOOL_NAME:-Task}"
  TOOL_INPUT_JSON="$CLAUDE_TOOL_INPUT_JSON"
fi

# Nothing to check → graceful pass
if [ -z "$TOOL_NAME" ] || [ -z "$TOOL_INPUT_JSON" ]; then
  exit 0
fi

# Only handle Task tool (matcher is Task but defensively re-check)
if [ "$TOOL_NAME" != "Task" ]; then
  exit 0
fi

# jq missing → cannot parse, graceful pass
if ! command -v jq &>/dev/null; then
  exit 0
fi

# ---------- Extract fields ----------

PROMPT=$(echo "$TOOL_INPUT_JSON" | jq -r '.prompt // empty' 2>/dev/null || true)
SUBAGENT=$(echo "$TOOL_INPUT_JSON" | jq -r '.subagent_type // empty' 2>/dev/null || true)

# Prompt missing → graceful pass (spec: edge case exit 0)
if [ -z "$PROMPT" ]; then
  exit 0
fi

# ---------- Filter: open-ended research agents ----------

case "$SUBAGENT" in
  Explore|general-purpose|claude-code-guide)
    exit 0
    ;;
esac

# ---------- Check A: length >= 200 (structural quality proxy) ----------

PROMPT_LEN=${#PROMPT}
STRUCT_PASS=0
if [ "$PROMPT_LEN" -ge 200 ]; then
  STRUCT_PASS=1
fi

# ---------- Check B: keyword present (case-insensitive) ----------

KEYWORDS='Scope:|Ziel:|Kontext:|Aufgabe:|Goal:|Task:|Context:|Intent:|Output:'
if echo "$PROMPT" | grep -qiE "$KEYWORDS"; then
  STRUCT_PASS=1
fi

# ---------- Check C: MCA-Brief Implicit-Decisions section ----------
#
# Per skills/_protocols/mca-brief-template.md: when subagent_type is
# main-code-agent AND the prompt is substantial (>=600 chars heuristic),
# expect `implicit_decisions_surfaced:` with the 4 standard classes:
# schema_and_contract, error_and_stop, layer_discipline, structural_invariants.
#
# WARN-only — the real trigger (>=3 ACs / schema change / cross-module / sub-
# build) is not visible from the prompt; length is a proxy.

MCA_BRIEF_WARN=""
if [ "$SUBAGENT" = "main-code-agent" ] && [ "$PROMPT_LEN" -ge 600 ]; then
  STANDARD_KLASSEN=(schema_and_contract error_and_stop layer_discipline structural_invariants)

  if ! echo "$PROMPT" | grep -qE '^[[:space:]]*implicit_decisions_surfaced:'; then
    MCA_BRIEF_WARN="MCA-Brief missing 'implicit_decisions_surfaced:' section. Per skills/_protocols/mca-brief-template.md, substantial dispatches MUST enumerate 4 Decision-Klassen + locked/value. Below threshold (≤2 ACs, single-file, no schema): add a 1-line '<!-- Below threshold -->' acknowledgement."
  else
    MISSING=()
    for klasse in "${STANDARD_KLASSEN[@]}"; do
      if ! echo "$PROMPT" | grep -qE "^[[:space:]]+${klasse}:"; then
        MISSING+=("$klasse")
      fi
    done
    if [ ${#MISSING[@]} -gt 0 ]; then
      MCA_BRIEF_WARN="MCA-Brief implicit_decisions_surfaced section incomplete. Missing Klassen: ${MISSING[*]}. Per skills/_protocols/mca-brief-template.md each Klasse needs locked + value field."
    fi
  fi
fi

# ---------- WARN aggregation ----------

if [ "$STRUCT_PASS" -eq 1 ] && [ -z "$MCA_BRIEF_WARN" ]; then
  exit 0
fi

MSGS=()
if [ "$STRUCT_PASS" -eq 0 ]; then
  MSGS+=("delegation-prompt-quality: WARN — prompt ${PROMPT_LEN} chars, no Plan-Block keyword. Consider adding 'Ziel:/Scope:/Kontext:' or expanding.")
fi
if [ -n "$MCA_BRIEF_WARN" ]; then
  MSGS+=("delegation-prompt-quality: WARN — $MCA_BRIEF_WARN")
fi

for msg in "${MSGS[@]}"; do
  if [ "$STDIN_MODE" -eq 1 ]; then
    echo "$msg" >&2
  else
    echo "$msg" >&2
  fi
done

if [ "$STDIN_MODE" -eq 1 ]; then
  exit 0
else
  exit 1
fi
