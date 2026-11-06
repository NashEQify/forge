# Code review board — review brief and team

Step-loaded unit of `skills/code_review_board/SKILL.md`. Read it after the level choice (§1) and before any reviewer
dispatch of a board review, at every level (a same-turn DIRECT check is not one: `SKILL.md` §Same-turn DIRECT check). Section numbers are skill-wide: §1 and §6–§10 in `SKILL.md`, §2–§3 in `brief-and-team.md`, §4–§4a in
`checklist-and-dispatch.md`, §5–§5a in `verdict.md`, §11 in `review-package.md`.

## 2. Review brief (MUST before dispatch)

Where the project keeps `context/risk-watch.md`, name the entries whose
trigger the change touches, and the open `absorb_next` entries of earlier
verdicts for the touched files, in the brief. This review's decision
states, for each, the trigger outcome and the `proposed_action_when_fires`
taken, or `absorbed` / `still open`.

5 steps, each producing output:

1. **TOPOLOGY** — `## Files changed` of the review package (§11): file, package, kind, LOC.
2. **DEPENDENCY TRACE** — who imports? New/changed signatures?
3. **RISK ASSESSMENT** — concurrent access, error paths, interface
   breaks, state machines, external deps.
4. **REQUIREMENTS MAP** — spec_ref ACs + delegation done-criteria.
   For any AC describing a producer→consumer / cross-process wire
   (integration / end-to-end), a GREEN wire-proving test is required
   evidence — a `skip`/`xfail` stub does NOT satisfy it (skipped E2E
   silently counts as "tests green"). Tripwire: a new
   `*Consumer`/`*Worker`/producer symbol with no instantiation outside
   `tests/` (grep the durable/consumer registry + app factory → no
   hit) = the wire is absent regardless of unit-green. This is the
   BOARD-stage catch; running the same grep tripwire earlier at the
   build Verify gate (before the board) is a noted follow-up — until
   then the board is the earliest net, not the cheapest one.
   **Faithfulness-evidence (the green suite must exercise the real
   surface, not a fabricated one):**
   - **Producer-faithfulness** — for each AC's GREEN test, name the
     production producer of every hand-passed input or polled state. If
     that producer is the function-under-test's own caller, require a
     wired (L3) companion; if it is an async/upstream service, the test
     must NAME the producer's floor latency and assert the poll budget
     brackets it (not a fabricated value, not a premature settled-empty).
   - **Test-hollowing** — when the diff REWRITES an adversarial test's
     assertions, require a mutation-or-equivalent proof it still goes
     RED on the original defect-class (vacuity signature: the rewrite
     feeds input already at the guarded boundary).
   - **Orphaned-corpus (Verify gate)** — a golden/byte-identity harness
     imported by no test (grep `tests/*golden*` → no importer, or 0
     cases under `--collect-only`) asserts coverage it does not provide.
   Design-side mandate: `skills/testing/test-design.md`
   §Execution-faithfulness.
   **Mechanism cells (when the diff touches a state carrier):** the
   brief carries the owning spec's `§Mechanism-Lifecycle` matrix
   (`_protocols/mechanism-model.md`) and marks the cells in scope.
   Reviewers review cells, not the diff's own framing: an in-scope cell
   without a guard or a test, a cell the code decides differently from
   the matrix, a placed (`task-N` / `beyond-MVP`) cell driven by a
   hand-built fixture, or an operation the matrix omits are findings and
   name the cell. A blocking finding on a state carrier without a section
   triggers the retro-model (`_protocols/mechanism-model.md` §Trigger);
   the board brief of the next pass then carries it.
   **Added tests (relevance).** Every test the diff adds traces to a
   behaviour the change changes (an AC or a changed code path) and guards
   a purpose a consumer relies on, not the text or presence of an
   artifact (`skills/testing/lean-suite.md` §Each test earns its place).
   A test that traces to no changed behaviour, or guards only an
   artifact's text or presence, is a finding that names the test
   (`file:line`) and the missing trace; its fix is a deletion. The brief
   hands this check to the L1 checklist (§3 item 3) and on L2 to the
   coverage owner as a focus point.
   **Additions (the reverse trace).** Map the diff back as well: every
   added layer, abstraction, dependency, configuration option, guard or
   public surface traces to a spec item, an AC, the brief or a
   `§Complexity-Tracking` row (`framework/spec-engineering-implementation-specs.md`
   §Convention: §Complexity-Tracking). Code for behavior none of them asked
   for is `unrequested`. An addition of those kinds that serves requested
   behavior but has no row, or a row that names no need, is
   `unjustified`; so is a fix's public surface or guard for a state the
   failure did not demonstrate, without a row
   (`_protocols/mca-brief-template.md` §Complexity-Tracking). The brief
   hands this trace to the L1 checklist (§3 item 5) and on L2 to the
   coverage owner as a focus point. A finding names the addition
   (`file:line`) and the missing trace, with severity by impact; its fix
   is a deletion or a row with a named need, not another guard that makes
   the addition safe.
   Conversely, a finding that asks for a guard against a state it shows no
   input or producer reaching is not a defect: code that fails loudly on a
   state the program was never shown to reach is correct. Source:
   spec-kit (MIT License, © GitHub, Inc.) and BMAD-METHOD (MIT License, © 2025 BMad Code, LLC); Forge's register of adopted methods.
