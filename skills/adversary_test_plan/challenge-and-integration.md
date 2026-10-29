# Adversary test plan — challenge, output, integration and definition of done

Step-loaded unit of `skills/adversary_test_plan/SKILL.md`. Read it before spawning the code-adversary persona (its
challenge runs under §3–§4) and again when the challenged test plan v2 returns, before integrating it and writing the
MCA brief. Section numbers are skill-wide: §1–§2 in `SKILL.md`, §3–§6 in `challenge-and-integration.md`.

### 3. Augenmaß discipline (core behaviour rule)

**Before adding any TC: stop and think.** Judge the challenge by substantive
coverage and oracle scrutiny, not additions. Valid outcomes include necessary
distinct new cases, strengthened assertions or fixtures, or evidence that existing
coverage is sufficient. Zero additions alone is not failure; vacuous approval,
missing substantive challenge or unresolved identified defects are failures.
Required cases and meaningful witnesses remain binding.

Anti-case observed empirically: 41 TCs for 6 deltas (6.8 TC/delta) drives MCA
into workaround patterns (trivial-green skeletons, impl-fragments that only
serve tests). Counts and ratios describe scope and invite scrutiny; they are
not success quotas.

When output reflex hits >2x deltas/ACs: pause. **Pattern-class
coverage is NOT required.** Classes without a clear code trigger go
into `patterns_excluded` with rationale.

**Per-TC value-floor (MANDATORY, framework/invariants.md Inv 9).** The growth guard
(`skills/testing/SKILL.md` §Test design from the change) applies to every ADV-TC. In
addition, before adding any ADV-TC, name in one sentence on the TC: *what production-
realistic failure-mode does this test catch that the implementer's
tests, the existing scope-suite, and the integration / contract-
pinning tests do NOT catch?* If the answer is "future-edit safety"
/ "convention" / "completeness" / "exports a new contract so it
needs coverage" — the TC fails the value-floor and stays out of v2.
Concrete consumer + concrete failure-mode = TC justified. The
sentence stays inline on the TC as rationale; absence is a
validation fail at MCA-ingest. Hand-curated configuration tuples,
trivially-defaulted Pydantic fields, and topology checks on data
the author edits by hand are typical fail patterns — a value-floor
pass on a 9-TC proposal often drops 7 as theater.

Three stop-and-think questions + consolidation rule (EXTENDS
mandates dropped): `REFERENCE.md` §Augenmaß + §Consolidation.

### 3a. Ground the tester's mechanism-claims (grep-at-the-asserter)

The tester's design output carries mechanism-claims — a hardcoded
literal (a `","` separator), a path-label, an in-process-vs-network
layer-classification. These are asserter-claims and owe the same
one-hop grounding as any brief claim
(`_protocols/evidence-author-claims.md` §8.3 — the tester-design
layer): grep the cited literal / path / symbol at HEAD before building
a TC on it. Observed: a design hard-coded a `","` separator the code
wrote as `", ".join`, and mislabeled a network MCP-client as
in-process — both grep-falsified. A TC resting on an un-grounded tester
literal is a false-green in waiting.

### 4. Output format (required)

Challenged test plan v2 = existing TCs (refined or consolidated where
applicable) + any justified adversary-added TCs with `pattern_class` annotation.
Zero additions are valid when the existing coverage rationale identifies the
assertions/fixtures strengthened or the evidence supporting sufficient coverage.

Required coverage rationale block (full YAML schemas in
`REFERENCE.md`): `scope_signal` (ratio + `proportional_check`),
`patterns_chosen` (per class with code-trigger rationale),
`patterns_excluded` (explicit rationale), `consolidations`,
`spec_assumption_diff`, `implementer_blindspots`.

**Bind rule (output):** all ADV-TCs are part of definition of done.
Few + binding > many + diluted. On uncertainty: leave out.
Non-included TCs are adversary private notes, not skill output.

### 5. Buddy integration

- v2 written to `docs/tasks/<id>.md` test-plan section (replaces v1
  with consolidations).
- `test-skeleton-writer` consumes v2 and writes assertions for all planned
  TCs (tester + adversary). Apply `skills/testing/SKILL.md` §Meaningful pre-fix
  witness for intended behavior changes; retain valid green controls and
  regressions. Report reference-oracle disagreements; Buddy rules each before
  the MCA dispatch.
- **Oracle independence:** when the plan relies on a differential
  oracle, the adversary checks it was written from the spec bullets,
  not mirrored from code; later oracle edits follow
  `skills/testing/test-design.md` §Oracle discipline (separate hunk, cited
  ruling, reviewed by a non-implementer).
- `delegation-artefact` references v2 + RED skeleton path.
- **Post-return check (Augenmaß verification):** substantive coverage and oracle
  challenge evidenced; `patterns_chosen` with code-trigger rationale,
  `patterns_excluded` filled, consolidations justified. Counts/ratios invite
  scrutiny but cannot establish success or failure alone. On an Augenmaß defect
  (unjustified additions or >2x ratio without active defence, missing
  `patterns_chosen` code-trigger rationale or `patterns_excluded`, unjustified
  consolidations): re-dispatch with Augenmaß reminder, max 1 retry. Missing
  substantive challenge, only happy-path scrutiny or an unresolved identified
  coverage/oracle defect → `SKILL.md` §FAIL Retry.

### 6. MCA definition of done

MCA brief contains: **"All adversary TCs (`ADV-TC-*`) MUST pass
post-implementation."** Adversary TCs are first-class definition of
done. Augenmaß on the adversary side ensures proportional bind
pressure — no severity splitting needed.

The build runbook carries adversary TCs as a definition-of-done
constraint: a run is not done while `ADV-TC-*` cases remain
unconfigured.
