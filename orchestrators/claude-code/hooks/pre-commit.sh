#!/usr/bin/env bash
set -euo pipefail

# pre-commit.sh — Git pre-commit / pre-merge-commit / commit-msg hook for
# forge consumers.
#
# Canonical location: orchestrators/claude-code/hooks/.
# Symlink into .git/hooks/pre-commit, .git/hooks/pre-merge-commit AND
# .git/hooks/commit-msg from any consumer repo. Idempotent installer:
# scripts/install-git-hooks.sh.
#
# Post hook-paradigm-shift (capability-first, hooks-minimal): 7 checks.
# 5 BLOCK + 2 WARN. Shared Git hook for repositories where installed;
# runtime prerequisites and actual Git invocation determine coverage.
# This does not establish equal host loading or enforcement.
#
# Each check runs once per commit: pre-commit (git commit) and
# pre-merge-commit (a merge commit that git merge creates) run checks 1, 3,
# 4, 5 and 6; commit-msg runs checks 2 and 7 only, except for a merge commit
# in an install without the pre-merge-commit hook, where it runs every check
# but 7 (a merge commit is exempt from 7).
#
# Checks (ordered; 1, 3 and 5 share one captured indexed candidate):
#   1. PLAN-VALIDATE        (BLOCK) — plan_engine.py --validate on the indexed
#                                     candidate tree must show 0 errors
#   2. CG-CONV              (BLOCK) — commit message format matches convention
#   3. SKILL-FM-VALIDATE    (BLOCK) — SKILL.md YAML/frontmatter subset
#   4. SECRET-SCAN          (WARN)  — gitleaks wrapper; WARN-only; skipped when
#                                     gitleaks is not installed.
#   5. SOURCE-VERIFICATION  (WARN)  — board/council reviews must cite source
#                                     files (line-numbered evidence pointers)
#                                     present in the indexed candidate, and
#                                     section cross-references in Markdown
#                                     that the commit touches (citing or
#                                     cited file changed) resolve in the
#                                     indexed candidate (WARN).
#   6. INSTRUCTION-UNIT-SIZE (BLOCK) — pre-commit / pre-merge-commit: each
#                                     staged instruction unit's staged blob is
#                                     within its byte cap (consistency_check.py
#                                     --check instruction-units --staged).
#   7. READ-PATH-RECORD     (BLOCK) — commit-msg: a change under the
#                                     instruction roots carries read-path
#                                     records in its message, each with the
#                                     four Read-path-* lines.
# Checks 6 and 7 run only in a Forge framework checkout (top level holds
# framework/invariants.md and scripts/consistency_check.py); in any other
# repository they do nothing and print nothing.
#
# Dropped in the hook paradigm shift (was 8 checks):
#   TASK-SYNC, OBLIGATIONS, STALE-CLEANUP, PERSIST-GATE, ENGINE-USE,
#   RUNBOOK-DRIFT, AGENT-SKILL-DRIFT, PIEBALD-BUDGET — discipline replaces
#   observability WARN signals; Piebald budget loosened in same commit.

FRAMEWORK_ROOT="$(cd "$(dirname "$(readlink -f "$0")")/../../.." && pwd)"
PLAN_ENGINE="${FRAMEWORK_ROOT}/scripts/plan_engine.py"
PROJECT_ROOT="$(git --no-replace-objects rev-parse --show-toplevel)"
cd "$PROJECT_ROOT"
COMMIT_MSG_HOOK="$(git rev-parse --git-path hooks/commit-msg)"
PRE_MERGE_HOOK="$(git rev-parse --git-path hooks/pre-merge-commit)"

BLOCK=0
WARNINGS=()
FORGE_CHECKOUT=0
if [ -f framework/invariants.md ] && [ -f scripts/consistency_check.py ]; then
  FORGE_CHECKOUT=1
fi
# Check 7's instruction roots (the one list).
READ_PATH_ROOTS='^(agents|framework|skills|workflows)/|^orchestrators/[^/]+/rules/|^(CLAUDE|AGENTS)\.md$'
READ_PATH_KEYS=(Read-path-reader Read-path-moment Read-path-text Read-path-carrier)

# indent_head N TEXT — first N lines of TEXT, indented by four spaces.
# Pipe-free on purpose: under `set -o pipefail`, `echo "$big" | head -N`
# lets head exit first, echo dies with SIGPIPE (141) and the hook aborts
# silently, turning a WARN check into an unexplained BLOCK.
indent_head() {
  local n="$1" i=0 line
  while [ "$i" -lt "$n" ] && IFS= read -r line; do
    printf '    %s\n' "$line"
    i=$((i + 1))
  done <<< "$2"
}

