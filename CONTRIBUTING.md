# Contributing to Forge

Forge is an opinionated, maintainer-led project. Contributions should improve
knowledge and continuity, general reasoning, software development, or the shared
integration these capabilities need. Start with the [overview](architecture-documentation/01-overview.md)
and [capability contract](framework/capabilities.md).

## Reports and proposals

Search existing issues before opening one. Explain the problem, affected users and
expected outcome; distinguish observed behavior from an alternative design you prefer.
For a bug, include sanitized reproduction steps, the Forge revision, installation
profile/method selection and agent host/version. Include the relevant helper output
without private knowledge, credentials or raw personal conversations.

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

## Verification

Run checks appropriate to the affected surface. Skill/index changes may require:

```bash
python3 scripts/generate_skill_map.py --check
python3 scripts/generate_workflow_router.py --check
python3 scripts/generate_skill_wrappers.py --check
```

The navigation generator writes its indexes directly: run
`python3 scripts/generate_navigation.py` only when regeneration is intended, then
inspect its diff. It has no check-only mode. Inspect each generator's supported
interface before use. Update affected generated
outputs together with their sources. Check source references, public Markdown links
and reader journeys for documentation changes. For code, include relevant tests and
reproduction evidence available in your checkout; do not claim tests you did not run.

Shared Git hooks can be installed with:

```bash
bash scripts/install-git-hooks.sh
```

When installed and invoked, they check plan validity, commit conventions and skill
frontmatter as blocking checks. Secret scanning, source verification and phantom
claims have warning checks. Tool availability affects coverage; a successful hook
is not a comprehensive security or behavioral test. Do not bypass a blocking check
instead of addressing its cause. Additional generator checks are not all enforced
by the hook; run the relevant ones explicitly.

## Working with an installation

Use the [coordinated installation guide](architecture-documentation/05-installation.md).
The setup shell scripts forward to the common installer; their names do not imply
separate host-only installations. Stop affected sessions and preserve the current
generation before changing shared source files. Verify the installed outcome after
changes, not just the repository diff.

## Boundaries

Preserve the historical paths listed in `.claude/frozen-zones.txt`. Changes to
capability ownership, installation policy or the skill model need explicit rationale
and review. Avoid unrelated skill-library imports and marketplace expansion.
The [Code of Conduct](CODE_OF_CONDUCT.md) applies to technical discussion as well as
other participation.

Contributions are licensed under [MIT](LICENSE).
