# Skill Anatomy — frontmatter field definitions

Step-loaded unit of `framework/skill-anatomy.md`. Read it when writing or changing a skill's frontmatter (`name`,
`description`, `status`, `invocation`, `disable-model-invocation`, `cc_wrapper`, `modes`, `relevant_for`) and when a
SKILL-FM-VALIDATE finding on a field is handled. The schema block itself stays in the core (§Frontmatter schema).

### Field definitions

#### `name`
The skill identifier — and **part of the trigger surface**: Claude uses
the `name` *and* `description` to decide whether to invoke a skill
(Anthropic skill best-practices), so a clear, distinct name raises
`P(invoked)` — the failure mode at scale is wrong-skill selection between
*similar* names (e.g. `task-creation` vs `task-status-update`).

**Convention — `kebab-case`** (lowercase letters, digits, hyphens only),
per Anthropic's `name`-field spec; the generated CC wrapper name (the
actual discovery surface) is kebab-normalized regardless. Prefer a
**descriptive** form — gerund (`processing-pdfs`) or noun-phrase
(`pdf-processing`); avoid vague/generic (`helper`, `utils`, `data`). The
skill *directory* stays `snake_case` (forge-internal); name + directory
harmonize under `-`/`_` normalization. (This supersedes an earlier
"snake OR kebab" convention and a proposed snake_case-the-name
normalization: the discovery name is kebab by spec, so a snake
source-field buys nothing for triggering.)

#### `description`
The skill's **discovery + invocation surface**: the model reads only
`name + description` from `available_skills` to decide whether to invoke
the skill — the body is NOT loaded until after the trigger fires. So the
description is an interface contract for an **automated consumer** (the
trigger-selection mechanism), and its job is to maximise *correct*
`P(invoked)`: the right agent reaches for this skill at the right moment,
and does NOT reach for it on a near-miss. That automated consumer is the
majority case — the framework leans on capability-driven tool use (an
autonomous agent reaches for a skill by reading its description, not
because a caller hardcoded the invocation), so description quality gates
how far the framework can rely on capability + tools instead of scripted
control flow. User-typed invocation is the minority.

**Content rule — three parts, nothing else:**
1. **what the skill does** — one phrase.
2. **when to trigger** — name the situations/contexts explicitly, a
   little "pushy" against *under*-triggering, so the agent reaches for the
   skill even when the caller won't say its noun. Bound: for an
   orchestrator a *spurious* fire has a real cost (a burned turn +
   context, a mis-routed delegation), so pushiness is capped by near-miss
   precision — recall on genuine under-coverage, NOT maximal firing. (The
   "under-triggering is the only cost" framing is end-user-app guidance;
   an orchestrator pays both ways.)
3. **when NOT to trigger** — the near-miss exclusions (adjacent cases that
   share keywords but need a different skill). For an orchestrator this is
   the **primary lever**, not an afterthought: it prevents the cross-skill
   confusion pushiness would otherwise cause (e.g. `task_creation` vs
   `task_status_update` share the whole task-noun surface).

Everything else — motivation, mode-internals, mechanism-detail,
quality-claims — belongs in the **body**, never the trigger surface: at
invocation time the body is not loaded, so that content is dead weight
AND it dilutes the trigger signal. Budget for the *trimmed* form: after
cutting to the three parts, expect ~30–60 words; >100 is almost always
un-cut bloat (the soft ~100-word metadata ceiling does NOT discriminate —
a bloated description can sit right at it). Trimming is a side-effect of
the rule, not its aim — the aim is signal for `P(invoked)`.

**Two worked transforms (the exact corpus failure shapes):**
- *mode-enumeration* (`council`): drop the per-mode member breakdown
  ("(a) light — 3 members + chief … (d) interactive …") to "(light /
  standard / full / interactive modes)" — the composition is body content.
- *quality-claim filler* (`task_creation`): delete "Task quality
  determines downstream quality" outright — it serves no trigger decision.