# ---------- Hook-Mode-Detection ----------
#
# This script handles three hook events, selected by the $0 basename:
#   - pre-commit:       no args; checks 1, 3, 4 and 5
#   - pre-merge-commit: no args; runs exactly as pre-commit, for the merge
#                       commit git merge creates (a conflicted merge ends in
#                       git commit, which fires pre-commit instead)
#   - commit-msg:       $1 = path to the commit message file; check 2 only,
#                       then exit (merge-commit fallback: see Check 2)
# Any other basename runs in pre-commit mode.
#
# Root cause: `git commit --amend -m "msg"` doesn't write the new message
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

# ---------- Check 2: CG-CONV — Commit-Convention Format (BLOCK in commit-msg mode) ----------
#
# Regex: type(scope): description [Task-NNN]
# Types: feat | fix | refactor | review | save | docs | chore
#        | solve | build | audit | research (workflow-engine commit-types)
# Scope optional, Task-Ref optional (entfaellt bei save/checkpoint)
#
# commit-msg mode receives fresh message path as $1 from git, runs only this
# check and exits: checks 1, 3, 4 and 5 already ran for the same commit in
# pre-commit or pre-merge-commit mode. Fallback: for a merge commit (MERGE_HEAD
# exists) in an install without the pre-merge-commit hook, it does not exit
# and runs every check, as such installs always did; a conflicted merge
# finished by git commit there runs the checks twice.
# pre-commit mode may see stale .git/COMMIT_EDITMSG and must never BLOCK on it;
# its part of check 2 follows the indexed block below.

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

  # ---------- Check 7: READ-PATH-RECORD (BLOCK, commit-msg mode) ----------
  #
  # A staged path (added, modified, deleted, either side of a rename) under
  # READ_PATH_ROOTS needs a read-path record in the message, and every record
  # must be complete and valid. A key line starts with a READ_PATH_KEYS key
  # and a colon at line start. A record starts at the first key line and ends
  # where a key line repeats a key the record already holds; that line opens
  # the next record. Other lines neither open nor end a record. Each record
  # holds all four keys, each with a valid value: 3+ non-space characters, not
  # starting with `<`; the carrier starts with (a)..(g), a..g then
  # space/comma/colon/end, or on-demand. Each bad record is named in the
  # refusal. Form only: whether the record is true is a reviewer's question.
  # A merge commit (MERGE_HEAD) is exempt: its commits passed their own check.
  if [ "$FORGE_CHECKOUT" -eq 1 ] && [ -n "${COMMIT_MSG_FILE:-}" ] \
     && [ ! -e "$(git rev-parse --git-path MERGE_HEAD)" ]; then
    RECORD_LIST="$(mktemp)"
    if ! git diff --cached --name-only --no-renames -z > "$RECORD_LIST"; then
      echo "commit-msg: READ-PATH-RECORD BLOCK — check could not run: staged paths not readable."
      BLOCK=1
    else
      RECORD_PATHS=()
      while IFS= read -r -d '' path; do
        if [[ "$path" =~ $READ_PATH_ROOTS ]]; then RECORD_PATHS+=("$path"); fi
      done < "$RECORD_LIST"
      RECORD_COUNT=0
      RECORD_BAD=()
      rec_seen=" "; rec_invalid=" "; rec_first=""
      # Close the current record; note it when a key is missing or invalid.
      read_path_close() {
        local k bad=""
        [ "$RECORD_COUNT" -gt 0 ] || return 0
        for k in "${READ_PATH_KEYS[@]}"; do
          if [[ "$rec_seen" != *" $k "* || "$rec_invalid" == *" $k "* ]]; then bad="${bad:+$bad }$k"; fi
        done
        [ -z "$bad" ] || RECORD_BAD+=("$RECORD_COUNT|$rec_first|$bad")
      }
      while IFS= read -r line || [ -n "$line" ]; do
        line="${line%$'\r'}"
        lkey=""
        for key in "${READ_PATH_KEYS[@]}"; do
          if [ "${line#"$key:"}" != "$line" ]; then lkey="$key"; break; fi
        done
        [ -n "$lkey" ] || continue
        if [ "$RECORD_COUNT" -eq 0 ] || [[ "$rec_seen" == *" $lkey "* ]]; then
          read_path_close
          RECORD_COUNT=$((RECORD_COUNT + 1))
          rec_seen=" "; rec_invalid=" "; rec_first="${line:0:80}"
        fi
        rec_seen+="$lkey "
        value="${line#"$lkey:"}"
        value="${value#"${value%%[![:space:]]*}"}"
        compact="${value//[[:space:]]/}"
        if [ "${#compact}" -lt 3 ] || [ "${value:0:1}" = "<" ]; then
          rec_invalid+="$lkey "
        elif [ "$lkey" = Read-path-carrier ] \
             && ! [[ "$value" =~ ^(\([a-g]\)|[a-g]([\ ,:]|$)|on-demand) ]]; then
          rec_invalid+="$lkey "
        fi
      done < "$COMMIT_MSG_FILE"
      read_path_close
      if [ "${#RECORD_PATHS[@]}" -gt 0 ] && [ "$RECORD_COUNT" -eq 0 ]; then
        echo "commit-msg: READ-PATH-RECORD BLOCK — instruction text changed without a read-path record (missing or invalid: ${READ_PATH_KEYS[*]}):"
      elif [ "${#RECORD_PATHS[@]}" -gt 0 ] && [ "${#RECORD_BAD[@]}" -gt 0 ]; then
        echo "commit-msg: READ-PATH-RECORD BLOCK — instruction text changed with an incomplete or invalid read-path record:"
        for entry in "${RECORD_BAD[@]}"; do
          n="${entry%%|*}"; rest="${entry#*|}"
          echo "    record $n of $RECORD_COUNT (${rest%|*}): missing or invalid: ${rest##*|}"
        done
      fi
      if [ "${#RECORD_PATHS[@]}" -gt 0 ] \
         && { [ "$RECORD_COUNT" -eq 0 ] || [ "${#RECORD_BAD[@]}" -gt 0 ]; }; then
        for path in "${RECORD_PATHS[@]:0:5}"; do echo "    $path"; done
        [ "${#RECORD_PATHS[@]}" -le 5 ] || echo "    … and $(( ${#RECORD_PATHS[@]} - 5 )) more"
        echo "  Add to the commit message, one record per changed rule:"
        echo "    Read-path-reader: <who acts on the rule>"
        echo "    Read-path-moment: <the moment it acts>"
        echo "    Read-path-text: <the text in front of it at that moment>"
        echo "    Read-path-carrier: <(a)..(g) or on-demand, then the carrier>"
        echo "  Walk the reader's path from its session start or dispatch to the moment it acts: skills/_protocols/instruction-form.md §Read-path record."
        BLOCK=1
      elif [ "${#RECORD_PATHS[@]}" -gt 0 ]; then
        echo "commit-msg: READ-PATH-RECORD PASS"
      fi
    fi
    rm -f "$RECORD_LIST"
  fi

  if [ ! -e "$(git rev-parse --git-path MERGE_HEAD)" ] || [ -e "$PRE_MERGE_HOOK" ]; then
    if [ "$BLOCK" -eq 1 ]; then
      echo ""
      echo "pre-commit: BLOCKED — fix errors above before committing."
      exit 1
    fi
    exit 0
  fi
  # Merge-commit fallback: continue with checks 1, 3, 4 and 5 below.
