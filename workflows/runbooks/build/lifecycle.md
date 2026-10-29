# build Workflow — lifecycle stages

Step-loaded unit of `workflows/runbooks/build/WORKFLOW.md`. Read it when deciding the route, and at the spec
interview, when deciding which conditional stages the change needs.

A software change runs through the stages below, from intent to close. A stage is a content responsibility that an
existing gate carries; it is not a gate of its own. Which gates a route runs is the route's step list
(`workflow.yaml` `routes:`); DIRECT eligibility is `framework/direct-eligibility.md`. Owners are the skills in
WORKFLOW §Named gates.

| Stage | What it settles | Runs when | Carried by |
|---|---|---|---|
| Intent and sizing | Intent, task, acceptance, authorization, route | Every change | route decision (WORKFLOW §Path determination), with §Sizing facts |
| UX | The look and the experience a person meets: a look contract and an experience contract (surfaces, states, journeys, voice) | The change adds or changes a screen, page, flow, or a CLI/TUI interaction a person operates. A documentation site counts only for a navigation or search mechanism the change builds in code; its pages, text and structure stay with the docs-rewrite workflow. A changed string, or an added option of an existing command, alone stays in the behaviour spec | `skills/ux_authoring/SKILL.md` in the interview (the contracts, the closure check); the board in UX mode |
| Architecture | The decisions that keep separately built units consistent: an architecture spine, with what fails its inclusion test named Deferred | The change defines or alters a contract that a unit built or changed in a separate task or dispatch consumes, and that consumer is named. Within one unit, a state carrier keeps its own trigger (`framework/spec-engineering.md` §Convention: §Mechanism-Lifecycle). A spec that already links a spine the change leaves intact cites it and writes none | `skills/_protocols/architecture-spine.md` in the interview and spec-write; its form check; board; plan-time architect lens |
| Behaviour spec with its test matrix | The behaviours the change promises, one matrix row each | The change promises behaviour. A refactoring promises none; an acceptance met by instruction text alone names its check instead (`skills/testing/SKILL.md` §Test design from the change) | spec-write, test-design |
| Plan and execution | Brief, implementation, test-first per matrix row | The route has an Execute phase | brief-author, brief-signoff, mca-implementation |
| Review | Risk-selected review of the diff | The route has a Verify phase | code-review-board, spec-drift-check |
| Convergence | Fix passes until the blocking findings are closed or ruled | A review leaves blocking findings | fix passes under `skills/convergence_loop/SKILL.md` |
| Close | Task status, records, durable knowledge, decisions taken for the user | Every change | close-bookkeeping, commit-deploy |

**Conditional stages.** UX and Architecture run on their trigger. When a trigger is absent, the route decision says
so in its existing record ("no person-operated surface", "no contract with a separately built consumer"). When a
trigger fires mid-build, the stage runs then, through the spec amendment path (WORKFLOW §Named gates).

**What each stage hands on.** The behaviour spec's matrix is the test plan. What the durable spec holds, and what
stays in the tests: `framework/spec-engineering.md` §Convention: spec carriers. Close moves what the change decided durably
into a durable carrier before the change records go stale.

## Sizing facts

The route decision's record opens with three lines, one each, written from the request, the code and the rules the
change falls under as they stand, before the route is chosen. On DIRECT they open the inline record of outcome, scope
and verification plan.

```
intent gaps: <each point the request leaves open and that costs the user if wrong — "asked" or "settled: <way taken>"> | none
irreversibles: floors: <each safety floor touched> | none; no undo: <data deleted or changed; publication; an install or deploy into a live host> | none
footprint: <paths changed, estimated>; new: <what another unit will call, read or depend on, and that consumer> | none; deliverables: <count that could each ship alone>
```

- **Intent gaps** are the points that pass the two tests of `skills/return_summary/SKILL.md` §Decisions I took for
  you, applied before the work. A request that conflicts with a standing rule leaves its point open. Mark a point
  `asked` when `framework/process-map.md` §Authorization names a reason to ask; a `settled` point goes on the
  decisions list.
- **Irreversibles** has two parts: the safety floors the change touches (`framework/direct-eligibility.md`), listed
  whatever their undo, and what the change's own undo cannot take back.

The route follows from the lines and the floors:
- an `asked` point is answered before the route runs on;
- a safety floor in the line excludes DIRECT;
- a new thing whose consumer is built in a separate task or dispatch fires the Architecture stage;
- two or more deliverables: before the spec, read and follow `framework/spec-engineering-implementation-specs.md`
  §Convention: one goal per change (which goal stays, who decides the split, where the others go);
- WORKFLOW §Path determination then decides among the routes that remain, and the lines are its recorded reason.

Source: BMAD-METHOD (MIT License, © 2025 BMad Code, LLC); Forge's register of adopted methods.
