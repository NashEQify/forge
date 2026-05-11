#!/usr/bin/env bash
set -euo pipefail

# pre-commit.sh — Git pre-commit hook for BuddyAI [Task-292]
#
# Canonical location post-Task-011 Phase 2a: orchestrators/claude-code/hooks/.
# `scripts/hooks/` remains as symlink-bridge until Phase 5 sunset.
# Symlink into .git/hooks/pre-commit (from any consumer repo):
#   ln -sf $FRAMEWORK_DIR/orchestrators/claude-code/hooks/pre-commit.sh .git/hooks/pre-commit
#
# Checks (ordered):
#   1. PLAN-VALIDATE     (BLOCK) — plan_engine.py --validate must show 0 errors
#   2. TASK-SYNC         (WARN)  — status/readiness changes in task YAMLs
#   3. OBLIGATIONS       (WARN)  — docs/dashboard/plan_engine changes need deploy
#   4. CG-CONV           (BLOCK) — commit message format matches convention
#   5. STALE-CLEANUP     (WARN)  — STALE/RETIRED/SUNSET marker refs outside frozen zones
#   6. PERSIST-GATE      (WARN)  — status-change without context-update
#   7. SKILL-FM-VALIDATE (BLOCK) — SKILL.md YAML/frontmatter subset
#   8. ENGINE-USE        (WARN)  — feat/fix/refactor commit with Task-ref must
#                                  have active workflow in .workflow-state/.
#   9. RUNBOOK-DRIFT     (WARN)  — workflow.yaml ↔ WORKFLOW.md parity for
#                                  staged runbook files.
#  10. AGENT-SKILL-DRIFT (WARN)  — agents/<name>.md AUTO-block out of sync
#                                  with skill frontmatter `relevant_for:`.
#  11. SECRET-SCAN       (WARN)  — gitleaks wrapper. WARN-only; skipped when
#                                  gitleaks is not installed.
#  12. SOURCE-VERIFICATION (WARN) — board/council reviews must cite source
#                                   files (line-numbered evidence pointers).

FRAMEWORK_ROOT="$(cd "$(dirname "$(readlink -f "$0")")/../../.." && pwd)"
PLAN_ENGINE="${FRAMEWORK_ROOT}/scripts/plan_engine.py"

BLOCK=0
WARNINGS=()
STATUS_CHANGE_FOUND=0

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
#
# Stale detection: COMMIT_EDITMSG content matches HEAD's commit-msg exactly
# (typical sign of amend with stale message data).
#
# Install commit-msg hook (idempotent):
#   ln -sf $FRAMEWORK_ROOT/orchestrators/claude-code/hooks/pre-commit.sh \
#          .git/hooks/commit-msg

HOOK_MODE="pre-commit"
case "$(basename "$0")" in
  commit-msg) HOOK_MODE="commit-msg" ;;
esac

MSG_IS_STALE=0
if [ "$HOOK_MODE" = "pre-commit" ]; then
  COMMIT_EDITMSG_PATH="${FRAMEWORK_ROOT}/.git/COMMIT_EDITMSG"
  if [ -f "$COMMIT_EDITMSG_PATH" ] && git rev-parse --verify HEAD >/dev/null 2>&1; then
    HEAD_MSG=$(git log -1 --pretty=%B 2>/dev/null || echo "")
    EDITMSG_BODY=$(grep -v '^#' "$COMMIT_EDITMSG_PATH" 2>/dev/null | sed -e 's/[[:space:]]*$//' || echo "")
    HEAD_MSG_NORMALIZED=$(echo "$HEAD_MSG" | sed -e 's/[[:space:]]*$//')
    if [ -n "$EDITMSG_BODY" ] && [ "$EDITMSG_BODY" = "$HEAD_MSG_NORMALIZED" ]; then
      MSG_IS_STALE=1
      echo "pre-commit: NOTE — COMMIT_EDITMSG matches HEAD message exactly. Likely amend-with-m (F-102). Message-checks downgraded to WARN; commit-msg hook (if installed) will re-verify."
    fi
  fi
fi

# ---------- Check 1: PLAN-VALIDATE (BLOCK) ----------

if [ -f "$PLAN_ENGINE" ]; then
  VALIDATE_OUTPUT=$(python3 "$PLAN_ENGINE" --validate 2>&1) || true

  # Accept either "Summary: 0 errors" (with-tasks) or "CLEAN" (empty-state).
  if echo "$VALIDATE_OUTPUT" | grep -qE '^Summary:.*0 errors|^CLEAN:'; then
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