fi

# ---------- Checks 1, 3, 5: indexed candidate (one capture) ----------
#
# 1. PLAN-VALIDATE (BLOCK): trusted plan_engine.py --validate against the
#    materialized candidate tree must show 0 errors.
# 3. SKILL-FM-VALIDATE (BLOCK): staged skills/**/SKILL.md frontmatter.
# 5. SOURCE-VERIFICATION (WARN): changed candidate reports under
#    docs/reviews/{board,council,code,architecture,sectional,amendment}/ and
#    docs/specs/ with schema_version: 1 cite pointers that resolve in the
#    candidate tree; section cross-references in live Markdown whose citing
#    or cited file the commit changes resolve in the candidate tree.
#
# All three read one captured indexed candidate and share the final
# currentness comparison before publication. Plan/evidence readers see a
# private materialized copy of the candidate (scripts/indexed_related.py),
# never the working tree; output names that copy <candidate>.
# PLAN-VALIDATE pass/block parse (unchanged, inside the driver): pinned
# '^Summary: 0 errors\b|^CLEAN:' — a greedy '.*0 errors' would fail open on
# multi-digit counts such as "Summary: 100 errors".

set +e
python3 -I - "$FRAMEWORK_ROOT" "$PROJECT_ROOT" <<'INDEXED_PY'
import contextlib
import importlib
import io
import json
import sys
from pathlib import Path

