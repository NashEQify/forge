---
name: knowledge-processor
description: >
  Reconcile useful new information with scoped knowledge and retrieve relevant
  context before dependent work. Shared continuity infrastructure for all work;
  no software workflow or user repository is required for project knowledge.
status: active
relevant_for: ["solution-expert"]
invocation:
  primary: cross-cutting
  secondary: [workflow-step:close, user-facing]
disable-model-invocation: false
modes: [process, wrap-up, user-signal]
uses: []
---

# Knowledge Processor

Canonical semantic lifecycle for knowledge and continuity. Modes specialize this
contract; boot, save and housekeeping invoke it. No database, hook, background
worker, automatic import or development engine is implied.

## Inputs and scope

Input: candidate information or retrieval need, active project, configured user
scope if any, and mode `process`, `user-signal` or `wrap-up`. Resolve location and
permissions through `framework/user-scope.md`. Project knowledge belongs to its
verified project/topic owner; private person facts only to the resolved
`<user_repo>/context/user/`. No user scope: project continuity still works; report
unroutable person facts, never create a profile or private fallback in the project.
A visiting agent retains its own user identity and follows the visited project's
entry and authorization rules without adopting another person's profile.

## Continuous maintenance

Configuring user scope authorizes its maintenance; project rules authorize project
maintenance. Honor explicit limits including “do not save”. Reconcile useful new
facts, decisions, corrections and changed state in the same response cycle, before
final output. A task-specific instruction remains with that task/topic. Checkpoint
substantive results before a topic switch; keep goal, next step, blockers and leading
files in the existing handoff. New leading drafts/results update their topic
pointer and handoff in the same operation, including externally stored results.
After compaction/resume reread project rules, configured boot set, full handoff and
relevant topics; check pending reconciliation before dependent work.

FACTS line while continuous maintenance applies:
`FACTS: keine | {Fakt} → {Ziel} [geschrieben|deferred:{Grund}]`.
Report only actual writes. Private deferred payloads never enter another repo's
handoff. A blocked write is **not persisted**; state target and reason in the
conversation, retry only with available source and authorized writable owner.
Project deferrals may stay in that project's handoff. Conversation-only retention
cannot promise recovery after context loss.

## Executable lifecycle

### 1. Retrieve and establish a coherent baseline

Before an answer/update needing stored context, identify the verified owner and
read its entry/navigation, topic-local rules and relevant current sections. Follow
qualifying evidence when needed. General questions need no personal retrieval.
Use the protected snapshot/publication interface in `framework/continuity.md` for
same-scope dependent reads; check its pending record before PRESENT or dependent
answers. Release protection before reasoning. Additional dependent reads require a
revalidated snapshot, not independently read files from potentially mixed states.

If routes are missing **or** current material is insufficient, inspect linked
evidence, then bounded filename/text search in the owner area, expanding to the
relevant repository as needed. Stop when supported, relevant search is exhausted,
or access fails. Finding one file is not sufficient by itself. Say “no relevant
record found in the searched scope”, never “did not happen”. Missing access is a
limit, not absence. Repair a missing route under existing maintenance authority.
Resolve links from the containing file or its declared repository root, never the
caller's CWD. Cross-repo routes use a verified location and confer no permission.
For external artifact directories first establish the owning workspace and its
rules; otherwise report the ownership gap before dependent work.

Use retrieved facts, settled choices, open questions and prior constraints in the
answer: do not re-ask answered questions, call known facts new, or bypass decisions.
Reading a file alone is not proof of using it. No permanent per-answer audit log.

### 2. Admit, scope and compare

Identify the future question/decision/continuation each candidate supports. Keep
subject and applicability (person-wide, topic, event/task/setup) distinct from
certainty. Separate user statements, observations, proposals, third-party reports
and marked inferences. Unknowns can be retained as open questions, never facts.
Useful adverse outcomes, exceptions, rationale and unresolved work matter too.
Do not infer lasting taste from one setup request, relationships from name mentions,
consumption from ownership, or acceptance from an assistant proposal.

Classify **NEW / CHANGED / PRESENT** against the baseline. Compare meaning, scope,
attribution, support, uncertainty and retraction. Confirmation of an inference or
withdrawal of its evidence is CHANGED even with identical proposition wording.
Repeated evidence is PRESENT; do not increment observation counts. With no pending
reconciliation or discovered inconsistency, PRESENT ends without writing or a new
impact traversal. Explicit instructions need no repeated-observation threshold.
This admission filter never authorizes discarding existing data during migration.

### 3. Place and curate

| Content | Leading owner |
|---|---|
| Person-wide values, identity, constraint defaults | Concise user `profile.md` |
| Collaboration with the person | User `soul.md` |
| Personal topic knowledge/scoped preferences | Responsible user topic file |
| Inner motives/reflection | `inner-life.md` when present/relevant |
| Current activity, task or technical setup | Responsible project/topic file |
| Dated experience/source evidence | Topic evidence section or linked detail |
| Findability | Navigation routes, not duplicate facts |

