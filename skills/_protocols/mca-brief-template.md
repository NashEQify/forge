# Protocol: MCA-Brief Implicit-Decisions Template

Mandatory decision-class enumeration in the MCA delegation brief.
Prevents brief-quality gap → implementation drift when the brief
stays sketchy and the implementer makes architecture decisions
without spec authority. Discipline-as-mechanism: structural
template fields > LLM persona review.

**Consumed by:** `workflows/runbooks/build/workflow.yaml` step
`brief-author` / `brief-signoff`; `brief_check` consumes declared structure.
`agents/main-code-agent.md` input validation as a required field
on Full / Standard.

**Brief as a file:** the brief is a file in the work unit's records, and the dispatch names it; the dispatch's parts
and the report file: `skills/_protocols/mca-dispatch.md`.

**Pre-dispatch check (discipline):**
Buddy verifies presence + completeness of all 5 classes before
dispatching the brief: Buddy reads this protocol before drafting
and self-checks all 5 classes against the dispatch, plus the
§Complexity-Tracking section every brief carries.

For build signoff, Buddy persists and stamps the final artifact, then explicitly
binds its project-relative path with `--complete brief-author --set brief_path
<path>` on the selected `--id`. Example additional frontmatter:

```yaml
brief_contract:
  workflow_id: "<exact selected workflow_id>"
  implicit_decisions:
    status: applicable
  mechanism_cells:
    status: exempt
    reason: "<specific reason the mechanism trigger does not apply>"
```

The contract requires exactly those three fields; obligation mappings accept only
`status` and optional `reason`. `unknown`, missing or unsupported declarations
fail. Exemption requires a nonblank reason. An applicable obligation requires its
canonical block (below; mechanism cells: `mca-brief-template-decision-classes.md` §4). Unrelated indexing/evidence metadata remains permitted.
Structural success does not establish decision quality, trigger correctness or
authorization; Buddy retains those judgments. No evidence schema is repurposed.

---

## Trigger (when the section is mandatory)

Analogous to the `impl_plan_review` trigger:

- the task has ≥ 3 acceptance criteria, **OR**
- the task contains a schema change (DB / API / event schema), **OR**
- the task has cross-module impact (>1 subsystem affected), **OR**
- the workflow is sub-build (parent has remaining scope).

Below threshold (≤2 ACs, single file, no schema): optional; Buddy
may write a one-sentence rationale why it's not enumerated.

## Section format

Required block in the MCA brief under
`## Implicit-Decisions-Surfaced`. Format is structured YAML —
checked by `brief_check` plus downstream skills. Headings may have a leading
`§`. Normal quoted, literal and folded YAML scalars are supported. Required
blocks reject duplicate mapping keys or competing payloads.

```yaml
implicit_decisions_surfaced:
  schema_and_contract:
    locked: "<status>"
    value: "<decision>"
  error_and_stop:
    locked: "<status>"
    value: "<decision>"
  layer_discipline:
    locked: "<status>"
    value: "<decision>"
  structural_invariants:
    locked: "<status>"
    value: "<decision>"
  vision_alignment:
    locked: "<status>"
    value: "<decision>"
  other:
    - klasse: "<task-specific decision class>"
      locked: "<status>"
      value: "<decision>"
```

**`locked` values (enum):**

- `"yes — spec §X.Y"` — decision is locked in the spec; MCA
  follows spec authority.
- `"yes — sub-build §X"` — decision is locked in the sub-build
  spec.
- `"no-but-derivable (<rationale>)"` — spec is implicit; MCA can
  derive without risk.
- `"no-NEEDS-LOCKING (Buddy decision: <choice>)"` — Buddy locks
  it in the brief.
- `"n/a (<rationale>)"` — class does not apply to the task.

**`value`** is the concrete decision content (1-3 sentences).

## Workflow scope (instance stamping — when a sibling workflow is live)

When this brief dispatches an agent **inside a workflow step** and
`workflow_engine.py --next` reports a `NOT-YOURS:` line (≥2 workflows live in
the checkout), paste the engine's `SCOPE:` + `NOT-YOURS:` block from `--next`
verbatim into the brief. This **stamps the agent with its own file pointers** so
it never reconstructs "which files are mine" by browsing `docs/<workflow>/` or
`.workflow-state/` — the failure that let a parallel workflow's agent (solve-593)
trip over a sibling's files (solve-594).

- Hand the agent its OWN concrete paths (state file, task file). Do **not** hand
  it a directory to browse — fewer cues beat more warnings.
- The `NOT-YOURS:` line names the sibling files to ignore.
- `--next` shows no `NOT-YOURS:` (single workflow live): omit the block —
  nothing to disambiguate.

This is content the agent NEEDS, so it lives **here in the brief**, never in the
anti-bias `dispatch-template.md` (whose contract is to STRIP Buddy's context out,
the opposite operation).

## Decision classes — detail