framework = Path(sys.argv[1])
trusted = framework / 'scripts'
repo = Path(sys.argv[2])
sys.path.insert(0, str(trusted))
skill = related = None
skill_missing = not (trusted / 'skill_fm_validate.py').is_file()
driver_missing = not (trusted / 'indexed_standalone.py').is_file()
related_missing = not (trusted / 'indexed_related.py').is_file()
plan_present = (trusted / 'plan_engine.py').is_file()
evidence_present = (trusted / 'validate_evidence_pointers.py').is_file()
dependency_missing = False
buffer = io.StringIO()
try:
    with contextlib.redirect_stdout(buffer), contextlib.redirect_stderr(buffer):
        if not skill_missing:
            skill = importlib.import_module('skill_fm_validate')
            dependency_missing = skill.yaml is None
        if driver_missing or related_missing:
            raise FileNotFoundError('trusted indexed driver missing')
        driver = importlib.import_module('indexed_standalone')
        related = importlib.import_module('indexed_related')
        report = driver.run(repo, skill, related, framework)
    for line in report.lines:
        print(line)
    print('INDEXED-STANDALONE ' + report.record)
    sys.exit(1 if report.blocking else 0)
except Exception as exc:
    # Failed startup must not publish captured incidental content diagnostics.
    missing = driver_missing or related_missing
    if skill_missing or missing:
        status, reason = 'SKIP', 'availability: trusted validator program missing'
    elif dependency_missing:
        status, reason = 'SKIP', 'dependency: PyYAML missing'
    else:
        status, reason = 'BLOCK', 'input unavailable: shared indexed driver failure'
    detail = 'input unavailable: ' + str(exc)
    # A present plan engine cannot be established without the indexed driver.
    plan_status = 'BLOCK' if plan_present else 'SKIP'
    evidence_status = 'WARN/input unavailable' if evidence_present else 'SKIP'
    payload = dict(version=1, mode='indexed', input_available=False, consumer=str(repo),
                   index=None, git_dir=None, input_identity=None, detail=detail,
                   skill_status=status, skill_detail=reason, checked_skills=[], skipped_paths=[],
                   skill_skipped_paths=[], defect_paths=[], definitive=[], worktree_fallback_paths=[],
                   plan_status=plan_status, plan_detail=detail, evidence_status=evidence_status,
                   evidence_detail=detail, checked_reports=[], unresolved_links=[], gitlink_paths=[],
                   related_file_mode='not-evaluated', fully_indexed_related_files=False,
                   limitations='No related-file or standalone result was established; '
                   'currentness is not transactional with a later commit.')
    if plan_present:
        print('pre-commit: PLAN-VALIDATE BLOCK — ' + detail)
    else:
        print('pre-commit: PLAN-VALIDATE SKIP — plan_engine.py not found (graceful degradation)')
    print('SKILL-FM-VALIDATE ' + status + ' — ' + reason)
    if evidence_present:
        print('pre-commit: WARNING — SOURCE-VERIFICATION WARN/input unavailable — ' + detail)
    print('INDEXED-STANDALONE ' + json.dumps(payload, ensure_ascii=True, sort_keys=True))
    sys.exit(1 if 'BLOCK' in (status, plan_status) else 0)
INDEXED_PY
INDEXED_RET=$?
set -e
if [ "$INDEXED_RET" -ne 0 ]; then
  if [ "$INDEXED_RET" -ne 1 ]; then
    if [ -f "$PLAN_ENGINE" ]; then
      echo "pre-commit: PLAN-VALIDATE BLOCK — indexed interpreter input unavailable"
    else
      echo "pre-commit: PLAN-VALIDATE SKIP — plan_engine.py not found (graceful degradation)"
    fi
    echo "pre-commit: SKILL-FM-VALIDATE BLOCK — indexed interpreter input unavailable"
    if [ -f "${FRAMEWORK_ROOT}/scripts/validate_evidence_pointers.py" ]; then
      echo "pre-commit: WARNING — SOURCE-VERIFICATION WARN/input unavailable — indexed interpreter failed"
    fi
  fi
  BLOCK=1
fi

# ---------- Check 6: INSTRUCTION-UNIT-SIZE (BLOCK) ----------
#
# Forge checkout only. The trusted consistency_check.py measures the staged
# blob (what is committed, not the working tree) of each staged added or
# modified instruction unit against its byte cap. A check that cannot run
# (python3 missing, import or git read failure) BLOCKs with that reason.

