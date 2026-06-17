# Protocol: Discourse

Shared cross-validation protocol for all board skills.
Referenced by: spec_board (incl. mode=ux), code_review_board,
sectional_deep_review, impl_plan_review, council.

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
| CHALLENGED, not rebutted | -1 (removal candidate — see Rules) |
| CONNECTED | +1, root-cause group |
| SURFACED | standard |

## Rules

- One round (no ping-pong).
- Max 5 discourse points per agent.
- **Malformed discourse points are dropped** (format-enforcement, not
  an evidence-quality judgement): a CHALLENGE carrying no
  counter-evidence, or a SURFACE carrying no evidence, is not a
  well-formed discourse point (Step 3 requires counter-evidence /
  full format) → dropped. This is a structural check on the discourse
  *entry*, NOT the chief re-judging a well-formed finding's evidence
  quality (which the consuming board chief's role-constraint bars).
- **Removal / downgrade rests on a reviewer surface, never on
  absence.** "CHALLENGED, not rebutted → -1" means the *challenger's*
  counter-evidence surface stands un-rebutted — that surface is the
  basis the consuming board's chief cites to refute (per that chief's
  own consolidation role-constraint). The original author's *silence* is not
  itself the basis; a challenge with no counter-evidence was already
  dropped one rule up, so absence alone can never drive a removal.
- "No discourse points." is explicitly allowed.
- Input = ALL individual findings with attribution, NOT the
  consolidated set.
