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
# Post hook-paradigm-shift (capability-first, hooks-minimal): 6 checks.
# 4 BLOCK + 2 WARN. Shared Git hook for repositories where installed;
# runtime prerequisites and actual Git invocation determine coverage.
# This does not establish equal host loading or enforcement.
#
# Each check runs once per commit: pre-commit (git commit) and
# pre-merge-commit (a merge commit that git merge creates) run checks 1, 3,
# 4, 5 and 6; commit-msg runs check 2 only, except for a merge commit in an
# install without the pre-merge-commit hook, where it runs every check.
#
# Checks (ordered; 1, 3 and 5 share one captured indexed candidate):
#   1. PLAN-VALIDATE        (BLOCK) — plan_engine.py --validate on the indexed
#                                     candidate tree must show 0 errors
#   2. CG-CONV              (BLOCK) — commit message format matches convention
#   3. SKILL-FM-VALIDATE    (BLOCK) — SKILL.md YAML/frontmatter subset
#   4. SECRET-SCAN          (WARN)  — gitleaks wrapper; WARN-only; skipped when
#                                     gitleaks is not installed. BLOCK under
#                                     range mode (see Range mode below).
#   5. SOURCE-VERIFICATION  (WARN)  — board/council reviews must cite source
#                                     files (line-numbered evidence pointers)
#                                     present in the indexed candidate, and
#                                     section cross-references in Markdown
#                                     that the commit touches (citing or
#                                     cited file changed) resolve in the
#                                     indexed candidate (WARN).
#   6. INSTRUCTION-UNIT-SIZE (BLOCK) — pre-commit / pre-merge-commit: each
#                                     staged instruction unit's staged blob is
#                                     within its byte cap, a staged unit is no
#                                     symlink, and a staged
#                                     framework/standing-block.md yields a
#                                     block within the hook budget
#                                     (consistency_check.py --check
#                                     instruction-units --staged). A commit
#                                     that removes framework/invariants.md
#                                     from the index while HEAD holds it
#                                     blocks (check 6 would stop).
# Check 6 runs only in a Forge framework checkout (the index, else HEAD,
# holds framework/invariants.md and scripts/consistency_check.py; the working
# tree is not read); in any other repository it does nothing and prints
# nothing.
#
# Range mode (CI): pre-commit.sh --range [--portable]
#   [--host-commits-format strict|exempt] [--default-ref REF] BASE HEAD
# replays each commit of BASE..HEAD in one throwaway linked worktree: working
# tree and index at the commit, HEAD at its first parent (a root commit: an
# unborn HEAD), MERGE_HEAD for a merge's further parents. Range resolution
# takes no degraded path and prints the rule it took: a given BASE that does
# not resolve exits 2 (force push or shallow history); a resolvable BASE gives
# BASE := merge-base(BASE, HEAD); a missing or all-zeros BASE takes the
# merge-base with REF (equal to HEAD: the branch adds no commits, exit 0);
# without a resolving REF the whole history (a repository's first push).
# A shallow clone or git older than 2.40 exits 2.
# It runs this script's pre-commit and commit-msg modes there with the commit's
# message, so the per-commit check list stays the one above. Exit 0 pass,
# 1 a check blocked, 2 usage or setup error. Under range mode no check prints
# SKIP and passes. --host-commits-format (only with --portable, default exempt):
# exempt runs no commit-msg mode for a commit whose committer email is
# noreply@github.com or whose author name ends in [bot], and prints EXEMPT;
# its secret scan runs. The replayed modes see three variables:
#   FORGE_HOOK_RANGE=1          SECRET-SCAN blocks (gitleaks missing, findings,
#                               or an error); commit-msg never takes the merge
#                               fallback and blocks an empty or `#` subject;
#                               no hook-link warnings; no marker file.
#   FORGE_HOOK_CHECKS=portable  (--portable; only with FORGE_HOOK_RANGE=1)
#                               pre-commit runs only check 4, commit-msg only
#                               check 2. Any other non-empty value exits 2.
#   FORGE_HOOK_GITLEAKS_DIR     (only with FORGE_HOOK_RANGE=1) the driver's
#                               trusted gitleaks rules: config.toml and
#                               gitleaksignore exported from merge-base(REF,
#                               HEAD), else BASE (none: default rules). The
#                               replayed commit's own rules are never read; a
#                               commit that changes them prints a WARN line.
#                               gitleaks runs with GIT_ATTR_SOURCE=<a tree
#                               holding only `* diff`> (attr-tree there).
# SOURCE-VERIFICATION stays WARN. Range-only whole-tree checks (not under
# --portable; HEAD's tree holds framework/invariants.md): RANGE_TREE_CHECKS
# below, run once at HEAD in the replay worktree with that tree's scripts.
# Replay fidelity: the per-commit checks run the trusted programs from
# FRAMEWORK_ROOT (in Forge CI the checkout at HEAD), and the plan engine reads
# its framework inputs (CLAUDE.md, AGENTS.md, framework/agent-autonomy.md,
# framework/task-schema.yaml) from there; every commit of a range is judged by
# HEAD's rules and programs.
#
# Dropped in the hook paradigm shift (was 8 checks):
#   TASK-SYNC, OBLIGATIONS, STALE-CLEANUP, PERSIST-GATE, ENGINE-USE,
#   RUNBOOK-DRIFT, AGENT-SKILL-DRIFT, PIEBALD-BUDGET — discipline replaces
#   observability WARN signals; Piebald budget loosened in same commit.

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