Split mixed person/activity input at the boundary and cross-link; one leading home
per claim. Minimal implications in summaries link to that owner. Topic names follow
the repository vocabulary; no empty life-domain tree or file per fact. A small topic
can be a section. Legacy facets are evidence, never file selectors or boot-promotion
rules. Read `connections.md` only for relevant actual relationships.

Every new owner must be reachable through question/topic descriptions and useful
aliases. User profile links to user navigation, which links to the person's activity
navigation for recall from another CWD. Project visitors enter the project directly.
Bulk evidence may use topic-local indexes instead of one root row per source.

### 4. Validity and provenance

Check time-bound state against the question and available observation/validity date.
Past plans are historical; an unresolved defect is an observation as of its last
check, not proof it still occurs. Stable values need no automatic interview.
Compare equal subject/scope before declaring conflict: later dates alone do not
supersede different contexts. Clear corrections update directly; unresolved
contradictions remain visible, asking only when resolution matters now.
Distinguish changed reality from correcting an earlier error. Retained erroneous
claims link to correction and basis; immutable originals stay intact with a
correction at the current owner/evidence index. Retraction is not a guessed replacement.
No expiry invented from silence, no immunity from a `stable` label, no age deletion.

Keep enough attribution, applicability/observation date and source/extract to
interpret and verify. Shared section metadata applies only to claims sharing it;
mark exceptions. A source link cannot replace unique meaningful content. Migration
or storage date is not reconfirmation. Repeated save timestamps, confidence badges
and counters are optional, not required. No raw transcripts or secrets; obey source
storage restrictions. Preserve rationale and qualifications in the current view.

### 5. Bounded impact and protected publication

Inspect owner, navigation and known dependent summaries/links. If local and
consistent, stop. Expand targeted search for unclear ownership, contradictory or
duplicate current claims, or changed person-wide constraints/contracts. Read enough
surrounding content to understand hits; full files only when necessary. Follow actual
affected dependencies until reconciled. Preserve approval, incident, security and
migration floors. New work uses the project's existing task/plan/handoff convention;
no automatic software task creation from knowledge capture.

For moves/replacements/deletions enumerate relevant live inventory **and** search
references before removal; repair live routes and preserve frozen history. Review
current views by synthesis/replacement, not append-only transcripts. Prefer targeted
edits; preserve unrelated simultaneous changes.

Publish through `framework/continuity.md`: protected baseline comparison through
atomic replace, with durable scoped recovery **before** multifile mutation. A final
reread alone is insufficient. A changed baseline requires semantic reconciliation,
never blind retry. Cooperating locks cannot cover external editors: establish an
exclusive window or equivalent storage protection, otherwise defer affected writes.
Project recovery: `<project_root>/context/maintenance-pending.md`; personal recovery:
`<user_repo>/context/user/maintenance-pending.md`, distinct even in the same repo.
Never put private payloads in project recovery. Project-only visitors check only the
project scope. Recovery rereads actual files, preserves later corrections and clears
only reconciled operations. Report **owner updated; reconciliation pending** for
partial publication; do not claim complete save. Cross-repo operations are separate
scoped publications, never a promised global transaction.

### 6. History, imports and maintenance

History preserves decisions, obligations, meaningful trajectories and unresolved
conflicts; no new entry per correction/save or agent self-chronicle. Explicit domain
audit/closeout obligations remain effective. Handoff contains goal/current state,
leading file, next step/blocker per open topic plus necessary decisions, approvals,
failed attempts and job status; no nine-heading template required.

Imports use existing source/package indexes and original-storage policy. Distinguish
discovery, actual source reading, attachment review, relevance screening and knowledge
integration. A summary/metadata scan proves none of the later stages. Record enough
coverage, resume position, unread attachments and pending integration at the existing
owner. Scope-complete assessment is not a completely read corpus. Counts are dated
snapshots unless automatically maintained; no duplicate manual status inventory.
This contract does not authorize reading excluded content or expanding retention.

Around 200 lines, or earlier for mixed topics, review decomposition; coherent longer
files can remain with sectional retrieval. Never evict by size, age or low mentions.
Review touched topics during use; wider housekeeping is explicit/lifecycle-triggered,
not a new scheduled job. Use the same lifecycle, not a separate decay algorithm.

## Modes and outcome

- `process`: `modes/process.md` — project facts/impact; routes person facts separately.
- `user-signal`: `modes/user-signal.md` — personal placement under the shared lifecycle.
- `wrap-up`: `modes/wrap-up.md` — common continuity/history, selected domain contribution.

DONE: admitted deltas reconciled at authorized owners, routes/current views coherent,
pending operation clear, and actual outcome verified. No-change PRESENT is success.
FAIL: report unavailable scope, evidence, coherent snapshot or pending recovery;
retain recoverable work in its scope, never claim completion on partial persistence.
Close-phase retros supply their Patterns-Emerged as process input; do not re-extract
raw sessions. Selected development closeout audit obligations remain domain-owned.

Incident handling: collect observations and locate/assess impact; defer transient
current-state replacement until the incident's recovery/fix boundary. Preserve
necessary incident checkpoints and approvals under local incident rules. Afterwards
reconcile observed end state and relevant failed attempts. No live action is
implicitly authorized by knowledge maintenance.
