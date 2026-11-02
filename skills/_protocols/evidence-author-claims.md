# Evidence pointer schema — author-side pointers

Step-loaded unit of `skills/_protocols/evidence-pointer-schema.md`. Read it before writing an artifact a downstream
consumer will trust as authority for code behaviour: a positive mechanical claim, a completeness or absence claim,
or a committed record that keeps evidence. Read §8.5 for a return, task close or a completion
claim whose reporting step does not specify its evidence. It applies to the author, in every mode. Section numbers are protocol-wide: §1–§5 in `evidence-pointer-schema.md`, §6–§7 in
`evidence-pointer-integrations.md`, §8 in `evidence-author-claims.md`, §9–§9.3 in `evidence-review-capture.md`, §9.4–§9.6
in `evidence-review-adoption.md`.

## 8. Author-side pointers (Buddy-authored artifacts)

§§1-6 define the pointer format the **reviewer** owes in a review
output (machine-checked by the validator + pre-commit Check 5
SOURCE-VERIFICATION). This section extends the same evidence discipline
to the **author** — the orchestrator writing an artifact a downstream
consumer will trust as authority for code behaviour. It is
discipline-only (no validator enforces it), the prose-level sibling of
the machine-checked reviewer mandate. SoT for the author obligation:
`framework/invariants.md` Inv 5 (completeness/absence) + Inv 10 (positive claims).

The author is the worst checker of their own mechanical claims (shared
lens): the same reading that produced a wrong claim re-reads it as
correct. Two failure shapes, two author obligations:

### 8.1 Positive claim — pointer at write time (Inv 10)

A load-bearing mechanical claim about how code behaves, written into a
Buddy-authored ADR / decision-record / handoff / consequential inline
assertion, carries its verifying command or `file:line` INLINE next to
the claim. The pointer need not be the YAML mapping of §2 — a prose
`(scripts/workflow_engine.py:796)` or a shown `grep`/`ls` line is
enough. The point is auditability: the next reader can open the cited
line and check the claim instead of re-trusting the author.

| Without pointer | With pointer |
|---|---|
| "The engine treats `guard` as a stub — it never reads it." | "The engine reads `guard` in `evaluate_guard` at `scripts/workflow_engine.py:796` (`grep -n 'def evaluate_guard'`) — so the 'stub' reading is checkable in one line." |

**Honest limit:** a pointer makes a claim auditable but does NOT prevent
a MISREAD. The author can cite the right line and still conclude wrong.
Only an independent reader catches the misread → §Independent
verify-pass in `skills/documentation_and_adrs/verify-pass.md`. (b) and (c) are
complementary, not redundant.

### 8.2 Completeness / absence claim — inventory-flip (Inv 5)

You cannot prove absence over an OPEN form-space by matching a retired
name: it has many surface-forms (canonical, label, spaced, prose
paraphrase), and a name-grep that finds zero hits proves only that the
*canonical* form is gone — not the variants. Prove completeness by the
INVENTORY-FLIP instead:

1. Enumerate a PINNED listing of what EXISTS in the dimension the
   retired artifact lived in: the files in a dir (`ls agents/`, the
   skill dirs), the named section-headers of a script. No knowledge of
   the dead artifact's name-forms needed.
2. Walk the doc's mechanism nouns (hook names, check names, skill/agent
   names, engine-field names) and confirm each resolves to an entry in
   that listing — a referential-integrity walk. Flag any claim that
   resolves to nothing (a dangling mechanism-claim). The name-grep still
   finds the obvious hits; it just cannot prove the absence — this walk
   does.
3. A "fully removed / all clean" claim ships the inventory-check shown
   (command + output), not asserted.
4. The verifier lens differs from the actor lens — don't verify a
   name-removal with the same name-grep that did the removal.

### 8.2.1 Honest bound — the flip does not magically close every dimension

The flip is only as closed as its listing. **Pin the membership
definition you used**, because for some dimensions "what counts as a
member" is itself a judgment, and an unpinned count re-opens the very
form-space the flip was supposed to close — one level up.