# ---------- Range mode driver (CI) ----------
#
# The whole-tree checks of range mode: one entry per run, script under scripts/
# then its arguments.
RANGE_TREE_CHECKS=(
  "generate_skill_wrappers.py --check"
  "consistency_check.py --check tier1-drift"
  "consistency_check.py --check tier1-multi-workflow-drift"
  "consistency_check.py --check enforcement-registry"
  "consistency_check.py --check instruction-units"
  "consistency_check.py --check dead-references"
  "validate_runbook_consistency.py"
)

range_die() {
  echo "range: $1" >&2
  exit 2
}

# range_mb A B — merge-base into RANGE_MB; return 1 for no shared history, any other failure exits 2.
range_mb() {
  local ret=0
  RANGE_MB="$("${G[@]}" merge-base "$1" "$2")" || ret=$?
  [ "$ret" -le 1 ] || range_die "git merge-base $1 $2 failed (exit $ret)"
  return "$ret"
}

# Remove the replay worktree and temp dirs on every exit path; keep the run's
# status, but a failed removal turns a pass (0) into a setup error (2).
range_cleanup() {
  local rc=$? fail=0
  if [ -n "${RANGE_WT:-}" ] && [ -e "$RANGE_WT/.git" ]; then
    if ! git --no-replace-objects -C "$RANGE_ROOT" worktree remove --force "$RANGE_WT" >/dev/null 2>&1; then
      echo "range: could not remove the replay worktree $RANGE_WT" >&2
      fail=1
    fi
  fi
  if [ -n "${RANGE_TMP:-}" ]; then rm -rf "$RANGE_TMP" || fail=1; fi
  if [ "$fail" -eq 1 ] && [ "$rc" -ne 1 ]; then rc=2; fi
  exit "$rc"
}

