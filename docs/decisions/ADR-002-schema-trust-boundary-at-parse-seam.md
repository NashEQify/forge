# ADR-002: A LOCKED, load-bearing config is validated at one parse-seam trust boundary, not by scattered per-site guards

## Status
Accepted

## Date
2026-05-19

## Context

The task-schema conformance validator (`plan_engine`) parses
`framework/task-schema.yaml` and dereferences it to drive a check
wired into the pre-commit PLAN-VALIDATE BLOCK across the framework
repo **and every consumer repo** (`scope: all_repos`). The schema
file is LOCKED — no intentional content change in normal flow — and
was therefore treated as trusted: the loader returned a `dict` and
every consumer treated "is a dict" as "is a valid schema",
dereferencing nested keys at every depth with ad-hoc `.get()` calls.

Adversarial review found the **same defect class three times, one
nesting level deeper each pass**: a single quoting/merge slip turning
a nested key into the wrong type produced either an uncaught traceback
(crashing the cross-repo commit gate) or a *silent* degrade (a
required-set dropped, a status set emptied, a field's vocabulary
silently unenforced) — in every case with no escalate diagnostic.
Each fix added guards for the level just named; the next review found
the next level. The patch set grows with schema depth, so the
per-site strategy is provably non-convergent.

The root cause is not "a missing guard". It is a **missing trust
boundary**: there was no point where the document transitioned from
*untrusted bytes* to *validated structure*. "LOCKED" constrains
intentional edits; it does not make the bytes uncorruptible in transit
(a botched merge resolution is the realistic vector). Trusted source
≠ trusted bytes.

## Decision

1. **One trust boundary at the parse seam.** A single function
   validates the entire schema document against its expected shape
   immediately after load and before any consumer reads it. Any
   structural defect at any depth produces exactly one
   `SCHEMA_FILE` ERROR + ESCALATE; the tree is never silently passed
   and the process never dies on a raw traceback. The pre-existing
   scattered per-site schema guards are removed (collapsed into the
   boundary); guards for a *different* trust boundary — per-task-file
   input — are retained.

2. **Expected shape is declarative data, walked by a generic
   checker.** The shape is a data structure; a generic walker
   interprets it. Adding schema depth is a data edit, not new
   control flow — so the defense cannot lag the schema the way a
   hand-written `isinstance` ladder does.

3. **No third-party validation dependency.** A meta-schema library
   (e.g. jsonschema) would solve this cleanly but is a runtime
   dependency on the toolchain that gates every consumer repo's
   commit path. That trades a low-probability schema-corruption risk
   for a permanent cross-repo operability/sovereignty liability. The
   pattern is adopted; the dependency is rejected. Standard-library
   only.

4. **Drift anchor.** The shape descriptor is a second structural
   description of a LOCKED file and must not silently diverge from
   it. Two mechanisms: the real schema must itself pass the boundary
   in the self-test (a descriptor/schema disagreement fails loudly),
   and the schema version is pinned so an intentional schema
   evolution forces a conscious descriptor update.

## Alternatives considered

- **A — continue per-site guards.** Rejected: provably
  non-convergent; the patch set scales with schema depth.
- **B — hand-rolled recursive validator with an inline type ladder.**
  Rejected: relocates the same defect class into the validator's own
  branches; the shape stays implicit in code and drifts from the
  file.
- **C — jsonschema / external meta-schema.** Pattern correct,
  dependency rejected: a new runtime dep on the cross-repo commit
  gate is a worse, permanent liability than the risk it removes.
- **D — declarative shape + generic checker + drift anchor
  (chosen).** Total (covers every depth by construction),
  single-boundary, dependency-free, and self-checked against the
  real file.

## Consequences

- Schema corruption at any depth fails safe (one ESCALATE
  diagnostic), never a cross-repo commit-gate crash and never a
  silent strictness loss.
- Adding schema structure later costs a data edit, not new validator
  code; coverage cannot silently lag the schema.
- The shape descriptor is itself a maintained mirror of the LOCKED
  file; the self-test anchor + version pin convert descriptor drift
  from "silent" to "loud test failure".
- **Accepted residual:** the boundary validates structural *type*
  conformance, not *conditional-requiredness* (e.g. an `enum`
  field-def whose value-list key is entirely absent is type-valid
  and passes, after which the consumer silently disables that
  field's vocabulary). This is a distinct category (semantic
  completeness), out of the originating scope, with a human-only
  trigger on the LOCKED file and a bounded consequence. Accepted as
  a documented residual rather than extending the descriptor grammar
  with a conditional-requiredness construct — that path leads back
  toward the constraint-language a full meta-schema library provides
  and was rejected for the same sovereignty reason as alternative C.
  The narrowest future fix, if the trigger ever fires, is a guard at
  the single consuming seam, not a grammar extension. Tracked as a
  forward-looking risk-watch item.

Originating work: task 327 (task-schema generator + validator);
sibling generator+validator pattern recorded in ADR-001.
