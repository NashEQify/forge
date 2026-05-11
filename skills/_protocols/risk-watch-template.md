# Protocol: risk-watch register template

Append-only register format for `target: watch_item` entries from
chief verdicts (per spec 306 §4.7 and `skills/risk_followup_routing/SKILL.md`).

**SoT:** `docs/specs/306-brief-architect.md` §4.7.

The framework provides this template; the consumer instantiates a
`context/risk-watch.md` (or equivalent path) when its first
`watch_item` lands. The instance is owned by the consumer, not the
framework.

---

## File template

Path: `context/risk-watch.md` (consumer-owned)

```markdown
# Risk Watch

Forward-looking risks that fire only on a future trigger. Per
spec 306 §4.7. Append-only — entries are never removed; resolved
risks are marked `resolved: <date> — <one-line rationale>`.

## Format per entry

```yaml
- id: <finding-id from chief verdict>
  severity: <low | medium | high | high_future>
  added: <YYYY-MM-DD>
  verdict_ref: <path to chief verdict that flagged the watch_item>
  trigger_condition: <one-sentence description of what would make
    this risk fire>
  proposed_action_when_fires: <one-sentence description of what
    to do if the trigger condition is met>
  resolved: <null | YYYY-MM-DD with rationale>
```

## Entries
```

(Initial state has the header and the format block; entries
accumulate as chief verdicts emit `target: watch_item` findings.)

---

## Append protocol

When `risk-followup-routing` (per `skills/risk_followup_routing/SKILL.md`)
sees a `target: watch_item` entry, it appends the entry verbatim
under `## Entries` of the consumer's `context/risk-watch.md`. No
mutation of existing entries.

If the file does not exist at append time, the routing skill
creates it from this template and then appends the first entry.

---

## Resolution protocol (manual, human-driven)

When a watch_item's trigger_condition is observed (e.g., the
foreseen middleware is actually introduced):

1. Find the entry by `id`.
2. Add `resolved: <YYYY-MM-DD> — <one-line rationale>` to the
   entry.
3. Apply the `proposed_action_when_fires` (typically: file a
   follow-up task, or amend a spec, or escalate to council).

Resolved entries stay in the file (append-only); they are not
deleted.

---

## Anti-patterns

- **Editing existing entries to update severity / proposed_action.**
  The chief verdict was the SoT at the time. New information about
  the same risk warrants a new entry referencing the old by `id`,
  NOT mutation of the original.
- **Removing resolved entries** to "keep the file short". The
  audit trail is the value. File length is not a constraint.
- **Adding entries by hand** outside the routing-skill flow. All
  entries should originate from a chief verdict. Hand-added items
  bypass the discipline that makes the watch register meaningful.