Worked example (real): "the pre-commit checks" is NOT a single number.
`grep -cE '^# -+ Check [0-9]+'` (section headers) → **6**; `grep -c
'BLOCK=1'` → **4**; `grep -c 'WARNINGS+='` → **6**. Three lenses, three
counts. The flip is sound ONLY when you pin which one you mean ("checks
= the 6 `# Check N` section-headers in `pre-commit.sh`"). Unpinned, you
have reproduced bedrock root-cause #1 (open-form-space by enumeration)
inside the supposed fix.

**Two tiers of dimension:**

- **Closed-listing dimensions** — files in a dir, named section-headers,
  skill/agent dirs: the flip genuinely closes the form-space. Strong.
- **Judgment-membership dimensions** — "what counts as a check", a
  config-key with no registry, a workflow-step name scattered across
  many `workflow.yaml` files with no single index: there is no closed
  listing to enumerate. Here the flip DEGRADES to a best-effort
  referential walk against whatever partial listing you can assemble —
  it NARROWS the open-ness, it does not prove absence. Say so; do not
  claim a closed proof you do not have. If the dimension matters and has
  no authoritative listing, that missing index is the real defect to
  file, not something the flip papers over.

This is the council L3 *live-state-vs-claim* axiom turned on the docs:
validate claims-of-mechanism against a pinned real listing — and stay
honest about which dimensions actually have one.

### 8.3 Layers where the asserter owes the grounding

The §8.1 positive-claim pointer is owed wherever a mechanical claim is
AUTHORED, not only in an ADR/handoff. The grep-at-the-asserter
discipline (Inv 10) extends to every layer that emits
mechanism-claims or inherits citations — each grounded *at HEAD, by the
asserter, at that layer*:

| Layer | Claim shape | Where the trigger lives |
|---|---|---|
| Lens (importer/caller count) | "N callers/importers" — grep `import` statements, NOT name-mentions (prose/comments inflate the count) | `agents/code-architect-lens.md` |
| Tester-design | tester output's mechanism-claims (hardcoded literals, path-labels, in-process-vs-network layer-classification) | `skills/adversary_test_plan/challenge-and-integration.md` |
| Dispatch-authoring | a dispatch's "thin wrapper / reuses-existing" claims, and any `file:line`/symbol it cites | `skills/_protocols/dispatch-template.md` |
| Brief-assembly (inherited) | every INHERITED symbol + `file:line` locator a brief carries from a prior artifact resolves at HEAD (phantom → no match; shifted → range moved) | `agents/brief-architect.md` |
| Re-review (fix-completeness) | a fix-claim naming a third-party teardown/lifecycle API verified against the INSTALLED SDK surface, not the remembered API | `skills/code_review_board/verdict.md` §5a |

The principle is one (assert ⇒ ground at HEAD by the asserter); the
triggers land at five read-sites — a lens author does not read the
brief-architect's pre-flight, so each layer carries its own.

### 8.4 What a committed record keeps

A committed work record (return, decision, review, history entry) keeps the
command, its exit status and the decisive result lines beside the claim:
counts, failing names, the verdict, the hash that matched. It does not commit
raw evidence: full command output, junit or other XML, logs, archives,
patches, before/after images, snapshot JSON or copies of repository trees.
Raw evidence stays in the staging copy or scratch space while the task runs;
the commit and Git history are the durable trace. A file that a live consumer
reads (a development binding's source, a skill-eval fixture) is not raw
evidence (`docs/STRUCTURE.md`).

### 8.5 Completion claims

A completion claim says that work reached a state the rows below name. The claim carries the evidence its row
requires, beside it in the record that makes it (the return, the final message, the task's records); there is no
separate list. Without that evidence, write what holds instead of the claim: "not run", "ran before the last edit",
"push pending", "unverified: <reason>". A claim no row names carries its command or `file:line` (§8.1).

| Claim | Required evidence | Not sufficient |
|---|---|---|
| Tests pass | The selection's command (`skills/testing/run-strategy.md` §Test selection), its exit status and counts (passed, failed, skipped), from a run started after the last edit to the paths it covers; a reused run only under that unit's qualified execution evidence | A run before the last edit; a hand-picked subset; skipped or `unexecuted` cases counted as passing |
| A test guards the change | Its failure before the change and its pass after: command and observed output (`skills/testing/SKILL.md` §Meaningful pre-fix witness) | A test seen passing only |
| Instruction-only change verified | The light-path checks (`framework/installation-activation.md` §Light path), each command and result on the final bytes | A pytest run in their place |
| A check is clean (consistency, generator `--check`, lint, hook) | That check's command and result on the final bytes | Another check passing; a hook run on an earlier commit |
| Build succeeds | The build command and exit status 0 on the final source | A clean lint or type check; logs that look right |
| Defect fixed | The retest command and result (`skills/root_cause_fix/SKILL.md` Step 4), the original symptom's reproduction among them, passing | Code changed; other tests passing |
| Delegated work complete | The commits or the review package's diff (`skills/code_review_board/review-package.md`) read against the brief; its unrun tests run per `agents/buddy/operational.md` §Sub-Agent Return | The return's `Status: DONE`; the report's own test counts |
| Requirements met | Each approved acceptance line and exclusion, verbatim, with the pointer where it is met or why not (`skills/_protocols/approved-acceptance.md`); a reading the line leaves open, marked as a reading | Tests passing; a paraphrased acceptance table; a reviewer's overall verdict |
| Finding true or false | The finding's row at the reviewed bytes (`skills/_protocols/finding-verification.md` §The row) | The reviewer's confidence; memory of the code |
| Tasks consistent with each other | The `## Conflicts between tasks` table (`skills/_protocols/plan-conflicts.md` §The table) | Each task's own review |
| Nothing else changed, all removed | The inventory shown (§8.2) | A name search with zero hits |
| Committed, pushed | The commit hash; for a push, the state after it: `git status -sb` showing `...origin/<branch>` with no ahead count | The push command without its result; "will be pushed" in a record written before the push |
| Active (installed, deployed) | Instruction text: committed at the path hosts read, and the installer's check rc 0 (`scripts/forge_install.py --check <project>` for a project install, `--profile full-ai-integration --check` for the machine installation), or the copies it lists named as behind. An install: that check rc 0 after it; on the coordinated maintenance path, the installer's validation `complete` after a fresh session read the change. A service: the user or service outcome after deployment (`framework/invariants.md` Invariant 6) | An install command's exit status; HTTP 200; a live process |

---

## Source

Superpowers (MIT License, © 2025 Jesse Vincent); Forge's register of adopted methods.