5. **TEAM COMPOSITION** — risk → agents + focus points. Includes the
   **L2-trigger table**: five rows (public API / wire; security / auth /
   secrets; real migration doubt; new subsystem; live infrastructure),
   each `yes | no` with an evidence pointer (file:line, grep or spec
   clause). Copy it into the verdict. A missing row counts as `yes`.
   On L2 also the roster table (§3): every candidate `run` with its open
   question, or `omit` with the evidence that answers it.

## 3. Team composition

**L1 core:** `code-adversary` + `code-domain-logic` +
`code-architect-roots`, one parallel cold-start dispatch (brief per §2,
cold-start rules per §4a; no separate frame check). **With a spec_ref**
the `code-domain-logic` brief names two extra focus points that
`code-spec-fit` covers on L2: AC conformance (every AC implemented;
types, bounds and error paths match the spec) and test vacuity (does
the guarding test of each HIGH-risk AC go red on a one-line mutant of
the guarded branch; record the mutant).

**L1 trigger lenses** (join only on the named trigger, logged in the
dispatch header):

| Lens | Trigger |
|---|---|
| `code-review` | the diff touches a hot path, or a path with a latency / throughput AC, that has no measurable perf-budget test |
| `code-data` | stored shape changes: it settles the migration-needed check (`skills/deprecation_and_migration/SKILL.md`); if its return leaves doubt, re-level to L2 |
| `code-reliability` | async / lock / worker / event-loop paths |
| `code-api-contract` | new exported interface consumed by other in-repo components (external API / wire → L2) |
| `code-security` | any auth / input / secrets touch found after level choice → re-level to L2 |

**L1 Buddy checklist (replaces `code-spec-fit` on L1; written into the
verdict):** (1) hand-offs — every cross-task / producer→consumer seam
the ACs name is wired or owned by a named task; (2) spec drift — does
the diff change spec-defined behavior (→ spec-drift-check gate);
(3) AC coverage — each AC maps to a green test, with the §2 step 4
faithfulness rules, and each added test passes §2's relevance check; a latency AC on a growing log or store has its N
and 4N slope leg (`skills/testing/test-design.md` §Oracle discipline). On L1
this item owns test coverage; conformance and test vacuity sit with
`code-domain-logic` (above). (4) mechanism cells — when a
`§Mechanism-Lifecycle` matrix is in scope, every in-scope cell has a
guard or a test (or a generator that spans it), every placed cell has
only refusal tests and its owning task is `blocked_by`-wired, and the matrix was edited in the same
change as any mechanism decision the diff implements; (5) additions — the
§2 step 4 reverse trace: each `unrequested` or `unjustified` addition is a
finding.

**L2 roster (fixed base + open questions).** Always, cold-start:
`code-adversary`; one coverage owner (`code-spec-fit` with a spec_ref, else
`code-domain-logic` with the §3 Buddy checklist); and each fired trigger's
perspective, with executed probes against that surface: security →
`code-security`;
public API / wire → `code-api-contract`; real migration doubt →
`code-data`; live infrastructure → `code-reliability`; new subsystem →
`code-review` + `code-architect-roots`. `code-architect-roots` also follows
the §1.2 gate. Candidates beyond that base (the rest of L1 core,
`code-review`, the risk specialists below) run when the
brief names an open question in its area that current independent evidence
for these bytes cannot answer and whose answer could change acceptance
(`agents/buddy/delegation.md` §Delegation hygiene); qualified earlier
independent returns count as evidence (`skills/testing/run-strategy.md` §Run
strategy). Still unclear whether such a question exists → run it. With four
or more reviewers a Chief consolidates and §4a applies; with three or fewer
Buddy consolidates per §1.3. The base never has fewer cold-start reviewers
than the L1 core. A fresh or broad change with open questions in many areas
keeps the full roster. Sizing never removes a floor, weakens
cold-start independence or changes severity and verdict thresholds.

| Risk area | Agent |
|---|---|
| Auth / input / secrets | code-security |
| State machine / business logic | code-domain-logic (core) |
| Infra / worker / message broker (e.g. NATS) / DB | code-reliability |
| Schema / queries / migrations | code-data |
| API contracts (e.g. REST / SSE) | code-api-contract |
| LLM / prompt / token budget | code-ai-llm |
| Code docs + spec readability | code-docs-consumer |
| Pattern-purity / structural roots | code-architect-roots (core) |
| Spec exists (spec_ref) | code-spec-fit (conditional; **sole test-coverage owner on L2**) |
| Retroactive spec drift | code-spec-drift (conditional) |

**Specialist names MUST resolve to real `agents/code-*.md`.**
Hallucinated labels (`code-async`, `code-concurrency`) fall through
silently — `ls agents/code-*.md` at dispatch-prep to verify. On a
non-matching name, substitute by risk-area from the §3 table above
(infra/worker → `code-reliability`; async/race → `code-adversary` +
`code-architect-roots`); log the substitution in the dispatch header.
