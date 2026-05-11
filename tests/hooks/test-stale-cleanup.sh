#!/usr/bin/env bash
# test-stale-cleanup.sh — Tests for H2 (Task-011 Phase 3b Check 5)
#
# Test cases from docs/specs/011-harness-refactor.md §H2 Minimal-Tests:
#   1. Kein Marker: commit "fix: typo" → no WARN
#   2. Clean: "STALE: foo-xyz-nonexistent.md" → no WARN
#   3. Frozen-only: STALE artefact only referenced in context/history/** → no WARN
#   4. Negative: STALE artefact referenced in framework/ → WARN
#   5. Edge: "STALE:" without args → no WARN
#
# Strategy: run pre-commit.sh with custom COMMIT_MSG_FILE (passed as $1).
# Isolate from real staged changes by using a fresh temp index via
# GIT_INDEX_FILE pointing to a scratch copy of the current index.
# To avoid side effects: create temp sandbox dir with isolated git repo
# for tests that need file-based references.
#
# Usage: bash tests/hooks/test-stale-cleanup.sh
# Exit 0 if all pass, exit 1 on any failure.

set -uo pipefail

FRAMEWORK_ROOT="$(cd "$(dirname "$(readlink -f "$0")")/../../.." && pwd)"
HOOK="$FRAMEWORK_ROOT/orchestrators/claude-code/hooks/pre-commit.sh"

if [ ! -x "$HOOK" ] && [ ! -r "$HOOK" ]; then
  echo "FAIL: hook not found at $HOOK"
  exit 1
fi

PASS=0
FAIL=0
FAILED_TESTS=()

# Create isolated sandbox
SANDBOX=$(mktemp -d /tmp/test-stale-cleanup.XXXXXX)
trap 'rm -rf "$SANDBOX"' EXIT

# Build a fake framework-root inside sandbox with the needed structure
mkdir -p "$SANDBOX/framework/_archived"
mkdir -p "$SANDBOX/skills/test"
mkdir -p "$SANDBOX/docs"
mkdir -p "$SANDBOX/agents"
mkdir -p "$SANDBOX/scripts"
mkdir -p "$SANDBOX/orchestrators/claude-code/hooks"
mkdir -p "$SANDBOX/context/history"
mkdir -p "$SANDBOX/.claude"
mkdir -p "$SANDBOX/.git"

# Copy hook + frozen-zones into sandbox so it's a realistic framework root
cp "$HOOK" "$SANDBOX/orchestrators/claude-code/hooks/pre-commit.sh"
chmod +x "$SANDBOX/orchestrators/claude-code/hooks/pre-commit.sh"
cp "$FRAMEWORK_ROOT/.claude/frozen-zones.txt" "$SANDBOX/.claude/frozen-zones.txt"

# Init minimal git for plan-validate skip (no plan_engine.py → graceful skip)
( cd "$SANDBOX" && git init -q && git config commit.gpgsign false && \
  git config user.email "test@test" && git config user.name "test" ) || true

run_hook() {
  local commit_msg_file="$1"
  cd "$SANDBOX" && bash "$SANDBOX/orchestrators/claude-code/hooks/pre-commit.sh" "$commit_msg_file" 2>&1
}

check_no_stale_warn() {
  local output="$1"
  ! echo "$output" | grep -q "STALE-CLEANUP:"
}

check_has_stale_warn() {
  local output="$1"
  echo "$output" | grep -q "STALE-CLEANUP:"
}

# ---------- Case 1: No marker ----------
MSG_FILE="$SANDBOX/msg1.txt"
echo "fix(test): typo in docs [Task-999]" > "$MSG_FILE"
OUT=$(run_hook "$MSG_FILE" || true)
if check_no_stale_warn "$OUT"; then
  echo "  PASS: 1-no-marker"
  PASS=$((PASS + 1))
else
  echo "  FAIL: 1-no-marker (unexpected STALE-CLEANUP warn)"
  echo "$OUT" | head -20
  FAIL=$((FAIL + 1))
  FAILED_TESTS+=("1-no-marker")
fi

