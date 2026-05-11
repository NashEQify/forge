#!/usr/bin/env bash
# test-persist-gate.sh — Tests for H3 (Task-011 Phase 3b Check 6)
#
# Test cases from docs/specs/011-harness-refactor.md §H3 Minimal-Tests:
#   1. No change: commit only CLAUDE.md → no PERSIST-GATE warn
#   2. Status+context: tasks/X.yaml status change + context/history/Y → no warn
#   3. Negative: tasks/X.yaml status change, no context → PERSIST-GATE warn
#   4. Edge: new task file (add only) → no warn (TASK-SYNC skips additions)
#
# Strategy: sandbox git repo, stage specific files, run hook with dummy
# commit message file, check for PERSIST-GATE WARN.
#
# Usage: bash tests/hooks/test-persist-gate.sh
# Exit 0 if all pass, exit 1 on any failure.

set -uo pipefail

FRAMEWORK_ROOT="$(cd "$(dirname "$(readlink -f "$0")")/../../.." && pwd)"
HOOK="$FRAMEWORK_ROOT/orchestrators/claude-code/hooks/pre-commit.sh"

if [ ! -r "$HOOK" ]; then
  echo "FAIL: hook not found at $HOOK"
  exit 1
fi

PASS=0
FAIL=0
FAILED_TESTS=()

# ---------- Create sandbox ----------
SANDBOX=$(mktemp -d /tmp/test-persist-gate.XXXXXX)
trap 'rm -rf "$SANDBOX"' EXIT

mkdir -p "$SANDBOX/orchestrators/claude-code/hooks"
mkdir -p "$SANDBOX/docs/tasks"
mkdir -p "$SANDBOX/context/history"
mkdir -p "$SANDBOX/.claude"
cp "$HOOK" "$SANDBOX/orchestrators/claude-code/hooks/pre-commit.sh"
chmod +x "$SANDBOX/orchestrators/claude-code/hooks/pre-commit.sh"
cp "$FRAMEWORK_ROOT/.claude/frozen-zones.txt" "$SANDBOX/.claude/frozen-zones.txt" 2>/dev/null || true

# Init git repo in sandbox
cd "$SANDBOX"
git init -q
git config commit.gpgsign false
git config user.email "test@test"
git config user.name "test"

# Seed initial task YAML so we can modify it
cat > "$SANDBOX/docs/tasks/T-001-sample.yaml" <<EOF
id: T-001
status: todo
readiness: ready
title: sample
EOF
cat > "$SANDBOX/CLAUDE.md" <<EOF
# sample
EOF
git add docs/tasks/T-001-sample.yaml CLAUDE.md
git commit -q -m "feat(test): initial [Task-999]" 2>&1 | grep -v "PLAN-VALIDATE\|COMMIT-CONVENTION\|pre-commit" || true

run_hook() {
  local commit_msg_file="$1"
  cd "$SANDBOX" && bash "$SANDBOX/orchestrators/claude-code/hooks/pre-commit.sh" "$commit_msg_file" 2>&1
}

check_no_persist_warn() {
  local output="$1"
  ! echo "$output" | grep -q "PERSIST-GATE:"
}

check_has_persist_warn() {
  local output="$1"
  echo "$output" | grep -q "PERSIST-GATE:"
}

reset_staging() {
  cd "$SANDBOX" && git reset -q HEAD -- . 2>/dev/null || true
  # Restore working tree files to HEAD
  cd "$SANDBOX" && git checkout -q -- docs/tasks/T-001-sample.yaml CLAUDE.md 2>/dev/null || true
  # Remove any new files
  cd "$SANDBOX" && rm -f context/history/*.md docs/tasks/T-002-*.yaml 2>/dev/null || true
}

# ---------- Case 1: No task change, no persist warn ----------
reset_staging
echo "# sample updated" > "$SANDBOX/CLAUDE.md"
cd "$SANDBOX" && git add CLAUDE.md
MSG_FILE="$SANDBOX/msg1.txt"
echo "docs(test): update claude [Task-999]" > "$MSG_FILE"
OUT=$(run_hook "$MSG_FILE" || true)
if check_no_persist_warn "$OUT"; then
  echo "  PASS: 1-no-task-change"
  PASS=$((PASS + 1))
else
  echo "  FAIL: 1-no-task-change (unexpected PERSIST-GATE warn)"
  echo "$OUT" | head -20
  FAIL=$((FAIL + 1))
  FAILED_TESTS+=("1-no-task-change")
fi

# ---------- Case 2: Status change + context file staged → PASS ----------
reset_staging
cat > "$SANDBOX/docs/tasks/T-001-sample.yaml" <<EOF
id: T-001
status: done
readiness: ready
title: sample
EOF
echo "# history" > "$SANDBOX/context/history/2026-04-20-note.md"
cd "$SANDBOX" && git add docs/tasks/T-001-sample.yaml context/history/2026-04-20-note.md
MSG_FILE="$SANDBOX/msg2.txt"
echo "feat(test): done [Task-999]" > "$MSG_FILE"
OUT=$(run_hook "$MSG_FILE" || true)
if check_no_persist_warn "$OUT"; then
  echo "  PASS: 2-status-plus-context"
  PASS=$((PASS + 1))
else
  echo "  FAIL: 2-status-plus-context"
  echo "$OUT" | head -20
  FAIL=$((FAIL + 1))
  FAILED_TESTS+=("2-status-plus-context")
fi

# ---------- Case 3: Status change WITHOUT context → WARN ----------
reset_staging
cat > "$SANDBOX/docs/tasks/T-001-sample.yaml" <<EOF
id: T-001
status: done
readiness: ready
title: sample
EOF
cd "$SANDBOX" && git add docs/tasks/T-001-sample.yaml
MSG_FILE="$SANDBOX/msg3.txt"
echo "feat(test): done [Task-999]" > "$MSG_FILE"
OUT=$(run_hook "$MSG_FILE" || true)
if check_has_persist_warn "$OUT"; then
  echo "  PASS: 3-status-no-context"
  PASS=$((PASS + 1))
else
  echo "  FAIL: 3-status-no-context (expected PERSIST-GATE warn)"
  echo "$OUT" | head -20
  FAIL=$((FAIL + 1))
  FAILED_TESTS+=("3-status-no-context")
fi

# ---------- Case 4: New task file (add, no +status:-diff) → no warn ----------
reset_staging
cat > "$SANDBOX/docs/tasks/T-002-new.yaml" <<EOF
id: T-002
status: todo
title: brand new
EOF
cd "$SANDBOX" && git add docs/tasks/T-002-new.yaml
MSG_FILE="$SANDBOX/msg4.txt"
echo "feat(test): new task [Task-999]" > "$MSG_FILE"
OUT=$(run_hook "$MSG_FILE" || true)
if check_no_persist_warn "$OUT"; then
  echo "  PASS: 4-new-task-add"
  PASS=$((PASS + 1))
else
  echo "  FAIL: 4-new-task-add"
  echo "$OUT" | head -20
  FAIL=$((FAIL + 1))
  FAILED_TESTS+=("4-new-task-add")
fi

echo ""
echo "test-persist-gate: $PASS pass, $FAIL fail"
if [ "$FAIL" -gt 0 ]; then
  echo "Failed: ${FAILED_TESTS[*]}"
  exit 1
fi
exit 0
