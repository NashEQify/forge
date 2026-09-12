# Workflow: fix

Investigate and permanently repair a defect. Active incidents use recovery
first; recovery is not a claim that the root cause has been fixed.

**Forge-feed trigger (active throughout this workflow):** framework-
relevant friction → apply the pre-write filter in
`$FRAMEWORK_DIR/docs/dogfood-learnings/README.md`; if it passes, append to
`$FRAMEWORK_DIR/docs/dogfood-learnings/forge-feed.md` on notice. Not at close.

## Trigger

- User reports a defect (directly or via Buddy's intake-gate INCIDENT).
- Sub-agent ESCALATED or AUTO-FIXED.
- Test failure in the verify phase of a build workflow.
- Monitoring / health-check alert.

## NOT for

Known feature gap → **build**. Spec error → **review**. Unclear
problem → **solve**. Research → **research** (sub-workflow).

## Incident recovery

For an active outage or ongoing harm, restore safely before final root-cause
analysis. This section takes precedence over the repair gates below and the
root-cause-fix skill's permanent-repair sequence.

1. Identify the affected service/host, impact, and current state. Preserve the
   essential evidence needed for diagnosis without prolonging ongoing harm.
2. Read the consumer's recovery procedure and authorization bounds. Choose a
   bounded recovery supported by that procedure and observed state, such as a
   known-good rollback. If no safe recovery is known, diagnose or escalate;
   do not improvise repeated restarts or destructive restores.
3. Execute only with authorization covering the host, session, action and
   data impact. Existing approval may suffice; destructive actions still
   require their explicit confirmation. Subagents and background runs gain
   no new live privileges.
4. Verify the actual service/user outcome and stability. If recovery fails,
   stop and reassess its scope; do not silently widen authority.
5. Record **Restored** separately from **Resolved**. Preserve what changed,
   evidence, authorization and remaining uncertainty. Then investigate and
   permanently repair the cause through the normal fix process as needed.

No mandatory hypothesis count, RED test, architect brief or repeated routine
signoff precedes an authorized recovery. Do not mark those unperformed repair
gates complete. Recovery can run as a short recorded operation before starting
the repair workflow; pause an existing repair workflow if needed.
Authorization SoT: `framework/process-map.md` section Authorization; consumer
live/destructive restrictions continue to apply.

## Path determination

```
Nested in a parent build (parent task has open ACs / sub-builds)? → SUB-FIX
Otherwise                                                          → STANDARD (default)
FULL = reserved for future-extension (L2 board on schema-impact fixes).
```

`workflow_engine.py --start fix --task <id> --route <path>`. SUB-FIX
mechanically excludes `close-bookkeeping` and `commit-deploy` — the
parent owns task-level status.

## Named gates

The fix workflow has **9 named gates**. Phase-status transitions
are engine-internal.

| # | Gate | Skill | Conditional |
|---|------|-------|-------------|
| 1 | root-cause | `root_cause_fix/SKILL.md` (Phase A) | — |
| 2 | test-plan | — (write failing test) | RED before fix |
| 3 | fix-brief | `agents/brief-architect.md` (architect-authored on substantial; Buddy-inline on DIRECT) | mirrors build's brief-author at fix scope |
| 4 | brief-signoff | gate (user approval) per spec 306 §4.4 | DIRECT path skips; sub-fix route omits (parent already approved at parent-scope brief-signoff) |
| 5 | fix-execute | `root_cause_fix/SKILL.md` (Phase B); MCA inline OR Buddy direct per architect-authored fix-brief | retest as inline sub-step (regression suite green) |
| 6 | code-review | `code_review_board/SKILL.md` | risk-first selection per §1; consolidation per §1.3 |
| 7 | spec-drift-check | `spec_amendment_verification/SKILL.md` | when fix changes spec-defined behaviour OR authority log exists with new spec edits |
| 8 | close-bookkeeping | **distill** `close_retro` (skip-eligible) → **emit** `knowledge_processor/SKILL.md` + `task_creation/SKILL.md` + `risk_followup_routing/SKILL.md` (consume the retro; each skip-eligible) |
| 9 | commit-deploy | **`task_status_update` (status=done, not a raw YAML edit)** + git pre-commit hooks | sub-fix route skips this gate |

## Detail per gate

**1. root-cause** — `root_cause_fix/SKILL.md` Phase A. Symptoms →
hypotheses → drill. Output: hypothesis + test plan that reproduces
the bug. Do NOT patch symptoms.

**2. test-plan** — write a failing test that triggers the bug
symptom. MUST be RED before the fix.

**3. fix-brief** — architect-authored fix-brief on substantial
fixes per spec 306 §4.5. Brief covers: root-cause hypothesis (from
gate 1), fix-implementation plan, scope-focused test/verification,
RETURN-SUMMARY structure, sign-off field per spec 306 §5.2. DIRECT
path: Buddy authors inline as today. **On external library API
references in the fix scope: invoke `get_api_docs` BEFORE writing
the fix plan** (source-grounding, mirrors build's spec-write hook).

**4. brief-signoff** — Mirrors build's brief-signoff (same step
ID, path-agnostic — single signoff shared across DIRECT/STANDARD/
FULL paths). Check the existing authorization against the actual fix-brief
per `framework/process-map.md` section Authorization. Record a matching
approval and continue; ask only for a new decision/scope/risk. Diagnosis-only
requires repair approval. DIRECT skips the separate gate; sub-fix inherits
the parent's approved scope without expanding it.

**5. fix-execute** — MCA inline OR Buddy direct (orchestrator
path). Fix-diff makes the RED test green per the architect-authored
fix-brief. Add regression coverage where it makes sense. Verify
regression suite is green.

**4. code-review** — `code_review_board/SKILL.md` §1 selects the level
with safety floors first; §1.3 determines consolidation from reviewer count.
This narrative defines no independent size-based shortcut.

**5. spec-drift-check** — spec-body drift: did the fix change behaviour
defined in a spec? Yes → spec patch in the SAME block-commit. No
spec-defined behaviour touched: skip with rationale.

**6. close-bookkeeping** — distill → emit. **Distill:** `close_retro`
(skill `skills/close_retro/SKILL.md`, spec 374) fires on FULL / a
decision-heavy fix (else skip the common small fix with a one-liner) →
read-only `close-retro` agent on the RCA + verdict + ACs → retro 1-pager at
`docs/fix/<slug>-retro.md`; fix has no ADR sub-step → §Stale-Decisions stays
noted in the retro. **Emit** (consume the retro when present, else current
behaviour):
(a) lessons-learned via `knowledge_processor` ← §Patterns-Emerged (root
cause + pattern lesson into context);
(b) risk follow-up — file ONE follow-up task per non-empty
`remaining_findings:` block (orthogonal to close_retro — routes review
findings, not lessons);
(c) §Framework-Feed — forge-feed entries (replaces the old workflow-retro
safety net; on skip, reverts to capture-now of missed entries).

**7. commit-deploy** — local commit only when authorized by the request or
standing repository policy. Push/deploy are separately authorized actions;
docs changes are not deployment permission. Engine auto-advances
`workflow_phase=done`; task-level
`status=done` is conditional (sub-fix route skips — parent owns
task status).

## Iteration bounds

| Gate | Max | On overshoot |
|------|-----|--------------|
| root-cause | 3 drill rounds | escalate to user (root cause unclear) |
| fix-execute | 3 attempts to make test green | escalate (architecture problem, not a fix) |
| code-review | 2 review-fix rounds | escalate (review NEEDS-WORK persistent) |

## References

| Topic | Detail SoT |
|-------|------------|
| Root cause fix | `skills/root_cause_fix/SKILL.md` |
| Code review | `skills/code_review_board/SKILL.md` |
| Spec amendment | `skills/spec_amendment_verification/SKILL.md` |
| API docs lookup | `skills/get_api_docs/SKILL.md` |
| Knowledge processor | `skills/knowledge_processor/SKILL.md` |
| Workflow engine CLI | `framework/workflow-engine-cookbook.md` |

## Workflow-Engine Integration

This runbook is tracked by `scripts/workflow_engine.py` when engine-driven
(some lifecycle / ad-hoc runs are skip-eligible — see the cookbook's *Skip
allowed for* list). The engine holds step state in `.workflow-state/<id>.json`
(SoT for the step pointer; persistent + cross-session-recoverable) and is
**Buddy-driven `[WORKFLOW]`** — it advances only when Buddy drives
`--complete`, a discipline-run state-tracker, not an autonomous runtime
(ADR-007 O-4, affirming ADR-004: no force-gate).

Generic cycle (identical across every workflow):

```bash
python3 $FRAMEWORK_DIR/scripts/workflow_engine.py --start <name> --task <id> [--route <path>]
python3 $FRAMEWORK_DIR/scripts/workflow_engine.py --next                       # current step + instruction
python3 $FRAMEWORK_DIR/scripts/workflow_engine.py --complete <step> --evidence "<short>"
#   classification step (mid-flow route): --complete <step> --route <key>
#   skip-eligible step: --skip <step> --reason "<why>"   ·   re-run: --retry <step> --reason "<why>"
#   >=2 workflows live? add --id <wf> (from --next `ID:`) — engine refuses keyless (exit 5)
```

`on_fail` per step: `block` (fix + retry), `warn` (`--complete --force` + reason),
`skip` (auto `warn_skipped`), `escalate` (pauses, user decision). Cross-session
resume surfaces active workflows at session start (`--boot-context`).

Full CLI + path-routing + extension API (`--guard` / `--handoff-context`) +
multi-machine constraint + skip-eligible list:
`framework/workflow-engine-cookbook.md`. Operational invariant:
`agents/buddy/operational.md` §Workflow engine.
