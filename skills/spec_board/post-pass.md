# Spec board — delta-verify and post-pass

Step-loaded unit of `skills/spec_board/SKILL.md`. Read it after each pass's consolidation and after every relevant
fix, before re-checking, closing or carrying findings forward. Section numbers are skill-wide: §0, §3, §5 and §7–§10
in `SKILL.md`, §1–§2 in `depth-and-team.md`, §4–§4b in `checklist-and-dispatch.md`, §3a and §6–§6a in `post-pass.md`.

### 3a. Delta-verify (standard mode, post-fix re-check)

After every relevant fix, retry the exact owner and capture the new subject before
applicable current verification. Put fix obligations/changed clauses in `focus`
and exact original reports/decisions in `history`; their old approval is not current.
When the trigger below does not fire, Buddy performs the existing bounded fix
verification in a captured slot with role `verification`, records actual checks,
scope and limits with current identity/evidence, then writes an explicit current
decision. Original independent reports remain history, not independent re-execution.
When the trigger fires, retain the adversary+implementer team below. Reduced final
teams remain unchanged; the final consuming attempt selects its applicable sources.


After fix in standard mode: 2-agent re-check on delta scope only.
Trigger (any): ≥10 normative lines changed; ≥3 files touched; ≥1
MAJOR fixed; fix touches gate composition / severity / enforcement.
Team: `board-adversary` + `board-implementer` (both deliver the `## Checked scope` section; no chief). Acceptance: 0 new BLOCKER + 0 new
MAJOR. Max 3 iterations → ESCALATE. Detail: REFERENCE.md.

## 6. Post-pass (NON-NEGOTIABLE)

- [ ] Chief consolidated has tracking table.
- [ ] Verification equation holds (Raw = Kept + Merged + Related + Removed).
- [ ] Merge spot-check (up to 3 available MERGED findings — same root cause? No merges → not applicable).
- [ ] Minority re-check (scan REMOVED + low-severity single-agent).
- [ ] Piebald-budget check on skill / runbook / persona reviews.
- [ ] §4b cell coverage reported when a `§Mechanism-Lifecycle` section is
  in scope; no empty cell; no blocking finding on a `now` cell in
  `residual`; the
  derived-state columns present for every "only via" invariant.
- [ ] Downgraded scale / latency finding carries a measured bound at
  the target scale, or a filed follow-up whose trigger a slope leg
  (N vs 4N, `skills/testing/test-design.md` §Oracle discipline) can fire.
- [ ] Every kept finding verified at its cited spec location before the fix
  (`skills/_protocols/finding-verification.md`); the fix takes the verified rows.
- [ ] All findings with a verified grade fixed (C+H+M+L); `false` rejected on
  its refutation, `maybe-false` settled or routed.
- [ ] Delta-Verify mini-board if §3a trigger fired — 0 new highs.
- [ ] Current explicit decision adopted; `spec_success` passes before forward
  readiness or `spec_states` ready. Use `task_status_update` with the exact owner.
  PASS writes `APPROVED`; current NEEDS-WORK maps to `REJECTED` and permits repair
  only. Refusal/error leaves requested review-derived fields unchanged.
- [ ] Task YAML `board_result` + `readiness` updated.
- [ ] Persist the result; commit/push/deploy only under the respective
  authorization in `framework/process-map.md`, not because task YAMLs changed.

## 6a. Risk carry-forward (MANDATORY on user-override / cherry-pick / valve-hit / ESCALATE-accepted)

Verdict file MUST carry unfixed findings forward in top-level YAML
block `remaining_findings:` listing every unfixed finding with `id`,
`severity`, `locator`, `title`, `rationale_for_carry_over`,
`proposed_action`. The `close-bookkeeping` step of the review workflow
(risk follow-up) reads the
block and files ONE follow-up task per workflow run via `task_creation`.
Empty/absent block → skip with rationale.

Full schema, example, acceptance scenarios: REFERENCE.md
§Risk carry-forward.
