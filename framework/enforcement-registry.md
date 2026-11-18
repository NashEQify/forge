# Enforcement Registry

Single source of truth for **what actually enforces what** in forge.
The framework makes enforcement claims throughout its docs ("X BLOCKs",
"Y guards Z"). After the hook paradigm shift removed the tool-event hook
layer, several of those claims described mechanisms that no longer have
a runnable artifact. This registry exists so every enforcement claim can
be checked against reality: each live mechanism carries a **class tag**
and a **resolvable artifact pointer**.

Discipline rule (enforcement-honesty): **no doc may state an enforcement
verb (`BLOCKs`, `guards`, `re-runs`, `enforces`) for a mechanism that is
not in the Live table below.** The rule is discipline;
`consistency_check` Check 11 validates this registry's own integrity.

## Class tags

Every enforcement reference carries exactly one:

- **`[STRUCTURAL]`** — the agent topology or tool grant makes the
  violation *impossible*, not merely discouraged. Nothing to remember;
  the wrong action cannot be taken. Example: a context-isolated
  reviewer cannot see sibling reviews; `disallowedTools` removes Write
  from a read-only persona.
- **`[GATE]`** — a mechanical boundary check that runs *independently of
  whether Buddy chooses to run it*. Today this is exactly the git
  pre-commit/pre-merge-commit/commit-msg hook and configured SessionStart hooks. They run
  only when installed/configured and their invocation conditions match.
  Severity is **BLOCK** (halts the action) or **WARN** (mechanical detection,
  advisory — does not halt); boot injectors supply context on their configured
  entrypoints. Shared methodology does not establish equal host loading,
  execution or enforcement. Check each artifact's actual applicability.
- **`[WORKFLOW]`** — a workflow step tracked by `workflow_engine.py`.
  The engine evaluates `completion` + `on_fail` **only when Buddy drives
  `--complete`** — it is a discipline-run state-tracker, not an
  autonomous runtime. So a workflow gate has teeth only inside an
  engine-driven run; it is stronger than bare discipline but weaker than
  a `[GATE]`.
- **`[DISCIPLINE]`** — a rule Buddy or an agent applies by reading it.
  No mechanical detection, no block. This is the honest class for most
  of the framework's "rules": their force is the agent following them.

The honest test for a claim: *if no human and no agent were watching,
would the mechanism still catch the violation?* `[STRUCTURAL]` and
`[GATE]` pass; `[WORKFLOW]` passes only mid-run; `[DISCIPLINE]` does not.

## Live mechanisms

Codex reader-role sandbox defaults are configuration, not proof of the
effective runtime policy. Parent permission overrides may replace them.
Claim filesystem write protection only after a harmless write-denial probe
through every exposed write channel in the actual launch mode. This does
not imply network isolation or protection against privileged remote actions.

Single-path `Artifact` pointers (one backticked path per row, optional
`§section` suffix) so Check 11 can resolve them.

