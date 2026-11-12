# Code review board — review package

Step-loaded unit of `skills/code_review_board/SKILL.md`. Read it before a change that a board review will review starts (to
record BASE; a same-turn DIRECT check is not one: `SKILL.md` §Same-turn DIRECT check), before dispatching any review seat on it, a re-review after a fix pass included, before a fix after a review in which every seat passed, and when persisting a
seat's return or writing the verdict (the Range line). Section numbers are skill-wide: §1 and §6–§10 in `SKILL.md` (§1.0a in `live-path.md`),
§2–§3 in `brief-and-team.md`, §4–§4a in `checklist-and-dispatch.md`, §5–§5a in `verdict.md`, §11 in
`review-package.md`.

## 11. Review package

The package is one file holding the change under review for the range BASE..HEAD: its commits, its stat and its diff
with context. The review seat reads the change there instead of deriving its own view, and the review record names
the range, so a fix pass after the review has a range of its own. The cost it prevents: a seat that reviews a working
tree with other writers' or host files in it, or without its untracked files; a record that cannot say which bytes it
covered; and fix-pass bytes that are committed with no review range.

### BASE

The package and the review capture cover one checkout. From the build workflow's Prepare phase on, the spec and the
code of one delivery are written on one branch in one checkout; a spec edited in another worktree would have to be
merged in before the review can start.

Before the change starts, record `BASE: <sha>` from `git rev-parse HEAD` in the checkout where the change is made: as
the first line of the dispatch file (`skills/_protocols/mca-dispatch.md` §The dispatch) when main-code-agent
implements, otherwise at the top of the work unit's record, with the full sha. In a checkout other writers share, the
record also lists the paths the change touches and keeps the list current: step 1 reads PATHS there. When no BASE was
recorded, BASE is the parent of the change's first commit, or `git rev-parse HEAD` at packaging time when the change
has no commit yet.

### Building the package

Run in the checkout where the change is made, once the implementer's report or Buddy's own change is in. Run steps 2–4
as one bash invocation: step 2 sets `GIT_INDEX_FILE` and shell variables, and a later call without them would rewrite
the checkout's own index.

1. **PATHS**, the paths the change touches:
   - Only this change writes in the checkout (a staging copy, a worktree of its own): every path that
     `git diff --name-only "$BASE"` and `git status --porcelain -uall --no-renames | cut -c4-` print.
   - Another writer or the host also writes in it (a shared checkout): the files that the report, the transfer list or
     Buddy's record names as changed.
2. **HEAD_SHA:**
   - `git status --porcelain -uall -- $PATHS` prints nothing: `HEAD_SHA=$(git rev-parse HEAD)`.
   - It prints paths: a snapshot commit. It changes no ref, not the checkout's index and not the working tree:
     ```sh
     export GIT_INDEX_FILE="$(mktemp -u)"
     git read-tree HEAD
     git add -A -- $PATHS || exit 1   # a PATHS entry that matches no file: correct PATHS
     HEAD_SHA=$(git commit-tree "$(git write-tree)" -p "$(git rev-parse HEAD)" -m "review snapshot")
     rm -f "$GIT_INDEX_FILE"; unset GIT_INDEX_FILE
     ```
3. **Range check:** `git diff --stat "$BASE" "$HEAD_SHA" -- $PATHS` prints at least one file, and the ancestry check
   exits 0:
   - BASE is the previous review's snapshot (its Range line says `snapshot`):
     `git merge-base --is-ancestor "$BASE^" "$HEAD_SHA"`, since nothing descends from a snapshot;
   - otherwise: `git merge-base --is-ancestor "$BASE" "$HEAD_SHA"`.

   A failed check means BASE comes from another history or PATHS misses the change: correct them before any dispatch.
4. **Write** the file into the record directory (`$REC`, relative to the checkout root):
   ```sh
   OUT="$REC/review-${BASE:0:7}..${HEAD_SHA:0:7}.diff"
   {
     echo "# Review package: $BASE..$HEAD_SHA"; echo
     echo "## Commits"; git log --oneline "$BASE..$HEAD_SHA" -- $PATHS; echo
     echo "## Files changed"; git diff --stat "$BASE" "$HEAD_SHA" -- $PATHS; echo
     echo "## Other changed paths in the checkout"
     { git diff --name-only "$BASE" "$HEAD_SHA"; git status --porcelain -uall --no-renames | cut -c4-; } \
       | sort -u | grep -vxF -f <(printf '%s\n' $PATHS "$OUT"); echo
     echo "## Diff"; git diff -U10 "$BASE" "$HEAD_SHA" -- $PATHS
   } > "$OUT"
   ```
   `## Commits` lists each commit in the range that touches PATHS; such a commit can hold more than the range's diff.
5. **Other paths:** each line under `## Other changed paths in the checkout` is a path the host writes on its own
   (such as `.claude/skills/synced/`), a path a named other writer changed, or a file of the work unit's own records
   under `$REC`. Any other line joins PATHS, and steps 2–4 run again.

