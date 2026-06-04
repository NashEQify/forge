# Skill-Description Optimization — Methodology

**Tier:** 1 (operational, companion to `skill-anatomy.md` §description)

## Purpose

`skill-anatomy.md` §description is the **rule** (what a good description is). This file is
the **method**: how to optimize a skill's `description` for correct `P(invoked)` and how to
measure it — at single-skill scale today, with corpus discrimination *derived* from
single-skill runs (see §Corpus scale + §Honest bounds).

The description is the skill's discovery + invocation surface (the model reads only
`name + description` from `available_skills`). The dominant consumer is the autonomous agent
reaching for a tool by capability — so triggering efficacy is load-bearing. Unlike
consistency or completeness it is *measurable in principle* — though the tool that measures
it is external and unpinned (see §Tooling).

## The optimization target — orchestrator, not end-user app

The naive target ("under-triggering is the only failure mode → be pushy") is **end-user-app**
guidance: there a missed skill is the only cost. forge's main consumer is an **orchestrator**
that also pays a real cost per *spurious* fire — a burned turn + context, a mis-routed
delegation. So the target is **correct discrimination**: a precision/recall trade keyed to
invocation cost — maximise recall on genuine under-coverage, bounded by **near-miss
precision**. The NOT-clause is the primary lever, not an afterthought (e.g. `task_creation`
and `task_status_update` share the whole task-noun surface — pushiness on both without sharp
NOT-clauses raises double-fire).

## The measurement — trigger-eval

Realistic queries, each labelled should-trigger or should-NOT-trigger for one skill:

- **should-trigger (8–10):** varied phrasings — formal, casual, typos, concrete detail;
  include cases where the caller does NOT say the skill's noun but needs it.
- **should-NOT-trigger (8–10):** the **near-misses** — share keywords but need a different
  skill. The valuable negatives; obviously-irrelevant queries test nothing.

Score = trigger-rate over N runs/query (Anthropic default 3) on a **held-out** split (the
description is scored on queries it was NOT tuned against, so a lucky over-fit to the tuning
set does not pass).

Eval-set format: a JSON array of `{"query": "…", "should_trigger": true|false}` objects.

## Tooling — external, unpinned (honest status)

The measurement tool is the **Anthropic skill-creator plugin** (`scripts/`), NOT a
framework-owned, version-pinned, pre-commit-reachable harness. It is present on a typical dev
box but is external and model-id-dependent (results are not reproducible across model
versions). Treat it as SHOULD-when-available, never a mandated gate:

- `run_eval.py` — score one description against one trigger-eval set (measure-only).
- `run_loop.py` — 60/40 train/test, 3 runs/query, proposes improved descriptions, picks
  `best_description` by held-out score (≤5 iters). `--results-dir` writes a timestamped
  `results.json` + `report.html`. Requires `--model` — pin the model-id so periodic
  re-audits stay comparable (the tool is model-id-dependent).
- `improve_description.py` — single-shot proposal.

**Capability limit (load-bearing):** `run_eval.py` writes ONE skill's command file and scores
trigger for that one skill. There is **no multi-skill competition surface** — so it cannot
natively measure "the right skill fires and its near-misses do not". Corpus discrimination is
*derived* (next section), not a tool primitive.

## Corpus scale — derived discrimination + a cost gate

Cross-skill confusion (a query fires `task_creation` AND `task_status_update`, or neither) is
the real corpus failure, but the tool only does single-skill scoring. **Derive** it: run
skill A's eval where A's should-NOT set is **seeded from the should-trigger sets of A's
confusable neighbours**, and assert A stays silent on them. That the tool CAN do.

Honest scope: this is per-skill recall+precision with neighbour-seeded negatives — **NOT** a
joint corpus optimum. Optimizing A's boundary shifts B's, which the per-skill loop never
re-measures; so after any boundary-moving change, **re-run the affected neighbours** until no
neighbour's verdict flips (cap ~2 passes). A true
joint metric (inject all N, score which fires) needs a framework-owned harness — a *named
future*, not claimed here.

Method:
1. **Confusable-cluster table (committed, hand-curated).** Define neighbours once — e.g.
   `task_creation ↔ task_status_update`, `frame ↔ bedrock_drill`, `spec_board ↔
   code_review_board`, … — and commit it (`docs/reviews/skill-evals/confusable-clusters.md` — created on the first corpus run, absent until then).
   "Nearest neighbour" IS this table, not an unspecified similarity.
2. **Eval-set authoring (per-skill, agent-drafted).** Draft each should/should-NOT set from
   the SKILL.md body; seed should-NOT from the cluster table. The skill-creator HTML
   user-review gate is **dropped at corpus scale** (41 human reviews don't scale) — an agent
   drafts directly, optional spot-review. Home: `docs/reviews/skill-evals/<skill>/trigger-eval.json`
   (NOT `~/Downloads`).
3. **Cost gate — baseline first.** Order of magnitude is large: ~41 active skills × (8–10 +
   8–10 queries) × 3 runs × ≤5 iters × one `claude -p` per query. So: run measure-only
   `run_eval.py` across all skills first (no improve calls), then `run_loop.py` **only** on
   the weak ones.
4. **Apply.** Adopt a proposed `best_description` only when it wins on held-out AND still
   carries a C3 trigger marker. The "+ NOT-clause" is a **manual reviewer check** (no
   mechanical NOT-clause validator exists today; candidate C3 extension). Record before/after
   in the per-skill results-dir (`docs/reviews/skill-evals/<skill>/`).

## Name contribution — resolved from Anthropic docs (not an experiment)

The `name` DOES contribute to triggering — no A/B needed. Anthropic's skill best-practices
load **both** fields into the system prompt and state that *"Claude uses [the name and
description] when deciding whether to trigger the Skill"*; at scale the dominant failure is
wrong-skill selection between *similar* names (`task-creation` vs `task-status-update`). So a
clear, distinct, descriptive name raises `P(invoked)` for the right skill.

The convention is therefore **fixed, not measured: kebab-case** (Anthropic `name`-field spec —
lowercase + hyphens; the generated CC wrapper name, the real discovery surface, is
kebab-normalized regardless) + **descriptive** (gerund / noun-phrase, never vague/generic). See
`skill-anatomy.md §name`. The earlier "is the name only legibility?" experiment is **dropped**
(documentation answers it), and a `snake_case` normalization of the source name field buys
nothing for triggering (the discovery name is kebab by spec) — so it is not worth its blast
radius.

## When to run

- **On skill add / description change** — measure when the optimizer is available (SHOULD,
  not MUST): the authored description is the hypothesis, the eval is the test. No optimizer →
  the NOT-clause + near-miss judgment is the manual fallback.
- **Periodic corpus audit** — re-run the neighbour-seeded evals as the corpus grows (new
  skills shift the confusable neighbourhood + the cluster table).

## Honest bounds

- The optimizer measures *triggering*, not skill *quality* — a description can trigger
  perfectly for a bad skill. Triggering-efficacy is one axis; consistency / completeness /
  buildability stay separate (human-review) axes.
- The tool is external + unpinned + model-id-dependent — measurement is a SHOULD, not a gate.
- Corpus discrimination is *derived* per-skill, not a joint optimum (a framework-owned N-skill
  scorer is the named future).
- Triggering only fires for tasks the model can't trivially self-handle, so eval queries must
  be substantive.
- Exempt skills: `invocation.primary` ∈ {workflow-step, hook} or `disable-model-invocation:
  true` are invoked positionally, not by `P(invoked)` — don't pull-optimize them (see
  `skill-anatomy.md` §description carve-out).
