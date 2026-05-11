# Concepts

## Maturity promotion (digital-gardening principle)

Knowledge matures in three stages. The stage determines where information lives and how it is treated:

| Stage | Means | Lives in | Promotion trigger |
|-------|-------|----------|-------------------|
| **seed** | Raw capture — single fact, not processed against knowledge | history entry, checkpoint note, task comment | IMPACT CHAIN run → sprout |
| **sprout** | Processed — IMPACT CHAIN ran, in detail file | detail files (e.g. `hosts/<hostname>.md`) | curation decision → evergreen |
| **evergreen** | Curated — promoted into overview.md | `overview.md` of an area | degradation when overview.md is full |

**Degradation (evergreen → sprout):** the 200-line limit of overview.md is the trigger. overview.md full + new candidate → degrade the oldest, least-referenced, or item rendered obsolete by something newer.

**Pre-Brain:** stages are implicit — position IS the stage (history = seed, detail = sprout, overview = evergreen). On every write knowledge-processor decides: overview-worthy or detail-worthy?

**Post-Brain:** `maturity: seed | sprout | evergreen` as a field in `brain_entries`. Promotion is explicitly triggered. Buddy can deliberately trigger context promotion.

## Entropy Audit

Systems become stale even without events. Certificates expire, versions change, services are migrated — without an agent observing it. Brain Logic (event-driven) does not catch that.

### At boot (Pre-Brain)

After loading context, Buddy runs a mechanical audit.
5 checks, binary (PASS/FLAG). On FLAG: fix immediately before normal work begins.

**Check 1 — history-context consistency:**
Read the last 2 history entries. For every claim describing a context state
(e.g. "Nextcloud migrated", "Task 041 done"): check whether the current context
reflects it. Contradiction → FLAG.
```bash
# Find the last 2 history files:
ls -t context/history/*.md | head -2
```

**Check 2 — state-area staleness:**
Persistent state-area files under `<active-context>/` (e.g. infrastructure
overviews, machine state, deploy state): read the "Last verification" header.
Older than 14 days → FLAG. No date → FLAG ("state unknown", DR-4).
```bash
# Example pattern (consumer repo adapts this):
for f in context/*/overview.md; do
  [ -f "$f" ] && head -5 "$f" | grep -i "verification\|verified\|updated"
done
```

**Check 4 — backlog corpses:**
Scan `docs/plan.yaml`. Tasks with `Status: in_progress` whose `updated` date
is older than 7 days → FLAG (potentially stuck or forgotten).
```bash
grep -B2 "Status: in_progress" docs/plan.yaml
# Then check the updated date in the corresponding YAML
```

**Check 5 — hook consistency:**
Read `docs/plan_engine --boot`. If not idle: check the referenced task in
the workflow checklist. Hook step ≠ checklist step → FLAG.
(Reconciliation rule: checklist wins, see `framework/agent-patterns.md`.)

### Proof block (MUST)

```
Entropy Audit:
  C1 history-context:  PASS / FLAG — [detail]
  C2 session-handoff:  PASS / FLAG — [age: Xh]
  C3 state areas:      PASS / FLAG — [which area, age]
  C4 backlog corpses:  PASS / FLAG — [task IDs]
  Result: CLEAN / [N] FLAGS — [immediate actions]
```

Without this proof block the Entropy Audit counts as not executed.

On FLAGS: correct BEFORE normal work. Every FLAG is a SIGNAL —
why did Brain Logic (7e) not catch this in the previous session?
If systemic: backlog entry.

### Later (Brain + Harness)

- Heartbeat + APScheduler triggers periodic area audits
- Brain entries with temporal fields (valid_until) are checked automatically
- Proactive verification: system SSHes onto servers and compares live state with context

## session-buffer relationship

knowledge_processor is invoked along two paths:

```
New information arises
  |
Is the routing target unambiguously clear?
  → Yes: single fact, unambiguous context area
    → call knowledge_processor directly (T1 path, mode=process)
  → No: ambiguous input, multi-topic, nuance
    → write to session-buffer (capture, zero friction)
    → CC SessionEnd hook (Task 161 Tier-1) extracts PENDING, calls knowledge_processor
```

**When direct (T1):** clear fact with unambiguous target, Agent Check 7e with unambiguous information, task status change.

**When via session-buffer (T2+):** unstructured multi-point input, agent return with nuance, multi-dispatch, or when unclear.

knowledge_processor is and remains the only path for context writes (exceptions: decisions.md, context/user/notes.md). EXTRACT → IMPACT CHAIN → SIGNAL CHECK runs every time. No bypass.

## Unloading after write

After every context write, check whether the topic can be unloaded. Criteria: fully persisted, no open thread, no PENDING entries on the same topic. If yes: "Topic X persisted, from now on read from file."
