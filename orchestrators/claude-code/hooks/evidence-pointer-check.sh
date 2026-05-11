#!/usr/bin/env bash
# evidence-pointer-check.sh — PostToolUse(Task) hook (Spec 299 Phase E).
#
# Mechanical Schicht-3 Adapter-Bonus: post Sub-Agent-Task validate
# evidence-pointers im Output-File. Filter: nur Tier-1-Skill-Sub-Agent-
# Outputs (skill_ref oder subagent_type).
#
# Pattern reuse: board-output-check.sh fuer stdin/jq/Pfad-Inferenz.
#
# Severity: WARN-only (initial). Spec §4.1 — Promotion zu BLOCK nach
# 4 Wochen Bewaehrung mit <5% False-Positive-Rate, eigene Spec-Amendment.
#
# Constraints:
# - Hook ist Post-Trigger only (Spec §8.2): tool_response wird nur nach
#   tool-execution sichtbar; capture-vor-execution-Hooks sind verboten.
# - Kein LLM-Aufruf (Spec §8.2): keine externen API-Calls. Mechanical-only.
#
# Exit codes:
#   0 — always (graceful, never blocks)

set -uo pipefail

# ---------- Tier-1-Skills ----------

# Spec 299 §3.1 + Phase D — Tier-1-Skills mit verification_tier: 1.
# Both kebab-case (subagent_type) and snake_case (skill-dir) variants.
TIER1_SKILLS=(
  "spec-board" "spec_board"
  "code-review-board" "code_review_board"
  "arch-coherence-review" "architecture_coherence_review"
  "sectional-deep" "sectional_deep_review"
  "adversary-test-plan" "adversary_test_plan"
  "spec-amendment-verify" "spec_amendment_verification"
)

is_tier1() {
  local needle="$1"
  for skill in "${TIER1_SKILLS[@]}"; do
    if [[ "$needle" == *"$skill"* ]]; then
      return 0
    fi
  done
  return 1
}

# CC-012 (F-CA-008) fix: strict-match auf subagent_type ONLY (no substring
# match in prompt-text, das hatte false-positives wenn der Prompt z.B.
# `do NOT use code-review-board` enthielt). Used for tier1-Filter unten.
is_tier1_strict() {
  local subagent="$1"
  for skill in "${TIER1_SKILLS[@]}"; do
    if [[ "$subagent" == "$skill" ]]; then
      return 0
    fi
  done
  return 1
}

# ---------- Input resolution ----------

TOOL_INPUT_JSON=""
TOOL_RESPONSE_JSON=""

if [ ! -t 0 ]; then
  STDIN_CONTENT=$(cat 2>/dev/null || true)
  if [ -n "$STDIN_CONTENT" ] && command -v jq &>/dev/null; then
    PARSED_TOOL=$(echo "$STDIN_CONTENT" | jq -r '.tool_name // empty' 2>/dev/null || true)
    if [ "$PARSED_TOOL" = "Task" ]; then
      TOOL_INPUT_JSON=$(echo "$STDIN_CONTENT" | jq -c '.tool_input // {}' 2>/dev/null || echo "{}")
      TOOL_RESPONSE_JSON=$(echo "$STDIN_CONTENT" | jq -c '.tool_response // {}' 2>/dev/null || echo "{}")
    fi
  fi
fi

if [ -z "$TOOL_INPUT_JSON" ] && [ -n "${CLAUDE_TOOL_INPUT_JSON:-}" ]; then
  TOOL_INPUT_JSON="$CLAUDE_TOOL_INPUT_JSON"
fi

if [ -z "$TOOL_INPUT_JSON" ]; then
  exit 0
fi

if ! command -v jq &>/dev/null; then
  exit 0
fi

# ---------- Tier-1 filter ----------

PROMPT=$(echo "$TOOL_INPUT_JSON" | jq -r '.prompt // empty' 2>/dev/null || true)
SUBAGENT=$(echo "$TOOL_INPUT_JSON" | jq -r '.subagent_type // empty' 2>/dev/null || true)

# CC-012 fix: filter strikt auf subagent_type — substring-Match im Prompt
# erzeugte false-positives ("do NOT use code-review-board" -> Hook triggert).
# Fallback auf is_tier1 (substring) bleibt nur wenn subagent_type leer ist
# und PROMPT erkennbar einen Tier-1 ref enthaelt; sonst skip.
if [ -n "$SUBAGENT" ]; then
  if ! is_tier1_strict "$SUBAGENT"; then
    exit 0
  fi
elif ! is_tier1 "$PROMPT"; then
  # No subagent_type in payload AND no Tier-1 mention in prompt → skip
  exit 0
fi

# ---------- Extract output file ----------

OUTPUT_FILE=""

# 1. Try tool_response.output_file (preferred — hook-injected by Tier-1
#    skills via output_file=<absolute-path> convention).
if [ -n "$TOOL_RESPONSE_JSON" ]; then
  OUTPUT_FILE=$(echo "$TOOL_RESPONSE_JSON" | jq -r '.output_file // empty' 2>/dev/null || true)