| Mechanism | Class | Severity | Artifact | Enforces |
|---|---|---|---|---|
| PLAN-VALIDATE | `[GATE]` | BLOCK | `orchestrators/claude-code/hooks/pre-commit.sh` | `plan_engine.py --validate` reports 0 errors for the captured indexed candidate tree before commit (§Indexed related-file input) |
| CG-CONV | `[GATE]` | BLOCK | `orchestrators/claude-code/hooks/pre-commit.sh` | Conventional-Commits message format, checked in commit-msg; commit-msg runs no other check, the others run once in pre-commit or, for a merge commit that `git merge` creates, pre-merge-commit. A repository without the `pre-merge-commit` link runs them in commit-msg for a merge, as before |
| SKILL-FM-VALIDATE | `[GATE]` | BLOCK | `orchestrators/claude-code/hooks/pre-commit.sh` | Frontmatter subset on applicable changed candidate `SKILL.md` entries, using captured indexed content and candidate membership under §Indexed standalone input contract. |
| SECRET-SCAN | `[GATE]` | WARN | `orchestrators/claude-code/hooks/pre-commit.sh` | gitleaks over staged content (skipped if gitleaks absent) |
| SOURCE-VERIFICATION | `[GATE]` | WARN | `orchestrators/claude-code/hooks/pre-commit.sh` | Changed board/council/spec reports with `schema_version: 1` cite evidence pointers that resolve in the captured indexed candidate tree, and section cross-references in live Markdown that the commit touches resolve in the same tree (§Indexed related-file input); WARN-only |
| buddy-boot-inject | `[GATE]` | on the plugin's SessionStart | `orchestrators/claude-code/hooks/buddy-boot-inject.sh` | The plugin's SessionStart hook (`orchestrators/claude-code/plugin-hooks.json`, `--plugin` mode) injects boot: under a project's activation line or the user switch `buddy: every-session`; a machine mode without argument serves the eval harnesses |
| cross-session resume | `[DISCIPLINE]` | — | `agents/buddy/boot-software.md` step 6 (RESUME) | Buddy runs `plan_engine.py --boot` (open tasks) at boot and `workflow_engine.py --boot-context` (active workflows + `current_step`) on demand; the engine state file `.workflow-state/<id>.json` is the process-position SoT. NOT harness-enforced — the ADR-007 amendment keeps resume `[DISCIPLINE]`, not a hook `[GATE]` |
| brief-architect read-only | `[STRUCTURAL]` | — | `agents/brief-architect.md` | `disallowedTools` removes Edit/Write/NotebookEdit/ExitPlanMode/Agent (no Write-tool target, cannot sub-delegate — structural); `Bash` is granted for read-only commands, so disk writes via Bash redirection are blocked only by the agent's read-only-Bash `[DISCIPLINE]`, not structurally |
| reviewer context-isolation | `[DISCIPLINE]` | — | `skills/_protocols/context-isolation.md` | fresh dispatch excludes other findings; shared filesystem access is not isolated; targeted fix verification is a separate assignment |
| workflow `on_fail` gates | `[WORKFLOW]` | BLOCK-in-run | `scripts/workflow_engine.py` | configured checks run only when the engine is driven; manual confirmation is not automatic verification |
| DIRECT eligibility | `[DISCIPLINE]` | — | `framework/direct-eligibility.md` | risk-first eligibility for bounded authorized changes; size cannot bypass safety floors; `skip_when` is NOT engine-evaluated |
| dispatch-package allowlist | `[DISCIPLINE]` | — | `docs/specs/306-brief-architect.md` | a Buddy-authored draft in a brief-architect package is a contract violation |
| Pre-Delegation artifact | `[DISCIPLINE]` | — | `framework/invariants.md` | no sub-agent call without a delegation artifact (Invariant 3) |
| STALE-CLEANUP | `[DISCIPLINE]` | — | `framework/invariants.md` | retired artifact → every live reference cleaned in the same commit (Invariant 5) |
| piebald-budget | `[DISCIPLINE]` | — | `skills/_protocols/piebald-budget.md` | instruction-loading/coherence review; size signals, no length-only gate |
| brief-acceptance | `[DISCIPLINE]` | — | `skills/_protocols/approved-acceptance.md` §The check | the briefing Buddy runs `consistency_check.py --check brief-acceptance --brief <path>` before dispatch and after each brief edit; a block that is missing, duplicated, lacks a nonblank `approved_by` or differs from the task file's lists exits non-zero; nothing runs it on its own (no hook, no engine step) |
| spine-form | `[DISCIPLINE]` | — | `skills/_protocols/architecture-spine.md` §Checks | Buddy runs `consistency_check.py --check spine --spine <path>` after each change to a spine and before the board; a missing header line or section, a non-ascending or incomplete `AD-<n>`, a Deferred entry without its reason, an inherited ID absent from its parent, or a placeholder exits non-zero; form only, the substance is the architect lenses'; nothing runs it on its own (no hook, no engine step) |

Git-check coverage depends on installation, invocation conditions and available programs. Skill-frontmatter evaluation uses §Indexed standalone input contract. Plan validation and source/evidence verification read the same captured candidate through §Indexed related-file input. SECRET-SCAN remains an optional external staged scan. No combined result establishes that every indexed byte, related source or agent write was validated.

## Indexed standalone input contract

**Scope.** This contract covers standalone skill/frontmatter evaluation. Skill applicability and the existing immediate `agents/*.md` name lookup use candidate membership. Plan and evidence target resolution use §Indexed related-file input with the same capture; amendment-reference integrity is a separate integration.

**Git invocation.** Every Git operation used for baseline, repository and HEAD resolution, membership enumeration, staged delta capture, blob reads and comparison must run with the global `--no-replace-objects` option, while preserving the consumer repository/index selection described below.

**Repository selection.** Resolve the consumer worktree, Git directory and effective index through Git from the invocation’s consumer root, preserving its Git-selection environment, including `GIT_INDEX_FILE`. Freeze that environment for all capture and comparison commands. Resolve the effective index using `git --no-replace-objects rev-parse --path-format=absolute --git-path index`; never assume `.git/index` or the common worktree index.

**Capture observations.** Observe repository/worktree/index locations, HEAD’s symbolic spelling or detached status, resolved commit/tree identities, and the effective index’s raw-byte SHA-256 plus file identity/size/mtime/ctime. Read index bytes between matching file-stat observations; absence is an explicit empty-index observation, not an I/O failure. An existing unreadable or unstable index is an input error.

