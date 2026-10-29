# MCA brief template — verification and pre-lock checks

Step-loaded unit of `skills/_protocols/mca-brief-template.md`. Read it when writing the brief's test and
verification scope (DoD), and before locking a brief that covers several commits, uses a claim trigger formulation,
is reviewed at L2 or touches imports (structural refactor). Lenses, adversaries and chiefs read it when they produce
or check Claim-Verifications rows or 4-link closure claims.

## Test/Verification scope (DoD)

Brief encodes the **selected set** per round, not the full repo suite;
scope and any due broad run follow `skills/testing/run-strategy.md` §Test
selection. When a broad run is due, the brief says which round carries
it and who runs it.

Per-fix DoD:
1. **Selected set** — `python3 "$FRAMEWORK_DIR/scripts/select_tests.py" <changed paths>`
   (from the project root);
   its files, not a `tests/` glob or a hand-picked list.
2. **Cross-pass-binding test** — RED skeleton's test file (where
   applicable) locks the convergence cluster.
3. **Integration smoke** — 0-1 test only if public-API contract or
   spec-defined behaviour touched.
4. **L0** — `ruff check <touched-files> && mypy <touched-files>` —
   touched files only.
5. **Resource-lifecycle audit** (only when the fix introduces a
   pooled/singleton resource carrying a close/teardown/invalidate
   path) — the lifecycle test (`skills/testing/test-design.md`
   §Execution-faithfulness) must EXECUTE build-once/reuse/close-awaits/
   rebuild against a fake matching the INSTALLED SDK surface, AND audit
   whether an autouse reset-fixture masks the singleton (if so, the
   lifecycle test opts out of the reset). A green suite over a
   masked singleton proves nothing about teardown.

**Bind rule:** MCA RETURN-SUMMARY reports per-fix scope (the selector's result
line and files) and, where the round carries it, the broad run,
distinguishing actual execution from inspected reuse with its original producer
and applicability comparison. Retain the checked source boundary, failures,
limits and outstanding obligations. Blanket `pytest tests/` without scope
breakdown = brief-discipline failure. Raw output (full logs, junit, patches,
tree copies) stays in staging or scratch, and the return quotes the decisive
lines (`skills/_protocols/evidence-author-claims.md` §8.4).

---

## Verification-gate cadence

Governs **when** a gate fires — per-commit vs once-at-HEAD. Mandatory
when brief covers multiple commits (strangler, shape-preserving
refactor, sequential moves, ≥5 commits). Single-commit briefs:
implicit (one commit, one gate-set).

**Default cadence:**

| Bug-class shape | Per-commit | Once-at-HEAD |
|---|---|---|
| In-process (start/stop, dep-order, kwarg, fixture-shape, type-check, lint, scope-suite) | `pytest <scope-suite>` + L0 (`ruff <touched> && mypy <touched>`) | — |
| Real-container (reverse-stop on SIGTERM, restart, ansible compose-recreate, real-process signals) | — | `make app-e2e` + targeted real-container test |
| Cross-process / external (Playwright, app-e2e-live, deploy-verify) | — | manual or `make app-e2e-live` post-deploy |

**Rule:** bug-class fully covered by an in-process gate firing per
commit → the heavy external-system gate belongs ONCE at HEAD, not
per commit. Per-commit external gates duplicating in-process
coverage = checklist-tick, no information gain.

**Auto-detection:** `code-architect-lens` axis "over-specified gate
cadence" flags per-commit external-system gates whose bug-class an
in-process gate already covers.

**Bind rule:** brief with ≥5 commits MUST name per gate (per-commit
OR once-at-HEAD) and cite the bug-class shape that justifies the
cadence. Re-author per-commit gates without a named real-container
bug-class to once-at-HEAD.

**Reject the unsafe shortcut:** NOT "skip app-e2e entirely on
strangler refactors". Real-container bug-classes are real; the
release-valve is cadence (once at HEAD), not coverage.

---

## Claim-Verifications (MUST when trigger formulations present)

If any AC, `intent_chain`, or brief section uses one of the trigger
formulations below, the brief MUST include a `## Claim-Verifications`
table with one row per claim:

- **Existing-impl triggers:** `supersedes`, `reuses existing`,
  `already implemented`, `wraps existing`, `delivered in Task`,
  `existing-code verifications confirm`.
- **Spec-citation triggers:** `spec requires X`, `AC says Y`,
  `per <file>.md §Z`, `<file>.md:N`.
- **Cross-producer dedup/collision/reconcile triggers:** any AC/brief
  that dedups, collides, or reconciles facts/events from ≥2 producers
  on a shared key (`reconcile`, `dedup`, `collapse the fork`,
  `more-specific-wins`, `same (key) different (type)`). The check is
  NOT "does the key exist?" but "does the key CO-LOCATE what the two
  producers actually EMIT?" Emit **one row per producer** (≥2 rows):
  for each, grep the *key-assignment site* — the line where that
  producer constructs the value that becomes the shared key (grep the
  key field-name, not a `build_*`/`emit_*` naming convention) — and
  quote the literal value. Then add a **co-location verdict** line: do
  the quoted values land under the SAME key? `FALSIFIED` = they do NOT
  co-locate (the seam is a production no-op). The key is often *derived*
  (`normalize(name)`, a tuple) — quote the value AFTER the derivation
  the seam keys on, not the raw emit. A premise inherited from a
  council/ADR is a claim, not a settled fact.

