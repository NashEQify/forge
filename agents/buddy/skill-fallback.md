# Buddy — Skill-invocation fallback

On-demand unit (`agents/buddy/navigation.md` §Moments). Read it when a canonical or utility skill is the required
path but the host cannot invoke it. The core's Applicability holds for software. On demand, follow the project's
working rules.

**Skill-invocation fallback (no CC wrapper / stale mirror):** when a
canonical or utility skill is the required path but is NOT invocable
via the `Skill` tool (absent from the available-skills reminder — no
wrapper yet generated, or the consumer session runs against a mirror
the wrapper hasn't been release-synced to), Buddy MUST read the
neutral SoT `skills/<name>/SKILL.md` and execute its methodology
directly. Do NOT substitute a different skill because it happens to be
discoverable (e.g. never reach for `task_creation` because
`task_status_update` is the required path but unwrapped). Wrappers are
a generated artifact (`generate_skill_wrappers.py`), so this is rare —
but it stays the behavioural net for new or not-yet-propagated skills.
The substitution error is the failure mode; the SoT is always the
ground truth.
