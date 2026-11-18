# Improve codebase architecture — process

Step-loaded unit of `skills/improve_codebase_architecture/SKILL.md`. Read it when starting the codebase walk, and
follow it through Phase 1 (explore), Phase 2 (present candidates) and Phase 3 (grilling loop once the user picks a
candidate). Use the strict glossary in `glossary.md` throughout.

## Process

### Phase 1: Explore

Read the project's domain glossary (CONTEXT.md if it exists)
and any ADRs in the area you're touching first.

Then use the Agent tool with `subagent_type=Explore` (CC
native) to walk through the codebase. Don't follow rigid
heuristics — explore **organically** and note where you
experience friction:

- Where does understanding one concept require bouncing
  between many small modules?
- Where are modules **shallow** — interface nearly as complex
  as implementation?
- Where were pure functions extracted just-for-testability,
  but the real bugs hide in HOW they are called (no
  **locality**)?
- Where do tightly coupled modules leak across their seams?
- Which parts of the codebase are untested or
  hard-to-test through their current interface?

**Apply the deletion test** to anything you suspect is
shallow: would deletion concentrate complexity or just shift
it? A "yes, it concentrates" is the signal you want.

### Phase 2: present candidates

Present a numbered list of deepening opportunities. Per
candidate:

- **Files** — which files / modules are involved.
- **Problem** — why the current architecture causes friction
  (use the glossary: shallow / leaky seam / no locality /
  etc).
- **Solution** — plain-English description of what would
  change.
- **Benefits** — explained in terms of **locality** +
  **leverage**, and how tests get better.

**Use CONTEXT.md vocabulary for the domain, and the strict
glossary for the architecture.** When `CONTEXT.md` (if
present) defines "Order", talk about "the Order intake
**module**" — not "the FooBarHandler", not "the Order
**service**".

**ADR conflicts:** when a candidate contradicts an existing
ADR, only surface it when the friction is real enough to
revisit the ADR. Mark clearly (e.g. *"contradicts ADR-0007 —
but worth reopening because…"*). Don't list every theoretical
refactor an ADR forbids.

**Important:** do NOT propose interfaces yet. Ask the user:
*"Which of these opportunities do you want to explore?"*

### Phase 3: grilling loop

Once the user picks a candidate, drop into a grilling
conversation. Walk the design tree with them — constraints /
dependencies / the shape of the deepened module / what sits
behind the seam / which tests survive.

**Side effects happen inline as decisions crystallize:**

- **Naming a deepened module after a concept that isn't in
  `CONTEXT.md`?** Add the term to CONTEXT.md (lazy-create if
  the file doesn't exist). Same discipline as the
  `grill-with-docs` pattern.

- **Sharpening a fuzzy term during the conversation?** Update
  CONTEXT.md right there.

- **User rejected the candidate with a load-bearing reason?**
  Offer an ADR, framed as: *"Want me to record this as an ADR
  so future architecture reviews don't re-suggest it?"* Only
  offer if:
  1. **Hard to reverse** (cost meaningful).
  2. **Surprising without context** (a future reader asks
     "why this way?").
  3. **Result of a real trade-off** (genuine alternatives,
     picked one for specific reasons).

  When any of the three are missing → skip the ADR.
  Cross-ref `documentation_and_adrs` for ADR format. The
  ADR-discipline triple also governs `knowledge_capture`
  decision entries.

- **Want to explore alternative interfaces for the deepened
  module?** → cross-ref
  `skills/api_and_interface_design/authoring.md` phase 3
  contract-first.