| Claim | Source-ref | grep command | grep output | Disposition |
|---|---|---|---|---|
| <verbatim claim phrase> | `<file:line>` for spec-cite OR `<scope-path>/` for existing-impl | `grep -n "<pattern>" <target>` | <verbatim stdout OR `(no output)`> | `CONFIRMED` / `FALSIFIED` / `SILENT` |

Disposition values:

- `CONFIRMED` — grep evidence supports the claim
- `FALSIFIED` — zero hits OR hits contradict the claim
- `SILENT` — target exists but doesn't address the claim
  (spec-cite only; escalation flag for council / user)

Producer is `code-architect-lens` (fresh-context-isolated reads
code / spec, runs grep — see lens §Claim-Verifications, single
merged table). Brief-architect copies the verbatim rows. **Adversary
re-verifies at L2 dispatch** per `agents/code-adversary.md`
§Cold-start pre-mission — two-pass author / verifier separation.
SKILL text remains binding; adversary's L2 re-verification is the
load-bearing check.

Any `FALSIFIED` row → brief is INCOMPLETE, return to author for AC
re-scope before MCA dispatch.

### Bind to the resolved seam, not a proxy (verification depth)

A Claim-Verifications row — or any VERIFY / CONFIRM gate that names a seam an
artifact MUST hit — has to resolve to the *runtime binding the claim rests on*,
never a name-match or a runtime symptom that a wrong target also satisfies. Two
recurring proxy-traps; both are the same root (the gate certified a **proxy** of
the obligation, not the obligation at its **real seam**):

- **Existing-impl / DTO-reuse claims → verify at the construction site.** When a
  `reuses existing` row asserts a wire / transport / envelope surface reuses an
  internal or sibling DTO, the grep MUST reach the first-party client / SDK that
  *constructs* the typed envelope — not merely confirm the field or type exists.
  Nominal typing (e.g. Pydantic) rejects a structurally-identical sibling
  instance at construction: field-presence reads GREEN while the constructor is
  RED. A `reuses existing` row whose grep stops at field-presence is SILENT on
  the claim, not CONFIRMED.
- **Test-seam obligations → verify the resolved callee identity.** When a gate
  mandates a test be (re-)pointed at a named production seam and asserts
  execution / `0 skipped`, pair that with a callee-identity check: grep the
  test's *resolved* target and assert it `==` the production caller, not a
  same-named orphan / twin. `0 skipped` reads GREEN while the test binds dead
  code that carries the same symbol the skip-guard probes.

---

## Reviewer Checkpoints — 4-link Evidence Chain DoD (MANDATORY for L2)

Every claim "C-N closed" / "INV-N satisfied" in MCA RETURN-SUMMARY or
reviewer verdict MUST carry the 4-link evidence chain:

| Variant | Link 1 | Link 2 | Link 3 | Link 4 |
|---|---|---|---|---|
| Signal-routing | Producer site | Boundary translation site | Consumer ACK / NAK / TERM site | Test that fails if boundary re-flattens |
| Schema / data | Write site | Read site | Constraint site (DDL / model) | Test |

Each link: `file:line` + 1-3 line verbatim code-quote (test variant:
`test:line` + assertion shape).

Fewer links = claim does NOT qualify as "closed". Chief rejects and
re-dispatches with the missing link explicit
(`agents/code-chief.md` + `agents/board-chief.md` §4-link
enforcement). Value-floor + bundle-laundering rules apply to
disposition; 4-link is a separate (and prior) gate on whether a
closure-claim is even valid.

Forces opening the file at each link → prevents single-layer
verification (helper repaired but signal-exit boundary still broken).

---

## Structural-refactor pre-lock checklist

Mandatory when brief mentions any of: `import` / `import cycle` /
`circular import` / `extract` / `extraction` / `move from X to Y` /
`relocate` / `unblock typing` / `eliminate Any` /
`forward reference` / `runtime import` / `TYPE_CHECKING`.

Pre-lock steps (result documented in brief BEFORE locking):
1. List ALL modules importing the affected module
   (`grep -rn "from <affected>"`).
2. List ALL modules the affected module imports (forward direction).
3. For each (caller, target) pair: check if new design creates a
   back-edge into a module already mid-init in caller chain.
4. Baseline collection BEFORE lock: `pytest --collect-only` on every
   test dir importing the affected module.
5. Document prior workarounds with rationale (typed `Any`,
   `TYPE_CHECKING`).

Static traversal: `scripts/import_graph_check.py` (AST-based).

**Bind rule:** brief contains, before `## Acceptance-Criteria`, a
`## §Import-Graph-Spike` block with steps 1-4 results; the
`structural_invariants` class cites the spike result in its
`value:`.