### What each seat receives

- **light** (`code-verification`, the per-task gate): the package path; the implementation brief's path and the
  report's path (`skills/_protocols/mca-dispatch.md` §The return), or Buddy's record for a change Buddy wrote; and the
  binding constraints copied verbatim from the brief (for a change Buddy wrote, from the task file and its spec): the
  `## Approved acceptance (read-only)` block, and the exact values, formats and stated relationships set for this
  change.
- **L1 and L2:** the package is the diff their dispatch carries (§4 item 4, §4a), beside the review brief (§2) and
  without the report: cold-start seats receive no implementer framing.
- **Re-review after a fix pass:** the fix range. BASE is the HEAD_SHA the previous persisted review names; PATHS adds
  every path the fix touches; HEAD_SHA and the file follow steps 2–5.
  - The reproduction re-run (`code-verification`) receives the fix package, the findings under verification copied
    from the previous persisted review, the implementation brief, and the report with the fix pass appended.
  - The other re-verify seats (§4 re-verify table, §5a) take the fix package as their diff under their own cold-start
    rules.

### What a re-review decides

Every fix pass ends with a re-review of its fix range, at the depth the §4 re-verify table selects, except a small
fix after a passing review (below). It covers the
findings under verification and the fix package's diff; Buddy sorts what the seats report:
- **A finding under verification** is addressed when its outcome no longer occurs at the fix package's HEAD, shown by
  its reproduction or by the read at its location; otherwise it stays open.
- **New breakage:** a reported outcome that occurs at the fix package's HEAD and not at the fix range's BASE: the fix
  caused it, wherever it shows. Two such reports are deferred instead: one with a ruling recorded on the same location
  and claim, and one that also occurs at the change's BASE (the `BASE` line of the change's first dispatch file) where the fix brief asked
  for that behaviour to be restored (a revert). New breakage is verified at the fix package's HEAD (`skills/_protocols/finding-verification.md`, its own `-verified-<head7>` record) and, when it holds,
  is an open finding of the loop.
- **Deferred:** every other report, listed under `## Deferred` in the review decision with the seat's text. It enters
  no fix pass of this loop. When the loop ends, a deferred item with a ruling recorded on the same location and claim
  keeps it; the others are verified and dispositioned once under §5, its rule on pre-existing defects included. One that
  §5 makes fix-now goes to the caller with the verdict as a scope decision, not into another round.

### Small fix after a passing review

Decide this before the §4 re-verify table. When every seat of the last review returned PASS or PASS_WITH_RISKS and
none of the findings left over is CRITICAL, HIGH or a dangerous invariant falsification
(`skills/_protocols/finding-verification.md` step 4), a fix of those findings, `fix-now` ones included, is evidenced by
the tests that failed before it, run until they are green, plus L0 on the touched files. It gets no re-verify, no new
review round and no broad run. Where no test failed before it (a wording, comment or log fix), the L0 checks are its
evidence; no test is written only to record it. Record the run (command, red before, green after) in the review decision under `## After the review`. The §4
re-verify table applies instead when the fix is not line-local (the §4 table's line-local row), changes a test's expected
value or an oracle, or touches a safety floor (§1).

### Persisting a seat's return

When Buddy persists a seat's return, before the Chief or Buddy's consolidation reads it:

1. In the root of the package's checkout, run
   `python3 "$FRAMEWORK_DIR/scripts/validate_evidence_pointers.py" --strict --repo-root . <return file>` (without
   `--strict` when the review has no capture under `skills/_protocols/evidence-review-capture.md` §9).
2. Exit 0: the return is ready for consolidation; with `--strict`, the validator reads evidence as the adoption does,
   `yaml` fences included, and keeps every check it has without `--strict`. A `WARN` line alone does not send the seat
   back.
3. Any other exit: send the seat back with the validator's output verbatim and the instruction to correct only what
   it names. Persist the corrected return verbatim beside the first, as the slot's current return, and run step 1 on it. A seat that cannot answer
   is replaced by a fresh cold-start seat in the same slot: adoption needs a passing return for every captured slot
   (`skills/_protocols/evidence-review-adoption.md` §9.4).

### The record

- Buddy writes the persisted review's range on the line after its title:
  `Range: <BASE>..<HEAD_SHA> (<package file>; commit | snapshot)`. The verdict names the range of each review it
  adopts.
- The package file stays in the record directory and is committed with the work unit's records. A snapshot commit has
  no ref, and git may prune it; the package file is the lasting record of what the seat saw.
- The package complements run receipts (`framework/workflow-engine-receipts.md` §Run receipts): a receipt records
  which check ran on which input bytes, the package and its Range line record which change a review seat saw.

## Source

Superpowers (MIT License, © 2025 Jesse Vincent); Forge's register of adopted methods.