range_main() {
  local usage="usage: pre-commit.sh --range [--portable] [--host-commits-format strict|exempt] [--default-ref REF] BASE HEAD"
  local portable=0 default_ref="" host_format="" base="" head ref mb c short subject rc_pre rc_msg entry out ret
  local rule gv gmaj gmin orphan exempt changed rules
  local -a G=(git --no-replace-objects) commits=() parents=() blocked=() argv=() hook_env=()
  shift
  while [ $# -gt 0 ]; do
    case "$1" in
      --portable) portable=1; shift ;;
      --default-ref) [ $# -ge 2 ] || range_die "$usage"; default_ref="$2"; shift 2 ;;
      --host-commits-format)
        [ $# -ge 2 ] || range_die "$usage"
        case "$2" in strict|exempt) host_format="$2" ;; *) range_die "$usage" ;; esac
        shift 2 ;;
      -*) range_die "$usage" ;;
      *) break ;;
    esac
  done
  [ $# -eq 2 ] || range_die "$usage"
  if [ -n "$host_format" ] && [ "$portable" -eq 0 ]; then
    range_die "--host-commits-format needs --portable (Forge's own range is always strict)"
  fi
  [ "$portable" -eq 0 ] || host_format="${host_format:-exempt}"
  unset GIT_DIR GIT_WORK_TREE GIT_INDEX_FILE GIT_OBJECT_DIRECTORY \
    GIT_ALTERNATE_OBJECT_DIRECTORIES GIT_COMMON_DIR GIT_PREFIX
  export PYTHONDONTWRITEBYTECODE=1
  RANGE_ROOT="$("${G[@]}" rev-parse --show-toplevel 2>/dev/null)" || range_die "not inside a Git repository"
  cd "$RANGE_ROOT"
  # GIT_ATTR_SOURCE (git 2.40) keeps the replayed commit's .gitattributes away from the secret scan.
  gv="$(git --version)"; gv="${gv#git version }"
  IFS=. read -r gmaj gmin _ <<< "$gv"
  if ! [[ "$gmaj" =~ ^[0-9]+$ && "$gmin" =~ ^[0-9]+$ ]] || [ "$gmaj" -lt 2 ] || { [ "$gmaj" -eq 2 ] && [ "$gmin" -lt 40 ]; }; then
    range_die "git $gv is older than 2.40 (range mode needs GIT_ATTR_SOURCE)"
  fi
  if [ "$("${G[@]}" rev-parse --is-shallow-repository)" != false ]; then
    range_die "RANGE: shallow clone; range mode needs the full history (fetch-depth: 0)"
  fi
  if [ "$portable" -eq 0 ] && ! python3 -c 'import yaml' >/dev/null 2>&1; then
    range_die "PyYAML is not importable by python3; without it three checks pass silently (install PyYAML, or use --portable)"
  fi

  # Range resolution: no degraded path. A given BASE that does not resolve stops
  # the run; a missing BASE takes the default-ref merge-base, else the whole history.
  head="$("${G[@]}" rev-parse -q --verify "$2^{commit}")" || range_die "HEAD '$2' is not a commit"
  ref=""
  [ -z "$default_ref" ] || ref="$("${G[@]}" rev-parse -q --verify "$default_ref^{commit}")" || ref=""
  if [ -n "$1" ] && ! [[ "$1" =~ ^0+$ ]]; then
    c="$("${G[@]}" rev-parse -q --verify "$1^{commit}")" \
      || range_die "RANGE: BASE $1 not in this clone (force push or shallow history?)"
    if range_mb "$c" "$head"; then
      base="$RANGE_MB"; rule="RANGE: base from merge-base with BASE"
    else
      base=""; rule="RANGE: whole history (BASE shares no history with HEAD)"
    fi
  elif [ -n "$ref" ]; then
    if ! range_mb "$ref" "$head"; then
      rule="RANGE: whole history (no merge-base with $default_ref)"
    elif [ "$RANGE_MB" = "$head" ]; then
      echo "RANGE: branch adds no commits beyond $default_ref"
      echo "RANGE: $("${G[@]}" rev-parse --short "$head")..$("${G[@]}" rev-parse --short "$head") (0 commits)"
      exit 0
    else
      base="$RANGE_MB"; rule="RANGE: base from default-ref merge-base"
    fi
  else
    rule="RANGE: whole history (first push)"
  fi
  out="$("${G[@]}" rev-list --reverse --topo-order "${base:+$base..}$head")" || range_die "could not list the commits"
  [ -z "$out" ] || mapfile -t commits <<< "$out"
  if [ "${#commits[@]}" -eq 0 ] && [ "$base" != "$head" ]; then
    range_die "RANGE: commit list empty although ${base:-(root)}..$head is not"
  fi
  echo "$rule"
  echo "RANGE: $(if [ -n "$base" ]; then "${G[@]}" rev-parse --short "$base"; else echo '(root)'; fi)..$("${G[@]}" rev-parse --short "$head") (${#commits[@]} commits)"
  [ "${#commits[@]}" -gt 0 ] || exit 0

  RANGE_TMP="$(mktemp -d)" || range_die "could not create a temp dir"
  trap range_cleanup EXIT
  trap 'exit 2' INT TERM HUP
  mkdir "$RANGE_TMP/nohooks" "$RANGE_TMP/links" "$RANGE_TMP/gitleaks"
  ln -s "$(readlink -f "$0")" "$RANGE_TMP/links/pre-commit"
  ln -s "$(readlink -f "$0")" "$RANGE_TMP/links/commit-msg"
  # gitleaks rules from a trusted tree, never the replayed commit's: the default
  # branch's merge-base with HEAD when --default-ref resolves, else BASE.
  rules="$base"
  if [ -n "$ref" ] && range_mb "$ref" "$head"; then rules="$RANGE_MB"; fi
  if [ -n "$rules" ] && "${G[@]}" cat-file -e "$rules:.gitleaks.toml" 2>/dev/null; then
    "${G[@]}" cat-file blob "$rules:.gitleaks.toml" > "$RANGE_TMP/gitleaks/config.toml" \
      || range_die "could not export the trusted .gitleaks.toml"
    if awk '/^[[:space:]]*\[/ { ext = /^[[:space:]]*\[extend\][[:space:]]*(#.*)?$/ }
            ext && /^[[:space:]]*path[[:space:]]*=/ { found = 1 } END { exit !found }' "$RANGE_TMP/gitleaks/config.toml"; then
      range_die "RANGE: trusted .gitleaks.toml uses [extend] path (not supported in range mode)"
    fi
  else
    printf '[extend]\nuseDefault = true\n' > "$RANGE_TMP/gitleaks/config.toml"
  fi
  if [ -n "$rules" ] && "${G[@]}" cat-file -e "$rules:.gitleaksignore" 2>/dev/null; then
    "${G[@]}" cat-file blob "$rules:.gitleaksignore" > "$RANGE_TMP/gitleaks/gitleaksignore" \
      || range_die "could not export the trusted .gitleaksignore"
  fi
  # Attribute tree for the scan: `* diff` only, so no file (NUL bytes, `-diff`) is diffed as binary.
  out="$(printf '* diff\n' | "${G[@]}" hash-object -w --stdin)" || range_die "could not write the attribute blob"
  printf '100644 blob %s\t.gitattributes\n' "$out" | "${G[@]}" mktree > "$RANGE_TMP/gitleaks/attr-tree" \
    || range_die "could not write the attribute tree"
  RANGE_WT="$RANGE_TMP/wt"
  local -a W=("${G[@]}" -C "$RANGE_WT" -c core.hooksPath="$RANGE_TMP/nohooks")
  "${G[@]}" -c core.hooksPath="$RANGE_TMP/nohooks" worktree add -q --detach --no-checkout "$RANGE_WT" "$head" \
    >/dev/null 2>&1 || range_die "could not create the replay worktree"
  local merge_head
  merge_head="$("${W[@]}" rev-parse --git-path MERGE_HEAD)" || range_die "replay worktree unreadable"
  [[ "$merge_head" = /* ]] || merge_head="$RANGE_WT/$merge_head"
  hook_env=(env -u FORGE_HOOK_CHECKS -u GITLEAKS_CONFIG FORGE_HOOK_RANGE=1 FORGE_HOOK_GITLEAKS_DIR="$RANGE_TMP/gitleaks")
  [ "$portable" -eq 0 ] || hook_env+=(FORGE_HOOK_CHECKS=portable)
  orphan="forge-range-root-$$-$RANDOM"

  for c in "${commits[@]}"; do
    short="$("${G[@]}" rev-parse --short "$c")"
    subject="$("${G[@]}" log -1 --format=%s "$c")"
    echo ""
    echo "== $short $subject"
    read -ra parents <<< "$("${G[@]}" rev-list --parents -n 1 "$c")"
    "${W[@]}" checkout -q -f --detach "$c" >/dev/null 2>&1 || range_die "could not check out $short"
    "${W[@]}" clean -ffdxq || range_die "could not clean the replay worktree"
    if [ "${#parents[@]}" -lt 2 ]; then
      # Root commit: unborn HEAD, index and tree at C (no ref is created).
      "${W[@]}" checkout -q --orphan "$orphan" || range_die "could not replay the root commit $short"
      changed="$("${G[@]}" ls-tree --name-only "$c" -- .gitleaks.toml .gitleaksignore)"
    else
      "${W[@]}" reset -q --soft "${parents[1]}" || range_die "could not reset to the parent of $short"
      changed="$("${G[@]}" diff --name-only "${parents[1]}" "$c" -- .gitleaks.toml .gitleaksignore)"
    fi
    if [ -n "$changed" ]; then
      echo "WARN $short gitleaks rules changed (${changed//$'\n'/, }); this run applies the trusted rules"
    fi
    # gitleaks reads .gitleaksignore from the working tree; the index keeps the commit's copy.
    rm -rf "$RANGE_WT/.gitleaksignore"
    if [ "${#parents[@]}" -gt 2 ]; then printf '%s\n' "${parents[@]:2}" > "$merge_head"; fi
    "${G[@]}" log -1 --format=%B "$c" > "$RANGE_TMP/message" || range_die "could not read the message of $short"
    rc_pre=0; (cd "$RANGE_WT" && "${hook_env[@]}" "$RANGE_TMP/links/pre-commit") || rc_pre=$?
    exempt=""
    if [ "$host_format" = exempt ]; then
      if [ "$("${G[@]}" log -1 --format=%ce "$c")" = noreply@github.com ]; then
        exempt="committer noreply@github.com"
      elif [[ "$("${G[@]}" log -1 --format=%an "$c")" == *'[bot]' ]]; then
        exempt="author is a [bot]"
      fi
    fi
    rc_msg=0
    if [ -n "$exempt" ]; then
      echo "EXEMPT $short commit-message checks: host-generated commit ($exempt)"
    else
      (cd "$RANGE_WT" && "${hook_env[@]}" "$RANGE_TMP/links/commit-msg" "$RANGE_TMP/message") || rc_msg=$?
    fi
    rm -f "$merge_head"
    if [ "$rc_pre" -ne 0 ] || [ "$rc_msg" -ne 0 ]; then blocked+=("$short"); fi
  done

  if [ "$portable" -eq 0 ] && "${G[@]}" cat-file -e "$head:framework/invariants.md" 2>/dev/null; then
    echo ""
    echo "== whole tree at $("${G[@]}" rev-parse --short "$head")"
    "${W[@]}" checkout -q -f --detach "$head" >/dev/null 2>&1 || range_die "could not check out HEAD"
    "${W[@]}" clean -ffdxq || range_die "could not clean the replay worktree"
    rm -f "$merge_head"
    for entry in "${RANGE_TREE_CHECKS[@]}"; do
      read -ra argv <<< "$entry"
      if [ ! -f "$RANGE_WT/scripts/${argv[0]}" ]; then
        echo "range: WHOLE-TREE BLOCK — scripts/${argv[0]} missing at HEAD"
        blocked+=("whole-tree:$entry"); continue
      fi
      set +e
      out="$(cd "$RANGE_WT" && env -u FRAMEWORK_ROOT python3 "scripts/${argv[0]}" "${argv[@]:1}" 2>&1)"
      ret=$?
      set -e
      if [ "$ret" -eq 0 ] && [[ $'\n'"$out" != *$'\n'SKIP* ]]; then
        echo "range: WHOLE-TREE PASS — $entry"
      else
        echo "range: WHOLE-TREE BLOCK — $entry (exit $ret)"
        indent_head 40 "$out"
        blocked+=("whole-tree:$entry")
      fi
    done
  fi

  echo ""
  if [ "${#blocked[@]}" -gt 0 ]; then
    echo "range: blocked: ${blocked[*]}"
    echo "RANGE: BLOCKED"
    exit 1
  fi
  echo "range: no check blocked"
  echo "RANGE: PASS"
  exit 0
}

FRAMEWORK_ROOT="$(cd "$(dirname "$(readlink -f "$0")")/../../.." && pwd)"
PLAN_ENGINE="${FRAMEWORK_ROOT}/scripts/plan_engine.py"
if [ "$(basename "$0")" != commit-msg ] && [ "${1:-}" = --range ]; then
  range_main "$@"
fi
PROJECT_ROOT="$(git --no-replace-objects rev-parse --show-toplevel)"
cd "$PROJECT_ROOT"
COMMIT_MSG_HOOK="$(git rev-parse --git-path hooks/commit-msg)"
PRE_MERGE_HOOK="$(git rev-parse --git-path hooks/pre-merge-commit)"

BLOCK=0
WARNINGS=()
# The Forge-checkout predicate reads the index (HEAD: fallback), not the working
# tree, so a sparse or moved working copy keeps check 6 on. A commit
# that drops the marker from the index while HEAD holds it is refused in
# pre-commit mode (FORGE_MARKER_REMOVED), so it cannot switch both checks off.
FORGE_CHECKOUT=0
FORGE_MARKER_REMOVED=0
# Index and HEAD are read by path listing (ls-files, ls-tree), not cat-file:
# the hook's per-blob reads name object ids only.
forge_indexed() { [ -n "$(git --no-replace-objects ls-files --cached -- "$1" 2>/dev/null)" ]; }
forge_marker() {
  forge_indexed "$1" || [ -n "$(git --no-replace-objects ls-tree HEAD -- "$1" 2>/dev/null)" ]
}
if forge_marker framework/invariants.md && forge_marker scripts/consistency_check.py; then
  FORGE_CHECKOUT=1
  if ! forge_indexed framework/invariants.md; then FORGE_MARKER_REMOVED=1; fi
fi
# ---------- Hook-Mode-Detection ----------
#
# This script handles three hook events, selected by the $0 basename:
#   - pre-commit:       no args; checks 1, 3, 4 and 5
#   - pre-merge-commit: no args; runs exactly as pre-commit, for the merge
#                       commit git merge creates (a conflicted merge ends in
#                       git commit, which fires pre-commit instead)
#   - commit-msg:       $1 = path to the commit message file; check 2,
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

# Replayed by range mode (see the header): RANGE_RUN and PORTABLE select the
# range behaviour; FORGE_HOOK_CHECKS has no effect without FORGE_HOOK_RANGE=1.
RANGE_RUN=0
PORTABLE=0
if [ "${FORGE_HOOK_RANGE:-}" = 1 ]; then
  RANGE_RUN=1
  case "${FORGE_HOOK_CHECKS:-}" in
    '') ;;
    portable) PORTABLE=1 ;;
    *) echo "pre-commit: FORGE_HOOK_CHECKS='${FORGE_HOOK_CHECKS}' unknown (expected: portable)" >&2; exit 2 ;;
  esac
fi

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

    # Skip empty lines and comment-only messages (git aborts these anyway);
    # a stored message under range mode already exists, so it blocks.
    if [ "$RANGE_RUN" -eq 1 ] && { [ -z "$FIRST_LINE" ] || [[ "$FIRST_LINE" =~ ^# ]]; }; then
      echo "commit-msg: COMMIT-CONVENTION BLOCK — stored commit message has no subject line"
      BLOCK=1
    elif [ -z "$FIRST_LINE" ] || [[ "$FIRST_LINE" =~ ^# ]]; then
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

  # Range mode never takes the fallback: its driver runs pre-commit mode itself.
  if [ "$RANGE_RUN" -eq 1 ] || [ ! -e "$(git rev-parse --git-path MERGE_HEAD)" ] || [ -e "$PRE_MERGE_HOOK" ]; then
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

# Range mode --portable skips this block (body not re-indented: the heredoc).
if [ "$PORTABLE" -eq 0 ]; then
set +e
python3 -I - "$FRAMEWORK_ROOT" "$PROJECT_ROOT" <<'INDEXED_PY'
import contextlib
import importlib
import io
import json
import os
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
    range_run = os.environ.get('FORGE_HOOK_RANGE') == '1'
    for line in report.lines:
        # Range mode prints no passing SKIP: a tree without skills/ is not applicable.
        if range_run and line == 'SKILL-FM-VALIDATE SKIP — no skills/ candidate membership':
            line = 'SKILL-FM-VALIDATE N/A — no skills/ candidate membership'
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
fi

# ---------- Check 6: INSTRUCTION-UNIT-SIZE (BLOCK) ----------
#
# Forge checkout only. The trusted consistency_check.py measures the staged
# blob (what is committed, not the working tree) of each staged added,
# modified or type-changed instruction unit against its byte cap, refuses a
# staged unit that is a symlink (index mode 120000), and, when
# framework/standing-block.md is staged, refuses a block that
# user_scope.standing_block would not deliver. A check that cannot run
# (python3 missing, import or git read failure) BLOCKs with that reason. A
# commit that removes framework/invariants.md from the index while HEAD holds
# it BLOCKs here, before the checks would stop for every later commit.

if [ "$FORGE_CHECKOUT" -eq 1 ] && [ "$PORTABLE" -eq 0 ] && [ "$FORGE_MARKER_REMOVED" -eq 1 ]; then
  echo "pre-commit: INSTRUCTION-UNIT-SIZE BLOCK — Forge marker removed; check 6 would stop: framework/invariants.md is at HEAD but not in the index."
  BLOCK=1
fi
if [ "$FORGE_CHECKOUT" -eq 1 ] && [ "$PORTABLE" -eq 0 ]; then
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
    elif [ "$SIZE_RET" -eq 1 ] && grep -qE ': (an instruction unit is a symlink|standing block not delivered: )' <<< "$SIZE_OUT"; then
      echo "pre-commit: INSTRUCTION-UNIT-SIZE BLOCK — staged instruction text refused:"
      indent_head 50 "$SIZE_OUT"
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

if [ "$HOOK_MODE" != "commit-msg" ] && [ "$RANGE_RUN" -eq 0 ]; then
  echo "pre-commit: COMMIT-CONVENTION SKIP (authoritative validation runs in commit-msg hook)"
fi
if [ "$HOOK_MODE" != "commit-msg" ] && [ "$RANGE_RUN" -eq 0 ]; then
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

# Range mode: gitleaks missing, findings (exit 1, also a fatal gitleaks error)
# or any other failure BLOCKs; no marker file is written. Rules come from the
# driver's FORGE_HOOK_GITLEAKS_DIR (BASE's tree), never the replayed commit;
# attributes from the empty tree, so a committed `-diff` hides nothing.
if [ "$RANGE_RUN" -eq 1 ]; then
  GITLEAKS_DIR="${FORGE_HOOK_GITLEAKS_DIR:-}"
  if ! command -v gitleaks &>/dev/null; then
    echo "pre-commit: SECRET-SCAN BLOCK — gitleaks not installed (range mode requires it)"
    BLOCK=1
  elif [ -z "$GITLEAKS_DIR" ] || [ ! -f "$GITLEAKS_DIR/config.toml" ] || [ ! -s "$GITLEAKS_DIR/attr-tree" ]; then
    echo "pre-commit: SECRET-SCAN BLOCK — no trusted gitleaks config (FORGE_HOOK_GITLEAKS_DIR unset or empty)"
    BLOCK=1
  else
    GITLEAKS_ARGS=(protect --staged --no-banner --redact --verbose --config "$GITLEAKS_DIR/config.toml")
    GITLEAKS_HELP="$(gitleaks protect --help 2>&1 || true)"
    if [[ "$GITLEAKS_HELP" == *--no-color* ]]; then GITLEAKS_ARGS+=(--no-color); fi
    if [ -f "$GITLEAKS_DIR/gitleaksignore" ] && [[ "$GITLEAKS_HELP" == *--gitleaks-ignore-path* ]]; then
      GITLEAKS_ARGS+=(--gitleaks-ignore-path "$GITLEAKS_DIR/gitleaksignore")
    fi
    set +e
    GITLEAKS_OUT=$(GIT_ATTR_SOURCE="$(cat "$GITLEAKS_DIR/attr-tree")" gitleaks "${GITLEAKS_ARGS[@]}" 2>&1)
    GITLEAKS_RET=$?
    set -e
    if [ "$GITLEAKS_RET" -eq 0 ]; then
      echo "pre-commit: SECRET-SCAN PASS"
    elif [ "$GITLEAKS_RET" -eq 1 ]; then
      echo "pre-commit: SECRET-SCAN BLOCK — gitleaks reported finding(s) or a fatal error in staged content:"
      indent_head 60 "$GITLEAKS_OUT"
      BLOCK=1
    else
      echo "pre-commit: SECRET-SCAN BLOCK — gitleaks could not run (exit ${GITLEAKS_RET}):"
      indent_head 20 "$GITLEAKS_OUT"
      BLOCK=1
    fi
  fi
elif command -v gitleaks &>/dev/null; then
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
