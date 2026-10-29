# Skill Anatomy — Format Standard for All Skills

**Tier:** 1 (operational, next to `process-map.md` + `skill-map.md`)

---

## Purpose

Binding format standard for all skills in `skills/`. Single-class
model plus explicit invocation axis.

What this spec does:
- defines frontmatter schema (mechanically enforceable via the
  SKILL-FM-VALIDATE pre-commit check)
- defines required sections (mentally enforceable via Spec-Board)
- standardizes mode conventions
- fixes naming conventions

What this spec does not do:
- prescribe skill content methodology
- introduce class hierarchy between skills
- define workflow routing standard (`process-map.md` does)
- provide semantic content validator (Spec-Board L1 does)

## Files in a skill directory

A skill has a `skills/<name>/SKILL.md` entrypoint and may have supporting
references. Keep purpose, essential constraints and routing in SKILL.md;
link substantial conditional detail with a concrete read trigger where
it is needed. A reference is not assumed to load automatically. Short
self-contained skills need no split. Loading and size-review guidance:
`skills/_protocols/piebald-budget.md`. Neither reference folding nor file
splitting is required solely to meet a line count. The host load limit in that protocol
(§Loading policy) is a measured byte budget, not a line count.

---

## Ontological split — 4 artifact types

This is not 4 classes *within* skills; it is 4 different framework artifacts.

| Artifact | Path | Nature | Examples |
|---|---|---|---|
| **Skill** | `skills/<name>/SKILL.md` | self-contained methodology + contract | `spec_authoring`, `frame`, `task_creation` |
| **Workflow** | `workflows/runbooks/<name>/WORKFLOW.md` | routing tree + phase sequence, composes skills | `build`, `solve`, `fix`, `save` |
| **Protocol** | `skills/_protocols/*.md`, `agents/_protocols/*.md` | loaded rules/formats | `discourse`, `dispatch-template`, `reasoning-trace` |
| **Persona** | `agents/<name>/` or `agents/<name>.md` | role prompt layer | `code-adversary`, `board-ux-heuristic` |

Operational skill test:
A `skills/<name>/SKILL.md` is treated as a skill for anatomy/migration when it:
(a) contains numbered process methodology or explicit hook/formatter contract,
(b) defines INPUT/OUTPUT/DONE/FAIL,
(c) is independently addressable in intended call context.
Pure templates/mechanics may live as service modules.

Consequence: `type: workflow` inside SKILL.md is ambiguous against
`workflows/runbooks/`. New schema removes `type:` entirely.
All skills are ontologically skills; variation is orthogonal frontmatter.

---

## Frontmatter schema

Required fields per skill:

```yaml
---
name: <skill-name>
description: >
  <What skill does in 1-3 sentences. Include "Use when ..." triggers.>

status: active | draft | deprecated

invocation:
  primary: user-facing | workflow-step | sub-skill | hook | cross-cutting
  secondary: [<path>:<modifier>?, ...]
  trigger_patterns: ["..."]    # only if primary = user-facing

disable-model-invocation: true | false    # default false

cc_wrapper: true | false    # OPTIONAL, override-only (see below)

modes: [<mode-name>, ...]    # omit if monomodal
---
```

### Field definitions

When writing or changing a skill's frontmatter and when a SKILL-FM-VALIDATE finding on a field is handled: read and
follow `framework/skill-anatomy-frontmatter.md` (§`name`, §`description`, §`status`, §`invocation`,
§`disable-model-invocation`, §`cc_wrapper`, §`modes`, §`relevant_for`, §What is removed from frontmatter).

## Required sections (7)

Every SKILL.md MUST contain these 7 sections in this order.
Spec-Board L1 checks completeness.

1. **Frontmatter**
2. **Purpose** (1-3 paragraphs)
3. **When to call** + **When not to call**
4. **Process** (numbered, executable)
5. **Red Flags**
6. **Common Rationalizations** (anti-excuse table)
7. **Contract** (INPUT/OUTPUT/DONE/FAIL)

Optional:
8. **Verification** checklist
9. **Standalone justification** (required for new skill proposals)

### Process for multi-mode skills

Use shared-first pattern:
- `Process — Shared`
- `Process — Mode <name>` per mode
or a compact delta table if differences are small.

### Mega-skill test

If >50% of process content is disjoint per mode, skill is overloaded:
- remove mode and split
- split into family skills
- switch mode axis to a structurally coherent one

