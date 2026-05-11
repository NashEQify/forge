# Mode: user-signal (User Model)

Guardrails (delta check, write-quality gate, unloading) apply — see SKILL.md.

Invoked when 7f USER-SIGNAL detects information about the user (life mode only). Dispatcher routes type=USER here.

## Decay thresholds (named constants)

```
DECAY_ROLE_EMERGING      = 6 months
DECAY_ROLE_GROWING       = 12 months
DECAY_COMPETENCE_EMERGING = 3 months
DECAY_COMPETENCE_GROWING  = 6 months
DECAY_GOAL_EMERGING      = 3 months
DECAY_GOAL_GROWING       = 6 months
DECAY_INTEREST_EMERGING  = 4 weeks
DECAY_INTEREST_GROWING   = 3 months
DECAY_CONCERN_EMERGING   = 2 weeks
DECAY_CONCERN_GROWING    = 6 weeks
DECAY_CONCERN_STABLE     = 3 months
DECAY_QUESTION_EMERGING  = 2 weeks
DECAY_QUESTION_GROWING   = 4 weeks
DECAY_STANCE_EMERGING    = 3 months
DECAY_STANCE_GROWING     = 6 months
```

Layer 1 and stable entries in layers 2-3 are immune (only invalidated via CONTRADICTS).

## Inputs

- **information:** what was observed
- **facet:** from 7f classification (INTEREST, CONCERN, TRAIT, etc.). If UNKNOWN → CLASSIFY decides.
- **source_quality:** observed (the user said it) / inferred (derived)

## Steps

### 1. CLASSIFY

Determine facet + layer (if not set by the dispatcher). Tiered strategy:

- **Tier 1 — unambiguous:** classify. No further questioning.
- **Tier 2 — ambiguous:** default hierarchy: CONCERN > INTEREST. Entry with [confidence:medium]. Pattern recognition: worry words → CONCERN, curiosity words → INTEREST.
- **Tier 3 — entry with [confidence:medium] reappears:** ask immediately. User answer → confidence:high.

Layer 6 (MOOD, ENERGY, STRESSOR, EXPERIENCE)? → session buffer only, no file write, STOP. Exception: reinforces an existing layer-4/5 signal.

Immediate-stable rule: layer 1-2 + observed → trajectory=stable. permanence=permanent + observed → stable. Importance assessment: signal strength, permanence, context → trajectory transition due?

### 2. LOCATE

Does an entry for this signal exist?
- Layers 1-3: read profile.md (MUST)
- Layers 4-5: read inner-life.md (MUST)
- Search: facet type + name/topic

Found → 3a (UPDATE). Not found → 3b (CREATE).

### 3a. UPDATE

- increment observation_count (obs:N → obs:N+1)
- update last_seen
- Trajectory: LLM judges whether transition is due (emerging → growing? growing → stable?)
- If [confidence:medium] reappears → questioning trigger (tier 3)
- Delta check (MUST) + write-quality gate (MUST)

### 3b. CREATE

- Immediate-stable? → entry with [stable]
- Otherwise: [emerging since <date>, obs:1]
- Target file: layers 1-3 → profile.md, layers 4-5 → inner-life.md
- Set inline connection markers when a relationship is recognisable: [← cause], [→ goal], [DRIVES → X]

### 4. IMPACT CHAIN (proportional)

User-model-specific variant. Underlying logic of the standard IMPACT CHAIN: see `modes/process.md` step 2.

LOCATE:
- ALWAYS: read the other user-model file (when writing inner-life.md → profile.md, and vice versa)
- ALWAYS: read connections.md
- FOR CONCERN/GOAL: check active task files
- FOR CONTRADICTS: Buddy asks the user

ASSESS:
- INTENSIFIED_BY: does the new entry reinforce an existing signal?
- RESOLVED_BY: does it resolve an existing signal?
- CONTRADICTS: does it contradict? → Buddy asks (change of mind vs. different context)

ACT:
- update affected entries

### 5. CONNECT

Only when a connection is RECOGNISED — not mechanically on every write. Read connections.md, existing connection → skip/update. New connection → entry: `- --<EDGE>--> <TARGET> [confidence:<level>, since <date>]`. Set inline markers in inner-life.md/profile.md.

### 6. REPORT

```
User Model (mode=user-signal): [FACET:Name] obs:N→M, trajectory:X.
Connection: [Source] --EDGE--> [Target] (new/updated).
```

## Decay check (user-triggered)

Trigger: user says "decay check" or "trajectory audit".

```
1. Read inner-life.md fully
2. For every entry:
   a. compute time_since_last_seen
   b. look up decay_threshold (named constants above)
   c. time < threshold → skip
   d. time >= threshold → LLM assessment:
      "Is [facet:name] still active despite [X] without mention?
       Context: [active tasks, commitments, life circumstances from profile.md]"
      → plausibly active: keep
      → not plausible: trajectory → fading
      → already fading + 2× threshold: → dormant
      → already dormant + 3× threshold: → remove (history retains the trace)
3. Promotion check (trajectory=stable):
   LLM: "Does [signal] belong to identity? Should it move into profile.md?"
   → yes: promotion (profile.md write, mark in inner-life.md, connections.md promotion history)
4. 200-line check: inner-life.md > 180 lines?
   → remove dormant immediately, remove fading with obs < 3
5. connections.md hygiene:
   connections whose source/target was removed → remove
   resolved > 6 months → remove
```
