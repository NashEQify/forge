# Knowledge Processor — Write

**Ground rule** ([Knowledge Processor](SKILL.md#knowledge-processor)): Preserve knowledge
about the subject and what is needed to continue open work. Do not turn the conversation
or work process into a factual chronicle.

Step-loaded unit of `skills/knowledge_processor/SKILL.md`. Read it before admitting, writing, correcting, moving or
removing a claim, in every mode and under continuous maintenance. Its baseline comes from `retrieve.md` §1.

### 2. Admit, scope and compare

Before classifying a delta, apply the admission check in
`skills/knowledge_processor/continuous-maintenance.md` §Admission to every candidate: topic knowledge, continuation
checkpoints, handoffs, history and FACTS. A session under continuous maintenance loaded that unit at boot; any other
session reads its §Admission now. Keep subject and applicability (person-wide, topic, event/task/setup) distinct
from certainty.

Separate user statements, observations, proposals, third-party reports
and marked inferences. Unknowns can be retained as open questions, never facts.
Useful adverse outcomes, exceptions, rationale and unresolved work matter too.
Do not infer lasting taste from one setup request, relationships from name mentions,
consumption from ownership, or acceptance from an assistant proposal.

Classify **NEW / CHANGED / PRESENT** against the baseline, which includes every
existing occurrence of the same subject in scope (§5), not only the expected owner.
Compare meaning, scope,
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
| Events, observations, source indexes (date and source are the content) | Dated entries at the topic owner |
| Findability | Navigation routes, not duplicate facts |

Split mixed person/activity input at the boundary and cross-link; one leading home
per claim: every claim, fact or rule, has exactly one current statement (§4 says
what stays in it). Minimal implications in summaries link to that owner. Topic names
follow the repository vocabulary; no empty life-domain tree or file per fact. A small
topic can be a section. Do not write facet tags, confidence badges, trajectory labels
or counters. When a claim with a legacy one is written, the tag goes and its meaning
stays as plain words in the repository's language:

| Legacy form | Plain words |
|---|---|
| `[new D]`; any `[… since D]` | stated on D ("Angabe vom D"); "since D" only where the text itself records D as the start |
| `[changed D]` | as of D ("Stand D") |
| `[stable]`, `[emerging]`, `[growing]` without a date | nothing |
| `confidence:` below high | uncertain |
| `user-stated` | according to the person |
| `obs:N`, facet types (`[TRAIT]`, `[ROLE]`, …), `→ VALUE:…` links | nothing; keep a relation only as a sentence |

Read `connections.md` only for relevant actual relationships.

Every new owner must be reachable through question/topic descriptions and useful
aliases. User profile links to user navigation, which links to the person's activity
navigation for recall from another CWD. Project visitors enter the project directly.
Bulk evidence may use topic-local indexes instead of one root row per source.

### 4. Validity and provenance

Check time-bound state against the question and available observation/validity date.
Past plans are historical; an unresolved defect is an observation as of its last
check, not proof it still occurs. Stable values need no automatic interview.
Compare equal subject/scope before declaring conflict: later dates alone do not
supersede different contexts. Clear corrections update the leading owner and every
live copy or summary of the claim in the same change; unresolved contradictions
remain visible at the owner, asking only when resolution matters now.
Distinguish changed reality from correcting an earlier error. Retained erroneous
claims link to correction and basis; immutable originals stay intact with a
correction at the current owner/evidence index. Retraction is not a guessed replacement.
No expiry invented from silence, no immunity from a `stable` label, no age deletion.

**Provenance.** Keep in the claim what a reader needs to interpret it: scope,
qualifications and rationale. By default a claim carries no source note. A time-bound
claim (a state, plan, location, status or event that can age) carries its date in
parentheses, such as `(19.10.2026)` or `(März 2026)`, so that its age stays visible; a
stable preference, value or trait carries none. A claim that comes from someone other
than the scope's own person or project names that source, such as `(laut Anna)`.
A note holds no channel, conversation,
document, quote or reason; those go into the commit. A quote stays only where its
wording is itself the claim. One note at a section heading covers the claims beneath it
that share it. That note is part of the claim, not a copy; a longer note or a
provenance paragraph at a file or section head is drift and is shortened when the file
is next written. What must not exist is a
second statement of the claim: a dated restatement, a provenance or "origin" section, a
copy in another file. Dated records marked as not current (earlier interpretations,
retained erroneous claims, events) are records, not copies: a correction updates the
current owner and leaves them. The rest of a change's provenance (which chat or document, a
short quote, why it changed, a restructuring mapping) goes into the commit that records
the change; Git keeps the old text. Where no commit follows soon (a scope without Git, a
repository committed later under its own rules), the source note at the claim is the
durable trace, so write it whenever the source matters. Shared section metadata applies
only to claims sharing it; mark exceptions. A source link cannot replace unique
meaningful content. Migration or storage date is not reconfirmation. No raw
transcripts or secrets; obey source storage restrictions. A person's own `soul.md` rule
on provenance overrides this default for their data.

### 5. Bounded impact and protected publication

Before every write find the subject's existing occurrences in scope: its route and
candidate owners, a bounded text search for its key terms, and a reading of the hits
(a word search alone misses paraphrases). For a person-wide fact the scope includes
the activity areas of the user repository that use it (an employment status in a
job-search area), read-only. For the same subject and scope the newest evidence of equal
or better support decides (the person's statement over a draft, proposal or import;
observation date, not storage date); the user-scope statement takes it with its source
note or links to the activity area that holds it. Remove a copy only when its leading
owner is committed; otherwise keep the copy or commit both paths together.
An ordinary write reconciles the claim it writes, with its copies and tags; converting
other existing content of a person's scope is maintenance (`history-imports.md` §6), not a side effect.
Inspect owner, navigation and known
dependent summaries/links. If local and consistent, stop. Expand targeted search for
unclear ownership, contradictory or duplicate current claims, or changed person-wide
constraints/contracts. Read enough
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
