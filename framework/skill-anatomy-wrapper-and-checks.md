# Skill Anatomy — wrapper and mechanical checks

Step-loaded unit of `framework/skill-anatomy.md`. Read it when a change affects wrapper eligibility (`status`,
`disable-model-invocation`, `invocation.primary`, `cc_wrapper`), the skill wrappers, the skill map or their
generators and validators, and when a SKILL-FM-VALIDATE or wrapper-drift (consistency check 10) finding is handled.

## Wrapper — required derived artifact

The Claude-Code skill-wrapper (`.claude/skills/<kebab>/SKILL.md`) is a
**mechanically generated derived artifact**, never hand-authored. It is
the thin, CC-discoverable proxy that lets Claude Code inject a skill
into the available-skills system-reminder for proactive discovery; it
carries no methodology — the SoT is `skills/<dir>/SKILL.md`.

- **Generator (sole SoT writer):**
  `scripts/generate_skill_wrappers.py`. Reads `skills/*/SKILL.md`
  frontmatter, writes only under `.claude/skills/`. Byte-identical
  on re-run (idempotent); orphan wrappers (source skill gone or no
  longer eligible) are removed. Mirrors the
  `generate_skill_map.py` generator+validator split. CLI:
  default = write, `--check` = verify-only, non-zero exit on drift.
- **Validator:** `consistency_check` check 10 (wrapper drift) —
  mechanically `generate_skill_wrappers.py --check`.
- **Inclusion predicate** (frontmatter-derived, no hand list).
  A skill is wrapper-eligible iff:
  - `status` not in {archived, deprecated}, AND (`archived` is a
    defensive guard for a retired/non-status value — see `framework/skill-anatomy-frontmatter.md` §status, not a
    status authors set)
  - `disable-model-invocation` != true, AND
  - ( `invocation.primary` in {user-facing, cross-cutting}
    OR `cc_wrapper: true` ), AND
  - `cc_wrapper` != false.

  `cc_wrapper` is the override-only escape hatch (see field
  definition in `framework/skill-anatomy-frontmatter.md`); absent ⇒ the implicit `invocation.primary` rule
  decides.
- **Plugin-listed skills:** the repository's set leaves out every skill
  `.claude-plugin/plugin.json` lists; the plugin lists it as `forge:<name>`, and a wrapper would show it twice in a
  session in this checkout. The Codex / `--framework-root` set keeps them. An unreadable manifest is a hard error.
- **Failure modes:** malformed/missing frontmatter ⇒ skip + stderr
  warning, continue (no crash); two eligible skills normalizing to
  the same kebab name ⇒ hard error, non-zero exit, NO partial
  write; `cc_wrapper` non-bool ⇒ hard error, non-zero exit.
- **Description normalization:** the wrapper `description` is
  token-normalized, not byte-copied. YAML block scalars (`|`, `>`)
  are collapsed to a single line and runs of inter-token whitespace
  are squeezed to one space; the trigger tokens themselves are
  preserved verbatim, so discovery (which is token-level) is
  unaffected. This is by design — the contract is token-level
  preservation, not literal-formatting preservation.
- **Distribution:** the public release includes the committed, generated
  wrappers from `.claude/skills/`. Skills installed there by the host
  stay local. Hand-edits are reverted on the next generator run and
  flagged by `consistency_check`.

---

## Verification — what hooks check vs not

### Mechanical checks

Pre-commit check 7 (`scripts/skill_fm_validate.py`) over active
`skills/**/SKILL.md` excluding archives:
1. YAML validity
2. required fields
3. `invocation.primary` vocabulary
4. `invocation.secondary` list format (warn-level)
5. `disable-model-invocation` bool semantics
6. `modes` list semantics
7. mode count warning (>3)

`generate_skill_map.py` maintains AUTO block in `framework/skill-map.md`.
Canonical section names are used by consistency checks.

`generate_skill_wrappers.py` maintains the CC skill-wrapper set under
`.claude/skills/` (derived artifact, see §Wrapper). Drift is caught by
`consistency_check` check 10 (`generate_skill_wrappers.py --check`).

### Generator output strategy

`framework/skill-map.md` remains mixed:
only marker-delimited block is generated,
rest stays manual until explicit extraction.

### Not checked mechanically (review discipline)

- section quality
- ontology quality
- standalone argument quality
- discovery quality of description
- mode convention quality
- naming quality

Principle: hooks catch schema drift, reviews catch content drift.

---
