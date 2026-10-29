# Evidence pointer schema — mandatory software-review capture

Step-loaded unit of `skills/_protocols/evidence-pointer-schema.md`. Read it before initiating a software review that
is meant to satisfy a mandatory result, readiness or completion boundary, and before producing a report for one.
Before consuming the reports, consolidating or writing the decision artifact, and before any fix-pass decision,
read `evidence-review-adoption.md` (§9.4–§9.6). Section numbers are protocol-wide: §1–§5 in `evidence-pointer-schema.md`, §6–§7 in
`evidence-pointer-integrations.md`, §8 in `evidence-author-claims.md`, §9–§9.3 in `evidence-review-capture.md`, §9.4–§9.6
in `evidence-review-adoption.md`.

## 9. Mandatory software-review adoption

This section is the operational authority for mandatory software-review capture, adoption and current-result
checks. Load it before producing or consuming a report for such a boundary. It does not apply merely because a
pointer is read, a historical report is inspected, or a standalone reasoning method is used.

An adoption is a **review receipt**: the reviewed input identity, Buddy's explicit decision, the selected reports
pinned by their bytes, and the evidence quotes resolved at adoption. Digests establish bytes, not authorship,
truthful execution, complete scope or correct interpretation; those remain Buddy's decision and C-VERIFY
obligations. Gate run receipts are defined in the engine's
[Run receipts](../../framework/workflow-engine-receipts.md#run-receipts).

### 9.1 Owner and operations

A review owner is exactly `{"workflow_id":"<exact ID>","step_id":"<exact ID>"}`; its step state holds one
active `review` record. Operations:

- `--review-capture STEP --id WORKFLOW`: read the capture request (§9.2) from JSON stdin; capture before dispatch.
- `--review-adopt STEP --id WORKFLOW --verdict PATH`: qualify and retain Buddy's decision artifact (§9.4).
- `--review-check STEP --id WORKFLOW --review-policy POLICY`: read-only current check (§9.5).

A successful capture prints exactly one JSON object, after the state is saved:

```json
{"schema_version":1,"owner":{"workflow_id":"<exact ID>","step_id":"<exact ID>"},
 "iteration":1,"review_run_id":"<captured run>","review_subject_digest":"<captured subject>"}
```

The dispatcher passes the run and subject identities verbatim to each producer. Initial capture requires the
selected owner step to be in progress; after it completes, its capture remains the review owner while the
workflow is live. Paused, aborted, completed or archived workflows cannot be mutated; read-only checks may
inspect them. No operation selects an ambient or latest owner; missing, conflicting or unreadable owner state
fails closed. These operations never complete or retry a step. A nested spec board receives its parent's exact
workflow/step pair and creates no competing capture.

### 9.2 Capture request and subject

```json
{"family":"spec","extent":"full","focus":[],"files":["docs/specs/<name>.md"],
 "code_diff":null,"slots":[{"slot":"implementer","role":"reviewer"}],"history":[]}
```

`family` is `spec|code`; `extent` is `full|scoped` (scoped needs non-empty `focus`). `files` lists the reviewed
regular files and explicit authority inputs; a missing file is an error. `slots` (nonempty) names every planned
producer with roles `reviewer|chief|verification|discourse`. `history` lists earlier reports or decisions given
as context, as exact `{path, sha256}` pairs. A code-family request adds
`"code_diff":{"base":"<full commit>","roots":["."],"exclude_files":[],"exclude_prefixes":[".workflow-state","docs/reviews"]}`:
the subject is the baseline-to-worktree candidate under the roots (committed, staged, unstaged and
non-ignored untracked changes, deletions as absent endpoints). Exclusions are literal project-relative paths
for declared output and state carriers; a reviewed input under an exclusion is refused.

The subject holds each file's raw-byte sha256 and Git mode and, for code, every changed path's before and after
endpoint. `review_subject_digest` is the SHA-256 of
`json.dumps(subject, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")`.
Capture creates a fresh `review_run_id` bound to the owner's iteration.

Repeating a capture on the same subject keeps the run and the iteration. An identical request changes nothing; a
changed request (for example an added slot) replaces it and moves any adoption into `adoption_history`, because
the earlier decision does not cover the new request. A changed subject is refused: run `--retry STEP --id WORKFLOW --reason …`, which
reopens the owner, moves the old record into retry history and advances the iteration, then capture again
before the applicable review. Do not list as reviewed input a file that the close itself rewrites (the task
YAML); the close-time check would report the subject noncurrent.

### 9.3 Reports

Buddy persists every return verbatim before use and records the returned actor, path and raw-byte digest.
Reports use the evidence-pointer format of §2 and §5 with an evidence quote under each finding; a report
without findings supports its conclusion with top-level evidence. Producers echo the capture in their
frontmatter:

```yaml
schema_version: 1
review_run_id: "<captured run>"
review_subject_digest: "<captured subject>"
review_slot: "<assigned slot>"
```

The run echo is the report's binding to the review it belongs to: a report that does not name the captured run,
or names a different run or subject, refuses adoption, whether or not the rest of its frontmatter parses. A
missing subject digest or slot is a diagnostic; a slot echo that names another slot refuses. `code-verification` keeps its command/output observations and terminal `VERDICT: PASS|FAIL|PARTIAL`.

The current reports are those of the final applicable review under the existing method: all producers of an
initial full review; the reproduction verifier and any reviewers code-board §4 adds for a scoped fix; the
adversary and implementer delta returns when spec-board §3a triggers; below that trigger, Buddy's bounded
fix-verification report in a slot with role `verification` (fresh scoped capture with the fix obligations in
`focus` and the original reports in `history`); complete-spec final returns after sectional fixes; the existing
verification of a coherence review. Earlier reports are history, never current, and their approval is not
inherited.