Measurement uses numbered process steps, not line count.

### Rationalization minimum

At least 2 rationalization rows (excluding headers).
0-1 rows => Spec-Board L1 FAIL.

The required sections keep this form. Wording elsewhere in a skill takes
its form from `skills/_protocols/instruction-form.md`.

---

## Mode convention

One mode axis per skill (do not mix axes):

| Axis | Convention | Examples |
|---|---|---|
| Depth | `quick/standard/deep` | frame, spec_board |
| Topic | action words | knowledge_processor modes |
| Phase | lifecycle stage | testing design/eval/execution |
| Level | staged levels | scoping L0-L3, code_review_board L1/L2 |
| Breadth | effort scope | focused/broad/exhaustive |

Default when unsure: depth axis.

Hard convention: max 3 modes per skill.
Exception: phase/level axes may exceed 3 when semantically justified.

Per mode document:
1) when used
2) what is skipped
3) what remains mandatory
4) auto-upgrade trigger (recommended)

---

## Naming convention

Default: `verb_object`.
`object`-only names allowed when verb is strongly implicit.
Max 3 segments.

Rename backlog A.5 (as recorded):
- `problem_framing` -> `frame` (DONE)
- `recursive_first_principles` -> `bedrock_drill` (DONE)
- `spec_amendment_verification` -> `verify_amendment`
- `pre_build_spec_audit` -> `mine_specs`
- `impl_plan_review` -> `plan_review`
- `architecture_coherence_review` -> `coherence_review`

Workflow renames are out-of-scope for this spec.

---

## Inflation guard

New skills only if:
1. standalone methodology is demonstrable
2. standalone required outputs are unique
3. Spec-Board L1 PASS on standalone argument
4. no existing skill + mode can cover use case

Operational consequence:
first question for any new skill idea: "is this a mode of an existing skill?"

---

## Consolidation mechanics (skill absorbed as mode)

When a skill is absorbed into another skill as a mode:

1. run mega-skill test (process overlap >= 80%, identical verdict type, comparable trigger phase)
2. extend target skill (`modes`, process blocks, triggers)
3. delete the source skill directory (git history is the archive)
4. update callers: runbooks, `uses` docs, `process-map.md`, persona files
5. run stale-cleanup in the same commit
6. regenerate `skill-map.md`

No mode-of-X marker in frontmatter; single-class model stays consistent.

---

## Skill inventory

The live inventory is `framework/skill-map.md` (AUTO block regenerated by
`scripts/generate_skill_map.py`).
Post phase-G additions and archive moves are additive updates.

---

## Wrapper — required derived artifact

When a change affects wrapper eligibility, the wrappers under `.claude/skills/` or their generator, and when a
wrapper-drift (consistency check 10) finding is handled: read and follow `framework/skill-anatomy-wrapper-and-checks.md`
(§Wrapper: generator, validator, inclusion predicate, failure modes, description normalization, distribution).

## Renames

Stale cleanup in the same commit is required (`framework/invariants.md` §5).

---

## Verification — what hooks check vs not

When changing a skill validator or generator, and when a SKILL-FM-VALIDATE finding is handled: read and follow
`framework/skill-anatomy-wrapper-and-checks.md` (§Mechanical checks, §Generator output strategy, §Not checked mechanically).

## Example — complete skill anatomy

(Reference skeleton preserved)

```markdown
---
name: task_creation
...
---

# Skill: task_creation

## Purpose
...
## When to call
...
### When not to call
...
## Process
...
## Red Flags
...
## Common Rationalizations
...
## Contract
### INPUT
### OUTPUT
### DONE
### FAIL
```

---

## Relation to other Tier-1 docs

- `framework/skill-map.md` (AUTO block generated)
- `framework/process-map.md` (workflow routing)
- `framework/boot-navigation.md` (boot index)
- `agents/buddy/operational.md` (operational anti-inflation behavior)
- `framework/spec-engineering.md` (5 primitives spirit)
- `skills/_protocols/piebald-budget.md` (instruction loading and size-review
  SoT — assess functional impact; length alone is not a gate, the measured
  host load limit aside)

---

## Council side findings (phase D.6)

Documented future extensions:
- additional invocation path families
- potential mode-axis standardization
- reminder that anatomy is an operational lever, not taxonomic vanity
