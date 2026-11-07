# 08 — Development + Maintenance

Maintain the owner of a behavior and verify its consumers. Forge's common
continuity and reasoning capabilities must remain usable without software task
machinery. Software development has its own explicit state and checks.

## Start with the affected contract

| Change | Primary owner | Check the boundary |
|---|---|---|
| Knowledge admission, placement or retrieval | [Knowledge Processor](../skills/knowledge_processor/SKILL.md) | Scope, qualifications and usable routes |
| Protected publication or recovery | [Continuity](../framework/continuity.md) | Stale baselines, interrupted writes and scope containment |
| Generic reasoning method | Its skill and required protocols | Supplied-context use and complete independent reports |
| Software progression | Runbook and workflow/plan owner | Exact state, selected obligations and compatibility |
| Host discovery or source update | [Installation activation](../framework/installation-activation.md) | Where each host reads Forge, the light or full path, fresh-session behavior |

Installation availability must not become an implicit workflow selector. Do not
make generic methods depend on software task files simply because a development
caller uses them.

## Engines

The [plan engine](../scripts/plan_engine.py) validates software planning data.
The [workflow engine](../scripts/workflow_engine.py) interprets definitions,
selected routes, progress and evidence. Use the current CLI help and
[engine cookbook](../framework/workflow-engine-cookbook.md) rather than copied
commands from an older guide.

The [development continuation adapter](../framework/development-continuation.md)
binds exact runs and required task/plan checks. Export preserves authoritative state;
restore reads it without advancing or unpausing. A display summary cannot replace
that state. Missing or incompatible selected state must remain a visible blocker.

Workflow definition changes can alter the meaning of existing evidence. Compatibility
is fingerprint-based, with exact reviewed transitions in the
[compatibility manifest](../framework/workflow-compatibility.yaml). Do not infer
compatibility from unchanged names or step counts. Preserve old routes and unfinished
obligations during both upgrade and rollback.

## Generators

| Source | Generated surface | Tool |
|---|---|---|
| Skill metadata | Skill map | [generate_skill_map.py](../scripts/generate_skill_map.py) |
| Skill metadata and entry definitions | Host skill wrappers | [generate_skill_wrappers.py](../scripts/generate_skill_wrappers.py) |
| Neutral roles | Codex role files | [generate_codex_agents.py](../scripts/generate_codex_agents.py) |
| Role/skill relevance metadata | Agent skill-awareness sections | [generate_agent_skill_map.py](../scripts/generate_agent_skill_map.py) |
| Navigation sources | Navigation AUTO blocks | [generate_navigation.py](../scripts/generate_navigation.py) |
| Workflow catalog | Discovery router | [generate_workflow_router.py](../scripts/generate_workflow_router.py) |

Edit canonical sources before regenerating their derived surfaces. Inspect each
generator's source for its destinations and supported check options; do not assume
`--help` or `--check` is implemented by every generator. Generating
repository files and activating host integrations are different actions; the latter
follows [installation activation](../framework/installation-activation.md).

Run relevant generators again to check idempotency: a second run should introduce
no additional intended changes. Report the actual diff/check result rather than
claiming a clean tree when other work is present.

## Validation and tests

Choose checks for the changed behavior. Documentation needs source, link, anchor
and reader-journey checks. Metadata needs its schema validator. Runtime helpers
need focused tests that exercise their actual failure boundaries.

Useful maintained checks include [skill frontmatter validation](../scripts/skill_fm_validate.py),
[runbook consistency](../scripts/validate_runbook_consistency.py),
[evidence-pointer validation](../scripts/validate_evidence_pointers.py) and
[structural consistency](../skills/consistency_check/SKILL.md).

For common capabilities, check use without development-only sources where the
selected profile permits it. For activation, verify actual installed entrypoints
and acceptance behavior. A fixture or static test does not establish live consumer
acceptance; report those evidence classes separately.

Whether Forge engages as intended is a behaviour of the model in a host, so it is
checked in fresh sessions rather than in the test suite. Fixed cases run on Claude
Code and Codex in two arms, once with Forge's start entry and once without it,
several runs per arm with the model pinned. A question in an on-demand project must stay quiet:
the start loads and selects on-demand, and no agent, skill, engine or task
bookkeeping starts. A scoped fix under a "write only here, no network" limit must
still load the start and report the fix with a verification that actually ran. Each run also records turns and tokens, so the
cost of the arm with Forge is visible against the arm without. Each case names when
it must run again: a new model or host version, a changed start entry, or a changed
start sequence or workflow selection. A passing unit test does not show that a
fresh session behaves. Maintainers run these checks; the case runner is
not part of this distribution.

## Hooks

Installed shared Git hooks check plan data, commit format and skill frontmatter,
with advisory secret, source-evidence and stale-enforcement checks. They run at
commit time, not on every write. Their actual behavior is in
[pre-commit.sh](../orchestrators/claude-code/hooks/pre-commit.sh).

Resolve a blocking check at its source. If the check is defective, preserve its
output and investigate it; deleting the hook or suppressing the diagnostic does
not validate the change. Host boot integration remains a separate verification.

## Conventions

Before changing a rule, structure or decision, name the intent it serves and the
failure it prevents, and check end to end that the changed version still does both
([work principle](../framework/work-principle.md)). Rules that must hold in every
project go into the [framework invariants](../framework/invariants.md); rules for one
repository stay in its own `CLAUDE.md` or `AGENTS.md`.

Follow [skill anatomy](../framework/skill-anatomy.md) for a new skill and justify
why an existing method cannot own the responsibility. Follow
[artifact structure](../docs/STRUCTURE.md) for placement and historical records.

Retiring a skill, role or route includes its live references and generated discovery
surfaces. Search names and enumerate the relevant live inventory; preserve frozen
history. A rename alone does not remove a dependency.

New tasks go through [task_creation](../skills/task_creation/SKILL.md), which checks
for duplicates and folds work that serves one deliverable into one task.
Task status changes go through [task_status_update](../skills/task_status_update/SKILL.md),
which owns dependent graph and plan reconciliation. Raw task YAML edits bypass that
process. This requirement concerns tracked development tasks, not ordinary knowledge.

## Maintenance routines

Housekeeping reconciles owners, routes and freshness using the common continuity
boundary. It need not start a development engine. Knowledge migrations must preserve
working-tree qualifications and usable routes while recovering partial publications.

For someone who uses Forge, the host's plugin update is the update
([updating](05-installation.md#updating)). Changing Forge's own sources on the machine
you work on follows [installation activation](../framework/installation-activation.md):
instruction-only Markdown changes take its light path; other source and integration
changes take its full path, with the tests and a fresh session on each host that reads
them.

## Contribution notes

Use [CONTRIBUTING.md](../CONTRIBUTING.md) for contribution conventions. Describe the
consumer-visible result, relevant checks and remaining limits. Avoid absolute
reliability claims or inventory counts that become stale as files change.

Next: [Agent guide](09-agent-guide.md) · [Source grounding](11-source-grounding.md).
