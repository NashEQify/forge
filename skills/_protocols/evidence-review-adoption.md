# Evidence pointer schema — mandatory software-review adoption

Step-loaded unit of `skills/_protocols/evidence-pointer-schema.md`. Read it before consuming the reports of a
mandatory software review, deciding and adopting, checking the current result, or writing review-derived tasks. Its
capture side is `evidence-review-capture.md`. Section numbers are protocol-wide: §1–§5 in `evidence-pointer-schema.md`, §6–§7 in
`evidence-pointer-integrations.md`, §8 in `evidence-author-claims.md`, §9–§9.3 in `evidence-review-capture.md`, §9.4–§9.6
in `evidence-review-adoption.md`.

### 9.4 Decision artifact and adoption

```yaml
schema_version: 1
review_run_id: "<run>"
review_subject_digest: "<subject>"
decision: PASS
current_reports:
  - path: "<retained report>"
    sha256: "<raw-byte digest>"
    actor: "<actual returned actor recorded by Buddy>"
    slot: "<captured slot>"
history:                          # optional
  - path: "<earlier report>"
    sha256: "<raw-byte digest>"
```

The artifact keeps Buddy's risk dispositions, uncertainty, dissent and scope limits; Chief recommendations stay
distinct from Buddy's decision. It carries no evidence requirement of its own.

Adoption refuses when:

- the subject is no longer current;
- the decision's frontmatter is unreadable, or its run or subject differs from the capture, or its decision
  word is not supported for the family;
- `current_reports` is empty, an entry lacks a slot, path, actor or 64-hex `sha256`, a slot or path repeats, or
  a captured slot has no report;
- a report's bytes differ from its `sha256`, two reports have identical bytes, or its run echo is missing or
  foreign, or its slot echo names another slot (§9.3);
- a recognized finding has no evidence block at all, or an evidence quote does not resolve (file, lines, quote
  or count do not hold). A pointer with a form problem but a readable in-repository `path` and a `quote` is
  still checked: its quote must occur in that file.

Evidence blocks are read one by one, including `evidence:` blocks in a `yaml` fence under a finding. Everything
else is a **diagnostic**, printed and retained in the adoption: a finding whose evidence does not parse, an
unrecognized finding heading, a missing `schema_version`, subject digest or slot echo, a report for a slot that
was not captured, decision history unequal to capture history. Evidence outside a finding is still resolved;
layout rules of §5 do not apply to adoption.
Buddy addresses each diagnostic in the decision: a finding without parseable evidence is grounded by Buddy's
own check or carried as unverified.

The retained adoption holds the verdict path and digest, the raw decision, the decision word, the current
reports, history, `quotes_verified` (the number of evidence pointers that resolved; a quote is compared only
where the pointer kind reads one, `file_range`, and behind form slips) and the diagnostics. A pointer whose
path lies outside the repository cannot be pinned and stays a diagnostic. A review-backed gate's run receipt and `--review-check`
show the run, subject digest, decision, decision digest, `quotes_verified` and the diagnostic count. Adopting a different decision replaces it and keeps
the earlier one in `adoption_history`; repeating the same adoption changes nothing.

### 9.5 Current check and transition policy

A check recaptures the subject and compares it, rereads the decision and the selected reports and compares their
digests with the adoption; it does not resolve quotes again. Relevant byte, membership, baseline or scope
changes, an owner retry or a replaced report make the adoption noncurrent; edits outside the subject keep it
current. Adoptions retained in an older record format are checked the same way. A check never creates a
capture or an adoption.

| Policy | Permitted when current |
|---|---|
| `evidence` | Any recognized decision |
| `spec_success` | Spec-family `PASS`, and no unresolved mediator audit marker in a captured file |
| `code_success` | Code-family `PASS` or `PASS_WITH_RISKS` |

Spec decisions are `PASS|NEEDS-WORK`; code decisions `PASS|PASS_WITH_RISKS|FAIL|PARTIAL`. A current negative
supports repair, inspection and resume. Code `PARTIAL` is an incomplete verification and never permits success.

**Mediator audit marker.** Under `spec_success` a captured Markdown file that contains
`[mediator-audit-pending]` outside fenced code, inline code and block quotes refuses, and so does a near-miss
spelling of it (other case, extra text before the bracket, missing bracket, joined words without brackets).
Fences follow §5.1's rules and hide lines only within their own indentation; a fence left open or closed at
another indentation hides nothing, and no later fence in that file hides anything either.
After a line that leaves an inline code span open, the rest of that paragraph is scanned without code-span
exemption, so a wrapped span cannot hide a marker. An absent or non-UTF-8 captured file refuses. Drafts stay
writable; the `evidence` policy is unaffected. Removing the marker changes the subject, so the resolved spec
needs a fresh capture and adoption; an earlier approval cannot be reused.

### 9.6 Review-derived task writes

Review-derived task writes use:

| Decision | `board_result` | Review-derived forward readiness |
|---|---|---|
| Spec PASS | `APPROVED` | Allowed |
| Spec NEEDS-WORK | `REJECTED` | Denied |
| Code PASS | `APPROVED` | Allowed |
| Code PASS_WITH_RISKS | `APPROVED_WITH_RISKS` (existing `PASS_WITH_RISKS` alias allowed) | Allowed under existing risk rules |
| Code FAIL | `REJECTED` | Denied |
| Code PARTIAL | `null` | Denied |

Forward readiness means `reviewed|ready|implementing|done`, including a `spec_states` transition to ready. A
spec `APPROVED` write also needs the `spec_success` check, so an unresolved mediator marker cannot be recorded
as approved.
Negative evidence may support `reviewing→fixing` and non-forward `raw|specced` updates. Before such a write the
task-status skill supplies the exact owner and runs the applicable check; on refusal it leaves the requested
fields unchanged. Research, general reasoning and ordinary lifecycle bookkeeping do not acquire this
requirement. Historical lowercase `pass` remains readable.