# ---------- Check 2: TASK-SYNC (WARN, by design) ----------
#
# Status / readiness changes in task YAMLs MUST go through the
# task_status_update skill (CLAUDE.md invariant), not raw edits.
# WARN-only by design: a trace-marker BLOCK would be faux-mechanism
# (trivially settable). The real failure class is "Buddy forgets the
# skill", not "actively bypasses" — WARN is enough.

STAGED_YAMLS=$(git diff --cached --name-only -- 'docs/tasks/*.yaml' 2>/dev/null || true)

if [ -n "$STAGED_YAMLS" ]; then
  while IFS= read -r yaml_file; do
    # Skip newly added files (task_creation via skill)
    if git diff --cached --diff-filter=A --name-only -- "$yaml_file" 2>/dev/null | grep -q .; then
      continue
    fi

    # Check for status/readiness changes in the diff
    if git diff --cached -- "$yaml_file" 2>/dev/null | grep -qE '^\+status:|^\+readiness:'; then
      WARNINGS+=("TASK-SYNC: status/readiness in ${yaml_file} geaendert. MUST via task_status_update Skill (CLAUDE.md Invariante).")
      STATUS_CHANGE_FOUND=1
    fi
  done <<< "$STAGED_YAMLS"
fi

# ---------- Check 3: OBLIGATIONS (WARN) ----------

OBLIGATION_FILES=$(git diff --cached --name-only -- 'docs/' 'dashboard/' 'scripts/plan_engine.py' 2>/dev/null || true)

if [ -n "$OBLIGATION_FILES" ]; then
  WARNINGS+=("OBLIGATIONS: docs/dashboard/plan_engine files changed. Deploy via scripts/deploy-docs.sh noetig.")
fi

# ---------- Check 4: CG-CONV — Commit-Convention Format ----------
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

# ---------- Check 5: STALE-CLEANUP (WARN) — Task-011 Phase 3b H2 ----------
#
# Scans commit message for STALE:/RETIRED:/SUNSET: marker lines and greps
# the repo for active references to the named artefacts. Refs inside frozen
# zones are filtered out. Non-frozen hits produce a WARN with file:line
# list. WARN-only (never BLOCK) — user may legitimately split cleanup into
# separate commits.

