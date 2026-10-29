# Workflow engine — local workflow closure

Step-loaded unit of `framework/workflow-engine-cookbook.md`. Read it when a workflow that owns a mechanism lifecycle
reaches its close step or a mechanism-lifecycle check fires.

## Mechanism-Lifecycle: local workflow closure

**Owner:** workflow engine.
**Carriers:** persisted workflow steps, existing pause/completion/abort markers, revision, and authoritative active/archive placement.
**Consumer:** exact selected-state export and development continuation close.
**Outside this model:** new parent propagation, parent/child correlation and distributed settlement.

Step terminality and successful workflow closure are different. `complete`, `skipped`, `route_skipped` and `warn_skipped` may contribute to eligible local closure. An unresolved `escalated` step prevents successful closure. A blocked or erroneous check remains unfinished; it does not create a persisted `failed` step status.

A local run is eligible when its current supported interpretation has no unfinished or escalated steps, is not paused or aborted, and has no unsupported child-finalization boundary. Successful closure preserves step statuses, evidence and publication skips, clears `current_step`, and archives the revision containing the existing `completed` timestamp.

Ordinary completion, permitted explicit skip, accepted warn/skip failure policy, navigation exhaustion after guard skips or mechanical completion, and mechanical recovery use the same local closure decision. `--next --id <workflow-id>` also reconciles an already eligible all-terminal active run. It never requires a false completion, retry of delivered work, or direct state editing.

Reconciliation of a retained active completion record retries archival without rerunning checks or work and without replacing its completion timestamp. If concurrent retry has reopened a step, closure eligibility is recomputed from the fresh revision; the old completion marker cannot close it.

An archive or save error fails the operation. A retained active completion record is not successfully closed merely because its `completed` field exists. Correct the reported filesystem problem and retry `--next --id <workflow-id>`. A stale revision requires reload and retry; no automatic replay overwrites newer evidence.

Paused runs are not progressed or finalized by completion, skip, retry, navigation or recovery. Explicit resume is required. Abort remains distinct and authoritative; navigation and recovery do not turn it into completion.

Escalation preserves the escalated step and requests attention; it is not successful delivery or successful closure. Explicit retry of the escalated step, or explicit abort, remains the supported resolution.

Newly added closure paths do not invoke parent propagation. If one would finalize a parent-linked run, it refuses that unsupported finalization with a concrete diagnostic and leaves the parent untouched. Existing explicit-completion propagation is preserved within its previous boundary; this contract adds no inference from workflow type.

States are derived views of existing fields, **not new persisted status values**:

- **N:** absent run.
- **A:** active, with unfinished steps.
- **F:** active with blocked/failed evaluation; unfinished obligation remains.
- **E:** unresolved escalation; other steps may remain unfinished.
- **P:** paused, including paused all-terminal runs.
- **T:** active, all steps eligible-terminal, no completion marker.
- **C:** active eligible completion record awaiting successful archival.
- **D:** successfully archived completion.
- **X:** authoritative abort, including pending steps or retained pause flag.

All cells below are **now**. `close` means the shared local finalizer, subject to the failure and child guards below.

| Operation ↓ / state → | N | A | F | E | P | T | C | D | X |
|---|---|---|---|---|---|---|---|---|---|
| Create | A or T | Existing pair refused | Existing pair refused | Existing pair refused | Existing pair refused | Existing pair refused | Existing pair refused | New distinct run permitted | New distinct run permitted after archival |
| Complete | Not found | Existing check/sequence rules → A/F/E/T; T closes | Same explicit re-evaluation | Other work retains E; resolving escalated step requires retry | Refuse progress | Existing terminal-step refusal; use next | Refuse step replay; use next | No active step | Refuse progress |
| Explicit skip | Not found | Existing eligibility rules → A/T; T closes | Same eligibility rules; no required-check bypass | Preserve unresolved escalation; cannot overwrite escalated evidence | Refuse progress | Refuse terminal-step rewrite; use next | Refuse step rewrite; use next | No active step | Refuse progress |
| Next, including guard skips/auto-completion | Existing empty result | Existing navigation → A/F/E/T; T closes | Error stays unfinished | Retain E; never close successfully | No mutation | Close | Retry archive only | Existing empty result; no replay | No progression |
| Recover | Existing no-work result | Recover permitted mechanical checks → A/F/E/T; T closes | Evaluation error stays unfinished | Retain E; never close successfully | No mutation | Close | Retry archive only | No active work | No progression |
| Local finalizer flow | Unreachable: no carrier | No closure | No closure | No successful closure | No closure | C → D | D after archive retry | Unreachable through supported active-run dispatch; repeated CLI next performs no work | No completion conversion |
| Explicit retry | Not found | Existing retry rules | Existing retry rules | Reopen selected escalated step with history | Refuse progress | Reopen selected step | Reopen selected step; invalidate stale completion eligibility | No active step | Refuse progress |
| Pause / resume | Existing not-found behavior | Pause → P; resume no-op | Pause → P | Pause → P | Resume restores derived underlying state | Pause → P | Pause → P | No active run | No progression |
| Explicit abort | Not found | X | X | X | X | X | X | No active run | Remains abort; never success conversion |
| Inspect / exact export | Missing-state result | Active, nonterminal | Active, nonterminal | Active, nonterminal; escalation retained | Paused, nonterminal | Active, nonterminal | Active, nonterminal | Completed, terminal | Aborted, terminal |