fi

# 2. Fallback: parse prompt for `output_file=` marker (explicit form).
#    CC-012 Pass-1-Fix: backtick-fallback ENTFERNT — `head -1` picked
#    den ersten backtick-`.md`-Path im Prompt, der oft ein Cross-Ref oder
#    Beispiel-Pfad war, nicht der echte Output-Pfad. Ergebnis: validator
#    auf falschem File → false-WARN auf real-saubere Outputs.
if [ -z "$OUTPUT_FILE" ] && [ -n "$PROMPT" ]; then
  OUTPUT_FILE=$(echo "$PROMPT" | grep -oE 'output_file=[a-zA-Z0-9_./-]+\.md' | head -1 | sed 's/^output_file=//' || true)
fi

if [ -z "$OUTPUT_FILE" ]; then
  echo "evidence-pointer-check: WARN — Tier-1-Sub-Agent-Task ohne erkennbares output_file. Prompt-Pattern fehlte." >&2
  exit 0
fi

# Resolve path relative to project root
PROJECT_ROOT="${CLAUDE_PROJECT_DIR:-$(pwd)}"
if [[ "$OUTPUT_FILE" != /* ]]; then
  OUTPUT_FILE="$PROJECT_ROOT/$OUTPUT_FILE"
fi

if [ ! -f "$OUTPUT_FILE" ]; then
  echo "evidence-pointer-check: WARN — Tier-1-Output-File fehlt: $OUTPUT_FILE" >&2
  exit 0
fi

# ---------- Filter: only schema_version: 1 outputs ----------
# Legacy outputs (schema_version: 0 or missing) silent-skip.
#
# C2-004 fix (Pass-2): pre-fix `^schema_version:\s*1` hatte zwei Bugs:
#   - Kein End-Anchor → matched `schema_version: 11`, `schema_version: 100`
#     (false-positive: hits validator mit "unsupported schema_version: 11").
#   - Kein Quote-Support → quoted-Forms `"1"` / `'1'` NO_MATCH (false-negative,
#     skipped legitime v1-Outputs).
# Validator-Acceptor (validate_evidence_pointers.py:648 `sv_raw.isdigit()`)
# akzeptiert genau die unten gelisteten 4 Forms; Filter ist jetzt symmetrisch.

if ! grep -qE "^schema_version:[[:space:]]*[\"']?1[\"']?[[:space:]]*(#.*)?$" "$OUTPUT_FILE" 2>/dev/null; then
  # Legacy or non-evidence-output — silent skip
  exit 0
fi

# ---------- Validate via standalone validator ----------

FRAMEWORK_ROOT="$(cd "$(dirname "$(readlink -f "$0")")/../../.." && pwd)"
VALIDATOR="$FRAMEWORK_ROOT/scripts/validate_evidence_pointers.py"

if [ ! -f "$VALIDATOR" ]; then
  echo "evidence-pointer-check: WARN — validator-Skript fehlt: $VALIDATOR" >&2
  exit 0
fi

PYTHON_BIN="${PYTHON:-python3}"
# Explicit --repo-root (CC-002 belt-and-suspenders): never trust the CLI
# default-resolution alone. PROJECT_ROOT is already set above; fall back to
# `git rev-parse --show-toplevel` so pointer-paths in the output-file resolve
# against the actual repo, not the directory that contains the output file.
REPO_ROOT_ARG="${PROJECT_ROOT:-$(git -C "$(dirname "$OUTPUT_FILE")" rev-parse --show-toplevel 2>/dev/null || echo "")}"
set +e
if [ -n "$REPO_ROOT_ARG" ]; then
  VALIDATOR_OUT=$("$PYTHON_BIN" "$VALIDATOR" "$OUTPUT_FILE" --repo-root "$REPO_ROOT_ARG" 2>&1)
else
  VALIDATOR_OUT=$("$PYTHON_BIN" "$VALIDATOR" "$OUTPUT_FILE" 2>&1)
fi
VALIDATOR_RC=$?
set -e

if [ "$VALIDATOR_RC" -ne 0 ]; then
  # WARN (initial). Spec §4.1: Promotion zu BLOCK nach Bewaehrung.
  echo "" >&2
  echo "============================================================" >&2
  echo "evidence-pointer-check: WARN — Tier-1-Sub-Agent-Output mit" >&2
  echo "fabricated/invalid evidence-pointers. Validator-Output:" >&2
  echo "" >&2
  echo "$VALIDATOR_OUT" | head -20 | sed 's/^/  /' >&2
  echo "" >&2
  echo "Output-File: $OUTPUT_FILE" >&2
  echo "Sub-Agent: ${SUBAGENT:-<inferred-tier-1>}" >&2
  echo "Spec: docs/specs/299-fabrication-mitigation.md §4.1 (WARN initial)" >&2
  echo "============================================================" >&2
fi

exit 0
