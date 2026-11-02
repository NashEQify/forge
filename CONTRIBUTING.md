# Contributing to Forge

Forge is an opinionated, maintainer-led project. Contributions should improve
knowledge and continuity, general reasoning, software development, or the shared
integration these capabilities need. Start with the [overview](architecture-documentation/01-overview.md)
and [capability contract](framework/capabilities.md).

## Reports and proposals

Search existing issues before opening one. Explain the problem, affected users and
expected outcome; distinguish observed behavior from an alternative design you prefer.

For a bug, say which layer failed, because each needs different evidence:

1. **Installation:** the installed files are missing or stale.
   `python3 scripts/forge_install.py --check <project>` shows the state of a project
   install; `python3 scripts/forge_install.py --profile full-ai-integration --check`
   and `python3 scripts/forge_install.py --maintenance status` show the state of the
   machine installation.
2. **Instruction loading:** the agent host did not load Forge's instructions, or the
   agent did not follow the boot they ask for. Report how you started the session
   and whether its first answer followed the boot instructions; that first answer
   is the evidence. The generator checks under Verification only show whether the
   source indexes are consistent.
3. **Session outcome:** the session loaded Forge but did the wrong thing. Report
   the action you asked for, the expected and the actual result, and sanitized
   evidence such as the relevant helper output.

Always include the Forge revision, the installation profile and method, the agent
host and version, and the model if the host reports it. Leave out private
knowledge, credentials and raw personal conversations; a transcript is never
required.

To gather this evidence from a session that went wrong, ask the agent to run the
[session diagnosis](skills/session_diagnosis/SKILL.md) on its transcript, on your own
machine. Its report checks first whether Forge loaded, names the layer, cites the
transcript lines behind every finding and asks whether the problem occurs without
Forge. Share its shared copy, which replaces paths, names and secrets, after reading it;
never the transcript.

A knowledge-retrieval failure and a development-engine failure need different evidence.
Only include plan/workflow diagnostics when that capability is involved. For nontrivial
changes, discuss scope before implementation. Security-sensitive reports follow
[SECURITY.md](SECURITY.md).

## Changes

Preserve capability independence and consumer ownership. Do not introduce fixed
user paths, duplicate a shared algorithm in an adapter, or require software tasks
for ordinary knowledge work. Preserve knowledge and current routes when changing
storage or installation behavior.

Skills follow [skill anatomy](framework/skill-anatomy.md), including frontmatter,
invocation descriptions and the justification for a new standalone skill. Retiring
an artifact includes its live references; preserve frozen history. Task status
changes use the [task status procedure](skills/task_status_update/SKILL.md).

Use Conventional Commits, such as `docs(usage): clarify standalone Council`.
Describe the problem, final behavior, relevant checks and limitations in the PR.
Avoid internal conversation history in reader-facing documentation.

This repository is generated from the maintainers' canonical source. An accepted
pull request is applied there with your authorship and reaches this repository
with the next sync. It is not merged here directly, because the next sync would
overwrite it.

## Verification

Run checks appropriate to the affected surface. The public checks run from a
fresh checkout with `python3 -m pytest tests`; [tests/README.md](tests/README.md)
says what they cover and what they do not. Skill/index changes may require:

```bash
python3 scripts/generate_skill_map.py --check
python3 scripts/generate_workflow_router.py --check
python3 scripts/generate_skill_wrappers.py --check
python3 scripts/generate_navigation.py --check
```

Without `--check`, each generator rewrites its outputs; regenerate only when
intended, then inspect the diff. Update affected generated
outputs together with their sources. Check source references, public Markdown links
and reader journeys for documentation changes. For code, include relevant tests and
reproduction evidence available in your checkout; do not claim tests you did not run.

Shared Git hooks can be installed with:

```bash
bash scripts/install-git-hooks.sh
```

When installed and invoked, they check plan validity, commit conventions and skill
frontmatter as blocking checks. Secret scanning and source verification are
warning checks. Tool availability affects coverage; a successful hook
is not a comprehensive security or behavioral test. Do not bypass a blocking check
instead of addressing its cause. Additional generator checks are not all enforced
by the hook; run the relevant ones explicitly.

## Working with an installation

Use the [coordinated installation guide](architecture-documentation/05-installation.md).
The setup shell scripts forward to the common installer; their names do not imply
separate host-only installations. Instruction-only Markdown follows the light
path of the activation contract; for other shared source files stop affected
sessions and preserve the current generation before changing them. Verify the installed outcome after
changes, not just the repository diff.

## Boundaries

Preserve the historical paths listed in `.claude/frozen-zones.txt`. Changes to
capability ownership, installation policy or the skill model need explicit rationale
and review. Avoid unrelated skill-library imports and marketplace expansion.
The [Code of Conduct](CODE_OF_CONDUCT.md) applies to technical discussion as well as
other participation.

Contributions are licensed under [MIT](LICENSE).