**Operations/producers and consumers:**

| Operation | Kind | Actual producer | Consumer |
|---|---|---|---|
| Create | Surface | `create_state`, `cmd_start` | Navigation and persistence |
| Complete / skip / retry | Surface | `complete_step`, `skip_step`, `retry_step`; corresponding CLI handlers | Step state and local finalizer |
| Navigate / guard skip / auto-complete | Flow | `find_next_step`, `cmd_start`, `cmd_next` | Actionable-step output and local finalizer |
| Recover | Flow | `recover_workflow`, `cmd_recover` | Step state and local finalizer |
| Finalize | Flow | `_check_workflow_completion` | `save_state`, `archive_state`, exact export |
| Pause / resume / abort | Surface | Existing CLI handlers | State and lifecycle projection |
| Inspect / export | Surface | `continuation_lifecycle`, `export_selected_states` | Development adapter `close` |

**Invariants:**

| Name | Enforcement |
|---|---|
| `EligibleLocalClosure` | Shared finalizer validates current step vocabulary/statuses, pause/abort and escalation before closure |
| `NoWorkReplay` | T/C reconciliation changes lifecycle bookkeeping only; repeated next cannot reopen archived work |
| `ArchiveAcknowledgedClosure` | Command succeeds only after archive; exact export checks authoritative storage placement |
| `PreserveTransitionEvidence` | No terminal-step rewriting during skip or reconciliation; retry retains its existing history rules |
| `AttentionIsNotSuccess` | Escalation/check errors never yield successful workflow closure |
| `PauseAndAbortIsolation` | Mutating consumers refuse paused/aborted progression; abort remains distinct |
| `RevisionProtectedClosure` | Existing write/archive revision checks remain operative; errors propagate |
| `NoNewParentPropagation` | Newly reached finalization refuses parent-linked settlement; parent state remains unchanged |

**Failure overlay, applicable to every mutating cell:** stale revision → exit 7; save/archive/validation refusal → existing nonzero failure; guard evaluation error → existing exit 6 where applicable. A contending lock must not produce success before acquisition and a valid transition; retain existing locking policy rather than adding a timeout system.

**Parent overlay:** preserve existing explicit-completion propagation only. New skip/navigation/recovery/reconciliation finalization of a parent-linked run refuses before archive/parent propagation. The already accepted step transition may remain persisted; the diagnostic must say local closure is unresolved. No future parent flow is built or assigned a speculative task here.

**Placed cells:** none. Parent propagation expansion is forbidden-adjacent by explicit task scope.


Maintenance inventory is an observational consumer of the existing D/X cells.
It validates supported schema, identity, revision, variables, nonempty step/status
mappings, current-step reference, pause type and lifecycle marker structure before
recognizing terminal history at the authoritative archive path. Archived successful
completion requires eligible terminal steps and no pause; authoritative abort may
retain pending steps and pause. Historical step/route vocabulary need not appear
in the current definition. Active/all-terminal or completion-awaiting-archive
records and archives without a positive terminal marker keep strict current
interpretation. The internal maintenance projection never changes persisted state,
ordinary continuation/export contracts or the lifecycle matrix above.
