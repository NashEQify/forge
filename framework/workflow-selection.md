# Workflow selection

Step-loaded unit of `framework/process-map.md`. Read it at boot step 2 (after the freshness gate, before loading
context) and whenever the mode of the active project's work is in question. It applies to every project and decides
whether the software workflows, gates and bookkeeping in the process map apply.

### Workflow selection

Use Forge's automatic processes for software development, as established by
the active project's intent. For other work, use the project's own working
rules and Forge tools on demand. An optional `Forge workflows: software` or
`Forge workflows: on-demand` line under `## Context` in `intent.md` makes the
choice explicit and takes precedence. If the intent does not establish
software development, use on-demand. A directory name or the presence of
scripts, configuration or IaC alone does not select software development.

### On demand

Follow the project's instructions, boot/context navigation, runbooks and
delegation rules. Software `DIRECT` / `STANDARD` / `FULL` eligibility,
automatic workflows, boards, spec cycles, test chains and engine bookkeeping
belong to software mode.

Before choosing a path or proceeding with an unresolved change that alters a
trust boundary, materially affects several components, or can leave effects
that are hard to reverse, apply the Council gate (`skills/council/SKILL.md`
§1.0), including its override floors. Reassess on a topic change. Evaluate what
a wrong choice could leave behind after rollback. If the gate fires, start a
standalone read-only Council in this turn before presenting options for the
user to decide, recommending a path, or proceeding with the change. Keep a
previously approved Apply pending while the decision remains open, even after
a successful dry run. During ongoing harm, follow authorized local incident
recovery first and assess the permanent fix separately.

Council and other Forge methods remain available on explicit request for
their scope. Standalone methods keep the project in on-demand mode. Preserve
existing workflow records and resume only the authorized work.

When the user asks Buddy to **“Forge my idea”**, follow the
[Solve runbook](../workflows/runbooks/solve/WORKFLOW.md) for that idea.

This selection governs Forge process and delegation requirements, including
triggers in adapters and skill discovery. Authorization, secret handling,
evidence, actual outcome verification and local safeguards remain binding.
