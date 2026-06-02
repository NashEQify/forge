#!/usr/bin/env bash
set -euo pipefail

# pre-commit.sh — Git pre-commit / commit-msg hook for forge consumers.
#
# Canonical location: orchestrators/claude-code/hooks/.
# Symlink into .git/hooks/pre-commit AND .git/hooks/commit-msg from any
# consumer repo. Idempotent installer: scripts/install-git-hooks.sh.
#
# Post-2026-05-31 (ADR-004 hook paradigm shift): 6 checks.
# 3 BLOCK + 3 WARN. Universally portable (git is on every harness).
#
# Checks (ordered):
#   1. PLAN-VALIDATE        (BLOCK) — plan_engine.py --validate must show 0 errors
#   2. CG-CONV              (BLOCK) — commit message format matches convention
#   3. SKILL-FM-VALIDATE    (BLOCK) — SKILL.md YAML/frontmatter subset
#   4. SECRET-SCAN          (WARN)  — gitleaks wrapper; WARN-only; skipped when
#                                     gitleaks is not installed.
#   5. SOURCE-VERIFICATION  (WARN)  — board/council reviews must cite source
#                                     files (line-numbered evidence pointers).
#   6. ANTI-PHANTOM         (WARN)  — staged docs must not bind a live
#                                     enforcement verb to a purged hook-name
#                                     (enforcement-honesty, ADR-005).
#
# Dropped 2026-05-31 (8 checks, see docs/decisions/ADR-004-hook-paradigm-shift.md):
#   TASK-SYNC, OBLIGATIONS, STALE-CLEANUP, PERSIST-GATE, ENGINE-USE,
#   RUNBOOK-DRIFT, AGENT-SKILL-DRIFT, PIEBALD-BUDGET — discipline replaces
#   observability WARN signals; Piebald budget loosened in same commit.

FRAMEWORK_ROOT="$(cd "$(dirname "$(readlink -f "$0")")/../../.." && pwd)"
PLAN_ENGINE="${FRAMEWORK_ROOT}/scripts/plan_engine.py"

BLOCK=0
WARNINGS=()

# ---------- Hook-Mode-Detection (F-102 fix) ----------
#
# This script handles BOTH pre-commit and commit-msg hook invocations:
#   - pre-commit hook: $0 basename = "pre-commit", no args
#   - commit-msg hook: $0 basename = "commit-msg", $1 = path to commit-msg file
#
# F-102 root cause: `git commit --amend -m "msg"` doesn't write the new message
# to .git/COMMIT_EDITMSG before pre-commit fires — pre-commit reads STALE old
# message. Workaround was `echo "msg" > .git/COMMIT_EDITMSG` before commit.
#
# Architectural fix:
#   - In commit-msg mode: $1 = fresh message file → message-checks BLOCK reliably
#   - In pre-commit mode: COMMIT-CONVENTION does NOT block. commit-msg is
#     authoritative for commit-message format checks.

HOOK_MODE="pre-commit"
case "$(basename "$0")" in
  commit-msg) HOOK_MODE="commit-msg" ;;
esac

# ---------- Check 1: PLAN-VALIDATE (BLOCK) ----------

if [ -f "$PLAN_ENGINE" ]; then
  VALIDATE_OUTPUT=$(python3 "$PLAN_ENGINE" --validate 2>&1) || true

  # Accept either "Summary: 0 errors" (with-tasks) or "CLEAN" (empty-state).
  # Pinned form — earlier `^Summary:.*0 errors|^CLEAN:` was fail-OPEN
  # because `.*` is greedy and any N-error count containing the
  # substring `0 errors` (e.g. "Summary: 100 errors found") matched the
  # pattern. Pinned literal " 0 errors\b" prevents the substring
  # collision on multi-digit error counts.
  if echo "$VALIDATE_OUTPUT" | grep -qE '^Summary: 0 errors\b|^CLEAN:'; then
    echo "pre-commit: PLAN-VALIDATE PASS"
  else
    ERROR_COUNT=$(echo "$VALIDATE_OUTPUT" | grep -oP '(\d+) errors' | grep -oP '^\d+' || echo "?")
    echo "pre-commit: PLAN-VALIDATE BLOCK — ${ERROR_COUNT} error(s) found"
    echo ""
    echo "$VALIDATE_OUTPUT" | grep -E '^ERRORS|^  ' || true
    echo ""
    BLOCK=1
  fi