if [ -f "${COMMIT_MSG_FILE:-}" ]; then
  FROZEN_ZONES_FILE="${FRAMEWORK_ROOT}/.claude/frozen-zones.txt"

  # Extract marker payloads. Format: "STALE: foo.md, bar/baz"
  STALE_PAYLOADS=$(grep -iE '^(STALE|RETIRED|SUNSET):' "$COMMIT_MSG_FILE" 2>/dev/null | sed -E 's/^[^:]+:[[:space:]]*//' || true)

  if [ -n "$STALE_PAYLOADS" ]; then
    # Collect hits across all listed artefacts
    STALE_HITS=()

    # Build frozen-pattern list (if file exists)
    FROZEN_PATTERNS=()
    if [ -f "$FROZEN_ZONES_FILE" ]; then
      while IFS= read -r fp || [ -n "$fp" ]; do
        [[ "$fp" =~ ^[[:space:]]*# ]] && continue
        [[ -z "${fp// /}" ]] && continue
        fp=$(echo "$fp" | tr -d '\r' | sed 's/[[:space:]]*$//')
        [[ -z "$fp" ]] && continue
        FROZEN_PATTERNS+=("$fp")
      done < "$FROZEN_ZONES_FILE"
    fi

    # Helper: does path match any frozen pattern (gitignore-glob → regex)
    is_frozen() {
      local path="$1"
      local pat
      [ ${#FROZEN_PATTERNS[@]} -eq 0 ] && return 1
      for pat in "${FROZEN_PATTERNS[@]}"; do
        local escaped
        escaped=$(printf '%s' "$pat" | sed -e 's/[][\.|$(){}?+^]/\\&/g')
        escaped="${escaped//\*\*/__DBLSTAR__}"
        escaped="${escaped//\*/[^/]*}"
        escaped="${escaped//__DBLSTAR__/.*}"
        if [[ "$path" =~ ^${escaped}$ ]] || [[ "$path" =~ ${escaped} ]]; then
          return 0
        fi
      done
      return 1
    }

    # Iterate payload lines (can be multiple STALE: lines)
    while IFS= read -r payload_line; do
      [ -z "$payload_line" ] && continue
      # Split on comma, trim
      IFS=',' read -ra NAMES <<< "$payload_line"
      for raw_name in "${NAMES[@]}"; do
        name=$(echo "$raw_name" | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//')
        [ -z "$name" ] && continue

        # Grep for references — limit dirs to avoid false positives in
        # node_modules etc. Include framework/, docs/, agents/, scripts/,
        # orchestrators/. Use --include='*.md' as per spec. Only pass dirs
        # that actually exist (consumer-repo tolerance).
        SEARCH_DIRS=()
        for d in framework docs agents scripts orchestrators; do
          [ -d "$FRAMEWORK_ROOT/$d" ] && SEARCH_DIRS+=("$d")
        done
        if [ ${#SEARCH_DIRS[@]} -eq 0 ]; then
          HITS=""
        else
          HITS=$(cd "$FRAMEWORK_ROOT" && grep -rn --include='*.md' \
            --fixed-strings "$name" \
            "${SEARCH_DIRS[@]}" 2>/dev/null || true)
        fi

        if [ -n "$HITS" ]; then
          while IFS= read -r hit; do
            [ -z "$hit" ] && continue
            # hit format: file:line:content
            hit_file=$(echo "$hit" | cut -d: -f1)
            if is_frozen "$hit_file"; then
              continue
            fi
            # Also skip hits inside the commit message itself (not a real ref)
            STALE_HITS+=("$hit")
          done <<< "$HITS"
        fi
      done
    done <<< "$STALE_PAYLOADS"

    if [ ${#STALE_HITS[@]} -gt 0 ]; then
      HIT_COUNT=${#STALE_HITS[@]}
      # Render up to first 10 hits inline, rest as "...(N more)"
      RENDER_MAX=10
      RENDERED=""
      for ((i=0; i<HIT_COUNT && i<RENDER_MAX; i++)); do
        RENDERED+=$'\n    '"${STALE_HITS[$i]}"
      done
      if [ "$HIT_COUNT" -gt "$RENDER_MAX" ]; then
        RENDERED+=$'\n    ...('"$((HIT_COUNT - RENDER_MAX))"' more)'
      fi
      WARNINGS+=("STALE-CLEANUP: ${HIT_COUNT} active reference(s) to declared STALE/RETIRED/SUNSET artefact(s) found outside frozen zones:${RENDERED}")
    fi
  fi
fi

# ---------- Check 6: PERSIST-GATE (WARN) — Task-011 Phase 3b H3 ----------
#
# When Check 2 detected a status/readiness change in a task YAML, verify
# that the commit also touches context/overview.md or context/history/*
# (framework-side or BuddyAI-side). If not → WARN "Persist Gate skipped".
# Re-uses STATUS_CHANGE_FOUND from Check 2.

if [ "$STATUS_CHANGE_FOUND" -eq 1 ]; then
  CONTEXT_FILES=$(git diff --cached --name-only -- \
    'context/overview.md' \
    'context/history/*' \
    'BuddyAI/context/overview.md' \
    'BuddyAI/context/history/*' \
    2>/dev/null || true)

  if [ -z "$CONTEXT_FILES" ]; then
    WARNINGS+=("PERSIST-GATE: status-change ohne context-update. Fehlend: context/overview.md ODER context/history/*. (operational.md §Persist Gate)")
  fi
fi

# ---------- Check 7: SKILL-FM-VALIDATE (BLOCK) — Task 366 F.2 ----------
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

# ---------- Check 8: ENGINE-USE (WARN) — Cross-Session-Workflow F-H-001 sub ----------
#
# Closes the Buddy-mental-trigger loophole: per operational.md §Workflow-Engine,
# build/fix/refactor work MUST run through the engine. If commit message is
# feat/fix/refactor with [Task-NNN] ref but NO active workflow in
# .workflow-state/<…>-NNN-….json carries that task_id → WARN.
#
# Mechanic: WARN-only because (a) some commits legitimately split a workflow's
# code-only step from the gate-step, (b) consumer repos may not use engine yet,
# (c) escape-hatch for manual workflows. The WARN nudges Buddy back to engine
# usage on next commit.

if [ -f "${COMMIT_MSG_FILE:-}" ]; then
  ENGINE_FIRST_LINE=$(head -1 "$COMMIT_MSG_FILE" | tr -d '\r')
  # Match: feat/fix/refactor + Task-NNN somewhere. Use grep -oE (no bash =~
  # quoting headaches with parens/brackets).
  ENGINE_TYPE=$(echo "$ENGINE_FIRST_LINE" | grep -oE '^(feat|fix|refactor|solve|build|audit)' || true)
  ENGINE_TASK_ID=$(echo "$ENGINE_FIRST_LINE" | grep -oE '\[Task-[0-9]+\]' | grep -oE '[0-9]+' || true)
  if [ -n "$ENGINE_TYPE" ] && [ -n "$ENGINE_TASK_ID" ]; then
    STATE_DIR_PATH="${FRAMEWORK_ROOT}/.workflow-state"
    ENGINE_FOUND=0
    if [ -d "$STATE_DIR_PATH" ]; then
      # Match "task_id": "NNN" exactly (string form per engine save_state)
      if grep -lE "\"task_id\":\s*\"${ENGINE_TASK_ID}\"" "$STATE_DIR_PATH"/*.json 2>/dev/null | grep -q .; then
        ENGINE_FOUND=1
      fi
    fi
    if [ "$ENGINE_FOUND" -eq 0 ]; then
      WARNINGS+=("ENGINE-USE: ${ENGINE_FIRST_LINE%% *}-commit for Task-${ENGINE_TASK_ID} without an active workflow in .workflow-state/. operational.md §Workflow engine: build/fix/refactor MUST go through the engine. Start: workflow_engine.py --start <build|fix|refactor> --task ${ENGINE_TASK_ID}")
    fi
  fi

  # Check 8 extension (post-comm-82657bc Defekt D, F-PA-002 root-cause-fix):
  # docs|chore commits with Tier-1-paths staged are equivalent in scope to
  # feat/fix/refactor — they touch framework/agents/skills/architecture-doc.
  # Without active workflow, they are the same engine-bypass loophole that
  # commit 82657bc rode through. WARN-only (consistent with Check 8 base).
  ENGINE_DOCS_TYPE=$(echo "$ENGINE_FIRST_LINE" | grep -oE '^(docs|chore)' || true)
  if [ -n "$ENGINE_DOCS_TYPE" ]; then
    TIER1_STAGED=$(git diff --cached --name-only 2>/dev/null \
      | grep -E '^(architecture-documentation/|framework/|agents/|skills/|workflows/|scripts/|orchestrators/|README\.md$|CLAUDE\.md$|AGENTS\.md$)' \
      | head -1 || true)
    if [ -n "$TIER1_STAGED" ]; then
      STATE_DIR_PATH="${FRAMEWORK_ROOT}/.workflow-state"
      DOCS_ENGINE_ACTIVE=0
      if [ -d "$STATE_DIR_PATH" ]; then
        if ls "$STATE_DIR_PATH"/*.json 2>/dev/null | grep -q .; then
          DOCS_ENGINE_ACTIVE=1
        fi
      fi
      if [ "$DOCS_ENGINE_ACTIVE" -eq 0 ]; then
        WARNINGS+=("ENGINE-USE (docs|chore): ${ENGINE_DOCS_TYPE}-commit with Tier-1-paths (${TIER1_STAGED}…) ohne aktiven Workflow in .workflow-state/. Start: workflow_engine.py --start solve --task <id>")
      fi
    fi
  fi
fi

# ---------- Check 9: RUNBOOK-DRIFT (WARN) — Cross-Session-Workflow Phase F ----------
#
# Heuristic check: when workflow.yaml or WORKFLOW.md is staged in any
# workflows/runbooks/<name>/ dir, run validate_runbook_consistency.py
# in --staged mode. Catches phase-section drift, missing derived_from, step-name
# keyword drift between yaml ↔ md. WARN-only (heuristic).

RUNBOOK_VALIDATOR="${FRAMEWORK_ROOT}/scripts/validate_runbook_consistency.py"
RUNBOOK_STAGED=$(git diff --cached --name-only -- 'workflows/runbooks/*/workflow.yaml' 'workflows/runbooks/*/WORKFLOW.md' 2>/dev/null || true)
if [ -n "$RUNBOOK_STAGED" ] && [ -f "$RUNBOOK_VALIDATOR" ]; then
  RUNBOOK_OUT=$(python3 "$RUNBOOK_VALIDATOR" --staged 2>&1) || true
  if echo "$RUNBOOK_OUT" | grep -q '^WARN:'; then
    # Render up to 5 warn lines (full count in summary)
    RUNBOOK_WARN_COUNT=$(echo "$RUNBOOK_OUT" | grep -c '^WARN:' || echo "0")
    RUNBOOK_RENDERED=$(echo "$RUNBOOK_OUT" | grep '^WARN:' | head -5 | sed 's/^/    /')
    WARNINGS+=("RUNBOOK-DRIFT: ${RUNBOOK_WARN_COUNT} drift signal(s) in staged runbook(s):"$'\n'"${RUNBOOK_RENDERED}")
  fi
fi

# ---------- Check 10: AGENT-SKILL-DRIFT (WARN) ----------
#
# When SKILL.md frontmatter or agents/*.md files are staged, run the
# agent-skill generator in --check mode. WARN on drift.

AGENT_SKILL_GEN="${FRAMEWORK_ROOT}/scripts/generate_agent_skill_map.py"
AGENT_SKILL_TRIGGER=$(git diff --cached --name-only -- 'skills/*/SKILL.md' 'agents/*.md' 'framework/agent-skill-map.md' 2>/dev/null || true)
if [ -n "$AGENT_SKILL_TRIGGER" ] && [ -f "$AGENT_SKILL_GEN" ]; then
  set +e
  AGENT_SKILL_OUT=$(python3 "$AGENT_SKILL_GEN" --check 2>&1)
  AGENT_SKILL_RET=$?
  set -e
  if [ "$AGENT_SKILL_RET" -ne 0 ]; then
    DRIFT_LINES=$(echo "$AGENT_SKILL_OUT" | head -8 | sed 's/^/    /')
    WARNINGS+=("AGENT-SKILL-DRIFT: agent-skill-map out of sync with skill frontmatter relevant_for:."$'\n'"${DRIFT_LINES}"$'\n'"    Run: python3 scripts/generate_agent_skill_map.py")
  fi
fi

# ---------- Check 11: SECRET-SCAN (WARN) — gitleaks-Wrapper ----------
#
# Run gitleaks against staged changes if the binary is available.
# WARN-only (don't block legitimate commits if gitleaks ist not installed
# yet). User can upgrade to BLOCK by editing this check.
#
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

# ---------- Check 12: SOURCE-VERIFICATION (WARN) ----------
#
# Filter: staged files under
#   - docs/reviews/board/*.md
#   - docs/reviews/council/**/*.md
#   - docs/specs/*.md
# that carry a YAML frontmatter with schema_version: 1 OR a per-finding
# evidence: block.
#
# Per file: call scripts/validate_evidence_pointers.py <file>.
# Exit 1 → WARN output, commit not blocked.
# Exit 2 → WARN parse-error.
# Legacy (schema_version: 0 or missing) → silent skip via grep filter.
#
# Severity: WARN-only initially. Promotion to BLOCK after a track record
# of <5% false-positive rate.
#
# Order: placed AFTER SECRET-SCAN — this check reads file contents, which
# is uncritical post-secret-scan.

VALIDATOR="${FRAMEWORK_ROOT}/scripts/validate_evidence_pointers.py"
if [ -f "$VALIDATOR" ]; then
  # Filter expanded to docs/reviews/{code,architecture,sectional,amendment}
  # so review files outside docs/reviews/board/ are also covered.
  STAGED_EVIDENCE_FILES=$(git diff --cached --name-only --diff-filter=AM 2>/dev/null \
    | grep -E '^docs/(reviews/(board|council|code|architecture|sectional|amendment)|specs)/' || true)

  if [ -n "$STAGED_EVIDENCE_FILES" ]; then
    EVIDENCE_WARNINGS=()
    # v1-only: legacy outputs (schema_version: 0 or missing) are not
    # opened — keeps the check fast and avoids false positives on a
    # corrupt prose `evidence:` block.
    FILTERED_FILES=()
    while IFS= read -r f; do
      [ -z "$f" ] && continue
      [ ! -f "$f" ] && continue
      # Filter is symmetric with the validator's parser: it accepts
      #   schema_version: 1                  (plain)
      #   schema_version: "1" / '1'          (quoted)
      #   schema_version: 1   (trailing ws)  (whitespace)
      #   schema_version: 1 # comment        (inline comment)
      # Rejects weiterhin: 0, 2, 11, 100, kommentierte Zeilen.
      if grep -qE "^schema_version:[[:space:]]*[\"']?1[\"']?[[:space:]]*(#.*)?$" "$f" 2>/dev/null; then
        FILTERED_FILES+=("$f")
      fi
    done <<< "$STAGED_EVIDENCE_FILES"

    if [ ${#FILTERED_FILES[@]} -gt 0 ]; then
      # CC-002 belt-and-suspenders: explicit --repo-root vermeidet die
      # parent-of-file Default-Falle (~100% false-positive vor Fix).
      # CC-018 fix: validator unterstuetzt nargs="+" Multi-File-Mode →
      # 1 Subprocess statt N → N-1 Python-cold-starts gespart (~30-50ms each).
      set +e
      VAL_OUT=$(python3 "$VALIDATOR" "${FILTERED_FILES[@]}" --repo-root "$FRAMEWORK_ROOT" 2>&1)
      VAL_RC=$?
      set -e
      if [ "$VAL_RC" -ne 0 ]; then
        # Multi-file-mode emits one block per file with its own header line.
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