if [ "$FORGE_CHECKOUT" -eq 1 ]; then
  if ! command -v python3 >/dev/null 2>&1; then
    echo "pre-commit: INSTRUCTION-UNIT-SIZE BLOCK — check could not run: python3 not found"
    BLOCK=1
  else
    set +e
    SIZE_OUT=$(python3 "${FRAMEWORK_ROOT}/scripts/consistency_check.py" --check instruction-units --staged 2>&1)
    SIZE_RET=$?
    set -e
    if [ "$SIZE_RET" -eq 0 ]; then
      echo "pre-commit: INSTRUCTION-UNIT-SIZE PASS"
    elif [ "$SIZE_RET" -eq 1 ] && grep -qE ': [0-9]+ bytes > [0-9]+ \(' <<< "$SIZE_OUT"; then
      echo "pre-commit: INSTRUCTION-UNIT-SIZE BLOCK — staged instruction text over its byte cap:"
      indent_head 50 "$SIZE_OUT"
      echo "  Split at a step boundary and give the moved part a carrier at that step: skills/_protocols/instruction-form.md §Writing rule."
      BLOCK=1
    else
      # Exit 1 without a violation line is an uncaught error (import failure), not a cap.
      echo "pre-commit: INSTRUCTION-UNIT-SIZE BLOCK — check could not run: ${SIZE_OUT%%$'\n'*} (consistency_check.py exit ${SIZE_RET})"
      indent_head 5 "$SIZE_OUT"
      BLOCK=1
    fi
  fi
fi

# ---------- Check 2 in pre-commit mode: no BLOCK ----------
#
# commit-msg mode ran check 2 above (and reaches this point only in the
# merge-commit fallback). Here the message may be stale, so check 2 only
# reports SKIP and warns when a hook link this contract relies on is missing.

if [ "$HOOK_MODE" != "commit-msg" ]; then
  echo "pre-commit: COMMIT-CONVENTION SKIP (authoritative validation runs in commit-msg hook)"
  if [ ! -e "$COMMIT_MSG_HOOK" ]; then
    WARNINGS+=("COMMIT-CONVENTION: commit-msg hook missing. Install via: bash ${FRAMEWORK_ROOT}/scripts/install-git-hooks.sh ${PROJECT_ROOT}")
  fi
  if [ ! -e "$PRE_MERGE_HOOK" ]; then
    WARNINGS+=("pre-merge-commit hook missing (merge commits fall back to checks in commit-msg). Install via: bash ${FRAMEWORK_ROOT}/scripts/install-git-hooks.sh ${PROJECT_ROOT}")
  fi
fi

# ---------- Check 3: SKILL-FM-VALIDATE (BLOCK) ----------
#
# Validates staged skills/**/SKILL.md frontmatter (YAML subset).
# SKIP: consumer repos without skills/, or PyYAML/skip inside script.
# Evaluated in the indexed candidate block at the Check 1 position.

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
    LEAKS_RENDERED=$(indent_head 10 "$GITLEAKS_OUT")
    WARNINGS+=("SECRET-SCAN: gitleaks reported finding(s) in staged content:"$'\n'"${LEAKS_RENDERED}"$'\n'"    Review carefully before pushing. False positive? Add to .gitleaksignore.")
  fi
else
  # Only warn about missing gitleaks once per session via marker (avoid noise)
  GITLEAKS_MARK="$(git rev-parse --git-path forge/gitleaks-missing.marker)"
  mkdir -p "$(dirname "$GITLEAKS_MARK")" 2>/dev/null || true
  if [ ! -f "$GITLEAKS_MARK" ] || [ "$(find "$GITLEAKS_MARK" -mtime +0 2>/dev/null)" ]; then
    WARNINGS+=("SECRET-SCAN: gitleaks not installed — secret-pattern check skipped. Install via 'brew install gitleaks' or github.com/gitleaks/gitleaks/releases. Suppressing this warning for 24h.")
    touch "$GITLEAKS_MARK" 2>/dev/null || true
  fi
fi

# ---------- Check 5: SOURCE-VERIFICATION (WARN) ----------
#
# Changed candidate reports with schema_version: 1 are validated against
# the materialized candidate tree in the indexed block at the Check 1
# position (legacy schema 0 / missing stays a silent skip), and so are the
# section cross-references in Markdown that the commit touches (citing or
# cited file changed). WARN-only.

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
