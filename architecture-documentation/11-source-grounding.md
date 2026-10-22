# 11 — Source Grounding

Public documentation explains the system; canonical contracts and implementation
support its technical claims. Use this index to check a claim at its responsible
owner without relying on copied line counts or an old inventory snapshot.

## Capability and scope

| Claim or question | Authority |
|---|---|
| Three independent capabilities and their dependencies | [Capability ownership](../framework/capabilities.md) |
| Installation availability versus workflow selection | [Process map: selection](../framework/process-map.md#workflow-selection) |
| Authorization survives phase changes without expanding scope | [Process map: authorization](../framework/process-map.md#authorization) |
| Proportional development process and DIRECT eligibility | [Process map: DIRECT](../framework/process-map.md#direct-eligibility) |
| Who writes each development artifact | [Agent autonomy](../framework/agent-autonomy.md) |

## Knowledge and continuity

| Claim or question | Authority |
|---|---|
| Semantic capture, owner placement, retrieval and validity | [Knowledge Processor](../skills/knowledge_processor/SKILL.md) |
| Personal location, profile interface and configuration | [User scope](../framework/user-scope.md), [resolver](../scripts/user_scope.py) |
| Same-scope coherent reads and conditional publication | [Continuity contract](../framework/continuity.md), [helper](../scripts/continuity.py) |
| Interrupted publication and stale-baseline recovery | [Continuity: recovery](../framework/continuity.md#recovery-without-stale-replay) |
| Common save and publication authorization | [Save runbook](../workflows/runbooks/save/WORKFLOW.md) |
| Context ownership and navigation upkeep | [Housekeeping runbook](../workflows/runbooks/context_housekeeping/WORKFLOW.md) |
| Minimal boot and ordinary resume | [On-demand start](../agents/buddy/boot-on-demand.md) |

The helper protects file operations; it does not decide whether a claim is true
or whether its intended change is authorized. Semantic and storage evidence must
be considered together.

## General reasoning

| Claim or question | Authority |
|---|---|
| Problem framing | [Frame](../skills/frame/SKILL.md) |
| First-principles drill and synthesis | [Bedrock](../skills/bedrock_drill/SKILL.md) |
| Independent perspectives and Council modes | [Council](../skills/council/SKILL.md) |
| Isolation and briefing constraints | [Context isolation](../skills/_protocols/context-isolation.md) |
| Complete reports before consolidation | [Consolidation preservation](../skills/_protocols/consolidation-preservation.md) |
| Evidence-pointer expectations | [Evidence schema](../skills/_protocols/evidence-pointer-schema.md) |

These describe required method behavior. They do not independently prove that a
particular model followed every instruction or that independent reviewers cannot
share a mistaken assumption.

## Software development

| Claim or question | Authority |
|---|---|
| Development routing and gates | [Process map](../framework/process-map.md), selected [runbooks](../workflows/runbooks/) |
| Task and plan validation | [Plan engine](../scripts/plan_engine.py) |
| Exact workflow state, routes and evidence | [Workflow engine](../scripts/workflow_engine.py) |
| Bound export/restore without progression | [Development continuation](../framework/development-continuation.md) |
| Definition compatibility | [Compatibility contract](../framework/workflow-compatibility.md) and [manifest](../framework/workflow-compatibility.yaml) |
| Task status reconciliation | [Task-status skill](../skills/task_status_update/SKILL.md) |
| Local workflow-state exclusion from Git | [Git ignore rules](../.gitignore) |

A handoff is a continuation route, not a substitute for authoritative engine state.
A source repository's ignore rules also do not establish how another consumer
synchronizes its files; inspect that consumer's rules before making a transport claim.

## Installation and hosts

| Claim or question | Authority |
|---|---|
| Daily/full selection and optional-method closure | [Profiles](../framework/install-profiles.yaml), [closure helper](../scripts/capability_closure.py) |
| Current CLI and managed host plans | [Shared installer](../scripts/forge_install.py), its `--help` output |
| Setup aliases use the shared coordinator | [setup-cc](../scripts/setup-cc.sh), [setup-codex](../scripts/setup-codex.sh), [setup-oc](../scripts/setup-oc.sh) |
| Baseline, activation, retry and rollback | [Activation contract](../framework/installation-activation.md), [implementation](../scripts/install_activation.py) |
| Codex roles and boot entries | [Codex generator](../scripts/generate_codex_agents.py) |
| Claude launcher and OpenCode launcher | [cc](../orchestrators/claude-code/bin/cc), [oc](../orchestrators/opencode/bin/oc) |
| Cursor rules-based support | [Cursor adapter](../orchestrators/cursor/README.md) |
| Commit-time checks and advisory limits | [Git hook](../orchestrators/claude-code/hooks/pre-commit.sh) |
| Mechanical versus protocol enforcement | [Enforcement registry](../framework/enforcement-registry.md) |

## Verify a documentation claim

1. Find its owner above and read the surrounding contract, not just a matching phrase.
2. Inspect the implementation or current CLI when the claim concerns mechanical behavior.
3. Distinguish intended behavior from an executed check and from live host acceptance.
4. Record the concrete result and remaining uncertainty; do not turn missing evidence
   into a passed check.

For an installation, a nonempty evidence file and its recorded hash are not proof
of its assertions. Fresh acceptance observations must support the claimed targets.
For a capability, a successful example does not establish reliability across all
models, hosts and future sessions.

If this guide disagrees with an owner, report the specific discrepancy and affected
reader action. Repair the explanation and its links rather than inventing a new
contract in public documentation.

Next: [Troubleshooting](12-troubleshooting.md).