Establish unborn HEAD only when HEAD is a valid symbolic reference whose target does not exist. Other HEAD resolution failures are errors. An unborn baseline has empty membership.

Capture baseline membership with `git --no-replace-objects ls-tree -r -z <captured-tree>` when HEAD exists. Capture index path/mode/stage/OID entries with `git --no-replace-objects ls-files --stage --sparse -z`. Reject nonzero stages. Reject sparse-directory entries and split-index input explicitly in this bounded implementation; determine split-index use through `git --no-replace-objects rev-parse --shared-index-path`. Do not rewrite either representation.

Capture the staged delta using `git --no-replace-objects diff --cached --raw -z --no-abbrev --no-renames --no-ext-diff --no-textconv --no-color --ita-invisible-in-index`. It compares HEAD, or Git’s empty baseline for unborn HEAD. Before/after HEAD observations must agree, so a moving baseline cannot yield accepted capture.

Derive candidate membership by applying that delta to captured baseline membership. Intent-to-add entries excluded by the staged delta are not candidate additions. Validate present candidate entries against the captured stage-zero index mapping. Changed destinations are present entries whose mode/OID differs from baseline; deletions have no content. Represent renames as deletion/addition, so destination checks cannot disappear through rename heuristics.

Preserve raw pathname boundaries through NUL-delimited parsing. Spaces, tabs and newlines must not become record separators. Do not normalize a literal backslash into a directory separator. Retrieve selected file content with `git --no-replace-objects cat-file blob <captured-oid>`, never a later `:<path>` lookup or worktree reopen. Candidate directories and immediate agent names derive from membership, without dereferencing candidate links.

Repeat the capture observations and enumeration before accepting the capture. Any mismatch or failed command invalidates it. Unsupported relevant file modes, missing/nonblob content or unreadable required data are check input errors; no worktree fallback is permitted.

**Evaluation and publication.** Evaluate immutable captured data using ordinary reusable functions. Buffer definitive check results. Immediately before publishing them, reobserve repository/index selection, raw index identity, HEAD identity, index mapping and staged delta; require equality with the accepted capture. A mismatch suppresses definitive results and reports changed input. A later invocation captures afresh.

A successful comparison establishes currentness only at that final observation. It does not exclude an external change afterward or make the subsequent Git commit transactional with validation.

**Execution and preservation.** Run code only from the explicitly selected trusted framework root. Candidate blobs are data; do not import, source or execute candidate programs, filters or configured actions to inspect them. Use no `write-tree`, index refresh/replacement, checkout or staging operation. Preserve index entries, staging choices and user content.

**Reporting and policy.** Identify indexed versus working-tree input, captured identity, exact checked/skipped paths and limitations. Apply the result table below. Working-tree CLI behavior remains available; the hook explicitly selects indexed evaluation.

| Condition | Skill-frontmatter | Hook consequence |
|---|---|---|
| Known PyYAML absence | Existing explicit SKIP | No skill BLOCK caused by capture uncertainty while already dependency-disabled |
| Capture/currentness unavailable, PyYAML available | BLOCK/input unavailable; cannot establish inapplicability | BLOCK through skill policy |
| Capture/currentness unavailable, PyYAML absent | Retain dependency SKIP | No BLOCK from this check, unless another existing check BLOCKs |
| Stable candidate has no `skills/` membership | Existing no-skills SKIP | No manufactured skill PASS |
| Stable candidate has no applicable changed skills | PASS with explicit empty scope | Existing policy |
| Required skill blob invalid/unavailable | BLOCK | BLOCK |
| Existing valid/invalid skill content | Preserve current rule outcome and warnings | Existing policy |

Missing trusted validator programs retain existing explicitly reported availability SKIPs; they never become PASS. Unexpected shared-driver failure is input unavailability, not automatic success or a generic severity decision. Other hook checks retain their existing outcomes.

## Indexed related-file input

**Scope.** PLAN-VALIDATE and SOURCE-VERIFICATION in the hook read task, plan,
report and cited-source content from the candidate captured for §Indexed
standalone input contract, in the same hook run. All rules of that contract
apply, including final comparison before publication.

**Candidate tree.** The trusted driver `scripts/indexed_related.py` writes the
captured entries into a fresh private temporary directory: regular blobs as
non-executable files, read by captured OID in one batch; symbolic links only
when their relative target stays inside the tree after lexical
normalization; gitlinks as empty directories. Any other mode, an absolute or
`.`/`..`/`.git` path component, or a path collision makes the input
unavailable. The directory is removed after the run. Nothing is written to the
index or the worktree.

**Readers.** The trusted plan engine runs with that directory as project root.
Evidence reports are the changed candidate entries under the existing paths
with `schema_version: 1`; their pointers resolve against that directory, so
the existing repository-boundary check applies to the candidate. A pointer to
content that exists only in the worktree, or to a link left out of the tree,
fails. Output names the directory `<candidate>`.