# ---------- Case 2: STALE marker, artefact has no references ----------
MSG_FILE="$SANDBOX/msg2.txt"
cat > "$MSG_FILE" <<EOF
refactor(test): remove old thing [Task-999]

STALE: xyz-totally-nonexistent-artefact-name-97531.md
EOF
OUT=$(run_hook "$MSG_FILE" || true)
if check_no_stale_warn "$OUT"; then
  echo "  PASS: 2-clean-no-refs"
  PASS=$((PASS + 1))
else
  echo "  FAIL: 2-clean-no-refs"
  echo "$OUT" | head -20
  FAIL=$((FAIL + 1))
  FAILED_TESTS+=("2-clean-no-refs")
fi

# ---------- Case 3: STALE marker, ref only in frozen zone ----------
# Write a reference only in context/history/ (which is frozen).
echo "This file references frozen-artefact-abc-12345.md" > "$SANDBOX/context/history/2026-01-01-note.md"
MSG_FILE="$SANDBOX/msg3.txt"
cat > "$MSG_FILE" <<EOF
refactor(test): sunset artefact [Task-999]

STALE: frozen-artefact-abc-12345.md
EOF
OUT=$(run_hook "$MSG_FILE" || true)
if check_no_stale_warn "$OUT"; then
  echo "  PASS: 3-frozen-only"
  PASS=$((PASS + 1))
else
  echo "  FAIL: 3-frozen-only (hits in frozen zone should be filtered)"
  echo "$OUT" | head -20
  FAIL=$((FAIL + 1))
  FAILED_TESTS+=("3-frozen-only")
fi

# ---------- Case 4: STALE marker, ref in non-frozen zone → WARN ----------
echo "Active reference to old-skill-xy-42 here." > "$SANDBOX/skills/test/SKILL.md"
MSG_FILE="$SANDBOX/msg4.txt"
cat > "$MSG_FILE" <<EOF
refactor(test): retire skill [Task-999]

RETIRED: old-skill-xy-42
EOF
OUT=$(run_hook "$MSG_FILE" || true)
if check_has_stale_warn "$OUT"; then
  echo "  PASS: 4-non-frozen-hit"
  PASS=$((PASS + 1))
else
  echo "  FAIL: 4-non-frozen-hit (expected STALE-CLEANUP warn)"
  echo "$OUT" | head -20
  FAIL=$((FAIL + 1))
  FAILED_TESTS+=("4-non-frozen-hit")
fi

# ---------- Case 5: Empty marker (no args) ----------
MSG_FILE="$SANDBOX/msg5.txt"
cat > "$MSG_FILE" <<EOF
refactor(test): something [Task-999]

STALE:
EOF
OUT=$(run_hook "$MSG_FILE" || true)
if check_no_stale_warn "$OUT"; then
  echo "  PASS: 5-empty-marker"
  PASS=$((PASS + 1))
else
  echo "  FAIL: 5-empty-marker"
  echo "$OUT" | head -20
  FAIL=$((FAIL + 1))
  FAILED_TESTS+=("5-empty-marker")
fi

# ---------- Case 6: Marker with multiple comma-separated names ----------
echo "Reference to artefact-A-99 in docs." > "$SANDBOX/docs/notes.md"
MSG_FILE="$SANDBOX/msg6.txt"
cat > "$MSG_FILE" <<EOF
refactor(test): sunset two things [Task-999]

SUNSET: artefact-A-99, artefact-B-nonexistent
EOF
OUT=$(run_hook "$MSG_FILE" || true)
if check_has_stale_warn "$OUT"; then
  echo "  PASS: 6-multi-comma"
  PASS=$((PASS + 1))
else
  echo "  FAIL: 6-multi-comma"
  echo "$OUT" | head -20
  FAIL=$((FAIL + 1))
  FAILED_TESTS+=("6-multi-comma")
fi

echo ""
echo "test-stale-cleanup: $PASS pass, $FAIL fail"
if [ "$FAIL" -gt 0 ]; then
  echo "Failed: ${FAILED_TESTS[*]}"
  exit 1
fi
exit 0