**Carve-out — not every skill needs trigger-optimization.** A skill whose
`invocation.primary` is `workflow-step` or `hook`, or that sets
`disable-model-invocation: true`, is invoked by runbook position /
explicit call, not by `P(invoked)`. Its description still needs a C3
marker and must not MIS-trigger elsewhere, but it is exempt from
pull-optimization — the marker is met by a positional note, not
eval-tuning. (The majority of skills ARE discovery-invoked by autonomous
agents; the exemption is the few genuinely positional ones, not a loophole.)

**Enforced (schema only — presence, not quality):** for `status: active`
skills the `description` MUST contain one of `Use when` / `Triggers when`
/ `Trigger:` (closed set, case-insensitive substring). Mechanical
surface: C3 WARN in `scripts/skill_fm_validate.py` (pre-commit Check 3).
The C3 check proves the trigger STRING is present — it does NOT measure
trigger *efficacy* (whether the description actually invokes when it
should, and only then). Efficacy is **measurable in principle** — run the
real trigger decision N× over should / should-not queries and score on a
held-out split — but the tool that does it (the skill-creator `run_loop.py`
optimizer) is **external and unpinned** (not framework-owned, model-id-
dependent). So measurement is a **SHOULD-when-available**, not a mandated
gate: where the optimizer is present, measure on author/change (an insider
review cannot see the cold trigger decision); where it is not, the
NOT-clause + near-miss judgment is the manual fallback. Method, honest
bounds, and corpus-scale staging: `framework/skill-description-optimization.md`.

#### `status`
- `active`
- `draft`
- `deprecated` (kept in tree for one release cycle, then removed via git history)

The three above are the only values an author sets. The wrapper-eligibility
predicate (`framework/skill-anatomy-wrapper-and-checks.md` §Wrapper) *additionally* excludes a retired `archived` token as a
defensive guard (tested) — it is NOT a status value, so its appearance there
is belt-and-suspenders, not a contradiction with this enum.

#### `invocation`
`invocation.primary` (required, exactly one):
- `user-facing`
- `workflow-step`
- `sub-skill`
- `hook`
- `cross-cutting`

`invocation.secondary` (optional list): additional call paths,
format `<path>` or `<path>:<modifier>`.

`invocation.trigger_patterns` (optional, user-facing only):
example user triggers.

Vocabulary is strict for `primary`; extend only via spec update + hook allowlist.
`secondary` remains documentation-level, not strict-validated.

#### `disable-model-invocation`
- `true`: hidden from auto-discovery, explicit-only
- `false` default: in discovery pool

Even if runtime ignores it, pre-commit + generators + Buddy logic use it.

#### `cc_wrapper` (optional)
Override-only bool for the CC skill-wrapper inclusion predicate
(see `framework/skill-anatomy-wrapper-and-checks.md` §Wrapper — required derived artifact). **Absent ⇒ the implicit
rule decides** — do not set it just to restate the implicit result.

- `cc_wrapper: true` — force a wrapper even when the implicit rule
  would not emit one (e.g. a `workflow-step` skill that still
  benefits from proactive discovery, like `code_review_board` /
  `get_api_docs`).
- `cc_wrapper: false` — suppress a wrapper the implicit rule would
  emit (opt a `user-facing`/`cross-cutting` skill out of CC
  discovery / out of the public mirror).

Type-strict: any non-bool value is a hard generator error
(non-zero exit, no wrapper written).

#### `modes`
Optional for multimodal skills. Monomodal: omit field.

#### `relevant_for` (optional)
Agent-skill awareness auto-inject list for participating agents.
Generator/validator: `scripts/generate_agent_skill_map.py` + check 10.

```yaml
relevant_for: ["main-code-agent"]
relevant_for: ["main-code-agent", "tester"]
relevant_for: ["*"]
# field absent = no auto-inject
```

Rules of thumb:
- MCA-relevant: implementation/fix helper skills
- tester-relevant: testing methodology
- solution-expert: decision support skills
- wildcard: truly universal only (`transparency_header`)

Workflow YAML maintenance remains complementary and mostly mental discipline.

### What is removed from frontmatter

| Old | Why removed |
|---|---|
| `type: workflow|capability|utility|protocol` | non-orthogonal, replaced by invocation |
| `phase_in` | overlaps with invocation.secondary |
| `uses` | stays as doc field, not strict schema validation |

---
