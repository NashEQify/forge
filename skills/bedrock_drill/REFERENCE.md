# bedrock_drill — REFERENCE

Detail mechanics for SKILL.md: algorithm, scoring, bedrock rules,
integrity check, unseen assumptions, examples.

## Algorithm — Phase 1 pseudocode

```
FUNCTION drill(problem, path_list=[], depth=0):
  1. Reformulate problem (more precise than input)
  2. Assign core label (3-5 words, concept fingerprint)
  3. Cycle check: core label in path_list?
     YES -> STOP + "Semantic cycle: [label]"
  4. path_list = path_list + [core_label]
  5. Identify assumptions (min 2, explicit + implicit)
  6. Per assumption:
     a. Bedrock? -> decision rule (§Bedrock) + AMG proof -> mark
     b. Drillable -> score = uncertainty + reach (§Scoring)
  7. Relevance check: "New info on the original problem?" NO -> terminate
  8. Pruning: focused top-1, broad top-2, exhaustive all
  9. IF depth < max_depth AND drillable available:
     -> drill(assumption, path_list, depth+1) per chosen one
  10. ELSE: branch terminates
  11. On backtrack: remove the last label from path_list
```

## Scoring rubric (Phase 1 Step 6b)

| Dimension | low (1) | med (2) | high (3) |
|-----------|---------|---------|----------|
| **Uncertainty** | Well attested, consensus, empirical | Plausible but unverified | Speculative, contradictory |
| **Reach** | Local branch, little depends | 2-3 conclusions depend | Tips much above it, foundation |

Score = uncertainty + reach (range 2-6). Highest gets drilled.
Tie: closer to the original problem preferred.

**Example scoring:**
- "Python is the right language" — U: low(1), R: high(3) -> **4**
- "Vector search is enough for retrieval" — U: high(3), R: high(3) -> **6** <- drilled
- "Users want CLI" — U: med(2), R: low(1) -> **3** (pruned in focused)

## Bedrock decision rules (Phase 1 Step 6a)

| Type | EXACTLY when | Positive example | Negative example |
|------|--------------|------------------|------------------|
| **Physics/empirics** | Value verifiable by external measurement | "Latency is 200ms" | "Latency is acceptable" (judgement) |
| **Logic/maths** | Follows logically necessarily from definitions | "A ∧ ¬A is false" | "Simplicity is better" (preference) |
| **Chosen value** | Preference setting that could be otherwise | "Sovereignty" | "HTTPS encrypts" (fact) |

**None of the above ->** not bedrock, drill further.
**Diversity check:** actively check all 3 types — especially logic/maths
is often overlooked (definitions, tautologies, mathematical limits).
analysis-mode-gate proof sentence on every classification (judgement call).

## Unseen Assumptions prompt (Phase 2 Step 6)

**Mandatory** after the bedrock map. Wording: "Which assumptions are missing because they are too
self-evident? What would someone from a different context see differently?"
Output section: `## Blind spots (user input)`. User adds -> new
nodes in the axiom tree. No input -> "none added", the prompt must still
be issued. Phase 1 finds only assumptions that the training corpus knows
as such. Civilisational defaults are structurally invisible.

## Phase 3 Pre-Step: Re-read the original problem. The derivation answers the
QUESTION ASKED, not a drift variant.

## Derivation Integrity Check (Phase 3 Step 4)
3 hard-coded questions per synthesis layer:

| # | Question | PASS when | FAIL when |
|---|----------|-----------|-----------|
| Q1 | "Does Y follow logically from X, or is this a leap?" | Causal/logical link nameable | The link is an assertion without grounds |
| Q2 | "Contradiction between Y and another branch?" | No contradiction or resolved | Contradiction stands |
| Q3 | "Name a concrete reason why Y might NOT follow from X." | Counter-reason exists but is refutable (1 sentence) | Counter-reason is solid and not refutable |

Per question: PASS/FAIL + one-sentence justification. Revision: reformulate Y,
all 3 again. **Post-revision counter-check (mandatory):** "How exactly
does the revision address the counter-reason [original Q3]?" — 1 sentence. If
the answer only splits the question without resolving it -> another
revision. Max 2/layer. 3rd FAIL -> escalate to user.
**State the self-critique limitation explicitly in the output.**

## Core-label convention

3-5 words concept fingerprint. The path list keeps all labels of the
recursion path, extending/trimming on drill(). E.g.: "Sovereignty-as-Core-Value".

## Axiom-tree output template

```
## Axiom Tree
- [L0] "Original problem" (core: <label>)
  - [L1] Assumption A (score: 5, status: drilled)
    - [L2] Sub-A.1 (bedrock:value) YOUR CHOICE: "<value>"
    - [L2] Sub-A.2 (score: 3, pruned)
  - [L1] Assumption B (bedrock:physics) FACT: "<measurable>"

## Bedrock Map
| Axiom | Type | Justification |
| Sub-A.1 | Value | Preference | B | Physics | Measurable |

## Blind spots (user input)
-> *(user input or "none added")*

## Derivation (L2 -> L1 -> L0)
L2->L1: Given [Sub-A.1]->[A] because [Z]. Q1:PASS|Q2:PASS|Q3:PASS (limitation: self-critique)
L1->L0: Given [A+B]->[answer] because [Z]. Q1-Q3: ...

## Axiom Alternatives
What if Sub-A.1 were different ("no <value>")?
-> Partial: Sub-A.1' -> A' -> answer'. Difference: ...
```

## Example: software (focused, depth 3)

"KG or VectorDB?" -> L0: (A) "Relations > similarity" U:high R:high->6, (B) "Latency <200ms" U:low R:med->3 pruned. Drill A -> L1: (A.1) "Graph traversal needed" U:med R:high->5 drilled -> L2: (A.1.1) "Multi-hop needed" bedrock:physics, (A.1.2) "Sovereignty" bedrock:value YOUR CHOICE. Build-up: multi-hop+self-hosting->KG. Alternative: without sovereignty->managed VectorDB.

## Example: non-software (focused, depth 3)

"Solo: infra or OSS?" -> L0: (B) "OSS = solo distribution" U:high R:high->6. Drill B -> L1: (B.2) "Community feasible solo" U:high R:high->6 -> L2: (B.2.1) "Time suffices" bedrock:physics, (B.2.2) "Community > control" bedrock:value YOUR CHOICE. Build-up: time+community-priority->OSS. Alternative: control-priority->vertical SaaS.