**Cross-references.** In the same tree, section citations in live Markdown
resolve against the candidate. Supported forms, what is reported and what is
not checked:
`skills/_protocols/spec-amendment-discipline-section-citations.md` §Section cross-references.
A citation is reported only when its citing file or its target file is
changed in the candidate. This part changes no other check; if it fails, it
reports SOURCE-VERIFICATION WARN (input unavailable) for itself.

**Policy.** Severities are unchanged. Unavailable capture, tree or final
comparison: PLAN-VALIDATE BLOCK (input unavailable), SOURCE-VERIFICATION
WARN (input unavailable). A plan input (`docs/plan.yaml`,
`docs/task-schema-extensions.yaml`, `docs/tasks/**`) left out of the tree as
a link or gitlink is input unavailable too. PLAN-VALIDATE passes only when the
plan engine exits 0 and its final summary reports 0 errors. Reports are read
with normalized line endings. A missing trusted plan engine keeps the existing
SKIP. The `INDEXED-STANDALONE` record reports `plan_status`,
`evidence_status`, `checked_reports`, `unresolved_links`, and sets
`fully_indexed_related_files` only when both checks evaluated the tree.

**Limits.** Validator programs and their configuration come from the trusted
framework root: `framework/task-schema.yaml`, and the autonomy-consistency
inputs `CLAUDE.md`, `AGENTS.md`, `framework/agent-autonomy.md` and the files
in `AUTONOMY_REFERENCE_FILES` (`scripts/consistency_check.py`). When the
framework root is the repository being committed, those files are read from
its worktree, so a staged change to them is not what PLAN-VALIDATE sees; the
record then reports `framework_inputs: worktree` and does not claim fully
indexed related files, although its `definitive` list still names the plan
result. File-gate paths that are absolute or
leave the project root are not candidate data; their existence is observed on
the host. The trusted plan engine runs without `PYTHON*` environment
variables, so a PyYAML reachable only through `PYTHONPATH` makes
PLAN-VALIDATE block. Each run needs temporary space and time for one copy of
the candidate; an aborted run can leave that private copy behind.
Currentness ends at the final comparison.

## Purged mechanisms (no runnable artifact)

These names appear in historical records (decision logs, review
artifacts) but have **no live artifact**. The hook paradigm shift
removed the tool-event hook layer (`PreToolUse` / `PostToolUse` /
`UserPromptSubmit`); the observability checks they carried are now
`[DISCIPLINE]` (the one-liner in `framework/invariants.md` §Observability and
`skills/transparency_header/SKILL.md`) or were dropped. A doc on the active surface that states present-tense
enforcement for any of these is a phantom claim — reframe it to the
honest class above or mark it historical.

- `BRIEF-CLAIMS` — claimed to re-run an evidence grep at write/commit;
  never built as a live hook.
- `path-whitelist-guard` — claimed to block writes outside the intent
  scope; now the `[DISCIPLINE]` path-scope rule (Invariant 4).
- `frozen-zone-guard` — claimed to block WORM-zone edits; now the
  `[DISCIPLINE]` frozen-zone convention (`.correction.md` sidecars).
- `ANTI-PHANTOM` — a narrow pre-commit WARN tripwire for enforcement claims about
  the three names above; retired once every live mention was an honest historical
  note. Enforcement-honesty remains the discipline rule at the top of this file.
- `TASK-SYNC`, `OBLIGATIONS`, `PERSIST-GATE`, `ENGINE-USE`,
  `RUNBOOK-DRIFT`, `AGENT-SKILL-DRIFT`, `PIEBALD-BUDGET` — former
  pre-commit observability checks, dropped or downgraded to discipline.
  Several names double as live *concepts* (the STALE-CLEANUP invariant,
  the PERSIST-GATE discipline, the piebald-budget protocol) — those are
  `[DISCIPLINE]`, listed in the Live table; only the *hook/BLOCK* claim
  is phantom.

## Maintenance

- Add a row to the Live table whenever a new enforcement mechanism
  ships; pick the class by the honest test above.
- When a mechanism is removed, move its name to Purged and run the
  Invariant-5 sweep (`grep -rn <name>`, fix every live present-tense
  enforcement claim).
- `consistency_check` Check 11 (`scripts/consistency_check.py --check
  enforcement-registry`) validates that every Live row carries a valid
  class tag and that its artifact pointer resolves on disk. Scope limit:
  it is **skill-run, not commit-wired** (no `pre-commit.sh` call), and it
  checks tag *membership* + pointer *resolution* — NOT tag *honesty* (an
  over-claimed but well-formed tag passes). Honest tagging stays a
  `[DISCIPLINE]` judgment against the honest-test above.