else
  echo "pre-commit: PLAN-VALIDATE SKIP — plan_engine.py not found (graceful degradation)"
fi

# ---------- Check 2: CG-CONV — Commit-Convention Format (BLOCK in commit-msg mode) ----------
#
# Regex: type(scope): description [Task-NNN]
# Types: feat | fix | refactor | review | save | docs | chore
#        | solve | build | audit | research (workflow-engine commit-types)
# Scope optional, Task-Ref optional (entfaellt bei save/checkpoint)
#
# commit-msg mode receives fresh message path as $1 from git.
# pre-commit mode may see stale .git/COMMIT_EDITMSG and must never BLOCK on it.

COMMIT_MSG_FILE="${1:-${FRAMEWORK_ROOT}/.git/COMMIT_EDITMSG}"
CONVENTION_REGEX='^(feat|fix|refactor|review|save|docs|chore|solve|build|audit|research)(\([^)]+\))?: [^ ].+( \[Task-[0-9]+\])?$'

if [ "$HOOK_MODE" = "commit-msg" ]; then
  if [ -z "${1:-}" ] || [ ! -f "${1:-}" ]; then
    echo "commit-msg: COMMIT-CONVENTION BLOCK — commit message file missing (\$1)."
    echo "  Ensure .git/hooks/commit-msg invokes this hook with the message path."
    BLOCK=1
  else
    COMMIT_MSG_FILE="$1"
    FIRST_LINE=$(head -1 "$COMMIT_MSG_FILE" | tr -d '\r')

    # Skip empty lines and comment-only messages (git aborts these anyway)
    if [ -z "$FIRST_LINE" ] || [[ "$FIRST_LINE" =~ ^# ]]; then
      echo "commit-msg: COMMIT-CONVENTION SKIP (empty or comment-only first line)"
    elif echo "$FIRST_LINE" | grep -qE "$CONVENTION_REGEX"; then
      echo "commit-msg: COMMIT-CONVENTION PASS"
    else
      echo "commit-msg: COMMIT-CONVENTION BLOCK — erwartetes Format:"
      echo "  type(scope): Beschreibung [Task-NNN]"
      echo "  Types: feat|fix|refactor|review|save|docs|chore|solve|build|audit|research"
      echo "  (Task-Ref entfaellt bei save/checkpoint)"
      echo "  Gefundene First-Line: $FIRST_LINE"
      echo "commit-msg: HINT — Retry mit korrigierter Message:"
      echo "  git commit -m \"docs(scope): short description [Task-123]\""
      echo "  OR:   echo \"docs(scope): short description [Task-123]\" > .git/COMMIT_EDITMSG && git commit -F .git/COMMIT_EDITMSG"
      BLOCK=1
    fi
  fi
else
  echo "pre-commit: COMMIT-CONVENTION SKIP (authoritative validation runs in commit-msg hook)"
  if [ ! -e "${FRAMEWORK_ROOT}/.git/hooks/commit-msg" ]; then
    WARNINGS+=("COMMIT-CONVENTION: commit-msg hook missing. Install via: ln -sf ${FRAMEWORK_ROOT}/orchestrators/claude-code/hooks/pre-commit.sh ${FRAMEWORK_ROOT}/.git/hooks/commit-msg")
  fi
fi

# ---------- Check 3: SKILL-FM-VALIDATE (BLOCK) ----------
#
# Validates staged skills/**/SKILL.md frontmatter (YAML subset).
# SKIP: consumer repos without skills/, or PyYAML/skip inside script.

SKILL_FM="${FRAMEWORK_ROOT}/scripts/skill_fm_validate.py"
if [ -f "$SKILL_FM" ] && [ -d "${FRAMEWORK_ROOT}/skills" ]; then
  set +e
  FM_OUT=$(python3 "$SKILL_FM" --repo "$FRAMEWORK_ROOT" 2>&1)
  FM_RET=$?
  set -e
  echo "$FM_OUT"
  # WARN lines from validator are echoed in FM_OUT; BLOCK → non-zero
  if [ "$FM_RET" -ne 0 ]; then
    echo "pre-commit: SKILL-FM-VALIDATE BLOCK"
    BLOCK=1
  fi
else
  echo "pre-commit: SKILL-FM-VALIDATE SKIP — script or skills/ missing"
fi

# ---------- Check 4: SECRET-SCAN (WARN) — gitleaks wrapper ----------
#
# Run gitleaks against staged changes if the binary is available.
# WARN-only (don't block legitimate commits if gitleaks ist not installed).
# Install:
#   - Linux/Mac: brew install gitleaks
#   - Linux apt: download release from github.com/gitleaks/gitleaks/releases
#   - Go: go install github.com/gitleaks/gitleaks/v8@latest

if command -v gitleaks &>/dev/null; then
  set +e
  GITLEAKS_OUT=$(gitleaks protect --staged --no-banner --redact 2>&1)
  GITLEAKS_RET=$?
  set -e
  if [ "$GITLEAKS_RET" -ne 0 ]; then
    # gitleaks exit 1 means findings; any other non-zero is error
    LEAKS_RENDERED=$(echo "$GITLEAKS_OUT" | head -10 | sed 's/^/    /')
    WARNINGS+=("SECRET-SCAN: gitleaks reported finding(s) in staged content:"$'\n'"${LEAKS_RENDERED}"$'\n'"    Review carefully before pushing. False positive? Add to .gitleaksignore.")
  fi
else
  # Only warn about missing gitleaks once per session via marker (avoid noise)
  GITLEAKS_MARK="${FRAMEWORK_ROOT}/.session/gitleaks-missing.marker"
  mkdir -p "$(dirname "$GITLEAKS_MARK")" 2>/dev/null || true
  if [ ! -f "$GITLEAKS_MARK" ] || [ "$(find "$GITLEAKS_MARK" -mtime +0 2>/dev/null)" ]; then
    WARNINGS+=("SECRET-SCAN: gitleaks not installed — secret-pattern check skipped. Install via 'brew install gitleaks' or github.com/gitleaks/gitleaks/releases. Suppressing this warning for 24h.")
    touch "$GITLEAKS_MARK" 2>/dev/null || true
  fi
fi

# ---------- Check 5: SOURCE-VERIFICATION (WARN) ----------
#
# Filter: staged files under
#   - docs/reviews/board/*.md
#   - docs/reviews/council/**/*.md
#   - docs/specs/*.md
#   - docs/reviews/{code,architecture,sectional,amendment}/*.md
# that carry YAML frontmatter with schema_version: 1.
#
# Per file: call scripts/validate_evidence_pointers.py <file>.
# Legacy (schema_version: 0 or missing) → silent skip via grep filter.
#
# Order: placed AFTER SECRET-SCAN — this check reads file contents, which
# is uncritical post-secret-scan.

VALIDATOR="${FRAMEWORK_ROOT}/scripts/validate_evidence_pointers.py"
if [ -f "$VALIDATOR" ]; then
  STAGED_EVIDENCE_FILES=$(git diff --cached --name-only --diff-filter=AM 2>/dev/null \
    | grep -E '^docs/(reviews/(board|council|code|architecture|sectional|amendment)|specs)/' || true)

  if [ -n "$STAGED_EVIDENCE_FILES" ]; then
    EVIDENCE_WARNINGS=()
    FILTERED_FILES=()
    while IFS= read -r f; do
      [ -z "$f" ] && continue
      [ ! -f "$f" ] && continue
      # Filter is symmetric with the validator's parser: it accepts
      #   schema_version: 1                  (plain)
      #   schema_version: "1" / '1'          (quoted)
      #   schema_version: 1   (trailing ws)  (whitespace)
      #   schema_version: 1 # comment        (inline comment)
      # Rejects: 0, 2, 11, 100, kommentierte Zeilen.
      if grep -qE "^schema_version:[[:space:]]*[\"']?1[\"']?[[:space:]]*(#.*)?$" "$f" 2>/dev/null; then
        FILTERED_FILES+=("$f")
      fi
    done <<< "$STAGED_EVIDENCE_FILES"

    if [ ${#FILTERED_FILES[@]} -gt 0 ]; then
      set +e
      VAL_OUT=$(python3 "$VALIDATOR" "${FILTERED_FILES[@]}" --repo-root "$FRAMEWORK_ROOT" 2>&1)
      VAL_RC=$?
      set -e
      if [ "$VAL_RC" -ne 0 ]; then
        EVIDENCE_WARNINGS+=("SOURCE-VERIFICATION ($VAL_RC fail across ${#FILTERED_FILES[@]} file(s)):"$'\n'"$(echo "$VAL_OUT" | head -20 | sed 's/^/    /')")
      fi
    fi

    if [ ${#EVIDENCE_WARNINGS[@]} -gt 0 ]; then
      for ew in "${EVIDENCE_WARNINGS[@]}"; do
        WARNINGS+=("$ew")
      done
    fi
  fi
fi

# ---------- Check 6: ANTI-PHANTOM (WARN) ----------
#
# Enforcement-honesty tripwire: flags staged docs that bind a
# present-tense enforcement verb to a hook-name with no runnable
# artifact (purged in the hook paradigm shift, ADR-004). An honest
# marker — a historical note or an enforcement-class tag — suppresses
# the warning. WARN-only (advisory, never blocks).
#
# Scope is deliberately narrow: only names with NO legitimate live
# meaning are listed. Names that double as live concepts (the
# STALE-CLEANUP invariant, the PERSIST-GATE discipline gate, the
# piebald-budget protocol) are NOT listed here — class-tagging in
# framework/enforcement-registry.md is the SoT for those. Extend
# PHANTOM_NAMES only with names that have no runnable artifact at all.

PHANTOM_NAMES='BRIEF-CLAIMS|path-whitelist-guard|frozen-zone-guard'
LIVE_VERB='BLOCKs|BLOCKS|blocks|guards|re-runs|reruns|enforces|enforced'
HONEST_MARK='purged|dropped|former|formerly|no longer|removed|historical|was a|used to|phantom|\[DISCIPLINE\]|\[GATE\]|\[WORKFLOW\]|\[STRUCTURAL\]'

# Active-surface only. Forensic/review zones (audit, reviews, build logs,
# dogfood-learnings, context) legitimately QUOTE phantom claims as
# evidence — they are append-only records, not docs that mislead a
# reader about live enforcement. Exclude them.
STAGED_DOCS=$(git diff --cached --name-only --diff-filter=AM 2>/dev/null \
  | grep -E '\.md$' \
  | grep -vE '^(docs/(audit|reviews|build|dogfood-learnings)|context)/' || true)
if [ -n "$STAGED_DOCS" ]; then
  PHANTOM_HITS=()
  while IFS= read -r f; do
    [ -z "$f" ] && continue
    [ ! -f "$f" ] && continue
    while IFS= read -r hit; do
      [ -z "$hit" ] && continue
      echo "$hit" | grep -qiE "$HONEST_MARK" && continue
      PHANTOM_HITS+=("${f}:${hit}")
    done < <(grep -nE "(${PHANTOM_NAMES}).{0,40}(${LIVE_VERB})|(${LIVE_VERB}).{0,40}(${PHANTOM_NAMES})" "$f" 2>/dev/null)
  done <<< "$STAGED_DOCS"
  if [ ${#PHANTOM_HITS[@]} -gt 0 ]; then
    RENDERED=$(printf '    %s\n' "${PHANTOM_HITS[@]}" | head -10)
    WARNINGS+=("ANTI-PHANTOM: doc(s) state live enforcement for a purged hook-name. Reframe to an honest enforcement-class statement (see framework/enforcement-registry.md) or add a historical marker:"$'\n'"${RENDERED}")
  fi
fi

# ---------- Output ----------

if [ ${#WARNINGS[@]} -gt 0 ]; then
  echo ""
  for w in "${WARNINGS[@]}"; do
    echo "pre-commit: WARNING — $w"
  done
fi

if [ "$BLOCK" -eq 1 ]; then
  echo ""
  echo "pre-commit: BLOCKED — fix errors above before committing."
  exit 1
fi

exit 0
