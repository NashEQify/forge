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

**On demand:** follow the project's instructions, boot/context navigation,
runbooks and delegation rules. Forge does not automatically start workflows,
Councils, boards, spec cycles, test chains or workflow-engine bookkeeping.
Software `DIRECT` / `STANDARD` / `FULL` eligibility does not classify this work.

Councils, reviews, skills and workflows remain available on explicit user
request. Follow the requested method for that scope; this does not switch the
project to software mode or start an enclosing workflow. Preserve existing
workflow records; selecting on-demand neither completes nor resumes them.

When the user asks Buddy to **“Forge my idea”**, follow the
[Solve runbook](../workflows/runbooks/solve/WORKFLOW.md) for that idea.

This selection governs Forge process and delegation requirements, including
triggers in adapters and skill discovery. Authorization, secret handling,
evidence, actual outcome verification and local safeguards remain binding.
