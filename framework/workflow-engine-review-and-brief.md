# Workflow engine — review capture and brief binding

Step-loaded unit of `framework/workflow-engine-cookbook.md`. Read it when a workflow step runs or adopts a mandatory
software review, and when a build brief is bound or legacy work is adopted.

## Mandatory software-review capture and adoption

Operational authority: [`evidence-pointer-schema.md` §9](../skills/_protocols/evidence-pointer-schema.md#9-mandatory-software-review-adoption).
Load it before review intended to satisfy a mandatory result/readiness/completion
boundary. These operations always require exact `--id` and STEP; they never select
an ambient owner, complete/retry the step implicitly, or resume a workflow.

```bash
# JSON stdin follows §9.2. Capture before dispatch on an in-progress owner.
python3 "$FRAMEWORK_DIR/scripts/workflow_engine.py" --review-capture STEP --id WORKFLOW < capture-request.json
# Consume the single successful JSON stdout envelope only after persistence.
# Pass run/subject/slot to each producer for its frontmatter echo; persist complete
# returns and record actor/path/raw-byte digest before consuming them.
# Write Buddy's decision with current_reports; adoption prints its diagnostics.
python3 "$FRAMEWORK_DIR/scripts/workflow_engine.py" --review-adopt STEP --id WORKFLOW --verdict retained-decision.md
python3 "$FRAMEWORK_DIR/scripts/workflow_engine.py" --review-check STEP --id WORKFLOW --review-policy evidence
python3 "$FRAMEWORK_DIR/scripts/workflow_engine.py" --review-check STEP --id WORKFLOW --review-policy spec_success
# Code forward progression instead uses code_success.
```

A capture refusal or persistence error emits no success envelope. A repeat capture
on the same subject keeps owner, iteration and run; a changed request (an added
slot) moves the current adoption into history. The owner may retain capture when complete in a live workflow; missing
capture cannot be backfilled. Mutations refuse paused, aborted, completed or
archived workflows. Explicit read-only checks can inspect retained evidence there,
without saving, reopening or creating approval. Adoption refuses on contradictions
and missing content (the full list is §9.4): noncurrent subject, a decision or
report not bound to the captured run, a captured slot without report, changed
bytes, a finding without evidence, a quote that does not resolve. Form problems
are retained as diagnostics for Buddy's decision.

Code subjects describe baseline-to-final-worktree bytes/modes and membership.
Declare state and intended report/decision output exclusions before capture; their
writes then preserve the subject while a relevant sibling addition invalidates it.
Required reviewed inputs cannot hide under exclusions. Relevant changes require
existing `--retry STEP --id WORKFLOW --reason ...`, then fresh capture before the
applicable scoped/full verification. Retry reopens in-progress or terminal work,
retains prior review in existing retry history and advances existing iteration; a
capture correction before any producer ran keeps it (`framework/workflow-engine-cookbook.md`
§Iteration cap and review rounds).
Historical reports are not relabelled current or rerun as current evidence.

Mandatory pointer completion adds all three fields together:

```yaml
review_owner_workflow: self  # or exact ID / flat variable
review_owner_step: board-spec
review_policy: spec_success # evidence | spec_success | code_success
```

On a review-backed check `min_schema_version` has no effect beyond rejecting values
above 1; the decision's own pointers are Buddy's C-VERIFY duty, not a mechanical
check. Variables must resolve nonblank;
partial configuration and unknown policies fail closed. The configured locator
must match the exact retained decision bytes. Fallback is selected only for an
unresolved primary, never for a missing resolved file. Mandatory qualification is
checked even with force and cannot advance through warn/skip/escalate refusal.
Ordinary pointer force/layout/legacy behavior remains unchanged.

Current negatives permit evidence/repair only. spec_success permits spec PASS
without an unresolved mediator audit marker in a captured file; code_success
permits code PASS or PASS_WITH_RISKS under existing risk rules. PARTIAL never
permits success. Before review-derived task writes use the exact owner checker and
the §9.6 mapping through task_status_update. This is a procedure duty, not an
atomic task writer. Digests establish bytes, not authorship, execution truth,
complete commissioning scope or correct interpretation.

## Build brief binding and legacy adoption

Buddy persists the final brief (synthesized output in multi-mode), stamps its
`brief_contract.workflow_id` with the exact selected run identity and explicitly
binds its project-relative path:

```sh
python3 scripts/workflow_engine.py --id <workflow-id> \
  --complete brief-author --set brief_path <project-relative-brief-path>
```

Build signoff uses:

```yaml
completion:
  type: compound
  checks:
    - type: brief_check
      path: "{brief_path}"
    - type: manual
on_fail: block
```

The required path resolves within the active project to a readable regular file
with nonblank UTF-8 content. The file is captured once per evaluation; definition
preflight performs no artifact read. There is no filename/glob discovery fallback.
The frontmatter `brief_contract` requires exactly `workflow_id`,
`implicit_decisions` and `mechanism_cells`. Each obligation declares `status:
applicable` or `status: exempt` with a nonblank `reason`; missing, `unknown`,
unsupported or malformed declarations fail. Unknown contract keys fail too.
Applicable obligations require canonical YAML blocks in their corresponding
`## Implicit-Decisions-Surfaced` / `## Mechanism-cells` sections (optional leading
`§`). All five decision classes need nonblank `locked` and `value`; mechanism
cells need nonblank `section`, nonempty `in_scope`, and `placed` /
`forbidden_adjacent` lists (empty allowed). Duplicate keys, duplicate sections,
competing payloads and empty headings fail. Reasoned exemptions may omit sections.
This local structure check does not infer applicability or certify semantics,
reference resolution, authorization or test coverage.

Invalid required input raises an evaluation error: CLI fails and signoff remains
open regardless of `on_fail`. Trees containing `brief_check` refuse `--force`
before binding/count mutation. The compound retains manual qualification:
`agent-confirmed (not verified)`. Other checks retain their force/failure policies.

Pending or in-progress old build signoff uses the installed contract. Explicitly
bind/adopt one artifact with the exact owner and applicability; normalize prose
legacy briefs into required canonical YAML without discarding substantive content
or history. No second legacy parser, fingerprint migration or bulk reset exists.
Terminal old signoff remains historical; its earlier evidence does not establish
that this check ran. Ordinary continuation does not recertify it. Explicit retry
retains existing retry history, then requires the current contract on completion.
Routes omitting signoff require no dummy brief; `skip_when` is instructional.
