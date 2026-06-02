# Agent patterns forge hardens against

The typical ways a coding agent goes wrong — the failure modes forge's
workflows are wired to control for. Each entry is the *tendency*, then
how forge catches it.

- **Inherited framing** — an agent picks up the framing it's handed and
  amplifies it, so a wrong premise propagates instead of getting caught.
  *forge:* reviewers start cold, with no shared brief colouring their
  findings.
- **Plausible-but-wrong premise** — the frame sounds right, so nobody
  challenges it. *forge:* an adversary whose whole job is to attack the
  premise.
- **Hand-waving** — findings asserted without evidence. *forge:* every
  finding must cite a file and line.
- **Belief over reality** — the agent trusts its own memory of the code
  over what's actually on disk. *forge:* claims are checked against the
  live state.
- **Local optimisation** — it fixes the local spot and misses the
  system-level break (a producer wired up with no consumer on the other
  end). *forge:* a coherence check at the milestone / architecture
  layer, not just per-file.
- **Prose over engine truth** — it trusts a spec's prose claim about how
  something mechanically behaves instead of the code that implements it.
  *forge:* a mechanical claim must point at the consuming engine, not at
  the prose that asserts it.
- **Bypass by relabelling** — substantial work gets framed as
  "spec-only" or "trivial" to skip the process. *forge:* the workflow
  trigger keys on the substance class, not the label.
- **Format as verification** — "well-formatted, therefore correct."
  *forge:* review weighs substance over presentation.

Each control lives in a skill, persona, or runbook — that is where the
rule actually fires. This page is the map, not the mechanism.
