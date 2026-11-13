# Convergence loop — derive the mechanism, exit on the owner's criterion

Step-loaded unit of `skills/convergence_loop/SKILL.md`. Read it when the Simplify-before-patch decision rule
(`skills/convergence_loop/simplify-before-patch.md`) answers with a drill or records `same_class: yes` (its `defined_by:` field), before declaring a loop on a mechanism with
an owner-approved exit criterion converged, and when such a loop reaches the re-review limit
(`skills/convergence_loop/at-the-cap.md`).

### Why a drill, not another invariant

An invariant over a mechanism the spec never decided closes the combination cells its author thought of. Each fresh
review then finds a new combination cell of the same class, and a second invariant fails the same way. A mechanism
derived from axioms has every cell decided before the fix, so its loop can converge. Many readings taken in place of
the spec (`cause-before-answer.md` §Ruling record) show the same gap from the other side: the spec does not decide the
mechanism, the rulings do.

A mechanism counts as derived when its `§Mechanism-Lifecycle` header carries a `Derived:` line naming the drill record
and the owner's approval of its axioms (`skills/_protocols/mechanism-model-schema.md`); without that line it was never
derived, whatever its matrix holds.

### The drill

1. **Scope:** the mechanism's carriers as its `§Mechanism-Lifecycle` section states them, every cell, reported or not.
2. **Run** `skills/bedrock_drill/SKILL.md` on the question what each cell must do. Its axioms come from owner text (the
   approved acceptance, owner-approved spec clauses, owner decisions quoted with their place) and from logic. A
   derived ruling is input to check against them, never an axiom.
3. **Owner approval:** the axioms and the exit criterion below go to the owner in one batch (the user, or a
   coordinator relaying the user's words with their quote). Until the owner approves, no fix pass runs on the
   mechanism; the wait counts as the ESCALATE of `SKILL.md` §Termination for the re-review limit.
4. **Into the spec:** the spec states the approved axioms; each matrix cell the drill decides cites its axiom; the
   header gets its `Derived:` line (naming the last RL id); every derived ruling on the mechanism is re-read against the axioms, and one they
   contradict is retired in the ruling log. Then the gate's record is written again against the derived matrix (it starts the consecutive `same_class` count
   again), and the class witness takes its axes (`simplify-before-patch.md` §Class witness).

### Derive from the defining unit

A hand-kept copy of semantics another unit defines differs from it in cases nobody listed: each patch adds one listed
case, and the next review finds another. Deriving the copying mechanism cleanly does not help; the gap lies between
the copy and the unit that defines its semantics (the defining unit; not the person who approves a drill).

**When the gate asks.** Only when its record says `same_class: yes` and the failing artifact computes a derived
quantity (a reach, a dependency, an index, a cache, a projection, a second reader or validator); otherwise
`defined_by: n/a`. A first finding never reaches the gate.

**Finding the defining unit.** Checked in this order, the first that holds named with its place:
1. a rules module or other code unit implements the spec section or contract that defines what the quantity
   encodes, and the copy restates its cases (a definition in text with no implementing unit does not count);
2. other code asks that unit for the same answer (a function, predicate set or reader the rest calls);
3. the copy was written beside an earlier implementation of the same answer and kept in step by hand.
None holds: `defined_by: none`, and the gate's other rows decide. The checks cannot decide (two candidates, or one
that covers only part): `defined_by: unsure` with the candidates and what is missing; no fix pass runs on the class
until the caller answers, and the wait counts as the ESCALATE of `SKILL.md` §Termination.

**The answer.** The quantity is computed from the defining unit: one call to its function, its predicate set or its
own reader, with the copy's own cases removed; the fix brief's `mechanism_cells` names the copy's cells as removed.
The defining unit's behaviour is the fixed point: the change reaches the copy and its callers, not what that unit
decides. Where it has no call for the quantity, adding one that reads its existing definitions and changes none of
its outputs (its tests stay unedited and pass) is part of the answer. A copy meant to differ (a stricter validator)
reads through the defining unit and keeps only its stated difference on top, named in the record. A defect the
derivation shows in the defining unit (it contradicts its own spec) is its own finding, with its own cause and pass;
for the inputs it affects the copy is not replaced until that finding is answered, and a known finding of the class
that is really that defect is witnessed there, not by the comparison.

**The comparison.** Before the fix brief, someone other than the implementer writes it without the copy's cases or
the derived function in view (`skills/testing/test-design.md` §Oracle discipline): over the input space the quantity
covers, it gets the quantity by brute force from the defining unit's behaviour (run that unit end to end on each
input and observe, not the call the derivation makes; where only that call exists, it is recorded as weaker) and
checks the derived quantity against it, exhaustively where the space can be enumerated, else as a sampled or property
comparison recorded as weaker with the part it covers. Run against the copy, it turns red every other known finding
of the class. For this answer it replaces the matrix-axis generator as the class witness
(`simplify-before-patch.md` §Class witness); the `class_witness` row's command is followed by `exhaustive` or
`sampled ({covered part})`. Where real data exists, the derived quantity is also compared with the copy's result on
it, each difference explained.

### Exit criterion

A convergence loop on a drilled mechanism ends when the owner-approved exit criterion holds, not when the next fresh
review finds no HIGH. The proposal in step 3 picks the parts the mechanism needs from these:
- **Mutants:** every mutant that a named tool and operator set (both in the record) generates over the mechanism's
  code is killed, or argued equivalent in the record.
- **Owner reference:** an oracle or reference implementation whose expectations come only from owner text; a case it
  cannot decide without a new reading becomes an owner question, not a ruling.
- **Properties:** no silent wrong value (each input yields the derived value or a visible refusal) and totality
  (every matrix cell yields a defined outcome), each as a property over the matrix axes.
- **Closing review:** one review at full breadth, with the seat set of the widest earlier review on the mechanism;
  classes come from the matrix.

Record it in the build log beside the gate's record:

```
- exit_criterion: {parts} — owner: "{quote}" ({where}); state: {part}: met {evidence} | open; …
```

The loop is CONVERGED only when every part is met with its evidence; a review PASS with a part open is not
convergence. An open part with no open finding (surviving mutants, a failing property) is the next fix pass's input,
counted like any other pass. At the re-review limit, an open part goes to the owner as ESCALATE with each part's state; it is never
accepted as a limit. Changing the criterion needs the owner's approval again.
