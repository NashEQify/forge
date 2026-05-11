# Protocol: Discourse

Shared cross-validation protocol for all board skills.
Referenced by: spec_board (incl. mode=ux), code_review_board.

## When

- **Deep board:** ALWAYS after chief consolidation (every pass).
- **Standard board:** optional (Buddy decides, proportional to
  risk).
- **UX board:** optional (Buddy decides).

## 5-step flow

**Step 1: Compile** — Buddy collects ALL individual review files
(NOT consolidated).

**Step 2: Present All Findings** — structured overview with
attribution:

```markdown
## All Findings for Discourse

### From {role} ({finding-ids}):
1. {ID}: {short description} - {Severity}
...
```

**Step 3: Spawn Discourse Tasks** — one discourse task per agent:

```markdown
# Discourse Task: {role}

## Your original findings
{your own findings}

## Findings from all other reviewers
{all others, with attribution}

## Questions for Other Reviewers
{collected questions}

## Brief
React to other reviewers' findings. Syntax:

AGREE [reviewer] [finding-id]       — rationale + your own evidence
CHALLENGE [reviewer] [finding-id]   — concrete counter-argument with proof
CONNECT [own-id] → [reviewer] [id]  — relationship; shared root cause?
SURFACE                              — new finding in full format
QUESTION                             — clarifying question, not a finding

Constructive. Challenge with reasoning, not dismissal.
```

**Step 4: Collect Responses** — one discourse file per agent.

**Step 5: Compile Results + Confidence Adjustment:**

```markdown
# Discourse Results

## Consensus (high confidence)
- {Finding} — agreed by: {agent list}

## Challenged Findings
- {Finding} ({reviewer}) — challenged by {agent}
  Reason: {counter-argument} | Resolution: confirmed | false positive | downgraded

## Connected Findings
- {Finding group} → root cause: {description}

## Surfaced in Discourse
- {New finding} (from {agent})
```

| Outcome | Confidence |
|----------|-----------|
| Multiple AGREE | +1 (very high) |
| CHALLENGED + defended | +1 |
| CHALLENGED, not defended | -1 (consider removal) |
| CONNECTED | +1, root-cause group |
| SURFACED | standard |

## Rules

- One round (no ping-pong).
- Max 5 discourse points per agent.
- CHALLENGE without counter-evidence → ignored.
- SURFACE without evidence → ignored.
- "No discourse points." is explicitly allowed.
- Input = ALL individual findings with attribution, NOT the
  consolidated set.
