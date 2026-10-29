# Council — development caller

Step-loaded unit of `skills/council/SKILL.md`. Read it only for an explicitly selected development caller: before a
build-context or solve-refine council starts, when deciding whether an ADR is required (§4 step 8), and when a
ruling splits a capability. Section numbers are skill-wide: §0–§1, §5–§8, §11 and §14 in `SKILL.md`, §2–§4 and
§9–§10 in `run.md`, §12–§13 in `development.md`.

## 12. ADR-trigger conditions

For an explicitly selected development caller, ADR REQUIRED on:
- Hard-to-reverse decision (data/schema/contract/identity)
- Decision spans ≥2 components or layers
- ≥1 HARD constraint (security, sovereignty per the user's values) explicitly traded off
- Council mode = standard or full (light optional)

Via `documentation_and_adrs/SKILL.md` in that development caller. Otherwise return rationale/alternatives/uncertainty inline; no ADR or task is mandatory or automatically written.

## 13. Optional development caller handshake

Only a selected development caller loads this section’s engine/runbook references. Standalone invocation never starts or probes an engine.

**Build-context council** (specify-phase substitute for spec_board): Buddy MUST trigger `python3 scripts/workflow_engine.py --start build --task <id>` in the SAME tool block as council spawn. Engine state SoT for cross-session recovery. This is Buddy-side discipline — `workflows/runbooks/build/workflow.yaml` board step has `alternative_skill_refs: skills/council/SKILL.md` as documentation-intent only (engine reads `skill_ref`).

**Solve-refine council** (opt-in via state-file marker): the `council-needed` guard at `scripts/workflow_engine.py` greps the solve state file for `council-required: true` (frontmatter or body). If present → guard exits 0, council step fires automatically. If absent → guard exits 1, refine step proceeds with user-dialog only. Buddy writes the marker when frame report's >1-path + hard-to-reverse criteria fire.

Default = skip (council is Buddy-judgmental per §1.0; engine does not auto-fire architectural decisions). See `framework/workflow-engine-cookbook.md` for engine shape.

**Split rulings (development caller):** a ruling that splits a capability
and moves its gate / proof half to a sibling names that half, every
producer / consumer of the ungated half, and the fail-closed edge; the
caller applies its task-creation split-gap check in the same change.