When filling the `## Implicit-Decisions-Surfaced` block (each class's `locked` and `value`) and when writing the
`## Mechanism-cells` block: read and follow `skills/_protocols/mca-brief-template-decision-classes.md` (§1
schema_and_contract, §2 error_and_stop, §3 layer_discipline, §4 structural_invariants with its pattern classes and the
mechanism-cells block, §5 vision_alignment with defer-durability and the architecture reading-map, §6 other).

## Anti-patterns

- **DO NOT** fill the section pro forma ("everything locked").
  **INSTEAD** check honestly per class — more `no-NEEDS-LOCKING`
  is more honest than unjustified `yes`.
- **DO NOT** mark `structural_invariants: n/a` without a reason.
  **INSTEAD** name what makes the brief mechanical.
- **DO NOT** drop the section below threshold without rationale.
  **INSTEAD** declare `implicit_decisions: {status: exempt, reason: "<specific
  below-threshold reason>"}` under `brief_contract` for build signoff. Trigger
  criteria remain unchanged.
- **DO NOT** put the section at the end of the brief as a
  postscript. **INSTEAD** place it before `## Acceptance-Criteria`
  — MCA reads top-down; decision locks belong before the AC list.
- **DO NOT** let MCA touch fields, files, or symbols outside the
  brief's explicit scope, even when an identical pattern would
  apply. **INSTEAD** the brief MUST name forbidden adjacent
  scope-changes prescriptively.

- **DO NOT** prescribe a hardcoded literal at a call-site boundary
  (e.g. `cost_currency="USD"`, `tenant_id="default-tenant"`,
  `role="assistant"`) without first grepping the upstream domain
  object for the same field. **INSTEAD** for every literal in a
  §code-touch snippet, grep the upstream model (e.g.
  `grep -n "<field_name>" src/<module>/models.py`). If the field
  exists upstream and is already validated, the brief MUST
  prescribe pass-through (`upstream.field`), NOT a re-derived
  literal. Hardcoding upstream-validated values at boundaries is
  cycle-symptom-cause: works coincidentally today (when the
  upstream value happens to equal the literal), latent bug when
  upstream emits a different value. Briefs ARE code-as-text and
  carry the same grep-verify-discipline as the §-section
  amendment gate in `_protocols/spec-amendment-discipline.md`.

- **DO NOT** prescribe a code-touch on a file or region (e.g.
  "extend the SSE handler in `chatAdapter.ts`", "add the audit fold
  to `orchestrator.py:1406`") without first grepping the upstream
  surface for whether the contract is already satisfied by existing
  wiring. **INSTEAD** for every prescribed code-touch: grep the
  upstream wiring (parent handler, mediator, capability boundary).
  If the upstream surface already satisfies the prescribed contract,
  the brief MUST say "verify X unchanged" not "extend X".
  Prescribing extension of pre-existing wiring is cycle-symptom-cause
  at the file / region level — same class as the hardcoded-literal
  bullet above with broader trigger. Catches the implicit "extend X"
  case where the brief prescribes a code-touch WITHOUT the
  `## Claim-Verifications` trigger phrases (`reuses existing`,
  `supersedes`, `already implemented`, etc.).

## Bind rule

Subsequent workflow steps must reference the decision locks by
name:

- `mca-implementation` step: MCA's plan MUST contain every
  `no-NEEDS-LOCKING` decision as a constraint (instead of making
  its own decision).
- `code-review-board` step: reviewers check the code against the
  decision locks. Code deviates from a lock → finding.
- `spec-co-evolve-check` step: when a `no-NEEDS-LOCKING` decision
  becomes spec-defined behaviour, apply a spec patch in the same
  block-commit.

---

## Approved acceptance (every brief on a task)

A brief for work on a task with acceptance criteria carries the read-only block `## Approved acceptance (read-only)`
first among the sections that map or plan against the acceptance: the task file's acceptance criteria and exclusions
copied as they stand, and the user's approving words quoted. `## Acceptance-Criteria` maps that block to obligations
and tests; it does not restate it. When writing the brief, and when reissuing it: read and follow
`skills/_protocols/approved-acceptance.md` (the block's form, the check before dispatch, change, resume and
re-brief). A brief past 12,000 bytes (`wc -c`): read and follow
`framework/spec-engineering-implementation-specs.md` §Convention: one goal per change (the size budget).

## UX contracts (a brief that builds a person-operated surface)

When the spec the brief implements links a look and an experience contract (`skills/ux_authoring/SKILL.md`), the brief
names both files as required input for the surfaces it builds. An `open` slot the brief needs is answered through
`ux_authoring` before the dispatch.

---

## Complexity-Tracking (every brief)

Every brief, at any size, carries a `## Complexity-Tracking` section
before `## Acceptance-Criteria`: the table of
`framework/spec-engineering-implementation-specs.md` §Convention: §Complexity-Tracking, with
the rows of the spec it implements plus every addition the brief itself
prescribes, or `None.`. The brief tells the implementer that an addition
the table does not list is dropped, or reported in the return with a
proposed row (need and simpler alternative); the implementer does not
keep it on its own judgment.

**Fixes.** A fix — a defect fix or a review fix pass — adds no public
surface (an exported symbol, command option, output field, configuration
key, file format or endpoint) and guards no state the failure did not
demonstrate, unless a row names why. Demonstrated means shown to occur
through the real entry point: the reported failure, its reproduction, or
an executed probe through that entry point. A state that only a
hand-built fixture reaches is not demonstrated. The fix's own acceptance
criterion counts as for any change: handling the inputs it names is the
fix, not a guard. When the smallest fix needs public surface or such a
guard to meet its criterion, the brief carries the row with that need;
everything else is dropped.

Source: BMAD-METHOD (MIT License, © 2025 BMad Code, LLC); Forge's register of adopted methods.

---

## Test/Verification scope, gate cadence, Claim-Verifications, Reviewer Checkpoints, structural-refactor pre-lock

When writing the brief's test and verification scope (DoD), and before locking a brief that covers several commits,
uses a claim trigger formulation, is reviewed at L2 or touches imports: read and follow
`skills/_protocols/mca-brief-template-verification.md` (per-fix DoD and its bind rule; gate cadence; the
Claim-Verifications table, its triggers and resolved-seam depth; the L2 4-link evidence chain; the import-graph
pre-lock checklist).
